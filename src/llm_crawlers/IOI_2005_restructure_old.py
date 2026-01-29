import os
import shutil
import zipfile
import glob

def safe_copy(src, dst):
    """Copies a file from src to dst, creating parent directories if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"    Copied: {src} -> {dst}")
    except Exception as e:
        print(f"    Error copying {src} to {dst}: {e}")

def safe_copytree(src, dst):
    """Recursively copies a directory tree, creating parent directories."""
    try:
        # Ensure parent of dst exists
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # Copy the tree
        shutil.copytree(src, dst, dirs_exist_ok=True)
        # print(f"    Copied Tree: {src} -> {dst}")
    except Exception as e:
        print(f"    Error copying directory {src} to {dst}: {e}")

def extract_zip(zip_path, extract_to):
    """Extracts a zip file to a specified directory."""
    try:
        os.makedirs(extract_to, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"    Extracted: {zip_path} -> {extract_to}")
        return True
    except zipfile.BadZipFile:
        print(f"    Error: Bad zip file {zip_path}")
        return False
    except Exception as e:
        print(f"    Error extracting {zip_path} to {extract_to}: {e}")
        return False

def process_ioi_2005(source_base, target_base):
    """
    Organizes IOI 2005 files from source_base to target_base.
    """
    year = "2005"
    source_dir = os.path.join(source_base, year)
    target_dir = os.path.join(target_base, year)

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory {source_dir} not found.")
        return

    print(f"Processing IOI {year}")
    print(f"Source: {source_dir}")
    print(f"Target: {target_dir}")

    # Create year directory and top-level editorial directory
    os.makedirs(target_dir, exist_ok=True)
    target_editorial_dir = os.path.join(target_dir, "editorial")
    os.makedirs(target_editorial_dir, exist_ok=True)

    # 1. Process top-level editorial files
    print("\nProcessing top-level files...")
    for item in os.listdir(source_dir):
        source_item_path = os.path.join(source_dir, item)
        if os.path.isfile(source_item_path) and item.startswith("ioi2005-tasks-and-solutions") and item.endswith(".pdf"):
            print(f"  Copying general editorial: {item}")
            safe_copy(source_item_path, os.path.join(target_editorial_dir, item))

    # 2. Process day folders
    day_folders = [d for d in os.listdir(source_dir) if os.path.isdir(os.path.join(source_dir, d)) and d.startswith("day")]
    # Ensure consistent order (day0, day1, day2)
    day_folders.sort(key=lambda x: int(x.replace("day","")))

    for day_folder in day_folders:
        source_day_path = os.path.join(source_dir, day_folder)
        target_day_path = os.path.join(target_dir, day_folder)
        os.makedirs(target_day_path, exist_ok=True)
        print(f"\nProcessing {day_folder}...")

        # 3. Process task folders within each day
        for task_name in sorted(os.listdir(source_day_path)):
            source_task_path = os.path.join(source_day_path, task_name)
            if not os.path.isdir(source_task_path):
                continue

            print(f"  Processing Task: {task_name}")
            target_task_path = os.path.join(target_day_path, task_name)

            # Create standard target subdirectories
            target_statements_path = os.path.join(target_task_path, "statements")
            target_graders_path = os.path.join(target_task_path, "graders")
            target_checkers_path = os.path.join(target_task_path, "checkers")
            target_tests_path = os.path.join(target_task_path, "tests")
            target_attachments_path = os.path.join(target_task_path, "attachments")
            target_solutions_path = os.path.join(target_task_path, "solutions")
            target_solutions_codes_path = os.path.join(target_solutions_path, "Codes")
            target_solutions_editorial_path = os.path.join(target_solutions_path, "editorial")
            target_subtasks_path = os.path.join(target_task_path, "subtasks")

            for path in [target_statements_path, target_graders_path, target_checkers_path,
                         target_tests_path, target_attachments_path, target_solutions_path,
                         target_solutions_codes_path, target_solutions_editorial_path,
                         target_subtasks_path]:
                os.makedirs(path, exist_ok=True)

            # 4. Process files within the source task folder
            tests_zip_path = None
            tests_unzipped_path = None
            module_zip_path = None
            module_unzipped_path = None

            for item in os.listdir(source_task_path):
                source_item_path = os.path.join(source_task_path, item)

                # Problem Statement PDF
                if os.path.isfile(source_item_path) and item == f"{task_name}.pdf":
                    print(f"    Found statement: {item}")
                    safe_copy(source_item_path, os.path.join(target_statements_path, item))

                # Tests Zip
                elif os.path.isfile(source_item_path) and item == f"{task_name}_tests.zip":
                    tests_zip_path = source_item_path
                    print(f"    Found tests zip: {item}")

                # Tests Unzipped Folder
                elif os.path.isdir(source_item_path) and item == f"{task_name}_tests":
                    tests_unzipped_path = source_item_path
                    print(f"    Found tests folder: {item}")

                # Module Zip (e.g., div_module.zip)
                elif os.path.isfile(source_item_path) and item == f"{task_name}_module.zip":
                    module_zip_path = source_item_path
                    print(f"    Found module zip: {item}")

                # Module Unzipped Folder (e.g., div_module)
                elif os.path.isdir(source_item_path) and item == f"{task_name}_module":
                     module_unzipped_path = source_item_path
                     print(f"    Found module folder: {item}")


            # 5. Handle Tests (prefer unzipped, fallback to zip)
            print(f"    Handling tests for {task_name}...")
            actual_tests_source = None
            if tests_unzipped_path:
                # Determine the deeply nested test folder path
                # Standard case: task_tests/task_tests/task/
                potential_path1 = os.path.join(tests_unzipped_path, f"{task_name}_tests", task_name)
                 # DOM case: dom_tests/tests/
                potential_path2 = os.path.join(tests_unzipped_path, "tests")

                if os.path.isdir(potential_path1):
                    actual_tests_source = potential_path1
                    print(f"      Using unzipped tests from standard path: {actual_tests_source}")
                elif os.path.isdir(potential_path2) and task_name == "dom":
                     actual_tests_source = potential_path2
                     print(f"      Using unzipped tests from 'dom' path: {actual_tests_source}")
                else:
                     print(f"      WARNING: Could not locate actual tests within {tests_unzipped_path}. Expected structure not found.")

                if actual_tests_source:
                    copied_count = 0
                    for test_item in os.listdir(actual_tests_source):
                        src_test_item = os.path.join(actual_tests_source, test_item)
                        if os.path.isfile(src_test_item):
                             safe_copy(src_test_item, os.path.join(target_tests_path, test_item))
                             copied_count += 1
                    print(f"      Copied {copied_count} test files from unzipped folder.")

            elif tests_zip_path:
                 print(f"      Unzipped tests folder not found or structure mismatch, trying to extract from {tests_zip_path}")
                 # Create a temporary extraction location
                 temp_extract_path = os.path.join(target_task_path, "_temp_tests_extract")
                 if extract_zip(tests_zip_path, temp_extract_path):
                     # Try to find the tests within the extracted structure
                     potential_path1 = os.path.join(temp_extract_path, f"{task_name}_tests", task_name)
                     potential_path2 = os.path.join(temp_extract_path, "tests") # for dom case if extracted flat

                     if os.path.isdir(potential_path1):
                         actual_tests_source = potential_path1
                         print(f"      Found tests in extracted standard path: {actual_tests_source}")
                     elif os.path.isdir(potential_path2) and task_name == "dom":
                         actual_tests_source = potential_path2
                         print(f"      Found tests in extracted 'dom' path: {actual_tests_source}")
                     else:
                         # Sometimes the zip extracts directly into the target dir
                         # check if test files exist directly in temp_extract_path
                         # Heuristic: check for common test file extensions like .in, .out, .ans
                         test_files_present = any(f.endswith(('.in', '.out', '.ans')) for f in os.listdir(temp_extract_path))
                         if test_files_present:
                            actual_tests_source = temp_extract_path
                            print(f"      Found test files directly in extracted path: {actual_tests_source}")
                         else:
                             print(f"      WARNING: Could not locate actual tests within extracted {temp_extract_path}. Trying to copy root content.")
                             # Fallback: Copy everything from the root of extraction if specific path fails
                             actual_tests_source = temp_extract_path


                     if actual_tests_source:
                         copied_count = 0
                         for test_item in os.listdir(actual_tests_source):
                             src_test_item = os.path.join(actual_tests_source, test_item)
                             if os.path.isfile(src_test_item):
                                 safe_copy(src_test_item, os.path.join(target_tests_path, test_item))
                                 copied_count += 1
                         print(f"      Copied {copied_count} test files from extracted zip.")

                     # Clean up temporary extraction folder
                     try:
                         shutil.rmtree(temp_extract_path)
                         print(f"      Cleaned up temporary directory: {temp_extract_path}")
                     except Exception as e:
                         print(f"      Warning: Could not remove temporary directory {temp_extract_path}: {e}")
                 else:
                     print(f"      Failed to extract tests from {tests_zip_path}")
            else:
                 print(f"    WARNING: No tests zip or folder found for task {task_name}")


            # 6. Handle Attachments/Modules (prefer unzipped, fallback to zip)
            print(f"    Handling attachments/modules for {task_name}...")
            if module_unzipped_path:
                print(f"      Using unzipped module folder: {module_unzipped_path}")
                # Copy the entire contents of the module folder to attachments
                safe_copytree(module_unzipped_path, target_attachments_path)
                print(f"      Copied attachments from unzipped folder.")
            elif module_zip_path:
                print(f"      Unzipped module folder not found, extracting from {module_zip_path}")
                if extract_zip(module_zip_path, target_attachments_path):
                     print(f"      Extracted attachments from zip file.")
                else:
                    print(f"      Failed to extract attachments from {module_zip_path}")
            else:
                print(f"    No module zip or folder found for task {task_name} (This is expected for most tasks).")


    print(f"\nFinished processing IOI {year}.")

# --- Configuration ---
SOURCE_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI"  # Contains the '2005' folder
TARGET_BASE_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"

# --- Run the processing ---
process_ioi_2005(SOURCE_BASE_DIR, TARGET_BASE_DIR)