import os
import shutil
import zipfile
import re

def safe_copy(src, dst):
    """Copies a file from src to dst, creating destination directories if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"Copied: {src} -> {dst}")
    except Exception as e:
        print(f"Error copying {src} to {dst}: {e}")

def copy_folder_contents(src_dir, dst_dir):
    """Copies contents of src_dir to dst_dir, creating dst_dir if needed."""
    try:
        if not os.path.isdir(src_dir):
            print(f"Source directory {src_dir} not found or is not a directory.")
            return
        os.makedirs(dst_dir, exist_ok=True)
        # Use shutil.copytree with dirs_exist_ok=True to copy contents
        # This requires Python 3.8+
        # For compatibility, let's iterate and copy
        for item in os.listdir(src_dir):
            s = os.path.join(src_dir, item)
            d = os.path.join(dst_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
                # print(f"Copied folder: {s} -> {d}")
            else:
                shutil.copy2(s, d)
                # print(f"Copied file: {s} -> {d}")
        print(f"Copied contents: {src_dir} -> {dst_dir}")

    except Exception as e:
        print(f"Error copying folder contents from {src_dir} to {dst_dir}: {e}")


def extract_zip(zip_path, dest_dir):
    """Extracts a zip file to a destination directory."""
    try:
        os.makedirs(dest_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        print(f"Extracted: {zip_path} -> {dest_dir}")
    except zipfile.BadZipFile:
        print(f"Error: {zip_path} is not a valid zip file or is corrupted.")
    except Exception as e:
        print(f"Error extracting {zip_path} to {dest_dir}: {e}")

def process_ioi_2008(source_base_dir, output_base_dir):
    """
    Organizes IOI 2008 contest materials from source_dir to output_dir
    following the specified structure.
    """
    year = "2008"
    source_dir = os.path.join(source_base_dir, year)
    output_dir = os.path.join(output_base_dir, year)

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory {source_dir} not found.")
        return

    print(f"Processing IOI {year} data...")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")

    # Create base output directory for the year
    os.makedirs(output_dir, exist_ok=True)

    # --- Top Level Files ---
    editorial_dir_top = os.path.join(output_dir, "editorial")
    os.makedirs(editorial_dir_top, exist_ok=True)

    top_level_files = {
        "IOI2008Booklet1.0.pdf": editorial_dir_top,
        # Add other potential top-level editorials/docs here if needed
    }

    for filename, dest_dir in top_level_files.items():
        src_file = os.path.join(source_dir, filename)
        if os.path.isfile(src_file):
            safe_copy(src_file, os.path.join(dest_dir, filename))

    # --- Process Days (day0, day1, day2) ---
    day_folders = ["day0", "day1", "day2"]
    # Mapping from abbreviation/folder name to task name (lowercase)
    # We will primarily rely on PDF names, but this helps link folders/zips
    abbr_map = {
        'isl': 'islands', 'fsh': 'fish', 'typ': 'printer', # day1
        'lin': 'linear_garden', 'tel': 'teleporters', 'pbs': 'pyramid_base', # day2
        'game_module': 'game', # day0 (special case folder)
        'pyramid_unix_data': 'pyramid', # day0 (special case folder)
        'pyramid_windows_data': 'pyramid' # day0 (special case folder)
        # Note: 'buses' in day0 has only PDF
    }

    for day in day_folders:
        src_day_dir = os.path.join(source_dir, day)
        out_day_dir = os.path.join(output_dir, day)

        if not os.path.isdir(src_day_dir):
            print(f"Warning: Day directory {src_day_dir} not found. Skipping.")
            continue

        print(f"\nProcessing {day}...")
        os.makedirs(out_day_dir, exist_ok=True)

        # --- Day Level Editorials/Overviews ---
        day_editorial_dir = os.path.join(out_day_dir, "editorial")
        os.makedirs(day_editorial_dir, exist_ok=True)
        overview_pattern = re.compile(r"overview\d*\.pdf", re.IGNORECASE)

        # --- Identify Tasks and Process Files ---
        tasks_processed = set()
        task_statement_files = {}

        # 1. Find statement PDFs first to define tasks
        for item in sorted(os.listdir(src_day_dir)):
            item_path = os.path.join(src_day_dir, item)
            if os.path.isfile(item_path) and item.lower().endswith(".pdf"):
                base_name, _ = os.path.splitext(item)
                # Check if it's an overview file
                if overview_pattern.match(item):
                    safe_copy(item_path, os.path.join(day_editorial_dir, item))
                # Check if it's a known statement file (heuristic: not overview, not booklet)
                elif "booklet" not in item.lower():
                    # Basic task name extraction
                    task_name = base_name.lower().replace(" ", "_")
                    # Handle known specific pdf names if needed (e.g. if different from folder abbr)
                    if task_name not in ["overview0", "overview1", "overview2"]: # Add known non-tasks
                         task_statement_files[task_name] = item_path
                         print(f"  Identified Task: {task_name} (from {item})")


        # 2. Process each identified task
        for task_name, stmt_path in task_statement_files.items():
            print(f"    Processing task: {task_name}")
            out_task_dir = os.path.join(out_day_dir, task_name)
            tasks_processed.add(task_name)

            # Create standard subdirectories
            statements_dir = os.path.join(out_task_dir, "statements")
            graders_dir = os.path.join(out_task_dir, "graders")
            checkers_dir = os.path.join(out_task_dir, "checkers")
            tests_dir = os.path.join(out_task_dir, "tests")
            attachments_dir = os.path.join(out_task_dir, "attachments")
            solutions_dir = os.path.join(out_task_dir, "solutions")
            solutions_codes_dir = os.path.join(solutions_dir, "Codes")
            solutions_editorial_dir = os.path.join(solutions_dir, "editorial")
            subtasks_dir = os.path.join(out_task_dir, "subtasks") # Even if empty

            for d in [statements_dir, graders_dir, checkers_dir, tests_dir,
                      attachments_dir, solutions_codes_dir, solutions_editorial_dir,
                      subtasks_dir]:
                os.makedirs(d, exist_ok=True)

            # Copy statement
            safe_copy(stmt_path, os.path.join(statements_dir, os.path.basename(stmt_path)))

        # 3. Process associated folders and zips (Tests, Attachments, Graders etc.)
        for item in sorted(os.listdir(src_day_dir)):
            item_path = os.path.join(src_day_dir, item)
            item_lower = item.lower()

            # Check if it's a directory potentially related to a task
            if os.path.isdir(item_path):
                dir_name_lower = item_lower
                target_task = abbr_map.get(dir_name_lower)

                if target_task:
                    out_task_dir = os.path.join(out_day_dir, target_task)
                    if not os.path.exists(out_task_dir):
                         print(f"      Warning: Task dir {out_task_dir} not found for folder {item}. Skipping copy.")
                         continue

                    # Specific handling based on folder name
                    if dir_name_lower == "game_module":
                         # Copy the entire game_module folder into attachments
                         dest_attach_dir = os.path.join(attachments_dir, item) # Keep original folder name
                         print(f"      Copying attachment folder: {item_path} -> {dest_attach_dir}")
                         if os.path.exists(dest_attach_dir): # Avoid error if ran twice
                             shutil.rmtree(dest_attach_dir)
                         shutil.copytree(item_path, dest_attach_dir)

                    elif dir_name_lower in ["pyramid_unix_data", "pyramid_windows_data"]:
                        # These contain test data, copy contents into tests/
                        target_tests_dir = os.path.join(out_day_dir, target_task, "tests")
                        print(f"      Copying test data folder contents: {item_path} -> {target_tests_dir}")
                        copy_folder_contents(item_path, target_tests_dir)
                    else:
                        # General case: assume folders like 'isl', 'fsh', 'tel' contain tests/data
                        target_tests_dir = os.path.join(out_day_dir, target_task, "tests")
                        print(f"      Copying potential test data folder contents: {item_path} -> {target_tests_dir}")
                        copy_folder_contents(item_path, target_tests_dir)
                else:
                    print(f"      Skipping unknown directory: {item}")


            # Check if it's a zip file potentially related to a task
            elif os.path.isfile(item_path) and item_lower.endswith(".zip"):
                zip_base_name, _ = os.path.splitext(item_lower)
                target_task = abbr_map.get(zip_base_name)

                # Check if a folder with the same base name already exists
                corresponding_folder_path = os.path.join(src_day_dir, zip_base_name)
                if os.path.isdir(corresponding_folder_path):
                    print(f"      Skipping zip file {item} as corresponding folder {zip_base_name}/ exists.")
                    continue # Prioritize folder contents

                if target_task:
                    out_task_dir = os.path.join(out_day_dir, target_task)
                    if not os.path.exists(out_task_dir):
                         print(f"      Warning: Task dir {out_task_dir} not found for zip {item}. Skipping extract.")
                         continue

                    # Determine where to extract based on zip name conventions
                    dest_dir = None
                    if zip_base_name == "game_module":
                        dest_dir = os.path.join(out_day_dir, target_task, "attachments", zip_base_name) # Extract into named folder
                    elif zip_base_name in ["pyramid_unix_data", "pyramid_windows_data"]:
                        dest_dir = os.path.join(out_day_dir, target_task, "tests") # Extract contents into tests
                    else:
                        # General case: assume zips like 'isl.zip', 'fsh.zip' contain tests/data
                         dest_dir = os.path.join(out_day_dir, target_task, "tests")

                    if dest_dir:
                         print(f"      Extracting zip: {item_path} -> {dest_dir}")
                         extract_zip(item_path, dest_dir)
                else:
                     print(f"      Skipping unknown zip file: {item}")


        # Check for tasks identified by PDF but without corresponding folders/zips processed
        # (e.g., 'buses' in day0 only has a PDF)
        all_items_in_day = {f.lower() for f in os.listdir(src_day_dir)}
        all_items_in_day.update({os.path.splitext(f)[0].lower() for f in all_items_in_day if f.endswith('.zip')})

        found_task_keys = set()
        for key, task in abbr_map.items():
            if key in all_items_in_day:
                found_task_keys.add(task)

        for task_name in task_statement_files:
             if task_name not in found_task_keys and task_name != 'buses': # buses known to have no folder/zip
                  # Check if it wasn't handled by a specific rule already
                  is_handled = False
                  for abbr, mapped_task in abbr_map.items():
                      if task_name == mapped_task:
                          # Check if the abbr folder or zip existed
                          if os.path.isdir(os.path.join(src_day_dir, abbr)) or \
                             os.path.isfile(os.path.join(src_day_dir, abbr + ".zip")):
                              is_handled = True
                              break
                  if not is_handled:
                      print(f"      Note: Task '{task_name}' has a statement PDF but no obvious associated folder/zip found for tests/attachments based on mappings.")


    print("\nProcessing complete.")


# --- Configuration ---
# Source directory containing the IOI 2008 folder structure
SOURCE_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI"
# Target directory where the processed '2008' folder will be created
OUTPUT_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"

# --- Run the processing ---
process_ioi_2008(SOURCE_BASE_DIR, OUTPUT_BASE_DIR)