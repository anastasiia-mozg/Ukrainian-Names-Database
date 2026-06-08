from abc import ABC, abstractmethod
from utils import custom_logger
from pathlib import Path

class OCRBase(ABC):
    def __init__(self, name:str, **kwargs) -> None:
        self.name = name
        self._logger = custom_logger.get_logger(self.name)

    @abstractmethod
    def ocr(self, input_file:Path, output_dir:Path, pages:str=None) -> None:
        """Performs OCR on a pdf file and saves the output in markdown file"""
        pass
