import os
import shutil
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base paths
source_base_dir = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2019"
output_base_dir = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
year = "2019"

# Create base output directory
output_year_dir = os.path.join(output_base_dir, year)
os.makedirs(output_year_dir, exist_ok=True)
logging.info(f"Created base output directory: {output_year_dir}")

# --- Helper function to safely copy file ---
def safe_copy_file(src, dst_dir, dst_filename=None):
    """Copies a file if it exists, creating the destination directory."""
    if not os.path.exists(src):
        logging.warning(f"Source file not found, skipping: {src}")
        return
    try:
        os.makedirs(dst_dir, exist_ok=True)
        dst_path = os.path.join(dst_dir, dst_filename or os.path.basename(src))
        shutil.copy2(src, dst_path)
        logging.debug(f"Copied file: {src} -> {dst_path}")
    except Exception as e:
        logging.error(f"Error copying file {src} to {dst_dir}: {e}")

# --- Helper function to safely copy directory contents ---
def safe_copy_tree_contents(src, dst_dir):
    """Copies the contents of a directory if it exists, creating the destination directory."""
    if not os.path.isdir(src):
        logging.warning(f"Source directory not found, skipping: {src}")
        return
    try:
        # Ensure destination exists
        os.makedirs(dst_dir, exist_ok=True)
        # Use copytree with dirs_exist_ok=True (Python 3.8+)
        # To copy *contents*, we iterate and copy items individually or use a workaround
        if hasattr(shutil, 'copytree') and 'dirs_exist_ok' in shutil.copytree.__code__.co_varnames:
             shutil.copytree(src, dst_dir, dirs_exist_ok=True)
             logging.debug(f"Copied directory contents: {src} -> {dst_dir}")
        else: # Fallback for older Python versions / ensure contents are copied
             for item in os.listdir(src):
                 s = os.path.join(src, item)
                 d = os.path.join(dst_dir, item)
                 if os.path.isdir(s):
                     shutil.copytree(s, d, symlinks=False, ignore=None)
                 else:
                     shutil.copy2(s, d)
             logging.debug(f"Copied directory contents (manual): {src} -> {dst_dir}")

    except Exception as e:
        logging.error(f"Error copying directory {src} to {dst_dir}: {e}")

# --- Helper function to copy entire directory ---
def safe_copy_directory(src, dst_dir):
    """Copies an entire directory if it exists, creating parent destination directory."""
    if not os.path.isdir(src):
        logging.warning(f"Source directory not found, skipping: {src}")
        return
    try:
        # We want to copy the src folder *into* dst_dir, maintaining the src folder name
        # Example: copy src='solutions/' to dst_dir='.../solutions/Codes/' -> .../solutions/Codes/solutions/
        # Correction: We want src='solutions/' contents copied to dst_dir='.../solutions/Codes/'
        # Let's use safe_copy_tree_contents for clarity on copying contents.
        safe_copy_tree_contents(src, dst_dir)

    except Exception as e:
        logging.error(f"Error copying directory {src} to {dst_dir}: {e}")


# --- Pre-collect potential Day 0 editorials ---
day0_editorials = {}
day0_dir_src = os.path.join(source_base_dir, "day0")
if os.path.isdir(day0_dir_src):
    for item in os.listdir(day0_dir_src):
        item_path = os.path.join(day0_dir_src, item)
        if item.endswith(".pdf") and os.path.isfile(item_path):
            task_name = item[:-4].lower() # e.g., 'packing' from 'packing.pdf'
            # Avoid adding 'notice' or others if they aren't tasks
            # We'll check later if a task with this name exists
            day0_editorials[task_name] = item_path
            logging.debug(f"Found potential day0 editorial: {item_path} for task '{task_name}'")


# Iterate through days (treating practice as day0)
for day in ["day0", "day1", "day2"]:
    day_folder_src = os.path.join(source_base_dir, day)
    output_day_folder = os.path.join(output_year_dir, day)

    if not os.path.isdir(day_folder_src):
        logging.warning(f"Day folder not found: {day_folder_src}")
        continue

    os.makedirs(output_day_folder, exist_ok=True)
    logging.info(f"Processing {day} folder: {day_folder_src}")

    # Find tasks within the day folder
    # Tasks seem to be in lowercase folders containing another folder of the same name
    for entry in os.listdir(day_folder_src):
        potential_task_dir = os.path.join(day_folder_src, entry)

        # Check if it's a directory and likely contains the actual task data folder
        if os.path.isdir(potential_task_dir):
            # Check for the nested structure (e.g., split/split, shoes/shoes)
            inner_task_dir = os.path.join(potential_task_dir, entry)

            # The *actual* task name is the folder name (entry)
            task_name = entry.lower() # Standardize to lowercase

            # Verify if the inner directory looks like a task folder (contains key files/dirs)
            if os.path.isdir(inner_task_dir) and \
               (os.path.exists(os.path.join(inner_task_dir, "problem.json")) or
                os.path.exists(os.path.join(inner_task_dir, "statement.md")) or
                os.path.isdir(os.path.join(inner_task_dir, "solutions")) or
                os.path.isdir(os.path.join(inner_task_dir, "tests"))):

                logging.info(f"  Processing Task: {task_name} from {inner_task_dir}")

                # --- Define Destination Paths ---
                dest_task_dir = os.path.join(output_day_folder, task_name)
                dest_statements = os.path.join(dest_task_dir, "statements")
                dest_graders = os.path.join(dest_task_dir, "graders")
                dest_checkers = os.path.join(dest_task_dir, "checkers")
                dest_tests = os.path.join(dest_task_dir, "tests")
                dest_attachments = os.path.join(dest_task_dir, "attachments")
                dest_solutions = os.path.join(dest_task_dir, "solutions")
                dest_solutions_codes = os.path.join(dest_solutions, "Codes")
                dest_solutions_editorial = os.path.join(dest_solutions, "editorial")
                dest_subtasks = os.path.join(dest_task_dir, "subtasks")

                # Create Directories for the task
                os.makedirs(dest_task_dir, exist_ok=True)
                # No need to pre-create subdirs like dest_statements, helpers will do it

                # --- Define Source Paths (within inner_task_dir) ---
                src_statement_md = os.path.join(inner_task_dir, "statement.md")
                src_problem_json = os.path.join(inner_task_dir, "problem.json")
                src_graders = os.path.join(inner_task_dir, "graders")
                src_checkers = os.path.join(inner_task_dir, "checker") # Source is often singular 'checker'
                src_tests = os.path.join(inner_task_dir, "tests")
                src_attachments = os.path.join(inner_task_dir, "attachments")
                src_solutions = os.path.join(inner_task_dir, "solutions")
                src_subtasks = os.path.join(inner_task_dir, "subtasks")

                # --- Copy Components ---

                # 1. Problem Statement
                safe_copy_file(src_statement_md, dest_statements)

                # 2. Problem JSON
                safe_copy_file(src_problem_json, dest_task_dir, "problem.json") # Copy to task root

                # 3. Graders
                safe_copy_directory(src_graders, dest_graders)

                # 4. Checkers
                safe_copy_directory(src_checkers, dest_checkers)

                # 5. Tests
                safe_copy_directory(src_tests, dest_tests)

                # 6. Attachments (Public files)
                safe_copy_directory(src_attachments, dest_attachments)
                # Also check for top-level zip file in dayX/ as potential attachment
                top_level_zip = os.path.join(day_folder_src, task_name + ".zip")
                if os.path.isfile(top_level_zip):
                     logging.info(f"    Found top-level attachment zip: {top_level_zip}")
                     safe_copy_file(top_level_zip, dest_attachments)


                # 7. Solutions Codes
                # Copy the *entire* original solutions/* structure into solutions/Codes/
                safe_copy_directory(src_solutions, dest_solutions_codes)


                # 8. Subtasks
                safe_copy_directory(src_subtasks, dest_subtasks)


                # 9. Editorials (Reviews, Day0 PDFs)
                # Check for review.pdf in capitalized folder (e.g., day1/Split/review.pdf)
                capitalized_task_folder_name = task_name.capitalize()
                # Handle potential inconsistency e.g. 'rect' vs 'Rect'
                possible_review_folders = [
                    os.path.join(day_folder_src, task_name.capitalize()), # e.g. day1/Split
                    os.path.join(day_folder_src, task_name) # e.g. day1/split (less likely for review.pdf based on structure)
                ]
                found_review = False
                for review_folder in possible_review_folders:
                    if os.path.isdir(review_folder):
                        src_review_pdf = os.path.join(review_folder, "review.pdf")
                        if os.path.exists(src_review_pdf):
                            logging.info(f"    Found editorial: {src_review_pdf}")
                            safe_copy_file(src_review_pdf, dest_solutions_editorial)
                            found_review = True
                            break # Found it, no need to check other possibilities

                # Check for Day 0 PDF associated with this task name
                if task_name in day0_editorials:
                     src_day0_pdf = day0_editorials[task_name]
                     logging.info(f"    Found day0 editorial: {src_day0_pdf}")
                     safe_copy_file(src_day0_pdf, dest_solutions_editorial)


                # If no specific editorial found, create the folder anyway for consistency
                if not os.path.exists(dest_solutions_editorial):
                    os.makedirs(dest_solutions_editorial, exist_ok=True)

            # else: # This directory didn't contain the expected inner structure or files
            #    logging.debug(f"  Skipping directory (no valid inner task structure found): {potential_task_dir}")


logging.info("Processing complete.")