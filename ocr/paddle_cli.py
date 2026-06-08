#!/usr/bin/env python3
"""
Runner script for OCRPaddle
Usage: python paddle_ocr_cli.py <input_file> [options]
"""

import argparse
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run PaddleOCR VL on a file and save output as Markdown"
    )
    parser.add_argument(
        "input_file",
        type=str,
        help="Path to the input file (PDF or image)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="Output directory for the Markdown file (default: same as input file)"
    )
    parser.add_argument(
        "-n", "--name",
        type=str,
        default=None,
        help="Custom output filename (default: paddle_ocr_<input_stem>.md)"
    )
    parser.add_argument(
        "-p", "--pages",
        type=str,
        default=None,
        help="Pages to process, e.g. '1-3,5' (optional)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    input_file = Path(args.input_file).resolve()
    if not input_file.exists():
        print(f"[ERROR] Input file not found: {input_file}")
        sys.exit(1)
    if not input_file.is_file():
        print(f"[ERROR] Input path is not a file: {input_file}")
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else input_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Input file  : {input_file}")
    print(f"[INFO] Output dir  : {output_dir}")
    if args.name:
        print(f"[INFO] Output name : {args.name}")
    if args.pages:
        print(f"[INFO] Pages       : {args.pages}")

    print("[INFO] Initializing OCRPaddle...")
    from ocr.paddle_pdf import OCRPaddle  # adjust import path if needed
    ocr = OCRPaddle()

    print("[INFO] Running OCR...")
    ocr.ocr(
        input_file=input_file,
        output_dir=output_dir,
        pages=args.pages,
        name=args.name,
    )

    expected_output = output_dir / (args.name if args.name else f"paddle_ocr_{input_file.stem}.md")
    if expected_output.exists():
        print(f"[OK] Output saved to: {expected_output}")
    else:
        print(f"[WARN] OCR finished but output file not found at: {expected_output}")
        print("      Check logs above for errors.")


if __name__ == "__main__":
    main()
