import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SOURCE_ROOT = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2022"
TARGET_ROOT = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
YEAR = "2022"
DAYS = ["day0", "day1", "day2"]

# --- Helper Functions ---

def safe_copy_file(src, dst):
    """Copies a file from src to dst, creating destination directories if needed. Logs errors."""
    if not os.path.exists(src):
        logging.warning(f"Source file not found, skipping: {src}")
        return
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst) # copy2 preserves metadata
        logging.debug(f"Copied file: {src} -> {dst}")
    except Exception as e:
        logging.error(f"Failed to copy file {src} to {dst}: {e}")

def safe_copy_tree(src, dst):
    """Copies a directory from src to dst, creating destination directories if needed. Logs errors."""
    if not os.path.isdir(src):
        logging.warning(f"Source directory not found, skipping: {src}")
        return
    try:
        # Ensure the parent directory of dst exists before calling copytree
        parent_dst = os.path.dirname(dst)
        if parent_dst:
             os.makedirs(parent_dst, exist_ok=True)
        # Use dirs_exist_ok=True for robustness if target subdirs already exist (Python 3.8+)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        logging.debug(f"Copied directory: {src} -> {dst}")
    except Exception as e:
        logging.error(f"Failed to copy directory {src} to {dst}: {e}")

# --- Main Processing Logic ---

def process_ioi_data(source_root, target_root, year, days):
    """Processes the IOI data structure and reorganizes it."""
    logging.info(f"Starting processing for year {year}")
    logging.info(f"Source directory: {source_root}")
    logging.info(f"Target directory: {target_root}")

    source_year_dir = os.path.join(source_root) # Source root already includes year in the example
    target_year_dir = os.path.join(target_root, year)
    os.makedirs(target_year_dir, exist_ok=True)

    # 1. Handle top-level editorial
    logging.info("Processing top-level editorial...")
    source_editorial_pdf = os.path.join(source_year_dir, "editorial.pdf")
    target_editorial_dir = os.path.join(target_year_dir, "editorial")
    if os.path.exists(source_editorial_pdf):
        safe_copy_file(source_editorial_pdf, os.path.join(target_editorial_dir, "editorial.pdf"))
    else:
        logging.warning(f"Top-level editorial not found: {source_editorial_pdf}")

    # 2. Process each day
    for day in days:
        logging.info(f"--- Processing {day} ---")
        source_day_dir = os.path.join(source_year_dir, day)
        target_day_dir = os.path.join(target_year_dir, day)

        if not os.path.isdir(source_day_dir):
            logging.warning(f"Source directory for {day} not found, skipping: {source_day_dir}")
            continue

        os.makedirs(target_day_dir, exist_ok=True)

        # 3. Process each task within the day
        for task_name_camel_case in os.listdir(source_day_dir):
            source_task_dir_top = os.path.join(source_day_dir, task_name_camel_case)

            # Skip files like PDFs or zips at the day level, focus on task directories
            if not os.path.isdir(source_task_dir_top):
                logging.debug(f"Skipping non-directory item in {day}: {task_name_camel_case}")
                continue

            # Heuristic: Assume task names are ProperCase in the top dir, lowercase in nested dirs
            task_name_lower = task_name_camel_case.lower()

            # Define the expected path to the nested task structure
            source_task_dir_nested = os.path.join(source_task_dir_top, task_name_lower, task_name_lower)

            # Verify if it looks like a valid task structure (e.g., contains problem.json or solutions)
            potential_problem_json = os.path.join(source_task_dir_nested, "problem.json")
            potential_solutions_dir = os.path.join(source_task_dir_nested, "solutions")
            if not (os.path.exists(potential_problem_json) or os.path.isdir(potential_solutions_dir)):
                 logging.warning(f"Skipping '{task_name_camel_case}' in {day}: Does not appear to have the expected nested task structure at {source_task_dir_nested}")
                 continue

            logging.info(f"Processing Task: {task_name_camel_case}")
            target_task_dir = os.path.join(target_day_dir, task_name_camel_case)
            os.makedirs(target_task_dir, exist_ok=True)

            # --- Create target subdirectories ---
            target_statements_dir = os.path.join(target_task_dir, "statements")
            target_graders_dir = os.path.join(target_task_dir, "graders")
            target_checkers_dir = os.path.join(target_task_dir, "checkers")
            target_tests_dir = os.path.join(target_task_dir, "tests")
            target_attachments_dir = os.path.join(target_task_dir, "attachments")
            target_solutions_dir = os.path.join(target_task_dir, "solutions")
            target_solutions_codes_dir = os.path.join(target_solutions_dir, "Codes")
            target_solutions_editorial_dir = os.path.join(target_solutions_dir, "editorial")
            target_subtasks_dir = os.path.join(target_task_dir, "subtasks")

            os.makedirs(target_statements_dir, exist_ok=True)
            os.makedirs(target_graders_dir, exist_ok=True)
            os.makedirs(target_checkers_dir, exist_ok=True)
            os.makedirs(target_tests_dir, exist_ok=True)
            os.makedirs(target_attachments_dir, exist_ok=True)
            os.makedirs(target_solutions_dir, exist_ok=True)
            # Don't create Codes/Editorial dirs yet, let copytree/copyfile handle them if source exists
            os.makedirs(target_subtasks_dir, exist_ok=True)
            # Create empty editorial dir as per requirement
            os.makedirs(target_solutions_editorial_dir, exist_ok=True)


            # --- Define source paths ---
            # Statement (PDF)
            statement_pdf_name = f"{task_name_lower}-en_ISC.pdf"
            source_statement_pdf = os.path.join(source_task_dir_top, statement_pdf_name)

            # Attachment (ZIP) - Assume the top-level one is for contestants
            attachment_zip_name = f"{task_name_lower}.zip"
            source_attachment_zip = os.path.join(source_task_dir_top, attachment_zip_name)

            # Components within the nested directory
            source_problem_json = os.path.join(source_task_dir_nested, "problem.json")
            source_graders_dir = os.path.join(source_task_dir_nested, "graders")
            source_checker_dir = os.path.join(source_task_dir_nested, "checker")
            source_solutions_dir = os.path.join(source_task_dir_nested, "solutions")
            source_subtasks_dir = os.path.join(source_task_dir_nested, "subtasks")
            source_tests_dir = os.path.join(source_task_dir_nested, "tests")

            # --- Copy components ---
            logging.debug(f"Task Source Paths for {task_name_camel_case}:")
            logging.debug(f"  Statement: {source_statement_pdf}")
            logging.debug(f"  Attachment: {source_attachment_zip}")
            logging.debug(f"  Nested Root: {source_task_dir_nested}")

            # Copy Statement
            safe_copy_file(source_statement_pdf, os.path.join(target_statements_dir, statement_pdf_name))

            # Copy Attachment
            safe_copy_file(source_attachment_zip, os.path.join(target_attachments_dir, attachment_zip_name))

            # Copy problem.json
            safe_copy_file(source_problem_json, os.path.join(target_task_dir, "problem.json"))

            # Copy Graders
            safe_copy_tree(source_graders_dir, target_graders_dir)

            # Copy Checkers
            safe_copy_tree(source_checker_dir, target_checkers_dir)

            # Copy Tests
            safe_copy_tree(source_tests_dir, target_tests_dir)

            # Copy Subtasks
            safe_copy_tree(source_subtasks_dir, target_subtasks_dir)

            # Copy Solutions (Code) - Copy the entire original solutions folder
            safe_copy_tree(source_solutions_dir, target_solutions_codes_dir)

            # Note: solutions/editorial/ is created but remains empty unless specific
            # non-code solution files are identified later. The top-level editorial.pdf
            # is handled separately.

    logging.info(f"--- Processing complete for year {year} ---")

# --- Execution ---
if __name__ == "__main__":
    # Ensure target root's parent exists if target_root is not just a folder name
    # os.makedirs(os.path.dirname(TARGET_ROOT), exist_ok=True) # Usually not needed if TARGET_ROOT is like /path/to/output
    process_ioi_data(SOURCE_ROOT, TARGET_ROOT, YEAR, DAYS)
    logging.info("Script finished.")