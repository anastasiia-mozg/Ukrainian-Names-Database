import json
from pathlib import Path
from utils import custom_logger
from pypdf import PdfReader, PdfWriter
import re

class FileManager:
    def __init__(self):
        self.__logger = custom_logger.get_logger('File Manager')
        self.__page_str_pattern = r"(?P<interval>\d+-\d+)|(?P<page>\d+)"

    def read_md(self, path:Path) -> str:
        try:
            with open(path, mode="r", encoding="utf-8") as f:
                data = f.readlines()
                return "".join(data)
        except Exception as e:
            self.__logger.error(e)

    def write_md(self, data:str, path:Path, name:str="data.md") -> None:
        try:
            with open(path / name, mode="w", encoding="utf-8") as f:
                f.write(data)
        except Exception as e:
            self.__logger.error(e)

    def dict2jsonl(self, data: dict | list[dict], path: Path, name: str = "data.jsonl") -> bool:
        """Saves dictionary or list of dictionaries in JSONL format (one JSON object per line)."""
        try:
            full_path = path / name
            with open(full_path, 'w', encoding="utf-8") as f:
                if isinstance(data, dict):
                    json.dump(data, f, ensure_ascii=False)
                else:  # list of dicts
                    for item in data:
                        json.dump(item, f, ensure_ascii=False)
                        f.write('\n')
            self.__logger.info(f"Successfully saved file {name} in {path}")
            return True
        except Exception as e:
            self.__logger.error(f"During saving given dictionary an error occurred: {e}")
            return False
        
    def jsonl2dict(self, path: Path) -> list[dict]:
        """Loads jsonl file and transforms each line into a python dictionary"""
        try:
            data = []
            with open(path, 'r', encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
            return data
        except Exception as e:
            self.__logger.error(f"During extracting data from jsonl file an error occurred: {e}")
            return None

    def save2markdown(self, data, path: Path, name:str="data.md") -> None:
        """Saves markdown file"""
        try:
            full_path = path / name
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(data)
            self.__logger.info(f"Successfully saved file {name} in {path}")
        except Exception as e:
            self.__logger.error(f"During saving data an error occurred: {e}")
            return None

    def save2pdf(self, path: Path, writer:PdfWriter, name:str="data.pdf") -> None:
        """Saves pdf file from a PdfWriter instance"""
        try:
            full_path = path / name
            with open(full_path, "wb") as f:
                writer.write(f)
            self.__logger.info(f"Successfully saved file {name} in {path}")
        except Exception as e:
            self.__logger.error(f"During saving data an error occurred: {e}")
            return None

    def __parse_page_range(self, pages:str) -> dict:
        result = {
            "individual_pages": [],
            "page_intervals": []
        }

        for match in re.finditer(self.__page_str_pattern, pages):
            if match.group("page"):
                result["individual_pages"].append(int(match.group("page")) -1)
            else:
                interval = match.group("interval").split("-")
                start, end = int(interval[0]), int(interval[1])
                # range(start_page - 1, end_page)
                result["page_intervals"].append(range(start - 1, end))

        return result

    def get_target_pdf_page_range(self, path: Path, pages:str, output:Path, name:str="target.pdf"):
        """Saves creates a pdf file that contains only pages passed on a pages string.
            Regarding the pages parameter here are the expected string structure:
            -  to enumerate separate pages we use a comma ("50, 65, 98")
            -  to set an interval of pages we use a hyphen ("50-60")
            -  we can combine two of above ("50, 65, 98, 50-60")"""
        try:
            reader = PdfReader(path.__str__())
            writer = PdfWriter()
            parsed_intervals = self.__parse_page_range(pages)

            for page in parsed_intervals["individual_pages"]:
                writer.add_page(reader.pages[page])
            for interval in parsed_intervals["page_intervals"]:
                for i in interval:
                    writer.add_page(reader.pages[i])
            self.save2pdf(output, writer, name)
        except Exception as e:
            self.__logger.error(f"During saving data an error occurred: {e}")
            return None


    def split_pdf_into_pages(self, path: Path, output_dir: Path, chunk_size: int, name: str = None) -> list[Path]:
        """
        Split a PDF file into smaller chunks and save them to disk.

        Args:
            path:       Path to the source PDF file.
            output_dir: Directory where the chunk files will be written.
            chunk_size: Number of pages per chunk.
            name:       Optional stem for output filenames. Defaults to the
                        source file's stem if not provided.
                        Output files are named: `{name}-{start}-{end}.pdf`

        Returns:
            List of Paths to the written chunk files, in page order.
        """


        try:
            reader = PdfReader(path.__str__())
            page_num = len(reader.pages)
            output_paths = []

            for start in range(0, page_num, chunk_size):
                end = min(start + chunk_size, page_num)  # don't overshoot last chunk
                writer = PdfWriter()  # fresh writer per chunk

                for i in range(start, end):
                    writer.add_page(reader.pages[i])

                stem = name or path.stem
                file_name = f"{stem}-{start}-{end}.pdf"
                output_path = output_dir / file_name

                with open(output_path, "wb") as f:
                    writer.write(f)

                output_paths.append(output_path)

            return output_paths

        except Exception as e:
            self.__logger.error(f"Failed to split PDF '{path}': {e}")
