import os
import shutil
from typing import List, Optional, Union
import json

class Task:
    """
    Represents a single task in a contest.
    Each Task is responsible for creating its own directory structure:
        ├── statements/ (required)
        ├── translations/ (optional)
        ├── graders/ (optional)
        ├── checkers/ (optional)
        ├── tests/ (required)
        ├── attachments/ (optional)
        └── solutions/
            ├── Codes/
                |── correct (required)
                |── incorrect (optional)
                ├── time_limit (optional)
                ├── runtime_error (optional)
            └── editorial.raw_format
            └── editorial.md (if needed)
        ├── subtasks.json ({"0":{"task": "sample", "score": 0, "tests": ["test1", "test2"],"1": :{"task": "", "score": 10, "tests": ["test1", "test2"]}})
        └── problem.json ({"task": "SampleTask", "time_limit": 2, "memory_limit": 1024MB...., "task_type":"Batch"})
    """

    def __init__(self,
                 name: str,
                 statements: Optional[Union[str, List[str]]] = None,
                 translations: Optional[str] = None,
                 graders: Optional[Union[str, List[str]]] = None,
                 subtasks: Optional[str] = None,
                 tests: Optional[str] = None,
                 attachments: Optional[str] = None,
                 editorial_files: Optional[str] = None,
                 code_files: Optional[List[str]] = None,
                 problem_json: Optional[str] = None,
                 checkers: Optional[Union[str, List[str]]] = None):
        """
        :param name: Name of the task (used as the folder name).
        :param statements: Path to the statement files (can be multiple files).
        :param translations: Path to translation files (optional).
        :param graders: Path to grader file(s) or folder (can be empty).
        :param subtasks: a json files containing subtasks info (required).
        :param tests: Path to a folder containing tests (required).
        :param attachments: Path to a folder or files for attachments (optional).
        :param editorial_file: Path to the editorial files.
        :param code_files: List of solution code files (e.g., .cpp, .py, etc.).
        :param problem_json: problem.json file.
        """
        self.name = name
        self.statements = statements
        self.translations = translations
        self.graders = graders
        self.subtasks = subtasks
        self.tests = tests
        self.attachments = attachments
        self.editorial_files = editorial_files
        self.code_files = code_files or []
        self.problem_json = problem_json
        self.checkers = checkers

    def _copy_file_or_folder(self, src: str, dst: str) -> None:
        """
        Helper method to copy a file or folder from src to dst.
        """
        if not src:
            return
        if not os.path.exists(src):
            print(f"Warning: Source {src} does not exist. Skipping.")
            return

        if os.path.isfile(src):
            shutil.copy2(src, dst)
        else:
            # src is a directory
            shutil.copytree(src, dst, dirs_exist_ok=True)
    def _copy_tests(self, src_folder, test_folder):
        """
        Copy test files from the source folder to the test folder.
        """
        if os.path.exists(test_folder):
            shutil.rmtree(test_folder)
        os.makedirs(test_folder, exist_ok=True)
        for root, _, files in os.walk(src_folder):
            for file in files:
                if os.path.isfile(os.path.join(root, file)):
                    splits  = file.split('.')
                    new_file = file
                    if len(splits) < 2:
                        new_file = file + ".in"
                    elif splits[-1] in ['a', "ans", "output", "sol", "ok"]:
                        splits[-1] = "out"
                        new_file = ".".join(splits)
                    elif splits[0] in ["input", "output"]:
                        splits[0] = "in" if splits[0] == "input" else "out"
                        new_file = ".".join(splits[1:]) + "." + splits[0] 
                    src_path = os.path.join(root, file)
                    dest_path = os.path.join(test_folder, new_file)
                    shutil.copy(src_path, dest_path)
        print(f"Copied tests from {src_folder} to {test_folder}")
    def write(self, base_path: str) -> None:
        """
        Create the task folder structure under base_path/<task_name>,
        and write/copy all relevant files/folders.
        """
        task_root = os.path.join(base_path, self.name)
        os.makedirs(task_root, exist_ok=True)

        # 1. statements
        statements_dir = os.path.join(task_root, "statements")
        os.makedirs(statements_dir, exist_ok=True)
        for statement_file in (self.statements if isinstance(self.statements, list) else [self.statements]):
            if os.path.isfile(statement_file):
                #if the file is not pdf, tex, md, or txt, keep the original name
                if statement_file.split('.')[-1] not in ["pdf", "tex", "md", "txt"]:
                    self._copy_file_or_folder(statement_file, statements_dir)
                else:
                    self._copy_file_or_folder(statement_file,
                                            os.path.join(statements_dir, "statement.{}".format(statement_file.split('.')[-1])))
            else:
                self._copy_file_or_folder(statement_file, statements_dir+"/"+os.path.basename(statement_file))
        # If you also have .md or images to copy, handle them here similarly.

        # 2. graders
        graders_dir = os.path.join(task_root, "graders")
        os.makedirs(graders_dir, exist_ok=True)
        if self.graders:
            # graders can be a single file or a folder or list
            if isinstance(self.graders, list):
                for grader_path in self.graders:
                    self._copy_file_or_folder(grader_path, graders_dir)
            else:
                self._copy_file_or_folder(self.graders, graders_dir)

        # 3. subtasks
        if self.subtasks:
            subtasks_dir = os.path.join(task_root, "subtasks.json")
            with open(subtasks_dir, 'w') as f:
                json.dump(self.subtasks, f)

        # 4. tests
        tests_dir = os.path.join(task_root, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        if self.tests:
            #check the suffixes of test files in the folder
            test_files = os.listdir(self.tests)
            in_suffix = False
            out_suffix = False
            rename_test = True
            for test_file in test_files:
                if test_file.endswith(".in"):
                    in_suffix = True
                if test_file.endswith(".out"):
                    out_suffix = True
                if in_suffix and out_suffix:
                    rename_test = False
                else:
                    rename_test = True
                    break
            if rename_test:
                self._copy_tests(self.tests, tests_dir)
            else:
                self._copy_file_or_folder(self.tests, tests_dir)

        # 5. attachments
        attachments_dir = os.path.join(task_root, "attachments")
        os.makedirs(attachments_dir, exist_ok=True)
        if self.attachments:
            for attachment in (self.attachments if isinstance(self.attachments, list) else [self.attachments]):
                self._copy_file_or_folder(attachment, attachments_dir)

        # 6. solutions
        solutions_dir = os.path.join(task_root, "solutions")
        os.makedirs(solutions_dir, exist_ok=True)

        # Editorial PDF (with preprocessing)
        if self.editorial_files:
            for editorial_file in (self.editorial_files if isinstance(self.editorial_files, list) else [self.editorial_files]):
                self._copy_file_or_folder(editorial_file,
                                          os.path.join(solutions_dir, f"editorial.{editorial_file.split('.')[-1]}"))

        # Codes folder
        codes_dir = os.path.join(solutions_dir, "codes")
        os.makedirs(codes_dir, exist_ok=True)
        #check if code_files is a list
        if isinstance(self.code_files, str):
            self.code_files = [self.code_files]
        for code_file in self.code_files:
            self._copy_file_or_folder(code_file, codes_dir)

        # 7. problem.json
        if self.problem_json:
            with open(os.path.join(task_root, "problem.json"), 'w') as f:
                json.dump(self.problem_json, f)

        # 8. translations
        if self.translations:
            self._copy_file_or_folder(self.translations, os.path.join(task_root, "translations"))
        
        # 9. checkers
        if self.checkers:
            checkers_dir = os.path.join(task_root, "checkers")
            os.makedirs(checkers_dir, exist_ok=True)
            if isinstance(self.checkers, list):
                for checker_path in self.checkers:
                    self._copy_file_or_folder(checker_path, checkers_dir)
            else:
                self._copy_file_or_folder(self.checkers, checkers_dir)
        
        print(f"[INFO] Task '{self.name}' structure created at {task_root}")


class Contest:
    """
    Represents a programming contest, which may optionally be split by days,
    and contains multiple tasks plus a result file.
    Each Contest is responsible for creating its own directory structure:
        ├── <year>/
        │   ├── <contest_name>/
        │   │   ├── <task_name>/
        │   │   ├── results/
        │   │   └── meta_info.json (date: "YYYY-MM", "practice":[""], "day1":["task"], "day2":["task"]) )
    """

    def __init__(self,
                 name: str = "contest",
                 tasks: Optional[List[Task]] = None,
                 result_file: Optional[str] = None,
                 year: Optional[int] = None,
                 month: Optional[int] = None,):
        """
        :param name: Name of the contest (e.g., "Contest2025").
        :param tasks: A list of Task objects.
        :param result_file: Path to the results file, if any.
        :param day: Optional day name (e.g., "Day1"), if splitting by days.
        """
        self.name = name
        self.tasks = tasks or []
        self.result_file = result_file
        self.year = year
        self.meta_info = {}
    def add_task(self, task: Task, split=None) -> None:
        """
        Add a task to the contest.
        :param task: A Task object to add.
        """
        self.tasks.append(task)
        if not split:
            split = "contest"
        if split not in self.meta_info:
            self.meta_info[split] = []
        self.meta_info[split].append(task.name)
    def write(self, base_path: str) -> None:
        """
        Create the contest folder structure under base_path/<contest_name>,
        optionally with a <day> subfolder, then write tasks and result file.
        """
        if self.year:
            base_path = os.path.join(base_path, str(self.year))
        # Create the base contest directory
        os.makedirs(base_path, exist_ok=True)
        contest_root = os.path.join(base_path, self.name)
        os.makedirs(contest_root, exist_ok=True)

        # Write tasks
        for task in self.tasks:
            task.write(contest_root)

        # Copy contest result file if provided
        results_dir = os.path.join(contest_root, "results")
        os.makedirs(results_dir, exist_ok=True)  # 确保 results/ 目录存在

        if isinstance(self.result_file, list):
            for result_file in self.result_file:
                if os.path.exists(result_file):
                    shutil.copy2(result_file, results_dir)
                else:
                    print(f"Warning: result_file {result_file} does not exist. Skipping.")
        elif self.result_file and os.path.exists(self.result_file):
            shutil.copy2(self.result_file, results_dir)
        elif self.result_file:
            print(f"Warning: result_file {self.result_file} does not exist. Skipping.")
        with open(os.path.join(contest_root, "meta_info.json"), 'w') as f:
            json.dump(self.meta_info, f, indent=4)
        print(f"[INFO] Contest '{self.name}' structure created at {contest_root}")


if __name__ == "__main__":
    # Example usage:

    # Create a Task
    task1 = Task(
        name="SampleTask",
        statement_pdf="path/to/statement.pdf",
        graders="path/to/graders_folder",
        subtasks="path/to/subtasks_folder",
        tests="path/to/tests_folder",
        attachments=None,  # or "path/to/attachments_folder"
        editorial_pdf="path/to/editorial.pdf",
        code_files=["path/to/solution1.cpp", "path/to/solution2.py"]
    )

    # Create a Contest with one task and an optional result file
    contest = Contest(
        name="SampleContest",
        tasks=[task1],
        result_file="path/to/results.txt",
    )

    # Write everything to a base path, e.g., "./output"
    base_output_path = "./output"
    contest.add(task1, split='day1')
    contest.write(base_output_path)
