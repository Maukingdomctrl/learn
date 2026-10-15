"""Builds cards/sample/sample-sheet.pdf: a small two-page study sheet in the same layout as the UK cities notes.

Words wrapped in **double stars** are printed bold, the way a teacher marks the key words.
Run from the repo root: python cards/test/fixtures/make_sample.py
"""

import re
from pathlib import Path

import pymupdf

OUT = Path(__file__).resolve().parents[2] / "sample" / "sample-sheet.pdf"
BODY, HEAD = 9.5, 12
FONTS = Path("/usr/share/fonts/truetype/liberation")
REGULAR, BOLD = FONTS / "LiberationSans-Regular.ttf", FONTS / "LiberationSans-Bold.ttf"
MEASURE = {"reg": pymupdf.Font(fontfile=str(REGULAR)), "bold": pymupdf.Font(fontfile=str(BOLD))}

PAGES = [
    [
        ("title", "IMPORTANT CITIES OF THE UNITED KINGDOM"),
        ("sub", "Grade 8 Social Studies | Sample notes"),
        ("section", "1. QUICK REVISION NOTES"),
        ("heading", "1. BELFAST – Capital of Northern Ireland"),
        ("bullet", "Capital and **largest city of Northern Ireland**; second largest city on the island of Ireland."),
        ("bullet", "Situated on the **River Lagan**; population about **286,000** (2011 census)."),
        ("bullet", "Historic industries: Irish linen, tobacco processing, rope-making and **shipbuilding**."),
        ("bullet", "**Harland and Wolff** shipyard built the **RMS Titanic**."),
        ("bullet", "Home to the **Titanic Belfast** interactive museum."),
        ("heading", "2. EDINBURGH – Capital of Scotland"),
        ("bullet", "Home to the **Scottish Parliament** and the seat of the monarchy in Scotland."),
        ("bullet", "Centre of banking for over 300 years: **Bank of Scotland** founded in **1695**."),
        ("bullet", "Tourism is a major mainstay: supports **30,000 jobs** worth £1.6 billion to the city economy."),
        ("bullet", "Famous for its stunning mix of architecture: medieval tenements, Old Town, cobbled wynds and"),
        ("wrap", "Georgian-era buildings."),
    ],
    [
        ("section", "2. QUICK COMPARISON"),
        ("bullet", "Belfast = Shipbuilding & Titanic (Lagan + Harland & Wolff)"),
        ("bullet", "Edinburgh = Banking Capital of Scotland (Parliament + Bank of Scotland)"),
        ("note", "MEMORY TIP: Belfast builds ships; Edinburgh keeps the money."),
    ],
]


def runs(text):
    """Splits '**bold**' markup into (text, bold) runs."""
    parts = re.split(r"(\*\*.+?\*\*)", text)
    return [(p[2:-2], True) if p.startswith("**") else (p, False) for p in parts if p]


def write_line(page, x, y, text, size, bold_all=False):
    for chunk, bold in runs(text):
        font = "bold" if bold or bold_all else "reg"
        page.insert_text((x, y), chunk, fontname=font, fontsize=size)
        x += MEASURE[font].text_length(chunk, fontsize=size)


def main():
    doc = pymupdf.open()
    for n, lines in enumerate(PAGES, start=1):
        page = doc.new_page(width=595, height=842)
        page.insert_font(fontname="reg", fontfile=str(REGULAR))
        page.insert_font(fontname="bold", fontfile=str(BOLD))
        write_line(page, 43, 28, f"Grade 8 Social Studies | Sample sheet          Page {n}", 8)
        y = 70
        for kind, text in lines:
            if kind == "title":
                write_line(page, 95, y, text, 18, bold_all=True)
                y += 24
            elif kind == "sub":
                write_line(page, 120, y, text, 12, bold_all=True)
                y += 34
            elif kind in ("section", "heading"):
                y += 8
                write_line(page, 50, y, text, 13 if kind == "section" else HEAD, bold_all=True)
                y += 20
            elif kind == "bullet":
                write_line(page, 61, y, "• " + text, BODY)
                y += 15
            elif kind == "wrap":
                write_line(page, 70, y - 1, text, BODY)
                y += 15
            elif kind == "note":
                y += 10
                write_line(page, 50, y, text, BODY)
                y += 15
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.subset_fonts()
    doc.save(OUT, garbage=4, deflate=True)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
