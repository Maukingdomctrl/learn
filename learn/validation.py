"""Section 8 checks.

D1-D7 are deterministic code checks. A1-A4 are separate model calls; they are fallible filters, not proof
of quality. Each check returns a CheckResult; a lesson is delivered only when every check passes.
"""
import json
import re
from dataclasses import asdict, dataclass, field

from . import config as C
from .calc import CalcError, answer_matches
from .grounding import SourceIndex
from .llm import LLM, LLMError
from .models import Lesson
from .rendering import RenderResult
from .sequence import stage_sequence
from .textutil import count_words, has_blank, sentences
from .timing import LessonTiming


@dataclass
class CheckResult:
    id: str
    name: str
    kind: str  # "deterministic" | "ai"
    status: str  # "passed" | "failed" | "not_run"
    problems: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict:
        return asdict(self)


def _result(cid: str, name: str, kind: str, problems: list[str]) -> CheckResult:
    return CheckResult(cid, name, kind, "failed" if problems else "passed", problems)


# ---------------------------------------------------------------- D1 structure
def d1_structure(lesson: Lesson) -> CheckResult:
    p = []
    if lesson.standard not in (7, 8):
        p.append(f"Standard must be 7 or 8, got {lesson.standard}")
    order = [s.stage for s in lesson.stages]
    if order != list(C.STAGES):
        p.append(f"stages must be {list(C.STAGES)} in order, got {order}")
    total = 0
    for s in lesson.stages:
        lo, hi = C.STAGE_ITEM_RANGES[s.stage]
        n = len(s.items)
        total += n
        if not lo <= n <= hi:
            p.append(f"{s.stage} has {n} scored items; allowed {lo}-{hi}")
    lo, hi = C.TOTAL_ITEM_RANGE
    if not lo <= total <= hi:
        p.append(f"total scored items {total}; allowed {lo}-{hi}")
    disc = lesson.stage("Discover")
    if disc and not [line for line in disc.worked_example if line.strip()]:
        p.append("Discover has no worked example or model")
    if disc and not disc.hook.strip():
        p.append("Discover has no hook")
    return _result("D1", "Structure", "deterministic", p)


# ---------------------------------------------------------------- D2 citations
def d2_citations(lesson: Lesson, index: SourceIndex) -> CheckResult:
    p = []

    def check(label: str, ids: list[str]):
        valid = [i for i in ids if index.exists(i)]
        unknown = [i for i in ids if not index.exists(i)]
        if not valid:
            p.append(f"{label} has no valid source_unit_id")
        if unknown:
            p.append(f"{label} cites unknown source units {unknown}")

    for c in lesson.concepts:
        check(f"concept '{c.name}'", c.source_unit_ids)
    if not lesson.core_claims:
        p.append("no core claims listed")
    for c in lesson.core_claims:
        check(f"claim '{c.text[:50]}'", c.source_unit_ids)
    for t in lesson.terms:
        check(f"term '{t.term}'", t.source_unit_ids)
    for e in lesson.answer_key.entries:
        check(f"answer-key entry {e.item_number}", e.source_unit_ids)
    for s in lesson.stages:
        for v in s.visuals:
            check(f"{s.stage} table '{v.caption[:40]}'", v.source_unit_ids)
    return _result("D2", "Citations", "deterministic", p)


# ---------------------------------------------------------------- D3 activity rules
def d3_activities(lesson: Lesson) -> CheckResult:
    p = []
    types = [s.activity_type for s in lesson.stages]
    if len(set(types)) < 3:
        p.append(f"only {len(set(types))} distinct activity types; need at least 3")
    for a, b in zip(lesson.stages, lesson.stages[1:], strict=False):
        if a.activity_type == b.activity_type:
            p.append(f"{a.stage} and {b.stage} both use {a.activity_type}")
    for s in lesson.stages:
        t = s.activity_type
        if s.stage not in C.ALLOWED_STAGES[t]:
            p.append(f"{t} is not allowed in {s.stage}")
        if t in C.EXAMPLE_REQUIRED and s.example is None:
            p.append(f"{s.stage} ({t}) needs a done-for-you example")
        n = len(s.items)
        if t == "MATCH":
            if n > 4:
                p.append(f"{s.stage} MATCH has {n} prompts; max 4")
            if len(s.options) < n + 1:
                p.append(f"{s.stage} MATCH has {len(s.options)} options for {n} prompts; need at least {n + 1}")
        if t == "FILL_IN":
            if s.word_bank and s.stage == "Apply":
                p.append("Apply FILL_IN must not have a word bank")
            if s.word_bank and len(s.word_bank) < n + 1:
                p.append(f"{s.stage} word bank has {len(s.word_bank)} words for {n} blanks; need at least {n + 1}")
        if t in ("FILL_IN", "COMPLETE_STEPS"):
            for i in s.items:
                if not has_blank(i.prompt):
                    p.append(f"item {i.number} ({t}) has no blank '____' in its prompt")
        if t == "SORT":
            if not 2 <= len(s.groups) <= 3:
                p.append(f"{s.stage} SORT needs 2-3 groups, has {len(s.groups)}")
            things = n + (1 if s.example else 0)
            if not 3 <= things <= 6:
                p.append(f"{s.stage} SORT has {things} things to sort; allowed 3-6")
        if s.stage == "Recall" and s.hint_pointer:
            p.append("Recall must not have a hint pointer")
        for i in s.items:
            entry = lesson.key_for(i.number)
            ans = entry.answer.strip() if entry else ""
            if t == "CHOOSE":
                if not 3 <= len(i.options) <= 4:
                    p.append(f"item {i.number} CHOOSE has {len(i.options)} options; need 3-4")
                if sum(1 for o in i.options if o.strip() == ans) != 1:
                    p.append(f"item {i.number} CHOOSE answer must equal exactly one option")
                if any(re.search(r"\b(all|none) of the above\b", o, re.I) for o in i.options):
                    p.append(f"item {i.number} uses 'all/none of the above'")
            if t == "ANNOTATE":
                need = 2 if s.stage == "Discover" else 3
                if len(i.options) < need:
                    p.append(f"item {i.number} ANNOTATE has {len(i.options)} targets; need at least {need}")
                targets = {o.strip() for o in i.options}
                if ans and not all(a.strip() in targets for a in ans.split(";")):
                    p.append(f"item {i.number} ANNOTATE answer is not one of its targets")
            if t == "MATCH" and ans not in [o.strip() for o in s.options]:
                p.append(f"item {i.number} MATCH answer is not one of the options")
            if t == "SORT" and ans.lower() not in [g.strip().lower() for g in s.groups]:
                p.append(f"item {i.number} SORT answer is not one of the groups")
            if t == "SPOT_MISTAKE":
                if not i.peer_work:
                    p.append(f"item {i.number} SPOT_MISTAKE has no peer work")
                elif not 1 <= i.peer_work.mistake_step <= len(i.peer_work.steps):
                    p.append(f"item {i.number} mistake_step is outside the peer's steps")
            if t == "SKETCH" and not (i.sketch_criteria or "").strip():
                p.append(f"item {i.number} SKETCH needs countable criteria")
    return _result("D3", "Activity rules", "deterministic", p)


# ---------------------------------------------------------------- D4 text limits
ACTION_VERBS = {
    "circle", "underline", "tick", "write", "draw", "match", "fill", "sort", "solve", "find", "explain",
    "complete", "choose", "label", "correct", "show", "calculate", "use", "look", "read", "turn", "list",
    "describe", "compare", "join", "mark", "cross", "copy", "check", "work", "put", "name", "give", "add",
    "fix", "shade", "count",
}
BANNED_STUDENT = [
    (r"\bscore\s*:", "score box"), (r"\btime limit\b", "time limit"),
    (r"\btimer\b", "timer"), (r"\bstopwatch\b", "stopwatch"), (r"\bword ?search\b", "word search"),
    (r"\bcrossword\b", "crossword"), (r"\banagram", "anagram"), (r"\bmaze\b", "maze"),
    (r"\bcolou?r(ing)? in\b", "colouring task"), (r"\beasy!", "'Easy!' label"),
    (r"\b(NOT|EXCEPT)\b", "negative-stem question (NOT/EXCEPT)"),
    (r"\b(all|none) of the above\b", "all/none of the above"),
    (r"\bguarantee", "guarantee claim"), (r"\bexam[- ]ready\b", "exam-readiness claim"),
]
COLOUR_RE = re.compile(r"\b(red|blue|green|yellow|orange|purple|pink|violet|colou?r(ed|s)?)\b", re.I)


def reading_runs(lesson: Lesson) -> tuple[int, int]:
    """(words before first mark, longest run of words between marks)."""
    before_first = None
    run = longest = 0
    for s in lesson.stages:
        for c in stage_sequence(s):
            if c.kind == "mark":
                if before_first is None:
                    before_first = run
                longest = max(longest, run)
                run = 0
            else:
                run += count_words(c.text)
    longest = max(longest, run)
    return (before_first if before_first is not None else run), longest


def d4_text(lesson: Lesson) -> CheckResult:
    p = []
    texts = []
    for s in lesson.stages:
        for c in stage_sequence(s):
            if c.kind == "instruction":
                for sent in sentences(c.text):
                    n = count_words(sent)
                    if n > C.MAX_INSTRUCTION_WORDS:
                        p.append(f"{s.stage} instruction sentence has {n} words "
                                 f"(max {C.MAX_INSTRUCTION_WORDS}): '{sent[:60]}'")
                    verbs = [w for w in re.findall(r"[a-z]+", sent.lower()) if w in ACTION_VERBS]
                    if len(verbs) > C.MAX_ACTIONS_PER_INSTRUCTION:
                        p.append(f"{s.stage} instruction has {len(verbs)} actions {verbs} "
                                 f"(max {C.MAX_ACTIONS_PER_INSTRUCTION})")
                if COLOUR_RE.search(c.text):
                    p.append(f"{s.stage} instruction refers to colour: '{c.text[:60]}'")
            elif c.kind == "text":
                for sent in sentences(c.text):
                    n = count_words(sent)
                    if n > C.MAX_SENTENCE_WORDS:
                        p.append(f"{s.stage} sentence has {n} words (max {C.MAX_SENTENCE_WORDS}): '{sent[:60]}'")
            if c.kind != "mark":
                texts.append(c.text)
    before, longest = reading_runs(lesson)
    if before > C.MAX_WORDS_BEFORE_FIRST_MARK:
        p.append(f"{before} words before the first pencil mark (max {C.MAX_WORDS_BEFORE_FIRST_MARK})")
    if longest > C.MAX_READING_RUN_WORDS:
        p.append(f"{longest} words of continuous reading between pencil marks (max {C.MAX_READING_RUN_WORDS})")
    texts += [lesson.title, lesson.scope_line]
    student_text = "\n".join(texts)
    for pattern, label in BANNED_STUDENT:
        flags = 0 if label.startswith("negative-stem") else re.I
        if re.search(pattern, student_text, flags):
            p.append(f"banned pattern on student pages: {label}")
    key_text = " ".join([e.reason for e in lesson.answer_key.entries] + [lesson.answer_key.scope_covered])
    if re.search(r"\bguarantee|\bexam[- ]ready\b|\bmaster(s|ed)? (the|this)\b", key_text, re.I):
        p.append("answer key text claims mastery or exam readiness")
    return _result("D4", "Text limits", "deterministic", p)


# ---------------------------------------------------------------- D5 timing
def d5_timing(lesson: Lesson, timing: LessonTiming, round_no: int) -> CheckResult:
    p = []
    t = timing.t_lesson
    rule_s = False
    if t > C.T_MAX_S:
        p.append(f"lesson is {t:.0f} s ({t / 60:.1f} min); max {C.T_MAX_S} s")
    elif t < C.T_MIN_S:
        note = (lesson.answer_key.shortened_lesson_note or "").strip()
        if note and round_no >= 1 and t >= C.RULE_S_FLOOR_S:
            rule_s = True  # Rule S: source too thin, after at least one attempt to lengthen
        else:
            why = "" if t >= C.RULE_S_FLOOR_S else f"; below the {C.RULE_S_FLOOR_S} s Rule S floor"
            p.append(f"lesson is {t:.0f} s ({t / 60:.1f} min); min {C.T_MIN_S} s{why}")
    elif (lesson.answer_key.shortened_lesson_note or "").strip():
        p.append("shortened_lesson_note is set but the lesson is not short; remove it")
    for st in timing.stages:
        if st.total > st.cap:
            p.append(f"{st.stage} block is {st.total:.0f} s; cap {st.cap:.0f} s")
    if timing.written_words > C.MAX_WRITTEN_WORDS:
        p.append(f"child must write {timing.written_words} words; max {C.MAX_WRITTEN_WORDS}")
    res = _result("D5", "Timing", "deterministic", p)
    if rule_s and not p:
        res.problems = [f"Rule S applied: {t:.0f} s with shortened-lesson note (informational)"]
    return res


# ---------------------------------------------------------------- D6 layout
def _landscape_a4(size: tuple[float, float]) -> bool:
    w, h = size
    return abs(w - 841.89) < 2 and abs(h - 595.28) < 2


def d6_layout(lesson: Lesson, r: RenderResult) -> CheckResult:
    p = []
    L = r.layout
    if len(r.student_pages) != 2:
        p.append(f"student PDF has {len(r.student_pages)} pages; must be exactly 2")
    if not 1 <= len(r.key_pages) <= 2:
        p.append(f"answer key PDF has {len(r.key_pages)} pages; must be 1-2")
    for name, pages in (("student", r.student_pages), ("answer key", r.key_pages)):
        bad = [i + 1 for i, s in enumerate(pages) if not _landscape_a4(s)]
        if bad:
            p.append(f"{name} pages {bad} are not landscape A4 (297 x 210 mm)")
    for o in L.get("overflow", []):
        p.append(f"content overflows: {o}")
    if L.get("min_font_pt", 99) < C.MIN_FONT_PT - 0.01:
        p.append(f"smallest text is {L['min_font_pt']:.1f} pt; min {C.MIN_FONT_PT} pt")
    for h in L.get("line_heights_mm", []):
        if h < C.MIN_LINE_MM - 0.05:
            p.append(f"write-in line {h:.1f} mm high; min {C.MIN_LINE_MM} mm")
            break
    for w in L.get("line_lengths_mm", []):
        if w < C.MIN_LINE_LEN_MM:
            p.append(f"write-in line {w:.0f} mm long; min {C.MIN_LINE_LEN_MM} mm")
            break
    for w in L.get("num_blank_mm", []):
        if w < C.MIN_NUM_BLANK_MM:
            p.append(f"numeric answer blank {w:.0f} mm wide; min {C.MIN_NUM_BLANK_MM} mm")
            break
    for h in L.get("solve_mm", []):
        if h < C.MIN_SOLVE_MM - 0.05:
            p.append(f"SOLVE workspace {h:.0f} mm high; min {C.MIN_SOLVE_MM} mm")
            break
    for it in L.get("items_lines", []):
        if it["found"] < it["required"]:
            p.append(f"item {it['item']} has {it['found']} ruled lines; needs {it['required']}")
    if not (L.get("recall_on_page2") and L.get("recall_banner") and L.get("recall_bottom_right")):
        p.append("Recall box with its banner must be at the bottom right of Page 2")
    hints = set(L.get("hints", []))
    for name in ("Vary", "Apply"):
        if name not in hints:
            p.append(f"{name} has no hint pointer")
    if "Recall" in hints:
        p.append("Recall must not have a hint pointer")
    # Separation: the key's answer table must not appear on student pages.
    if "Parent answer key" in r.student_text or "Why it is correct" in r.student_text:
        p.append("answer-key content found in the student PDF")
    return _result("D6", "Layout", "deterministic", p)


# ---------------------------------------------------------------- D7 key completeness and arithmetic
def d7_key(lesson: Lesson, index: SourceIndex) -> CheckResult:
    p = []
    numbers = [i.number for _, i in lesson.items()]
    if numbers != list(range(1, len(numbers) + 1)):
        p.append(f"scored items must be numbered 1..{len(numbers)} in order, got {numbers}")
    key_numbers = [e.item_number for e in lesson.answer_key.entries]
    for n in numbers:
        c = key_numbers.count(n)
        if c != 1:
            p.append(f"item {n} has {c} answer-key entries; needs exactly 1")
    extra = sorted(set(key_numbers) - set(numbers))
    if extra:
        p.append(f"answer-key entries for items that do not exist: {extra}")
    for e in lesson.answer_key.entries:
        if not e.answer.strip():
            p.append(f"item {e.item_number}: empty answer")
        if not e.reason.strip():
            p.append(f"item {e.item_number}: missing reason")
        if not index.pages(e.source_unit_ids):
            p.append(f"item {e.item_number}: no source page")
        if e.calculation:
            try:
                ok, detail = answer_matches(e.answer, e.calculation)
                if not ok:
                    p.append(f"item {e.item_number}: arithmetic mismatch ({detail})")
            except CalcError as err:
                p.append(f"item {e.item_number}: calculation cannot be evaluated ({err})")
    stage_of = {i.number: s for s, i in lesson.items()}
    for e in lesson.answer_key.entries:
        s = stage_of.get(e.item_number)
        if s and s.activity_type in ("SOLVE", "COMPLETE_STEPS") and re.search(r"\d", e.answer) and not e.calculation:
            p.append(f"item {e.item_number}: numeric answer has no calculation to verify")
    if not lesson.answer_key.scope_covered.strip():
        p.append("answer key has no scope statement")
    return _result("D7", "Answer key and arithmetic", "deterministic", p)


def deterministic_checks(lesson: Lesson, index: SourceIndex, timing: LessonTiming,
                         render: RenderResult, round_no: int) -> list[CheckResult]:
    return [d1_structure(lesson), d2_citations(lesson, index), d3_activities(lesson), d4_text(lesson),
            d5_timing(lesson, timing, round_no), d6_layout(lesson, render), d7_key(lesson, index)]


# ---------------------------------------------------------------- AI checks
AI_SYSTEM = ("You are a strict reviewer of printed lessons for Standard 7-8 students. "
             "Reply with one JSON object only.")

A1_PROMPT = """Check grounding and factual correctness (check A1).
Pass only if: every taught claim and every answer is supported by its cited source units; practice items use
the source's own method; no facts, terms or methods come from outside the source; no analogy (is_analogy=true)
is tested; nothing contradicts the source. Report each problem with its location.

Lesson:
{lesson}

Cited source units:
{units}

Reply: {{"pass": true|false, "issues": [{{"location": "...", "problem": "..."}}]}}"""

A2_PROMPT = """You are a student who has ONLY these two printed worksheet pages. Answer every numbered item using
ONLY what is printed on the pages. You may already know this topic: ignore that knowledge. Flag any item that is
ambiguous, has more than one defensible answer, or needs knowledge that is not on the pages.
Skip the "Ex - done for you" examples; they are not numbered items.

Worksheet text:
{text}

Reply: {{"answers": [{{"item_number": 1, "answer": "...", "flag": null or "reason"}}]}}"""

A3_PROMPT = """Compare a blind solver's answers with the answer key (check A3).
For each item, decide whether the solver's answer matches the key's answer or accepted alternatives in meaning.
For each mismatch, say whether the item wording or the key looks wrong, using the source units.

Solver answers:
{answers}

Answer key:
{key}

Lesson items:
{items}

Source units:
{units}

Reply: {{"pass": true|false, "issues": [{{"location": "item N", "problem": "..."}}]}}"""

A4_PROMPT = """Check clarity and age fit of these student pages for Standard 7-8 (ages 12-14), first-time learners
(check A4).
Pass only if: instructions are clear without adult help; every technical term used after Discover is explained
in Discover; language suits ages 12-14; the hook is relevant and answered by the lesson; no trick questions;
no item can be answered by copying a sentence word for word; items within a stage differ meaningfully;
support fades across the stages (Discover > Reinforce > Vary > Apply > Recall); Recall cannot be answered by
copying from Page 2; tone is neutral and respectful.

Lesson (student-facing fields):
{lesson}

Reply: {{"pass": true|false, "issues": [{{"location": "...", "problem": "..."}}]}}"""


def _issues(data: dict) -> list[str]:
    out = []
    for i in data.get("issues", []) or []:
        if isinstance(i, dict):
            out.append(f"{i.get('location', '?')}: {i.get('problem', '')}".strip())
        else:
            out.append(str(i))
    return out


def _verdict(cid: str, name: str, data: dict) -> CheckResult:
    issues = _issues(data)
    if data.get("pass") is True and not issues:
        return CheckResult(cid, name, "ai", "passed")
    return CheckResult(cid, name, "ai", "failed", issues or ["reviewer did not pass the lesson"])


def _student_view(lesson: Lesson) -> str:
    d = lesson.model_dump(exclude={"answer_key"})
    return json.dumps(d, ensure_ascii=False, indent=1)


def _cited(lesson: Lesson) -> list[str]:
    ids = [i for c in lesson.concepts for i in c.source_unit_ids]
    ids += [i for c in lesson.core_claims for i in c.source_unit_ids]
    ids += [i for t in lesson.terms for i in t.source_unit_ids]
    ids += [i for e in lesson.answer_key.entries for i in e.source_unit_ids]
    return list(dict.fromkeys(ids))


def ai_checks(llm: LLM, lesson: Lesson, index: SourceIndex, render: RenderResult) -> list[CheckResult]:
    units = index.texts(_cited(lesson))
    results = []
    try:
        results.append(_verdict("A1", "Grounding and factual correctness", llm.json(
            "A1", AI_SYSTEM, A1_PROMPT.format(lesson=lesson.model_dump_json(indent=1), units=units))))
    except LLMError as e:
        results.append(CheckResult("A1", "Grounding and factual correctness", "ai", "failed", [str(e)]))

    # A2 sees only the text of the rendered student PDF.
    a2_answers: list = []
    try:
        data = llm.json("A2", AI_SYSTEM, A2_PROMPT.format(text=render.student_text))
        a2_answers = data.get("answers", []) or []
        problems = [f"item {a.get('item_number')}: {a.get('flag')}" for a in a2_answers if a.get("flag")]
        answered = {a.get("item_number") for a in a2_answers if str(a.get("answer", "")).strip()}
        missing = [i.number for _, i in lesson.items() if i.number not in answered]
        if missing:
            problems.append(f"blind solver could not answer items {missing}")
        results.append(_result("A2", "Blind solve (student pages only)", "ai", problems))
    except LLMError as e:
        results.append(CheckResult("A2", "Blind solve (student pages only)", "ai", "failed", [str(e)]))

    try:
        if not a2_answers:
            raise LLMError("no blind-solver answers to compare")
        key = [e.model_dump() for e in lesson.answer_key.entries]
        items = [{"number": i.number, "stage": s.stage, "type": s.activity_type, "prompt": i.prompt,
                  "options": i.options or s.options or s.groups} for s, i in lesson.items()]
        results.append(_verdict("A3", "Key agreement", llm.json("A3", AI_SYSTEM, A3_PROMPT.format(
            answers=json.dumps(a2_answers, ensure_ascii=False), key=json.dumps(key, ensure_ascii=False),
            items=json.dumps(items, ensure_ascii=False), units=units))))
    except LLMError as e:
        results.append(CheckResult("A3", "Key agreement", "ai", "failed", [str(e)]))

    try:
        results.append(_verdict("A4", "Clarity and age fit", llm.json(
            "A4", AI_SYSTEM, A4_PROMPT.format(lesson=_student_view(lesson)))))
    except LLMError as e:
        results.append(CheckResult("A4", "Clarity and age fit", "ai", "failed", [str(e)]))
    return results


def not_run_ai(reason: str) -> list[CheckResult]:
    names = [("A1", "Grounding and factual correctness"), ("A2", "Blind solve (student pages only)"),
             ("A3", "Key agreement"), ("A4", "Clarity and age fit")]
    return [CheckResult(c, n, "ai", "not_run", [reason]) for c, n in names]
