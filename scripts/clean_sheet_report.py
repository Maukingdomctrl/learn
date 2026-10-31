"""Run `clean_sheet(pdf)` on every PDF in `fixtures/sheets/` (or a specified folder)
and print/write `fixtures/clean_sheet_report.md` showing, per sheet, every line in
reading order marked `KEEP` (with `kind`, `subject`, `section`) or `REMOVE(reason)`.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from learn.teaching_engine.card_quality import (
    _iter_sheet_lines_with_pages,
    _merge_wrapped_and_hyphenated_page_lines,
)
from learn.teaching_engine.key_facts_input import clean_sheet
from question_quality_engine import PDFExtractionEngine
from scripts.key_facts_report import save_attached_sheets


def inspect_sheet_reading_order(pdf_path: Path) -> dict[str, Any]:
    """Run `clean_sheet` on `pdf_path` and build a reading-order trace of KEEP vs REMOVE(reason)."""
    extractor = PDFExtractionEngine()
    extraction = extractor.extract_from_pdf(str(pdf_path))
    cleaned = clean_sheet(extraction)
    facts = cleaned["facts"]
    removed = cleaned["removed"]
    tables = cleaned["tables"]

    # Index facts by (page, raw_line) in order and removed full lines by (page, line) in order
    facts_iter = iter(facts)
    next_fact = next(facts_iter, None)

    full_line_removed = [r for r in removed if "source_line" not in r]
    rem_iter = iter(full_line_removed)
    next_rem = next(rem_iter, None)

    raw_page_lines = _iter_sheet_lines_with_pages(extraction)
    pages_map: dict[int, list[str]] = {}
    page_order: list[int] = []
    for pno, ln in raw_page_lines:
        if pno not in pages_map:
            pages_map[pno] = []
            page_order.append(pno)
        pages_map[pno].append(ln)

    reading_rows: list[dict[str, Any]] = []
    for pno in page_order:
        merged_lines = _merge_wrapped_and_hyphenated_page_lines(pages_map[pno])
        for mln in merged_lines:
            if next_fact is not None and next_fact["page"] == pno and (
                next_fact["raw_line"] == mln or next_fact["text"] == mln or mln.endswith(next_fact["raw_line"])
            ):
                reading_rows.append(
                    {
                        "page": pno,
                        "status": "KEEP",
                        "reason": "",
                        "text": next_fact["text"],
                        "raw_line": mln,
                        "kind": next_fact["kind"],
                        "subject": next_fact["subject"],
                        "section": next_fact["section"],
                        "bold_spans": next_fact["bold_spans"],
                        "credits_removed": next_fact.get("credits_removed", []),
                    }
                )
                next_fact = next(facts_iter, None)
            elif next_rem is not None and next_rem["page"] == pno:
                reading_rows.append(
                    {
                        "page": pno,
                        "status": f"REMOVE({next_rem['reason']})",
                        "reason": next_rem["reason"],
                        "text": next_rem["text"],
                        "raw_line": mln,
                        "kind": "",
                        "subject": "",
                        "section": "",
                        "bold_spans": [],
                        "credits_removed": [],
                    }
                )
                next_rem = next(rem_iter, None)

    reason_counts: dict[str, int] = {}
    for r in removed:
        rsn = r["reason"]
        reason_counts[rsn] = reason_counts.get(rsn, 0) + 1

    return {
        "pdf_name": pdf_path.name,
        "page_count": len(extraction.pages),
        "facts": facts,
        "removed": removed,
        "tables": tables,
        "reason_counts": reason_counts,
        "reading_rows": reading_rows,
    }


def generate_clean_sheet_report(folder: Path | str | None = None, print_stdout: bool = True) -> Path:
    default_sheets_dir = ROOT_DIR / "fixtures" / "sheets"
    if folder is None:
        sheets_dir = default_sheets_dir
        save_attached_sheets(sheets_dir)
    else:
        sheets_dir = Path(folder).resolve()
        if sheets_dir == default_sheets_dir.resolve() and not list(sheets_dir.glob("*.pdf")):
            save_attached_sheets(sheets_dir)

    pdf_files = sorted(sheets_dir.glob("*.pdf"))
    md_lines: list[str] = [
        "# Clean Sheet Input Report (`clean_sheet(pdf)`)",
        "",
        "Every line in reading order marked `KEEP` (with `kind`, `subject`, `section`) or `REMOVE(reason)`.",
        "",
    ]

    for pdf_path in pdf_files:
        info = inspect_sheet_reading_order(pdf_path)
        facts = info["facts"]
        removed = info["removed"]
        tables = info["tables"]
        reason_counts = info["reason_counts"]
        reasons_str = ", ".join(f"`{k}`: {v}" for k, v in sorted(reason_counts.items()))

        md_lines.append(f"## {info['pdf_name']}")
        md_lines.append("")
        md_lines.append(
            f"- **Pages:** {info['page_count']} | **Kept fact lines:** **{len(facts)}** | "
            f"**Removed items:** **{len(removed)}** ({reasons_str}) | **Structured tables:** **{len(tables)}**"
        )
        md_lines.append("")
        md_lines.append("| Page | Action | Kind | Subject | Section | Line Text |")
        md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")

        if print_stdout:
            print(f"=== {info['pdf_name']} (pages={info['page_count']}, kept={len(facts)}, removed={len(removed)}: {reason_counts}, tables={len(tables)}) ===")

        for row in info["reading_rows"]:
            pno = row["page"]
            status = row["status"]
            kind = row["kind"] or "—"
            subj = row["subject"] or "—"
            sec = row["section"] or "—"
            txt = str(row["text"]).replace("|", "\\|")
            cred_note = ""
            if row["credits_removed"]:
                cred_note = f" *(stripped REMOVE(credit): {', '.join(row['credits_removed'])})*"
            md_lines.append(f"| {pno} | `{status}` | `{kind}` | `{subj}` | `{sec}` | {txt}{cred_note} |")

        md_lines.append("")

    report_path = ROOT_DIR / "fixtures" / "clean_sheet_report.md"
    report_path.write_text("\n".join(md_lines), encoding="utf-8")
    return report_path


if __name__ == "__main__":
    arg_folder = sys.argv[1] if len(sys.argv) > 1 else None
    out = generate_clean_sheet_report(arg_folder, print_stdout=True)
    print(f"Wrote {out}")
