import zipfile
import os
import requests
from git import Repo
import PyPDF2
from io import BytesIO
import json
import shutil
import re
from pathlib import PurePosixPath
import configparser
import sys
import fnmatch
from rapidfuzz import process, fuzz
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse

def unzip(zip_path, output_dir):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(output_dir)

def download_file(url, save_path, redownload=False, timeout=10):
    """
    下载文件并保存到指定路径:
      - 如果返回的是 PDF (Content-Type: application/pdf)，则以二进制文件方式保存。
      - 如果返回的是 HTML (Content-Type: text/html)，则用 pdfkit 转换为 PDF。
      - 否则，直接按二进制方式保存。
    注意: 这里使用 verify=False 跳过了证书验证 (会产生警告).
    """
    if not redownload and os.path.exists(save_path):
        print(f"File already exists: {save_path}")
        return False
    try:
        r = requests.get(url, timeout=timeout, verify=False)
        r.raise_for_status()
        content_type = r.headers.get('Content-Type', '').lower()

        if 'application/pdf' in content_type:
            # 直接保存为 PDF
            with open(save_path, 'wb') as f:
                f.write(r.content)
            print(f"Downloaded PDF: {url} -> {save_path}")

        elif 'text/html' in content_type:
            # 将 HTML 转为 PDF
            # 如果原始链接后缀是 .php/.html，我们把最终文件名后缀改成 .pdf
            base_name, _ = os.path.splitext(save_path)
            save_path = base_name + '.html'
            with open(save_path, 'wb') as f:
                f.write(r.content)
            print(f"Downloaded HTML: {url} -> {save_path}")
        else:
            # 其它类型（zip, etc.），直接二进制保存
            with open(save_path, 'wb') as f:
                f.write(r.content)
            print(f"Downloaded (binary): {url} -> {save_path}")
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False

def fetch_url(url):
    """
    Fetch the url and return the response content.
    """
    try:
        r = requests.get(url, timeout=5, verify=False)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"Failed to fetch {url}: {e}")
        return None
    
def unzip_file(zip_path, extract_dir):
    """Unzip a ZIP file to the specified directory."""
    print(f"Unzipping: {zip_path} -> {extract_dir}")
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(extract_dir)
    except Exception as e:
        print(f"Failed to unzip {zip_path}: {e}")
def zip_contains_only_one_folder(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        top_level_items = set()
        for info in zip_ref.infolist():
            parts = PurePosixPath(info.filename).parts
            if parts:
                top_level_items.add(parts[0])
        return len(top_level_items) == 1 and zip_ref.getinfo(list(top_level_items)[0] + '/').is_dir()
def unzip_files(dir_path):
    """Unzip all ZIP files in the specified directory."""
    print(f"Unzipping all files in: {dir_path}")
    for root, _, files in os.walk(dir_path):
        for file in files:
            if file.endswith('.zip'):
                zip_path = os.path.join(root, file)
                if zip_contains_only_one_folder(zip_path):
                    extract_dir = root
                else:
                    extract_dir = os.path.splitext(zip_path)[0]
                    os.makedirs(extract_dir, exist_ok=True)
                unzip(zip_path, extract_dir)
def clone_repo(git_url, dest_path):
    """
    Clone a Git repository to the specified destination path.
    """
    try:
        Repo.clone_from(git_url, dest_path)
        print(f"Cloned {git_url} to {dest_path}")
    except Exception as e:
        print(f"Failed to clone {git_url}: {e}")

def remove_pdf(input_pdf, output_pdf, header_height=110, footer_height=50, first_page_only=False):
    reader = PyPDF2.PdfReader(input_pdf)
    writer = PyPDF2.PdfWriter()

    for i, page in enumerate(reader.pages):
        # The media box represents the full page size.
        # Get the original boundaries
        llx, lly, urx, ury = page.mediabox.lower_left[0], page.mediabox.lower_left[1], page.mediabox.upper_right[0], page.mediabox.upper_right[1]
        if first_page_only and i > 0:
            writer.add_page(page)
            continue
        # Define the new crop box boundaries
        new_lly = lly + footer_height  # bottom moves up
        new_ury = ury - header_height  # top moves down
        page.cropbox.lower_left = (llx, new_lly)
        page.cropbox.upper_right = (urx, new_ury)
        
        writer.add_page(page)

    with open(output_pdf, "wb") as f_out:
        writer.write(f_out)
    
    return output_pdf

def find_task_splits(input_pdf, task_keywords, prefix_length=100, number_tasks=3):
    """
    Detects the starting page for each task based on keywords found 
    only in the beginning of each page (first 'prefix_length' characters).
    
    Parameters:
        input_pdf (str): Path to the input PDF.
        task_keywords (list): List of keywords (in lowercase) to search for.
        prefix_length (int): Number of characters from the beginning of the page to check.
        
    Returns:
        ranges (dict): A dictionary where each key is a task keyword and each value
                       is a tuple (start_page, end_page) indicating the page range for that task.
                       The page numbers are 0-indexed.
    """
    # Initialize dictionary to record the first occurrence of each task keyword
    task_keywords = [keyword.lower() for keyword in task_keywords]
    splits = {keyword: None for keyword in task_keywords}
    
    with open(input_pdf, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        total_pages = len(reader.pages)
        # Loop over each page and check only the beginning (prefix) for each keyword
        for i in range(total_pages):
            page_text = reader.pages[i].extract_text() or ""
            prefix = page_text[:prefix_length].lower()
            for keyword in task_keywords:
                if splits[keyword] is None and keyword in prefix:
                    splits[keyword] = i

    # Filter out keywords not found
    valid_splits = {k: v for k, v in splits.items() if v is not None}
    # Sort tasks by the order they appear in the PDF
    sorted_tasks = sorted(valid_splits.items(), key=lambda x: x[1])
    
    # Determine the page range for each task
    ranges = {}
    for idx, (task, start_page) in enumerate(sorted_tasks):
        # End page is the start of the next task or the end of the document
        end_page = sorted_tasks[idx+1][1] if idx < len(sorted_tasks) - 1 else total_pages
        ranges[task] = (start_page, end_page)
    
    assert len(ranges) == number_tasks, f"Expected {number_tasks} tasks, found {len(ranges)}"
    return ranges

def split_pdf(input_pdf, ranges, editorial = False):
    """
    Splits the input PDF into separate files based on the provided page ranges.
    
    Parameters:
        input_pdf (str): Path to the input PDF file.
        ranges (dict): Dictionary with task names as keys and (start, end) page ranges as values.
    """
    with open(input_pdf, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for task, (start, end) in ranges.items():
            writer = PyPDF2.PdfWriter()
            for i in range(start, end):
                writer.add_page(reader.pages[i])

            if (editorial):
                output_filename = os.path.dirname(input_pdf) + f"/{task}_editorial.pdf"
            else:
                output_filename = os.path.dirname(input_pdf) + f"/{task}.pdf"

            with open(output_filename, "wb") as out_f:
                writer.write(out_f)
            print(f"Created '{output_filename}' with pages {start+1} to {end}")

def remove_first_page(input_pdf):
    """
    Removes the first page of an input PDF

    Parameters:
        input_pdf (str): Path to the input PDF file.
    """
    reader = PyPDF2.PdfReader(input_pdf)
    writer = PyPDF2.PdfWriter()
    for page in reader.pages[1:]:
        writer.add_page(page)
    with open(input_pdf, "wb") as out_pdf:
        writer.write(out_pdf)
    print(f"Removed first page from '{input_pdf}'")

def create_subtask_json_by_folder(folder):
    """
    Create a JSON structure for subtasks based on the folder structure.
    Each subfolder represents a task, and each file within it is a subtask.
    """
    subtasks = {}
    for i, subtask_file in enumerate(sorted(os.listdir(folder))):
        subtask_path = os.path.join(folder, subtask_file)
        with open(subtask_path, 'r') as f:
            subtask_data = json.load(f)
        subtask_data['task'] = subtask_file.replace(".json", "")
        subtasks[i] = subtask_data
    return subtasks

def create_subtask_json_kattis(folder):
    def handle_group(group_folder):
        group_name = os.path.basename(group_folder)
        subtask = {"task": group_name}
        tasks_files = set()
        test_files = os.listdir(group_folder)
        if len(test_files) == 2 and group_name != "sample":
            test_files = os.listdir(os.path.join(group_folder, group_name))
        for test_file in test_files:
            if test_file == "testdata.yaml":
                with open(os.path.join(group_folder, test_file), 'r') as f:
                    text = f.read()
                match = re.search(r'accept_score:\s*(\d+)', text)
                if match:
                    subtask["score"] = int(match.group(1))
                else:
                    subtask["score"] = -1
            else:
                tasks_files.add(test_file.split(".")[0])
        tasks_files = list(tasks_files)
        tasks_files.sort()
        subtask["testcases"] = tasks_files
        return subtask
    subtasks = {}
    subtasks[0] = handle_group(folder+"/sample")
    group_number = 1
    for group in os.listdir(folder+"/secret"):
        group_folder = os.path.join(folder, "secret", group)
        if not os.path.isdir(group_folder) or group == "combined_tests":
            continue
        group_number = int(group.strip("group"))
        subtasks[group_number] = handle_group(group_folder)
    return subtasks
def extract_image_files(folder):
    """
    Extract image files from the specified folder and return a list of their paths.
    """
    image_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                image_files.append(os.path.join(root, file))
    return image_files

def extract_editorial_files(folder):
    """
    Extract editorial files from the specified folder and return a list of their paths.
    """
    editorial_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            if "sol" in file.lower() or "solution" in file.lower():
                editorial_files.append(os.path.join(root, file))
    return editorial_files

def categorize_pisek(result_str):
    """
    Categorize the solution based on its subtasks result string.
    
    The characters in the string mean:
      1 - success
      0 - fail
      P - partial success
      W - wrong answer
      ! - runtime error
      T - timeout
      X - any result
    
    The categorization logic is:
      - If any character is "!" -> runtime_error.
      - Else if any character is "T" -> time_limit.
      - Else if all characters are "1" -> correct.
      - Otherwise -> incorrect.
    """
    if "!" in result_str:
        return "runtime_error"
    elif "T" in result_str:
        return "time_limit"
    elif all(ch == '1' for ch in result_str):
        return "correct"
    else:
        return "incorrect"
def calculate_score_for_solution_pisek(solution, tests):
    """
    Calculate the score for a given solution.
    
    Parameters:
      solution (dict): Contains a 'subtasks' key whose string has one character per test.
      tests (list): A list of tests, each having an 'id' and a 'points' value.
    
    Scoring logic:
      - For each test, if the corresponding character in the solution's subtasks string is '1',
        add the test's points to the total score.
      - Any other result (including "0", "P", etc.) gives 0 points for that test.
      - If the solution's result string is longer than the number of tests, extra characters are ignored.
    """
    result_str = solution.get("subtasks", "")
    score = 0
    # Sort tests in increasing order of their test number (assumes test IDs like "test01", "test02", etc.)
    sorted_tests = sorted(tests, key=lambda t: int(t["id"].replace("test", "")) if t["id"].replace("test", "").isdigit() else 0)
    
    # Process each test for which we have a corresponding result character.
    for i, test in enumerate(sorted_tests):
        if i >= len(result_str):
            break
        if result_str[i] == '1':
            score += test.get("points", 0)
    return score

def parse_config_pisek(filename):
    # Use ConfigParser with '#' as inline comment prefix.
    config = configparser.ConfigParser(inline_comment_prefixes=['#'])
    # Preserve key letter case.
    config.optionxform = str  
    config.read(filename)
    task_type = "Batch"
    if config.has_section("task") and config.has_option("task", "task_type"):
        task_type = config.get("task", "task_type")

    # Get time_limit from [cms] if available, default to 1 second.
    if config.has_section("cms"):
        if config.has_option("cms", "time_limit"):
            time_limit = float(config.get("cms", "time_limit"))
        else:
            time_limit = 1.0
        if config.has_option("cms", "mem_limit"):
            mem_limit = int(config.get("cms", "mem_limit"))
        else:
            mem_limit = 1024
    else:
        time_limit = 1.0
        mem_limit = 1024


    # Extract test/subtask information: sections starting with "test"
    subtasks = [{"id": "test00", "name": "Subtask 1", "points": 0, "in_globs":["sample*.in"], "predecessors": []}]
    for section in config.sections():
        if section.startswith("test") and section != "tests":
            test_info = {"id": section}
            test_info["name"] = config.get(section, "name") if config.has_option(section, "name") else f"Subtask {int(section[-2:])}"
            test_info["points"] = int(config.get(section, "points")) if config.has_option(section, "points") else 0
            if config.has_option(section, "in_globs"):
                in_globs = config.get(section, "in_globs")
                test_info["in_globs"] = in_globs.split()
            else:
                test_info["in_globs"] = [f"{section[-2:]}*.in"]
            if config.has_option(section, "predecessors"):
                preds = config.get(section, "predecessors")
                test_info["predecessors"] = preds.split() if preds.strip() else []
            else:
                test_info["predecessors"] = []
            subtasks.append(test_info)

    # Extract solution information: sections starting with "solution_"
    solutions = []
    for section in config.sections():
        if section.startswith("solution_"):
            sol_info = {"id": section}
            if config.has_option(section, "subtasks"):
                result_str = config.get(section, "subtasks")
                sol_info["subtasks"] = result_str
                sol_info["category"] = categorize_pisek(result_str)
            else:
                sol_info["subtasks"] = ""
                sol_info["category"] = "unknown"
            sol_info['score'] = calculate_score_for_solution_pisek(sol_info, subtasks)
            sol_info['id'] = section[9:]
            if config.has_option(section, "source"):
                sol_info["id"] = config.get(section, "source")
            solutions.append(sol_info)
    return {
        "task_type": task_type,
        "time_limit": time_limit,
        "memory_limit": mem_limit,
        "subtasks": subtasks,
        "solutions": solutions
    }
def categorize_tests_pisek(test_folder, tests_config):
    """
    Categorizes the list of test_files into subtasks using the glob patterns in tests_config.
    Returns a dictionary mapping test IDs to the list of matching files.
    """
    categorized = {}
    test_files = os.listdir(test_folder)
    for test in tests_config:
        test_id = int(test["id"].strip("test"))
        patterns = test["in_globs"]
        matching_files = []
        for file in test_files:
            # If the file name matches any of the glob patterns, include it
            if any(fnmatch.fnmatch(file, pattern) for pattern in patterns):
                matching_files.append(file.replace(".in", ""))
        #remove duplicates
        matching_files = list(set(matching_files))
        categorized[test_id] = {"score": test["points"], "testcases": matching_files, "task": test["name"]}
    for test in tests_config:
        test_id = int(test["id"].strip("test"))
        if "predecessors" in test:
            for pred in test["predecessors"]:
                if int(pred) in categorized:
                    categorized[test_id]['testcases'].extend(categorized[int(pred)]['testcases'])
        categorized[test_id]['testcases'] = sorted(list(set(categorized[test_id]['testcases'])))
    return categorized

def create_solution_folders(base_dir, solutions, source_dir, file_extension=".cpp"):
    """
    Creates folders for each distinct category found in the given solutions,
    and moves the corresponding solution file from the source directory into the folder.
    
    Parameters:
        base_dir (str): The base directory where category folders will be created.
        solutions (list of dict): Each dictionary should have 'id' and 'category' keys.
        source_dir (str): The directory where the original solution files are located.
        file_extension (str): The extension appended to each solution's id to form the filename.
                              Default is ".py".
    
    Returns:
        A dictionary mapping each category to its created folder path.
    """
    # Determine distinct categories.
    categories = set(sol.get("category", "unknown") for sol in solutions)
    folder_paths = {}
    for category in categories:
        folder_path = os.path.join(base_dir, category)
        os.makedirs(folder_path, exist_ok=True)
        folder_paths[category] = folder_path

    # Move each solution file into the appropriate category folder.
    for sol in solutions:
        category = sol.get("category", "unknown")
        sol_filename = sol.get("id") + file_extension  # e.g. "solution_full_dp.py"
        src_path = os.path.join(source_dir, sol_filename)
        if os.path.exists(src_path):
            dest_path = os.path.join(folder_paths[category], sol_filename)
            shutil.move(src_path, dest_path)
        else:
            print(f"Warning: Source file {src_path} not found for solution {sol.get('id')}")
    
    return folder_paths
def extract_grader_folder(folder):
    if os.path.exists(folder+"/grader"):
        return folder+"/grader"
    elif os.path.exists(folder+"/graders"):
        return folder+"/graders"
    else:
        return None
def convert_cases_by_hash(hash_folder, dest_folder):
    case_folders = [f for f in os.listdir(hash_folder) if os.path.isdir(os.path.join(hash_folder, f))]
    test_folder = os.path.join(dest_folder, "tests")
    os.makedirs(test_folder, exist_ok=True)
    for case_folder in case_folders:
        case_path = os.path.join(hash_folder, case_folder)
        case_files = [f for f in os.listdir(case_path) if os.path.isfile(os.path.join(case_path, f))]
        for case_file in case_files:
            suffix = "in" if "in" in case_file else "out"
            case_file_path = os.path.join(case_path, case_file)
            dest_file = os.path.join(case_file_path, test_folder + f"/{case_folder}.{suffix}")
            shutil.copy(case_file_path, dest_file)
def create_subtasks_by_hash(subtasks_folder):
    subtasks = {}
    for subtask_folder in os.listdir(subtasks_folder):
        subtask_path = os.path.join(subtasks_folder, subtask_folder)
        if not os.path.isdir(subtask_path):
            continue
        for group in os.listdir(subtask_path):
            group_path = os.path.join(subtask_path, group)
            if not os.path.isdir(group_path):
                continue
            subtask = {"task": subtask_folder+"_"+group, 'testcases': [], 'score': -1}
            for cases in os.listdir(group_path):
                case_path = os.path.join(group_path, cases)
                with open(case_path, 'r') as f:
                    path = f.read()
                subtask['testcases'].append(os.path.basename(path))
            name = subtask_folder.split("_")[1] + "_" + group.split("_")[1]
            subtasks[name] = subtask
    return subtasks

def check_subtask_tests(subtasks, tests, delete_missing=False):
    """
    Check if all testcases referenced in subtasks are present in the tests directory.
    Optionally remove missing tests from subtasks.
    
    Parameters:
        subtasks (dict): Dictionary of subtasks, where each subtask contains a 'testcases' list
        tests (list or str): List of test filenames without extensions or directory containing test files
        delete_missing (bool): If True, remove missing tests from subtasks instead of just reporting them
    
    Returns:
        tuple: (missing_tests, is_valid, modified_subtasks)
            - missing_tests: List of testcases that were referenced but not found
            - is_valid: Boolean indicating whether all testcases were found
            - modified_subtasks: Dictionary of subtasks with missing tests removed (if delete_missing=True)
    """
    missing_tests = []
    
    # If tests is a directory, get the list of files
    if isinstance(tests, str) and os.path.isdir(tests):
        test_files = []
        for file in os.listdir(tests):
            # Remove extensions to get base filename
            base_name = os.path.splitext(file)[0]
            if base_name not in test_files:
                test_files.append(base_name)
    else:
        # Assume tests is already a list of test files
        test_files = tests
    
    # Create a deep copy if we're going to modify subtasks
    if delete_missing:
        import copy
        modified_subtasks = copy.deepcopy(subtasks)
    else:
        modified_subtasks = subtasks  # Just reference the original if not modifying
    
    # Check each subtask's testcases
    for subtask_id, subtask in subtasks.items():
        if 'testcases' not in subtask:
            continue
        
        if delete_missing:
            # List to track valid testcases
            valid_testcases = []
            
        for testcase in subtask['testcases']:
            # Remove any extension if present
            testcase_base = os.path.splitext(testcase)[0]
            
            if testcase_base not in test_files:
                missing_tests.append((subtask_id, testcase))
                # Skip adding this testcase to valid_testcases if delete_missing=True
            elif delete_missing:
                valid_testcases.append(testcase)
        
        # Update the subtask's testcases list if deleting missing tests
        if delete_missing:
            modified_subtasks[subtask_id]['testcases'] = valid_testcases
    
    # Determine if validation passed
    is_valid = len(missing_tests) == 0
    
    return missing_tests, is_valid, modified_subtasks


def fuzzy_matching_indices(list1, list2, threshold=80):
    """Return list of (i, j) where i is index in list1, j is best matching index in list2."""
    matches = []
    list2 = [item.lower() for item in list2]  # Normalize list2 to lowercase
    for i, item in enumerate(list1):
        match, score, j = process.extractOne(item, list2, scorer=fuzz.ratio)
        print(f"Matching '{item}' with '{match}' (score: {score})")
        if score >= threshold:
            matches.append((i, j))  # i from list1, j from list2
    return matches
def parse_memory_to_mb(mem_str: str) -> float:
    """
    Parses a memory string and converts it to MB.
    Supports units: MB, MiB, GB, GiB (case insensitive).
    If no unit is provided, assumes MB.
    """
    mem_str = mem_str.strip().lower().replace(' ', '')
    
    # Extract number and unit using regex
    match = re.match(r'([0-9]*\.?[0-9]+)([a-z]*)', mem_str)
    if not match:
        return 0
        raise ValueError(f"Invalid memory string: '{mem_str}'")

    value, unit = match.groups()
    value = float(value)

    # Normalize to MB
    if unit in ['', 'mb', 'mib', 'megabyte', 'megabytes']:
        return value
    elif unit in ['gb', 'gib', "gigabyte", "gigabytes"]:
        return value * 1024
    else:
        raise ValueError(f"Unsupported memory unit: '{unit}'")

def parse_time_to_seconds(time_str: str) -> float:
    """
    Parses a time string and converts it to seconds.
    Supports units: ms, s, sec, second(s), min, minute(s) (case insensitive).
    Defaults to seconds if unit is missing.
    """
    time_str = time_str.strip().lower().replace(' ', '')

    match = re.match(r'([0-9]*\.?[0-9]+)([a-z]*)', time_str)
    if not match:
        return 0
        raise ValueError(f"Invalid time string: '{time_str}'")

    value, unit = match.groups()
    value = float(value)

    # Normalize to seconds
    if unit in ['', 's', 'sec', 'second', 'seconds']:
        return value
    elif unit in ['ms', 'millisecond', 'milliseconds']:
        return value / 1000
    else:
        raise ValueError(f"Unsupported time unit: '{unit}'")
def identify_task_type(text):
    interactive_keywords = ["interactive task", "interactive problem", "communcation task", "communication problem", "sample interaction", "example interaction", "interactive grader", "multirun task", "multirun problem", "multi-run task", "multi-run problem"]
    output_only = ["output only task", "output-only task"]
    for keyword in interactive_keywords:
        if keyword in text.lower():
            return "interactive"
    for keyword in output_only:
        if keyword in text.lower():
            return "output_only"
    return "batch"
def create_dir_if_not_exists(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return


def download_google_sheet(sheet_url, save_path):
    """
    从 Google Sheets 分享链接下载为 .xlsx 文件。

    :param sheet_url: 原始 Google Sheets 共享链接
    :param save_path: 本地保存路径，带 .xlsx 后缀
    """
    try:
        # 提取 file_id
        parsed = urlparse(sheet_url)
        parts = parsed.path.split('/')
        if 'd' not in parts:
            raise ValueError("Invalid Google Sheets URL format.")
        file_id = parts[parts.index('d') + 1]

        # 构造导出链接
        export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"

        # 发起下载
        resp = requests.get(export_url)
        resp.raise_for_status()

        with open(save_path, 'wb') as f:
            f.write(resp.content)

        print(f"[OK] Downloaded Google Sheet → {save_path}")
    except Exception as e:
        print(f"[ERROR] Failed to download Google Sheet: {e}")

def clean_text(text):
    # 把 ASCII < 32 和 ASCII = 127 的控制字符都换成空格
    return re.sub(r'[\x00-\x1F\x7F]', '', text)

def sanitize_folder_name(name):
        """
        Sanitizes a string so that it can be used as a folder name.
        This function removes characters that are not alphanumeric, spaces, underscores, or hyphens.
        Then, it trims leading/trailing whitespace and replaces spaces with underscores.
        
        Args:
            name (str): The string to sanitize.
        
        Returns:
            str: The sanitized string.
        """
        # Remove any character that is not a word character, whitespace, or hyphen.
        safe = re.sub(r"[^\w\s-]", "", name)
        safe = safe.strip()
        safe = safe.replace(" ", "_")
        return safe
