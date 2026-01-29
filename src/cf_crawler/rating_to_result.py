"""
Utility for enriching competition results with Codeforces rating data.

This module matches contestants in competition result files with their Codeforces
rating data from the database, then appends the ratings to result files.

Main Functions:
- safe_literal_eval(): Safely parse competition list strings
- extract_competition_info(): Extract competition name and year from file path
- get_rating(): Look up contestant rating in database
- process_results_files(): Main function to update all result files with ratings

Usage:
    python rating_to_result.py  # Updates Results_sample with Codeforces ratings
"""

import pandas as pd
import os
import ast
import re

def safe_literal_eval(val):
    """Parse competition list strings safely, returning empty list on failure."""
    if isinstance(val, str):
        try:
            # Validate format before parsing (safety check)
            if val.strip().startswith('[') and val.strip().endswith(']'):
                return ast.literal_eval(val)
            else:
                print(f"Warning: Skipping potentially unsafe eval for value: {val}")
                return []
        except (ValueError, SyntaxError, TypeError) as e:
            print(f"Warning: Could not parse competitions list '{val}'. Error: {e}")
            return []
    elif isinstance(val, list):
        return val
    else:
        print(f"Warning: Unexpected type for competitions: {type(val)}")
        return []

def extract_competition_info(file_path, results_root):
    """
    Extract competition name and year from Results directory file path.
    
    Path format: Results/Competition/Year/[Stage]/results.csv
    Returns: (competition_key, year) or (None, None) if parsing fails
    """
    try:
        relative_path = os.path.relpath(file_path, results_root)
        path_parts = relative_path.split(os.sep)
        
        # Expecting structure like Competition/Year/[Stage]/results.csv
        if len(path_parts) < 3 or path_parts[-1] != 'results.csv':
            print(f"Warning: Unexpected path structure, cannot extract info: {file_path}")
            return None, None

        # Find the year (assuming it's a 4-digit number)
        year = None
        year_index = -1
        for i, part in enumerate(path_parts):
            if re.fullmatch(r'\d{4}', part):
                year = int(part)
                year_index = i
                break
        
        if year is None:
            print(f"Warning: Could not extract year from path: {file_path}")
            return None, None

        # Competition components are before the year, stage components are after year but before results.csv
        competition_name_parts = path_parts[:year_index]
        stage_parts = path_parts[year_index+1:-1] # Parts between year and results.csv

        competition_key_parts = competition_name_parts + [str(year)] + stage_parts
        competition_key = ' '.join(competition_key_parts)
        
        return competition_key, year

    except Exception as e:
        print(f"Error extracting competition info from path {file_path}: {e}")
        return None, None

def get_rating(row, db_df, competition_key, db_rating_col):
    """
    Look up a contestant's Codeforces rating from database.
    
    Matching strategy:
    - JOI/TOKI: Match by name or Codeforces handle
    - Others: Match by name+country or Codeforces handle
    
    Args:
        row: Result row with Contestant_norm, Country_norm
        db_df: Database with name_norm, country_norm, competitions_list
        competition_key: Competition identifier to search for
        db_rating_col: Column name for the rating year
        
    Returns:
        Rating value or None if no match found
    """
    contestant = row['Contestant_norm']
    country = row['Country_norm']

    # Determine matching strategy based on competition type
    is_joi_or_toki = competition_key.startswith("JOI ") or competition_key.startswith("TOKI ")
    
    # Prepare matching masks: name, country, and Codeforces handle
    contestant_cf_candidate = str(row.get('Contestant', '')).strip().lower()
    
    name_mask = db_df['name_norm'] == contestant
    cf_mask = db_df['codeforces_id'].astype(str).str.lower() == contestant_cf_candidate

    if is_joi_or_toki:
        mask = name_mask | cf_mask  # Name or Codeforces handle
    else:
        mask = (name_mask & (db_df['country_norm'] == country)) | cf_mask  # Name+country or handle
    
    match_candidates = db_df[mask]
    
    # Build competition prefix for flexible matching (handles stage variations like "JOI 2024 JOI_honsen")
    try:
        year_match = re.search(r"\b(\d{4})\b", competition_key)
        comp_year_prefix = None
        if year_match:
            year_str = year_match.group(1)
            comp_base = competition_key.split(year_str)[0].strip()
            comp_year_prefix = f"{comp_base} {year_str}"
    except Exception:
        comp_year_prefix = None

    for _, db_row in match_candidates.iterrows():
        comps = db_row.get('competitions_list') or []
        # Normalize list entries to strings for safe comparison
        comps_str = [str(c) for c in comps]

        if competition_key in comps_str:
            return db_row.get(db_rating_col)

        if comp_year_prefix:
            for entry in comps_str:
                if entry.startswith(comp_year_prefix):
                    return db_row.get(db_rating_col)

    # No matching entry found with the specific competition
    # print(f"No matching DB entry found for '{contestant}' participating in '{competition_key}'.")
    return None

def process_results_files(results_dir="Results_sample", db_path="database.csv"):
    """
    Main function: Update all result files with Codeforces ratings.
    
    Walks through results_dir, matches contestants with database entries,
    and adds a CF_Rating column with their rating for that competition year.
    
    Args:
        results_dir: Directory containing result files (default: "Results_sample")
        db_path: Path to database CSV (default: "database.csv")
    """
    # Load database from CSV
    try:
        db_df = pd.read_csv(db_path)
        print(f"Database loaded successfully from {db_path}")
    except FileNotFoundError:
        print(f"Error: Database file not found at {db_path}")
        return
    except Exception as e:
        print(f"Error loading database {db_path}: {e}")
        return
    
    # Validate required columns
    required_db_cols = ['name', 'country', 'competitions']
    if not all(col in db_df.columns for col in required_db_cols):
        print(f"Error: Database missing required columns: {required_db_cols}")
        return
    
    # Prepare database: normalize names, countries, and parse competition lists
    db_df['name_norm'] = db_df['name'].astype(str).str.lower().str.strip()
    db_df['country_norm'] = db_df['country'].astype(str).str.lower().str.strip()
    db_df['competitions_list'] = db_df['competitions'].apply(safe_literal_eval)
    print("Database prepared (normalized and parsed)")
    
    # Process all result files
    print(f"Starting search for results.csv files in {results_dir}...")
    files_processed = 0
    files_updated = 0
    
    for root, _, files in os.walk(results_dir):
        for filename in files:
            if filename == 'results.csv':
                file_path = os.path.join(root, filename)
                print(f"\nProcessing file: {file_path}")
                files_processed += 1
                
                # Extract competition name and year from path
                competition_key, year = extract_competition_info(file_path, results_dir)
                if not competition_key or not year:
                    print(f"Skipping file - unable to extract competition info")
                    continue
                    
                print(f"  Competition: '{competition_key}', Year: {year}")

                # Check for rating column in database
                db_rating_col = f"Codeforces_rating_{year}"
                if db_rating_col not in db_df.columns:
                    print(f"  Warning: Database does not contain column '{db_rating_col}'. Skipping.")
                    continue
                
                # Load results file
                try:
                    results_df = pd.read_csv(file_path)
                except Exception as e:
                    print(f"  Error reading results file: {e}. Skipping.")
                    continue
                
                # Validate required columns
                if not all(col in results_df.columns for col in ['Contestant', 'Country']):
                    print(f"  Error: Missing required columns. Skipping.")
                    continue
                
                # Prepare and normalize contestant data
                results_df['Contestant_norm'] = results_df['Contestant'].astype(str).str.lower().str.strip()
                results_df['Country_norm'] = results_df['Country'].astype(str).str.lower().str.strip()
                
                # Look up ratings for each contestant and save
                print(f"  Looking up ratings from '{db_rating_col}'...")
                results_df['CF_Rating'] = results_df.apply(
                    lambda row: get_rating(row, db_df, competition_key, db_rating_col),
                    axis=1
                )
                
                # Clean up temporary normalized columns
                results_df.drop(columns=['Contestant_norm', 'Country_norm'], inplace=True)
                
                # Save updated results
                try:
                    results_df.to_csv(file_path, index=False)
                    print(f"  Successfully saved {file_path}")
                    files_updated += 1
                except Exception as e:
                    print(f"  Error saving results file: {e}")

    print(f"\nFinished: {files_processed} files found, {files_updated} files updated.")

if __name__ == "__main__":
    process_results_files()
