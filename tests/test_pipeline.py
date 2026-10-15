"""End-to-end pipeline with a SCRIPTED fake model.

These tests exercise the real extraction, timing, rendering, deterministic checks, repair loop and delivery
rules. The model's outputs (concept selection, lesson, AI-check verdicts) are canned, so they say nothing
about the quality of real generated lessons.
"""
import copy
import os

from learn.pipeline import run
from tests.fixtures import SAMPLE_LESSON

SELECTION = {
    "status": "ok", "concept": "Area of a triangle", "sub_concepts": ["finding area", "finding height"],
    "is_procedure": True, "explanation_unit_ids": ["SRC-P1-U3"], "procedure_unit_ids": ["SRC-P1-U4"],
    "supporting_unit_ids": ["SRC-P1-U2", "SRC-P1-U5"], "can_support_7_items": True,
    "not_covered": "", "source_issues": [], "insufficiency_reason": "", "parent_action": "",
}
PASS = {"pass": True, "issues": []}
BLIND = {"answers": [{"item_number": n, "answer": "x", "flag": None} for n in range(1, 13)]}


def responses(**over):
    r = {"select_concept": SELECTION, "generate_lesson": copy.deepcopy(SAMPLE_LESSON),
         "repair_lesson": copy.deepcopy(SAMPLE_LESSON), "A1": PASS, "A2": BLIND, "A3": PASS, "A4": PASS}
    r.update(over)
    return r


def test_delivers_when_all_checks_pass(sample_pdf, tmp_path, scripted):
    llm = scripted(responses())
    rep = run(sample_pdf, 7, llm, str(tmp_path))
    assert rep.status == "delivered", (rep.parent_message, rep.checks)
    assert os.path.exists(rep.student_pdf) and os.path.exists(rep.key_pdf)
    assert rep.rounds == 0
    assert {c["id"] for c in rep.checks} == {"D1", "D2", "D3", "D4", "D5", "D6", "D7", "A1", "A2", "A3", "A4"}
    tasks = [t for t, _ in llm.calls]
    assert tasks == ["select_concept", "generate_lesson", "A1", "A2", "A3", "A4"]
    # The blind solver sees only student-page text: never the answer key.
    a2_prompt = dict(llm.calls)["A2"]
    assert "Parent answer key" not in a2_prompt and "Why it is correct" not in a2_prompt


def test_insufficient_source_stops_without_lesson(sample_pdf, tmp_path, scripted):
    sel = dict(SELECTION, status="insufficient", insufficiency_reason="The topic is only listed, not explained.",
               parent_action="Upload the chapter pages.")
    rep = run(sample_pdf, 7, scripted(responses(select_concept=sel)), str(tmp_path))
    assert rep.status == "stopped" and rep.stage == "sufficiency"
    assert "only listed" in rep.parent_message
    assert not os.path.exists(tmp_path / "deliver")


def test_code_rejects_ungrounded_selection(sample_pdf, tmp_path, scripted):
    sel = dict(SELECTION, explanation_unit_ids=["SRC-P5-U1"])
    rep = run(sample_pdf, 8, scripted(responses(select_concept=sel)), str(tmp_path))
    assert rep.status == "stopped" and rep.stage == "sufficiency"


def test_repair_then_deliver(sample_pdf, tmp_path, scripted):
    bad = copy.deepcopy(SAMPLE_LESSON)
    bad["answer_key"]["entries"][9]["answer"] = "48 m²"  # arithmetic error caught by D7
    llm = scripted(responses(generate_lesson=bad))
    rep = run(sample_pdf, 7, llm, str(tmp_path))
    assert rep.status == "delivered" and rep.rounds == 1
    repair_prompt = dict(llm.calls)["repair_lesson"]
    assert "arithmetic mismatch" in repair_prompt
    # Round 0 skipped AI checks because deterministic checks failed first.
    assert [t for t, _ in llm.calls].count("A1") == 1


def test_stops_after_two_repairs_and_delivers_nothing(sample_pdf, tmp_path, scripted):
    bad = copy.deepcopy(SAMPLE_LESSON)
    bad["stages"][3]["items"] = []
    llm = scripted(responses(generate_lesson=bad, repair_lesson=bad))
    rep = run(sample_pdf, 7, llm, str(tmp_path))
    assert rep.status == "stopped" and rep.stage == "validate" and rep.rounds == 2
    assert [t for t, _ in llm.calls].count("repair_lesson") == 2
    assert not os.path.exists(tmp_path / "deliver")
    assert rep.student_pdf is None and rep.key_pdf is None


def test_ai_check_failure_blocks_delivery(sample_pdf, tmp_path, scripted):
    flagged = {"answers": [{"item_number": n, "answer": "x", "flag": "ambiguous" if n == 4 else None}
                           for n in range(1, 13)]}
    rep = run(sample_pdf, 7, scripted(responses(A2=flagged)), str(tmp_path))
    assert rep.status == "stopped"
    a2 = next(c for c in rep.checks if c["id"] == "A2")
    assert a2["status"] == "failed" and "ambiguous" in a2["problems"][0]


def test_no_model_configured(sample_pdf, tmp_path):
    rep = run(sample_pdf, 7, None, str(tmp_path))
    assert rep.status == "stopped" and rep.stage == "input"


def test_rejects_other_standards(sample_pdf, tmp_path, scripted):
    rep = run(sample_pdf, 9, scripted(responses()), str(tmp_path))
    assert rep.status == "stopped" and "Standard 7 or Standard 8" in rep.parent_message


def test_bad_page_range(sample_pdf, tmp_path, scripted):
    rep = run(sample_pdf, 7, scripted(responses()), str(tmp_path), page_range="5-9")
    assert rep.status == "stopped" and rep.stage == "input"


def test_model_errors_become_reports(sample_pdf, tmp_path, scripted):
    from learn.llm import LLMError

    def boom(prompt, llm):
        raise LLMError("Claude API credentials are not configured (set ANTHROPIC_API_KEY).")

    rep = run(sample_pdf, 7, scripted(responses(select_concept=boom)), str(tmp_path))
    assert rep.status == "stopped" and "credentials" in rep.parent_message


def test_unexpected_error_never_delivers(sample_pdf, tmp_path, scripted):
    def crash(prompt, llm):
        raise KeyError("surprise")

    rep = run(sample_pdf, 7, scripted(responses(A1=crash)), str(tmp_path))
    assert rep.status == "stopped" and rep.stage == "internal"
    assert not os.path.exists(tmp_path / "deliver")


def test_unreadable_file_reports_extract_stage(tmp_path, scripted):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"%PDF-1.4 not really")
    rep = run(str(bad), 7, scripted(responses()), str(tmp_path / "out"))
    assert rep.status == "stopped" and rep.stage == "extract"


def test_many_choose_options_fail_checks_not_rendering(sample_pdf, tmp_path, scripted):
    bad = copy.deepcopy(SAMPLE_LESSON)
    bad["stages"][0]["items"][1]["options"] = [f"{n} cm" for n in range(1, 31)]
    rep = run(sample_pdf, 7, scripted(responses(generate_lesson=bad, repair_lesson=bad)), str(tmp_path))
    assert rep.stage == "validate"
    d3 = next(c for c in rep.checks if c["id"] == "D3")
    assert any("need 3-4" in p for p in d3["problems"])
