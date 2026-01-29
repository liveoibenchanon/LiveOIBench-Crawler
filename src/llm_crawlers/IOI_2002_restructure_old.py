import os
import shutil
import zipfile
import glob

# Configuration
SOURCE_ROOT = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI/2002'
OUTPUT_ROOT = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-Processed-2/'
YEAR = '2002'

OUTPUT_YEAR_DIR = os.path.join(OUTPUT_ROOT, YEAR)
TEMP_EXTRACT_DIR = os.path.join(OUTPUT_ROOT, 'temp_extract_2002')

# Helper function to safely create directories
def ensure_dir(dir_path):
    os.makedirs(dir_path, exist_ok=True)

# Helper function to copy files
def copy_file(src_path, dest_dir, dest_filename=None):
    if not os.path.exists(src_path):
        print(f"Warning: Source file not found: {src_path}")
        return
    ensure_dir(dest_dir)
    dest_path = os.path.join(dest_dir, dest_filename if dest_filename else os.path.basename(src_path))
    try:
        shutil.copy2(src_path, dest_path)
        # print(f"Copied: {src_path} -> {dest_path}")
    except Exception as e:
        print(f"Error copying {src_path} to {dest_path}: {e}")

# Helper function to extract zip files
def extract_zip(zip_path, extract_to):
    if not os.path.exists(zip_path):
        print(f"Warning: Zip file not found: {zip_path}")
        return False
    try:
        ensure_dir(extract_to)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Extracted: {zip_path} -> {extract_to}")
        return True
    except zipfile.BadZipFile:
        print(f"Error: Bad zip file: {zip_path}")
        return False
    except Exception as e:
        print(f"Error extracting {zip_path}: {e}")
        return False

# --- Cleanup and Setup ---
if os.path.exists(OUTPUT_YEAR_DIR):
    shutil.rmtree(OUTPUT_YEAR_DIR)
    print(f"Removed existing output directory: {OUTPUT_YEAR_DIR}")
if os.path.exists(TEMP_EXTRACT_DIR):
    shutil.rmtree(TEMP_EXTRACT_DIR)
    print(f"Removed existing temp directory: {TEMP_EXTRACT_DIR}")

ensure_dir(OUTPUT_YEAR_DIR)
ensure_dir(TEMP_EXTRACT_DIR)
ensure_dir(os.path.join(OUTPUT_YEAR_DIR, 'editorial')) # Create root editorial dir

# --- Extract Archives ---
print("\n--- Extracting Archives ---")
extract_zip(os.path.join(SOURCE_ROOT, 'day0material.zip'), os.path.join(TEMP_EXTRACT_DIR, 'day0material'))
extract_zip(os.path.join(SOURCE_ROOT, 'day0extra.zip'), os.path.join(TEMP_EXTRACT_DIR, 'day0extra'))
extract_zip(os.path.join(SOURCE_ROOT, 'day1', 'day1-input+solution.zip'), os.path.join(TEMP_EXTRACT_DIR, 'day1-input+solution'))
extract_zip(os.path.join(SOURCE_ROOT, 'day2', 'day2-input+solution.zip'), os.path.join(TEMP_EXTRACT_DIR, 'day2-input+solution'))

# Handle potential nested folder in extracted zips
# e.g., day1-input+solution.zip might contain a folder named 'day1-input+solution'
def find_extracted_base(extract_path, expected_folder_name):
    content = os.listdir(extract_path)
    if len(content) == 1 and os.path.isdir(os.path.join(extract_path, content[0])) and content[0] == expected_folder_name:
        return os.path.join(extract_path, content[0])
    return extract_path

day1_data_base = find_extracted_base(os.path.join(TEMP_EXTRACT_DIR, 'day1-input+solution'), 'day1-input+solution')
day2_data_base = find_extracted_base(os.path.join(TEMP_EXTRACT_DIR, 'day2-input+solution'), 'day2-input+solution')


# --- Process Root Editorial Files ---
print("\n--- Processing Root Editorial Files ---")
root_editorial_dir = os.path.join(OUTPUT_YEAR_DIR, 'editorial')
for pdf_file in glob.glob(os.path.join(SOURCE_ROOT, '*.pdf')):
    copy_file(pdf_file, root_editorial_dir)

# --- Process Day 0 (Practice) ---
print("\n--- Processing Day 0 ---")
day0_dir = os.path.join(OUTPUT_YEAR_DIR, 'day0')
ensure_dir(day0_dir)

# Day 0 General Attachments (from day0material)
day0_material_src = os.path.join(TEMP_EXTRACT_DIR, 'day0material')
if os.path.exists(day0_material_src):
    day0_attachments_dir = os.path.join(day0_dir, 'attachments_general') # Keep separate initially
    ensure_dir(day0_attachments_dir)
    for item in os.listdir(day0_material_src):
        s = os.path.join(day0_material_src, item)
        if os.path.isfile(s):
            copy_file(s, day0_attachments_dir)
        elif os.path.isdir(s):
             # If directories exist, copy them entirely for now, might need manual sorting
             shutil.copytree(s, os.path.join(day0_attachments_dir, item), dirs_exist_ok=True)
    print("Processed day0material contents as general attachments.")


# Day 0 Extra Tasks (red, string)
day0_extra_src = os.path.join(TEMP_EXTRACT_DIR, 'day0extra', 'day0extra') # The zip might contain a 'day0extra' folder

if os.path.exists(day0_extra_src):
    # Task: red
    task_name = 'red'
    task_dir = os.path.join(day0_dir, task_name)
    red_src_dir = os.path.join(day0_extra_src, 'red')
    if os.path.exists(red_src_dir):
        print(f"Processing task: {task_name}")
        ensure_dir(task_dir)
        # Tests
        tests_dir = os.path.join(task_dir, 'tests')
        ensure_dir(tests_dir)
        for test_file in glob.glob(os.path.join(red_src_dir, '*.in')):
            copy_file(test_file, tests_dir)
        # No obvious statements, solutions, graders here

    # Task: string
    task_name = 'string'
    task_dir = os.path.join(day0_dir, task_name)
    string_src_dir = os.path.join(day0_extra_src, 'string')
    if os.path.exists(string_src_dir):
        print(f"Processing task: {task_name}")
        ensure_dir(task_dir)

        statements_dir = os.path.join(task_dir, 'statements')
        graders_dir = os.path.join(task_dir, 'graders')
        attachments_dir = os.path.join(task_dir, 'attachments')
        solutions_dir = os.path.join(task_dir, 'solutions', 'Codes')
        editorial_dir = os.path.join(task_dir, 'solutions', 'editorial')

        # Check day0material for potential statements (Manual step might be needed)
        # Example: If 'string.pdf' was in day0material
        # string_pdf_path = os.path.join(day0_attachments_dir, 'string.pdf')
        # if os.path.exists(string_pdf_path):
        #     copy_file(string_pdf_path, statements_dir)
        # else:
        #     print(f"Warning: No statement found for task {task_name} in day0material.")


        # Graders & Attachments from lib folders
        for platform in ['linux', 'windows']:
            platform_src = os.path.join(string_src_dir, platform)
            if os.path.exists(platform_src):
                for lang in ['lib_c', 'lib_p']:
                    lib_src = os.path.join(platform_src, lang)
                    if os.path.exists(lib_src):
                        platform_grader_dir = os.path.join(graders_dir, platform, lang)
                        platform_attach_dir = os.path.join(attachments_dir, platform, lang) # Copy test harnesses here too

                        for item in os.listdir(lib_src):
                            item_path = os.path.join(lib_src, item)
                            if item.endswith(('.o', '.ppu', '.h')):
                                copy_file(item_path, platform_grader_dir)
                            elif item in ('lib_test.c', 'lib_test.pas'):
                                copy_file(item_path, platform_attach_dir)
                                # Also copy to grader dir? Maybe not needed if contestants compile locally.
                                # copy_file(item_path, platform_grader_dir)
                            else:
                                print(f"Warning: Uncategorized file in {lib_src}: {item}")

        # Source code (oracle/library source)
        string_source_dir = os.path.join(string_src_dir, 'source')
        if os.path.exists(string_source_dir):
            # Copy whole source dir to Solutions/Codes
            target_sol_code_dir = os.path.join(solutions_dir, 'source')
            shutil.copytree(string_source_dir, target_sol_code_dir, dirs_exist_ok=True)
            print(f"Copied source code: {string_source_dir} -> {target_sol_code_dir}")
            # Also copy oracle.h to grader dir? It's often needed.
            oracle_h = os.path.join(string_source_dir, 'oracle.h')
            if os.path.exists(oracle_h):
                 copy_file(oracle_h, graders_dir)
            # Copy README to attachments or editorial
            readme_path = os.path.join(string_source_dir, 'README.txt')
            if os.path.exists(readme_path):
                copy_file(readme_path, attachments_dir) # Let's put README in attachments

# --- Process Day 1 ---
print("\n--- Processing Day 1 ---")
day1_dir = os.path.join(OUTPUT_YEAR_DIR, 'day1')
ensure_dir(day1_dir)
day1_src_root = os.path.join(SOURCE_ROOT, 'day1')

# Day 1 Overview
for overview_file in glob.glob(os.path.join(day1_src_root, 'overview1.*')):
    copy_file(overview_file, root_editorial_dir)

# Day 1 Tasks
for task_name in ['utopia', 'frog', 'xor']:
    task_dir = os.path.join(day1_dir, task_name)
    task_src_dir = os.path.join(day1_src_root, task_name)
    print(f"Processing task: {task_name}")
    ensure_dir(task_dir)

    statements_dir = os.path.join(task_dir, 'statements')
    tests_dir = os.path.join(task_dir, 'tests')
    solutions_dir = os.path.join(task_dir, 'solutions', 'Codes')
    editorial_dir = os.path.join(task_dir, 'solutions', 'editorial')
    attachments_dir = os.path.join(task_dir, 'attachments') # Added for consistency

    # Statements and Task-specific Editorial/Docs
    found_handout = False
    if os.path.exists(task_src_dir):
        for f in glob.glob(os.path.join(task_src_dir, f'{task_name}*.*')):
            if f.endswith('-handout.pdf'):
                copy_file(f, statements_dir)
                found_handout = True
            elif f.endswith('.pdf') or f.endswith('.doc'):
                 # Assume other pdf/doc are editorial/extra info
                 copy_file(f, editorial_dir)
            else:
                 copy_file(f, attachments_dir) # Catch any other files

    if not found_handout:
         print(f"Warning: Handout PDF not found for task {task_name} in {task_src_dir}")

    # Tests and Solutions from extracted zip
    task_data_src = os.path.join(day1_data_base, task_name) if day1_data_base and os.path.exists(os.path.join(day1_data_base, task_name)) else None

    # Fallback: Sometimes the task data is directly in the base, not a subfolder
    if not task_data_src and day1_data_base:
         # Check if files like taskname.c or taskname01.in exist directly in day1_data_base
         if glob.glob(os.path.join(day1_data_base, f"{task_name}*.*")):
              task_data_src = day1_data_base # Use the base directory itself
         else:
             print(f"Warning: Could not find data directory for task {task_name} in {day1_data_base}")


    if task_data_src:
        print(f"Searching for tests/solutions in: {task_data_src}")
        ensure_dir(tests_dir)
        ensure_dir(solutions_dir)
        ensure_dir(editorial_dir)

        # Heuristic categorization of files within the data folder
        for item in os.listdir(task_data_src):
            item_path = os.path.join(task_data_src, item)
            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                # Tests (Common IOI extensions)
                if ext in ['.in', '.dat', '.inp']:
                    copy_file(item_path, tests_dir)
                elif ext in ['.out', '.ans', '.sol', '.diff']: # Expected outputs or diffs
                     # Check if it's a solution code file first
                    if item.startswith(task_name) and ext in ['.c', '.cpp', '.pas', '.java']:
                        copy_file(item_path, solutions_dir)
                    else:
                        copy_file(item_path, tests_dir) # Assume it's test output data
                # Solutions (Source code)
                elif ext in ['.c', '.cpp', '.pas', '.java', '.py', '.cs']:
                     # Simple check if filename relates to task name (or common names)
                     fn_lower = item.lower()
                     if task_name in fn_lower or 'sol' in fn_lower or 'main' in fn_lower:
                          copy_file(item_path, solutions_dir)
                     else: # Otherwise, maybe attachment or tool?
                          copy_file(item_path, attachments_dir)
                # Editorials / Notes
                elif ext in ['.txt', '.pdf', '.doc', '.html'] and ('sol' in item.lower() or 'readme' in item.lower() or 'notes' in item.lower()):
                     copy_file(item_path, editorial_dir)
                # Other files -> attachments
                else:
                    copy_file(item_path, attachments_dir)
            elif os.path.isdir(item_path):
                # If there are subdirs, copy them to attachments for now, needs manual check
                print(f"Info: Copying subdirectory '{item}' to attachments for task {task_name}")
                shutil.copytree(item_path, os.path.join(attachments_dir, item), dirs_exist_ok=True)

    else:
        print(f"Warning: No specific test/solution data found for task {task_name} after extraction.")


# --- Process Day 2 ---
print("\n--- Processing Day 2 ---")
day2_dir = os.path.join(OUTPUT_YEAR_DIR, 'day2')
ensure_dir(day2_dir)
day2_src_root = os.path.join(SOURCE_ROOT, 'day2')

# Day 2 Overview
for overview_file in glob.glob(os.path.join(day2_src_root, 'overview2.*')):
    copy_file(overview_file, root_editorial_dir)

# Day 2 Tasks
for task_name in ['rods', 'batch', 'bus']:
    task_dir = os.path.join(day2_dir, task_name)
    task_src_dir = os.path.join(day2_src_root, task_name)
    print(f"Processing task: {task_name}")
    ensure_dir(task_dir)

    statements_dir = os.path.join(task_dir, 'statements')
    tests_dir = os.path.join(task_dir, 'tests')
    graders_dir = os.path.join(task_dir, 'graders')
    solutions_dir = os.path.join(task_dir, 'solutions', 'Codes')
    editorial_dir = os.path.join(task_dir, 'solutions', 'editorial')
    attachments_dir = os.path.join(task_dir, 'attachments')

    # Statements and Task-specific Editorial/Docs
    found_handout = False
    if os.path.exists(task_src_dir):
        for f in glob.glob(os.path.join(task_src_dir, f'{task_name}*.*')):
             if f.endswith('-handout.pdf'):
                 copy_file(f, statements_dir)
                 found_handout = True
             elif f.endswith('.pdf') or f.endswith('.doc'):
                 copy_file(f, editorial_dir)
             else:
                 copy_file(f, attachments_dir)

    if not found_handout:
         print(f"Warning: Handout PDF not found for task {task_name} in {task_src_dir}")


    # Tests and Solutions from extracted zip
    task_data_src = os.path.join(day2_data_base, task_name) if day2_data_base and os.path.exists(os.path.join(day2_data_base, task_name)) else None

     # Fallback: Check if files like taskname.c or taskname01.in exist directly in day2_data_base
    if not task_data_src and day2_data_base:
        if glob.glob(os.path.join(day2_data_base, f"{task_name}*.*")) or (task_name == 'rods' and os.path.exists(os.path.join(day2_data_base, 'rods.library'))): # Special case for rods library
            task_data_src = day2_data_base # Use the base directory itself
        else:
            print(f"Warning: Could not find data directory for task {task_name} in {day2_data_base}")


    if task_data_src:
        print(f"Searching for tests/solutions/graders in: {task_data_src}")
        ensure_dir(tests_dir)
        ensure_dir(solutions_dir)
        ensure_dir(editorial_dir)
        ensure_dir(graders_dir)
        ensure_dir(attachments_dir)

        # Process files and potential library folder
        for item in os.listdir(task_data_src):
            item_path = os.path.join(task_data_src, item)
            if os.path.isfile(item_path):
                ext = os.path.splitext(item)[1].lower()
                 # Basic categorization (similar to Day 1)
                if ext in ['.in', '.dat', '.inp']:
                    copy_file(item_path, tests_dir)
                elif ext in ['.out', '.ans', '.sol', '.diff']:
                    if item.startswith(task_name) and ext in ['.c', '.cpp', '.pas', '.java']:
                         copy_file(item_path, solutions_dir)
                    else:
                         copy_file(item_path, tests_dir)
                elif ext in ['.c', '.cpp', '.pas', '.java', '.py', '.cs']:
                     fn_lower = item.lower()
                     if task_name in fn_lower or 'sol' in fn_lower or 'main' in fn_lower:
                          copy_file(item_path, solutions_dir)
                     else: # Otherwise, maybe attachment or tool? Check common grader tool names
                         if any(toolname in fn_lower for toolname in ['tool', 'gen', 'check', 'validator']):
                              copy_file(item_path, graders_dir) # Assume it's a grader tool
                         else:
                              copy_file(item_path, attachments_dir)
                elif ext in ['.txt', '.pdf', '.doc', '.html'] and ('sol' in item.lower() or 'readme' in item.lower() or 'notes' in item.lower()):
                     copy_file(item_path, editorial_dir)
                elif ext in ['.h', '.o', '.ppu']: # Likely grader/library components
                     copy_file(item_path, graders_dir)
                else:
                    copy_file(item_path, attachments_dir)

            elif os.path.isdir(item_path):
                # Special handling for rods.library
                if task_name == 'rods' and item == 'rods.library':
                    print(f"Processing rods.library: {item_path}")
                    rods_lib_src = item_path
                    for platform in ['WindowsXP', 'Linux']:
                        platform_src = os.path.join(rods_lib_src, platform)
                        if os.path.exists(platform_src):
                            platform_grader_dir = os.path.join(graders_dir, 'library', platform)
                            platform_attach_dir = os.path.join(attachments_dir, 'library', platform)

                            for lib_item in os.listdir(platform_src):
                                lib_item_path = os.path.join(platform_src, lib_item)
                                lib_ext = os.path.splitext(lib_item)[1].lower()
                                if lib_ext in ['.o', '.ppu', '.h']:
                                    copy_file(lib_item_path, platform_grader_dir)
                                elif lib_ext in ['.c', '.pas'] and 'tool' in lib_item.lower(): # Tool source code
                                    copy_file(lib_item_path, platform_grader_dir) # Put tool source in grader
                                    copy_file(lib_item_path, platform_attach_dir) # Also provide as attachment
                                elif lib_item == 'rods.in': # Input file specifically for the library/tool?
                                     copy_file(lib_item_path, platform_grader_dir, dest_filename=f'library_test_{platform}.in') # Store in grader with context
                                     copy_file(lib_item_path, tests_dir, dest_filename=f'rods_lib_test_{platform}.in') # Also put in main tests? Maybe confusing. Let's keep in grader dir primarily.
                                else:
                                     copy_file(lib_item_path, platform_attach_dir) # Other files as attachments

                else:
                    # Copy other subdirectories to attachments
                    print(f"Info: Copying subdirectory '{item}' to attachments for task {task_name}")
                    shutil.copytree(item_path, os.path.join(attachments_dir, item), dirs_exist_ok=True)

    else:
        print(f"Warning: No specific test/solution data found for task {task_name} after extraction.")


# --- Final Cleanup ---
print("\n--- Cleaning up temporary files ---")
try:
    shutil.rmtree(TEMP_EXTRACT_DIR)
    print(f"Removed temporary directory: {TEMP_EXTRACT_DIR}")
except Exception as e:
    print(f"Error removing temp directory {TEMP_EXTRACT_DIR}: {e}")

print("\n--- Processing Complete ---")
print(f"Output generated at: {OUTPUT_YEAR_DIR}")