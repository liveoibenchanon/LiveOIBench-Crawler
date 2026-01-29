import os
import re
import requests
import zipfile
import time
from urllib.parse import urljoin
from tqdm import tqdm
from bs4 import BeautifulSoup
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ioi_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class IOICrawler:
    def __init__(self, start_year=2002, end_year=2022, base_url="https://ioinformatics.org", 
                 output_dir=f"{os.environ['HOME_DIR']}/IOI-Bench/IOI-New", max_workers=4, delay=1.0):
        self.start_year = start_year
        self.end_year = end_year
        self.base_url = base_url
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.delay = delay
        
        # User agent to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make sure the base output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created base directory: {output_dir}")
    
    def discover_year_url(self, year):
        """
        Discover the correct URL for a given IOI year by trying different patterns
        """
        # Try different URL patterns
        url_patterns = [
            f"/page/ioi-{year}/",
            f"/page/ioi-{year}",
            f"/page/ioi{year}/",
            f"/page/ioi{year}",
            f"/page/ioi-{year}/56",
            f"/page/ioi-{year}/55",
            f"/page/ioi-{year}/28",
        ]
        
        for pattern in url_patterns:
            url = urljoin(self.base_url, pattern)
            
            try:
                logger.info(f"Trying URL: {url}")
                response = requests.get(url, headers=self.headers)
                
                if response.status_code == 200 and f"IOI {year}" in response.text:
                    logger.info(f"Found valid URL for IOI {year}: {url}")
                    return url
                
                time.sleep(self.delay)  # Be nice to the server
            except Exception as e:
                logger.error(f"Error checking URL {url}: {str(e)}")
        
        # If direct patterns fail, try searching
        search_url = f"{self.base_url}/search?q=IOI+{year}"
        try:
            logger.info(f"Direct URL not found, trying search: {search_url}")
            response = requests.get(search_url, headers=self.headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Look for links containing the year
                links = soup.find_all('a', href=True)
                for link in links:
                    if f"IOI {year}" in link.text or f"IOI-{year}" in link.text or f"IOI{year}" in link.text:
                        url = urljoin(self.base_url, link['href'])
                        logger.info(f"Found URL through search for IOI {year}: {url}")
                        return url
            
            time.sleep(self.delay)
        except Exception as e:
            logger.error(f"Error searching for IOI {year}: {str(e)}")
        
        # Try the "contests" page as a last resort
        contests_url = f"{self.base_url}/page/contests/10"
        try:
            logger.info(f"Trying to find from contests page: {contests_url}")
            response = requests.get(contests_url, headers=self.headers)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = soup.find_all('a', href=True)
                for link in links:
                    if f"IOI {year}" in link.text or f"IOI-{year}" in link.text or f"IOI{year}" in link.text:
                        url = urljoin(self.base_url, link['href'])
                        logger.info(f"Found URL through contests page for IOI {year}: {url}")
                        return url
        except Exception as e:
            logger.error(f"Error checking contests page for IOI {year}: {str(e)}")
        
        logger.warning(f"Could not find URL for IOI {year}")
        return None
    
    def clean_filename(self, filename):
        """
        Clean filename to remove whitespace and special characters
        """
        # Replace whitespace with underscore and remove special characters
        cleaned = re.sub(r'\s+', '_', filename)
        cleaned = re.sub(r'[^\w\-\.]', '', cleaned)
        return cleaned
    
    def is_day_problem_pdf(self, href, year):
        """
        Check if a link is a day problem PDF (problems 1-6)
        """
        problem_pattern = f"ioi{year}problem[1-6]"
        return re.search(problem_pattern, href, re.IGNORECASE) is not None
        
    def parse_year_page(self, url, year):
        """
        Parse the IOI year page to extract problem links and materials
        """
        materials = {
            "day1": [],
            "day2": [],
            "other": []
        }
        
        try:
            logger.info(f"Parsing page: {url}")
            response = requests.get(url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch page: {url}")
                return materials
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract Day 1, Day 2, and Other materials sections
            day1_section = soup.find(lambda tag: tag.name == "b" and "Day 1" in tag.text)
            day2_section = soup.find(lambda tag: tag.name == "b" and "Day 2" in tag.text)
            other_section = soup.find(lambda tag: tag.name == "b" and ("Other" in tag.text or "Materials" in tag.text))
            
            if not day1_section or not day2_section:
                logger.warning(f"Could not find Day 1 or Day 2 sections for IOI {year}")
                # Fallback: try to find links with problem filenames
                all_links = soup.find_all('a', href=True)
                for link in all_links:
                    href = link['href']
                    text = link.text.strip()
                    
                    # Clean the text for filename
                    clean_text = self.clean_filename(text)
                    
                    # Only day1 gets problems 1-3, only PDFs
                    if f"ioi{year}problem1" in href or f"ioi{year}problem2" in href or f"ioi{year}problem3" in href:
                        problem_num = re.search(r'problem(\d+)', href).group(1)
                        nice_name = f"{int(problem_num):02d}_{clean_text}.pdf"
                        materials["day1"].append((href, nice_name))
                    # Only day2 gets problems 4-6, only PDFs
                    elif f"ioi{year}problem4" in href or f"ioi{year}problem5" in href or f"ioi{year}problem6" in href:
                        problem_num = re.search(r'problem(\d+)', href).group(1)
                        adj_num = int(problem_num) - 3  # Adjust for day 2 (4→1, 5→2, 6→3)
                        nice_name = f"{adj_num:02d}_{clean_text}.pdf"
                        materials["day2"].append((href, nice_name))
                    # All zip files and other PDFs go to other_materials
                    elif f"ioi{year}tests" in href:
                        materials["other"].append((href, "TestCases.zip"))
                    elif f"ioi{year}solutions" in href:
                        materials["other"].append((href, "Solutions.zip"))
                    elif f"ioi{year}practice" in href:
                        materials["other"].append((href, "Practice.zip"))
                    # Other PDFs that are not day problems
                    elif href.endswith(".pdf") and not self.is_day_problem_pdf(href, year):
                        nice_name = f"{clean_text}.pdf"
                        materials["other"].append((href, nice_name))
            else:
                # Function to extract links from a section - with stricter categorization
                def extract_links_from_section(section, section_name):
                    links = []
                    if section:
                        # Get all links under this section until the next section
                        # (this is more robust than just getting next links)
                        if section_name == "day1":
                            end_section = day2_section if day2_section else other_section
                        elif section_name == "day2":
                            end_section = other_section
                        else:
                            end_section = None
                            
                        # Get all links between current section and next section
                        current_elem = section.next_element
                        section_links = []
                        
                        while current_elem and (end_section is None or current_elem != end_section):
                            if hasattr(current_elem, 'name') and current_elem.name == 'a' and current_elem.has_attr('href'):
                                section_links.append(current_elem)
                            current_elem = current_elem.next_element
                        
                        # Process found links
                        for i, link in enumerate(section_links):
                            href = link['href']
                            text = link.text.strip()
                            clean_text = self.clean_filename(text)
                            
                            # Categorize files based on section and file type
                            if section_name == "day1" and href.endswith(".pdf"):
                                if i < 3:  # Typically 3 problems per day
                                    nice_name = f"{i+1:02d}_{clean_text}.pdf"
                                    links.append((href, nice_name))
                            elif section_name == "day2" and href.endswith(".pdf"):
                                if i < 3:  # Typically 3 problems per day
                                    nice_name = f"{i+1:02d}_{clean_text}.pdf"
                                    links.append((href, nice_name))
                            elif section_name == "other":
                                if "tests" in href.lower() and href.endswith(".zip"):
                                    links.append((href, "TestCases.zip"))
                                elif "solution" in href.lower() and href.endswith(".zip"):
                                    links.append((href, "Solutions.zip"))
                                elif "practice" in href.lower() and href.endswith(".zip"):
                                    links.append((href, "Practice.zip"))
                                # Other PDFs
                                elif href.endswith(".pdf") and not self.is_day_problem_pdf(href, year):
                                    nice_name = f"{clean_text}.pdf"
                                    links.append((href, nice_name))
                    
                    return links
                
                # Extract links from each section
                materials["day1"] = extract_links_from_section(day1_section, "day1")
                materials["day2"] = extract_links_from_section(day2_section, "day2")
                materials["other"] = extract_links_from_section(other_section, "other")
                
                # If we failed to get links, try a different approach
                if not materials["day1"] and not materials["day2"]:
                    logger.warning(f"Could not extract links using primary method for IOI {year}, trying fallback...")
                    
                    # Fallback: look at all links with stricter categorization
                    all_links = soup.find_all('a', href=True)
                    for link in all_links:
                        href = link['href']
                        text = link.text.strip()
                        clean_text = self.clean_filename(text)
                        
                        # Only day1 gets problems 1-3, only PDFs
                        if f"ioi{year}problem1" in href or f"ioi{year}problem2" in href or f"ioi{year}problem3" in href:
                            problem_num = re.search(r'problem(\d+)', href).group(1)
                            nice_name = f"{int(problem_num):02d}_{clean_text}.pdf"
                            materials["day1"].append((href, nice_name))
                        # Only day2 gets problems 4-6, only PDFs
                        elif f"ioi{year}problem4" in href or f"ioi{year}problem5" in href or f"ioi{year}problem6" in href:
                            problem_num = re.search(r'problem(\d+)', href).group(1)
                            adj_num = int(problem_num) - 3  # Adjust for day 2
                            nice_name = f"{adj_num:02d}_{clean_text}.pdf"
                            materials["day2"].append((href, nice_name))
                        # All zip files go to other_materials
                        elif f"ioi{year}tests" in href:
                            materials["other"].append((href, "TestCases.zip"))
                        elif f"ioi{year}solutions" in href:
                            materials["other"].append((href, "Solutions.zip"))
                        elif f"ioi{year}practice" in href:
                            materials["other"].append((href, "Practice.zip"))
                        # Other PDFs that are not day problems
                        elif href.endswith(".pdf") and not self.is_day_problem_pdf(href, year):
                            nice_name = f"{clean_text}.pdf"
                            materials["other"].append((href, nice_name))
            
            # Log extraction results
            logger.info(f"Extracted links for IOI {year}:")
            logger.info(f"  Day 1: {len(materials['day1'])} problems")
            logger.info(f"  Day 2: {len(materials['day2'])} problems")
            logger.info(f"  Other: {len(materials['other'])} resources")
            
            return materials
            
        except Exception as e:
            logger.error(f"Error parsing page for IOI {year}: {str(e)}")
            return materials
    
    def download_file(self, url, save_path):
        """
        Download a file with progress bar and resume capability
        """
        full_url = url if url.startswith('http') else urljoin(self.base_url, url)
        
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Check if file already exists
        if os.path.exists(save_path):
            logger.info(f"File {save_path} already exists. Checking if complete...")
            try:
                response = requests.head(full_url, headers=self.headers)
                response.raise_for_status()
                remote_size = int(response.headers.get('content-length', 0))
                local_size = os.path.getsize(save_path)
                
                if local_size >= remote_size and remote_size > 0:
                    logger.info(f"File {save_path} is already completely downloaded.")
                    return True
                else:
                    logger.info(f"Resuming download of {full_url} from byte {local_size}...")
                    headers = self.headers.copy()
                    headers['Range'] = f'bytes={local_size}-'
                    mode = 'ab'  # append to the existing file
            except requests.exceptions.RequestException as e:
                logger.error(f"Error checking file size: {str(e)}")
                logger.info(f"Restarting download of {full_url}...")
                headers = self.headers
                mode = 'wb'  # write a new file
                local_size = 0
        else:
            logger.info(f"Downloading {full_url} to {save_path}...")
            headers = self.headers
            mode = 'wb'  # write a new file
            local_size = 0
        
        try:
            response = requests.get(full_url, stream=True, headers=headers)
            response.raise_for_status()
            
            # Get file size for progress bar
            total_size = int(response.headers.get('content-length', 0)) + local_size
            
            with open(save_path, mode) as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, 
                         desc=os.path.basename(save_path), initial=local_size) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:  # filter out keep-alive chunks
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            # Verify file was downloaded correctly
            if os.path.getsize(save_path) > 0:
                logger.info(f"Downloaded {save_path} successfully.")
                return True
            else:
                logger.error(f"Downloaded file {save_path} is empty.")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download {full_url}. Error: {str(e)}")
            return False
    
    def extract_zip(self, zip_path, extract_dir):
        """
        Extract a zip file with improved error handling
        """
        # Create extraction directory if it doesn't exist
        try:
            if not os.path.exists(extract_dir):
                os.makedirs(extract_dir)
                logger.info(f"Created extraction directory: {extract_dir}")
        except PermissionError:
            logger.error(f"Permission denied when creating directory: {extract_dir}")
            return False
        except Exception as e:
            logger.error(f"Error creating extraction directory {extract_dir}: {str(e)}")
            return False
        
        logger.info(f"Extracting {zip_path} to {extract_dir}...")
        
        try:
            # First verify the zip file is valid
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # Test zip file validity
                    if zip_ref.testzip() is not None:
                        logger.error(f"Zip file {zip_path} is corrupted")
                        return False
                    
                    # Get list of files for progress reporting
                    file_list = zip_ref.namelist()
                    
                    # Extract files with progress bar
                    for file in tqdm(file_list, desc="Extracting"):
                        try:
                            zip_ref.extract(file, extract_dir)
                        except Exception as e:
                            logger.error(f"Error extracting file {file}: {str(e)}")
                            # Continue with other files
                            continue
            except zipfile.BadZipFile:
                logger.error(f"File {zip_path} is not a valid zip file")
                return False
            
            logger.info(f"Extracted {zip_path} successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to extract {zip_path}: {str(e)}")
            return False
    
    def process_year(self, year):
        """
        Process a single IOI year
        """
        logger.info(f"Processing IOI {year}...")
        
        # Create year directory in the specified path format
        year_dir = os.path.join(self.output_dir, str(year))
        if not os.path.exists(year_dir):
            os.makedirs(year_dir)
            logger.info(f"Created year directory: {year_dir}")
        
        # Discover the URL for this year
        url = self.discover_year_url(year)
        if not url:
            logger.warning(f"Could not find URL for IOI {year}, skipping...")
            return False
        
        # Parse the page to extract links
        materials = self.parse_year_page(url, year)
        
        # If no materials were found, skip this year
        if not materials["day1"] and not materials["day2"] and not materials["other"]:
            logger.warning(f"No materials found for IOI {year}, skipping...")
            return False
        
        # Create subdirectories
        directories = {
            "day1": os.path.join(year_dir, "day1"),
            "day2": os.path.join(year_dir, "day2"),
            "other": os.path.join(year_dir, "other_materials")
        }
        
        for dir_name, dir_path in directories.items():
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                logger.info(f"Created directory: {dir_path}")
        
        # Download files for each category
        download_tasks = []
        
        for category, files in materials.items():
            for url, filename in files:
                save_path = os.path.join(directories[category], filename)
                download_tasks.append((url, save_path, category, filename))
        
        # Use ThreadPoolExecutor for parallel downloads
        success_count = 0
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit download tasks
            future_to_task = {
                executor.submit(self.download_file, url, save_path): (save_path, category, filename)
                for url, save_path, category, filename in download_tasks
            }
            
            # Process completed downloads
            for future in as_completed(future_to_task):
                save_path, category, filename = future_to_task[future]
                try:
                    success = future.result()
                    if success:
                        success_count += 1
                        
                        # Extract zip files - ONLY for files in other_materials category
                        if filename.endswith('.zip') and category == "other":
                            # Extract to a folder under other_materials
                            extract_dir = os.path.join(directories["other"], os.path.splitext(filename)[0])
                            self.extract_zip(save_path, extract_dir)
                except Exception as e:
                    logger.error(f"Error processing {save_path}: {str(e)}")
        
        logger.info(f"Completed processing IOI {year}. Downloaded {success_count}/{len(download_tasks)} files.")
        return success_count > 0
    
    def run(self):
        """
        Run the crawler for all years in the specified range
        """
        logger.info(f"Starting IOI crawler for years {self.start_year} to {self.end_year}")
        logger.info(f"Files will be saved to: {self.output_dir}/<year>")
        
        results = {}
        for year in range(self.start_year, self.end_year + 1):
            results[year] = self.process_year(year)
            time.sleep(self.delay)  # Be nice to the server between years
        
        # Print summary
        logger.info("\n--- Crawler Summary ---")
        successful = 0
        for year, success in results.items():
            status = "✓ Success" if success else "✗ Failed"
            logger.info(f"IOI {year}: {status}")
            if success:
                successful += 1
        
        logger.info(f"\nSuccessfully processed {successful}/{len(results)} years.")
        logger.info(f"All materials saved to: {os.path.abspath(self.output_dir)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download IOI problems and materials for multiple years')
    parser.add_argument('--start', type=int, default=2002, help='Start year (default: 2002)')
    parser.add_argument('--end', type=int, default=2022, help='End year (default: 2022)')
    parser.add_argument('--output', default=f'{os.environ["HOME_DIR"]}/IOI-Bench/IOI-New', help='Base output directory')
    parser.add_argument('--workers', type=int, default=4, help='Maximum number of concurrent downloads (default: 4)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests in seconds (default: 1.0)')
    
    args = parser.parse_args()
    
    crawler = IOICrawler(
        start_year=args.start,
        end_year=args.end,
        output_dir=args.output,
        max_workers=args.workers,
        delay=args.delay
    )
    
    crawler.run()