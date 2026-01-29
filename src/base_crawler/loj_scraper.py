import requests
from bs4 import BeautifulSoup
import re
import time
import json
import os

class LOJcraper:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://loj.ac/"
        self.headers = {
            "User-Agent": "Mozilla/5.0"
        }
        self.username = os.environ["LOJ_USERNAME"]
        self.password = os.environ["LOJ_PASSWORD"]
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

    def category_tag_id(self):
        pass
    def get_problem_page(self):    
        pass
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
            else:
                print(f"Status is '{status_text}', waiting for READY...")
                time.sleep(2)
        
        if debug:
            print("=== Submission Result Page HTML ===")
            print(res.text)
            
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Updated: find a span that has both "inline-score" and "task-score" in its class list.
        score_tag = soup.find("span", class_=lambda x: x and "inline-score" in x and "task-score" in x)
        overall_score = score_tag.text.strip() if score_tag else "N/A"
        
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
        Downloads the test cases from the submission result page, categorizes them into subtask groups,
        and saves them in the specified test folder. Then creates and returns a subtasks.json dictionary.
        
        Parameters:
            contest_id (str): Contest identifier.
            submission_id (str): Submission identifier.
            test_folder (str): Folder where test cases will be downloaded.
            group_score (tuple): Tuple in the format (overall_score, list of group feedback tuples).
        
        Returns:
            dict: A dictionary corresponding to subtasks.json.
        """
        # Build submission result page URL
        submission_url = f"{self.base_url}/{contest_id}/result/{submission_id}/"
        res = self.session.get(submission_url)
        soup = BeautifulSoup(res.text, "html.parser")
        
        # Locate test detail sections; assume they are marked with <h4 id=\"testX\"> tags
        test_details = soup.find_all("h4", id=re.compile(r"test\\d+"))
        tests = sorted(test_details, key=lambda tag: int(re.findall(r'\\d+', tag['id'])[0]))
        
        # Define expected test counts per subtask (based on the sample structure):
        # Subtask 0: 1 test (sample), Subtask 1: 5 tests, Subtask 2: 11 tests
        expected_counts = {"0": 1, "1": 5, "2": 11}
        total_expected = sum(expected_counts.values())
        all_tests = tests[:total_expected]
        
        # Assign tests to subtasks sequentially
        assigned = {"0": [], "1": [], "2": []}
        idx = 0
        for key in ["0", "1", "2"]:
            count = expected_counts[key]
            for _ in range(count):
                if idx < len(all_tests):
                    assigned[key].append(all_tests[idx])
                    idx += 1
        
        # Create directories for each subtask and download test cases
        subtask_counters = {"0": 1, "1": 1, "2": 1}
        for subtask, tags in assigned.items():
            subtask_dir = os.path.join(test_folder, f"subtask_{subtask}")
            os.makedirs(subtask_dir, exist_ok=True)
            for tag in tags:
                # Extract test number from tag id (e.g., 'test1' -> 1)
                test_num = int(re.findall(r'\\d+', tag['id'])[0])
                
                # Find corresponding test details: search for tables following the <h4> tag
                input_text = None
                output_text = None
                next_elem = tag.find_next()
                while next_elem:
                    if next_elem.name == "table":
                        header = next_elem.find("th")
                        if header:
                            header_text = header.get_text().lower()
                            if "input" in header_text and input_text is None:
                                samp = next_elem.find("samp")
                                if samp:
                                    input_text = samp.get_text()
                            elif "correct output" in header_text and output_text is None:
                                samp = next_elem.find("samp")
                                if samp:
                                    output_text = samp.get_text()
                            if input_text is not None and output_text is not None:
                                break
                    next_elem = next_elem.find_next()
                
                # Prepare filenames with the naming pattern: \"<subtask>-<counter:02d>.in\" and \".out\"
                counter = subtask_counters[subtask]
                in_filename = os.path.join(subtask_dir, f"{subtask}-{counter:02d}.in")
                out_filename = os.path.join(subtask_dir, f"{subtask}-{counter:02d}.out")
                
                with open(in_filename, "w") as f:
                    if input_text is not None:
                        f.write(input_text)
                with open(out_filename, "w") as f:
                    if output_text is not None:
                        f.write(output_text)
                
                subtask_counters[subtask] += 1
        
        # Create subtasks.json dictionary based on the sample structure
        subtasks = {
            "0": {"score": 0, "testcases": [f"0-{i:02d}" for i in range(1, expected_counts["0"] + 1)], "task": "Subtask 0"},
            "1": {"score": 30, "testcases": [f"1-{i:02d}" for i in range(1, expected_counts["1"] + 1)], "task": "Subtask 1"},
            "2": {"score": 70, "testcases": [f"2-{i:02d}" for i in range(1, expected_counts["2"] + 1)], "task": "Subtask 2"}
        }
        
        # Write the subtasks.json file into the test folder
        subtasks_path = os.path.join(test_folder, "subtasks.json")
        with open(subtasks_path, "w") as f:
            json.dump(subtasks, f, indent=2)
        
        return subtasks