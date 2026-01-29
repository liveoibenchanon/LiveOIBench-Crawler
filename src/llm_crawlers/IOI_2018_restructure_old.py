import os
import shutil
import re

def safe_copy(src, dst):
    """Safely copies a file, creating destination directory if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"  Copied: {src} -> {dst}")
        return True
    except Exception as e:
        print(f"  Error copying {src} to {dst}: {e}")
        return False

def safe_copytree(src, dst):
    """Safely copies a directory tree, creating destination directory if needed."""
    try:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        # dirs_exist_ok=True requires Python 3.8+
        # If using older Python, remove existing dst dir first if necessary
        if os.path.exists(dst):
             print(f"  Destination exists, skipping copytree to avoid overwrite errors for now: {dst}")
             # Or alternatively: shutil.rmtree(dst) # Use with caution!
             # shutil.copytree(src, dst)
        else:
            shutil.copytree(src, dst) #, dirs_exist_ok=True) # Re-enable if Python 3.8+ is guaranteed
        # print(f"  Copied Tree: {src} -> {dst}")
        return True
    except Exception as e:
        print(f"  Error copying tree {src} to {dst}: {e}")
        return False

def process_ioi_2018(source_base, output_base_root):
    """
    Organizes IOI 2018 files from source_base to output_base_root/2018
    following the specified structure.
    """
    year = "2018"
    source_dir = os.path.join(source_base, year)
    output_dir = os.path.join(output_base_root, year)

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory not found: {source_dir}")
        return

    print(f"Processing IOI {year} data from: {source_dir}")
    print(f"Outputting processed data to: {output_dir}")

    # Ensure root output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # --- Process each day (day0, day1, day2) ---
    for day_folder_name in ["day0", "day1", "day2"]:
        source_day_path = os.path.join(source_dir, day_folder_name)
        output_day_path = os.path.join(output_dir, day_folder_name)

        if not os.path.isdir(source_day_path):
            print(f"Warning: Source directory {source_day_path} not found. Skipping.")
            continue

        print(f"\nProcessing {day_folder_name}...")
        os.makedirs(output_day_path, exist_ok=True)

        # --- Identify Tasks for the day ---
        tasks = set()
        task_source_paths = {} # Map task_name to its primary source folder (e.g., 2018/day1/combo)

        # 1. From subdirectories that look like task folders
        for item in os.listdir(source_day_path):
            item_path = os.path.join(source_day_path, item)
            if os.path.isdir(item_path):
                # Heuristic: Check for common subfolders/files within a task dir
                has_cpp = os.path.exists(os.path.join(item_path, "cpp"))
                has_java = os.path.exists(os.path.join(item_path, "java"))
                has_pas = os.path.exists(os.path.join(item_path, "pas"))
                has_in = os.path.exists(os.path.join(item_path, "in"))
                # road_service only has in/out directly under task folder
                is_road_service_structure = item == "road_service" and has_in and os.path.exists(os.path.join(item_path, "out"))

                if has_cpp or has_java or has_pas or has_in or is_road_service_structure:
                   task_name = item
                   tasks.add(task_name)
                   task_source_paths[task_name] = item_path

        # 2. From zip files at day level
        for item in os.listdir(source_day_path):
            if item.endswith(".zip"):
                task_name = item[:-4] # Remove .zip
                tasks.add(task_name)
                # If we haven't found a source path yet, it might be zip-only
                if task_name not in task_source_paths:
                    task_source_paths[task_name] = None # Mark as potentially zip-only or structureless

        # 3. From review pdfs at day level
        for item in os.listdir(source_day_path):
             if item.endswith("-review.pdf"):
                 task_name = item[:-12] # Remove -review.pdf
                 tasks.add(task_name)
                 if task_name not in task_source_paths:
                     task_source_paths[task_name] = None

        # 4. From statement pdfs in translations/dayN (especially for day0)
        source_translation_day_path = os.path.join(source_dir, "translations", day_folder_name)
        if os.path.isdir(source_translation_day_path):
            for item in os.listdir(source_translation_day_path):
                # Exclude reviews explicitly, use other PDFs as potential statements
                task_names = ["combo", "seats", "werewolf", "doll", "highway", "meetings"]
                if item.endswith(".pdf") and not item.endswith("-review.pdf"):
                     task_name = item[:-4] # Remove .pdf
                     if task_name not in task_names:
                        continue
                     tasks.add(task_name)
                     if task_name not in task_source_paths:
                         task_source_paths[task_name] = None # Could be statement-only in this view

        # Also check for PDFs/Reviews directly under day0 (practice)
        if day_folder_name == "day0":
             for item in os.listdir(source_day_path):
                 if item.endswith(".pdf"):
                     if item.endswith("-review.pdf"):
                          task_name = item[:-12]
                     else:
                          task_name = item[:-4]
                     tasks.add(task_name)
                     if task_name not in task_source_paths:
                         # Special check for road_service which has a folder but maybe not detected above
                         potential_path = os.path.join(source_day_path, task_name)
                         if os.path.isdir(potential_path):
                              task_source_paths[task_name] = potential_path
                         else:
                              task_source_paths[task_name] = None


        if not tasks:
            print(f"  No tasks identified for {day_folder_name}.")
            continue

        print(f"  Identified tasks: {sorted(list(tasks))}")

        # --- Process each identified task ---
        for task_name in sorted(list(tasks)):
            print(f"    Processing task: {task_name}")
            source_task_path = task_source_paths.get(task_name) # Unpacked task folder path, might be None
            output_task_path = os.path.join(output_day_path, task_name)

            # Create base task directories in output
            statements_dir = os.path.join(output_task_path, "statements")
            graders_dir = os.path.join(output_task_path, "graders")
            checkers_dir = os.path.join(output_task_path, "checkers")
            tests_dir = os.path.join(output_task_path, "tests")
            attachments_dir = os.path.join(output_task_path, "attachments")
            solutions_dir = os.path.join(output_task_path, "solutions")
            solutions_codes_dir = os.path.join(solutions_dir, "Codes")
            solutions_editorial_dir = os.path.join(solutions_dir, "editorial")
            subtasks_dir = os.path.join(output_task_path, "subtasks")

            os.makedirs(statements_dir, exist_ok=True)
            os.makedirs(graders_dir, exist_ok=True)
            os.makedirs(checkers_dir, exist_ok=True) # Create even if empty
            os.makedirs(tests_dir, exist_ok=True)
            os.makedirs(attachments_dir, exist_ok=True)
            os.makedirs(solutions_codes_dir, exist_ok=True)
            os.makedirs(solutions_editorial_dir, exist_ok=True)
            os.makedirs(subtasks_dir, exist_ok=True) # Create even if empty

            # --- 1. Copy Statements (PDFs) ---
            # Priority 1: translations/dayN/task.pdf
            statement_found = False
            statement_pdf_trans = os.path.join(source_dir, "translations", day_folder_name, f"{task_name}.pdf")
            if os.path.exists(statement_pdf_trans):
                safe_copy(statement_pdf_trans, os.path.join(statements_dir, f"{task_name}.pdf"))
                print(f"      Copied statement: {statement_pdf_trans}")
                statement_found = True

            # Priority 2: day0/task.pdf (for practice tasks)
            if not statement_found and day_folder_name == "day0":
                 statement_pdf_day0 = os.path.join(source_day_path, f"{task_name}.pdf")
                 if os.path.exists(statement_pdf_day0) and not statement_pdf_day0.endswith("-review.pdf"):
                    safe_copy(statement_pdf_day0, os.path.join(statements_dir, f"{task_name}.pdf"))
                    print(f"      Copied statement: {statement_pdf_day0}")
                    statement_found = True

            if not statement_found:
                 print(f"      Warning: Statement PDF for {task_name} not found in expected locations.")

            # --- 2. Copy Editorials/Reviews (PDFs) ---
            # Check dayN/task-review.pdf
            review_pdf = os.path.join(source_day_path, f"{task_name}-review.pdf")
            editorial_found = False
            if os.path.exists(review_pdf):
                safe_copy(review_pdf, os.path.join(solutions_editorial_dir, f"{task_name}-review.pdf"))
                print(f"      Copied editorial: {review_pdf}")
                editorial_found = True

            # Check day0/task-review.pdf (if not found above, specifically for day0 tasks)
            if not editorial_found and day_folder_name == "day0":
                review_pdf_day0_root = os.path.join(source_dir, "day0", f"{task_name}-review.pdf")
                if os.path.exists(review_pdf_day0_root):
                     safe_copy(review_pdf_day0_root, os.path.join(solutions_editorial_dir, f"{task_name}-review.pdf"))
                     print(f"      Copied editorial: {review_pdf_day0_root}")
                     editorial_found = True

            if not editorial_found:
                print(f"      Info: Editorial/Review PDF for {task_name} not found.")


            # --- 3. Copy Tests (in/out) ---
            tests_copied = False
            if source_task_path and os.path.isdir(source_task_path): # Check if unpacked folder exists
                source_in_path = os.path.join(source_task_path, "in")
                source_out_path = os.path.join(source_task_path, "out")

                # Copy files directly into tests_dir
                if os.path.isdir(source_in_path):
                    print(f"      Copying tests from {source_in_path}...")
                    for item in os.listdir(source_in_path):
                        safe_copy(os.path.join(source_in_path, item), os.path.join(tests_dir, item))
                        tests_copied = True
                if os.path.isdir(source_out_path):
                    print(f"      Copying tests from {source_out_path}...")
                    for item in os.listdir(source_out_path):
                        safe_copy(os.path.join(source_out_path, item), os.path.join(tests_dir, item))
                        tests_copied = True # Count as copied even if only input or output exists

            if not tests_copied:
                 print(f"      Warning: Test data (in/out) for {task_name} not found in {source_task_path or 'N/A'}.")

            # --- 4. Copy Attachments (Zips, Headers, Libs, Scripts) ---
            # Zip files from day level
            zip_file = os.path.join(source_day_path, f"{task_name}.zip")
            if os.path.exists(zip_file):
                safe_copy(zip_file, os.path.join(attachments_dir, f"{task_name}.zip"))
                print(f"      Copied attachment: {zip_file}")

            # Files from language folders (if source_task_path exists)
            if source_task_path and os.path.isdir(source_task_path):
                for lang in ["cpp", "pas", "java"]:
                    lang_path = os.path.join(source_task_path, lang)
                    if os.path.isdir(lang_path):
                        for item in os.listdir(lang_path):
                            item_path = os.path.join(lang_path, item)
                            is_attachment = False
                            # Headers (.h)
                            if item.endswith(".h"): # Includes task.h
                                 is_attachment = True
                            # Pascal Libs (*_lib.pas)
                            elif item.endswith("_lib.pas"):
                                 is_attachment = True
                            # Compile/Run Scripts (*.sh)
                            elif item.endswith(".sh"):
                                 is_attachment = True

                            if is_attachment:
                                 safe_copy(item_path, os.path.join(attachments_dir, item))
                                 print(f"      Copied attachment: {item_path}")


            # --- 5. Copy Graders ---
            graders_copied = False
            if source_task_path and os.path.isdir(source_task_path):
                for lang in ["cpp", "pas", "java"]:
                    lang_path = os.path.join(source_task_path, lang)
                    if os.path.isdir(lang_path):
                        # Handle variations like grader.cpp, grader.pas, grader.java
                        grader_file_name = f"grader.{lang}"
                        if lang == "pas": grader_file_name = "grader.pas"
                        if lang == "java": grader_file_name = "grader.java"

                        grader_file = os.path.join(lang_path, grader_file_name)
                        if os.path.exists(grader_file):
                            # Ensure we don't copy duplicates if naming is inconsistent
                            dest_grader_path = os.path.join(graders_dir, grader_file_name)
                            if not os.path.exists(dest_grader_path):
                                safe_copy(grader_file, dest_grader_path)
                                print(f"      Copied grader: {grader_file}")
                                graders_copied = True

            if not graders_copied and task_name != "road_service": # road_service is IO only
                print(f"      Info: Grader files for {task_name} not found.")


            # --- 6. Copy Solutions (Code) ---
            # Copy entire cpp/ pas/ java/ folders if they contain the main solution file
            solution_code_copied = False
            if source_task_path and os.path.isdir(source_task_path):
                for lang in ["cpp", "pas", "java"]:
                    lang_path = os.path.join(source_task_path, lang)
                    if os.path.isdir(lang_path):
                        # Check for task_name.lang, task_name.pas, task_name.java
                        solution_file_name = f"{task_name}.{lang}"
                        if lang == "pas": solution_file_name = f"{task_name}.pas"
                        if lang == "java": solution_file_name = f"{task_name}.java"

                        solution_file = os.path.join(lang_path, solution_file_name)

                        if os.path.exists(solution_file):
                             dest_lang_path = os.path.join(solutions_codes_dir, lang)
                             # Use copytree to copy the whole directory
                             # Make sure destination doesn't exist or use dirs_exist_ok=True (Py3.8+)
                             if not os.path.exists(dest_lang_path):
                                 if safe_copytree(lang_path, dest_lang_path):
                                     print(f"      Copied solution code folder: {lang_path} -> {dest_lang_path}")
                                     solution_code_copied = True
                             else:
                                  print(f"      Skipping copytree, destination exists: {dest_lang_path}")


            if not solution_code_copied and task_name != "road_service": # road_service is IO only
                 print(f"      Warning: Solution code folder for task {task_name} not found or not copied.")

    print("\nScript finished.")

# --- Configuration ---
# Source directory containing the '2018' folder
SOURCE_IOI_BENCH_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI"
# Root directory where the processed '2018' folder will be created
OUTPUT_PROCESSED_DIR = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"

# --- Run the processing ---
process_ioi_2018(SOURCE_IOI_BENCH_DIR, OUTPUT_PROCESSED_DIR)