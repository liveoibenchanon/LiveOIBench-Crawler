"""User database management for competitive programming contestants.

Manages contestant information including names, countries, Codeforces usernames,
and rating histories. Searches for Codeforces profiles using CPHOF, Google,
and Serper API with AI-powered relevance confirmation.

Key Functions:
- search_cphof(): Find Codeforces handles via CPHOF database
- find_codeforces_username(): Search using Google with confidence matching
- get_codeforces_rating_history(): Fetch yearly max ratings from Codeforces API
"""

import pandas as pd
import requests
import json
import sys
import os
from typing import Optional, Dict, List, Tuple
from bs4 import BeautifulSoup
from googlesearch import search
import re
import time
import unicodedata
from google import genai
from dotenv import load_dotenv
from time import sleep
load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

class UserDatabase:
    def __init__(self):
        self.database_path = "database.csv"
        self.columns = [
            'name', 
            'country', 
            'codeforces_id', 
            'competitions',
            'Codeforces_rating_2025',
            'Codeforces_rating_2024',
            'Codeforces_rating_2023',
            'Codeforces_rating_2022',
            'search_confidence_percent'
        ]
        self.df = pd.DataFrame(columns=self.columns)
    
    def database_exists(self) -> bool:
        """Check if database CSV exists."""
        return os.path.exists(self.database_path)
    
    def load_database(self):
        """Load existing database."""
        if self.database_exists():
            self.df = pd.read_csv(self.database_path)
        else:
            print("No existing database found.")
            sys.exit(1)
    
    def read_competition_results(self, file_path: str) -> pd.DataFrame:
        """Read competition results from CSV file.
        
        Args:
            file_path: Path to competition results CSV
            
        Returns:
            DataFrame with competition results
        """
        try:
            df = pd.read_csv(file_path)
            required_columns = ['Contestant', 'Country']
            if not all(col in df.columns for col in required_columns):
                print(f"Error: Competition CSV must contain columns: {required_columns}")
                sys.exit(1)
            return df
        except Exception as e:
            print(f"Error reading competition results: {e}")
            sys.exit(1)
    
    def normalize_name(self, name: str) -> str:
        """Normalize name by removing diacritical marks and converting to lowercase.
        
        Args:
            name: Name to normalize (e.g., 'Kalniņš')
            
        Returns:
            Normalized name (e.g., 'kalnins')
        """
        normalized = unicodedata.normalize('NFKD', name)
        return ''.join(c for c in normalized if not unicodedata.combining(c)).lower()
    
    def get_country_from_ioi_profile(self, profile_url: str) -> Optional[str]:
        """Extract country name from CPHOF IOI profile page.
        
        Args:
            profile_url: URL of the CPHOF IOI profile page
            
        Returns:
            Country name if found, None otherwise
        """
        try:
            response = requests.get(profile_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            country_links = soup.find_all('a', href=lambda href: href and href.startswith('/country/'))

            if not country_links:
                print(f"Could not find any country links (href^='/country/') on {profile_url}")
                return None

            for link in country_links:
                link_text = link.get_text(strip=True)
                if link_text:
                    print(f"Extracted country '{link_text}' from link text.")
                    return link_text

                link_title = link.get('title', '').strip()
                if link_title:
                    print(f"Extracted country '{link_title}' from link title.")
                    return link_title
            
            print(f"Found country links, but none had extractable text or title on {profile_url}")
            return None

        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch profile {profile_url}: {e}")
            return None
        except Exception as e:
            print(f"Error parsing profile {profile_url}: {e}")
            return None

    def search_cphof(self, contestant_name: str, contestant_country: str) -> Optional[str]:
        """Search CPHOF for contestant and return Codeforces profile URL.
        
        Args:
            contestant_name: Name of the contestant
            contestant_country: Country of the contestant
            
        Returns:
            Codeforces profile URL if found, None otherwise
        """
        base_url = "https://cphof.org/search"
        query = "+".join(contestant_name.split())
        
        try:
            response = requests.get(f"{base_url}?query={query}")
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code} when searching for {contestant_name}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            results_container = soup.find('div', class_='container-fluid')
            if not results_container:
                print(f"No results container found for {contestant_name}")
                return None
                
            result_rows = results_container.find_all('div', class_='row')
            if not result_rows:
                print(f"No search results found for {contestant_name}")
                return None
                
            valid_results = []
            for row in result_rows:
                name_link = row.find('a')
                if not name_link:
                    continue
                    
                result_name = name_link.get_text().strip()
                print(f"Found result: {result_name}")
                valid_results.append((row, name_link, result_name))
                
            if not valid_results:
                print(f"No valid results found for {contestant_name}")
                return None
                
            if len(valid_results) > 1:
                exact_match = []
                print(f"Multiple valid results found, looking for exact match for: {contestant_name}")
                for row, name_link, result_name in valid_results:
                    if result_name == contestant_name:
                        exact_match.append((row, name_link))
                if len(exact_match) == 1:
                    row, name_link = exact_match[0]
                    href = name_link.get('href', '')
                    if 'profile/codeforces:' in href:
                        if href.startswith('/'):
                            href = f"https://cphof.org{href}"
                        return href
                    return self.get_profile_url(row)
                
                if len(exact_match) > 1:
                    print(f"Multiple exact matches found for: {contestant_name}")
                    for row, name_link in exact_match:
                        print(f"Name link: {name_link.get('href')}")
                        country = self.get_country_from_ioi_profile(f"https://cphof.org{name_link.get('href')}")
                        if country == contestant_country:
                            print(f"Found exact match for: {contestant_name} with country: {country}")
                            name_link_href = name_link.get('href')
                            if 'profile/codeforces:' in name_link_href:
                                if name_link_href.startswith('/'):
                                    href = f"https://cphof.org{name_link_href}"
                                return href
                            else:
                                print(f"Row: {row}")
                                print(f"Profile URL: {self.get_profile_url(row)}")
                                return self.get_profile_url(row)
                    return None
                
                print(f"No exact match found among multiple results for: {contestant_name}")
                return None
            
            row, name_link, _ = valid_results[0]
            href = name_link.get('href', '')
            if 'profile/codeforces:' in href:
                if href.startswith('/'):
                    href = f"https://cphof.org{href}"
                return href
                
            return self.get_profile_url(row)
            
        except Exception as e:
            print(f"Error searching cphof for {contestant_name}: {e}")
            return None
        
    def get_profile_url(self, result_row) -> Optional[str]:
        """Extract IOI profile URL from search result row.
        
        Args:
            result_row: BeautifulSoup result row element
            
        Returns:
            Profile URL if found, None otherwise
        """
        profile_link = result_row.find('a', href=lambda href: href and '/profile/ioi:' in href)
        if not profile_link:
            return None
        
        profile_url = profile_link.get('href')
        if profile_url.startswith('/'):
            profile_url = f"https://cphof.org{profile_url}"
        return profile_url
    
    def get_codeforces_username(self, cphof_profile: str) -> Optional[str]:
        """Extract Codeforces username from CPHOF profile page.
        
        Args:
            cphof_profile: URL of the CPHOF profile page
            
        Returns:
            Codeforces username if found, None otherwise
        """
        try:
            response = requests.get(cphof_profile)
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code} when accessing profile {cphof_profile}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            codeforces_link = soup.find('a', href=lambda href: href and 'codeforces.com/profile/' in href)
            
            if codeforces_link:
                cf_url = codeforces_link['href']
                username = cf_url.split('profile/')[-1]
                print(f"Found Codeforces username: {username}")
                return username
            
            print("No Codeforces profile found on CPHOF page")
            return None
            
        except Exception as e:
            print(f"Error extracting Codeforces username from {cphof_profile}: {e}")
            return None

    def search_codeforces_username(self, contestant_name, country) -> Tuple[Optional[str], Optional[float]]:
        """Search Serper API for Codeforces profiles and match using API data.
        
        Directly searches for Codeforces profile URLs and verifies matches
        using Codeforces API user info with AI confirmation for medium-confidence matches.
        
        Args:
            contestant_name: Name of the contestant
            country: Country of the contestant
            
        Returns:
            Tuple of (username, score) or (None, None)
        """
        query = f'{contestant_name} {country} codeforces'
        print(f"Searching Serper: {query}")
        urls_endpoint = "https://google.serper.dev/search"

        payload = json.dumps({
        "q": query
        })
        headers = {
        'X-API-KEY': 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        'Content-Type': 'application/json'
        }
        response = requests.request("POST", urls_endpoint, headers=headers, data=payload)

        search_results = response.json().get('organic', [])
        names_and_urls = [
            (url.split('/')[-1].split('?')[0], url)
            for url in [item['link'] for item in search_results] if "https://codeforces.com/profile/" in url
        ]
        print("names:", [name for name, _ in names_and_urls])

        if not names_and_urls:
            print("No name found.")
            return None, None

        normalized_contestant_name = self.normalize_name(contestant_name)
        name_words = normalized_contestant_name.split()
        country_lower = country.lower()
        print(f"Normalized components for matching: {name_words}")

        for name, search_url in names_and_urls:
            url = f"https://codeforces.com/api/user.info?handles={name}&checkHistoricHandles=false"
            headers = {"User-Agent": "Mozilla/5.0"}

            response = requests.get(url, headers=headers, timeout=3)

            data = response.json()    
            if data["status"] == "OK":
                user = data["result"][0]

                first_name = self.normalize_name(user.get('firstName', ''))
                last_name = self.normalize_name(user.get('lastName', ''))
                middle_name = self.normalize_name(user.get('middleName', ''))
                country_name = self.normalize_name(user.get('country', ''))

                score = 0
                if first_name:
                    if first_name in name_words:
                        score += 25
                if last_name:
                    if last_name in name_words:
                        score += 25
                if middle_name:
                    if middle_name in name_words:
                        score += 25
                else:
                    score += 25
                if country_name:
                    if country_name == country_lower:
                        score += 25
                else:
                    score += 25

                if score > 0:
                    print(f"Match score for {name}: {score}")
                    
                    if 50 <= score <= 75:
                        print(f"Medium confidence match ({score}) for {name}. Checking with AI confirmation...")
                        
                        try:
                            page_response = requests.get(search_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
                            page_response.raise_for_status()
                            page_soup = BeautifulSoup(page_response.text, 'html.parser')
                            page_text = page_soup.get_text()
                            normalized_page_text = self.normalize_name(page_text)
                            
                            if country_lower in normalized_page_text:
                                print(f"Exact country '{country_lower}' found in page text. Proceeding to AI relevance check.")
                                if self.confirm_page_relevance(query, search_url, page_text):
                                    print(f"AI confirmed relevance for {name}.")
                                    return user['handle'], score
                                else:
                                    print(f"AI denied relevance for {name}.")
                                    continue
                            else:
                                print(f"Exact country '{country_lower}' NOT found in page text. Skipping this match.")
                                continue
                        except Exception as e:
                            print(f"Error fetching search result page for AI confirmation: {e}")
                            continue
                    else:
                        return user['handle'], score

            else:
                print("Error in codeforces API response.")
                
        return None, None


    def confirm_page_relevance(self, query: str, url: str, page_text_snippet: str) -> bool:
        """Use Gemini AI to determine if search result is relevant to query.
        
        Args:
            query: Original search query
            url: URL of the search result
            page_text_snippet: Page text content
            
        Returns:
            True if AI confirms relevance, False otherwise
        """
        print("\n--- Manual Confirmation Required ---")
        print(f"Search Query: {query}")
        print(f"Checking URL: {url}")
        print("------------------------------------")
        contestant_name = query.split("+")[0]
        country = query.split("+")[1]
        cleaned_text = re.sub(r'\s+', ' ', page_text_snippet).strip()
        max_len = 30000
        if len(cleaned_text) > max_len:
            print(f"Cleaned text length ({len(cleaned_text)}) exceeds limit ({max_len}). Truncating.")
            cleaned_text = cleaned_text[:max_len]
        prompt = f"""
                    Context:
                    I am searching for the Codeforces profile of a competitive programmer.
                    Original Google Search Query Used: "{query}"
                    Candidate URL found by Google: {url}
                    Page Content Snippet:
                    ---
                    {cleaned_text}
                    ---

                    Task:
                    Based *only* on the provided context and snippet, determine if this page ({url}) seems relevant for finding the Codeforces profile or information about the competitive programmer "{contestant_name}" from "{country}". Look for mentions of the name, country, "Codeforces", programming contests (like IOI, ICPC), or related terms.

                    Respond with ONLY "YES" or "NO". Do not provide any explanation.

                    Answer:
                """
        try:
            print(f"Prompt: {len(prompt)}")
            response = client.models.generate_content(
                model="gemini-2.0-flash", 
                contents=prompt
            )
            sleep(3)
            ai_decision = response.text.strip().upper()
            print(f"AI decision: {ai_decision}")
            if ai_decision == "YES":
                return True
            elif ai_decision == "NO":
                return False
            else:
                print(f"Invalid response from AI: {ai_decision}")
                return self.confirm_page_relevance(query, url, page_text_snippet[:2500])
        except Exception as e:
            print(f"Error confirming page relevance: {e}")
            return False
    
    def get_codeforces_rating_history(self, cf_username: str) -> Dict[str, int]:
        """Fetch yearly max ratings from Codeforces API.
        
        Args:
            cf_username: Codeforces username
            
        Returns:
            Dictionary of yearly max ratings (2022-2025), -1000 on error
        """
        yearly_ratings = {
            'Codeforces_rating_2025': 0,
            'Codeforces_rating_2024': 0,
            'Codeforces_rating_2023': 0,
            'Codeforces_rating_2022': 0
        }
        error_rating = -1000

        try:
            info_url = f"https://codeforces.com/api/user.info?handles={cf_username}"
            
            headers = {
                "User-Agent": "Mozilla/5.0"
            }

            info_response = requests.get(info_url, headers=headers, timeout=3)

            if info_response.status_code == 200:
                info_data = info_response.json()
                if info_data["status"] == "OK":
                    current_handle = info_data["result"][0]["handle"]
                    if current_handle != cf_username:
                        print(f"Handle changed from {cf_username} to {current_handle}")
                        cf_username = current_handle
                else:
                    print(f"API Error for user.info: {info_data.get('comment', 'Unknown error')}")
            
            rating_url = f"https://codeforces.com/api/user.rating?handle={cf_username}"
            response = requests.get(rating_url, headers=headers, timeout=3)

            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code} when fetching rating history for {cf_username}")
                yearly_ratings['Codeforces_rating_2025'] = -1000
                yearly_ratings['Codeforces_rating_2024'] = -1000
                yearly_ratings['Codeforces_rating_2023'] = -1000
                yearly_ratings['Codeforces_rating_2022'] = -1000
                return yearly_ratings
            
            data = response.json()
            if data["status"] != "OK":
                print(f"API Error for rating history: {data.get('comment', 'Unknown error')}")
                yearly_ratings['Codeforces_rating_2025'] = -1000
                yearly_ratings['Codeforces_rating_2024'] = -1000
                yearly_ratings['Codeforces_rating_2023'] = -1000
                yearly_ratings['Codeforces_rating_2022'] = -1000
                return yearly_ratings
            
            for contest in data["result"]:
                timestamp = contest["ratingUpdateTimeSeconds"]
                year = pd.Timestamp.fromtimestamp(timestamp).year
                rating = contest["newRating"]

                if year == 2025:
                    yearly_ratings['Codeforces_rating_2025'] = max(
                        yearly_ratings['Codeforces_rating_2025'], 
                        rating
                    )
                
                if year == 2024:
                    yearly_ratings['Codeforces_rating_2024'] = max(
                        yearly_ratings['Codeforces_rating_2024'], 
                        rating
                    )
                elif year == 2023:
                    yearly_ratings['Codeforces_rating_2023'] = max(
                        yearly_ratings['Codeforces_rating_2023'], 
                        rating
                    )
                elif year == 2022:
                    yearly_ratings['Codeforces_rating_2022'] = max(
                        yearly_ratings['Codeforces_rating_2022'], 
                        rating
                    )
            
            if yearly_ratings['Codeforces_rating_2024'] == 0 and yearly_ratings['Codeforces_rating_2023'] > 0:
                print(f"No 2024 rating found for {cf_username}, using 2023 rating")
                yearly_ratings['Codeforces_rating_2024'] = yearly_ratings['Codeforces_rating_2023']
            if yearly_ratings['Codeforces_rating_2023'] == 0 and yearly_ratings['Codeforces_rating_2022'] > 0:
                print(f"No 2023 rating found for {cf_username}, using 2022 rating")
                yearly_ratings['Codeforces_rating_2023'] = yearly_ratings['Codeforces_rating_2022']
            if yearly_ratings['Codeforces_rating_2025'] == 0 and yearly_ratings['Codeforces_rating_2024'] > 0:
                print(f"No 2025 rating found for {cf_username}, using 2024 rating")
                yearly_ratings['Codeforces_rating_2025'] = yearly_ratings['Codeforces_rating_2024']
            
            print(f"Successfully fetched ratings for {cf_username}: {yearly_ratings}")
            return yearly_ratings
            
        except Exception as e:
            print(f"Error fetching Codeforces rating for {cf_username}: {e}")
            yearly_ratings['Codeforces_rating_2025'] = -1000
            yearly_ratings['Codeforces_rating_2024'] = -1000
            yearly_ratings['Codeforces_rating_2023'] = -1000
            yearly_ratings['Codeforces_rating_2022'] = -1000
            return yearly_ratings
    
    def add_contestant(self, contestant_data: Dict):
        """Add contestant to the database DataFrame.
        
        Args:
            contestant_data: Dictionary with contestant information
        """
        full_data = {col: contestant_data.get(col, None) for col in self.columns}
        self.df = pd.concat([self.df, pd.DataFrame([full_data])], ignore_index=True)
    
    def save_database(self):
        """Save database to CSV file."""
        try:
            self.df.to_csv(self.database_path, index=False)
            print(f"Database saved to {self.database_path}")
        except Exception as e:
            print(f"Error saving database: {e}")

    def update_contestant_competitions(self, name: str, country: str, competition: str):
        """Update existing contestant's competitions list.
        
        Args:
            name: Contestant name
            country: Contestant country
            competition: Competition name to add
            
        Returns:
            True if contestant found and updated, False otherwise
        """
        mask = (self.df['name'] == name) & (self.df['country'] == country)
        if any(mask):
            current_competitions = self.df.loc[mask, 'competitions'].iloc[0]
            if isinstance(current_competitions, str):
                competitions_list = eval(current_competitions)
            else:
                competitions_list = []
            
            if competition not in competitions_list:
                competitions_list.append(competition)
                self.df.loc[mask, 'competitions'] = str(competitions_list)
            return True
        return False
    
    def update_contestant_competitions_cfusername(self, codeforces_id: str, competition: str):
        """Update contestant's competitions list by Codeforces ID.
        
        Args:
            codeforces_id: Codeforces username
            competition: Competition name to add
            
        Returns:
            True if contestant found and updated, False otherwise
        """
        mask = self.df['codeforces_id'].str.lower() == codeforces_id.lower()
        if any(mask):
            current_competitions = self.df.loc[mask, 'competitions'].iloc[0]
            if isinstance(current_competitions, str):
                competitions_list = eval(current_competitions)
            else:
                competitions_list = []
            
            if competition not in competitions_list:
                competitions_list.append(competition)
                self.df.loc[mask, 'competitions'] = str(competitions_list)
            return True
        return False
                