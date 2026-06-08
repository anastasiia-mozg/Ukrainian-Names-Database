import torch
from pathlib import Path

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.config.parser import ConfigParser

from ocr.base import OCRBase
from utils.file_manager import FileManager


class OCRMarker(OCRBase):
    def __init__(self):
        super().__init__(name='OCR MARKER')
        self.__fm = FileManager()
        self.__device = "cuda" if torch.cuda.is_available() else "cpu"

    #we need it to create a proper config for a model and in time identify errors
    def __get_config_parser(self, pages:str):
        config = {"output_format": "markdown",
                  "force_ocr": True,
                   "page_range": pages,
                 }
        try:
            config_parser = ConfigParser(config)
            return config_parser
        except Exception as e:
            self._logger.critical(f"There was an error during config creation: {e}")


    def ocr(self, input_file:Path, output_dir:Path, name:str=None, pages:str=None) -> None:
        """Performs OCR on a pdf file and saves the output in markdown file
        - the input_file parameter must be a path to a pdf file.
        - the output_dir parameter must be a path to a directory where a markdown file will be saved.
        - the pages parameter specifies what pages of a given file to process.
        - regarding the pages parameter here are some tips:
            -  to enumerate separate pages we use a comma ("50, 65, 98")
            -  to set an interval of pages we use a hyphen ("50-60")
            -  we can combine two of above ("50, 65, 98, 50-60")
        """
        name = name or input_file.stem
        try:
            self._logger.info(f"Using device: {self.__device}")
            config_parser = self.__get_config_parser(pages)
            converter = PdfConverter(
                            config=config_parser.generate_config_dict(),
                            artifact_dict=create_model_dict(),
                            processor_list=config_parser.get_processors(),
                            renderer=config_parser.get_renderer(),
                            )
            rendered = converter(input_file.__str__()) # we use .__str__() as converter expects str not Path object
            markdown_text = rendered.markdown
            self.__fm.save2markdown(markdown_text, output_dir, f"{name}.md")
            self._logger.info(f"The {input_file.name} has successfully been processed and stored in {output_dir}")
        except Exception as e:
            self._logger.critical(f"During the processing of a {input_file} an error occurred: {e}")

