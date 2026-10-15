"""Source-unit index, page ranges, and the code side of the sufficiency test (Section 3)."""
import re
from typing import Optional

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

    def total_chars(self) -> int:
        return sum(len(u.text) for u in self.units)


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
    bad = [i for key in ("explanation_unit_ids", "procedure_unit_ids", "supporting_unit_ids")
           for i in sel.get(key, []) if not index.exists(i)]
    if bad:
        problems.append(f"cites unknown source units: {', '.join(bad[:5])}")
    if not sel.get("can_support_7_items", False):
        problems.append("(3.3b) source does not support at least 7 grounded scored items")
    return problems
