# Marker Python API
from .converter import Converter
import os
from io import BytesIO
import json
import re

from google import genai
from google.genai import types

import pathlib
from tenacity import retry, wait_exponential, stop_after_attempt

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
def extract_block(response_text, type_block):
    if type_block == "json":
        match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
    elif type_block == "markdown":
        match = re.search(r"```markdown\s*(.*?)\s*```", response_text, re.DOTALL)
    if match:
        text = match.group(1)
        if type_block == "json":
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                print(f"Failed to parse {type_block}:", e)
                return text  # return raw string if JSON is invalid
        elif type_block == "markdown":
            return text
    return None
def extract_markdown_block(text):
    start_index = text.find("```markdown") + len("```markdown")
    end_index = text.rfind("```")
    markdown_text = text[start_index:end_index].strip()
    return markdown_text
class LLMConverter(Converter):
    def __init__(self, llm):
        self.llm = llm
        if "gemini" in llm:
            self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        elif "gpt" in llm:
            raise NotImplementedError("GPT-4 is not supported yet")
        else:
            raise NotImplementedError("Only Gemini is supported")
    def return_prompt(self, marker_statement, file_name='statement'):
        prompt = f"""
        You are a formatting and conversion expert.

        I have a problem {file_name} from an informatics contest that was originally written in PDF. It has been automatically converted to Markdown, but the result may contain the following issues:
        - Broken or inconsistent formatting
        - Missing or incorrectly rendered equations
        - Distorted or misaligned tables
        - Incorrect or shuffled section order
        - Minor OCR or conversion artifacts

        Your task is to **carefully compare the original content (from the PDF) and the auto-generated Markdown**, and then output a clean, corrected, and well-structured Markdown version of the problem {file_name}.

        **Instructions:**
        - Preserve the original structure of the {file_name} (e.g., title, input/output specification, constraints, examples, and explanation).
        - Keep all existing image links as-is (do not remove them).
        - Do *not* include or reformat images—just leave their paths untouched.
        - Make reasonable assumptions to fix formatting errors and recover mathematical notation.

        ---

        ### Current Markdown
        {marker_statement}
        ---

        ### Output Format

        First, list the changes you made in JSON format, describing what was fixed. Wrap this section in:

        \`\`\`json  
        <your list of changes here>  
        \`\`\`

        Then, provide the final improved Markdown in:

        \`\`\`markdown  
        <your corrected Markdown here>  
        \`\`\`

        Only return these two blocks, nothing else.
        """
        return prompt
    
    @retry(wait=wait_exponential(multiplier=1, min=1, max=30), stop=stop_after_attempt(10), reraise=True)
    def generate_gemini_answer(self, prompt, filepath):
        filepath = pathlib.Path(filepath)
        response = self.client.models.generate_content(
            model=self.llm,
            contents=[
                types.Part.from_bytes(
                    data=filepath.read_bytes(),
                    mime_type='application/pdf',
                ),
                prompt
            ]
        )
        return response
    def convert(self, file, output_path, rerun, marker_file=None, file_name='statement'):
        fname_base = os.path.splitext(os.path.basename(file))[0] + f"_{self.llm}"
        #save_output(rendered, output_path, fname_base)
        if not rerun and os.path.exists(os.path.join(output_path, f"{fname_base}.md")):
            # with open(os.path.join(output_path, self.llm, f"raw.json"), "r") as f:
            #     response = json.load(f)
            # full_text = response["candidates"][0]["content"]["parts"][0]["text"]
            # markdown_text = extract_markdown_block(full_text)
            # with open(os.path.join(output_path, f"{fname_base}.md"), "w") as f:
            #     f.write(markdown_text)
            print(f"File already exists: {os.path.join(output_path, f'{fname_base}.md')}")

            return None
        if os.path.exists(marker_file):
            with open(marker_file, "r") as f:
                marker_statement = f.read()
        else:
            print(f"Marker file not found: {marker_file}")
            return None
        
        prompt = self.return_prompt(marker_statement, file_name=file_name)
        
        try:
            response = self.generate_gemini_answer(prompt, file)
        except Exception as e:
            print(f"Error during generation: {e}")
            return

        # Create a folder for the output file if it doesn't exist
        file_folder = os.path.join(output_path, self.llm)
        os.makedirs(file_folder, exist_ok=True)
        # Save the response to a file
        with open(os.path.join(file_folder, f"raw.json"), "w") as f:
            json.dump(response.to_json_dict(), f)
        # match the json that is surrounded by ```json ```
        text = response.text
        json_text = extract_block(text, "json")
        markdown_text = extract_markdown_block(text)
        with open(os.path.join(file_folder, f"changes.json"), "w") as f:
            json.dump(json_text, f)
        with open(os.path.join(output_path, f"{fname_base}.md"), "w") as f:
            f.write(markdown_text)
        print(f"Converted {file} to {fname_base}.md")
    def parse_competition(self, path, parse_path, parse_statement=True, parse_solution=True, rerun=False, years=None):
        total_statements = 0
        total_editorials = 0
        missing_statements = []
        missing_editorials = []
        if years is None:
            years = [year for year in os.listdir(path) if os.path.isdir(os.path.join(path, year))]
        for year in years:
            year_path = os.path.join(path, year)
            for round_name in os.listdir(year_path):
                round_path = os.path.join(year_path, round_name)
                if not os.path.isdir(round_path):
                    continue
                for task in os.listdir(round_path):
                    task_path = os.path.join(round_path, task)
                    if not os.path.isdir(task_path) or task == "results":
                        continue
                    parsed_task_path = os.path.join(parse_path, year, round_name, task)
                    os.makedirs(parsed_task_path, exist_ok=True)
                    if parse_statement and os.path.exists(os.path.join(task_path, "statements", "statement.pdf")):
                        self.convert(
                            os.path.join(task_path, "statements", "statement.pdf"),
                            os.path.join(parsed_task_path, "statements"),
                            rerun=rerun,
                            marker_file=os.path.join(parsed_task_path, "statements", "statement_marker.md")
                        )
                    if parse_solution and os.path.exists(os.path.join(task_path, "solutions", "editorial.pdf")):
                        self.convert(
                            os.path.join(task_path, "solutions", "editorial.pdf"),
                            os.path.join(parsed_task_path, "solutions"),
                            rerun=rerun,
                            marker_file=os.path.join(parsed_task_path, "solutions", "editorial_marker.md"),
                            file_name='editorial'
                        )
                    if os.path.exists(os.path.join(parsed_task_path, "statements", f"statement_{self.llm}.md")):
                        total_statements += 1
                    elif parse_statement:
                        missing_statements.append(os.path.join(parsed_task_path))
                    if os.path.exists(os.path.join(parsed_task_path, "solutions", f"editorial_{self.llm}.md")):
                        total_editorials += 1
                    elif parse_solution:
                        missing_editorials.append(os.path.join(parsed_task_path))
        return total_statements, total_editorials, missing_statements, missing_editorials

