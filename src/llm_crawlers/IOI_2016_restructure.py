import os
import shutil
import re
import json # Although not used for writing, it's good practice if problem.json was needed

def safe_copy(src, dst):
    """Copies a file from src to dst, creating destination directories if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"Copied: {src} -> {dst}")
    except FileNotFoundError:
        print(f"Warning: Source file not found - {src}")
    except Exception as e:
        print(f"Warning: Failed to copy {src} to {dst} - {e}")

def safe_copy_tree(src, dst):
    """Copies a directory tree from src to dst, creating destination directories."""
    try:
        # Ensure the parent directory of dst exists before calling copytree
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # If dst exists, copytree might fail. We might need to copy contents instead.
        # For simplicity here, let's assume dst doesn't exist or overwrite is desired.
        # A more robust approach might merge contents if dst exists.
        if os.path.exists(dst):
             # Simple merging: copy contents recursively
             for item in os.listdir(src):
                 s_item = os.path.join(src, item)
                 d_item = os.path.join(dst, item)
                 if os.path.isdir(s_item):
                     safe_copy_tree(s_item, d_item)
                 else:
                     safe_copy(s_item, d_item)
        else:
             shutil.copytree(src, dst, copy_function=shutil.copy2)
        # print(f"Copied folder: {src} -> {dst}")
    except FileNotFoundError:
        print(f"Warning: Source directory not found - {src}")
    except FileExistsError:
         # This can happen if called directly and dst exists. Re-try with merge logic.
         print(f"Warning: Destination {dst} exists, attempting merge.")
         try:
             for item in os.listdir(src):
                 s_item = os.path.join(src, item)
                 d_item = os.path.join(dst, item)
                 if os.path.isdir(s_item):
                     safe_copy_tree(s_item, d_item)
                 else:
                     safe_copy(s_item, d_item)
         except Exception as e_merge:
              print(f"Warning: Failed to merge {src} into {dst} - {e_merge}")

    except Exception as e:
        print(f"Warning: Failed to copy folder {src} to {dst} - {e}")

def main():
    source_base = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New/2016"
    output_base = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed/2016"

    print(f"Source base directory: {source_base}")
    print(f"Output base directory: {output_base}")

    if not os.path.isdir(source_base):
        print(f"Error: Source directory {source_base} not found.")
        return

    # Create the base output directory
    os.makedirs(output_base, exist_ok=True)
    print(f"Created base output directory: {output_base}")

    # --- Global Editorial ---
    global_editorial_src = os.path.join(source_base, "other_materials", "Solutions_to_all_problems.pdf")
    global_editorial_dst_dir = os.path.join(output_base, "editorial")
    if os.path.exists(global_editorial_src):
        print("Processing global editorial...")
        os.makedirs(global_editorial_dst_dir, exist_ok=True)
        safe_copy(global_editorial_src, os.path.join(global_editorial_dst_dir, os.path.basename(global_editorial_src)))
    else:
        print("Warning: Global editorial 'Solutions_to_all_problems.pdf' not found.")

    # --- Task Day Mapping ---
    # Determined by inspecting day1/ and day2/ PDF names
    day_map = {
        "molecules": "day1",
        "railroad": "day1",
        "shortcut": "day1",
        "paint": "day2",
        "messy": "day2",
        "aliens": "day2",
    }

    task_base_src = os.path.join(source_base, "other_materials", "TestCases")
    if not os.path.isdir(task_base_src):
        print(f"Error: Task base directory {task_base_src} not found.")
        return

    # --- Process Each Task ---
    tasks = [d for d in os.listdir(task_base_src) if os.path.isdir(os.path.join(task_base_src, d))]

    for task_name in tasks:
        print(f"\nProcessing task: {task_name}")
        task_name_lower = task_name.lower()

        if task_name_lower not in day_map:
            print(f"Warning: Day assignment not found for task '{task_name}'. Skipping.")
            continue

        day = day_map[task_name_lower]
        print(f"Assigned to: {day}")

        task_src_dir = os.path.join(task_base_src, task_name)
        task_dst_dir = os.path.join(output_base, day, task_name)

        # Create task directories
        statements_dst = os.path.join(task_dst_dir, "statements")
        graders_dst = os.path.join(task_dst_dir, "graders")
        checkers_dst = os.path.join(task_dst_dir, "checkers")
        tests_dst = os.path.join(task_dst_dir, "tests")
        attachments_dst = os.path.join(task_dst_dir, "attachments")
        solutions_codes_dst = os.path.join(task_dst_dir, "solutions", "Codes")
        solutions_editorial_dst = os.path.join(task_dst_dir, "solutions", "editorial")
        subtasks_dst = os.path.join(task_dst_dir, "subtasks") # Placeholder, might not be populated

        for d in [statements_dst, graders_dst, checkers_dst, tests_dst, attachments_dst, solutions_codes_dst, solutions_editorial_dst, subtasks_dst]:
            os.makedirs(d, exist_ok=True)

        # 1. Statements
        print("  Processing statements...")
        # Copy PDF from day1/day2 folder
        day_pdf_dir = os.path.join(source_base, day)
        statement_pdf_found = False
        if os.path.isdir(day_pdf_dir):
            for pdf_file in os.listdir(day_pdf_dir):
                # Match PDF name like "03_Shortcut.pdf" to task name "shortcut"
                # Use regex for robustness: match number, underscore, name (case-insensitive), .pdf
                match = re.match(r"\d+_(.+)\.pdf", pdf_file, re.IGNORECASE)
                if match and match.group(1).replace('_', '').lower() == task_name_lower.replace('_', ''):
                    src_pdf = os.path.join(day_pdf_dir, pdf_file)
                    safe_copy(src_pdf, os.path.join(statements_dst, pdf_file))
                    statement_pdf_found = True
                    break
        if not statement_pdf_found:
             print(f"  Warning: Statement PDF not found in {day_pdf_dir} for task {task_name}")

        # Copy description.txt from documents/ if exists
        doc_dir = os.path.join(task_src_dir, "documents")
        desc_file_src = os.path.join(doc_dir, "description.txt")
        if os.path.exists(desc_file_src):
            safe_copy(desc_file_src, os.path.join(statements_dst, "description.txt"))

        # 2. Graders and Attachments (from public/)
        print("  Processing graders and attachments...")
        public_src = os.path.join(task_src_dir, "public")
        if os.path.isdir(public_src):
            # Language subdirs (cpp, c, pas, java)
            for lang_dir in os.listdir(public_src):
                lang_src_path = os.path.join(public_src, lang_dir)
                if os.path.isdir(lang_src_path) and lang_dir not in ['examples']:
                    lang_graders_dst = os.path.join(graders_dst, lang_dir)
                    lang_attachments_dst = os.path.join(attachments_dst, lang_dir)
                    os.makedirs(lang_graders_dst, exist_ok=True)
                    os.makedirs(lang_attachments_dst, exist_ok=True)

                    for item in os.listdir(lang_src_path):
                        item_src = os.path.join(lang_src_path, item)
                        if os.path.isfile(item_src):
                            # Identify graders (grader.*, *.h)
                            if item.startswith("grader.") or item.endswith(".h") or item == "graderlib.pas": # Added specific pas lib
                                safe_copy(item_src, os.path.join(lang_graders_dst, item))
                            # Identify compile scripts and template code as attachments
                            elif item.startswith("compile_") or item == f"{task_name_lower}.{lang_dir}" or item == f"{task_name_lower}_c.h" or item == f"{task_name_lower}.c" or item == f"{task_name_lower}.java" or item == f"{task_name_lower}.pas" or item == f"{task_name_lower}.cpp":
                                 safe_copy(item_src, os.path.join(lang_attachments_dst, item))
                            else:
                                print(f"    Unclassified file in public/{lang_dir}: {item}. Placing in attachments.")
                                safe_copy(item_src, os.path.join(lang_attachments_dst, item))

            # Copy examples to tests
            examples_src = os.path.join(public_src, "examples")
            examples_dst = os.path.join(tests_dst, "examples")
            if os.path.isdir(examples_src):
                safe_copy_tree(examples_src, examples_dst)

        # 3. Checkers
        print("  Processing checkers...")
        checker_files = ["check.cpp", "check.exe", "compile_checker.sh", "compile-checker.sh"] # Added second compile script name
        for cf in checker_files:
            checker_src = os.path.join(task_src_dir, cf)
            if os.path.exists(checker_src):
                safe_copy(checker_src, os.path.join(checkers_dst, cf))

        # 4. Tests
        print("  Processing tests...")
        # Main tests
        main_tests_src = os.path.join(task_src_dir, "tests")
        if os.path.isdir(main_tests_src):
            # Copy contents into tests_dst directly
            safe_copy_tree(main_tests_src, tests_dst)
            # for item in os.listdir(main_tests_src):
            #     s = os.path.join(main_tests_src, item)
            #     d = os.path.join(tests_dst, item)
            #     if os.path.isdir(s):
            #         safe_copy_tree(s, d)
            #     else:
            #         safe_copy(s, d)

        # Public tests
        public_tests_src = os.path.join(task_src_dir, "public-tests")
        public_tests_dst = os.path.join(tests_dst, "public-tests")
        if os.path.isdir(public_tests_src):
             safe_copy_tree(public_tests_src, public_tests_dst)

        # Checker/Validator tests inside files/tests/ or tests/
        # The safe_copy_tree above should handle nested tests/ directories correctly.
        # Specifically handle files/tests/checker-tests or files/tests/validator-tests
        files_tests_src = os.path.join(task_src_dir, "files", "tests")
        if os.path.isdir(files_tests_src):
             safe_copy_tree(files_tests_src, os.path.join(tests_dst, "files_tests")) # Copy into a subfolder for clarity

        # 5. Attachments (files/)
        print("  Processing attachments (files/)...")
        files_src = os.path.join(task_src_dir, "files")
        files_dst = os.path.join(attachments_dst, "files") # Keep 'files' subfolder
        if os.path.isdir(files_src):
             # Avoid copying the 'tests' subdirectory again if it exists here
             os.makedirs(files_dst, exist_ok=True)
             for item in os.listdir(files_src):
                 s_item = os.path.join(files_src, item)
                 d_item = os.path.join(files_dst, item)
                 if item != 'tests': # Don't copy tests again
                     if os.path.isdir(s_item):
                         safe_copy_tree(s_item, d_item)
                     else:
                         safe_copy(s_item, d_item)

        # 6. Solutions (Code and Editorial)
        print("  Processing solutions...")
        # Code from solutions-to-submit/
        solutions_submit_src = os.path.join(task_src_dir, "solutions-to-submit")
        if os.path.isdir(solutions_submit_src):
            for sol_dir in os.listdir(solutions_submit_src):
                sol_dir_path = os.path.join(solutions_submit_src, sol_dir)
                if os.path.isdir(sol_dir_path) and sol_dir.endswith(".dir"):
                    # Find the code file inside
                    code_file_found = False
                    for root, _, files in os.walk(sol_dir_path):
                        for file in files:
                            # Basic check for common code extensions
                            if file.lower().endswith(('.cpp', '.c', '.java', '.pas')):
                                src_code_file = os.path.join(root, file)
                                # Construct a unique name: parentDirName_originalFileName
                                # Remove .dir suffix from parent dir name
                                base_sol_dir_name = sol_dir[:-4] if sol_dir.endswith(".dir") else sol_dir
                                dst_code_file_name = f"{base_sol_dir_name}_{file}"
                                dst_code_file_path = os.path.join(solutions_codes_dst, dst_code_file_name)
                                safe_copy(src_code_file, dst_code_file_path)
                                code_file_found = True
                                break # Assume one primary code file per .dir
                        if code_file_found:
                            break
                    if not code_file_found:
                         print(f"    Warning: No code file found in {sol_dir_path}")

        # Code from solutions/
        solutions_src = os.path.join(task_src_dir, "solutions")
        if os.path.isdir(solutions_src):
            for item in os.listdir(solutions_src):
                item_src = os.path.join(solutions_src, item)
                # Heuristic: copy files directly, assume they are solution files or related material
                # Avoid copying directories for now unless structure is known
                if os.path.isfile(item_src):
                    safe_copy(item_src, os.path.join(solutions_codes_dst, item))
                # else:
                #     print(f"    Skipping directory in solutions/: {item}")

        # Editorial from documents/
        tut_file_src = os.path.join(doc_dir, "tutorial.txt")
        if os.path.exists(tut_file_src):
            safe_copy(tut_file_src, os.path.join(solutions_editorial_dst, "tutorial.txt"))

        # 7. Problem XML -> JSON (or copy XML)
        print("  Processing problem metadata...")
        problem_xml_src = os.path.join(task_src_dir, "problem.xml")
        problem_xml_dst = os.path.join(task_dst_dir, "problem.xml") # Copy as XML as requested
        if os.path.exists(problem_xml_src):
            safe_copy(problem_xml_src, problem_xml_dst)

        print(f"Finished processing task: {task_name}")

    print("\nScript finished.")

if __name__ == "__main__":
    main()