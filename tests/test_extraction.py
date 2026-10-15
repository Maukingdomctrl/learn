import pytest

from learn.extraction import ExtractionError, choose_ocr, extract
from learn.grounding import InputError, SourceIndex, check_selection, parse_page_range
from tests.fixtures import make_scanned_pdf


def test_extracts_numbered_units(sample_pdf):
    src = extract(sample_pdf)
    ids = [u.id for u in src.units]
    assert ids[0] == "SRC-P1-U1" and "SRC-P2-U2" in ids
    assert any("1/2 × base × height" in u.text for u in src.units)
    assert src.page_count == 2 and not src.unreadable_pages


def test_page_range_filters_pages(sample_pdf):
    src = extract(sample_pdf, pages={2})
    assert {u.page for u in src.units} == {2}


def test_parse_page_range():
    assert parse_page_range("1-2", 3) == {1, 2}
    assert parse_page_range(" 3, 1 ", 3) == {1, 3}
    assert parse_page_range("", 3) is None
    for bad in ("0", "2-1", "4", "x"):
        with pytest.raises(InputError):
            parse_page_range(bad, 3)


def test_scanned_page_without_ocr_is_reported(tmp_path):
    pdf = make_scanned_pdf(str(tmp_path / "scan.pdf"))
    src = extract(pdf, ocr=None)
    assert src.units == [] and src.unreadable_pages == [1]


def test_scanned_page_uses_ocr(tmp_path):
    pdf = make_scanned_pdf(str(tmp_path / "scan.pdf"))
    text = "The area of a triangle is half of base times height.\n\nExample: base 4 cm, height 3 cm gives 6 cm²."
    src = extract(pdf, ocr=lambda png: text, ocr_name="fake")
    assert src.ocr_pages == [1] and len(src.units) == 2 and src.units[0].method == "ocr"
    assert any("OCR" in w for w in src.warnings)


def test_not_a_pdf(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_text("hello")
    with pytest.raises(ExtractionError):
        extract(str(p))


def test_choose_ocr_off():
    assert choose_ocr("off")[0] is None


def test_check_selection(sample_pdf):
    index = SourceIndex(extract(sample_pdf).units)
    good = {"concept": "Area of a triangle", "explanation_unit_ids": ["SRC-P1-U3"], "is_procedure": True,
            "procedure_unit_ids": ["SRC-P1-U4"], "can_support_7_items": True}
    assert check_selection(good, index) == []
    bad = dict(good, explanation_unit_ids=["SRC-P9-U1"], can_support_7_items=False)
    problems = check_selection(bad, index)
    assert any("3.3a" in p for p in problems) and any("3.3b" in p for p in problems)
