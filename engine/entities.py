"""
Stage 2: entities.py
Recognise PERSON, PLACE, ORGANISATION, EVENT, DOCUMENT, TITLE, DATE, NUMBER,
QUANTITY, FORMULA, TERM using general structural patterns.
A date, number, quantity, or formula is always ONE atomic unit, never split.
"""
from __future__ import annotations
import re
from typing import Dict, List, Any

LIFESPAN_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-2][0-9])[–-](?:1[0-9]{3}|20[0-2][0-9])\b")
FULL_DATE_RE = re.compile(
    r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(?:1[0-9]{3}|20[0-2][0-9])\b"
)
CENTURY_RE = re.compile(r"\b(?:early\s+|late\s+|mid-)?\d{1,2}(?:st|nd|rd|th)\s+century\b", re.IGNORECASE)
DECADE_RE = re.compile(r"\b(?:early\s+|late\s+|mid-)?(?:1[0-9]{3}|20[0-2][0-9])s\b")
YEAR_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-2][0-9])\b")

FORMULA_RE = re.compile(
    r"\b(?:1\s+[A-Za-z]+\s*=\s*\d+(?:\.\d+)?\s*[A-Za-z·/²³0-9-]+|[A-Za-z]\s*=\s*[A-Za-z]{2}|[A-Za-z]\s*=\s*[A-Za-z]\s*[÷×/+-]\s*[A-Za-z])\b"
)

QUANTITY_RE = re.compile(
    r"(?:(?:about|over|approx\.?|~|≈)\s+)?(?:[£₹$]\s*)?\d+(?:,\d{2,3})*(?:\.\d+)?\s*(?:billion|million|bn|km|kg·m/s²|kg|g|m/s²|m/s|N|°C|%|jobs|years|visitors)\b"
    r"|\b(?:about|over)\s+\d+(?:,\d{2,3})*(?:\.\d+)?\b",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(r"\b\d+(?:,\d{2,3})+(?:\.\d+)?\b|\b\d+\.\d+\b")

RANK_RE = re.compile(
    r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|2nd|7th|11th)[-\s]+(?:largest|most\s+populous|biggest)\b"
    r"|\b(?:Second\s+largest|eleventh-largest)\b",
    re.IGNORECASE,
)

TITLE_EPITHET_RE = re.compile(
    r"\b(?:Father|Mother|Pioneer|Architect|Founder)\s+of\s+(?:the\s+)?[A-Z][A-Za-z'’]+(?:\s+(?:of|and|the|[A-Z][A-Za-z'’]+))*",
)

ORG_HEAD_WORDS = (
    "College", "Samaj", "Sabha", "Mill", "Hotel", "Committee",
    "Assembly", "Parliament", "Bank", "Centre", "Center", "Museum",
    "Hippodrome", "Steel", "Power", "University", "Institute", "School",
)

EVENT_HEAD_WORDS = (
    "Revolution", "Abolition", "Renaissance", "Movement", "Rebellion", "War",
)

DOC_HEAD_WORDS = (
    "Constitution", "Treaty", "Act", "Charter", "Declaration",
)

PERSON_PREFIX_RE = re.compile(
    r"\b(?:Dr\.|Mahatma|Raja|Sir|Lord|Smt\.)\s+[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3}\b"
)

PLACE_PREFIX_RE = re.compile(r"\bRiver\s+[A-Z][a-zA-Z]+\b")

UNIT_RE = re.compile(r"\b(?:kg·m/s²|m/s²|m/s|kilograms|grams|kg|g|N)\b")


def extract_entities(text: str, bold: List[str] | None = None) -> List[Dict[str, str]]:
    """Recognise entities in text with general patterns.
    Dates, numbers, quantities, and formulas are always kept as single atomic units.
    """
    if not text:
        return []
    bold = bold or []
    found: List[Dict[str, Any]] = []
    occupied: List[tuple[int, int]] = []

    def is_free(start: int, end: int) -> bool:
        for s, e in occupied:
            if not (end <= s or start >= e):
                return False
        return True

    def add_span(start: int, end: int, ent_type: str, surface: str | None = None) -> None:
        if is_free(start, end):
            occupied.append((start, end))
            found.append({
                "text": (surface if surface is not None else text[start:end]).strip(),
                "type": ent_type,
                "start": start,
                "end": end,
            })

    # 1. Formulas (atomic)
    for m in FORMULA_RE.finditer(text):
        add_span(m.start(), m.end(), "FORMULA")

    # 2. Dates (lifespans, full dates, centuries, decades, years - atomic)
    for regex in (LIFESPAN_RE, FULL_DATE_RE, CENTURY_RE, DECADE_RE, YEAR_RE):
        for m in regex.finditer(text):
            add_span(m.start(), m.end(), "DATE")

    # 3. Titles / epithets
    for m in TITLE_EPITHET_RE.finditer(text):
        add_span(m.start(), m.end(), "TITLE")

    # 4. Quantities, ranks, numbers (atomic)
    for m in QUANTITY_RE.finditer(text):
        add_span(m.start(), m.end(), "QUANTITY")
    for m in RANK_RE.finditer(text):
        add_span(m.start(), m.end(), "NUMBER")
    for m in NUMBER_RE.finditer(text):
        add_span(m.start(), m.end(), "NUMBER")

    # 5. Persons with honorific prefixes
    for m in PERSON_PREFIX_RE.finditer(text):
        add_span(m.start(), m.end(), "PERSON")

    # 6. Documents
    doc_pattern = re.compile(r"\b(?:[A-Z][A-Za-z'’]+\s+){0,3}(?:" + "|".join(DOC_HEAD_WORDS) + r")\b")
    for m in doc_pattern.finditer(text):
        add_span(m.start(), m.end(), "DOCUMENT")

    # 7. Events
    event_pattern = re.compile(
        r"\b(?:Abolition\s+of\s+[A-Z][A-Za-z]+|(?:[A-Z][A-Za-z'’]+\s+){1,2}(?:Revolution|Renaissance|Movement))\b"
    )
    for m in event_pattern.finditer(text):
        add_span(m.start(), m.end(), "EVENT")

    # 8. Places
    for m in PLACE_PREFIX_RE.finditer(text):
        add_span(m.start(), m.end(), "PLACE")

    # 9. Organisations
    org_pattern = re.compile(
        r"\b(?:[A-Z][A-Za-z'’&.-]+\s+){0,4}(?:" + "|".join(ORG_HEAD_WORDS) + r")(?:\s+of\s+[A-Z][A-Za-z]+)?\b"
    )
    for m in org_pattern.finditer(text):
        add_span(m.start(), m.end(), "ORGANISATION")

    # 10. Standalone units
    for m in UNIT_RE.finditer(text):
        add_span(m.start(), m.end(), "QUANTITY")

    # 11. Bold terms
    for b in bold:
        b_clean = b.strip()
        if not b_clean:
            continue
        idx = text.find(b_clean)
        if idx != -1:
            add_span(idx, idx + len(b_clean), "TERM", b_clean)

    found.sort(key=lambda x: x["start"])
    return [{"text": f["text"], "type": f["type"]} for f in found]


def classify_answer_entity(answer: str, relation: str = "", bold: List[str] | None = None) -> Dict[str, str]:
    """Classify a candidate answer string into an entity type and output category."""
    ans = answer.strip()
    if FORMULA_RE.fullmatch(ans) or ("=" in ans and any(ch.isalpha() for ch in ans)):
        return {"type": "FORMULA", "category": "formula"}
    if (
        LIFESPAN_RE.fullmatch(ans)
        or FULL_DATE_RE.fullmatch(ans)
        or CENTURY_RE.fullmatch(ans)
        or DECADE_RE.fullmatch(ans)
        or YEAR_RE.fullmatch(ans)
    ):
        return {"type": "DATE", "category": "date"}
    if relation in ("UNIT_OF", "CONVERT_TO") or UNIT_RE.fullmatch(ans):
        return {"type": "QUANTITY", "category": "quantity"}
    if relation in ("POPULATION", "VISITORS_PER_YEAR", "BANKING_FOR", "SUPPORTS", "WORTH", "ACCELERATION_CALC", "ACCELERATION_TABLE", "EQUALS"):
        if QUANTITY_RE.fullmatch(ans):
            return {"type": "QUANTITY", "category": "number"}
        return {"type": "NUMBER", "category": "number"}
    if QUANTITY_RE.fullmatch(ans):
        return {"type": "QUANTITY", "category": "quantity"}
    if NUMBER_RE.fullmatch(ans) or RANK_RE.fullmatch(ans) or relation in ("RANK_IN_UK", "FINANCIAL_RANK"):
        return {"type": "NUMBER", "category": "number"}
    if ans.lower().startswith("to ") or relation == "PURPOSE":
        return {"type": "TERM", "category": "purpose"}
    if TITLE_EPITHET_RE.fullmatch(ans) or relation in ("IS_CALLED", "ALSO_CALLED", "REGARDED_AS_FIRST", "IS_UKS"):
        return {"type": "TITLE", "category": "title"}
    if relation in ("AT_HEART_OF", "CAMPAIGNED_FOR") or any(w in ans for w in EVENT_HEAD_WORDS):
        return {"type": "EVENT", "category": "event"}
    if relation in ("WORKED_ALONGSIDE", "PERSON") or PERSON_PREFIX_RE.fullmatch(ans):
        return {"type": "PERSON", "category": "person"}
    if (
        any(w in ans for w in ORG_HEAD_WORDS)
        or relation
        in (
            "FOUNDED",
            "OPENED",
            "CHAIRED",
            "GRADUATED_FROM",
            "SHIPYARD",
            "HOME_TO",
            "SEAT_OF",
            "CONVERTED_INTO",
            "ESTABLISHED",
            "LAID_FOUNDATIONS_FOR",
            "PART_OF",
            "PRECURSOR_TO",
            "INSPIRED",
        )
    ):
        return {"type": "ORGANISATION", "category": "organisation"}
    if (
        PLACE_PREFIX_RE.fullmatch(ans)
        or relation
        in (
            "CAPITAL_OF",
            "SITUATED_ON",
            "LOCATED_IN",
            "REGION",
            "RESIDENCE",
            "HEADQUARTERS_IN",
            "FINANCIAL_CENTRE_OF",
            "LARGEST_OUTSIDE",
            "REFORMER_IN",
            "ARCHITECTURE_INCLUDES",
        )
    ):
        return {"type": "PLACE", "category": "place"}
    return {"type": "TERM", "category": "term"}
