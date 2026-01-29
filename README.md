# LiveOIBench Crawler

This repository contains scripts to crawl and parse problems from various Informatics Olympiad contests. The contests to be crawled and their metadata are listed in the provided CSV file.

## Environment Variables

Before running any scripts, export the following environment variables:

```bash
export HOME_DIR="/path/to/your/data/directory"
export CSES_USERNAME="your_cses_username"
export CSES_PASSWORD="your_cses_password"
export LOJ_USERNAME="your_loj_username"
export LOJ_PASSWORD="your_loj_password"
```

- `HOME_DIR`: Base directory for all crawled/restructured/parsed data.
- `CSES_USERNAME` / `CSES_PASSWORD`: Credentials for the CSES scraper.
- `LOJ_USERNAME` / `LOJ_PASSWORD`: Credentials for the LOJ scraper.

## Getting Started

To add support for crawling a new contest, follow these steps:

### 1. Extend the Base Crawler Class

Create a new crawler class by extending the base crawler (`BaseCrawler`) and implement the following methods:

- **`crawl()`**

  This method retrieves problems from the contest website. As contest formats may vary across different years, the recommended workflow is:

  - Fetch the target webpage.
  - Use ChatGPT to extract downloadable links automatically.

- **`restructure()`**

  Organizes downloaded files into the standardized directory structure shown below:

  ```
  <year>/
  ├── <contest_name>/
  │   ├── <task_name>/
  │   │   ├── statements/           # Required
  │   │   ├── translations/         # Optional
  │   │   ├── graders/              # Optional
  │   │   ├── tests/                # Required
  │   │   ├── attachments/          # Optional
  │   │   ├── solutions/
  │   │   │   ├── Codes/
  │   │   │   │   ├── correct/           # Required
  │   │   │   │   ├── incorrect/         # Optional
  │   │   │   │   ├── time_limit/        # Optional
  │   │   │   │   └── runtime_error/     # Optional
  │   │   │   ├── editorial.raw_format
  │   │   │   └── editorial.md           # Optional, as needed
  │   │   ├── subtasks.json
  │   │   └── problem.json
  │   ├── results
  │   │       ├── result.csv
  │   └── meta_info.json             # Contains date ("YYYY-MM") and task info
  ```

  Utilize the provided classes `Contest` and `Task` from `contest.py` to facilitate this process. Even for the same competition, the folder structure will be different across years. You may have to write a function for each contest if they don't share the same structure.
  
  **`problem.json`**
  ```
  {
    "task": "{task_name}",
    "time_limit": x.xx, (seconds)
    "memory_limit": xxx, (MB)
    "task_type": "Batch", "Interactive", "Communication", or, "Output_only",
  }
  ```
  **`subtasks.json`**
  ```
  {
    "0": {"score":0, "testcases": ["0-01"], "task": "Subtask 0"},
    "1": {"score": 30, "testcases": ["1-01", "1-02", "1-03", "1-04", "1-05"], "task": "Subtask 1"},
    "2": {"score": 70, "testcases": ["2-01", "2-02", "2-03", "2-04", "2-05", "2-06", "2-07", "2-08", "2-09", "2-10", "2-11"], "task": "Subtask 2"},
  }
  ```
  This subtasks.json file means that there are two subtasks for this problem Subtask 1 (30 points) and Subtask 2 (70 points). Usually, Subtask 0 is the sample input and output. A solution will score 30 points if it passes all the test cases assocated with Subtask 1. Similarly, if it passes all the test cases in Subtasks 2, it will score 70 points. 
  
  Its test folder should look something like this:
  ```
  0-01.in
  0-01.out
  1-01.in
  1-02.out
  ...
  ```
  Base on the task type, the test folder may look differently. The interactive tasks sometimes will only have the input files. In utils.py, there are some helper functions to convert different types of subtasks and tests folder into subtasks.json. You may need to write your own functions to create your own subtasks.json.  
- **`parse()`**

  Converts problem statements and solutions (PDF/HTML/...) into Markdown format. At present, PDF parsing via marker_converter is supported. However, we are still exploring different ways we can parse. The marker_converter can be connected to Gemini-2.0-Flash (up to 1500 free requests/day), you need to provide a Google API Key to the converter.

## Implementation Details

- Refer to scripts located in the `src` folder for examples of crawling and restructuring tasks.
- Utility functions are available in `utils.py`. Feel free to add new functions here.
- Do not modify existing functions in `contest.py` and `utils.py`, as they are shared across different crawlers. If you have suggestions for improvements or changes, please open an issue.


