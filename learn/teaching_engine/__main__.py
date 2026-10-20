"""Run the offline teaching engine on a curriculum PDF."""

import argparse
import json
from pathlib import Path

from ..extraction import choose_ocr, extract, pdf_page_count
from ..grounding import parse_page_range
from . import create_teaching_lesson, extract_facts
from .cards import reject_generated_pdf
from .detective import render_printable_case_file_pdf


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a source-grounded teaching plan without an API key.")
    parser.add_argument("pdf", help="input curriculum PDF")
    parser.add_argument("--out", default="teaching_lesson.json", help="output JSON file")
    parser.add_argument("--pages", default="", help="optional page range, e.g. 3-5 or 2,4")
    parser.add_argument("--case-file", default="", help="also print a Detective case file PDF to this path")
    args = parser.parse_args(argv)

    data = Path(args.pdf).read_bytes()
    reject_generated_pdf(data)
    page_range = parse_page_range(args.pages, pdf_page_count(args.pdf))
    ocr, ocr_name = choose_ocr("auto", None)
    source = extract(args.pdf, ocr, ocr_name, page_range)
    lesson = create_teaching_lesson(extract_facts(source.units))
    result = {"lesson": lesson.model_dump(), "source_warnings": source.warnings}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved offline teaching plan to {output}")
    if args.case_file:
        try:
            case_file = render_printable_case_file_pdf(extract_facts(source.units), data, page_range)
        except ValueError as error:
            print(f"No Detective case file: {error}")
            return 2
        case_path = Path(args.case_file)
        case_path.parent.mkdir(parents=True, exist_ok=True)
        case_path.write_bytes(case_file)
        print(f"Saved Detective case file to {case_path}")
    if source.warnings:
        print("Review source warnings in the JSON output, especially unreadable or diagram-heavy pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
