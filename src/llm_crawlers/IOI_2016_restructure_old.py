import os
import shutil
import glob
import json
import re

SOURCE_ROOT = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2016"
DEST_ROOT = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"
YEAR = "2016"

# Helper function to copy files, creating destination directory if needed
def copy_file(src, dst_folder, dst_filename=None):
    """Copies a source file to a destination folder.

    Args:
        src (str): Path to the source file.
        dst_folder (str): Path to the destination folder.
        dst_filename (str, optional): New name for the file in the destination.
                                      Defaults to the original filename.
    """
    if not os.path.exists(src):
        print(f"Warning: Source file not found: {src}")
        return
    os.makedirs(dst_folder, exist_ok=True)
    dst_path = os.path.join(dst_folder, dst_filename if dst_filename else os.path.basename(src))
    try:
        shutil.copy2(src, dst_path)
        # print(f"Copied: {src} -> {dst_path}")
    except Exception as e:
        print(f"Error copying {src} to {dst_path}: {e}")

# Helper function to copy directory contents recursively
def copy_directory_contents(src_dir, dst_dir):
    """Copies contents of src_dir to dst_dir recursively."""
    if not os.path.isdir(src_dir):
        # print(f"Warning: Source directory not found or not a directory: {src_dir}")
        return
    os.makedirs(dst_dir, exist_ok=True)
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dst_dir, item)
        if os.path.isdir(s):
            copy_directory_contents(s, d) # Recurse for subdirectories
        else:
            try:
                shutil.copy2(s, d)
                # print(f"Copied: {s} -> {d}")
            except Exception as e:
                print(f"Error copying file {s} to {d}: {e}")


def process_ioi_data(source_root, dest_root, year):
    """Processes IOI data from source structure to destination structure."""
    print(f"Starting processing for year {year}...")
    dest_year_dir = os.path.join(dest_root, year)
    os.makedirs(dest_year_dir, exist_ok=True)

    # 1. Process Global Editorial (if any)
    print("Processing global editorial...")
    global_editorial_src = os.path.join(source_root, "translations", "IOI2016_analysis.pdf")
    global_editorial_dest = os.path.join(dest_year_dir, "editorial")
    if os.path.exists(global_editorial_src):
        copy_file(global_editorial_src, global_editorial_dest)
    else:
        print("Warning: Global editorial 'IOI2016_analysis.pdf' not found.")

    # 2. Process Days (day0, day1, day2)
    day_folders = sorted([d for d in os.listdir(source_root) if d.startswith("day") and os.path.isdir(os.path.join(source_root, d))])

    for day in day_folders:
        print(f"\nProcessing {day}...")
        source_day_dir = os.path.join(source_root, day)
        dest_day_dir = os.path.join(dest_year_dir, day)
        os.makedirs(dest_day_dir, exist_ok=True)

        # Find task folders within the day directory
        tasks = [t for t in os.listdir(source_day_dir) if os.path.isdir(os.path.join(source_day_dir, t))]
        # Find task zip files to potentially add as attachments
        task_zips = glob.glob(os.path.join(source_day_dir, "*.zip"))

        for task_name in tasks:
            print(f"  Processing task: {task_name}...")
            source_task_dir = os.path.join(source_day_dir, task_name)
            dest_task_dir = os.path.join(dest_day_dir, task_name)

            # Create standard destination subdirectories
            statements_dir = os.path.join(dest_task_dir, "statements")
            graders_dir = os.path.join(dest_task_dir, "graders")
            checkers_dir = os.path.join(dest_task_dir, "checkers")
            tests_dir = os.path.join(dest_task_dir, "tests")
            attachments_dir = os.path.join(dest_task_dir, "attachments")
            solutions_dir = os.path.join(dest_task_dir, "solutions")
            solutions_codes_dir = os.path.join(solutions_dir, "Codes")
            solutions_editorial_dir = os.path.join(solutions_dir, "editorial")
            subtasks_dir = os.path.join(dest_task_dir, "subtasks") # Will likely remain empty

            os.makedirs(statements_dir, exist_ok=True)
            os.makedirs(graders_dir, exist_ok=True)
            os.makedirs(checkers_dir, exist_ok=True)
            os.makedirs(tests_dir, exist_ok=True)
            os.makedirs(attachments_dir, exist_ok=True)
            os.makedirs(solutions_codes_dir, exist_ok=True)
            os.makedirs(solutions_editorial_dir, exist_ok=True)
            os.makedirs(subtasks_dir, exist_ok=True)

            # a. Process Statements
            statement_pdf_src = os.path.join(source_root, "translations", day, f"{task_name}.pdf")
            if os.path.exists(statement_pdf_src):
                copy_file(statement_pdf_src, statements_dir)
            else:
                 print(f"    Warning: Statement PDF not found at {statement_pdf_src}")
                 # Check for alternative locations if needed (e.g., inside task dir)
                 alt_pdfs = glob.glob(os.path.join(source_task_dir, f"{task_name}.pdf")) # Less common
                 if alt_pdfs:
                     copy_file(alt_pdfs[0], statements_dir)
                 else:
                    print(f"    Warning: No statement PDF found for {task_name}")


            # b. Process Graders
            public_dir_src = os.path.join(source_task_dir, "public")
            graders_dir_src = os.path.join(source_task_dir, "files") # Primarily for day0

            # # Check public directory (common structure)
            # if os.path.isdir(public_dir_src):
            #     for lang_dir in os.listdir(public_dir_src):
            #         lang_path = os.path.join(public_dir_src, lang_dir)
            #         if os.path.isdir(lang_path):
            #             # Copy graders and necessary headers/libraries
            #             for pattern in ["grader.*", "*.h", "*_c.h", "graderlib.pas"]:
            #                 for grader_file in glob.glob(os.path.join(lang_path, pattern)):
            #                     copy_file(grader_file, graders_dir)

            # Check specific graders directory (day0 structure)
            print(graders_dir_src)
            if os.path.isdir(graders_dir_src):
                    # Copy graders and necessary headers/libraries
                    for pattern in ["grader.*", "*.h", "*_c.h", "graderlib.pas"]:
                        for grader_file in glob.glob(os.path.join(graders_dir_src, pattern)):
                            copy_file(grader_file, graders_dir)
                            print(f"    Copied grader file: {grader_file} to {graders_dir}")

            # c. Process Checkers
            checker_patterns = ["check.cpp", "check.exe", "compile_checker.sh", "compile-checker.sh", "Check.jar", "Check.java", "testlib.h", "testlib4j.jar"]
            for pattern in checker_patterns:
                 for checker_file in glob.glob(os.path.join(source_task_dir, pattern)):
                     copy_file(checker_file, checkers_dir)
            copy_file(os.path.join(graders_dir_src, "testlib.h"), checkers_dir) # Copy testlib.h from graders directory

            # d. Process Tests
            # Copy main tests folder
            task_tests_src = os.path.join(source_task_dir, "tests")
            copy_directory_contents(task_tests_src, tests_dir)

            # Copy public-tests folder contents
            public_tests_src = os.path.join(source_task_dir, "public-tests")
            copy_directory_contents(public_tests_src, tests_dir)

            # Copy public/examples folder contents
            public_examples_src = os.path.join(public_dir_src, "examples")
            copy_directory_contents(public_examples_src, tests_dir)


            # e. Process Attachments
            # Copy non-grader/non-header files from public/*/
            if os.path.isdir(public_dir_src):
                copy_directory_contents(public_dir_src, attachments_dir)

            # Copy files from task documents/ folder (as attachments AND solution editorials)
            documents_src = os.path.join(source_task_dir, "documents")
            if os.path.isdir(documents_src):
                for doc_file in glob.glob(os.path.join(documents_src, "*.txt")):
                     copy_file(doc_file, solutions_editorial_dir) # Also copy to solution editorial

            # Copy non-grader files from day0 solutions/ folder (templates)
            day0_solutions_src = os.path.join(source_task_dir, "solutions")
            if day == "day0" and os.path.isdir(day0_solutions_src):
                 for item in os.listdir(day0_solutions_src):
                     item_path = os.path.join(day0_solutions_src, item)
                     if os.path.isfile(item_path):
                         base, ext = os.path.splitext(item)
                         is_grader_related = (base.startswith("grader") or
                                             ext in ['.h'] or
                                             item == "graderlib.pas" or
                                             base.endswith("_c") and ext == ".h")
                         if not is_grader_related:
                            copy_file(item_path, attachments_dir)


            # Copy task-specific zip file found at day level
            for zip_file in task_zips:
                if os.path.basename(zip_file).startswith(task_name):
                    copy_file(zip_file, attachments_dir)

            # f. Process Solutions (Codes)
            solutions_submit_src = os.path.join(source_task_dir, "solutions-to-submit")
            if os.path.isdir(solutions_submit_src):
                for sol_dir_name in os.listdir(solutions_submit_src):
                    sol_dir_path = os.path.join(solutions_submit_src, sol_dir_name)

                    if os.path.isdir(sol_dir_path) and sol_dir_name.endswith(".dir"):
                        # Try to find a file matching the task name
                        code_files = glob.glob(os.path.join(sol_dir_path, f"{task_name}.*"))

                        # If not found, try any common source code extension
                        if not code_files:
                            code_files = (
                                glob.glob(os.path.join(sol_dir_path, "*.cpp")) +
                                glob.glob(os.path.join(sol_dir_path, "*.c")) +
                                glob.glob(os.path.join(sol_dir_path, "*.java")) +
                                glob.glob(os.path.join(sol_dir_path, "*.pas"))
                            )

                        if code_files:
                            source_code_path = code_files[0]
                            dest_filename_base = sol_dir_name[:-4]  # Strip ".dir"
                            _, ext = os.path.splitext(source_code_path)
                            dest_filename = f"{dest_filename_base}"
                            copy_file(source_code_path, solutions_codes_dir, dest_filename)
                        else:
                            print(f"    Warning: No code file found in solution directory: {sol_dir_path}")


            # g. Process problem.xml (copy as is)
            problem_xml_src = os.path.join(source_task_dir, "problem.xml")
            if os.path.exists(problem_xml_src):
                 copy_file(problem_xml_src, dest_task_dir)
            # The request mentioned problem.json, but the source has problem.xml.
            # We copy the xml file. Conversion could be a separate step if needed.

            # h. Subtasks - No clear source for this, leaving directory empty.

            print(f"    Finished task: {task_name}")

    print(f"\nFinished processing year {year}.")


# --- Main Execution ---
if __name__ == "__main__":
    if not os.path.isdir(SOURCE_ROOT):
        print(f"Error: Source directory not found: {SOURCE_ROOT}")
    else:
        process_ioi_data(SOURCE_ROOT, DEST_ROOT, YEAR)
        print(f"\nProcessing complete. Output saved to: {os.path.join(DEST_ROOT, YEAR)}")