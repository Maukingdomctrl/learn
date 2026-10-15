"""End-to-end pipeline (methodology Section 2).

Order: input -> extract -> select + sufficiency -> focus -> teaching plan -> generate
-> [timing -> render -> D checks -> A checks] -> repair (max 2 rounds, full re-render and re-check each time)
-> deliver or stop with a limitation report.

After selection, planning, generation, repair and the checks use only the focused source: the selected units
plus their immediate neighbours on the same page, never the whole PDF.

Timing adjustment (step 6) is folded into the repair loop: a timing failure is repaired with the 6.4
hierarchy and then re-rendered and re-checked like any other failure.
Rendered files live in a private work folder and are copied to the delivery folder only when every
check has passed, so partial or unvalidated PDFs are never delivered.
"""

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from typing import Optional

from . import config as C
from .extraction import ExtractionError, choose_ocr, extract, pdf_page_count
from .generation import GenerationError, generate_lesson, plan_lesson, repair_lesson, select_concept
from .grounding import InputError, SourceIndex, check_selection, parse_page_range, selection_unit_ids
from .llm import LLM, LLMError
from .rendering import RenderError, render
from .timing import lesson_timing
from .validation import CheckResult, ai_checks, deterministic_checks, not_run_ai
from .visuals.practice import fill_visual_answers


@dataclass
class Report:
    status: str  # "delivered" | "stopped"
    parent_message: str
    parent_actions: list[str] = field(default_factory=list)
    stage: str = ""  # pipeline step where it stopped
    rounds: int = 0
    checks: list[dict] = field(default_factory=list)
    timing: Optional[dict] = None
    warnings: list[str] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    student_pdf: Optional[str] = None
    key_pdf: Optional[str] = None
    error: Optional[str] = None  # technical detail of the failure that stopped the run, if any
    source_focus: list[str] = field(default_factory=list)  # source units planning and generation could use
    plan: Optional[dict] = None
    model_calls: list[dict] = field(default_factory=list)  # per request: limits, stop_reason, token usage, error

    def to_dict(self) -> dict:
        return asdict(self)


def _stop(report: Report, stage: str, message: str, actions: list[str], error: Optional[Exception] = None) -> Report:
    report.status = "stopped"
    report.stage = stage
    report.parent_message = message
    report.parent_actions = actions
    if error is not None:
        report.error = f"{type(error).__name__}: {error}"
    return report


def _attach_model_log(report: Report, llm) -> Report:
    report.model_calls = list(getattr(llm, "call_log", None) or [])
    report.log += list(getattr(llm, "notes", None) or [])
    return report


def _model_actions(err: Exception) -> list[str]:
    if "credentials" in str(err).lower():
        return ["Ask the person who set up Learn to configure ANTHROPIC_API_KEY (see README)."]
    return ["Try again later."]


def _failures(checks: list[CheckResult]) -> list[str]:
    return [f"{c.id} {c.name}: {p}" for c in checks if c.status == "failed" for p in c.problems]


def run(
    pdf_path: str,
    standard: int,
    llm: Optional[LLM],
    out_dir: str,
    topic: str = "",
    page_range: str = "",
    ocr_setting: Optional[str] = None,
) -> Report:
    """Run the pipeline. Any unexpected error becomes a stopped report; nothing is delivered."""
    try:
        return _attach_model_log(_run(pdf_path, standard, llm, out_dir, topic, page_range, ocr_setting), llm)
    except Exception as e:  # noqa: BLE001 - last-resort guard so the parent always gets a report
        deliver = os.path.join(out_dir, "deliver")
        shutil.rmtree(deliver, ignore_errors=True)
        report = Report(status="stopped", parent_message="")
        report.log.append(f"Unexpected error: {type(e).__name__}: {e}")
        _stop(
            report,
            "internal",
            "Learn hit an unexpected error, so no lesson was delivered.",
            ["Try again. If it keeps happening, share report.json with the developer."],
            error=e,
        )
        return _attach_model_log(report, llm)


def _run(
    pdf_path: str,
    standard: int,
    llm: Optional[LLM],
    out_dir: str,
    topic: str,
    page_range: str,
    ocr_setting: Optional[str],
) -> Report:
    report = Report(status="stopped", parent_message="")
    work = os.path.join(out_dir, "work")
    deliver = os.path.join(out_dir, "deliver")
    os.makedirs(work, exist_ok=True)

    # Step 1: input
    if standard not in (7, 8):
        return _stop(report, "input", "Learn V1 supports Standard 7 or Standard 8 only.", ["Select Standard 7 or 8."])
    if llm is None:
        return _stop(
            report,
            "input",
            "Learn is not connected to the Claude API, so it cannot write a lesson.",
            ["Ask the person who set up Learn to configure ANTHROPIC_API_KEY (see README)."],
        )

    # Step 2: extract
    ocr_fn, ocr_name = choose_ocr(ocr_setting or C.ocr_backend(), llm)
    report.log.append(f"OCR backend: {ocr_name}")
    try:
        page_count = pdf_page_count(pdf_path)
        pages = parse_page_range(page_range, page_count)
        source = extract(pdf_path, ocr_fn, ocr_name, pages)
    except InputError as e:
        return _stop(report, "input", str(e), ["Correct the page range, or leave it empty to use all pages."], e)
    except (ExtractionError, RuntimeError) as e:
        return _stop(
            report, "extract", f"The file could not be read as a PDF ({e}).", ["Upload an unprotected PDF file."], e
        )
    report.warnings = list(source.warnings)
    report.log.append(f"Extracted {len(source.units)} source units from {source.page_count} pages")
    if not source.units:
        actions = ["Upload a PDF with selectable text, or a clearer scan."]
        if source.unreadable_pages and ocr_fn is None:
            actions.append("This PDF looks scanned and no OCR is available on this installation.")
        return _stop(report, "extract", "No usable text could be read from the PDF.", actions)
    index = SourceIndex(source.units)

    # Steps 3-4: select scope and apply the sufficiency test
    try:
        sel = select_concept(llm, index, standard, topic)
    except LLMError as e:
        return _stop(report, "select", f"Learn could not analyse the material: {e}", _model_actions(e), e)
    report.log.append(f"Selection: {json.dumps(sel, ensure_ascii=False)[:400]}")
    if sel.get("status") != "ok":
        return _stop(
            report,
            "sufficiency",
            sel.get("insufficiency_reason") or "The material does not explain a topic fully enough to teach it.",
            [sel.get("parent_action") or "Upload the pages that explain the topic."],
        )
    problems = check_selection(sel, index)
    if problems:
        return _stop(
            report,
            "sufficiency",
            "The uploaded material does not contain enough explanation to teach "
            f"'{sel.get('concept') or 'a topic'}' without adding outside content.",
            ["Upload the pages that explain this topic, or choose a different topic or page range."]
            + [f"Detail: {p}" for p in problems],
        )

    # Focus: from here on the model sees only the selected units and their immediate neighbours.
    focus = index.focus(selection_unit_ids(sel), C.CONTEXT_NEIGHBORS)
    report.source_focus = [u.id for u in focus.units]
    report.log.append(f"Focused source: {len(focus.units)} of {len(index.units)} units")

    # Step 5a: teaching plan (checked in code against the focused source)
    try:
        plan = plan_lesson(llm, focus, standard, sel)
    except GenerationError as e:
        return _stop(
            report,
            "plan",
            f"Learn could not plan a lesson grounded in this material: {e}",
            _model_actions(e) if "credentials" in str(e).lower() else ["Try a narrower topic or page range."],
            e,
        )
    report.plan = plan.model_dump()
    with open(os.path.join(work, "plan.json"), "w") as f:
        f.write(plan.model_dump_json(indent=1))

    # Step 5b: generate the lesson from the plan
    try:
        lesson = generate_lesson(llm, focus, standard, sel, plan)
    except GenerationError as e:
        return _stop(report, "generate", f"Learn could not produce a valid lesson: {e}", _model_actions(e), e)
    lesson.standard = standard
    report.log += fill_visual_answers(lesson)  # hidden-label answers come from the diagram spec, not the model

    # Steps 6-9: timing, render, validate, repair
    checks: list[CheckResult] = []
    for round_no in range(C.MAX_REPAIR_ROUNDS + 1):
        report.rounds = round_no
        timing = lesson_timing(lesson)
        report.timing = timing.to_dict()
        round_dir = os.path.join(work, f"round{round_no}")
        with open(os.path.join(work, f"lesson_round{round_no}.json"), "w") as f:
            f.write(lesson.model_dump_json(indent=1))
        try:
            rendered = render(lesson, focus, timing, round_dir, report.warnings)
        except RenderError as e:
            return _stop(report, "render", f"Learn could not print the lesson: {e}", ["Contact support."], e)
        checks = deterministic_checks(lesson, focus, timing, rendered, round_no, plan)
        if all(c.passed for c in checks):
            checks += ai_checks(llm, lesson, focus, rendered, plan)
        else:
            checks += not_run_ai("not run this round: deterministic checks failed first")
        report.checks = [c.to_dict() for c in checks]
        failures = _failures(checks)
        report.log.append(f"Round {round_no}: {len(failures)} problems")
        if not failures and all(c.passed for c in checks):
            os.makedirs(deliver, exist_ok=True)
            report.student_pdf = shutil.copy(rendered.student_pdf, os.path.join(deliver, "student_lesson.pdf"))
            report.key_pdf = shutil.copy(rendered.key_pdf, os.path.join(deliver, "parent_answer_key.pdf"))
            report.status = "delivered"
            report.stage = "deliver"
            report.parent_message = (
                f"Your lesson is ready: about {round(timing.t_lesson / 60)} minutes, "
                "2 student pages and a separate answer key. All checks passed."
            )
            report.parent_actions = [
                "Print the student pages single-sided.",
                "Keep the answer key away from your child until they finish.",
            ]
            return report
        if round_no == C.MAX_REPAIR_ROUNDS:
            break
        try:
            lesson = repair_lesson(llm, focus, lesson, failures, timing.to_dict(), plan)
            lesson.standard = standard
            report.log += fill_visual_answers(lesson)
        except GenerationError as e:
            report.log.append(f"Repair {round_no + 1} failed: {e}")
            report.error = f"{type(e).__name__}: {e}"
            break

    failed_ids = sorted({c["id"] for c in report.checks if c["status"] == "failed"})
    return _stop(
        report,
        "validate",
        "Learn could not produce a lesson that passes all quality checks for this material, so no "
        "lesson was delivered.",
        [
            "Try again, or choose a narrower topic or page range.",
            f"Checks still failing: {', '.join(failed_ids) or 'unknown'}",
        ],
    )


def save_report(report: Report, out_dir: str) -> str:
    path = os.path.join(out_dir, "report.json")
    with open(path, "w") as f:
        json.dump(report.to_dict(), f, indent=1, ensure_ascii=False)
    return path
