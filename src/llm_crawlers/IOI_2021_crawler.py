import os
import shutil
import re
import zipfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# --- Configuration ---
SOURCE_ROOT = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-New/2021' # The root directory of the provided structure
OUTPUT_ROOT = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-Processed/2021' # The desired output directory

# --- Mappings and Definitions ---

# Map day directories in source to day numbers in output
DAY_SOURCE_MAP = {
    'day0': os.path.join(SOURCE_ROOT, 'other_materials', 'Practice'),
    'day1': os.path.join(SOURCE_ROOT, 'day1'),
    'day2': os.path.join(SOURCE_ROOT, 'day2'),
}

# Base source directories for common components (relative to SOURCE_ROOT)
TESTCASES_BASE_SRC = os.path.join(SOURCE_ROOT, 'other_materials', 'TestCases')
SOLUTIONS_BASE_SRC = os.path.join(SOURCE_ROOT, 'other_materials', 'Solutions')
PRACTICE_TESTS_SRC = os.path.join(SOURCE_ROOT, 'other_materials', 'Practice', 'tests')

# Define task names explicitly to handle potential inconsistencies
# We'll use lowercase names internally for matching folder names
TASKS = {
    'day0': ['robot', 'jelly', 'gift', 'routers'],
    'day1': ['candies', 'keys', 'parks'],
    'day2': ['dna', 'dungeons', 'registers']
}

# Map statement file patterns (lowercase) to internal task names
# (Handles prefixes like 01_ and suffixes like -ISC)
def get_task_name_from_pdf(filename):
    """Extracts task name from PDF filename."""
    filename_lower = filename.lower()
    # Try matching day 1/2 format (e.g., 01_candies.pdf)
    match = re.match(r'^\d{2}_(.*)\.pdf$', filename_lower)
    if match:
        return match.group(1)
    # Try matching practice format (e.g., robot-isc.pdf)
    match = re.match(r'^(.*?)-?isc\.pdf$', filename_lower)
    if match:
         # Map practice PDF names to folder names if different, else return base
        practice_map = {'robot-isc': 'robot', 'jelly-isc': 'jelly', 'gift-isc': 'gift', 'routers-isc': 'routers'}
        pdf_base = match.group(1) + ('-isc' if filename_lower.endswith('-isc.pdf') else '') # reconstruct original base if needed for map
        return practice_map.get(pdf_base, pdf_base) # Default to base name if not in map
    return None


# --- Helper Functions ---

def safe_copy(src, dst):
    """Copies a file, creating destination directory if needed, handling errors."""
    if not os.path.exists(src):
        logging.warning(f"Source file not found: {src}")
        return
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # logging.info(f"Copied file: {src} -> {dst}")
    except Exception as e:
        logging.error(f"Failed to copy file {src} to {dst}: {e}")

def safe_copytree(src, dst):
    """Copies a directory tree, handling errors and existing directories."""
    if not os.path.isdir(src):
        logging.warning(f"Source directory not found: {src}")
        return
    try:
        # Ensure parent of dst exists, copytree handles dst creation/overwrite
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        # logging.info(f"Copied directory: {src} -> {dst}")
    except Exception as e:
        logging.error(f"Failed to copy directory {src} to {dst}: {e}")

def safe_extract_zip(zip_src, extract_dst):
    """Extracts a zip file, creating destination directory, handling errors."""
    if not os.path.exists(zip_src):
        logging.warning(f"Source zip file not found: {zip_src}")
        return
    try:
        os.makedirs(extract_dst, exist_ok=True)
        with zipfile.ZipFile(zip_src, 'r') as zip_ref:
            zip_ref.extractall(extract_dst)
        logging.info(f"Extracted zip: {zip_src} -> {extract_dst}")
    except zipfile.BadZipFile:
         logging.error(f"Failed to extract zip: {zip_src} is not a valid zip file.")
    except Exception as e:
        logging.error(f"Failed to extract zip {zip_src} to {extract_dst}: {e}")

def copy_folder_contents(src_folder, dst_folder):
    """Copies the contents of src_folder into dst_folder."""
    if not os.path.isdir(src_folder):
        logging.warning(f"Source content directory not found: {src_folder}")
        return
    try:
        os.makedirs(dst_folder, exist_ok=True)
        for item in os.listdir(src_folder):
            s = os.path.join(src_folder, item)
            d = os.path.join(dst_folder, item)
            if os.path.isdir(s):
                safe_copytree(s, d)
            else:
                safe_copy(s, d)
        # logging.info(f"Copied contents: {src_folder} -> {dst_folder}")
    except Exception as e:
        logging.error(f"Failed to copy contents from {src_folder} to {dst_folder}: {e}")


# --- Main Script ---

logging.info(f"Starting IOI 2021 material organization.")
logging.info(f"Source directory: {os.path.abspath(SOURCE_ROOT)}")
logging.info(f"Output directory: {os.path.abspath(OUTPUT_ROOT)}")

# Create the main output directory
os.makedirs(OUTPUT_ROOT, exist_ok=True)

# 1. Copy Global Editorial (assuming Solutions.zip is it)
logging.info("Processing global editorial...")
global_editorial_dest = os.path.join(OUTPUT_ROOT, 'editorial')
solutions_zip_src = os.path.join(SOURCE_ROOT, 'other_materials', 'Solutions.zip')
if os.path.exists(solutions_zip_src):
    os.makedirs(global_editorial_dest, exist_ok=True)
    safe_copy(solutions_zip_src, global_editorial_dest)
else:
    logging.warning(f"Global editorial file not found: {solutions_zip_src}")

# 2. Process each day
for day_label, day_tasks in TASKS.items():
    logging.info(f"\nProcessing {day_label}...")
    day_output_dir = os.path.join(OUTPUT_ROOT, day_label)
    os.makedirs(day_output_dir, exist_ok=True)

    day_statement_src_dir = DAY_SOURCE_MAP.get(day_label)
    if not day_statement_src_dir or not os.path.isdir(day_statement_src_dir):
        logging.warning(f"Statement source directory not found for {day_label}: {day_statement_src_dir}")
        continue

    # Find statement files for the day and map them
    statement_files = {}
    try:
        for f in os.listdir(day_statement_src_dir):
            if f.lower().endswith('.pdf'):
                 task_name = get_task_name_from_pdf(f)
                 if task_name in day_tasks: # Only consider tasks defined for this day
                     statement_files[task_name] = os.path.join(day_statement_src_dir, f)
                 elif task_name:
                     logging.warning(f"Found statement PDF '{f}' but task '{task_name}' is not listed for {day_label}. Skipping.")

    except FileNotFoundError:
         logging.warning(f"Statement source directory listing failed for {day_label}: {day_statement_src_dir}")
         continue


    # Process each task for the day
    for task_name in day_tasks:
        logging.info(f"  Processing task: {task_name}")
        task_output_dir = os.path.join(day_output_dir, task_name)
        os.makedirs(task_output_dir, exist_ok=True)

        # Define standard subdirectories
        statements_dir = os.path.join(task_output_dir, 'statements')
        graders_dir = os.path.join(task_output_dir, 'graders')
        checkers_dir = os.path.join(task_output_dir, 'checkers')
        tests_dir = os.path.join(task_output_dir, 'tests')
        attachments_dir = os.path.join(task_output_dir, 'attachments')
        solutions_dir = os.path.join(task_output_dir, 'solutions')
        solutions_codes_dir = os.path.join(solutions_dir, 'Codes')
        solutions_editorial_dir = os.path.join(solutions_dir, 'editorial') # Create even if empty
        subtasks_dir = os.path.join(task_output_dir, 'subtasks')

        # Create all standard directories
        for d in [statements_dir, graders_dir, checkers_dir, tests_dir,
                  attachments_dir, solutions_dir, solutions_codes_dir,
                  solutions_editorial_dir, subtasks_dir]:
            os.makedirs(d, exist_ok=True)

        # a) Copy Statement
        statement_src = statement_files.get(task_name)
        if statement_src:
            safe_copy(statement_src, statements_dir)
        else:
            logging.warning(f"    Statement PDF not found for task: {task_name} in {day_statement_src_dir}")

        # --- Components primarily from TestCases and Solutions folders (not for day0 based on input structure) ---
        if day_label != 'day0':
            task_src_folder_name = task_name # Assumes folder name matches task name lowercase

            # b) Copy Graders
            grader_src = os.path.join(TESTCASES_BASE_SRC, task_src_folder_name, 'graders')
            copy_folder_contents(grader_src, graders_dir)

            # c) Copy Checkers
            checker_src = os.path.join(TESTCASES_BASE_SRC, task_src_folder_name, 'checker')
            copy_folder_contents(checker_src, checkers_dir)

            # d) Copy Tests (Contents)
            tests_src = os.path.join(TESTCASES_BASE_SRC, task_src_folder_name, 'tests')
            copy_folder_contents(tests_src, tests_dir)

            # e) Copy Attachments
            attachments_src = os.path.join(TESTCASES_BASE_SRC, task_src_folder_name, 'attachments')
            copy_folder_contents(attachments_src, attachments_dir)

            # f) Copy Solutions (Code)
            solution_code_src = os.path.join(SOLUTIONS_BASE_SRC, task_src_folder_name)
            safe_copytree(solution_code_src, solutions_codes_dir)
            # Note: solutions/editorial remains empty as no source was identified

            # g) Copy Subtasks
            subtasks_src = os.path.join(TESTCASES_BASE_SRC, task_src_folder_name, 'subtasks')
            copy_folder_contents(subtasks_src, subtasks_dir)

            # h) Copy problem.json
            problem_json_src = os.path.join(TESTCASES_BASE_SRC, task_src_folder_name, 'problem.json')
            safe_copy(problem_json_src, task_output_dir)

        # --- Handle Day 0 (Practice) specific test structure ---
        elif day_label == 'day0':
            # Practice tasks have tests in zipped files like 'robot-CMS.zip'
            # Map internal task name 'robot' back to expected zip file base 'robot-CMS'
            practice_zip_bases = {
                'robot': 'robot-CMS',
                'jelly': 'jelly-CMS',
                'gift': 'gift-CMS',
                'routers': 'routers-CMS'
            }
            zip_base = practice_zip_bases.get(task_name)
            if zip_base:
                practice_test_zip = os.path.join(PRACTICE_TESTS_SRC, f"{zip_base}.zip")
                safe_extract_zip(practice_test_zip, tests_dir)
            else:
                 logging.warning(f"    Could not determine practice test zip name for task: {task_name}")

            # Log that other components are likely missing for practice tasks based on input
            logging.info(f"    Note: Graders, Checkers, Solutions, Attachments, Subtasks, problem.json are typically sourced differently or may not be present for practice tasks in this structure.")


logging.info("\nOrganization process completed.")
# Check output directory size or list contents for verification if needed
# import subprocess
# subprocess.run(['ls', '-R', OUTPUT_ROOT])