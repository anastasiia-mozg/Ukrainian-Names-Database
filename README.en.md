# Ukrainian Names Database ([База знань українських особових імен](README.md))

A machine-readable knowledge base of Ukrainian personal names with their variants, origin, and transliteration into Latin script.

The knowledge base was built on the third edition of the academic reference dictionary *Vlasni imena liudei* (*Personal Names*) by L. H. Skrypnyk and N. P. Dziatkivska (Kyiv: Naukova Dumka, 2005).

## What's inside

The finished knowledge base is located in `data/results/`:

- `ukrainian_names_database.jsonl` — the database of Ukrainian names;
- `transliterated_ukrainian_names_database.jsonl` — the same names with transliteration under several standards.

905 entries in total.

Each record contains:

- the documentary name;
- official variants of the name;
- informal (colloquial, hypocoristic) variants;
- a brief etymology and origin;
- transliteration into Latin script under several systems.

The data is stored in JSONL — a document-oriented (post-relational) format that freely accommodates the variable, nested structure of dictionary entries without a rigid relational schema.

## Repository structure

```
.
├── abbreviations.py           # Expansion table for dictionary abbreviations
├── data/
│   ├── dictionary/            # Source dictionary in Markdown (after OCR)
│   │   ├── dictionary_f.md    # Female names section
│   │   ├── dictionary_m.md    # Male names section
│   │   └── shorts.md          # List of abbreviations used in the dictionary
│   ├── parsed_dict/           # Stage 1: macro-parsing (one entry per line)
│   ├── parsed_entries/        # Stage 2: micro-parsing (structured fields)
│   └── results/               # The finished knowledge base
├── dev.ipynb                  # Development notebook
├── ocr/                       # PDF → Markdown via three tools
│   ├── base.py
│   ├── marker_pdf.py
│   ├── marker_pdf_cli.py
│   ├── mistral_pdf.py
│   ├── paddle_pdf.py
│   └── paddle_cli.py
├── parsers/
│   ├── macro_parser.py        # Splits the Markdown into individual entries
│   └── micro_parser.py        # Extracts structured fields from each entry
├── patterns/
│   ├── macro_structure_patterns.py
│   └── micro_structure_patterns.py            # Regular expressions for the parsers
├── test_app/
│   └── app.py                 # Interface for verifying parsed entries
└── utils/
    ├── custom_logger.py
    ├── drive_downloader.py    # Helper module for downloading the source PDF
    ├── file_manager.py
    ├── name_transformer.py    # Normalization of name forms
    └── transliterater.py      # Wrapper around translit-ua
```

## How the knowledge base was created

The data was produced in several sequential stages:

1. **OCR** The source dictionary, available only as a scanned PDF (not included in the repository), was converted to Markdown using Mistral Document AI (see `data/dictionary/`).
2. **Macro-parsing** (`parsers/macro_parser.py`). The Markdown is split into individual entries — one per name — and saved to `data/parsed_dict/`.
3. **Micro-parsing** (`parsers/micro_parser.py`). Each entry is parsed into structured fields — the documentary name, its variants, and its origin. The result is saved to `data/parsed_entries/`.
4. **Verification** `test_app/app.py` provides an interface for checking the parsed entries against the source.
5. **Transliteration** (`utils/transliterater.py`). Each name and its variants are transliterated under several standards using the `translit-ua` library.
6. **Merging** The names database and the transliteration database are merged into a single knowledge base — the files in `data/results/`.

## Source

The knowledge base was built on the academic dictionary: Скрипник Л. Г., Дзятківська Н. П. Власні імена людей: словник-довідник / За ред. В. М. Русанівського. — 3-тє вид., випр. — Київ: Наукова думка, 2005. — 334 с.
