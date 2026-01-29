# Competitive Framing Crawler

A Python-based system for processing competitive programming results and enriching them with Codeforces rating data.

## Overview

This project processes competition results from various programming competitions (IOI, ICPC, COCI, NOI, OOI), matches contestants with their Codeforces profiles, retrieves their rating history, and enriches the results with this data.

## Prerequisites

- Python 3.x
- pandas
- requests
- beautifulsoup4 (bs4)
- googlesearch-python
- google-genai
- python-dotenv

Note: For anonymized submissions, the included `database.csv` contains only synthetic placeholder rows.
Generate a real database locally with `python main.py setup` and then run the pipeline to populate it.

## Installation

1. Install dependencies:
```bash
pip install pandas requests beautifulsoup4 googlesearch-python google-genai python-dotenv
```
 
GOOGLE_API_KEY=your_gemini_api_key
```

3. Create a `Results/` directory with competition CSV files organized as:
```
Results/
├── IOI/
│   ├── 2024/
│   │   └── results.csv
│   └── 2023/
│       └── results.csv
├── ICPC/
│   └── 2024/
│       └── results.csv
└── [other competitions]/
```

Each CSV file should contain at minimum:
- `Contestant`: Contestant name
- `Country`: Country name

## Quick Start

Run the complete pipeline:
```bash
./main.bash
```

Or run each step individually (see below).

## Detailed Usage

### Step 1: Initialize Data Processing (util.py)

```bash
python util.py
```

**What it does:**
- Validates and fixes the Results directory structure
- Standardizes country names across all result files
- Cleans and renames columns (removes unwanted columns, standardizes medal columns)
- Creates backups of original files

**Output:**
- Cleaned and standardized CSV files in Results directory
- Backup files with `.backup_clean` extension

---

### Step 2: Add Competition to Database (main.py)

```bash
python main.py Results/IOI/2024/results.csv
```

**What it does:**
- Adds a competition's contestants to the existing database
- For each contestant in the CSV file:
  1. Searches CPHOF database for Codeforces profile
  2. Retrieves Codeforces username
  3. Fetches rating history (2022-2025)
  4. Adds/updates contestant entry in database.csv
  5. Records the competition in their competitions list

**Parameters:**
- Competition CSV file path (e.g., `Results/IOI/2024/results.csv`)

**Output:**
- Updated `database.csv` with new contestants and competition data

**Prerequisites:**
- Must have `database.csv` already created
- If no database exists, use command `python main.py setup` to create a new one (see main.py for details)
- Requires valid competition CSV file with `Contestant` and `Country` columns

---

### Step 3: Copy Results to Sample Directory (copy_results.py)

```bash
python copy_results.py Results/Competition_Name/Year/results.csv
```

**What it does:**
- Copies competition result files to `Results_sample/` directory
- Preserves the original directory structure:
  - `Results/IOI/2024/results.csv` → `Results_sample/IOI/2024/results.csv`

**Parameters:**
- Path to source results CSV file

**Output:**
- Copied files in `Results_sample/` with identical directory hierarchy

---

### Step 4: Enrich Results with Ratings (rating_to_result.py)

```bash
python rating_to_result.py
```

**What it does:**
- Processes all CSV files in `Results_sample/` directory
- Matches contestants with database entries
- Appends Codeforces rating columns:
  - `CF_Rating`: Most recent Codeforces rating
  - `Codeforces_rating_2025`, `2024`, `2023`, `2022`: Yearly max ratings
- Maintains original result data

**Output:**
- Updated CSV files in `Results_sample/` with rating columns added

---

### Step 5: Filter and Analyze Results (filter_results.py)

```bash
python filter_results.py
```

**What it does:**
- Filters results by rating thresholds (CF_Rating >= 500)
- Removes statistical outliers using auto-detection
- Generates visualization plots for ranked humans
- Validates data quality and count statistics

**Output:**
- Filtered CSV files in Results_sample
- PNG plot files showing human ranking distributions

---

## Database Schema

`database.csv` contains:

| Column | Type | Description |
|--------|------|-------------|
| `name` | string | Contestant name |
| `country` | string | Country of origin |
| `codeforces_id` | string | Codeforces username |
| `competitions` | list | List of competitions entered |
| `Codeforces_rating_2025` | int | Max rating in 2025 (-1000 if not found) |
| `Codeforces_rating_2024` | int | Max rating in 2024 |
| `Codeforces_rating_2023` | int | Max rating in 2023 |
| `Codeforces_rating_2022` | int | Max rating in 2022 |
| `search_confidence_percent` | float | Match confidence percentage |

## Pipeline Flow

```
Results/                           (Raw competition results)
    ↓
util.py                            (Standardize & clean)
    ↓
Results/                           (Cleaned results)
    ↓
main.py                            (Build database from IOI 2024)
    ↓
database.csv                       (Contestant + Codeforces data)
    ↓
copy_results.py                    (Copy to sample directory)
    ↓
Results_sample/                    (Sample data for enrichment)
    ↓
rating_to_result.py                (Add Codeforces ratings)
    ↓
Results_sample/                    (Results + ratings)
    ↓
filter_results.py                  (Filter & analyze)
    ↓
Results_sample/ + plots            (Final filtered results + visualizations)
```

## Error Handling

- **Missing files:** Scripts will exit with error messages if required files don't exist
- **API limits:** Rate limiting is built into Google searches
- **Invalid data:** Warnings are printed but processing continues
- **Database conflicts:** main.py will not overwrite existing database.csv

## Performance Notes

- Initial database creation (main.py) requires API calls and may take 5-10 minutes per 100 contestants
- Copy operations are fast (< 1 minute for typical datasets)
- Rating enrichment processes files in parallel where possible
- Filter operations are memory-efficient even for large datasets

## Troubleshooting

**"Database already exists" error:**
- Delete `database.csv` if you want to reinitialize
- Or add new competitions with different paths

**No matches found for contestants:**
- Check if country names are standardized (run util.py first)
- Verify CPHOF and Codeforces have profiles for the contestants
- Check internet connection for API access

**Missing ratings:**
- Contestant may not have Codeforces profile or competed in specified years
- Ratings show -1000 when data unavailable
