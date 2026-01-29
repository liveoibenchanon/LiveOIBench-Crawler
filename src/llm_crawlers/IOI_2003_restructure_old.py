import os
import shutil
import glob
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base directories
SOURCE_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2003"
DEST_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
YEAR = "2003"

# Construct specific source and destination paths
source_dir = SOURCE_BASE # Already includes year in the path description
dest_year_dir = os.path.join(DEST_BASE, YEAR)
dest_editorial_dir = os.path.join(dest_year_dir, "editorial")

def safe_copy(src, dst, is_dir=False):
    """
    Safely copies a file or directory. Creates destination directories if they don't exist.
    Logs warnings if the source doesn't exist. Logs errors during copy.
    Uses copy2 for files to preserve metadata.
    Uses copytree for directories.
    """
    if not os.path.exists(src):
        logging.warning(f"Source '{src}' not found. Skipping.")
        return

    try:
        # Ensure the parent directory of the destination exists
        dest_parent_dir = os.path.dirname(dst)
        if not os.path.exists(dest_parent_dir):
            os.makedirs(dest_parent_dir, exist_ok=True)
            logging.info(f"Created directory: '{dest_parent_dir}'")

        if is_dir:
            # For directories, copy the entire tree
            # dirs_exist_ok=True prevents errors if the destination already exists (useful for retries)
            shutil.copytree(src, dst, dirs_exist_ok=True)
            logging.info(f"Copied directory: '{src}' -> '{dst}'")
        else:
            # For files, copy the file using copy2 to preserve metadata
            shutil.copy2(src, dst)
            logging.info(f"Copied file: '{src}' -> '{dst}'")
    except Exception as e:
        logging.error(f"Error copying '{src}' to '{dst}': {e}")

def classify_and_copy_task_files(task_source_subdir, task_dest_base):
    """
    Classifies files within the task source subdirectory (e.g., 2003/day1/reverse/reverse/)
    and copies them into the appropriate destination folders (graders, checkers, tests, attachments).
    """
    if not os.path.isdir(task_source_subdir):
        logging.warning(f"Task source sub-directory '{task_source_subdir}' not found or not a directory. Skipping classification.")
        return

    # Define destination directories for classified files
    dest_graders_dir = os.path.join(task_dest_base, "graders")
    dest_checkers_dir = os.path.join(task_dest_base, "checkers")
    dest_tests_dir = os.path.join(task_dest_base, "tests")
    dest_attachments_dir = os.path.join(task_dest_base, "attachments")

    # Create these directories if they don't exist
    os.makedirs(dest_graders_dir, exist_ok=True)
    os.makedirs(dest_checkers_dir, exist_ok=True)
    os.makedirs(dest_tests_dir, exist_ok=True)
    os.makedirs(dest_attachments_dir, exist_ok=True)

    logging.info(f"Classifying files in '{task_source_subdir}'")

    copied_to_specific_folder = set()

    for item_name in os.listdir(task_source_subdir):
        src_item_path = os.path.join(task_source_subdir, item_name)

        if os.path.isfile(src_item_path):
            lower_item_name = item_name.lower()
            copied = False

            # --- Classification Logic ---

            # Graders / Libraries
            # Simple check for common grader/library names
            if lower_item_name in ('grader.cpp', 'grader.pas', 'grader.h', 'grader.c',
                                   'score.cpp', 'score.pas', 'score.c', 'score.h'): # Common scoring/grading names
                safe_copy(src_item_path, os.path.join(dest_graders_dir, item_name))
                copied_to_specific_folder.add(item_name)
                copied = True

            # Checkers
            # Check for files starting with 'check' or 'chk'
            elif lower_item_name.startswith(('check', 'chk')):
                 # Avoid matching check*.in/.out test files
                 if not lower_item_name.endswith(('.in', '.out', '.ans', '.sol', '.dat', '.inp')):
                    safe_copy(src_item_path, os.path.join(dest_checkers_dir, item_name))
                    copied_to_specific_folder.add(item_name)
                    copied = True

            # Tests (Inputs and Outputs)
            # Check for common test file extensions
            elif lower_item_name.endswith(('.in', '.dat', '.inp', '.out', '.ans', '.sol')):
                safe_copy(src_item_path, os.path.join(dest_tests_dir, item_name))
                copied_to_specific_folder.add(item_name)
                copied = True

            # Attachments (Makefiles, READMEs, text files)
            # Check for common auxiliary file names/types
            elif lower_item_name == 'makefile' or lower_item_name.startswith('readme') or lower_item_name.endswith('.txt'):
                 safe_copy(src_item_path, os.path.join(dest_attachments_dir, item_name))
                 copied_to_specific_folder.add(item_name)
                 copied = True

            # Note: Solution files (like taskname.cpp, etc.) are *not* explicitly copied here.
            # They are expected to be within the solutions/Codes/ directory copied earlier.
            # Any remaining files not classified above will only reside in solutions/Codes/.

        elif os.path.isdir(src_item_path):
            # Optionally handle subdirectories within the task source subdir if needed
            # For now, we assume most relevant files are at the top level of task_source_subdir
            # The whole structure is already copied to solutions/Codes/
            logging.debug(f"Skipping subdirectory during classification: '{src_item_path}'")


# --- Main Script ---
logging.info(f"Starting IOI data processing for year {YEAR}")
logging.info(f"Source directory: {source_dir}")
logging.info(f"Destination directory: {dest_year_dir}")

# Create base destination directories if they don't exist
os.makedirs(dest_year_dir, exist_ok=True)
os.makedirs(dest_editorial_dir, exist_ok=True)

# 1. Process top-level editorial files (slides)
slides_source_dir = os.path.join(source_dir, "slides")
if os.path.isdir(slides_source_dir):
    logging.info("Processing slides directory...")
    for filename in os.listdir(slides_source_dir):
        if filename.lower().endswith(".pdf"):
            src_path = os.path.join(slides_source_dir, filename)
            dest_path = os.path.join(dest_editorial_dir, filename)
            safe_copy(src_path, dest_path)
else:
    logging.warning(f"Slides directory '{slides_source_dir}' not found.")

# 2. Process days (including day0 for practice)
# Note: The prompt mentions day0 exists at the source path.
days_to_process = ["day0", "day1", "day2"]

for day in days_to_process:
    day_source_dir = os.path.join(source_dir, day)
    day_dest_dir = os.path.join(dest_year_dir, day)

    if not os.path.isdir(day_source_dir):
        logging.info(f"Day directory '{day_source_dir}' not found. Skipping {day}.")
        continue

    logging.info(f"\nProcessing {day}...")
    os.makedirs(day_dest_dir, exist_ok=True)

    # Copy day overview PDF(s) to top-level editorial
    # Example: overview1.pdf, overview2.pdf
    overview_pattern = os.path.join(day_source_dir, f"overview*.pdf")
    for overview_file in glob.glob(overview_pattern):
         filename = os.path.basename(overview_file)
         dest_path = os.path.join(dest_editorial_dir, filename)
         safe_copy(overview_file, dest_path)

    # Process tasks within the day
    for item_name in os.listdir(day_source_dir):
        task_source_dir = os.path.join(day_source_dir, item_name)

        # Check if it's a directory (potential task folder) and not a file like overviewX.pdf
        if not os.path.isdir(task_source_dir):
            continue

        task_name = item_name # The directory name is the task name
        logging.info(f"  Processing task: {task_name}")

        task_dest_dir = os.path.join(day_dest_dir, task_name)
        os.makedirs(task_dest_dir, exist_ok=True)

        # Define standard destination subdirectories for the task
        dest_statements_dir = os.path.join(task_dest_dir, "statements")
        dest_solutions_dir = os.path.join(task_dest_dir, "solutions")
        dest_sol_editorial_dir = os.path.join(dest_solutions_dir, "editorial")
        dest_sol_codes_dir = os.path.join(dest_solutions_dir, "Codes")
        # Other dirs (graders, checkers, tests, attachments) will be created by classify_and_copy_task_files

        os.makedirs(dest_statements_dir, exist_ok=True)
        os.makedirs(dest_sol_editorial_dir, exist_ok=True)
        # dest_sol_codes_dir will be created by safe_copy if needed

        # a. Copy statement PDF (e.g., reverse.pdf)
        statement_pdf_src = os.path.join(task_source_dir, f"{task_name}.pdf")
        statement_pdf_dst = os.path.join(dest_statements_dir, f"{task_name}.pdf")
        safe_copy(statement_pdf_src, statement_pdf_dst)

        # b. Copy data/editorial PDF (e.g., data-reverse.pdf)
        data_pdf_src = os.path.join(task_source_dir, f"data-{task_name}.pdf")
        data_pdf_dst = os.path.join(dest_sol_editorial_dir, f"data-{task_name}.pdf")
        safe_copy(data_pdf_src, data_pdf_dst)

        # c. Copy the task's code/data subdirectory (e.g., reverse/reverse/) to solutions/Codes/
        # This directory contains solutions, tests, graders etc. as distributed.
        task_subdir_src = os.path.join(task_source_dir, task_name)
        if os.path.isdir(task_subdir_src):
            safe_copy(task_subdir_src, dest_sol_codes_dir, is_dir=True)
        else:
             # Log if the crucial subdirectory is missing
             logging.warning(f"Task sub-directory '{task_subdir_src}' not found for task '{task_name}'. Cannot copy to solutions/Codes/ or classify files.")
             # Continue to next task if this core dir is missing
             continue # Skip classification if source subdir doesn't exist

        # d. Classify and copy specific files (tests, graders, checkers, attachments)
        #    from the task's code/data subdirectory (task_subdir_src) to dedicated folders.
        #    This happens *after* copying the entire subdir to solutions/Codes/
        classify_and_copy_task_files(task_subdir_src, task_dest_dir)

        # e. Ignore the .tgz file (e.g., reverse.tgz) as we are using the extracted directory.
        tgz_file = os.path.join(task_source_dir, f"{task_name}.tgz")
        if os.path.exists(tgz_file):
            logging.info(f"  Ignoring archive file: {tgz_file}")


logging.info(f"\nProcessing finished for year {YEAR}")
logging.info(f"Output generated at: {dest_year_dir}")