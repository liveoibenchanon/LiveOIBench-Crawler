# Marker Python API
from .converter import Converter
import os
from io import BytesIO
import json

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered, save_output
from marker.config.parser import ConfigParser
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
#
import torch

class MarkerConverter(Converter):
    def __init__(self, source_format, target_format, use_LLM=True):
        self.source_format = source_format
        self.target_format = target_format
        self.config = {
            "output_format": target_format,
            "redo_inline_math": True,
            "use_llm": use_LLM,
            "gemini_api_key": GEMINI_API_KEY,
        }
        config_parser = ConfigParser(self.config)

        self.converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
            llm_service=config_parser.get_llm_service()
        )
        self.converter.llm_service.max_retries = 10
        self.converter.llm_service.timeout = 120
    def convert(self, file, output_path, rerun, **kwargs):
        fname_base = os.path.splitext(os.path.basename(file))[0] + "_marker"
        #save_output(rendered, output_path, fname_base)
        if not rerun and os.path.exists(os.path.join(output_path, f"{fname_base}.md")):
            print(f"File already exists: {os.path.join(output_path, f'{fname_base}.md')}")
            return None
        
        rendered = self.converter(file)
        text_mardown, metadata, images = text_from_rendered(rendered)

        os.makedirs(output_path, exist_ok=True)
        with open(os.path.join(output_path, f"{fname_base}.md"), "w", encoding="utf-8") as f:
            f.write(text_mardown)
        # Save metadata to a JSON file
        if metadata:
            with open(os.path.join(output_path, f"{fname_base}_metadata.json"), "w", encoding="utf-8") as meta_file:
                json.dump(metadata, meta_file, ensure_ascii=False, indent=4)
        if images:
            img_dir = os.path.join(output_path, "images")
            os.makedirs(img_dir, exist_ok=True)
            # Save images to the specified directory
            for img_name, img_data in images.items():
                img_bytes_io = BytesIO()  # Create a BytesIO stream
                img_data.save(img_bytes_io, format="JPEG")  # Convert image to bytes, specify format
                img_bytes = img_bytes_io.getvalue()  # Get byte data
                with open(os.path.join(img_dir, img_name), "wb") as img_file:
                    img_file.write(img_bytes)  # Write byte data to file
        return metadata
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
                            rerun=rerun
                        )
                    if parse_solution and os.path.exists(os.path.join(task_path, "solutions", "editorial.pdf")):
                        self.convert(
                            os.path.join(task_path, "solutions", "editorial.pdf"),
                            os.path.join(parsed_task_path, "solutions"),
                            rerun=rerun
                        )
                    if os.path.exists(os.path.join(parsed_task_path, "statements", "statement_marker.md")):
                        total_statements += 1
                    elif parse_statement:
                        missing_statements.append(os.path.join(parsed_task_path))
                    if os.path.exists(os.path.join(parsed_task_path, "solutions", "editorial_marker.md")):
                        total_editorials += 1
                    elif parse_solution:
                        missing_editorials.append(os.path.join(parsed_task_path))
                    
        return total_statements, total_editorials, missing_statements, missing_editorials