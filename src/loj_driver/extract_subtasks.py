#!/usr/bin/env python3
import os
import re
import json
import argparse
from bs4 import BeautifulSoup
from datetime import datetime
import unicodedata

def slugify(text):
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "_", text)

def write_samples(soup, outdir):
    """Extract sample inputs and outputs, saving sampleN.in and sampleN.out"""
    samples = []
    # locate Samples section
    sample_sec = None
    for title in soup.select("div.accordion .title"):
        if title.get_text(strip=True).startswith("Sample"):
            sample_sec = title.find_next_sibling(
                lambda tag: tag.name == "div" and tag.get("class") and "content" in tag.get("class")
            )
            break
    if not sample_sec:
        return samples

    # iterate each Sample entry
    for title in sample_sec.find_all("div", class_=lambda c: c and "title" in c):
        txt = title.get_text(strip=True)
        m = re.match(r"Sample\s*#?(\d+)", txt)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        content = title.find_next_sibling(
            lambda tag: tag.name == "div" and tag.get("class") and "content" in tag.get("class")
        )
        if not content:
            continue
        pres = content.find_all("pre")
        if len(pres) < 2:
            continue
        inp, out = pres[0].get_text(), pres[1].get_text()
        name = f"sample{idx}"
        with open(os.path.join(outdir, f"{name}.in"), "w") as f:
            f.write(inp)
        with open(os.path.join(outdir, f"{name}.out"), "w") as f:
            f.write(out)
        samples.append(name)
    return sorted(set(samples), key=lambda x: int(x.replace('sample','')))

def write_subtasks(soup):
    """Extract subtasks excluding samples; dedupe testcases. If no subtasks, gather test cases."""
    subtasks = {}
    # primary: look for Subtask sections
    for title in soup.select("div.accordion .title"):
        txt = title.get_text(strip=True)
        m = re.match(r"Subtask\s*#?(\d+)", txt)
        if not m:
            continue
        sid = m.group(1)
        # score
        cols = title.select(".column")
        score = 0
        if len(cols) >= 3:
            parts = cols[2].get_text(strip=True).split()
            if parts:
                try:
                    score = int(parts[0].split("/")[0])
                except:
                    pass
        # content
        content = title.find_next_sibling(
            lambda tag: tag.name == "div" and tag.get("class") and "content" in tag.get("class")
        )
        if not content:
            continue
        raw = [span.get_text(strip=True) for span in content.select("span[class*='fileName']")]
        files = []
        for fname in raw:
            key = re.sub(r'^(?:input\.|output\.)', '', fname)
            key = re.sub(r'\.(?:in|out|ok)$', '', key)
            if key not in files:
                files.append(key)
        subtasks[sid] = {"task": f"Subtask {sid}", "score": score, "testcases": files}
    # fallback: if no subtasks found, treat top-level Testcase entries as a single subtask
    if not subtasks:
        raw = [span.get_text(strip=True) for span in soup.select("span[class*='fileName']")]
        files = []
        for fname in raw:
            key = re.sub(r'^(?:input\.|output\.)', '', fname)
            key = re.sub(r'\.(?:in|out|ok)$', '', key)
            if key not in files:
                files.append(key)
        subtasks["0"] = {"task": "Testcases", "score": 0, "testcases": files}
    return subtasks

def write_solution_and_result(soup, outdir, cxx_version, submitter, platform, submission_id, problem_id):
    # Solution code with header comments
    code = soup.select_one("pre._codeBoxContent_122zh_12")
    lang = "cpp"
    version = None
    lang_ver = None
    if code:
        first = code.get_text().splitlines()[0]
        m_py = re.match(r"#!.*python(\d+(?:\.\d+)*)", first)
        if m_py:
            lang = "py"
            version = m_py.group(1)
        elif cxx_version:
            version = cxx_version
        else:
            version = "17"
        lang_ver = f"{lang}{version}"
        comment = "//" if lang == "cpp" else "#"
        header = (
            f"{comment} Submission ID: {submission_id}\n"
            f"{comment} Problem ID: {problem_id}\n"
            f"{comment} Submitter: {submitter}\n"
            f"{comment} Platform: {platform}\n"
            f"{comment} Language: {lang_ver}\n\n"
        )
        content = header + code.get_text()
        with open(os.path.join(outdir, f"solution.{lang}"), "w") as f:
            f.write(content)

    result = {
        "submission_id": submission_id,
        "problem_id": problem_id
    }
    st = soup.select_one("span.statustext")
    if st:
        result["status"] = st.get_text(strip=True)
    if lang_ver:
        result["language"] = lang_ver
    result["submitter"] = submitter
    result["platform"] = platform
    sc = soup.select_one("span._score_10_1lqan_31")
    if sc:
        try: result["score"] = int(sc.get_text(strip=True))
        except: pass
    m = re.search(r"(\d+)\s*ms", soup.text)
    if m: result["time_ms"] = int(m.group(1))
    m2 = re.search(r"([\d\.]+)\s*M", soup.text)
    if m2: result["memory_kb"] = int(float(m2.group(1))*1024)
    ts = re.search(r"(\d{2}/\d{2})\s*(\d{2}:\d{2}:\d{2})", soup.text)
    if ts:
        try:
            dt = datetime.strptime(f"{ts.group(1)} {ts.group(2)}", "%m/%d %H:%M:%S")
            result["submission_time"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            result["submission_time"] = f"{ts.group(1)} {ts.group(2)}"
    with open(os.path.join(outdir, "result.json"), "w") as f:
        json.dump(result, f, indent=2)

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
    parser = argparse.ArgumentParser()
    submission_group = parser.add_mutually_exclusive_group()
    submission_group.add_argument("--submission_id", help="ID of the submission (numeric)")
    submission_group.add_argument("--file", "-f", help="File containing submission IDs (one per line)")
    parser.add_argument("--output-dir", "-o", default="rendered_submissions", 
                        help="Directory containing submission HTML files")
    args = parser.parse_args()
    
    output_dir = args.output_dir
    
    # Determine which submissions to process
    if args.submission_id:
        submissions = [args.submission_id]
    elif args.file:
        submissions = read_ids_from_file(args.file)
        print(f"Loaded {len(submissions)} submission IDs from {args.file}")
    else:
        # Process all HTML files in the output directory
        try:
            files = os.listdir(output_dir)
            submissions = [f.replace(".html", "") for f in files if f.endswith(".html") and not f.endswith("_tooltip.html")]
            print(f"Processing all {len(submissions)} submissions in {output_dir}")
        except Exception as e:
            print(f"Error reading directory {output_dir}: {e}")
            return
    
    for sid in submissions:
        html_file = f"{output_dir}/{sid}.html"
        if not os.path.exists(html_file):
            print(f"Warning: HTML file '{html_file}' not found for submission {sid}, skipping")
            continue
            
        print(f"Processing submission {sid}...")
        with open(html_file, encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        # C++ version from tooltip
        tip_file = f"{output_dir}/{sid}_tooltip.txt"
        cxx_version = None
        if os.path.exists(tip_file):
            with open(tip_file, encoding="utf-8") as tf:
                for line in tf:
                    if line.lower().startswith("c++ standard"):
                        parts = line.strip().split()
                        cxx_version = parts[-1]
                        break

        # submitter via /u/ link
        submitter = None
        u_link = soup.find("a", href=re.compile(r"^/u/"))
        if u_link:
            submitter = u_link.get_text(strip=True)
        # platform from <title>
        platform = ""
        if soup.title:
            parts = soup.title.get_text().split('-',1)
            if len(parts) == 2:
                platform = parts[1].strip()

        # problem folder
        link = soup.find("a", href=re.compile(r"^/p/\d+"))
        pid, pname = "unknown","problem"
        if link:
            m = re.match(r"^/p/(\d+)", link['href'])
            if m: pid = m.group(1)
            pname = re.sub(r"^#\d+\.\s*", "", link.get_text(strip=True))
        folder = f"data/{slugify(pname)}"
        os.makedirs(folder, exist_ok=True)

        samples = write_samples(soup, folder)
        subtasks = write_subtasks(soup)
        if samples:
            subtasks = {"0": {"task":"Samples","score":0,"testcases":samples}, **subtasks}
        with open(os.path.join(folder, "subtasks.json"), "w") as f:
            json.dump(subtasks, f, indent=2)

        write_solution_and_result(soup, folder, cxx_version, submitter, platform, sid, pid)
        print(f"Extracted to ./{folder}")

if __name__ == "__main__":
    main()
