import os
from base_crawler import Crawler, Contest, Task, CSESScraper
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
import time
# from converter import MarkerConverter
from concurrent.futures import ThreadPoolExecutor
import json
import shutil

def split_solution_files(dir):
    file_list = [os.path.join(dir, f) for f in os.listdir(dir)]
    code_files = []
    editorial_files = []
    editorial_exts = {'.pdf', '.tex', '.png', '.jpg', '.jpeg', '.gif'}
    for file in file_list:
        ext = os.path.splitext(file)[1].lower()
        if ext in editorial_exts:
            editorial_files.append(file)
        else:
            code_files.append(file)
    return code_files, editorial_files

class BOICrawler(Crawler):
    def __init__(self, *, competition="BOI", crawl_path,restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=converter)
        self.base_url = "https://boi.cses.fi/tasks.php"
        self.cses_ids = self._get_contest_ids()

    def _get_contest_ids(self):
        cses_website = "https://cses.fi/boi/list/"
        html = fetch_url(cses_website)
        soup = BeautifulSoup(html, 'html.parser')

        result = {}

        # Find all <h2> headers with year and following <ul class="task-list"> with contest links
        for header in soup.find_all('h2'):
            year_text = header.get_text(strip=True)
            if re.fullmatch(r'BOI \d{4}', year_text):
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
        self.cses_ids = boi_crawler._get_contest_ids()
        years = self.cses_ids.keys()
        cses_problem_info = self._get_cses_problem_info(["2009", "2010"])
        self._update_subtask_and_problem_info(cses_problem_info)

        # To do: 
        # Finished: 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2017, 2018, 2019, 2020, 2021, 2023, 2024
        # no solution: 2019 flash, 2005
        # test error: 2022, 2016

        # https://github.com/stefdasca/CompetitiveProgramming/blob/master/BalticOI/Baltic%2007-Sequence.cpp
        # https://github.com/AvaLovelace1/competitive-programming/blob/master/solutions/boi/boi2007p3.cpp
        # https://github.com/Carson-Tang/Competitive-Programming/blob/master/BOI/boi2007p3.cpp
        # https://oj.uz/problems/source/boi2006
        # https://github.com/koosaga/olympiad/tree/master/Baltic

        

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
                        time.sleep(30)
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

    def _download_tasks(self):
        BASE_URL = "https://boi.cses.fi/files/"
        # List of years from 1995 to 2024 (inclusive)
        years = range(1995, 2025)

        # Loop over each year
        for year in years:
            year_str = str(year)
            print(f"\nProcessing year {year_str}...")
            
            # Download tasks (day1 and day2)
            for day in ['day1', 'day2']:
                # Create folder {year}/{day}
                task_dir = os.path.join(self._path, year_str, day)
                os.makedirs(task_dir, exist_ok=True)
                
                # Build the file URL and destination file path
                filename = f"boi{year}_{day}.pdf"
                file_url = f"{BASE_URL}{filename}"
                dest_path = os.path.join(task_dir, f"{day}.pdf")
                
                print(f"Downloading {file_url} to {dest_path}...")
                try:
                    response = requests.get(file_url)
                    if response.status_code == 200:
                        with open(dest_path, "wb") as f:
                            f.write(response.content)
                        print(f"Saved {dest_path}")
                    else:
                        print(f"Warning: Failed to download {file_url} (status code {response.status_code}).")
                except Exception as e:
                    print(f"Error downloading {file_url}: {e}")
            
            # Download and extract zip files for tests and solutions
            for zip_type in ['tests', 'solutions']:
                zip_filename = f"boi{year}_{zip_type}.zip"
                zip_url = f"{BASE_URL}{zip_filename}"
                zip_dest = os.path.join(self._path, year_str, f"{zip_type}.zip")
                
                print(f"Downloading {zip_url} to {zip_dest}...")
                download_file(zip_url, zip_dest)
                try:
                    # Create extraction directory: {year}/{zip_type}/
                    extract_dir = os.path.join(self._path, year_str, zip_type)
                    os.makedirs(extract_dir, exist_ok=True)
                    
                    # Unzip the file into the extraction directory
                    with zipfile.ZipFile(zip_dest, "r") as zip_ref:
                        zip_ref.extractall(extract_dir)
                    print(f"Extracted {zip_dest} to {extract_dir}")
                except Exception as e:
                    print(f"Error extracting {zip_url}: {e}")
    def crawl(self):
        self._download_tasks()

    def _find_test_folder(self, path, combine=True):
        """
        If combine=False: Find the last group folder in the given path.
        If combine=True: Create a new folder containing all test cases from all group folders.
        """
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        if not folders:
            return None
        
        if not combine:
            # Original behavior: return the last folder alphabetically
            folders.sort()
            return os.path.join(path, folders[-1])
        
        # New behavior: combine all test cases into a new directory
        import shutil
        combined_dir = os.path.join(path, "combined_tests")
        shutil.rmtree(combined_dir, ignore_errors=True)
        os.makedirs(combined_dir, exist_ok=True)
        
        # Track files to handle name conflicts
        file_counts = {}
        
        for folder in folders:
            folder_path = os.path.join(path, folder)
            test_files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            
            for test_file in test_files:
                source_path = os.path.join(folder_path, test_file)
                # Handle possible file name conflicts
                if test_file not in file_counts:
                    file_counts[test_file] = 1
                    dest_file = test_file
                    dest_path = os.path.join(combined_dir, dest_file)
                    shutil.copy2(source_path, dest_path)
        print(f"Created combined test folder at {combined_dir} with {sum(file_counts.values())} files from {len(folders)} group folders")
        return combined_dir
    
    def _create_subtasks(self, test_files):
        subtasks = {}
        for test_file in test_files:
            if test_file.endswith(".in"):
                task_name = test_file.split(".")[0]
                subtasks_names = test_file.split("-")[-1].split(".")[0]
                for number in subtasks_names:
                    subtask_name = f"subtask{number}"
                    if number not in subtasks:
                        subtasks[number] = {"score": -1, "testcases": [], "task": subtask_name}
                    subtasks[number]["testcases"].append(test_file.replace(".in", ""))
        return subtasks
    
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

    def _restructure_2023(self, new_path):
        year = "2023"
        contest = Contest(year=year)
        year_dir = os.path.join(self._path, year)
        test_dir = os.path.join(year_dir, "tests")
        day1_tasks = ["astronomer", "staringcontest", "tycho"]
        day2_tasks = ["minequake", "mineraldeposits", "sequence"]
        for i, tasks in enumerate([day1_tasks, day2_tasks]):
            for task in tasks:
                day = f"day{i+1}"
                problem_statement_folder = os.path.join(test_dir, task, "problem_statement")
                test_folder = self._find_test_folder(os.path.join(test_dir, task, "data", "secret"), combine=True)
                task_obj = Task(
                    name=task,
                    statements=[os.path.join(test_dir, f"{task}.pdf"), problem_statement_folder + "/problem.en.tex", problem_statement_folder + "/img"],
                    subtasks=create_subtask_json_kattis(os.path.join(test_dir, task, "data")),
                    tests=test_folder,
                    code_files=os.path.join(test_dir, task, "submissions", "accepted"),
                )
                contest.add_task(task_obj, day)
        contest.write(new_path)

    def _restructure_2024(self, new_path):
        # Parse the 2024 contest data
        year = "2024"
        contest = Contest(year=year)
        year_dir = os.path.join(self._path, year)
        test_dir = os.path.join(year_dir, "tests")
        day1_tasks = []
        day2_tasks = []
        for task in os.listdir(test_dir):
            day, task_name = task.split("-")
            if day == 'd1':
                day1_tasks.append(task_name)
            elif day == 'd2':
                day2_tasks.append(task_name)
        day1_pdf = os.path.join(year_dir, "day1", "day1.pdf")
        day2_pdf = os.path.join(year_dir, "day2", "day2.pdf")
        day1_range =  find_task_splits(day1_pdf, day1_tasks)
        day2_range =  find_task_splits(day2_pdf, day2_tasks)
        split_pdf(day1_pdf, day1_range)
        split_pdf(day2_pdf, day2_range)
        for i, tasks in enumerate([day1_range.keys(), day2_range.keys()]):
            for task in tasks:
                day = f"day{i+1}"
                task = Task(
                    name=task,
                    statements=os.path.join(year_dir, day, f"{task}.pdf"),
                    subtasks=self._create_subtasks(os.listdir(os.path.join(year_dir, "tests", f"d{i+1}-{task}"))),
                    tests=os.path.join(year_dir, "tests", f"d{i+1}-{task}"),
                    code_files=os.path.join(year_dir, "solutions", f"d{i+1}-{task}-solution.cpp"),
                )
                contest.add_task(task, day)
        contest.write(new_path)

    def _restructure_2022(self, parse_path):
        year = "2022"
        contest = Contest(year=year)
        tasks = {
            "day1": ["art", "events", "vault"],
            "day2": ["communication", "island", "passes"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        unzip_files(test_path)
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                testdata_path = os.path.join(test_path, f"boi2022-{day}-{task_name}-testdata")
                convert_cases_by_hash(os.path.join(testdata_path, "cases_by_hash"), testdata_path)
                subtask =  create_subtasks_by_hash(os.path.join(testdata_path, "subtasks"))
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = os.path.join(solution_path, f"{task_name}.cpp"),
                    attachments = None,
                    # grader = os.path.join(testdata_path, "grader"),
                    subtasks = subtask,
                    tests = os.path.join(testdata_path, "tests"),
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2021(self, parse_path):
        year = "2021"
        contest = Contest(year=year)
        tasks = {
            "day1": ["books", "servers", "watchmen"],
            "day2": ["prison", "swaps", "xanadu"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = os.path.join(solution_path, f"{task_name}.cpp"),
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2020(self, parse_path):
        year = "2020"
        contest = Contest(year=year)
        tasks = {
            "day1": ["colors", "mixture", "joker"],
            "day2": ["graph", "village", "viruses"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = [os.path.join(solution_path, task_name, "solution", "model.cpp"),os.path.join(solution_path, task_name, "solution", "second.cpp")],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2019(self, parse_path):
        year = "2019"
        contest = Contest(year=year)
        tasks_names = {
            "day1": ["flash", "nautilus", "valley"],
            "day2": ["kitchen", "necklace", "olympiads"]
        }
        tasks = {
            "day1": ["flash", "nautilus", "valley"],
            "day2": ["kitchen", "necklace", "olymp"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks_names[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks_names[day], 120))
            for task_name in tasks[day]:
                pdf_name = task_name
                if task_name == "olymp":
                    pdf_name = "olympiads"
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{pdf_name}.pdf"),
                    editorial_files = os.path.join(solution_path, task_name, "sol.en.pdf"),
                    code_files = [os.path.join(solution_path, task_name, file) for file in os.listdir(os.path.join(solution_path, task_name)) if file.endswith(".cpp")],
                    attachments = [os.path.join(solution_path, task_name, file) for file in os.listdir(os.path.join(solution_path, task_name))],
                )
                if os.path.isdir(os.path.join(solution_path, task_name, "fast")):
                    task.code_files += [os.path.join(solution_path, task_name, "fast", file) for file in os.listdir(os.path.join(solution_path, task_name, "fast")) if file.endswith(".cpp")]
                if os.path.isdir(os.path.join(solution_path, task_name, "fast", "n^2")):
                    task.code_files += [os.path.join(solution_path, task_name, "fast", "n^2", file) for file in os.listdir(os.path.join(solution_path, task_name, "fast", "n^2")) if file.endswith(".cpp")]
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2018(self, parse_path):
        year = "2018"
        contest = Contest(year=year)
        tasks = {
            "day1": ["polygon", "dna", "worm"],
            "day2": ["alternating", "genetics", "paths"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = [os.path.join(solution_path, task_name, "accepted", file) for file in os.listdir(os.path.join(solution_path, task_name, "accepted")) if file.endswith(".cpp")],
                    attachments = [os.path.join(solution_path, task_name, file) for file in os.listdir(os.path.join(solution_path, task_name)) if file != "accepted"]
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2017(self, parse_path):
        year = "2017"
        contest = Contest(year=year)
        tasks = {
            "day1": ["politicaldevelopment", "railway", "toll"],
            "day2": ["catinatree", "friends", "plusminus"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = [os.path.join(solution_path, task_name, "accepted", file) for file in os.listdir(os.path.join(solution_path, task_name, "accepted")) if file.endswith(".cpp")],
                    attachments = [os.path.join(solution_path, task_name, file) for file in os.listdir(os.path.join(solution_path, task_name)) if file != "accepted"]
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2016(self, parse_path):
        year = "2016"
        contest = Contest(year=year)
        tasks = {
            "day1": ["bosses", "park", "spiral"],
            "day2": ["cities", "maze", "swap"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = os.path.join(solution_path, f"{task_name}-sol.cpp"),
                    attachments = None,
                    tests = os.path.join(test_path, task_name),
                )
                contest.add_task(task, day)
        contest.write(parse_path)
        # test_path = os.path.join(self._restructure_path, year, "contest", )

    def _restructure_2015(self, parse_path):
        year = "2015"
        contest = Contest(year=year)
        tasks = {
            "day1": ["bow", "edi", "net"],
            "day2": ["fil", "tug", "hac"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day], 120))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file and file.endswith(".cpp")],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2014(self, parse_path):
        year = "2014"
        contest = Contest(year=year)
        tasks = {
            "day1": ["coprobber", "friends", "sequence"],
            "day2": ["portals", "demarcation", "postmen"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task_solution_path = os.path.join(solution_path, task_name)
                code_files = []
                # Recursively get all files in the directory and subdirectories
                for root, _, files in os.walk(task_solution_path):
                    for file in files:
                        code_files.append(os.path.join(root, file))
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = code_files,
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2013(self, parse_path):
        year = "2013"
        contest = Contest(year=year)
        tasks = {
            "day1": ["ballmachine", "pipes", "numbers"],
            "day2": ["brunhilda", "tracks", "vim"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = os.path.join(solution_path, f"{task_name}-sol.pdf"),
                    code_files = os.path.join(solution_path, f"{task_name}-sol.cpp"),
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2012(self, parse_path):
        year = "2012"
        contest = Contest(year=year)
        tasks = {
            "day1": ["brackets", "mobile", "peaks"],
            "day2": ["fire", "melody", "tiny"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = os.path.join(solution_path, f"{task_name}-sol.cpp"),
                    code_files = None,
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2011(self, parse_path):
        year = "2011"
        contest = Contest(year=year)
        tasks = {
            "day1": ["grow", "icecream", "lamp", "vikings"],
            "day2": ["plagiarism", "meetings", "treemirroring", "polygon"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day], 100, 4))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = os.path.join(solution_path, f"{task_name}-sol.pdf"),
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file and file.endswith(".cpp")],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2010(self, parse_path):
        year = "2010"
        contest = Contest(year=year)
        tasks = {
            "day1": ["bears", "lego", "pcb"],
            "day2": ["bins", "candies", "mines"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = os.path.join(solution_path, f"{task_name}-sol.pdf"),
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file and (file.endswith(".cpp") or file.endswith(".c"))],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2009(self, parse_path):
        year = "2009"
        contest = Contest(year=year)
        tasks = {
            "day1": ["beetle", "candy", "subway"],
            "day2": ["monument", "rectangle", "trian"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = os.path.join(solution_path, f"{task_name}-sol.pdf"),
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file and (file.endswith(".cpp") or file.endswith(".c"))],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2008(self, parse_path):
        year = "2008"
        contest = Contest(year=year)
        tasks = {
            "day1": ["game", "gates", "magical"],
            "day2": ["elections", "gloves", "grid"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = os.path.join(solution_path, f"{task_name}-sol-en.pdf"),
                    code_files = None,
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2007(self, parse_path):
        year = "2007"
        contest = Contest(year=year)
        tasks = {
            "day1": ["escape", "sorting", "sound"],
            "day2": ["fence", "points", "sequence"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2006(self, parse_path):
        year = "2006"
        contest = Contest(year=year)
        tasks = {
            "day1": ["bitwise", "coins", "countries"],
            "day2": ["city", "rle", "jump"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file],
                    code_files = None,
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_2005(self, parse_path):
        year = "2005"
        contest = Contest(year=year)
        tasks = {
            "day1": ["camp", "lisp", "maze"],
            "day2": ["ancient", "trip", "polygon"]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day], 200))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file and "sol" in file][0],
                    code_files = [os.path.join(solution_path, file) for file in os.listdir(solution_path) if task_name in file and (file.endswith(".c") or file.endswith(".cpp"))],
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)

    def _restructure_year(self, parse_path):
        year = ""
        contest = Contest(year=year)
        tasks = {
            "day1": ["", "", ""],
            "day2": ["", "", ""]
        }
        solution_path = os.path.join(self._path, year, "solutions")
        test_path = os.path.join(self._path, year, "tests")
        for day in ["day1", "day2"]:
            task_path = os.path.join(self._path, year, day)
            task_file = os.path.join(task_path, f"{day}.pdf")
            if next((file for file in os.listdir(task_path) if file.startswith(tasks[day][0])), None) is None:
                split_pdf(task_file, find_task_splits(task_file, tasks[day]))
            for task_name in tasks[day]:
                task = Task(
                    name = task_name,
                    statements = os.path.join(task_path, f"{task_name}.pdf"),
                    editorial_files = None,
                    code_files = os.path.join(solution_path, f"{task_name}.cpp"),
                    attachments = None,
                )
                contest.add_task(task, day)
        contest.write(parse_path)



    def restructure(self):
        new_path = self._restructure_path
        # self._restructure_2005(new_path)
        # self._restructure_2006(new_path)
        # self._restructure_2007(new_path)
        # self._restructure_2008(new_path)
        # self._restructure_2009(new_path)
        # self._restructure_2010(new_path)
        # self._restructure_2011(new_path)
        # self._restructure_2012(new_path)
        # self._restructure_2013(new_path)
        # self._restructure_2014(new_path)
        # self._restructure_2015(new_path)
        self._restructure_2016(new_path)
        # self._restructure_2017(new_path)
        # self._restructure_2018(new_path)
        # # self._restructure_2019(new_path)
        # self._restructure_2020(new_path)
        # # self._restructure_2021(new_path)
        # self._restructure_2022(new_path)
        # self._restructure_2023(new_path)
        # self._restructure_2024(new_path)

    def parse(self, parse_path):
        pass

if __name__ == "__main__":
    # converter = MarkerConverter(source_format="pdf", target_format="markdown", use_LLM=True)
    boi_crawler = BOICrawler(competition="BOI", crawl_path=f"{os.environ['HOME_DIR']}/IOI-Bench/BOI", restructure_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/BOI", parse_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/BOI", converter=None)
    # boi_crawler.parse()
    boi_crawler.restructure()
    # boi_crawler._restructure_2019(boi_crawler._restructure_path)
    # boi_crawler._get_all_problem_info()
    # boi_crawler._scrape_one("247", "12778515", "$HOME_DIR/IOI-Bench-Restructured/BOI/2019/contest/flash")

# import pdb; pdb.set_trace()