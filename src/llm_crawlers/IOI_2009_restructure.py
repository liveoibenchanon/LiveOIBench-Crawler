import os
import shutil
import re
import zipfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SRC_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New"
DEST_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed"
YEAR = "2009"

IOI_YEAR_SRC = os.path.join(SRC_BASE, YEAR)
IOI_YEAR_DEST = os.path.join(DEST_BASE, YEAR)

# Temporary directory for extracting archives
TEMP_DIR = os.path.join(IOI_YEAR_DEST, "temp_extract")

# --- Helper Functions ---
def safe_create_dir(dir_path):
    """Creates a directory if it doesn't exist."""
    try:
        os.makedirs(dir_path, exist_ok=True)
        # logging.info(f"Ensured directory exists: {dir_path}")
    except OSError as e:
        logging.error(f"Error creating directory {dir_path}: {e}")
        raise

def safe_copy(src, dest):
    """Copies a file, logging errors."""
    try:
        shutil.copy2(src, dest) # copy2 preserves metadata
        # logging.info(f"Copied {src} to {dest}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dest}: {e}")

def safe_copytree(src, dest):
    """Copies a directory tree, logging errors, overwriting existing dirs."""
    try:
        # shutil.copytree doesn't easily overwrite, remove dest first if exists
        if os.path.exists(dest):
             shutil.rmtree(dest)
        shutil.copytree(src, dest, dirs_exist_ok=False) # Use False after deleting
        # logging.info(f"Copied directory {src} to {dest}")
    except Exception as e:
        logging.error(f"Error copying directory {src} to {dest}: {e}")

def extract_zip(zip_path, extract_to):
    """Extracts a zip file safely."""
    try:
        safe_create_dir(extract_to)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logging.info(f"Extracted {zip_path} to {extract_to}")
    except zipfile.BadZipFile:
        logging.error(f"Error: Bad zip file {zip_path}")
    except Exception as e:
        logging.error(f"Error extracting {zip_path} to {extract_to}: {e}")

def find_item_case_insensitive(directory, item_name):
    """Finds a file or directory case-insensitively."""
    if not os.path.exists(directory):
        return None
    for item in os.listdir(directory):
        if item.lower() == item_name.lower():
            return os.path.join(directory, item)
    return None

# --- Main Logic ---
def main():
    logging.info(f"Processing IOI {YEAR} from {IOI_YEAR_SRC} to {IOI_YEAR_DEST}")

    if not os.path.exists(IOI_YEAR_SRC):
        logging.error(f"Source directory {IOI_YEAR_SRC} does not exist.")
        return

    # Clean destination and temp directories before starting
    if os.path.exists(IOI_YEAR_DEST):
        logging.warning(f"Destination directory {IOI_YEAR_DEST} already exists. Removing.")
        shutil.rmtree(IOI_YEAR_DEST)
    if os.path.exists(TEMP_DIR):
         shutil.rmtree(TEMP_DIR)

    safe_create_dir(IOI_YEAR_DEST)
    safe_create_dir(TEMP_DIR)

    temp_solutions_dir = os.path.join(TEMP_DIR, "Solutions")
    temp_tests_dir = os.path.join(TEMP_DIR, "TestCases")

    # 1. Process other_materials
    other_materials_src = os.path.join(IOI_YEAR_SRC, "other_materials")
    editorial_dest = os.path.join(IOI_YEAR_DEST, "editorial")

    if os.path.exists(other_materials_src):
        logging.info("Processing 'other_materials' directory...")

        # Copy main editorial booklet (if exists)
        booklet_files = ["Solutions_and_booklet.pdf", "solutions_and_booklet.pdf"]
        booklet_found = False
        for bf in booklet_files:
            booklet_src_path = os.path.join(other_materials_src, bf)
            if os.path.exists(booklet_src_path):
                safe_create_dir(editorial_dest)
                safe_copy(booklet_src_path, os.path.join(editorial_dest, bf))
                logging.info(f"Copied main editorial: {bf}")
                booklet_found = True
                break
        if not booklet_found:
             logging.warning(f"Main editorial booklet (e.g., Solutions_and_booklet.pdf) not found in {other_materials_src}")

        # Extract Solutions (prefer zip, fallback to folder)
        solutions_zip = os.path.join(other_materials_src, "Solutions.zip")
        solutions_folder = os.path.join(other_materials_src, "Solutions")
        if os.path.exists(solutions_zip):
            extract_zip(solutions_zip, temp_solutions_dir)
        elif os.path.exists(solutions_folder):
            logging.info("Using pre-extracted Solutions folder.")
            safe_copytree(solutions_folder, temp_solutions_dir)
        else:
            logging.warning("Neither Solutions.zip nor Solutions/ folder found in other_materials.")

        # Extract Test Cases (prefer zip, fallback to folder)
        tests_zip = os.path.join(other_materials_src, "TestCases.zip")
        tests_folder = os.path.join(other_materials_src, "TestCases")
        if os.path.exists(tests_zip):
            extract_zip(tests_zip, temp_tests_dir)
        elif os.path.exists(tests_folder):
            logging.info("Using pre-extracted TestCases folder.")
            safe_copytree(tests_folder, temp_tests_dir)
        else:
            logging.warning("Neither TestCases.zip nor TestCases/ folder found in other_materials.")

    else:
        logging.warning(f"'other_materials' directory not found in {IOI_YEAR_SRC}")
        # Proceed anyway, maybe solutions/tests are elsewhere (unlikely for this year)


    # 2. Process day directories
    logging.info("Processing day directories...")
    day_folders = [d for d in os.listdir(IOI_YEAR_SRC) if d.startswith("day") and os.path.isdir(os.path.join(IOI_YEAR_SRC, d))]
    if not day_folders:
         logging.warning(f"No 'dayX' folders found in {IOI_YEAR_SRC}")

    for day_folder in sorted(day_folders):
        day_num_match = re.match(r"day(\d+)", day_folder)
        if not day_num_match:
            logging.warning(f"Could not parse day number from folder: {day_folder}")
            continue
        day_num = day_num_match.group(1)
        day_src_path = os.path.join(IOI_YEAR_SRC, day_folder)
        logging.info(f"Processing {day_folder}...")

        for filename in os.listdir(day_src_path):
            # Identify task statement PDF using regex like '01_TaskName.pdf'
            pdf_match = re.match(r"^\d{1,2}_(.*)\.pdf$", filename, re.IGNORECASE)
            if pdf_match:
                task_name_raw = pdf_match.group(1)
                # Basic cleaning if needed (e.g., removing extra spaces)
                task_name = task_name_raw.strip()
                pdf_src_path = os.path.join(day_src_path, filename)
                logging.info(f"  Found task: '{task_name}' from file {filename}")

                # Create destination structure for the task
                task_dest_base = os.path.join(IOI_YEAR_DEST, f"day{day_num}", task_name)
                statements_dest = os.path.join(task_dest_base, "statements")
                solutions_code_dest = os.path.join(task_dest_base, "solutions", "Codes")
                solutions_editorial_dest = os.path.join(task_dest_base, "solutions", "editorial") # For task-specific solution text/pdf
                tests_dest = os.path.join(task_dest_base, "tests")
                graders_dest = os.path.join(task_dest_base, "graders")
                checkers_dest = os.path.join(task_dest_base, "checkers")
                attachments_dest = os.path.join(task_dest_base, "attachments")
                subtasks_dest = os.path.join(task_dest_base, "subtasks") # Create even if empty

                safe_create_dir(statements_dest)
                safe_create_dir(solutions_code_dest)
                safe_create_dir(solutions_editorial_dest)
                safe_create_dir(tests_dest)
                safe_create_dir(graders_dest)
                safe_create_dir(checkers_dest)
                safe_create_dir(attachments_dest)
                safe_create_dir(subtasks_dest)

                # a) Copy statement
                safe_copy(pdf_src_path, os.path.join(statements_dest, filename))
                logging.info(f"    Copied statement: {filename}")

                # b) Find and copy solutions (code)
                # Search strategy: Look for a directory named like the task_name (case-insensitive)
                # within the extracted temp_solutions_dir.
                solution_src_path = find_item_case_insensitive(temp_solutions_dir, task_name)
                if solution_src_path and os.path.isdir(solution_src_path):
                    logging.info(f"    Found solutions folder: {solution_src_path}")
                    safe_copytree(solution_src_path, solutions_code_dest)
                else:
                    logging.warning(f"    No specific solution folder found for task '{task_name}' in {temp_solutions_dir}. Check root level.")
                    # Fallback: Check for loose files at the root of temp_solutions_dir (less common)
                    found_loose_sol = False
                    if os.path.exists(temp_solutions_dir):
                        for sol_file in os.listdir(temp_solutions_dir):
                             # Example: Check if filename starts with taskname (case-insensitive)
                             if sol_file.lower().startswith(task_name.lower()) and os.path.isfile(os.path.join(temp_solutions_dir, sol_file)):
                                  safe_copy(os.path.join(temp_solutions_dir, sol_file), os.path.join(solutions_code_dest, sol_file))
                                  logging.info(f"    Copied loose solution file: {sol_file}")
                                  found_loose_sol = True
                    if not found_loose_sol and not solution_src_path:
                         logging.warning(f"    Could not find any solutions for task '{task_name}'.")


                # c) Find and copy tests
                # Search strategy: Look for a directory named like the task_name (case-insensitive)
                # within the extracted temp_tests_dir.
                tests_src_path = find_item_case_insensitive(temp_tests_dir, task_name)
                if tests_src_path and os.path.isdir(tests_src_path):
                    logging.info(f"    Found tests folder: {tests_src_path}")
                    safe_copytree(tests_src_path, tests_dest)
                else:
                    logging.warning(f"    No specific tests folder found for task '{task_name}' in {temp_tests_dir}")


                # d) Find Graders/Checkers/Attachments (Placeholders - needs specific logic if files exist)
                # Example: Look for files like 'grader.cpp', 'checker.cpp', 'attachments/*' etc.
                # This might require searching in day_src_path, or within extracted solution/test folders
                # For IOI 2009 structure given, these are unlikely to be separate top-level files.
                # They might be inside the solution or test folders already copied.
                logging.info(f"    Placeholder check for graders/checkers/attachments for '{task_name}'. No specific files searched by default.")


                # e) Task-specific editorial (Could be part of the main booklet, requires PDF parsing, or separate files)
                # If task specific editorials exist as separate files (e.g. in other_materials/Solutions/TaskName_sol.pdf)
                # they would need specific logic here. For now, assume it's in the main booklet.
                logging.info(f"    Placeholder check for task-specific editorial for '{task_name}'.")


    # 3. Cleanup Temporary Directory
    logging.info(f"Cleaning up temporary directory: {TEMP_DIR}")
    try:
        shutil.rmtree(TEMP_DIR)
    except OSError as e:
        logging.error(f"Error removing temporary directory {TEMP_DIR}: {e}")

    logging.info(f"Finished processing IOI {YEAR}. Output at: {IOI_YEAR_DEST}")

if __name__ == "__main__":
    main()