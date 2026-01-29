import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os

class CSESScraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://cses.fi"
        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }
        self.username = os.environ["CSES_USERNAME"]
        self.password = os.environ["CSES_PASSWORD"]
        self.csrf_token = None

    def debug_page(self, url):
        """
        Retrieve and return the raw HTML of a given URL for debugging.
        """
        res = self.session.get(url)
        return res.text
    
    def login(self):
        login_url = f"{self.base_url}/login"
        res = self.session.get(login_url, headers=self.headers)
        soup = BeautifulSoup(res.text, "html.parser")
        token = soup.find("input", {"name": "csrf_token"})["value"]

        payload = {
            "csrf_token": token,
            "nick": self.username,
            "pass": self.password,
        }
        self.csrf_token = token
        post = self.session.post(login_url, data=payload, headers=self.headers)
        return "Log out" in post.text

    def join_contest(self, contest_id, upsolve=True, debug=False):
        """
        Join a contest.
        If upsolve is True, uses the upsolve endpoint.
        If debug=True, prints out the contest page and join response.
        Returns True if joining was successful.
        """
        # Use upsolve or join endpoint accordingly:
        endpoint = "upsolve" if upsolve else "join"
        join_url = f"{self.base_url}/{contest_id}/{endpoint}/"
        contest_page_url = f"{self.base_url}/{contest_id}/"
        res = self.session.get(contest_page_url)
        if debug:
            print("=== Contest Page HTML ===")
            print(res.text)
        soup = BeautifulSoup(res.text, "html.parser")

        payload = {
            "csrf_token": self.csrf_token,
            "id": contest_id,
            "u": "1" if upsolve else "0"
        }

        post = self.session.post(join_url, data=payload)
        if debug:
            print("=== Join Contest Response HTML ===")
            print(post.text)
        # Check for some indicator that the contest page now shows problems/tasks.
        return "Problems" in post.text or "Tasks" in post.text

    def get_problem_limits(self, contest_id, debug=False):
        """
        Retrieves the problem list for a contest and extracts each problem's
        time and memory limits, along with problem letter, title, and submission link.
        
        If the task list is not found (i.e. contest not started/upsolved),
        this function calls join_contest to join/upsolve the contest and then re-fetches the list.
        
        Returns a dictionary with the problem letter as key.
        """
        list_url = f"{self.base_url}/{contest_id}/list/"
        res = self.session.get(list_url)
        if debug:
            print("=== Problem List Page HTML ===")
            print(res.text)
        soup = BeautifulSoup(res.text, "html.parser")
        task_list = soup.find("ul", class_="task-list contest headless")
        
        # If task list not found, try joining/upsolving the contest via join_contest
        if not task_list:
            if debug:
                print("No task list found! Attempting to join/upsolve the contest using join_contest().")
            if not self.join_contest(contest_id, upsolve=True, debug=debug):
                if debug:
                    print("join_contest did not succeed; cannot access problem list.")
                return {}
            # Re-fetch the problem list page after joining/upsolving.
            res = self.session.get(list_url)
            if debug:
                print("=== Problem List Page HTML (after join_contest) ===")
                print(res.text)
            soup = BeautifulSoup(res.text, "html.parser")
            task_list = soup.find("ul", class_="task-list contest headless")
            if not task_list:
                if debug:
                    print("Still no task list found after joining contest.")
                return {}
        
        problems = {}
        for li in task_list.find_all("li", class_="task"):
            # Get problem letter (e.g., A, B, C)
            letter_tag = li.find("b")
            problem_letter = letter_tag.text.strip() if letter_tag else "Unknown"

            # Get problem title.
            title_div = li.find("div")
            title = title_div.contents[0].strip() if title_div and title_div.contents else "No Title"

            # Get details: time limit and memory limit are in the <div class="details">
            details_div = li.find("div", class_="details")
            if details_div:
                spans = details_div.find_all("span")
                time_limit = spans[0].text.strip() if len(spans) >= 1 else "?"
                memory_limit = spans[1].text.strip() if len(spans) >= 2 else "?"
            else:
                time_limit, memory_limit = "?", "?"

            # Get submit link from the <a> tag inside details (if present)
            submit_link = None
            if details_div:
                a_tag = details_div.find("a", href=True)
                if a_tag:
                    submit_link = self.base_url + a_tag["href"]

            problems[problem_letter] = {
                "title": title,
                "time_limit": time_limit,
                "memory_limit": memory_limit,
                "submit_link": submit_link
            }
        return problems


    def submit_solution(self, submit_url, file_path, lang="C++", option="C++17", max_retries=5, wait_seconds=10, debug=False):
        """
        Submits a solution file to the given submission URL with retry mechanism.
        
        Parameters:
        submit_url (str): The full URL of the submission page (e.g., "https://cses.fi/498/submit/A")
        file_path (str): Path to the solution file.
        lang (str): Programming language (default "C++").
        option (str): Language option (default "C++17").
        max_retries (int): Maximum number of retry attempts (default 5).
        wait_seconds (int): Wait time between retries in seconds (default 10).
        debug (bool): If True, prints debug information.
        
        Returns:
        submission_id (str): The submission id extracted from the redirect URL.
        
        Raises:
        ValueError: If the necessary form fields are missing or if submission id cannot be found after retries.
        """
        # Fetch the submission page to extract form fields
        page = self.session.get(submit_url)
        if debug:
            print("=== Submit Page HTML ===")
            print(page.text)
        soup = BeautifulSoup(page.text, "html.parser")
        
        token_input = soup.find("input", {"name": "csrf_token"})
        task_input = soup.find("input", {"name": "task"})
        target_input = soup.find("input", {"name": "target"})
        
        if not token_input or not task_input:
            raise ValueError("Missing necessary form fields (csrf_token or task).")
        
        token = token_input["value"]
        task_id = task_input["value"]
        target = target_input["value"] if target_input else ""
        
        data = {
            "csrf_token": token,
            "task": task_id,
            "lang": lang,
            "option": option,
            "type": "contest",
            "target": target
        }
        
        attempt = 0
        while attempt < max_retries:
            with open(file_path, "rb") as f:
                files = {"file": (file_path, f)}
                response = self.session.post(f"{self.base_url}/contest/send.php", data=data, files=files)
            
            if debug:
                print("=== Submission Response HTML (Attempt {}): ===".format(attempt+1))
                print(response.text)
            
            # Check if response indicates too high submission rate.
            if "You are not allowed to submit at the moment due to high submission rate" in response.text:
                if debug:
                    print("High submission rate detected. Waiting {} seconds before retrying...".format(wait_seconds))
                time.sleep(wait_seconds)
                attempt += 1
            else:
                # Try to extract submission id from the redirect URL
                match = re.search(r"/result/(\d+)/", response.url)
                if match:
                    submission_id = match.group(1)
                    return submission_id
                else:
                    print("Submission ID not found in the response URL.")
                    if debug:
                        print("Response URL:", response.url)
                    return None
        
        # If we get here, all attempts failed
        print("Max retries reached. Submission failed.")
        return None

    def get_submission_result(self, contest_id, submission_id, debug=False):
        """
        Retrieves the submission result page for a specific task and submission id.
        
        Parameters:
        contest_id (str): The contest identifier (e.g., "498")
        task_letter (str): The task letter (e.g., "A")
        submission_id (str): The submission id (e.g., "12532813")
        debug (bool): If True, prints the raw HTML for debugging.
        
        Returns:
        tuple: (overall_score, feedback_list) where feedback_list is a list of tuples (group, verdict, score)
        """
        # Construct the URL including the submission_id.
        result_url = f"{self.base_url}/{contest_id}/result/{submission_id}/"

        while True:
            res = self.session.get(result_url)
            soup = BeautifulSoup(res.text, "html.parser")
            # Look for the status element (assumed to have id="status")
            status_tag = soup.find("span", id="status")
            if not status_tag:
                print("Status element not found, retrying in 2 seconds...")
                time.sleep(2)
                continue
            status_text = status_tag.text.strip().upper()
            if status_text == "READY":
                break
            if status_text == "COMPILE ERROR":
                break
            else:
                print(f"Status is '{status_text}', waiting for READY...")
                time.sleep(2)
        
        if debug:
            print("=== Submission Result Page HTML ===")
            print(res.text)
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Updated: find a span that has both "inline-score" and "task-score" in its class list.
        score_tag = soup.find("span", class_=lambda x: x and "inline-score" in x and "task-score" in x)
        overall_score = score_tag.text.strip() if score_tag else "0"
        
        feedback_table_caption = soup.find("caption", string=lambda text: text and "Feedback" in text)
        feedback = []
        if feedback_table_caption:
            table = feedback_table_caption.find_parent("table")
            rows = table.find_all("tr")[1:]  # Skip header row
            for row in rows:
                cols = row.find_all("td")
                group = cols[0].text.strip()
                verdict = cols[1].text.strip()
                score = cols[2].text.strip()
                feedback.append((group, verdict, score))
        
        return overall_score, feedback
    def download_testcases(self, contest_id, submission_id, test_folder, group_score):
        """
        Downloads test cases from the submission result page, saves them in test_folder as
        "1.in", "1.out", "2.in", "2.out", etc., and then categorizes each test case into groups.
        The grouping is done based on the "Test results" table: for each test, the associated groups 
        (e.g. "4, 5") are extracted. After all tests are saved, a subtasks.json file is produced that 
        for each group (from group_score) lists the tests belonging to that group.
        
        Parameters:
            contest_id (str): Contest identifier.
            submission_id (str): Submission identifier.
            test_folder (str): Folder where test case files and subtasks.json will be saved.
            group_score (tuple): Tuple in the format (overall_score, list of group feedback tuples).
                                For example: 
                                ('100', [('#1', 'ACCEPTED', '11'),
                                        ('#2', 'ACCEPTED', '14'),
                                        ('#3', 'ACCEPTED', '15'),
                                        ('#4', 'ACCEPTED', '29'),
                                        ('#5', 'ACCEPTED', '31')])
                                
        Returns:
            dict: A dictionary corresponding to subtasks.json.
        """
        from tqdm import tqdm
        import os
        import json

        # Ensure test_folder exists.
        os.makedirs(test_folder, exist_ok=True)

        # Build submission result page URL and fetch it.
        submission_url = f"{self.base_url}/{contest_id}/result/{submission_id}/"
        res = self.session.get(submission_url)
        soup = BeautifulSoup(res.text, "html.parser")

        # -------------------------
        # Part 1: Extract test details.
        # -------------------------
        # Find all test detail sections like <h4 id="test123"> and sort them by number.
        test_headers = soup.find_all("h4", id=re.compile(r"test\d+"))
        tests = sorted(test_headers, key=lambda tag: int(re.findall(r"\d+", tag["id"])[0]))
        if not tests:
            raise ValueError("No test cases found on the submission page.")

        def extract_test_io(tag):
            """
            Extracts the input and expected output for a test case.
            It first tries to use the "save" (or "view") link from the associated table;
            if not available, it falls back to the inline content.
            """
            input_text, output_text = None, None
            next_elem = tag.find_next()
            while next_elem:
                if next_elem.name == "table":
                    header = next_elem.find("th")
                    if header:
                        header_text = header.get_text().lower()
                        if "input" in header_text and input_text is None:
                            link = next_elem.find("a", class_="save") or next_elem.find("a", class_="view")
                            if link:
                                url = self.base_url + link["href"]
                                r = self.session.get(url)
                                input_text = r.text.strip()
                            else:
                                samp = next_elem.find("samp")
                                if samp:
                                    input_text = samp.get_text()
                        elif "correct output" in header_text and output_text is None:
                            link = next_elem.find("a", class_="save") or next_elem.find("a", class_="view")
                            if link:
                                url = self.base_url + link["href"]
                                r = self.session.get(url)
                                output_text = r.text.strip()
                            else:
                                samp = next_elem.find("samp")
                                if samp:
                                    output_text = samp.get_text()
                        if input_text is not None and output_text is not None:
                            break
                next_elem = next_elem.find_next()
            return input_text, output_text

        # -------------------------
        # Part 2: Parse test results table to extract group assignments.
        # -------------------------
        test_to_groups = {}  # Map test number (as string) -> list of group ids (as strings)
        test_to_groups = {}  # Map test number (as string) -> list of group ids (as strings)
        results_table = None
        for table in soup.find_all("table", class_="narrow"):
            thead = table.find("thead")
            if thead:
                ths = thead.find_all("th")
                header_texts = [th.get_text().strip().lower() for th in ths]
                if "test" in header_texts and "group" in header_texts:
                    # Get the column indices
                    header_index = {name: i for i, name in enumerate(header_texts)}
                    test_idx = header_index.get("test")
                    group_idx = header_index.get("group")
                    results_table = table
                    rows = table.find_all("tr")[1:]  # Skip the header row.
                    for row in rows:
                        cols = row.find_all("td")
                        if len(cols) > max(test_idx, group_idx):
                            test_label = cols[test_idx].get_text().strip()  # e.g. "#1"
                            test_num = test_label.lstrip("#").strip()
                            group_text = cols[group_idx].get_text().strip()
                            groups = [g.strip() for g in group_text.split(",") if g.strip()]
                            test_to_groups[test_num] = groups
                    break
        if results_table is None:
            print("Warning: Test results table not found. No group info will be assigned.")
        
        # -------------------------
        # Part 3: Download and save test cases.
        # -------------------------
        # Use a global sequential counter based on the test number from the h4 tag.
        # We assume that the h4 tags for tests contain numbers that match those in the results table.
        # We create files named e.g. "1.in", "1.out", "2.in", "2.out", etc.
        # for header in tqdm(tests, desc="Downloading test cases", leave=False):
        #     # Extract test number from the header.
        #     tn = str(int(re.findall(r"\d+", header["id"])[0]))
        #     input_text, output_text = extract_test_io(header)
        #     in_filename = os.path.join(test_folder, f"{tn}.in")
        #     out_filename = os.path.join(test_folder, f"{tn}.out")
        #     with open(in_filename, "w") as f:
        #         if input_text:
        #             f.write(input_text)
        #     with open(out_filename, "w") as f:
        #         if output_text:
        #             f.write(output_text)

        # -------------------------
        # Part 4: Categorize tests into groups according to test_to_groups and group_score.
        # -------------------------
        # Build subtasks.json: for each feedback tuple from group_score, assign all test cases whose
        # number is present in test_to_groups mapping for that group.
        subtasks = {}
        # Iterate over the group_score feedback list.
        for feedback in group_score[1]:
            # feedback tuple format: ("#<group>", verdict, score)
            group_label = feedback[0].strip()  # e.g. "#1"
            group_id = group_label.lstrip("#")  # e.g. "1"
            score = int(feedback[2])
            # Find all test numbers whose groups (from results table) include this group id.
            testcases = []
            for test_num, groups in test_to_groups.items():
                if group_id in groups:
                    testcases.append(test_num)  # Use test number (which matches the file name, e.g., "1")
            # Sort testcases numerically
            testcases = sorted(testcases, key=lambda x: int(x))
            subtasks[group_id] = {"score": score, "testcases": testcases, "task": f"Subtask {group_id}"}

        # -------------------------
        # Part 5: Write subtasks.json
        # -------------------------
        subtasks_path = os.path.join(test_folder, "subtasks.json")
        with open(subtasks_path, "w") as f:
            json.dump(subtasks, f, indent=2)

        return subtasks