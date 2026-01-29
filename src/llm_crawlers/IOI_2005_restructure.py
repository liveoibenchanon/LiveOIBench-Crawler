import os
import shutil
import zipfile
import re
from pathlib import Path

# --- Configuration ---
SRC_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2005")
DEST_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed")
YEAR = "2005"

# --- Mappings ---
# Map the short codes used in test/solution folders to standardized task names
# Determined by looking at test folder names and problem statement filenames
TASK_CODE_MAP = {
    "gar": "garden",
    "mea": "mean_sequence",
    "mou": "mountain",
    "bir": "birthday",
    "rec": "rectangle_game",
    "riv": "rivers",
}

# Map standardized task names to their respective days
# Determined by looking at the day folders containing the problem statements
TASK_DAY_MAP = {
    "garden": "day1",
    "mean_sequence": "day1",
    "mountain": "day1",
    "birthday": "day2",
    "rectangle_game": "day2",
    "rivers": "day2",
}

# Map short codes directly to days (derived from above)
CODE_DAY_MAP = {code: TASK_DAY_MAP[name] for code, name in TASK_CODE_MAP.items()}

# --- Helper Functions ---

def extract_zip(zip_path, extract_to_dir):
    """Extracts a zip file."""
    print(f"Extracting {zip_path} to {extract_to_dir}...")
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to_dir)
        print(f"Successfully extracted {zip_path}")
        return True
    except zipfile.BadZipFile:
        print(f"Error: Failed to extract {zip_path}. File might be corrupted.")
        return False
    except FileNotFoundError:
        print(f"Error: Zip file not found at {zip_path}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred during extraction of {zip_path}: {e}")
        return False

def safe_copy(src, dest):
    """Safely copies a file or directory, creating destination dirs."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True) # Use dirs_exist_ok=True for robustness
            print(f"Copied directory {src} to {dest}")
        elif src.is_file():
            shutil.copy2(src, dest) # copy2 preserves metadata
            print(f"Copied file {src} to {dest}")
        else:
            print(f"Warning: Source {src} is neither a file nor a directory. Skipping.")
    except FileNotFoundError:
        print(f"Error: Source not found {src}. Skipping copy.")
    except Exception as e:
        print(f"Error copying {src} to {dest}: {e}")

def create_task_structure(dest_task_dir):
    """Creates the standard subdirectories for a task."""
    subdirs = [
        "statements",
        "graders",
        "checkers",
        "tests",
        "attachments",
        "solutions/Codes",
        "solutions/editorial",
        "subtasks" # Even if empty, maintain structure
    ]
    for subdir in subdirs:
        (dest_task_dir / subdir).mkdir(parents=True, exist_ok=True)
    print(f"Created standard directory structure under {dest_task_dir}")


def clean_task_name(name):
    """Cleans the task name extracted from PDF filenames."""
    # Remove leading numbers and underscore (e.g., "01_Garden")
    name = re.sub(r"^\d{2}_", "", name)
    # Convert to lowercase and replace spaces/hyphens with underscores
    name = name.lower().replace(" ", "_").replace("-", "_")
    return name

# --- Main Processing Logic ---

def main():
    src_dir = SRC_BASE_DIR
    dest_year_dir = DEST_BASE_DIR / YEAR

    print(f"Starting processing for IOI {YEAR}")
    print(f"Source directory: {src_dir}")
    print(f"Destination directory: {dest_year_dir}")

    if not src_dir.is_dir():
        print(f"Error: Source directory {src_dir} does not exist.")
        return

    # Create the base destination directory for the year
    dest_year_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Handle General Editorial ---
    print("\n--- Processing General Editorial ---")
    editorial_dest = dest_year_dir / "editorial"
    editorial_dest.mkdir(parents=True, exist_ok=True)
    editorial_pdf = src_dir / "other_materials" / "Solutions_and_booklet.pdf"
    if editorial_pdf.is_file():
        safe_copy(editorial_pdf, editorial_dest / editorial_pdf.name)
    else:
        print(f"Warning: General editorial file {editorial_pdf} not found.")

    # --- 2. Extract Archives ---
    print("\n--- Extracting Archives ---")
    other_materials_dir = src_dir / "other_materials"
    solutions_zip = other_materials_dir / "Solutions.zip"
    testcases_zip = other_materials_dir / "TestCases.zip"

    # Paths where archives *might* already be extracted or where we extract them
    solutions_extracted_path = other_materials_dir / "Solutions"
    testcases_extracted_path = other_materials_dir / "TestCases"

    # Check if extraction is needed (if directory doesn't exist or zip is newer)
    # For simplicity, we'll extract if the zip exists, assuming it's the primary source.
    # A more robust check might involve timestamps or checking if the directories are empty.
    if solutions_zip.exists():
         if not extract_zip(solutions_zip, other_materials_dir):
             print("Halting solution processing due to extraction error.")
             # Decide if you want to continue with other parts or stop completely
    elif not solutions_extracted_path.is_dir():
         print(f"Warning: Solutions zip {solutions_zip} not found and extracted folder {solutions_extracted_path} not found.")


    if testcases_zip.exists():
        if not extract_zip(testcases_zip, other_materials_dir):
            print("Halting test case processing due to extraction error.")
            # Decide if you want to continue or stop
    elif not testcases_extracted_path.is_dir():
         print(f"Warning: TestCases zip {testcases_zip} not found and extracted folder {testcases_extracted_path} not found.")


    # --- 3. Process Problem Statements and Create Task Structures ---
    print("\n--- Processing Problem Statements ---")
    processed_tasks = set() # Keep track of tasks for which structure is created

    for day_folder in ["day1", "day2"]:
        day_src_dir = src_dir / day_folder
        if not day_src_dir.is_dir():
            print(f"Warning: Day directory {day_src_dir} not found. Skipping.")
            continue

        print(f"Processing {day_folder}...")
        for item in day_src_dir.iterdir():
            if item.is_file() and item.suffix.lower() == '.pdf':
                # Extract task name from PDF filename (e.g., "01_Garden.pdf" -> "garden")
                raw_name = item.stem # e.g., "01_Garden"
                task_name = clean_task_name(raw_name)

                if not task_name:
                    print(f"Warning: Could not derive task name from {item.name}. Skipping.")
                    continue

                day = day_folder # Assign day based on folder

                # Check if this task name is expected
                if task_name not in TASK_DAY_MAP or TASK_DAY_MAP[task_name] != day:
                     print(f"Warning: Task '{task_name}' found in {day} but mapping suggests otherwise or is missing. Using folder day: {day}.")
                     # Update map if necessary, or just proceed cautiously
                     if task_name not in TASK_DAY_MAP:
                         TASK_DAY_MAP[task_name] = day
                         # Try to find a matching code if possible (less reliable)
                         found_code = None
                         for code, name in TASK_CODE_MAP.items():
                             if name == task_name:
                                 found_code = code
                                 break
                         if found_code:
                             CODE_DAY_MAP[found_code] = day
                         else:
                            print(f"Could not find a matching short code for unexpected task '{task_name}'")


                dest_task_dir = dest_year_dir / day / task_name
                create_task_structure(dest_task_dir)
                processed_tasks.add(task_name)

                # Copy statement PDF
                statement_dest_dir = dest_task_dir / "statements"
                safe_copy(item, statement_dest_dir / item.name)

    # --- 4. Process Test Cases ---
    print("\n--- Processing Test Cases ---")
    if testcases_extracted_path.is_dir():
        for code_folder in testcases_extracted_path.iterdir():
            # Expecting folders like 'rec_tests', 'mea_tests', etc.
            if code_folder.is_dir() and code_folder.name.endswith("_tests"):
                code_match = re.match(r"([a-z]{3})_tests", code_folder.name)
                if code_match:
                    short_code = code_match.group(1)
                    if short_code in TASK_CODE_MAP:
                        task_name = TASK_CODE_MAP[short_code]
                        day = CODE_DAY_MAP.get(short_code)

                        if not day:
                             print(f"Warning: Day not found for code '{short_code}' (task: {task_name}). Skipping tests.")
                             continue
                        if task_name not in processed_tasks:
                             print(f"Warning: Test folder found for task '{task_name}' but no statement was processed. Creating structure.")
                             dest_task_dir = dest_year_dir / day / task_name
                             create_task_structure(dest_task_dir)
                             processed_tasks.add(task_name)
                        else:
                             dest_task_dir = dest_year_dir / day / task_name


                        # Source test files are inside an inner folder named with the short code
                        src_tests_inner_dir = code_folder / short_code
                        dest_tests_dir = dest_task_dir / "tests"

                        if src_tests_inner_dir.is_dir():
                            print(f"Copying tests for {task_name} ({short_code})...")
                            # Copy all contents of the inner folder
                            for item in src_tests_inner_dir.iterdir():
                                safe_copy(item, dest_tests_dir / item.name)
                        else:
                            print(f"Warning: Inner test directory {src_tests_inner_dir} not found for code {short_code}. Skipping tests.")
                    else:
                        print(f"Warning: Unrecognized test code folder pattern: {code_folder.name}")
                else:
                    print(f"Warning: Folder name {code_folder.name} doesn't match expected test pattern '*_tests'.")
        if not any(testcases_extracted_path.iterdir()):
             print(f"Warning: Extracted TestCases directory {testcases_extracted_path} is empty.")

    else:
        print(f"Warning: Extracted TestCases directory {testcases_extracted_path} not found. Skipping test processing.")


    # --- 5. Process Code Solutions ---
    print("\n--- Processing Code Solutions ---")
    if solutions_extracted_path.is_dir():
        # Assuming solutions are in subdirectories named by short code (gar, mea, etc.)
        for item in solutions_extracted_path.iterdir():
            if item.is_dir():
                short_code = item.name
                if short_code in TASK_CODE_MAP:
                    task_name = TASK_CODE_MAP[short_code]
                    day = CODE_DAY_MAP.get(short_code)

                    if not day:
                        print(f"Warning: Day not found for code '{short_code}' (task: {task_name}). Skipping solutions.")
                        continue

                    if task_name not in processed_tasks:
                        print(f"Warning: Solution folder found for task '{task_name}' but no statement was processed. Creating structure.")
                        dest_task_dir = dest_year_dir / day / task_name
                        create_task_structure(dest_task_dir)
                        processed_tasks.add(task_name)
                    else:
                        dest_task_dir = dest_year_dir / day / task_name

                    dest_solutions_code_dir = dest_task_dir / "solutions" / "Codes"
                    print(f"Copying solution codes for {task_name} ({short_code})...")
                    # Copy the entire folder content
                    safe_copy(item, dest_solutions_code_dir) # Copies 'gar' into 'Codes/gar' effectively if we want the original folder name preserved inside 'Codes'
                    # If you want the *content* of 'gar' directly inside 'Codes', use:
                    # for sub_item in item.iterdir():
                    #    safe_copy(sub_item, dest_solutions_code_dir / sub_item.name)
                    # Let's stick with copying the folder itself for now as it preserves original structure.

                else:
                    print(f"Warning: Unrecognized item in Solutions folder: {item.name}. Assuming it's not a task solution folder.")
            else:
                 print(f"Warning: Non-directory item found in Solutions folder: {item.name}. Skipping.")
        if not any(solutions_extracted_path.iterdir()):
             print(f"Warning: Extracted Solutions directory {solutions_extracted_path} is empty.")

    else:
        print(f"Warning: Extracted Solutions directory {solutions_extracted_path} not found. Skipping solution processing.")

    # --- 6. Final Checks (Optional) ---
    # Add checks for missing essential components if needed

    print(f"\nFinished processing for IOI {YEAR}.")
    print(f"Output structure generated at: {dest_year_dir}")

if __name__ == "__main__":
    main()