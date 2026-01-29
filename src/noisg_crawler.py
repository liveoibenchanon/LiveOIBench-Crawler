from base_crawler import Crawler
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
from git import Repo

class NOISGCrawler(Crawler):
    def __init__(self, *, competition="NOI_SG", path):
        super().__init__(competition=competition, path=path)
        self.base_url = ""
    def crawl(self):
        github_url = "https://github.com/noisg/sg_noi_archive.git"
        url_by_years = {
            "2022": ["https://github.com/noisg/noi_2022_finals"],
            "2023": ["https://github.com/noisg/noi_2023"],
            "2024": ["https://github.com/noisg/noi-2024-prelim", "https://github.com/noisg/noi-2024-final"],
            "2025": ["https://github.com/noisg/noi-2025-prelim"]
        }
        os.makedirs(self._path, exist_ok=True)
        #Repo.clone_from(github_url, self._path)
        for year, urls in url_by_years.items():
            os.makedirs(f"{self._path}/{year}", exist_ok=True)
            for url in urls:
                try:
                    if "finals" in url:
                        Repo.clone_from(url, f"{self._path}/{year}/finals")
                        print(f"Cloned {url} to {self._path}/{year}/finals")
                    elif "prelim" in url:
                        Repo.clone_from(url, f"{self._path}/{year}/prelim")
                        print(f"Cloned {url} to {self._path}/{year}/prelim")
                    else:
                        Repo.clone_from(url, f"{self._path}/{year}")
                        print(f"Cloned {url} to {self._path}/{year}")
                except Exception as e:
                    print(f"Failed to clone {url}: {e}")
    def parse(self):
        pass