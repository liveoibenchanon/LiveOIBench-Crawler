from base_crawler import Crawler, Contest, Task
from utils import *
import requests
import os
import shutil
import csv
from bs4 import BeautifulSoup
from urllib.request import urlopen

class JOICrawler(Crawler):
    def __init__(self, *, competition, crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=None)
        self.base_url = "https://contests.ioi-jp.org/"

    def fix_encoding(self, text):
        # return text.encode('latin1').decode('utf-8')
        b = text.encode('latin1', errors='ignore')       # drop any un‐mappable codepoints
        return b.decode('utf-8', errors='ignore')       # skip any invalid UTF-8
    
    def parse_ranking_online(self, url):
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch page: {response.status_code}")
            exit()

        # Step 2: Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Find the table
        table = soup.find("table", class_="table-bordered")

        # Get headers
        headers = [th.get_text(strip=True) for th in table.find_all("th")]

        # Extract rows
        rows = []
        for tr in table.find_all("tr")[1:]:  # Skip header row
            cells = tr.find_all(["td", "th"])
            row = [cell.get_text(strip=True) for cell in cells]
            rows.append(row)

        # Convert to list of dicts
        ranking_data = [dict(zip(headers, row)) for row in rows]

        # Print result
        return ranking_data
    
    def parse_ranking_contestants(self, url):
        response = requests.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch page: {response.status_code}")
            exit()

        # Step 2: Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Step 3: Locate the score distribution table
        # It’s the only table with "合計点得点分布" somewhere near it, so we find by caption or summary
        score_table = None
        for table in soup.find_all("table"):
            if "合計点得点分布" in self.fix_encoding(table.get_text()):
                score_table = table
                break

        if not score_table:
            print("Could not find the 合計点得点分布 table.")
            exit()

        headers = [self.fix_encoding(th.get_text(strip=True)) for th in score_table.find_all("th")]

        # Translate Japanese headers into English
        headers_translation = {
            "得点": "Score",
            "人数": "Number of Contestants",
            "累計": "Cumulative Count"
        }

        headers = [headers_translation.get(header, header) for header in headers]

        # Step 5: Extract rows
        rows = []
        for tr in score_table.find_all("tr")[1:]:  # Skip header
            cells = tr.find_all(["td", "th"])
            row = [cell.get_text(strip=True).replace("\u00e7\u0082\u00b9", "").replace("\u00ef\u00bd\u009e", "-") for cell in cells]
            rows.append(row)

        # Step 6: Structure data as list of dictionaries
        score_distribution = [dict(zip(headers, row)) for row in rows]

        return score_distribution
    
    
    def list_test_cases(self, directory):
        print(directory)
        tmp =  [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        test_cases_list = list(set([x.replace(".in", "").replace(".out", "") for x in tmp]))
        test_cases_list_sample = []
        test_cases_list_no_sample = []
        for x in test_cases_list:
            if "sample" in x:
                test_cases_list_sample.append(x)
            else:
                test_cases_list_no_sample.append(x)
        test_cases_list = test_cases_list_no_sample
        # print(test_cases_list)
        test_cases_list.sort(key=lambda x: (int(x.split('-')[0]), int(x.split('-')[1])))
        test_cases_list_sample.sort(key=lambda x: int(x.split('-')[1]))
        return test_cases_list+test_cases_list_sample
    
    def expand_testcases(self, subtask_patterns, test_case_pool):
        expanded = set()
        for pattern in subtask_patterns:
            pattern_clean = pattern.strip('"')
            matches = fnmatch.filter(test_case_pool, pattern_clean)
            expanded.update(matches)
        return sorted(expanded)
    
    def convert_to_subtasks_json(self, input_file):
        # Read the plain text file
        with open(input_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        tasks = []
        current_task = {}
        task_id = -1
        subtask_id = 0
        time_limit = None
        memory_limit = None

        for line in lines:
            line = line.strip()
            # replace single quote with double quote, if needed
            line = line.replace("'", "\"")
            
            # Skip empty lines or lines with only '%' (which marks the end of a task)
            if not line or '%' in line:
                continue

            # New task detection (based on "2023-sp" format)
            if line[:2] == '20' and line[4:7] == '-sp':
                if current_task:
                    tasks.append(current_task)  # Save the previous task
                
                task_id += 1  # Increment task id
                task_name = line

                current_task = {
                    'task_name': task_name.strip(),
                    'subtasks': [],
                    'time_limit': time_limit,
                    'memory_limit': memory_limit
                }
                subtask_id = 0  # Reset subtask id for the new task
                time_limit = None  # Reset time_limit for the new task
                memory_limit = None  # Reset memory_limit for the new task
                continue

            # Extract time_limit and memory_limit from the lines
            if line.startswith('time_limit'):
                time_limit = float(line.split(':')[1].strip())
                current_task["time_limit"] = time_limit
            elif line.startswith('memory_limit'):
                memory_limit = int(line.split(':')[1].strip())
                current_task["memory_limit"] = memory_limit

            # Match the subtasks and their corresponding testcases
            # match = re.match(r'Subtask (\d+)\s*\((\d+)\):\s*(.*)', line)
            pattern = re.compile(r'Subtask (\d+)\s*\((\d+)\):\s*(.*)', re.DOTALL)
            match = pattern.match(line)
            # if current_task['task_name'].startswith("2023-ho-t3"):
            #     import pdb; pdb.set_trace()
            if match:
                subtask_id = int(match.group(1))
                score = int(match.group(2))
                testcases = match.group(3).strip().split(",")
                testcases = [tc.replace("\"","").strip() for tc in testcases]  # Clean up the test case names
                task_name = f"Subtask {subtask_id}"

                # Add the subtask to the current task's subtasks list
                current_task['subtasks'].append({
                    "score": score,
                    "testcases": testcases,
                    "task": task_name
                })

        # Append the last task
        if current_task:
            tasks.append(current_task)

        # Convert to JSON format
        # json_output = json.dumps(tasks, ensure_ascii=False, indent=4)
        return tasks
    
    def rename_and_copy_files(self, input_dir, output_dir, keyword):
        # Create output directory if it doesn't exist

        # Process and copy files
        for filename in os.listdir(input_dir):
            if filename.endswith(".txt"):
                base, ext = os.path.splitext(filename)
                parts = base.split("-")
                if len(parts) == 2:
                    new_filename = f"{base}.{keyword}"
                    src = os.path.join(input_dir, filename)
                    dst = os.path.join(output_dir, new_filename)
                    shutil.copyfile(src, dst)
                    print(f"Copied and renamed: {filename} → {new_filename}")
                else:
                    print(f"Skipped (invalid format): {filename}")
    
    def json_to_csv(self, json_path, csv_path):
        # Load JSON data
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Validate that data is a list of dictionaries
        if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
            print("Error: JSON file must contain a list of objects (dictionaries).", file=sys.stderr)
            sys.exit(1)

        # Determine CSV columns (union of all keys)
        fieldnames = set()
        for item in data:
            fieldnames.update(item.keys())
        fieldnames = sorted(fieldnames)

        # Write CSV
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in data:
                writer.writerow(row)


    def crawl(self, start_year, end_year):
        """
        Crawl the data from the competition website.Includes downloading the data, extracting the data, unzipping the data, etc.
        """
        baseurl = "https://contests.ioi-jp.org/joi-sp-<YEAR>/index-en.html"
        taskurl = "https://www2.ioi-jp.org/camp/<YEAR>/<YEAR>-sp-tasks/index.html"
        htmls = {}
        urls = {}
        for year in range(start_year, end_year+1):
            url_baseurl = baseurl.replace("<YEAR>", str(year))
            html_base = fetch_url(url_baseurl)
            url_taskurl = taskurl.replace("<YEAR>", str(year))
            html_task = fetch_url(url_taskurl)
            htmls[year] = (html_base, html_task)
            urls[year] = (url_baseurl, url_taskurl)

        packed_paths = {}
        for year in range(start_year, end_year+1):
            packed_paths[year] = {"results": [], "tasks": {}}

            url_baseurl, url_taskurl = urls[year]

            # Fetch the HTML content
            try:
                with urlopen(url_taskurl) as response:
                    html = response.read().decode('utf-8')
            except Exception as e:
                print(f"Error fetching {url_taskurl}: {e}", file=sys.stderr)
                sys.exit(1)

            soup = BeautifulSoup(html, 'html.parser')
            url_baseurl = url_baseurl.replace("index-en.html", "")
            url_taskurl = url_taskurl.replace("index.html", "")

            day_div = "contest" if year >= 2022 else "day"


            statement_pattern = re.compile(rf'^\.\/{day_div}[1-4]\/[^"]+-en\.pdf$')
            statements = [a['href'].replace("./", url_taskurl) for a in soup.find_all('a', href=statement_pattern)]

            editorial_pattern = re.compile(rf'^\.\/{day_div}[1-4]\/[^"]+-en\.pdf$')
            editorials = [a['href'].replace("./", url_taskurl) for a in soup.find_all('a', href=editorial_pattern)]

            solution_code_pattern = re.compile(rf'^\.\/{day_div}[1-4]\/[^"]+\.cpp$')
            solutions_code = [a['href'].replace("./", url_taskurl) for a in soup.find_all('a', href=solution_code_pattern)]

            task_list = [x.split("/")[-1].replace("-en.pdf", "") for x in statements]

            problem_meta = f"{url_taskurl}{year}-sp-score.txt"

            # for statement in statements:
            #     response = requests.get(statement)
            #     if not os.path.exists(f"{self._path}/{year}"):
            #         os.makedirs(f"{self._path}/{year}")

            #     if response.status_code == 200:
            #         with open(f"{self._path}/{year}/{statement.split('/')[-1]}", 'wb') as f:
            #             f.write(response.content)
            #     else:
            #         print(f"Failed to download {statement}")
                

            # for editorial in editorials:
            #     response = requests.get(editorial)
            #     if response.status_code == 200:
            #         with open(f"{self._path}/{year}/{editorial.split('/')[-1]}", 'wb') as f:
            #             f.write(response.content)
            #     else:
            #         print(f"Failed to download {editorial}")
            
            solution_code_files = []
            for i, solution_code_file in enumerate(solutions_code):
                response = requests.get(solution_code_file)
                if response.status_code == 200:
                    with open(f"{self._path}/{year}/{solution_code_file.split('/')[-1]}", 'wb') as f:
                        f.write(response.content)
                    solution_code_files.append(f"{self._path}/{year}/{solution_code_file.split('/')[-1]}")
                else:
                    print(f"Failed to download {solution_code_file}")
            

            #### Use wget instead
            # response = requests.get(problem_data)
            # if response.status_code == 200:
            #     with open(f"{self._path}/{year}/{problem_data.split('/')[-1]}", 'wb') as f:
            #         f.write(response.content)
            #     print("Download completed successfully.")
            # else:
            #     print(f"Failed to download file. Status code: {response.status_code}")


            # create directory for ranking
            os.makedirs(f"{self._path}/{year}/ranking", exist_ok=True)
            
            ranking_data_online = self.parse_ranking_online(url_baseurl + "ranking.html")
            with open(f"{self._path}/{year}/ranking/ranking_online_contestants.json", 'w') as f:
                json.dump(ranking_data_online, f, indent=4)


            ranking_data_onsite = self.parse_ranking_contestants(url_taskurl + "index.html")
            with open(f"{self._path}/{year}/ranking/ranking_onsite_contestants.json", 'w') as f:
                json.dump(ranking_data_onsite, f, indent=4)
            
            
            subtasks_raw = self.convert_to_subtasks_json(f"{self._path}/{year}/{problem_meta.split('/')[-1]}")

            self.json_to_csv(f"{self._path}/{year}/ranking/ranking_online_contestants.json", f"{self._path}/{year}/ranking/ranking_online_contestants.csv")
            self.json_to_csv(f"{self._path}/{year}/ranking/ranking_onsite_contestants.json", f"{self._path}/{year}/ranking/ranking_onsite_contestants.csv")
            packed_paths[year]["results"] = [
                f"{self._path}/{year}/ranking/ranking_online_contestants.json",
                f"{self._path}/{year}/ranking/ranking_onsite_contestants.json",
                f"{self._path}/{year}/ranking/ranking_online_contestants.csv",
                f"{self._path}/{year}/ranking/ranking_onsite_contestants.csv"
            ]


            for i, task_id in enumerate(task_list):
                subtask_raw = subtasks_raw[i]
                task_name = "_".join(subtask_raw["task_name"].split(" "))
                task_type = "Batch"

                test_data_path = f"{self._path}/{year}/tests_{year}/{task_id}-data"

                

                for ext in ["in", "out"]:
                    input_dir = os.path.join(test_data_path, ext)
                    if year in [2018, 2019]:
                        input_dir = os.path.join(test_data_path+"/"+task_id, ext) 
                    if not os.path.exists(input_dir):
                        print(f"Directory {input_dir} does not exist.")
                        task_type = "Interactive"
                        if subtask_raw["time_limit"] == 1000.0:
                            task_type = "Output"
                        continue
                    output_dir = os.path.join(test_data_path, "processed")
                    os.makedirs(output_dir, exist_ok=True)
                    self.rename_and_copy_files(input_dir, output_dir, ext)

                problem = {
                    "task":subtask_raw["task_name"],
                    "time_limit": subtask_raw["time_limit"],
                    "memory_limit": subtask_raw['memory_limit'], 
                    "task_type": task_type 
                }
                with open(f"{self._path}/{year}/problem_{task_id}.json", 'w') as f:
                    json.dump(problem, f, indent=4)


                test_cases_list = self.list_test_cases(output_dir)
                subtasks_to_expand = subtask_raw["subtasks"]

                subtask = {}
                for item in subtasks_to_expand:
                    expanded_testcases = self.expand_testcases(item['testcases'], test_cases_list)
                    item['testcases'] = expanded_testcases
                    subtask_id = item['task'].split(" ")[-1]
                    subtask[subtask_id] = item
                
                with open(f"{self._path}/{year}/subtasks_{task_id}.json", 'w') as f:
                    json.dump(subtask, f, indent=4)

                packed_paths[year]["tasks"][task_name] = {
                    "statements": f"{self._path}/{year}/{statements[i].split('/')[-1]}" ,
                    "editorials": f"{self._path}/{year}/{editorials[i].split('/')[-1]}",
                    "solutions_code": [x for x in solution_code_files if task_id in x],
                    "test_cases" : f"{self._path}/{year}/tests_{year}/{task_id}-data/processed",
                    "problem_meta": f"{self._path}/{year}/problem_{task_id}.json",
                    "subtasks": f"{self._path}/{year}/subtasks_{task_id}.json"
                }


        return urls, htmls, packed_paths
    


    def restructure(self, packed_paths, start_year, end_year):
        """
        Restructure the crawled data into a more manageable format. This may include organizing files, renaming them, etc.
        """
        new_path = self._restructure_path
        for year in range(start_year, end_year+1):
            contest = Contest(
                name="JOI_spring", 
                year=year,
                result_file=packed_paths[year]["results"]
                )
            for task_name in packed_paths[year]["tasks"]:
                task = packed_paths[year]["tasks"][task_name]
                statements = task["statements"]
                editorial_file = task["editorials"]
                code_files = task["solutions_code"]
                tests = task["test_cases"]
                problem_json = task["problem_meta"]
                subtasks = task["subtasks"]

                with open(problem_json, 'r') as f:
                    problem_json_content = json.load(f)

                with open(subtasks, 'r') as f:
                    subtasks_content = json.load(f)
            
                task_obj = Task(
                    name=task_name,
                    statements=statements,
                    tests=tests,
                    editorial_files=editorial_file,
                    code_files=code_files,
                    subtasks=subtasks_content,
                    problem_json=problem_json_content
                )
                contest.add_task(task_obj)
        
            contest.write(new_path)

            

    def parse(self, parse_path):
        """
        Parse the crawled data. The data may be in different formats like HTML, PDF, etc.
        """
        pass


if __name__ == "__main__":
    crawler = JOICrawler(competition="JOI", crawl_path=f"{os.environ['HOME_DIR']}/coding_benchmark_data/JOI_spring_raw", restructure_path=f"{os.environ['HOME_DIR']}/coding_benchmark_data/JOI", parse_path=None, converter=None)
    urls, htmls, packed_paths = crawler.crawl(2018, 2021)
    crawler.restructure(packed_paths, 2018, 2021)    