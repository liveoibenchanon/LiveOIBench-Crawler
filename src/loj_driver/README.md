# LOJ File Downloader - README

## Introduction

This tool is designed to fetch and download problem files, submissions, and other content from the LibreOJ (LOJ) online judge platform. It provides a robust and flexible way to archive problem test data, submissions, and problem statements.

## Requirements

- Python 3.7+
- Chrome browser installed
- Internet connection
- Required Python packages: selenium, beautifulsoup4, requests

## Installation

1. Clone or download this repository

2. Install required dependencies:
```bash
pip install selenium beautifulsoup4 requests
```

3. Make sure you have Chrome browser installed on your system

## Usage

### Basic Command Structure

```bash
python chrome_driver.py --type TYPE --ids ID [ID...] [OPTIONS]
```

or

```bash
python chrome_driver.py --type TYPE --file ID_FILE [OPTIONS]
```

### Required Arguments

- `--type` or `-t`: Content type to fetch
  - `problem-files`: Downloads test data and additional files
  - `problem`: Downloads problem statements
  - `submission`: Downloads submission code and results

- `--ids` or `-i`: One or more IDs to process
  - Example: `--ids 2813 2814 2815`
  
OR

- `--file` or `-f`: Path to a file containing IDs (one per line)
  - Example: `--file problem_ids.txt`

### Optional Arguments

- `--output-dir` or `-o`: Directory for saving output (default: 'rendered_output')
- `--workers` or `-w`: Number of parallel downloads (default: 2)
- `--wait`: Time to wait after page load in seconds (default: 5)
- `--download-files`: Enable downloading problem files (for `problem-files` type)
- `--no-headless`: Show browser window during execution

### Examples

1. Download test data for a single problem:
```bash
python chrome_driver.py --type problem-files --ids 2813 --download-files
```

2. Download multiple problems from a list:
```bash
python chrome_driver.py --type problem-files --file my_problems.txt --download-files
```

3. Fetch submissions with visible browser:
```bash
python chrome_driver.py --type submission --ids 123456 789012 --no-headless
```

4. Download problem statements only:
```bash
python chrome_driver.py --type problem --ids 1001 1002 1003 --output-dir loj_archive
```

## Output Structure

### For Problem Files

```
output_dir/problem-files/
└── problem_XXXX/
    ├── page.html           # HTML of the problem files page
    ├── download.log        # Detailed log of the download process
    └── files/
        └── TestData_#XXXX.zip  # ZIP archive containing all test data
```

### For Submissions

```
output_dir/submission/
└── submission_XXXX.html    # HTML of the submission page
```

### For Problems

```
output_dir/problem/
└── problem_XXXX.html       # HTML of the problem statement page
```

## Log File

Each problem download includes a detailed download.log file that contains:

- Start and completion timestamps
- URL of the problem
- Download directory location
- File counts for test data and additional files
- List of downloaded files with sizes
- Any errors encountered during downloading

## Tips and Troubleshooting

1. **For large files**: Increase the `--wait` time to allow for longer downloads

2. **If downloads fail**: Try with `--no-headless` flag to see what's happening

3. **For rate limiting**: Reduce the number of `--workers` to avoid overloading the server

4. **Common issues**:
   - If you see "No downloads detected", check your internet connection
   - If the script times out, try increasing the wait time
   - For authentication issues, you may need to log in manually first

## File Format for ID Lists

Create a text file with one ID per line:
```
# IOI problems
1001
1002

# Regional problems
2813
2814
```
Comments (lines starting with #) and empty lines are ignored.

---

## Processing Submission Files

After downloading submissions, you can extract problem details, solution code, and results using the `extract_subtasks.py` script.

### Usage

```bash
python extract_subtasks.py [OPTIONS]
```

### Options

- `--submission_id`: Process a single submission ID
  - Example: `--submission_id 123456`

- `--file` or `-f`: Path to a file containing submission IDs (one per line)
  - Example: `--file submission_ids.txt`
  
- `--output-dir` or `-o`: Directory containing submission HTML files (default: "rendered_submissions")
  - Example: `--output-dir my_submissions`

### Examples

1. Process a single submission:
```bash
python extract_subtasks.py --submission_id 123456
```

2. Process multiple submissions from a file:
```bash
python extract_subtasks.py --file submission_ids.txt
```

3. Process all submissions in a custom directory:
```bash
python extract_subtasks.py --output-dir my_custom_submissions_folder
```

### File Format for submission_ids.txt

Create a text file with one submission ID per line:
```
# IOI submissions
123456
789012

# Regional submissions
345678
901234
```
Comments (lines starting with #) and empty lines are ignored.

### Output Structure

For each submission, the script creates a directory in data named after the problem:

```
data/problem_name/
├── solution.cpp          # Solution code with metadata header
├── result.json           # Submission results (score, time, memory)
├── subtasks.json         # Subtask definitions and test cases
├── sample0.in            # Sample input files
└── sample0.out           # Sample output files
```


