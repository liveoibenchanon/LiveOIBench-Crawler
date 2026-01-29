import os
import shutil
import glob

# Define base paths
SOURCE_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2017"
OUTPUT_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
YEAR = "2017"

# Define the target structure components
STATEMENTS_DIR = "statements"
GRADERS_DIR = "graders"
CHECKERS_DIR = "checkers"
TESTS_DIR = "tests"
ATTACHMENTS_DIR = "attachments"
SOLUTIONS_DIR = "solutions"
SOLUTIONS_CODE_DIR = os.path.join(SOLUTIONS_DIR, "Codes")
SOLUTIONS_EDITORIAL_DIR = os.path.join(SOLUTIONS_DIR, "editorial")
SUBTASKS_DIR = "subtasks"

# --- Helper Functions ---

def safe_copy(src, dst):
    """Copies a file from src to dst, creating destination directories if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"  Copied: {src} -> {dst}")
    except FileNotFoundError:
        print(f"  Warning: Source file not found - {src}")
    except Exception as e:
        print(f"  Error copying {src} to {dst}: {e}")

def safe_copy_tree(src, dst):
    """Copies a directory tree from src to dst."""
    try:
        if os.path.exists(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
            # print(f"  Copied Tree: {src} -> {dst}")
        else:
             print(f"  Warning: Source directory not found - {src}")
    except Exception as e:
        print(f"  Error copying directory {src} to {dst}: {e}")

def copy_files_with_extensions(src_dir, dst_dir, extensions):
    """Copies files with specific extensions from src_dir to dst_dir."""
    if not os.path.exists(src_dir):
        # print(f"  Info: Source directory for extension copy not found - {src_dir}")
        return
    os.makedirs(dst_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        src_item_path = os.path.join(src_dir, item)
        if os.path.isfile(src_item_path):
            _, ext = os.path.splitext(item)
            if ext.lower() in extensions:
                safe_copy(src_item_path, os.path.join(dst_dir, item))

# --- Main Processing Logic ---

dest_year_path = os.path.join(OUTPUT_BASE, YEAR)
os.makedirs(dest_year_path, exist_ok=True)
print(f"Processing year {YEAR}...")
print(f"Source: {SOURCE_BASE}")
print(f"Destination: {dest_year_path}")

days = ["day0", "day1", "day2"]

for day in days:
    src_day_path = os.path.join(SOURCE_BASE, day)
    dest_day_path = os.path.join(dest_year_path, day)

    if not os.path.isdir(src_day_path):
        print(f"\nWarning: Source directory for {day} not found: {src_day_path}")
        continue

    print(f"\nProcessing {day}...")
    os.makedirs(dest_day_path, exist_ok=True)

    # --- Identify Tasks ---
    # Tasks usually reside in directories named after the task within the day folder
    # Sometimes they are nested one level deeper (e.g., day1/nowruz/nowruz)
    potential_tasks = [d for d in os.listdir(src_day_path) if os.path.isdir(os.path.join(src_day_path, d))]
    tasks_processed = set() # Avoid double processing if structure varies slightly

    for task_name in potential_tasks:
        # Skip common non-task directories
        if task_name in ["attachments", "all", "editorial"]:
            continue

        # Determine the most likely source task directory path
        src_task_path_nested = os.path.join(src_day_path, task_name, task_name)
        src_task_path_direct = os.path.join(src_day_path, task_name)

        src_task_path = None
        if os.path.exists(os.path.join(src_task_path_nested, "problem.json")) or \
           os.path.exists(os.path.join(src_task_path_nested, "statement")):
             src_task_path = src_task_path_nested
        elif os.path.exists(os.path.join(src_task_path_direct, "problem.json")) or \
             os.path.exists(os.path.join(src_task_path_direct, "statement")):
             src_task_path = src_task_path_direct

        if not src_task_path or not os.path.isdir(src_task_path):
            # print(f"  Skipping potential task '{task_name}': Could not confirm task directory structure.")
            continue

        if task_name in tasks_processed:
            continue
        tasks_processed.add(task_name)

        print(f"  Processing Task: {task_name}")
        dest_task_path = os.path.join(dest_day_path, task_name)
        os.makedirs(dest_task_path, exist_ok=True)

        # --- Create Destination Subdirectories ---
        dest_statements_path = os.path.join(dest_task_path, STATEMENTS_DIR)
        dest_graders_path = os.path.join(dest_task_path, GRADERS_DIR)
        dest_checkers_path = os.path.join(dest_task_path, CHECKERS_DIR)
        dest_tests_path = os.path.join(dest_task_path, TESTS_DIR)
        dest_attachments_path = os.path.join(dest_task_path, ATTACHMENTS_DIR)
        dest_solutions_path = os.path.join(dest_task_path, SOLUTIONS_DIR)
        dest_solutions_code_path = os.path.join(dest_task_path, SOLUTIONS_CODE_DIR)
        dest_solutions_editorial_path = os.path.join(dest_task_path, SOLUTIONS_EDITORIAL_DIR)
        dest_subtasks_path = os.path.join(dest_task_path, SUBTASKS_DIR)

        os.makedirs(dest_statements_path, exist_ok=True)
        os.makedirs(dest_graders_path, exist_ok=True)
        os.makedirs(dest_checkers_path, exist_ok=True)
        os.makedirs(dest_tests_path, exist_ok=True)
        os.makedirs(dest_attachments_path, exist_ok=True)
        os.makedirs(dest_solutions_path, exist_ok=True)
        os.makedirs(dest_solutions_code_path, exist_ok=True)
        os.makedirs(dest_solutions_editorial_path, exist_ok=True)
        os.makedirs(dest_subtasks_path, exist_ok=True)

        # --- 1. Problem Statements ---
        print(f"    Copying Statements...")
        src_statement_path = os.path.join(src_task_path, "statement")
        safe_copy_tree(src_statement_path, dest_statements_path)
        # Also check for PDF statement directly under translations/dayX/taskname.pdf (less common)
        # Note: the prompt structure shows translations/dayX/<taskname>/... , PDFs directly under translations/dayX seem to be collected ones
        # Let's stick to the statement directory for now.

        # --- 2. Graders ---
        print(f"    Copying Graders...")
        # Copy the main grader directory if it exists
        src_grader_path = os.path.join(src_task_path, "grader")
        safe_copy_tree(src_grader_path, dest_graders_path)

        # Copy public grader files/language specific folders
        src_public_path = os.path.join(src_task_path, "public")
        for lang_dir in ["cpp", "pas", "java"]:
            src_lang_path = os.path.join(src_public_path, lang_dir)
            if os.path.isdir(src_lang_path):
                # Copy the entire language folder into graders
                safe_copy_tree(src_lang_path, os.path.join(dest_graders_path, lang_dir))

        # Special handling for day0 attachments structure
        if day == "day0":
             src_day0_attach_task = os.path.join(SOURCE_BASE, "day0", "attachments", task_name)
             for lang_dir in ["cpp", "pas", "java"]:
                 src_lang_path = os.path.join(src_day0_attach_task, lang_dir)
                 if os.path.isdir(src_lang_path):
                    safe_copy_tree(src_lang_path, os.path.join(dest_graders_path, lang_dir))


        # --- 3. Checkers ---
        print(f"    Copying Checkers...")
        src_checker_path = os.path.join(src_task_path, "checker")
        safe_copy_tree(src_checker_path, dest_checkers_path)

        # --- 4. Tests ---
        print(f"    Copying Tests...")
        # Copy main 'tests' directory (usually includes .in/.out or .in/.ans)
        src_tests_main_path = os.path.join(src_task_path, "tests")
        safe_copy_tree(src_tests_main_path, dest_tests_path)

        # Copy public examples (.in/.out)
        src_public_examples_path = os.path.join(src_public_path, "examples")
        safe_copy_tree(src_public_examples_path, dest_tests_path)

        # Copy public tests (.in only usually)
        src_public_tests_path = os.path.join(src_public_path, "tests")
        safe_copy_tree(src_public_tests_path, dest_tests_path)

        # Special handling for day0 attachments structure for examples/tests
        if day == "day0":
             src_day0_attach_task = os.path.join(SOURCE_BASE, "day0", "attachments", task_name)
             src_day0_examples = os.path.join(src_day0_attach_task, "examples")
             src_day0_tests = os.path.join(src_day0_attach_task, "tests")
             safe_copy_tree(src_day0_examples, dest_tests_path)
             safe_copy_tree(src_day0_tests, dest_tests_path)


        # --- 5. Attachments ---
        print(f"    Copying Attachments...")
        # Copy files directly under public/ that are not examples/tests or language dirs
        if os.path.isdir(src_public_path):
            for item in os.listdir(src_public_path):
                src_item = os.path.join(src_public_path, item)
                dest_item = os.path.join(dest_attachments_path, item)
                if item not in ["examples", "tests", "cpp", "pas", "java"]:
                    if os.path.isfile(src_item):
                        safe_copy(src_item, dest_item)
                    elif os.path.isdir(src_item):
                         safe_copy_tree(src_item, dest_item)

        # Special handling for day0 attachments (copy anything not examples/tests/lang)
        if day == "day0":
             src_day0_attach_task = os.path.join(SOURCE_BASE, "day0", "attachments", task_name)
             if os.path.isdir(src_day0_attach_task):
                 for item in os.listdir(src_day0_attach_task):
                     src_item = os.path.join(src_day0_attach_task, item)
                     dest_item = os.path.join(dest_attachments_path, item)
                     if item not in ["examples", "tests", "cpp", "pas", "java"]:
                         if os.path.isfile(src_item):
                             safe_copy(src_item, dest_item)
                         elif os.path.isdir(src_item):
                             safe_copy_tree(src_item, dest_item)


        # --- 6. Solutions ---
        print(f"    Copying Solutions...")
        # Copy solution code
        src_solution_path = os.path.join(src_task_path, "solution")
        safe_copy_tree(src_solution_path, dest_solutions_code_path)

        # Copy editorial content
        src_editorial_path = os.path.join(src_task_path, "editorial")
        safe_copy_tree(src_editorial_path, dest_solutions_editorial_path)
        # Also check for a task PDF in translations/dayX/editorial/
        src_trans_editorial_pdf = os.path.join(SOURCE_BASE, "translations", day, "editorial", f"{task_name}.pdf")
        if os.path.isfile(src_trans_editorial_pdf):
             safe_copy(src_trans_editorial_pdf, os.path.join(dest_solutions_editorial_path, f"{task_name}_translated_editorial.pdf"))


        # --- 7. Subtasks ---
        print(f"    Copying Subtasks...")
        src_subtasks_file = os.path.join(src_task_path, "subtasks.json")
        if os.path.isfile(src_subtasks_file):
            safe_copy(src_subtasks_file, os.path.join(dest_subtasks_path, "subtasks.json"))
        else:
             print(f"      Info: subtasks.json not found for {task_name}")


        # --- 8. Problem JSON ---
        print(f"    Copying problem.json...")
        src_problem_file = os.path.join(src_task_path, "problem.json")
        if os.path.isfile(src_problem_file):
            safe_copy(src_problem_file, os.path.join(dest_task_path, "problem.json"))
        else:
            print(f"      Info: problem.json not found for {task_name}")


    # --- Handle Overall Day Editorials (if any) ---
    print(f"  Checking for overall {day} editorials...")
    dest_overall_editorial_path = os.path.join(dest_year_path, "editorial", day) # Place in year/editorial/<day>
    src_trans_day_editorial_path = os.path.join(SOURCE_BASE, "translations", day, "editorial")
    if os.path.isdir(src_trans_day_editorial_path):
        os.makedirs(dest_overall_editorial_path, exist_ok=True)
        copy_files_with_extensions(src_trans_day_editorial_path, dest_overall_editorial_path, ['.pdf'])
        print(f"    Copied overall PDF editorials from {src_trans_day_editorial_path}")


print("\nProcessing finished.")