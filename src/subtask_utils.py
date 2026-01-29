import json
import os
import re
import shutil
from utils import *

def create_subtask_json_by_folder(folder):
    """
    Create a JSON structure for subtasks based on the folder structure.
    Each subfolder represents a task, and each file within it is a subtask.

    Warning: This function assumes that the folder structure is consistent and
    that each subfolder contains JSON files representing subtasks. No score information

    Example folder structure:
    ├── Group1
    │   ├── test1.in
    │   ├── test1.out
    │   ├── test2.in
    │── Group2
    │   ├── test1.in
    ....
    """
    subtasks = {}
    for i, subtask_file in enumerate(sorted(os.listdir(folder))):
        subtask_path = os.path.join(folder, subtask_file)
        with open(subtask_path, 'r') as f:
            subtask_data = json.load(f)
        subtask_data['task'] = subtask_file.replace(".json", "")
        subtasks[i] = subtask_data
    return subtasks

def create_subtask_json_kattis(folder):
    """
    Create a JSON structure for subtasks in Kattis-style test folder organization.
    
    The function expects a sample tests folder named "sample" and a secret tests folder.
    It builds a subtasks dictionary where key "0" holds sample tests and subsequent keys correspond
    to groups found in the secret folder.
    
    Returns:
        dict: A dictionary where each key maps to a subtask with its score (default -1) and list of testcase identifiers.

    Example folder structure:
    ├── data
    │   ├── sample
    │   ├── secret
    │       ├── group1
    │       │   ├── test1.in
    │       │   ├── test1.out
    │       │   ...
    │       │   ├── testdata.yaml
    │       ├── group2
    │       ...
    │       ├── testdata.yaml
    """
    def handle_group(group_folder):
        group_name = os.path.basename(group_folder)
        subtask = {"task": group_name}
        tasks_files = set()
        test_files = os.listdir(group_folder)
        if len(test_files) == 2 and group_name != "sample":
            test_files = os.listdir(os.path.join(group_folder, group_name))
        for test_file in test_files:
            if test_file == "testdata.yaml":
                with open(os.path.join(group_folder, test_file), 'r') as f:
                    text = f.read()
                match = re.search(r'accept_score:\s*(\d+)', text)
                if match:
                    subtask["score"] = int(match.group(1))
                else:
                    subtask["score"] = -1
            else:
                tasks_files.add(test_file.split(".")[0])
        tasks_files = list(tasks_files)
        tasks_files.sort()
        subtask["testcases"] = tasks_files
        return subtask
    subtasks = {}
    subtasks[0] = handle_group(folder+"/sample")
    group_number = 1
    for group in os.listdir(folder+"/secret"):
        group_folder = os.path.join(folder, "secret", group)
        if not os.path.isdir(group_folder) or group == "combined_tests":
            continue
        group_number = int(group.strip("group"))
        subtasks[group_number] = handle_group(group_folder)
    return subtasks

def convert_cases_by_hash(hash_folder, dest_folder):
    case_folders = [f for f in os.listdir(hash_folder) if os.path.isdir(os.path.join(hash_folder, f))]
    test_folder = os.path.join(dest_folder, "tests")
    os.makedirs(test_folder, exist_ok=True)
    for case_folder in case_folders:
        case_path = os.path.join(hash_folder, case_folder)
        case_files = [f for f in os.listdir(case_path) if os.path.isfile(os.path.join(case_path, f))]
        for case_file in case_files:
            suffix = "in" if "in" in case_file else "out"
            case_file_path = os.path.join(case_path, case_file)
            dest_file = os.path.join(case_file_path, test_folder + f"/{case_folder}.{suffix}")
            shutil.copy(case_file_path, dest_file)
def create_subtasks_by_hash(subtasks_folder):
    """
    Create subtasks based on a folder structure where each subfolder represents a subtask
    and is named based on a hash value.
    
    Scans through the subtasks_folder and returns a dictionary with each subtask's details.
    
    Returns:
        dict: A dictionary mapping subtask folder names to a dictionary with keys:
              "score" (default -1), "testcases" (list of test identifiers), and "task" (subtask name).

    Example folder structure:
    ├── cases_by_hash
    │   ├── 12345678
    │   │   ├── in.txt
    │   │   ├── out.txt
    ├── subtasks
    │   ├── subtask1
    │   ├── subtask2
    │   ...
    """
    subtasks = {}
    for subtask_folder in os.listdir(subtasks_folder):
        subtask_path = os.path.join(subtasks_folder, subtask_folder)
        for group in os.listdir(subtask_path):
            group_path = os.path.join(subtask_path, group)
            subtask = {"task": subtask_folder+"_"+group, 'testcases': [], 'score': -1}
            for cases in os.listdir(group_path):
                case_path = os.path.join(group_path, cases)
                with open(case_path, 'r') as f:
                    path = f.read()
                subtask['testcases'].append(os.path.basename(path))
            name = subtask_folder.split("_")[1] + "_" + group.split("_")[1]
            subtasks[name] = subtask
    return subtasks

def extract_codeforce_problem_details(xml_file_path):
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
def create_subtasks_by_files(test_files, individual=False):
        subtasks = {}
        for test_file in test_files:
            if test_file.endswith(".in"):
                task_name = test_file.split(".")[0]
                if individual:
                    number = task_name
                else:
                    number = task_name.split("-")[0]
                number = task_name.split("-")[0]
                if number == "sample":
                    number = 0
                else:
                    number = int(number)
                subtask_name = f"subtask{number}"
                if str(number) not in subtasks:
                    subtasks[str(number)] = {"score": -1, "testcases": [], "task": subtask_name}
                subtasks[str(number)]["testcases"].append(test_file.replace(".in", ""))
        return subtasks
def create_subtasks_with_no_subtasks(test_files):
    """
    Create subtasks from test files without subtask folders.
    
    Args:
        test_files (list): List of test file names.
        
    Returns:
        dict: A dictionary mapping subtask numbers to a dictionary with keys:
              "score" (default -1), "testcases" (list of test identifiers), and "task" (subtask name).
    """
    subtasks = {}
    for test_file in test_files:
        if test_file.endswith(".in"):
            task_name = test_file.split(".")[0]
            number = task_name.split("-")[0]
            if number == "sample":
                number = 0
            else:
                number = 1
            if str(number) not in subtasks:
                if number == 0:
                    subtasks[str(number)] = {"score": 0, "testcases": [], "task": "sample"}
                else:
                    subtasks[str(number)] = {"score": 100, "testcases": [], "task": "main"}
            subtasks[str(number)]["testcases"].append(test_file.replace(".in", ""))
    return subtasks