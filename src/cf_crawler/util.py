"""
Utility module for processing and standardizing competitive programming results data.

This module processes CSV files in the Results directory by validating, standardizing
column names, normalizing country data, and filling missing fields. Supports competition-specific
logic for COCI, NOI 2024, OOI, and others.

Main Functions:
- validate_and_fix_results_directory(): Standardize columns and handle missing data
- standardize_country_names(): Normalize country names to standard format
- clean_and_rename_columns(): Remove unnecessary columns and finalize output

Usage:
    python util.py  # Runs the complete data processing pipeline
"""

import os
import pandas as pd
from typing import Dict, Optional
from dotenv import load_dotenv
from openai import OpenAI
from google import genai
from time import sleep

# Load environment variables from .env file
load_dotenv()

# Initialize OpenRouter API client for AI-powered data processing
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=os.getenv("OPENROUTER_API_KEY"),
)

# Define the country mapping
# Maps ISO 3-letter country codes to full country names
# Used to normalize country data from various competitions
COUNTRY_MAPPING = {
    'POL': 'Poland',
    'LVA': 'Latvia',
    'FIN': 'Finland',
    'SWE': 'Sweden',
    'ISL': 'Iceland',
    'LTU': 'Lithuania',
    'DNK': 'Denmark',
    'PRT': 'Portugal',
    'AZE': 'Azerbaijan',
    'SVN': 'Slovenia',
    'BEL': 'Belgium',
    'NLD': 'Netherlands',
    'EST': 'Estonia',
    'NOR': 'Norway',
    'USA': 'United States of America',
    'HKG': 'Hong Kong, China',
    'CHN': 'China',
    'JPN': 'Japan',
    'KOR': 'Republic of Korea',
    'IRN': 'Iran',
    'ISR': 'Israel',
    'VNM': 'Vietnam',
    'THA': 'Thailand',
    'SGP': 'Singapore',
    'MYS': 'Malaysia',
    'IDN': 'Indonesia',
    'TWN': 'Taiwan',
    'IND': 'India',
    'BGD': 'Bangladesh',
    'ROU': 'Romania',
    'HUN': 'Hungary',
    'BGR': 'Bulgaria',
    'SRB': 'Serbia',
    'HRV': 'Croatia',
    'SVK': 'Slovakia',
    'CZE': 'Czech Republic',
    'GBR': 'United Kingdom',
    'FRA': 'France',
    'DEU': 'Germany',
    'ESP': 'Spain',
    'ITA': 'Italy',
    'CHE': 'Switzerland',
    'AUT': 'Austria',
    'TUR': 'Türkiye',  # Note: using the new official name, not 'Turkey'
    'BRA': 'Brazil',
    'EGY': 'Egypt',
    'GEO': 'Georgia',
    'BIH': 'Bosnia and Herzegovina',
    'CYP': 'Cyprus',
    'AUS': 'Australia',
    'ARM': 'Armenia',
    'MKD': 'North Macedonia',  # Note: this is the new official name
    'KGZ': 'Kyrgyzstan',
    'UZB': 'Uzbekistan',
    'MEX': 'Mexico',
    'PER': 'Peru',
    'MNG': 'Mongolia',
    'KAZ': 'Kazakhstan',
    'IRL': 'Ireland',
    'SAU': 'Saudi Arabia',
    'GRC': 'Greece',
    'NZL': 'New Zealand',
    'LUX': 'Luxembourg',
    'ARE': 'United Arab Emirates',
    'DZA': 'Algeria',
    'UKR': 'Ukraine',
    'TUN': 'Tunisia',
    'BOL': 'Bolivia',
    'MDA': 'Moldova',
    'ECU': 'Ecuador',
}

# Target column names for standardized result files
STANDARD_COLUMNS = ['Rank', 'Contestant', 'Country', 'Total']

# Column name aliases mapped to standard names (case-insensitive)
COLUMN_ALIASES = {
    'name': 'Contestant',
    'contestant_contestant': 'Contestant',
    'english name': 'Contestant',
    'total': 'Total',
    'total score': 'Total',
    'award_award': 'medal',
    'prize': 'medal',
    'rank': 'Rank',
    'country': 'Country',
    'country_country': 'Country',
    'location': 'Country',
    'rank_rank': 'Rank',
    'score': 'Total',
    'score_score': 'Total',
    'ranking': 'Rank',
    'total_score': 'Total',
    'Points': 'Total',
    'Score▼_Abs.': 'Total',
    'points': 'Total',
    'score▼_abs.': 'Total',
    'ukupno': 'Total',
}

def normalize_country(country: str) -> str:
    """
    Normalize country name to standard format.
    
    Handles multiple input formats including ISO codes, abbreviations, and various
    naming conventions. Returns standardized country name or original input if no
    mapping found.
    
    Args:
        country: Country name, code, or abbreviation to normalize
        
    Returns:
        Standardized country name or original input with whitespace stripped
    """
    if not country:
        return ""
    
    country_upper = country.strip().upper()
    
    if country_upper in COUNTRY_MAPPING:
        return COUNTRY_MAPPING[country_upper]
    
    # Handle special cases
    if country_upper == "UK":
        return "United Kingdom"
    if country_upper == "HONG KONG":
        return "Hong Kong, China"
    if country_upper == "KOREA" or country_upper == "SOUTH KOREA":
        return "Republic of Korea"
    if country_upper == "USA" or country_upper == "UNITED STATES":
        return "United States of America"
    
    return country.strip()

def standardize_country_names():
    """
    Standardize country names across all result CSV files.
    
    Walks through Results directory, applies normalization to Country columns,
    creates backups, and tracks changes.
    """
    results_dir = "Results"
    
    for root, dirs, files in os.walk(results_dir):
        for file in files:
            if file.endswith('.csv'):
                file_path = os.path.join(root, file)
                print(f"Processing {file_path}")
                
                try:
                    df = pd.read_csv(file_path)
                    
                    if 'Country' in df.columns:
                        backup_path = file_path + '.backup'
                        if not os.path.exists(backup_path):
                            df.to_csv(backup_path, index=False)
                            print(f"Created backup at {backup_path}")
                        
                        changes = []
                        original_countries = df['Country'].copy()
                        df['Country'] = df['Country'].apply(normalize_country)
                        
                        for orig, norm in zip(original_countries, df['Country']):
                            if orig != norm:
                                changes.append((orig, norm))
                        
                        if changes:
                            print(f"Changes in {file_path}:")
                            for orig, norm in changes:
                                print(f"  {orig} -> {norm}")
                        
                        df.to_csv(file_path, index=False)
                        print(f"Updated {file_path}")
                    else:
                        print(f"No 'Country' column found in {file_path}")
                
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

def handle_missing_country(file_path: str, df: pd.DataFrame):
    """
    Handle CSVs missing Country column with competition-specific logic.
    
    Competition-specific assignments:
    - JOI, TOKI: 'Placeholder'
    - COCI: 'Croatia'
    - SOI 2024: 'Sweden'
    - OOI: Extract from City column via Google Gemini API
    
    Args:
        file_path: Path to the CSV file
        df: DataFrame with missing Country column
        
    Returns:
        DataFrame with Country column populated
    """
    print(f"Handling missing 'Country' column in {file_path}.")

    if "JOI" in file_path or "TOKI" in file_path:
        df['Country'] = 'Placeholder'
        print("Assigned Placeholder as country for JOI and TOKI.")
        return df
    
    if "COCI" in file_path:
        df['Country'] = 'Croatia'
        print("Assigned Croatia as country for COCI.")
        return df

    if file_path == "Results/SOI/2024/Final/results.csv":
        df['Country'] = 'Sweden'
        print("Assigned 'Sweden' as country for SOI 2024 Final.")
    elif "OOI" in file_path and 'City' in df.columns:
        print("Processing OOI file to determine countries from cities...")
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        index = 0
        max_retries_per_row = 3 # Add a limit to prevent infinite loops

        while index < len(df):
            row = df.iloc[index]
            retries = 0
            while retries < max_retries_per_row:
                prompt = f"""
                Given the following City, return the Country that the city is in.
                City: {row['City']}
                Country:
                ONLY RETURN THE COUNTRY, NOTHING ELSE.
                CONVERT THE COUNTRY NAME TO ENGLISH.
                IF YOU CANNOT FIND THE COUNTRY, RETURN 'Russia'.
                """
                try:
                    response = client.models.generate_content(
                        model="gemini-2.0-flash-lite", 
                        contents=prompt
                    )
                    country = response.text.strip() # Ensure no extra whitespace
                    print(f"Row {index}: City '{row['City']}' -> Country '{country}'")
                    df.at[index, 'Country'] = country
                    sleep(3) # Reduced sleep slightly, adjust as needed
                    break # Success, move to next row

                except Exception as e:
                    retries += 1
                    print(f"API call failed for row {index} (City: {row['City']}). Attempt {retries}/{max_retries_per_row}. Error: {str(e)}")
                    if retries < max_retries_per_row:
                        print("Retrying after a short delay...")
                        sleep(5 + retries * 2)
                    else:
                        print(f"Max retries reached for row {index}. Assigning 'Russia'.")
                        df.at[index, 'Country'] = 'Russia'
                        break

            index += 1

    elif "OOI" in file_path and 'City' not in df.columns:
         print(f"Warning: Cannot process OOI file {file_path} - 'City' column missing.")
    else:
        print(f"Warning: No specific handling for missing 'Country' in {file_path}")

    return df

def validate_and_fix_results_directory(root_dir='Results'):
    """
    Validate and fix all result CSV files in Results directory.
    
    Operations:
    1. COCI-specific: Move formal_results.csv to CONTEST_#X_formal directories
    2. Standardize filenames to 'results.csv'
    3. Rename columns using COLUMN_ALIASES
    4. Validate required columns
    5. Handle missing Country column
    6. NOI 2024-specific: Extract country from Contestant column
    7. Save modifications
    
    Args:
        root_dir: Root directory containing results (default: 'Results')
    """
    for dirpath, dirnames, filenames in os.walk(root_dir):

        # COCI-specific: Move formal_results.csv to separate directories
        try:
            norm_path = os.path.normpath(dirpath)
            parts = norm_path.split(os.sep)
            # Check structure: Results/COCI/Year/CONTEST_#X
            if (len(parts) == 4 and
                parts[0] == root_dir and
                parts[1].upper() == 'COCI' and
                parts[3].upper().startswith('CONTEST_#') and
                not parts[3].upper().endswith('_FORMAL')):

                contest_dir_name = parts[3]
                formal_results_file = 'formal_results.csv'

                if formal_results_file in filenames:
                    source_path = os.path.join(dirpath, formal_results_file)
                    new_dir_name = contest_dir_name + "_formal"
                    new_dir_path = os.path.join(os.path.dirname(dirpath), new_dir_name)
                    destination_path = os.path.join(new_dir_path, 'results.csv')

                    print(f"COCI: Moving {source_path} to {destination_path}")
                    try:
                        os.makedirs(new_dir_path, exist_ok=True)
                        os.rename(source_path, destination_path)
                        print(f"COCI: Successfully moved formal results for {contest_dir_name}.")
                        filenames.remove(formal_results_file)
                    except OSError as e:
                        print(f"Error moving COCI formal results: {e}")

        except Exception as path_e:
             print(f"Warning: Could not process path for COCI handling {dirpath}: {path_e}")

    # Process all CSV files in Results directory
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith('.csv'):
                file_path = os.path.join(dirpath, filename)

                # Standardize filename to 'results.csv'
                if filename != 'results.csv':
                    new_path = os.path.join(dirpath, 'results.csv')
                    print(f"Renaming {file_path} to {new_path}")
                    try:
                        os.rename(file_path, new_path)
                        file_path = new_path # Use the new path going forward
                    except OSError as e:
                        print(f"Error renaming file {file_path}: {e}")
                        continue # Skip to next file if rename fails

                try:
                    df = pd.read_csv(file_path)
                    if df.empty:
                        print(f"Skipping empty file: {file_path}")
                        continue

                    original_columns = {col.lower(): col for col in df.columns}
                    file_modified = False

                    # Create working copy of column mapping
                    # Special handling for OOI competition's 'English Name' column
                    new_original_columns = original_columns.copy()
                    ooi_contestant_handled = False

                    # Extract competition name from directory path
                    competition_name = ""
                    try:
                        norm_path = os.path.normpath(dirpath)
                        parts = norm_path.split(os.sep)
                        if len(parts) > 1 and parts[0] == root_dir:
                             competition_name = parts[1]
                    except Exception as path_e:
                        print(f"Warning: Could not determine competition name from path {dirpath}: {path_e}")

                    year = ""
                    try:
                        norm_path = os.path.normpath(dirpath)
                        parts = norm_path.split(os.sep)
                        if len(parts) > 1 and parts[0] == root_dir:
                             year = parts[2]
                    except Exception as path_e:
                        print(f"Warning: Could not determine year from path {dirpath}: {path_e}")

                    # OOI-specific handling for 'english name' column
                    if competition_name.upper() == 'OOI':
                        ooi_alias = 'english name'
                        if ooi_alias in new_original_columns:
                            original_col_name = new_original_columns[ooi_alias]
                            standard_name = 'Contestant'
                            if original_col_name != standard_name:
                                print(f"OOI: Renaming '{original_col_name}' to '{standard_name}' in {file_path}")
                                df.rename(columns={original_col_name: standard_name}, inplace=True)
                                file_modified = True
                                del new_original_columns[ooi_alias]
                                new_original_columns[standard_name.lower()] = standard_name
                                ooi_contestant_handled = True

                    # Apply general column name standardization
                    for alias, standard_name in COLUMN_ALIASES.items():
                        if ooi_contestant_handled and standard_name == 'Contestant':
                            continue

                        if alias in new_original_columns:
                            original_col_name = new_original_columns[alias]
                            if original_col_name != standard_name:
                                # Avoid duplicate columns
                                if standard_name.lower() in new_original_columns and alias != standard_name.lower():
                                     if original_col_name != new_original_columns[standard_name.lower()]:
                                           del new_original_columns[alias]
                                     continue

                                print(f"Renaming '{original_col_name}' to '{standard_name}' in {file_path}")
                                try:
                                    df.rename(columns={original_col_name: standard_name}, inplace=True)
                                    file_modified = True
                                    del new_original_columns[alias]
                                    new_original_columns[standard_name.lower()] = standard_name
                                except KeyError as rename_error:
                                     print(f"Warning: Could not rename '{original_col_name}' in {file_path}: {rename_error}")

                    original_columns = new_original_columns

                    current_columns = df.columns
                    current_columns_lower = {col.lower() for col in current_columns}
                    required_columns_lower = {col.lower() for col in STANDARD_COLUMNS}

                    missing_std_cols = [
                        std_col for std_col in STANDARD_COLUMNS
                        if std_col.lower() not in current_columns_lower
                    ]

                    # Apply competition-specific logic for missing required columns
                    # --- NOI 2024 Specific Handling ---
                    # NOI 2024 stores country code at the end of Contestant name (e.g., "John FI")
                    if competition_name.upper() == 'NOI' and year == '2024' and 'Country' not in df.columns:
                        print(f"Processing NOI 2024 file: Splitting Country from Contestant column in {file_path}")
                        if 'Contestant' in df.columns:
                            try:
                                # Split 'Contestant' into name and country_code
                                # Splits from the right to handle names with spaces properly
                                split_data = df['Contestant'].str.rsplit(' ', n=1, expand=True)

                                # Assign the parts back
                                # First part is contestant name, second part is country code
                                df['Contestant'] = split_data[0].str.strip()
                                extracted_countries = split_data[1].str.strip().str.upper() # Extract and uppercase

                                # Define the specific NOI 2024 country code mapping
                                # Maps 2-letter ISO codes used by NOI to full country names
                                noi_country_map = {
                                    'FI': 'Finland',
                                    'SE': 'Sweden',
                                    'DK': 'Denmark',
                                    'NO': 'Norway',
                                }

                                # Apply NOI 2024-specific 2-letter code mapping
                                df['Country'] = extracted_countries.map(noi_country_map)
                                df['Country'].fillna(extracted_countries, inplace=True)

                                # Apply general normalization
                                print(f"Applying general normalization to Country column for {file_path}")
                                df['Country'] = df['Country'].apply(normalize_country)

                                file_modified = True
                                print(f"Successfully split and normalized Country for NOI 2024 in {file_path}")

                                # Update column tracking
                                if 'country' not in current_columns_lower:
                                     current_columns_lower.add('country')
                                     missing_std_cols = [col for col in missing_std_cols if col.lower() != 'country']

                            except Exception as split_error:
                                print(f"Error splitting 'Contestant' column in {file_path}: {split_error}")
                        else:
                            print(f"Warning: 'Contestant' column not found in {file_path} for NOI 2024 processing.")
                    # --- End NOI 2024 Handling ---
                    
                    country_missing = 'country' in [m.lower() for m in missing_std_cols]

                    if country_missing:
                        updated_df = handle_missing_country(file_path, df)
                        df = updated_df
                        file_modified = True
                        missing_std_cols = [col for col in missing_std_cols if col.lower() != 'country']

                    if missing_std_cols:
                         print(f"Missing required columns in {file_path}: {', '.join(missing_std_cols)}")

                    # Write modified DataFrame back to CSV if any changes were made
                    if file_modified:
                        try:
                           df.to_csv(file_path, index=False)
                           print(f"Saved changes to {file_path}")
                        except Exception as e:
                           print(f"Error saving {file_path}: {e}")

                except pd.errors.EmptyDataError:
                     print(f"Skipping empty file: {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}\n")

def clean_and_rename_columns(root_dir='Results'):
    """
    Clean and standardize columns across all results CSV files.
    
    Performs two main operations:
    1. Drops unnecessary columns that are not required for analysis
       (grade, city, class of study, etc.)
    2. Renames columns to standardized names (award -> medal, etc.)
    
    Creates backups before modification and processes all results.csv files
    in the Results directory tree recursively.
    
    Args:
        root_dir: Root directory containing competition results (default: 'Results')
    """
    print(f"Starting column cleaning and renaming in {root_dir}...")

    # Columns that should be removed from result files
    # These are not needed for analysis and can clutter the data
    columns_to_drop = ['grade', 'city', 'class of study', 'participation class',
                       'name', 'score rel.','score▼_rel.','username', 'school']
    
    # Mapping of old column names to standardized names
    # Ensures consistent naming across all result files
    rename_mapping = {
        'award': 'medal',
        'medal english': 'medal',
        'mention': 'medal',
    }

    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename == 'results.csv':
                file_path = os.path.join(dirpath, filename)
                print(f"Processing {file_path}")
                file_modified = False

                try:
                    df = pd.read_csv(file_path)
                    if df.empty:
                        print(f"Skipping empty file: {file_path}")
                        continue

                    current_columns = df.columns.tolist()
                    columns_to_drop_found = []
                    rename_map_for_df = {}

                    # Find columns to drop (case-insensitive)
                    for col in current_columns:
                        if col.lower() in columns_to_drop:
                            columns_to_drop_found.append(col)

                    # Find columns to rename (case-insensitive)
                    for col in current_columns:
                        if col.lower() in rename_mapping:
                            target_name = rename_mapping[col.lower()]
                            # Avoid overwriting existing columns
                            if target_name != col and target_name not in df.columns:
                                rename_map_for_df[col] = target_name
                            elif target_name != col and target_name in df.columns and target_name == 'medal':
                                rename_map_for_df[col] = target_name
                            elif target_name == col:
                                pass
                            else:
                                print(f"  Skipping rename of '{col}' to '{target_name}' - target exists")

                    # Drop unwanted columns
                    if columns_to_drop_found:
                        print(f"  Dropping: {', '.join(columns_to_drop_found)}")
                        df.drop(columns=columns_to_drop_found, inplace=True)
                        file_modified = True

                    # Rename columns
                    if rename_map_for_df:
                         print(f"  Renaming: {rename_map_for_df}")
                         df.rename(columns=rename_map_for_df, inplace=True)
                         file_modified = True

                    # Save if modified
                    if file_modified:
                        backup_path = file_path + '.backup_clean'
                        if not os.path.exists(backup_path):
                             pd.read_csv(file_path).to_csv(backup_path, index=False)
                             print(f"  Created backup at {backup_path}")

                        df.to_csv(file_path, index=False)
                        print(f"  Saved {file_path}")
                    else:
                        print(f"  No changes needed")

                except pd.errors.EmptyDataError:
                     print(f"Skipping empty file: {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")

    print("Finished column cleaning and renaming.")

if __name__ == "__main__":
    print("Starting validation and fixing results directory...")
    validate_and_fix_results_directory()
    print("Finished validation and fixing.")

    print("Starting country name standardization...")
    standardize_country_names()
    print("Finished country name standardization.")

    clean_and_rename_columns()

    print("All processing finished.")
