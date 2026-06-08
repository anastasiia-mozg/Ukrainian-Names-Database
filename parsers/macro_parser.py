from utils import custom_logger
from typing import List
from utils import file_manager, custom_logger
from pathlib import Path
import re

class MacroParser:
    def __init__(self):
        self.__logger = custom_logger.get_logger('Macro Parser')
        self.__fm = file_manager.FileManager()
        self.md_pattern = r"(\!\[[^\]]+\]\([^\)]+\))|([\*\#><])"

    def __replace_md(self, text:str) -> str:
        return re.sub(self.md_pattern, "", text)

    def parse(self, text:str, pattern:str, flags:int=re.MULTILINE) -> List[dict]:
        """
        Try to find all matches of *pattern* in *text*.

        Returns:
            A list of dicts with named groups on success, or an empty list on no-match / error.
        """
        try:
            matches = re.findall(pattern=pattern, string=text, flags=flags)
            parsed_entries = [{"id": i, "entry": content} for i, content in enumerate(matches)]
            return parsed_entries
        except Exception as e:
            self.__logger.error(f"{e}")
            return []

    def parse_dict(self, file_path:Path, output_path:str, pattern:str, flags:int=re.MULTILINE, replace_md=False, name:str=None):
        """
        Try to find all matches of *pattern* in *text* and saves the results as a JSONL file.

        Returns:
            None
        """
        try:
            text = self.__fm.read_md(file_path)
            target_text = self.__replace_md(text) if replace_md else text
            parsed_entries = self.parse(text=target_text, pattern=pattern, flags=flags)
            self.__fm.dict2jsonl(data=parsed_entries, path=Path(output_path), name=name)
        except Exception as e:
            self.__logger.error(f"{e}")