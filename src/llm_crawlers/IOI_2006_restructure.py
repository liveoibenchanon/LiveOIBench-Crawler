import os
import shutil
import re
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base directories
input_base_dir = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2006"
output_base_dir = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/"
year = "2006"

# Construct specific input and output paths
input_dir = os.path.join(input_base_dir) # The structure starts directly with 2006/
output_year_dir = os.path.join(output_base_dir, year)

# Helper function to create directories if they don't exist
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

# --- Task Identification and Mapping ---

# Manual mapping from statement PDF names (or parts) to (canonical_name, day)
# Canonical names derived from solution/testdata folders where possible
task_name_map = {
    # Day 1
    "Forbidden_Subgraph": ("forbidden", 1),
    "Pyramid": ("pyramid", 1),
    "Deciphering_the_Mayan_Writing": ("writing", 1),
    # Day 2
    "A_Black_Box_Game": ("blackbox", 2),
    "The_Valley_of_Mexico": ("mexico", 2),
    "Joining_Points": ("points", 2),
    # Practice (Day 0) - Use a sensible canonical name if no direct match in sol/tests
    "Highways": ("highways", 0),
    "Cutting a grid": ("cutting_a_grid", 0),
    "The fifth sun": ("the_fifth_sun", 0),
}

# Reverse map for quick lookup from solution/test short names
# Maps short_name (like 'mexico') to canonical_name (could be the same)
short_name_to_canonical = { val[0]: val[0] for key, val in task_name_map.items()}
# Ensure all solution/test names map correctly if canonical differs
# (In this case, they seem consistent, e.g., 'writing' maps to 'writing')
canonical_to_day = { val[0]: val[1] for key, val in task_name_map.items()}


# --- Main Processing Logic ---

def process_ioi_2006():
    logging.info(f"Processing IOI {year} from {input_dir} to {output_year_dir}")
    ensure_dir(output_year_dir)

    # Create a dictionary to hold paths for each task
    task_data = {} # { canonical_name: {'day': int, 'statements': [], 'solutions_editorial': [], 'tests': [], 'attachments': []} }

    # 1. Process Day 1 and Day 2 Problem Statements
    for day_num_str in ["day1", "day2"]:
        day_num = int(day_num_str[-1])
        day_path = os.path.join(input_dir, day_num_str)
        if not os.path.isdir(day_path):
            logging.warning(f"Directory not found: {day_path}")
            continue

        logging.info(f"Processing statements in {day_path}")
        for filename in os.listdir(day_path):
            if filename.endswith(".pdf"):
                match = re.match(r"0\d_(.+)\.pdf", filename)
                if match:
                    raw_name = match.group(1).replace('_', ' ') # Handle names like "Forbidden_Subgraph" -> "Forbidden Subgraph"
                    # Find the canonical name and day from the map
                    found = False
                    for map_key, (canonical_name, map_day) in task_name_map.items():
                         # Allow for slight variations (space vs underscore)
                        if raw_name.replace(' ', '_') == map_key or raw_name == map_key:
                            if map_day == day_num:
                                if canonical_name not in task_data:
                                    task_data[canonical_name] = {'day': day_num, 'statements': [], 'solutions_editorial': [], 'tests': [], 'attachments': []}
                                task_data[canonical_name]['statements'].append(os.path.join(day_path, filename))
                                logging.info(f"  Found statement: {filename} -> Task: {canonical_name}, Day: {day_num}")
                                found = True
                                break
                    if not found:
                         logging.warning(f"  Could not map statement file: {filename} in {day_path}")
                else:
                    logging.warning(f"  Unexpected PDF file name format in {day_path}: {filename}")

    # 2. Process Practice Problems (Day 0)
    practice_path = os.path.join(input_dir, "other_materials", "Practice")
    if os.path.isdir(practice_path):
        logging.info(f"Processing practice tasks in {practice_path}")
        for filename in os.listdir(practice_path):
            if filename.endswith(".pdf"):
                if filename == "Task Overview Sheet.pdf":
                    # Handle this general document later
                    continue
                raw_name = filename[:-4] # Remove .pdf
                found = False
                for map_key, (canonical_name, map_day) in task_name_map.items():
                    if raw_name == map_key and map_day == 0:
                         if canonical_name not in task_data:
                            task_data[canonical_name] = {'day': 0, 'statements': [], 'solutions_editorial': [], 'tests': [], 'attachments': []}
                         task_data[canonical_name]['statements'].append(os.path.join(practice_path, filename))
                         logging.info(f"  Found practice statement: {filename} -> Task: {canonical_name}, Day: 0")
                         found = True
                         break
                if not found:
                    logging.warning(f"  Could not map practice statement file: {filename}")
    else:
        logging.warning(f"Directory not found: {practice_path}")

    # 3. Process Solutions (Editorials)
    solutions_path = os.path.join(input_dir, "other_materials", "Solutions")
    if os.path.isdir(solutions_path):
        logging.info(f"Processing solutions in {solutions_path}")
        for filename in os.listdir(solutions_path):
            if filename.endswith("_sol.pdf"):
                short_name = filename[:-8] # Remove _sol.pdf
                canonical_name = short_name_to_canonical.get(short_name)
                if canonical_name and canonical_name in task_data:
                    task_data[canonical_name]['solutions_editorial'].append(os.path.join(solutions_path, filename))
                    logging.info(f"  Found solution: {filename} -> Task: {canonical_name}")
                elif canonical_name:
                     logging.warning(f"  Found solution file {filename} for task {canonical_name}, but task not previously identified from statements.")
                     # Decide how to handle - maybe create task entry now? Assume day based on canonical_to_day
                     day_num = canonical_to_day.get(canonical_name)
                     if day_num is not None:
                         task_data[canonical_name] = {'day': day_num, 'statements': [], 'solutions_editorial': [os.path.join(solutions_path, filename)], 'tests': [], 'attachments': []}
                         logging.info(f"    Created entry for task {canonical_name}, Day: {day_num} based on solution file.")
                     else:
                         logging.warning(f"    Cannot determine day for task {canonical_name} from solution file {filename}.")
                else:
                    logging.warning(f"  Could not map solution file: {filename}")
    else:
        logging.warning(f"Directory not found: {solutions_path}")

    # 4. Process Test Cases
    testcases_path = os.path.join(input_dir, "other_materials", "TestCases")
    if os.path.isdir(testcases_path):
        logging.info(f"Processing test cases in {testcases_path}")
        for dirname in os.listdir(testcases_path):
            if dirname.endswith("_td"):
                short_name = dirname[:-3] # Remove _td
                full_test_dir_path = os.path.join(testcases_path, dirname)
                if not os.path.isdir(full_test_dir_path):
                    continue

                canonical_name = short_name_to_canonical.get(short_name)
                if canonical_name and canonical_name in task_data:
                    task_data[canonical_name]['tests'].append(full_test_dir_path)
                    logging.info(f"  Found tests: {dirname} -> Task: {canonical_name}")
                elif canonical_name:
                    logging.warning(f"  Found test directory {dirname} for task {canonical_name}, but task not previously identified.")
                    # Create task entry if possible
                    day_num = canonical_to_day.get(canonical_name)
                    if day_num is not None:
                        task_data[canonical_name] = {'day': day_num, 'statements': [], 'solutions_editorial': [], 'tests': [full_test_dir_path], 'attachments': []}
                        logging.info(f"    Created entry for task {canonical_name}, Day: {day_num} based on test directory.")
                    else:
                        logging.warning(f"    Cannot determine day for task {canonical_name} from test directory {dirname}.")
                else:
                    logging.warning(f"  Could not map test directory: {dirname}")
    else:
        logging.warning(f"Directory not found: {testcases_path}")

    # 5. Copy files to the structured output directory
    logging.info("Copying files to output structure...")
    for canonical_name, data in task_data.items():
        day = data['day']
        task_output_dir = os.path.join(output_year_dir, f"day{day}", canonical_name)
        logging.info(f"  Processing task: {canonical_name} (Day {day}) -> {task_output_dir}")

        # Create standard subdirectories
        statements_dir = os.path.join(task_output_dir, "statements")
        graders_dir = os.path.join(task_output_dir, "graders")
        checkers_dir = os.path.join(task_output_dir, "checkers")
        tests_dir = os.path.join(task_output_dir, "tests")
        attachments_dir = os.path.join(task_output_dir, "attachments")
        solutions_dir = os.path.join(task_output_dir, "solutions")
        solutions_codes_dir = os.path.join(solutions_dir, "Codes")
        solutions_editorial_dir = os.path.join(solutions_dir, "editorial")
        subtasks_dir = os.path.join(task_output_dir, "subtasks")

        ensure_dir(statements_dir)
        ensure_dir(graders_dir) # Empty for this year
        ensure_dir(checkers_dir) # Empty for this year
        ensure_dir(tests_dir)
        ensure_dir(attachments_dir) # Empty for this year
        ensure_dir(solutions_dir)
        ensure_dir(solutions_codes_dir) # Empty for this year
        ensure_dir(solutions_editorial_dir)
        ensure_dir(subtasks_dir) # Empty for this year

        # Copy statements
        for src_file in data['statements']:
            try:
                dest_file = os.path.join(statements_dir, os.path.basename(src_file))
                shutil.copy2(src_file, dest_file)
                logging.info(f"    Copied statement: {os.path.basename(src_file)}")
            except Exception as e:
                logging.error(f"    Error copying statement {src_file} to {statements_dir}: {e}")

        # Copy solution editorials
        for src_file in data['solutions_editorial']:
             try:
                dest_file = os.path.join(solutions_editorial_dir, os.path.basename(src_file))
                shutil.copy2(src_file, dest_file)
                logging.info(f"    Copied solution editorial: {os.path.basename(src_file)}")
             except Exception as e:
                 logging.error(f"    Error copying solution {src_file} to {solutions_editorial_dir}: {e}")

        # Copy tests
        for src_test_dir in data['tests']:
            try:
                logging.info(f"    Copying tests from: {src_test_dir}")
                for item in os.listdir(src_test_dir):
                    s = os.path.join(src_test_dir, item)
                    d = os.path.join(tests_dir, item)
                    if os.path.isfile(s):
                        shutil.copy2(s, d)
                logging.info(f"      Copied test files from {os.path.basename(src_test_dir)}")
            except Exception as e:
                logging.error(f"    Error copying tests from {src_test_dir} to {tests_dir}: {e}")

        # Copy attachments (if any were identified)
        for src_file in data['attachments']:
             try:
                dest_file = os.path.join(attachments_dir, os.path.basename(src_file))
                shutil.copy2(src_file, dest_file)
                logging.info(f"    Copied attachment: {os.path.basename(src_file)}")
             except Exception as e:
                 logging.error(f"    Error copying attachment {src_file} to {attachments_dir}: {e}")


    # 6. Handle General/Other files
    logging.info("Processing general files...")
    general_editorial_dir = os.path.join(output_year_dir, "editorial")
    ensure_dir(general_editorial_dir)

    # Copy Task Overview Sheet if it exists
    overview_sheet_src = os.path.join(input_dir, "other_materials", "Practice", "Task Overview Sheet.pdf")
    if os.path.exists(overview_sheet_src):
        try:
            overview_sheet_dest = os.path.join(general_editorial_dir, os.path.basename(overview_sheet_src))
            shutil.copy2(overview_sheet_src, overview_sheet_dest)
            logging.info(f"  Copied general document: {os.path.basename(overview_sheet_src)} to {general_editorial_dir}")
        except Exception as e:
            logging.error(f"  Error copying {overview_sheet_src}: {e}")
    else:
        logging.info(f"  General document not found: {overview_sheet_src}")

    # Consider copying top-level ZIPs if needed as backups or primary source
    # For this script, we assume the unzipped folders are the primary source as shown in the example.
    # Example:
    # solutions_zip = os.path.join(input_dir, "other_materials", "Solutions.zip")
    # if os.path.exists(solutions_zip):
    #     shutil.copy2(solutions_zip, general_editorial_dir)
    #     logging.info(f"  Copied archive: Solutions.zip to {general_editorial_dir}")


    logging.info("Processing finished.")

# --- Execution ---
if __name__ == "__main__":
    # Basic validation of input directory
    if not os.path.isdir(input_dir):
        logging.error(f"Input directory not found: {input_dir}")
    elif not os.path.isdir(os.path.join(input_dir, "day1")) and not os.path.isdir(os.path.join(input_dir, "other_materials")):
         logging.error(f"Input directory {input_dir} does not seem to contain expected IOI 2006 structure (e.g., day1/, other_materials/).")
    else:
        process_ioi_2006()