import os
import shutil
import glob
import json

def copy_files(src_pattern, dest_dir, desc):
    """
    Copies files matching a glob pattern to a destination directory.
    Creates the destination directory if it doesn't exist.
    """
    try:
        os.makedirs(dest_dir, exist_ok=True)
        files_copied_count = 0
        for src_path in glob.glob(src_pattern):
            if os.path.isfile(src_path):
                try:
                    shutil.copy2(src_path, dest_dir)
                    files_copied_count += 1
                    # print(f"  Copied: {os.path.basename(src_path)} to {dest_dir}")
                except Exception as e:
                    print(f"  Error copying file {src_path} to {dest_dir}: {e}")
            elif os.path.isdir(src_path):
                # If the pattern matches a directory, copy its contents recursively
                dest_subdir = os.path.join(dest_dir, os.path.basename(src_path))
                copy_dir_contents(src_path, dest_subdir, f"{desc} subdir {os.path.basename(src_path)}")
                files_copied_count +=1 # Count the directory as one item copied at this level

        if files_copied_count > 0:
             print(f"  Copied {files_copied_count} item(s) for {desc} matching {os.path.basename(src_pattern)} to {dest_dir}")
        # else:
        #      print(f"  No files found for {desc} matching {src_pattern}")

    except Exception as e:
        print(f"  Error processing pattern {src_pattern} for {desc}: {e}")

def copy_dir_contents(src_dir, dest_dir, desc):
    """
    Copies all contents (files and subdirectories) of src_dir to dest_dir.
    Creates the destination directory if it doesn't exist.
    Uses copy2 for files to preserve metadata.
    Handles existing destination directory by copying contents into it.
    """
    if not os.path.isdir(src_dir):
        # print(f"  Source directory for {desc} not found: {src_dir}")
        return

    try:
        os.makedirs(dest_dir, exist_ok=True)
        items_copied_count = 0
        for item_name in os.listdir(src_dir):
            src_item = os.path.join(src_dir, item_name)
            dest_item = os.path.join(dest_dir, item_name)
            try:
                if os.path.isdir(src_item):
                    # Recursively copy subdirectories using copytree
                    shutil.copytree(src_item, dest_item, copy_function=shutil.copy2, dirs_exist_ok=True)
                elif os.path.isfile(src_item):
                     # Copy files using copy2
                    shutil.copy2(src_item, dest_item)
                else:
                    # print(f"  Skipping non-file/non-dir item: {src_item}")
                    continue # Skip sockets, links, etc.
                items_copied_count += 1
                # print(f"  Copied: {item_name} to {dest_dir}")
            except Exception as e:
                print(f"  Error copying item {src_item} to {dest_item}: {e}")

        if items_copied_count > 0:
            print(f"  Copied {items_copied_count} item(s) for {desc} from {src_dir} to {dest_dir}")
        # else:
        #     print(f"  Source directory for {desc} was empty: {src_dir}")

    except Exception as e:
        print(f"  Error copying directory contents for {desc} from {src_dir} to {dest_dir}: {e}")


def copy_attachments(src_public_dir, dest_attach_dir):
    """
    Copies attachments from the public directory, excluding 'examples' and 'tests'.
    """
    if not os.path.isdir(src_public_dir):
        # print(f"  Public directory not found: {src_public_dir}")
        return

    try:
        os.makedirs(dest_attach_dir, exist_ok=True)
        items_copied_count = 0
        for item_name in os.listdir(src_public_dir):
            src_item = os.path.join(src_public_dir, item_name)
            dest_item = os.path.join(dest_attach_dir, item_name)

            # Skip the specific subdirectories meant for tests/examples
            if item_name in ['examples', 'tests']:
                continue

            try:
                if os.path.isdir(src_item):
                    shutil.copytree(src_item, dest_item, copy_function=shutil.copy2, dirs_exist_ok=True)
                elif os.path.isfile(src_item):
                    shutil.copy2(src_item, dest_item)
                else:
                    # print(f"  Skipping non-file/non-dir attachment item: {src_item}")
                    continue
                items_copied_count += 1
                # print(f"  Copied attachment: {item_name} to {dest_attach_dir}")
            except Exception as e:
                print(f"  Error copying attachment item {src_item} to {dest_item}: {e}")

        if items_copied_count > 0:
            print(f"  Copied {items_copied_count} attachment item(s) from {src_public_dir} to {dest_attach_dir}")
        # else:
        #     print(f"  No attachment items found in {src_public_dir} (excluding examples/tests)")

    except Exception as e:
        print(f"  Error copying attachments from {src_public_dir}: {e}")


# --- Configuration ---
SOURCE_ROOT = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2017"  # Adjust this path
TARGET_ROOT = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed" # Adjust this path
YEAR = "2017"

# Define task names and their corresponding days
# Based on the day1/ day2/ folders in the source structure
TASK_MAP = {
    "nowruz": {"day": 1, "src_name": "nowruz"},
    "wiring": {"day": 1, "src_name": "wiring"},
    "train": {"day": 1, "src_name": "train"},
    "prize": {"day": 2, "src_name": "prize"},
    "simurgh": {"day": 2, "src_name": "simurgh"},
    "books": {"day": 2, "src_name": "books"},
}

PRACTICE_TASKS = ["mountains", "cup", "coins", "sudoku", "notice"]

# --- Main Processing Logic ---
target_year_dir = os.path.join(TARGET_ROOT, YEAR)
source_base_dir = os.path.join(SOURCE_ROOT) # Adjusted to match provided structure

# Create the base directory for the year
os.makedirs(target_year_dir, exist_ok=True)
print(f"Created base directory: {target_year_dir}")

# --- Process Competition Tasks ---
print("\nProcessing Competition Tasks...")
source_testcases_dir = os.path.join(source_base_dir, "other_materials", "TestCases") # Use the unzipped version

if not os.path.isdir(source_testcases_dir):
    print(f"ERROR: Competition task source directory not found: {source_testcases_dir}")
else:
    for task_name, info in TASK_MAP.items():
        day = info["day"]
        src_task_name = info["src_name"]
        print(f"\nProcessing Task: {task_name} (Day {day})")

        src_task_dir = os.path.join(source_testcases_dir, src_task_name)
        target_task_dir = os.path.join(target_year_dir, f"day{day}", task_name)

        if not os.path.isdir(src_task_dir):
            print(f"  WARNING: Source directory for task {task_name} not found: {src_task_dir}")
            continue

        # Create target directory for the task
        os.makedirs(target_task_dir, exist_ok=True)

        # 1. Statements
        target_statements_dir = os.path.join(target_task_dir, "statements")
        src_statement_dir = os.path.join(src_task_dir, "statement")
        copy_dir_contents(src_statement_dir, target_statements_dir, "Statements")
        # Fallback: Check day folders for PDFs if statement dir is empty/missing PDF
        if not glob.glob(os.path.join(target_statements_dir, "*.pdf")):
             print(f"  Note: No PDF found in {src_statement_dir}. Checking day folders.")
             day_pdf_pattern = os.path.join(source_base_dir, f"day{day}", f"*{task_name}*.pdf")
             copy_files(day_pdf_pattern, target_statements_dir, "Statements (from day folder)")


        # 2. Graders
        target_graders_dir = os.path.join(target_task_dir, "graders")
        src_grader_dir = os.path.join(src_task_dir, "grader")
        if os.path.isdir(src_grader_dir):
            copy_dir_contents(src_grader_dir, target_graders_dir, "Graders")
        else:
            print(f"  No grader directory found for {task_name}")

        # 3. Checkers
        target_checkers_dir = os.path.join(target_task_dir, "checkers")
        src_checker_dir = os.path.join(src_task_dir, "checker")
        if os.path.isdir(src_checker_dir):
             copy_dir_contents(src_checker_dir, target_checkers_dir, "Checkers")
        else:
            print(f"  No checker directory found for {task_name}")

        # 4. Tests
        target_tests_dir = os.path.join(target_task_dir, "tests")
        os.makedirs(target_tests_dir, exist_ok=True)
        # Copy main tests first
        src_tests_dir = os.path.join(src_task_dir, "tests")
        copy_dir_contents(src_tests_dir, target_tests_dir, "Main Tests")
        # Copy public examples (often contains sample .in/.out)
        src_examples_dir = os.path.join(src_task_dir, "public", "examples")
        copy_dir_contents(src_examples_dir, target_tests_dir, "Example Tests")
        # Copy public tests inputs (if any exist separately)
        src_public_tests_dir = os.path.join(src_task_dir, "public", "tests")
        copy_dir_contents(src_public_tests_dir, target_tests_dir, "Public Tests")


        # 5. Attachments (Public files excluding examples/tests)
        target_attachments_dir = os.path.join(target_task_dir, "attachments")
        src_public_dir = os.path.join(src_task_dir, "public")
        copy_attachments(src_public_dir, target_attachments_dir)

        # 6. Solutions (Code)
        target_solutions_code_dir = os.path.join(target_task_dir, "solutions", "Codes")
        src_solution_dir = os.path.join(src_task_dir, "solution")
        copy_dir_contents(src_solution_dir, target_solutions_code_dir, "Solution Codes")

        # 7. Solutions (Editorial)
        target_solutions_editorial_dir = os.path.join(target_task_dir, "solutions", "editorial")
        src_editorial_dir = os.path.join(src_task_dir, "editorial")
        copy_dir_contents(src_editorial_dir, target_solutions_editorial_dir, "Task Editorial")
        # Check for general solution PDF as fallback/supplement if task editorial is missing PDF
        if not glob.glob(os.path.join(target_solutions_editorial_dir, "*.pdf")):
             print(f"  Note: No PDF found in {src_editorial_dir}. Checking general Solutions folder.")
             general_sol_pdf_path = os.path.join(source_base_dir, "Solutions", f"{src_task_name}.pdf")
             if os.path.exists(general_sol_pdf_path):
                 copy_files(general_sol_pdf_path, target_solutions_editorial_dir, "Editorial PDF (from Solutions folder)")
             else:
                 print(f"  No general solution PDF found at {general_sol_pdf_path}")


        # 8. Subtasks JSON
        target_subtasks_dir = os.path.join(target_task_dir, "subtasks")
        src_subtasks_json = os.path.join(src_task_dir, "subtasks.json")
        if os.path.isfile(src_subtasks_json):
             copy_files(src_subtasks_json, target_subtasks_dir, "Subtasks JSON")
        else:
             print(f"  subtasks.json not found for {task_name}")


        # 9. Problem JSON
        src_problem_json = os.path.join(src_task_dir, "problem.json")
        if os.path.isfile(src_problem_json):
            copy_files(src_problem_json, target_task_dir, "Problem JSON")
        else:
            print(f"  problem.json not found for {task_name}")


# --- Process Practice Tasks ---
print("\nProcessing Practice Tasks (Day 0)...")
source_practice_dir = os.path.join(source_base_dir,"other_materials", "Practice") # Use the unzipped version

if not os.path.isdir(source_practice_dir):
    print(f"ERROR: Practice task source directory not found: {source_practice_dir}")
else:
    for task_name in PRACTICE_TASKS:
        print(f"\nProcessing Practice Task: {task_name}")

        target_task_dir = os.path.join(target_year_dir, "day0", task_name)
        os.makedirs(target_task_dir, exist_ok=True)

        # 1. Statements (only PDFs seem available)
        target_statements_dir = os.path.join(target_task_dir, "statements")
        src_pdf_path = os.path.join(source_practice_dir, f"{task_name}.pdf")
        if os.path.isfile(src_pdf_path):
             copy_files(src_pdf_path, target_statements_dir, f"{task_name} Statement PDF")
        else:
             print(f"  WARNING: Statement PDF not found for practice task {task_name}: {src_pdf_path}")

        # Print notes about missing components for practice tasks
        print(f"  Note: Tests, Solutions, Graders, Checkers, Attachments are typically not provided in this structure for practice tasks.")
        # Create empty placeholder directories as per the target structure
        os.makedirs(os.path.join(target_task_dir, "graders"), exist_ok=True)
        os.makedirs(os.path.join(target_task_dir, "checkers"), exist_ok=True)
        os.makedirs(os.path.join(target_task_dir, "tests"), exist_ok=True)
        os.makedirs(os.path.join(target_task_dir, "attachments"), exist_ok=True)
        os.makedirs(os.path.join(target_task_dir, "solutions", "Codes"), exist_ok=True)
        os.makedirs(os.path.join(target_task_dir, "solutions", "editorial"), exist_ok=True)
        os.makedirs(os.path.join(target_task_dir, "subtasks"), exist_ok=True)


# --- Process General Editorial (Optional) ---
# The request asks for task-specific editorials first.
# The Solutions/*.pdf seem task-specific based on names.
# We've already tried to copy them into task folders as fallbacks.
# So, we might not need a top-level editorial folder, or it might remain empty.
target_general_editorial_dir = os.path.join(target_year_dir, "editorial")
# Create it just in case, although likely empty based on source structure analysis
os.makedirs(target_general_editorial_dir, exist_ok=True)
print("\nChecked for general editorial materials (Top-level editorial folder created if needed).")

print("\nProcessing complete.")