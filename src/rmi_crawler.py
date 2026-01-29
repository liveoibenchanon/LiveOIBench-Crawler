import os
from base_crawler import Crawler, Contest, Task
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar

class RMICrawler(Crawler):
    def __init__(self, *, competition="RMI", crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=converter)
    def crawl(self):
        html = fetch_url(self.base_url)
        return html
    def restructure_eval(self):
        years = ["2023", "2024"]
        for year in years:
            year_folder = os.path.join(self._path, year)
            contest = Contest(year=year)
            for day in ["day1", "day2"]:
                day_folder = os.path.join(year_folder, day)
                for task in os.listdir(day_folder):
                    task_folder = os.path.join(day_folder, task)
                    #unzip_files(task_folder)
                    tests_folder = os.path.join(task_folder, [f for f in os.listdir(task_folder) if f.startswith("TestData")][0]).replace(".zip", "")
                    submission_result_folder = os.path.join(task_folder, [f for f in os.listdir(task_folder) if f.endswith(task.lower())][0])
                    sample_tests = [f for f in os.listdir(task_folder) if f.startswith("sample")]
                    if len(sample_tests) > 0:
                        #copy sample tests to test folder
                        for sample_test in sample_tests:
                            sample_test_path = os.path.join(task_folder, sample_test)
                            test_path = os.path.join(tests_folder, sample_test)
                            if not os.path.exists(test_path):
                                os.rename(sample_test_path, test_path)
                    subtasks_json = os.path.join(submission_result_folder, "subtasks.json")
                    if os.path.exists(subtasks_json):
                        with open(subtasks_json, "r") as f:
                            subtasks = json.load(f)
                    else:
                        subtasks = None
                    solution = os.path.join(submission_result_folder, "solution.cpp")
                    with open(os.path.join(task_folder,"problem.json"), "r") as f:
                        problem_json = json.load(f)
                    task_obj = Task(
                        name=task,
                        statements=[os.path.join(task_folder, f"{task}.pdf"), os.path.join(task_folder, f"statement.md")],
                        tests=tests_folder,
                        subtasks=subtasks,
                        code_files=solution,
                        problem_json=problem_json
                    )
                    contest.add_task(task_obj, split=day)
            contest.write(self._restructure_path)
    def restructure(self):
        self.restructure_eval()
    def parse(self):
        pass
if __name__ == "__main__":
    crawl_path = f"{os.environ['HOME_DIR']}/IOI-Bench/RMI"
    restructure_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/RMI"
    parse_path = f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed/RMI"
    rmi_crawler = RMICrawler(crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path)
    rmi_crawler.restructure()