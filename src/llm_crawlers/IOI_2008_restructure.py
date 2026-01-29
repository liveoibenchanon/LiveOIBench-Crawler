import os
import shutil
import re
import zipfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SOURCE_BASE_DIR = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-New/2008'
TARGET_BASE_DIR = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-Processed'
YEAR = '2008'

# --- Mappings ---
# Map abbreviations found in TestCases/Solutions to standardized task names
# Determined by inspecting PDF names and TestCases folder names
TASK_ABBREVIATION_MAP = {
    'lin': 'Linear_Garden',
    'isl': 'Islands',
    'tel': 'Teleporters',
    'fsh': 'Fish',
    'typ': 'Type_Printer',
    'pbs': 'Pyramid_Base',
    # Practice task abbreviations might need inspection of Practice.zip/Solutions.zip
    # For now, we'll derive practice task names directly from PDFs
}

# Map task names derived from PDFs to their day and abbreviation (if known)
# We will populate this by scanning the day folders
TASK_INFO = {}

# --- Helper Functions ---

def safe_create_dir(path):
    """Creates a directory if it doesn't exist."""
    try:
        os.makedirs(path, exist_ok=True)
        logging.debug(f"Ensured directory exists: {path}")
    except OSError as e:
        logging.error(f"Error creating directory {path}: {e}")
        raise

def safe_copy(src, dst):
    """Copies a file or directory, logging errors."""
    try:
        if os.path.isdir(src):
            # Ensure destination parent directory exists
            safe_create_dir(os.path.dirname(dst))
            # Copy entire directory tree
            shutil.copytree(src, dst, dirs_exist_ok=True)
            logging.info(f"Copied directory {src} to {dst}")
        elif os.path.isfile(src):
             # Ensure destination directory exists
            safe_create_dir(os.path.dirname(dst))
            shutil.copy2(src, dst) # copy2 preserves metadata
            logging.info(f"Copied file {src} to {dst}")
        else:
            logging.warning(f"Source not found or not a file/dir: {src}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dst}: {e}")

def extract_task_name_from_pdf(pdf_filename):
    """Extracts a clean task name from PDF filenames like '01_Type_Printer.pdf' or 'game.pdf'."""
    base_name = os.path.splitext(pdf_filename)[0]
    # Remove potential numeric prefixes like "01_", "02_"
    base_name = re.sub(r'^\d{2}_', '', base_name)
    # Replace spaces/hyphens with underscores and ensure consistent casing (e.g., TitleCase or snake_case)
    # Let's use the name as is after removing prefix, assuming it's descriptive enough.
    # Example: 'Type_Printer', 'Islands', 'Linear_Garden', 'buses', 'pyramid', 'game'
    return base_name

def find_abbr_for_task(task_name):
    """Finds the abbreviation for a given full task name."""
    for abbr, name in TASK_ABBREVIATION_MAP.items():
        if name == task_name:
            return abbr
    return None

# --- Main Processing Logic ---

def main():
    logging.info(f"Starting processing for IOI {YEAR}")
    source_year_dir = os.path.join(SOURCE_BASE_DIR)
    target_year_dir = os.path.join(TARGET_BASE_DIR, YEAR)

    if not os.path.isdir(source_year_dir):
        logging.error(f"Source directory not found: {source_year_dir}")
        return

    logging.info(f"Creating target directory: {target_year_dir}")
    safe_create_dir(target_year_dir)

    # --- 1. Process General Editorial ---
    logging.info("Processing general editorial...")
    editorial_target_dir = os.path.join(target_year_dir, 'editorial')
    source_editorial_pdf = os.path.join(source_year_dir, 'other_materials', 'Solutions_and_booklet.pdf')
    if os.path.isfile(source_editorial_pdf):
        safe_create_dir(editorial_target_dir)
        safe_copy(source_editorial_pdf, os.path.join(editorial_target_dir, os.path.basename(source_editorial_pdf)))
    else:
        logging.warning(f"General editorial file not found: {source_editorial_pdf}")

    # --- 2. Pre-scan and build TASK_INFO ---
    logging.info("Scanning day folders to build task map...")
    day_source_map = {
        'day0': os.path.join(source_year_dir, 'other_materials', 'Practice'),
        'day1': os.path.join(source_year_dir, 'day1'),
        'day2': os.path.join(source_year_dir, 'day2'),
    }

    for day, source_day_dir in day_source_map.items():
        if os.path.isdir(source_day_dir):
            for item in os.listdir(source_day_dir):
                if item.lower().endswith('.pdf'):
                    task_name = extract_task_name_from_pdf(item)
                    abbr = find_abbr_for_task(task_name)
                    if task_name not in TASK_INFO:
                        TASK_INFO[task_name] = {'day': day, 'pdf': item, 'abbr': abbr}
                        logging.info(f"Mapped task '{task_name}' (PDF: {item}, Abbr: {abbr}) to {day}")
                    else:
                         logging.warning(f"Duplicate task name '{task_name}' detected while scanning {day}. Check source structure.")
        else:
            logging.warning(f"Source directory for {day} not found: {source_day_dir}")

    logging.info(f"Task map built: {TASK_INFO}")


    # --- 3. Process Each Task ---
    logging.info("Processing individual tasks...")
    source_test_base = os.path.join(source_year_dir, 'other_materials', 'TestCases')
    source_solution_base = os.path.join(source_year_dir, 'other_materials', 'Solutions') # Assuming extracted solutions exist here

    # Check if we should unzip first (optional, use extracted folders if they exist)
    # Example: Unzip TestCases.zip if TestCases folder seems incomplete or missing
    # test_zip_path = os.path.join(source_year_dir, 'other_materials', 'TestCases.zip')
    # if os.path.exists(test_zip_path) and not os.path.exists(source_test_base):
    #     logging.info(f"Extracting {test_zip_path}...")
    #     with zipfile.ZipFile(test_zip_path, 'r') as zip_ref:
    #         zip_ref.extractall(os.path.join(source_year_dir, 'other_materials')) # Extracts into 'other_materials/TestCases'

    # solution_zip_path = os.path.join(source_year_dir, 'other_materials', 'Solutions.zip')
    # if os.path.exists(solution_zip_path) and not os.path.exists(source_solution_base):
    #     logging.info(f"Extracting {solution_zip_path}...")
    #      with zipfile.ZipFile(solution_zip_path, 'r') as zip_ref:
    #         zip_ref.extractall(os.path.join(source_year_dir, 'other_materials')) # Extracts into 'other_materials/Solutions'


    for task_name, info in TASK_INFO.items():
        day = info['day']
        pdf_filename = info['pdf']
        task_abbr = info['abbr']

        logging.info(f"Processing task: {task_name} ({day})")

        target_task_dir = os.path.join(target_year_dir, day, task_name)
        safe_create_dir(target_task_dir)

        # --- a) Statements ---
        target_statements_dir = os.path.join(target_task_dir, 'statements')
        source_pdf_path = os.path.join(day_source_map[day], pdf_filename)
        if os.path.isfile(source_pdf_path):
            safe_copy(source_pdf_path, os.path.join(target_statements_dir, f"{task_name}.pdf")) # Standardize name
        else:
            logging.warning(f"Statement PDF not found for task {task_name}: {source_pdf_path}")

        # --- b) Tests ---
        target_tests_dir = os.path.join(target_task_dir, 'tests')
        if task_abbr and os.path.isdir(source_test_base):
            source_task_test_dir = os.path.join(source_test_base, task_abbr)
            if os.path.isdir(source_task_test_dir):
                 # Copy contents of the source test folder
                for item in os.listdir(source_task_test_dir):
                    s_item = os.path.join(source_task_test_dir, item)
                    d_item = os.path.join(target_tests_dir, item)
                    safe_copy(s_item, d_item)
            else:
                logging.warning(f"Test directory not found for task {task_name} (abbr: {task_abbr}): {source_task_test_dir}")
        elif task_abbr:
             logging.warning(f"Source test base directory not found or task abbreviation missing for task {task_name}. Searched: {source_test_base}")
        else:
             logging.warning(f"No abbreviation found for task {task_name}, cannot locate tests automatically in {source_test_base}.")
             # Could add logic here to check Practice.zip if day == 'day0'

        # --- c) Solutions ---
        target_solutions_dir = os.path.join(target_task_dir, 'solutions')
        target_solutions_code_dir = os.path.join(target_solutions_dir, 'Codes')
        target_solutions_editorial_dir = os.path.join(target_solutions_dir, 'editorial')

        if os.path.isdir(source_solution_base):
            found_solution = False
            # Try finding solutions by abbreviation first
            if task_abbr:
                source_task_solution_dir = os.path.join(source_solution_base, task_abbr)
                if os.path.isdir(source_task_solution_dir):
                    logging.info(f"Found solution folder for {task_name} by abbreviation: {source_task_solution_dir}")
                    # Copy contents to Codes/
                    safe_create_dir(target_solutions_code_dir) # Ensure Codes exists
                    for item in os.listdir(source_task_solution_dir):
                       s_item = os.path.join(source_task_solution_dir, item)
                       d_item = os.path.join(target_solutions_code_dir, item)
                       # Simple check: assume non-code files might be editorials, otherwise code
                       if os.path.isfile(s_item) and item.lower().endswith(('.pdf', '.txt', '.doc', '.docx')):
                           safe_create_dir(target_solutions_editorial_dir)
                           safe_copy(s_item, os.path.join(target_solutions_editorial_dir, item))
                       else: # Assume code file or subfolder
                           safe_copy(s_item, d_item) # Copies files or subdirs into Codes/
                    found_solution = True

            # Add fallback: check for folder by full task name (if different from abbr)
            if not found_solution:
                 source_task_solution_dir_alt = os.path.join(source_solution_base, task_name)
                 if os.path.isdir(source_task_solution_dir_alt):
                    logging.info(f"Found solution folder for {task_name} by full name: {source_task_solution_dir_alt}")
                    # Copy contents to Codes/
                    safe_create_dir(target_solutions_code_dir) # Ensure Codes exists
                    for item in os.listdir(source_task_solution_dir_alt):
                       s_item = os.path.join(source_task_solution_dir_alt, item)
                       d_item = os.path.join(target_solutions_code_dir, item)
                       if os.path.isfile(s_item) and item.lower().endswith(('.pdf', '.txt', '.doc', '.docx')):
                           safe_create_dir(target_solutions_editorial_dir)
                           safe_copy(s_item, os.path.join(target_solutions_editorial_dir, item))
                       else:
                           safe_copy(s_item, d_item)
                    found_solution = True

            if not found_solution:
                logging.warning(f"Solution directory not found for task {task_name} in {source_solution_base} (tried abbr: {task_abbr}, name: {task_name})")
        else:
            logging.warning(f"Source solution base directory not found: {source_solution_base}")
            # Could add logic here to check Solutions.zip or Practice.zip if needed

        # --- d) Graders, Checkers, Attachments ---
        # These are often bundled with solutions or tests.
        # We can try searching common names within the copied solution/test folders later
        # or look for specific files/folders in the original source structure if known.
        # For this structure, they are likely inside the TestCases or Solutions zips/folders.
        # The current copy logic for tests/solutions might already bring them over.
        # Create the empty directories for consistency.
        safe_create_dir(os.path.join(target_task_dir, 'graders'))
        safe_create_dir(os.path.join(target_task_dir, 'checkers'))
        safe_create_dir(os.path.join(target_task_dir, 'attachments'))
        safe_create_dir(os.path.join(target_task_dir, 'subtasks')) # If subtask info is available elsewhere

        # Example: Search for common grader/checker names in the source test/solution folders
        # (Could be added if specific file names are known)
        # potential_sources = []
        # if task_abbr and os.path.isdir(os.path.join(source_test_base, task_abbr)):
        #     potential_sources.append(os.path.join(source_test_base, task_abbr))
        # if os.path.isdir(source_solution_base):
        #      if task_abbr and os.path.isdir(os.path.join(source_solution_base, task_abbr)):
        #           potential_sources.append(os.path.join(source_solution_base, task_abbr))
        #      if os.path.isdir(os.path.join(source_solution_base, task_name)):
        #           potential_sources.append(os.path.join(source_solution_base, task_name))
        #
        # for source_dir in potential_sources:
        #      for item in os.listdir(source_dir):
        #            # Check for graders
        #           if 'grader' in item.lower() and os.path.isfile(os.path.join(source_dir, item)):
        #               safe_copy(os.path.join(source_dir, item), os.path.join(target_task_dir, 'graders', item))
        #           # Check for checkers
        #           if 'checker' in item.lower() and os.path.isfile(os.path.join(source_dir, item)):
        #                safe_copy(os.path.join(source_dir, item), os.path.join(target_task_dir, 'checkers', item))
            # Add similar checks for attachment files if patterns are known

    logging.info(f"Finished processing for IOI {YEAR}")

if __name__ == "__main__":
    main()