import os
import shutil
import re
import zipfile
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base paths
# Input path: $HOME_DIR/IOI-Bench/IOI-New/2010
# Output path: $HOME_DIR/IOI-Bench/IOI-Processed/
# Use environment variables or command-line arguments for flexibility in a real scenario
# For this example, we'll hardcode them based on the prompt.
# INPUT_BASE_DIR = "$HOME_DIR/IOI-Bench/IOI-New"
# OUTPUT_BASE_DIR = "$HOME_DIR/IOI-Bench/IOI-Processed"

# Using placeholder paths for local testing if needed
INPUT_BASE_DIR = "ioi_2010_input_example" # Replace with the actual path if running locally
OUTPUT_BASE_DIR = "ioi_2010_output_example" # Replace with the actual path if running locally

IOI_YEAR = "2010"
INPUT_DIR = os.path.join(INPUT_BASE_DIR, IOI_YEAR)
OUTPUT_DIR = os.path.join(OUTPUT_BASE_DIR, IOI_YEAR)

# --- Task Name Normalization and Day Mapping ---
# Based on PDF names and TestCases folder names
# Normalizing to lowercase, underscore-separated names
TASK_NAME_MAP = {
    "Cluedo": "cluedo",
    "Hotter_Colder": "hotter_colder",
    "Quality_of_Living": "quality",
    "Memory": "memory",
    "Traffic": "traffic",
    "Maze": "maze",
    # Adding tasks found only in TestCases, assuming they are practice (day 0)
    "language": "language",
    "saveit": "saveit",
}

# Mapping canonical task names to days
TASK_DAY_MAP = {
    "cluedo": "day1",
    "hotter_colder": "day1",
    "quality": "day1",
    "memory": "day2",
    "traffic": "day2",
    "maze": "day2",
    # Practice tasks
    "language": "day0",
    "saveit": "day0",
}

# Helper function to safely copy files
def safe_copy(src, dst):
    """Copies a file from src to dst, creating destination directories if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # logging.info(f"Copied {src} to {dst}")
    except FileNotFoundError:
        logging.warning(f"Source file not found: {src}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dst}: {e}")

# Helper function to copy entire directory contents
def copy_directory_contents(src_dir, dst_dir):
    """Copies all contents of src_dir to dst_dir."""
    try:
        if not os.path.isdir(src_dir):
            logging.warning(f"Source directory not found or is not a directory: {src_dir}")
            return
        os.makedirs(dst_dir, exist_ok=True)
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(dst_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        # logging.info(f"Copied contents of {src_dir} to {dst_dir}")
    except Exception as e:
        logging.error(f"Error copying directory {src_dir} to {dst_dir}: {e}")

# Helper function to extract zip files
def extract_zip(zip_path, extract_to):
    """Extracts a zip file to a specified directory."""
    if not os.path.exists(zip_path):
        logging.warning(f"Zip file not found: {zip_path}")
        return False
    try:
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        logging.info(f"Extracted {zip_path} to {extract_to}")
        return True
    except zipfile.BadZipFile:
        logging.error(f"Error: Bad zip file {zip_path}")
        return False
    except Exception as e:
        logging.error(f"Error extracting {zip_path}: {e}")
        return False

# --- Main Processing Logic ---

def process_ioi_2010():
    logging.info(f"Starting processing for IOI {IOI_YEAR}")
    logging.info(f"Input directory: {INPUT_DIR}")
    logging.info(f"Output directory: {OUTPUT_DIR}")

    if not os.path.isdir(INPUT_DIR):
        logging.error(f"Input directory {INPUT_DIR} does not exist. Please check the path.")
        # Create dummy input structure for local testing if needed
        # create_dummy_input(INPUT_DIR) # Uncomment to create dummy files/folders
        # return # Stop if input dir is missing in a real run

    # Create the base output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 1. Process General Editorial ---
    logging.info("Processing general editorial...")
    editorial_src = os.path.join(INPUT_DIR, "other_materials", "Solutions_to_all_problems.pdf")
    editorial_dst_dir = os.path.join(OUTPUT_DIR, "editorial")
    if os.path.exists(editorial_src):
        safe_copy(editorial_src, os.path.join(editorial_dst_dir, os.path.basename(editorial_src)))
        logging.info(f"Found and copied general editorial: {editorial_src}")
    else:
        logging.warning("General editorial PDF not found.")

    # --- Extract Archives (if necessary) ---
    # Check if unzipped folders exist, otherwise try extracting
    solutions_dir = os.path.join(INPUT_DIR, "other_materials", "Solutions")
    testcases_dir = os.path.join(INPUT_DIR, "other_materials", "TestCases")
    solutions_zip = os.path.join(INPUT_DIR, "other_materials", "Solutions.zip")
    testcases_zip = os.path.join(INPUT_DIR, "other_materials", "TestCases.zip")

    temp_extract_dir = os.path.join(OUTPUT_DIR, "_temp_extract") # Temporary extraction location

    if not os.path.isdir(solutions_dir):
        logging.info(f"Solutions directory not found at {solutions_dir}. Trying to extract from {solutions_zip}")
        if extract_zip(solutions_zip, temp_extract_dir):
            # Check if the zip extraction created the expected 'Solutions' folder structure
            extracted_solutions_path = os.path.join(temp_extract_dir, "Solutions") # Common zip structure
            if not os.path.isdir(extracted_solutions_path):
                 extracted_solutions_path = temp_extract_dir # Assume extraction is flat if 'Solutions' isn't there
            
            if os.path.isdir(extracted_solutions_path):
                 solutions_dir = extracted_solutions_path
            else:
                 logging.warning(f"Could not find a valid 'Solutions' structure after extracting {solutions_zip}")
        else:
            logging.warning(f"Solutions directory and zip file not found or failed to extract.")
            solutions_dir = None # Mark as unavailable

    if not os.path.isdir(testcases_dir):
        logging.info(f"TestCases directory not found at {testcases_dir}. Trying to extract from {testcases_zip}")
        if extract_zip(testcases_zip, temp_extract_dir):
            extracted_testcases_path = os.path.join(temp_extract_dir, "TestCases")
            if not os.path.isdir(extracted_testcases_path):
                 extracted_testcases_path = temp_extract_dir

            if os.path.isdir(extracted_testcases_path):
                testcases_dir = extracted_testcases_path
            else:
                logging.warning(f"Could not find a valid 'TestCases' structure after extracting {testcases_zip}")
        else:
            logging.warning(f"TestCases directory and zip file not found or failed to extract.")
            testcases_dir = None # Mark as unavailable


    # --- 2. Process Tasks (Statements, Tests, Solutions, Graders, Checkers) ---
    processed_tasks = set()

    # First, identify tasks from PDF statements
    logging.info("Processing problem statements (PDFs)...")
    for day_folder in ["day1", "day2"]:
        day_path = os.path.join(INPUT_DIR, day_folder)
        if not os.path.isdir(day_path):
            logging.warning(f"Directory not found: {day_path}")
            continue

        for filename in os.listdir(day_path):
            if filename.lower().endswith(".pdf"):
                match = re.match(r"\d{2}_(.*)\.pdf", filename, re.IGNORECASE)
                if match:
                    pdf_task_name = match.group(1).replace('_', ' ').replace('-', ' ')
                    # Attempt to find a direct match or normalize
                    task_name_key = pdf_task_name.replace(' ', '_') # Try underscore version first
                    if task_name_key not in TASK_NAME_MAP:
                         # Fallback: check variation like "Quality of Living" vs "Quality_of_Living"
                         task_name_key = pdf_task_name.replace(' ', '') # Try removing spaces
                         found = False
                         for k, v in TASK_NAME_MAP.items():
                             if k.replace('_','').lower() == task_name_key.lower():
                                 task_name_key = k
                                 found = True
                                 break
                         if not found:
                              logging.warning(f"Could not map PDF task name '{pdf_task_name}' from {filename} to a known canonical name.")
                              continue


                    canonical_task_name = TASK_NAME_MAP.get(task_name_key)
                    if not canonical_task_name:
                        logging.warning(f"No canonical name found for PDF task: {task_name_key}")
                        continue

                    day = TASK_DAY_MAP.get(canonical_task_name)
                    if not day:
                        logging.warning(f"No day assigned for task: {canonical_task_name}")
                        continue

                    processed_tasks.add(canonical_task_name)
                    logging.info(f"Found task: {canonical_task_name} (Day {day[-1]}) from {filename}")

                    task_output_dir = os.path.join(OUTPUT_DIR, day, canonical_task_name)

                    # Create task structure
                    statements_dir = os.path.join(task_output_dir, "statements")
                    graders_dir = os.path.join(task_output_dir, "graders")
                    checkers_dir = os.path.join(task_output_dir, "checkers")
                    tests_dir = os.path.join(task_output_dir, "tests")
                    attachments_dir = os.path.join(task_output_dir, "attachments")
                    solutions_dir_out = os.path.join(task_output_dir, "solutions")
                    solutions_codes_dir = os.path.join(solutions_dir_out, "Codes")
                    solutions_editorial_dir = os.path.join(solutions_dir_out, "editorial")
                    subtasks_base_dir = os.path.join(task_output_dir, "subtasks")

                    os.makedirs(statements_dir, exist_ok=True)
                    os.makedirs(graders_dir, exist_ok=True)
                    os.makedirs(checkers_dir, exist_ok=True)
                    os.makedirs(tests_dir, exist_ok=True)
                    os.makedirs(attachments_dir, exist_ok=True)
                    os.makedirs(solutions_codes_dir, exist_ok=True)
                    os.makedirs(solutions_editorial_dir, exist_ok=True)
                    os.makedirs(subtasks_base_dir, exist_ok=True) # Base for subtask info

                    # Copy statement PDF
                    statement_src = os.path.join(day_path, filename)
                    statement_dst = os.path.join(statements_dir, f"{canonical_task_name}.pdf")
                    safe_copy(statement_src, statement_dst)

    # Process tasks found only in TestCases/Solutions (likely practice/day0)
    logging.info("Checking for additional tasks in TestCases/Solutions...")
    source_dirs_for_tasks = []
    if testcases_dir and os.path.isdir(testcases_dir):
        source_dirs_for_tasks.append(testcases_dir)
    if solutions_dir and os.path.isdir(solutions_dir):
         # Check if solutions_dir contains task folders directly
        is_task_folder = False
        for item in os.listdir(solutions_dir):
            if os.path.isdir(os.path.join(solutions_dir, item)) and item.lower() in TASK_DAY_MAP:
                 is_task_folder = True
                 break
        if is_task_folder:
            source_dirs_for_tasks.append(solutions_dir)


    for source_dir in source_dirs_for_tasks:
         for task_folder_name in os.listdir(source_dir):
             task_folder_path = os.path.join(source_dir, task_folder_name)
             if os.path.isdir(task_folder_path):
                 canonical_task_name = task_folder_name.lower()
                 # Find the canonical name if it's slightly different (e.g., case)
                 matched_canonical_name = None
                 for cn in TASK_DAY_MAP.keys():
                     if cn == canonical_task_name:
                         matched_canonical_name = cn
                         break
                 
                 if matched_canonical_name and matched_canonical_name not in processed_tasks:
                     day = TASK_DAY_MAP.get(matched_canonical_name)
                     if not day: continue # Skip if no day assigned

                     processed_tasks.add(matched_canonical_name)
                     logging.info(f"Found additional task: {matched_canonical_name} (Day {day[-1]}) from {source_dir}")

                     task_output_dir = os.path.join(OUTPUT_DIR, day, matched_canonical_name)
                     # Create structure (redundant if created by PDF processing, but safe)
                     os.makedirs(os.path.join(task_output_dir, "statements"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "graders"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "checkers"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "tests"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "attachments"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "solutions", "Codes"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "solutions", "editorial"), exist_ok=True)
                     os.makedirs(os.path.join(task_output_dir, "subtasks"), exist_ok=True)


    # --- 3. Process Tests from TestCases directory ---
    logging.info("Processing test cases...")
    if testcases_dir and os.path.isdir(testcases_dir):
        for task_folder_name in os.listdir(testcases_dir):
             canonical_task_name = None
             for cn_map, cn_target in TASK_NAME_MAP.items():
                 # Match TestCases folder name (e.g., 'quality') to canonical name ('quality')
                 if task_folder_name.lower() == cn_target:
                      canonical_task_name = cn_target
                      break
             # Fallback for cases where the folder name *is* the canonical name but not in TASK_NAME_MAP keys
             if not canonical_task_name and task_folder_name.lower() in TASK_DAY_MAP:
                 canonical_task_name = task_folder_name.lower()


             if not canonical_task_name:
                 logging.warning(f"Skipping unrecognized folder in TestCases: {task_folder_name}")
                 continue

             day = TASK_DAY_MAP.get(canonical_task_name)
             if not day:
                 logging.warning(f"No day found for task {canonical_task_name} from TestCases folder. Skipping tests.")
                 continue

             task_tests_input_dir = os.path.join(testcases_dir, task_folder_name)
             task_output_dir = os.path.join(OUTPUT_DIR, day, canonical_task_name)
             tests_output_dir = os.path.join(task_output_dir, "tests")
             subtasks_output_dir = os.path.join(task_output_dir, "subtasks")

             # Locate the actual test data, often inside 'appeal/SubtaskX-data'
             appeal_dir = os.path.join(task_tests_input_dir, "appeal")
             if os.path.isdir(appeal_dir):
                 for subtask_folder in os.listdir(appeal_dir):
                     subtask_match = re.match(r"Subtask(\d+)-data", subtask_folder, re.IGNORECASE)
                     if subtask_match:
                         subtask_num = subtask_match.group(1)
                         subtask_data_dir = os.path.join(appeal_dir, subtask_folder)
                         
                         # Create marker folder for the subtask
                         os.makedirs(os.path.join(subtasks_output_dir, f"subtask{subtask_num}"), exist_ok=True)

                         logging.info(f"Processing tests for {canonical_task_name}, Subtask {subtask_num}")
                         for filename in os.listdir(subtask_data_dir):
                             src_file = os.path.join(subtask_data_dir, filename)
                             if not os.path.isfile(src_file): continue

                             # --- Test file renaming logic ---
                             dst_filename = filename
                             # Case 1: grader.in.G-S / grader.expect.G-S (e.g., quality)
                             match_gs_in = re.match(r"grader\.in\.(\d+)-(\d+)", filename, re.IGNORECASE)
                             match_gs_expect = re.match(r"grader\.expect\.(\d+)-(\d+)", filename, re.IGNORECASE)
                             # Case 2: grader.in.N / grader.expect.N (e.g., cluedo, hottercolder)
                             match_n_in = re.match(r"grader\.in\.(\d+)", filename, re.IGNORECASE)
                             match_n_expect = re.match(r"grader\.expect\.(\d+)", filename, re.IGNORECASE)

                             if match_gs_in:
                                 # Group (G), Subtask (S) -> S_G.in
                                 # Note: The subtask number in the filename might differ from the folder subtask number.
                                 # Let's use the one from the filename primarily.
                                 g, s_file = match_gs_in.groups()
                                 # Check consistency:
                                 # if s_file != subtask_num:
                                 #    logging.warning(f"Subtask number mismatch for {filename}: Folder says {subtask_num}, file says {s_file}")
                                 # Prioritize filename subtask number for naming convention
                                 dst_filename = f"subtask{s_file}_{g}.in"
                             elif match_gs_expect:
                                 g, s_file = match_gs_expect.groups()
                                 # if s_file != subtask_num:
                                 #    logging.warning(f"Subtask number mismatch for {filename}: Folder says {subtask_num}, file says {s_file}")
                                 dst_filename = f"subtask{s_file}_{g}.ans" # Use .ans for expected output
                             elif match_n_in:
                                 n = match_n_in.group(1)
                                 # For files like grader.in.1, just use the number N.in
                                 # Prefix with subtask number from folder if needed for uniqueness across subtasks
                                 dst_filename = f"subtask{subtask_num}_{n}.in"
                                 # Simpler alternative: just n.in? Could clash if N repeats across subtasks.
                                 # Let's stick with subtask prefix for safety.
                                 # If only one subtask exists maybe remove prefix later? For now, be explicit.
                                 # Example: subtask1_1.in
                             elif match_n_expect:
                                 n = match_n_expect.group(1)
                                 dst_filename = f"subtask{subtask_num}_{n}.ans" # Example: subtask1_1.ans
                             else:
                                 # General case: Copy as is, maybe try standardizing extensions
                                 if filename.lower().endswith(".in"):
                                     pass # Keep .in
                                 elif filename.lower().endswith(".out") or filename.lower().endswith(".ans") or filename.lower().endswith(".expect"):
                                     base, _ = os.path.splitext(filename)
                                     dst_filename = f"{base}.ans"
                                 # Handle cases with just numbers or base names (assuming pairs)
                                 # This part is heuristic. If 'test1' and 'test1.a' exist, assume in/ans.
                                 # Let's just copy as-is for simplicity now.
                                 pass # Keep original name if no pattern matches


                             dst_file = os.path.join(tests_output_dir, dst_filename)
                             safe_copy(src_file, dst_file)
             else:
                 # Fallback: Maybe tests are directly in the task folder? Unlikely based on structure.
                 logging.warning(f"No 'appeal' directory found in {task_tests_input_dir}. Cannot locate subtask tests.")

    else:
        logging.warning("TestCases directory not found or is not a directory. Skipping test processing.")


    # --- 4. Process Solutions, Graders, Checkers from Solutions directory ---
    logging.info("Processing solutions, graders, checkers...")
    if solutions_dir and os.path.isdir(solutions_dir):
        for item_name in os.listdir(solutions_dir):
            item_path = os.path.join(solutions_dir, item_name)
            if os.path.isdir(item_path): # Assume item_name is the task name (or similar)
                task_folder_name = item_name

                canonical_task_name = None
                # Try to match folder name to a canonical task name
                for cn_map, cn_target in TASK_NAME_MAP.items():
                     # Try direct match first (case-insensitive)
                    if task_folder_name.lower() == cn_map.lower():
                        canonical_task_name = cn_target
                        break
                    # Try matching to the canonical name itself
                    if task_folder_name.lower() == cn_target:
                        canonical_task_name = cn_target
                        break
                # Fallback like in TestCases
                if not canonical_task_name and task_folder_name.lower() in TASK_DAY_MAP:
                      canonical_task_name = task_folder_name.lower()


                if not canonical_task_name:
                    logging.warning(f"Skipping unrecognized folder in Solutions: {task_folder_name}")
                    continue

                day = TASK_DAY_MAP.get(canonical_task_name)
                if not day:
                    logging.warning(f"No day found for task {canonical_task_name} from Solutions folder. Skipping solutions.")
                    continue

                task_output_dir = os.path.join(OUTPUT_DIR, day, canonical_task_name)
                solutions_codes_dir = os.path.join(task_output_dir, "solutions", "Codes")
                graders_dir = os.path.join(task_output_dir, "graders")
                checkers_dir = os.path.join(task_output_dir, "checkers")

                logging.info(f"Processing solutions/graders for {canonical_task_name}")

                # Recursively search for relevant files within the task solution folder
                for root, _, files in os.walk(item_path):
                    for filename in files:
                        src_file_path = os.path.join(root, filename)
                        # Simple heuristic classification based on name
                        fn_lower = filename.lower()
                        is_grader = fn_lower.startswith("grader.") or fn_lower == "grader"
                        is_checker = fn_lower.startswith("checker.") or fn_lower == "checker" or fn_lower.startswith("check.")

                        if is_grader:
                            safe_copy(src_file_path, os.path.join(graders_dir, filename))
                        elif is_checker:
                             safe_copy(src_file_path, os.path.join(checkers_dir, filename))
                        else:
                             # Assume everything else is part of the solution code/materials
                             # Copy preserving relative structure within the task's solution folder
                             relative_path = os.path.relpath(src_file_path, item_path)
                             dst_file_path = os.path.join(solutions_codes_dir, relative_path)
                             safe_copy(src_file_path, dst_file_path)

    else:
        logging.warning("Solutions directory not found or is not a directory. Skipping solution/grader processing.")

    # --- Cleanup ---
    if os.path.exists(temp_extract_dir):
        logging.info(f"Removing temporary extraction directory: {temp_extract_dir}")
        try:
            shutil.rmtree(temp_extract_dir)
        except Exception as e:
            logging.error(f"Failed to remove temporary directory {temp_extract_dir}: {e}")


    logging.info(f"Finished processing for IOI {IOI_YEAR}.")

# --- Dummy Input Creation (for local testing without real data) ---
def create_dummy_input(base_dir):
    """Creates a minimal dummy structure mirroring the input"""
    logging.info(f"Creating dummy input structure at {base_dir}")
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "memory", "appeal", "Subtask1-data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "cluedo", "appeal", "Subtask1-data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "quality", "appeal", "Subtask1-data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "quality", "appeal", "Subtask2-data"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "day1"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "day2"), exist_ok=True)

    # Dummy files
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions_to_all_problems.pdf"), 'w') as f: f.write("Dummy Editorial")
    with open(os.path.join(base_dir, IOI_YEAR, "day1", "01_Cluedo.pdf"), 'w') as f: f.write("Dummy Cluedo Statement")
    with open(os.path.join(base_dir, IOI_YEAR, "day1", "03_Quality_of_Living.pdf"), 'w') as f: f.write("Dummy Quality Statement")
    with open(os.path.join(base_dir, IOI_YEAR, "day2", "01_Memory.pdf"), 'w') as f: f.write("Dummy Memory Statement")
    with open(os.path.join(base_dir, IOI_YEAR, "day2", "03_Maze.pdf"), 'w') as f: f.write("Dummy Maze Statement") # Task with no tests/solutions in example

    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "cluedo", "appeal", "Subtask1-data", "grader.in.1"), 'w') as f: f.write("cluedo test in 1")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "cluedo", "appeal", "Subtask1-data", "grader.expect.1"), 'w') as f: f.write("cluedo test ans 1")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "quality", "appeal", "Subtask1-data", "grader.in.1-1"), 'w') as f: f.write("quality test in 1-1")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "quality", "appeal", "Subtask1-data", "grader.expect.1-1"), 'w') as f: f.write("quality test ans 1-1")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "quality", "appeal", "Subtask2-data", "grader.in.1-2"), 'w') as f: f.write("quality test in 1-2")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "quality", "appeal", "Subtask2-data", "grader.expect.1-2"), 'w') as f: f.write("quality test ans 1-2")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "memory", "appeal", "Subtask1-data", "mem1.in"), 'w') as f: f.write("mem in")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "TestCases", "memory", "appeal", "Subtask1-data", "mem1.out"), 'w') as f: f.write("mem out") # Use .out here to test renaming

    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions", "cluedo"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions", "quality"), exist_ok=True)
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions", "cluedo", "cluedo.cpp"), 'w') as f: f.write("dummy cluedo sol")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions", "cluedo", "grader.cpp"), 'w') as f: f.write("dummy cluedo grader")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions", "quality", "quality_fast.pas"), 'w') as f: f.write("dummy quality sol")
    with open(os.path.join(base_dir, IOI_YEAR, "other_materials", "Solutions", "quality", "checker.cpp"), 'w') as f: f.write("dummy quality checker")


if __name__ == "__main__":
    # Example of creating dummy input if the specified INPUT_BASE_DIR doesn't exist
    # Useful for testing the script structure without the actual IOI data.
    # In a real run, you would remove or comment out this check/creation.
    # if not os.path.exists(INPUT_DIR):
    #    create_dummy_input(INPUT_BASE_DIR)

    # Check if input directory exists before running
    if os.path.isdir(INPUT_DIR):
        process_ioi_2010()
    else:
        logging.error(f"Input directory {INPUT_DIR} not found. Cannot proceed.")
        logging.info("Consider creating a dummy structure using create_dummy_input() for testing,")
        logging.info(f"or ensure the real data exists at the specified path: {INPUT_BASE_DIR}")