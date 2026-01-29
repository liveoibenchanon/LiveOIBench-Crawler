"""
Main entry point for the Competitive Framing Crawler application.

This module orchestrates the database setup and competition results processing.
It integrates contestant data from competitive programming competitions with their
Codeforces profiles and rating history.

Features:
- setup(): Initializes the database with IOI 2024 results
- process_competition(): Adds results from other competitions to the database
- main(): CLI interface for running the above operations

Usage:
    python main.py setup                                    # Initialize database
    python main.py Results/IOI/2024/results.csv            # Add competition results
"""

import sys
import os
from user_database import UserDatabase
import math
import requests

def setup():
    """
    Initialize the database with IOI 2024 competition results.
    
    Creates a new database and populates it with IOI 2024 contestants by:
    1. Reading IOI 2024 results from CSV file
    2. Searching for each contestant's Codeforces profile via CPHOF
    3. Retrieving their Codeforces rating history
    4. Storing contestant data with their ratings
    
    Raises:
        SystemExit: If database already exists or file is not found
    """
    db = UserDatabase()
    
    # Check if database already exists to prevent overwriting
    if db.database_exists():
        print("Database already exists. Use competition path to add new data.")
        sys.exit(1)
    
    # Load IOI 2024 results from standardized CSV file
    results_df = db.read_competition_results("Results/IOI/2024/results.csv")
    
    # Process each contestant from IOI 2024
    for _, row in results_df.iterrows():
        contestant_name = row['Contestant']
        country = row['Country']
        
        print(f"\nProcessing {contestant_name} from {country} (Setup)")
        
        # Search CPHOF (Competitive Programmers' Hall of Fame) for contestant profile
        cphof_profile = db.search_cphof(contestant_name, country)
        cf_username = None
        if cphof_profile:
            print(f"Found CPHOF profile: {cphof_profile}")
            # Extract Codeforces username from CPHOF profile page
            cf_username = db.get_codeforces_username(cphof_profile)
        
        if not cf_username:
            print(f"Could not find Codeforces username for {contestant_name} via CPHOF. Skipping.")
            continue
        
        # Fetch Codeforces rating history for the contestant
        cf_ratings = db.get_codeforces_rating_history(cf_username)
        
        # Prepare contestant data for database insertion
        contestant_data = {
            'name': contestant_name,
            'country': country,
            'codeforces_id': cf_username,
            'competitions': str(['IOI 2024']),  # Store as string representation of list
            'Codeforces_rating_2025': cf_ratings['Codeforces_rating_2025'],
            'Codeforces_rating_2024': cf_ratings['Codeforces_rating_2024'],
            'Codeforces_rating_2023': cf_ratings['Codeforces_rating_2023'],
            'Codeforces_rating_2022': cf_ratings['Codeforces_rating_2022'],
            'search_confidence_percent': 100.0  # High confidence for direct CPHOF match
        }
        db.add_contestant(contestant_data)
        print(f"Added {contestant_name} to database (Setup)")
    
    # Save database to disk
    db.save_database()

def process_competition(competition_path: str):
    """
    Process new competition results and update the existing database.
    
    Adds contestants from a new competition to the database. Handles two workflows:
    1. Direct match (JOI, TOKI, APIO, OOI): Uses Codeforces username directly
    2. Search-based match: Searches for Codeforces username using Serper API
    
    Args:
        competition_path: Path to competition results CSV (e.g., "Results/IOI/2024/results.csv")
        
    Raises:
        SystemExit: If database doesn't exist or invalid path format provided
    """
    db = UserDatabase()
    
    # Verify database exists before processing
    if not db.database_exists():
        print("Database doesn't exist. Run setup first.")
        sys.exit(1)
    
    # Load existing database
    db.load_database()
    
    # Extract competition name from directory path
    # Path format: Results/Competition/Year/[Stage]/results.csv
    path_parts = competition_path.split('/')
    try:
        results_index = path_parts.index('Results')
        # Extract components between 'Results' and 'results.csv' to form competition name
        competition_components = path_parts[results_index + 1:-1]
        competition_name = f"{' '.join(competition_components)}"
        print(f"Processing competition: {competition_name}")
    except ValueError:
        print("Invalid path format. Expected path format: Results/Competition/Year/[Stage]/results.csv")
        sys.exit(1)
    
    # Load competition results from CSV
    results_df = db.read_competition_results(competition_path)

    # Handle competitions with direct Codeforces username matching
    # These competitions allow direct username lookup without search
    if ("JOI" in competition_name and "EJOI" not in competition_name) or ("TOKI" in competition_name) or ("APIO 2024" in competition_name) or ("OOI" in competition_name):
        for _, row in results_df.iterrows():
            contestant_name = row['Contestant']
            print(f"\nProcessing {contestant_name} ({competition_name})")

            # Check if contestant already exists in database
            # If yes, update their competition list and continue
            if db.update_contestant_competitions_cfusername(contestant_name, competition_name):
                print(f"Updated existing contestant: {contestant_name}")
                continue

            # Fetch Codeforces rating history using username directly
            cf_ratings = db.get_codeforces_rating_history(contestant_name)
            # Query Codeforces API for contestant country information
            info_url = f"https://codeforces.com/api/user.info?handles={contestant_name}"
            info_data = requests.get(info_url).json()
            if info_data['status'] == 'OK':
                try:
                    country = info_data['result'][0]['country']
                except:
                    country = ""
                # Prepare contestant data for database insertion
                contestant_data = {
                    'name': contestant_name,
                    'country': country,
                    'codeforces_id': contestant_name,
                    'competitions': str([competition_name]),
                    'Codeforces_rating_2025': cf_ratings['Codeforces_rating_2025'],
                    'Codeforces_rating_2024': cf_ratings['Codeforces_rating_2024'],
                    'Codeforces_rating_2023': cf_ratings['Codeforces_rating_2023'],
                    'Codeforces_rating_2022': cf_ratings['Codeforces_rating_2022'],
                    'search_confidence_percent': 100.0  # Direct match from Codeforces API
                }
                db.add_contestant(contestant_data)
                print(f"Added new contestant: {contestant_name}")
    
    else:
        # Handle competitions requiring Codeforces username search
        # For competitions not in the direct-match list
        for _, row in results_df.iterrows():
            contestant_name = row['Contestant']
            country = row['Country']
            # Handle missing country data
            if country != country: 
                country = ""
            print(f"\nProcessing {contestant_name} from {country} ({competition_name})")
            
            # Check if contestant already exists in database
            # If yes, update their competition list and continue
            if db.update_contestant_competitions(contestant_name, country, competition_name):
                print(f"Updated existing contestant: {contestant_name}")
                continue
            
            # Search for Codeforces username using Serper API
            print(f"New contestant {contestant_name}, attempting Codeforces search...")
            cf_username, confidence = db.search_codeforces_username(contestant_name, country)
            if not cf_username:
                print(f"Could not find Codeforces username for {contestant_name} via serper search. Skipping.")
                continue  # Skip this contestant if username not found
            print(f"Found potential Codeforces username: {cf_username} with confidence {confidence:.2f}%")

            # Fetch Codeforces rating history for the found username
            cf_ratings = db.get_codeforces_rating_history(cf_username)
            
            # Prepare contestant data for database insertion
            contestant_data = {
                'name': contestant_name,
                'country': country,
                'codeforces_id': cf_username,
                'competitions': str([competition_name]),
                'codeforces_rating_2025': cf_ratings['Codeforces_rating_2025'],
                'Codeforces_rating_2024': cf_ratings['Codeforces_rating_2024'],
                'Codeforces_rating_2023': cf_ratings['Codeforces_rating_2023'],
                'Codeforces_rating_2022': cf_ratings['Codeforces_rating_2022'],
                'search_confidence_percent': confidence  # Confidence from search algorithm
            }
            db.add_contestant(contestant_data)
            print(f"Added new contestant: {contestant_name}")
        
    # Save updated database
    db.save_database()

def main():
    """
    CLI entry point for the application.
    
    Accepts two commands:
    - "setup": Initialize database with IOI 2024 results
    - competition_path: Add new competition results to database
    """
    if len(sys.argv) < 2:
        print("Usage: python main.py [setup|Results/path/to/competition]")
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "setup":
        setup()
    else:
        process_competition(command)

if __name__ == "__main__":
    main()