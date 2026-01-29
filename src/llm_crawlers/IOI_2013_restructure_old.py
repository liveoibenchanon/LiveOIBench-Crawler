import os
import shutil
import tarfile
import pathlib
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
SRC_BASE_DIR = pathlib.Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2013")
DEST_BASE_DIR = pathlib.Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2")
YEAR = "2013"
DEST_DIR = DEST_BASE_DIR / YEAR

# Task mapping: day -> list of task names
# Determined by examining the folder structure provided
TASKS = {
    "day0": ["fog", "citizen", "birthday"], # From data/day0/
    "day1": ["artclass", "dreaming", "wombats"], # From translations/day1/ and data/*_template.tgz
    "day2": ["cave", "robots", "game"] # From translations/day2/ and data/*_template.tgz
}

# --- Helper Functions ---

def safe_copy(src, dest_dir):
    """Copies a file or directory src to dest_dir, creating dest_dir if needed."""
    if not src.exists():
        logging.warning(f"Source not found, skipping copy: {src}")
        return
    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            # Copy entire directory tree
            dest_path = dest_dir / src.name
            if dest_path.exists():
                 # Avoid error if dest exists, useful for attachments like 'images'
                 # that might be copied multiple times if found in different places.
                 # A more robust approach might involve checking contents or removing first.
                 logging.debug(f"Destination directory {dest_path} already exists. Overwriting.")
                 # shutil.rmtree(dest_path) # Optionally remove before copying
            shutil.copytree(src, dest_path, dirs_exist_ok=True)
            logging.info(f"Copied directory {src} to {dest_path}")
        else:
            # Copy single file
            shutil.copy2(src, dest_dir) # copy2 preserves metadata
            logging.info(f"Copied file {src} to {dest_dir}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dest_dir}: {e}")

def extract_tgz(tgz_path, extract_to):
    """Extracts a .tgz file."""
    if not tgz_path.exists():
        logging.warning(f"Archive not found, skipping extraction: {tgz_path}")
        return False
    try:
        extract_to.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tgz_path, "r:gz") as tar:
            tar.extractall(path=extract_to)
            logging.info(f"Extracted {tgz_path} to {extract_to}")
            return True
    except Exception as e:
        logging.error(f"Error extracting {tgz_path}: {e}")
        return False

def identify_and_copy(src_path, task_dest_dir):
    """Identifies file types within src_path and copies them to appropriate subdirs."""
    if not src_path.exists() or not src_path.is_dir():
        logging.warning(f"Source directory for identification not found or not a dir: {src_path}")
        return

    # Define target subdirectories
    statements_dir = task_dest_dir / "statements"
    graders_dir = task_dest_dir / "graders"
    checkers_dir = task_dest_dir / "checkers"
    tests_dir = task_dest_dir / "tests"
    attachments_dir = task_dest_dir / "attachments"
    solutions_code_dir = task_dest_dir / "solutions" / "Codes"
    solutions_editorial_dir = task_dest_dir / "solutions" / "editorial"

    # Ensure base solution directories exist
    solutions_code_dir.mkdir(parents=True, exist_ok=True)
    solutions_editorial_dir.mkdir(parents=True, exist_ok=True)

    for item in src_path.rglob('*'): # rglob searches recursively
        if item.is_file():
            # Lowercase extension and name for easier matching
            ext = item.suffix.lower()
            name_lower = item.name.lower()

            # Prioritize specific names first
            if "grader" in name_lower and ext in ['.cpp', '.c', '.pas', '.java', '.py', '.h', '.sh']:
                safe_copy(item, graders_dir)
            elif "checker" in name_lower and ext in ['.cpp', '.c', '.pas', '.java', '.py', '.sh']:
                 safe_copy(item, checkers_dir)
            elif name_lower in ['sol', 'solution', 'model'] or name_lower.startswith(('sol', 'model')) and ext in ['.cpp', '.c', '.pas', '.java', '.py']:
                 safe_copy(item, solutions_code_dir)
            # Heuristics based on extensions
            elif ext in ['.in', '.i', '.inp', '.in1', '.in2']: # Input files
                 safe_copy(item, tests_dir)
            elif ext in ['.out', '.ans', '.sol', '.diff', '.o']: # Output/Answer files (avoid .sol C++ obj files if possible)
                 if ext != '.sol' or 'solution' not in name_lower: # Try not to misclassify solution code as test output
                     safe_copy(item, tests_dir)
                 elif ext == '.sol' and 'solution' in name_lower and item.stat().st_size < 1024*1024: # Heuristic: small .sol file might be text
                      safe_copy(item, tests_dir) # Copy small .sol files to tests, larger ones might be solutions
                      logging.warning(f"Small .sol file {item.name} copied to tests/. Verify if it's an output file.")
                 # If a .sol file wasn't copied to tests, it might be picked up as solution code later
            elif ext in ['.cpp', '.c', '.pas', '.java', '.py', '.h']: # Code files (might be solutions, graders, libs)
                # If not already copied as grader/checker/solution, consider as attachment or part of grader framework
                # Copy task-specific headers to graders (e.g., wombat.h)
                task_name = task_dest_dir.name
                if task_name in name_lower and ext == '.h':
                     safe_copy(item, graders_dir)
                elif 'template' in name_lower:
                     safe_copy(item, attachments_dir)
                elif 'solution' in name_lower or 'model' in name_lower: # Catch solutions missed earlier
                     safe_copy(item, solutions_code_dir)
                elif ext == '.h': # Other headers likely part of grader/framework
                    safe_copy(item, graders_dir)
                else: # Other code files could be less critical attachments or examples
                    # Let's place remaining source code as potential solutions for review
                    # This is a bit ambiguous based solely on file names/extensions
                    safe_copy(item, solutions_code_dir)
                    logging.debug(f"Copied general code file {item.name} to solutions/Codes/. Verify role.")
            elif ext in ['.pdf', '.txt', '.md', '.html']: # Documentation/Statements/Editorials
                 if 'solution' in name_lower or 'editorial' in name_lower or 'analysis' in name_lower:
                     safe_copy(item, solutions_editorial_dir)
                 elif 'statement' in name_lower or 'problem' in name_lower:
                     safe_copy(item, statements_dir)
                 else: # Default to attachments if role unclear
                     safe_copy(item, attachments_dir)
            elif ext in ['.jpg', '.png', '.gif', '.bmp', '.jpeg']: # Images are usually attachments
                # Handle cases like artclass/images directory explicitly below
                safe_copy(item, attachments_dir)
            elif name_lower == 'compile.sh' or name_lower == 'run.sh':
                 safe_copy(item, attachments_dir) # Often provided for contestants
            # Add more rules as needed for specific file types/names
            else:
                logging.debug(f"Skipping file with unhandled type/name in {src_path}: {item.name}")

        elif item.is_dir():
            # Handle specific known directories
            if item.name == 'images': # Special case for artclass attachments
                safe_copy(item, attachments_dir)
            # Recursion is handled by rglob, but we might need specific dir handling

# --- Main Execution ---

def main():
    logging.info(f"Starting IOI {YEAR} data processing.")
    logging.info(f"Source directory: {SRC_BASE_DIR}")
    logging.info(f"Destination directory: {DEST_DIR}")

    if not SRC_BASE_DIR.exists():
        logging.error(f"Source directory {SRC_BASE_DIR} not found!")
        return

    # Create the main destination directory
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"Ensured destination directory exists: {DEST_DIR}")

    # --- Step 1: Extract Archives ---
    data_dir = SRC_BASE_DIR / "data"
    # Extract day0.tgz if present
    day0_tgz = data_dir / "day0.tgz"
    day0_extracted_path = data_dir / "day0" # Standard location after extraction
    if day0_tgz.exists() and not day0_extracted_path.exists(): # Only extract if not already extracted
         extract_tgz(day0_tgz, data_dir) # Extract into data/, creating data/day0/
    elif not day0_extracted_path.exists():
         logging.warning(f"Neither {day0_tgz} nor {day0_extracted_path} found.")


    # Extract task templates for day1 and day2 if present
    for day in ["day1", "day2"]:
        for task_name in TASKS[day]:
            template_tgz = data_dir / f"{task_name}_template.tgz"
            template_extracted_path = data_dir / f"{task_name}_template"
            if template_tgz.exists() and not template_extracted_path.exists(): # Extract if needed
                 extract_tgz(template_tgz, data_dir) # Extract into data/, creating data/<task_name>_template/
            elif not template_extracted_path.exists():
                 logging.warning(f"Neither {template_tgz} nor {template_extracted_path} found for task {task_name}.")


    # --- Step 2: Process each task ---
    for day, task_list in TASKS.items():
        for task_name in task_list:
            logging.info(f"Processing {day} task: {task_name}")
            task_dest_dir = DEST_DIR / day / task_name

            # Create basic task structure
            task_dest_dir.mkdir(parents=True, exist_ok=True)
            (task_dest_dir / "statements").mkdir(exist_ok=True)
            (task_dest_dir / "graders").mkdir(exist_ok=True)
            (task_dest_dir / "checkers").mkdir(exist_ok=True)
            (task_dest_dir / "tests").mkdir(exist_ok=True)
            (task_dest_dir / "attachments").mkdir(exist_ok=True)
            (task_dest_dir / "solutions" / "Codes").mkdir(parents=True, exist_ok=True)
            (task_dest_dir / "solutions" / "editorial").mkdir(parents=True, exist_ok=True)

            # --- Locate and Copy Statements ---
            translations_dir = SRC_BASE_DIR / "translations"
            if day == "day0":
                # Day 0 statements are in a single PDF
                day0_pdf = translations_dir / "day0.pdf"
                if day0_pdf.exists():
                    safe_copy(day0_pdf, task_dest_dir / "statements")
                else:
                    logging.warning(f"Day 0 statement PDF not found: {day0_pdf}")
                # Also check within translations/day0/<task> if it exists (less likely based on structure)
                day0_task_trans_dir = translations_dir / day / task_name
                if day0_task_trans_dir.exists():
                     for item in day0_task_trans_dir.glob('*.pdf'):
                         safe_copy(item, task_dest_dir / "statements")
            else:
                # Day 1/2 statements are likely in translations/dayX/task_name/
                task_trans_dir = translations_dir / day / task_name
                if task_trans_dir.exists():
                    # Copy all PDFs found in the task's translation folder
                    found_pdf = False
                    for item in task_trans_dir.glob('*.pdf'):
                        safe_copy(item, task_dest_dir / "statements")
                        found_pdf = True
                    if not found_pdf:
                         logging.warning(f"No PDF statements found in {task_trans_dir}")
                    # Look for solution/editorial files here too
                    for item in task_trans_dir.glob('*'):
                         name_lower = item.name.lower()
                         if item.is_file() and ('solution' in name_lower or 'editorial' in name_lower or 'analysis' in name_lower):
                              if item.suffix.lower() in ['.pdf', '.txt', '.md']:
                                   safe_copy(item, task_dest_dir / "solutions" / "editorial")
                              elif item.suffix.lower() in ['.cpp', '.c', '.pas', '.java', '.py']:
                                   safe_copy(item, task_dest_dir / "solutions" / "Codes")

                else:
                     logging.warning(f"Translation directory not found: {task_trans_dir}")


            # --- Locate and Copy Data (Tests, Graders, Attachments, Solutions Code) ---
            task_data_src_dir = None
            if day == "day0":
                task_data_src_dir = data_dir / "day0" / task_name # From extracted day0.tgz
            else: # day1, day2
                # Data comes from the extracted template folder
                task_data_src_dir = data_dir / f"{task_name}_template" / task_name # Structure is data/<task>_template/<task>/

            if task_data_src_dir and task_data_src_dir.exists():
                logging.info(f"Identifying and copying files from {task_data_src_dir}")
                identify_and_copy(task_data_src_dir, task_dest_dir)
            elif task_data_src_dir:
                logging.warning(f"Data source directory not found: {task_data_src_dir}")
            else:
                 logging.warning(f"Could not determine data source directory for {day}/{task_name}")

            # --- Specific Attachment Handling (Example: Art Class Images) ---
            # The identify_and_copy function with rglob should handle the 'images' dir,
            # but we can add an explicit check if needed.
            if task_name == "artclass":
                images_src = data_dir / "artclass_template" / "artclass" / "images"
                if images_src.exists():
                    safe_copy(images_src, task_dest_dir / "attachments")
                else:
                    logging.warning(f"Artclass images directory not found at expected location: {images_src}")


    logging.info(f"Finished processing IOI {YEAR}.")

if __name__ == "__main__":
    # Create the destination base directory if it doesn't exist
    DEST_BASE_DIR.mkdir(parents=True, exist_ok=True)
    main()