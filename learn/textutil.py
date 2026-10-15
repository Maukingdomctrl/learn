"""Word and sentence counting shared by timing, validation and rendering."""

import re

_MATH_CHARS = set("0123456789.,+-−×÷*/=^()%²³√π<>≤≥:")
_BLANK_RE = re.compile(r"_{3,}")


def is_math_token(tok: str) -> bool:
    core = tok.strip(".,;:!?")
    return bool(core) and all(c in _MATH_CHARS for c in core) and any(c.isdigit() or c in "+-−×÷*/=^√" for c in core)


def tokens(text: str) -> list[str]:
    return [t for t in re.split(r"\s+", text or "") if t and not _BLANK_RE.fullmatch(t)]


def count_words(text: str) -> int:
    """Words as defined in Section 6.2: a number or symbolic expression counts as 1 word.

    Consecutive math tokens ("3 + 4 = 7") merge into one word. Blank markers ("____") are not words.
    """
    n = 0
    prev_math = False
    for tok in tokens(text):
        math = is_math_token(tok)
        if not (math and prev_math):
            n += 1
        prev_math = math
    return n


def written_words(answer: str) -> int:
    """Expected handwriting words for an answer (Section 6.2).

    A single letter or single number counts as 0 because it is already in item time.
    """
    toks = tokens(answer)
    if len(toks) == 1:
        core = toks[0].strip(".,;:!?()")
        if len(core) == 1 or is_math_token(core):
            return 0
    return count_words(answer)


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if p and p.strip()]


def has_blank(text: str) -> bool:
    return bool(_BLANK_RE.search(text or ""))
