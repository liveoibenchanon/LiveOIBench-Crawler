import os
import shutil
import zipfile
import glob

def copy_files(src_dir, dest_dir):
    """Copies all files from src_dir to dest_dir."""
    if not os.path.isdir(src_dir):
        print(f"    Warning: Source directory for copying not found: {src_dir}")
        return
    os.makedirs(dest_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        s_item = os.path.join(src_dir, item)
        d_item = os.path.join(dest_dir, item)
        if os.path.isfile(s_item):
            try:
                shutil.copy2(s_item, d_item)
                # print(f"      Copied {s_item} to {d_item}")
            except Exception as e:
                print(f"      Error copying {s_item} to {d_item}: {e}")
        elif os.path.isdir(s_item):
            # Optionally recurse for subdirectories if needed,
            # but for tests, graders, etc., a flat structure is expected.
            # copy_files(s_item, d_item)
            pass

def extract_files_from_zip(zip_f, task_name, dest_tests_dir):
    """Extracts files for a specific task from a zip archive."""
    extracted_count = 0
    # Common path patterns inside IOI zips
    # Sometimes it's just taskname/, sometimes testdata/taskname/, sometimes testdata_unix/taskname/
    possible_prefixes = [
        f"{task_name}/",
        f"testdata/{task_name}/",
        f"testdata_unix/{task_name}/",
        f"Testdata/{task_name}/",
        f"Testdata_unix/{task_name}/",
    ]
    
    target_prefix = None
    # Determine the correct prefix inside the zip
    for member in zip_f.namelist():
         for prefix in possible_prefixes:
             if member.startswith(prefix):
                 target_prefix = prefix
                 break
         if target_prefix:
             break
             
    if not target_prefix:
        print(f"    Warning: Could not find test data prefix for task '{task_name}' in zip file.")
        # Fallback: Try extracting anything under a directory named task_name
        target_prefix = f"{task_name}/" # A common case
        found_in_fallback = False
        for member in zip_f.namelist():
            # Check if path contains /task_name/
            path_parts = member.replace('\\', '/').split('/')
            if task_name in path_parts:
                 # Try to reconstruct a plausible prefix
                 try:
                     idx = path_parts.index(task_name)
                     target_prefix = "/".join(path_parts[:idx+1]) + "/"
                     print(f"    Using fallback prefix guess: {target_prefix}")
                     found_in_fallback = True
                     break
                 except ValueError:
                     continue
        if not found_in_fallback:
             print(f"    Warning: Could not determine test data folder for task '{task_name}' even with fallback.")
             return 0 # Indicate nothing extracted


    os.makedirs(dest_tests_dir, exist_ok=True)
    for member in zip_f.namelist():
        # Check if the member starts with the determined prefix and is a file
        if member.startswith(target_prefix) and not member.endswith('/'):
            # Extract the file to the destination, preserving subdirectory structure *within* the task folder if any exists
            # Calculate target path relative to dest_tests_dir
            relative_path = member[len(target_prefix):]
            target_path = os.path.join(dest_tests_dir, relative_path)

            # Ensure the target directory exists
            target_dir = os.path.dirname(target_path)
            os.makedirs(target_dir, exist_ok=True)

            try:
                with zip_f.open(member) as source_f, open(target_path, "wb") as target_f:
                    shutil.copyfileobj(source_f, target_f)
                extracted_count += 1
            except Exception as e:
                print(f"      Error extracting {member} from zip: {e}")

    if extracted_count > 0:
        print(f"    Extracted {extracted_count} test file(s) for {task_name} from zip.")
    else:
        print(f"    Warning: No test files found or extracted for {task_name} with prefix '{target_prefix}' from zip.")
    return extracted_count


def process_ioi_year(source_root_year, dest_root, year):
    """Processes the IOI data for a specific year."""
    print(f"Processing IOI {year}...")
    print(f"Source: {source_root_year}")
    print(f"Destination: {dest_root}")

    output_year_dir = os.path.join(dest_root, year)
    os.makedirs(output_year_dir, exist_ok=True)

    # --- Handle Top-Level Files (General Editorial) ---
    top_level_editorial_dir = os.path.join(output_year_dir, "editorial")
    solutions_pdf = os.path.join(source_root_year, "solutions.pdf")
    if os.path.isfile(solutions_pdf):
        print("  Found general solutions PDF.")
        os.makedirs(top_level_editorial_dir, exist_ok=True)
        try:
            shutil.copy2(solutions_pdf, top_level_editorial_dir)
            print(f"    Copied {solutions_pdf} to {top_level_editorial_dir}")
        except Exception as e:
            print(f"    Error copying {solutions_pdf}: {e}")
    else:
        print("  No general solutions.pdf found at the top level.")

    # --- Process Days ---
    day_folders = [d for d in os.listdir(source_root_year) if d.startswith("day") and os.path.isdir(os.path.join(source_root_year, d))]
    # Treat 'practice' as day0 if it exists
    if os.path.isdir(os.path.join(source_root_year, "practice")):
        day_folders.append("practice")

    for day_folder_name in sorted(day_folders):
        day_num = day_folder_name.replace("day", "") if day_folder_name != "practice" else "0"
        source_day_path = os.path.join(source_root_year, day_folder_name)
        dest_day_path = os.path.join(output_year_dir, f"day{day_num}")

        print(f"\nProcessing {day_folder_name} (-> day{day_num})...")
        os.makedirs(dest_day_path, exist_ok=True)

        # --- Find Tasks for the Day ---
        tasks = []
        task_statement_files = {}
        pdf_files = glob.glob(os.path.join(source_day_path, "*.pdf"))
        excluded_pdfs = ["overview.pdf", "solutions.pdf", "analysis.pdf"] # Common non-task pdfs

        for pdf_path in pdf_files:
            pdf_filename = os.path.basename(pdf_path)
            task_name = os.path.splitext(pdf_filename)[0]
            # Basic heuristic: if it's not explicitly excluded, assume it's a task statement
            if pdf_filename.lower() not in excluded_pdfs:
                 # Additional check: Ensure it's not purely numeric or very short, common for non-task docs
                 if not task_name.isdigit() and len(task_name) > 2:
                     tasks.append(task_name)
                     task_statement_files[task_name] = pdf_path
                     print(f"  Identified task '{task_name}' from {pdf_filename}")

        if not tasks:
             print(f"  Warning: No tasks identified in {day_folder_name} based on PDF files.")
             # Try identifying tasks based on testdata subdirectories if PDFs missing/ambiguous
             potential_test_dir = os.path.join(source_day_path, "testdata_unix")
             if os.path.isdir(potential_test_dir):
                 print(f"  Attempting task identification from {potential_test_dir} subdirectories...")
                 for item in os.listdir(potential_test_dir):
                     item_path = os.path.join(potential_test_dir, item)
                     if os.path.isdir(item_path) and item not in tasks:
                         tasks.append(item)
                         print(f"  Identified task '{item}' from testdata directory.")


        # --- Handle Day-Level Attachments (e.g., overview.pdf) ---
        overview_pdf = os.path.join(source_day_path, "overview.pdf")
        if os.path.isfile(overview_pdf):
            dest_day_attachments_dir = os.path.join(dest_day_path, "attachments")
            os.makedirs(dest_day_attachments_dir, exist_ok=True)
            try:
                shutil.copy2(overview_pdf, dest_day_attachments_dir)
                print(f"    Copied day overview {overview_pdf} to {dest_day_attachments_dir}")
            except Exception as e:
                print(f"    Error copying {overview_pdf}: {e}")


        # --- Locate Test Data (Extracted dir or Zip) ---
        test_data_extracted_dir = os.path.join(source_day_path, "testdata_unix")
        test_data_zip_path = os.path.join(source_day_path, "testdata_unix.zip")
        test_data_source = None # Can be 'dir', 'zip', or None

        if os.path.isdir(test_data_extracted_dir):
            test_data_source = 'dir'
            print(f"  Found extracted test data directory: {test_data_extracted_dir}")
        elif os.path.isfile(test_data_zip_path):
            test_data_source = 'zip'
            print(f"  Found test data zip file: {test_data_zip_path}")
        else:
            print(f"  Warning: No test data (directory or zip) found in {source_day_path}")

        zip_file = None
        if test_data_source == 'zip':
             try:
                 zip_file = zipfile.ZipFile(test_data_zip_path, 'r')
             except zipfile.BadZipFile:
                 print(f"  Error: Failed to open zip file {test_data_zip_path}. It might be corrupted.")
                 test_data_source = None # Cannot use this source
             except Exception as e:
                 print(f"  Error opening zip file {test_data_zip_path}: {e}")
                 test_data_source = None

        # --- Process Each Task ---
        for task_name in tasks:
            print(f"\n  Processing Task: {task_name}")
            dest_task_path = os.path.join(dest_day_path, task_name)
            os.makedirs(dest_task_path, exist_ok=True)

            # Create standard subdirectories
            statements_dir = os.path.join(dest_task_path, "statements")
            graders_dir = os.path.join(dest_task_path, "graders")
            checkers_dir = os.path.join(dest_task_path, "checkers")
            tests_dir = os.path.join(dest_task_path, "tests")
            attachments_dir = os.path.join(dest_task_path, "attachments")
            solutions_dir = os.path.join(dest_task_path, "solutions")
            solutions_codes_dir = os.path.join(solutions_dir, "Codes")
            solutions_editorial_dir = os.path.join(solutions_dir, "editorial")
            subtasks_dir = os.path.join(dest_task_path, "subtasks")

            os.makedirs(statements_dir, exist_ok=True)
            os.makedirs(graders_dir, exist_ok=True)
            os.makedirs(checkers_dir, exist_ok=True)
            os.makedirs(tests_dir, exist_ok=True)
            os.makedirs(attachments_dir, exist_ok=True)
            os.makedirs(solutions_dir, exist_ok=True)
            os.makedirs(solutions_codes_dir, exist_ok=True)
            os.makedirs(solutions_editorial_dir, exist_ok=True)
            os.makedirs(subtasks_dir, exist_ok=True)

            # 1. Copy Statement
            if task_name in task_statement_files:
                statement_src = task_statement_files[task_name]
                try:
                    shutil.copy2(statement_src, statements_dir)
                    print(f"    Copied statement: {statement_src} to {statements_dir}")
                except Exception as e:
                    print(f"    Error copying statement {statement_src}: {e}")
            else:
                 print(f"    Warning: No statement PDF found for task {task_name}.")


            # 2. Copy Tests
            if test_data_source == 'dir':
                source_test_task_dir = os.path.join(test_data_extracted_dir, task_name)
                if os.path.isdir(source_test_task_dir):
                    print(f"    Copying tests from directory {source_test_task_dir}...")
                    copy_files(source_test_task_dir, tests_dir)
                else:
                    print(f"    Warning: Task test data directory not found: {source_test_task_dir}")
            elif test_data_source == 'zip' and zip_file:
                 print(f"    Extracting tests from zip file for task {task_name}...")
                 extract_files_from_zip(zip_file, task_name, tests_dir)
            else:
                 print(f"    No test data source available for task {task_name}.")


            # 3. Look for Graders, Checkers, Solutions, Attachments (in day folder or test data folder)
            # Define search patterns
            grader_patterns = [f"grader.*", f"{task_name}_grader.*"]
            checker_patterns = ["checker.*", "chk.*", f"{task_name}_checker.*", f"{task_name}_chk.*"]
            # Solution patterns (less likely in this structure, but check)
            solution_code_patterns = ["*.cpp", "*.c", "*.pas", "*.java", "*.py"] # Add more if needed
            # Task-specific editorial/attachment patterns (besides statement pdf)
            task_doc_patterns = [f"{task_name}.*", f"{task_name}_*.*"]


            # Search locations
            search_paths = [source_day_path]
            if test_data_source == 'dir':
                 source_test_task_dir = os.path.join(test_data_extracted_dir, task_name)
                 if os.path.isdir(source_test_task_dir):
                    search_paths.append(source_test_task_dir) # Also search inside task's test folder

            found_grader = False
            found_checker = False
            found_solution_code = False

            for search_dir in search_paths:
                if not os.path.isdir(search_dir): continue

                # Find Graders
                for pattern in grader_patterns:
                    for file_path in glob.glob(os.path.join(search_dir, pattern)):
                        if os.path.isfile(file_path):
                            try:
                                shutil.copy2(file_path, graders_dir)
                                print(f"    Copied grader: {file_path} to {graders_dir}")
                                found_grader = True
                            except Exception as e:
                                print(f"    Error copying grader {file_path}: {e}")

                # Find Checkers
                for pattern in checker_patterns:
                     for file_path in glob.glob(os.path.join(search_dir, pattern)):
                         if os.path.isfile(file_path):
                            try:
                                shutil.copy2(file_path, checkers_dir)
                                print(f"    Copied checker: {file_path} to {checkers_dir}")
                                found_checker = True
                            except Exception as e:
                                print(f"    Error copying checker {file_path}: {e}")

                # Find Solution Codes
                for pattern in solution_code_patterns:
                     for file_path in glob.glob(os.path.join(search_dir, pattern)):
                         # Avoid copying graders/checkers again if they match code patterns
                         basename = os.path.basename(file_path).lower()
                         is_grader = any(basename.startswith(p.replace('*','')) for p in ["grader.", f"{task_name}_grader."])
                         is_checker = any(basename.startswith(p.replace('*','')) for p in ["checker.", "chk.", f"{task_name}_checker.", f"{task_name}_chk."])

                         if os.path.isfile(file_path) and not is_grader and not is_checker:
                            try:
                                shutil.copy2(file_path, solutions_codes_dir)
                                print(f"    Copied solution code: {file_path} to {solutions_codes_dir}")
                                found_solution_code = True
                            except Exception as e:
                                print(f"    Error copying solution code {file_path}: {e}")

                # Find potential Attachments/Task Editorials (non-statement, non-grader, non-checker)
                # This is heuristic - might copy unwanted files if names are ambiguous
                for pattern in task_doc_patterns:
                    for file_path in glob.glob(os.path.join(search_dir, pattern)):
                         basename = os.path.basename(file_path)
                         # Skip if it's the statement pdf, a known grader/checker, or already copied code
                         statement_pdf_name = os.path.basename(task_statement_files.get(task_name, ''))
                         if os.path.isfile(file_path) and \
                            basename != statement_pdf_name and \
                            not os.path.exists(os.path.join(graders_dir, basename)) and \
                            not os.path.exists(os.path.join(checkers_dir, basename)) and \
                            not os.path.exists(os.path.join(solutions_codes_dir, basename)):

                            # Decide if it's an attachment or task editorial based on extension
                            if basename.lower().endswith(('.pdf', '.txt', '.html', '.md', '.doc', '.docx')):
                                target_dir = solutions_editorial_dir
                                type_desc = "editorial/doc"
                            else:
                                target_dir = attachments_dir # Other file types likely attachments
                                type_desc = "attachment"

                            try:
                                shutil.copy2(file_path, target_dir)
                                print(f"    Copied task {type_desc}: {file_path} to {target_dir}")
                            except Exception as e:
                                print(f"    Error copying task {type_desc} {file_path}: {e}")


            # Report missing components
            if not found_grader: print(f"    Note: No grader files found for task {task_name}.")
            if not found_checker: print(f"    Note: No checker files found for task {task_name}.")
            if not found_solution_code: print(f"    Note: No solution code files found for task {task_name}.")
            # Note: We don't expect task-specific editorials in the 2007 structure provided,
            # the main one is top-level solutions.pdf

        # Close zip file if it was opened
        if zip_file:
            zip_file.close()

    print(f"\nFinished processing IOI {year}.")

# --- Configuration ---
source_base = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI"
dest_base = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
year_to_process = "2007"

source_dir_year = os.path.join(source_base, year_to_process)

# --- Run Processing ---
if os.path.isdir(source_dir_year):
    process_ioi_year(source_dir_year, dest_base, year_to_process)
else:
    print(f"Error: Source directory not found: {source_dir_year}")