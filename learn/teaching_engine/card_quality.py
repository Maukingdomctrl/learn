"""No-AI, rule-based 7-criterion card quality checker and Key Facts card writer for the Teaching Engine.

Scores each candidate card 1–5 on seven rule-based criteria:
1. grounded: answer appears word-for-word on the sheet
2. short_answer: a word, name, year, number, or short term (<= 5 words)
3. clear_question: no template slot filled with a verb/sentence fragment or generic boilerplate
   (e.g. "Explain Indian Industry and its main features.", "Explain FULL CARD and its main features."),
   no cut-off proper nouns (e.g. "Man Planning Commission"), ends with '?' or '___'
4. names_subject: the clue identifies who/what it is about without containing the answer
5. not_furniture: answer/clue not taken from practice Q&A, memory tips,
   source credits like "(Britannica)", card/page labels ("FULL CARD"), or headers/footers
6. not_table_soup: answer/clue is not a run of several table cells
7. distinct: no near-duplicate of another card in the same case file
"""

from __future__ import annotations

import re
from typing import Any, Callable

CRITERIA: tuple[str, ...] = (
    "grounded",
    "short_answer",
    "clear_question",
    "names_subject",
    "not_furniture",
    "not_table_soup",
    "distinct",
)

MAX_ANSWER_WORDS = 5
MAX_ANSWER_CHARS = 48
DEFAULT_MIN_CRITERION_SCORE = 4
DEFAULT_MIN_AVERAGE_SCORE = 4.2

# Leading past/present verbs or participles that indicate a predicate fragment
# was stuffed into a noun-phrase template slot (e.g. "Explain Graduated from ...").
_FRAGMENT_START_VERBS = frozenset(
    {
        "graduated",
        "studied",
        "born",
        "died",
        "served",
        "worked",
        "founded",
        "established",
        "appointed",
        "elected",
        "became",
        "joined",
        "led",
        "wrote",
        "authored",
        "published",
        "built",
        "constructed",
        "designed",
        "discovered",
        "invented",
        "received",
        "awarded",
        "won",
        "moved",
        "returned",
        "married",
        "helped",
        "organized",
        "organised",
        "campaigned",
        "fought",
        "defeated",
        "ruled",
        "reigned",
        "succeeded",
        "attended",
        "completed",
        "earned",
        "obtained",
        "held",
        "headed",
        "chaired",
        "presided",
        "known",
        "famous",
        "noted",
        "remembered",
        "located",
        "situated",
        "based",
        "includes",
        "including",
        "contains",
        "containing",
        "consists",
        "consisting",
        "provides",
        "providing",
        "ensures",
        "ensuring",
        "leads",
        "leading",
        "caused",
        "causing",
        "resulted",
        "resulting",
        "offered",
        "went",
    }
)

# Dangling trailing function words in a filled template slot
_DANGLING_SLOT_ENDINGS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "with",
        "by",
        "as",
        "into",
        "and",
        "or",
        "but",
        "who",
        "which",
        "that",
        "whose",
        "where",
        "when",
        "while",
        "was",
        "were",
        "is",
        "are",
        "had",
        "has",
        "have",
        "been",
    }
)

# Common singular/broken prefix fragments before an institutional proper noun
# where a table border or line wrap sliced off a word (e.g. "Man Planning Commission"
# from "... Chair-man | Planning Commission").
_CUTOFF_PROPER_PREFIX_RE = re.compile(
    r"\b(?:Man|Men|Tion|Sion|Ment|Ness|Ship|Ing|Ed|Er|Or|Al|Ic|Ive|Ous)\s+[A-Z][a-z]+\s+[A-Z][a-z]+"
)

# Generic offline boilerplate templates that must not be emitted in Key Facts mode
_TEMPLATE_SLOT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^Explain\s+(.+?)\s+and\s+its\s+main\s+features\.?$", re.IGNORECASE),
    re.compile(r"^Explain\s+the\s+concept\s+and\s+significance\s+of\s+(.+?)\.?$", re.IGNORECASE),
    re.compile(
        r"^What\s+is\s+meant\s+by\s+(.+?),\s+and\s+what\s+are\s+its\s+key\s+characteristics\??$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^What\s+(?:reason|cause)(?:,\s*reason,?\s*or\s+mechanism|\s+or\s+cause)?\s+is\s+explained\s+regarding\s+(.+?)(?:,\s+and\s+what\s+is\s+its\s+(?:result|effect))?\??$",
        re.IGNORECASE,
    ),
    re.compile(r"^What\s+is\s+the\s+main\s+difference\s+explained\s+regarding\s+(.+?)\??$", re.IGNORECASE),
    re.compile(r"^How\s+is\s+(.+?)\s+used\s+or\s+applied\??$", re.IGNORECASE),
    re.compile(
        r"^What\s+is\s+the\s+chronological\s+order\s+of\s+events\s+or\s+steps\s+described\s+for\s+(.+?)\??$",
        re.IGNORECASE,
    ),
)

# Sheet furniture patterns: practice Q&A, memory tips, source attributions, card/page labels, headers/footers
_FURNITURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|\b)(?:Q\.?\s*\d*[:.)]|Question\s*\d*[:.)]|Ans(?:wer)?\s*\d*[:.)])\s+", re.IGNORECASE),
    re.compile(
        r"(?:^|\b)(?:Memory\s+tip|Quick\s+tip|Study\s+tip|Exam\s+tip|Mnemonic|Remember\s+this|Remember\s+trick|Fun\s+fact|Did\s+you\s+know)\s*[:\-–]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\((?:Source\s*:?\s*)?(?:Britannica|Wikipedia|Encyclop(?:ae|e)dia\s+Britannica|NCERT|ICSE|CBSE|PTI|Reuters|AP|Wikimedia[^)]*|Courtesy[^)]*)\)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:Source|Courtesy|Photo\s+credit|Image\s+credit)\s*:\s*[A-Z]", re.IGNORECASE),
    re.compile(
        r"(?:^|\b)(?:FULL\s+CARD|HALF\s+CARD|CARD\s+#?\d+|CASE\s+FILE\s*#?\d*|Page\s+\d+(?:\s+of\s+\d+)?|All\s+rights\s+reserved|Not\s+to\s+be\s+republished|Reprint\s+20\d{2}|Practice\s+Questions|Check\s+Your\s+Progress|Exercises?\s+for\s+Practice)\b",
        re.IGNORECASE,
    ),
)

_INLINE_SOURCE_CREDIT_RE = re.compile(
    r"\s*\((?:Source\s*:?\s*)?(?:Britannica|Wikipedia|Encyclop(?:ae|e)dia\s+Britannica|NCERT|ICSE|CBSE|PTI|Reuters|AP|Wikimedia[^)]*|Courtesy[^)]*)\)\.?",
    re.IGNORECASE,
)

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "with",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "when",
        "where",
        "why",
        "how",
        "explain",
        "define",
        "name",
        "state",
        "identify",
        "describe",
        "meant",
        "key",
        "main",
        "features",
        "characteristics",
        "regarding",
        "explained",
        "reason",
        "cause",
        "result",
        "difference",
        "used",
        "applied",
        "this",
        "that",
        "these",
        "those",
        "its",
        "their",
        "his",
        "her",
        "and",
        "or",
    }
)


def _get_field(obj: Any, *names: str, default: str = "") -> str:
    """Read a string field from either a dict or an object with attributes."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        for name in names:
            val = obj.get(name)
            if val is not None and str(val).strip():
                return str(val).strip()
        return default
    for name in names:
        val = getattr(obj, name, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def _get_sheet_text(sheet: Any) -> str:
    """Extract full plain text from a sheet (str, dict, or Sheet object)."""
    if sheet is None:
        return ""
    if isinstance(sheet, str):
        return sheet
    if isinstance(sheet, dict):
        if "text" in sheet and isinstance(sheet["text"], str):
            return sheet["text"]
        if "lines" in sheet and isinstance(sheet["lines"], list):
            return "\n".join(
                _get_field(ln, "text", "raw", "content") if not isinstance(ln, str) else ln
                for ln in sheet["lines"]
            )
        if "pages" in sheet and isinstance(sheet["pages"], list):
            return "\n".join(
                _get_field(pg, "text", "raw_text") if not isinstance(pg, str) else pg
                for pg in sheet["pages"]
            )
    for attr in ("text", "raw_text", "content"):
        val = getattr(sheet, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    lines = getattr(sheet, "lines", None)
    if isinstance(lines, list):
        return "\n".join(
            _get_field(ln, "text", "raw", "content") if not isinstance(ln, str) else ln
            for ln in lines
        )
    return str(sheet)


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_clue(card: Any) -> str:
    return _get_field(card, "clue", "question", "prompt", "front", "stem")


def _extract_answer(card: Any) -> str:
    return _get_field(card, "answer", "expected_answer", "back", "target", "solution")


def _extract_evidence(card: Any) -> str:
    return _get_field(card, "source_line", "source_evidence", "line", "evidence", "context")


def _extract_subject(card: Any) -> str:
    return _get_field(card, "subject", "heading", "section", "entity", "topic", "title")


def _score_grounded(answer: str, sheet_text: str) -> tuple[int, list[str]]:
    """Criterion 1: answer appears word-for-word on the sheet."""
    reasons: list[str] = []
    if not answer:
        return 1, ["grounded: card has an empty answer"]
    if not sheet_text.strip():
        return 1, ["grounded: sheet text is empty"]

    ans_norm = _normalize_spaces(answer)
    sheet_norm = _normalize_spaces(sheet_text)

    # Check word-for-word presence (case-insensitive, respecting word boundaries on alphanumeric edges)
    escaped = re.escape(ans_norm)
    if ans_norm[0].isalnum():
        escaped = r"\b" + escaped
    if ans_norm[-1].isalnum():
        escaped = escaped + r"\b"

    if re.search(escaped, sheet_norm, flags=re.IGNORECASE):
        return 5, []

    if ans_norm.lower() in sheet_norm.lower():
        return 4, ["grounded: answer appears only as a substring inside another token on the sheet"]

    return 1, [f"grounded: answer {answer!r} does not appear word-for-word on the sheet"]


def _score_short_answer(answer: str) -> tuple[int, list[str]]:
    """Criterion 2: answer is a word, name, year, number, or short term (<= 5 words)."""
    reasons: list[str] = []
    if not answer:
        return 1, ["short_answer: answer is empty"]

    ans_clean = _normalize_spaces(answer)
    words = ans_clean.split()
    word_count = len(words)

    # Reject full sentences or multi-clause answers
    if any(p in ans_clean for p in (";", "?", "!")) or (
        ans_clean.endswith(".") and word_count > 3 and not re.match(r"^(?:[A-Z]\.\s*)+[A-Za-z]+$", ans_clean)
    ):
        reasons.append(f"short_answer: answer {ans_clean!r} is a full sentence or multi-clause statement")
        return 1, reasons

    if word_count > MAX_ANSWER_WORDS or len(ans_clean) > MAX_ANSWER_CHARS:
        reasons.append(
            f"short_answer: answer has {word_count} words ({len(ans_clean)} chars); limit is {MAX_ANSWER_WORDS} words"
        )
        return 1 if word_count > 8 else 2, reasons

    # Check if the answer contains a finite verb clause rather than a name/term/number/year
    lower_words = [w.strip(",.:;()'\"‘’“”").lower() for w in words]
    if word_count >= 3 and any(w in _FRAGMENT_START_VERBS or w in {"is", "was", "were", "are", "because"} for w in lower_words):
        reasons.append(f"short_answer: answer {ans_clean!r} contains a verb clause instead of a short term/name")
        return 2, reasons

    return 5, []


def _score_clear_question(clue: str) -> tuple[int, list[str]]:
    """Criterion 3: no template slot filled with a sentence/verb fragment or generic boilerplate, no cut-off proper nouns, ends properly."""
    reasons: list[str] = []
    if not clue or len(clue.strip()) < 8:
        return 1, ["clear_question: clue is empty or too short"]

    clue_clean = _normalize_spaces(clue)

    # Check for cut-off proper nouns like "Man Planning Commission"
    if _CUTOFF_PROPER_PREFIX_RE.search(clue_clean):
        reasons.append(f"clear_question: clue contains a cut-off proper noun fragment ({clue_clean!r})")
        return 1, reasons

    # Reject generic offline template stems ("Explain X and its main features.", "What reason or cause is explained regarding X...", etc.)
    for pat in _TEMPLATE_SLOT_PATTERNS:
        m = pat.match(clue_clean)
        if m:
            slot = m.group(1).strip(" ,.:;()'\"‘’“”")
            slot_words = [w.strip(",.:;()'\"‘’“”") for w in slot.split() if w.strip(",.:;()'\"‘’“”")]
            if not slot_words:
                reasons.append("clear_question: template slot is empty")
                return 1, reasons
            first_w = slot_words[0].lower()
            last_w = slot_words[-1].lower()
            if first_w in _FRAGMENT_START_VERBS:
                reasons.append(
                    f"clear_question: template slot {slot!r} starts with verb/participle {slot_words[0]!r}"
                )
                return 1, reasons
            if last_w in _DANGLING_SLOT_ENDINGS:
                reasons.append(f"clear_question: template slot {slot!r} ends with dangling word {slot_words[-1]!r}")
                return 1, reasons
            internal_verbs = {"graduated", "studied", "served", "worked", "founded", "was", "were", "is", "are", "had", "did", "went", "look"}
            if any(w.lower() in internal_verbs for w in slot_words):
                reasons.append(f"clear_question: template slot {slot!r} is a verb/sentence fragment")
                return 1, reasons
            if len(slot_words) >= 3 and all(w[0].isupper() for w in slot_words if w) and first_w in {"man", "men", "boy", "girl", "one", "two", "three"}:
                reasons.append(f"clear_question: template slot {slot!r} has a broken proper-noun prefix")
                return 1, reasons
            reasons.append(f"clear_question: clue uses generic boilerplate template ({clue_clean!r})")
            return 1, reasons

    # Also catch inline verb-phrase after "Explain " or "What is meant by " even without the suffix
    m_inline = re.match(
        r"^(?:Explain|Describe|Define|What\s+is\s+(?:meant\s+by)?)\s+([A-Za-z]+)\b",
        clue_clean,
        re.IGNORECASE,
    )
    if m_inline and m_inline.group(1).lower() in _FRAGMENT_START_VERBS:
        reasons.append(
            f"clear_question: clue starts slot with verb fragment {m_inline.group(1)!r} ({clue_clean!r})"
        )
        return 1, reasons

    # Check proper ending: question mark '?' or fill-in-the-blank '___'
    has_blank = "___" in clue_clean or "____" in clue_clean
    ends_valid = clue_clean.endswith("?") or (has_blank and clue_clean.endswith((".", "___", "____")))
    if not ends_valid:
        reasons.append(f"clear_question: clue {clue_clean!r} does not end with '?' or a valid blank")
        return 1, reasons

    # Catch double spaces/punctuation or broken mid-word hyphenation
    if re.search(r"[A-Za-z]-\s+[a-z]", clue_clean) or ".." in clue_clean.replace("...", ""):
        reasons.append("clear_question: clue contains broken hyphenation or malformed punctuation")
        return 2, reasons

    return 5, []


def _score_names_subject(clue: str, answer: str, subject_hint: str = "") -> tuple[int, list[str]]:
    """Criterion 4: the clue identifies who/what it is about without containing the answer."""
    reasons: list[str] = []
    if not clue:
        return 1, ["names_subject: clue is empty"]

    clue_norm = _normalize_spaces(clue)
    ans_norm = _normalize_spaces(answer)

    # 1. Clue must not leak the answer
    if ans_norm:
        escaped_ans = re.escape(ans_norm)
        if ans_norm[0].isalnum():
            escaped_ans = r"\b" + escaped_ans
        if ans_norm[-1].isalnum():
            escaped_ans = escaped_ans + r"\b"
        if re.search(escaped_ans, clue_norm, flags=re.IGNORECASE):
            reasons.append(f"names_subject: clue leaks the answer {ans_norm!r}")
            return 1, reasons

    # 2. Clue must identify a concrete subject (a proper noun, named entity, or >=2 specific content nouns)
    # and must not rely on a dangling pronoun ("He graduated from ___", "Why did she do this?")
    clue_without_first = re.sub(
        r"^(?:What|Which|Who|Whom|Whose|When|Where|Why|How|In|On|At|During|After|Before|From|To|By|For|Through|Into|Under|Name|Identify|State|Complete)\b\s*",
        "",
        clue_norm,
        flags=re.IGNORECASE,
    )
    has_proper_noun = bool(re.search(r"\b[A-Z][a-z]{2,}\b", clue_without_first))
    content_tokens = [
        w.lower()
        for w in re.findall(r"[A-Za-z]{3,}", clue_norm)
        if w.lower() not in _STOP_WORDS and w.lower() not in _FRAGMENT_START_VERBS
    ]

    # Reject dangling pronouns when no proper noun or subject is named in the clue
    has_dangling_pronoun = bool(
        re.search(r"\b(?:he|she|they|him|her|them|his|hers|their|it)\b", clue_norm, flags=re.IGNORECASE)
    )
    if has_dangling_pronoun and not has_proper_noun:
        reasons.append(f"names_subject: clue uses a pronoun without naming who/what it is about ({clue_norm!r})")
        return 1, reasons

    if subject_hint:
        subj_tokens = [
            w.lower() for w in re.findall(r"[A-Za-z]{3,}", subject_hint) if w.lower() not in _STOP_WORDS
        ]
        if (
            subj_tokens
            and ans_norm.lower() != subject_hint.strip().lower()
            and not any(t in clue_norm.lower() for t in subj_tokens)
            and not has_proper_noun
        ):
            reasons.append(
                f"names_subject: clue does not mention its subject {subject_hint!r} ({clue_norm!r})"
            )
            return 2, reasons

    if not has_proper_noun and len(content_tokens) < 2:
        reasons.append(f"names_subject: clue lacks a clear subject noun or entity ({clue_norm!r})")
        return 1, reasons

    return 5, []


def _score_not_furniture(clue: str, answer: str, evidence: str = "") -> tuple[int, list[str]]:
    """Criterion 5: answer/clue not taken from practice Q&A, memory tips, source credits, card/page labels, or headers/footers."""
    reasons: list[str] = []
    combined_parts = [("clue", clue), ("answer", answer), ("evidence", evidence)]

    for label, text in combined_parts:
        if not text:
            continue
        for pat in _FURNITURE_PATTERNS:
            if pat.search(text):
                reasons.append(f"not_furniture: {label} contains sheet furniture/Q&A/credit/tip ({text!r})")
                return 1, reasons

    # Also check if answer itself is a bare source credit or layout label
    if re.match(
        r"^\(?(?:Britannica|Wikipedia|NCERT|ICSE|CBSE|Source|Memory\s+Tip|FULL\s+CARD|HALF\s+CARD|CARD\s*\d*)\)?$",
        answer.strip(),
        re.IGNORECASE,
    ):
        reasons.append(f"not_furniture: answer {answer!r} is a source credit or layout label")
        return 1, reasons

    return 5, []


def _score_not_table_soup(clue: str, answer: str, evidence: str = "") -> tuple[int, list[str]]:
    """Criterion 6: answer/clue isn't a run of several table cells or jumbled column text."""
    reasons: list[str] = []

    for label, text in (("answer", answer), ("clue", clue), ("evidence", evidence)):
        if not text:
            continue
        if text.count("|") >= 2 or len(re.findall(r"\t+|\s{3,}", text)) >= 2:
            if label in ("answer", "clue"):
                reasons.append(f"not_table_soup: {label} contains raw multi-column table cells ({text!r})")
                return 1, reasons

    years_in_ans = re.findall(r"\b(?:1[5-9]\d{2}|20\d{2})\b", answer)
    if len(years_in_ans) >= 2 and not re.match(r"^\d{4}\s*[–\-—]\s*\d{2,4}$", answer.strip()):
        reasons.append(f"not_table_soup: answer {answer!r} concatenates multiple table years/cells")
        return 1, reasons

    ans_tokens = answer.split()
    if len(ans_tokens) >= 4 and sum(1 for t in ans_tokens if any(ch.isdigit() for ch in t)) >= 1 and sum(
        1 for t in ans_tokens if t[0].isupper()
    ) >= 2:
        reasons.append(f"not_table_soup: answer {answer!r} looks like a run of multiple table cells")
        return 1, reasons

    if answer.count(":") >= 1 and len(ans_tokens) >= 3:
        reasons.append(f"not_table_soup: answer {answer!r} contains key-value table/list formatting")
        return 1, reasons

    return 5, []


def _content_tokens(text: str) -> set[str]:
    return {
        w.lower()
        for w in re.findall(r"[A-Za-z0-9]{3,}", text)
        if w.lower() not in _STOP_WORDS
    }


def _score_distinct(card: Any, prior_cards: list[Any]) -> tuple[int, list[str]]:
    """Criterion 7: no near-duplicate of another card in the same case file."""
    if not prior_cards:
        return 5, []

    clue = _normalize_spaces(_extract_clue(card)).lower()
    answer = _normalize_spaces(_extract_answer(card)).lower()
    clue_tokens = _content_tokens(clue)

    for idx, other in enumerate(prior_cards):
        other_clue = _normalize_spaces(_extract_clue(other)).lower()
        other_answer = _normalize_spaces(_extract_answer(other)).lower()

        if clue and clue == other_clue:
            return 1, [f"distinct: exact duplicate clue of card #{idx + 1}"]

        other_tokens = _content_tokens(other_clue)
        if clue_tokens and other_tokens:
            overlap = len(clue_tokens & other_tokens) / max(1, min(len(clue_tokens), len(other_tokens)))
            if answer and answer == other_answer and overlap >= 0.5:
                return 1, [
                    f"distinct: same answer ({answer!r}) and overlapping clue ({overlap:.0%}) with card #{idx + 1}"
                ]
            if overlap >= 0.8:
                return 1, [f"distinct: clue has {overlap:.0%} token overlap with card #{idx + 1}"]

    return 5, []


def score_card(
    card: Any,
    sheet: Any,
    *,
    prior_cards: list[Any] | None = None,
) -> tuple[dict[str, int], list[str]]:
    """Score a card 1–5 on each of the 7 rule-based criteria and return (scores, reasons)."""
    clue = _extract_clue(card)
    answer = _extract_answer(card)
    evidence = _extract_evidence(card)
    subject_hint = _extract_subject(card)
    sheet_text = _get_sheet_text(sheet)

    scores: dict[str, int] = {}
    reasons: list[str] = []

    c1, r1 = _score_grounded(answer, sheet_text)
    scores["grounded"] = c1
    reasons.extend(r1)

    c2, r2 = _score_short_answer(answer)
    scores["short_answer"] = c2
    reasons.extend(r2)

    c3, r3 = _score_clear_question(clue)
    scores["clear_question"] = c3
    reasons.extend(r3)

    c4, r4 = _score_names_subject(clue, answer, subject_hint)
    scores["names_subject"] = c4
    reasons.extend(r4)

    c5, r5 = _score_not_furniture(clue, answer, evidence)
    scores["not_furniture"] = c5
    reasons.extend(r5)

    c6, r6 = _score_not_table_soup(clue, answer, evidence)
    scores["not_table_soup"] = c6
    reasons.extend(r6)

    c7, r7 = _score_distinct(card, prior_cards or [])
    scores["distinct"] = c7
    reasons.extend(r7)

    return scores, reasons


def is_card_acceptable(
    scores: dict[str, int],
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
) -> bool:
    """Return True if all 7 criteria meet the minimum threshold and average score."""
    if not scores:
        return False
    if any(v < min_criterion_score for v in scores.values()):
        return False
    avg = sum(scores.values()) / len(scores)
    return avg >= min_average_score


def is_sheet_furniture_or_heading(line: str) -> bool:
    """Return True if a sheet line is furniture (Q&A, memory tip, credit, card/page label) or a bare heading."""
    s = _normalize_spaces(line)
    if not s:
        return True
    for pat in _FURNITURE_PATTERNS:
        if pat.search(s):
            return True
    # Table header row or raw pipe-separated table row with no prose verb
    if s.count("|") >= 2 and re.match(
        r"^(?:Name|Person|Personality|Year|Date|Role|Institution|Contribution|Event|Category)\b",
        s,
        re.IGNORECASE,
    ):
        return True
    # Bare heading without a finite verb or colon definition (e.g. "Prominent Personalities of Mumbai", "Indian Industry", "Dadabhai Naoroji (1825–1917)")
    s_no_dates = re.sub(r"\(\s*\d{3,4}\s*[–\-—]\s*\d{2,4}\s*\)", "", s).strip()
    words = s_no_dates.split()
    has_verb = bool(
        re.search(
            r"\b(?:is|are|was|were|has|have|had|graduated|studied|born|died|served|worked|founded|established|appointed|elected|became|joined|led|wrote|authored|published|built|discovered|invented|chaired|presided|known|called|states|refers|occurs|dissociates|defied|marched|proclaimed|applied)\b",
            s_no_dates,
            re.IGNORECASE,
        )
    )
    if not has_verb and ":" not in s_no_dates and "|" not in s_no_dates and len(words) <= 7:
        return True
    return False


def _clean_subject_heading(heading: str) -> str:
    """Clean a section/person heading by stripping life-span dates and card/page prefixes."""
    h = _INLINE_SOURCE_CREDIT_RE.sub("", heading or "")
    h = re.sub(r"\b(?:FULL\s+CARD|HALF\s+CARD|CARD\s+#?\d+|CASE\s+FILE\s*#?\d*)\b[:.\-–]?\s*", "", h, flags=re.IGNORECASE)
    h = re.sub(r"\(\s*\d{3,4}\s*[–\-—]\s*\d{2,4}\s*\)", "", h)
    h = re.sub(r"^(?:CHAPTER|SECTION|UNIT|PART)\s+\d+[:.\-–]?\s*", "", h, flags=re.IGNORECASE)
    return _normalize_spaces(h).strip(" ,.:;-–")


def write_key_fact_card(line: str, subject: str = "") -> dict[str, str] | None:
    """Deterministic Key Facts question writer (no AI, no generic 'Explain X and its main features' templates).

    Produces a single short-answer Key Facts card from a factual sheet line:
    - `clue`: Clear question ending with '?' that names who/what it is about without leaking the answer.
    - `answer`: Short verbatim span (1–5 words: a name, year, number, or term) copied word-for-word from `line`.
    - Returns `None` for headings, page/card labels, memory tips, source credits, or practice Q&A lines.
    """
    raw_line = _normalize_spaces(line)
    if not raw_line:
        return None

    # Strip inline source credits like "(Britannica)" before checking/extracting
    cleaned_line = _INLINE_SOURCE_CREDIT_RE.sub("", raw_line).strip()
    cleaned_line = re.sub(r"^(?:[•\-\*Æƒ‹\{]|\(\d+\)|\d+[.)])\s*", "", cleaned_line).strip()
    if not cleaned_line or is_sheet_furniture_or_heading(cleaned_line):
        return None

    subj_clean = _clean_subject_heading(subject)
    generic_subjects = {
        "history",
        "civics",
        "history & civics",
        "science",
        "physics",
        "chemistry",
        "biology",
        "geography",
        "mathematics",
        "summary table",
        "core concept",
    }
    has_specific_subj = bool(
        subj_clean
        and subj_clean.lower() not in generic_subjects
        and len(subj_clean.split()) <= 6
        and not re.search(r"\b(?:personalities|industry|chapter|overview|introduction|summary)\b", subj_clean, re.IGNORECASE)
    )

    # 1. Pipe-separated factual table row: "Person | Year | Institution | Role"
    if cleaned_line.count("|") >= 2:
        cells = [c.strip() for c in cleaned_line.split("|") if c.strip()]
        if len(cells) >= 3 and not re.match(r"^(?:Name|Person|Personality|Electrolyte|Column)\b", cells[0], re.IGNORECASE):
            row_subj = cells[0]
            # Pick a specific non-subject cell (prefer a 1-4 word institution/role or 4-digit year)
            for cell in cells[2:] + cells[1:2]:
                cell_words = cell.split()
                if 1 <= len(cell_words) <= MAX_ANSWER_WORDS and cell.lower() != row_subj.lower():
                    if re.match(r"^\d{4}$", cell):
                        other_context = cells[2] if len(cells) >= 3 and cells[2] != cell else cells[-1]
                        clue = f"In which year was {row_subj} associated with {other_context}?"
                    else:
                        year_ctx = f" in {cells[1]}" if re.match(r"^\d{4}$", cells[1]) else ""
                        clue = f"Which institution or role is associated with {row_subj}{year_ctx}?"
                    return {
                        "clue": clue,
                        "question": clue,
                        "answer": cell,
                        "source_line": raw_line,
                        "subject": row_subj,
                    }
        return None

    # 2. Quoted nickname / title / key term: e.g. "Known as the 'Grand Old Man of India'."
    m_quote = re.search(r"[‘'“\"]([A-Za-z0-9][A-Za-z0-9\s\-–]{2,38}?)[’'”\"]", cleaned_line)
    if m_quote:
        ans = m_quote.group(1).strip()
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS:
            who_str = subj_clean if has_specific_subj else "this subject"
            if re.search(r"\b(?:known\s+as|called|titled|nicknamed)\b", cleaned_line, re.IGNORECASE) and has_specific_subj:
                clue = f"By what title or epithet was {who_str} known?"
                return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    # 3. Graduated / studied / educated at <Institution>
    m_grad = re.search(
        r"\b(?:graduated\s+from|studied\s+at|educated\s+at|attended)\s+([A-Z][A-Za-z0-9’'\-–]+(?:\s+[A-Z][A-Za-z0-9’'\-–]+){0,3})",
        cleaned_line,
        re.IGNORECASE,
    )
    if m_grad:
        ans = m_grad.group(1).strip(" ,.:;()")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS:
            loc_match = re.search(r"\bin\s+([A-Z][A-Za-z]+)\b", cleaned_line[m_grad.end() :])
            loc_str = f" in {loc_match.group(1)}" if loc_match and loc_match.group(1) not in ans else ""
            who_str = subj_clean if has_specific_subj else "the subject"
            clue = f"From which college or institution{loc_str} did {who_str} graduate?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    # 4. Chaired / headed / founded / established <Committee/Institution>
    m_chair = re.search(
        r"\b(?:chaired|headed|presided\s+over|founded|established)\s+(?:the\s+)?([A-Z][A-Za-z0-9’'\-–]+(?:\s+[A-Z][A-Za-z0-9’'\-–]+){0,3})",
        cleaned_line,
        re.IGNORECASE,
    )
    if m_chair:
        ans = m_chair.group(1).strip(" ,.:;()")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS:
            verb_word = cleaned_line[m_chair.start() : m_chair.end()].split()[0].lower()
            rest_after = cleaned_line[m_chair.end() :].strip(" .,:;")
            ctx_suffix = f" {rest_after}" if rest_after and ans.lower() not in rest_after.lower() else ""
            # Check if the subject is before the verb in the sentence itself
            prefix_subj = cleaned_line[: m_chair.start()].strip(" ,.:;")
            who_str = prefix_subj if len(prefix_subj) >= 3 else (subj_clean if has_specific_subj else "the leader")
            clue = f"Which body or institution{ctx_suffix} was {verb_word} by {who_str}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": who_str}

    # 5. Definition / Principle / Law pattern: "<Term> is defined as / states that / refers to <Definition>"
    m_def = re.match(
        r"^(?:The\s+)?([A-Z][A-Za-z0-9’'\-–]+(?:\s+[A-Za-z0-9’'\-–]+){0,3}?)\s+(is\s+defined\s+as|states\s+that|refers\s+to|is\s+the\s+process\s+of)\s+(.+)$",
        cleaned_line,
    )
    if m_def:
        ans = m_def.group(1).strip(" ,.:;()")
        verb_phrase = m_def.group(2)
        rhs = m_def.group(3).strip().rstrip(".")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS and ans.lower() not in rhs.lower():
            kind_word = "law or principle" if any(w in ans.lower() for w in ("law", "principle")) else "term or process"
            clue = f"Which {kind_word} {verb_phrase} {rhs}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean or ans}

    # 6. "... called <term>" inside a sentence (e.g. "minute openings called lenticels on the bark of woody stems")
    m_called = re.search(
        r"\b(?:called|known\s+as)\s+[‘'“\"]?([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+(?!on\b|in\b|at\b|of\b|for\b|from\b|to\b|with\b|by\b|which\b|that\b|where\b|when\b|whereas\b|while\b|and\b|or\b)[A-Za-z0-9’'\-–]+){0,2})[’'”\"]?",
        cleaned_line,
        re.IGNORECASE,
    )
    if m_called:
        ans = re.sub(r"^(?:the|a|an)\s+", "", m_called.group(1).strip(), flags=re.IGNORECASE).strip(" ,.:;()")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS:
            before_part = cleaned_line[: m_called.start()].strip(" ,.:;")
            after_part = cleaned_line[m_called.end() :].strip(" .,:;")
            after_part = re.split(r",\s*(?:whereas|while|which|that)\b", after_part)[0].strip()
            clue_body = f"{before_part} {after_part}".strip()
            if ans.lower() not in clue_body.lower() and len(clue_body.split()) >= 4:
                clue = f"What term is given to the feature described as: {clue_body}?"
                return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    # 7. Sentence with a specific 4-digit year (e.g. "... in 1901.", "... in 1892.", "... in 1890.")
    m_year = re.search(r"\b(in|on|during)\s+(\d{1,2}\s+[A-Z][a-z]+\s+\d{4}|\d{4})\b", cleaned_line, re.IGNORECASE)
    if m_year:
        ans = m_year.group(2).strip()
        without_year = (cleaned_line[: m_year.start()] + " " + cleaned_line[m_year.end() :]).strip(" .,:;")
        without_year = _normalize_spaces(without_year)
        if without_year and ans not in without_year:
            first_w = without_year.split()[0].lower()
            if first_w in _FRAGMENT_START_VERBS and has_specific_subj:
                clause = f"{subj_clean} {without_year[0].lower() + without_year[1:]}"
            elif has_specific_subj and subj_clean.lower() not in without_year.lower():
                clause = f"{subj_clean} — {without_year}"
            else:
                clause = without_year
            interrogative = "On what date" if len(ans.split()) > 1 else "In which year"
            clue = f"{interrogative} did the following take place: {clause}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    # 8. "applied by / written by / discovered by / proclaimed <Person>"
    m_by_person = re.search(
        r"\b(?:applied\s+by|written\s+by|authored\s+by|discovered\s+by|invented\s+by|led\s+by|founded\s+by)\s+((?:Lord|Dr\.|Mr\.|Sir|King|Queen|Emperor)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
        cleaned_line,
    )
    if m_by_person:
        ans = _normalize_spaces(m_by_person.group(1)).strip(" ,.:;()")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS:
            replaced = (cleaned_line[: m_by_person.start()] + cleaned_line[m_by_person.end() :]).strip(" .,:;")
            clue = f"Who was responsible for the policy or work described in: {replaced}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    # 8b. "... subsequently, <Person> was proclaimed <Title>"
    m_proclaimed = re.search(
        r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+was\s+proclaimed\s+([A-Z][a-z]+)",
        cleaned_line,
    )
    if m_proclaimed:
        ans = m_proclaimed.group(1).strip()
        title_word = m_proclaimed.group(2).strip()
        before_clause = cleaned_line[: m_proclaimed.start()].strip(" ,.;:")
        clue = f"Who was proclaimed {title_word} after the events in which {before_clause}?"
        return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    # 8c. "The immediate cause of <Event> was the introduction of the <Item>, whose..."
    m_cause_intro = re.search(
        r"immediate\s+cause\s+of\s+(?:the\s+)?(.+?)\s+was\s+the\s+introduction\s+of\s+(?:the\s+)?([A-Za-z0-9’'\-–]+(?:\s+[A-Za-z0-9’'\-–]+){0,2})",
        cleaned_line,
        re.IGNORECASE,
    )
    if m_cause_intro:
        event_name = m_cause_intro.group(1).strip(" ,.:;")
        ans = m_cause_intro.group(2).strip(" ,.:;")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS and ans.lower() not in event_name.lower():
            clue = f"The introduction of which item was the immediate cause of {event_name}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": event_name}

    # 8d. Contrast / advocacy sentence: "... in contrast the <Group> advocated <Items>"
    m_advocated = re.search(
        r"\b(?:in\s+contrast\s+)?(?:the\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,2})\s+advocated\s+(.+)$",
        cleaned_line,
    )
    if m_advocated:
        ans = m_advocated.group(1).strip(" ,.:;")
        adv_items = m_advocated.group(2).strip().rstrip(".")
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS and ans.lower() not in adv_items.lower():
            clue = f"Which group advocated {adv_items}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean or ans}

    # 8e. Scientific molecule / symbol in parentheses: "... from <term> (<Formula>) to ..."
    m_mol = re.search(
        r"\bfrom\s+([a-zA-Z]{4,25})\s*\(([A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)\)",
        cleaned_line,
    )
    if m_mol:
        ans = m_mol.group(1).strip()
        rest_clause = (cleaned_line[: m_mol.start()].strip(" ,.:;") + " " + cleaned_line[m_mol.end() :].strip(" .,:;")).strip()
        if 1 <= len(ans.split()) <= MAX_ANSWER_WORDS and ans.lower() not in rest_clause.lower():
            clue = f"From which molecule does the process occur when {rest_clause}?"
            return {"clue": clue, "question": clue, "answer": ans, "source_line": raw_line, "subject": subj_clean or ans}

    # 9. Colon definition / check: "<Label>: <Formula or Short Fact>"
    if ":" in cleaned_line:
        lhs, rhs = [p.strip() for p in cleaned_line.split(":", 1)]
        m_into = re.search(r"^(.+?)\s+dissociates\s+into\s+(.+)$", rhs, re.IGNORECASE)
        if m_into:
            reactant = m_into.group(1).strip()
            products = m_into.group(2).strip().rstrip(".")
            if 1 <= len(products.split()) <= MAX_ANSWER_WORDS:
                clue = f"Into which ions does {reactant} dissociate?"
                return {"clue": clue, "question": clue, "answer": products, "source_line": raw_line, "subject": reactant}
        if 1 <= len(lhs.split()) <= 4 and len(rhs.split()) >= 4 and lhs.lower() not in rhs.lower():
            clue = f"Which term corresponds to: {rhs.rstrip('.')}?"
            return {"clue": clue, "question": clue, "answer": lhs, "source_line": raw_line, "subject": subj_clean or lhs}

    # 10. General fallback: pick a proper noun or 1-3 word key term inside the sentence and mask it cleanly
    candidates: list[str] = []
    for mp in re.finditer(r"\b([A-Z][a-zA-Z0-9’'\-–]+(?:\s+[A-Z][a-zA-Z0-9’'\-–]+){0,2})\b", cleaned_line):
        cand = mp.group(1).strip(" ,.:;()")
        if (
            1 <= len(cand.split()) <= 4
            and cand.lower() not in _STOP_WORDS
            and cand.split()[0].lower() not in _FRAGMENT_START_VERBS
            and (not has_specific_subj or cand.lower() not in subj_clean.lower())
        ):
            candidates.append(cand)

    if candidates:
        ans = candidates[-1]
        masked = re.sub(re.escape(ans), "___", cleaned_line, count=1)
        if has_specific_subj and subj_clean.lower() not in masked.lower():
            masked = f"{subj_clean}: {masked}"
        if not masked.endswith("?"):
            masked = masked.rstrip(".") + " — what fills the blank (___)?"
        return {"clue": masked, "question": masked, "answer": ans, "source_line": raw_line, "subject": subj_clean}

    return None


def plan_key_facts_cards(
    sheet: Any,
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate Key Facts cards from a sheet (leaving Detective mode untouched) and filter via score_card()."""
    sheet_text = _get_sheet_text(sheet)
    raw_lines = [ln.strip() for ln in sheet_text.splitlines() if ln.strip()]

    planned_cards: list[dict[str, Any]] = []
    current_subject = ""

    for ln in raw_lines:
        if is_sheet_furniture_or_heading(ln):
            # If it's a clean heading (not furniture like Q1:, Memory tip:, Britannica, or table header), update subject context
            if not any(pat.search(ln) for pat in _FURNITURE_PATTERNS) and "|" not in ln:
                cleaned_h = _clean_subject_heading(ln)
                if cleaned_h and len(cleaned_h.split()) <= 6:
                    current_subject = cleaned_h
            continue

        card = write_key_fact_card(ln, subject=current_subject)
        if card is not None:
            planned_cards.append(card)
        else:
            planned_cards.append(
                {
                    "card_type": "plain",
                    "kind": "plain",
                    "clue": _INLINE_SOURCE_CREDIT_RE.sub("", ln).strip(),
                    "question": _INLINE_SOURCE_CREDIT_RE.sub("", ln).strip(),
                    "answer": "",
                    "source_line": ln,
                    "subject": current_subject,
                }
            )

    return filter_cards_after_plan(
        planned_cards,
        sheet,
        min_criterion_score=min_criterion_score,
        min_average_score=min_average_score,
    )


def _make_plain_fallback_card(card: Any) -> Any:
    """Build a plain reading/fact card for Rule A fallback so every sheet line stays on some card."""
    evidence = _extract_evidence(card) or _extract_clue(card)
    subject = _extract_subject(card)
    if isinstance(card, dict):
        fallback = dict(card)
        fallback["card_type"] = "plain"
        fallback["kind"] = "plain"
        fallback["clue"] = evidence
        fallback["question"] = evidence
        fallback["answer"] = ""
        if subject:
            fallback["subject"] = subject
        return fallback

    try:
        import copy

        fallback_obj = copy.copy(card)
        for attr, val in (("card_type", "plain"), ("kind", "plain"), ("clue", evidence), ("question", evidence), ("answer", "")):
            if hasattr(fallback_obj, attr):
                setattr(fallback_obj, attr, val)
        return fallback_obj
    except Exception:
        return {"card_type": "plain", "clue": evidence, "answer": "", "source_line": evidence, "subject": subject}


def filter_cards_after_plan(
    cards: list[Any],
    sheet: Any,
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
    fallback_builder: Callable[[Any], Any] | None = None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Filter planned cards with score_card(), enforcing Rule A (every sheet line remains on a card)."""
    accepted: list[Any] = []
    accepted_quiz_cards: list[Any] = []
    dropped_report: list[dict[str, Any]] = []
    builder = fallback_builder or _make_plain_fallback_card

    for card in cards:
        card_kind = _get_field(card, "card_type", "kind", "type").lower()
        if card_kind in ("plain", "fact", "reading", "note") or not _extract_answer(card):
            accepted.append(card)
            continue

        scores, reasons = score_card(card, sheet, prior_cards=accepted_quiz_cards)
        if is_card_acceptable(
            scores,
            min_criterion_score=min_criterion_score,
            min_average_score=min_average_score,
        ):
            accepted.append(card)
            accepted_quiz_cards.append(card)
        else:
            dropped_report.append(
                {
                    "clue": _extract_clue(card),
                    "answer": _extract_answer(card),
                    "source_line": _extract_evidence(card),
                    "scores": scores,
                    "average": round(sum(scores.values()) / max(1, len(scores)), 2),
                    "reasons": reasons,
                }
            )
            accepted.append(builder(card))

    return accepted, dropped_report


def format_dropped_cards_report(dropped_report: list[dict[str, Any]], sheet_name: str = "") -> str:
    """Format a concise CLI/batch_report summary of dropped cards and their failure reasons."""
    header = f"Card Quality Report{f' ({sheet_name})' if sheet_name else ''}: {len(dropped_report)} card(s) dropped"
    if not dropped_report:
        return f"{header} (all cards passed)."
    lines = [header]
    for idx, item in enumerate(dropped_report, start=1):
        clue = item.get("clue", "")
        ans = item.get("answer", "")
        avg = item.get("average", 0.0)
        reasons = "; ".join(item.get("reasons", []))
        lines.append(f"  {idx}. [avg={avg:.2f}] Q: {clue!r} | A: {ans!r} -> {reasons}")
    return "\n".join(lines)
