import os
import shutil
import re
from pathlib import Path

def sanitize_filename(name):
    """Removes or replaces characters problematic in filenames/paths."""
    # Remove leading/trailing whitespace
    name = name.strip()
    # Replace spaces and problematic characters with underscores
    name = re.sub(r'[\\/*?:"<>|\s]+', '_', name)
    # Lowercase for consistency
    name = name.lower()
    return name

def process_ioi_2006(input_dir, output_dir):
    """
    Processes the IOI 2006 folder structure and reorganizes it.

    Args:
        input_dir (str or Path): Path to the IOI 2006 input folder
                                 ($HOME_DIR/IOI-Bench/IOI/2006).
        output_dir (str or Path): Path to the root output folder
                                 ($HOME_DIR/IOI-Bench/IOI-Processed-2).
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    year = "2006"
    output_year_path = output_path / year

    print(f"Processing IOI {year} from {input_path} to {output_year_path}")

    # Create the base output directory for the year
    output_year_path.mkdir(parents=True, exist_ok=True)

    day_folders = [d for d in input_path.iterdir() if d.is_dir() and d.name.startswith('day')]
    # Ensure consistent day order (day0, day1, day2)
    day_folders.sort(key=lambda x: int(x.name.replace('day', '')))


    for day_folder in day_folders:
        day_name = day_folder.name
        day_num_str = day_name # e.g., "day0", "day1", "day2"
        output_day_path = output_year_path / day_num_str
        output_day_path.mkdir(parents=True, exist_ok=True)

        print(f"Processing {day_name}...")

        # --- Special Handling for Day 0 (Practice) ---
        if day_name == "day0":
            practice_dir = day_folder / "practice_day"
            practice_zip = day_folder / "practice_day.zip"

            # Copy practice_day.zip as a general day0 attachment if it exists
            if practice_zip.exists():
                 day0_attach_dir = output_day_path / "_attachments" # Day-level attachments
                 day0_attach_dir.mkdir(parents=True, exist_ok=True)
                 try:
                     shutil.copy2(practice_zip, day0_attach_dir / practice_zip.name)
                     print(f"  Copied {practice_zip.name} to {day0_attach_dir}")
                 except Exception as e:
                     print(f"  Error copying {practice_zip.name}: {e}")


            if practice_dir.is_dir():
                for item in practice_dir.iterdir():
                    if item.is_file() and item.suffix == ".pdf":
                        # Derive task name from PDF filename
                        pdf_name = item.stem
                        if "Task Overview Sheet" in pdf_name:
                            # Copy overview to year level
                            try:
                                shutil.copy2(item, output_year_path / item.name)
                                print(f"  Copied general file {item.name} to {output_year_path}")
                            except Exception as e:
                                print(f"  Error copying {item.name}: {e}")
                            continue # Skip processing this as a task

                        task_name = sanitize_filename(pdf_name)
                        task_output_path = output_day_path / task_name
                        print(f"  Processing task: {task_name}")

                        # Create standard directories for the task
                        statement_dir = task_output_path / "statements"
                        grader_dir = task_output_path / "graders"
                        checker_dir = task_output_path / "checkers"
                        test_dir = task_output_path / "tests"
                        attachment_dir = task_output_path / "attachments"
                        solution_code_dir = task_output_path / "solutions" / "Codes"
                        solution_editorial_dir = task_output_path / "solutions" / "editorial"

                        statement_dir.mkdir(parents=True, exist_ok=True)
                        grader_dir.mkdir(parents=True, exist_ok=True)
                        checker_dir.mkdir(parents=True, exist_ok=True)
                        test_dir.mkdir(parents=True, exist_ok=True)
                        attachment_dir.mkdir(parents=True, exist_ok=True)
                        solution_code_dir.mkdir(parents=True, exist_ok=True)
                        solution_editorial_dir.mkdir(parents=True, exist_ok=True)

                        # Copy statement PDF
                        try:
                            shutil.copy2(item, statement_dir / item.name)
                            print(f"    Copied statement: {item.name}")
                        except Exception as e:
                            print(f"    Error copying statement {item.name}: {e}")

                        # Note: Based on the structure, no separate tests/solutions/attachments
                        # are explicitly linked to individual practice tasks in this folder.
                        # They might be inside the practice_day.zip, which was copied earlier.
            continue # Move to the next day

        # --- Handling for Day 1 and Day 2 ---

        # Copy Task Overview PDF to the year level
        overview_pdf_name = f"Task_Overview_{day_name.capitalize()}.pdf"
        overview_pdf = day_folder / overview_pdf_name
        if overview_pdf.exists():
            try:
                shutil.copy2(overview_pdf, output_year_path / overview_pdf.name)
                print(f"  Copied general file {overview_pdf.name} to {output_year_path}")
            except Exception as e:
                print(f"  Error copying {overview_pdf.name}: {e}")

        # Iterate through potential task folders within the day folder
        for task_folder in day_folder.iterdir():
            # Skip non-directories and special folders like extracted test data/libs
            if not task_folder.is_dir() or task_folder.name.endswith(('_td', '_lib')):
                continue

            task_name = task_folder.name
            task_output_path = output_day_path / task_name
            print(f"  Processing task: {task_name}")

            # Create standard directories for the task
            statement_dir = task_output_path / "statements"
            grader_dir = task_output_path / "graders"
            checker_dir = task_output_path / "checkers"
            test_dir = task_output_path / "tests"
            attachment_dir = task_output_path / "attachments"
            solution_code_dir = task_output_path / "solutions" / "Codes"
            solution_editorial_dir = task_output_path / "solutions" / "editorial"

            statement_dir.mkdir(parents=True, exist_ok=True)
            grader_dir.mkdir(parents=True, exist_ok=True)
            checker_dir.mkdir(parents=True, exist_ok=True)
            test_dir.mkdir(parents=True, exist_ok=True)
            attachment_dir.mkdir(parents=True, exist_ok=True)
            solution_code_dir.mkdir(parents=True, exist_ok=True)
            solution_editorial_dir.mkdir(parents=True, exist_ok=True)

            # Process files and folders within the task folder
            for item in task_folder.iterdir():
                try:
                    # --- Files ---
                    if item.is_file():
                        # Problem Statement PDF
                        if item.name == f"{task_name}.pdf":
                            shutil.copy2(item, statement_dir / item.name)
                            print(f"    Copied statement: {item.name}")
                        # Solution Editorial PDF
                        elif item.name == f"{task_name}_sol.pdf":
                            shutil.copy2(item, solution_editorial_dir / item.name)
                            print(f"    Copied solution editorial: {item.name}")
                        # Test Data Zip (Attachment)
                        elif item.name == f"{task_name}_td.zip":
                            shutil.copy2(item, attachment_dir / item.name)
                            print(f"    Copied attachment: {item.name}")
                        # Library Zip (Attachment)
                        elif item.name == f"{task_name}_lib.zip":
                            shutil.copy2(item, attachment_dir / item.name)
                            print(f"    Copied attachment: {item.name}")
                        # Potentially other files might exist, ignore for now or classify as needed

                    # --- Directories ---
                    elif item.is_dir():
                        # Test Data Directory
                        if item.name == f"{task_name}_td":
                            print(f"    Copying tests from directory: {item.name}")
                            for sub_item in item.iterdir():
                                dest_path = test_dir / sub_item.name
                                if sub_item.is_file():
                                    shutil.copy2(sub_item, dest_path)
                                elif sub_item.is_dir():
                                    shutil.copytree(sub_item, dest_path, dirs_exist_ok=True)
                        # Library Directory (Attachment)
                        elif item.name == f"{task_name}_lib":
                            print(f"    Copying attachments from directory: {item.name}")
                            for sub_item in item.iterdir():
                                dest_path = attachment_dir / sub_item.name
                                if sub_item.is_file():
                                    shutil.copy2(sub_item, dest_path)
                                elif sub_item.is_dir():
                                    shutil.copytree(sub_item, dest_path, dirs_exist_ok=True)
                except Exception as e:
                    print(f"    Error processing {item.name} for task {task_name}: {e}")

    print(f"\nProcessing for IOI {year} complete.")
    print(f"Output generated at: {output_year_path}")

# --- Main Execution ---
if __name__ == "__main__":
    # Define the input and output directories
    # MAKE SURE THESE PATHS ARE CORRECT FOR YOUR SYSTEM
    input_directory = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2006"
    output_directory = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"

    # Ensure input directory exists
    if not Path(input_directory).is_dir():
        print(f"Error: Input directory not found at {input_directory}")
    else:
        # Run the processing function
        process_ioi_2006(input_directory, output_directory)