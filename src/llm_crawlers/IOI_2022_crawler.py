import requests
from bs4 import BeautifulSoup
import os
from pathlib import Path
import zipfile
from urllib.parse import urljoin, urlparse
import re
import time
import logging

# --- Configuration ---
# The path to the local HTML file provided.
HTML_FILE_PATH = f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI/htmls/2022.html'
# The base URL of the original web page. This is crucial for resolving relative links
# found within the downloaded HTML file correctly.
BASE_URL = 'https://ioi.te.lv/locations/ioi22/contest/'
# The root directory where the crawled data will be saved.
OUTPUT_ROOT_DIR = Path(f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI/2022')

# --- Logging Setup ---
# Set up basic logging to see progress and errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---

def sanitize_filename(name):
    """
    Sanitizes a string to be used as a filename or directory name.
    Removes characters not allowed or problematic in file paths and replaces spaces/underscores.
    """
    if not name:
        return "untitled"
    # Remove characters that are not alphanumeric, underscore, hyphen, or dot
    sanitized = re.sub(r'[^\w\s\.\-]', '', name)
    # Replace spaces and multiple underscores/hyphens with a single underscore
    sanitized = re.sub(r'[\s_-]+', '_', sanitized)
    # Remove leading/trailing underscores/hyphens/dots
    sanitized = sanitized.strip('_.')
    # Ensure it's not empty after sanitization
    if not sanitized:
        return "untitled" + str(int(time.time())) # Fallback to a unique name
    return sanitized

def download_file(url, destination_path, retries=3):
    """
    Downloads a file from a given URL to a destination path.
    Includes basic error handling and retries.
    """
    logging.info(f"Attempting to download {url}")
    logging.info(f"Saving to {destination_path}")

    # Ensure parent directory exists
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(retries):
        try:
            # Use stream=True to handle large files efficiently
            response = requests.get(url, stream=True, timeout=60) # Added a reasonable timeout
            response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)

            with open(destination_path, 'wb') as f:
                # Write file in chunks
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk: # Filter out keep-alive new chunks
                        f.write(chunk)

            logging.info(f"Successfully downloaded {destination_path.name}")
            return True

        except requests.exceptions.RequestException as e:
            logging.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
            if attempt < retries - 1:
                time.sleep(2 ** attempt) # Exponential backoff before retrying
            else:
                logging.error(f"Failed to download {url} after {retries} attempts.")
                return False
        except IOError as e:
            logging.error(f"Error writing file {destination_path}: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred during download of {url}: {e}")
            return False

def unzip_file(zip_path, dest_dir):
    """
    Unzips a zip file to a specified destination directory.
    Includes error handling.
    """
    logging.info(f"Attempting to unzip {zip_path} to {dest_dir}")

    if not zip_path.exists():
        logging.warning(f"Zip file not found for unzipping at {zip_path}")
        return False

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Basic check to prevent Zip Slip vulnerability (though zipfile is relatively safe)
            # Ensure extracted path is inside dest_dir
            for file_info in zip_ref.infolist():
                extracted_path = dest_dir / file_info.filename
                if not str(extracted_path).startswith(str(dest_dir)):
                     raise ZipSlipError("Attempted path traversal detected in zip file!")
            zip_ref.extractall(dest_dir)
        logging.info(f"Successfully unzipped {zip_path.name} to {dest_dir}")

        # Optionally remove the zip file after successful extraction
        # Consider whether you want to keep the zip file or remove it.
        # For this request, let's remove it as per common practice after unzipping.
        try:
            os.remove(zip_path)
            logging.info(f"Removed original zip file: {zip_path.name}")
        except OSError as e:
             logging.warning(f"Could not remove zip file {zip_path}: {e}")

        return True

    except zipfile.BadZipFile:
        logging.error(f"Error: {zip_path} is not a valid zip file.")
        return False
    except ZipSlipError as e:
        logging.error(f"Security error unzipping {zip_path}: {e}")
        return False
    except Exception as e:
        logging.error(f"An unexpected error occurred during unzipping {zip_path}: {e}")
        return False

class ZipSlipError(Exception):
    """Custom exception for Zip Slip vulnerability detection."""
    pass


# --- Main Crawler Logic ---

def crawl_ioi2022():
    """
    Reads the local IOI 2022 HTML file, parses it, and downloads associated files
    organized by day and problem.
    """
    logging.info(f"Starting IOI 2022 data crawl from {HTML_FILE_PATH}")

    # Create root output directory if it doesn't exist
    OUTPUT_ROOT_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"Ensured output directory exists: {OUTPUT_ROOT_DIR}")

    # Read the local HTML file
    try:
        # Use 'utf-8' as a common encoding for web pages
        with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
            html_content = f.read()
        logging.info(f"Successfully read HTML file: {HTML_FILE_PATH}")
    except FileNotFoundError:
        logging.error(f"Error: HTML file not found at {HTML_FILE_PATH}")
        return
    except Exception as e:
        logging.error(f"Error reading HTML file {HTML_FILE_PATH}: {e}")
        return

    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'html.parser')
    logging.info("HTML parsed successfully.")

    # --- Locate Day Sections and Problems ---
    # This is the most structure-dependent part. We need to find elements
    # that represent the different competition days (Day 0, Day 1, Day 2)
    # and then find elements within those sections that represent individual problems.

    # A common pattern is using IDs or classes to mark sections.
    # Let's try finding sections based on common naming conventions or structure
    # observed on similar contest sites.
    # If the actual HTML structure is different, this section needs adjustment.

    # Find all potential day sections. Look for elements that might contain
    # day identifiers or group problems by day.
    # This selector is an educated guess; inspect the actual HTML if it fails.
    # Example: divs with specific IDs or classes, or maybe headings.
    potential_day_sections = soup.find_all(lambda tag:
        tag.name in ['div', 'section', 'article'] and (
            re.search(r'(^|\s)day[-_]?0($|\s)', tag.get('id', '') + ' ' + (' '.join(tag.get('class', [])))) or
            re.search(r'(^|\s)day[-_]?1($|\s)', tag.get('id', '') + ' ' + (' '.join(tag.get('class', [])))) or
            re.search(r'(^|\s)day[-_]?2($|\s)', tag.get('id', '') + ' ' + (' '.join(tag.get('class', []))))
        ) or (tag.name in ['h2', 'h3'] and re.search(r'Day\s*[012]', tag.get_text()))
    )

    if not potential_day_sections:
        logging.error("Could not identify potential day sections in the HTML. Please inspect the HTML structure.")
        # Fallback: search the whole document for problems if days aren't clearly sectioned
        all_problem_blocks = soup.find_all(lambda tag: tag.find(['h3', 'h4', 'strong']) and tag.find('a'))
        if all_problem_blocks:
             logging.warning("Proceeding without explicit day sections, inferring structure.")
             # This fallback will treat all problems found as if they are under a single 'unknown_day' or try to infer day?
             # Let's refine the logic to group by inferred day if possible.
             # For now, if no day sections are found, we cannot fulfill the dayX structure requirement well.
             # Let's exit and ask the user to check the structure.
             return
        else:
             logging.error("No problem blocks found in the HTML. Please check the HTML structure.")
             return


    logging.info(f"Found {len(potential_day_sections)} potential day sections.")

    # Process each potential day section
    for day_section in potential_day_sections:
        # Attempt to determine the day number (0, 1, 2) from the section's ID, class, or heading
        day_match = re.search(r'day[-_]?([012])', day_section.get('id', '') + ' ' + ' '.join(day_section.get('class', [])))
        if not day_match:
             day_heading = day_section.find(['h2', 'h3'], text=re.compile(r'Day\s*[012]', re.IGNORECASE))
             if day_heading:
                 day_match = re.search(r'([012])', day_heading.get_text())

        day_number_str = day_match.group(1) if day_match else 'unknown' # Default to 'unknown'
        day_folder_name = f'day{day_number_str}'
        day_output_dir = OUTPUT_ROOT_DIR / day_folder_name
        day_output_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"\n--- Processing {day_folder_name} ---")

        # Find individual problem blocks within this day section.
        # Look for elements that contain a problem name (e.g., h3, strong) and associated links.
        # This selector is another critical assumption about the HTML structure.
        # Example: Look for list items (li) or divs that contain links relevant to a problem.
        problem_blocks = day_section.select('li.problem-item, div.problem-block, tr.problem-row, div:has(a[href*="problems"])')

        if not problem_blocks:
            # Fallback: Find any elements containing links, hoping they group problems.
            # This might pick up extraneous links, but better than nothing.
            problem_blocks = day_section.find_all(lambda tag: tag.find_all('a', href=True))
            if problem_blocks:
                logging.warning(f"Could not find specific problem block selectors in {day_folder_name}. Falling back to finding elements with any links.")
            else:
                logging.warning(f"Could not identify individual problem blocks within {day_folder_name}. No problems found for this day section.")
                continue # Move to the next day section

        logging.info(f"Found {len(problem_blocks)} potential problem blocks in {day_folder_name}.")

        # Process each problem block
        for problem_block in problem_blocks:
            # Attempt to extract the problem name
            # Look for headings (h3, h4), strong tags, or text near the first link
            problem_name = "untitled_problem"
            name_tag = problem_block.find(['h3', 'h4', 'strong'])
            if name_tag:
                 problem_name = name_tag.get_text(strip=True)

            # If name still generic or not found, try siblings or parent text near links?
            # This is complex and error-prone without the actual HTML.
            # Let's use a fallback based on the first link text if name is still generic.
            if problem_name in ["", "untitled_problem"]:
                 first_link = problem_block.find('a', href=True)
                 if first_link:
                     # Use part of the link text or URL path as a hint for the name
                     link_text_hint = first_link.get_text(strip=True)
                     if link_text_hint and len(link_text_hint) < 50: # Avoid using long texts as names
                          problem_name = link_text_hint.split()[0] # Take the first word
                     elif 'href' in first_link.attrs:
                          parsed_url = urlparse(urljoin(BASE_URL, first_link['href']))
                          # Look for a segment in the path that might be the problem slug
                          path_segments = [seg for seg in parsed_url.path.split('/') if seg]
                          if 'problems' in path_segments:
                              try:
                                  problem_slug_index = path_segments.index('problems') + 1
                                  if problem_slug_index < len(path_segments):
                                      problem_name = path_segments[problem_slug_index]
                              except ValueError:
                                  pass # 'problems' not in path segments

            # Sanitize the problem name
            problem_name = sanitize_filename(problem_name)
            if problem_name == "untitled_problem": # Add a unique ID if still generic
                 problem_name += "_" + str(abs(hash(str(problem_block)[:500]))) # Use a hash of block content as unique id part

            logging.info(f"\nProcessing problem: {problem_name} in {day_folder_name}")
            problem_output_dir = day_output_dir / problem_name
            problem_output_dir.mkdir(parents=True, exist_ok=True)

            # Find all links within this problem block
            links = problem_block.find_all('a', href=True)

            downloaded_statement_en = False # Flag to download only one English statement

            for link in links:
                href = link['href']
                # Construct the full URL by joining with the base URL
                full_url = urljoin(BASE_URL, href)
                link_text = link.get_text(strip=True)

                # Extract the proposed filename from the URL
                parsed_url = urlparse(full_url)
                path = parsed_url.path
                # Get the last segment of the path as the filename
                filename = Path(path).name

                # If the URL ends with a /, try to guess filename from link text or default
                if not filename:
                    # Simple guess from link text (e.g., "Download Tests" -> "Tests")
                    filename = sanitize_filename(link_text.split()[0]) + "_file" if link_text else "downloaded_file"
                    logging.warning(f"URL {full_url} has no filename. Guessed filename: {filename}")


                destination_path = problem_output_dir / filename

                # --- Filtering and Logic for Downloading ---

                # Identify if the link points to a statement and its language
                is_statement = re.search(r'statement|problem', link_text, re.IGNORECASE) or re.search(r'/problems/.*?\.pdf$', path, re.IGNORECASE)
                is_english = re.search(r'english|en', link_text, re.IGNORECASE) or re.search(r'\.en\.pdf$', path, re.IGNORECASE) or 'statement.pdf' in filename.lower() # Assume 'statement.pdf' is English if no other language indicated

                if is_statement:
                    if is_english:
                        if not downloaded_statement_en:
                            logging.info(f"Found English Statement: {link_text} ({full_url})")
                            # Rename generic statement.pdf to problem_name_statement.pdf for clarity?
                            # Or just keep original filename inside the problem directory. Let's keep original.
                            success = download_file(full_url, destination_path)
                            if success:
                                downloaded_statement_en = True # Mark as downloaded
                        else:
                            logging.info(f"Skipping extra English statement link: {link_text} ({full_url})")
                    else:
                        logging.info(f"Skipping non-English statement: {link_text} ({full_url})")
                    continue # Move to the next link after handling statements

                # Download other file types (tests, solutions, graders, attachments, etc.)
                logging.info(f"Found other resource link: {link_text} ({full_url})")
                success = download_file(full_url, destination_path)

                if success:
                    # Check if the downloaded file is a zip archive
                    if destination_path.suffix.lower() == '.zip':
                        # Create a specific directory for the extracted contents based on the zip filename
                        extract_dir = problem_output_dir / destination_path.stem # e.g., tests.zip -> tests
                        unzip_file(destination_path, extract_dir)

                # Add a small delay between downloads to be polite
                time.sleep(0.5)

    logging.info("\nIOI 2022 data crawling process finished.")

# --- Run the crawler ---
if __name__ == "__main__":
    crawl_ioi2022()