from pathlib import Path
from ocr.marker_pdf import OCRMarker

if __name__ == "__main__":

    maker = OCRMarker()
    pdf_path = Path("/home/kris/work/Ukrainian-Dictionary-Parser/data/downloads/власні_імена_людей/власні_імена_людей_2005.pdf")
    output_dir = Path("data/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    maker.ocr(input_file=pdf_path, output_dir=output_dir, name="marker_власні_імена_людей_2005.md", pages="30, 31, 128, 49-56, 114-117, 190-191")
