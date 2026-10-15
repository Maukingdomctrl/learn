"""Rendering to PDF with headless Chromium: page counts, landscape A4, separation, overflow detection."""

import pytest

from learn.extraction import extract
from learn.grounding import SourceIndex
from learn.models import Lesson
from learn.rendering import render
from learn.timing import lesson_timing
from learn.validation import d6_layout


@pytest.fixture
def index(sample_pdf):
    return SourceIndex(extract(sample_pdf).units)


def _render(data, index, tmp_path):
    lesson = Lesson.model_validate(data)
    return lesson, render(lesson, index, lesson_timing(lesson), str(tmp_path))


def test_sample_renders_valid_pdfs(lesson_data, index, tmp_path):
    lesson, r = _render(lesson_data, index, tmp_path)
    assert len(r.student_pages) == 2
    assert 1 <= len(r.key_pages) <= 2
    for w, h in r.student_pages + r.key_pages:
        assert abs(w - 841.89) < 2 and abs(h - 595.28) < 2  # landscape A4 in points
    assert "Parent answer key" in r.key_text and "Parent answer key" not in r.student_text
    assert "Turn Page 1 face down" in r.student_text
    result = d6_layout(lesson, r)
    assert result.passed, result.problems


def test_overflow_is_detected(lesson_data, index, tmp_path):
    lesson_data["stages"][3]["items"][0]["prompt"] = " ".join(["This problem is long."] * 40)
    lesson, r = _render(lesson_data, index, tmp_path)
    assert any("overflows" in p for p in d6_layout(lesson, r).problems)
