import os
import shutil
import re
from pathlib import Path

# Configuration
SOURCE_ROOT = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI/2010")
OUTPUT_ROOT = Path(f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2")
YEAR = "2010"

# --- Helper Functions ---

def safe_copy(src, dst):
    """Safely copies a file, creating parent directories if needed."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        # print(f"  Copied: {src} -> {dst}")
    except Exception as e:
        print(f"  Error copying {src} to {dst}: {e}")

def safe_copytree(src, dst):
    """Safely copies a directory tree, creating parent directories."""
    try:
        dst.parent.mkdir(parents=True, exist_ok=True)
        # Avoid errors if dst already exists, but copy contents
        shutil.copytree(src, dst, dirs_exist_ok=True)
        # print(f"  Copied Tree: {src} -> {dst}")
    except Exception as e:
        print(f"  Error copying tree {src} to {dst}: {e}")

def classify_and_copy_file(file_path, source_task_root, target_task_dir, task_name_lower):
    """Classifies a file and copies it to the appropriate target location."""
    relative_path = file_path.relative_to(source_task_root)
    file_name_lower = file_path.name.lower()
    parent_dir_name_lower = file_path.parent.name.lower()
    file_suffix_lower = file_path.suffix.lower()

    # --- Classification Logic ---

    # 1. problem.json
    if file_name_lower == "problem.json":
        safe_copy(file_path, target_task_dir / "problem.json")
        return True

    # 2. Statements (.pdf, .txt usually)
    # Look for PDFs directly in task root or statement folder
    if file_suffix_lower == ".pdf" or (file_suffix_lower == ".txt" and ("statement" in file_name_lower or "problem" in file_name_lower)):
        # Check if it's inside a potential solution/editorial folder first
        if not any(part in file_path.parts for part in ["solution", "sol", "editorial", "analysis"]):
             # Prioritize statement folder if it exists
            if parent_dir_name_lower in ["statement", "statements", "problem", "problema"]:
                 safe_copy(file_path, target_task_dir / "statements" / file_path.name)
                 return True
             # If directly in task root, and matches task name somewhat
            elif file_path.parent == source_task_root and (task_name_lower in file_name_lower or "statement" in file_name_lower):
                 safe_copy(file_path, target_task_dir / "statements" / file_path.name)
                 return True
            # Less certain, could be attachment or other PDF, check later

    # 3. Graders (.cpp, .pas, .h)
    # Often loose, in 'grader', 'lib', or task root
    if file_suffix_lower in [".cpp", ".pas", ".h", ".c"]:
        if "grader" in file_name_lower or parent_dir_name_lower in ["grader", "graders", "lib"] or (file_name_lower == f"{task_name_lower}.h" and file_path.parent == source_task_root):
            # Avoid copying checkers mistakenly classified as graders
             if "check" not in file_name_lower and "checker" not in file_name_lower and "scorer" not in file_name_lower:
                safe_copy(file_path, target_task_dir / "graders" / file_path.name)
                return True

    # 4. Checkers (.cpp, .pas)
    # Often loose, in 'checker', 'chk'
    if file_suffix_lower in [".cpp", ".pas", ".c"]:
        if "check" in file_name_lower or "checker" in file_name_lower or "scorer" in file_name_lower or parent_dir_name_lower in ["checker", "check", "chk"]:
            safe_copy(file_path, target_task_dir / "checkers" / file_path.name)
            return True

    # 5. Subtasks (.json, .txt, .cfg)
    if "subtask" in file_name_lower and file_suffix_lower in [".json", ".txt", ".cfg", ".ini", ".dat"]:
         safe_copy(file_path, target_task_dir / "subtasks" / file_path.name)
         return True
    if file_name_lower in ["scoring.json", "scoring.txt", "subtasks.json", "subtasks.txt"]: # Common names
        safe_copy(file_path, target_task_dir / "subtasks" / file_path.name)
        return True


    # 6. Solutions (Code) (.cpp, .pas, .java, etc.)
    # Look in folders like 'solution', 'sol', 'model', 'author' or specific file names
    code_extensions = [".cpp", ".pas", ".java", ".c", ".py"]
    if file_suffix_lower in code_extensions:
        is_solution = False
        if parent_dir_name_lower in ["solution", "solutions", "sol", "model", "author", "submissions"]:
            is_solution = True
        elif "sol" in file_name_lower or file_name_lower.startswith(task_name_lower + "_"): # e.g. task_full.cpp
             # Avoid classifying graders/checkers as solutions if they slipped through
             if not any(kw in file_name_lower for kw in ["grader", "checker", "check", "stub", f"{task_name_lower}.h"]):
                 is_solution = True

        if is_solution:
            target_sol_code_dir = target_task_dir / "solutions" / "Codes"
            # If the solution is within a standard folder (like 'sol'), copy relative path
            if parent_dir_name_lower in ["solution", "solutions", "sol", "model", "author", "submissions"]:
                 relative_sol_path = file_path.relative_to(file_path.parent) # Just the filename
                 safe_copy(file_path, target_sol_code_dir / relative_sol_path)
            else: # Loose solution file
                 safe_copy(file_path, target_sol_code_dir / file_path.name)
            return True

    # 7. Solutions (Editorial) (.pdf, .txt)
    # Look for descriptive documents within solution folders or named appropriately
    if file_suffix_lower in [".pdf", ".txt", ".md"]:
        if parent_dir_name_lower in ["solution", "solutions", "sol", "editorial", "analysis"] or \
           ("sol" in file_name_lower or "analysis" in file_name_lower or "editorial" in file_name_lower):
             # Avoid re-copying statements if they exist in these folders
            if not (target_task_dir / "statements" / file_path.name).exists():
                safe_copy(file_path, target_task_dir / "solutions" / "editorial" / file_path.name)
                return True

    # --- Directory Handling ---

    # 8. Tests (.in, .out, .ans) - Handled by directory copy below
    # Test folders often named 'tests', 'testdata', 'data', 'in', 'out'
    test_dir_names = ["tests", "testdata", "data", "in", "out", "samples"]
    if file_path.is_dir() and file_path.name.lower() in test_dir_names:
        print(f"  Identified Tests Folder: {file_path}")
        safe_copytree(file_path, target_task_dir / "tests")
        # Return None to indicate the whole dir was handled, skip individual file processing within
        return None # Signal directory processed

    # 9. Solution Code Directories (Copy whole folder if standard name)
    sol_code_dir_names = ["solution", "solutions", "sol", "model", "submissions", "author"]
    if file_path.is_dir() and file_path.name.lower() in sol_code_dir_names:
         # Check if it primarily contains code files before copying wholesale
         contains_code = any(f.suffix.lower() in code_extensions for f in file_path.rglob("*") if f.is_file())
         if contains_code:
             print(f"  Identified Solution Codes Folder: {file_path}")
             safe_copytree(file_path, target_task_dir / "solutions" / "Codes" / file_path.name)
             # Check for editorials within this folder separately if needed, or assume they are handled above
             return None # Signal directory processed

    # 10. Attachment folders ('files', 'attachments', 'public', specific data folders)
    attachment_dir_names = ["files", "attachments", "public", "images"]
    if file_path.is_dir() and file_path.name.lower() in attachment_dir_names:
         print(f"  Identified Attachments Folder: {file_path}")
         safe_copytree(file_path, target_task_dir / "attachments" / file_path.name)
         return None # Signal directory processed


    # --- Fallback / Default ---

    # 11. Remaining files might be attachments (especially if loose in task root)
    # Put images, data files etc. into attachments if not classified otherwise
    if file_path.is_file():
        # Check if it was already copied (e.g., as part of tests/solutions dir copy)
        potential_targets = [
            target_task_dir / "statements" / file_path.name,
            target_task_dir / "graders" / file_path.name,
            target_task_dir / "checkers" / file_path.name,
            target_task_dir / "solutions" / "editorial" / file_path.name,
            target_task_dir / "solutions" / "Codes" / file_path.name,
            target_task_dir / "subtasks" / file_path.name,
        ]
        is_copied = any(p.exists() for p in potential_targets)

        # Check within copied test/attachment/solution directories
        if not is_copied:
             for copied_dir_base in ["tests", "attachments", "solutions/Codes"]:
                 if (target_task_dir / copied_dir_base).exists():
                      if any((target_task_dir / copied_dir_base).rglob(file_path.name)):
                          is_copied = True
                          break

        if not is_copied:
            # Default assumption: if not classified and not code/pdf/txt, it's an attachment
            # Or if it's a PDF/TXT that didn't fit statement/editorial (e.g. sample explanation)
            attachment_extensions = [".png", ".jpg", ".jpeg", ".gif", ".zip", ".bmp", ".dat", ".in", ".out", ".diff", ".sh"] # Add common data/script types
            if file_suffix_lower in attachment_extensions or parent_dir_name_lower == "public" or \
               (file_suffix_lower in [".pdf", ".txt"] and not any(kw in file_name_lower for kw in ["statement", "problem", "solution", "analysis", "editorial"])):
                 print(f"  Defaulting to Attachment: {file_path.name}")
                 safe_copy(file_path, target_task_dir / "attachments" / file_path.name)
                 return True
            else:
                 # If it's some other code/pdf/txt file we missed, maybe log it
                 print(f"  * Unclassified file: {file_path} (Parent: {parent_dir_name_lower})")
                 return False # Indicate not classified/copied by this logic

    return False # Indicate not handled (might be a dir we don't want to copy directly)

# --- Main Processing Logic ---

def organize_ioi_2010(source_dir, output_dir, year):
    """Organizes IOI 2010 contest materials from source_dir to output_dir."""
    print(f"Starting IOI {year} processing...")
    print(f"Source: {source_dir}")
    print(f"Output: {output_dir}")

    output_year_dir = output_dir / year
    output_year_dir.mkdir(parents=True, exist_ok=True)
    print(f"Created base year directory: {output_year_dir}")

    # 1. Process General Editorials/Files at the root level
    output_general_editorial_dir = output_year_dir / "editorial"
    processed_root_files = set()
    general_editorial_keywords = ["booklet", "editorial", "review", "report", "solution", "analysis", "problems"] # Broader keywords for root level
    for item in source_dir.glob('*'):
        if item.is_file() and item.suffix.lower() in ['.pdf', '.txt', '.md']:
            item_name_lower = item.name.lower()
            # Check if it looks like a general editorial doc
            if any(keyword in item_name_lower for keyword in general_editorial_keywords):
                 # Avoid task-specific PDFs at the root if possible (less common)
                 # This check is weak, relies on general naming conventions
                 is_likely_task_pdf = False
                 for day_folder in source_dir.iterdir():
                      if day_folder.is_dir():
                           for task_folder in day_folder.iterdir():
                                if task_folder.is_dir() and task_folder.name.lower() in item_name_lower:
                                     is_likely_task_pdf = True
                                     break
                           if is_likely_task_pdf:
                                break

                 if not is_likely_task_pdf:
                      print(f"Found general editorial file: {item.name}")
                      output_general_editorial_dir.mkdir(parents=True, exist_ok=True)
                      safe_copy(item, output_general_editorial_dir / item.name)
                      processed_root_files.add(item)

    # 2. Process Day Folders
    for day_dir in source_dir.iterdir():
        if not day_dir.is_dir():
            continue

        day_name_lower = day_dir.name.lower()
        if day_name_lower == "practice":
            day_num = "day0"
        elif day_name_lower == "day1":
            day_num = "day1"
        elif day_name_lower == "day2":
            day_num = "day2"
        else:
            print(f"Skipping unrecognized directory: {day_dir.name}")
            continue

        print(f"\nProcessing {day_num} ({day_dir.name})...")
        output_day_dir = output_year_dir / day_num
        output_day_dir.mkdir(parents=True, exist_ok=True)

        # 3. Process Task Folders within each Day
        for task_dir in day_dir.iterdir():
            if not task_dir.is_dir():
                # Check if it's a day-level editorial file we missed
                 if task_dir.is_file() and task_dir not in processed_root_files and task_dir.suffix.lower() in ['.pdf', '.txt', '.md']:
                     if any(keyword in task_dir.name.lower() for keyword in general_editorial_keywords):
                         print(f"Found day-level editorial file: {task_dir.name}")
                         output_general_editorial_dir.mkdir(parents=True, exist_ok=True)
                         safe_copy(task_dir, output_general_editorial_dir / f"{day_num}_{task_dir.name}") # Prefix with day
                         processed_root_files.add(task_dir)
                 else:
                      print(f"  Skipping non-directory item in day folder: {task_dir.name}")
                 continue

            task_name = task_dir.name
            task_name_lower = task_name.lower()
            print(f"\n Processing Task: {task_name}")

            target_task_dir = output_day_dir / task_name_lower
            target_task_dir.mkdir(parents=True, exist_ok=True)

            # Create standard subdirectories eagerly
            for sub in ["statements", "graders", "checkers", "tests", "attachments", "solutions", "subtasks"]:
                if sub == "solutions":
                    (target_task_dir / sub / "Codes").mkdir(parents=True, exist_ok=True)
                    (target_task_dir / sub / "editorial").mkdir(parents=True, exist_ok=True)
                else:
                    (target_task_dir / sub).mkdir(parents=True, exist_ok=True)

            # 4. Walk through the source task directory and classify/copy items
            processed_paths = set() # Keep track of files/dirs processed by directory copies

            # First pass: copy entire directories (tests, solutions, attachments)
            for item in sorted(list(task_dir.iterdir())): # Sort for consistent processing order
                 if item.is_dir():
                     result = classify_and_copy_file(item, task_dir, target_task_dir, task_name_lower)
                     if result is None: # Directory was copied successfully
                         processed_paths.add(item)
                         # Add all files within the copied directory to processed_paths
                         for root, _, files in os.walk(item):
                              for name in files:
                                   processed_paths.add(Path(root) / name)
                         # Add subdirs too, to prevent re-processing attempts
                         for root, dirs, _ in os.walk(item):
                              for name in dirs:
                                   processed_paths.add(Path(root) / name)


            # Second pass: process individual files, skipping those already handled
            for item in task_dir.rglob('*'):
                 if item in processed_paths or item.is_dir(): # Skip already processed items and directories themselves
                      continue

                 # Ensure we don't process files inside already copied directories again
                 part_of_processed_dir = False
                 for processed_dir in processed_paths:
                      if processed_dir.is_dir() and item.is_relative_to(processed_dir):
                          part_of_processed_dir = True
                          break
                 if part_of_processed_dir:
                      continue

                 classify_and_copy_file(item, task_dir, target_task_dir, task_name_lower)
                 processed_paths.add(item) # Mark file as processed


    print(f"\nFinished IOI {year} processing.")
    print(f"Output saved to: {output_dir}")

# --- Execution ---
if __name__ == "__main__":
    if not SOURCE_ROOT.is_dir():
        print(f"Error: Source directory not found: {SOURCE_ROOT}")
    else:
        organize_ioi_2010(SOURCE_ROOT, OUTPUT_ROOT, YEAR)