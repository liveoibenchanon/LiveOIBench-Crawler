import os
import shutil
import re
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SOURCE_ROOT = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2011")
OUTPUT_ROOT = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/")
YEAR = "2011"

# --- Helper Functions ---

def safe_copy(src: Path, dst: Path):
    """Safely copies a file, creating destination directories if needed."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        # logging.info(f"Copied: {src} -> {dst}")
    except FileNotFoundError:
        logging.warning(f"Source file not found: {src}")
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dst}: {e}")

def safe_makedirs(path: Path):
    """Safely creates directories."""
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed to create directory {path}: {e}")

def normalize_task_name(name: str) -> str:
    """Normalizes task names from various formats to a standard lowercase identifier."""
    name = name.lower()
    # Remove prefixes like '01_', '02_' etc.
    name = re.sub(r"^\d{1,2}_", "", name)
    # Remove suffixes like '.pdf', '-test'
    name = name.replace(".pdf", "").replace("-test", "")
    # Replace hyphens and spaces with underscores (optional, choose a standard)
    # name = name.replace("-", "_").replace(" ", "_")
    # Or just remove them if the target structure implies it (like 'ricehub')
    name = name.replace("-", "").replace(" ", "").replace("_", "")

    # Specific known case from structure: garden.pdf maps to garden-test
    # The base name seems sufficient after lowercasing and removing extensions/suffixes.
    return name

# --- Main Script ---

def main():
    logging.info(f"Starting processing for IOI {YEAR}")
    logging.info(f"Source directory: {SOURCE_ROOT}")
    logging.info(f"Output directory: {OUTPUT_ROOT}")

    if not SOURCE_ROOT.is_dir():
        logging.error(f"Source directory {SOURCE_ROOT} does not exist.")
        return

    output_year_dir = OUTPUT_ROOT / YEAR
    safe_makedirs(output_year_dir)

    # Create general editorial folder (even if unused for this year)
    safe_makedirs(output_year_dir / "editorial")

    # --- Discover Tasks and Map to Days ---
    task_to_day = {}
    task_statement_files = {}
    task_original_names = {} # To map normalized name back to original PDF name if needed

    day_folders = [d for d in SOURCE_ROOT.iterdir() if d.is_dir() and d.name.startswith("day")]
    if not day_folders:
        logging.warning(f"No 'day*' folders found in {SOURCE_ROOT}")
        # Add specific day folders if missing detection
        day_folders = [SOURCE_ROOT / "day1", SOURCE_ROOT / "day2"]


    for day_folder in day_folders:
        day_name = day_folder.name
        logging.info(f"Processing {day_name}...")
        for item in day_folder.glob("*.pdf"):
            # Expected format: 01_Tropical_Garden.pdf
            match = re.match(r"(\d{1,2})_([^\.]+)\.pdf", item.name, re.IGNORECASE)
            if match:
                original_name = match.group(2).replace('_', ' ') # Keep original spacing/casing if needed later
                task_name_normalized = normalize_task_name(original_name)
                if task_name_normalized:
                    task_to_day[task_name_normalized] = day_name
                    task_statement_files[task_name_normalized] = item
                    task_original_names[task_name_normalized] = original_name # Store original-like name
                    logging.info(f"  Found task: {task_name_normalized} (Original: {original_name}) -> {day_name}")
                else:
                     logging.warning(f"Could not normalize task name from statement file: {item.name}")
            else:
                logging.warning(f"  Unexpected PDF file name format in {day_folder}: {item.name}")


    if not task_to_day:
        logging.error("No tasks discovered from day folders. Aborting.")
        # Fallback: Manually define if necessary, but detection is preferred.
        # task_to_day = { 'tropicalgarden': 'day1', 'race': 'day1', 'ricehub': 'day1',
        #                 'crocodile': 'day2', 'elephants': 'day2', 'parrots': 'day2'}
        # # Need to manually find statement files if using fallback
        return


    # --- Locate Solution Editorials and Test Case Folders ---
    solutions_dir = SOURCE_ROOT / "other_materials" / "Solutions"
    testcases_root = SOURCE_ROOT / "other_materials" / "TestCases"

    if not solutions_dir.is_dir():
        logging.warning(f"Solutions directory not found: {solutions_dir}")
    if not testcases_root.is_dir():
        logging.error(f"TestCases directory not found: {testcases_root}. Aborting.")
        return

    # --- Process Each Discovered Task ---
    for task_name, day in task_to_day.items():
        logging.info(f"Processing task: {task_name} ({day})")

        task_out_dir = output_year_dir / day / task_name

        # Create standard subdirectories
        statements_dir = task_out_dir / "statements"
        graders_dir = task_out_dir / "graders"
        checkers_dir = task_out_dir / "checkers"
        tests_dir = task_out_dir / "tests"
        attachments_dir = task_out_dir / "attachments"
        solutions_dir_task = task_out_dir / "solutions"
        solutions_codes_dir = solutions_dir_task / "Codes"
        solutions_editorial_dir = solutions_dir_task / "editorial"
        subtasks_dir = task_out_dir / "subtasks" # Create even if empty

        for d in [statements_dir, graders_dir, checkers_dir, tests_dir, attachments_dir,
                  solutions_codes_dir, solutions_editorial_dir, subtasks_dir]:
            safe_makedirs(d)

        # 1. Copy Statement
        statement_src = task_statement_files.get(task_name)
        if statement_src and statement_src.exists():
            # Use original PDF name or a standard name like 'problem.pdf'
            statement_dst = statements_dir / statement_src.name
            # statement_dst = statements_dir / "problem.pdf" # Alternative: standard name
            safe_copy(statement_src, statement_dst)
        else:
            logging.warning(f"Statement PDF not found for task: {task_name}")

        # 2. Copy Solution Editorial (PDF)
        # Try finding solution PDF using variations of the task name
        editorial_found = False
        possible_editorial_names = [f"{task_name}.pdf", f"{task_original_names.get(task_name, task_name)}.pdf"]
        for possible_name in possible_editorial_names:
            editorial_src = solutions_dir / possible_name
            if editorial_src.exists():
                editorial_dst = solutions_editorial_dir / editorial_src.name
                safe_copy(editorial_src, editorial_dst)
                editorial_found = True
                break # Found one, stop looking
        if not editorial_found:
             # Try lowercase version as last resort
             editorial_src_lower = solutions_dir / f"{task_name}.pdf"
             if editorial_src_lower.exists():
                 editorial_dst = solutions_editorial_dir / editorial_src_lower.name
                 safe_copy(editorial_src_lower, editorial_dst)
                 editorial_found = True
             else:
                logging.warning(f"Solution editorial PDF not found for task: {task_name} in {solutions_dir}")


        # 3. Find and Copy Test Cases, Graders, Attachments
        test_task_dir_name = f"{task_name}-test" # Standard convention seems to be task_name-test
        task_test_dir = testcases_root / test_task_dir_name

        # Handle inconsistency like ricehub-test/ricehub
        potential_nested_dir = task_test_dir / task_name
        if potential_nested_dir.is_dir() and task_name == "ricehub":
             logging.warning(f"Found nested test structure for {task_name}, prioritizing outer dir: {task_test_dir}")
             # Decide whether to use outer, inner, or merge. Prioritizing outer for now.

        if not task_test_dir.is_dir():
            logging.warning(f"Test directory not found for task {task_name} at {task_test_dir}")
            # Maybe try without '-test' suffix if primary lookup fails?
            task_test_dir_alt = testcases_root / task_name
            if task_test_dir_alt.is_dir():
                 logging.warning(f"Found alternative test directory: {task_test_dir_alt}")
                 task_test_dir = task_test_dir_alt
            else:
                 logging.warning(f"Still couldn't find test directory for {task_name}")
                 continue # Skip tests/graders/attachments if test dir missing


        # 3a. Copy Tests (input/output files)
        tests_found_count = 0
        for item in task_test_dir.rglob("*"): # Recurse through subtask folders etc.
             # Match typical test file patterns
            if item.is_file():
                if item.name.startswith("grader.in.") or item.name.startswith("grader.expect."):
                     safe_copy(item, tests_dir / item.name)
                     tests_found_count += 1
                # Add other potential test file patterns if needed e.g. *.in, *.out, *.ans

        logging.info(f"  Found and copied {tests_found_count} test files for {task_name}")
        if tests_found_count == 0:
             logging.warning(f"  No test files (grader.in.*, grader.expect.*) found for {task_name} in {task_test_dir}")


        # 3b. Copy Graders and Attachments (look primarily in api/)
        api_dir = task_test_dir / "api"
        graders_found = False
        attachments_found = False

        if api_dir.is_dir():
            for item in api_dir.iterdir():
                if not item.is_file():
                    continue

                # Grader Files
                if item.name.startswith("grader.") and item.suffix in ['.cpp', '.c', '.pas']:
                    safe_copy(item, graders_dir / item.name)
                    graders_found = True
                # Task-specific Headers/Libraries (often needed for grader AND contestant)
                elif item.suffix == '.h':
                    safe_copy(item, graders_dir / item.name) # Needed for compiling grader
                    safe_copy(item, attachments_dir / item.name) # Also an attachment
                    attachments_found = True
                elif item.name == "crocodilelib.pas": # Specific known library
                    safe_copy(item, graders_dir / item.name) # Needed for compiling grader
                    safe_copy(item, attachments_dir / item.name) # Also an attachment
                    attachments_found = True
                # Other potential attachments? Could copy everything else from api/ to attachments/
                # elif not (item.name.startswith("grader.in.") or item.name.startswith("grader.expect.")):
                #      # Avoid copying sample tests already handled
                #      safe_copy(item, attachments_dir / item.name)
                #      attachments_found = True

            if not graders_found:
                 logging.warning(f"  No grader files (.c, .cpp, .pas) found in {api_dir}")
            if not attachments_found:
                 logging.info(f"  No specific attachments (.h, known libs) found in {api_dir}")
        else:
            logging.warning(f"  'api' directory not found for task {task_name} in {task_test_dir}")

        # 4. Copy Code Solutions (Not available in the provided input structure)
        # Placeholder: If solution codes were in a predictable place, logic would go here.
        # e.g., check SOURCE_ROOT / "other_materials" / "Codes" / task_name / ...
        logging.info(f"  No source code solutions provided in the input structure for {task_name}")


        # 5. Checkers (Not available in the provided input structure)
        # Placeholder: If checkers were present, logic to find and copy them would go here.
        logging.info(f"  No checkers provided in the input structure for {task_name}")

    logging.info(f"Finished processing IOI {YEAR}")

if __name__ == "__main__":
    main()