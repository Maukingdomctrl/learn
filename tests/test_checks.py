"""Deterministic checks D1-D5 and D7 on the sample lesson and on targeted mutations of it."""

import pytest

from learn.extraction import extract
from learn.grounding import SourceIndex
from learn.models import Lesson
from learn.timing import lesson_timing
from learn.validation import d1_structure, d2_citations, d3_activities, d4_text, d5_timing, d7_key


@pytest.fixture
def index(sample_pdf):
    return SourceIndex(extract(sample_pdf).units)


def L(d):
    return Lesson.model_validate(d)


def test_sample_lesson_passes(lesson_data, index):
    lesson = L(lesson_data)
    t = lesson_timing(lesson)
    for check in (
        d1_structure(lesson),
        d2_citations(lesson, index),
        d3_activities(lesson),
        d4_text(lesson),
        d5_timing(lesson, t, 0),
        d7_key(lesson, index),
    ):
        assert check.passed, (check.id, check.problems)


def test_d1_stage_order_and_counts(lesson_data):
    d = lesson_data
    d["stages"][1], d["stages"][2] = d["stages"][2], d["stages"][1]
    assert not d1_structure(L(d)).passed


def test_d1_too_few_items(lesson_data):
    lesson_data["stages"][3]["items"] = []
    r = d1_structure(L(lesson_data))
    assert any("Apply has 0" in p for p in r.problems)


def test_d2_uncited_and_unknown_units(lesson_data, index):
    lesson_data["core_claims"][0]["source_unit_ids"] = []
    lesson_data["answer_key"]["entries"][0]["source_unit_ids"] = ["SRC-P7-U1"]
    r = d2_citations(L(lesson_data), index)
    assert any("no valid" in p for p in r.problems) and any("unknown" in p for p in r.problems)


def test_d3_match_needs_extra_option(lesson_data):
    st = lesson_data["stages"][1]
    st.update(activity_type="MATCH", word_bank=[], options=["height", "half", "base", "unit"])
    for it in st["items"]:
        it["prompt"] = it["prompt"].replace("____", "?")
    r = d3_activities(L(lesson_data))
    assert any("need at least 5" in p for p in r.problems)


def test_d3_choose_answer_must_be_option(lesson_data):
    lesson_data["answer_key"]["entries"][1]["answer"] = "five"
    assert any("exactly one option" in p for p in d3_activities(L(lesson_data)).problems)


def test_d3_consecutive_types_and_disallowed_stage(lesson_data):
    lesson_data["stages"][4]["activity_type"] = "SOLVE"  # same as Apply
    lesson_data["stages"][0]["activity_type"] = "MATCH"  # not allowed in Discover
    p = d3_activities(L(lesson_data)).problems
    assert any("both use SOLVE" in x for x in p) and any("not allowed in Discover" in x for x in p)


def test_d4_instruction_limits_and_banned_patterns(lesson_data):
    st = lesson_data["stages"][1]
    st["instruction"] = (
        "Read the sentences, circle the key word, write it in the blank and check your answer "
        "with the word bank carefully before you go on to the next part."
    )
    lesson_data["stages"][3]["items"][0]["prompt"] = "Which of these is NOT an area?"
    p = d4_text(L(lesson_data)).problems
    assert any("instruction sentence has" in x for x in p)
    assert any("actions" in x for x in p)
    assert any("negative-stem" in x for x in p)


def test_d4_colour_in_instruction(lesson_data):
    lesson_data["stages"][2]["instruction"] = "Circle the red step."
    assert any("colour" in p for p in d4_text(L(lesson_data)).problems)


def test_d4_reading_run(lesson_data):
    lesson_data["stages"][0]["body_text"] = " ".join(["Area is the surface it covers."] * 30)
    assert any("continuous reading" in p for p in d4_text(L(lesson_data)).problems)


def test_d5_too_long(lesson_data):
    lesson_data["stages"][0]["visuals"] *= 8
    lesson = L(lesson_data)
    r = d5_timing(lesson, lesson_timing(lesson), 0)
    assert any("max 990" in p for p in r.problems) and any("Discover block" in p for p in r.problems)


def test_d5_too_short_and_rule_s(lesson_data):
    lesson_data["stages"][0]["visuals"] = []
    lesson_data["stages"][0]["body_text"] = "Area = 1/2 × base × height."
    lesson = L(lesson_data)
    t = lesson_timing(lesson)
    assert 600 <= t.t_lesson < 780
    assert not d5_timing(lesson, t, 0).passed
    lesson.answer_key.shortened_lesson_note = "This lesson is about 12 minutes, shorter than usual, because ..."
    assert not d5_timing(lesson, t, 0).passed  # Rule S only after a repair attempt
    r = d5_timing(lesson, t, 1)
    assert r.passed and "Rule S" in r.problems[0]


def test_d7_arithmetic_and_coverage(lesson_data, index):
    entries = lesson_data["answer_key"]["entries"]
    entries[9]["answer"] = "48 m²"  # item 10: 1/2 × 12 × 7 = 42
    del entries[2]
    p = d7_key(L(lesson_data), index).problems
    assert any("arithmetic mismatch" in x for x in p)
    assert any("item 3 has 0" in x for x in p)
