"""Generation sees only the selected source units (plus same-page neighbours), and citations must stay inside."""

import copy

from learn.extraction import extract
from learn.grounding import SourceIndex
from learn.pipeline import run
from tests.fixtures import SAMPLE_LESSON
from tests.test_pipeline import SELECTION, responses

PAGE1_ONLY = dict(SELECTION, supporting_unit_ids=["SRC-P1-U2", "SRC-P1-U5"])


def test_focus_keeps_selected_units_and_same_page_neighbours(sample_pdf):
    index = SourceIndex(extract(sample_pdf).units)
    assert [u.id for u in index.focus(["SRC-P1-U3"], 1).units] == ["SRC-P1-U2", "SRC-P1-U3", "SRC-P1-U4"]
    # the last unit on page 1 does not pull in page 2
    assert [u.id for u in index.focus(["SRC-P1-U6"], 1).units] == ["SRC-P1-U5", "SRC-P1-U6"]
    assert index.focus(["SRC-P9-U1"], 1).units == []


def test_model_never_sees_unselected_units(sample_pdf, tmp_path, scripted):
    llm = scripted(responses(select_concept=PAGE1_ONLY))
    rep = run(sample_pdf, 7, llm, str(tmp_path))
    prompts = dict(llm.calls)
    assert "SRC-P2-U2" in prompts["select_concept"]  # selection still sees the whole PDF
    for task in ("plan_lesson", "generate_lesson"):
        assert "SRC-P1-U3" in prompts[task] and "SRC-P2-U1" not in prompts[task] and "SRC-P2-U2" not in prompts[task]
    assert rep.source_focus == [f"SRC-P1-U{n}" for n in range(1, 7)]


def test_citations_outside_the_focus_fail_d2(sample_pdf, tmp_path, scripted):
    # SAMPLE_LESSON cites page-2 units, which this selection did not choose.
    llm = scripted(responses(select_concept=PAGE1_ONLY, repair_lesson=copy.deepcopy(SAMPLE_LESSON)))
    rep = run(sample_pdf, 7, llm, str(tmp_path))
    d2 = next(c for c in rep.checks if c["id"] == "D2")
    assert rep.status == "stopped" and d2["status"] == "failed"
    assert any("unselected" in p and "SRC-P2-U1" in p for p in d2["problems"])


def test_report_carries_model_call_log_and_error(sample_pdf, tmp_path, scripted):
    from learn.llm import LLMError

    class LoggingLLM(scripted):
        call_log = [{"task": "select_concept", "stop_reason": "max_tokens", "output_tokens": 32000}]
        notes = ["claude-test: Models API reports max output 128000 tokens"]

    def cut_off(prompt, llm):
        raise LLMError("select_concept: the model response was cut off at its 32000-token output limit")

    rep = run(sample_pdf, 7, LoggingLLM(responses(select_concept=cut_off)), str(tmp_path))
    assert rep.stage == "select" and "cut off" in rep.error
    assert rep.model_calls[0]["stop_reason"] == "max_tokens"
    assert any("Models API" in line for line in rep.log)
