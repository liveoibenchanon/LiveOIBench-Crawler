import os
import shutil
import zipfile
import re
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SRC_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2004")
DEST_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed")
YEAR = "2004"

# --- Helper Functions ---

def safe_copy(src, dest):
    """Copies a file or directory, creating parent directories if needed."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
            logging.info(f"Copied directory {src} to {dest}")
        else:
            shutil.copy2(src, dest) # copy2 preserves metadata
            logging.info(f"Copied file {src} to {dest}")
    except FileNotFoundError:
        logging.error(f"Source file/directory not found: {src}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dest}: {e}")

def extract_zip(zip_path, extract_to):
    """Extracts a zip file."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            logging.info(f"Extracted {zip_path} to {extract_to}")
            return True
    except FileNotFoundError:
        logging.error(f"Zip file not found: {zip_path}")
        return False
    except Exception as e:
        logging.error(f"Error extracting {zip_path}: {e}")
        return False

def get_task_name_from_statement(pdf_filename):
    """Extracts task name from statement PDF filename (e.g., 01_Artemis.pdf -> Artemis)."""
    match = re.match(r'\d+_(.*)\.pdf', pdf_filename, re.IGNORECASE)
    if match:
        # Capitalize first letter, rest lower (or use title() if appropriate)
        name = match.group(1)
        # Simple capitalization:
        # return name[0].upper() + name[1:].lower()
        # Title case (might be better if names are multi-word, like "Polygon Tool"):
        return name.replace('_', ' ').title().replace(' ', '') # E.g. Artemis, Polygon
    return None

def get_task_name_from_editorial_pdf(pdf_filename):
    """Extracts task name from editorial PDF filename (e.g., artemis-sol.pdf -> Artemis)."""
    match = re.match(r'(.*)-sol\.pdf', pdf_filename, re.IGNORECASE)
    if match:
        name = match.group(1)
        return name.replace('_', ' ').title().replace(' ', '') # E.g. Artemis
    return None


# --- Main Processing Logic ---

src_dir = SRC_BASE_DIR
dest_dir = DEST_BASE_DIR / YEAR

# Create the base destination directory for the year
dest_dir.mkdir(parents=True, exist_ok=True)
logging.info(f"Ensured destination directory exists: {dest_dir}")

# --- Data Structures to hold discovered tasks ---
# tasks = { 'day0': {}, 'day1': {}, 'day2': {} } # {day: {task_name: {paths...}}}
# Let's use a simpler mapping first: task_name -> day
task_to_day_map = {}
task_names = {} # Store the "official" casing, mapping lowercase to official

# 1. Process Problem Statements (to identify tasks and days)
logging.info("--- Processing Problem Statements ---")
for day_folder in ["day1", "day2"]:
    day_src_path = src_dir / day_folder
    if day_src_path.is_dir():
        for item in day_src_path.iterdir():
            if item.is_file() and item.suffix.lower() == '.pdf':
                task_name = get_task_name_from_statement(item.name)
                if task_name:
                    logging.info(f"Found statement for task: {task_name} in {day_folder}")
                    task_names[task_name.lower()] = task_name # Store mapping
                    task_to_day_map[task_name.lower()] = day_folder
                    # Copy statement
                    statement_dest_dir = dest_dir / day_folder / task_name / "statements"
                    # Use original capitalization for the directory, standardized name for file
                    safe_copy(item, statement_dest_dir / f"{task_name}.pdf")
                else:
                    logging.warning(f"Could not parse task name from statement: {item.name} in {day_folder}")
    else:
        logging.warning(f"Source directory for {day_folder} statements not found: {day_src_path}")

# Note: Day 0 (Practice) tasks statements are not explicitly listed.
# We might discover them later from test cases or solutions.

# 2. Process PDF Editorials (Solution descriptions)
logging.info("--- Processing PDF Editorials ---")
editorial_src_dir = src_dir / "other_materials" / "Solutions"
if editorial_src_dir.is_dir():
    for item in editorial_src_dir.iterdir():
        if item.is_file() and item.suffix.lower() == '.pdf':
            task_name_lower = None
            parsed_name = get_task_name_from_editorial_pdf(item.name)
            if parsed_name:
                task_name_lower = parsed_name.lower()

            if task_name_lower and task_name_lower in task_to_day_map:
                day = task_to_day_map[task_name_lower]
                official_task_name = task_names[task_name_lower]
                editorial_dest_dir = dest_dir / day / official_task_name / "solutions" / "editorial"
                safe_copy(item, editorial_dest_dir / item.name)
            else:
                logging.warning(f"Could not map editorial PDF {item.name} to a known task/day.")
                # Copy to general editorial folder?
                general_editorial_dir = dest_dir / "editorial"
                # safe_copy(item, general_editorial_dir / item.name)
                # Decided against general editorial based on target structure request
else:
    logging.warning(f"Source directory for PDF editorials not found: {editorial_src_dir}")


# 3. Process Code Solutions (from Solutions.zip)
logging.info("--- Processing Code Solutions ---")
solutions_zip_path = src_dir / "other_materials" / "Solutions.zip"
solutions_extract_path = src_dir / "other_materials" / "Solutions_extracted"

if solutions_zip_path.exists():
    if extract_zip(solutions_zip_path, solutions_extract_path):
        # --- !!! IMPORTANT: Inspect the extracted structure !!! ---
        # The structure inside Solutions.zip is CRUCIAL and not defined in the prompt.
        # Common structures:
        #   a) Solutions_extracted/TaskName/solution.cpp
        #   b) Solutions_extracted/day1/TaskName/solution.pas
        #   c) Solutions_extracted/solution-taskname.c
        # Let's ASSUME structure (a) or similar (top-level folders per task)

        extracted_items = list(solutions_extract_path.iterdir())

        # Check if the first level seems to be task names directly
        potential_task_folders = [d for d in extracted_items if d.is_dir()]

        if potential_task_folders:
             logging.info(f"Assuming extracted solutions structure: {solutions_extract_path}/TaskName/")
             for task_folder in potential_task_folders:
                 task_name_lower = task_folder.name.lower()
                 if task_name_lower in task_to_day_map:
                     day = task_to_day_map[task_name_lower]
                     official_task_name = task_names[task_name_lower]
                     solution_dest_dir = dest_dir / day / official_task_name / "solutions" / "Codes"
                     # Copy the entire contents of the task folder
                     safe_copy(task_folder, solution_dest_dir)
                 else:
                     # Check if it might be a Day 0 task
                     logging.warning(f"Found potential solution folder '{task_folder.name}', but it doesn't match known Day 1/2 tasks. Could be Day 0?")
                     # Try to handle as Day 0
                     day = "day0"
                     official_task_name = task_folder.name.title().replace('_', ' ').replace(' ', '') # Best guess for name
                     task_names[official_task_name.lower()] = official_task_name
                     task_to_day_map[official_task_name.lower()] = day
                     logging.info(f"Treating '{official_task_name}' as a Day 0 task based on solution folder.")
                     solution_dest_dir = dest_dir / day / official_task_name / "solutions" / "Codes"
                     safe_copy(task_folder, solution_dest_dir)
        else:
            # If no directories, maybe flat structure? Needs more complex logic
            logging.warning(f"Extracted solutions structure in {solutions_extract_path} is not '/TaskName/'. Manual inspection needed.")
            # Basic attempt: copy all files? Not ideal.
            # for file_item in extracted_items:
            #     if file_item.is_file():
            #         # Try to guess task from filename? Very unreliable.
            #         pass


        # Optional: Clean up extracted folder
        # shutil.rmtree(solutions_extract_path)
        # logging.info(f"Removed temporary extraction folder: {solutions_extract_path}")

else:
    logging.warning(f"Solutions zip file not found: {solutions_zip_path}")


# 4. Process Test Cases, Graders, Checkers
logging.info("--- Processing Tests, Graders, Checkers ---")
# Check if TestCases is a directory (already extracted) or needs extraction from TestCases.zip
testcases_base_src = src_dir / "other_materials" / "TestCases"
testcases_zip_path = src_dir / "other_materials" / "TestCases.zip"

if not testcases_base_src.is_dir() and testcases_zip_path.exists():
    logging.info(f"TestCases directory not found, attempting extraction from {testcases_zip_path}")
    testcases_extract_path = src_dir / "other_materials" # Extract into other_materials
    extract_zip(testcases_zip_path, testcases_extract_path)
    # Now testcases_base_src should exist if extraction worked

if not testcases_base_src.is_dir():
     logging.error(f"Test cases source directory not found or could not be extracted: {testcases_base_src}")
else:
    # Treat practice as day0
    for day_folder in ["day0", "day1", "day2"]:
        day_grading_path = testcases_base_src / day_folder / "grading"
        if day_grading_path.is_dir():
            logging.info(f"Processing test data for {day_folder} from {day_grading_path}")

            # Get task names relevant for this day (might include newly discovered day0 tasks)
            current_day_tasks_lower = [tn_lower for tn_lower, d in task_to_day_map.items() if d == day_folder]

            if not current_day_tasks_lower:
                logging.warning(f"No tasks identified for {day_folder}. Cannot associate files in {day_grading_path}.")
                # Attempt to infer task names from filenames if day0 is empty?
                # Complex and potentially unreliable. Skip for now.
                continue


            for item in day_grading_path.iterdir():
                if not item.is_file():
                    continue # Skip directories within grading

                filename_lower = item.name.lower()
                matched_task_lower = None

                # --- Try to match file to a task ---
                # Simple approach: check if filename starts with task name (lowercase)
                for tn_lower in current_day_tasks_lower:
                    # Use regex to avoid partial matches (e.g., 'poly' matching 'polygon')
                    # Match taskname followed by non-alphanumeric or end of string
                    if re.match(rf"{re.escape(tn_lower)}([._-].*|$)", filename_lower):
                         matched_task_lower = tn_lower
                         break
                # Fallback: check if task name is *anywhere* in filename (less precise)
                if not matched_task_lower:
                    for tn_lower in current_day_tasks_lower:
                        if tn_lower in filename_lower:
                            matched_task_lower = tn_lower
                            logging.debug(f"Fallback match: '{item.name}' associated with task '{tn_lower}' based on substring presence.")
                            break

                if not matched_task_lower:
                    # Could be a general checker/grader?
                    if "checker" in filename_lower or "chk" in filename_lower or "grader" in filename_lower:
                         # Problem: which task does it belong to if multiple tasks exist?
                         # Cannot reliably determine. Skip for now.
                         logging.warning(f"Could not associate file '{item.name}' in {day_folder} with a specific task. Skipping.")
                    else:
                         logging.warning(f"Could not associate file '{item.name}' in {day_folder} with any task for the day. Skipping.")
                    continue


                official_task_name = task_names[matched_task_lower]
                task_dest_base = dest_dir / day_folder / official_task_name

                # --- Classify and Copy File ---
                if item.suffix in ['.in', '.dat']:
                    dest_subdir = task_dest_base / "tests"
                    safe_copy(item, dest_subdir / item.name)
                elif item.suffix in ['.out', '.sol', '.ans']:
                    # Standardize to .out? Or keep original? Keep original for now.
                    dest_subdir = task_dest_base / "tests"
                    # Maybe rename .sol/.ans to .out? Let's keep original name for traceability.
                    # Example rename: safe_copy(item, dest_subdir / f"{item.stem}.out")
                    safe_copy(item, dest_subdir / item.name)
                elif "grader" in filename_lower: # Check name part, not just suffix
                    dest_subdir = task_dest_base / "graders"
                    safe_copy(item, dest_subdir / item.name)
                elif "checker" in filename_lower or "chk" in filename_lower: # Check name part
                    dest_subdir = task_dest_base / "checkers"
                    safe_copy(item, dest_subdir / item.name)
                else:
                    # Potentially an attachment or other support file?
                    logging.info(f"File '{item.name}' in {day_grading_path} not classified as test/grader/checker. Placing in 'attachments'.")
                    dest_subdir = task_dest_base / "attachments"
                    safe_copy(item, dest_subdir / item.name)

        else:
            logging.warning(f"Grading directory not found for {day_folder}: {day_grading_path}")

# 5. Final Touches (e.g., create empty folders if needed)
logging.info("--- Finalizing Structure ---")
for day, tasks_dict in task_to_day_map.items():
     day_val = task_to_day_map.get(day) # Gets the day string ('day0', 'day1', ...)
     if day_val:
         official_task_name = task_names.get(day)
         if official_task_name:
             task_dir = dest_dir / day_val / official_task_name
             # Ensure standard subdirectories exist even if empty
             for subdir in ["statements", "graders", "checkers", "tests", "attachments", "solutions/Codes", "solutions/editorial", "subtasks"]:
                 (task_dir / subdir).mkdir(parents=True, exist_ok=True)


logging.info("--- IOI 2004 Processing Complete ---")
logging.info(f"Output data is located at: {dest_dir}")
logging.info("Identified Tasks:")
for day in sorted(task_to_day_map.values()):
    tasks_on_day = [tn_lower for tn_lower, d in task_to_day_map.items() if d == day]
    if tasks_on_day:
        official_names = sorted([task_names[tn_lower] for tn_lower in tasks_on_day])
        logging.info(f" {day}: {', '.join(official_names)}")