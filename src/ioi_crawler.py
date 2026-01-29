from base_crawler import Crawler, Contest, Task
from utils import *
from subtask_utils import *
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
import re
import os
import logging
import zipfile
from pathlib import Path
from urllib.parse import urljoin, urlparse
import concurrent.futures, threading
from bs4 import BeautifulSoup, FeatureNotFound
import tarfile
import xml.etree.ElementTree as ET
# ─────────────—— HTML parsing and link extraction —————————— #
def _soup(html: str):
    try:
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound:
        return BeautifulSoup(html, "html.parser")


def _extract_links(html: str, base_url: str):
    """
    Return every task‑related link on the page.

    • Works even if the organiser did *not* prefix folders with "day0/", "day1/", …
    • Accepts any relative link (or same‑host absolute link) whose filename ends with
      the extensions we care about.
    • Keeps special cases for editorials / reviews so they’re always downloaded.
    """
    soup = _soup(html)

    exts = (".pdf", ".doc", ".docx", ".zip", ".tgz", ".tar.gz")

    base_host = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"]
        low  = href.lower()

        # Skip obvious non‑task links (CSS, JS, external hosts)
        parsed = urlparse(href)
        if parsed.scheme in ("http", "https") and parsed.netloc and parsed.netloc != base_host:
            continue          # external link → ignore

        # Special‑case editorials / reviews (any folder)
        if low.endswith(("-editorial.pdf", "-editorial.doc", "-editorial.docx", "review.pdf", "review.doc", "review.docx")) \
           or low in ("editorial.pdf", "editorial.doc", "editorial.docx"):
            yield href
            continue

        # Generic rule: keep anything whose filename ends with the wanted extensions
        if low.endswith(exts):
            yield href

# ─────────────—— Translation detection —————————— #
_EN_RE   = re.compile(r"(?:_|-|\b)en[_-]|en_isc", re.IGNORECASE)
_EXTRA_RE = re.compile(r"(editorial|review)", re.IGNORECASE)
def _is_translation(p: Path) -> bool:
    if p.suffix.lower() not in {".pdf", ".doc", ".docx"}:               # only statements
        return False
    return not _EN_RE.search(p.name) and not _EXTRA_RE.search(p.name)

# ─────────────—— Archive extraction —————————— #
def _extract_archive(path: Path, root: Path):
    target_dir = root / path.with_suffix("").with_suffix("").relative_to(root) \
                if path.suffix.lower() in {".gz", ".tgz"} else \
                root / path.with_suffix("").relative_to(root)

    if target_dir.exists():
        return "already_extracted", target_dir

    try:
        if path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                zf.extractall(target_dir)
        elif path.suffix.lower() in {".tgz", ".gz"}:
            with tarfile.open(path) as tf:
                tf.extractall(target_dir)
        else:
            return "no_extractor", path
        return "extracted", target_dir
    except (zipfile.BadZipFile, tarfile.TarError):
        return "archive_corrupt", path

# ─────────────—— Concurrent downloader —————————— #
_lock = threading.Lock()  # for tidy console prints

def _fetch(rel, base_url, out_root, timeout, year):
    abs_url   = urljoin(base_url, rel)
    rel_path  = Path(rel)
    if _is_translation(rel_path) and year >= 2013:
        rel_path = Path("translations") / rel_path

    local = Path(out_root) / rel_path
    local.parent.mkdir(parents=True, exist_ok=True)

    if local.exists():
        with _lock: print(f"↷ skip  {local.relative_to(out_root)}")
        status = "skipped"
    else:
        try:
            r = requests.get(abs_url, stream=True, timeout=timeout)
            r.raise_for_status()
            with open(local, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            with _lock: print(f"✓ done  {local.relative_to(out_root)}")
            status = "downloaded"
        except Exception as e:
            with _lock: print(f"✗ fail  {rel}  ({e})")
            return "failed", rel

    # extract archives we just downloaded
    if status == "downloaded" and local.suffix.lower() in {".zip", ".tgz", ".gz"}:
        ex_status, tgt = _extract_archive(local, Path(out_root))
        with _lock:
            tag = "✓" if ex_status == "extracted" else "↷"
            print(f"{tag} {ex_status:17} {tgt.relative_to(out_root)}")
        status = f"{status}+{ex_status}"

    return status, local
class IOICrawler(Crawler):
    def __init__(self, *, competition="IOI", crawl_path, restructure_path, parse_path, converter=None):
        super().__init__(competition=competition, crawl_path=crawl_path, restructure_path=restructure_path, parse_path=parse_path, converter=converter)
    def crawl_htmls(self):
        baseurl = "https://ioi.te.lv/locations/ioi<YEAR>/contest"
        result_baseurl = "https://stats.ioinformatics.org/results/<YEAR>"
        htmls = {}
        results = {}
        for year in tqdm(range(2002, 2023)):
            url = baseurl.replace("<YEAR>", str(year)[-2:])
            html = fetch_url(url)
            url = result_baseurl.replace("<YEAR>", str(year))
            result_html = fetch_url(url)
            htmls[str(year)] = html
            results[str(year)] = result_html
        os.makedirs(self._path + "/htmls", exist_ok=True)
        os.makedirs(self._path + "/results", exist_ok=True)
        for year, html in htmls.items():
            with open(os.path.join(self._path, "htmls", f"{year}.html"), "w") as f:
                f.write(html.decode())
        for year, result_html in results.items():
            with open(os.path.join(self._path, "results", f"{year}.html"), "w") as f:
                f.write(result_html.decode())
        return htmls, results

    def download_tasks_concurrent(self, html: str,
                                      base_url: str,
                                      year: int, 
                                      output_dir: str = "ioi2022",
                                      max_workers: int = 8,
                                      timeout: int = 30):
        """
        Concurrently download all IOI Day 0–2 resources plus editorials.

        * .pdf / .doc(x) statements →  English vs translation routing
        * .zip and .tgz archives →  auto‑extracted
        * skips files already present / already extracted
        """
        links = sorted(set(_extract_links(html, base_url)))
        if not links:
            print("No matching links found.")
            return {}

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(_fetch, l, base_url, output_dir, timeout, year) for l in links]
            for fut in concurrent.futures.as_completed(futures):
                st, p = fut.result()
                results.setdefault(st, []).append(p)
        return results
    def crawl(self):
        """
        Crawl all IOI tasks, extract archives, and provide a comprehensive download summary
        including failures.
        """
        # Track statistics across all years
        #self.crawl_htmls()
        all_results = {
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "extracted": 0,
            "archive_corrupt": 0,
            "already_extracted": 0,
            "failures_by_year": {}
        }
        
        # Process each year
        for year in tqdm(range(2020, 2021), desc="Processing IOI years"):
            year_str = str(year)
            try:
                html_path = os.path.join(self._path, "htmls", f"{year_str}.html")
                if not os.path.exists(html_path):
                    print(f"Warning: HTML file for year {year_str} not found, skipping")
                    continue
                    
                with open(html_path, "r", encoding="utf-8") as f:
                    html_text = f.read()
                    
                page_url = f"https://ioi.te.lv/locations/ioi{str(year)[-2:]}/contest/"
                output_dir = os.path.join(self._path, year_str)
                
                print(f"\nProcessing year {year_str}:")
                summary = self.download_tasks_concurrent(
                    html_text, 
                    base_url=page_url,
                    year=year,
                    output_dir=output_dir, 
                    max_workers=4
                )
                
                # Print year summary
                print(f"\nSummary for {year_str}:")
                for k, v in summary.items():
                    if isinstance(v, list):
                        print(f"{k:11}: {len(v)}")
                        
                        # Track failures by year
                        if k == "failed":
                            all_results["failures_by_year"][year_str] = [str(item) for item in v]
                            all_results["failed"] += len(v)
                        # Count successful downloads and extractions
                        elif k == "downloaded":
                            all_results["downloaded"] += len(v)
                        elif k == "skipped":
                            all_results["skipped"] += len(v)
                        elif "extracted" in k:
                            all_results["extracted"] += len(v)
                        elif "archive_corrupt" in k:
                            all_results["archive_corrupt"] += len(v)
                        elif "already_extracted" in k:
                            all_results["already_extracted"] += len(v)
                        
            except Exception as e:
                print(f"Error processing year {year_str}: {e}")
                all_results["failures_by_year"].setdefault(year_str, []).append(f"Complete year failed: {str(e)}")
        
        # Print overall summary
        print("\n" + "="*50)
        print("OVERALL CRAWLING SUMMARY")
        print("="*50)
        print(f"Total files downloaded:      {all_results['downloaded']}")
        print(f"Total files skipped:         {all_results['skipped']}")
        print(f"Total archives extracted:    {all_results['extracted']}")
        print(f"Total already extracted:     {all_results['already_extracted']}")
        print(f"Total corrupt archives:      {all_results['archive_corrupt']}")
        print(f"Total failed downloads:      {all_results['failed']}")
        
        # Print failures by year if any
        if all_results["failed"] > 0:
            print("\nFailed downloads by year:")
            for year, failures in all_results["failures_by_year"].items():
                if failures:
                    print(f"\nYear {year} ({len(failures)} failures):")
                    for i, failure in enumerate(failures[:10], 1):  # Show at most 10 failures per year
                        print(f"  {i}. {failure}")
                    if len(failures) > 10:
                        print(f"  ... and {len(failures) - 10} more failures")
        
        # Check if day1 and day2 are missing for any year
        print("\nChecking for missing competition days:")
        for year in range(2002, 2023):
            year_str = str(year)
            year_path = os.path.join(self._path, year_str)
            if os.path.exists(year_path):
                missing_days = []
                for day in ["day0", "day1", "day2"]:
                    day_path = os.path.join(year_path, day)
                    if not os.path.exists(day_path) or not os.listdir(day_path):
                        missing_days.append(day)
                if missing_days:
                    print(f"  Year {year_str}: Missing or empty {', '.join(missing_days)}")
        
        return all_results

    def extract_subtask_info(self, xml_file_path):
        # Parse the XML file
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # Initialize the result dictionary
        result = {}
        
        # Find the testset element
        testset = root.find(".//testset")
        
        # Extract time and memory limits
        time_limit = testset.get("time-limit")
        memory_limit = testset.get("memory-limit")
        result["time_limit"] = time_limit
        result["memory_limit"] = memory_limit
        
        # Find all test groups
        test_groups = testset.findall(".//test-group")
        
        # Initialize a counter for test cases
        test_case_counter = 1
        
        # Process each test group
        for i, group in enumerate(test_groups):
            group_index = str(i)
            
            # Extract group information
            comment = group.get("comment")
            group_bonus = group.get("group-bonus")
            require_groups = group.get("require-groups", "").strip()
            
            # Parse required groups into a list of integers
            required_groups = []
            if require_groups:
                required_groups = [int(g) for g in require_groups.split() if g]
            
            # Extract test cases
            test_cases = group.findall(".//test")
            test_case_ids = []
            
            for _ in test_cases:
                # Format the test case ID with leading zeros
                test_case_id = f"{test_case_counter:02d}"
                test_case_ids.append(test_case_id)
                test_case_counter += 1
            
            # Store the group information
            result[group_index] = {
                "score": int(group_bonus) if group_bonus else 0,
                "task": comment,
                "testcases": test_case_ids,
                "required_groups": required_groups
            }
        
        return result

    def restructure_2020(self, year="2020"):
        #2020, 2018
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            if not os.path.exists(day_path):
                continue
            for task in os.listdir(day_path):
                task_path = os.path.join(day_path, task)
                if not os.path.isdir(task_path):
                    continue
                statements_path = task_path + "/statements"
                statements = [os.path.join(statements_path, f) for f in os.listdir(statements_path) if f.endswith(".pdf") or f.endswith(".md")]
                print(statements_path)
                assert len(statements) > 0, f"Statements file not found: {statements}"

                graders = task_path + "/graders/cpp/"
                if year == "2016" or year == "2018":
                    graders= task_path + "/graders/"
                checkers = task_path + "/checkers/"
                tests = task_path + "/tests/"
                assert len(os.listdir(tests)) > 0, f"Tests folder is empty: {tests}"
                #combine in and out folder together
                if os.path.exists(tests + "in/"):
                    shutil.rmtree(tests + "in_out/")
                    os.makedirs(tests + "in_out/", exist_ok=True)
                    for f in os.listdir(tests + "in/"):
                        shutil.copy(os.path.join(tests + "in/", f), os.path.join(tests + "in_out/", f.replace(".txt", ".in")))
                    if os.path.exists(tests + "out/"):
                        for f in os.listdir(tests + "out/"):
                            shutil.copy(os.path.join(tests + "out/", f), os.path.join(tests + "in_out/", f.replace(".txt", ".out")))
                    tests = tests + "in_out/"

                attachments = [task_path + "/attachments/cpp/", task_path+"/attachments/examples"]
                editorial_path = task_path + "/solutions/editorial/"
                editorial_file =[os.path.join(editorial_path, f) for f in os.listdir(editorial_path) if f.endswith(".pdf") or f.endswith(".md")]
                code_files = task_path + f"/solutions/Codes"
                #assert len(os.listdir(code_files)) > 0, f"Code files folder is empty: {code_files}"
                problem_json = task_path + f"/problem.json"
                if os.path.exists(problem_json):
                    with open(problem_json, "r") as f:
                        problem_json = json.load(f)
                        new_problem_json = {
                            "task": problem_json['code'],
                            "time_limit": problem_json.get("time_limit", 10.01),
                            "memory_limit": problem_json.get("memory_limit"),
                            "task_type": problem_json.get("type")
                        }
                else:
                    new_problem_json = {
                        "task": task,
                        "time_limit": 10.01,
                        "memory_limit": 2048,
                        "task_type": "unknown"
                    }
                if year != "2016":
                    if year == "2020":
                        test_files = [f for f in os.listdir(tests) if f not in ["01.in", "01.out", "02.in", "02.out", "03.in", "03.out"]]
                    elif year == "2017":
                        test_files = [f for f in os.listdir(tests) if f not in ["mapping"]]
                    else:
                        test_files = os.listdir(tests)
                    if year == "2020" and task == "mushrooms":
                        subtasks = create_subtasks_with_no_subtasks(test_files)
                    else:
                        subtasks = create_subtasks_by_files(test_files, new_problem_json["task_type"] == "OutputOnly")
                        if os.path.exists(task_path + "/subtasks/subtasks.json"):
                            with open(os.path.join(task_path, "subtasks/subtasks.json"), "r") as f:
                                subtasks_info = json.load(f)
                                for task_name, subtask in subtasks_info["subtasks"].items():
                                    index = str(subtask['index'])
                                    assert index in subtasks, f"Subtask {subtask['index']} not found in {subtasks}"
                                    subtasks[index].update({
                                        "task": task_name,
                                        "score": subtask['score'],
                                    })
                else:
                    subtasks = self.extract_subtask_info(os.path.join(task_path, "problem.xml"))
                    new_problem_json['time_limit'] = parse_time_to_seconds(subtasks["time_limit"])
                    new_problem_json['memory_limit'] = parse_memory_to_mb(subtasks["memory_limit"])
                    new_problem_json['task_type'] = "Batch"
                    del subtasks["time_limit"]
                    del subtasks["memory_limit"]
                task_obj = Task(
                    name=task,
                    statements=statements,
                    graders=graders,
                    checkers=checkers,
                    subtasks=subtasks,
                    tests=tests,
                    attachments=attachments,
                    editorial_files=editorial_file,
                    code_files=code_files,
                    problem_json=new_problem_json
                )
                contest.add_task(task_obj, split=day)
        contest.write(self._restructure_path)
    def restructure_year(self, year):
        contest = Contest(year=year)
        for day in ["day1", "day2"]:
            day_path = os.path.join(self._path, year, day)
            if not os.path.exists(day_path):
                continue
            for task in os.listdir(day_path):
                task_path = os.path.join(day_path, task)
                if not os.path.isdir(task_path):
                    continue
                statements_path = task_path + "/statements"
                statements = os.path.join(statements_path, os.listdir(statements_path)[0])
                assert os.path.exists(statements), f"Statements file not found: {statements}"

                graders = task_path + "/graders/"
                checkers = task_path + "/checkers/"
                subtasks = create_subtask_json_by_folder(task_path + "/subtasks")
                tests = task_path + "/tests/"
                assert len(os.listdir(tests)) > 0, f"Tests folder is empty: {tests}"

                zip_file = task_path + f"/attachments/{task}.zip"
                unzip_file(zip_file, task_path + "/attachments/")
                attachments = [task_path + "/attachments/cpp/", task_path + "/attachments/samples/","/attachments/examples/"]
                editorial_path = task_path + "/solutions/editorial/"
                editorial_file = os.path.join(editorial_path, os.listdir(editorial_path)[0])
                code_files = task_path + f"/solutions/Codes"
                assert len(os.listdir(code_files)) > 0, f"Code files folder is empty: {code_files}"

                problem_json = task_path + f"/problem.json"
                with open(problem_json, "r") as f:
                    problem_json = json.load(f)
                    new_problem_json = {
                        "task": problem_json['code'],
                        "time_limit": problem_json.get("time_limit", 10.01),
                        "memory_limit": problem_json.get("memory_limit"),
                        "task_type": problem_json.get("task_type")
                    }
                task_obj = Task(
                    name=task,
                    statements=statements,
                    graders=graders,
                    checkers=checkers,
                    subtasks=subtasks,
                    tests=tests,
                    attachments=attachments,
                    editorial_files=editorial_file,
                    code_files=code_files,
                    problem_json=new_problem_json
                )
                contest.add_task(task_obj, split=day)
        contest.write(self._restructure_path)
    def restructure(self, new_path):
        for year in range(2002, 2023):
            year = str(year)
            contest = Contest(year=year)
            for day in ["day0", "day1", "day2"]:
                path = os.path.join(self._path, year, day)
                if not os.path.exists(path):
                    continue
                for task in os.listdir(path):
                    task_path = os.path.join(path, task)
                    if not os.path.isdir(task_path):
                        continue
                    if year == "2024":
                        statements = [task_path + "/statements/en.pdf", task_path + "/translations/en.md"] + extract_image_files(task_path+"/translations/")
                        translations = task_path + "/translations/"
                        graders = task_path + f"/{task}/graders/"
                        subtasks = create_subtask_json_by_folder(task_path + f"/{task}/subtasks")
                        tests = task_path + f"/{task}/tests/"
                        attachments = task_path + f"/{task}/cpp/"
                        editorial_file = task_path + f"/{task}_editorial.pdf"
                        code_files = task_path + f"/{task}/solutions/"
                        problem_json = task_path + f"/{task}/problem.json"
                    elif year == "2023":
                        statements = [task_path + f"/{task}-md/{task}_ISC.md"] + extract_image_files(task_path + f"{task}-md/")
                        translations = None
                        graders = task_path + "/graders/"
                        subtasks = create_subtask_json_by_folder(task_path + "/subtasks")
                        tests = task_path + "/tests/"
                        attachments = [task_path + "/attachments/cpp", task_path + "/attachments/examples"]
                        editorial_file = None
                        code_files = task_path + "/solutions/" 
                        problem_json = task_path + "/problem.json"
                    with open(problem_json, "r") as f:
                        problem_json = json.load(f)
                        new_problem_json = {
                            "task": problem_json['code'],
                            "time_limit": problem_json.get("time_limit", 10.01),
                            "memory_limit": problem_json.get("memory_limit")/1024/1024,
                            "task_type": problem_json.get("task_type")
                        }
                    task_obj = Task(
                        name=task,
                        statements=statements,
                        translations=translations,
                        graders=graders,
                        subtasks=subtasks,
                        tests=tests,
                        attachments=attachments,
                        editorial_files=editorial_file,
                        code_files=code_files,
                        problem_json=new_problem_json
                    )
                    contest.add_task(task_obj, split=day)
            contest.write(new_path)
    def parse(self):
        pass

if __name__ == "__main__":
    crawler = IOICrawler(competition="IOI", crawl_path=f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-Processed", restructure_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Restructured/IOI", parse_path=f"{os.environ['HOME_DIR']}/IOI-Bench-Parsed/IOI")
    #crawler.restructure_year(year="2019")
    #crawler.restructure_2020(year="2017")
    crawler.restructure_2020(year="2018")