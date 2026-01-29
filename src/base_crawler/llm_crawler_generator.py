import os
from io import BytesIO
import json
import re

from google import genai
from google.genai import types

import pathlib
from tenacity import retry, wait_exponential, stop_after_attempt
from tqdm import tqdm
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


def get_folder_structure(root_path, file_limit=10):
    lines = []
    root_path = os.path.abspath(root_path)

    for root, dirs, files in os.walk(root_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        # Determine level
        rel_path = os.path.relpath(root, root_path)
        level = 0 if rel_path == "." else rel_path.count(os.sep) + 1
        indent = "    " * level
        lines.append(f"{indent}{os.path.basename(root)}/")

        # Apply file limit only for levels deeper than 0
        if level > 0 and len(files) > file_limit:
            lines.append(f"{indent}    ... ({len(files)} files)")
            continue

        subindent = "    " * (level + 1)
        for f in files:
            if not f.startswith('.'):  # Optional: ignore hidden files too
                lines.append(f"{subindent}{f}")

    return "\n".join(lines)



class LLMCrawler():
    def __init__(self, llm):
        self.llm = llm
        if "gemini" in llm:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
        elif "gpt" in llm:
            raise NotImplementedError("GPT-4 is not supported yet")
        else:
            raise NotImplementedError("Only Gemini is supported")

    def generate_gemini_answer(self, prompt):
        content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=24576),
            max_output_tokens=65536,
            temperature=1,
        )
        response = self.client.models.generate_content(
            model=self.llm,
            contents=[
                prompt
            ],
            config=content_config,
        )
        return response

    def return_prompt(self, competition, year, output_dir, url, html_file):
        # Read the HTML file
        with open(html_file, "r") as f:
            html_content = f.read()
        prompt = f"""
        HTML file: {html_file}
        Given the html file of the {competition}-{year} competition with url: {url}, I want you write a python program to crawl all the problems and their related information from the html file, which includes problem statements, test data, solution files, editorial files, translations, graders, and attachments, and other related files. The output should have the following structure and save it in the {output_dir} folder:
        - {year}
            - day0
            - day1
                ....
            - day2
                ....
        If there is a zip file, please unzip it. Only download the English version of statements. Also, you can modify the folder structure if you think it is necessary to make it more organized. You should return the python program surrdounded by "```"python" and "```" tags. The program should be able to run without any errors. The program should be well-structured and easy to understand. You can use any libraries you want, but please make sure to include the import statements at the beginning of the program. The program should be able to handle any edge cases and should be robust enough to handle any errors that may occur during the crawling process. Please make sure to include comments in the code to explain what each part of the code does.
        """
        return prompt  # This was missing
    def return_restructure_prompt(self, competition, year, input_dir, output_dir):
        folder_structure = get_folder_structure(input_dir)
        prompt = f"""
        Given the folder structure of the {competition}-{year} competition:
        {folder_structure}
        This is a folder at {input_dir} containing {competition}-{year} contests. Write a Python program surrdounded by "```"python" and "```" tags to extract problem statements, code solutions, editorials (reviews, solution booklet, non-code solution files), tests, grader, checker, and attachments (any public files that are available to contestants during the contest). Treat practice as day0. The output folder should be saved at {output_dir}, have the following structure:

        ├── <{year}>/

        │ ├─editorial (if individual task editorial is not available)

        │ ├─<day>/

        │ ├── <task_name>/

        │ │ ├── statements/

        │ │ ├── graders/

        │ │ ├── checkers/

        │ │ ├── tests/

        │ │ ├── attachments/

        │ │ ├── solutions/

        │ │ │ ├── Codes/ (copy the original code folder if available)

        │ │ │ ├── editorial/

        │ │ ├── subtasks/

        │ │ └── problem.json if exist
        """
        return prompt 
    def generate_crawler_code(self, competition, year, output_dir, html_file, prediction_path, url, mode="crawler"):
        if mode == "crawler":
            prompt = self.return_prompt(competition, year, output_dir, url, html_file)
        elif mode == "restructure":
            input_dir = f"{os.environ['HOME_DIR']}/IOI-Bench/{competition}/{year}"
            prompt = self.return_restructure_prompt(competition, year, input_dir, output_dir)
        print(prompt)
        response = self.generate_gemini_answer(prompt)
        
        # Extract the code from the response
        content = response.text
        
        pattern = r"```(?:python|cpp|c\+\+)?([\s\S]*?)```"
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            code = match.group(1).strip()
            if code:
                # Check and fix first line if needed
                lines = code.split('\n')
                first_line = lines[0].strip()
                
                # If the first line is 'python', remove it
                if first_line.lower() == 'python':
                    code = '\n'.join(lines[1:])
                
                # Save extracted code
                with open(f"{prediction_path}/{competition}_{year}_{mode}_old.py", "w") as f:
                    f.write(code)
            else:
                print(f"No code found in the response for {competition}-{year}.")
        else:
            print(f"No code found in the response for {competition}-{year}.")
        
        # Also save the response to a file
        with open(f"{prediction_path}/{competition}_{year}_response_{mode}_old.json", "w") as f:
            json.dump(response.to_json_dict(), f)
        
        return response

if __name__ == "__main__":
    
    #llm = "gemini-2.5-pro-exp-03-25"
    for year in tqdm(range(2002,2022)):
        llm = "gemini-2.5-pro-exp-03-25"
        competition = "IOI"
        year = str(year)
        output_dir = f"{os.environ['HOME_DIR']}/IOI-Bench/{competition}-Processed-2/"
        html_file = f"{os.environ['HOME_DIR']}/IOI-Bench/{competition}/htmls/{year}.html"
        prediction_path = f"{os.environ['HOME_DIR']}/ioi-benchmark/ioi-crawler/src/llm_crawlers"
        url =  f"https://ioi.te.lv/locations/ioi{year[-2:]}/contest/"
        
        crawler = LLMCrawler(llm)
        response = crawler.generate_crawler_code(competition, year, output_dir, html_file, prediction_path, url, mode="restructure")
