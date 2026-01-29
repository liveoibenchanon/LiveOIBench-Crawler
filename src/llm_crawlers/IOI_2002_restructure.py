import os
import shutil
import re
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define source and destination directories
SOURCE_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2002")
OUTPUT_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/")
YEAR = "2002"
OUTPUT_YEAR_DIR = OUTPUT_BASE_DIR / YEAR

# --- Task definitions ---
# We need to map the different file naming conventions to a standard task name and day.
# Standard names chosen are simple lowercase versions.
# Patterns are regex for matching statement files.
tasks_info = {
    'frog': {'day': 'day1', 'name': 'frog', 'statement_pattern': re.compile(r"01_The_Troublesome_Frog.*\.pdf", re.I)},
    'utopia': {'day': 'day1', 'name': 'utopia', 'statement_pattern': re.compile(r"02_Utopia_Divided.*\.pdf", re.I)},
    'xor': {'day': 'day1', 'name': 'xor', 'statement_pattern': re.compile(r"03_XOR.*\.pdf", re.I)},
    'batch': {'day': 'day2', 'name': 'batch', 'statement_pattern': re.compile(r"01_Batch_Scheduling.*\.pdf", re.I)},
    'bus': {'day': 'day2', 'name': 'bus', 'statement_pattern': re.compile(r"02_Bus_Terminals.*\.pdf", re.I)},
    'rods': {'day': 'day2', 'name': 'rods', 'statement_pattern': re.compile(r"03_Two_Rods.*\.pdf", re.I)},
}

# Helper map for solution handouts (lowercase filename without extension)
solution_handout_map = {f"{name}-handout": info for name, info in tasks_info.items()}

# Helper map for test prefixes per day
test_prefix_map = {}
for day_num in ['day1', 'day2']:
    test_prefix_map[day_num] = {name: info for name, info in tasks_info.items() if info['day'] == day_num}

# --- Utility Functions ---
def safe_copy(src: Path, dest: Path):
    """Copies a file or directory, creating parent directories if needed."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
            logging.info(f"Copied directory {src} to {dest}")
        elif src.is_file():
            shutil.copy2(src, dest)
            logging.info(f"Copied file {src} to {dest}")
        else:
            logging.warning(f"Source {src} is neither a file nor a directory. Skipping.")
    except Exception as e:
        logging.error(f"Error copying {src} to {dest}: {e}")

def create_dirs(task_output_dir: Path):
    """Creates the standard directory structure for a task."""
    for sub_dir in ["statements", "graders", "checkers", "tests", "attachments", "solutions/Codes", "solutions/editorial", "subtasks"]:
        (task_output_dir / sub_dir).mkdir(parents=True, exist_ok=True)

# --- Main Processing Logic ---
def main():
    logging.info(f"Starting processing for IOI {YEAR}")
    logging.info(f"Source directory: {SOURCE_BASE_DIR}")
    logging.info(f"Output directory: {OUTPUT_YEAR_DIR}")

    if not SOURCE_BASE_DIR.is_dir():
        logging.error(f"Source directory {SOURCE_BASE_DIR} not found.")
        return

    # Create the base output directory for the year
    OUTPUT_YEAR_DIR.mkdir(parents=True, exist_ok=True)

    processed_tasks = set() # Keep track of tasks for which we've created dirs

    # 1. Process Problem Statements (from day1/ and day2/ folders)
    logging.info("Processing problem statements...")
    for day_folder in ["day1", "day2"]:
        day_src_dir = SOURCE_BASE_DIR / day_folder
        if not day_src_dir.is_dir():
            logging.warning(f"Directory not found: {day_src_dir}")
            continue

        for item in day_src_dir.iterdir():
            if item.is_file() and item.suffix.lower() == ".pdf":
                matched_task = None
                for task_key, task_data in tasks_info.items():
                    if task_data['statement_pattern'].match(item.name) and task_data['day'] == day_folder:
                        matched_task = task_data
                        break

                if matched_task:
                    task_name = matched_task['name']
                    task_day = matched_task['day']
                    task_output_dir = OUTPUT_YEAR_DIR / task_day / task_name
                    create_dirs(task_output_dir) # Ensure standard structure exists
                    dest_path = task_output_dir / "statements" / item.name
                    safe_copy(item, dest_path)
                    processed_tasks.add((task_day, task_name))
                else:
                    logging.warning(f"Could not map statement file {item.name} in {day_folder} to a known task.")

    # 2. Process Solution Handouts (Editorials)
    logging.info("Processing solution handouts (editorials)...")
    solutions_dir = SOURCE_BASE_DIR / "other_materials" / "Solutions"
    if solutions_dir.is_dir():
        for item in solutions_dir.iterdir():
             if item.is_file() and item.suffix.lower() == ".pdf" and "-handout" in item.stem.lower():
                base_name = item.stem.lower() # e.g., 'frog-handout'
                matched_task = solution_handout_map.get(base_name)

                if matched_task:
                    task_name = matched_task['name']
                    task_day = matched_task['day']
                    task_output_dir = OUTPUT_YEAR_DIR / task_day / task_name
                    create_dirs(task_output_dir) # Ensure structure exists
                    dest_path = task_output_dir / "solutions" / "editorial" / item.name
                    safe_copy(item, dest_path)
                    processed_tasks.add((task_day, task_name)) # Mark task as processed
                else:
                     logging.warning(f"Could not map solution handout {item.name} to a known task.")
    else:
        logging.warning(f"Solutions directory not found: {solutions_dir}")

    # 3. Process Test Cases and Attachments
    logging.info("Processing test cases and attachments...")
    testcases_base_dir = SOURCE_BASE_DIR / "other_materials" / "TestCases"
    if testcases_base_dir.is_dir():
        for day_folder in ["day1", "day2"]:
            day_test_dir = testcases_base_dir / day_folder
            if not day_test_dir.is_dir():
                logging.warning(f"Test case directory not found: {day_test_dir}")
                continue

            # Get task prefixes for the current day
            current_day_tasks = test_prefix_map.get(day_folder, {})

            for item in day_test_dir.iterdir():
                item_name_lower = item.name.lower()
                matched_task = None

                # Special case: rods.library attachment
                if day_folder == "day2" and item.is_dir() and item_name_lower == "rods.library":
                     matched_task = tasks_info.get('rods')
                     if matched_task:
                         task_name = matched_task['name']
                         task_day = matched_task['day']
                         task_output_dir = OUTPUT_YEAR_DIR / task_day / task_name
                         create_dirs(task_output_dir) # Ensure structure exists
                         dest_path = task_output_dir / "attachments" / item.name
                         safe_copy(item, dest_path)
                         processed_tasks.add((task_day, task_name)) # Mark task as processed
                     else:
                         logging.warning(f"Found rods.library but 'rods' task info is missing.")
                     continue # Handled this item, move to next

                # General test file matching based on prefix
                for task_prefix, task_data in current_day_tasks.items():
                    # Use startswith for prefix matching (e.g., 'frog.in1', 'frog01.in')
                    # Also check common separators like '.' or '_' after prefix
                    if item_name_lower.startswith(task_prefix + '.') or \
                       item_name_lower.startswith(task_prefix + '_') or \
                       item_name_lower == task_prefix: # Handles exact match if any
                        matched_task = task_data
                        break

                if matched_task:
                    task_name = matched_task['name']
                    task_day = matched_task['day']
                    task_output_dir = OUTPUT_YEAR_DIR / task_day / task_name
                    create_dirs(task_output_dir) # Ensure structure exists
                    dest_path = task_output_dir / "tests" / item.name
                    safe_copy(item, dest_path)
                    processed_tasks.add((task_day, task_name)) # Mark task as processed
                elif item_name_lower != "rods.library": # Avoid warning for the already handled dir
                    logging.warning(f"Could not map test file/dir {item.name} in {day_folder} to a known task via prefix.")

    else:
        logging.warning(f"Test cases base directory not found: {testcases_base_dir}")

    # 4. Ensure all standard directories exist for all identified tasks
    logging.info("Ensuring standard directory structure for all identified tasks...")
    for task_day, task_name in processed_tasks:
        task_output_dir = OUTPUT_YEAR_DIR / task_day / task_name
        create_dirs(task_output_dir)

    # Note: Code solutions are not explicitly available in the provided unzipped structure.
    # If Solutions.zip contained code, it would need to be extracted and processed separately.
    # The 'solutions/Codes/' directory is created but will remain empty based on the input structure.
    # Similarly, Graders and Checkers are not present.

    # 5. Handle potential general editorial (if any - none specified in this structure)
    # Example: check for a general solutions PDF at top level or in other_materials
    # If found, copy to OUTPUT_YEAR_DIR / "editorial"
    # For IOI 2002, the handouts seem task-specific, so no general editorial is expected here.
    # Create the general editorial folder just in case, although likely empty.
    (OUTPUT_YEAR_DIR / "editorial").mkdir(parents=True, exist_ok=True)


    logging.info(f"Processing for IOI {YEAR} completed.")
    logging.info(f"Output saved to: {OUTPUT_YEAR_DIR}")

if __name__ == "__main__":
    main()