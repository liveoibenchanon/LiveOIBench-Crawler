import os
import shutil
import zipfile
import pathlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base paths
INPUT_BASE_DIR = pathlib.Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2012")
OUTPUT_BASE_DIR = pathlib.Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2")
YEAR = "2012"
OUTPUT_YEAR_DIR = OUTPUT_BASE_DIR / YEAR

# Task information: (task_name, day)
# Based on official IOI 2012 schedule
# Day 0 is for practice
TASKS = {
    "odometer": "day1",
    "scrivener": "day1",
    "city": "day1", # Actual task name: Crayfish, but files use 'city'
    "rings": "day2", # Actual task name: Ideal City, but files use 'rings'
    "supper": "day2", # Actual task name: Parachute Rings, but files use 'supper'
    "tournament": "day2",
}

# --- Helper Functions ---

def ensure_dir(path):
    """Creates a directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)

def copy_file(src, dest_dir, dest_filename=None):
    """Copies a file to a destination directory."""
    if not src.is_file():
        logging.warning(f"Source file not found: {src}")
        return
    ensure_dir(dest_dir)
    dest_path = dest_dir / (dest_filename if dest_filename else src.name)
    try:
        shutil.copy2(src, dest_path)
        logging.info(f"Copied {src} to {dest_path}")
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dest_path}: {e}")

def copy_directory(src, dest_dir):
    """Copies an entire directory recursively."""
    if not src.is_dir():
        logging.warning(f"Source directory not found: {src}")
        return
    ensure_dir(dest_dir.parent) # Ensure parent of destination exists
    try:
        # Use shutil.copytree, ensuring the destination itself doesn't exist yet
        # or handle appropriately if it might (e.g., using dirs_exist_ok=True in Python 3.8+)
        # For broader compatibility, remove destination if it exists before copying
        if dest_dir.exists():
             shutil.rmtree(dest_dir) # Or decide to merge if needed
        shutil.copytree(src, dest_dir)
        logging.info(f"Copied directory {src} to {dest_dir}")
    except Exception as e:
        logging.error(f"Failed to copy directory {src} to {dest_dir}: {e}")


def classify_and_copy(file_path, task_output_dir, source_base_path):
    """
    Classifies a file from the unzipped archive and copies it to the appropriate
    location in the output structure.
    """
    relative_path = file_path.relative_to(source_base_path)
    parts = relative_path.parts
    filename = file_path.name
    extension = file_path.suffix.lower()

    # 1. Statements
    if extension == ".pdf" and "statement" in filename.lower() or "problem" in filename.lower():
         copy_file(file_path, task_output_dir / "statements")
         return
    # Also catch editorials often found as PDFs
    if extension == ".pdf" and ("editorial" in filename.lower() or "analysis" in filename.lower() or "solut" in filename.lower()):
        copy_file(file_path, task_output_dir / "solutions" / "editorial")
        return

    # 2. Solutions Code (often in folders like 'solution', 'sol', 'solutions')
    # Check if the file is within a directory indicating solutions
    if any(part in ['solution', 'solutions', 'sol'] for part in parts[:-1]):
         # Try copying the whole directory structure if not already done
         # This heuristic assumes solutions are neatly grouped.
         # A more robust approach might copy file by file.
         # Let's copy file by file for better control.
         dest_sol_code_dir = task_output_dir / "solutions" / "Codes" / pathlib.Path(*parts[:-1])
         copy_file(file_path, dest_sol_code_dir)
         return
    # Catch common solution filenames if not in specific folders
    if extension in ['.cpp', '.c', '.pas', '.java', '.py'] and \
       ('sol' in filename.lower() or 'solution' in filename.lower() or task_output_dir.name in filename.lower()):
           copy_file(file_path, task_output_dir / "solutions" / "Codes")
           return

    # 3. Graders (look for grader., *_grader.*, *.h often belongs here)
    if "grader" in filename.lower() or (extension == ".h" or extension == ".hpp"):
        # Heuristic: .h files are often part of the grader setup or attachments
        # Prioritize 'graders' if 'grader' is in the name, otherwise consider 'attachments' later
        copy_file(file_path, task_output_dir / "graders")
        return
    # Check if it's inside a grader directory
    if any(part in ['grader', 'graders', 'interactive'] for part in parts[:-1]):
         dest_grader_dir = task_output_dir / "graders" / pathlib.Path(*parts[:-1])
         copy_file(file_path, dest_grader_dir)
         return


    # 4. Checkers
    if "checker" in filename.lower() or "check" in filename.lower() or filename.startswith("chk"):
        copy_file(file_path, task_output_dir / "checkers")
        return
    # Check if it's inside a checker directory
    if any(part in ['checker', 'checkers', 'chk'] for part in parts[:-1]):
         dest_checker_dir = task_output_dir / "checkers" / pathlib.Path(*parts[:-1])
         copy_file(file_path, dest_checker_dir)
         return

    # 5. Test Data (look for .in, .out, .ans, often in 'tests', 'testdata', 'data')
    if extension in ['.in', '.out', '.ans', '.txt'] or \
       any(part in ['tests', 'testdata', 'data', 'in', 'out'] for part in parts[:-1]):
        # Crude check for test files based on extension or parent folder
        if extension in ['.in', '.out', '.ans'] or 'sample' in filename.lower() or filename.isdigit() or parts[-2].isdigit(): # catches 01.in, 01.out etc.
             copy_file(file_path, task_output_dir / "tests")
             return

    # 6. Attachments (Public files, skeletons, sometimes .h files)
    # Files in 'public' or 'attachment' directories
    if any(part in ['public', 'attachment', 'attachments'] for part in parts[:-1]):
        dest_attach_dir = task_output_dir / "attachments" / pathlib.Path(*parts[:-1])
        copy_file(file_path, dest_attach_dir)
        return

    # Fallback: Treat remaining common code/header files not classified as solutions/graders/checkers
    # as potential attachments if they are relevant (e.g., task-specific headers)
    # Note: The grader rule for .h files might catch these first.
    # If a .h file wasn't caught by the grader rule:
    if extension in [".h", ".hpp"] and "grader" not in filename.lower():
        copy_file(file_path, task_output_dir / "attachments")
        return

    # If file is in root of zip and seems like code or header -> attachment? or skip?
    # Example: Makefile, compile scripts often in root. Maybe attachments or ignored.
    if len(parts) == 1 and extension not in ['.pdf']: # Avoid recopying statement/editorial pdfs
         logging.info(f"Potentially unclassified file in zip root: {relative_path}. Placing in attachments.")
         copy_file(file_path, task_output_dir / "attachments")
         return

    logging.warning(f"Unclassified file: {relative_path} at {file_path}")


# --- Main Processing Logic ---

def main():
    logging.info(f"Starting IOI {YEAR} file processing.")
    logging.info(f"Input directory: {INPUT_BASE_DIR}")
    logging.info(f"Output directory: {OUTPUT_YEAR_DIR}")

    if not INPUT_BASE_DIR.is_dir():
        logging.error(f"Input directory not found: {INPUT_BASE_DIR}")
        return

    # Create the base output directory for the year
    ensure_dir(OUTPUT_YEAR_DIR)

    # Handle practice materials (Day 0)
    practice_pdf = INPUT_BASE_DIR / "practice.pdf"
    if practice_pdf.is_file():
        logging.info("Processing practice materials (Day 0)...")
        # Create a generic 'practice' task folder under day0
        practice_task_dir = OUTPUT_YEAR_DIR / "day0" / "practice"
        ensure_dir(practice_task_dir)
        # Copy practice statement
        copy_file(practice_pdf, practice_task_dir / "statements")
        # Note: No practice zip mentioned, assuming only PDF available based on input structure.
    else:
        logging.warning("practice.pdf not found, skipping Day 0.")


    # Process each official task
    for task_name, day in TASKS.items():
        logging.info(f"Processing task: {task_name} (Day: {day})")

        task_input_dir = INPUT_BASE_DIR # PDFs and ZIPs are directly in the year folder
        task_output_dir = OUTPUT_YEAR_DIR / day / task_name

        # Create task output directories
        ensure_dir(task_output_dir)
        ensure_dir(task_output_dir / "statements")
        ensure_dir(task_output_dir / "graders")
        ensure_dir(task_output_dir / "checkers")
        ensure_dir(task_output_dir / "tests")
        ensure_dir(task_output_dir / "attachments")
        ensure_dir(task_output_dir / "solutions" / "Codes")
        ensure_dir(task_output_dir / "solutions" / "editorial")
        # ensure_dir(task_output_dir / "subtasks") # Not requested based on input structure

        # 1. Copy Problem Statement PDF
        statement_pdf = task_input_dir / f"{task_name}.pdf"
        copy_file(statement_pdf, task_output_dir / "statements")

        # 2. Extract and classify files from ZIP archive
        task_zip = task_input_dir / f"{task_name}.zip"
        if task_zip.is_file():
            temp_extract_dir = OUTPUT_BASE_DIR / f"{YEAR}_{task_name}_temp_extract"
            ensure_dir(temp_extract_dir)
            logging.info(f"Extracting {task_zip} to {temp_extract_dir}")
            try:
                with zipfile.ZipFile(task_zip, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)

                # Sometimes the zip extracts into a subfolder named after the task
                extracted_content_base = temp_extract_dir
                potential_subfolder = temp_extract_dir / task_name
                # Check if all extracted content is inside a single subfolder named after the task
                extracted_items = list(temp_extract_dir.iterdir())
                if len(extracted_items) == 1 and extracted_items[0].is_dir() and extracted_items[0].name == task_name:
                     extracted_content_base = potential_subfolder
                     logging.info(f"Zip contents found in subfolder: {extracted_content_base}")


                # Walk through extracted files and classify
                logging.info(f"Classifying files from {extracted_content_base}")
                for item in extracted_content_base.rglob('*'): # Recurse through all files/dirs
                    if item.is_file():
                         classify_and_copy(item, task_output_dir, extracted_content_base)
                    elif item.is_dir():
                         # Check if a whole directory needs copying (e.g., solutions/Codes)
                         relative_dir_path = item.relative_to(extracted_content_base)
                         dir_name_lower = item.name.lower()

                         # If a 'solutions' or 'sol' directory exists, copy it entirely to solutions/Codes
                         # This might be redundant if classify_and_copy handles files within it,
                         # but can be useful if the structure should be preserved exactly.
                         # Let's rely on file-by-file copy in classify_and_copy to avoid duplicate copies
                         # and allow finer control.

                         # If a 'tests' or 'testdata' dir exists, ensure files within are copied (handled by rglob)
                         pass # Handled by file iteration


            except zipfile.BadZipFile:
                logging.error(f"Failed to extract {task_zip}: Bad zip file.")
            except Exception as e:
                logging.error(f"An error occurred during extraction or classification for {task_name}: {e}")
            finally:
                # Clean up temporary directory
                try:
                    shutil.rmtree(temp_extract_dir)
                    logging.info(f"Removed temporary directory: {temp_extract_dir}")
                except Exception as e:
                    logging.error(f"Failed to remove temporary directory {temp_extract_dir}: {e}")
        else:
            logging.warning(f"Task zip file not found: {task_zip}. Attempting to use folder if exists.")
            # Optional: Check if a folder with the task name exists as an alternative source
            task_folder_source = INPUT_BASE_DIR / task_name
            if task_folder_source.is_dir():
                logging.info(f"Using existing folder as source: {task_folder_source}")
                # Walk through the existing folder and classify
                for item in task_folder_source.rglob('*'):
                    if item.is_file():
                        classify_and_copy(item, task_output_dir, task_folder_source)
            else:
                 logging.warning(f"No zip or folder found for task {task_name}.")


        logging.info(f"Finished processing task: {task_name}")

    # Optional: Check for general editorial files in the root input folder
    # Example: look for 'editorial.pdf', 'booklet.pdf' etc. in INPUT_BASE_DIR
    # and copy to OUTPUT_YEAR_DIR / "editorial"
    # ensure_dir(OUTPUT_YEAR_DIR / "editorial")
    # for item in INPUT_BASE_DIR.glob('*.pdf'):
    #    if 'editorial' in item.name.lower() or 'booklet' in item.name.lower():
    #         copy_file(item, OUTPUT_YEAR_DIR / "editorial")

    logging.info(f"Finished processing all tasks for IOI {YEAR}.")

if __name__ == "__main__":
    main()