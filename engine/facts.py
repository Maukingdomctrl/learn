"""
Stage 1: facts.py
Split each fact source into independently testable clauses and resolve topic/context subjects.
Standard-library Python only. No hardcoded topic names.
"""
from __future__ import annotations
import re
from typing import Dict, List

TITLE_START_RE = re.compile(
    r"^(?:Father|Mother|Pioneer|Architect|Founder|Leader)\s+of\s+",
    re.IGNORECASE,
)


def parse_topic_header(topic_text: str) -> Dict[str, str]:
    """Extract clean subject name, optional lifespan, and optional title/capital/region from a topic header.
    Examples:
      'Jamsetji Nusserwanji Tata (1839–1904) – Father of Indian Industry'
      'Savitribai Phule (1831–1897) – Pioneer of Women's Education in Maharashtra'
      'LONDON – Capital of the United Kingdom & England'
      'BIRMINGHAM – West Midlands, England'
    """
    text = topic_text.strip()
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

    if left.isupper() and len(left) > 1:
        left = left.title()

    subtitle_kind = ""
    clean_subtitle = subtitle
    if subtitle:
        m_cap = re.match(r"^Capital\s+of\s+(?:the\s+)?(.+)$", subtitle, re.IGNORECASE)
        if m_cap:
            subtitle_kind = "CAPITAL_OF"
            clean_subtitle = m_cap.group(1).strip()
        elif TITLE_START_RE.match(subtitle):
            subtitle_kind = "IS_CALLED"
            # Strip trailing 'in <Place>' location qualifier so title is concise (e.g. "Pioneer of Women's Education")
            clean_subtitle = re.sub(r"\s+in\s+[A-Z][A-Za-z]+$", "", subtitle).strip()
        elif "," in subtitle:
            subtitle_kind = "REGION_HEADER"
            clean_subtitle = subtitle.split(",")[0].strip()
        else:
            subtitle_kind = "IS_CALLED"

    return {
        "subject": left,
        "lifespan": lifespan,
        "subtitle": clean_subtitle,
        "subtitle_kind": subtitle_kind,
    }


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
    s = subject.strip()
    # Strip honorifics
    s_clean = re.sub(r"^(?:Mahatma|Dr\.?|Raja|Sir|Smt\.?|The)\s+", "", s, flags=re.IGNORECASE).strip()
    # If all tokens are capitalized words/initials (a person name like 'Jamsetji Nusserwanji Tata' or 'B. R. Ambedkar'),
    # canonicalize to the surname (last token) so abbreviated table headers ('Jamsetji Tata', 'R. R. M. Roy') match.
    tokens = s_clean.split()
    if len(tokens) >= 2 and all(t[0].isupper() for t in tokens) and not any(
        w in s_clean.lower()
        for w in ("river", "college", "samaj", "sabha", "mill", "hotel", "committee", "assembly", "parliament", "bank", "centre", "museum", "hippodrome", "kingdom", "ireland", "midlands", "town", "sati", "revolution", "trial", "force", "mass", "law", "object", "book", "car", "satellite")
    ):
        return f"{tokens[0][0].lower()} {tokens[-1].lower()}"
    s_low = s_clean.lower()
    s_low = re.sub(r"[^a-z0-9]+", " ", s_low).strip()
    return s_low
