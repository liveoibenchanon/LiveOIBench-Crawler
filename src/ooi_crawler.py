import os
from base_crawler import Crawler, Contest, Task
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

class OOICrawler(Crawler):
    def __init__(self, *, competition="OOI", crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=converter)
        self.base_url = "https://inf-open.ru/"
        self.old_base_url = "https://olympiads.ru/zaoch/"
    def process_materials(self, html_str, year, round_name, split_by_day=True):
        """
        Process an HTML file with competition materials.
        
        Expects three sections:
        - A section with h4 id="условия-задача" containing statement PDFs.
        - A section with h4 id="разбор-задач" containing editorial PDFs.
        - A section with h4 id="архивы" containing problem ZIPs.
        
        If split_by_day is True, for each statement link the code looks for "первый" or "Day 1" 
        versus "второй" or "Day 2" to determine day folders.
        
        For problem ZIPs, filenames are expected to contain "day1-" or "day2-" and a problem letter.
        Downloads are saved to:
        {year}/{day}/{problem_letter}/{problem_letter}.zip  (then unzipped)
        """
        soup = BeautifulSoup(html_str, "html.parser")
        base_url = self.base_url
        year_dir = os.path.join(self._path, year, round_name)
        os.makedirs(year_dir, exist_ok=True)
        
        # --- Process Statements ---
        statements_id = "statements" if round_name == "qualification" else "problem-statements"
        h4_statements = soup.find("h4", id=statements_id)
        if h4_statements:
            ul_statements = h4_statements.find_next_sibling("ul")
            if ul_statements:
                for li in ul_statements.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    href = a.get("href")
                    if href.startswith("/"):
                        href = urljoin(base_url, href)
                    text = a.get_text(strip=True).lower()
                    # Determine day from text
                    if "первый" in text or "day 1" in text:
                        day = "day1" if split_by_day else ""
                    elif "второй" in text or "day 2" in text:
                        day = "day2" if split_by_day else ""
                    else:
                        day = ""
                    # Determine language from URL or link text
                    if "-ru.pdf" in href or "рус" in text:
                        lang = "ru"
                    elif "-en.pdf" in href or "english" in text:
                        lang = "en"
                    elif "-fa.pdf" in href or "persian" in text:
                        lang = "fa"
                    else:
                        lang = "unknown"
                    # Destination folder: if day is set and splitting by day, use {year}/{day}, else {year}
                    dest_folder = os.path.join(year_dir, day) if day else year_dir
                    os.makedirs(dest_folder, exist_ok=True)
                    if day:
                        dest_filename = f"statements_{day}_{lang}.pdf"
                    else:
                        dest_filename = f"statements_{lang}.pdf"
                    dest_path = os.path.join(dest_folder, dest_filename)
                    download_file(href, dest_path)
            else:
                print("No <ul> found after statements header.")
        else:
            print("No statements section found.")

        # --- Process Editorial (Разбор задания) ---
        h4_editorial = soup.find("h4", id="editorial")
        if h4_editorial:
            ul_editorial = h4_editorial.find_next_sibling("ul")
            if ul_editorial:
                for li in ul_editorial.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    href = a.get("href")
                    if href.startswith("/"):
                        href = urljoin(base_url, href)
                    text = a.get_text(strip=True).lower()
                    if "-ru.pdf" in href or "рус" in text:
                        lang = "ru"
                    elif "-en.pdf" in href or "english" in text:
                        lang = "en"
                    else:
                        lang = "unknown"
                    if href.endswith(".pdf"):
                        dest_filename = f"editorial_{lang}.pdf"
                    else:
                        dest_filename = href.split("/")[-1]
                    dest_path = os.path.join(year_dir, dest_filename)
                    download_file(href, dest_path)
            else:
                print("No <ul> found after editorial header.")
        else:
            print("No editorial section found.")

        # --- Process Problems (Архивы) ---
        target_str = "archives-with-problem-materials" if round_name == "qualification" else "archive"
        h4_problems = soup.find("h4", id=target_str)
        if h4_problems:
            ul_problems = h4_problems.find_next_sibling("ul")
            if ul_problems:
                for li in ul_problems.find_all("li"):
                    a = li.find("a")
                    if not a:
                        continue
                    href = a.get("href")
                    if href.startswith("/"):
                        href = urljoin(base_url, href)
                    parsed = urlparse(href)
                    filename = os.path.basename(parsed.path)
                    # Expect filename to match pattern like "open-2024-day1-A.zip"
                    if split_by_day:
                        m = re.search(r'day(\d+)-([A-Z])\.zip', filename)
                        if m:
                            day_number = m.group(1)
                            problem_letter = m.group(2)
                            day = f"day{day_number}"
                        else:
                            print(f"Could not parse day/problem from filename: {filename}")
                            continue
                    else:
                        m = re.search(r'-([A-Z])\.zip', filename)
                        if m:
                            problem_letter = m.group(1)
                            day = ""
                        else:
                            print(f"Could not parse problem from filename: {filename}")
                            continue
                    # Destination folder: if split_by_day, then {year}/{day}/{problem_letter}, else {year}/{problem_letter}
                    if split_by_day and day:
                        dest_folder = os.path.join(year_dir, day, problem_letter)
                    else:
                        dest_folder = os.path.join(year_dir, problem_letter)
                    os.makedirs(dest_folder, exist_ok=True)
                    dest_zip = os.path.join(dest_folder, f"{problem_letter}.zip")
                    if download_file(href, dest_zip, timeout=30):
                        unzip_file(dest_zip, dest_folder)
            else:
                print("No <ul> found after 'Архивы' header.")
        else:
            print("No archive section found.")
    def crawl(self, year=None, round_name=None):
        urls = {
            "2023": {
                "final": self.base_url + "2023-24/final-materials/?lang=en",
                "qualification": self.base_url + "2023-24/zaoch-materials/?lang=en",
            },
            "2024":{
                "qualification": self.base_url + "2024-25/zaoch-materials/?lang=en",
                "final": self.base_url + "2024-25/final-materials/?lang=en",
            },
        }
        for year, year_urls in urls.items():
            for round_name, url in year_urls.items():
                if year and round_name and (year != year or round_name != round_name):
                    continue
                print(f"Processing {year} {round_name} materials...")
                html = fetch_url(url)
                if round_name == "final":
                    self.process_materials(html, year, round_name='final', split_by_day=True)
                else:
                    self.process_materials(html, year, round_name='qualification', split_by_day=False)
    
    def _extract_problem_details(self, xml_file_path):
        """
        Extracts details from a Polygon problem XML file and returns three dictionaries:
        
        1. problem: Contains overall problem details (time limit, memory limit, total score,
            tags, and english_name).
        2. subtasks: Mapping from subtask (group) ids to a dictionary:
                { "score": <float>, "testcases": [list of test indices], "task": "Subtask X" }
        3. solutions: Mapping (keyed by an index string) of solution details:
                {
                "tag": <solution tag>,
                "score": <float or None>,      # score for the solution if available
                "source": { "path": <string>, "type": <string> },
                "extra_tags": [ { attribute: value, ... }, ... ]
                }

        Args:
            xml_file_path (str): The path to the XML file.
            
        Returns:
            tuple: (problem, subtasks, solutions)
        """
        # Parse the XML file.
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # ---------------------- Extract Problem Details ----------------------
        # Time limit and memory limit.
        time_limit_elem = root.find(".//judging/testset/time-limit")
        memory_limit_elem = root.find(".//judging/testset/memory-limit")
        try:
            time_limit = int(time_limit_elem.text.strip()) if time_limit_elem is not None and time_limit_elem.text else None
        except Exception:
            time_limit = None
        try:
            memory_limit = int(memory_limit_elem.text.strip()) if memory_limit_elem is not None and memory_limit_elem.text else None
        except Exception:
            memory_limit = None

        # Total score: here we take it from the group with name "9".
        group9 = root.find(".//judging/testset/groups/group[@name='9']")
        total_score = 0.0
        if group9 is not None:
            total_score_str = group9.attrib.get("points")
            try:
                total_score = float(total_score_str) if total_score_str else 0.0
            except ValueError:
                total_score = 0.0

        # Problem tags.
        tags = []
        tag_elements = root.findall(".//tags/tag")
        for tag_elem in tag_elements:
            value = tag_elem.attrib.get("value")
            if value:
                tags.append(value)
                
        # --- Extract the english name ---
        english_name = None
        names_elem = root.find(".//names")
        if names_elem:
            for name_elem in names_elem.findall("name"):
                if name_elem.attrib.get("language") == "english":
                    english_name = name_elem.attrib.get("value")
                    break

        # Build the problem dictionary.
        task_type = "batch"
        for tag in tags:
            if tag in ["interactive", "interactive-judge"]:
                task_type = "interactive"
                break
            if "output" in tag and "only" in tag:
                task_type = "output-only"
                break
        problem = {
            "task": sanitize_folder_name(english_name),
            "time_limit": time_limit/1000,
            "memory_limit": memory_limit/1024/1024,
            "task_type": task_type,
            "tags": tags,
        }
        
        # ----------------------- Extract Subtasks -----------------------
        # Map test groups to test indices (1-indexed).
        test_group_map = {}
        tests = root.findall(".//judging/testset/tests/test")
        for idx, test in enumerate(tests, start=1):
            group = test.attrib.get("group")
            if not group:
                continue  # Skip tests without a group attribute.
            test_case = f"{idx:02d}"
            test_group_map.setdefault(group, []).append(test_case)
        
        # Process each <group> element to build the subtasks dictionary.
        subtasks = {}
        groups = root.findall(".//judging/testset/groups/group")
        for grp in groups:
            group_id = grp.attrib.get("name")
            score_str = grp.attrib.get("points")
            try:
                score = float(score_str) if score_str else 0.0
            except ValueError:
                score = 0.0
            testcases = test_group_map.get(group_id, [])
            subtasks[group_id] = {
                "score": score,
                "testcases": testcases,
                "task": f"Subtask {group_id}"
            }
            if score == 0 and group_id != "0":
                import pdb; pdb.set_trace()
                print(problem['task'], "has a subtask with 0 score. This is not supported by the system.")
        
        # ----------------------- Extract Solutions -----------------------
        # Define the mapping from solution tag to category.
        tag_to_category = {
            "main": "correct",
            "accepted": "correct",
            "rejected": "incorrect",
            "time-limit-exceeded": "time_limit",
            "time-limit-exceeded-or-accepted": "time_limit",
            "memory-limit-exceeded": "memory_limit",
            "runtime-error": "run_time",
        }
        
        solutions_list = []
        solution_nodes = root.findall(".//solutions/solution")
        for sol in solution_nodes:
            sol_dict = {}
            # Main tag for the solution.
            sol_tag = sol.attrib.get("tag", "").strip()
            sol_dict["tag"] = sol_tag
            
            # Determine the category based on the tag (case-insensitive).
            sol_dict["category"] = tag_to_category.get(sol_tag.lower(), "unknown")
            
            # Extract the score for the solution if available.
            sol_score = sol.attrib.get("score")
            try:
                sol_dict["score"] = float(sol_score) if sol_score else None
            except ValueError:
                sol_dict["score"] = None
            
            # Get source file info.
            source_elem = sol.find("source")
            if source_elem is not None:
                sol_dict["source"] = {
                    "path": source_elem.attrib.get("path"),
                    "type": source_elem.attrib.get("type")
                }
            else:
                sol_dict["source"] = {}
            # Collect any extra tags.
            extra_tags = []
            extra_tags_parent = sol.find("extra-tags")
            if extra_tags_parent is not None:
                for et in extra_tags_parent.findall("extra-tag"):
                    extra_tag = { key: value for key, value in et.attrib.items() }
                    extra_tags.append(extra_tag)
            sol_dict["extra_tags"] = extra_tags
            solutions_list.append(sol_dict)
        
        # Convert the list of solutions into a dictionary keyed by index (as string).
        solutions = {}
        for i, sol in enumerate(solutions_list):
            solutions[str(i)] = sol

        return problem, subtasks, solutions
    def _extract_problem_details(self, xml_file_path):
        """
        Extracts details from a Polygon problem XML file and returns three dictionaries:
        
        1. problem: Contains overall problem details (time_limit, memory_limit, total_score,
        tags, english_name, task (sanitized english name), and task_type).
        2. subtasks: Mapping from subtask (group) ids to a dictionary:
                { 
                "score": <float>, 
                "testcases": [list of test case names (e.g., "01", "02", ...)], 
                "task": <sanitized task name>
                }
        The aggregated testcases include tests from the current group plus those from its transitive
        dependency groups. However, the subtask score is determined as follows:
            - If the group element has a "points" attribute, that value is used.
            - Otherwise, the score is computed as the sum of the scores of tests directly assigned to the group.
        3. solutions: Mapping (keyed by a two-digit index string) of solution details:
                {
                "tag": <solution tag>,
                "score": <float or None>,
                "category": <string>,    # category based on tag ("correct", "incorrect", "time_limit", etc.)
                "source": { "path": <string>, "type": <string> },
                "extra_tags": [ { attribute: value, ... }, ... ]
                }
                
        The categorization of solutions is defined as:
            accepted                          -> correct
            rejected                          -> incorrect
            time-limit-exceeded               -> time_limit
            time-limit-exceeded-or-accepted   -> time_limit
            memory-limit-exceeded             -> memory_limit
            runtime-error                     -> run_time
            
        Args:
            xml_file_path (str): The path to the XML file.
            
        Returns:
            tuple: (problem, subtasks, solutions)
        """
        # Parse the XML file.
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # ---------------------- Extract Problem Details ----------------------
        time_limit_elem = root.find(".//judging/testset/time-limit")
        memory_limit_elem = root.find(".//judging/testset/memory-limit")
        try:
            time_limit = int(time_limit_elem.text.strip()) if time_limit_elem is not None and time_limit_elem.text else None
        except Exception:
            time_limit = None
        try:
            memory_limit = int(memory_limit_elem.text.strip()) if memory_limit_elem is not None and memory_limit_elem.text else None
        except Exception:
            memory_limit = None

        # Total score is taken from the group with name "9"
        group9 = root.find(".//judging/testset/groups/group[@name='9']")
        total_score = 0.0
        if group9 is not None:
            total_score_str = group9.attrib.get("points")
            try:
                total_score = float(total_score_str) if total_score_str else 0.0
            except ValueError:
                total_score = 0.0

        # Problem tags.
        tags = []
        for tag_elem in root.findall(".//tags/tag"):
            value = tag_elem.attrib.get("value")
            if value:
                tags.append(value)
                    
        # Extract the english name.
        english_name = None
        names_elem = root.find(".//names")
        if names_elem:
            for name_elem in names_elem.findall("name"):
                if name_elem.attrib.get("language") == "english":
                    english_name = name_elem.attrib.get("value")
                    break

        # Determine task type.
        task_type = "batch"
        for tag in tags:
            if tag in ["interactive", "interactive-judge"]:
                task_type = "interactive"
                break
            if "output" in tag and "only" in tag:
                task_type = "output-only"
                break
        problem = {
            "task": sanitize_folder_name(english_name),
            "time_limit": time_limit/1000 if time_limit else None,
            "memory_limit": memory_limit/1024/1024 if memory_limit else None,
            "task_type": task_type,
            "tags": tags,
        }
        
        # ----------------------- Extract Subtasks -----------------------
        # Build a mapping from test groups to list of tuples (test_case_name, points)
        test_group_map = {}
        tests = root.findall(".//judging/testset/tests/test")
        for idx, test in enumerate(tests, start=1):
            group = test.attrib.get("group")
            if not group:
                continue
            test_case = f"{idx:02d}"  # Two-digit name (e.g., "01", "02", ...)
            try:
                points = float(test.attrib.get("points", "0.0"))
            except ValueError:
                points = 0.0
            test_group_map.setdefault(group, []).append((test_case, points))
            
        # Build a dependency mapping: group id -> list of immediate dependency group ids.
        dependency_map = {}
        groups_elem = root.findall(".//judging/testset/groups/group")
        for grp in groups_elem:
            group_id = grp.attrib.get("name")
            deps = []
            dependencies_elem = grp.find("dependencies")
            if dependencies_elem is not None:
                for dep in dependencies_elem.findall("dependency"):
                    dep_group = dep.attrib.get("group")
                    if dep_group:
                        deps.append(dep_group)
            dependency_map[group_id] = deps

        # Helper: Compute transitive dependencies for a given group.
        def get_transitive_deps(gid, dep_map, visited=None):
            if visited is None:
                visited = set()
            if gid in visited:
                return set()
            visited.add(gid)
            result = set(dep_map.get(gid, []))
            for dep in dep_map.get(gid, []):
                result |= get_transitive_deps(dep, dep_map, visited)
            return result

        subtasks = {}
        for grp in groups_elem:
            group_id = grp.attrib.get("name")
            # direct tests for this group
            direct_tests = test_group_map.get(group_id, [])
            # Aggregated test cases: include direct tests and tests from transitive dependencies.
            aggregated_tests = {}
            for tc, pts in direct_tests:
                aggregated_tests[tc] = pts
            trans_deps = get_transitive_deps(group_id, dependency_map)
            for dep in trans_deps:
                for tc, pts in test_group_map.get(dep, []):
                    aggregated_tests[tc] = pts
            test_case_names = sorted(aggregated_tests.keys(), key=lambda x: int(x))
            
            # Determine subtask score:
            # - If the group element has a "points" attribute, use that.
            # - Otherwise (for points-policy="each-test"), sum up only the direct tests’ scores.
            group_points = grp.attrib.get("points")
            if group_points is not None and group_points.strip() != "":
                try:
                    aggregated_score = float(group_points)
                except ValueError:
                    aggregated_score = 0.0
            else:
                aggregated_score = direct_tests[0][1] if direct_tests else -1000
                
            subtasks[group_id] = {
                "score": aggregated_score,
                "testcases": test_case_names,
                "task": sanitize_folder_name(f"Subtask {group_id}")
            }
            
        # ----------------------- Extract Solutions -----------------------
        tag_to_category = {
            "accepted": "correct",
            "rejected": "incorrect",
            "time-limit-exceeded": "time_limit",
            "time-limit-exceeded-or-accepted": "time_limit",
            "memory-limit-exceeded": "memory_limit",
            "runtime-error": "run_time",
        }
            
        solutions_list = []
        solution_nodes = root.findall(".//solutions/solution")
        for sol in solution_nodes:
            sol_dict = {}
            sol_tag = sol.attrib.get("tag", "").strip()
            sol_dict["tag"] = sol_tag
            sol_dict["category"] = tag_to_category.get(sol_tag.lower(), "unknown")
            sol_score = sol.attrib.get("score")
            try:
                sol_dict["score"] = float(sol_score) if sol_score else None
            except ValueError:
                sol_dict["score"] = None
            source_elem = sol.find("source")
            if source_elem is not None:
                sol_dict["source"] = {
                    "path": source_elem.attrib.get("path"),
                    "type": source_elem.attrib.get("type")
                }
            else:
                sol_dict["source"] = {}
            extra_tags = []
            extra_tags_parent = sol.find("extra-tags")
            if extra_tags_parent is not None:
                for et in extra_tags_parent.findall("extra-tag"):
                    extra_tag = { key: value for key, value in et.attrib.items() }
                    extra_tags.append(extra_tag)
            sol_dict["extra_tags"] = extra_tags
            solutions_list.append(sol_dict)
            
        # Convert solutions list into a dictionary keyed by two-digit indices.
        solutions = {}
        for i, sol in enumerate(solutions_list, start=1):
            solutions[f"{i:02d}"] = sol

        return problem, subtasks, solutions
    def _move_solutions_by_category(self, solutions, base_dir="solutions", target_base_dir="categorized_solutions"):
        """
        Creates a folder for each unique solution category and moves the solution files into the corresponding folder.

        Each solution in the `solutions` dictionary is expected to be a dictionary that contains:
        - "category": A string representing the category (e.g., "correct", "incorrect", "time_limit", etc.)
        - "source": A dictionary with key "path" that gives the location of the solution file.
        
        If the source path is relative, it is assumed to be relative to `base_dir`.
        
        Args:
            solutions (dict): A dictionary (keyed by solution ID/index) of solution details.
            base_dir (str): The directory where the solution files are currently located (if file paths are relative).
            target_base_dir (str): The parent directory where the categorized solution folders will be created.
        
        Returns:
            None
        """
        # Ensure the target base directory exists.
        os.makedirs(target_base_dir, exist_ok=True)
        
        for sol_id, sol in solutions.items():
            # Get the category (default to "unknown" if not present).
            category = sol.get("category", "unknown")
            # Get the source file path.
            source_info = sol.get("source", {})
            source_path = source_info.get("path")
            
            # Create the destination folder for the given category.
            dest_folder = os.path.join(target_base_dir, category)
            os.makedirs(dest_folder, exist_ok=True)
            
            # Determine the destination path using the original file name.
            file_name = os.path.basename(source_path)
            dest_path = os.path.join(dest_folder, file_name)

            if os.path.exists(dest_path):
                continue
            if not source_path:
                print(f"Solution {sol_id} has no source path defined. Skipping.")
                continue

            # If source_path is relative, interpret it relative to base_dir.
            if not os.path.isabs(source_path):
                # We use the basename to avoid duplicating directory hierarchies.
                source_path = os.path.join(base_dir, os.path.basename(source_path))
            
            # Check if the file exists.
            if not os.path.exists(source_path):
                print(f"Source file {source_path} for solution {sol_id} does not exist. Skipping.")
                continue

            try:
                shutil.move(source_path, dest_path)
                print(f"Moved solution file {source_path} to {dest_path}.")
            except Exception as e:
                print(f"Error moving file {source_path} for solution {sol_id}: {e}")
    def _process_contest(self, contest_path):
        tasks = []
        for task in os.listdir(contest_path):
            task_path = os.path.join(contest_path, task)
            if not os.path.isdir(task_path):
                continue
            statement_pdf_folder = os.path.join(task_path, "statements", ".pdf")
            statement_tex_folder = os.path.join(task_path, "statements")
            problem, subtasks, solutions = self._extract_problem_details(os.path.join(task_path, "problem.xml"))
            self._move_solutions_by_category(solutions, base_dir=os.path.join(task_path, "solutions"), target_base_dir=os.path.join(task_path, "categorized_solutions"))
            problem['original_folder'] = task
            material_path = os.path.join(task_path, "materials")
            if os.path.exists(material_path):
                unzip_files(material_path)
                zip_file = [file for file in os.listdir(material_path) if file.endswith(".zip")]
                code_name = zip_file[0].split(".")[0]
                problem['code'] = code_name
            task_obj = Task(
                name=problem["task"],
                statements=[os.path.join(statement_pdf_folder,"english", "problem.pdf"),os.path.join(statement_tex_folder, "english", "problem.tex"), statement_tex_folder],
                translations = os.path.join(statement_pdf_folder, "russian"),
                graders = [os.path.join(task_path, "check.cpp"), os.path.join(task_path, "files", "testlib.h")],
                tests=os.path.join(task_path, "tests"),
                editorial_files=[os.path.join(statement_pdf_folder, "english", "tutorial.pdf"),os.path.join(statement_tex_folder, "english", "tutorial.tex")],
                code_files=os.path.join(task_path, "categorized_solutions"),
                attachments=os.path.join(material_path, "files"),
                problem_json=problem,
                subtasks=subtasks,
            )
            tasks.append(task_obj)
        return tasks
    
    def restructure(self):
        new_path = self._restructure_path
        for year in ["2024", "2023"]:
            # process qualification round
            qualification_path = os.path.join(self._path, year, "qualification")
            tasks = self._process_contest(qualification_path)
            contest = Contest("qualification", year=year)
            for task in tasks:
                contest.add_task(task)
            contest.write(new_path)
            contest = Contest("final", year=year)
            for day in ["day1", "day2"]:
                contest_path = os.path.join(self._path, year, "final", day)
                if not os.path.exists(contest_path):
                    continue
                tasks = self._process_contest(contest_path)
                for task in tasks:
                    contest.add_task(task, split=day)
            contest.write(new_path)       
    def parse(self):
        pass

if __name__ == "__main__":
    ooi_crawler = OOICrawler(crawl_path = f"{os.environ['HOME_DIR']}/IOI-Bench/OOI", competition="OOI", restructure_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/OOI", parse_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed/OOI", converter=None)
    #ooi_crawler.crawl(year="2024", round_name="final")
    ooi_crawler.restructure()