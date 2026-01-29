from base_crawler import Crawler, Contest, Task
from utils import *
import requests
import os
import shutil
import csv
from bs4 import BeautifulSoup

class JOICrawler(Crawler):
    def __init__(self, *, competition, crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=None)
        self.base_url = "https://contests.ioi-jp.org/"

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
        # remove ".txt"
        subtask_patterns = [pattern.replace(".txt", "").strip() for pattern in subtask_patterns]

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

            # New task detection (based on "2024-ho-t" format)
            if line[4:11] == '-open-t':
                if current_task:
                    tasks.append(current_task)  # Save the previous task
                
                task_id += 1  # Increment task id

                # Initialize the current task with the time and memory limits
                current_task = {
                    'task_name': line.strip(),
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
    
    def extract_links(self, html_file, section_id):
        """
        Find the element with the given id, then extract all hrefs
        from the first <ul> that follows it.
        """
        soup = BeautifulSoup(html_file, 'html.parser')

        section = soup.find(id=section_id)
        if not section:
            return []
        ul = section.find_next_sibling('ul')
        if not ul:
            return []
        return [a['href'] for a in ul.find_all('a', href=True)]


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
        baseurl = "https://contests.ioi-jp.org/open-<YEAR>/index.html"
        htmls = {}
        urls = {}
        for year in range(start_year, end_year+1):
            url_baseurl = baseurl.replace("<YEAR>", str(year))
            html_base = fetch_url(url_baseurl)
            htmls[year] = html_base
            urls[year] = url_baseurl

        packed_paths = {}
        for year in range(start_year, end_year+1):
            packed_paths[year] = {"results": [], "tasks": {}}

            url_baseurl = urls[year]
            html_base = htmls[year]


            task_names = []
            soup = BeautifulSoup(html_base, 'html.parser')
            statements_section = soup.find(id='statements')
            if statements_section:
                ul = statements_section.find_next_sibling('ul')
                if ul:
                    for li in ul.find_all('li', recursive=False):
                        # The task name is the first text node in the <li>
                        if li.contents and isinstance(li.contents[0], str):
                            name = li.contents[0].strip()
                            task_names.append(name)
            task_names_converter = {}
            for i, task_name in enumerate(task_names):
                task_names_converter[task_name] = f"t{i+1}"

            task_list = [task_names_converter[x] for x in task_names]

            statements = [x for x in self.extract_links(html_base, 'statements') if "en.pdf" in x]
            translations = [x for x in self.extract_links(html_base, 'statements') if "en.pdf" not in x]
            editorials = [x for x in self.extract_links(html_base, 'reviews')  if "en.pdf" in x]
            solutions_code = self.extract_links(html_base, 'sample-sources')


            # problem_data = f"{url_taskurl}{year}-ho-data.zip"


            for statement in statements:
                response = requests.get(statement)

                if not os.path.exists(f"{self._path}/{year}"):
                    os.makedirs(f"{self._path}/{year}")

                for x in task_names:
                    if x in statement:
                        task_name = task_names_converter[x]
                        break

                if response.status_code == 200:
                    with open(f"{self._path}/{year}/{year}-open-{task_name}-en.pdf", 'wb') as f:
                        f.write(response.content)
                else:
                    print(f"Failed to download {statement}")
                

            for translation in translations:
                response = requests.get(translation)

                for x in task_names:
                    if x in translation:
                        task_name = task_names_converter[x]
                        break

                if response.status_code == 200:
                    with open(f"{self._path}/{year}/{year}-open-{task_name}.pdf", 'wb') as f:
                        f.write(response.content)
                else:
                    print(f"Failed to download {translation}")
            

            for editorial in editorials:
                response = requests.get(editorial)

                for x in task_names:
                    if x in editorial:
                        task_name = task_names_converter[x]
                        break

                if response.status_code == 200:
                    with open(f"{self._path}/{year}/{year}-open-{task_name}-review.pdf", 'wb') as f:
                        f.write(response.content)
                else:
                    print(f"Failed to download {editorial}")
            
            solution_code_files = []
            for i, solution_code in enumerate(solutions_code):
                for x in task_names:
                    if x in solution_code:
                        task_name = task_names_converter[x]
                        solution_code_file = solution_code.replace(x, task_name)
                        break
                assert task_name in solution_code_file
                

                response = requests.get(solution_code)
                if response.status_code == 200:
                    with open(f"{self._path}/{year}/{solution_code_file.split('/')[-1]}", 'wb') as f:
                        f.write(response.content)
                        solution_code_files.append(f"{self._path}/{year}/{solution_code_file.split('/')[-1]}")
                else:
                    print(f"Failed to download {solution_code}")
                  

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
            
            
            ranking_data_online = self.parse_ranking_online(url_baseurl.replace("index","ranking"))
            with open(f"{self._path}/{year}/ranking/ranking_online_contestants.json", 'w') as f:
                json.dump(ranking_data_online, f, indent=4)

            

            subtasks_raw = self.convert_to_subtasks_json(f"{self._path}/{year}/{year}-open-score.txt")
            
            self.json_to_csv(f"{self._path}/{year}/ranking/ranking_online_contestants.json", f"{self._path}/{year}/ranking/ranking_online_contestants.csv")
            packed_paths[year]["results"] = [
                f"{self._path}/{year}/ranking/ranking_online_contestants.json",
                f"{self._path}/{year}/ranking/ranking_online_contestants.csv",
            ]


            for i, task_id in enumerate(task_list):
                subtask_raw = subtasks_raw[i]
                task_name = subtask_raw["task_name"]
                task_type = "Batch"

                # processing test data 
                test_data_path = f"{self._path}/{year}/tests_{year}/{task_names[i]}"
                for ext in ["in", "out"]:
                    input_dir = os.path.join(test_data_path, ext)
                    if not os.path.exists(input_dir):
                        print(f"Directory {input_dir} does not exist.")
                        task_type = "Interactive"
                        continue
                    output_dir = os.path.join(test_data_path, "processed")
                    os.makedirs(output_dir, exist_ok=True)
                    self.rename_and_copy_files(input_dir, output_dir, ext)

                # process problem_ti files
                problem = {
                    "task":subtask_raw["task_name"],
                    "time_limit": subtask_raw["time_limit"],
                    "memory_limit": subtask_raw['memory_limit'], 
                    "task_type": task_type
                }
                with open(f"{self._path}/{year}/problem_{task_id}.json", 'w') as f:
                    json.dump(problem, f, indent=4)

                # process subtasks_ti files
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

                # import pdb; pdb.set_trace()
                # dump paths
                packed_paths[year]["tasks"][task_name] = {
                    "statements": f"{self._path}/{year}/{year}-open-{task_id}-en.pdf" ,
                    "translations": f"{self._path}/{year}/{year}-open-{task_id}.pdf",
                    "editorials": f"{self._path}/{year}/{year}-open-{task_id}-review.pdf",
                    "solutions_code": [x for x in solution_code_files if task_id in x],
                    "test_cases" : f"{self._path}/{year}/tests_{year}/{task_names[i]}/processed",
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
                name="JOI_open", 
                year=year,
                result_file=packed_paths[year]["results"]
                )
            for task_name in packed_paths[year]["tasks"]:
                task = packed_paths[year]["tasks"][task_name]
                statements = task["statements"]
                translations = task["translations"]
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
                    translations=translations,
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
    crawler = JOICrawler(competition="JOI", crawl_path=f"{os.environ['HOME_DIR']}/coding_benchmark_data/JOI_open_raw", restructure_path=f"{os.environ['HOME_DIR']}/coding_benchmark_data/JOI", parse_path=None, converter=None)
    urls, htmls, packed_paths = crawler.crawl(2021, 2024)
    crawler.restructure(packed_paths, 2021, 2024)    