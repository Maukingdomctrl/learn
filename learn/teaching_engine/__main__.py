"""Run the offline teaching engine on a curriculum PDF."""

import argparse
import json
from pathlib import Path

from ..extraction import choose_ocr, extract, pdf_page_count
from ..grounding import parse_page_range
from . import create_teaching_lesson, extract_facts
from .cards import reject_generated_pdf
from .detective import plan_case_file, render_case_file_pdf
from .sheet import read_sheet


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a source-grounded teaching plan without an API key.")
    parser.add_argument("pdf", help="input curriculum PDF")
    parser.add_argument("--out", default="teaching_lesson.json", help="output JSON file")
    parser.add_argument("--pages", default="", help="optional page range, e.g. 3-5 or 2,4")
    parser.add_argument("--case-file", default="", help="also print a Detective case file PDF to this path")
    parser.add_argument(
        "--ai",
        action="store_true",
        help="let the card model (LEARN_PROVIDER, LEARN_CARDS_MODEL) choose the case file's cards; "
        "only LEARN_CARDS_AI_SHEETS sheets are sent (default 1)",
    )
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
            case_file = plan_case_file(read_sheet(extract_facts(source.units), data, page_range))
            if args.ai:
                case_file = _with_model(case_file)
            pdf = render_case_file_pdf(case_file)
        except ValueError as error:
            print(f"No Detective case file: {error}")
            return 2
        case_path = Path(args.case_file)
        case_path.parent.mkdir(parents=True, exist_ok=True)
        case_path.write_bytes(pdf)
        print(f"Saved Detective case file to {case_path}")
    if source.warnings:
        print("Review source warnings in the JSON output, especially unreadable or diagram-heavy pages.")
    return 0


def _with_model(case_file):
    """The case file with model-chosen cards where they pass every check, and what the calls used."""
    from .. import config as C
    from ..llm import AnthropicLLM
    from .ai_cards import write_with_model

    llm = AnthropicLLM.for_cards()
    result = write_with_model(case_file, llm, C.cards_sheet_limit())
    print(f"Model {llm.model} at {llm.effort} effort chose the cards for {result.ai_sheets} of {result.sheets} sheets.")
    for note in result.notes:
        print(f"  {note}")
    for call in llm.call_log:
        print(
            f"  call: {call['input_tokens']} tokens in, {call['output_tokens']} out "
            f"({call['thinking_tokens']} thinking), {call['seconds']} s, stop {call['stop_reason']}"
            + (f", error {call['error']}" if call["error"] else "")
        )
    return result.case_file


if __name__ == "__main__":
    raise SystemExit(main())
