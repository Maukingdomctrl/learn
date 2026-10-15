"""Progressive visual practice (D9): hidden labels, derived answers, teachability, decreasing support."""

import copy

import pytest

from learn.extraction import extract
from learn.grounding import SourceIndex
from learn.models import Lesson
from learn.pipeline import run
from learn.rendering import render, student_html
from learn.timing import lesson_timing
from learn.validation import d8_visuals, d9_progression
from learn.visuals.checks import check_visual, svg_texts
from learn.visuals.practice import derived_answer, fill_visual_answers, label_slots
from learn.visuals.specs import Bar, BarModelSpec, BarPart, FlowSequenceSpec, NumberJump, NumberLineSpec, Table
from learn.visuals.svg import BLANK, draw
from tests.fixtures import SAMPLE_LESSON
from tests.test_pipeline import responses

STEPS = ["Small town", "Major coal port", "City (1905)", "Capital of Wales (1955)"]


def flow(**kw):
    return dict(
        {"kind": "flow_sequence", "purpose": "see the order", "steps": STEPS, "source_unit_ids": ["SRC-P1-U4"]}, **kw
    )


def L(d):
    return Lesson.model_validate(d)


# ---------------------------------------------------------------- slots and derived answers
def test_label_slots_and_derived_answers():
    tri = L(SAMPLE_LESSON).stage("Reinforce").items[3].visual
    assert label_slots(tri) == {"base": "6", "height": "8"}
    assert derived_answer(tri, ["height"]) == "8"
    bar = BarModelSpec(bars=[Bar(label="Ravi", parts=[BarPart(value=12), BarPart(value=8)])], purpose="p")
    assert label_slots(bar) == {"bar0.part0": "12", "bar0.part1": "8", "bar0.total": "20"}
    line = NumberLineSpec(start=0, end=10, step=1, jumps=[NumberJump(start=3, end=7, label="+4")], purpose="p")
    assert label_slots(line) == {"jump0": "+4"}
    table = Table(headers=["City", "River"], rows=[["Belfast", "Lagan"]], purpose="p")
    assert derived_answer(table, ["cell0.1"]) == "Lagan"
    assert derived_answer(FlowSequenceSpec(steps=STEPS, purpose="p"), ["step1", "step3"]) == (
        "Major coal port; Capital of Wales (1955)"
    )


def test_key_is_filled_from_the_diagram(lesson_data):
    lesson_data["answer_key"]["entries"] = [e for e in lesson_data["answer_key"]["entries"] if e["item_number"] != 6]
    lesson = L(lesson_data)
    log = fill_visual_answers(lesson)
    assert lesson.key_for(6).answer == "8" and "created" in log[0]
    lesson.key_for(6).answer = "9"  # a wrong model answer is replaced
    assert "set from the diagram" in fill_visual_answers(lesson)[0] and lesson.key_for(6).answer == "8"


# ---------------------------------------------------------------- hidden rendering
def test_hidden_labels_print_as_blanks():
    tri = L(SAMPLE_LESSON).stage("Reinforce").items[3].visual
    texts = svg_texts(draw(tri, {"height"}).svg)
    assert f"height = {BLANK} cm" in texts and "base = 6 cm" in texts and "height = 8 cm" not in texts
    flow_texts = " ".join(svg_texts(draw(FlowSequenceSpec(steps=STEPS, purpose="p"), {"step1"}).svg))
    assert "Small town" in flow_texts and "coal port" not in flow_texts
    bar = BarModelSpec(bars=[Bar(label="Ravi", parts=[BarPart(value=12), BarPart(value=8)])], purpose="p")
    assert f"= {BLANK}" in svg_texts(draw(bar, {"bar0.total"}).svg)


def test_hidden_table_cells_print_as_blanks(lesson_data):
    item = lesson_data["stages"][1]["items"][3]
    item["visual"] = {
        "kind": "table",
        "purpose": "p",
        "headers": ["Base", "Height"],
        "rows": [["6 cm", "8 cm"]],
        "source_unit_ids": ["SRC-P1-U5"],
    }
    item["hidden"] = ["cell0.1"]
    html = student_html(L(lesson_data))
    assert "<td>6 cm</td>" in html and "<td>8 cm</td>" not in html


def test_d8_accepts_hidden_labels_and_does_not_need_hidden_values_printed():
    tri = L(SAMPLE_LESSON).stage("Reinforce").items[3].visual
    # 8 is hidden, so it is not required on the page for D8 (D9 checks it is teachable instead)
    assert check_visual(tri, "base 6 cm", "", "base", {"height"}) == []


# ---------------------------------------------------------------- D9
@pytest.fixture
def lesson():
    return L(copy.deepcopy(SAMPLE_LESSON))


def test_sample_lesson_progression_passes(lesson):
    assert d9_progression(lesson).passed


def test_full_progression_from_demonstration_to_independence(lesson_data):
    """Discover shows the full timeline; Reinforce hides 1 of 4, Vary 2, Apply all 4; Recall has none."""
    lesson_data["stages"][0]["visuals"].append(flow(caption="Cardiff"))
    lesson_data["stages"][1]["items"][3].update(visual=flow(), hidden=["step1"])
    lesson_data["stages"][2]["activity_type"] = "FILL_IN"
    lesson_data["stages"][2]["items"][0].update(visual=flow(), hidden=["step1", "step2"])
    lesson_data["stages"][3]["items"][0].update(visual=flow(), hidden=["step0", "step1", "step2", "step3"])
    lesson = L(lesson_data)
    fill_visual_answers(lesson)
    assert d9_progression(lesson).passed, d9_progression(lesson).problems


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda d: d["stages"][4]["items"][0].update(visual=flow(), hidden=["step0"]), "belongs in Reinforce"),
        (lambda d: d["stages"][2]["items"][0].update(visual=flow(), hidden=["step0"]), "must be FILL_IN or SOLVE"),
        (lambda d: d["stages"][1]["items"][3].update(visual=flow(), hidden=["step0"]), "never demonstrates"),
        (lambda d: d["stages"][1]["items"][3].update(hidden=["area"]), "do not exist"),
        (lambda d: d["stages"][1]["items"][3].update(hidden=[]), "hide at least one"),
        (lambda d: d["stages"][1]["items"][3].update(hidden=["base", "height"]), "partly completed"),
    ],
)
def test_d9_catches(lesson_data, mutate, expected):
    mutate(lesson_data)
    lesson = L(lesson_data)
    fill_visual_answers(lesson)
    assert any(expected in p for p in d9_progression(lesson).problems), d9_progression(lesson).problems


def test_support_must_not_increase(lesson_data):
    lesson_data["stages"][0]["visuals"].append(flow(caption="Cardiff"))
    lesson_data["stages"][1]["items"][3].update(visual=flow(), hidden=["step1", "step2"])  # 50%
    lesson_data["stages"][3]["items"][0].update(visual=flow(), hidden=["step3"])  # 25% later: more support
    lesson = L(lesson_data)
    fill_visual_answers(lesson)
    assert any("support increases" in p for p in d9_progression(lesson).problems)


def test_key_must_match_the_diagram(lesson):
    lesson.key_for(6).answer = "9"  # not re-filled: the guard catches it
    assert any("diagram's own value" in p for p in d9_progression(lesson).problems)


def test_hidden_numbers_must_be_given_or_verified(lesson):
    assert d9_progression(lesson).passed  # 8 is not on the page, but the key calculation 24/(0.5*6) verifies it
    lesson.key_for(6).calculation = None
    assert any("neither given on the page" in p for p in d9_progression(lesson).problems)
    lesson.stage("Reinforce").items[3].prompt += " Its height is 8 cm."  # now given on the page
    assert d9_progression(lesson).passed


def test_hidden_words_must_be_taught_in_discover_or_offered(lesson_data):
    lesson_data["stages"][0]["visuals"].append(flow(caption="Cardiff"))
    other = flow(steps=["Small town", "Railway town", "City (1905)", "Capital of Wales (1955)"])
    lesson_data["stages"][0]["visuals"][1] = flow(caption="Cardiff")  # Discover shows the true steps
    lesson_data["stages"][1]["items"][3].update(visual=other, hidden=["step1"])  # asks for an untaught step
    lesson = L(lesson_data)
    fill_visual_answers(lesson)
    assert any("not taught in Discover" in p for p in d9_progression(lesson).problems)
    lesson.stage("Reinforce").word_bank.append("Railway town")
    assert d9_progression(lesson).passed


# ---------------------------------------------------------------- integration
@pytest.fixture
def index(sample_pdf):
    return SourceIndex(extract(sample_pdf).units)


def test_practice_diagram_prints_and_passes_visual_checks(lesson, index, tmp_path):
    r = render(lesson, index, lesson_timing(lesson), str(tmp_path))
    assert f"height = {BLANK} cm" in r.student_text
    assert d8_visuals(lesson, index).passed, d8_visuals(lesson, index).problems
    assert lesson_timing(lesson).stages[1].visuals == 1  # the practice diagram counts as viewing time


def test_pipeline_derives_the_key_and_delivers(sample_pdf, tmp_path, scripted):
    wrong = copy.deepcopy(SAMPLE_LESSON)
    next(e for e in wrong["answer_key"]["entries"] if e["item_number"] == 6)["answer"] = "9"
    rep = run(sample_pdf, 7, scripted(responses(generate_lesson=wrong)), str(tmp_path))
    assert rep.status == "delivered", rep.checks
    assert any("set from the diagram" in line for line in rep.log)
