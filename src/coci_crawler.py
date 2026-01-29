import os
import re
import requests
from bs4 import BeautifulSoup
import utils
import urllib3
import shutil
from urllib.parse import urljoin
from base_crawler import Crawler, Contest, Task
import json
from converter import MarkerConverter
import difflib
import unicodedata
from typing import Dict, List, Tuple
import pathlib
import PyPDF2
from io import BytesIO
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class COCICrawler(Crawler):
    def __init__(self, *, competition, path, base_url):
        super().__init__(competition=competition, path=path)
        self.base_url = base_url

    def crawl(self):
        """
        1. 获取所有年份链接
        2. 对每个年份，解析各个 contest 并下载 (task, test_data, solution, results)
        3. 通通先放进 self._path/<year>/COCI/<contest_name>/ 中
        """
        print(f"[COCICrawler] Start crawling from: {self.base_url}")

        year_links = self._get_year_links()
        for year_str in sorted(year_links.keys()):
            if(year_str != "2022-2023" and year_str != "2023-2024" and year_str != "2024-2025"):
                 continue
            year_url = year_links[year_str]
            year_dir = os.path.join(self._path, year_str)
            utils.create_dir_if_not_exists(year_dir)

            #coci_dir = os.path.join(year_dir, "COCI")
            #utils.create_dir_if_not_exists(coci_dir)

            contests_data = self._parse_contests(year_url)
            for (contest_name, files_info) in contests_data:
                folder_name = re.sub(r'[^\w\-\#]+', '_', contest_name)
                contest_dir = os.path.join(year_dir, folder_name)
                utils.create_dir_if_not_exists(contest_dir)
                self._download_by_category(files_info, contest_dir)

        print("[COCICrawler] crawl() finished.")

    def _get_year_links(self):
        """
        解析主页中所有 <div class="naslov"> ... <a href="archive/xxxx_xxxx/">COCI 2006-2007</a> ...
        并返回 dict, 例如: {"2006-2007": "https://...archive/2006_2007/", ...}

        同时，我们也会检查是否有“COCI 20XX/20XX”对应当年（比如 2024/2025）。
        如果找到了，就给它一个 key，比如 '2024-2025'，并将链接设为主页本身 (base_url)。
        """
        year_links = {}
        resp = requests.get(self.base_url, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # 1) 先解析“archive/xxxx_xxxx”形式的往年链接
        for div_tag in soup.find_all('div', class_='naslov'):
            link = div_tag.find('a', href=True)
            if link and 'archive/' in link['href']:
                text = link.get_text(strip=True)  # e.g. "COCI 2006-2007"
                match = re.match(r'COCI\s+(\d{4})-(\d{4})', text)
                if match:
                    y_str = f"{match.group(1)}-{match.group(2)}"
                    # e.g. https://hsin.hr/coci/archive/2006_2007/
                    year_url = urljoin(self.base_url, link['href'])
                    year_links[y_str] = year_url

        # 2) 检查当年 “COCI 2024/2025” (在主页上的表格, 无单独 href)
        #    <div class="naslov" style="font-size: 16px;">COCI 2024/2025</div>
        # 如果存在，就加一个特殊 key -> base_url
        for div_tag in soup.find_all('div', class_='naslov'):
            text = div_tag.get_text(strip=True)
            match2 = re.match(r'COCI\s+(\d{4})/(\d{4})', text)
            if match2:
                current_year_str = f"{match2.group(1)}-{match2.group(2)}"
                # 当年的链接就设为 base_url (因为当年比赛信息直接在主页)
                year_links[current_year_str] = self.base_url
                break

        return year_links

    @staticmethod
    def _parse_contests(page_url):
        """
        解析页面上的比赛信息，返回列表 [(contest_name, files_info), ...]。
        在 <table align="center"> 中，逐个 <td> 寻找 <div class="naslov"> (比赛名称)，
        再根据 <a> 的文字或链接判断是 tasks、test_data、solution、results。
        """
        contests = []
        resp = requests.get(page_url, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        tables = soup.find_all('table', align='center')
        for table in tables:
            for td in table.find_all('td'):
                title_div = td.find('div', class_='naslov')
                if not title_div:
                    continue

                contest_name = title_div.get_text(strip=True)
                files_info = {
                    "tasks": [],
                    "test_data": [],
                    "solution": [],
                    "results": []
                }

                for link in td.find_all('a', href=True):
                    href = link['href'].strip()
                    text = link.get_text(strip=True).lower()
                    file_url = urljoin(page_url, href)

                    if "task" in text or "task" in href.lower():
                        files_info["tasks"].append(file_url)
                    elif "solution" in text or "solution" in href.lower():
                        files_info["solution"].append(file_url)
                    elif "result" in text or "result" in href.lower():
                        files_info["results"].append(file_url)
                    elif "test" in text or "test" in href.lower():
                        files_info["test_data"].append(file_url)

                contests.append((contest_name, files_info))

        return contests

    def _download_by_category(self, files_info, contest_dir):
        """
        下载 tasks、test_data、solution、results 四类文件的第一份，
        并保存在子目录中（tasks/、test_data/ 等），文件名为 tasks.pdf / test_data.zip 等。
        """

        def download_to_subdir(file_list, subfolder):
            if file_list:
                file_url = file_list[0]
                ext = os.path.splitext(file_url)[1]
                if not ext or ext.lower() == '.php':
                    ext = '.pdf'

                subdir_path = os.path.join(contest_dir, subfolder)
                utils.create_dir_if_not_exists(subdir_path)

                save_path = os.path.join(subdir_path, f"{subfolder}{ext}")
                utils.download_file(file_url, save_path)
                #如果是zip，解压所有文件到这个文件夹下，然后删掉
                if ext.lower() == '.zip':
                    utils.unzip_file(save_path, subdir_path)
                    os.remove(save_path)

        # 下载各类文件到各自子目录
        download_to_subdir(files_info.get("tasks", []), "tasks")
        download_to_subdir(files_info.get("test_data", []), "test_data")
        download_to_subdir(files_info.get("solution", []), "solution")
        download_to_subdir(files_info.get("results", []), "results")

        return

    @staticmethod
    def remove_accents(s: str) -> str:
        """
        将字符串 s 中的重音、变音符号移除，例如 'Ž' -> 'Z'
        """
        # normalize 将字符分解为 base + accent
        nfkd_form = unicodedata.normalize('NFKD', s)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def fuzzy_match(self, name: str, candidates: List[str], cutoff=0.5) -> str:
        """
        从 candidates 中找与 name 最相似的 clean 字符串（即 remove_accents + lower）。
        若相似度 >= cutoff，则返回匹配到的 clean 值；否则返回空串。
        """
        name_clean = self.remove_accents(name).lower()
        candidates_clean = [self.remove_accents(c).lower() for c in candidates]
        best = difflib.get_close_matches(name_clean, candidates_clean, n=1, cutoff=cutoff)
        return best[0] if best else ""

    def restructure(self, output_path=None):
        """
        重新构建 (restructure / reconstruct) 成统一目录:
        1) 遍历 self._path 下的 <year>/<contest>
        2) 找到 tasks.pdf, 调用 split_pdf_by_task -> 生成 [task_1.pdf, task_2.pdf, ...]
        3) 依次创建 Task(name="Task1", statements="path/to/task_1.pdf"), ...
        4) 最终写出 Contest 到指定 output_path (默认为 ./output_coci)
        """
        if not output_path:
            output_path = "./output_coci"
        os.makedirs(output_path, exist_ok=True)

        # 遍历所有年份目录
        for year_str in sorted(os.listdir(self._path)):
            year_dir = os.path.join(self._path, year_str)
            if not os.path.isdir(year_dir):
                continue

            # 遍历该年所有 contest
            contest_names = [
                d for d in sorted(os.listdir(year_dir))
                if os.path.isdir(os.path.join(year_dir, d))
            ]
            for contest_name in contest_names:
                contest_dir = os.path.join(year_dir, contest_name)
                # 构造 Contest 对象
                # year = int(year_str[:4])  # 取年份数字
                # 也可以 year=None
                results_file = os.path.join(contest_dir, "results", "results.html")
                c = Contest(name=contest_name, result_file=results_file, year=int(year_str[:4]))

                # 1) 找 tasks.pdf
                tasks_pdf_path = os.path.join(contest_dir, "tasks", "tasks.pdf")
                if os.path.exists(tasks_pdf_path):
                    # 2) 切分 PDF => [task_1.pdf, task_2.pdf, ...]
                    task_names = self.split_pdf_by_task(tasks_pdf_path, contest_dir)
                    # 3) 对每个小PDF创建一个 Task
                    for i, task_name in enumerate(task_names, start=1):
                        task_pdf_path = os.path.join(contest_dir, "tasks", f"{task_name}.pdf")
                        test_path = os.path.join(contest_dir, "test_data", f"{task_name}")
                        solution_path = os.path.join(contest_dir, "solution")
                        code_files = self.find_code_files(solution_path, task_name)

                        t = Task(
                            name=task_name,
                            statements=task_pdf_path,
                            tests=test_path,
                            code_files=code_files
                        )
                        c.add_task(t)
                else:
                    print(f"[WARN] {tasks_pdf_path} not found.")

                # 4) 调用 Contest.write(...) 写到 output_path/<year>/<contest_name>/
                c.write(output_path)

        print("[RECONSTRUCT] Done. All contests restructured.")


    def extract_header(self, page_text):
        """
        从给定文本的前三行中查找包含“Task XXX”结构的内容（忽略大小写），
        如发现“task A”则返回"A"；若前三行都找不到，则返回空字符串。
        """
        # 将文本按行拆分并去除空行、首尾空格
        lines = [line.strip() for line in page_text.split('\n') if line.strip()]
        pattern = r'(?i)Task\s*(.*)'
        # 只查看前三行
        for line in lines[:3]:
            # 使用正则在行内查找 "task + 非空字符" 的结构
            match = re.search(pattern, line)
            if match:
                content = match.group(1)
                # 去掉所有空格, 并变成小写
                cleaned_content = re.sub(r'\s+', '', content).lower()
                cleaned_content = self.remove_accents(cleaned_content)
                return cleaned_content

        return ""

    def split_pdf_by_task(self, input_pdf_path, contest_dir):
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

        # Group pages into tasks based on header and footer differences.
        for i in range(1, num_pages):
            page = pdf_reader.pages[i]
            text = page.extract_text() or ""
            header_task = self.extract_header(text)

            # For the first page, initialize the current header/footer marker.
            if current_header_task is None:
                current_header_task = header_task

            # If header change, assume new task starts.
            elif header_task != current_header_task:
                tasks.append((current_header_task, current_task_pages))
                current_task_pages = []
                current_header_task = header_task
            current_task_pages.append(page)

        if current_task_pages:
            tasks.append((current_header_task, current_task_pages))

        task_names=[]
        test_dir = os.path.join(contest_dir, "test_data")
        candidates = [d for d in os.listdir(test_dir) if os.path.isdir(os.path.join(test_dir, d))]
        # Write each task into a separate PDF file.
        for idx, (task_name, pages) in enumerate(tasks, start=1):
            # 如果没取到任务名，就用 "unknown" 或其它占位符
            if not task_name:
                task_name = f"unknown_{idx}"
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

    def find_code_files(self, base_path: str, code_name: str) -> list:
        """
        在 base_path 及其子目录下查找形如 code_name.xxx 的所有文件（忽略大小写）。
        例如，code_name = 'abc' 时，匹配 abc.cpp、ABC.py、Abc.pas 等。
        返回这些文件的完整路径列表。
        """
        matched_files = []
        lower_code_name = code_name.lower()
        # 递归遍历 base_path 目录
        for root, dirs, files in os.walk(base_path):
            for file in files:
                # 忽略大小写地检查是否以 code_name + "." 开头
                if file.lower().startswith(lower_code_name + "."):
                    full_path = os.path.join(root, file)
                    matched_files.append(full_path)
        return matched_files

if __name__ == "__main__":
    coci_crawler = COCICrawler(
        competition="COCI",
        path="./download_data",
        base_url="https://hsin.hr/coci/"
    )
    #coci_crawler.crawl()
    #coci_crawler.parse()
    coci_crawler.restructure()



'''
    def parse(self, parse_path=None):
        """
        1. 遍历 self._path 下所有 <year>/<contest> 目录
        2. 解析 results.html 获取题目名 (problem_names)
        3. 将 tasks.pdf 转为 tasks.md，并按 "## Task XXX" 分块 -> blocks
           - 每个分块模糊匹配 results.html 里的题目名
           - 放到 <contest>/problems/<题目>/tasks/tasks.md
           - 同时移动对应图片
        4. 再将 editorial.pdf (若有) 转为 editorial.md，分块 -> blocks
           - 同理模糊匹配并保存到 <题目>/solution/solution.md
           - 移动图片 + 代码文件
        5. Done.
        """

        if not parse_path:
            parse_path = self._path

        # 遍历年份目录
        for year_str in sorted(os.listdir(parse_path)):
            year_dir = os.path.join(parse_path, year_str)
            if not os.path.isdir(year_dir):
                continue

            # 遍历该年下的所有“比赛”目录
            for contest_name in sorted(os.listdir(year_dir)):
                contest_dir = os.path.join(year_dir, contest_name)
                if not os.path.isdir(contest_dir):
                    continue

                print(f"[PARSE] Processing {year_str}/{contest_name} ...")

                # =============== 1) 从 results.html 中获取题目名字列表 ===============
                results_html_path = os.path.join(contest_dir, "results", "results.html")
                if os.path.exists(results_html_path):
                    problem_names = self.parse_result_problems(results_html_path)
                else:
                    problem_names = []

                # 先准备一个 <contest>/problems 目录，供我们后续写入题目
                problems_dir = os.path.join(contest_dir, "problems")
                os.makedirs(problems_dir, exist_ok=True)

                # =============== 2) 解析 tasks.pdf => tasks.md => 分块 => 写入题目 ===============
                tasks_pdf_path = os.path.join(contest_dir, "tasks", "tasks.pdf")
                tasks_md_path = self.convert_pdf_to_md(tasks_pdf_path, os.path.join(contest_dir, "tasks"))
                if tasks_md_path and os.path.exists(tasks_md_path):
                    # 根据  r"(#+)\s*[\*]*Task\s+(.*?)[\*]*\s*$" 进行分块
                    pattern = re.compile(r"(#+)\s*\**Task\s+(.*?)[\*]*\s*$", re.IGNORECASE)
                    tasks_blocks = self.parse_md_into_blocks(tasks_md_path, pattern)

                    # 对每个分块 (block_name, block_text) 做 fuzzy 匹配 + 存盘 + 移图
                    for block_name, block_text in tasks_blocks:
                        matched_problem_folder = self._match_block_to_problem(
                            block_name, problem_names, problems_dir
                        )
                        # 写 tasks.md
                        tasks_subdir = os.path.join(problems_dir, matched_problem_folder, "tasks")
                        os.makedirs(tasks_subdir, exist_ok=True)
                        md_out_path = os.path.join(tasks_subdir, "tasks.md")
                        with open(md_out_path, "w", encoding="utf-8") as f:
                            f.write(block_text)

                        # 移动图片
                        self.move_images_in_text(block_text, os.path.join(contest_dir, "tasks"), tasks_subdir)

                # =============== 3) 解析 editorial.pdf => editorial.md => 分块 => 写入题目 ===============
                solution_pdf_path = os.path.join(contest_dir, "solution", "editorial.pdf")
                sol_md_path = self.convert_pdf_to_md(solution_pdf_path, os.path.join(contest_dir, "solution"))
                if sol_md_path and os.path.exists(sol_md_path):
                    pattern = re.compile(r"(#+)\s*\**Task\s+(.*?)[\*]*\s*$", re.IGNORECASE)
                    sol_blocks = self.parse_md_into_blocks(sol_md_path, pattern)

                    for block_name, block_text in sol_blocks:
                        matched_problem_folder = self._match_block_to_problem(
                            block_name, problem_names, problems_dir
                        )
                        # 写 solution.md
                        sol_subdir = os.path.join(problems_dir, matched_problem_folder, "solution")
                        os.makedirs(sol_subdir, exist_ok=True)
                        md_out_path = os.path.join(sol_subdir, "solution.md")
                        with open(md_out_path, "w", encoding="utf-8") as f:
                            f.write(block_text)

                        # 移动图片
                        self.move_images_in_text(block_text, os.path.join(contest_dir, "solution"), sol_subdir)

                    # 额外：移动代码文件 (同在 solution/ 目录中)
                    # 这里需要 existing_map = {cleaned: real_folder}, 以便 fuzzy_match
                    existing_map = {}
                    for d in os.listdir(problems_dir):
                        dpath = os.path.join(problems_dir, d)
                        if os.path.isdir(dpath):
                            clean_d = self.remove_accents(d).lower()
                            existing_map[clean_d] = d
                    self.move_code_files(
                        src_dir=os.path.join(contest_dir, "solution"),
                        existing_map=existing_map,
                        problems_dir=problems_dir
                    )

                print(f"[PARSE] Done: {year_str}/{contest_name}")

        print("[PARSE] All done!")

    @staticmethod
    def convert_pdf_to_md(pdf_path: str, output_dir: str) -> str:
        """
        将给定 pdf_path 转为 Markdown 文件，保存在 output_dir 里。
        返回生成的 .md 文件路径；若失败返回空字符串。
        """
        if not os.path.exists(pdf_path):
            print(f"[WARN] PDF not found: {pdf_path}")
            return ""

        converter = MarkerConverter(source_format="pdf", target_format="markdown", use_LLM=False)
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        # 执行转换
        converter.convert(pdf_path, output_dir, rerun=False)
        md_path = os.path.join(output_dir, f"{base_name}.md")
        return md_path if os.path.exists(md_path) else ""

    @staticmethod
    def parse_result_problems(results_html_path: str) -> List[str]:
        """
        从 results.html 中解析出题目的名称列表，比如 ["DESNI KLIK", "COKOLADE", ...]
        """
        with open(results_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        soup = BeautifulSoup(html_content, "html.parser")

        problem_names = []
        table = soup.find("table", class_="rezultati")
        if not table:
            return problem_names

        # 在第一行(tr)下找 <acronym title="xxx">
        header_cells = table.find("tr").find_all("acronym")
        for acr in header_cells:
            title = acr.get("title", "").strip()
            if title:
                problem_names.append(title)
        return problem_names


    @staticmethod
    def move_images_in_text(text_body: str, src_dir: str, dst_dir: str):
        """
        从 text_body 中找形如 ![](filename.jpg) 等本地图片引用，
        若该图片文件在 src_dir 下，则移动到 dst_dir 同时保留文件名。
        注意这里不会修改 text_body 中的图片链接路径，你也可以视情况替换。
        """
        images = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text_body)
        for img_name in images:
            # 忽略绝对路径或远程链接
            if os.path.isabs(img_name) or '://' in img_name:
                continue
            src_img = os.path.join(src_dir, img_name)
            if os.path.isfile(src_img):
                os.makedirs(dst_dir, exist_ok=True)
                shutil.move(src_img, os.path.join(dst_dir, os.path.basename(img_name)))
        return

    @staticmethod
    def move_code_files(src_dir: str, existing_map: Dict[str, str], problems_dir: str,
                        code_exts=(".cpp", ".py", ".java", ".c", ".pas")):
        """
        将 src_dir 下的若干代码文件，根据其文件名前缀做 fuzzy 匹配，
        然后移动到 problems_dir/<matched_problem>/solution/。

        existing_map: {cleaned_key: actual_folder_name} 用于 fuzzy 匹配
        """
        for filename in os.listdir(src_dir):
            filepath = os.path.join(src_dir, filename)
            if not os.path.isfile(filepath):
                continue

            if filename.endswith(code_exts):
                # 示例：hijerarhija.cpp => prob_name = "hijerarhija"
                prob_name, _ = os.path.splitext(filename)
                matched_folder = fuzzy_match(prob_name, existing_map)
                if matched_folder:
                    dst_sol = os.path.join(problems_dir, matched_folder, 'solution')
                    os.makedirs(dst_sol, exist_ok=True)
                    shutil.move(filepath, os.path.join(dst_sol, filename))
        return

    @staticmethod
    def parse_md_into_blocks(md_path: str, pattern) -> list:
        """
        按给定的正则 pattern 将 md_path 文件拆分成若干块：
        每个块返回 (problem_name, text_body)。
        pattern示例: r"(#+)\s*[\*]*Task\s+(.*?)[\*]*\s*$"
        """
        with open(md_path, "r", encoding="utf-8", errors="ignore") as f:
            raw_text = f.read()
        raw_text = re.sub(
            r"(?<!\n)(#+\s*\**Task\s+.*)",  # group1: "# Task"...后面整行都捕捉
            r"\n\1",  # 在其前面插入一个换行符
            raw_text
        )

        lines = raw_text.splitlines()
        blocks = []
        current_problem_name = None
        current_lines = []

        for line in lines:
            match = pattern.match(line)
            if match:
                # 把前面块先收集起来
                if current_problem_name is not None:
                    blocks.append((current_problem_name, "".join(current_lines)))
                # 开始新的块
                current_problem_name = match.group(2).strip()  # group(2) 即题目名
                current_lines = [line]
            else:
                current_lines.append(line)

        # 收尾
        if current_problem_name is not None:
            blocks.append((current_problem_name, "".join(current_lines)))

        return blocks

    @staticmethod
    def match_and_save_blocks(
            blocks: List[tuple],
            problem_names: List[str],  # 来自 results.html 之类的“官方题名”
            problems_dir: str,  # 形如： path/to/contest/problems/
            src_dir: str,  # 原先放 pdf、md、图片、代码的来源目录
            subfolder_name: str,  # "tasks" 或 "solution" (决定目标md文件名)
            move_code: bool = False  # 若是处理 solution 可能要搬运代码
    ):
        """
        将 PDF->MD 拆分后的 blocks，逐一匹配到 problem_names 并写入 problems_dir/<matched>/subfolder_name/*.md

        - blocks: [(block_title, block_text), ...]
        - problem_names: 例如从 results.html 里获取到的 ["DESNI KLIK", "COKOLADE", ...]
        - problems_dir: contest 级别的 problems/ 文件夹，里面已有每道题的子目录
        - src_dir: tasks/ 或 solution/ 目录（含生成的 .md, .jpg, .cpp 等）
        - subfolder_name: "tasks" | "solution" 或你喜欢的命名，用来决定 md 文件名 (tasks.md / solution.md)
        - move_code: 若 True，则在结束后把 .cpp / .py 等文件也按照题目名 fuzzy 匹配搬走
        """

        # 首先构建 existing_map: {cleaned_name: "Hijerarhija"}
        existing_map = {}
        for d in os.listdir(problems_dir):
            dpath = os.path.join(problems_dir, d)
            if os.path.isdir(dpath):
                cleaned_key = remove_accents(d).lower()
                existing_map[cleaned_key] = d

        # 逐块写入
        for (pdf_name, pdf_content) in blocks:
            # fuzzy 匹配 PDF块名 与 official names
            best_official = fuzzy_match(pdf_name, {remove_accents(n).lower(): n for n in problem_names})
            # 如果在 results 里也没有匹配，就用现有 problem 文件夹（existing_map）再 fuzzy 一次
            final_problem_name = best_official
            if not final_problem_name:
                # 试着直接在 existing_map 里匹配
                matched_folder = fuzzy_match(pdf_name, existing_map)
                if matched_folder:
                    final_problem_name = matched_folder
                else:
                    # 如果依然匹配不到，干脆把 PDF 的原名当作 fallback
                    final_problem_name = pdf_name

            # 在 problems_dir 里找对应子目录
            # final_problem_name 可能是 official 全称“DESNI KLIK”，需要去 existing_map 查一下
            matched_folder = fuzzy_match(final_problem_name, existing_map)
            if not matched_folder:
                # 如果又没匹配到，就统一“创建”一个
                safe_folder = re.sub(r"[^\w_-]+", "_", final_problem_name)
                matched_folder = safe_folder
                os.makedirs(os.path.join(problems_dir, safe_folder), exist_ok=True)
                # 也可以顺便更新 existing_map
                cleaned_key = remove_accents(safe_folder).lower()
                existing_map[cleaned_key] = safe_folder

            # 准备写入
            dst_sub_dir = os.path.join(problems_dir, matched_folder, subfolder_name)
            os.makedirs(dst_sub_dir, exist_ok=True)

            # 写 .md 文件
            # 例如 tasks.md / solution.md
            md_filename = f"{subfolder_name}.md"
            md_path = os.path.join(dst_sub_dir, md_filename)
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(pdf_content)

            # 移动文档里引用到的图片
            move_images_in_text(pdf_content, src_dir, dst_sub_dir)

            print(f"[INFO] Written {md_path} (from block '{pdf_name}')")

        # 如果需要搬运代码文件(通常在 solution/ 下)
        if move_code:
            move_code_files(src_dir, existing_map, problems_dir)
'''