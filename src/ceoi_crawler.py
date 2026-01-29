import os
from base_crawler import Crawler, Contest, Task, CSESScraper
# from converter import MarkerConverter
from concurrent.futures import ThreadPoolExecutor
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
from urllib.parse import urljoin, urlparse
import json
import time

class CEOICrawler(Crawler):
    def __init__(self, *, competition="CEOI", crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=converter)
        self.base_url = "http://ceoi.inf.elte.hu/tasks/"
    def _download_tasks(self):
        # Decode the HTML bytes
        html_str = fetch_url("http://ceoi.inf.elte.hu/tasks-archive/")
        # Create BeautifulSoup object
        soup = BeautifulSoup(html_str, "html.parser")

        # For relative URLs, use this as base
        base_url = "http://ceoi.inf.elte.hu"
        # -------------------------------
        # Parse the HTML table
        # -------------------------------
        table = soup.find("table", class_="stripe")
        if not table:
            print("No table with class 'stripe' found.")
            exit(1)
        missing_files = {}
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            left_cell = cells[0]
            right_cell = cells[1]
            
            # Extract a year from the left cell (searching for a 4-digit number)
            year_match = re.search(r"(19\d{2}|20\d{2})", left_cell.get_text())
            if not year_match:
                continue
            year = year_match.group(0)
            missing_files[year] = []
            print(f"\nProcessing year {year}")
            year_dir = os.path.join(self._path, year)
            os.makedirs(year_dir, exist_ok=True)
            
            # Find all list items (each representing one or more task files)
            lis = right_cell.find_all("li", recursive=True)
            if year == '2017':
                lis = right_cell.find('li', style="list-style-type: none;").find('ul').find_all('li', recursive=False)
            for li in lis:
                li_text = li.get_text(separator=" ").strip()
                # Look for "Day" information (e.g. "Day 1" or "Day 2")
                day_match = re.search(r"Day\s*(\d+)", li_text, re.IGNORECASE)
                day = None
                practice = False
                if day_match:
                    day = "day" + day_match.group(1)
                elif "practice" in li_text.lower() or "practise" in li_text.lower():
                    practice = True
                # Get all links in this list item
                links = li.find_all("a")
                if not links:
                    continue
                # Use the first link as the main statement file
                main_link = links[0]
                href = main_link.get("href")
                if not href:
                    continue
                if href.startswith("/"):
                    href = urljoin(base_url, href)
                parsed = urlparse(href)
                file_name = os.path.basename(parsed.path)
                if not file_name:
                    file_name = "index.html"
                task_name = os.path.splitext(file_name)[0]
                
                # Determine the base directory for this task:
                # if day info is available, use {year}/{day}/; otherwise, use {year}/.
                if day:
                    task_base_dir = os.path.join(year_dir, day)
                elif practice:
                    task_base_dir = os.path.join(year_dir, "practice")
                else:
                    task_base_dir = year_dir
                os.makedirs(task_base_dir, exist_ok=True)
                
                # Download the statement file into {year}/{day}/{file_name}
                statement_dest = os.path.join(task_base_dir, file_name)
                if download_file(href, statement_dest, timeout=30):
                    if href.lower().endswith(".zip"):
                        unzip_file(statement_dest, task_base_dir)
                else:
                    missing_files[year].append(href)
                
                # Process any extra links (assumed to be solutions, tests, etc.)
                for extra_link in links[1:]:
                    extra_text = extra_link.get_text().lower()
                    extra_href = extra_link.get("href")
                    if not extra_href:
                        continue
                    if extra_href.startswith("/"):
                        extra_href = urljoin(base_url, extra_href)
                    
                    # Decide type based on anchor text
                    if "solut" in extra_text or "model" in extra_text or "grader" in extra_text:
                        file_type = "solutions"
                    elif "test" in extra_text:
                        file_type = "tests"
                    else:
                        # If the link text does not clearly indicate type, skip it.
                        continue
                    
                    # Create a subdirectory for the extra file under {year}/{day}/{task_name}/{file_type}/
                    task_extra_dir = os.path.join(task_base_dir, task_name, file_type)
                    os.makedirs(task_extra_dir, exist_ok=True)
                    
                    extra_parsed = urlparse(extra_href)
                    extra_file = os.path.basename(extra_parsed.path)
                    if not extra_file:
                        extra_file = "file"
                    extra_dest = os.path.join(task_extra_dir, extra_file)
                    
                    if download_file(extra_href, extra_dest, timeout=30):
                        if extra_href.lower().endswith(".zip"):
                            unzip_file(extra_dest, task_extra_dir)
                    else:
                        missing_files[year].append(extra_href)
        #Save missing files
        with open(os.path.join(self._path, "missing_files.json"), "w") as f:
            json.dump(missing_files,f)
    def crawl(self):
        self._download_tasks()
        html = fetch_url(self.base_url)
        return html
    def _restructure_2024(self, parse_path):
        # Parse the 2024 contest data
        year = "2024"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            tasks = os.listdir(day_path + "/Task packages")
            for task_name in tasks:
                task_dir = os.path.join(day_path, "Task packages", task_name)
                translation_dir = os.path.join(day_path, "Translations", task_name)
                test_data_dir = os.path.join(day_path, "Test data", task_name)
                if not os.path.isdir(task_dir):
                    continue
                config = parse_config_pisek(task_dir + "/config")
                solutions_folder = os.path.join(task_dir, "solutions")
                subtasks = categorize_tests_pisek(test_data_dir, config['subtasks'])
                create_solution_folders(solutions_folder, config['solutions'], solutions_folder)
                problem_json = {
                    "task": task_name,
                    "time_limit": config['time_limit'],
                    "memory_limit": config['memory_limit'],
                    "task_type": config['task_type'],
                }
                task = Task(
                    name = task_name,
                    statements = [os.path.join(day_path, "Task statements", task_name + ".pdf"), os.path.join(translation_dir, "en.md")],
                    translations= translation_dir,
                    subtasks = subtasks,
                    graders = extract_grader_folder(task_dir),
                    tests = os.path.join(day_path, "Test data", task_name),
                    editorial_files= os.path.join(task_dir, "editorial.md"),
                    code_files= solutions_folder,
                    problem_json = problem_json
                )
                contest.add_task(task, day)
            contest.write(parse_path)
    def _restructure_2023(self, parse_path):
        year = "2023"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            pdf_files = [file for file in os.listdir(day_path) if file.endswith(".pdf") and "spoiler" not in file]
            for file in pdf_files:
                num, task_name = file.split("-",1)[0], file.split("-",1)[1].replace(".pdf", "")
                task_path = os.path.join(day_path, task_name)
                convert_cases_by_hash(os.path.join(task_path, "cases_by_hash"), task_path)
                subtasks = create_subtasks_by_hash(os.path.join(task_path, "subtasks"))
                code_files = [os.path.join(task_path, file) for file in os.listdir(task_path) if file.endswith(".cpp")]
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, file),
                    graders = extract_grader_folder(task_path),
                    subtasks= subtasks,
                    tests = os.path.join(task_path, "tests"),
                    editorial_files= os.path.join(day_path, f"{num}-{task_name}-spoiler.pdf"),
                    code_files = code_files
                )
                contest.add_task(task, day)
        contest.write(parse_path)
        
    def _extract_limits(self, problem_text):
        """
        Extracts the time and memory limits from the given problem text.
        
        Returns a dictionary with keys 'time_limit' and 'memory_limit'.
        """
        limits = {}
        # Pattern to match "Time:" followed by the limit value (until the newline)
        time_match = re.search(r"Time:\s*([^\n]+)", problem_text)
        if time_match:
            limits["time_limit"] = parse_time_to_seconds(time_match.group(1).strip())
        else:
            limits["time_limit"] = None
        
        # Pattern to match "Memory:" followed by the limit value (until the newline)
        memory_match = re.search(r"Memory:\s*([^\n]+)", problem_text)
        if memory_match:
            limits["memory_limit"] = parse_memory_to_mb(memory_match.group(1).strip())
        else:
            limits["memory_limit"] = None
            
        return limits

    def _extract_subtask_scores(self, problem_text):
        """
        Extracts subtask scores from the problem text.
        
        Expects lines of the form:
        "Subtask X (score points)."
        
        If the score expression contains one or more plus signs (e.g., "10+20+30"),
        it splits the score into as many groups as present and adds keys of the form:
        group1_score, group2_score, etc.
        
        If no '+' is found, it simply converts the score to an integer.
        
        Returns a list of dictionaries; each dictionary corresponds to one subtask.
        """
        subtasks = {}
        
        # Matches text like: "**Subtask 1 (5 points).**" or similar variations.
        pattern = re.compile(r"Subtask\s+(\d+).*?\(\s*([0-9+\s]+?)\s*points", re.IGNORECASE)
        
        for match in pattern.finditer(problem_text):
            subtask_num = int(match.group(1))
            score_str = match.group(2).strip()
            
            # Check if the score string contains a '+' sign.
            if '+' in score_str:
                # Split the string by '+' and remove extra spaces.
                groups = [g.strip() for g in score_str.split('+') if g.strip()]
                # For each group, try converting to int and assign with a dynamic key.
                for i, group_score in enumerate(groups):
                    try:
                        subtasks[f"{subtask_num}_{i+1}"] = int(group_score)
                    except ValueError:
                        # If conversion fails, store the original string.
                        subtasks[f"{subtask_num}_{i+1}"] = group_score
            else:
                # No groups present; just a single score.
                try:
                    subtasks[f"{subtask_num}_1"] = int(score_str)
                except ValueError:
                    subtasks[f"{subtask_num}_1"] = score_str
        return subtasks

    def _extract_problem_info(self, problem_text):
        """
        Combines extraction of limits and subtask scores from the problem text.
        
        Returns a dictionary with:
        - "time_limit": Time limit as a string.
        - "memory_limit": Memory limit as a string.
        - "subtasks": A list of dictionaries with subtask score details.
        """
        info = {}
        info["problem_info"] = self._extract_limits(problem_text)
        info["subtasks"] = self._extract_subtask_scores(problem_text)
        return info
    
    def _create_problem_info_json(self, converter_type):
        """
        Create a JSON file with problem information.
        """
        parse_path = self._parse_path
        for year in ["2023"]:
            year_path = os.path.join(parse_path, year)
            if not os.path.exists(year_path):
                continue
            for round_name in os.listdir(year_path):
                for task in os.listdir(os.path.join(year_path, round_name)):
                    task_path = os.path.join(year_path, round_name, task)
                    if not os.path.isdir(task_path):
                        continue
                    statement_path = os.path.join(task_path, "statements", f"statement_{converter_type}.md")
                    print(task_path)
                    if not os.path.exists(statement_path):
                        print(f"Statement file not found: {statement_path}")
                        continue
                    with open(statement_path, "r", encoding="utf-8") as f:
                        markdown_text = f.read()
                    problem_info = self._extract_problem_info(markdown_text)
                    problem_info, group_scores = problem_info["problem_info"], problem_info["subtasks"]
                    problem_info["task"] = task
                    problem_info["task_type"] = identify_task_type(markdown_text)
                    if problem_info['task_type'] != "batch":
                        print(f"{task} is not a batch task")
                    restruture_task_path = os.path.join(self._restructure_path, year, round_name, task, "problem.json")
                    with open(restruture_task_path, "w", encoding="utf-8") as f:
                        json.dump(problem_info, f, indent=4)
                    restruture_subtask_path = os.path.join(self._restructure_path, year, round_name, task, "subtasks.json")
                    
                    with open(restruture_subtask_path, "r", encoding="utf-8") as f:
                        subtasks = json.load(f)
                    for group, subtask in subtasks.items():
                        if group in group_scores:
                            if "score" not in subtask or subtask["score"] == -1:
                                subtask["score"] = group_scores[group]
                        if "0" in group and ("score" not in subtasks[group] or subtasks[group]["score"] == -1):
                            subtasks[group]["score"] = 0
                    with open(restruture_subtask_path, "w", encoding="utf-8") as f:
                        json.dump(subtasks, f, indent=4)

    def create_subtask_json(self, subtask_path):
        subtasks = {}
        for test_file in os.listdir(subtask_path):
            if os.path.isfile(os.path.join(subtask_path, test_file)):
                taskname = test_file.split(".")[0]
                subtaskname = test_file.split(".")[-1]
                inout = test_file.split(".")[-2]

                if inout == "in" and len(subtaskname) > 1:
                    subtask_name = f"Subtask {subtaskname[0]}"
                    if subtaskname[0] not in subtasks:
                        subtasks[subtaskname[0]] = {"score": -1, "testcases": [], "task": subtask_name}
                    subtasks[subtaskname[0]]["testcases"].append(f"{taskname}.{subtaskname}")
        return subtasks

    def _restructure_2022(self, parse_path):
        year = "2022"
        contest = Contest(year=year)
        for day in ["day1"]:
            day_path = os.path.join(self._path, year, day)
            task_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("tasks.pdf")))
            editorial_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("editorial.pdf")))
            code_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("solutions")))
            code_files = [os.path.join(code_path, file) for file in os.listdir(code_path) if file.endswith(".cpp")]
            test_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("testdata")))
            task_names = [os.path.basename(file).replace(".cpp", "") for file in code_files]
            if next((file for file in os.listdir(day_path) if file.startswith(task_names[0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, task_names))
                remove_first_page(os.path.join(day_path, "abracadabra.pdf"))
                split_pdf(editorial_file, find_task_splits(editorial_file, task_names, 300), True)
            for file in code_files:
                task_name = os.path.basename(file).replace(".cpp", "")
                subtasks = self.create_subtask_json(os.path.join(test_path, task_name))
                problem_json = {
                    "task": task_name,
                    "time_limit": 2.0,
                    "memory_limit": 1024,
                    "task_type": "Batch",
                }
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    tests = os.path.join(test_path, task_name),
                    editorial_files = os.path.join(day_path, f"{task_name}_editorial.pdf"),
                    code_files = os.path.join(code_path, task_name + ".cpp"),
                    subtasks = subtasks,
                    problem_json = problem_json
                )
                contest.add_task(task, day)
        for day in ["day2"]:
            day_path = os.path.join(self._path, year, day)
            task_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("tasks.pdf")))
            editorial_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("editorial.pdf")))
            code_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("solutions")))
            code_files = [os.path.join(code_path, file) for file in os.listdir(code_path) if file.endswith(".cpp")]
            test_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("testdata")))
            task_names = [os.path.basename(file).replace(".cpp", "") for file in code_files]
            if next((file for file in os.listdir(day_path) if file.startswith(task_names[0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, task_names))
                remove_first_page(os.path.join(day_path, "drawing.pdf"))
                split_pdf(editorial_file, find_task_splits(editorial_file, task_names, 300), True)
            for file in code_files:
                task_name = os.path.basename(file).replace(".cpp", "")
                subtasks = self.create_subtask_json(os.path.join(test_path, task_name))
                problem_json = {
                    "task": task_name,
                    "time_limit": 2.0,
                    "memory_limit": 1024,
                    "task_type": "Batch",
                }
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    tests = os.path.join(test_path, task_name),
                    editorial_files = os.path.join(day_path, f"{task_name}_editorial.pdf"),
                    code_files = os.path.join(code_path, task_name + ".cpp"),
                    subtasks = subtasks,
                    problem_json = problem_json
                )
                contest.add_task(task, day)
        contest.write(parse_path)
        self._organize_test_file_2022()

    def _restructure_2021(self, parse_path):
        year = "2021"
        contest = Contest(year=year)
        for day in ["day1"]:
            day_path = os.path.join(self._path, year, day, day)
            task_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("tasks.pdf")))
            editorial_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("editorial.pdf")))
            code_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("solutions")))
            code_files = [os.path.join(code_path, file) for file in os.listdir(code_path) if file.endswith(".cpp")]
            test_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("testdata")))
            task_names = ["diversity", "l-triominoes", "newspapers"]
            if next((file for file in os.listdir(day_path) if file.startswith(task_names[0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, task_names))
                remove_first_page(os.path.join(day_path, "diversity.pdf"))
                split_pdf(editorial_file, find_task_splits(editorial_file, task_names, 300), True)
            for file in code_files:
                task_name = os.path.basename(file).replace(".cpp", "")
                subtasks = self.create_subtask_json(os.path.join(test_path, task_name))
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    # tests = os.path.join(test_path, task_name),
                    editorial_files = os.path.join(day_path, f"{task_name}_editorial.pdf"),
                    code_files = os.path.join(code_path, task_name + ".cpp"),
                    # subtasks = subtasks
                )
                contest.add_task(task, day)
        for day in ["day2"]:
            day_path = os.path.join(self._path, year, day, day)
            task_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("tasks.pdf")))
            editorial_file = os.path.join(day_path, next(file for file in os.listdir(day_path) if file.endswith("editorial.pdf")))
            code_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("solutions")))
            code_files = [os.path.join(code_path, file) for file in os.listdir(code_path) if file.endswith(".cpp")]
            test_path = os.path.join(day_path, next(entry for entry in os.listdir(day_path) if entry.endswith("testdata")))
            task_names = [os.path.basename(file).replace(".cpp", "") for file in code_files]
            if next((file for file in os.listdir(day_path) if file.startswith(task_names[0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, task_names))
                remove_first_page(os.path.join(day_path, "stones.pdf"))
                split_pdf(editorial_file, find_task_splits(editorial_file, task_names, 300), True)
            for file in code_files:
                task_name = os.path.basename(file).replace(".cpp", "")
                subtasks = self.create_subtask_json(os.path.join(test_path, task_name))
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    # tests = os.path.join(test_path, task_name),
                    editorial_files = os.path.join(day_path, f"{task_name}_editorial.pdf"),
                    code_files = os.path.join(code_path, task_name + ".cpp"),
                    # subtasks = subtasks
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2020(self, parse_path): 
        year = "2020"
        contest = Contest(year=year)
        day1_tasks = ["fancyfence", "roads", "startrek"]
        day2_tasks = ["chessrush", "cleaning", "potion"]
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, "day1")
            # unzip_files(day_path)
            if day == "day1":
                task_files = [os.path.join(day_path, file) for file in os.listdir(day_path) if file.endswith("_eng.pdf") and any(task in file for task in day1_tasks)]
            else:
                task_files = [os.path.join(day_path, file) for file in os.listdir(day_path) if file.endswith("_eng.pdf") and any(task in file for task in day2_tasks)]
            for file in task_files:
                task_name = os.path.basename(file).replace("_eng.pdf", "")
                solution_path = os.path.join(day_path, task_name + "_solution")
                test_path = os.path.join(day_path, task_name + "_testdata")
                # subtasks = {}
                # subtasks[0] = {"score": -1, "testcases": [], "task": "Subtask 0"}
                # for test_file in os.listdir(os.path.join(test_path, "input")):
                #     subtask_name = test_file.split(".")[0]
                #     subtasks[0]["testcases"].append(subtask_name)
                task = Task(
                    name = task_name,
                    statements = file,
                    translations = os.path.join(day_path, task_name),
                    # tests = os.path.join(test_path, "input"),
                    # subtasks = subtasks,
                    editorial_files = os.path.join(solution_path, "solution.pdf"),
                    code_files = os.path.join(solution_path, "solution.cpp"),
                    # graders = os.path.join(solution_path, "sample_grader.cpp"),
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2019(self, parse_path):
        year = "2019"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day, day)
            for entry in os.listdir(day_path):
                if entry.endswith(".DS_Store"):
                    continue
                task_path = os.path.join(day_path, entry)
                unzip_files(task_path)
                task_file = next((file for file in os.listdir(task_path) if file.endswith("ENG.pdf")), None)
                task_name = os.path.basename(task_file).replace("-ENG.pdf", "")
                solution_path = os.path.join(task_path, f"{task_name}-full")
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, task_file),
                    editorial_files = os.path.join(task_path, f"{task_name}-solution.pdf"),
                    attachments = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if file.endswith(".cpp") or file.endswith(".java") or file.endswith(".h")],
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if file.endswith(".cpp") or file.endswith(".java")],
                    # translations = [os.path.join(task_path, file) for file in os.listdir(task_path) if file.endswith(".pdf") and "ENG.pdf" not in file],
                )
                contest.add_task(task, day)
        contest.write(parse_path)
        
    def _restructure_2018(self, parse_path):
        year = "2018"
        contest = Contest(year=year)
        for day in ["day1"]:
            day_path = os.path.join(self._path, year, day)
            editorial_names = ["cloud computing", "global warming", "lottery"]
            editorial_file = os.path.join(day_path, "solutions_day1.pdf")
            if next((file for file in os.listdir(day_path) if file.startswith(editorial_names[0])), None) is None:
                split_pdf(editorial_file, find_task_splits(editorial_file, editorial_names), True)
            for entry in os.listdir(day_path):
                if not os.path.isdir(os.path.join(day_path,entry)):
                    continue
                task_path = os.path.join(day_path, entry)
                unzip_files(task_path)
                solution_path = next((entry for entry in os.listdir(task_path) if entry.endswith("sol")), None)
                test_path = next((entry for entry in os.listdir(task_path) if entry.endswith("tests")), None)
                task_name = os.path.basename(solution_path).split("-")[0]
                editorial_name = next((file for file in os.listdir(day_path) if task_name in file), None)
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, task_name + ".pdf"),
                    editorial_files = os.path.join(day_path, editorial_name),
                    # tests = os.path.join(task_path, test_path),
                    code_files = os.path.join(task_path, solution_path, task_name + ".cpp"),
                    # translations = ,
                )
                contest.add_task(task, day)
        for day in ["day2"]:
            day_path = os.path.join(self._path, year, day)
            editorial_names = ["fibonacci", "toys", "triangles"]
            editorial_file = os.path.join(day_path, "day2.pdf")
            if next((file for file in os.listdir(day_path) if file.startswith(editorial_names[0])), None) is None:
                split_pdf(editorial_file, find_task_splits(editorial_file, editorial_names), True)
            for entry in os.listdir(day_path):
                if not os.path.isdir(os.path.join(day_path,entry)):
                    continue
                task_path = os.path.join(day_path, entry)
                unzip_files(task_path)
                solution_path = next((entry for entry in os.listdir(task_path) if entry.endswith("sol")), None)
                test_path = next((entry for entry in os.listdir(task_path) if entry.endswith("tests")), None)
                task_name = os.path.basename(solution_path).split("-")[0]
                editorial_name = next((file for file in os.listdir(day_path) if task_name in file), None)
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, task_name + ".pdf"),
                    editorial_files = os.path.join(day_path, editorial_name),
                    # tests = os.path.join(task_path, test_path),
                    code_files = os.path.join(task_path, solution_path, task_name + ".cpp"),
                    # translations = ,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2017(self, parse_path):
        year = "2017"
        contest = Contest(year=year)
        day1_tasks = ["one-way", "sure", "mousetrap"]
        day2_tasks = ["building", "palindromic", "chase"]
        for day in ["day1"]:
            day_path = os.path.join(self._path, year, day)
            statement_file = os.path.join(day_path, next((file for file in os.listdir(day_path) if file.startswith("eng")), None))
            if next((file for file in os.listdir(day_path) if file.startswith(day1_tasks[0])), None) is None:
                split_pdf(statement_file, find_task_splits(statement_file, day1_tasks))
            solution_path = os.path.join(day_path, f"ceoi2017-statements-{day}", "solutions")
            unzip_files(solution_path)
            for task_name in day1_tasks:
                task_path = os.path.join(solution_path, task_name)
                if task_name == "one-way":
                    task_path = os.path.join(solution_path, "oneway")
                    task = Task(
                        name = "oneway",
                        statements = os.path.join(day_path, f"{task_name}.pdf"),
                        editorial_files = None,
                        code_files = [os.path.join(task_path, "oneway.cpp"), os.path.join(task_path, "solution.cpp")],
                        # tests = task_path
                    )
                else:
                    task = Task(
                        name = task_name,
                        statements = os.path.join(day_path, f"{task_name}.pdf"),
                        editorial_files = None,
                        code_files = [os.path.join(task_path, task_name + ".cpp"), os.path.join(task_path, "solution.cpp")],
                        # tests = task_path
                    )
                contest.add_task(task, day)
        for day in ["day2"]:
            day_path = os.path.join(self._path, year, day)
            statement_file = os.path.join(day_path, next((file for file in os.listdir(day_path) if file.startswith("eng")), None))
            if next((file for file in os.listdir(day_path) if file.startswith(day2_tasks[0])), None) is None:
                split_pdf(statement_file, find_task_splits(statement_file, day2_tasks))
            solution_path = os.path.join(day_path, f"ceoi2017-statements-{day}", "solutions")
            unzip_files(solution_path)
            for task_name in day2_tasks:
                task_path = os.path.join(solution_path, task_name)
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = [os.path.join(task_path, task_name + ".cpp"), os.path.join(task_path, "solution.cpp")],
                    # tests = task_path
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2016(self, parse_path):
        year = "2016"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            solution_path = os.path.join(self._path, year, "day1", "icc-statement", "solutions")
            test_path = os.path.join(self._path, year, "day1", "icc-statement", "tests")
            unzip_files(test_path)
            for file in os.listdir(day_path):
                if not file.endswith(".pdf"):
                    continue
                task_name = file.split("-")[0]
                code_path = os.path.join(test_path, task_name)
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, file),
                    # graders = [os.path.join(code_path, file) for file in os.listdir(code_path) if "grader" in file],
                    editorial_files = os.path.join(solution_path, f"{task_name}-solution.pdf"),
                    code_files = None,
                    attachments = [os.path.join(code_path, file) for file in os.listdir(code_path) if (file.endswith(".cpp") or file.endswith(".h")) and "grader" not in file],
                    # tests = os.path.join(test_path, task_name),
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2015(self, parse_path):
        year = "2015"
        contest = Contest(year=year)
        solution_path = os.path.join(self._path, year, "ceoi2015")
        for day in ["day1", "day2"]:
            num = day[3]
            day_path = os.path.join(self._path, year, day)
            task_files = [file for file in os.listdir(day_path) if file.endswith(".pdf") and "solution" not in file]
            for file in task_files:
                task_name = os.path.basename(file).split("-")[0]
                code_path = os.path.join(solution_path, task_name)
                attachments = []
                if os.path.exists(os.path.join(code_path, "pic")):
                    attachments = [os.path.join(code_path, "pic", file) for file in os.listdir(os.path.join(code_path, "pic"))]
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, file),
                    # graders = ,
                    editorial_files = os.path.join(day_path, f"solutions{num}.pdf"),
                    code_files = [os.path.join(code_path, "solutions", file) for file in os.listdir(os.path.join(code_path, "solutions"))],
                    attachments = attachments,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2014(self, parse_path):
        year = "2014"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            task_files = [os.path.join(day_path, file) for file in os.listdir(day_path) if file.endswith(".pdf")]
            for file in task_files:
                task_name = os.path.basename(file).split(".")[0]
                # task_path = os.path.join(day_path, task_name)
                task = Task(
                    name = task_name,
                    statements = file,
                    editorial_files = None,
                    code_files = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2013(self, parse_path):
        year = "2013"
        contest = Contest(year=year)
        day1_tasks = ["treasure", "tram", "splot"]
        day2_tasks = ["board", "adriatic", "watering"]
        for day in ["day1"]:
            day_path = os.path.join(self._path, year, day)
            task_file = os.path.join(day_path, f"tasks_{day}.pdf")
            if next((file for file in os.listdir(day_path) if file.startswith(day1_tasks[0]) and file.endswith(".pdf")), None) is None:
                split_pdf(task_file, find_task_splits(task_file, day1_tasks, 212))
                remove_first_page(os.path.join(day_path, f"{day1_tasks[0]}.pdf"))
            for task_name in day1_tasks:
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    # tests = os.path.join(day_path, task_name),
                    code_files = os.path.join(day_path, task_name + ".cpp"),
                )
                contest.add_task(task, day)
        contest.write(parse_path)
        for day in ["day2"]:
            day_path = os.path.join(self._path, year, day)
            task_file = os.path.join(day_path, f"tasks_{day}.pdf")
            if next((file for file in os.listdir(day_path) if file.startswith(day2_tasks[0]) and file.endswith(".pdf")), None) is None:
                split_pdf(task_file, find_task_splits(task_file, day2_tasks, 212))
                remove_first_page(os.path.join(day_path, f"{day2_tasks[0]}.pdf"))
            for task_name in day2_tasks:
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    # tests = os.path.join(day_path, task_name),
                    code_files = os.path.join(day_path, task_name + ".cpp"),
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2012(self, parse_path):
        year = "2012"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            for entry in os.listdir(day_path):
                if entry.endswith(".DS_Store"):
                    continue
                task_path = os.path.join(day_path, entry)
                task_name = entry.split("_")[1]
                test_path = os.path.join(task_path, "tests")
                unzip_files(test_path)
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, entry + ".pdf"),
                    editorial_files = os.path.join(task_path, "solutions", entry[0]+"_sol"+task_name+".pdf"),
                    # tests = os.path.join(test_path, entry),
                    code_files = None
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2011(self, parse_path):
        year = "2011"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            for entry in os.listdir(day_path):
                if not os.path.isdir(os.path.join(day_path, entry)):
                    continue
                task_name = entry.replace("zad", "")
                solution_path = os.path.join(day_path, entry, "solutions")
                test_path = os.path.join(day_path, entry, "tests")

                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, entry + ".pdf"),
                    graders = os.path.join(solution_path, task_name+"gra"),
                    editorial_files = None,
                    code_files = None,
                    attachments = os.path.join(solution_path, task_name+"prg"),
                    # tests = [os.path.join(test_path, file) for file in os.listdir(test_path) if not file.endswith(".zip")]
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2010(self, parse_path):
        year = "2010"
        contest = Contest(year=year)
        year_path = os.path.join(self._path, year)
        for file in os.listdir(year_path):
            if not file.endswith(".pdf"):
                continue
            task_name = file.split("-")[0]
            task_path = os.path.join(year_path, task_name+"-eng", "tests")
            test_path = os.path.join(task_path, next((entry for entry in os.listdir(task_path) if os.path.isdir(os.path.join(task_path, entry))), None))

            task = Task(
                name = task_name,
                statements = os.path.join(year_path, file ),
                graders = [os.path.join(test_path, file) for file in os.listdir(test_path) if "tester" in file],
                code_files= None,
                editorial_files = None,
                # tests = test_path
            )
            contest.add_task(task, "day1") # unkown day
        contest.write(parse_path)

    def _restructure_2009(self, parse_path):
        year = "2009"
        contest = Contest(year=year)
        task_dict = {
            "day1": ["boxes", "harbingers", "photo"],
            "day2": ["logs", "sorting", "tri"] 
        }
        year_path = os.path.join(self._path, year)
        test_path = os.path.join(year_path, "tests")
        for day in ["day1", "day2"]:
            for task_name in task_dict[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(year_path, task_name + ".pdf"),
                    editorial_files = None,
                    code_files = None,
                    # tests = os.path.join(test_path, task_name),
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2008(self, parse_path):
        year = "2008"
        contest = Contest(year=year)
        test_path = os.path.join(self._path, year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            for file in os.listdir(day_path):
                if "day" in file or ".pdf" not in file:
                    continue
                task_name = file.split(".")[0]
                task = Task(
                    name = task_name,
                    statements = os.path.join(day_path, file),
                    editorial_files= None,
                    graders = [os.path.join(test_path, task_name, "grader")] + [os.path.join(test_path, task_name, file) for file in os.listdir(os.path.join(test_path, task_name)) if file.endswith(".cpp")],
                    attachments = [os.path.join(test_path, task_name, file) for file in os.listdir(os.path.join(test_path, task_name)) if file.endswith(".h")],
                    code_files= None,
                    # tests = os.path.join(test_path, task_name),
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2007(self, parse_path):
        year = "2007"
        contest = Contest(year=year)
        year_path = os.path.join(self._path, year)
        task_dict = {
            "day1": ["Ministry", "Nasty", "Sail"],
            "day2": ["Airport", "Necklace", "Treasury"] 
        }
        for day in ["day1", "day2"]:
            for task_name in task_dict[day]:
                test_path = os.path.join(year_path, task_name + ".pdf", "tests", task_name.lower())
                task = Task(
                    name = task_name,
                    statements = os.path.join(year_path, task_name + ".pdf.en"),
                    editorial_files= None,
                    attachments = [os.path.join(test_path, file) for file in os.listdir(test_path) if file.endswith(".h")],
                    # code_files= os.path.join(test_path, task_name.lower() + ".c"),
                    # tests = test_path,,
                )
                contest.add_task(task, day)
        contest.write(parse_path)
        
    def _restructure_2006(self, parse_path):
        year = "2006"
        contest = Contest(year=year)
        task_dict = {
            "day1": ["antenna", "queue", "walk"],
            "day2": ["connect", "link", "meandian"] 
        }
        year_path = os.path.join(self._path, year)
        for day in ["day1", "day2"]:
            for task_name in task_dict[day]:
                test_path = os.path.join(year_path, task_name, "tests")
                task = Task(
                    name = task_name,
                    statements = os.path.join(year_path, task_name + ".pdf"),
                    editorial_files= None,
                    code_files= None,
                    graders = os.path.join(test_path, "check.cpp"),
                    # tests = test_path
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2005(self, parse_path):
        year = "2005"
        contest = Contest(year=year)
        task_dict = {
            "day1": ["depot", "keys", "service"],
            "day2": ["fence", "net", "ticket"] 
        }
        year_path = os.path.join(self._path, year)
        for day in ["day1", "day2"]:
            for task_name in task_dict[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(year_path, task_name + ".pdf"),
                    editorial_files= None,
                    code_files= None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_year(self, parse_path):
        year = ""
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)

                # task = Task(
                #     name = ,
                #     statements = ,
                #     graders = ,
                #     editorial_files = ,
                #     code_files = ,
                #     attachments = ,
                # )
                # contest.add_task(task, day)
        contest.write(parse_path)

    def _scrape_one(self, contest_id, submission_id, task_folder):
        scraper = CSESScraper()
        test_folder = os.path.join(task_folder, "tests")
        scraper.login()
        for filename in os.listdir(test_folder):
            file_path = os.path.join(test_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        
        group_score = scraper.get_submission_result(contest_id, submission_id)
        subtask_json = scraper.download_testcases(contest_id, submission_id, test_folder, group_score)
        
        file_path = os.path.join(task_folder, "subtasks.json")
        if os.path.isfile(file_path):
            os.remove(file_path)
            # print(f"Removed subtasks.json from {task_folder}")

        with open(file_path, "w") as f:
            json.dump(subtask_json, f, indent=4)
    

    def _scrape_all(self):
        base_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/CEOI/2021/contest"
        jobs = [
        ("390", "12598982", base_path + "/diversity/tests"),
        ("390", "12598788", base_path + "/ltriominoes/tests"),
        ("390", "12598787", base_path + "/newspapers/tests"),
        ("391", "12598794", base_path + "/stones/tests"),
        ("391", "12598793", base_path + "/tortoise/tests"),
        ("391", "12598799", base_path + "/wells/tests")
        # Add more (contest_id, submission_id, test_folder) tuples here
        ]
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(self._scrape_one, cid, sid, folder) for cid, sid, folder in jobs]

        print("All scrapes submitted.")

    def _get_cses_problem_info(self, years):
        cses_scraper = CSESScraper()
        cses_scraper.login()
        if os.path.exists(os.path.join(self._path, "cses_problem_info.json")):
            with open(os.path.join(self._path, "cses_problem_info.json"), "r") as f:
                cses_problem_info = json.load(f)
        else:
            cses_problem_info = {}
        jobs = []
        for year in years:
            contest_ids = self.cses_ids[year]
            contest_folder = os.path.join(self._restructure_path, year, "contest")
            with open(os.path.join(contest_folder, "meta_info.json"), "r") as f:
                meta_info = json.load(f)
            problem_info = cses_problem_info.get(year, {})
            for day, contest_id in contest_ids.items():
                contest_problems = cses_scraper.get_problem_limits(contest_id=contest_id)
                # import pdb; pdb.set_trace()
                matching_pairs = fuzzy_matching_indices(meta_info[day], [problem['title'] for problem in contest_problems.values()], threshold=0.6)
                for i, j in matching_pairs:
                    task = meta_info[day][i]
                    if task in problem_info:
                        continue
                    problem = list(contest_problems.values())[j]
                    problem_info[task] = {
                        "time_limit": parse_time_to_seconds(problem["time_limit"]),
                        "memory_limit": parse_memory_to_mb(problem["memory_limit"]),
                        "submission_id": []
                    }
                    solutions_path = os.path.join(contest_folder, task,"solutions", "codes")
                    solutions = [os.path.join(solutions_path, f) for f in os.listdir(solutions_path) if f.endswith(".cpp") or f.endswith(".c") or f.endswith(".cxx")]
                    for solution in solutions:
                        assert os.path.exists(solution), f"Solution file {solution} does not exist."
                        time.sleep(20)
                        submission_id = cses_scraper.submit_solution(problem['submit_link'], solution, debug=False, option = "C++17")
                        if submission_id:
                            problem_info[task]["submission_id"].append((submission_id, os.path.basename(solution)))
                
                for task, info in problem_info.items():
                    if "subtasks" in info or "submission_id" not in info:
                        continue
                    highest_score = -1
                    job = None
                    task_path = os.path.join(contest_folder, task)
                    solutions_path = os.path.join(task_path, "solutions", "codes")
                    solution_info = {}
                    for entry in os.listdir(solutions_path):
                        path = os.path.join(solutions_path, entry)
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                        elif entry == "solution_info.json" or entry == "solution.json":
                            os.remove(path)
                            
                    for submission_id, solution_name in info["submission_id"]:
                        submission_result, feedback = cses_scraper.get_submission_result(contest_id, submission_id)
                        # assert int(submission_result) == 100, f"Submission {info['submission_id']} for task {task} failed with result: {submission_result[1]}"
                        subtasks = {}
                        for subtask in feedback:
                            subtask_id = int(subtask[0].strip("#"))
                            score = float(subtask[-1])
                            subtasks[subtask_id] = {
                                "score": score,
                            }
                        problem_info[task]["subtasks"] = subtasks

                        code_file = os.path.join(solutions_path, solution_name)
                        category = "correct"
                        if solution_name == "no_solution.cpp":
                            category = "no_solution"
                        elif solution_name == "NA.cpp":
                            category = "NA"
                        else:
                            for group in feedback:
                                if group[1] == "WRONG ANSWER":
                                    category = "wrong_answer"
                                    break
                                elif group[1] == "TIME LIMIT EXCEEDED":
                                    category = "time_limit"
                                    break
                                elif group[1] == "RUNTIME ERROR":
                                    category = "runtime_error"
                                    break
                            if not feedback:
                                category = "compile_error"

                        category_folder = os.path.join(solutions_path, category)
                        os.makedirs(category_folder, exist_ok=True)
                        shutil.copy2(code_file, os.path.join(category_folder, solution_name))
                        if category not in solution_info:
                            solution_info[category] = {}
                        feedback_dict = {
                            int(subtask[0].strip("#")): {
                                "status": subtask[1],
                                "score": float(subtask[2])
                            }
                            for subtask in feedback
                        }
                        solution_info[category][solution_name] = {
                            "contest": "BOI",
                            "year": year,
                            "task": task,
                            "result": submission_result,
                            "feedback": feedback_dict,
                            "contest_id": contest_id,
                            "submission_id": submission_id,
                        }
                        if category == "correct" and submission_result != "100":
                            print(f"Warning: task {task} Submission {submission_id} solution {solution_name} has a score of {submission_result} but is marked as {category}")
                        print(f"{task}, {submission_id}, {solution_name}, {submission_result}, {category}")
                        

                        if float(submission_result) > highest_score and category != "compile_error":
                            job = (contest_id, submission_id, task_path)
                            highest_score = float(submission_result)

                    if job:
                        jobs.append(job)

                    with open(os.path.join(solutions_path, "solution.json"), "w") as f:
                        json.dump(solution_info, f, indent=4)

                cses_problem_info[year] = problem_info

        # import pdb; pdb.set_trace()

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(self._scrape_one, cid, sid, folder) for cid, sid, folder in jobs]
        # self._organize_test_files(years)

        # with open(os.path.join(self._path, "cses_problem_info.json"), "w") as f:
        #     json.dump(cses_problem_info, f, indent=4)
        return cses_problem_info

    def _organize_test_files(self, years):
        for year in years:
            year_path = os.path.join(self._restructure_path, year, "contest")
            for task in os.listdir(year_path):
                if not os.path.isdir(os.path.join(year_path, task)) or task == "results":
                    continue
                test_path = os.path.join(year_path, task, "tests")
                for file in os.listdir(test_path):
                    if " " in file:
                        os.remove(os.path.join(test_path, file))
                        print(f"File removed: {file}")

    def _organize_test_file_2022(self):
        year_path = os.path.join(self._restructure_path, "2022", "contest")
        for task in os.listdir(year_path):
            if not os.path.isdir(os.path.join(year_path, task)) or task == "results":
                continue
            test_path = os.path.join(year_path, task, "tests")
            for file in os.listdir(test_path):
                taskname = file.split(".")[0]
                subtaskname = file.split(".")[-1]
                inout = file.split(".")[-2]

                if len(subtaskname) == 1:
                    os.remove(os.path.join(test_path, file))
                    print(f"File removed: {file}")
                else:
                    new_file = f"{taskname}.{subtaskname}.{inout}"
                    os.rename(os.path.join(test_path, file), os.path.join(test_path, new_file))

    
    def _update_subtask_and_problem_info(self, cses_problem_info):
        for year, tasks in cses_problem_info.items():
            contest_folder = os.path.join(self._restructure_path, year, "contest")
            for task, info in tasks.items():
                task_folder = os.path.join(contest_folder, task)
                #update subtasks.json
                # with open(os.path.join(task_folder, "subtasks.json"), "r") as f:
                #     subtasks = json.load(f)
                # for subtask_id, subtask in info['subtasks'].items():
                #     assert subtask_id in subtasks, f"Subtask {subtask_id} not found in {task_folder}/subtasks.json"
                #     if subtasks[subtask_id]["score"] == -1:
                #         subtasks[subtask_id]["score"] = subtask["score"]
                # with open(os.path.join(task_folder, "subtasks.json"), "w") as f:
                #     json.dump(subtasks, f)
                #update problem_info.json
                problem_info_path = os.path.join(task_folder, "problem.json")
                if os.path.exists(problem_info_path):
                    with open(problem_info_path, "r") as f:
                        problem_info = json.load(f)
                else:
                    problem_info = {}
                problem_info['task'] = problem_info.get('task', task)
                problem_info['time_limit'] = info['time_limit']
                problem_info['memory_limit'] = info['memory_limit']
                problem_info['task_type'] = problem_info.get('task_type', "Batch")
                with open(problem_info_path, "w") as f:
                    json.dump(problem_info, f)

    def _get_contest_ids(self):
        cses_website = "https://cses.fi/ceoi/list/"
        html = fetch_url(cses_website)
        soup = BeautifulSoup(html, 'html.parser')

        result = {}

        # Find all <h2> headers with year and following <ul class="task-list"> with contest links
        for header in soup.find_all('h2'):
            year_text = header.get_text(strip=True)
            if re.fullmatch(r'CEOI \d{4}', year_text):
                year = year_text.split()[1]
                ul = header.find_next_sibling('ul', class_='task-list')
                if ul:
                    links = ul.find_all('a')
                    if len(links) >= 2:
                        # Extract the contest ID from the URL
                        day1_id = re.search(r'/(\d+)/list/', links[0]['href'])
                        day2_id = re.search(r'/(\d+)/list/', links[1]['href'])
                        if day1_id and day2_id:
                            result[year] = {
                                'day1': int(day1_id.group(1)),
                                'day2': int(day2_id.group(1)),
                            }
        return result

    def _get_all_problem_info(self):
        self.cses_ids = ceoi_crawler._get_contest_ids()
        years = self.cses_ids.keys()
        cses_problem_info = self._get_cses_problem_info(["2009", "2012"])

        # To do: 
        # Finished: 2021 to 2005
        # no solution: 2010 arithmetic, 2008 information, 2007
        # test error: 2014 question, 2012 highway, 2011 Treasure, 2008 order
        # https://loj.ac/
        # https://www.luogu.com.cn/

        # https://github.com/dolphingarlic/CompetitiveProgramming/tree/master/CEOI
        # https://github.com/koosaga/olympiad/tree/master/CEOI
        # https://github.com/mostafa-saad/MyCompetitiveProgramming/tree/master/Olympiad/CEOI
        # https://github.com/thecodingwizard/competitive-programming/tree/master/CEOI
        # https://github.com/luciocf/CP-Problems/tree/master/CEOI

        # print(cses_problem_info)
        self._update_subtask_and_problem_info(cses_problem_info)
        # for year in contest_ids:
        #     for day in contest_ids[year]:
        #         contest_id = contest_ids[year][day]
        #         print(year + " " + day + " " + str(contest_id))

    def restructure(self):
        new_path = self._restructure_path
        # self._restructure_2024(new_path)
        # self._restructure_2023(new_path)
        # self._restructure_2022(new_path)
        # self._restructure_2021(new_path)
        # self._restructure_2020(new_path)
        # self._restructure_2019(new_path)
        # self._restructure_2018(new_path)
        # self._restructure_2017(new_path)
        # self._restructure_2016(new_path)
        # # self._restructure_2015(new_path)
        # self._restructure_2014(new_path)
        # self._restructure_2013(new_path)
        # self._restructure_2012(new_path)
        # self._restructure_2011(new_path)
        # self._restructure_2010(new_path)
        # self._restructure_2009(new_path)
        # self._restructure_2008(new_path)
        # self._restructure_2007(new_path)
        # self._restructure_2006(new_path)
        # self._restructure_2005(new_path)


    def parse(self):
        self._preprocess_parse(self._restructure_path, parse_statement=True, parse_solution=True, rerun=False)
        self._create_problem_info_json(converter_type="marker")

if __name__ == "__main__":
    # converter = MarkerConverter(source_format="pdf", target_format="markdown", use_LLM=True)
    ceoi_crawler = CEOICrawler(competition="CEOI", crawl_path=f"{os.environ['HOME_DIR']}/IOI-Bench/CEOI", restructure_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/CEOI", parse_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/CEOI", converter=None)
    #ceoi_crawler.restructure("$HOME_DIR/IOI-Bench-Parsed/CEOI")  # Uncomment if parse logic is implemented
    ceoi_crawler.restructure()
    # ceoi_crawler._organize_test_file_2022()
    # ceoi_crawler.parse()
    # ceoi_crawler._scrape_one("187", "12727252", "$HOME_DIR/IOI-Bench-Restructured/CEOI/2007/contest/Ministry")
    # ceoi_crawler._scrape_all()
    # ceoi_crawler._organize_test_files(["2005", "2006", "2007", "2008", "2009", "2010", "2011", "2012", "2013", "2014", "2015", "2016", "2017", "2018", "2019", "2020", "2021"])
    # ceoi_crawler._get_all_problem_info()


# import pdb; pdb.set_trace()