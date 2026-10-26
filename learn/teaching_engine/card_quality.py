"""No-AI, rule-based 7-criterion card quality checker for the Teaching Engine.

Scores each candidate card 1–5 on seven rule-based criteria:
1. grounded: answer appears word-for-word on the sheet
2. short_answer: a word, name, year, number, or short term (<= 5 words)
3. clear_question: no template slot filled with a verb/sentence fragment,
   no cut-off proper nouns (e.g. "Man Planning Commission"), ends with '?' or '___'
4. names_subject: the clue identifies who/what it is about without containing the answer
5. not_furniture: answer/clue not taken from practice Q&A, memory tips,
   source credits like "(Britannica)", or headers/footers
6. not_table_soup: answer/clue is not a run of several table cells
7. distinct: no near-duplicate of another card in the same case file
"""

from __future__ import annotations

import re
from typing import Any, Callable

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

# Template slot extraction patterns used to inspect what was plugged into a question stem
_TEMPLATE_SLOT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^Explain\s+(.+?)\s+and\s+its\s+main\s+features\.?$", re.IGNORECASE),
    re.compile(
        r"^What\s+is\s+meant\s+by\s+(.+?),\s+and\s+what\s+are\s+its\s+key\s+characteristics\??$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^What\s+reason\s+or\s+cause\s+is\s+explained\s+regarding\s+(.+?)(?:,\s+and\s+what\s+is\s+its\s+result)?\??$",
        re.IGNORECASE,
    ),
    re.compile(r"^What\s+is\s+the\s+main\s+difference\s+explained\s+regarding\s+(.+?)\??$", re.IGNORECASE),
    re.compile(r"^How\s+is\s+(.+?)\s+used\s+or\s+applied\??$", re.IGNORECASE),
    re.compile(
        r"^What\s+is\s+the\s+chronological\s+order\s+of\s+events\s+or\s+steps\s+described\s+for\s+(.+?)\??$",
        re.IGNORECASE,
    ),
)

# Sheet furniture patterns: practice Q&A, memory tips, source attributions, headers/footers
_FURNITURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|\b)(?:Q\.?\s*\d*[:.)]|Question\s*\d*[:.)]|Ans(?:wer)?\s*\d*[:.)])\s+", re.IGNORECASE),
    re.compile(
        r"(?:^|\b)(?:Memory\s+tip|Quick\s+tip|Study\s+tip|Exam\s+tip|Mnemonic|Remember\s+this|Fun\s+fact|Did\s+you\s+know)\s*[:\-–]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\((?:Source\s*:?\s*)?(?:Britannica|Wikipedia|NCERT|ICSE|CBSE|PTI|Reuters|AP|Wikimedia[^)]*|Courtesy[^)]*)\)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:Source|Courtesy|Photo\s+credit|Image\s+credit)\s*:\s*[A-Z]", re.IGNORECASE),
    re.compile(
        r"(?:^|\b)(?:Page\s+\d+\s+of\s+\d+|All\s+rights\s+reserved|Not\s+to\s+be\s+republished|Reprint\s+20\d{2}|Practice\s+Questions|Check\s+Your\s+Progress|Exercises?\s+for\s+Practice)\b",
        re.IGNORECASE,
    ),
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
    """Criterion 3: no template slot filled with a sentence/verb fragment, no cut-off proper nouns, ends properly."""
    reasons: list[str] = []
    if not clue or len(clue.strip()) < 8:
        return 1, ["clear_question: clue is empty or too short"]

    clue_clean = _normalize_spaces(clue)

    # Check proper ending: question mark '?' or fill-in-the-blank '___' (or clean period for imperative only if valid)
    has_blank = "___" in clue_clean or "____" in clue_clean
    ends_valid = clue_clean.endswith("?") or (has_blank and clue_clean.endswith((".", "___", "____")))
    if not ends_valid:
        # Allow "Explain X and its main features." only if X itself passes slot checks below; otherwise flag ending
        if not clue_clean.endswith("."):
            reasons.append(f"clear_question: clue {clue_clean!r} does not end with '?' or a valid blank")
            return 1, reasons

    # Check for cut-off proper nouns like "Man Planning Commission"
    if _CUTOFF_PROPER_PREFIX_RE.search(clue_clean):
        reasons.append(f"clear_question: clue contains a cut-off proper noun fragment ({clue_clean!r})")
        return 1, reasons

    # Inspect template slots if the clue uses a generic template stem
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
            # Check for internal finite verbs or prepositional sentence fragments inside a noun-slot template
            internal_verbs = {"graduated", "studied", "served", "worked", "founded", "was", "were", "is", "are", "had", "did", "went", "look"}
            if any(w.lower() in internal_verbs for w in slot_words):
                reasons.append(f"clear_question: template slot {slot!r} is a verb/sentence fragment")
                return 1, reasons
            # Check for ungrammatical 3+ capitalized/random word concatenation like "Man Planning Commission"
            if len(slot_words) >= 3 and all(w[0].isupper() for w in slot_words if w) and first_w in {"man", "men", "boy", "girl", "one", "two", "three"}:
                reasons.append(f"clear_question: template slot {slot!r} has a broken proper-noun prefix")
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

    # Catch double spaces/punctuation or broken mid-word hyphenation
    if re.search(r"[A-Za-z]-\s+[a-z]", clue_clean) or ".." in clue_clean.replace("...", ""):
        reasons.append("clear_question: clue contains broken hyphenation or malformed punctuation")
        return 2, reasons

    if not clue_clean.endswith("?") and not has_blank:
        reasons.append("clear_question: clue is a declarative/imperative template rather than a question or blank")
        return 3, reasons

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
        r"^(?:What|Which|Who|Whom|Whose|When|Where|Why|How|In|On|At|During|After|Before|From|To|By|For|Name|Identify|State|Complete)\b\s*",
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
        # If the card belongs to a named section/person/topic and the answer is NOT that subject itself,
        # check that the clue either mentions the subject or has its own explicit proper noun.
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
    """Criterion 5: answer/clue not taken from practice Q&A, memory tips, source credits, or headers/footers."""
    reasons: list[str] = []
    combined_parts = [("clue", clue), ("answer", answer), ("evidence", evidence)]

    for label, text in combined_parts:
        if not text:
            continue
        for pat in _FURNITURE_PATTERNS:
            if pat.search(text):
                reasons.append(f"not_furniture: {label} contains sheet furniture/Q&A/credit/tip ({text!r})")
                return 1, reasons

    # Also check if answer itself is a bare source credit like "Britannica" or "(Britannica)"
    if re.match(r"^\(?(?:Britannica|Wikipedia|NCERT|ICSE|CBSE|Source|Memory\s+Tip)\)?$", answer.strip(), re.IGNORECASE):
        reasons.append(f"not_furniture: answer {answer!r} is a source credit or label")
        return 1, reasons

    return 5, []


def _score_not_table_soup(clue: str, answer: str, evidence: str = "") -> tuple[int, list[str]]:
    """Criterion 6: answer/clue isn't a run of several table cells or jumbled column text."""
    reasons: list[str] = []

    for label, text in (("answer", answer), ("clue", clue), ("evidence", evidence)):
        if not text:
            continue
        # Pipe-separated or multi-space/tab-separated table cells
        if text.count("|") >= 2 or len(re.findall(r"\t+|\s{3,}", text)) >= 2:
            if label in ("answer", "clue"):
                reasons.append(f"not_table_soup: {label} contains raw multi-column table cells ({text!r})")
                return 1, reasons

    # Check if answer or clue concatenates multiple unrelated years/dates or column headers
    years_in_ans = re.findall(r"\b(?:1[5-9]\d{2}|20\d{2})\b", answer)
    if len(years_in_ans) >= 2 and not re.match(r"^\d{4}\s*[–\-—]\s*\d{2,4}$", answer.strip()):
        reasons.append(f"not_table_soup: answer {answer!r} concatenates multiple table years/cells")
        return 1, reasons

    # Detect jumbled multi-cell runs in answer or clue: e.g. "1885 Mumbai Elphinstone" or 4+ capitalized words from adjacent cells
    ans_tokens = answer.split()
    if len(ans_tokens) >= 4 and sum(1 for t in ans_tokens if any(ch.isdigit() for ch in t)) >= 1 and sum(
        1 for t in ans_tokens if t[0].isupper()
    ) >= 2:
        reasons.append(f"not_table_soup: answer {answer!r} looks like a run of multiple table cells")
        return 1, reasons

    # Detect colon/pipe key-value runs inside the answer
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
    """Score a card 1–5 on each of the 7 rule-based criteria and return (scores, reasons).

    Parameters
    ----------
    card:
        Dict or object representing a card (with clue/question, answer, optional source_line/subject).
    sheet:
        Plain text string, dict, or Sheet object containing the source sheet text.
    prior_cards:
        Optional list of already-accepted cards in the same case file for distinctness checking.

    Returns
    -------
    tuple[dict[str, int], list[str]]
        A dictionary mapping each of the 7 criterion names to an integer score 1–5,
        and a list of human-readable failure/warning reasons.
    """
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

    # Object / dataclass card
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
    """Filter planned cards with score_card(), enforcing Rule A (every sheet line remains on a card).

    Cards that already have card_type/kind == 'plain' (no Q&A quiz slot) are kept as-is.
    Quiz cards that fail the quality threshold are logged in `dropped_report` with their
    per-criterion scores and reasons; if the dropped card's source line is not covered by
    another accepted card, it falls back to a plain card so no sheet line is lost (Rule A).
    """
    accepted: list[Any] = []
    accepted_quiz_cards: list[Any] = []
    dropped_report: list[dict[str, Any]] = []
    builder = fallback_builder or _make_plain_fallback_card

    # Pre-scan which source lines are covered by which cards
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
            # Rule A: keep every sheet line on some card by falling back to a plain card
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
