import os
import shutil
import re
from pathlib import Path

def safe_copy(src, dst):
    """Safely copies a file from src to dst, creating parent directories if needed."""
    try:
        if not src.exists():
            print(f"Warning: Source file not found: {src}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"Copied file: {src} -> {dst}")
    except Exception as e:
        print(f"Error copying file {src} to {dst}: {e}")

def safe_copy_tree(src, dst):
    """Safely copies a directory tree from src to dst, creating parent directories if needed."""
    try:
        if not src.exists() or not src.is_dir():
            print(f"Warning: Source directory not found or not a directory: {src}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Use copytree, ensuring destination doesn't already exist in a way that conflicts
        # If dst exists as a file, remove it. If it exists as a dir, copy into it.
        if dst.is_file():
            dst.unlink()
        # shutil.copytree might complain if dst exists, dirs_exist_ok=True helps
        shutil.copytree(src, dst, dirs_exist_ok=True)
        # print(f"Copied directory: {src} -> {dst}")
    except Exception as e:
        print(f"Error copying directory {src} to {dst}: {e}")

def find_statement_pdf(directory, pattern):
    """Finds a PDF file in a directory matching a regex pattern."""
    try:
        for item in directory.iterdir():
            if item.is_file() and item.suffix.lower() == '.pdf' and re.search(pattern, item.name, re.IGNORECASE):
                return item
    except FileNotFoundError:
        print(f"Warning: Statement directory not found: {directory}")
    return None


# --- Configuration ---
INPUT_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2022")
OUTPUT_BASE_DIR = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed")
YEAR = "2022"

# --- Main Execution ---
output_year_dir = OUTPUT_BASE_DIR / YEAR
input_year_dir = INPUT_BASE_DIR

print(f"Processing IOI {YEAR}")
print(f"Input directory: {input_year_dir}")
print(f"Output directory: {output_year_dir}")

# Create base output directory for the year
output_year_dir.mkdir(parents=True, exist_ok=True)

# --- Global Editorial/Materials ---
print("\nProcessing global materials...")
global_editorial_dir = output_year_dir / "editorial"
global_editorial_dir.mkdir(parents=True, exist_ok=True)

# Copy Solutions.zip (potential overall editorials)
solutions_zip_src = input_year_dir / "other_materials" / "Solutions.zip"
safe_copy(solutions_zip_src, global_editorial_dir / solutions_zip_src.name)

# Copy notice files
testcases_dir = input_year_dir / "TestCases"
if testcases_dir.exists():
    for notice_file in testcases_dir.glob("notice-*.pdf"):
        safe_copy(notice_file, global_editorial_dir / notice_file.name)
else:
     print(f"Warning: Directory not found {testcases_dir}")


# --- Process Practice (Day 0) ---
print("\nProcessing Day 0 (Practice)...")
day0_str = "day0"
practice_base_src = input_year_dir / "other_materials" / "Practice"
practice_tasks_src = practice_base_src / "tests"
day0_output_dir = output_year_dir / day0_str

if practice_base_src.exists() and practice_tasks_src.exists():
    practice_tasks = [d.name for d in practice_tasks_src.iterdir() if d.is_dir()]
    print(f"Found practice tasks: {practice_tasks}")

    for task_name in practice_tasks:
        print(f"  Processing task: {task_name}")
        task_output_dir = day0_output_dir / task_name
        task_src_dir = practice_tasks_src / task_name

        # Create standard directories
        statements_dir = task_output_dir / "statements"
        graders_dir = task_output_dir / "graders"
        checkers_dir = task_output_dir / "checkers"
        tests_dir = task_output_dir / "tests"
        attachments_dir = task_output_dir / "attachments"
        solutions_dir = task_output_dir / "solutions"
        solutions_codes_dir = solutions_dir / "Codes"
        solutions_editorial_dir = solutions_dir / "editorial"
        subtasks_dir = task_output_dir / "subtasks"

        statements_dir.mkdir(parents=True, exist_ok=True)
        graders_dir.mkdir(parents=True, exist_ok=True)
        # Checkers might not exist
        tests_dir.mkdir(parents=True, exist_ok=True)
        attachments_dir.mkdir(parents=True, exist_ok=True)
        solutions_codes_dir.mkdir(parents=True, exist_ok=True)
        solutions_editorial_dir.mkdir(parents=True, exist_ok=True) # Create even if empty
        subtasks_dir.mkdir(parents=True, exist_ok=True)

        # 1. Statements
        # Statement names seem to be like <task_name>-en_ISC.pdf in other_materials/Practice/
        statement_pdf_src = practice_base_src / f"{task_name}-en_ISC.pdf"
        if statement_pdf_src.exists():
            safe_copy(statement_pdf_src, statements_dir / statement_pdf_src.name)
        else:
            print(f"Warning: Practice statement PDF not found: {statement_pdf_src}")

        # 2. Graders
        graders_src = task_src_dir / "graders"
        if graders_src.exists():
            safe_copy_tree(graders_src, graders_dir)

        # 3. Checkers (if exists)
        checkers_src = task_src_dir / "checker"
        if checkers_src.exists():
            checkers_dir.mkdir(parents=True, exist_ok=True) # Ensure checker dir exists
            safe_copy_tree(checkers_src, checkers_dir)

        # 4. Tests
        tests_src = task_src_dir / "tests"
        if tests_src.exists():
            safe_copy_tree(tests_src, tests_dir)

        # 5. Attachments
        attachments_src = task_src_dir / "attachments"
        if attachments_src.exists():
            safe_copy_tree(attachments_src, attachments_dir)

        # 6. Solutions (Codes) - Copy the whole original solutions folder
        solutions_src = task_src_dir / "solutions"
        if solutions_src.exists():
             safe_copy_tree(solutions_src, solutions_codes_dir)
        # 6b. Solutions (Editorial) - Folder created, look for specific files if known

        # 7. Subtasks
        subtasks_src = task_src_dir / "subtasks"
        if subtasks_src.exists():
            safe_copy_tree(subtasks_src, subtasks_dir)

        # 8. problem.json
        problem_json_src = task_src_dir / "problem.json"
        safe_copy(problem_json_src, task_output_dir / "problem.json")

else:
    print(f"Warning: Practice source directory not found: {practice_base_src} or {practice_tasks_src}")


# --- Process Competition Days (Day 1, Day 2) ---

# Map PDF statement patterns to task folder names used in TestCases/Solutions
# Based on PDF names and folder structure inspection
task_mapping = {
    "day1": [
        ("Catfish_Farm", "fish"),
        ("Prisoner_Challenge", "prison"),
        ("Radio_Towers", "towers"),
    ],
    "day2": [
        ("Digital_Circuit", "circuit"),
        ("Rarest_Insects", "insects"),
        ("Thousands_Islands", "islands"),
    ]
}

# Source directory for competition task materials (graders, tests, solutions etc.)
# Note: Solutions are duplicated in top-level Solutions/ and TestCases/<task>/solutions/.
# We'll consistently use the TestCases/ version.
materials_base_src = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2022/other_materials/TestCases")

for day_num in [1, 2]:
    day_str = f"day{day_num}"
    print(f"\nProcessing {day_str.capitalize()}...")
    day_output_dir = output_year_dir / day_str
    statements_src_dir = input_year_dir / day_str # e.g., 2022/day1/

    if not os.path.exists(statements_src_dir):
        print(f"Warning: Statement directory not found: {statements_src_dir}")
        continue

    if not os.path.exists(materials_base_src):
        print(f"Warning: Materials source directory not found: {materials_base_src}")
        continue

    tasks = task_mapping.get(day_str, [])
    print(f"Tasks for {day_str}: {[(p, t) for p, t in tasks]}")

    for pdf_pattern, task_name in tasks:
        print(f"  Processing task: {task_name}")
        task_output_dir = day_output_dir / task_name
        task_materials_src_dir = materials_base_src / task_name

        # Create standard directories
        statements_dir = task_output_dir / "statements"
        graders_dir = task_output_dir / "graders"
        checkers_dir = task_output_dir / "checkers"
        tests_dir = task_output_dir / "tests"
        attachments_dir = task_output_dir / "attachments"
        solutions_dir = task_output_dir / "solutions"
        solutions_codes_dir = solutions_dir / "Codes"
        solutions_editorial_dir = solutions_dir / "editorial"
        subtasks_dir = task_output_dir / "subtasks"

        statements_dir.mkdir(parents=True, exist_ok=True)
        graders_dir.mkdir(parents=True, exist_ok=True)
        # Checkers might not exist
        tests_dir.mkdir(parents=True, exist_ok=True)
        attachments_dir.mkdir(parents=True, exist_ok=True)
        solutions_codes_dir.mkdir(parents=True, exist_ok=True)
        solutions_editorial_dir.mkdir(parents=True, exist_ok=True) # Create even if empty
        subtasks_dir.mkdir(parents=True, exist_ok=True)

        # 1. Statements
        statement_pdf_src = find_statement_pdf(statements_src_dir, pdf_pattern)
        if statement_pdf_src:
            safe_copy(statement_pdf_src, statements_dir / statement_pdf_src.name)
        else:
            print(f"Warning: Statement PDF not found for pattern '{pdf_pattern}' in {statements_src_dir}")

        # Check if the task materials source directory exists
        if not task_materials_src_dir.exists():
             print(f"Warning: Task materials directory not found: {task_materials_src_dir}. Skipping materials copy for {task_name}.")
             continue

        # 2. Graders
        graders_src = task_materials_src_dir / "graders"
        if graders_src.exists():
            safe_copy_tree(graders_src, graders_dir)

        # 3. Checkers (if exists)
        checkers_src = task_materials_src_dir / "checker"
        if checkers_src.exists():
            checkers_dir.mkdir(parents=True, exist_ok=True) # Ensure checker dir exists
            safe_copy_tree(checkers_src, checkers_dir)

        # 4. Tests
        tests_src = task_materials_src_dir / "tests"
        if tests_src.exists():
            safe_copy_tree(tests_src, tests_dir)

        # 5. Attachments
        attachments_src = task_materials_src_dir / "attachments"
        if attachments_src.exists():
            safe_copy_tree(attachments_src, attachments_dir)

        # 6. Solutions (Codes) - Copy the whole original solutions folder from TestCases/<task>/solutions
        solutions_src = task_materials_src_dir / "solutions"
        if solutions_src.exists():
             safe_copy_tree(solutions_src, solutions_codes_dir)
        # 6b. Solutions (Editorial) - Folder created, look for specific files if known

        # 7. Subtasks
        subtasks_src = task_materials_src_dir / "subtasks"
        if subtasks_src.exists():
            safe_copy_tree(subtasks_src, subtasks_dir)

        # 8. problem.json
        problem_json_src = task_materials_src_dir / "problem.json"
        safe_copy(problem_json_src, task_output_dir / "problem.json")

print(f"\nProcessing complete for IOI {YEAR}.")
print(f"Output saved to: {output_year_dir}")