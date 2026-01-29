import tempfile
import os
import time
import argparse
import requests
from bs4 import BeautifulSoup
from multiprocessing import Pool, cpu_count
from datetime import datetime as now
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from tqdm import tqdm

def setup_driver(headless=True, download_dir=None):
    """Initialize Chrome WebDriver with configurable headless setting and download path"""
    tmp_profile = tempfile.mkdtemp(prefix="selenium-profile-")
    opts = Options()
    opts.add_argument(f"--user-data-dir={tmp_profile}")
    opts.add_argument("--disable-gpu")
    
    # Configure download settings if directory is specified
    if download_dir:
        prefs = {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": False
        }
        opts.add_experimental_option("prefs", prefs)
    
    if headless:
        opts.add_argument("--headless=new")  # use faster new headless mode
    
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-dev-shm-usage")
    service = Service()
    return webdriver.Chrome(service=service, options=opts)

def download_problem_files(html_content, problem_id, output_dir):
    """Download all test files from problem files page"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Create directory for test files
    files_dir = os.path.join(output_dir, f"problem_{problem_id}_files")
    os.makedirs(files_dir, exist_ok=True)
    
    # Find all file rows in the table
    file_rows = soup.select("table.table tbody tr")
    
    downloaded_count = 0
    total_size = 0
    
    print(f"Found {len(file_rows)} files to download")
    
    for row in file_rows:
        try:
            # Extract filename from the first column
            filename_div = row.select_one("div._filename_r2613_17")
            if not filename_div:
                continue
                
            # Get the filename text (skip any hidden chars)
            filename = filename_div.get_text(strip=True)
            
            # Skip if no filename found
            if not filename:
                continue
            
            # Get file size from second column
            size_col = row.select_one("td.center.aligned:nth-of-type(2)")
            file_size = size_col.get_text(strip=True) if size_col else "Unknown"
            
            # Check if this row has a download icon
            download_icon = row.select_one("i.download.icon")
            if not download_icon:
                continue
            
            # In LibreOJ, the download link is constructed with the problem ID and filename
            download_url = f"https://api.loj.ac/api/problem/downloadFile"
            params = {
                "problemId": problem_id,
                "filename": filename,
                "type": "testdata"
            }
            
            file_path = os.path.join(files_dir, filename)
            
            print(f"Downloading {filename} ({file_size})...")
            
            # Make request to download file
            response = requests.get(download_url, params=params, stream=True)
            
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                actual_size = os.path.getsize(file_path)
                total_size += actual_size
                downloaded_count += 1
                print(f"Saved: {file_path} ({actual_size} bytes)")
            else:
                print(f"Failed to download {filename}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Error downloading file: {e}")
    
    print(f"Downloaded {downloaded_count} files ({total_size} bytes total) to {files_dir}")
    return downloaded_count

def is_download_finished(download_dir):
    """Check if all downloads in directory have completed"""
    # Look for temporary Chrome download files
    for filename in os.listdir(download_dir):
        if filename.endswith('.crdownload') or filename.endswith('.part'):
            return False
    return True

def wait_for_downloads(download_dir, timeout=300, check_interval=2):
    """Wait for all downloads to complete with timeout"""
    start_time = time.time()
    print(f"Waiting for downloads to complete in {download_dir}...")
    
    # First wait for downloads to start (look for any .crdownload or .part files)
    download_started = False
    while time.time() - start_time < 30:  # 30 second timeout for downloads to start
        for filename in os.listdir(download_dir):
            if filename.endswith('.crdownload') or filename.endswith('.part'):
                download_started = True
                print("Download started, waiting for completion...")
                break
        if download_started:
            break
        time.sleep(1)
    
    if not download_started:
        # Check if there are already completed ZIP files (download was very fast)
        zip_files = [f for f in os.listdir(download_dir) if f.endswith('.zip')]
        if zip_files:
            print(f"Found {len(zip_files)} already completed zip files")
            return True
        print("Warning: No downloads detected")
        return False
    
    # Now wait for downloads to finish
    while time.time() - start_time < timeout:
        if is_download_finished(download_dir):
            elapsed = time.time() - start_time
            print(f"All downloads completed in {elapsed:.1f} seconds")
            return True
        time.sleep(check_interval)
    
    print(f"Download timeout after {timeout} seconds!")
    return False

def _download_files_from_table(driver, table, section_name, download_dir):
    """Helper function to download files from a specific table section"""
    try:
        # Check if this section has any files
        no_files = table.find_elements(By.CSS_SELECTOR, "._filesTableNoFiles_r2613_48")
        if no_files:
            print(f"No files found in {section_name} section")
            return 0
            
        # Find the checkbox in this table's header
        select_all = table.find_element(By.CSS_SELECTOR, "th .ui.fitted.checkbox input")
        driver.execute_script("arguments[0].click();", select_all)
        
        # Get file count from the table
        file_rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        if not file_rows:
            print(f"No file rows found in {section_name} section")
            return 0
            
        print(f"Selected {len(file_rows)} files in {section_name}")
        
        # Wait for selection info to appear
        footer_info = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "._fileTableFooterInfo_r2613_78"))
        )
        
        # Find dropdown near the footer info
        # First check if there's a dropdown directly after this element
        dropdown = None
        try:
            dropdown_parent = footer_info.find_element(By.XPATH, "./parent::th/parent::tr")
            dropdown = WebDriverWait(dropdown_parent, 3).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui.dropdown"))
            )
        except:
            # If we can't find the dropdown directly, look for it near the selection info
            dropdown_candidates = driver.find_elements(By.CSS_SELECTOR, ".ui.dropdown")
            for candidate in dropdown_candidates:
                if candidate.is_displayed():
                    dropdown = candidate
                    break
        
        if dropdown:
            # Click the dropdown to show the options
            driver.execute_script("arguments[0].click();", dropdown)
            print(f"Clicked dropdown for {section_name}")
            
            # Find the download archive option
            download_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@role='option']//i[contains(@class,'download')]/.."))
            )
            driver.execute_script("arguments[0].click();", download_option)
            print(f"Clicked 'Download as Archive' for {section_name}")
            
            # Calculate minimum wait based on file size (for very small files)
            footer_text = footer_info.text
            size_text = footer_text.split(", ")[1] if ", " in footer_text else "0 B"
            print(f"Total size: {size_text}")
            
            # Return file count for reporting
            return len(file_rows)
        else:
            print(f"No dropdown found for {section_name}, possibly no files selected")
            return 0
    
    except Exception as e:
        print(f"Error processing {section_name} section: {e}")
        return 0

def download_all_files(driver, problem_id, output_dir):
    """Download all files (both test data and additional files if available) as archives"""
    try:
        # Wait for the page to load completely
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr"))
        )
        
        # Create directory for files
        files_dir = os.path.join(output_dir, f"problem_{problem_id}_files")
        os.makedirs(files_dir, exist_ok=True)
        
        # First process Test Data table
        print("Processing Test Data section...")
        test_data_table = driver.find_element(By.CSS_SELECTOR, "table.green.table")
        test_count = _download_files_from_table(driver, test_data_table, "Test Data", files_dir)
        
        # Then process Additional Files table if it has files
        print("Processing Additional Files section...")
        additional_table = driver.find_element(By.CSS_SELECTOR, "table.pink.table") 
        add_count = _download_files_from_table(driver, additional_table, "Additional Files", files_dir)
        
        # Wait for all downloads to complete
        if test_count > 0 or add_count > 0:
            wait_for_downloads(files_dir, timeout=1200)  # Wait up to 20 minutes
        
        return test_count + add_count
    except Exception as e:
        print(f"Error in batch download: {e}")
        return 0

def fetch_webpage(item):
    """Generic function to fetch different types of webpages"""
    item_id, output_dir, fetch_type, download_files, headless = item
    
    # Set URL based on fetch type
    if fetch_type == "submission":
        url = f"https://loj.ac/s/{item_id}"
        file_prefix = "submission"
    elif fetch_type == "problem-files":
        url = f"https://loj.ac/p/{item_id}/files"
        file_prefix = "problem"
    elif fetch_type == "problem":
        url = f"https://loj.ac/p/{item_id}"
        file_prefix = "problem"
    else:
        raise ValueError(f"Unknown fetch type: {fetch_type}")
    
    # Create a dedicated folder for each problem-files, but not for submissions
    if fetch_type == "problem-files":
        item_folder = os.path.join(output_dir, f"problem_{item_id}")
        os.makedirs(item_folder, exist_ok=True)
        
        # Create and open log file
        log_path = os.path.join(item_folder, "download.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(f"=== Log for problem {item_id} ===\n")
            log_file.write(f"Started: {now.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            log_file.write(f"URL: {url}\n\n")
            
            # Set up download directory inside the problem folder
            if download_files:
                files_dir = os.path.join(item_folder, "files")
                os.makedirs(files_dir, exist_ok=True)
                log_file.write(f"Download directory: {files_dir}\n")
                driver = setup_driver(headless=headless, download_dir=os.path.abspath(files_dir))
            else:
                log_file.write("File download disabled\n")
                driver = setup_driver(headless=headless)
                files_dir = None
            
            try:
                driver.get(url)
                log_file.write(f"Visiting: {url}\n")
                print(f"Visiting: {url}")

                # Wait for page to fully load
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(5)  # Wait for React content to load
                log_file.write("Page load complete\n")

                # Save the HTML content
                rendered_html = driver.execute_script("return document.documentElement.outerHTML;")
                html_path = os.path.join(item_folder, "page.html")
                with open(html_path, "w", encoding="utf-8") as f:
                    f.write(rendered_html)
                log_file.write(f"Saved HTML to: {html_path}\n")
                print(f"Saved: {html_path}")
                
                # Download files if requested for problem-files
                if download_files:
                    log_file.write("\n=== Starting file downloads ===\n")
                    
                    # Capture download output for logging
                    try:
                        # Wait for the page to load completely
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table.table tbody tr"))
                        )
                        
                        # Process Test Data table
                        log_file.write("\nProcessing Test Data section...\n")
                        print("Processing Test Data section...")
                        test_data_table = driver.find_element(By.CSS_SELECTOR, "table.green.table")
                        test_count = _download_files_from_table(driver, test_data_table, "Test Data", files_dir)
                        log_file.write(f"Selected {test_count} test data files\n")
                        
                        # Process Additional Files table
                        log_file.write("\nProcessing Additional Files section...\n")
                        print("Processing Additional Files section...")
                        additional_table = driver.find_element(By.CSS_SELECTOR, "table.pink.table") 
                        add_count = _download_files_from_table(driver, additional_table, "Additional Files", files_dir)
                        log_file.write(f"Selected {add_count} additional files\n")
                        
                        # Wait for all downloads to complete
                        if test_count > 0 or add_count > 0:
                            log_file.write("\nWaiting for downloads to complete...\n")
                            wait_result = wait_for_downloads(files_dir, timeout=1200)  # Wait up to 20 minutes
                            if wait_result:
                                log_file.write("All downloads completed successfully\n")
                            else:
                                log_file.write("WARNING: Download timeout or error\n")
                                
                        # Log downloaded files
                        if os.path.exists(files_dir):
                            downloaded_files = os.listdir(files_dir)
                            log_file.write(f"\nFiles in download directory ({len(downloaded_files)}):\n")
                            for f in downloaded_files:
                                file_path = os.path.join(files_dir, f)
                                if os.path.isfile(file_path):
                                    size = os.path.getsize(file_path)
                                    log_file.write(f"- {f} ({size} bytes)\n")
                        
                        log_file.write(f"\nDownloaded {test_count + add_count} files in total\n")
                        print(f"Downloaded {test_count + add_count} files in total")
                        
                    except Exception as e:
                        error_msg = f"Error during download: {str(e)}"
                        log_file.write(f"\n{error_msg}\n")
                        print(error_msg)
                
            except Exception as e:
                error_msg = f"Error processing problem {item_id}: {str(e)}"
                log_file.write(f"\n{error_msg}\n")
                print(error_msg)
            finally:
                log_file.write(f"\nCompleted: {now.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                driver.quit()
    else:
        # For submissions, keep the original structure
        item_folder = output_dir
        driver = setup_driver(headless=headless)
        
        try:
            driver.get(url)
            print(f"Visiting: {url}")

            # Wait for page to fully load
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            time.sleep(5)  # Wait for React content to load

            # Save the HTML content
            rendered_html = driver.execute_script("return document.documentElement.outerHTML;")
            html_path = os.path.join(item_folder, f"{file_prefix}_{item_id}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(rendered_html)
            print(f"Saved: {html_path}")
        except Exception as e:
            print(f"Error processing {file_prefix} {item_id}: {e}")
        finally:
            driver.quit()
    
    return item_id

def read_ids_from_file(file_path):
    """Read IDs from a file, one ID per line, ignore empty lines and comments"""
    with open(file_path, 'r') as f:
        ids = []
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                ids.append(line)
        return ids

def main():
    parser = argparse.ArgumentParser(description='Fetch content from LOJ website')
    
    parser.add_argument('--type', '-t', choices=['submission', 'problem', 'problem-files'], 
                        required=True, help='Type of content to fetch')
    
    id_group = parser.add_mutually_exclusive_group(required=True)
    id_group.add_argument('--ids', '-i', nargs='+', help='List of IDs to process')
    id_group.add_argument('--file', '-f', help='File containing IDs (one per line)')
    
    parser.add_argument('--output-dir', '-o', default='rendered_output',
                        help='Directory to save output files')
    parser.add_argument('--workers', '-w', type=int, default=6,
                        help='Number of parallel workers')
    parser.add_argument('--wait', type=int, default=5,
                        help='Wait time after page load (seconds)')
    parser.add_argument('--download-files', action='store_true',
                        help='Download problem files if fetching problem-files')
    parser.add_argument('--no-headless', action='store_true',
                        help='Disable headless mode (show browser window)')
    parser.add_argument('--no-progress', action='store_true',
                        help='Disable progress bar')
    
    args = parser.parse_args()
    
    # Get IDs from file or command line
    if args.file:
        ids = read_ids_from_file(args.file)
    else:
        ids = args.ids
    
    # Create output directory based on type
    output_dir = os.path.join(args.output_dir, args.type)
    os.makedirs(output_dir, exist_ok=True)
    
    # Create tasks list
    tasks = [(item_id, output_dir, args.type, args.download_files, not args.no_headless) 
             for item_id in ids]
    
    print(f"Starting to fetch {len(tasks)} {args.type} pages...")
    start_time = now.now()
    
    # Choose number of parallel processes
    num_workers = min(args.workers, cpu_count())
    print(f"Using {num_workers} workers")
    
    # Process tasks with or without progress bar
    if args.no_progress:
        # Process without progress bar
        with Pool(num_workers) as pool:
            results = pool.map(fetch_webpage, tasks)
    else:
        # Process with progress bar that updates as each task completes
        completed_items = []
        with Pool(num_workers) as pool:
            # Create a progress bar that updates with completed items
            with tqdm(total=len(tasks), desc=f"Fetching {args.type}", unit="item") as pbar:
                # Use imap_unordered to get results as they complete (not in order)
                for result in pool.imap_unordered(fetch_webpage, tasks):
                    completed_items.append(result)
                    pbar.update(1)
                    pbar.set_postfix({"latest": result}, refresh=True)
            results = completed_items
    
    print(f"All tasks completed in {now.now() - start_time}")
    print(f"Processed {len(results)} items: {', '.join(str(r) for r in results[:5])}" + 
          ("..." if len(results) > 5 else ""))

if __name__ == "__main__":
    main()