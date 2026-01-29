import os
import shutil
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define base paths
input_base_dir = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2015")
output_base_dir = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2")
output_year_dir = output_base_dir / "2015"

# Define tasks for each day (map day number to list of task names)
# Treat practice day as day 0
tasks_by_day = {
    0: ["divide", "search", "graph"],
    1: ["boxes", "teams", "scales"],
    2: ["horses", "towns", "sorting"]
}

# --- Helper Function ---
def copy_item(src: Path, dst: Path):
    """Copies a file or directory, creating parent directories if needed."""
    try:
        if not src.exists():
            logging.warning(f"Source not found, skipping: {src}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            # For copytree, the destination directory itself must not exist initially
            # unless dirs_exist_ok=True (Python 3.8+)
            # To be safe across versions, remove if exists, or handle content copy manually
            if dst.exists():
                 logging.warning(f"Destination directory {dst} already exists. Removing before copy.")
                 shutil.rmtree(dst)
            shutil.copytree(src, dst)
            logging.info(f"Copied directory {src} to {dst}")
        else:
            shutil.copy2(src, dst) # copy2 preserves metadata
            logging.info(f"Copied file {src} to {dst}")
    except Exception as e:
        logging.error(f"Error copying {src} to {dst}: {e}")

# --- Main Processing Logic ---

# Create the base output directory for the year
output_year_dir.mkdir(parents=True, exist_ok=True)
logging.info(f"Ensured base output directory exists: {output_year_dir}")

# Process each day
for day_num, tasks in tasks_by_day.items():
    day_str = f"day{day_num}"
    input_day_dir = input_base_dir / day_str
    input_trans_day_dir = input_base_dir / "translations" / day_str
    output_day_dir = output_year_dir / day_str

    logging.info(f"Processing {day_str}...")

    if not input_day_dir.is_dir():
        logging.warning(f"Input directory not found for {day_str}, skipping: {input_day_dir}")
        continue

    # Process each task within the day
    for task_name in tasks:
        logging.info(f"  Processing task: {task_name}")
        input_task_dir = input_day_dir / task_name
        # The core files (graders, tests) seem to be in a nested directory
        input_task_core_dir = input_task_dir / task_name
        input_trans_task_dir = input_trans_day_dir / task_name
        output_task_dir = output_day_dir / task_name

        # Define target subdirectories
        target_statements_dir = output_task_dir / "statements"
        target_graders_dir = output_task_dir / "graders"
        target_checkers_dir = output_task_dir / "checkers" # May not exist, look inside graders
        target_tests_dir = output_task_dir / "tests"
        target_attachments_dir = output_task_dir / "attachments"
        target_solutions_dir = output_task_dir / "solutions"
        target_solutions_code_dir = target_solutions_dir / "Codes"
        target_solutions_editorial_dir = target_solutions_dir / "editorial"

        # Create necessary output directories for the task
        output_task_dir.mkdir(parents=True, exist_ok=True)
        target_statements_dir.mkdir(exist_ok=True)
        # target_graders_dir will be created by copy_item if source exists
        # target_tests_dir will be created by copy_item if source exists
        target_attachments_dir.mkdir(exist_ok=True)
        target_solutions_dir.mkdir(exist_ok=True)
        target_solutions_code_dir.mkdir(exist_ok=True) # Create even if empty
        target_solutions_editorial_dir.mkdir(exist_ok=True)

        # 1. Copy Statements (English PDF from translations)
        statement_pdf_name = f"{task_name}-en.pdf"
        src_statement = input_trans_day_dir / statement_pdf_name
        dst_statement = target_statements_dir / statement_pdf_name
        copy_item(src_statement, dst_statement)

        # 2. Copy Graders
        src_graders = input_task_core_dir / "graders"
        # Destination is the directory itself
        copy_item(src_graders, target_graders_dir)
        # Check if a checker exists within the graders dir (common practice)
        # No explicit checker folder found in the input structure description.
        # If specific checker files (e.g., chk.cpp, checker.cpp) are known,
        # they could be searched for and moved to target_checkers_dir.
        # For now, graders potentially include checkers.

        # 3. Copy Tests
        src_tests = input_task_core_dir / "tests"
        copy_item(src_tests, target_tests_dir)

        # 4. Copy Solution Editorial (PDF from translations/solutions)
        editorial_pdf_name = f"{task_name}.pdf"
        src_editorial = input_base_dir / "translations" / "solutions" / editorial_pdf_name
        dst_editorial = target_solutions_editorial_dir / editorial_pdf_name
        copy_item(src_editorial, dst_editorial)

        # 5. Copy Solution Codes (Look for official codes - none specified in structure)
        # Placeholder: Create the directory, but no source identified to copy from.
        logging.info(f"  Created solutions code directory: {target_solutions_code_dir} (manual population may be needed)")


        # 6. Copy Attachments
        # Attachments can come from multiple places:
        # a) Files directly in the task folder (e.g., day1/scales/* excluding scales/ and zip)
        # b) Day-level notice folder (e.g., day1/notice/)
        # c) Translated task folder (e.g., translations/day1/scales/)
        # d) Translated day-level notice folder (e.g., translations/day1/notice/)

        # a) Files directly under input_task_dir
        logging.info(f"  Checking for attachments in {input_task_dir}")
        if input_task_dir.is_dir():
            target_attach_task_root = target_attachments_dir / "task_root_files"
            for item in input_task_dir.iterdir():
                 # Exclude the nested task directory (handled for graders/tests)
                 # and the zip file
                if item.is_file() and item.suffix != '.zip':
                     copy_item(item, target_attach_task_root / item.name)
                elif item.is_dir() and item.name != task_name: # Exclude the core dir
                    copy_item(item, target_attach_task_root / item.name)


        # b) Day-level notice folder
        src_day_notice = input_day_dir / "notice"
        if src_day_notice.is_dir():
            logging.info(f"  Copying attachments from {src_day_notice}")
            copy_item(src_day_notice, target_attachments_dir / "day_notice")

        # c) Translated task-specific folder
        if input_trans_task_dir.is_dir():
             logging.info(f"  Copying attachments from {input_trans_task_dir}")
             copy_item(input_trans_task_dir, target_attachments_dir / "translated_task_files")


        # d) Translated day-level notice folder
        src_trans_day_notice = input_trans_day_dir / "notice"
        if src_trans_day_notice.is_dir():
            logging.info(f"  Copying attachments from {src_trans_day_notice}")
            copy_item(src_trans_day_notice, target_attachments_dir / "translated_day_notice")

        # 7. Copy problem.json if it exists (not shown in structure, but good practice)
        src_problem_json = input_task_core_dir / "problem.json" # Assuming it might be here
        if not src_problem_json.exists():
             src_problem_json = input_task_dir / "problem.json" # Or maybe here

        if src_problem_json.exists():
            copy_item(src_problem_json, output_task_dir / "problem.json")
        else:
            logging.info(f"  problem.json not found for task {task_name}")


logging.info("Script finished.")