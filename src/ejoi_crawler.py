import os
from base_crawler import Crawler, Contest, Task
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
from urllib.parse import urljoin

class EJOICrawler(Crawler):
    def __init__(self, *, competition="EJOI", crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, 
                         crawl_path=crawl_path,
                         restructure_path=restructure_path,
                         parse_path=parse_path,
                         converter=converter)
        self.base_url = "https://olympiads.jsoft.am/"
    # def _download_2023_files(self):
    #     days = {
    #         "day1": 1693,
    #         "day2": 1694,
    #     }
    #     problem_dict = {
    #         "day1": {
    #             "tree_search": (8762, 1,2024, "Interactive"),
    #             "teleporters": (8763, 1, 2024),
    #             "opening_offices": (8764, 1, 2024)
    #         },
    #         "day2": {
    #             "square_grid_puzzle": (8765, 1, 2024),
    #             "tree_infection": (8766, 1, 2024),
    #             "team_building": (8767, 1, 2024),
    #         }
    #     }
    #     year_path = os.path.join(self._path, "2023")
    #     for day, contest_id in days.items():
    #         day_path = os.path.join(year_path, day)
    #         os.makedirs(day_path, exist_ok=True)
    #         # Download the problem statement
    #         for problem, problem_info in problem_dict[day].items():
    #             problem_folder = os.path.join(day_path, problem)
    #             os.makedirs(problem_folder, exist_ok=True)
    #             try:
    #                 self.qoj_scraper.download_file(f"https://qoj.ac/download.php?type=statement&id={problem_info[0]}&contest_id={contest_id}", os.path.join(problem_folder, f"{problem}_en.pdf"))
    #             except Exception as e:
    #                 print(f"Error downloading {problem} statement: {e}")
    #             # Download the attachment
    #             try:
    #                 self.qoj_scraper.download_file(f"https://qoj.ac/download.php?type=problem&id={problem_info[0]}&contest_id={contest_id}", os.path.join(problem_folder, f"attachment.zip"))
    #             except Exception as e:
    #                 print(f"Error downloading {problem} attachment: {e}")
    #             probelm_info = {
    #                 "task": problem,
    #                 "time_limit": problem_info[1],
    #                 "memory_limit": problem_info[2],
    #                 "task_type": "batch" if len(problem_info) == 3 else problem_info[-1]
    #             }
    #             with open(os.path.join(problem_folder, "problem.json"), "w") as f:
    #                 json.dump(probelm_info, f, indent=4)
    #     #meta_info
    #     with open(os.path.join(year_path, "meta_info.json"), "w") as f:
    #         json.dump({
    #             "day1": list(problem_dict["day1"].keys()),
    #             "day2": list(problem_dict["day2"].keys())
    #         }, f, indent=4)
    def _unzip_2023_files(self):
        year_path = os.path.join(self._path, "2023")
        for day in ["day1", "day2"]:
            day_path = os.path.join(year_path, day)
            for task in os.listdir(day_path):
                task_path = os.path.join(day_path, task)
                attachment_path = os.path.join(task_path, "attachment.zip")
                if os.path.exists(attachment_path):
                    unzip_file(attachment_path, os.path.join(task_path, "attachments"))
                #find zip file start with "TestData"
                for file in os.listdir(task_path):
                    if file.startswith("TestData") and file.endswith(".zip"):
                        zip_path = os.path.join(task_path, file)
                        unzip_file(zip_path, os.path.join(task_path, "tests"))
    def _find_links_by_year(self):
        # Parse the HTML with BeautifulSoup
        html = fetch_url(self.base_url)
        soup = BeautifulSoup(html, "html.parser")
        # Find the table containing the olympiad details (by its class)
        table = soup.find("table", class_="table-olymps")

        # Dictionary to collect URLs by year (as integers)
        urls_by_year = {}

        # Get all rows in the table (skip header row if present)
        rows = table.find_all("tr")
        for row in rows:
            tds = row.find_all("td")
            if not tds:
                continue  # Skip header or empty rows
            # The second <td> should contain the year as an <a> tag
            year_cell = tds[1]
            a_year = year_cell.find("a")
            if not a_year:
                continue
            try:
                year_int = int(a_year.get_text(strip=True))
            except ValueError:
                continue
            if 2017 <= year_int <= 2024:
                # Collect all <a> tags in this row
                row_urls = []
                for a in row.find_all("a"):
                    href = a.get("href")
                    if href:
                        # Resolve relative URLs:
                        if "Details" in href or "CountryStat" in href:
                            continue
                        if "http" in href and href.startswith("//"):
                            full_url = href[2:]
                        elif href.startswith("//"):
                            full_url = "https:" + href
                        else:
                            full_url = urljoin(self.base_url, href)
                        row_urls.append(full_url)
                urls_by_year[year_int] = row_urls[0]
    def _download_2024(self):
        year = "2024"
        url = "https://ejoi2024.gov.md/tasks/"
        html = fetch_url(url)
        soup = BeautifulSoup(html, 'html.parser')

        # We'll assume tasks are inside the "entry-content" div.
        content_div = soup.find("div", class_="entry-content")
        if not content_div:
            raise ValueError("Could not find entry-content div")

        # Get all <p> tags inside the content
        p_tags = content_div.find_all("p")
        current_day = None
        tasks = {}  # tasks[day] will be a list of dicts with keys: name, statement, solution, tests
        editorial_url = None

        for p in p_tags:
            text = p.get_text(strip=True)
            if text.startswith("Day 1"):
                current_day = "day1"
                continue
            elif text.startswith("Day 2"):
                current_day = "day2"
                continue
            elif "Editorial" in text:
                a_editorial = p.find("a")
                if a_editorial:
                    editorial_url = a_editorial.get("href")
                continue

            # If we're in a day and the paragraph contains tasks (tasks are separated by <br>)
            if current_day and p.find("br"):
                # Decode the inner HTML and split by <br> tags.
                parts = p.decode_contents().split("<br")
                for part in parts:
                    part = part.strip()
                    if not part:
                        continue
                    # Create a new BeautifulSoup object for this part
                    part_soup = BeautifulSoup(part, 'html.parser')
                    full_text = part_soup.get_text(" ", strip=True)
                    if ":" not in full_text:
                        continue
                    # The task name is the part before the colon
                    task_name = full_text.split(":", 1)[0].strip()
                    task_name = re.sub(r"[^\w\s]", "", task_name)  # Remove non-alphanumeric characters
                    # Assume the links appear in order: statement, solution, tests
                    links = part_soup.find_all("a")
                    if len(links) < 3:
                        continue
                    tasks.setdefault(current_day, []).append({
                        "name": task_name,
                        "statement": links[0].get("href"),
                        "solution": links[1].get("href"),
                        "tests": links[2].get("href")
                    })

        # --- Download Files ---

        # Create a base directory for the year.
        base_year_dir = os.path.join(self._path, year)
        os.makedirs(base_year_dir, exist_ok=True)
        # For each day, create its directory and then for each task, create a task directory.
        for day, task_list in tasks.items():
            day_dir = os.path.join(base_year_dir, day)
            os.makedirs(day_dir, exist_ok=True)
            for task in task_list:
                task_dir = os.path.join(day_dir, task["name"])
                print(task_dir)
                os.makedirs(task_dir, exist_ok=True)
                # Download the English statement as {task}_en.pdf
                statement_filename = f"{task['name']}_en.pdf"
                download_file(task["statement"], os.path.join(task_dir, statement_filename))
                # Download the solution as {task}.cpp (even if the link is to a .txt file)
                solution_filename = f"{task['name']}.cpp"
                download_file(task["solution"], os.path.join(task_dir, solution_filename))
                # Download the tests as tests.zip
                download_file(task["tests"], os.path.join(task_dir, "tests.zip"))

        # Download the editorial into the base year directory if available.
        if editorial_url:
            editorial_filename = os.path.basename(editorial_url)
            download_file(editorial_url, os.path.join(base_year_dir, editorial_filename))
    def _unzip_2024(self):
        year = "2024"
        base_year_dir = os.path.join(self._path, year)
        for day in ["day1", "day2"]:
            day_dir = os.path.join(base_year_dir, day)
            if not os.path.exists(day_dir):
                continue
            for task in os.listdir(day_dir):
                task_dir = os.path.join(day_dir, task)
                unzip_files(task_dir)
    def crawl(self):
        links_by_year = self._find_links_by_year()
        valid_years = [2024, 2022, 2020, 2019, 2017]
        self._download_2024()
        return
    def _restructure_2024(self):
        year = "2024"
        year_path = os.path.join(self._restructure_path, year)
        os.makedirs(year_path, exist_ok=True)
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            for task in os.listdir(os.path.join(self._path, year, day)):
                task_dir = os.path.join(self._path, year, day, task)
                notice = os.path.join(task_dir, task, "notice.txt")
                #read TL: and ML: from notice.txt
                with open(notice, "r") as f:
                    lines = f.readlines()
                    time_limit = parse_time_to_seconds(lines[0].split(":")[1].strip())
                    memory_limit = parse_memory_to_mb(lines[1].split(":")[1].strip())
                problem_json = {
                    "task": task,
                    "time_limit": time_limit,
                    "memory_limit": memory_limit,
                    "task_type": ""
                }
                submission_path = os.path.join(task_dir, f"ejoi2024{task}")
                with open(os.path.join(submission_path, "subtasks.json"), "r") as f:
                    subtasks = json.load(f)
                sample_tests = [f for f in os.listdir(submission_path) if f.startswith("sample")]
                test_folder = os.path.join(task_dir, task, "tests")
                for sample_test in sample_tests:
                    sample_test_path = os.path.join(submission_path, sample_test)
                    test_path = os.path.join(test_folder, sample_test)
                    #copy sample tests to test folder
                    shutil.copyfile(sample_test_path, test_path)
                task = Task(
                    name=task,
                    statements=os.path.join(task_dir, f"{task}_en.pdf"),
                    tests=test_folder,
                    code_files=[os.path.join(task_dir, f"{task}.cpp")],
                    graders=os.path.join(task_dir, "graders"),
                    subtasks=subtasks,
                    problem_json=problem_json,
                )
                contest.add_task(task)
        contest.write(self._restructure_path)
    def _restructure_2023(self):
        year = "2023"
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            for task in os.listdir(day_path):
                task_dir = os.path.join(day_path, task)
                problem_json = json.load(open(os.path.join(task_dir, "problem.json")))
                tests_folder = os.path.join(task_dir,[f for f in os.listdir(task_dir) if f.startswith("TestData")][0].replace(".zip", ""))
                submission_result_folder = os.path.join(task_dir, f"ejoi2023{task}")
                with open(os.path.join(submission_result_folder, "subtasks.json"), "r") as f:
                    subtasks = json.load(f)
                sample_tests = [f for f in os.listdir(submission_result_folder) if f.startswith("sample")]
                for sample_test in sample_tests:
                    sample_test_path = os.path.join(submission_result_folder, sample_test)
                    test_path = os.path.join(tests_folder, sample_test)
                    #copy sample tests to test folder
                    shutil.copyfile(sample_test_path, test_path)
                solution = os.path.join(submission_result_folder, "solution.cpp")
                print(solution)
                task_obj = Task(
                    name=task,
                    statements=os.path.join(task_dir, f"{task}_en.pdf"),
                    tests=tests_folder,
                    code_files=[solution],
                    checkers=os.path.join(task_dir, "checkers"),
                    subtasks=subtasks,
                    problem_json=problem_json,
                    attachments=os.path.join(task_dir, "attachments"),
                )
                contest.add_task(task_obj, split=day)
        contest.write(self._restructure_path)
    def restructure(self):
        self._restructure_2023()
        #self._restructure_2024()
    def parse(self):
        pass

if __name__ == "__main__":
    ejoi_crawler = EJOICrawler(
        crawl_path = f"{os.environ['HOME_DIR']}/IOI-Bench/EJOI",
        restructure_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/EJOI",
        parse_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed/EJOI",
        converter=None
    )
    ejoi_crawler.restructure()