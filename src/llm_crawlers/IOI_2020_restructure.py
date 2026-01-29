import os
import shutil
import re

# Define source and target base directories
source_base_dir = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-New/2020'
target_base_dir = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-Processed/2020'

# Mapping from task names (lowercase) to days (0 for practice)
# Determined by looking at day1/, day2/ folders and practice/ folder
task_to_day = {
    # Practice (Day 0) - Extracted from other_materials/Practice/ filenames
    'routers': 0,
    'squares': 0,
    'gift': 0,
    'jelly': 0,
    'notice': 0,
    # Day 1 - Extracted from day1/ filenames
    'plants': 1,
    'supertrees': 1,
    'tickets': 1,
    # Day 2 - Extracted from day2/ filenames
    'biscuits': 2,
    'mushrooms': 2,
    'stations': 2,
}

# Function to safely copy a file
def copy_file(src, dst_dir, dst_filename=None):
    """Copies a file from src to dst_dir. Creates dst_dir if needed."""
    if not os.path.exists(src):
        print(f"Warning: Source file not found: {src}")
        return
    os.makedirs(dst_dir, exist_ok=True)
    dst_path = os.path.join(dst_dir, dst_filename if dst_filename else os.path.basename(src))
    try:
        shutil.copy2(src, dst_path)
        # print(f"Copied: {src} -> {dst_path}")
    except Exception as e:
        print(f"Error copying file {src} to {dst_path}: {e}")

# Function to safely copy a directory
def copy_directory(src, dst, ignore_patterns=None):
    """Copies a directory from src to dst. Creates dst parent if needed."""
    if not os.path.exists(src):
        print(f"Warning: Source directory not found: {src}")
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        ignore = shutil.ignore_patterns(*ignore_patterns) if ignore_patterns else None
        shutil.copytree(src, dst, ignore=ignore, dirs_exist_ok=True)
        # print(f"Copied directory: {src} -> {dst}")
    except Exception as e:
        print(f"Error copying directory {src} to {dst}: {e}")

# Function to copy specific file types from a source directory
def copy_files_by_type(src_dir, dst_dir, extensions):
    """Copies files with specified extensions from src_dir to dst_dir."""
    if not os.path.exists(src_dir):
        # print(f"Warning: Source directory for type copy not found: {src_dir}")
        return
    os.makedirs(dst_dir, exist_ok=True)
    copied_count = 0
    for item in os.listdir(src_dir):
        src_path = os.path.join(src_dir, item)
        if os.path.isfile(src_path) and any(item.lower().endswith(ext) for ext in extensions):
            try:
                shutil.copy2(src_path, os.path.join(dst_dir, item))
                copied_count += 1
            except Exception as e:
                print(f"Error copying file {src_path} to {dst_dir}: {e}")
    # if copied_count > 0:
        # print(f"Copied {copied_count} file(s) of types {extensions} from {src_dir} -> {dst_dir}")


# --- Main Processing Logic ---

print(f"Starting processing for IOI 2020")
print(f"Source: {source_base_dir}")
print(f"Target: {target_base_dir}")

# Create the base target directory
os.makedirs(target_base_dir, exist_ok=True)

# Create a top-level editorial folder (might remain empty if no general editorial found)
# The provided structure doesn't explicitly show a general editorial file/folder
# outside of the zipped Solutions.zip, which we are not extracting here.
general_editorial_dir = os.path.join(target_base_dir, 'editorial')
os.makedirs(general_editorial_dir, exist_ok=True)
print(f"Created general editorial directory (may be empty): {general_editorial_dir}")

# Process each task
for task_name, day in task_to_day.items():
    print(f"\nProcessing Day {day} Task: {task_name}")

    day_str = f"day{day}"
    task_target_base = os.path.join(target_base_dir, day_str, task_name)
    os.makedirs(task_target_base, exist_ok=True)

    # --- Define Source Paths ---
    testcases_task_dir = os.path.join(source_base_dir, 'other_materials', 'TestCases', task_name)
    solutions_task_dir = os.path.join(source_base_dir, 'other_materials', 'Solutions', task_name)
    practice_dir = os.path.join(source_base_dir, 'other_materials', 'Practice')
    day1_dir = os.path.join(source_base_dir, 'day1')
    day2_dir = os.path.join(source_base_dir, 'day2')

    # --- 1. Problem Statements ---
    statements_dir = os.path.join(task_target_base, 'statements')
    os.makedirs(statements_dir, exist_ok=True)
    statement_copied = False

    # Try copying statement directory from TestCases first (HTML/MD)
    src_statement_dir = os.path.join(testcases_task_dir, 'statement')
    if os.path.exists(src_statement_dir):
        copy_directory(src_statement_dir, statements_dir, ignore_patterns=['*.zip', '*.tar', '*.gz']) # Copy HTML/MD and assets
        print(f"Copied statement folder: {src_statement_dir} -> {statements_dir}")
        statement_copied = True
        # Also copy specific statement images if present outside assets
        for item in os.listdir(src_statement_dir):
            if item.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pptx')):
                 copy_file(os.path.join(src_statement_dir, item), statements_dir)


    # Copy PDF statement if available (can be supplemental or primary)
    pdf_found = False
    if day == 0:
        # Practice tasks: Find matching PDF in practice_dir
        pdf_pattern = re.compile(f"practice-{task_name}-.*\.pdf", re.IGNORECASE)
        if os.path.exists(practice_dir):
            for f in os.listdir(practice_dir):
                if pdf_pattern.match(f):
                    copy_file(os.path.join(practice_dir, f), statements_dir)
                    print(f"Copied statement PDF: {f} -> {statements_dir}")
                    pdf_found = True
                    statement_copied = True
                    break
    elif day == 1:
        # Day 1 tasks: Find matching PDF in day1_dir
        pdf_pattern = re.compile(f".*_{task_name}\.pdf", re.IGNORECASE)
        if os.path.exists(day1_dir):
            for f in os.listdir(day1_dir):
                if pdf_pattern.match(f):
                    copy_file(os.path.join(day1_dir, f), statements_dir)
                    print(f"Copied statement PDF: {f} -> {statements_dir}")
                    pdf_found = True
                    statement_copied = True
                    break
    elif day == 2:
        # Day 2 tasks: Find matching PDF in day2_dir
        pdf_pattern = re.compile(f".*_{task_name}\.pdf", re.IGNORECASE)
        if os.path.exists(day2_dir):
            for f in os.listdir(day2_dir):
                 if pdf_pattern.match(f):
                    copy_file(os.path.join(day2_dir, f), statements_dir)
                    print(f"Copied statement PDF: {f} -> {statements_dir}")
                    pdf_found = True
                    statement_copied = True
                    break

    if not statement_copied:
        print(f"Warning: No statement found for task {task_name}")

    # --- 2. Graders ---
    graders_dir = os.path.join(task_target_base, 'graders')
    src_grader_dir = os.path.join(testcases_task_dir, 'grader')
    if os.path.exists(src_grader_dir):
        copy_directory(src_grader_dir, graders_dir, ignore_patterns=['*.o', '__pycache__'])
        print(f"Copied grader folder: {src_grader_dir} -> {graders_dir}")
    else:
        print(f"Info: No primary grader folder found for {task_name} at {src_grader_dir}")
    # Also copy public grader files if they exist (e.g. grader.cpp in public/cpp)
    # src_public_dir = os.path.join(testcases_task_dir, 'public')
    # if os.path.exists(src_public_dir):
    #     for lang_dir in os.listdir(src_public_dir):
    #         lang_path = os.path.join(src_public_dir, lang_dir)
    #         if os.path.isdir(lang_path):
    #              # Look for grader files (e.g., grader.cpp, grader.java)
    #              for f in os.listdir(lang_path):
    #                  if f.startswith('grader.') or f == 'manager' or f.endswith('.h'): # Include headers too
    #                      src_file = os.path.join(lang_path, f)
    #                      target_lang_dir = os.path.join(graders_dir, lang_dir)
    #                      copy_file(src_file, target_lang_dir)
    #                      print(f"Copied public grader/header file: {src_file} -> {target_lang_dir}")


    # --- 3. Checkers ---
    checkers_dir = os.path.join(task_target_base, 'checkers')
    src_checker_dir = os.path.join(testcases_task_dir, 'checker')
    if os.path.exists(src_checker_dir):
        copy_directory(src_checker_dir, checkers_dir, ignore_patterns=['*.o'])
        print(f"Copied checker folder: {src_checker_dir} -> {checkers_dir}")
    else:
         # Check if checker exists in grader folder (common for interactive)
         manager_cpp = os.path.join(src_grader_dir, 'manager.cpp')
         manager_bin = os.path.join(src_grader_dir, 'manager')
         if os.path.exists(manager_cpp) or os.path.exists(manager_bin):
             copy_directory(src_grader_dir, checkers_dir, ignore_patterns=['*.o', 'cpp', 'java', 'py', '__pycache__', 'stub.*']) # Copy only manager related files
             print(f"Copied manager/checker from grader folder: {src_grader_dir} -> {checkers_dir}")
         else:
             print(f"Info: No checker folder found for {task_name} at {src_checker_dir}")

    # --- 4. Tests ---
    tests_dir = os.path.join(task_target_base, 'tests')
    os.makedirs(tests_dir, exist_ok=True)
    # Copy main tests
    src_tests_dir = os.path.join(testcases_task_dir, 'tests')
    copied_tests = False
    if os.path.exists(src_tests_dir):
        copy_files_by_type(src_tests_dir, tests_dir, ['.in', '.out', '.txt'])
        print(f"Copied test files from: {src_tests_dir} -> {tests_dir}")
        copied_tests = True
    # Copy example tests from public/examples
    src_examples_dir = os.path.join(testcases_task_dir, 'public', 'examples')
    if os.path.exists(src_examples_dir):
        copy_files_by_type(src_examples_dir, tests_dir, ['.in', '.out', '.txt'])
        print(f"Copied example files from: {src_examples_dir} -> {tests_dir}")
        copied_tests = True
    if not copied_tests:
         print(f"Warning: No test files found for task {task_name}")


    # --- 5. Attachments ---
    attachments_dir = os.path.join(task_target_base, 'attachments')
    os.makedirs(attachments_dir, exist_ok=True)
    copied_attachments = False
    # Copy contents of public/files
    src_public_files_dir = os.path.join(testcases_task_dir, 'public')
    if os.path.exists(src_public_files_dir):
        copy_directory(src_public_files_dir, attachments_dir)
        print(f"Copied attachments from: {src_public_files_dir} -> {attachments_dir}")
        copied_attachments = True
    # Copy public language-specific template files (e.g., tickets.cpp, mushrooms.py, stub.java)
    src_public_dir = os.path.join(testcases_task_dir, 'public')
    if os.path.exists(src_public_dir):
        for lang_dir_name in os.listdir(src_public_dir):
            lang_path = os.path.join(src_public_dir, lang_dir_name)
            # Check if it's a directory representing a language (cpp, java, py etc.)
            if os.path.isdir(lang_path) and lang_dir_name not in ['examples', 'files']:
                 target_lang_attach_dir = os.path.join(attachments_dir, lang_dir_name)
                 os.makedirs(target_lang_attach_dir, exist_ok=True)
                 # Copy all files except grader.* and compile/run scripts (already handled or not needed as attachment)
                 for item in os.listdir(lang_path):
                      item_path = os.path.join(lang_path, item)
                      if os.path.isfile(item_path) and not item.startswith('grader.') and not item.startswith('compile_') and not item.startswith('run_'):
                           copy_file(item_path, target_lang_attach_dir)
                           copied_attachments = True
                 print(f"Copied attachments from: {lang_path} -> {target_lang_attach_dir}")

    if not copied_attachments:
        print(f"Info: No specific attachments found for task {task_name}")


    # --- 6. Solutions ---
    solutions_dir = os.path.join(task_target_base, 'solutions')
    solutions_codes_dir = os.path.join(solutions_dir, 'Codes')
    solutions_editorial_dir = os.path.join(solutions_dir, 'editorial')
    os.makedirs(solutions_codes_dir, exist_ok=True)
    os.makedirs(solutions_editorial_dir, exist_ok=True)

    # Copy solution codes from other_materials/Solutions/<task>
    if os.path.exists(solutions_task_dir):
        copy_directory(solutions_task_dir, solutions_codes_dir, ignore_patterns=['*.zip', '*.tar', '*.gz'])
        print(f"Copied solution codes: {solutions_task_dir} -> {solutions_codes_dir}")
        # Check for non-code files (potential editorial) in the source solution folder
        for item in os.listdir(solutions_task_dir):
            src_item_path = os.path.join(solutions_task_dir, item)
            if os.path.isfile(src_item_path) and not any(item.lower().endswith(ext) for ext in ['.cpp', '.java', '.py', '.c', '.pas', '.h']):
                 copy_file(src_item_path, solutions_editorial_dir)
                 print(f"Copied potential solution editorial file: {src_item_path} -> {solutions_editorial_dir}")

    else:
        print(f"Warning: Solution codes directory not found: {solutions_task_dir}")


    # --- 7. Subtasks ---
    subtasks_dir = os.path.join(task_target_base, 'subtasks')
    src_subtasks_json = os.path.join(testcases_task_dir, 'subtasks.json')
    if os.path.exists(src_subtasks_json):
        copy_file(src_subtasks_json, subtasks_dir)
        print(f"Copied subtasks file: {src_subtasks_json} -> {subtasks_dir}")
    else:
        print(f"Info: No subtasks.json found for task {task_name}")


    # --- 8. Problem JSON ---
    src_problem_json = os.path.join(testcases_task_dir, 'problem.json')
    if os.path.exists(src_problem_json):
        copy_file(src_problem_json, task_target_base)
        print(f"Copied problem.json: {src_problem_json} -> {task_target_base}")
    else:
        print(f"Info: No problem.json found for task {task_name}")


print("\nProcessing finished.")