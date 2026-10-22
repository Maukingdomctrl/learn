"""Source-unit index, page ranges, focused context, and the code side of grounding checks (Section 3)."""

import re
from typing import Optional

from .calc import CalcError, answer_matches
from .extraction import SourceUnit


class InputError(ValueError):
    pass


def parse_page_range(text: Optional[str], page_count: int) -> Optional[set[int]]:
    """'3-5, 7' -> {3,4,5,7}. Empty -> None (all pages)."""
    if not text or not text.strip():
        return None
    pages: set[int] = set()
    for part in text.split(","):
        part = part.strip()
        m = re.fullmatch(r"(\d+)\s*(?:-\s*(\d+))?", part)
        if not m:
            raise InputError(f"Page range '{text}' is not valid. Use a form like 3-5 or 2, 4.")
        lo, hi = int(m.group(1)), int(m.group(2) or m.group(1))
        if lo < 1 or hi < lo or hi > page_count:
            raise InputError(f"Page range '{part}' is outside the PDF's {page_count} pages.")
        pages.update(range(lo, hi + 1))
    return pages


class SourceIndex:
    def __init__(self, units: list[SourceUnit]):
        self.units = units
        self.by_id = {u.id: u for u in units}

    def exists(self, uid: str) -> bool:
        return uid in self.by_id

    def pages(self, ids: list[str]) -> list[int]:
        return sorted({self.by_id[i].page for i in ids if i in self.by_id})

    def texts(self, ids: list[str]) -> str:
        return "\n".join(f"[{i}] {self.by_id[i].text}" for i in ids if i in self.by_id)

    def prompt_block(self) -> str:
        return "\n".join(f"[{u.id}] (page {u.page}) {u.text}" for u in self.units)

    def focus(self, ids: list[str], neighbors: int = 1) -> "SourceIndex":
        """The selected units plus up to `neighbors` units either side of each on the same page, in source order.

        Generation, repair and the citation check use this subset, so the model writes from the material the
        selection step chose rather than from the whole PDF.
        """
        wanted = {i for i in ids if i in self.by_id}
        keep: set[int] = set()
        for pos, unit in enumerate(self.units):
            if unit.id not in wanted:
                continue
            for j in range(max(0, pos - neighbors), min(len(self.units), pos + neighbors + 1)):
                if self.units[j].page == unit.page:
                    keep.add(j)
        return SourceIndex([self.units[j] for j in sorted(keep)])


def selection_unit_ids(sel: dict) -> list[str]:
    ids = []
    for key in ("explanation_unit_ids", "procedure_unit_ids", "supporting_unit_ids"):
        ids += [i for i in sel.get(key, []) or [] if isinstance(i, str)]
    return list(dict.fromkeys(ids))


def check_selection(sel: dict, index: SourceIndex) -> list[str]:
    """Code checks on the model's concept selection (sufficiency test 3.3 a and c; b is enforced by D1/A1/A2).

    Returns a list of problems; empty means the selection is acceptable.
    """
    problems = []
    if not sel.get("concept"):
        problems.append("no concept named")
    expl = [i for i in sel.get("explanation_unit_ids", []) if index.exists(i)]
    if not expl:
        problems.append("(3.3a) no source unit explains or defines the concept")
    if sel.get("is_procedure"):
        proc = [i for i in sel.get("procedure_unit_ids", []) if index.exists(i)]
        if not proc:
            problems.append("(3.3c) procedure without source steps or worked example")
    bad = [
        i
        for key in ("explanation_unit_ids", "procedure_unit_ids", "supporting_unit_ids")
        for i in sel.get(key, [])
        if not index.exists(i)
    ]
    if bad:
        problems.append(f"cites unknown source units: {', '.join(bad[:5])}")
    if not sel.get("can_support_7_items", False):
        problems.append("(3.3b) source does not support at least 7 grounded scored items")
    return problems


def check_plan(plan, index: SourceIndex, step_range: tuple[int, int]) -> list[str]:
    """Code checks on the teaching plan: shape, grounding in the focused units, and worked-example arithmetic."""
    problems = []
    lo, hi = step_range
    if not lo <= len(plan.learning_steps) <= hi:
        problems.append(f"plan has {len(plan.learning_steps)} learning steps; need {lo}-{hi}")

    def cites(label: str, ids: list[str]):
        valid = [i for i in ids if index.exists(i)]
        bad = [i for i in ids if not index.exists(i)]
        if not valid:
            problems.append(f"{label} cites no source unit from the selected material")
        if bad:
            problems.append(f"{label} cites unknown or unselected source units {bad}")

    for n, step in enumerate(plan.learning_steps, start=1):
        if not step.idea.strip():
            problems.append(f"learning step {n} is empty")
        cites(f"learning step {n}", step.source_unit_ids)
    if not plan.misconception.wrong_idea.strip() or not plan.misconception.correct_idea.strip():
        problems.append("misconception needs both the wrong idea and the correct idea")
    cites("misconception correction", plan.misconception.source_unit_ids)
    ex = plan.worked_example
    if len([s for s in ex.steps if s.strip()]) < 2:
        problems.append("worked example needs at least 2 steps")
    cites("worked example", ex.source_unit_ids)
    if ex.calculation:
        try:
            ok, detail = answer_matches(ex.answer, ex.calculation)
            if not ok:
                problems.append(f"worked example arithmetic mismatch ({detail})")
        except CalcError as e:
            problems.append(f"worked example calculation cannot be evaluated ({e})")
    elif re.search(r"\d", ex.answer) and "=" in " ".join(ex.steps):
        problems.append("worked example has a computed numeric answer but no calculation to verify")
    if plan.visual_type != "none" and not plan.visual_purpose.strip():
        problems.append(f"visual type '{plan.visual_type}' needs a teaching purpose")
    return problems
