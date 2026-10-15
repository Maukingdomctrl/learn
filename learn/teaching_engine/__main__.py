"""Run the offline teaching engine on a curriculum PDF."""

import argparse
import json
from pathlib import Path

from ..extraction import choose_ocr, extract, pdf_page_count
from ..grounding import parse_page_range
from . import create_teaching_lesson, extract_facts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a source-grounded teaching plan without an API key.")
    parser.add_argument("pdf", help="input curriculum PDF")
    parser.add_argument("--out", default="teaching_lesson.json", help="output JSON file")
    parser.add_argument("--pages", default="", help="optional page range, e.g. 3-5 or 2,4")
    args = parser.parse_args(argv)

    page_range = parse_page_range(args.pages, pdf_page_count(args.pdf))
    ocr, ocr_name = choose_ocr("auto", None)
    source = extract(args.pdf, ocr, ocr_name, page_range)
    lesson = create_teaching_lesson(extract_facts(source.units))
    result = {"lesson": lesson.model_dump(), "source_warnings": source.warnings}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved offline teaching plan to {output}")
    if source.warnings:
        print("Review source warnings in the JSON output, especially unreadable or diagram-heavy pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
