import base64
import json
import os
import shutil
import time
from typing import List, Optional

from pathlib import Path

from mistralai.client import Mistral

from ocr.base import OCRBase
from utils.file_manager import FileManager

from dotenv import load_dotenv
load_dotenv("secrets.env")


class OCRMistral(OCRBase):
    def __init__(self):
        super().__init__(name='OCR MISTRAL')
        self.__fm = FileManager()
        self.__api_key = self.__get_api_key()
        self.__client = self.__connect_to_client()

    def __get_api_key(self):
        """Checks whether the API key is accessible in the environment."""
        try:
            key = os.getenv("MISTRAL_API_KEY")
            return key
        except Exception as e:
            self._logger.error(f"There was an error during retrieving api key from the environment: {e}")

    def __connect_to_client(self):
        """Connects to mistral server"""
        try:
            client = Mistral(api_key=self.__api_key)
            return client
        except Exception as e:
            self._logger.error(f"Error: {e}")
            return None

    def get_ocr_models(self) -> List[str]:
        """Fetches all OCR-capable models from the Mistral API."""
        all_models = self.__client.models.list()
        return [
            m.id for m in all_models.data
            if "ocr" in m.id.lower()
        ]

    def __encode_pdf(self, pdf_path: Path) -> Optional[str]:
        """Encode the pdf to base64."""
        try:
            with open(pdf_path, "rb") as pdf_file:
                content = pdf_file.read()
                self._logger.warn(f"Encoding {pdf_path.name}: {len(content)} bytes")
                return base64.b64encode(content).decode('utf-8')
        except FileNotFoundError:
            self._logger.error(f"File not found: {pdf_path}")
            return None
        except Exception as e:
            self._logger.error(f"Error encoding {pdf_path}: {e}")
            return None


    def __get_combined_markdown(self, ocr_response) -> str:
        """
        Combine OCR text from all pages into a single markdown string.

        Args:
            ocr_response: Response from OCR processing containing text per page.

        Returns:
            Combined markdown string.
        """
        markdowns: list[str] = []
        for page in ocr_response.pages:
            markdowns.append(page.markdown)
        return "\n\n".join(markdowns)

    def __get_target_pdf_path(self, doc: Path, output_dir: Path, pages: str) -> Path:
        """Gets the path to the target pdf file"""
        file_name = f"{doc.stem}_target.pdf"
        self.__fm.get_target_pdf_page_range(doc, pages, output_dir, file_name)
        return output_dir / file_name

    def __create_requests(self, file_path: Path, temp_dir: Path, chunk_size: int) -> List[dict]:
        """Creates requests for inline batch processing, where each request is a chunk of the document."""
        split_pdf_paths = self.__fm.split_pdf_into_pages(file_path, temp_dir, chunk_size)
        requests = []
        for i, doc in enumerate(split_pdf_paths):
            encoded = self.__encode_pdf(doc)
            if not encoded:
                self._logger.error(f"Failed to encode chunk {i}: {doc}")
                continue
            requests.append({
                "custom_id": f"{i}",
                "body": {
                    "document": {
                        "type": "document_url",  # ← was missing
                        "document_url": f"data:application/pdf;base64,{encoded}"  # ← was a local path
                    }
                }
            })
        return requests

    def __create_batch_job(self, model: str, requests: list) -> Optional[str]:
        """
        Creates a batch job and returns its ID.

        Args:
            model: The OCR model to use.
            requests: List of request dicts for batch processing.

        Returns:
            The batch job ID, or None on failure.
        """
        try:
            created_job = self.__client.batch.jobs.create(
                requests=requests,
                model=model,
                endpoint="/v1/ocr",
            )
            self._logger.info(f"Created batch job: {created_job.id}")
            return created_job.id
        except Exception as e:
            self._logger.error(f"Error creating batch job: {e}")
            return None

    def __poll_batch_job(self, job_id: str, poll_interval: int = 10, timeout: int = 3600) -> Optional[object]:
        """
        Polls a batch job until it completes or times out.

        Args:
            job_id: The batch job ID to poll.
            poll_interval: Seconds between polls (default 10).
            timeout: Max seconds to wait before giving up (default 3600).

        Returns:
            The completed job object, or None on failure/timeout.
        """
        elapsed = 0
        while elapsed < timeout:
            try:
                job = self.__client.batch.jobs.get(job_id=job_id)
                status = job.status
                self._logger.info(f"Batch job {job_id} status: {status} ({elapsed}s elapsed)")

                if status == "SUCCESS":
                    return job
                elif status in ("FAILED", "CANCELLED", "TIMEOUT_REACHED"):
                    self._logger.error(f"Batch job {job_id} ended with status: {status}")
                    return None

                time.sleep(poll_interval)
                elapsed += poll_interval
            except Exception as e:
                self._logger.error(f"Error polling batch job {job_id}: {e}")
                return None

        self._logger.error(f"Batch job {job_id} timed out after {timeout}s.")
        return None

    def __collect_batch_results(self, job) -> str:
        """
        Downloads and combines markdown results from a completed batch job,
        ordered by custom_id (chunk index).

        Args:
            job: The completed batch job object.

        Returns:
            Combined markdown string from all chunks.
        """
        try:
            result_file = self.__client.files.download(file_id=job.output_file)
            raw_content = result_file.read().decode("utf-8")

            # Each line in the output file is a JSON object (JSONL format)
            results: dict[int, str] = {}
            for line in raw_content.strip().splitlines():
                if not line.strip():
                    continue
                entry = json.loads(line)
                chunk_index = int(entry["custom_id"])
                # Extract markdown from the OCR response body
                pages = entry.get("response", {}).get("body", {}).get("pages", [])
                chunk_markdown = "\n\n".join(p.get("markdown", "") for p in pages)
                results[chunk_index] = chunk_markdown

            # Reassemble in order
            ordered_chunks = [results[i] for i in sorted(results.keys())]
            return "\n\n".join(ordered_chunks)
        except Exception as e:
            self._logger.error(f"Error collecting batch results: {e}")
            return ""

    def __process_pdf_inline(self, input_file: Path, model: str) -> Optional[str]:
        """
        Processes a single PDF synchronously using the OCR endpoint.

        Args:
            input_file: Path to the PDF file.
            model: The OCR model to use.
        Returns:
            Combined markdown string, or None on failure.
        """
        base64_pdf = self.__encode_pdf(input_file)
        if not base64_pdf:
            self._logger.critical(f"Unable to process input file: {input_file}")
            return None

        ocr_kwargs = dict(
            model=model,
            document={
                "type": "document_url",
                "document_url": f"data:application/pdf;base64,{base64_pdf}",
            },
            include_image_base64=False,
        )

        pdf_response = self.__client.ocr.process(**ocr_kwargs)
        return self.__get_combined_markdown(pdf_response)

    def __process_pdf_batch(self, input_file: Path, temp_dir: Path, model: str, chunk_size: int) -> Optional[str]:
        """
        Processes a PDF via Mistral batch jobs (async, chunked).

        Args:
            input_file: Path to the PDF file.
            temp_dir: Temporary directory for split chunks.
            model: The OCR model to use.
            chunk_size: Number of pages per chunk.

        Returns:
            Combined markdown string, or None on failure.
        """
        requests = self.__create_requests(input_file, temp_dir, chunk_size)
        job_id = self.__create_batch_job(model, requests)
        if not job_id:
            return None

        completed_job = self.__poll_batch_job(job_id)
        if not completed_job:
            return None

        return self.__collect_batch_results(completed_job)

    def __process_pdf(self, input_file: Path, temp_dir: Path, model: str, batches: bool, chunk_size: int) -> Optional[str]:
        """
        Dispatches PDF processing to either inline or batch mode.

        Args:
            input_file: Path to the (possibly page-filtered) PDF.
            temp_dir: Temporary directory for intermediate files.
            model: The OCR model to use.
            batches: Whether to use batch processing.
            chunk_size: Pages per batch chunk (only relevant if batches=True).

        Returns:
            Combined markdown string, or None on failure.
        """
        if batches:
            return self.__process_pdf_batch(input_file, temp_dir, model, chunk_size)
        else:
            return self.__process_pdf_inline(input_file, model)

    def ocr(
        self,
        input_file: Path,
        output_dir: Path,
        model: str = "mistral-ocr-latest",
        batches: bool = False,
        chunk_size: int = 20,
        pages: str = None,
        name: str = None,
    ) -> None:
        """
        Main entry point. Runs OCR on a PDF and saves the result as markdown.

        Args:
            input_file: Path to the source PDF.
            output_dir: Directory where the markdown output will be saved.
            model: Mistral OCR model to use.
            batches: If True, use async batch processing; otherwise use inline.
            chunk_size: Pages per chunk for batch mode.
            pages: Optional page range string (e.g. "1-5") to process a subset.
            name: Optional output filename (defaults to mistral_ocr_<stem>.md).
        """
        temp_dir_path = input_file.parent / "temp"
        try:
            temp_dir_path.mkdir(exist_ok=True)

            target_pdf = self.__get_target_pdf_path(input_file, temp_dir_path, pages) if pages else input_file
            self._logger.warn(f"target_pdf exists: {target_pdf.exists()} — {target_pdf}")

            combined_pages = self.__process_pdf(
                input_file=target_pdf,
                temp_dir=temp_dir_path,
                model=model,
                batches=batches,
                chunk_size=chunk_size,
            )

            if not combined_pages:
                self._logger.error("OCR returned no content.")
                return None

            output_file_name = name if name else f"mistral_ocr_{input_file.stem}.md"
            self.__fm.save2markdown(combined_pages, output_dir, output_file_name)
            self._logger.info(f"The file was successfully converted and saved in {output_dir}")

        except Exception as e:
            self._logger.error(f"Error: {e}")
            return None
        finally:
            if temp_dir_path.exists():
                shutil.rmtree(temp_dir_path, ignore_errors=True)