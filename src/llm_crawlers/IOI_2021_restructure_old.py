import os
import shutil
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base paths
input_base = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI/2021'
output_base = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-Processed-2'
year = '2021'

# Create the main output directory for the year
os.makedirs(os.path.join(output_base, year), exist_ok=True)

# --- Helper function to copy safely ---
def copy_item(src, dst):
    """Safely copies a file or directory."""
    try:
        if os.path.isdir(src):
            # For Python 3.8+ include dirs_exist_ok=True
            # shutil.copytree(src, dst, dirs_exist_ok=True)
            # For compatibility with older pythons:
            if os.path.exists(dst):
                 logging.warning(f"Destination directory {dst} already exists. Skipping copytree for {src}.")
                 # Or alternatively, remove dst first:
                 # shutil.rmtree(dst)
                 # shutil.copytree(src, dst)
            else:
                 shutil.copytree(src, dst)
            logging.info(f"Copied directory {src} to {dst}")
        elif os.path.isfile(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst) # copy2 preserves metadata
            logging.info(f"Copied file {src} to {dst}")
        else:
            logging.warning(f"Source item {src} not found or is not a file/directory.")
    except FileNotFoundError:
        logging.warning(f"Source item {src} not found.")
    except Exception as e:
        logging.error(f"Failed to copy {src} to {dst}: {e}")

# --- Process each day ---
for day in ["day0", "day1", "day2"]:
    day_path_in = os.path.join(input_base, day)
    day_path_out = os.path.join(output_base, year, day)

    if not os.path.isdir(day_path_in):
        logging.warning(f"Input directory for {day} not found: {day_path_in}")
        continue

    logging.info(f"Processing {day}...")
    os.makedirs(day_path_out, exist_ok=True)

    # --- Iterate through items in the day directory (potential tasks) ---
    for item_name in os.listdir(day_path_in):
        item_path = os.path.join(day_path_in, item_name)

        # Skip files at the day level, except for potential day0 editorial PDFs
        if not os.path.isdir(item_path) and day != "day0":
            continue
        if not os.path.isdir(item_path) and day == "day0" and not item_name.endswith("-ISC.pdf"):
             continue # Skip non-directories and non-ISC PDFs on day0


        # Determine task name and potential inner directory
        task_name_canonical = item_name # Default for day1/day2 tasks like Keys, Parks
        task_name_output = item_name    # Default output name
        inner_task_dir = None
        editorial_pdf_src = None

        if day == "day0":
            if item_name.endswith("-CMS"):
                 task_name_canonical = item_name[:-4] # e.g., "robot" from "robot-CMS"
                 task_name_output = task_name_canonical # Use "robot", "jelly" etc. for output
                 # Try finding the inner dir: robot-CMS/robot/
                 potential_inner = os.path.join(item_path, task_name_canonical.lower())
                 if os.path.isdir(potential_inner):
                     inner_task_dir = potential_inner
                 # Find editorial PDF: day0/robot-ISC.pdf
                 potential_editorial = os.path.join(day_path_in, f"{task_name_canonical}-ISC.pdf")
                 if os.path.isfile(potential_editorial):
                      editorial_pdf_src = potential_editorial

            elif item_name.endswith("-ISC.pdf"):
                 # This is an editorial file, handled when processing the corresponding CMS folder
                 continue # Skip processing the PDF directly
            else:
                logging.warning(f"Skipping unexpected item in day0: {item_path}")
                continue # Skip unexpected items

        else: # day1, day2
             task_name_canonical = item_name # e.g. Keys
             task_name_output = item_name # e.g. Keys
             # Try finding the inner dir: Keys/keys-CMS/keys/
             potential_inner = os.path.join(item_path, f"{task_name_canonical.lower()}-CMS", task_name_canonical.lower())
             if os.path.isdir(potential_inner):
                 inner_task_dir = potential_inner
             # Find editorial PDF: Keys/keys-editorial.pdf
             potential_editorial = os.path.join(item_path, f"{task_name_canonical.lower()}-editorial.pdf")
             if os.path.isfile(potential_editorial):
                 editorial_pdf_src = potential_editorial

        # If we couldn't find the inner directory containing task data, skip
        if not inner_task_dir:
            # Check if it's just the PDF file we already skipped
            if not (day == "day0" and item_name.endswith("-ISC.pdf")):
                 logging.warning(f"Could not find standard inner task data directory for {item_name} in {day}. Skipping.")
            continue

        logging.info(f"  Processing task: {task_name_output}")

        # --- Define output paths for the task ---
        task_path_out = os.path.join(day_path_out, task_name_output)
        statements_out = os.path.join(task_path_out, "statements")
        graders_out = os.path.join(task_path_out, "graders")
        checkers_out = os.path.join(task_path_out, "checkers")
        tests_out = os.path.join(task_path_out, "tests")
        attachments_out = os.path.join(task_path_out, "attachments")
        solutions_out = os.path.join(task_path_out, "solutions")
        solutions_code_out = os.path.join(solutions_out, "Codes")
        solutions_editorial_out = os.path.join(solutions_out, "editorial")
        subtasks_out = os.path.join(task_path_out, "subtasks")

        # --- Create output directories ---
        os.makedirs(task_path_out, exist_ok=True)
        os.makedirs(statements_out, exist_ok=True)
        # Other directories will be created by copy_item or os.makedirs below

        # --- Copy components ---

        # problem.json
        copy_item(os.path.join(inner_task_dir, "problem.json"), os.path.join(task_path_out, "problem.json"))

        # graders
        copy_item(os.path.join(inner_task_dir, "graders"), graders_out)

        # checkers
        copy_item(os.path.join(inner_task_dir, "checker"), checkers_out)

        # tests
        copy_item(os.path.join(inner_task_dir, "tests"), tests_out)

        # attachments
        copy_item(os.path.join(inner_task_dir, "attachments"), attachments_out)

        # solutions/Codes
        os.makedirs(solutions_out, exist_ok=True) # Ensure parent 'solutions' dir exists
        copy_item(os.path.join(inner_task_dir, "solutions"), solutions_code_out)

        # solutions/editorial (PDFs)
        os.makedirs(solutions_editorial_out, exist_ok=True)
        if editorial_pdf_src and os.path.isfile(editorial_pdf_src):
            copy_item(editorial_pdf_src, os.path.join(solutions_editorial_out, os.path.basename(editorial_pdf_src)))
        else:
            logging.warning(f"Editorial PDF not found for task {task_name_output}")

        # subtasks
        copy_item(os.path.join(inner_task_dir, "subtasks"), subtasks_out)

        # Note: Statements are not explicitly found as separate files in the provided input
        # structure for day1/day2 tasks (often generated from sources or part of translations).
        # The statement directory is created but may remain empty unless problem.json is considered the statement.
        # For day0, the ISC PDFs are treated as editorials/solution booklets per the prompt.


logging.info("Processing complete.")