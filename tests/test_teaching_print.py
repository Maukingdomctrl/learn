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
