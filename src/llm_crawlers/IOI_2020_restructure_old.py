import os
import shutil
import glob

def copy_item(src, dst):
    """Copies a file or directory from src to dst.
    Creates destination directory if it doesn't exist.
    Handles potential FileNotFoundError for src."""
    try:
        if os.path.isdir(src):
            # Ensure parent of dst exists if dst is a new dir itself
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            # Copy directory tree
            shutil.copytree(src, dst, dirs_exist_ok=True)
            print(f"Copied directory: {src} -> {dst}")
        elif os.path.isfile(src):
            # Ensure destination directory exists
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst) # copy2 preserves metadata
            print(f"Copied file: {src} -> {dst}")
        else:
            print(f"Warning: Source item not found or not a file/directory: {src}")
    except FileNotFoundError:
        print(f"Warning: Source item not found: {src}")
    except Exception as e:
        print(f"Error copying {src} to {dst}: {e}")

def process_ioi_data(source_base_dir, output_base_dir):
    """
    Processes the IOI 2020 data structure and reorganizes it into the target structure.
    """
    year = "2020"
    source_dir = os.path.join(source_base_dir, year)
    output_dir = os.path.join(output_base_dir, year)

    if not os.path.isdir(source_dir):
        print(f"Error: Source directory not found: {source_dir}")
        return

    print(f"Starting processing for year {year}")
    print(f"Source: {source_dir}")
    print(f"Destination: {output_dir}")

    # Create base output directory for the year
    os.makedirs(output_dir, exist_ok=True)

    # --- Handle potential contest-wide editorial/notice ---
    # Check for notice.pdf in day0, treat it as potential contest editorial
    day0_notice_pdf = os.path.join(source_dir, "day0", "notice.pdf")
    output_editorial_dir = os.path.join(output_dir, "editorial")
    if os.path.exists(day0_notice_pdf):
        os.makedirs(output_editorial_dir, exist_ok=True)
        copy_item(day0_notice_pdf, os.path.join(output_editorial_dir, "notice_day0.pdf"))

    # --- Process each day ---
    days = ["day0", "day1", "day2"]
    # Define tasks based on the provided structure analysis
    # Day 0 tasks from folders inside day0/
    # Day 1/2 tasks inferred from translations folder (assuming data exists elsewhere, standard structure is often dayX/task/task)
    tasks_by_day = {
        "day0": ["gift", "jelly", "routers", "squares"],
        "day1": ["Tickets", "Supertrees", "Plants"], # Inferred from translations
        "day2": ["Mushrooms", "Stations", "Biscuits"] # Inferred from translations
    }

    for day in days:
        print(f"\nProcessing {day}...")
        source_day_dir = os.path.join(source_dir, day)
        output_day_dir = os.path.join(output_dir, day)

        if not os.path.isdir(source_day_dir):
            print(f"Warning: Source directory for {day} not found: {source_day_dir}")
            continue

        os.makedirs(output_day_dir, exist_ok=True)

        tasks = tasks_by_day.get(day, [])
        if not tasks:
             # Fallback: try listing directories if predefined list is wrong/incomplete
             try:
                 tasks = [d for d in os.listdir(source_day_dir) if os.path.isdir(os.path.join(source_day_dir, d)) and d != 'translations']
                 print(f"Dynamically detected tasks for {day}: {tasks}")
             except FileNotFoundError:
                 print(f"Could not list tasks for {day}, directory not found.")
                 continue


        for task_name in tasks:
            print(f"  Processing task: {task_name}")

            # --- Define Source Paths ---
            # Handle the nested structure like day0/gift/gift or day1/Tickets/Tickets (assumption)
            # Check if the double nested structure exists first
            source_task_nested_dir = os.path.join(source_day_dir, task_name, task_name)
            if os.path.isdir(source_task_nested_dir):
                 source_task_base = source_task_nested_dir
            else:
                 # Fallback to single nesting if double doesn't exist (less likely based on day0 example)
                 source_task_base = os.path.join(source_day_dir, task_name)
                 if not os.path.isdir(source_task_base):
                     print(f"    Warning: Could not find valid source directory for task {task_name} in {day}. Tried {source_task_nested_dir} and {source_task_base}. Skipping task.")
                     continue
                 else:
                     print(f"    Info: Using single nested path for task {task_name}: {source_task_base}")


            source_statement_dir = os.path.join(source_task_base, "statement")
            source_grader_dir = os.path.join(source_task_base, "grader")
            source_checker_dir = os.path.join(source_task_base, "checker")
            source_tests_dir = os.path.join(source_task_base, "tests")
            source_public_dir = os.path.join(source_task_base, "public")
            source_public_examples_dir = os.path.join(source_public_dir, "examples")
            source_public_files_dir = os.path.join(source_public_dir, "files") # Specific attachments folder
            source_solution_dir = os.path.join(source_task_base, "solution")
            source_problem_json = os.path.join(source_task_base, "problem.json")
            source_subtasks_json = os.path.join(source_task_base, "subtasks.json")

            # Specific day0 PDF statements
            day0_pdf_statement = os.path.join(source_dir, "day0", f"{task_name}.pdf")


            # --- Define Destination Paths ---
            dest_task_dir = os.path.join(output_day_dir, task_name)
            dest_statements_dir = os.path.join(dest_task_dir, "statements")
            dest_graders_dir = os.path.join(dest_task_dir, "graders")
            dest_checkers_dir = os.path.join(dest_task_dir, "checkers")
            dest_tests_dir = os.path.join(dest_task_dir, "tests")
            dest_attachments_dir = os.path.join(dest_task_dir, "attachments")
            dest_solutions_dir = os.path.join(dest_task_dir, "solutions")
            dest_solutions_codes_dir = os.path.join(dest_solutions_dir, "Codes")
            dest_solutions_editorial_dir = os.path.join(dest_solutions_dir, "editorial")
            dest_subtasks_dir = os.path.join(dest_task_dir, "subtasks")
            dest_problem_json = os.path.join(dest_task_dir, "problem.json")
            dest_subtasks_json = os.path.join(dest_subtasks_dir, "subtasks.json")

            # --- Create Destination Directories ---
            os.makedirs(dest_task_dir, exist_ok=True)
            os.makedirs(dest_statements_dir, exist_ok=True)
            os.makedirs(dest_graders_dir, exist_ok=True)
            os.makedirs(dest_checkers_dir, exist_ok=True)
            os.makedirs(dest_tests_dir, exist_ok=True)
            os.makedirs(dest_attachments_dir, exist_ok=True)
            os.makedirs(dest_solutions_dir, exist_ok=True)
            os.makedirs(dest_solutions_codes_dir, exist_ok=True)
            os.makedirs(dest_solutions_editorial_dir, exist_ok=True) # Create even if empty
            os.makedirs(dest_subtasks_dir, exist_ok=True)

            # --- Copy Files and Directories ---

            # Statements (HTML/Markdown + Assets, and PDF for day0)
            copy_item(source_statement_dir, dest_statements_dir)
            if day == "day0" and os.path.exists(day0_pdf_statement):
                copy_item(day0_pdf_statement, os.path.join(dest_statements_dir, f"{task_name}_statement.pdf"))

            # Graders
            copy_item(source_grader_dir, dest_graders_dir)

            # Checkers
            copy_item(source_checker_dir, dest_checkers_dir)

            # Tests (from tests/ and public/examples/)
            copy_item(source_tests_dir, dest_tests_dir)
            copy_item(source_public_examples_dir, dest_tests_dir)

            # Attachments (public/cpp, public/java, public/files, potentially others in public/)
            if os.path.isdir(source_public_dir):
                for item in os.listdir(source_public_dir):
                    s_item = os.path.join(source_public_dir, item)
                    # Copy directories like cpp/, java/, files/ explicitly if they exist
                    if item in ["cpp", "java", "files"] and os.path.isdir(s_item):
                         # Copy into a subdirectory within attachments for clarity
                         dest_attach_sub_dir = os.path.join(dest_attachments_dir, item)
                         copy_item(s_item, dest_attach_sub_dir)
                    # Avoid copying 'examples' again
                    elif item != "examples" and os.path.exists(s_item):
                         # Copy other files/dirs directly into attachments/
                         copy_item(s_item, os.path.join(dest_attachments_dir, item))


            # Solutions (Code)
            copy_item(source_solution_dir, dest_solutions_codes_dir)
            # Note: Editorials (text descriptions) are not explicitly found in this structure,
            # the editorial dir is created but will likely remain empty unless manually populated.

            # Subtasks JSON
            copy_item(source_subtasks_json, dest_subtasks_json)

            # Problem JSON
            copy_item(source_problem_json, dest_problem_json)

    print("\nProcessing finished.")

# --- Configuration ---
# Source directory containing the '2020' folder
SOURCE_BASE_DIRECTORY = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI"
# Destination directory where the processed '2020' folder will be created
OUTPUT_BASE_DIRECTORY = f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed-2"

# --- Run the processing ---
if __name__ == "__main__":
    process_ioi_data(SOURCE_BASE_DIRECTORY, OUTPUT_BASE_DIRECTORY)