"""Visual engine: deterministic SVG, print-safe ink, faithful labels, size budgets, D8 checks, browser rendering."""

import copy
import re

import pytest

from learn.extraction import extract
from learn.grounding import SourceIndex
from learn.models import Lesson, Stage, TeachingPlan
from learn.rendering import _chromium, render
from learn.timing import lesson_timing
from learn.validation import d8_visuals
from learn.visuals.checks import MAX_HEIGHT_MM, check_visual, svg_inks, svg_texts
from learn.visuals.specs import (
    Bar,
    BarModelSpec,
    BarPart,
    FlowSequenceSpec,
    NumberJump,
    NumberLineSpec,
    NumberPoint,
    ShapeSpec,
    Table,
)
from learn.visuals.svg import INK_FILLS, PX, draw
from tests.fixtures import SAMPLE_PLAN

SOURCE = (
    "base 8 cm height 5 cm length 12 width 4 radius 7 total 20 parts 12 8 Ravi Meena start 3 7 +4 "
    "Cardiff was a small town; it became a major coal port; made a city in 1905; capital of Wales in 1955. "
    "evaporation condensation precipitation water cycle"
)

SPECS = {
    "triangle": ShapeSpec(shape="triangle", base=8, height=5, unit="cm", purpose="see the height"),
    "rectangle": ShapeSpec(shape="rectangle", length=12, width=4, unit="cm", purpose="see length and width"),
    "parallelogram": ShapeSpec(shape="parallelogram", base=8, height=5, unit="cm", purpose="see the height"),
    "circle": ShapeSpec(shape="circle", radius=7, unit="cm", purpose="see the radius"),
    "number_line": NumberLineSpec(
        start=0,
        end=10,
        step=1,
        points=[NumberPoint(value=3, label="start")],
        jumps=[NumberJump(start=3, end=7, label="+4")],
        purpose="see adding as a jump",
    ),
    "bar_model": BarModelSpec(
        bars=[
            Bar(label="Ravi", parts=[BarPart(value=12), BarPart(value=8)], total=20),
            Bar(label="Meena", parts=[BarPart(value=12)]),
        ],
        purpose="compare the two amounts",
    ),
    "flow_linear": FlowSequenceSpec(
        steps=["Small town", "Major coal port", "City (1905)", "Capital of Wales (1955)"],
        purpose="see how Cardiff grew in order",
    ),
    "flow_cycle": FlowSequenceSpec(
        steps=["Evaporation", "Condensation", "Precipitation"], layout="cycle", purpose="see the cycle repeat"
    ),
}


@pytest.mark.parametrize("name", SPECS)
def test_drawings_are_deterministic_print_safe_and_valid(name):
    v = SPECS[name]
    first, second = draw(v), draw(copy.deepcopy(v))
    assert first.svg == second.svg
    fills, strokes = svg_inks(first.svg)
    assert fills <= INK_FILLS and strokes == {"#000"}
    assert first.height_mm <= MAX_HEIGHT_MM
    assert check_visual(v, SOURCE, "", SOURCE) == []


def test_old_tables_without_kind_still_load():
    stage = Stage.model_validate(
        {
            "stage": "Discover",
            "activity_type": "CHOOSE",
            "instruction": "x",
            "items": [],
            "visuals": [{"caption": "t", "headers": ["a"], "rows": [["1"]]}],
        }
    )
    assert isinstance(stage.visuals[0], Table) and draw(stage.visuals[0]) is None


def test_labels_come_from_the_numbers():
    texts = svg_texts(draw(SPECS["triangle"]).svg)
    assert "base = 8 cm" in texts and "height = 5 cm" in texts
    flow = " ".join(svg_texts(draw(SPECS["flow_linear"]).svg))
    assert "1905" in flow and "Capital of Wales" in flow
    assert "= 20" in svg_texts(draw(SPECS["bar_model"]).svg)


def test_rectangle_is_drawn_to_proportion_and_extremes_are_flagged():
    svg = draw(SPECS["rectangle"]).svg
    m = re.search(r'<rect x="[\d.]+" y="[\d.]+" width="([\d.]+)" height="([\d.]+)"', svg)
    assert abs(float(m.group(1)) / float(m.group(2)) - 3.0) < 0.01  # 12 x 4
    flat = draw(ShapeSpec(shape="rectangle", length=100, width=1, unit="m", purpose="p"))
    assert "(not to scale)" in svg_texts(flat.svg)


def test_bar_model_height_grows_by_row_within_budget():
    one = BarModelSpec(bars=[Bar(label="A", parts=[BarPart(value=1)])], purpose="p")
    three = BarModelSpec(bars=[Bar(label=x, parts=[BarPart(value=1)]) for x in "ABC"], purpose="p")
    assert draw(one).height_mm < draw(three).height_mm <= MAX_HEIGHT_MM


@pytest.mark.parametrize(
    "spec, expected",
    [
        (
            BarModelSpec(bars=[Bar(label="Ravi", parts=[BarPart(value=12), BarPart(value=8)], total=21)], purpose="p"),
            "not the sum",
        ),
        (NumberLineSpec(start=0, end=10, step=1, points=[NumberPoint(value=12)], purpose="p"), "outside"),
        (NumberLineSpec(start=0, end=10, step=3, purpose="p"), "does not divide"),
        (NumberLineSpec(start=0, end=100, step=1, purpose="p"), "intervals"),
        (ShapeSpec(shape="triangle", base=8, height=6, unit="cm", purpose="p"), "numbers ['6']"),
        (ShapeSpec(shape="triangle", base=8, unit="cm", purpose="p"), "positive height"),
        (ShapeSpec(shape="triangle", base=8, height=5, unit="cm"), "teaching purpose"),
        (FlowSequenceSpec(steps=["Small town", "Railway junction"], purpose="p"), "railway"),
        (FlowSequenceSpec(steps=list("abcdefg"), purpose="p"), "7 steps"),
        (FlowSequenceSpec(steps=["Evaporation", "Condensation"], layout="cycle", purpose="p"), "2 steps"),
        (FlowSequenceSpec(steps=["evaporation " * 9, "condensation"], purpose="p"), "too long for its box"),
        (Table(headers=["a", "b"], rows=[["1"]], purpose="p"), "same number of cells"),
        (FlowSequenceSpec(steps=["Small town", "Capital of Wales (1956)"], purpose="p"), "numbers ['1956']"),
        (Table(headers=["City"], rows=[["Railway town"]], purpose="p"), "railway"),
    ],
)
def test_d8_catches(spec, expected):
    problems = check_visual(spec, SOURCE, "", SOURCE)
    assert any(expected in p.lower() for p in problems), problems


def test_stage_text_can_ground_numbers():
    spec = ShapeSpec(shape="triangle", base=9, height=4, unit="cm", purpose="p")
    assert check_visual(spec, "base height", "A triangle with base 9 cm and height 4 cm.", "base height") == []


@pytest.fixture
def index(sample_pdf):
    return SourceIndex(extract(sample_pdf).units)


def test_d8_requires_the_plans_visual_type(lesson_data, index):
    lesson = Lesson.model_validate(lesson_data)
    assert d8_visuals(lesson, index, TeachingPlan.model_validate(SAMPLE_PLAN)).passed
    plan = TeachingPlan.model_validate(dict(SAMPLE_PLAN, visual_type="number_line"))
    assert any("number_line visual" in p for p in d8_visuals(lesson, index, plan).problems)
    none_plan = TeachingPlan.model_validate(dict(SAMPLE_PLAN, visual_type="none"))
    lesson.stages[0].visuals = []
    assert d8_visuals(lesson, index, none_plan).passed


def test_sample_lesson_prints_its_triangle(lesson_data, index, tmp_path):
    lesson = Lesson.model_validate(lesson_data)
    r = render(lesson, index, lesson_timing(lesson), str(tmp_path))
    assert "base = 8 cm" in r.student_text and "height = 5 cm" in r.student_text  # the blind solver can read them
    assert r.layout["min_font_pt"] >= 10.5


def test_browser_draws_each_visual_at_its_declared_size():
    from playwright.sync_api import sync_playwright

    figures = "".join(f'<div class="v" data-h="{draw(v).height_mm}">{draw(v).svg}</div>' for v in SPECS.values())
    with sync_playwright() as p:
        browser = _chromium(p)
        try:
            page = browser.new_page()
            page.set_content(f"<html><body style='margin:0'>{figures}</body></html>")
            got = page.evaluate(
                """() => Array.from(document.querySelectorAll('.v')).map(d => ({
                    declared: +d.dataset.h,
                    height: d.querySelector('svg').getBoundingClientRect().height,
                    font: Math.min(...Array.from(d.querySelectorAll('text')).map(t =>
                        parseFloat(getComputedStyle(t).fontSize)))}))"""
            )
        finally:
            browser.close()
    for g in got:
        assert abs(g["height"] / PX - g["declared"]) < 0.5
        assert g["font"] * 0.75 >= 10.5


def test_long_timelines_use_two_readable_rows():
    five = FlowSequenceSpec(
        steps=["Small town", "Major coal port", "City (1905)", "Capital of Wales (1955)", "Small town"],
        purpose="p",
    )
    d = draw(five)
    assert d.problems == [] and d.height_mm == 50.0
    assert check_visual(five, SOURCE, "", SOURCE) == []


def test_column_headers_and_jump_lengths_are_not_grounding_failures():
    table = Table(headers=["City", "Status"], rows=[["Cardiff", "Capital of Wales"]], purpose="p")
    assert check_visual(table, SOURCE, "", SOURCE) == []
    jump = NumberLineSpec(start=0, end=10, step=1, jumps=[NumberJump(start=3, end=7, label="+4")], purpose="p")
    assert check_visual(jump, "3 7", "", "") == []
