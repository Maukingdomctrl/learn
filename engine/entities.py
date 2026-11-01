"""
Stage 2: entities.py
Recognise PERSON, PLACE, ORGANISATION, EVENT, DOCUMENT, TITLE, DATE, NUMBER,
QUANTITY, FORMULA, DEFINITION, CAUSE, STEP, TERM using general structural patterns
and the Expression Library (engine/expressions.py, Families A–L).
Every date, number, quantity, or formula span is ONE atomic unit, never split.
"""
from __future__ import annotations

import re
from typing import Dict, List, Any

from .expressions import (
    FAMILIES,
    FAMILY_A,
    FAMILY_B,
    FAMILY_C,
    FAMILY_D,
    FAMILY_E,
    FAMILY_F,
    FAMILY_G,
    FAMILY_H,
    FAMILY_I,
    FAMILY_J,
    FAMILY_K,
    FAMILY_L,
    SUPERLATIVE_CHECK_NOTE,
    check_cut_in_half_span,
    find_all_expressions,
    find_atomic_spans,
)

MONTH_NAMES = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

RANK_WORDS = (
    "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
    "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th",
)

TITLE_HEAD_WORDS = (
    "Father", "Mother", "Pioneer", "Architect", "Founder",
    "Leader", "Head", "Guardian", "Commander",
)

ORG_HEAD_WORDS = (
    "College", "Committee", "Assembly", "Parliament", "Bank",
    "Centre", "Center", "Museum", "University", "Institute",
    "School", "Court", "Company", "Council",
)

EVENT_HEAD_WORDS = (
    "Revolution", "Movement", "Rebellion", "Revolt", "Uprising", "War",
)

DOC_HEAD_WORDS = (
    "Constitution", "Treaty", "Act", "Charter", "Declaration", "Proclamation",
)

UNIT_WORDS = (
    "billion", "million", "bn", "lakh", "crore", "km", "m", "cm", "mm",
    "kg·m/s²", "kg", "kilograms", "kilogram", "g", "grams", "gram", "mg",
    "mL", "L", "m/s²", "m/s", "km/h", "N", "°C", "°F", "%",
    "years", "year", "months", "month", "days", "day",
    "hours", "hour", "minutes", "minute", "seconds", "second",
)

LIFESPAN_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-2][0-9])[–-](?:1[0-9]{3}|20[0-2][0-9])\b")
FULL_DATE_RE = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:" + "|".join(MONTH_NAMES) + r"),?\s+(?:1[0-9]{3}|20[0-2][0-9])\b"
)
MONTH_YEAR_RE = re.compile(
    r"\b(?:" + "|".join(MONTH_NAMES) + r")\s+(?:1[0-9]{3}|20[0-2][0-9])\b"
)
CENTURY_RE = re.compile(r"\b(?:early\s+|late\s+|mid-)?\d{1,2}(?:st|nd|rd|th)\s+century\b", re.IGNORECASE)
DECADE_RE = re.compile(r"\b(?:early\s+|late\s+|mid-)?(?:1[0-9]{3}|20[0-2][0-9])s\b")
YEAR_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-2][0-9])\b")

FORMULA_RE = re.compile(
    r"\b(?:1\s+[A-Za-z]+\s*=\s*\d+(?:\.\d+)?\s*[A-Za-z·/²³0-9-]+|"
    r"[A-Za-z]\s*=\s*[A-Za-z0-9()½¾²³π√\s×÷/+-]+|"
    r"\d*[a-z]\s*[+-]\s*\d+\s*=\s*\d+|"
    r"\d*(?:[A-Z][a-z]?(?:[₀-₉]+|\d+)*)*[A-Z][a-z]?(?:[₀-₉]+|\d+)(?:[A-Z][a-z]?(?:[₀-₉]+|\d+)*)*)\b"
)

QUANTITY_RE = re.compile(
    r"(?:(?:about|over|approx\.?|~|≈)\s+)?(?:[£₹$]\s*)?(?:\d{1,2}(?:,\d{2})+,\d{3}|\d+(?:,\d{3})*)(?:\.\d+)?\s*(?:"
    + "|".join(re.escape(u) for u in UNIT_WORDS)
    + r")\b"
    r"|(?:[£₹$]\s*)(?:\d{1,2}(?:,\d{2})+,\d{3}|\d+(?:,\d{3})*)(?:\.\d+)?(?:\s*(?:billion|million|bn|lakh|crore))?\b"
    r"|\b(?:about|over)\s+(?:\d{1,2}(?:,\d{2})+,\d{3}|\d+(?:,\d{3})*)(?:\.\d+)?\b",
    re.IGNORECASE,
)

NUMBER_RE = re.compile(
    r"\b\d{1,2}(?:,\d{2})+,\d{3}(?:\.\d+)?\b|\b\d+(?:,\d{3})+(?:\.\d+)?\b|\b\d+\.\d+%?\b|\b\d+/\d+\b|\b[½¾¼⅓⅔⅛⅜⅝⅞]\b|\b\d+\b"
)

RANK_RE = re.compile(
    r"\b(?:" + "|".join(RANK_WORDS) + r")[-\s]+(?:largest|most\s+populous|biggest)\b",
    re.IGNORECASE,
)

TITLE_EPITHET_RE = re.compile(
    r"\b(?:" + "|".join(TITLE_HEAD_WORDS) + r")\s+of\s+(?:the\s+)?[A-Z][A-Za-z'’]+(?:\s+(?:of|and|the|[A-Z][A-Za-z'’]+))*",
)

PERSON_PREFIX_RE = re.compile(
    r"\b(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|Lady|Queen|King)\s+[A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3}\b"
)

PLACE_PREFIX_RE = re.compile(r"\bRiver\s+[A-Z][a-zA-Z]+\b")

UNIT_RE = re.compile(r"\b(?:kg·m/s²|m/s²|m/s|km/h|kilograms|grams|kg|g|mL|L|N|km|cm|mm|°C)\b")


def extract_entities(text: str, bold: List[str] | None = None) -> List[Dict[str, str]]:
    """Recognise entities in text using general patterns and the Expression Library (Families A–I).
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

    # 1. Formulas & Chemical formulas (atomic)
    for m in FORMULA_RE.finditer(text):
        add_span(m.start(), m.end(), "FORMULA")
    for m_d in FAMILY_D.find(text):
        if m_d["type"] in ("chemical_formula", "chemical_equation", "state_symbol"):
            s_d, e_d = m_d["span"]
            add_span(s_d, e_d, "FORMULA", m_d["text"])

    # 2. Dates (lifespans, full dates, month+year, centuries, decades, years, eras - atomic)
    for regex in (LIFESPAN_RE, FULL_DATE_RE, MONTH_YEAR_RE, CENTURY_RE, DECADE_RE):
        for m in regex.finditer(text):
            add_span(m.start(), m.end(), "DATE")
    for m_a in FAMILY_A.find(text):
        if m_a["type"] in ("full_date", "month_year", "day_month", "year_range", "century", "decade", "era", "era_marker", "indian_calendar"):
            s_a, e_a = m_a["span"]
            add_span(s_a, e_a, "DATE", m_a["text"])
    for m in YEAR_RE.finditer(text):
        add_span(m.start(), m.end(), "DATE")

    # 3. Titles / epithets
    for m in TITLE_EPITHET_RE.finditer(text):
        add_span(m.start(), m.end(), "TITLE")
    for m_e in FAMILY_E.find(text):
        if m_e["type"] == "title_epithet":
            s_e, e_e = m_e["span"]
            add_span(s_e, e_e, "TITLE", m_e["text"])

    # 4. Quantities, measurements, ranks, numbers (atomic - never split comma-formatted numbers or number+unit)
    for m in QUANTITY_RE.finditer(text):
        add_span(m.start(), m.end(), "QUANTITY")
    for m_c in FAMILY_C.find(text):
        s_c, e_c = m_c["span"]
        add_span(s_c, e_c, "QUANTITY", m_c["text"])
    for m in RANK_RE.finditer(text):
        add_span(m.start(), m.end(), "NUMBER")
    for m in NUMBER_RE.finditer(text):
        add_span(m.start(), m.end(), "NUMBER")

    # 5. Persons with honorific prefixes
    for m in PERSON_PREFIX_RE.finditer(text):
        add_span(m.start(), m.end(), "PERSON")

    # 6. Documents
    doc_pattern = re.compile(
        r"\b(?:[A-Z][A-Za-z'’]+\s+){0,4}(?:" + "|".join(DOC_HEAD_WORDS) + r")(?:\s+of\s+\d{4}|,\s*\d{4})?\b"
    )
    for m in doc_pattern.finditer(text):
        add_span(m.start(), m.end(), "DOCUMENT")

    # 7. Events
    event_pattern = re.compile(
        r"\b(?:[A-Z][A-Za-z'’]+\s+){1,2}(?:" + "|".join(EVENT_HEAD_WORDS) + r")\b"
    )
    for m in event_pattern.finditer(text):
        add_span(m.start(), m.end(), "EVENT")

    # 8. Places (rivers and location phrases from Family I)
    for m in PLACE_PREFIX_RE.finditer(text):
        add_span(m.start(), m.end(), "PLACE")
    for m_i in FAMILY_I.find(text):
        s_i, e_i = m_i["span"]
        add_span(s_i, e_i, "PLACE", m_i["text"])

    # 9. Organisations
    org_pattern = re.compile(
        r"\b(?:[A-Z][A-Za-z'’&.-]+\s+){0,4}(?:" + "|".join(ORG_HEAD_WORDS) + r")(?:\s+of\s+[A-Z][A-Za-z]+)?\b"
    )
    for m in org_pattern.finditer(text):
        add_span(m.start(), m.end(), "ORGANISATION")

    # 10. Definitions, Causes, Steps from Families F, G, H
    for m_f in FAMILY_F.find(text):
        s_f, e_f = m_f["span"]
        add_span(s_f, e_f, "DEFINITION", m_f["text"])
    for m_g in FAMILY_G.find(text):
        s_g, e_g = m_g["span"]
        add_span(s_g, e_g, "CAUSE", m_g["text"])
    for m_h in FAMILY_H.find(text):
        s_h, e_h = m_h["span"]
        add_span(s_h, e_h, "STEP", m_h["text"])

    # 11. Standalone units
    for m in UNIT_RE.finditer(text):
        add_span(m.start(), m.end(), "QUANTITY")

    # 12. Bold terms
    for b in bold:
        b_clean = b.strip()
        if not b_clean:
            continue
        idx = text.find(b_clean)
        if idx != -1:
            add_span(idx, idx + len(b_clean), "TERM", b_clean)

    found.sort(key=lambda x: x["start"])
    return [{"text": f["text"], "type": f["type"]} for f in found]


def find_item_spans(item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Step 2: In any point/summary/table item, find all date, number, quantity, formula,
    name/title, definition, cause, step and place spans; each span is ONE atomic unit.
    """
    kind = item.get("kind", "")
    spans: List[Dict[str, Any]] = []
    if kind in ("point", "summary", "topic"):
        txt = (item.get("text") or "").strip()
        if txt:
            spans.extend(find_all_expressions(txt))
    elif kind == "table":
        table = item.get("table") or {}
        for row in table.get("rows", []):
            for cell in row:
                cell_str = str(cell).strip()
                if cell_str:
                    spans.extend(find_all_expressions(cell_str))
    return spans


def classify_answer_entity(answer: str, relation: str = "", bold: List[str] | None = None) -> Dict[str, str]:
    """Classify a candidate answer string into an entity type and output category."""
    ans = answer.strip()
    if (
        FORMULA_RE.fullmatch(ans)
        or relation in ("FORMULA", "DEFINITION_FORMULA", "EQUATION_STEP")
        or ("=" in ans and any(ch.isalpha() for ch in ans))
        or ("÷" in ans or "×" in ans or "→" in ans)
    ):
        return {"type": "FORMULA", "category": "formula"}
    if (
        LIFESPAN_RE.fullmatch(ans)
        or FULL_DATE_RE.fullmatch(ans)
        or MONTH_YEAR_RE.fullmatch(ans)
        or CENTURY_RE.fullmatch(ans)
        or DECADE_RE.fullmatch(ans)
        or YEAR_RE.fullmatch(ans)
        or relation
        in (
            "DATE", "YEAR", "FOUNDED_IN", "OPENED_ON", "GRADUATED_IN",
            "MADE_CITY_IN", "PROCLAIMED_CAPITAL_IN", "STARTED_IN",
            "PROMINENCE_IN", "SMALL_TOWN_UNTIL", "RECAPTURED_IN", "EVENT_ON_DATE",
        )
    ):
        return {"type": "DATE", "category": "date"}
    if relation in ("UNIT_OF", "CONVERT_TO") or UNIT_RE.fullmatch(ans):
        return {"type": "QUANTITY", "category": "quantity"}
    if relation in (
        "POPULATION", "VISITORS_PER_YEAR", "BANKING_FOR", "SUPPORTS", "WORTH",
        "ACCELERATION_CALC", "ACCELERATION_TABLE", "EQUALS", "MATH_VALUE",
        "RETIRE_AGE", "MIN_AGE", "TERM_LENGTH", "MEM_TERM_LENGTH",
    ):
        if QUANTITY_RE.fullmatch(ans):
            return {"type": "QUANTITY", "category": "quantity" if relation in ("MIN_AGE", "TERM_LENGTH", "MEM_TERM_LENGTH") else "number"}
        return {"type": "NUMBER", "category": "number"}
    if QUANTITY_RE.fullmatch(ans):
        return {"type": "QUANTITY", "category": "quantity"}
    if NUMBER_RE.fullmatch(ans) or RANK_RE.fullmatch(ans) or relation in ("RANK", "FINANCIAL_RANK"):
        return {"type": "NUMBER", "category": "number"}
    if ans.lower().startswith("to ") or relation in ("PURPOSE", "CAUSE_REASON"):
        return {"type": "TERM", "category": "purpose"}
    if TITLE_EPITHET_RE.fullmatch(ans) or relation in (
        "IS_CALLED", "ALSO_CALLED", "REGARDED_AS_FIRST", "SUPERLATIVE_ROLE", "ROLE_TITLE", "BECAME_ROLE",
    ):
        return {"type": "TITLE", "category": "title"}
    if any(w in ans for w in DOC_HEAD_WORDS) or relation in ("DOCUMENT", "ENDED_RULE_BY_DOC"):
        return {"type": "DOCUMENT", "category": "document"}
    if relation in ("AT_HEART_OF", "CAMPAIGNED_FOR") or any(w in ans for w in EVENT_HEAD_WORDS):
        return {"type": "EVENT", "category": "event"}
    if (
        relation
        in (
            "WORKED_ALONGSIDE", "PERSON", "PRESIDING_OFFICER", "APPOINTED_BY",
            "LED_BY", "PROCLAIMED_AS", "ATTACKED_BY", "TITLE_TO_PERSON",
            "LED_AT_PLACE", "ACTOR_ON_DATE", "PASSIVE_AGENT",
        )
        or PERSON_PREFIX_RE.fullmatch(ans)
    ):
        return {"type": "PERSON", "category": "person"}
    if (
        any(w in ans for w in ORG_HEAD_WORDS)
        or relation
        in (
            "FOUNDED", "OPENED", "CHAIRED", "GRADUATED_FROM", "FACILITY_IN",
            "HOME_TO", "SEAT_OF", "CONVERTED_INTO", "ESTABLISHED",
            "LAID_FOUNDATIONS_FOR", "PART_OF", "PRECURSOR_TO", "INSPIRED",
            "ELECTED_BY", "ENDED_RULE_OF",
        )
    ):
        return {"type": "ORGANISATION", "category": "organisation"}
    if (
        PLACE_PREFIX_RE.fullmatch(ans)
        or relation
        in (
            "CAPITAL_OF", "SITUATED_ON", "LOCATED_IN", "REGION", "RESIDENCE",
            "HEADQUARTERS_IN", "FINANCIAL_CENTRE_OF", "LARGEST_OUTSIDE",
            "REFORMER_IN", "ARCHITECTURE_INCLUDES", "PLACE", "LED_WHERE",
        )
    ):
        return {"type": "PLACE", "category": "place"}
    return {"type": "TERM", "category": "term"}
