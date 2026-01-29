import os
from base_crawler import Crawler, Contest, Task
from converter import MarkerConverter
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar

class EGOICrawler(Crawler):
    def __init__(self, *, competition="EGOI", crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=converter)
        self.base_url = "https://stats.egoi.org/"
    def _get_full_url(self,link):
        """Convert a relative URL to a full URL."""
        if link.startswith("http"):
            return link
        return self.base_url + link
    def _extract_task(self, tasks_html):
        soup = BeautifulSoup(tasks_html, 'html.parser')
        table = soup.find('table')
        result = {}

        current_year = None
        current_day = None

        for row in table.find_all('tr'):
            tds = row.find_all('td')
            if not tds:
                continue

            # Determine columns based on number of <td> cells:
            # - 6 cells: year, day, task, max, avg, full
            # - 5 cells: day, task, max, avg, full (year carried over)
            # - 4 cells: task, max, avg, full (year and day carried over)
            if len(tds) == 6:
                current_year = tds[0].get_text(strip=True)
                current_day = tds[1].get_text(strip=True)
                task_td = tds[2]
                avg_score = tds[4].get_text(strip=True)
                full_score = tds[5].get_text(strip=True)
            elif len(tds) == 5:
                current_day = tds[0].get_text(strip=True)
                task_td = tds[1]
                avg_score = tds[3].get_text(strip=True)
                full_score = tds[4].get_text(strip=True)
            elif len(tds) == 4:
                task_td = tds[0]
                avg_score = tds[2].get_text(strip=True)
                full_score = tds[3].get_text(strip=True)
            else:
                continue

            # Process only tasks for day 1 and day 2
            if current_day not in ["1", "2"]:
                continue

            # Initialize the year entry if needed.
            if current_year not in result:
                result[current_year] = {"day1": {}, "day2": {}}

            day_key = "day" + current_day
            # Determine sequential task key (e.g., task1, task2, etc.)

            # Get URL from the <a> tag within the task cell.
            a_tag = task_td.find('a')
            url = a_tag['href'] if a_tag and a_tag.has_attr('href') else None
            task_key = url.split('/')[-2]
            result[current_year][day_key][task_key] = {
                "url": url,
                "avg score": avg_score,
                "full score": full_score
            }
        return result
    def _download_task(self, html, year, day, task):
        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        # Create the base directory: year/day/task
        base_dir = os.path.join(self._path, year, day, task)
        if os.path.exists(base_dir):
            print(f"Directory already exists: {base_dir}")
            return
        os.makedirs(base_dir, exist_ok=True)
        # Create translations directory
        translations_dir = os.path.join(base_dir, "translations")
        os.makedirs(translations_dir, exist_ok=True)
       # Collect download tasks as (url, destination_path) tuples
        download_tasks = []

        # --- Add description files tasks ---
        descriptions_div = soup.find("div", class_="descriptions")
        if descriptions_div:
            for a in descriptions_div.find_all("a"):
                href = a.get("href")
                if not href:
                    continue
                full_url = self._get_full_url(href)
                text = a.get_text(strip=True)
                # Expect text format: "Language (lang)"
                lang_match = re.search(r'\((\w+)\)', text)
                if not lang_match:
                    continue
                lang = lang_match.group(1).lower()
                if lang == "en" or lang == "en_en":
                    dest_file = os.path.join(base_dir, "task_en.pdf")
                else:
                    dest_file = os.path.join(translations_dir, f"task_{lang}.pdf")
                download_tasks.append((full_url, dest_file))
        else:
            print("No descriptions found.")

        # --- Add solution (editorial) task ---
        solution_url = None
        solution_links = soup.find_all("a", string=lambda x: x and "Solutions" in x)
        for a in solution_links:
            href = a.get("href")
            if href and "youtu" not in href.lower():
                solution_url = self._get_full_url(href)
                break
        if solution_url:
            dest_solution = os.path.join(base_dir, "editorial.pdf")
            download_tasks.append((solution_url, dest_solution))
        else:
            print("No non-YouTube solution link found.")

        # --- Add test data task ---
        testdata_a = soup.find("a", string=lambda x: x and "Testdata" in x)
        if testdata_a:
            testdata_href = testdata_a.get("href")
            if testdata_href:
                testdata_url = self._get_full_url(testdata_href)
                dest_testdata = os.path.join(base_dir, "testdata.zip")
                download_tasks.append((testdata_url, dest_testdata))
        else:
            print("No testdata link found.")
        # --- Download files concurrently using ThreadPoolExecutor ---
        max_workers = 10  # adjust based on your needs
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(download_file, url, dest) for url, dest in download_tasks]
            # Use tqdm to display a progress bar as downloads complete
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Downloading files"):
                # Optionally, check results or catch exceptions:
                future.result()
    def _unzip_testdata(self, year, day, task):
        base_dir = os.path.join(self._path, year, day, task)
        testdata_zip = os.path.join(base_dir, "testdata.zip")
        testdata_dir = os.path.join(base_dir, "testdata")
        if not os.path.exists(testdata_zip):
            print(f"Testdata ZIP file not found: {testdata_zip}")
            return
        if os.path.exists(testdata_dir):
            print(f"Testdata directory already exists: {testdata_dir}")
            return
        os.makedirs(testdata_dir, exist_ok=True)
        with zipfile.ZipFile(testdata_zip, 'r') as zip_ref:
            zip_ref.extractall(testdata_dir)
        print(f"Extracted testdata to: {testdata_dir}")
    def _extract_problem_info(self, markdown_text):
        """
        Extracts information from the markdown:
        - The first table containing the problem name, time limit, and memory limit.
        - The second table with group scores.
        
        Args:
            markdown_text (str): The markdown content containing the tables.
        
        Returns:
            dict: A dictionary with keys:
            - "problem_info": A dict with keys "problem_name", "time_limit", and "memory_limit".
            - "group_scores": A list of dictionaries, each with keys "group", "max_score", and "limits".
        """
        result = {
            "problem_info": {},
            "group_scores": []
        }
        
        # --- Extract problem information table ---
        prob_pattern = (
            r"\| Problem Name \|\s*(?P<problem_name>.*?)\s*\|\s*\n"  # Problem Name row
            r"\|[-]+\|[-]+\|\s*\n"                                   # Separator row
            r"\| Time Limit\s*\|\s*(?P<time_limit>.*?)\s*\|\s*\n"     # Time Limit row
            r"\| Memory Limit\s*\|\s*(?P<memory_limit>.*?)\s*\|"
        )
        
        prob_match = re.search(prob_pattern, markdown_text, re.MULTILINE)
        if prob_match:
            result["problem_info"] = {
                "task": prob_match.group("problem_name"),
                "time_limit": parse_time_to_seconds(prob_match.group("time_limit")),
                "memory_limit": parse_memory_to_mb(prob_match.group("memory_limit")),
                "task_type": identify_task_type(markdown_text.lower())
            }
        
        # --- Extract group scores table ---
        # Split the text into lines so we can scan for the group table.
        lines = markdown_text.splitlines()
        group_table_started = False
        header = []
        group_rows = {}
        
        for i, line in enumerate(lines):
            # Look for the header line of the group table.
            if line.strip().startswith("| Group ") and ("Max score" in line or "Score" in line):
                group_table_started = True
                header = [h.strip() for h in line.strip().split("|") if h.strip()]
                # Expect header to be something like: ['Group', 'Max score', 'Limits']
                # Skip the next line (separator) and continue.
                continue
            
            if group_table_started:
                # If the line is a separator, skip it.
                if set(line.strip()) <= {"|", "-", " "}:
                    continue
                # End the table if the line is empty or does not begin with '|'
                if not line.strip().startswith("|"):
                    break
                
                # Parse the row: splitting on '|' and stripping spaces.
                cols = [col.strip() for col in line.strip().split("|")]
                # The first and last items might be empty if the line starts and ends with '|'
                if cols and cols[0] == "":
                    cols = cols[1:]
                if cols and cols[-1] == "":
                    cols = cols[:-1]
                
                # If the number of columns matches the header, build a dictionary.
                if len(cols) >= 3:
                    row_dict = {
                        "group": cols[0],
                        "max_score": cols[1],
                        "limits": cols[2]
                    }
                    # If there are more columns, join the remaining as part of the "limits" field.
                    if len(cols) > 3:
                        row_dict["limits"] = " | ".join(cols[2:])
                    group_rows[cols[0]] = row_dict
        
        result["group_scores"] = group_rows
        return result
    def _find_last_group_folder(self, path):
        """
        Find the last group folder in the given path.
        """
        folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f))]
        if not folders:
            return None
        # Sort folders by name and return the last one
        folders.sort()
        return os.path.join(path, folders[-1])
    def _create_problem_info_json(self, converter_type):
        """
        Create a JSON file with problem information.
        """
        parse_path = self._parse_path
        for year in ["2024", "2023"]:
            year_path = os.path.join(parse_path, year)
            if not os.path.exists(year_path):
                continue
            for round_name in os.listdir(year_path):
                for task in os.listdir(os.path.join(year_path, round_name)):
                    task_path = os.path.join(year_path, round_name, task)
                    if not os.path.isdir(task_path):
                        continue
                    statement_path = os.path.join(task_path, "statements", f"statement_{converter_type}.md")
                    if not os.path.exists(statement_path):
                        print(f"Statement file not found: {statement_path}")
                        continue
                    with open(statement_path, "r", encoding="utf-8") as f:
                        markdown_text = f.read()
                    problem_info = self._extract_problem_info(markdown_text)
                    problem_info, group_scores = problem_info["problem_info"], problem_info["group_scores"]
                    if problem_info['task_type'] != "batch":
                        print(f"{task} is not a batch task")
                    restruture_task_path = os.path.join(self._restructure_path, year, round_name, task, "problem.json")
                    with open(restruture_task_path, "w", encoding="utf-8") as f:
                        json.dump(problem_info, f, indent=4)
                    restruture_subtask_path = os.path.join(self._restructure_path, year, round_name, task, "subtasks.json")
                    print(restruture_subtask_path)
                    with open(restruture_subtask_path, "r", encoding="utf-8") as f:
                        subtasks = json.load(f)
                    for group, subtask in subtasks.items():
                        if group in group_scores:
                            if "score" not in subtask or subtask["score"] == -1:
                                subtask["score"] = int(group_scores[group]["max_score"])
                    if "0" in subtasks and "score" not in subtasks["0"]:
                        subtasks["0"]["score"] = 0
                    with open(restruture_subtask_path, "w", encoding="utf-8") as f:
                        json.dump(subtasks, f, indent=4)
                    
    def crawl(self):
        baseurl = "https://stats.egoi.org/"
        tasks_url = "https://stats.egoi.org/tasks"
        tasks_html = fetch_url(tasks_url)
        tasks = self._extract_task(tasks_html)
        for year, days in tasks.items():
            for day, tasks in days.items():
                for task, task_info in tasks.items():
                    url = baseurl + task_info["url"]
                    html = fetch_url(url)
                    self._download_task(html, year, day, task)
                    self._unzip_testdata(year, day, task)
    def restructure(self):
        new_path = self._restructure_path
        os.makedirs(new_path, exist_ok=True)
        for year in ["2024", "2023"]:
            contest = Contest(year=year)
            for day in ["day1", "day2"]:
                year_path = os.path.join(self._path, year, day)
                if not os.path.exists(year_path):
                    continue
                for task in os.listdir(year_path):
                    task_path = os.path.join(year_path, task)
                    if not os.path.isdir(task_path):
                        continue
                    test_data = os.path.join(task_path, "testdata")
                    tests = os.path.join(task_path, "testdata", "data") if year == '2024' else test_data
                    test_folder = self._find_last_group_folder(tests + "/secret")
                    subtasks = create_subtask_json_kattis(tests)
                    
                    task = Task(
                        name=task,
                        statements=[os.path.join(task_path, "task_en.pdf"),os.path.join(test_data, "problem_statement", "problem.en.tex"),os.path.join(test_data, "problem_statement")],
                        translations=os.path.join(task_path, "translations"),
                        subtasks=subtasks,
                        graders = extract_grader_folder(os.path.join(task_path, "testdata")),
                        tests = test_folder, 
                        attachments=os.path.join(test_data, "attachments"),
                        editorial_files=os.path.join(task_path, "editorial.pdf"),
                        code_files=os.path.join(task_path, "testdata", "submissions", "accepted"),
                    )
                    contest.add_task(task, day)
            contest.write(new_path)
    def parse(self):
        self._preprocess_parse(self._restructure_path, parse_statement=True, parse_solution=True, rerun=False)
        self._create_problem_info_json(converter_type="marker")
                
if __name__ == "__main__":
    converter = converter = MarkerConverter(source_format="pdf", target_format="markdown", use_LLM=True)
    crawler = EGOICrawler(crawl_path = f"{os.environ['HOME_DIR']}/IOI-Bench/EGOI", competition="EGOI", restructure_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/EGOI", parse_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed/EGOI", converter=converter)
    crawler.restructure()
    crawler.parse()