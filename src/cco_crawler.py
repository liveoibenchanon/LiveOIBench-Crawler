import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from base_crawler import Crawler, Contest, Task
import utils
import shutil
import PyPDF2
from io import BytesIO
import difflib

class CCCCrawler(Crawler):
    def __init__(self, *, competition, path, base_url):
        super().__init__(competition=competition, path=path)
        self.base_url = base_url

    def crawl(self):
        """
        爬取 CCC 所有页，每场比赛下载题目、数据、解答、结果等资源。
        """
        print(f"[CCC] Start crawling from: {self.base_url}")
        if self._competition == "CCC":
            for page in range(3):
                page_url = f"{self.base_url}?grade=All&academic_year=All&contest_category=29&page={page}"
                print(f"[CCC] Visiting page {page} ...")
                self._parse_page(page_url)
        self._competition = "CCO"
        if self._competition == "CCO":
            for page in range(1):
                page_url = f"{self.base_url}?grade=All&academic_year=All&contest_category=80&page={page}"
                print(f"[CCO] Visiting page {page} ...")
                self._parse_page(page_url)
            print(f"{self._competition} crawl() finished.")

    def _parse_page(self, page_url):
        """
        解析一页的所有比赛，提取 title、year 和下载链接。
        """
        resp = requests.get(page_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        rows = soup.select("table.table tbody tr")
        for row in rows:
            title_cell = row.select_one(".views-field-title")
            if not title_cell:
                continue
            title = title_cell.get_text(strip=True)
            title = re.sub(r'[^\w ]+', '', title).replace(' ', '_').strip('_')

            year_cell = row.select_one(".views-field-field-year-term")
            year = year_cell.get_text(strip=True) if year_cell else "unknown"
 #           if year!='2019' and year!='2020' and year!='2021':
 #               continue
            def get_link(td_class, kind):
                td = row.select_one(td_class)
                if not td:
                    return None
                for a in td.find_all('a', href=True):
                    href = a['href']
                    if kind == "download" and a.has_attr("download"):
                        return urljoin(self.base_url, href)
                    if kind == "view" and a.has_attr("target"):
                        return urljoin(self.base_url, href)
                return None

            contest_url = get_link(".views-field-nothing", "download")
            commentary_url = get_link(".views-field-nothing-2", "view")  # HTML commentary
            data_url = get_link(".views-field-nothing-2", "download")  # ZIP test data
            results_url = get_link(".views-field-nothing-1", "download")

            # 保存路径
            base_dir = os.path.join(self._path, year, title)
            for name, url in [
                ("contest", contest_url),
                ("data", data_url),
                ("commentary", commentary_url),
                ("results", results_url)
            ]:
                if not url:
                    if name == "commentary":
                        subdir = os.path.join(base_dir, name)
                        utils.create_dir_if_not_exists(subdir)
                        if os.path.exists(f"{base_dir}/data"):
                            for f in os.listdir(f"{base_dir}/data"):
                                if f.lower().endswith(".pdf"):
                                    src = os.path.join(f"{base_dir}/data", f)
                                    dst = os.path.join(subdir, f)
                                    if not os.path.exists(dst):
                                        os.rename(src, dst)
                                        print(f"[CCC] Moved fallback commentary PDF → {dst}")

                    continue
                subdir = os.path.join(base_dir, name)
                utils.create_dir_if_not_exists(subdir)
                filename = url.split("/")[-1]
                save_path = os.path.join(subdir, filename)
                utils.download_file(url, save_path)
                if self._competition == "CCO" and name == "results":
                    ## 拿到对应年份的CCO结果的url，多下载一个csv
                    def fetch_cco_results_links(target_year):
                        url = 'https://kobortor.com/cco/'
                        resp = requests.get(url)
                        resp.raise_for_status()
                        soup = BeautifulSoup(resp.text, 'html.parser')
                        for a_tag in soup.select('a[href*="docs.google.com/spreadsheets"]'):
                            href = a_tag['href']
                            text = a_tag.get_text(strip=True)
                            year = text.split()[-1]  # 链接文本格式为 "CCO Results YYYY"
                            if year == target_year:
                                return href
                    url = fetch_cco_results_links(year)
                    utils.download_google_sheet(url, f"{subdir}/results_csv.xslx")
                print(f"[CCC] Downloaded {name} → {save_path}")

                if save_path.lower().endswith(".zip"):
                    utils.unzip(save_path, subdir)
                    os.remove(save_path)

                    # 删除 __MACOSX 文件夹
                    macosx_path = os.path.join(subdir, '__MACOSX')
                    if os.path.exists(macosx_path):
                        shutil.rmtree(macosx_path)

                    # 查找唯一的非 __MACOSX 目录
                    while True:
                        inner_items = os.listdir(subdir)
                        real_dirs = [f for f in inner_items if os.path.isdir(os.path.join(subdir, f))]
                        real_dirs = [d for d in real_dirs if not d.startswith('__')]
                        #判断inner_items内部都是dir而不是文件
                        should_split = True
                        for d in real_dirs:
                            d_path = os.path.join(subdir, d)
                            ds_store = os.path.join(d_path, '.DS_Store')
                            if os.path.exists(ds_store):
                                os.remove(ds_store)
                            inner_items = os.listdir(d_path)
                            has_subdir = any(os.path.isdir(os.path.join(d_path, item)) for item in inner_items)
                            if not has_subdir:
                                # 当前目录全是文件，不需要再往下拆
                                should_split = False
                                break
                        if not should_split:
                            break
                        for dir in real_dirs:
                            inner_dir = os.path.join(subdir, dir)
                            for item in os.listdir(inner_dir):
                                src = os.path.join(inner_dir, item)
                                filename = item
                                if filename.startswith("cco_"):
                                    filename = filename[len("cco_"):]
                                if filename.endswith("_data"):
                                    filename = filename[:-len("_data")]
                                dst = os.path.join(subdir, filename)
                                os.rename(src, dst)
                            os.rmdir(inner_dir)

                    # 删除 .DS_Store 文件（macOS下的隐藏系统文件）
                    ds_store = os.path.join(subdir, '.DS_Store')
                    if os.path.exists(ds_store):
                        os.remove(ds_store)

    def restructure(self, output_path=None):
        if not output_path:
            output_path = "./output_ccc"
        os.makedirs(output_path, exist_ok=True)

        for year_str in sorted(os.listdir(self._path)):
            #if year_str not in ["2015", "2016", "2017", "2018", "2019"]: continue
            #if year_str not in ["2015"]: continue
            year_dir = os.path.join(self._path, year_str)
            if not os.path.isdir(year_dir):
                continue

            for contest_name in sorted(os.listdir(year_dir)):
                #if contest_name != "Canadian_Computing_Competition_Junior": continue
                contest_dir = os.path.join(year_dir, contest_name)
                if not os.path.isdir(contest_dir):
                    continue

                results_dir = os.path.join(contest_dir, "results")
                all_files = os.listdir(results_dir)
                # 优先查找 .xlsx 文件
                xlsx_files = [f for f in all_files if f.endswith('.xslx')]
                pdf_files = [f for f in all_files if f.endswith('.pdf')]
                if xlsx_files:
                    results_file = os.path.join(results_dir, xlsx_files[0])
                else:
                    results_file = os.path.join(results_dir, pdf_files[0])
                c = Contest(name=contest_name, result_file=results_file, year=int(year_str))

                # 用pdf分割contest
                contest_pdf = self._find_first_file(os.path.join(contest_dir, "contest"), ".pdf")
                task_names = self.split_pdf_by_task(contest_name, contest_pdf, contest_dir)

                if contest_name != "Canadian_Computing_Olympiad": ##CCO没有答案
                    # 尝试从 HTML 中分割 commentary
                    html_file = self._find_first_file(os.path.join(contest_dir, "commentary"), ".html")
                    if html_file:
                        html_solution = self.split_html_by_task(html_file, contest_dir)
                    #如果匹配不上的话，在后面的parse先转换成md再分割

                for i, task_name in enumerate(task_names, start=1):
                    task_pdf_path = os.path.join(contest_dir, "contest", f"{task_name}.pdf")
                    test_path = os.path.join(contest_dir, "data")
                    if os.path.exists(test_path):
                        test_path = os.path.join(test_path, f"{task_name}")
                    else:
                        test_path = None
                    if contest_name != "Canadian_Computing_Olympiad":
                        editorial_files = os.path.join(contest_dir, "commentary", f"{task_name}.md")
                        t = Task(
                            name=task_name,
                            statements=task_pdf_path,
                            tests=test_path,
                            editorial_files=editorial_files
                        )
                    else:
                        t = Task(
                            name=task_name,
                            statements=task_pdf_path,
                            tests=test_path
                        )
                    c.add_task(t)
                c.write(output_path)
        print("[RESTRUCTURE] Done.")

    def _find_first_file(self, folder, suffix):
        if not os.path.exists(folder):
            return None
        for f in os.listdir(folder):
            if f.lower().endswith(suffix):
                return os.path.join(folder, f)
        return None

    def extract_header(self, contest_name, page_text):
        """
        CCC -- Problem J/S
        CCO -- Day X, Problem Y
        """
        # 将文本按行拆分并去除空行、首尾空格
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        if contest_name == "Canadian_Computing_Olympiad":
            pattern = r'Day\s*(\d+),\s*Problem\s*(\d+)'
        else:
            pattern = r'Problem ([A-Z]\d)(?:/([A-Z]\d))?'
        if any(year in lines[0] for year in ["2015", "2016", "2017", "2018", "2019"]) and contest_name == "Canadian_Computing_Olympiad":
            return 1, lines[2]

        for line in lines[:2]:
            match = re.search(pattern, line)
            if match:
                if contest_name == "Canadian_Computing_Olympiad":
                    day = match.group(1)
                    problem = match.group(2)
                    code = f"d{day}p{problem}"
                else:
                    code = match.group(1)
                    if match.group(2):
                        code += match.group(2)
                return 0, code
        return 0, None

    def extract_code_blocks(self, name):
        """
        从字符串中提取类似 J4、S1、B6 这样的子任务编号块
        """
        return set(re.findall(r'[A-Z]\d+', name.upper()))

    def fuzzy_match(self, task_name, candidates):
        target_blocks = self.extract_code_blocks(task_name)

        for candidate in candidates:
            candidate_blocks = self.extract_code_blocks(candidate)
            # 只要 task_name 所有块都在 candidate 中，就视为匹配
            if target_blocks.issubset(candidate_blocks) or candidate_blocks.issubset(target_blocks):
                return candidate
        return None

    def fuzzy_match_realname(self, name, candidates, cutoff=0.2):
        """
        从 candidates 中找与 name 最相似的字符串。
        若相似度 >= cutoff，则返回匹配到的值；否则返回空串。
        """
        matches = [c for c in candidates if c.lower() in name.lower()]
        # 从中选长度最长的那个
        best_match = max(matches, key=len, default=None)
        if best_match:
            return best_match
        else:
            name_clean = name.lower()
            best = difflib.get_close_matches(name_clean, candidates, n=1, cutoff=cutoff)
            if best:
                return best[0]
            else:
                return ""

    def split_pdf_by_task(self, contest_name, input_pdf_path, contest_dir):
        # Read the PDF file into memory
        with open(input_pdf_path, 'rb') as infile:
            pdf_bytes = infile.read()

        # Use BytesIO so the PDF is in memory and available to PyPDF2
        pdf_stream = BytesIO(pdf_bytes)
        pdf_reader = PyPDF2.PdfReader(pdf_stream)
        num_pages = len(pdf_reader.pages)
        print(f"Total pages in PDF: {num_pages}")

        tasks = []  # List to hold lists of pages for each task
        current_task_pages = []  # Pages for the current task
        current_header_task = None  # Stores the header_task of the current task
        flag = 0 #corner case
        french_flag = 0
        # Group pages into tasks based on header and footer differences.
        for i in range(num_pages):
            page = pdf_reader.pages[i]
            text = page.extract_text() or ""
            if re.search(r'P\s*r\s*o\s*b\s*l[\s\`\'’]*[eèêé]{1,2}\s*m\s*e', utils.clean_text(text)):
                print(f"Skipping French page {i}")
                french_flag = 1
                continue
            local_flag, header_task = self.extract_header(contest_name, text)
            if local_flag:
                flag = 1
            # For the first page, initialize the current header/footer marker.
            if current_header_task is None:
                current_header_task = header_task
                current_task_pages = []

            # If header change, assume new task starts.
            elif header_task and header_task != current_header_task:
                french_flag = 0
                tasks.append((current_header_task, current_task_pages))
                current_task_pages = []
                current_header_task = header_task
            elif not header_task and french_flag:
                continue
            current_task_pages.append(page)

        if current_task_pages:
            tasks.append((current_header_task, current_task_pages))

        task_names=[]
        test_dir = os.path.join(contest_dir, "data")
        if os.path.exists(test_dir):
            candidates = [d for d in os.listdir(test_dir) if os.path.isdir(os.path.join(test_dir, d))]
        else:
            candidates = []
        # Write each task into a separate PDF file.
        for idx, (task_name, pages) in enumerate(tasks, start=1):
            # 如果没取到任务名，就用 "unknown" 或其它占位符
            if not task_name:
                task_name = f"unknown_{idx}"
            if flag:
                matched_name = self.fuzzy_match_realname(task_name, candidates)
            else:
                matched_name = self.fuzzy_match(task_name, candidates)
            if matched_name:
                task_name = matched_name
            else:
                print(f"[WARN] No good match for task name '{task_name}', fallback to raw name.")
                continue
            task_names.append(task_name)
            output_filename = os.path.join(
                os.path.dirname(input_pdf_path),
                f"{task_name}.pdf"
            )

            pdf_writer = PyPDF2.PdfWriter()
            for page in pages:
                pdf_writer.add_page(page)

            with open(output_filename, 'wb') as outfile:
                pdf_writer.write(outfile)

            print(f"Created: {output_filename}")
            for page in pages:
                pdf_writer.add_page(page)
        return task_names

    def split_html_by_task(self, html: str, contest_dir):
        with open(html, "r", encoding="utf-8") as f:
            html_file = f.read()
        soup = BeautifulSoup(html_file, 'html.parser')
        blocks = []
        current_task_id = None
        current_block = []
        for tag in soup.find_all(['h2', 'p', 'pre', 'ul', 'ol', 'div', 'table']):
            if tag.name == 'h2':
                match = re.match(r'^([A-Z]\d)', tag.get_text(strip=True))
                if match:
                    if current_task_id:
                        blocks.append((current_task_id, current_block))
                    current_task_id = match.group(1)
                    current_block = [tag]
                    continue
            if current_task_id:
                current_block.append(tag)

        if current_task_id:
            blocks.append((current_task_id, current_block))

        task_names = []
        test_dir = os.path.join(contest_dir, "data")
        if os.path.exists(test_dir):
            candidates = [d for d in os.listdir(test_dir) if os.path.isdir(os.path.join(test_dir, d))]
        else:
            candidates = []
        # Write each task into a separate Markdown file.
        for idx, (task_name, tags) in enumerate(blocks, start=1):
            if not task_name:
                task_name = f"unknown_{idx}"
            matched_name = self.fuzzy_match(task_name, candidates)
            if matched_name:
                task_name = matched_name
            else:
                print(f"[WARN] No good match for task name '{task_name}', fallback to raw name.")
                continue

            task_names.append(task_name)
            output_filename = os.path.join(os.path.dirname(html), f"{task_name}.md")

            # 转换 HTML tags 为 markdown 文本
            md_lines = []
            for tag in tags:
                if tag.name == 'h2':
                    md_lines.append(f"# {tag.get_text(strip=True)}")
                elif tag.name == 'p':
                    md_lines.append(tag.get_text(strip=True))
                elif tag.name == 'pre':
                    md_lines.append("```")
                    md_lines.append(tag.get_text())
                    md_lines.append("```")
            content = "\n\n".join(md_lines)

            # 写入 Markdown 文件
            with open(output_filename, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"Created: {output_filename}")
        return task_names


    def parse(self):
        pass
if __name__ == "__main__":
    ccc_crawler = CCCCrawler(
        competition="CCC",
        path="./output_ccc",
        base_url="https://cemc.uwaterloo.ca/resources/past-contests"
    )
    #ccc_crawler.crawl()
    ccc_crawler.restructure(output_path="./restructure_ccc")
    '''
    cco_crawler = CCCCrawler(
        competition="CCO",
        path="./output_cco",
        base_url="https://cemc.uwaterloo.ca/resources/past-contests"
    )
    cco_crawler.crawl()
    '''