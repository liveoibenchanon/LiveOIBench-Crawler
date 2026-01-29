import os
import shutil
import re
import logging
from pathlib import Path
import zipfile

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
INPUT_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2013")
OUTPUT_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed")
YEAR = "2013"

# --- Mappings and Constants ---

# Map task names derived from PDF filenames to the names used in folder structures (like TestCases, Practice)
# (Format: normalized_pdf_name: folder_name)
TASK_NAME_MAPPING = {
    "dreaming": "dreaming",
    "art_class": "artclass",
    "wombats": "wombats",
    "cave": "cave",
    "robots": "robots",
    "game": "game",
}

# Files/extensions to identify as solutions
SOLUTION_EXTENSIONS = {".cpp", ".c", ".cc", ".java", ".py", ".pas"}
SOLUTION_KEYWORDS = {"solution", "sol"}

# Files/folders to identify as graders
GRADER_KEYWORDS = {"grader", "stub"}
GRADER_EXTENSIONS = {".h", ".hpp"} # Often included with graders

# Files/folders to identify as checkers
CHECKER_KEYWORDS = {"checker", "chk", "testlib"}

# Files that are likely part of task infrastructure but not easily categorized
# These might be moved to attachments or ignored if clearly build/junk files
INFRASTRUCTURE_KEYWORDS = {"compile", "run", "Makefile", ".sh", ".bat"}
INFRASTRUCTURE_EXTENSIONS = {".so", ".dll", ".o", ".exe"} # Usually ignored


# --- Helper Functions ---

def safe_copy(src: Path, dest: Path, item_type: str = "file"):
    """Safely copies a file or directory, creating parent directories."""
    if not src.exists():
        logging.warning(f"{item_type.capitalize()} not found: {src}")
        return
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file():
            shutil.copy2(src, dest)
            logging.info(f"Copied {item_type}: {src} -> {dest}")
        elif src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
            logging.info(f"Copied {item_type} tree: {src} -> {dest}")
    except Exception as e:
        logging.error(f"Failed to copy {item_type} {src} to {dest}: {e}")

def extract_zip(zip_path: Path, extract_to: Path):
    """Extracts a zip file."""
    if not zip_path.exists():
        logging.warning(f"ZIP file not found: {zip_path}")
        return False
    try:
        extract_to.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logging.info(f"Extracted ZIP: {zip_path} -> {extract_to}")
        return True
    except Exception as e:
        logging.error(f"Failed to extract ZIP {zip_path}: {e}")
        return False

def normalize_task_name(name: str) -> str:
    """Normalizes task name (lowercase, underscores)."""
    name = name.lower()
    name = name.replace(" ", "_").replace("-", "_")
    # Remove leading numbers/underscores if present from PDF names like "01_"
    name = re.sub(r"^\d+_", "", name)
    return name

def identify_file_type(item: Path, task_folder_name: str) -> str:
    """Identifies the type of file/folder based on naming conventions."""
    name_lower = item.name.lower()
    ext_lower = item.suffix.lower()

    # Specific task libraries often named like taskname.h
    if name_lower == f"{task_folder_name}.h" or name_lower == f"{task_folder_name}.hpp":
         return "grader" # Often provided as part of grader package

    if item.is_dir():
        if any(keyword in name_lower for keyword in GRADER_KEYWORDS):
            return "grader"
        if any(keyword in name_lower for keyword in CHECKER_KEYWORDS):
            return "checker"
        if any(keyword in name_lower for keyword in SOLUTION_KEYWORDS) or name_lower == "codes":
             return "solution_codes" # Treat as a directory of solutions
        # Consider common code folders directly under task name
        if name_lower in ["correct", "model", "solutions"]:
             return "solution_codes"

    if item.is_file():
        if ext_lower in SOLUTION_EXTENSIONS:
            # Check if it contains keywords suggesting it's *not* a solution (like grader)
             if not any(keyword in name_lower for keyword in GRADER_KEYWORDS + CHECKER_KEYWORDS):
                 return "solution"
        if any(keyword in name_lower for keyword in GRADER_KEYWORDS):
            return "grader"
        if ext_lower in GRADER_EXTENSIONS and not any(keyword in name_lower for keyword in CHECKER_KEYWORDS):
             # Headers are often part of the grader package unless they are clearly checkers
            return "grader"
        if any(keyword in name_lower for keyword in CHECKER_KEYWORDS) or name_lower == "testlib.h":
            return "checker"
        if ext_lower == ".pdf":
            if any(keyword in name_lower for keyword in ["editorial", "solution", "analysis"]):
                return "editorial"
        if any(keyword in name_lower for keyword in INFRASTRUCTURE_KEYWORDS) or ext_lower in INFRASTRUCTURE_EXTENSIONS:
            return "ignore" # Skip build/run scripts etc.

    # Default: if not identified and not clearly ignorable, treat as attachment
    if name_lower not in [".ds_store"] and ext_lower not in [".zip", ".gz", ".tar"]: # Avoid copying archives found within
        return "attachment"
    else:
        return "ignore"


# --- Main Processing Logic ---

def process_year(year: str, input_dir: Path, output_dir: Path):
    """Processes the data for a given year."""
    logging.info(f"--- Processing IOI {year} ---")
    year_output_dir = output_dir / year
    year_output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create general editorial folder
    general_editorial_dir = year_output_dir / "editorial"
    general_editorial_dir.mkdir(parents=True, exist_ok=True)

    # 2. Extract Zipped Materials if folders don't exist or seem incomplete
    # Note: The prompt shows TestCases and Practice folders unzipped. We prioritize these.
    # If needed, add logic here to check `TestCases/` and `Practice/` and unzip if empty/missing.
    # For this specific structure, we assume the folders are the primary source.
    other_materials_dir = input_dir / "other_materials"
    test_cases_src_dir = other_materials_dir / "TestCases"
    practice_src_dir = other_materials_dir / "Practice"

    # Check if source directories exist
    if not input_dir.exists():
        logging.error(f"Input directory not found: {input_dir}")
        return
    if not other_materials_dir.exists():
         logging.warning(f"Other materials directory not found: {other_materials_dir}")
    if not test_cases_src_dir.exists():
         logging.warning(f"TestCases source directory not found: {test_cases_src_dir}")
    if not practice_src_dir.exists():
         logging.warning(f"Practice source directory not found: {practice_src_dir}")


    # 3. Identify tasks from day folders
    tasks = {} # { 'normalized_task_name': {'day': 'dayX', 'pdf_name': '...', 'folder_name': '...'} }
    for day_folder in ["day1", "day2"]:
        day_path = input_dir / day_folder
        if not day_path.exists():
            logging.warning(f"Directory not found: {day_path}")
            continue
        for pdf_file in day_path.glob("*.pdf"):
            match = re.match(r"(\d+)_([ A-Za-z_]+)\.pdf", pdf_file.name, re.IGNORECASE)
            if match:
                pdf_task_name = match.group(2)
                normalized_name = normalize_task_name(pdf_task_name)
                if normalized_name in TASK_NAME_MAPPING:
                    folder_name = TASK_NAME_MAPPING[normalized_name]
                    tasks[normalized_name] = {
                        "day": day_folder,
                        "pdf_name": pdf_file.name,
                        "folder_name": folder_name # Name used in TestCases/Practice
                    }
                    logging.info(f"Identified task: {normalized_name} ({day_folder}) -> {folder_name}")
                else:
                    logging.warning(f"No folder mapping found for task '{normalized_name}' from PDF '{pdf_file.name}'. Skipping.")
            else:
                 logging.warning(f"Could not parse task name from PDF: {pdf_file.name}")

    # 4. Process each identified task
    for norm_name, task_info in tasks.items():
        day = task_info["day"]
        pdf_name = task_info["pdf_name"]
        folder_name = task_info["folder_name"] # The name used in TestCases, Practice folders
        task_output_dir = year_output_dir / day / norm_name

        logging.info(f"Processing task: {norm_name} ({day})")

        # Create standard subdirectories
        statements_dir = task_output_dir / "statements"
        graders_dir = task_output_dir / "graders"
        checkers_dir = task_output_dir / "checkers"
        tests_dir = task_output_dir / "tests"
        attachments_dir = task_output_dir / "attachments"
        solutions_dir = task_output_dir / "solutions"
        solutions_codes_dir = solutions_dir / "Codes"
        solutions_editorial_dir = solutions_dir / "editorial"

        for d in [statements_dir, graders_dir, checkers_dir, tests_dir,
                  attachments_dir, solutions_dir, solutions_codes_dir, solutions_editorial_dir]:
            d.mkdir(parents=True, exist_ok=True)

        # a. Copy Statement
        statement_src = input_dir / day / pdf_name
        statement_dest = statements_dir / pdf_name
        safe_copy(statement_src, statement_dest, "statement")

        # b. Copy Tests
        task_test_src_dir = test_cases_src_dir / folder_name
        if task_test_src_dir.exists() and task_test_src_dir.is_dir():
             # Copy contents of the source test folder directly into 'tests'
            safe_copy(task_test_src_dir, tests_dir, "tests")
        else:
            logging.warning(f"Test directory not found for task {norm_name}: {task_test_src_dir}")

        # c. Process Practice folder contents for this task
        task_practice_src_dir = practice_src_dir / folder_name
        if task_practice_src_dir.exists() and task_practice_src_dir.is_dir():
            logging.info(f"Processing practice materials for {norm_name} from {task_practice_src_dir}")
            for item in task_practice_src_dir.iterdir():
                file_type = identify_file_type(item, folder_name) # Pass folder_name for context

                if file_type == "solution":
                    safe_copy(item, solutions_codes_dir / item.name, "solution code")
                elif file_type == "solution_codes": # A directory identified as solutions
                    safe_copy(item, solutions_codes_dir / item.name, "solution codes dir")
                elif file_type == "grader":
                    safe_copy(item, graders_dir / item.name, "grader")
                elif file_type == "checker":
                    safe_copy(item, checkers_dir / item.name, "checker")
                elif file_type == "editorial":
                     safe_copy(item, solutions_editorial_dir / item.name, "task editorial")
                elif file_type == "attachment":
                    safe_copy(item, attachments_dir / item.name, "attachment")
                elif file_type == "ignore":
                    logging.debug(f"Ignoring item: {item}")
                else:
                    logging.warning(f"Unknown file type or unhandled item in practice folder {task_practice_src_dir}: {item.name} (Type: {file_type}). Copying to attachments.")
                    safe_copy(item, attachments_dir / item.name, "attachment (unknown)")
        else:
             logging.info(f"No specific practice materials folder found for task {norm_name} at {task_practice_src_dir}")


    # 5. Copy general materials (like Practice_problems.pdf)
    practice_pdf_src = other_materials_dir / "Practice_problems.pdf"
    if practice_pdf_src.exists():
        safe_copy(practice_pdf_src, general_editorial_dir / practice_pdf_src.name, "general document")
    else:
        logging.warning(f"General practice PDF not found: {practice_pdf_src}")


    logging.info(f"--- Finished processing IOI {year} ---")


# --- Execution ---
if __name__ == "__main__":
    if not INPUT_BASE_DIR.exists():
        logging.error(f"FATAL: Base input directory does not exist: {INPUT_BASE_DIR}")
    else:
        process_year(YEAR, INPUT_BASE_DIR, OUTPUT_BASE_DIR)
        logging.info(f"Script finished. Output generated at: {OUTPUT_BASE_DIR}")