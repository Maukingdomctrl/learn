"""Teaching plan: code checks, bounded re-ask, focused source, and use in lesson generation."""

import copy
import os

import pytest

from learn import config as C
from learn.extraction import extract
from learn.generation import GenerationError, generate_lesson, plan_lesson
from learn.grounding import SourceIndex, check_plan, selection_unit_ids
from learn.models import TeachingPlan
from learn.pipeline import run
from tests.fixtures import SAMPLE_PLAN
from tests.test_pipeline import SELECTION, responses


@pytest.fixture
def index(sample_pdf):
    return SourceIndex(extract(sample_pdf).units)


@pytest.fixture
def focus(index):
    return index.focus(selection_unit_ids(SELECTION), C.CONTEXT_NEIGHBORS)


def P(d):
    return TeachingPlan.model_validate(d)


def test_sample_plan_passes(focus):
    assert check_plan(P(SAMPLE_PLAN), focus, C.PLAN_STEP_RANGE) == []


def test_plan_problems_are_caught(focus):
    d = copy.deepcopy(SAMPLE_PLAN)
    d["learning_steps"].append(dict(d["learning_steps"][0]))  # 4 steps
    d["learning_steps"][0]["source_unit_ids"] = ["SRC-P9-U9"]
    d["worked_example"]["answer"] = "40 cm²"  # 0.5*8*5 = 20
    d["visual_purpose"] = ""
    problems = check_plan(P(d), focus, C.PLAN_STEP_RANGE)
    assert any("4 learning steps" in p for p in problems)
    assert any("unselected" in p for p in problems)
    assert any("arithmetic mismatch" in p for p in problems)
    assert any("teaching purpose" in p for p in problems)


def test_computed_answer_needs_a_calculation(focus):
    d = copy.deepcopy(SAMPLE_PLAN)
    d["worked_example"]["calculation"] = None
    assert any("no calculation" in p for p in check_plan(P(d), focus, C.PLAN_STEP_RANGE))


def test_plan_is_reasked_once_with_problems(focus, scripted):
    bad = copy.deepcopy(SAMPLE_PLAN)
    bad["worked_example"]["answer"] = "40 cm²"
    llm = scripted({"plan_lesson": [bad, copy.deepcopy(SAMPLE_PLAN)]})
    plan = plan_lesson(llm, focus, 7, SELECTION)
    assert plan.concept == "Area of a triangle"
    assert len(llm.calls) == 2 and "arithmetic mismatch" in llm.calls[1][1]


def test_plan_fails_after_one_reask(focus, scripted):
    bad = copy.deepcopy(SAMPLE_PLAN)
    bad["learning_steps"] = bad["learning_steps"][:1]
    llm = scripted({"plan_lesson": bad})
    with pytest.raises(GenerationError, match="1 learning steps"):
        plan_lesson(llm, focus, 7, SELECTION)
    assert len(llm.calls) == 2


def test_generation_prompt_carries_the_plan(focus, scripted, lesson_data):
    llm = scripted({"generate_lesson": lesson_data})
    generate_lesson(llm, focus, 7, SELECTION, P(SAMPLE_PLAN))
    prompt = llm.calls[0][1]
    assert "FOLLOW THE TEACHING PLAN" in prompt and "forgetting to halve" in prompt


def test_pipeline_stops_at_plan_and_delivers_nothing(sample_pdf, tmp_path, scripted):
    bad = copy.deepcopy(SAMPLE_PLAN)
    bad["misconception"]["source_unit_ids"] = ["SRC-P7-U1"]
    rep = run(sample_pdf, 7, scripted(responses(plan_lesson=bad)), str(tmp_path))
    assert rep.status == "stopped" and rep.stage == "plan"
    assert "unselected" in rep.error
    assert not os.path.exists(tmp_path / "deliver")


def test_delivered_report_includes_plan(sample_pdf, tmp_path, scripted):
    rep = run(sample_pdf, 7, scripted(responses()), str(tmp_path))
    assert rep.status == "delivered" and rep.plan["concept"] == "Area of a triangle"
    assert os.path.exists(tmp_path / "work" / "plan.json")
