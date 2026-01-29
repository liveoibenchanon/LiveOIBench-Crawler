import time
import math
import json
import re
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor

def extract_problem_sort_key(title):
    match = re.search(r"#(\d+)", title)
    if match:
        return (0, int(match.group(1)))  # 优先排序项1：题号数字
    return (1, title)  # 优先排序项2：标题字符串

def setup_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    service = Service(executable_path="C:\\edgedriver_win32\\msedgedriver.exe")
    return webdriver.Edge(service=service, options=options)

def get_max_pages(keyword):
    driver = setup_driver()
    url = f"https://www.luogu.com.cn/problem/list?keyword={keyword}"
    driver.get(url)
    time.sleep(2)

    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        count_tag = soup.select_one(".result-count .number")
        total = int(count_tag.text.strip())
        max_page = math.ceil(total / 50)
        print(f"🔢 关键词 {keyword} 共 {total} 题，约为 {max_page} 页（每页50题）")
    except Exception as e:
        print("⚠️ 获取题目总数失败，默认设为1页:", e)
        max_page = 1

    driver.quit()
    return max_page


def scrape_luogu_problems(keyword, pages=1):
    driver = setup_driver()
    structured_data = defaultdict(lambda: defaultdict(list))
    for page in range(1, pages + 1):
        url = f"https://www.luogu.com.cn/problem/list?keyword={keyword}&page={page}"
        print(f"\n--- 访问第 {page} 页: {url}")
        driver.get(url)
        time.sleep(2)

        # Step 1: 获取来源标签 + 难度
        source_info = {}
        rows = driver.find_elements(By.CSS_SELECTOR, ".row-wrap .row")
        print(f"找到 {len(rows)} 个题目行")
        for row in rows:
            try:
                title_el = row.find_element(By.CSS_SELECTOR, ".title a")
                href = title_el.get_attribute("href")
                pid = href.split("/")[-1]

                tags = [t.text.strip() for t in row.find_elements(By.CSS_SELECTOR, ".tags .tag span")]

                # 获取难度
                try:
                    difficulty = row.find_element(By.CSS_SELECTOR, ".difficulty span").text.strip()
                except:
                    difficulty = ""

                source_info[pid] = {
                    "标题": title_el.text.strip(),
                    "链接": href,
                    "来源标签": tags,
                    "难度": difficulty
                }

                print(f"[来源] {pid}: 标签={tags} 难度={difficulty}")
            except Exception as e:
                print("跳过某行（可能结构异常）:", e)

        # Step 2: 点击全局“显示算法”按钮
        try:
            show_btn = driver.find_element(By.LINK_TEXT, "显示算法")
            driver.execute_script("arguments[0].click();", show_btn)
            print("已点击‘显示算法’，等待标签加载...")
            time.sleep(1)
        except:
            print("没有找到‘显示算法’按钮，跳过算法标签")

        # Step 3: 获取算法标签
        algo_info = {}
        rows = driver.find_elements(By.CSS_SELECTOR, ".row-wrap .row")
        for row in rows:
            try:
                title_el = row.find_element(By.CSS_SELECTOR, ".title a")
                href = title_el.get_attribute("href")
                pid = href.split("/")[-1]
                tags = [t.text.strip() for t in row.find_elements(By.CSS_SELECTOR, ".tags .tag span")]
                algo_info[pid] = tags
                print(f"[算法] {pid}: {tags}")
            except:
                continue

        # Step 4: 合并结果并存入 structured_data（新增）
        for pid, info in source_info.items():
            algo_tags = algo_info.get(pid, [])

            # 提取年份
            year = None
            for tag in info["来源标签"]:
                match = re.match(r"\d{4}", tag)
                if match:
                    year = match.group()
                    break

            # 提取比赛名（如 COCI）
            comp = None
            for tag in info["来源标签"]:
                if not any(c.isdigit() for c in tag):
                    comp = tag.split("（")[0].strip()
                    break

            if not comp or not year:
                print(f"⚠️ 来源标签中未识别到比赛/年份，尝试从标题中提取: {info['标题']}")
                # 比赛名 = [] 中的字母部分
                match_comp = re.search(r"\[([A-Za-z]+)", info["标题"])
                if match_comp:
                    comp = match_comp.group(1).upper()

                # 年份 = [] 中最大的4位数字
                match_years = re.findall(r"\d{4}", info["标题"])
                if match_years:
                    year = max(match_years)

                if not comp or not year:
                    print(f"❌ 无法从标题中提取比赛或年份，跳过: {pid}")
                    continue

            structured_data[comp][year].append({
                "标题": info["标题"],
                "难度": info["难度"],
                "算法标签": algo_tags
            })

            print(f"\n📌 综合信息 - {pid}")
            print(f"标题: {info['标题']}")
            print(f"链接: {info['链接']}")
            print(f"来源标签: {', '.join(info['来源标签'])}")
            print(f"难度: {info['难度']}")
            print(f"算法标签: {', '.join(algo_tags)}")

    driver.quit()
    print("\n✅ 所有页处理完成。")


    sorted_output = {
        comp: {
            year: sorted(problem_list, key=lambda x: extract_problem_sort_key(x["标题"]))
            for year, problem_list in sorted(years.items(), key=lambda item: int(item[0]))
        }
        for comp, years in structured_data.items()
    }

    print("\n📦 整理完成的结构化数据：")
    print(json.dumps(sorted_output, indent=2, ensure_ascii=False))

    with open(f"./jsons/{keyword}_problems.json", "w", encoding="utf-8") as f:
        json.dump(sorted_output, f, indent=2, ensure_ascii=False)

    print(f"\n💾 已保存为文件：{keyword}_problems.json")

def crawl_keyword(keyword):
    max_page = get_max_pages(keyword)
    scrape_luogu_problems(keyword=keyword, pages=max_page)

# 示例调用
if __name__ == "__main__":
    #keyword = "CCO"
    keywords = ["APIO", "BalticOI", "CCO", "CCC", "CEOI", "EGOI", "eJOI", "IOI", "JOI", "RMI", "USACO"]
    with ProcessPoolExecutor(max_workers=11) as executor:
        executor.map(crawl_keyword, keywords)

