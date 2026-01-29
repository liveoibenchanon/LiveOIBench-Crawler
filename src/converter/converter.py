import abc

class Converter(metaclass = abc.ABCMeta):
    def __init__(self, source_format, target_format):
        self.source_format = source_format
        self.target_format = target_format

    @abc.abstractmethod
    def convert(self, file, output_path, rerun, **kwargs):
        """
        Convert the file from source_format to target_format.
        :param file: The input file to convert.
        :param output_path: The path to save the converted file.    "
        """
        pass