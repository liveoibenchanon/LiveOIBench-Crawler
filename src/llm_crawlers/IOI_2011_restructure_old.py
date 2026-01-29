import os
import shutil
import glob
import re
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base paths
source_base_dir = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2011")
dest_base_dir = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2")
year = "2011"
dest_year_dir = dest_base_dir / year

# --- Configuration ---

# Task names derived from the folder structure and files
# Assume Day 1: elephants, crocodile, parrots
# Assume Day 2: ricehub, garden, race
# This is a reasonable guess based on typical IOI structure.
TASKS = {
    "elephants": {"day": "1"},
    "crocodile": {"day": "1"},
    "parrots": {"day": "1"},
    "ricehub": {"day": "2"},
    "garden": {"day": "2"},
    "race": {"day": "2"},
}

# --- Helper Functions ---

def create_dir(path):
    """Creates a directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)

def copy_file(src, dest_dir, dest_name=None):
    """Copies a file to a destination directory, optionally renaming it."""
    if not src.is_file():
        logging.warning(f"Source file not found or is not a file: {src}")
        return
    dest_path = dest_dir / (dest_name if dest_name else src.name)
    try:
        shutil.copy2(src, dest_path)
        logging.info(f"Copied {src} to {dest_path}")
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dest_path}: {e}")

def find_task_data_root(base_path, task_name):
    """Finds the likely root directory for a task's test data, handling inconsistencies."""
    # Expected patterns: *-test/*-test/ or *-test/*-test/task/
    pattern1 = base_path / f"{task_name}-test" / f"{task_name}-test"
    pattern2 = pattern1 / task_name # Specific case for ricehub

    if pattern2.is_dir() and (pattern2 / "api").is_dir():
         logging.info(f"Found task data root at {pattern2} for {task_name}")
         return pattern2
    if pattern1.is_dir() and (pattern1 / "api").is_dir():
         logging.info(f"Found task data root at {pattern1} for {task_name}")
         return pattern1

    logging.warning(f"Could not reliably determine task data root for {task_name} starting from {base_path}")
    # Fallback to the first level if api exists there (less likely based on structure)
    if (base_path / f"{task_name}-test" / "api").is_dir():
         logging.warning(f"Using fallback task data root: {base_path / f'{task_name}-test'}")
         return base_path / f"{task_name}-test"
    return None # Indicate failure

def find_public_api_root(base_path, task_name):
    """Finds the likely root directory for a task's public API data."""
    # Expected pattern: task/task/
    pattern = base_path / task_name / task_name
    if pattern.is_dir():
        # Check for presence of some expected files to be more certain
        if list(pattern.glob(f"{task_name}.h")) or list(pattern.glob("grader.c*")):
             logging.info(f"Found public api root at {pattern} for {task_name}")
             return pattern
    logging.warning(f"Could not reliably determine public api root for {task_name} at {pattern}")
    # Fallback to the first level if it seems plausible
    first_level = base_path / task_name
    if first_level.is_dir() and (list(first_level.glob(f"{task_name}.h")) or list(first_level.glob("grader.c*"))):
        logging.warning(f"Using fallback public api root: {first_level}")
        return first_level
    return None # Indicate failure


# --- Main Processing Logic ---

logging.info(f"Starting processing for IOI {year}")
create_dir(dest_year_dir)

# 1. Process General Editorials/Overviews
editorial_dest_dir = dest_year_dir / "editorial"
create_dir(editorial_dest_dir)
overview_src_dir = source_base_dir / "tasks" / "EN"
for overview_pdf in overview_src_dir.glob("overview*.pdf"):
    copy_file(overview_pdf, editorial_dest_dir)

# 2. Process Each Task
for task_name, task_info in TASKS.items():
    day = task_info["day"]
    logging.info(f"Processing Task: {task_name} (Day {day})")

    # Define destination directories for the task
    task_dest_dir = dest_year_dir / f"day{day}" / task_name
    statements_dir = task_dest_dir / "statements"
    graders_dir = task_dest_dir / "graders"
    checkers_dir = task_dest_dir / "checkers" # Will likely remain empty
    tests_dir = task_dest_dir / "tests"
    attachments_dir = task_dest_dir / "attachments"
    solutions_dir = task_dest_dir / "solutions"
    solutions_code_dir = solutions_dir / "Codes"
    solutions_editorial_dir = solutions_dir / "editorial"
    # subtasks_dir = task_dest_dir / "subtasks" # Not strictly needed by structure req

    # Create directories
    create_dir(statements_dir)
    create_dir(graders_dir)
    create_dir(checkers_dir)
    create_dir(tests_dir)
    create_dir(attachments_dir)
    create_dir(solutions_dir)
    create_dir(solutions_code_dir) # Create even if empty
    create_dir(solutions_editorial_dir)
    # create_dir(subtasks_dir)

    # --- Process Statements ---
    statement_pdf = overview_src_dir / f"{task_name}.pdf"
    if statement_pdf.exists():
        copy_file(statement_pdf, statements_dir)
    else:
        logging.warning(f"Statement PDF not found for {task_name} at {statement_pdf}")

    # --- Process Solution Editorials ---
    editorial_src_dir = source_base_dir / "tasks" / "solutions"
    editorial_pdf = editorial_src_dir / f"{task_name}.pdf"
    if editorial_pdf.exists():
        copy_file(editorial_pdf, solutions_editorial_dir)
    else:
        logging.warning(f"Solution PDF not found for {task_name} at {editorial_pdf}")

    # --- Locate Task Data Root (Tests/Graders) ---
    testdata_base = source_base_dir / "hsc" / "testdata"
    task_data_root = find_task_data_root(testdata_base, task_name)

    if task_data_root:
        # --- Process Tests ---
        test_files_count = 0
        for subtask_dir in task_data_root.glob("subtask*"):
            if not subtask_dir.is_dir():
                continue
            logging.info(f"Processing tests in {subtask_dir}")
            for infile in subtask_dir.glob("grader.in.*"):
                match = re.match(r"grader\.in\.(\d+)", infile.name)
                if match:
                    test_num = match.group(1)
                    outfile_name = f"grader.expect.{test_num}"
                    outfile = subtask_dir / outfile_name
                    if outfile.exists():
                        copy_file(infile, tests_dir, dest_name=f"{test_num}.in")
                        copy_file(outfile, tests_dir, dest_name=f"{test_num}.out")
                        test_files_count += 2
                    else:
                        logging.warning(f"Input file {infile} found, but corresponding output file {outfile_name} missing.")
            # Check for files directly in api folder too (e.g., sample 1)
            api_dir_for_tests = task_data_root / "api"
            if api_dir_for_tests.exists():
                 for infile in api_dir_for_tests.glob("grader.in.*"):
                    match = re.match(r"grader\.in\.(\d+)", infile.name)
                    if match:
                        test_num = match.group(1)
                        outfile_name = f"grader.expect.{test_num}"
                        outfile = api_dir_for_tests / outfile_name
                        dest_in_file = tests_dir / f"{test_num}.in"
                        # Avoid overwriting if already copied from subtask folder
                        if not dest_in_file.exists():
                            if outfile.exists():
                                copy_file(infile, tests_dir, dest_name=f"{test_num}.in")
                                copy_file(outfile, tests_dir, dest_name=f"{test_num}.out")
                                test_files_count += 2
                            else:
                                logging.warning(f"Input file {infile} found in api/, but corresponding output file {outfile_name} missing.")

        if test_files_count == 0:
             logging.warning(f"No test files found for task {task_name} in {task_data_root}")
        else:
             logging.info(f"Copied {test_files_count // 2} test case pairs for {task_name}")


        # --- Process Graders ---
        api_dir = task_data_root / "api"
        grader_files_found = False
        if api_dir.is_dir():
            for grader_file in api_dir.glob("grader.*"): # C, C++, Pascal
                 if grader_file.suffix in ['.c', '.cpp', '.pas']:
                     copy_file(grader_file, graders_dir)
                     grader_files_found = True
            for header_file in api_dir.glob(f"{task_name}.h"): # Task header
                copy_file(header_file, graders_dir)
                # Headers are often needed by contestants too
                copy_file(header_file, attachments_dir)
                grader_files_found = True # Count header as part of grader components
            # Special case for crocodile library
            if task_name == "crocodile":
                for lib_file in api_dir.glob("crocodilelib.pas"):
                    copy_file(lib_file, graders_dir)
                    copy_file(lib_file, attachments_dir) # Assume library is also public
                    grader_files_found = True

            if not grader_files_found:
                logging.warning(f"No grader files (grader.c/cpp/pas, {task_name}.h) found in {api_dir}")
        else:
            logging.warning(f"API directory not found for {task_name} at {api_dir}")

    else:
        logging.error(f"Could not find data root for task {task_name}. Skipping tests and graders from hsc.")


    # --- Process Attachments (Public API) ---
    public_api_base = source_base_dir / "public_api"
    public_api_root = find_public_api_root(public_api_base, task_name)
    attachments_found = False
    if public_api_root:
        for item in public_api_root.iterdir():
             # Avoid copying zip files if they exist here (shouldn't based on structure, but safety)
             if item.is_file() and item.suffix != '.zip':
                 # Avoid recopying headers already copied from hsc/api
                 if item.name != f"{task_name}.h" and item.name != "crocodilelib.pas":
                    copy_file(item, attachments_dir)
                    attachments_found = True
             elif item.is_dir(): # Copy subdirectories if any (unlikely based on example)
                 shutil.copytree(item, attachments_dir / item.name, dirs_exist_ok=True)
                 logging.info(f"Copied directory {item} to {attachments_dir / item.name}")
                 attachments_found = True

        # Check if the essential header was copied either from hsc or public_api
        if not (attachments_dir / f"{task_name}.h").exists() and task_name != "crocodile": # Crocodile has .h in hsc but not public_api
             # If header wasn't found in hsc/api earlier, try finding it here again just for attachments
            header_in_public = public_api_root / f"{task_name}.h"
            if header_in_public.exists():
                copy_file(header_in_public, attachments_dir)
                attachments_found = True
            else:
                 logging.warning(f"Task header {task_name}.h not found in {api_dir} or {public_api_root}")

        if not attachments_found and not list(attachments_dir.iterdir()): # Check if dir is still empty
             logging.warning(f"No attachment files found for {task_name} in {public_api_root}")
    else:
        logging.warning(f"Could not find public API root for task {task_name}. Skipping attachments from public_api.")
        if not list(attachments_dir.iterdir()): # Check if dir is still empty
             logging.warning(f"No attachments found for {task_name} from any source.")


    # --- Process Solution Codes ---
    # The provided structure doesn't seem to contain official solution *codes*.
    # The 'solutions' folder has PDFs (editorials).
    # The `public_api` has skeleton files (`task.c`, `task.cpp`, etc.), which are attachments.
    # Leaving solutions/Codes empty unless specific solution code folders are found.
    logging.info(f"Solutions code directory created at {solutions_code_dir}, but no source code found in the input structure.")

    # --- Checkers ---
    # No checkers explicitly mentioned or found in the structure.
    logging.info(f"Checkers directory created at {checkers_dir}, but no checkers found in the input structure.")


logging.info(f"Finished processing IOI {year}.")
logging.info(f"Output saved to: {dest_year_dir}")