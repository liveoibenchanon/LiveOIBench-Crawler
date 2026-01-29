from base_crawler import Crawler
from utils import *
from bs4 import BeautifulSoup
import re
import concurrent.futures
from tqdm import tqdm  # progress bar
from git import Repo
class NOINordicCrawler(Crawler):
    def __init__(self, *, competition="NOI_Nordic", path):
        super().__init__(competition=competition, path=path)
        self.base_url = "https://nordic.progolymp.se/"
    def _download_tasks(self):
        base_git = "https://github.com/nordicolympiad/nordic-olympiad-YEAR.git"
        for i in range(2017, 2026):
            git_url = base_git.replace("YEAR", str(i))
            try:
                repo = Repo.clone_from(git_url, f"{self._path}/{i}")
                print(f"Cloned {git_url} to {self._path}/{i}")
            except:
                print(f"Failed to clone {git_url}")
    def crawl(self):
        self._download_tasks()
    def parse(self):
        pass