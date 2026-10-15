"""Progressive visual practice: label slots, derived answers, and the progression rules (D9).

A practice item can carry a copy of a diagram with some labels hidden. Each hideable label is a named slot:

    shape          base, height (triangle, parallelogram) | length, width (rectangle) | radius (circle)
    number_line    point{i}, jump{i}            (only labelled points and jumps)
    bar_model      bar{b}.part{p}, bar{b}.total
    flow_sequence  step{i}
    table          cell{r}.{c}

The answer to a hidden-label item is read from the validated spec by code, never written by the model, so the
key cannot disagree with the picture.
"""

import re

from ..calc import CalcError, evaluate
from .checks import labels, numbers_in, printed_texts
from .specs import BarModelSpec, FlowSequenceSpec, NumberLineSpec, ShapeSpec, Table
from .svg import bar_total, draw, fmt

PRACTICE_STAGES = ("Reinforce", "Vary", "Apply")  # Discover demonstrates; Recall is from memory
PRACTICE_TYPES = {"FILL_IN", "SOLVE"}
NUMERIC_KINDS = (ShapeSpec, BarModelSpec)


def label_slots(v) -> dict[str, str]:
    """Hideable slot -> the answer a child would write in it."""
    if isinstance(v, ShapeSpec):
        names = {"triangle": ("base", "height"), "parallelogram": ("base", "height"), "rectangle": ("length", "width")}
        return {n: fmt(getattr(v, n)) for n in names.get(v.shape, ("radius",)) if getattr(v, n) is not None}
    if isinstance(v, NumberLineSpec):
        slots = {f"point{i}": p.label for i, p in enumerate(v.points) if p.label}
        slots.update({f"jump{i}": j.label for i, j in enumerate(v.jumps) if j.label})
        return slots
    if isinstance(v, BarModelSpec):
        slots = {}
        for b, bar in enumerate(v.bars):
            for p, part in enumerate(bar.parts):
                slots[f"bar{b}.part{p}"] = fmt(part.value)
            slots[f"bar{b}.total"] = fmt(bar.total if bar.total is not None else bar_total(bar))
        return slots
    if isinstance(v, FlowSequenceSpec):
        return {f"step{i}": s for i, s in enumerate(v.steps)}
    if isinstance(v, Table):
        return {f"cell{r}.{c}": cell for r, row in enumerate(v.rows) for c, cell in enumerate(row)}
    return {}


def derived_answer(v, hidden: list[str]) -> str:
    slots = label_slots(v)
    return "; ".join(slots[k] for k in hidden if k in slots)


def hidden_numbers(v, hidden) -> set[float]:
    """Numeric values hidden from the drawing (their grounding is checked by D9's teachability rule)."""
    slots = label_slots(v)
    out = set()
    for k in hidden:
        if isinstance(v, NUMERIC_KINDS) and k in slots:
            out.add(float(slots[k]))
    return out


def practice_items(lesson):
    return [(s, i) for s in lesson.stages for i in s.items if i.visual is not None]


def fill_visual_answers(lesson) -> list[str]:
    """Write the derived answer into the key for every hidden-label item. Returns a log of changes."""
    from ..models import KeyEntry

    log = []
    for _stage, item in practice_items(lesson):
        if not item.hidden:
            continue
        answer = derived_answer(item.visual, item.hidden)
        entry = lesson.key_for(item.number)
        if entry is None:
            lesson.answer_key.entries.append(
                KeyEntry(
                    item_number=item.number,
                    answer=answer,
                    reason="Completes the diagram using the lesson's rule and values.",
                    source_unit_ids=list(item.visual.source_unit_ids),
                )
            )
            log.append(f"item {item.number}: key entry created from the diagram ({answer})")
        elif entry.answer != answer:
            log.append(f"item {item.number}: key answer set from the diagram ({entry.answer!r} -> {answer!r})")
            entry.answer = answer
    lesson.answer_key.entries.sort(key=lambda e: e.item_number)
    return log


def _discover_text(lesson) -> str:
    from ..sequence import stage_sequence

    disc = lesson.stage("Discover")
    if disc is None:
        return ""
    parts = [c.text for c in stage_sequence(disc) if c.kind != "mark"]
    for v in disc.visuals:
        # Spec labels as well as printed lines: drawn text is wrapped, so a step can span several lines.
        parts += printed_texts(v, draw(v)) + labels(v)
    return _norm_space(" | ".join(parts))


def _norm_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def _matches_calculation(value: float, calculation) -> bool:
    if not calculation:
        return False
    try:
        return abs(evaluate(calculation) - value) < 1e-9
    except CalcError:
        return False


def check_progression(lesson) -> list[str]:
    """D9 problems: hidden labels valid and teachable; support decreases from demonstration to recall."""
    from ..sequence import stage_sequence

    p = []
    disc = lesson.stage("Discover")
    demo_kinds = {v.kind for v in (disc.visuals if disc else [])}
    discover_text = _discover_text(lesson)
    last_fraction, last_stage = 0.0, "Discover"
    for stage, item in practice_items(lesson):
        v, n = item.visual, item.number
        if stage.stage not in PRACTICE_STAGES:
            p.append(f"item {n}: diagram practice belongs in Reinforce, Vary or Apply, not {stage.stage}")
            continue
        if stage.activity_type not in PRACTICE_TYPES:
            p.append(f"item {n}: diagram practice must be FILL_IN or SOLVE, not {stage.activity_type}")
        if v.kind not in demo_kinds:
            p.append(f"item {n}: practises a {v.kind} diagram that Discover never demonstrates fully labelled")
        slots = label_slots(v)
        unknown = [k for k in item.hidden if k not in slots]
        if unknown:
            p.append(f"item {n}: hidden labels {unknown} do not exist; choose from {sorted(slots)}")
            continue
        if not item.hidden:
            p.append(f"item {n}: a practice diagram must hide at least one label for the child to complete")
            continue
        if len(set(item.hidden)) != len(item.hidden):
            p.append(f"item {n}: a hidden label is listed twice")
        fraction = len(set(item.hidden)) / len(slots)
        if stage.stage == "Reinforce" and fraction >= 1:
            p.append(f"item {n}: Reinforce must give a partly completed diagram (leave at least one label)")
        if fraction + 1e-9 < last_fraction:
            p.append(
                f"item {n}: support increases again ({fraction:.0%} of labels hidden, after {last_fraction:.0%} "
                f"in {last_stage}); hide at least as many as before"
            )
        last_fraction, last_stage = fraction, stage.stage
        # The key must hold exactly what the diagram implies.
        entry = lesson.key_for(n)
        expected = derived_answer(v, item.hidden)
        if entry is None or entry.answer != expected:
            p.append(f"item {n}: answer key must be the diagram's own value(s) {expected!r}")
        # Every hidden answer must be learnable from the student pages.
        stage_text = " ".join(c.text for c in stage_sequence(stage) if c.kind != "mark")
        bank = _norm_space(" | ".join(stage.word_bank))
        for key in item.hidden:
            ans = slots[key]
            nums = numbers_in(ans)
            if isinstance(v, NUMERIC_KINDS) or (nums and ans.strip().lstrip("+-").replace(".", "", 1).isdigit()):
                value = float(ans) if isinstance(v, NUMERIC_KINDS) else next(iter(nums))
                if not any(abs(value - x) < 1e-9 for x in numbers_in(f"{item.prompt} {stage_text}")):
                    if not _matches_calculation(value, entry.calculation if entry else None):
                        p.append(
                            f"item {n}: hidden value {ans} is neither given on the page nor verified by a key "
                            "calculation"
                        )
            elif _norm_space(ans) not in discover_text and _norm_space(ans) not in bank:
                p.append(f"item {n}: hidden label '{ans}' is not taught in Discover or offered in the word bank")
    recall = lesson.stage("Recall")
    if recall and any(i.visual for i in recall.items):
        p.append("Recall must not show a diagram; the child recalls or sketches from memory")
    return p
