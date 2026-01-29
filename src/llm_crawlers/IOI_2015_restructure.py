import os
import shutil
import re

def safe_copy(src, dst):
    """Safely copies a file or directory, creating destination dirs if needed."""
    try:
        dst_dir = os.path.dirname(dst)
        os.makedirs(dst_dir, exist_ok=True)
        if os.path.isdir(src):
            # Avoid copying into itself if dst is within src
            # Also handle cases where dst already exists and is a directory
            if os.path.commonpath([src]) == os.path.commonpath([src, dst]):
                 print(f"Skipping copy to avoid recursion: {src} -> {dst}")
                 return
            if os.path.exists(dst):
                 print(f"Destination directory {dst} already exists. Merging contents.")
                 # Manually copy contents if dest exists to merge
                 for item in os.listdir(src):
                     s_item = os.path.join(src, item)
                     d_item = os.path.join(dst, item)
                     safe_copy(s_item, d_item) # Recursive call for sub-items
            else:
                 shutil.copytree(src, dst, dirs_exist_ok=True)
                 print(f"Copied directory: {src} -> {dst}")
        else:
            shutil.copy2(src, dst) # copy2 preserves metadata
            print(f"Copied file: {src} -> {dst}")
    except FileNotFoundError:
        print(f"Error: Source not found - {src}")
    except Exception as e:
        print(f"Error copying {src} to {dst}: {e}")

def extract_task_name_day(pdf_filename):
    """Extracts task name from day PDF filenames like '01_Scales.pdf'."""
    match = re.match(r"\d{2}_([a-zA-Z0-9]+)\.pdf", pdf_filename)
    if match:
        return match.group(1).lower()
    return None

def extract_task_name_other(filename):
    """Extracts task name from other filenames like 'teams.pdf' or 'divide.pdf'."""
    return os.path.splitext(filename)[0].lower()

def main():
    source_root = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2015"
    dest_root = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/2015"

    # --- Basic Setup ---
    if os.path.exists(dest_root):
        print(f"Destination directory {dest_root} already exists. Proceeding.")
    else:
        os.makedirs(dest_root, exist_ok=True)
        print(f"Created destination directory: {dest_root}")

    # --- Task to Day Mapping ---
    # Determined by examining the day1/ day2/ folders and practice folder
    task_day_map = {
        'scales': 'day1', 'teams': 'day1', 'boxes': 'day1',
        'towns': 'day2', 'sorting': 'day2', 'horses': 'day2',
        'divide': 'day0', 'search': 'day0', 'graph': 'day0' # From Practice folder
    }

    processed_tasks = set()

    # --- 1. Process Problem Statements ---
    print("\n--- Processing Problem Statements ---")
    # Day 1 & 2
    for day in ['day1', 'day2']:
        day_src_dir = os.path.join(source_root, day)
        if os.path.isdir(day_src_dir):
            for filename in os.listdir(day_src_dir):
                if filename.endswith(".pdf"):
                    task_name = extract_task_name_day(filename)
                    if task_name and task_name in task_day_map and task_day_map[task_name] == day:
                        src_path = os.path.join(day_src_dir, filename)
                        dest_path = os.path.join(dest_root, day, task_name, "statements", filename)
                        safe_copy(src_path, dest_path)
                        processed_tasks.add((day, task_name))
                    else:
                        print(f"Warning: Could not map statement file {filename} in {day} or map mismatch.")

    # Day 0 (Practice)
    practice_src_dir = os.path.join(source_root, "other_materials", "Practice")
    day0 = "day0"
    if os.path.isdir(practice_src_dir):
        for filename in os.listdir(practice_src_dir):
            if filename.endswith(".pdf"):
                task_name = extract_task_name_other(filename)
                if task_name and task_name in task_day_map and task_day_map[task_name] == day0:
                    src_path = os.path.join(practice_src_dir, filename)
                    dest_path = os.path.join(dest_root, day0, task_name, "statements", filename)
                    safe_copy(src_path, dest_path)
                    processed_tasks.add((day0, task_name))
                else:
                     print(f"Warning: Could not map practice statement file {filename} or map mismatch.")


    # --- 2. Process Solution Editorials (PDFs) ---
    print("\n--- Processing Solution Editorials (PDFs) ---")
    solutions_src_dir = os.path.join(source_root, "other_materials", "Solutions")
    if os.path.isdir(solutions_src_dir):
        for filename in os.listdir(solutions_src_dir):
            if filename.endswith(".pdf"):
                task_name = extract_task_name_other(filename)
                if task_name in task_day_map:
                    day = task_day_map[task_name]
                    src_path = os.path.join(solutions_src_dir, filename)
                    dest_path = os.path.join(dest_root, day, task_name, "solutions", "editorial", filename)
                    safe_copy(src_path, dest_path)
                    # Ensure this task is marked as processed even if statement wasn't found
                    if (day, task_name) not in processed_tasks:
                       processed_tasks.add((day, task_name))
                else:
                    print(f"Warning: Could not map solution PDF {filename} to a known task/day.")
    else:
        print(f"Warning: Solutions directory not found at {solutions_src_dir}")

    # --- 3. Process TestCases (Tests and Graders) ---
    print("\n--- Processing Tests and Graders ---")
    testcases_base_dir = os.path.join(source_root, "other_materials", "TestCases")
    if os.path.isdir(testcases_base_dir):
        for task_name_case in os.listdir(testcases_base_dir):
            task_src_dir = os.path.join(testcases_base_dir, task_name_case)
            if os.path.isdir(task_src_dir):
                task_name = task_name_case.lower() # Normalize to lowercase
                if task_name in task_day_map:
                    day = task_day_map[task_name]

                    # Process Tests
                    tests_src = os.path.join(task_src_dir, "tests")
                    if os.path.isdir(tests_src):
                        tests_dest = os.path.join(dest_root, day, task_name, "tests")
                        safe_copy(tests_src, tests_dest)
                    else:
                         print(f"Warning: Tests directory not found for task {task_name} at {tests_src}")

                    # Process Graders
                    graders_src = os.path.join(task_src_dir, "graders")
                    if os.path.isdir(graders_src):
                        graders_dest = os.path.join(dest_root, day, task_name, "graders")
                        safe_copy(graders_src, graders_dest)
                    else:
                         print(f"Warning: Graders directory not found for task {task_name} at {graders_src}")

                    # Ensure this task is marked as processed
                    if (day, task_name) not in processed_tasks:
                       processed_tasks.add((day, task_name))
                else:
                    print(f"Warning: Test case folder {task_name_case} does not map to a known task/day.")
    else:
        print(f"Warning: TestCases directory not found at {testcases_base_dir}")


    # --- 4. Create Standard Empty Folders ---
    print("\n--- Creating standard empty folders ---")
    standard_folders = [
        "checkers",
        "attachments",
        "solutions/Codes",
        # "subtasks" # Not creating this as file structure, subtasks are within tests
        # "solutions/editorial" # Created when copying PDFs
        # "statements" # Created when copying PDFs
        # "graders" # Created when copying graders
        # "tests" # Created when copying tests
    ]
    for day, task_name in processed_tasks:
        task_base_dir = os.path.join(dest_root, day, task_name)
        os.makedirs(task_base_dir, exist_ok=True) # Ensure base task dir exists
        for folder in standard_folders:
            folder_path = os.path.join(task_base_dir, *folder.split('/'))
            if not os.path.exists(folder_path):
                 os.makedirs(folder_path, exist_ok=True)
                 print(f"Created standard folder: {folder_path}")

    # --- 5. Handle potential overall editorial ---
    # Check if Solutions.zip contains a general PDF, or if there are other top-level PDFs.
    # For this specific structure, there isn't an obvious overall editorial file.
    # Create the top-level editorial folder anyway for consistency.
    overall_editorial_dir = os.path.join(dest_root, "editorial")
    if not os.path.exists(overall_editorial_dir):
        os.makedirs(overall_editorial_dir, exist_ok=True)
        print(f"Created overall editorial directory: {overall_editorial_dir}")

    print("\n--- Processing Complete ---")
    print(f"Data processed and saved to: {dest_root}")
    print(f"Processed tasks: {len(processed_tasks)}")

if __name__ == "__main__":
    main()