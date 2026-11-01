"""
Stage 1: facts.py
Split each fact source into independently testable clauses and resolve topic/context subjects.
Standard-library Python only. No sheet-specific words or topic names.
"""
from __future__ import annotations
import re
from typing import Dict, List, Any

TITLE_START_RE = re.compile(
    r"^(?:Father|Mother|Pioneer|Architect|Founder|Leader)\s+of\s+",
    re.IGNORECASE,
)

ROLE_SUBTITLE_RE = re.compile(
    r"^(?:(?:Lower|Upper)\s+House\s+of\s+.+|Head\s+of\s+(?:the\s+)?.+|Highest\s+court\s+of\s+.+)$",
    re.IGNORECASE,
)

HONORIFIC_PREFIXES = (
    "dr", "mr", "mrs", "ms", "sir", "lord", "lady",
    "queen", "king", "prince", "princess", "general",
)

NON_PERSON_ROLE_WORDS = (
    "river", "college", "committee", "assembly", "parliament", "bank",
    "centre", "center", "museum", "university", "institute", "school",
    "court", "house", "city", "town", "state", "country", "region",
    "company", "party", "council", "union", "government", "law", "act",
    "treaty", "proclamation", "declaration", "charter", "movement",
    "rebellion", "revolt", "uprising", "revolution", "war", "dynasty",
    "empire", "crown", "army", "office", "officer", "president",
    "speaker", "judge", "member", "people", "citizens", "equation",
    "equations", "formula", "formulas", "fraction", "fractions",
    "power", "powers", "number", "numbers", "comparison",
)

GENERIC_SECTION_TOPICS = {
    "causes", "outbreak", "key leaders", "leaders", "consequences",
    "effects", "measures", "precautions", "summary", "overview",
    "introduction", "comparison", "worked calculations",
    "units and conversions", "free-body reasoning", "model",
}


def parse_topic_header(topic_text: str) -> Dict[str, str]:
    """Extract clean subject name, optional lifespan, and optional title/capital/region from a topic header."""
    text = (topic_text or "").strip()
    if not text:
        return {"subject": "", "lifespan": "", "subtitle": "", "subtitle_kind": ""}

    parts = re.split(r"\s+[–—-]\s+", text, maxsplit=1)
    left = parts[0].strip()
    subtitle = parts[1].strip() if len(parts) > 1 else ""

    lifespan = ""
    m_life = re.search(r"\((\d{4}[–-]\d{4})\)", left)
    if m_life:
        lifespan = m_life.group(1)
        left = (left[: m_life.start()] + left[m_life.end() :]).strip()

    left = re.sub(r"^\d+[.)]\s*", "", left).strip()
    if left.isupper() and len(left) > 1:
        left = left.title()

    subtitle_kind = ""
    clean_subtitle = subtitle
    if subtitle:
        m_cap = re.match(r"^Capital\s+of\s+(?:the\s+)?(.+)$", subtitle, re.IGNORECASE)
        if m_cap:
            subtitle_kind = "CAPITAL_OF"
            clean_subtitle = m_cap.group(1).strip()
        elif TITLE_START_RE.match(subtitle) or lifespan:
            subtitle_kind = "IS_CALLED"
            clean_subtitle = re.sub(r"\s+in\s+[A-Z][A-Za-z]+$", "", subtitle).strip()
        elif ROLE_SUBTITLE_RE.match(subtitle):
            subtitle_kind = "ROLE_DEFINITION"
            clean_subtitle = subtitle.strip()
        elif "," in subtitle:
            subtitle_kind = "REGION_HEADER"
            clean_subtitle = subtitle.split(",")[0].strip()
        else:
            subtitle_kind = "TOPIC_GLOSS"

    return {
        "subject": left,
        "lifespan": lifespan,
        "subtitle": clean_subtitle,
        "subtitle_kind": subtitle_kind,
    }


def resolve_sheet_title(reader_json: Dict[str, Any]) -> str:
    """Return a clean main title for the sheet from its first title item."""
    for it in reader_json.get("items", []):
        if it.get("kind") == "title":
            t = (it.get("text") or "").strip()
            if not t:
                continue
            # If title has 'FULL CARD <N> — <Topic>', take the right side
            if "—" in t:
                t = t.split("—", 1)[1].strip()
            if t.isupper() and len(t) > 1:
                t = t.title()
            return t
    return ""


def split_into_clauses(text: str) -> List[str]:
    """Split a point's text at sentence boundaries and semicolons when each side holds a fact."""
    if not text:
        return []
    semi_parts = [p.strip() for p in text.split(";") if p.strip()]
    clauses: List[str] = []
    for part in semi_parts:
        sents = re.split(r"(?<!\bDr)(?<!\bMr)(?<!\bSt)(?<!\b[A-Z])\.\s+(?=[A-Z0-9])", part)
        for s in sents:
            s_clean = s.strip().rstrip(".")
            if s_clean:
                clauses.append(s_clean)
    return clauses


def canonicalize_subject(subject: str) -> str:
    """Normalize subject string for deduplication while preserving distinct subjects."""
    s = (subject or "").strip()
    prefix_pat = r"^(?:" + "|".join(HONORIFIC_PREFIXES) + r"|the|a|an)\.?\s+"
    s_clean = re.sub(prefix_pat, "", s, flags=re.IGNORECASE).strip()
    tokens = s_clean.split()
    lower_tokens = [re.sub(r"[^a-z0-9]", "", t.lower()) for t in tokens]
    # Person-name heuristic: 2–4 capitalized words/initials with no prepositions or non-person role words
    if (
        2 <= len(tokens) <= 4
        and all(t[0].isupper() for t in tokens if t)
        and not any(lt in ("of", "in", "on", "for", "and", "to", "the", "at", "by") for lt in lower_tokens)
        and not any(w in lower_tokens for w in NON_PERSON_ROLE_WORDS)
    ):
        return f"{lower_tokens[0][0]} {lower_tokens[-1]}"
    s_low = s_clean.lower()
    s_low = re.sub(r"[^a-z0-9]+", " ", s_low).strip()
    return s_low
