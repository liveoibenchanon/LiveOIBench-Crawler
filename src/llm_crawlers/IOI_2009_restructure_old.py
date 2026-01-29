import os
import shutil
import zipfile
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define source and destination paths
SRC_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2009"
DEST_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
YEAR = "2009"
DEST_YEAR_DIR = os.path.join(DEST_BASE, YEAR)

# --- Task Identification ---
# Derive task names and days primarily from the reliable source code structure
# Treat practice day as Day 0
task_day_map = {
    # From solution_sources0a66/author_sources/Day 0/
    "museum": "Day0",
    "area": "Day0",
    "hill": "Day0",
    # From solution_sources0a66/author_sources/Day 1/
    "poi": "Day1",
    "archery": "Day1",
    "hiring": "Day1",
    "raisins": "Day1",
    # From solution_sources0a66/author_sources/Day 2/
    "mecho": "Day2",
    "salesman": "Day2",
    "garage": "Day2",
    "regions": "Day2",
}

# Files to be treated as general editorial/attachments
general_editorial_keywords = ["overview", "solution", "technical"] # Case-insensitive keywords

def find_task_for_pdf(filename, task_names):
    """
    Tries to match a PDF filename to a known task name.
    Prioritizes matching based on known task names contained within the filename.
    """
    filename_lower = filename.lower()
    matched_task = None
    for task in task_names:
        # Check if the task name is present, potentially preceded by digits/underscores
        # and followed by other characters. Use word boundaries (\b) for better matching.
        # Example: Matches 'hill' in 'Hilld801.pdf', 'regions' in '3_Regionsc951.pdf'
        # Use simple containment as regex with boundaries might be too strict for names like 'poi'
        if task in filename_lower:
            # Basic check for task name substring
             pattern = r'(?:^\d+_)?' + re.escape(task) + r'\b' # Optional number prefix, task name, word boundary
             if re.search(pattern, filename_lower, re.IGNORECASE):
                 if matched_task:
                     logging.warning(f"Ambiguous match for {filename}: Found {task} and {matched_task}. Skipping.")
                     return None # Ambiguous
                 matched_task = task

    # Fallback: try extracting alphanumeric part if no direct match
    if not matched_task:
        match = re.match(r"(?:\d+_)?([a-zA-Z]+)", filename)
        if match:
            potential_task = match.group(1).lower()
            if potential_task in task_names:
                 if matched_task and matched_task != potential_task:
                      logging.warning(f"Ambiguous match for {filename} (fallback): Found {potential_task} and {matched_task}. Skipping.")
                      return None
                 matched_task = potential_task

    return matched_task


def create_base_structure(dest_dir, task_map):
    """Creates the basic directory structure for all tasks."""
    logging.info(f"Creating base structure in {dest_dir}")
    os.makedirs(dest_dir, exist_ok=True)
    os.makedirs(os.path.join(dest_dir, "editorial"), exist_ok=True)
    # os.makedirs(os.path.join(dest_dir, "attachments"), exist_ok=True) # General attachments if needed

    for task, day in task_map.items():
        task_path = os.path.join(dest_dir, day, task)
        os.makedirs(os.path.join(task_path, "statements"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "graders"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "checkers"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "tests"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "attachments"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "solutions", "Codes"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "solutions", "editorial"), exist_ok=True)
        os.makedirs(os.path.join(task_path, "subtasks"), exist_ok=True)
    logging.info("Base structure created.")

def process_root_files(src_dir, dest_dir, task_map):
    """Processes PDFs and ZIP files found in the root source directory."""
    logging.info(f"Processing root files in {src_dir}")
    solution_zip_path = None
    tests_zip_path = None

    for item in os.listdir(src_dir):
        item_path = os.path.join(src_dir, item)
        if os.path.isfile(item_path):
            filename_lower = item.lower()
            # Handle PDFs
            if filename_lower.endswith(".pdf"):
                # Check if it's a general editorial/info file
                is_general = False
                for keyword in general_editorial_keywords:
                    if keyword in filename_lower:
                        dest_pdf_path = os.path.join(dest_dir, "editorial", item)
                        shutil.copy2(item_path, dest_pdf_path)
                        logging.info(f"Copied general file {item} to {dest_pdf_path}")
                        is_general = True
                        break
                
                if not is_general:
                    # Try to match it to a task
                    task_name = find_task_for_pdf(item, task_map.keys())
                    if task_name:
                        day = task_map[task_name]
                        dest_task_stmt_dir = os.path.join(dest_dir, day, task_name, "statements")
                        dest_pdf_path = os.path.join(dest_task_stmt_dir, f"{task_name}_statement.pdf") # Standardize name
                        shutil.copy2(item_path, dest_pdf_path)
                        logging.info(f"Copied statement {item} to {dest_pdf_path}")
                    else:
                         # Maybe specific task editorial? Less likely with generic names like 'Solutionsa84c.pdf'
                         # Place potentially task-specific but unidentifiable PDFs in root editorial for now
                         is_known_general = any(k in filename_lower for k in ["ioi2009_tasks_sol", "solutionsa84c"])
                         if is_known_general:
                             dest_pdf_path = os.path.join(dest_dir, "editorial", item)
                             shutil.copy2(item_path, dest_pdf_path)
                             logging.info(f"Copied probable general file {item} to {dest_pdf_path}")
                         else:
                             logging.warning(f"Could not classify PDF {item}. Skipping.")

            # Handle ZIPs
            elif filename_lower.endswith(".zip"):
                if "solution_sources" in filename_lower:
                    if solution_zip_path:
                        logging.warning(f"Multiple solution zips found. Using {item}.")
                    solution_zip_path = item_path
                    logging.info(f"Found solution source zip: {item}")
                elif "tests" in filename_lower:
                    if tests_zip_path:
                        logging.warning(f"Multiple tests zips found. Using {item}.")
                    tests_zip_path = item_path
                    logging.info(f"Found tests zip: {item}")
                else:
                    logging.warning(f"Unidentified zip file {item}. Skipping.")
        # Ignore subdirectories in this function, they are handled separately or via ZIPs
        elif os.path.isdir(item_path):
             logging.info(f"Ignoring directory {item} in root processing.")


    return solution_zip_path, tests_zip_path

def process_solutions_zip(zip_path, dest_dir, task_map):
    """Extracts solution codes from the specified ZIP file."""
    if not zip_path:
        logging.warning("Solution ZIP path not provided. Skipping solution code processing.")
        return
    logging.info(f"Processing solutions zip: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Find the base path within the zip (e.g., 'solution_sources0a66/author_sources/')
            source_base = ""
            for member in zf.namelist():
                 if 'author_sources/' in member:
                      # Extract the path up to and including author_sources/
                      source_base = member.split('author_sources/')[0] + 'author_sources/'
                      break
            if not source_base:
                 logging.error(f"Could not find 'author_sources/' directory within {zip_path}. Cannot extract solutions.")
                 return

            logging.info(f"Source base in zip detected as: {source_base}")

            for task, day_orig in task_map.items():
                # Map Day0 to Day 0 etc for path construction inside zip
                day_zip_format = day_orig.replace("Day", "Day ") # e.g., Day0 -> Day 0
                
                # Try common source extensions
                found_code = False
                for ext in ['.cpp', '.c', '.pas']: # Add other extensions if needed
                    code_filename = task + ext
                    code_path_in_zip = os.path.join(source_base, day_zip_format, code_filename).replace("\\", "/")

                    if code_path_in_zip in zf.namelist():
                        target_dir = os.path.join(dest_dir, day_orig, task, "solutions", "Codes")
                        target_path = os.path.join(target_dir, code_filename)
                        os.makedirs(target_dir, exist_ok=True)
                        try:
                            # Extract file to the target directory with its original name
                            zf.extract(code_path_in_zip, target_dir)
                            # Rename if necessary (ZipFile extracts keeping the base path)
                            extracted_file_path = os.path.join(target_dir, code_path_in_zip) # Full path as extracted
                            
                            # Check if it was extracted inside unwanted folders
                            if os.path.dirname(extracted_file_path) != target_dir:
                                # Move the file to the correct target dir root
                                final_correct_path = os.path.join(target_dir, os.path.basename(code_path_in_zip))
                                # Ensure not overwriting itself or existing file unintentionally before moving
                                if os.path.abspath(extracted_file_path) != os.path.abspath(final_correct_path):
                                     shutil.move(extracted_file_path, final_correct_path)
                                     logging.info(f"Extracted and moved solution {code_path_in_zip} to {final_correct_path}")
                                     # Clean up empty directories potentially left by extract
                                     try:
                                         os.removedirs(os.path.dirname(extracted_file_path))
                                     except OSError:
                                         pass # Ignore if directory is not empty or doesn't exist
                                else:
                                    logging.info(f"Extracted solution {code_path_in_zip} directly to {target_path}")

                            else:
                                # Rename the final part if needed (e.g. if extract didn't create the final filename)
                                if os.path.abspath(extracted_file_path) != os.path.abspath(target_path):
                                    os.rename(extracted_file_path, target_path)
                                    logging.info(f"Extracted solution {code_path_in_zip} to {target_path}")
                                else:
                                     logging.info(f"Extracted solution {code_path_in_zip} to {target_path} (already correct)")


                            found_code = True
                            break # Found code for this task, move to next task
                        except Exception as e:
                            logging.error(f"Error extracting/moving file {code_path_in_zip}: {e}")
                            
                if not found_code:
                    logging.warning(f"No source code found for task {task} (Day: {day_orig}) in {zip_path}")

    except FileNotFoundError:
        logging.error(f"Solution ZIP file not found: {zip_path}")
    except zipfile.BadZipFile:
        logging.error(f"Invalid or corrupted ZIP file: {zip_path}")
    except Exception as e:
        logging.error(f"An unexpected error occurred processing solutions zip {zip_path}: {e}")


def process_tests_zip(zip_path, dest_dir, task_map):
    """Extracts test cases from the specified ZIP file."""
    if not zip_path:
        logging.warning("Tests ZIP path not provided. Skipping test case processing.")
        return
    logging.info(f"Processing tests zip: {zip_path}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            # Find the base path within the zip (e.g., 'ioi2009_tests/')
            test_base = ""
            members = zf.namelist()
            # Find a common prefix ending with '/'
            if members:
                 common_prefix = os.path.commonprefix(members)
                 # Ensure it looks like a directory path
                 if '/' in common_prefix and not common_prefix.endswith('/'):
                      test_base = common_prefix[:common_prefix.rfind('/')+1]
                 elif common_prefix.endswith('/'):
                     test_base = common_prefix
                 else: # Handle case where zip might not have a single root folder
                      test_base = "" 
            logging.info(f"Test base in zip detected as: {test_base}")

            for member in members:
                # Ensure we are processing files, not directories themselves
                if member.endswith('/'):
                    continue

                # Construct path relative to the detected base
                relative_path = member[len(test_base):] if member.startswith(test_base) else member
                path_parts = relative_path.split('/')
                
                # Expected structure: Day X/task_name/test_file
                if len(path_parts) >= 3:
                    day_folder_zip = path_parts[0] # e.g., "Day 1"
                    task_folder_zip = path_parts[1] # e.g., "raisins"
                    test_filename = os.path.basename(member) # The actual test file name

                    # Normalize day format (e.g., "Day 1" -> "Day1")
                    day_normalized = day_folder_zip.replace(" ", "")

                    # Find the corresponding task name (case-insensitive match)
                    matched_task = None
                    for task_name_map in task_map:
                        if task_folder_zip.lower() == task_name_map.lower():
                             # Check if the day also matches
                             if task_map[task_name_map] == day_normalized:
                                  matched_task = task_name_map
                                  break
                             else:
                                  logging.warning(f"Task folder '{task_folder_zip}' matches task '{task_name_map}', but day '{day_folder_zip}' does not match expected day '{task_map[task_name_map]}'. Skipping file {member}")
                                  break # Stop checking this task folder for this file


                    if matched_task:
                        target_test_dir = os.path.join(dest_dir, day_normalized, matched_task, "tests")
                        target_path = os.path.join(target_test_dir, test_filename)
                        
                        os.makedirs(target_test_dir, exist_ok=True)
                        
                        try:
                           # Extract the file directly to the target directory
                           # We need to ensure the path inside the zip doesn't create unwanted subdirs in the target
                           # Extract to a temp buffer then write to target path
                            with zf.open(member) as source, open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)
                            # logging.debug(f"Extracted test file {member} to {target_path}") # Debug level
                        except Exception as e:
                             logging.error(f"Error extracting test file {member} to {target_path}: {e}")
                    # else: # Only log if it seems like a test file but couldn't match
                    #     if any(ext in test_filename for ext in ['.in', '.out', '.ans', '.txt']):
                    #          logging.warning(f"Could not match test file structure for: {member}. Relative path: {relative_path}")

            logging.info(f"Finished processing tests zip: {zip_path}")

    except FileNotFoundError:
        logging.error(f"Tests ZIP file not found: {zip_path}")
    except zipfile.BadZipFile:
        logging.error(f"Invalid or corrupted ZIP file: {zip_path}")
    except Exception as e:
        logging.error(f"An unexpected error occurred processing tests zip {zip_path}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    logging.info(f"Starting IOI {YEAR} processing.")
    logging.info(f"Source directory: {SRC_BASE}")
    logging.info(f"Destination directory: {DEST_YEAR_DIR}")

    if not os.path.isdir(SRC_BASE):
        logging.error(f"Source directory {SRC_BASE} not found. Aborting.")
        exit(1)

    # 1. Create the basic destination structure
    create_base_structure(DEST_YEAR_DIR, task_day_map)

    # 2. Process root files (PDFs, find ZIPs)
    # Use the source directory containing the PDFs and initial ZIPs
    root_content_dir = SRC_BASE # The directory listed in the prompt
    solution_zip, tests_zip = process_root_files(root_content_dir, DEST_YEAR_DIR, task_day_map)

    # 3. Process Solution Codes ZIP
    # Check if the zip path is relative or absolute, adjust if needed
    if solution_zip and not os.path.isabs(solution_zip):
        solution_zip = os.path.join(root_content_dir, os.path.basename(solution_zip)) # Reconstruct absolute path if only filename was returned
    process_solutions_zip(solution_zip, DEST_YEAR_DIR, task_day_map)

    # 4. Process Tests ZIP
    if tests_zip and not os.path.isabs(tests_zip):
        tests_zip = os.path.join(root_content_dir, os.path.basename(tests_zip)) # Reconstruct absolute path
    process_tests_zip(tests_zip, DEST_YEAR_DIR, task_day_map)

    # 5. Handle potential unpacked source/test folders (if they exist alongside zips)
    # The prompt implies primary content is in zips, but check just in case
    unpacked_solutions_dir = os.path.join(SRC_BASE, "solution_sources0a66") # Name from prompt
    if os.path.isdir(unpacked_solutions_dir) and not solution_zip: # Only if zip wasn't found/processed
         logging.warning(f"Found unpacked solutions folder {unpacked_solutions_dir}, but solution zip processing is preferred. Check if zip was processed.")
         # Add logic here to process unpacked folders similar to zip extraction if needed

    unpacked_tests_dir = os.path.join(SRC_BASE, "ioi2009_tests") # Name from prompt
    if os.path.isdir(unpacked_tests_dir) and not tests_zip:
         logging.warning(f"Found unpacked tests folder {unpacked_tests_dir}, but tests zip processing is preferred. Check if zip was processed.")
         # Add logic here to process unpacked folders similar to zip extraction if needed


    logging.info(f"IOI {YEAR} processing finished. Output at: {DEST_YEAR_DIR}")