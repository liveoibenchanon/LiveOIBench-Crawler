import abc
import os

class Crawler(metaclass = abc.ABCMeta):
    def __init__(self, *, competition, crawl_path, restructure_path, parse_path, converter):
        self._path = crawl_path
        self._restructure_path = restructure_path
        self._parse_path = parse_path
        self._competition = competition
        self.converter = converter
    @abc.abstractmethod
    def crawl(self):
        """
        Crawl the data from the competition website.Includes downloading the data, extracting the data, unzipping the data, etc.
        """
        pass
    @abc.abstractmethod
    def restructure(self):
        """
        Restructure the crawled data into a more manageable format. This may include organizing files, renaming them, etc.
        """
        pass
    @abc.abstractmethod
    def parse(self):
        """
        Parse the crawled data. The data may be in different formats like HTML, PDF, etc.
        """
        pass
    def _preprocess_parse(self, path, parse_statement=True, parse_solution=True, rerun=False, years=None):
        """
        Preprocess the data before parsing. This may include unzipping files, converting formats, etc.
        """
        if years is None:
            years = [year for year in os.listdir(path) if os.path.isdir(os.path.join(path, year))]
        for year in years:
            year_path = os.path.join(path, year)
            for round_name in os.listdir(year_path):
                round_path = os.path.join(year_path, round_name)
                for task in os.listdir(round_path):
                    task_path = os.path.join(round_path, task)
                    if not os.path.isdir(task_path) or task == "results":
                        continue
                    parsed_task_path = os.path.join(self._parse_path, year, round_name, task)
                    os.makedirs(parsed_task_path, exist_ok=True)
                    if parse_statement and os.path.exists(os.path.join(task_path, "statements", "statement.pdf")):
                        self.converter.convert(
                            os.path.join(task_path, "statements", "statement.pdf"),
                            os.path.join(parsed_task_path, "statements"),
                            rerun=rerun
                        )
                    if parse_solution and os.path.exists(os.path.join(task_path, "solutions", "editorial.pdf")):
                        self.converter.convert(
                            os.path.join(task_path, "solutions", "editorial.pdf"),
                            os.path.join(parsed_task_path, "solutions"),
                            rerun=rerun
                        )