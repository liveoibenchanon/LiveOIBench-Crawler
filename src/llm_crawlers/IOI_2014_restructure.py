import os
import shutil
import re
from pathlib import Path
import zipfile
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SOURCE_ROOT = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2014")
OUTPUT_ROOT = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed")
YEAR = "2014"

OUTPUT_DIR = OUTPUT_ROOT / YEAR
SOURCE_DIR = SOURCE_ROOT # Already points to the 2014 folder

# --- Helper Functions ---

def ensure_dir(path: Path):
    """Creates a directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)

def copy_file(src: Path, dest_dir: Path, dest_filename: str = None):
    """Copies a file to a destination directory."""
    if not src.is_file():
        logging.warning(f"Source file not found or is not a file: {src}")
        return
    ensure_dir(dest_dir)
    dest_path = dest_dir / (dest_filename if dest_filename else src.name)
    try:
        shutil.copy2(src, dest_path)
        logging.info(f"Copied '{src}' to '{dest_path}'")
    except Exception as e:
        logging.error(f"Failed to copy '{src}' to '{dest_path}': {e}")

def copy_directory_contents(src_dir: Path, dest_dir: Path):
    """Copies the contents of a source directory to a destination directory."""
    if not src_dir.is_dir():
        logging.warning(f"Source directory not found or is not a directory: {src_dir}")
        return
    ensure_dir(dest_dir)
    try:
        # Use copytree with dirs_exist_ok=True to copy contents into existing dest_dir
        shutil.copytree(src_dir, dest_dir, dirs_exist_ok=True)
        logging.info(f"Copied contents of '{src_dir}' to '{dest_dir}'")
    except Exception as e:
        logging.error(f"Failed to copy directory contents from '{src_dir}' to '{dest_dir}': {e}")

def create_task_structure(base_dir: Path, day: str, task_name: str) -> Path:
    """Creates the standard directory structure for a task."""
    task_dir = base_dir / day / task_name
    ensure_dir(task_dir / "statements")
    ensure_dir(task_dir / "graders")
    ensure_dir(task_dir / "checkers")
    ensure_dir(task_dir / "tests")
    ensure_dir(task_dir / "attachments")
    ensure_dir(task_dir / "solutions" / "Codes")
    ensure_dir(task_dir / "solutions" / "editorial")
    ensure_dir(task_dir / "subtasks")
    logging.info(f"Created standard structure for task '{task_name}' in '{day}'")
    return task_dir

# --- Main Processing Logic ---

def main():
    logging.info(f"Starting processing for IOI {YEAR}")
    logging.info(f"Source directory: {SOURCE_DIR}")
    logging.info(f"Output directory: {OUTPUT_DIR}")

    if not SOURCE_DIR.is_dir():
        logging.error(f"Source directory {SOURCE_DIR} does not exist.")
        return

    # Clean and create output directory
    if OUTPUT_DIR.exists():
        logging.warning(f"Output directory {OUTPUT_DIR} already exists. Removing it.")
        shutil.rmtree(OUTPUT_DIR)
    ensure_dir(OUTPUT_DIR)
    logging.info(f"Created base output directory: {OUTPUT_DIR}")

    # --- Task Name Mapping (derived from file/folder names) ---
    # We'll derive task names dynamically where possible and use this for validation/lookup
    task_details = {} # Structure: { 'task_name_lower': {'day': 'dayX', 'official_name': 'TaskName'} }

    # --- Process Practice (Day 0) ---
    logging.info("Processing Practice (Day 0)...")
    practice_src_dir = SOURCE_DIR / "other_materials" / "Practice"
    day0_dir = OUTPUT_DIR / "day0"

    if practice_src_dir.is_dir():
        for item in practice_src_dir.iterdir():
            if item.is_file() and item.suffix == '.pdf':
                # Match statement files like "1-square.pdf" or "2-station.pdf"
                match_stmt = re.match(r"(\d+)-([\w\-]+)\.pdf", item.name, re.IGNORECASE)
                # Match solution files like "1-square-solution.pdf"
                match_sol = re.match(r"(\d+)-([\w\-]+)-solution\.pdf", item.name, re.IGNORECASE)

                task_name = None
                file_type = None # 'statement' or 'solution'

                if match_sol:
                    task_prefix_num, task_name_raw = match_sol.groups()
                    task_name = task_name_raw.lower()
                    file_type = 'solution'
                elif match_stmt:
                    task_prefix_num, task_name_raw = match_stmt.groups()
                    task_name = task_name_raw.lower()
                    file_type = 'statement'

                if task_name:
                    if task_name not in task_details:
                         task_details[task_name] = {'day': 'day0', 'official_name': task_name_raw} # Use raw name? Or CamelCase? Let's keep raw for now.

                    task_dir = create_task_structure(OUTPUT_DIR, "day0", task_name)

                    if file_type == 'statement':
                        copy_file(item, task_dir / "statements")
                    elif file_type == 'solution':
                        copy_file(item, task_dir / "solutions" / "editorial")
    else:
        logging.warning(f"Practice source directory not found: {practice_src_dir}")

    # --- Process Contest Days (Day 1, Day 2) ---
    for day_num in [1, 2]:
        day_str = f"day{day_num}"
        day_src_dir = SOURCE_DIR / day_str
        logging.info(f"Processing {day_str.capitalize()}...")

        if not day_src_dir.is_dir():
            logging.warning(f"{day_str.capitalize()} source directory not found: {day_src_dir}")
            continue

        # Process Statement PDFs
        for item in day_src_dir.glob("*.pdf"):
            match = re.match(r"(\d+)_([\w\-]+)\.pdf", item.name, re.IGNORECASE)
            if match:
                task_order, task_name_official = match.groups()
                task_name_lower = task_name_official.lower()

                if task_name_lower not in task_details:
                    task_details[task_name_lower] = {'day': day_str, 'official_name': task_name_official}
                elif task_details[task_name_lower]['day'] != day_str:
                     logging.warning(f"Task '{task_name_lower}' found in {day_str} but already assigned to {task_details[task_name_lower]['day']}. Check source structure.")
                     continue # Skip if day mismatch

                task_dir = create_task_structure(OUTPUT_DIR, day_str, task_name_lower)
                copy_file(item, task_dir / "statements")

    # --- Process Solutions and Test Cases from other_materials ---
    solutions_src_dir = SOURCE_DIR / "other_materials" / "Solutions"
    testcases_src_dir = SOURCE_DIR / "other_materials" / "TestCases"

    # Process Solution PDFs (Editorials)
    if solutions_src_dir.is_dir():
        for item in solutions_src_dir.glob("*-solution.pdf"):
             match = re.match(r"([\w\-]+)-solution\.pdf", item.name, re.IGNORECASE)
             if match:
                 task_name_lower = match.group(1).lower()
                 if task_name_lower in task_details:
                     day_str = task_details[task_name_lower]['day']
                     task_dir = OUTPUT_DIR / day_str / task_name_lower
                     if task_dir.is_dir(): # Ensure task structure was created
                         copy_file(item, task_dir / "solutions" / "editorial")
                     else:
                          logging.warning(f"Task directory for solution '{item.name}' not found for task '{task_name_lower}' in day '{day_str}'.")
                 else:
                     logging.warning(f"Found solution PDF '{item.name}' but task '{task_name_lower}' is unknown or not assigned to a day.")
    else:
        logging.warning(f"Solutions source directory not found: {solutions_src_dir}")

    # Process Test Cases
    if testcases_src_dir.is_dir():
        for item in testcases_src_dir.iterdir():
             # Match directories like "friend-testdata"
             if item.is_dir() and item.name.endswith("-testdata"):
                 task_name_lower = item.name[:-len("-testdata")].lower()
                 if task_name_lower in task_details:
                     day_str = task_details[task_name_lower]['day']
                     task_dir = OUTPUT_DIR / day_str / task_name_lower
                     if task_dir.is_dir(): # Ensure task structure was created
                         copy_directory_contents(item, task_dir / "tests")
                     else:
                         logging.warning(f"Task directory for testdata '{item.name}' not found for task '{task_name_lower}' in day '{day_str}'.")

                 else:
                     logging.warning(f"Found testdata directory '{item.name}' but task '{task_name_lower}' is unknown or not assigned to a day.")
    else:
        logging.warning(f"TestCases source directory not found: {testcases_src_dir}")

    # --- Handle ZIP Archives (Optional - Check if needed) ---
    # The provided structure shows unzipped folders. If code solutions or other
    # materials are *only* in the zips, uncomment and adapt this section.

    # solutions_zip = SOURCE_DIR / "other_materials" / "Solutions.zip"
    # if solutions_zip.exists():
    #     logging.info(f"Found Solutions.zip. Checking contents (extraction logic not implemented yet)...")
    #     # Example: Extract to a temp dir and find code solutions
    #     # with zipfile.ZipFile(solutions_zip, 'r') as zip_ref:
    #     #     # Inspect zip_ref.namelist()
    #     #     # Extract relevant files/folders (e.g., *.cpp, *.java)
    #     #     # Copy them to the correct task_dir / "solutions" / "Codes"
    #     pass # Add extraction and copying logic if needed

    # --- Final Check ---
    logging.info("Checking created structure...")
    found_tasks = set()
    for day_dir in OUTPUT_DIR.iterdir():
        if day_dir.is_dir() and day_dir.name.startswith("day"):
            for task_dir in day_dir.iterdir():
                if task_dir.is_dir():
                    found_tasks.add(f"{day_dir.name}/{task_dir.name}")
                    # Basic check for essential components
                    if not list((task_dir / "statements").glob('*')):
                         logging.warning(f"Task {day_dir.name}/{task_dir.name} seems to be missing statement files.")
                    if not list((task_dir / "tests").glob('*')) and day_dir.name != "day0": # Tests expected for contest days
                         logging.warning(f"Task {day_dir.name}/{task_dir.name} seems to be missing test files.")
                    if not list((task_dir / "solutions" / "editorial").glob('*')):
                         logging.warning(f"Task {day_dir.name}/{task_dir.name} seems to be missing editorial files.")


    logging.info(f"Processed tasks: {', '.join(sorted(list(found_tasks)))}")
    logging.info(f"Processing for IOI {YEAR} complete. Output at: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()