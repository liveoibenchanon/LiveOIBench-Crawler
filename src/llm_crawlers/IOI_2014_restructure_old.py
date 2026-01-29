import os
import shutil
import tarfile
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define source and target directories
source_base_dir = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2014")
target_base_dir = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2")
year = "2014"
target_dir = target_base_dir / year

# Helper function to safely copy files or directories
def safe_copy(src, dst, is_dir=False):
    """Safely copies a file or directory."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if is_dir:
            if src.is_dir():
                # Copy contents of the directory
                shutil.copytree(src, dst, dirs_exist_ok=True, copy_function=shutil.copy2)
                logging.info(f"Copied directory {src} to {dst}")
            else:
                 logging.warning(f"Source directory {src} not found or is not a directory.")
        else:
            if src.is_file():
                shutil.copy2(src, dst)
                logging.info(f"Copied file {src} to {dst}")
            else:
                logging.warning(f"Source file {src} not found or is not a file.")
    except Exception as e:
        logging.error(f"Error copying {src} to {dst}: {e}")

def extract_tarball(tar_path, extract_to_dir):
    """Extracts a tarball to a specified directory."""
    if not tar_path.is_file():
        logging.warning(f"Tarball {tar_path} not found.")
        return False
    try:
        extract_to_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(tar_path, "r:*") as tar:
            # Check for common nested structures like task-testdata/task-testdata/
            members = tar.getmembers()
            # Detect if all members are within a single top-level directory
            common_prefix = os.path.commonprefix([m.name for m in members if not m.name.startswith('.')]) # Use commonprefix without hidden files
            strip_level = 0
            if common_prefix and all(m.name.startswith(common_prefix) for m in members if not m.name.startswith('.')):
                 # Check if this common_prefix itself contains another directory with the same name pattern
                 # e.g. holiday-testdata/holiday-testdata/
                 parts = Path(common_prefix.strip('/')).parts
                 if len(parts) >= 2 and parts[0] == parts[1]:
                     strip_level = 2 # Strip two levels
                 elif len(parts) >= 1:
                     strip_level = 1 # Strip one level

            if strip_level > 0:
                prefix_to_strip = str(Path(*parts[:strip_level])) + '/'
                logging.info(f"Detected common prefix '{prefix_to_strip}'. Stripping {strip_level} level(s) during extraction.")
                for member in members:
                    original_path = Path(member.name)
                    if original_path.is_absolute() or ".." in original_path.parts:
                        logging.warning(f"Skipping potentially unsafe path in tarball: {member.name}")
                        continue
                    if member.name.startswith(prefix_to_strip):
                         member.name = str(Path(*original_path.parts[strip_level:]))
                         if member.name: # Don't extract empty names (like the root folder itself)
                            tar.extract(member, extract_to_dir)
                    # else: maybe keep files not under the prefix? Or skip? Let's extract them directly.
                    elif not member.name.startswith('.'): # Avoid hidden files not under prefix
                         tar.extract(member, extract_to_dir)

            else:
                 logging.info(f"Extracting tarball {tar_path} directly to {extract_to_dir}")
                 tar.extractall(path=extract_to_dir)

        logging.info(f"Successfully extracted {tar_path} to {extract_to_dir}")
        return True
    except tarfile.ReadError:
        logging.error(f"Error reading tarball {tar_path}. It might be corrupted or not a tar file.")
        return False
    except Exception as e:
        logging.error(f"Error extracting {tar_path}: {e}")
        return False

def create_task_structure(day_path, task_name):
    """Creates the standard directory structure for a task."""
    task_path = day_path / task_name
    task_path.mkdir(parents=True, exist_ok=True)
    (task_path / "statements").mkdir(exist_ok=True)
    (task_path / "graders").mkdir(exist_ok=True)
    (task_path / "checkers").mkdir(exist_ok=True)
    (task_path / "tests").mkdir(exist_ok=True)
    (task_path / "attachments").mkdir(exist_ok=True)
    (task_path / "solutions").mkdir(exist_ok=True)
    (task_path / "solutions" / "Codes").mkdir(exist_ok=True)
    (task_path / "solutions" / "editorial").mkdir(exist_ok=True)
    (task_path / "subtasks").mkdir(exist_ok=True)
    return task_path

# --- Main Processing ---

# Create the base target directory for the year
target_dir.mkdir(parents=True, exist_ok=True)
(target_dir / "editorial").mkdir(exist_ok=True) # For year-level editorial

# --- Process Day 0 (Practice) ---
logging.info("Processing Day 0 (Practice)")
day0_target_path = target_dir / "day0"
day0_source_path = source_base_dir / "day0"
practice_base_path = day0_source_path / "ioi14-practice-v2" / "ioi14-practice"

# Mapping from task name to PDF prefix
practice_task_map = {
    "square": "1",
    "station": "2",
    "tile": "3"
}

if practice_base_path.is_dir():
    for task_name, task_prefix in practice_task_map.items():
        logging.info(f"Processing Day 0 Task: {task_name}")
        task_source_path = practice_base_path / task_name
        if not task_source_path.is_dir():
            logging.warning(f"Practice task source directory not found: {task_source_path}")
            continue

        task_target_path = create_task_structure(day0_target_path, task_name)

        # 1. Statements
        # From practice description folder
        statement_src_dir = task_source_path / "description"
        if statement_src_dir.is_dir():
            for pdf_file in statement_src_dir.glob("*.pdf"):
                safe_copy(pdf_file, task_target_path / "statements" / pdf_file.name)
        # From day0 root PDF
        pdf_name_root = f"{task_prefix}-{task_name}.pdf"
        statement_src_pdf = day0_source_path / pdf_name_root
        if statement_src_pdf.exists():
            safe_copy(statement_src_pdf, task_target_path / "statements" / pdf_name_root)
        else:
             logging.warning(f"Did not find root statement PDF: {statement_src_pdf}")


        # 2. Graders
        grader_src_dir = task_source_path / "judge"
        if grader_src_dir.is_dir():
            safe_copy(grader_src_dir, task_target_path / "graders", is_dir=True)

        # 3. Tests
        tests_src_dir = task_source_path / "testdata"
        if tests_src_dir.is_dir():
            safe_copy(tests_src_dir, task_target_path / "tests", is_dir=True)

        # 4. Attachments
        attachment_src_dir = task_source_path / "attachment"
        workspace_src_dir = task_source_path / "workspace"
        if attachment_src_dir.is_dir():
            safe_copy(attachment_src_dir, task_target_path / "attachments", is_dir=True)
        if workspace_src_dir.is_dir():
             # Copy contents of workspace into attachments
             safe_copy(workspace_src_dir, task_target_path / "attachments", is_dir=True)


        # 5. Solutions (Editorial PDF)
        solution_pdf_name = f"{task_prefix}-{task_name}-solution.pdf"
        solution_src_pdf = day0_source_path / solution_pdf_name
        if solution_src_pdf.exists():
            safe_copy(solution_src_pdf, task_target_path / "solutions" / "editorial" / solution_pdf_name)
        else:
             logging.warning(f"Did not find solution PDF: {solution_src_pdf}")

        # 6. Checkers, Solutions/Codes, Subtasks, problem.json - Create folders (likely empty)
        # Already created by create_task_structure

else:
    logging.warning(f"Practice base directory not found: {practice_base_path}")


# --- Process Day 1 and Day 2 ---
logging.info("Processing Contest Days (Day 1, Day 2)")
translations_base_path = source_base_dir / "translations"

for day in ["day1", "day2"]:
    logging.info(f"Processing {day}")
    day_target_path = target_dir / day
    day_source_path = source_base_dir / day
    day_translations_path = translations_base_path / day

    if not day_translations_path.is_dir():
        logging.warning(f"Translations directory not found for {day}: {day_translations_path}")
        continue

    # Iterate through tasks based on translation folders
    for task_translation_dir in day_translations_path.iterdir():
        if not task_translation_dir.is_dir():
            continue
        task_name = task_translation_dir.name
        logging.info(f"Processing {day} Task: {task_name}")

        task_target_path = create_task_structure(day_target_path, task_name)
        task_day_source_path = day_source_path / task_name # Path like 2014/day2/holiday/

        # 1. Statements (from translations)
        safe_copy(task_translation_dir, task_target_path / "statements", is_dir=True)

        # 2. Tests
        # Look for tar.gz archive
        tests_extracted = False
        test_tarball_path = task_day_source_path / f"{task_name}-testdata.tar.gz"
        if test_tarball_path.is_file():
            logging.info(f"Found test data archive: {test_tarball_path}")
            tests_extracted = extract_tarball(test_tarball_path, task_target_path / "tests")
        else:
            logging.info(f"No test data archive found at {test_tarball_path}")

        # Look for extracted test data folder (potentially nested)
        test_data_folder_name = f"{task_name}-testdata"
        potential_test_dir1 = task_day_source_path / test_data_folder_name
        potential_test_dir2 = task_day_source_path / test_data_folder_name / test_data_folder_name # Handle nested case

        test_src_dir_to_copy = None
        if potential_test_dir2.is_dir():
             test_src_dir_to_copy = potential_test_dir2
             logging.info(f"Found nested extracted test data directory: {test_src_dir_to_copy}")
        elif potential_test_dir1.is_dir():
             test_src_dir_to_copy = potential_test_dir1
             logging.info(f"Found extracted test data directory: {test_src_dir_to_copy}")
        else:
            logging.info(f"No pre-extracted test data directory found for {task_name} in {task_day_source_path}")


        # Copy if found and not already handled by tar extraction (simple check)
        if test_src_dir_to_copy and not tests_extracted: # Avoid double copying if tar extract worked
             safe_copy(test_src_dir_to_copy, task_target_path / "tests", is_dir=True)
        elif test_src_dir_to_copy and tests_extracted:
             logging.info(f"Skipping copy of {test_src_dir_to_copy} as tests were likely extracted from tarball.")


        # 3. Graders, Checkers, Attachments, Solutions - Assume missing unless found
        # (Structure doesn't show explicit sources for these for day1/day2)
        logging.info(f"No explicit source structure for graders, checkers, attachments, solutions code/editorial for {day}/{task_name}. Folders created.")

# --- Final Check for Year-Level Editorials ---
# Check root folder or day0 for potential general solution booklets (less likely based on structure)
# Example: Look for pdfs directly under source_base_dir or day0_source_path that don't match task patterns.
# This step is often manual or requires specific knowledge of the contest materials.
# For now, the `2014/editorial` folder remains empty unless manually populated.
logging.info("Looking for potential year-level editorial files (heuristic)...")
possible_editorial_files = list(source_base_dir.glob("*.pdf")) + list(day0_source_path.glob("*.pdf"))
processed_day0_files = set()
for task_name, task_prefix in practice_task_map.items():
    processed_day0_files.add(f"{task_prefix}-{task_name}.pdf")
    processed_day0_files.add(f"{task_prefix}-{task_name}-solution.pdf")

copied_editorial = False
for pdf_file in possible_editorial_files:
    if pdf_file.name not in processed_day0_files:
         # Simple heuristic: if it contains 'solution', 'review', 'booklet', 'editorial' etc.
         if any(keyword in pdf_file.name.lower() for keyword in ['solution', 'review', 'booklet', 'editorial', 'analysis']):
              logging.info(f"Potential year-level editorial found: {pdf_file}. Copying.")
              safe_copy(pdf_file, target_dir / "editorial" / pdf_file.name)
              copied_editorial = True

if not copied_editorial:
    logging.info("No obvious year-level editorial files found based on filename patterns.")


logging.info(f"Processing complete. Output saved to: {target_dir}")