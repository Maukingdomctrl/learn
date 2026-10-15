import time

import pymupdf

from learn.grounding import SourceUnit
from learn.teaching_engine import create_teaching_lesson, extract_facts, render_teaching_pdf


def test_printable_pdf_keeps_source_citations_recall_and_review_flags():
    units = [
        SourceUnit(
            id="unit-1",
            page=2,
            text="London is in England. London stands on the River Thames.",
            method="text",
        ),
        SourceUnit(
            id="unit-2",
            page=3,
            text="The steam engine was invented by James Watt.",
            method="text",
        ),
    ]
    lesson = create_teaching_lesson(extract_facts(units))

    pdf_bytes = render_teaching_pdf(lesson, ["A source page contains a diagram."])
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in document)

    assert pdf_bytes.startswith(b"%PDF")
    assert document.page_count >= 1
    assert "SOURCE" in text
    assert "PAGE 2" in text
    assert "London is in England." in text
    assert "REMEMBER IT" in text
    assert "Your sketch" in text
    assert "PAUSE" in text
    assert "James Watt" in text
    assert "diagram" in text


def test_long_source_renders_quickly():
    # A 40-page chapter took ~55 s to render before wrapping and drawing were batched, which made
    # the hosted app time out instead of returning the PDF. The bound is generous to avoid flakes.
    sentence = "The river Ganga flows to the Bay of Bengal. Farmers grow rice in the fertile delta. "
    units = [SourceUnit(id=f"unit-{n}", page=n, text=sentence * 12, method="text") for n in range(1, 41)]
    lesson = create_teaching_lesson(extract_facts(units))

    started = time.perf_counter()
    pdf_bytes = render_teaching_pdf(lesson)
    elapsed = time.perf_counter() - started

    assert pymupdf.open(stream=pdf_bytes, filetype="pdf").page_count > 100
    assert elapsed < 20, f"rendering took {elapsed:.1f} s"
