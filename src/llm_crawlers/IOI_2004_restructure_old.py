import os
import shutil
import zipfile
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Configuration ---
SRC_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2004"
DEST_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
YEAR = "2004"

# --- Helper Functions ---

def ensure_dir(path):
    """Creates a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

def safe_copy(src, dest):
    """Copies a file, ensuring destination directory exists and handling errors."""
    if not os.path.exists(src):
        logging.warning(f"Source file not found: {src}")
        return
    try:
        ensure_dir(os.path.dirname(dest))
        shutil.copy2(src, dest)
        logging.info(f"Copied {src} to {dest}")
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dest}: {e}")

def get_task_name_from_pdf(filename):
    """Extracts task name from PDF filename (e.g., 'artemis.pdf' -> 'artemis', 'artemis-sol.pdf' -> 'artemis')."""
    base = os.path.basename(filename)
    if base.lower().endswith('-sol.pdf'):
        return base[:-len('-sol.pdf')]
    elif base.lower().endswith('.pdf'):
        return base[:-len('.pdf')]
    return None

def classify_test_file(filename, task_map):
    """
    Classifies a file from the grading folder and determines its task and type.

    Args:
        filename (str): The full path or relative path within the zip/extracted folder.
        task_map (dict): A mapping from potential filename prefixes to canonical task names.

    Returns:
        tuple: (task_name, file_type, destination_subfolder) or (None, None, None) if unclassified.
               file_type can be 'test_in', 'test_out', 'grader', 'checker', 'other'.
               destination_subfolder is the target subfolder name (e.g., 'tests', 'graders').
    """
    base_filename = os.path.basename(filename)
    
    # Try to match known task prefixes
    task_name = None
    # Use a regex to find a potential prefix and separator (., _, digit)
    # Example: artemis.1.in, farm_01.out, phidias1.in, poly.in, hermes.out
    match = re.match(r'^([a-zA-Z]+)[._]?(\d+)?\.?([a-zA-Z0-9_]+)?\.(in|out|ans|sol|zip|dat|c|cpp|pas|java|sh|py|exe|txt)$', base_filename, re.IGNORECASE)
    
    potential_prefix = None
    if match:
        potential_prefix = match.group(1).lower()
    else:
        # Handle cases like polygon.pdf inside grading (unlikely but possible)
         match_simple = re.match(r'^([a-zA-Z]+)\.(in|out|ans|sol|zip|dat|c|cpp|pas|java|sh|py|exe|txt)$', base_filename, re.IGNORECASE)
         if match_simple:
             potential_prefix = match_simple.group(1).lower()

    if potential_prefix and potential_prefix in task_map:
            task_name = task_map[potential_prefix]
    # Fallback: if no prefix match, maybe the file IS the taskname? (less common)
    elif '.' in base_filename:
         potential_prefix_base = base_filename.split('.')[0].lower()
         if potential_prefix_base in task_map:
             task_name = task_map[potential_prefix_base]


    # Classify file type
    if base_filename.lower().endswith('.in'):
        return task_name, 'test_in', 'tests'
    elif base_filename.lower().endswith(('.out', '.ans', '.sol')): # .sol might be solution output
        return task_name, 'test_out', 'tests'
    elif 'grader' in base_filename.lower() or base_filename.lower().startswith('gr'):
        return task_name, 'grader', 'graders'
    elif 'checker' in base_filename.lower() or base_filename.lower().startswith(('chk', 'check')):
        return task_name, 'checker', 'checkers'
    elif base_filename.lower().endswith(('.c', '.cpp', '.pas', '.java', '.py')):
         # Could be solution, grader, checker, or library
         # If task_name is known, maybe put in solutions/Codes? or attachments?
         # Let's classify as 'other' for now, might need manual sorting later
         # Or assume it's a utility/attachment if not clearly grader/checker
         return task_name, 'other_code', 'attachments'
    else:
        # Other files could be attachments, configuration, docs etc.
        return task_name, 'other', 'attachments'


# --- Main Processing Logic ---

def main():
    logging.info(f"Starting processing for IOI {YEAR}")
    src_dir = os.path.join(SRC_BASE_DIR)
    dest_dir = os.path.join(DEST_BASE_DIR, YEAR)

    if not os.path.isdir(src_dir):
        logging.error(f"Source directory not found: {src_dir}")
        return

    ensure_dir(dest_dir)
    ensure_dir(os.path.join(dest_dir, "editorial")) # Global editorial folder

    # --- 1. Process Day 1 & Day 2 PDFs ---
    logging.info("Processing Day 1 and Day 2 PDF files...")
    tasks_by_day = {'day1': set(), 'day2': set()}
    task_name_map_pdf = {} # Maps PDF filename base to canonical task name

    for day in ["day1", "day2"]:
        day_src_dir = os.path.join(src_dir, day)
        if not os.path.isdir(day_src_dir):
            logging.warning(f"Directory not found: {day_src_dir}")
            continue

        for filename in os.listdir(day_src_dir):
            if filename.lower().endswith('.pdf'):
                src_path = os.path.join(day_src_dir, filename)
                
                if filename.lower().startswith('overview'):
                    dest_path = os.path.join(dest_dir, "editorial", filename)
                    safe_copy(src_path, dest_path)
                    continue # Skip further processing for overview files

                task_name = get_task_name_from_pdf(filename)
                if not task_name:
                    logging.warning(f"Could not determine task name for PDF: {filename}")
                    continue
                
                tasks_by_day[day].add(task_name)
                task_name_map_pdf[task_name] = task_name # Simple 1:1 mapping here

                task_dest_dir = os.path.join(dest_dir, day, task_name)

                if filename.lower().endswith('-sol.pdf'):
                    dest_subfolder = os.path.join(task_dest_dir, "solutions", "editorial")
                else:
                    dest_subfolder = os.path.join(task_dest_dir, "statements")
                
                dest_path = os.path.join(dest_subfolder, filename)
                safe_copy(src_path, dest_path)

    logging.info(f"Identified tasks: {tasks_by_day}")

    # --- 2. Process Scanned Documents ---
    logging.info("Processing scanned documents...")
    scanned_docs_dir = os.path.join(src_dir, "scanned-documents")
    if os.path.isdir(scanned_docs_dir):
        for filename in os.listdir(scanned_docs_dir):
            src_path = os.path.join(scanned_docs_dir, filename)
            # Place general docs in the root editorial folder
            dest_path = os.path.join(dest_dir, "editorial", filename)
            # Special case: IOI-Practice might relate to day0, but let's keep it general for now
            safe_copy(src_path, dest_path)
    else:
        logging.warning(f"Scanned documents folder not found: {scanned_docs_dir}")


    # --- 3. Extract and Process Test Data ---
    logging.info("Processing test data zip file...")
    zip_path = os.path.join(src_dir, "ioi2004-test-data.zip")
    temp_extract_dir = os.path.join(dest_dir, "_temp_extract") # Extract temporarily

    # Define task name mappings (potential prefixes to canonical names)
    # This requires knowing the tasks or guessing from PDF names
    task_name_map_test = {
        # Day 1
        'artemis': 'artemis', 'art': 'artemis',
        'polygon': 'polygon', 'poly': 'polygon',
        'hermes': 'hermes', 'her': 'hermes',
        # Day 2
        'empodia': 'empodia', 'emp': 'empodia',
        'phidias': 'phidias', 'phi': 'phidias',
        'farmer': 'farmer', 'far': 'farmer',
        # Day 0 (Practice) - Assign a generic name if needed
        'practice': 'practice', # Example if files are named practice.*
        # Add any other variations observed in filenames
    }
    
    # Add task names derived from PDFs to the map if not already covered
    for day, tasks in tasks_by_day.items():
        for task in tasks:
            if task not in task_name_map_test:
                 task_name_map_test[task] = task # Add the full name itself as a key

    if os.path.exists(zip_path):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                logging.info(f"Extracting {zip_path}...")
                # Extract files safely, avoid path traversal issues
                for member in zip_ref.infolist():
                    # Skip directories, handle potential malicious paths
                    if member.is_dir() or ".." in member.filename or member.filename.startswith("/"):
                        continue
                    
                    # Determine the target path within the final structure
                    # Expected path format in zip: ioi2004-test-data/dayX/grading/filename
                    path_parts = member.filename.split('/')
                    
                    if len(path_parts) >= 3 and path_parts[0] == 'ioi2004-test-data' and path_parts[2] == 'grading':
                        day_folder_name = path_parts[1] # day0, day1, day2
                        relative_filename = "/".join(path_parts[2:]) # grading/filename or grading/subfolder/filename
                        base_filename = os.path.basename(relative_filename)
                        
                        current_task_map = task_name_map_test
                        day_str = day_folder_name # Keep 'day0', 'day1', 'day2'

                        # Classify the file
                        task_name, file_type, dest_subfolder_name = classify_test_file(base_filename, current_task_map)

                        if not dest_subfolder_name:
                            logging.warning(f"Could not classify file: {member.filename}")
                            continue

                        if not task_name:
                            # Handle day0 files without clear task names
                            if day_str == 'day0':
                                task_name = 'practice' # Assign to a generic 'practice' task
                                logging.info(f"Assigning Day 0 file '{base_filename}' to task '{task_name}'")
                            else:
                                logging.warning(f"Could not determine task for file: {member.filename} in {day_str}. Skipping.")
                                # Optionally, copy to a day-level 'unknown' folder
                                # unknown_dir = os.path.join(dest_dir, day_str, "_unknown_task_files")
                                # ensure_dir(unknown_dir)
                                # target_extract_path = os.path.join(unknown_dir, base_filename)
                                continue # Skip placing if task is unknown for day1/day2


                        # Construct final destination path
                        task_dest_dir = os.path.join(dest_dir, day_str, task_name)
                        final_dest_path = os.path.join(task_dest_dir, dest_subfolder_name, base_filename)

                        # Ensure the target directory exists before extracting
                        ensure_dir(os.path.dirname(final_dest_path))

                        # Extract the file directly to the final destination
                        try:
                           with zip_ref.open(member.filename) as source, open(final_dest_path, "wb") as target:
                                shutil.copyfileobj(source, target)
                           logging.info(f"Extracted {member.filename} to {final_dest_path}")
                        except Exception as e:
                            logging.error(f"Failed to extract {member.filename} to {final_dest_path}: {e}")

                    else:
                        logging.warning(f"Skipping file with unexpected path in zip: {member.filename}")

        except zipfile.BadZipFile:
            logging.error(f"Error: {zip_path} is not a valid zip file.")
        except Exception as e:
            logging.error(f"An error occurred during zip processing: {e}")
    else:
        logging.warning(f"Test data zip file not found: {zip_path}")
        # Attempt to process the directory if it exists (already extracted)
        extracted_data_dir = os.path.join(src_dir, "ioi2004-test-data")
        if os.path.isdir(extracted_data_dir):
            logging.info(f"Processing already extracted test data from: {extracted_data_dir}")
            for day_folder_name in ["day0", "day1", "day2"]:
                 day_grading_dir = os.path.join(extracted_data_dir, day_folder_name, "grading")
                 if os.path.isdir(day_grading_dir):
                     for root, _, files in os.walk(day_grading_dir):
                          for base_filename in files:
                                src_file_path = os.path.join(root, base_filename)
                                
                                current_task_map = task_name_map_test
                                day_str = day_folder_name

                                task_name, file_type, dest_subfolder_name = classify_test_file(base_filename, current_task_map)

                                if not dest_subfolder_name:
                                    logging.warning(f"Could not classify file: {src_file_path}")
                                    continue
                                
                                if not task_name:
                                     if day_str == 'day0':
                                         task_name = 'practice' 
                                         logging.info(f"Assigning Day 0 file '{base_filename}' to task '{task_name}'")
                                     else:
                                         logging.warning(f"Could not determine task for file: {src_file_path} in {day_str}. Skipping.")
                                         continue

                                task_dest_dir = os.path.join(dest_dir, day_str, task_name)
                                final_dest_path = os.path.join(task_dest_dir, dest_subfolder_name, base_filename)
                                safe_copy(src_file_path, final_dest_path)
                 else:
                    logging.warning(f"Grading directory not found: {day_grading_dir}")
        else:
            logging.warning(f"Neither zip file nor extracted directory found for test data.")


    # --- 4. Final Cleanup (Optional) ---
    # Remove temporary extraction folder if it exists
    # if os.path.isdir(temp_extract_dir):
    #     logging.info(f"Removing temporary directory: {temp_extract_dir}")
    #     shutil.rmtree(temp_extract_dir)

    logging.info(f"Processing for IOI {YEAR} completed.")
    logging.info(f"Output structure generated at: {dest_dir}")

if __name__ == "__main__":
    main()