from pathlib import Path
import torch
import shutil

from ocr.base import OCRBase
from utils.file_manager import FileManager

from paddleocr import PaddleOCRVL

class OCRPaddle(OCRBase):
    def __init__(self):
        super().__init__(name='OCR PADDLE VL')
        self.__fm = FileManager()
        self.pipeline = PaddleOCRVL(engine="transformers", device="gpu:0", use_doc_orientation_classify=True, use_doc_unwarping=True, use_layout_detection=True, pipeline_version="v1.5")


    def __get_target_pdf_path(self, doc:Path, output_dir:Path, pages:str) -> Path:
        file_name = f"{doc.stem}_target.pdf"
        self.__fm.get_target_pdf_page_range(doc, pages, output_dir, file_name)
        return output_dir / file_name


    def ocr(self, input_file:Path, output_dir:Path, pages:str=None, name:str=None) -> None:

        temp_dir_path = input_file.parent / "temp"

        try:
            temp_dir_path.mkdir(parents=True, exist_ok=True)
            target_pdf = self.__get_target_pdf_path(input_file, temp_dir_path, pages) if pages else input_file
            prediction = self.pipeline.predict(input=str(target_pdf), max_pixels=2048*2048)
            pages_res = list(prediction)

            # paddle processes and returns each page separately, so we need it to combine pages to get one parsed file
            restructured = self.pipeline.restructure_pages(pages_res, concatenate_pages=True)
            markdown_text = "\n\n".join(res.markdown["markdown_texts"] for res in restructured if res.markdown and res.markdown.get("markdown_texts"))
            output_file_name = name if name else f"paddle_ocr_{input_file.stem}.md"
            self.__fm.save2markdown(data=markdown_text, path=output_dir,name=output_file_name)

        except Exception as e:
            self._logger.error(e)

        finally:
            if temp_dir_path.exists():
                shutil.rmtree(temp_dir_path, ignore_errors=True)
