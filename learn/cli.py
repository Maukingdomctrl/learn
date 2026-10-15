"""Command line: python -m learn.cli path/to/curriculum.pdf --standard 7 [--topic ...] [--pages 3-5]"""
import argparse
import json
import os
import sys
import time

from . import config as C
from .pipeline import run, save_report


def make_llm():
    """The real Claude client, or None (with a reason) when the SDK or credentials are unavailable."""
    try:
        from .llm import AnthropicLLM
        return AnthropicLLM(C.model_name(), C.model_effort()), ""
    except Exception as e:  # missing credentials surface here or on the first call
        return None, str(e)


def main(argv=None) -> int:
    C.load_dotenv()
    ap = argparse.ArgumentParser(description="Generate a validated Learn lesson from a curriculum PDF.")
    ap.add_argument("pdf")
    ap.add_argument("--standard", type=int, required=True, choices=[7, 8])
    ap.add_argument("--topic", default="")
    ap.add_argument("--pages", default="", help="page range, e.g. 3-5 or 2,4")
    ap.add_argument("--out", default="", help="output folder (default: output/<timestamp>)")
    args = ap.parse_args(argv)

    out = args.out or os.path.join(C.output_dir(), time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(out, exist_ok=True)
    llm, why = make_llm()
    if llm is None:
        print(f"Claude client unavailable: {why}", file=sys.stderr)
    report = run(args.pdf, args.standard, llm, out, topic=args.topic, page_range=args.pages)
    path = save_report(report, out)
    print(report.parent_message)
    for a in report.parent_actions:
        print(f"  - {a}")
    for c in report.checks:
        print(f"  [{c['status']:>7}] {c['id']} {c['name']}" + (f": {c['problems'][0]}" if c["problems"] else ""))
    if report.status == "delivered":
        print(f"Student pages: {report.student_pdf}\nAnswer key:    {report.key_pdf}")
    print(f"Report: {path}")
    if report.timing:
        print(f"Calculated time: {report.timing['t_lesson']:.0f} s ({report.timing['minutes']} min)")
    print(json.dumps({"status": report.status, "stage": report.stage}))
    return 0 if report.status == "delivered" else 2


if __name__ == "__main__":
    sys.exit(main())
