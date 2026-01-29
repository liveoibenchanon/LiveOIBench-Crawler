import os
import shutil
import re

# Base paths
source_base = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2018"
dest_base = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/"
year = "2018"

# --- Mappings ---
# Map day folder names and statement PDF prefixes to task folder names used in TestCases
# Also include the full statement PDF name for easier lookup
task_mapping = {
    "day1": [
        {"pdf_prefix": "01_", "pdf_name": "01_Combo.pdf", "task_folder": "combo"},
        {"pdf_prefix": "02_", "pdf_name": "02_Seats.pdf", "task_folder": "seats"},
        {"pdf_prefix": "03_", "pdf_name": "03_Werewolf.pdf", "task_folder": "werewolf"},
    ],
    "day2": [
        {"pdf_prefix": "01_", "pdf_name": "01_Mechanical_Doll.pdf", "task_folder": "doll"},
        {"pdf_prefix": "02_", "pdf_name": "02_Highway_Tolls.pdf", "task_folder": "highway"},
        {"pdf_prefix": "03_", "pdf_name": "03_Meetings.pdf", "task_folder": "meetings"},
    ],
    # Practice tasks are treated as day0, but they lack TestCases folders in the provided structure.
    # We will only process tasks listed in day1/day2 with corresponding TestCases folders.
    # If practice tasks with TestCases were present, they would be added here.
    # "day0": [
    #     {"pdf_name": "xylophone.pdf", "task_folder": "xylophone"}, # Assuming TestCases/xylophone existed
    # ]
}

# --- Helper Functions ---

def safe_copy(src, dst):
    """Safely copies a file, creating destination directories if needed."""
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            shutil.copy2(src, dst) # copy2 preserves metadata
            print(f"  Copied: {src} -> {dst}")
        except Exception as e:
            print(f"  Error copying {src} to {dst}: {e}")
    else:
        print(f"  Source file not found: {src}")

def safe_copytree(src, dst):
    """Safely copies a directory tree, creating destination directories."""
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dst), exist_ok=True) # Ensure parent of dst exists
        try:
            # If dst exists, remove it first to avoid merging issues with copytree
            if os.path.exists(dst):
                 shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"  Copied Tree: {src} -> {dst}")
        except Exception as e:
            print(f"  Error copying tree {src} to {dst}: {e}")
    else:
        print(f"  Source directory not found: {src}")

# --- Main Processing Logic ---

print(f"Starting processing for IOI {year}")
dest_year_dir = os.path.join(dest_base, year)
os.makedirs(dest_year_dir, exist_ok=True)
print(f"Output directory: {dest_year_dir}")

# Paths to source materials
source_day1_dir = os.path.join(source_base, "day1")
source_day2_dir = os.path.join(source_base, "day2")
# source_practice_dir = os.path.join(source_base, "other_materials", "Practice") # Not used due to lack of TestCases
source_solutions_dir = os.path.join(source_base, "other_materials", "Solutions")
source_testcases_base = os.path.join(source_base, "other_materials", "TestCases")

# Process Day 1 and Day 2 tasks
for day, tasks in task_mapping.items():
    print(f"\nProcessing {day}...")
    dest_day_dir = os.path.join(dest_year_dir, day)
    os.makedirs(dest_day_dir, exist_ok=True)
    source_day_dir = os.path.join(source_base, day) # e.g., source_base/day1

    for task_info in tasks:
        task_folder_name = task_info["task_folder"]
        pdf_statement_name = task_info["pdf_name"]
        print(f"\n Processing Task: {task_folder_name}")

        dest_task_dir = os.path.join(dest_day_dir, task_folder_name)
        os.makedirs(dest_task_dir, exist_ok=True)

        # Define destination subdirectories
        dest_statements_dir = os.path.join(dest_task_dir, "statements")
        dest_graders_dir = os.path.join(dest_task_dir, "graders")
        dest_checkers_dir = os.path.join(dest_task_dir, "checkers") # Likely empty
        dest_tests_dir = os.path.join(dest_task_dir, "tests")
        dest_attachments_dir = os.path.join(dest_task_dir, "attachments") # Likely empty
        dest_solutions_dir = os.path.join(dest_task_dir, "solutions")
        dest_solutions_code_dir = os.path.join(dest_solutions_dir, "Codes")
        dest_solutions_editorial_dir = os.path.join(dest_solutions_dir, "editorial")
        dest_subtasks_dir = os.path.join(dest_task_dir, "subtasks") # Likely empty

        # Create all destination directories
        os.makedirs(dest_statements_dir, exist_ok=True)
        os.makedirs(dest_graders_dir, exist_ok=True)
        os.makedirs(dest_checkers_dir, exist_ok=True)
        os.makedirs(dest_tests_dir, exist_ok=True)
        os.makedirs(dest_attachments_dir, exist_ok=True)
        os.makedirs(dest_solutions_dir, exist_ok=True)
        os.makedirs(dest_solutions_code_dir, exist_ok=True)
        os.makedirs(dest_solutions_editorial_dir, exist_ok=True)
        os.makedirs(dest_subtasks_dir, exist_ok=True)

        # 1. Copy Statement PDF
        source_statement_pdf = os.path.join(source_day_dir, pdf_statement_name)
        dest_statement_pdf = os.path.join(dest_statements_dir, pdf_statement_name)
        safe_copy(source_statement_pdf, dest_statement_pdf)

        # 2. Copy Editorial PDF (Review PDF)
        # Construct expected editorial filename (e.g., combo-review.pdf)
        # Handle potential inconsistency like seats-review.pdf vs seat-review.pdf if needed
        editorial_pdf_name = f"{task_folder_name}-review.pdf"
        source_editorial_pdf = os.path.join(source_solutions_dir, editorial_pdf_name)
        # Check alternative naming convention seen in practice section (task_name.pdf)
        # This doesn't seem to apply to the main contest editorials based on the input list.
        if not os.path.exists(source_editorial_pdf):
             print(f"  Editorial file {editorial_pdf_name} not found in {source_solutions_dir}. Skipping editorial copy.")
        else:
            dest_editorial_pdf = os.path.join(dest_solutions_editorial_dir, editorial_pdf_name)
            safe_copy(source_editorial_pdf, dest_editorial_pdf)

        # 3. Process TestCases folder
        source_task_testcases_dir = os.path.join(source_testcases_base, task_folder_name)
        if not os.path.isdir(source_task_testcases_dir):
            print(f"  Warning: TestCases folder not found for {task_folder_name} at {source_task_testcases_dir}. Skipping tests, graders, solutions code.")
            continue # Skip to next task if no TestCases folder

        # 3a. Copy Tests (in/ and out/)
        source_tests_in = os.path.join(source_task_testcases_dir, "in")
        dest_tests_in = os.path.join(dest_tests_dir, "in")
        safe_copytree(source_tests_in, dest_tests_in)

        source_tests_out = os.path.join(source_task_testcases_dir, "out")
        dest_tests_out = os.path.join(dest_tests_dir, "out")
        if os.path.exists(source_tests_out): # Check if 'out' exists
             safe_copytree(source_tests_out, dest_tests_out)
        else:
             print(f"  No 'out' directory found for {task_folder_name}")


        # 3b. Copy Graders and Solution Code Templates (from cpp/, java/, pas/)
        for lang_folder in ["cpp", "java", "pas"]:
            source_lang_dir = os.path.join(source_task_testcases_dir, lang_folder)
            if os.path.isdir(source_lang_dir):
                print(f"  Processing language folder: {lang_folder}")
                # Copy entire language folder to solutions/Codes/
                dest_lang_code_dir = os.path.join(dest_attachments_dir, lang_folder)
                safe_copytree(source_lang_dir, dest_lang_code_dir)

                # Find and copy grader files specifically to graders/
                for item in os.listdir(source_lang_dir):
                    if item.startswith("grader."):
                        src_grader_file = os.path.join(source_lang_dir, item)
                        dst_grader_file = os.path.join(dest_graders_dir, item)
                        safe_copy(src_grader_file, dst_grader_file)
                    # Optionally identify attachments like .h or _lib.pas here if needed,
                    # but they are already included in the solutions/Codes copy.
                    # If specific files should *only* be attachments, copy them here.
                    # Example (copy .h files):
                    # if item.endswith(".h"):
                    #     src_attach_file = os.path.join(source_lang_dir, item)
                    #     dst_attach_file = os.path.join(dest_attachments_dir, item)
                    #     safe_copy(src_attach_file, dst_attach_file)

            else:
                print(f"  Language folder not found: {source_lang_dir}")

        # 4. Checkers - Assumed none separate from graders in this structure
        print(f"  No separate checker files identified for {task_folder_name}.")

        # 5. Attachments - Includes .h, _lib.pas etc. copied with solution codes.
        # Add specific logic here if other files are considered attachments.
        print(f"  Attachments (like headers/libs) included in solutions/Codes/. Check attachments/ if specific non-code files exist.")

        # 6. Subtasks - No subtask information in the provided structure.
        print(f"  No subtask information found to populate subtasks/.")

        # 7. problem.json - Not present in source.
        print(f"  No problem.json found in source.")


# Optional: Handle general materials if needed (e.g., Solution booklet zip)
# source_solutions_zip = os.path.join(source_base, "other_materials", "Solutions.zip")
# dest_editorial_dir = os.path.join(dest_year_dir, "editorial")
# os.makedirs(dest_editorial_dir, exist_ok=True)
# safe_copy(source_solutions_zip, os.path.join(dest_editorial_dir, "Solutions.zip"))
# print(f"\nCopied general Solutions.zip to {dest_editorial_dir}")


print(f"\nProcessing for IOI {year} complete.")
print(f"Output saved to: {dest_year_dir}")