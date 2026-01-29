import os
import shutil
import re

# --- Configuration ---
SOURCE_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New"
OUTPUT_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed"
YEAR = "2019"

# --- Helper Functions ---
def safe_copy(src, dst):
    """Safely copies a file, creating destination directory if needed."""
    if not os.path.exists(src):
        print(f"Warning: Source file not found: {src}")
        return
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst) # copy2 preserves metadata
        # print(f"Copied: {src} -> {dst}")
    except Exception as e:
        print(f"Error copying file {src} to {dst}: {e}")

def safe_copy_tree(src, dst):
    """Safely copies a directory tree, creating destination directory if needed."""
    if not os.path.exists(src) or not os.path.isdir(src):
        print(f"Warning: Source directory not found or not a directory: {src}")
        return
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # Ensure the destination *directory* itself exists before copying *into* it
        os.makedirs(dst, exist_ok=True)
        # Use copytree with dirs_exist_ok=True for robustness
        shutil.copytree(src, dst, dirs_exist_ok=True)
        # print(f"Copied Tree: {src} -> {dst}")
    except Exception as e:
        print(f"Error copying directory {src} to {dst}: {e}")

def create_dir(path):
    """Creates a directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)

# --- Main Logic ---
def main():
    source_dir = os.path.join(SOURCE_BASE, YEAR)
    output_dir = os.path.join(OUTPUT_BASE, YEAR)

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory not found: {source_dir}")
        return

    print(f"Starting processing for year {YEAR}...")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")

    create_dir(output_dir)

    # --- Task Identification and Day Mapping ---
    task_to_day = {}
    task_name_map_pdf_to_folder = {
        # Maps PDF base name (without number/ext) to TestCases folder name
        'Arranging_Shoes': 'shoes',
        'Split_the_Attractions': 'split',
        'Rectangles': 'rect',
        'Broken_Line': 'line',
        'Vision_Program': 'vision',
        'Sky_Walking': 'walk'
    }

    # Identify competition tasks and their days
    for day_num in [1, 2]:
        day_folder = f"day{day_num}"
        day_path_src = os.path.join(source_dir, day_folder)
        if os.path.isdir(day_path_src):
            for pdf_file in os.listdir(day_path_src):
                if pdf_file.lower().endswith(".pdf"):
                    # Extract base name like 'Arranging_Shoes'
                    base_name = os.path.splitext(pdf_file)[0]
                    # Remove leading number like '01_' if present
                    match = re.match(r"\d+_(.*)", base_name)
                    if match:
                        pdf_task_key = match.group(1)
                    else:
                         pdf_task_key = base_name # Use as is if no number prefix

                    if pdf_task_key in task_name_map_pdf_to_folder:
                        task_name = task_name_map_pdf_to_folder[pdf_task_key]
                        task_to_day[task_name] = day_folder
                    else:
                        print(f"Warning: Could not map PDF {pdf_file} in {day_folder} to a known task folder.")

    # Identify practice tasks (treat as day0)
    practice_dir_src = os.path.join(source_dir, "other_materials", "Practice")
    if os.path.isdir(practice_dir_src):
        for item in os.listdir(practice_dir_src):
             # Check both PDF files and potential folders if Practice.zip was extracted here
            if item.lower().endswith(".pdf"):
                task_name = os.path.splitext(item)[0].lower() # Use lowercase task name
                if task_name not in task_to_day: # Don't overwrite if already found
                    task_to_day[task_name] = 'day0'
            # Add logic here if practice tasks might have folders too (e.g., from Practice.zip)

    print(f"Identified tasks and days: {task_to_day}")

    # --- Process Each Task ---
    processed_tasks = set()
    testcases_base_src = os.path.join(source_dir, "other_materials", "TestCases")
    solutions_pdf_src = os.path.join(source_dir, "other_materials", "Solutions")

    for task_name, day in task_to_day.items():
        print(f"\nProcessing Task: {task_name} (Day: {day})")
        task_output_root = os.path.join(output_dir, day, task_name)
        create_dir(task_output_root)

        # Define standard output subdirectories
        statements_dir = os.path.join(task_output_root, "statements")
        graders_dir = os.path.join(task_output_root, "graders")
        checkers_dir = os.path.join(task_output_root, "checkers")
        tests_dir = os.path.join(task_output_root, "tests")
        attachments_dir = os.path.join(task_output_root, "attachments")
        solutions_dir = os.path.join(task_output_root, "solutions")
        solutions_codes_dir = os.path.join(solutions_dir, "Codes")
        solutions_editorial_dir = os.path.join(solutions_dir, "editorial")
        subtasks_dir = os.path.join(task_output_root, "subtasks")

        create_dir(statements_dir)
        create_dir(solutions_dir)
        create_dir(solutions_codes_dir)
        create_dir(solutions_editorial_dir)

        # --- Handle Competition Tasks (day1, day2) ---
        if day in ['day1', 'day2']:
            task_source_base = os.path.join(testcases_base_src, task_name)
            if not os.path.isdir(task_source_base):
                 print(f"Warning: Source directory for task '{task_name}' not found at {task_source_base}")
                 continue

            create_dir(graders_dir)
            create_dir(checkers_dir)
            create_dir(tests_dir)
            create_dir(attachments_dir)
            create_dir(subtasks_dir)

            # 1. problem.json
            safe_copy(os.path.join(task_source_base, "problem.json"),
                      os.path.join(task_output_root, "problem.json"))

            # 2. Statements
            # Copy PDF from dayX folder
            found_pdf = False
            day_path_src = os.path.join(source_dir, day)
            if os.path.isdir(day_path_src):
                 for pdf_file in os.listdir(day_path_src):
                     if pdf_file.lower().endswith(".pdf"):
                         base_name = os.path.splitext(pdf_file)[0]
                         match = re.match(r"\d+_(.*)", base_name)
                         pdf_task_key = match.group(1) if match else base_name
                         if pdf_task_key in task_name_map_pdf_to_folder and task_name_map_pdf_to_folder[pdf_task_key] == task_name:
                             safe_copy(os.path.join(day_path_src, pdf_file),
                                       os.path.join(statements_dir, pdf_file))
                             found_pdf = True
                             break
            if not found_pdf:
                 print(f"Warning: Statement PDF for task '{task_name}' not found in {day_path_src}")
            # Copy statement.md
            safe_copy(os.path.join(task_source_base, "statement.md"),
                      os.path.join(statements_dir, f"{task_name}_statement.md"))

            # 3. Graders
            safe_copy_tree(os.path.join(task_source_base, "graders"), graders_dir)

            # 4. Checkers
            safe_copy_tree(os.path.join(task_source_base, "checker"), checkers_dir)

            # 5. Tests
            safe_copy_tree(os.path.join(task_source_base, "tests"), tests_dir)

            # 6. Attachments
            safe_copy_tree(os.path.join(task_source_base, "attachments"), attachments_dir)

            # 7. Solutions (Code) - Copy the entire original solutions folder
            safe_copy_tree(os.path.join(task_source_base, "solutions"), solutions_codes_dir)

            # 8. Solutions (Editorial PDF)
            editorial_pdf_src = os.path.join(solutions_pdf_src, f"{task_name}.pdf")
            safe_copy(editorial_pdf_src,
                      os.path.join(solutions_editorial_dir, f"{task_name}_editorial.pdf"))

            # 9. Subtasks
            safe_copy_tree(os.path.join(task_source_base, "subtasks"), subtasks_dir)

        # --- Handle Practice Tasks (day0) ---
        elif day == 'day0':
             # For practice tasks, primarily copy the statement PDF
             practice_pdf_src = os.path.join(practice_dir_src, f"{task_name}.pdf")
             safe_copy(practice_pdf_src, os.path.join(statements_dir, f"{task_name}.pdf"))
             # Create other standard dirs but leave them empty unless Practice.zip reveals more
             create_dir(graders_dir)
             create_dir(checkers_dir)
             create_dir(tests_dir)
             create_dir(attachments_dir)
             create_dir(subtasks_dir)
             # Optionally, check if Practice.zip exists and contains more details for this task

        processed_tasks.add(task_name)

    # --- Handle General Editorial ---
    general_editorial_dir = os.path.join(output_dir, "editorial")
    create_dir(general_editorial_dir)
    solutions_zip_src = os.path.join(source_dir, "other_materials", "Solutions.zip")
    safe_copy(solutions_zip_src, os.path.join(general_editorial_dir, "Solutions.zip"))

    # --- Final Check ---
    # Verify if all folders in TestCases were processed
    if os.path.isdir(testcases_base_src):
        for item in os.listdir(testcases_base_src):
            item_path = os.path.join(testcases_base_src, item)
            if os.path.isdir(item_path) and item not in processed_tasks:
                print(f"Warning: Task folder '{item}' in TestCases was not processed (missing day mapping?).")

    print(f"\nProcessing for year {YEAR} complete.")
    print(f"Output saved to: {output_dir}")

if __name__ == "__main__":
    main()