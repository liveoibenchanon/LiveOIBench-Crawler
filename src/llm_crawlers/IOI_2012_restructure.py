import os
import shutil
import re
from pathlib import Path

# Define base paths
SRC_BASE = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2012")
DST_BASE = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/")

# Define the year
YEAR = "2012"

# Define the target base directory for the year
DST_YEAR_BASE = DST_BASE / YEAR

# --- Helper Function ---
def copy_file(src_path: Path, dst_dir: Path, dst_filename: str = None):
    """Copies a file to a destination directory, creating it if necessary."""
    if not src_path.exists():
        print(f"Warning: Source file not found: {src_path}")
        return
    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst_path = dst_dir / (dst_filename if dst_filename else src_path.name)
        shutil.copy2(src_path, dst_path)
        # print(f"Copied: {src_path} -> {dst_path}")
    except Exception as e:
        print(f"Error copying {src_path} to {dst_dir}: {e}")

def copy_directory(src_path: Path, dst_dir: Path, dst_dirname: str = None):
    """Copies a directory recursively to a destination."""
    if not src_path.exists() or not src_path.is_dir():
        print(f"Warning: Source directory not found or not a directory: {src_path}")
        return
    try:
        dst_path = dst_dir / (dst_dirname if dst_dirname else src_path.name)
        # Remove destination if it exists to avoid merging issues with copytree
        if dst_path.exists():
            shutil.rmtree(dst_path)
        shutil.copytree(src_path, dst_path, copy_function=shutil.copy2)
        # print(f"Copied Directory: {src_path} -> {dst_path}")
    except Exception as e:
        print(f"Error copying directory {src_path} to {dst_dir}: {e}")

# --- Main Processing Logic ---

print(f"Processing IOI {YEAR}...")
DST_YEAR_BASE.mkdir(parents=True, exist_ok=True)

# 1. Process General Editorial/Solutions Booklet
print("\nProcessing General Editorial...")
editorial_src_pdf = SRC_BASE / "other_materials" / "Solutions_to_all_problems.pdf"
editorial_dst_dir = DST_YEAR_BASE / "editorial"
copy_file(editorial_src_pdf, editorial_dst_dir)


# 2. Process Practice Problem (Day 0)
# We need to infer the practice task name or use a placeholder.
# Let's assume 'practice_task' as a placeholder if we can't determine it.
# Based on Practice_problems.pdf, but we don't have its contents.
# Let's check if there's a folder named 'Practice' in 'other_materials/TestCases/'
# The provided structure does *not* show a practice folder under TestCases.
# We will only copy the statement PDF for now into a 'day0' structure.

print("\nProcessing Practice (Day 0)...")
practice_task_name = "practice" # Placeholder name
practice_pdf_src = SRC_BASE / "other_materials" / "Practice_problems.pdf"

if practice_pdf_src.exists():
    day0_dst_base = DST_YEAR_BASE / "day0" / practice_task_name
    statement_dst_dir = day0_dst_base / "statements"
    copy_file(practice_pdf_src, statement_dst_dir, dst_filename=f"{practice_task_name}.pdf")

    # Create other standard directories for consistency, even if empty
    (day0_dst_base / "graders").mkdir(parents=True, exist_ok=True)
    (day0_dst_base / "checkers").mkdir(parents=True, exist_ok=True)
    (day0_dst_base / "tests").mkdir(parents=True, exist_ok=True)
    (day0_dst_base / "attachments").mkdir(parents=True, exist_ok=True)
    (day0_dst_base / "solutions" / "Codes").mkdir(parents=True, exist_ok=True)
    (day0_dst_base / "solutions" / "editorial").mkdir(parents=True, exist_ok=True)
    print(f"Created structure for practice task: {practice_task_name} (Statement only)")
else:
    print("Practice problem PDF not found, skipping Day 0 creation.")


# 3. Process Contest Days (Day 1, Day 2)
print("\nProcessing Contest Days...")
for day in ["day1", "day2"]:
    print(f"\n--- Processing {day} ---")
    day_num = day[-1] # '1' or '2'
    day_src_pdf_dir = SRC_BASE / day
    day_src_data_dir = SRC_BASE / "other_materials" / "TestCases" / day
    day_dst_base = DST_YEAR_BASE / f"day{day_num}"

    if not day_src_pdf_dir.exists():
        print(f"Warning: Source PDF directory not found: {day_src_pdf_dir}")
        continue
    if not day_src_data_dir.exists():
         print(f"Warning: Source data directory not found: {day_src_data_dir}")
         continue

    # Find problem statement PDFs to determine task names
    pdf_files = sorted(list(day_src_pdf_dir.glob("*.pdf")))
    task_name_map = {}
    for pdf_file in pdf_files:
        # Extract task name (e.g., "odometer" from "01_Pebbling_odometer.pdf")
        match = re.match(r"\d{2}_.*?_(.*?)\.pdf", pdf_file.name, re.IGNORECASE)
        if match:
            task_name = match.group(1).lower()
            # The folder names in TestCases seem to be the direct task names
            task_folder_name = task_name
            # Handle potential inconsistencies if needed (e.g., city vs ideal_city)
            if task_name == "ideal": # Handle potential partial name from PDF
                 task_folder_name = "city" # Assuming the folder is named 'city'
            elif task_name == "jousting":
                 task_folder_name = "tournament"
            elif task_name == "last":
                task_folder_name = "supper"
            elif task_name == "pebbling":
                task_folder_name = "odometer"
            elif task_name == "crayfish":
                task_folder_name = "scrivener"
            elif task_name == "parachute":
                task_folder_name = "rings"
            else:
                 # Use the extracted name directly if no specific mapping needed
                 task_folder_name = task_name

            task_name_map[task_folder_name] = pdf_file
        else:
            print(f"Warning: Could not extract task name from PDF: {pdf_file.name}")

    # Process each task folder found in the data directory
    for task_folder in day_src_data_dir.iterdir():
        if not task_folder.is_dir():
            continue

        task_name = task_folder.name
        print(f"Processing Task: {task_name}")

        if task_name not in task_name_map:
            print(f"Warning: No matching PDF statement found for task folder: {task_name}")
            # continue # Or decide to process anyway without statement

        task_dst_base = day_dst_base / task_name

        # Define source paths for this task
        task_src_sol = task_folder / "sol"
        task_src_env = task_folder / "env"
        task_src_input = task_folder / "input"
        task_src_output = task_folder / "output"
        task_src_readme = task_folder / "README"


        # Define destination paths
        statement_dst_dir = task_dst_base / "statements"
        graders_dst_dir = task_dst_base / "graders"
        checkers_dst_dir = task_dst_base / "checkers" # Often empty unless checker specifically found
        tests_dst_dir = task_dst_base / "tests"
        attachments_dst_dir = task_dst_base / "attachments"
        solutions_dst_dir = task_dst_base / "solutions"
        solutions_codes_dst_dir = solutions_dst_dir / "Codes"
        solutions_editorial_dst_dir = solutions_dst_dir / "editorial" # Typically empty for individual tasks

        # Create standard directories
        statement_dst_dir.mkdir(parents=True, exist_ok=True)
        graders_dst_dir.mkdir(parents=True, exist_ok=True)
        checkers_dst_dir.mkdir(parents=True, exist_ok=True)
        tests_dst_dir.mkdir(parents=True, exist_ok=True)
        attachments_dst_dir.mkdir(parents=True, exist_ok=True)
        solutions_codes_dst_dir.mkdir(parents=True, exist_ok=True)
        solutions_editorial_dst_dir.mkdir(parents=True, exist_ok=True)


        # a) Copy Statement
        if task_name in task_name_map:
             pdf_src_path = task_name_map[task_name]
             copy_file(pdf_src_path, statement_dst_dir, dst_filename=f"{task_name}.pdf")
        else:
             print(f"  - Statement PDF not found for {task_name}")

        # b) Copy Tests (input/output folders)
        print(f"  - Copying tests...")
        copy_directory(task_src_input, tests_dst_dir, dst_dirname="input")
        copy_directory(task_src_output, tests_dst_dir, dst_dirname="output")


        # c) Copy Solutions (sol folder)
        print(f"  - Copying solution codes...")
        copy_directory(task_src_sol, solutions_codes_dst_dir.parent, dst_dirname="Codes") # Copy sol/* into Codes/


        # d) Copy Graders and Attachments from env folder
        print(f"  - Copying graders and attachments...")
        if task_src_env.exists() and task_src_env.is_dir():
            for item in task_src_env.iterdir():
                # Graders
                if item.name.startswith("grader.") or item.name in ["simulator.py", "runner.c"]:
                    copy_file(item, graders_dst_dir)
                # Attachments (Examples, Compile Scripts, Provided Skeletons/Files)
                elif item.name.endswith(".txt") or \
                     item.name.startswith("compile_") or \
                     item.name in ["rings.cpp", "rings.pas", "rings.c", # Provided env files
                                  "scrivener.cpp", "scrivener.pas", "scrivener.c",
                                  "tournament.cpp", "tournament.pas", "tournament.c",
                                  "city.cpp", "city.pas", "city.c"] or \
                     item.is_dir() and item.name == "examples": # Specific examples folder for odometer
                     if item.is_dir():
                         # Copy contents of examples directory
                         for example_item in item.iterdir():
                              copy_file(example_item, attachments_dst_dir)
                     else:
                        copy_file(item, attachments_dst_dir)
                # Specific Supper files (might be graders or attachments depending on role)
                elif task_name == "supper" and item.suffix in ['.cpp', '.c', '.pas', '.py', '.sh']:
                     # Let's cautiously put them in attachments unless clearly a grader
                     if item.name.startswith("grader"):
                          copy_file(item, graders_dst_dir)
                     else: # Treat advisor/assistant etc. as attachments/env files for now
                          copy_file(item, attachments_dst_dir)

                # else:
                    # print(f"    - Skipping env file: {item.name}") # Optional: log skipped files

        # e) Copy top-level README as attachment
        if task_src_readme.exists():
             copy_file(task_src_readme, attachments_dst_dir)

print(f"\nFinished processing IOI {YEAR}.")
print(f"Output structure generated at: {DST_YEAR_BASE}")