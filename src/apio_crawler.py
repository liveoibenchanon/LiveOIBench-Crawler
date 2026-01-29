import os
from base_crawler import Crawler, Contest, Task
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
from converter import MarkerConverter
class APIOCrawler(Crawler):
    def __init__(self, *, competition="APIO", path, converter=None):
        super().__init__(competition=competition, path=path, converter=converter)
        self.base_url = "https://olympiads.jsoft.am/"
        self.website_url = {
            "2021": "https://apio2021.toki.id/",
            "2020": "https://apio2020.toki.id/tasks.html"
        }
        self.git_urls = {
            "2024": "https://github.com/APIO-2024/apio2024_tasks.git",
            "2023": "https://github.com/apio2023/apio2023_tasks.git",
            "2022": "https://github.com/apio2022/apio2022_tasks.git",
            "2021": "https://github.com/ia-toki/apio-2021.git",
            "2015": "https://github.com/ia-toki/apio-2015",
            "2016": "https://github.com/apio-2016/apio2016-tasks.git",
        }
        self.cses_contest = {
            "2018": 246,
            "2012": 242,
            "2014": 243,
            "2015": 244,
            "2016": 245,
            "2007": 237
        }
    def _clone_repo(self):
        for year, url in self.git_urls.items():
            os.makedirs(f"{self._path}/{year}", exist_ok=True)
            clone_repo(url, f"{self._path}/{year}")
    def _extract_subtasks(self, config_file):
        """
        Parse the configuration string and extract subtasks information.

        The expected output format is:
        {
            "task": "",
            "time_limit": <int>,
            "memory_limit": <int>,
            "1": {"name": "", "score": <int>, "tests": [<test_name>, ...]},
            "2": {...},
            ...
        }
        
        Test names are constructed using the configuration parameters:
            input_pre, input_suf, output_pre, output_suf
        Each test name is a string formatted as:
            "<input_pre><test_number><input_suf> / <output_pre><test_number><output_suf>"
        """
        with open(config_file, "r") as f:
            config_str = f.read()
        conf = {}
        # Build a dictionary of keys and values from the config file.
        for line in config_str.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            key = parts[0]
            value = " ".join(parts[1:])
            conf[key] = value

        # Extract basic parameters.
        time_limit = int(conf.get("time_limit", "0"))
        memory_limit = int(conf.get("memory_limit", "0"))
        n_tests = int(conf.get("n_tests", "0"))
        n_subtasks = int(conf.get("n_subtasks", "0"))
        
        # Extract test naming parameters (default to empty strings if not present)
        input_pre = conf.get("input_pre", "")
        input_suf = conf.get("input_suf", "")
        output_pre = conf.get("output_pre", "")
        output_suf = conf.get("output_suf", "")

        result = {
            "task": "",
            "time_limit": time_limit,
            "memory_limit": memory_limit
        }

        previous_end = 0
        # Process each subtask.
        for i in range(1, n_subtasks + 1):
            score_key = f"subtask_score_{i}"
            end_key = f"subtask_end_{i}"
            score = int(conf.get(score_key, "0"))
            end = int(conf.get(end_key, "0"))
            
            # Generate test names for this subtask.
            tests = []
            for j in range(previous_end + 1, end + 1):
                # Construct the test name using the prefixes and suffixes.
                test_name = f"{input_pre}{j}"
                tests.append(test_name)
            
            previous_end = end
            
            # Save subtask info (name left empty if not specified)
            result[str(i)] = {
                "name": "Subtask " + str(i),
                "score": score,
                "testcases": tests
            }
        return result
    
    def _parse_table_from_file(self,file_path):
        """
        Reads a file containing a markdown table (possibly with extra text) and returns the parsed table
        as a list of dictionaries with keys: 'task', 'name', 'time_limit', 'memory_limit'.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract lines that look like table rows (start with '|')
        table_lines = [line for line in content.splitlines() if line.strip().startswith('|')]
        
        # Join the table lines into a single string
        table_str = "\n".join(table_lines)
        
        # Split the table string into lines
        lines = table_str.strip().split('\n')
        if len(lines) < 3:
            return []  # Not enough lines for header, divider, and data

        # Skip the header and divider lines
        data_lines = lines[2:]
        
        tasks = {}
        for line in data_lines:
            # Skip empty lines
            if not line.strip():
                continue
            # Split the line by '|' and remove extra whitespace from each cell
            columns = [col.strip() for col in line.strip('|').split('|')]
            if len(columns) >= 4:
                memory_limit = float(columns[3].split()[0])
                if "GiB" in columns[3]:
                    memory_limit *= 1024
                task_info = {
                    'task': columns[0],
                    'name': columns[1],
                    'time_limit': float(columns[2].split()[0]),
                    'memory_limit': memory_limit
                }
                tasks[task_info['task']] = task_info
        return tasks

    def crawl(self):
        self._clone_repo()
    def restructure(self, new_path):
        years = ['2024', '2023']
        os.makedirs(new_path, exist_ok=True)
        # Parse each year directory
        for year in years:
            print("Parsing year:", year)
            contest = Contest(year=year)
            year_path = os.path.join(self._path, year)
            tasks = self._parse_table_from_file(year_path + "/README.md")
            dirs = os.listdir(year_path)
            for dir_name in dirs:
                dir_path = os.path.join(year_path, dir_name)
                if os.path.isdir(dir_path) and not dir_name.startswith(".") and not dir_name.startswith("statements"):
                    print("Parsing task:", dir_name)
                    editorial_files = extract_editorial_files(dir_path)
                    subtask_path = os.path.join(dir_path, "subtasks")
                    if not os.path.exists(subtask_path):
                        print(os.path.join(dir_path, "tests", "problem.conf"))
                        subtasks = self._extract_subtasks(os.path.join(dir_path, "tests", "problem.conf"))
                    else:
                        subtasks = create_subtask_json_by_folder(subtask_path)
                    if not os.path.exists(os.path.join(dir_path, "problem.json")):
                        problem_json = {
                            "task": dir_name,
                            "time_limit": tasks[dir_name]["time_limit"],
                            "memory_limit": tasks[dir_name]["memory_limit"],
                            "task_type": ""
                        }
                    else:
                        with open(os.path.join(dir_path, "problem.json"), "r") as f:
                            problem_json = json.load(f)
                        problem_json["memory_limit"] /= 1024 * 1024
                    #remove task, time_limit, memory_limit from subtasks
                    subtasks.pop("task", None)
                    subtasks.pop("time_limit", None)
                    subtasks.pop("memory_limit", None)
                    missing_tests, is_valid, subtasks = check_subtask_tests(subtasks, os.path.join(dir_path, "tests"), delete_missing=True)
                    print(missing_tests, "missing tests")
                    task = Task(
                        name = dir_name,
                        statements=os.path.join(year_path, "statements", dir_name, "ISC.pdf"),
                        translations=os.path.join(year_path,dir_name, "statements"),
                        graders=os.path.join(dir_path, "graders"),
                        subtasks=subtasks,
                        tests=os.path.join(dir_path, "tests"),
                        attachments=[os.path.join(dir_path, "attachments", "cpp"),os.path.join(dir_path, "attachments", "samples")],
                        editorial_files = editorial_files,
                        code_files=os.path.join(dir_path, "solutions"),
                        problem_json=problem_json
                    )
                    contest.add_task(task)
            contest.write(new_path)
    def parse(self, parse_path):
        self._preprocess_parse(parse_path, parse_statement=True, parse_solution=True, rerun=False)
if __name__ == "__main__":
    converter = MarkerConverter(source_format="pdf", target_format="markdown", use_LLM=True)
    apio_crawler = APIOCrawler(path=f"{os.environ['HOME_DIR']}/IOI-Bench/APIO", competition="APIO", converter=converter)
    #apio_crawler.crawl()
    apio_crawler.restructure(f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed/APIO")  # Uncomment if parse logic is implemented
    #apio_crawler.parse("$HOME_DIR/IOI-Bench-Parsed/APIO")  # Uncomment if parse logic is implemented