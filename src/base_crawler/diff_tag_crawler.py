import requests
from bs4 import BeautifulSoup
import time
import json

class SolvedACTreeCrawler:
    def __init__(self, base_url='https://www.acmicpc.net/'):
        self.base_url = base_url
        self.visited = set()
        self.result = {}
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; SolvedACCrawler/1.0)'
        })

    def fetch(self, url, max_retries=5, delay=1):
        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url)
                response.raise_for_status()
                return BeautifulSoup(response.text, 'html.parser')
            except requests.RequestException as e:
                print(f"Attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                else:
                    print(f">>> Failed to fetch after {max_retries} attempts: {url}")
        return None

    def get_page_links(self, soup):
        links = []
        for row in soup.find_all('tr'):
            a = row.find('a', href=True)
            if a:
                name = a.text.strip()
                href = a['href']
                full_url = self.base_url + href.lstrip('/')
                links.append((name, full_url, href))
        return links

    def get_problem_data_from_solvedac(self, problem_id):
        search_url = f"https://solved.ac/en/search?query={problem_id}"
        soup = self.fetch(search_url)
        if soup is None:
            return None

        try:
            url = f"https://solved.ac/api/v3/problem/show?problemId={problem_id}"
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()

            title = data.get("titleEn") or data.get("titleKo", "N/A")
            difficulty_level = data.get("level", "N/A")
            tag_list = []

            for tag in data.get("tags", []):
                english_names = [name["name"] for name in tag.get("displayNames", []) if name["language"] == "en"]
                if english_names:
                    tag_list.append(english_names[0])
                else:
                    # fallback: add Korean if English not found
                    fallback_name = tag["displayNames"][0]["name"] if tag.get("displayNames") else ""
                    tag_list.append(fallback_name)

            return {
                "id": int(problem_id),
                "title": title,
                "difficulty": difficulty_level,
                "tags": tag_list
            }
        except Exception as e:
            print(f">>> Error fetching problem {problem_id} from solved.ac API: {e}")
            return None

    def insert_nested(self, path, data, problem_key, problem_data):
        current = data
        for p in path:
            if p not in current:
                current[p] = {}
            current = current[p]
        current[problem_key] = problem_data

    def traverse(self, url, path=None):
        if path is None:
            path = []

        if url in self.visited:
            return
        self.visited.add(url)

        soup = self.fetch(url)
        if soup is None:
            return

        links = self.get_page_links(soup)
        print(f"Visiting: {' > '.join(path) or 'Root'} | Found {len(links)} links")

        for text, full_url, href in links:
            if '/problem/' in href:
                problem_id = href.split('/')[-1]
                problem_data = self.get_problem_data_from_solvedac(problem_id)
                if problem_data:
                    key = f"{problem_id} - {problem_data['title']}"
                    self.insert_nested(path, self.result, key, problem_data)
                else:
                    print(f">>> Problem data not found for {problem_id}")
                time.sleep(1)
            else:
                self.traverse(full_url, path + [text])

    def crawl(self, start_url):
        self.traverse(start_url)
        return self.result

if __name__ == '__main__':
    crawler = SolvedACTreeCrawler()
    result = crawler.crawl("https://www.acmicpc.net/category/2")
    # print(result)

    with open("diff_tags_0423.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
