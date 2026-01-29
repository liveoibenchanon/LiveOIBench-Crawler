import os
import shutil
import zipfile
import re
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
YEAR = "2007"
SRC_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2007"
DEST_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed"
DEST_YEAR_DIR = os.path.join(DEST_BASE_DIR, YEAR)

# --- Helper Functions ---

def safe_copy(src, dst):
    """Copies a file, creating destination directories if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst) # copy2 preserves metadata
        logging.info(f"Copied '{src}' to '{dst}'")
    except Exception as e:
        logging.error(f"Failed to copy '{src}' to '{dst}': {e}")

def safe_copytree(src, dst):
    """Copies a directory tree, creating destination directories if needed."""
    try:
        # Ensure the parent of the destination directory exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # Copy the tree, replacing existing directories if dirs_exist_ok is True (Python 3.8+)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        logging.info(f"Copied directory '{src}' to '{dst}'")
    except FileNotFoundError:
         logging.warning(f"Source directory not found, skipping copy: '{src}'")
    except Exception as e:
        logging.error(f"Failed to copy directory '{src}' to '{dst}': {e}")

def unzip_file(zip_path, extract_to):
    """Unzips a file if it hasn't been extracted already."""
    if not os.path.exists(extract_to):
        logging.info(f"Extracting '{zip_path}' to '{extract_to}'...")
        try:
            os.makedirs(extract_to, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            logging.info(f"Successfully extracted '{zip_path}'")
            return True # Indicate extraction happened
        except zipfile.BadZipFile:
            logging.error(f"Error: '{zip_path}' is not a valid zip file or is corrupted.")
            return False
        except FileNotFoundError:
            logging.error(f"Error: Zip file not found at '{zip_path}'.")
            return False
        except Exception as e:
            logging.error(f"Failed to extract '{zip_path}': {e}")
            return False
    else:
        logging.info(f"Directory '{extract_to}' already exists. Skipping extraction of '{zip_path}'.")
        return False # Indicate no extraction needed now

def normalize_task_name(name):
    """Normalizes task names for consistent matching (e.g., 'Trainings' -> 'training')."""
    return name.lower()

# --- Main Processing Logic ---

def process_ioi_2007():
    logging.info(f"Starting processing for IOI {YEAR}")
    logging.info(f"Source directory: {SRC_BASE_DIR}")
    logging.info(f"Destination directory: {DEST_YEAR_DIR}")

    # Create base destination directory
    os.makedirs(DEST_YEAR_DIR, exist_ok=True)

    # --- Handle Materials ---
    materials_dir = os.path.join(SRC_BASE_DIR, "other_materials")
    solutions_zip = os.path.join(materials_dir, "Solutions.zip")
    testcases_zip = os.path.join(materials_dir, "TestCases.zip")
    solutions_dir_unzipped = os.path.join(materials_dir, "Solutions")
    testcases_dir_unzipped = os.path.join(materials_dir, "TestCases")
    global_editorial_pdf = os.path.join(materials_dir, "Solutions_to_all_problems.pdf")

    # Determine source for solutions and test cases (prefer unzipped)
    solutions_src_dir = None
    if os.path.isdir(solutions_dir_unzipped):
        solutions_src_dir = solutions_dir_unzipped
        logging.info(f"Using existing unzipped solutions directory: {solutions_src_dir}")
    elif os.path.exists(solutions_zip):
        unzip_file(solutions_zip, solutions_dir_unzipped)
        if os.path.isdir(solutions_dir_unzipped):
             solutions_src_dir = solutions_dir_unzipped
             logging.info(f"Using newly unzipped solutions directory: {solutions_src_dir}")
        else:
             logging.error("Failed to find solutions directory after attempting unzip.")
    else:
        logging.warning("Could not find solutions zip or directory.")

    testcases_src_dir = None
    if os.path.isdir(testcases_dir_unzipped):
        testcases_src_dir = testcases_dir_unzipped
        logging.info(f"Using existing unzipped test cases directory: {testcases_src_dir}")
    elif os.path.exists(testcases_zip):
        # Unzipping TestCases.zip usually creates a 'TestCases' folder *inside* the target
        temp_extract_target = os.path.join(materials_dir, "temp_testcases_extract")
        extracted = unzip_file(testcases_zip, temp_extract_target)
        # Check if the expected structure (e.g., TestCases/flood) exists inside temp_extract_target
        potential_testcases_dir = os.path.join(temp_extract_target, "TestCases") # Often zips contain a root folder
        if os.path.isdir(potential_testcases_dir):
             # Move contents up or rename
             try:
                 # Move contents from temp_extract_target/TestCases to materials_dir/TestCases
                 # Need to be careful not to overwrite if materials_dir/TestCases existed before zip attempt
                 if os.path.exists(testcases_dir_unzipped):
                     logging.warning(f"Target unzipped dir {testcases_dir_unzipped} exists, potential conflict.")
                     # Example: Merge contents carefully or just use what's in temp
                     # For simplicity here, let's assume we rename the extracted folder if the target doesn't exist
                     if not os.path.exists(testcases_dir_unzipped):
                          os.rename(potential_testcases_dir, testcases_dir_unzipped)
                          testcases_src_dir = testcases_dir_unzipped
                          logging.info(f"Renamed extracted testcases to: {testcases_src_dir}")
                     else:
                          # If target exists, maybe just use the extracted temp path? Less clean.
                          # Or implement a merge. Let's stick to using the newly extracted path for now.
                          testcases_src_dir = potential_testcases_dir
                          logging.info(f"Using extracted testcases from temporary location: {testcases_src_dir}")


                 else:
                     os.rename(potential_testcases_dir, testcases_dir_unzipped)
                     testcases_src_dir = testcases_dir_unzipped
                     logging.info(f"Renamed extracted testcases to: {testcases_src_dir}")

                 # Clean up empty temp parent dir
                 if os.path.exists(temp_extract_target) and not os.listdir(temp_extract_target):
                    os.rmdir(temp_extract_target)
                 elif os.path.exists(os.path.join(temp_extract_target, "TestCases")): # Check if rename failed and original still there
                     # If rename didn't happen but extraction did, use the path inside temp
                     testcases_src_dir = potential_testcases_dir
                     logging.info(f"Using extracted testcases from temporary location: {testcases_src_dir}")


             except Exception as e:
                  logging.error(f"Error moving/renaming extracted TestCases: {e}")
                  # Fallback: Maybe the zip extracted directly into temp_extract_target?
                  if os.path.isdir(os.path.join(temp_extract_target, "flood")): # Check for a known task folder
                       testcases_src_dir = temp_extract_target
                       logging.info(f"Using extracted testcases directly from: {testcases_src_dir}")

        elif os.path.isdir(os.path.join(temp_extract_target, "flood")): # Check if extracted directly
             testcases_src_dir = temp_extract_target
             logging.info(f"Using extracted testcases directly from: {testcases_src_dir}")
        else:
            logging.error("Failed to find test cases directory structure after attempting unzip.")
            # Cleanup temp dir if it's empty or only contains failed extraction remnants
            if os.path.exists(temp_extract_target):
                 try:
                     shutil.rmtree(temp_extract_target)
                     logging.info(f"Cleaned up temporary extraction directory: {temp_extract_target}")
                 except Exception as e:
                     logging.error(f"Could not remove temp directory {temp_extract_target}: {e}")


    else:
        logging.warning("Could not find test cases zip or directory.")


    # --- Process Global Editorial ---
    dest_editorial_dir = os.path.join(DEST_YEAR_DIR, "editorial")
    if os.path.exists(global_editorial_pdf):
        os.makedirs(dest_editorial_dir, exist_ok=True)
        safe_copy(global_editorial_pdf, os.path.join(dest_editorial_dir, os.path.basename(global_editorial_pdf)))
    else:
        logging.warning(f"Global editorial PDF not found: {global_editorial_pdf}")

    # --- Process Days and Tasks ---
    task_map = {} # Store task_name_norm -> day mapping

    for day_folder in ["day1", "day2"]:
        src_day_dir = os.path.join(SRC_BASE_DIR, day_folder)
        day_num = day_folder[3:] # Extract day number

        if not os.path.isdir(src_day_dir):
            logging.warning(f"Source directory for {day_folder} not found: {src_day_dir}")
            continue

        logging.info(f"Processing {day_folder}...")

        for filename in os.listdir(src_day_dir):
            if filename.lower().endswith(".pdf"):
                match = re.match(r"\d{2}_(.*)\.pdf", filename, re.IGNORECASE)
                if match:
                    task_name_orig = match.group(1)
                    task_name_norm = normalize_task_name(task_name_orig)
                    task_map[task_name_norm] = day_num # Store mapping
                    logging.info(f"Found task: {task_name_orig} (Normalized: {task_name_norm}) in {day_folder}")

                    # --- Create Destination Structure ---
                    dest_task_dir = os.path.join(DEST_YEAR_DIR, f"day{day_num}", task_name_norm)
                    dest_statement_dir = os.path.join(dest_task_dir, "statements")
                    dest_grader_dir = os.path.join(dest_task_dir, "graders")
                    dest_checker_dir = os.path.join(dest_task_dir, "checkers")
                    dest_tests_dir = os.path.join(dest_task_dir, "tests")
                    dest_attachments_dir = os.path.join(dest_task_dir, "attachments")
                    dest_solutions_dir = os.path.join(dest_task_dir, "solutions")
                    dest_solutions_codes_dir = os.path.join(dest_solutions_dir, "Codes")
                    dest_solutions_editorial_dir = os.path.join(dest_solutions_dir, "editorial")
                    dest_subtasks_dir = os.path.join(dest_task_dir, "subtasks")

                    os.makedirs(dest_statement_dir, exist_ok=True)
                    os.makedirs(dest_grader_dir, exist_ok=True)
                    os.makedirs(dest_checker_dir, exist_ok=True)
                    os.makedirs(dest_tests_dir, exist_ok=True)
                    os.makedirs(dest_attachments_dir, exist_ok=True)
                    os.makedirs(dest_solutions_codes_dir, exist_ok=True)
                    os.makedirs(dest_solutions_editorial_dir, exist_ok=True)
                    os.makedirs(dest_subtasks_dir, exist_ok=True)

                    # --- Copy Statement ---
                    src_statement_path = os.path.join(src_day_dir, filename)
                    dest_statement_path = os.path.join(dest_statement_dir, filename)
                    safe_copy(src_statement_path, dest_statement_path)

                    # --- Copy Tests ---
                    if testcases_src_dir:
                        # Find the corresponding test case folder (case-insensitive check)
                        src_test_folder_name = None
                        for item in os.listdir(testcases_src_dir):
                             # Special check for 'training' vs 'trainings'
                             if task_name_norm == 'training' and item.lower() == 'training':
                                 src_test_folder_name = item
                                 break
                             elif item.lower() == task_name_norm:
                                 src_test_folder_name = item
                                 break

                        if src_test_folder_name:
                            src_tests_path = os.path.join(testcases_src_dir, src_test_folder_name)
                            if os.path.isdir(src_tests_path):
                                # Copy contents of the source test folder
                                safe_copytree(src_tests_path, dest_tests_dir)
                            else:
                                logging.warning(f"Source test path is not a directory: {src_tests_path}")
                        else:
                            logging.warning(f"Could not find test case folder for task '{task_name_norm}' in {testcases_src_dir}")
                    else:
                        logging.warning(f"Test cases source directory not available. Cannot copy tests for {task_name_norm}.")


                    # --- Copy Solutions ---
                    if solutions_src_dir:
                         # Find the corresponding solutions folder (case-insensitive check)
                        src_solution_folder_name = None
                        # The structure inside Solutions might be different, common patterns:
                        # 1. Solutions/<task_name>/...
                        # 2. Solutions/<TaskName>/...
                        # 3. Solutions/files starting with <task_name>...
                        # Assuming pattern 1 or 2 first
                        potential_names = [task_name_norm, task_name_orig]
                        if task_name_norm == 'training': # Handle variation explicitly if needed
                            potential_names.append('trainings')

                        found_solution = False
                        for potential_name in potential_names:
                            potential_path = os.path.join(solutions_src_dir, potential_name)
                            if os.path.isdir(potential_path):
                                safe_copytree(potential_path, dest_solutions_codes_dir)
                                found_solution = True
                                break # Found solution dir

                        if not found_solution:
                             # Fallback: check for loose files starting with task name?
                            found_files = False
                            for item in os.listdir(solutions_src_dir):
                                tem_path = os.path.join(solutions_src_dir, item)
                                if os.path.isfile(item_path) and item.lower().startswith(task_name_norm):
                                    safe_copy(item_path, os.path.join(dest_solutions_codes_dir, item))
                                    found_files = True
                            if not found_files:
                                logging.warning(f"Could not find solution folder or files for task '{task_name_norm}' in {solutions_src_dir}")
                        elif found_solution:
                            logging.info(f"Solutions copied for {task_name_norm}")

                    else:
                        logging.warning(f"Solutions source directory not available. Cannot copy solutions for {task_name_norm}.")


    # --- Post-processing/Verification (Optional) ---
    # Could add checks here to ensure all expected tasks were processed.
    expected_tasks = {'aliens', 'flood', 'sails', 'miners', 'pairs', 'training'}
    processed_tasks = set(task_map.keys())
    missing_tasks = expected_tasks - processed_tasks
    extra_tasks = processed_tasks - expected_tasks

    if missing_tasks:
        logging.warning(f"Did not find statement PDFs for expected tasks: {missing_tasks}")
    if extra_tasks:
        logging.warning(f"Found unexpected tasks based on PDFs: {extra_tasks}")


    logging.info(f"Finished processing IOI {YEAR}.")

# --- Run the script ---
if __name__ == "__main__":
    process_ioi_2007()