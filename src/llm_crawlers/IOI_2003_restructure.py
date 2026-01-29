import os
import shutil
import re
import zipfile
from pathlib import Path

def create_dir_if_not_exists(path):
    """Creates a directory if it doesn't exist."""
    Path(path).mkdir(parents=True, exist_ok=True)

def extract_zip(zip_path, extract_to):
    """Extracts a zip file to a specified location."""
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            print(f"Successfully extracted {zip_path} to {extract_to}")
            return True
    except zipfile.BadZipFile:
        print(f"Error: {zip_path} is not a valid zip file or is corrupted.")
        return False
    except FileNotFoundError:
        print(f"Error: Zip file not found at {zip_path}")
        return False
    except Exception as e:
        print(f"An error occurred during extraction: {e}")
        return False

def process_ioi_2003(input_base_dir, output_base_dir):
    """
    Processes the IOI 2003 folder structure and organizes files into
    the standardized output structure.
    """
    year = "2003"
    input_year_dir = Path(input_base_dir) / year
    output_year_dir = Path(output_base_dir) / year

    if not input_year_dir.is_dir():
        print(f"Error: Input directory not found: {input_year_dir}")
        return

    print(f"Processing IOI {year} data from: {input_year_dir}")
    print(f"Outputting processed data to: {output_year_dir}")

    # Create base output directories
    create_dir_if_not_exists(output_year_dir)
    create_dir_if_not_exists(output_year_dir / "editorial") # Top-level editorial

    # --- Handle Test Cases ---
    other_materials_dir = input_year_dir / "other_materials"
    test_cases_source_dir = other_materials_dir / "TestCases"
    test_cases_zip = other_materials_dir / "TestCases.zip"

    # Extract TestCases.zip if the directory doesn't exist
    if not test_cases_source_dir.is_dir() and test_cases_zip.is_file():
        print(f"TestCases directory not found, attempting to extract from {test_cases_zip}...")
        if extract_zip(test_cases_zip, other_materials_dir):
             # Check again if extraction was successful
             if not test_cases_source_dir.is_dir():
                 print(f"Error: Extraction seems to have failed, {test_cases_source_dir} still not found.")
                 # Decide whether to proceed without tests or stop
                 # For now, we'll continue and report missing tests later
        else:
            print(f"Warning: Could not extract test cases from {test_cases_zip}.")
            # Continue, but tests might be missing

    if not test_cases_source_dir.is_dir():
         print(f"Warning: Test case source directory not found at {test_cases_source_dir}. Tests will be missing.")


    # --- Task Name Mapping ---
    # Map official task names (from PDFs) to test case folder names
    task_name_mapping = {
        "Trail_Maintenance": "maintain",
        "Comparing_Code": "code",
        "Reverse": "reverse",
        "Guess_Which_Cow": "guess",
        "Amazing_Robots": "robots",
        "Seeing_the_Boundary": "boundary",
    }

    # --- Process Days ---
    for day_folder in ["day1", "day2"]:
        input_day_dir = input_year_dir / day_folder
        output_day_dir = output_year_dir / day_folder

        if not input_day_dir.is_dir():
            print(f"Warning: Day directory not found: {input_day_dir}")
            continue

        create_dir_if_not_exists(output_day_dir)
        print(f"Processing {day_folder}...")

        for item in sorted(input_day_dir.iterdir()):
            if item.is_file() and item.suffix.lower() == '.pdf':
                # Match filenames like "01_Trail_Maintenance.pdf"
                match = re.match(r"(\d+)_([a-zA-Z_]+)\.pdf", item.name, re.IGNORECASE)
                if match:
                    # task_num_str = match.group(1)
                    task_name_pdf = match.group(2)
                    print(f"  Found task statement: {item.name} -> Task Name: {task_name_pdf}")

                    # Normalize task name if needed (e.g., remove underscores for folder)
                    # Here, we keep the underscore as per example structure implicit intent
                    output_task_name = task_name_pdf
                    output_task_dir = output_day_dir / output_task_name

                    # Create standard task subdirectories
                    statements_dir = output_task_dir / "statements"
                    graders_dir = output_task_dir / "graders"
                    checkers_dir = output_task_dir / "checkers"
                    tests_dir = output_task_dir / "tests"
                    attachments_dir = output_task_dir / "attachments"
                    solutions_dir = output_task_dir / "solutions"
                    solutions_codes_dir = solutions_dir / "Codes"
                    solutions_editorial_dir = solutions_dir / "editorial"
                    subtasks_dir = output_task_dir / "subtasks"

                    create_dir_if_not_exists(statements_dir)
                    create_dir_if_not_exists(graders_dir)
                    create_dir_if_not_exists(checkers_dir)
                    create_dir_if_not_exists(tests_dir)
                    create_dir_if_not_exists(attachments_dir)
                    create_dir_if_not_exists(solutions_dir)
                    create_dir_if_not_exists(solutions_codes_dir)
                    create_dir_if_not_exists(solutions_editorial_dir)
                    create_dir_if_not_exists(subtasks_dir)

                    # 1. Copy Statement
                    try:
                        shutil.copy2(item, statements_dir / item.name)
                        print(f"    Copied statement: {item.name}")
                    except Exception as e:
                        print(f"    Error copying statement {item.name}: {e}")

                    # 2. Copy Tests
                    test_folder_name = task_name_mapping.get(output_task_name)
                    if test_folder_name and test_cases_source_dir.is_dir():
                        input_tests_dir = test_cases_source_dir / test_folder_name
                        if input_tests_dir.is_dir():
                            print(f"    Copying tests from {input_tests_dir}...")
                            file_count = 0
                            for test_file in input_tests_dir.iterdir():
                                if test_file.is_file():
                                    try:
                                        shutil.copy2(test_file, tests_dir / test_file.name)
                                        file_count += 1
                                    except Exception as e:
                                        print(f"      Error copying test file {test_file.name}: {e}")
                            print(f"      Copied {file_count} test files.")
                        else:
                            print(f"    Warning: Test directory not found for task {output_task_name}: {input_tests_dir}")
                    elif not test_folder_name:
                         print(f"    Warning: No test folder mapping found for task: {output_task_name}")
                    # Implicit else: test_cases_source_dir wasn't found, warning already printed

                    # 3. Look for other relevant files (solutions, editorials, etc.) - None explicitly mentioned
                    # If specific solution files or general editorials were present in the input structure,
                    # logic would be added here to copy them to the appropriate output folders
                    # (e.g., solutions/Codes, solutions/editorial, or the top-level /editorial)

                else:
                    print(f"  Skipping file (doesn't match task PDF pattern): {item.name}")
            # else:
                # print(f"  Skipping non-PDF item: {item.name}") # Optional: log skipped items

    print(f"\nProcessing for IOI {year} finished.")
    print(f"Output structure generated at: {output_year_dir}")

# --- Configuration ---
# Adjust these paths as necessary
INPUT_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New"
OUTPUT_BASE = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed"

# --- Execution ---
if __name__ == "__main__":
    process_ioi_2003(INPUT_BASE, OUTPUT_BASE)