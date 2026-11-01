"""
Stage 5: validate.py
Reject any card that fails:
 - answer printed on the sheet word-for-word (in the cited item);
 - answer is 1–4 words (names, dates, titles may be longer; never a sentence);
 - the front does not contain the answer (no giveaway);
 - the front names its subject (in the question or label);
 - grammatical: starts with a capital, ends with "?" or ".", no leftover template text,
   brackets balanced, no cut-off words;
 - not trivial: answer is an entity, date, number, quantity, formula part or term —
   never a common word ("the", "If", "Make", "centre", "Members");
 - not a duplicate: one card per fact; two cards testing the same answer about the same subject
   -> keep the clearer one.
"""
from __future__ import annotations
import re
from typing import Dict, List, Any, Set, Tuple
from .questions import ALLOWED_QUESTION_WORDS
from .facts import canonicalize_subject

TRIVIAL_WORDS = {
    "the", "a", "an", "if", "make", "centre", "members", "and", "or",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "is",
    "are", "was", "were", "be", "been", "this", "that", "these", "those",
    "it", "its", "their", "his", "her", "also", "very", "more", "most",
    "other", "some", "any", "each", "every", "both", "all",
}


def tokenize_words(text: str) -> List[str]:
    """Extract alphabetic word tokens from text for vocabulary checking."""
    cleaned = text.replace("______", " ").replace("’", "'").replace("‘", "'")
    tokens: List[str] = []
    for w in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", cleaned):
        wl = w.lower()
        tokens.append(wl)
        if wl.endswith("'s"):
            tokens.append(wl[:-2])
    return tokens


def build_sheet_vocabulary(reader_json: Dict[str, Any]) -> Set[str]:
    """Collect all lowercase word tokens printed anywhere on the sheet."""
    vocab: Set[str] = set()
    for item in reader_json.get("items", []):
        for field in ("text", "topic", "context", "answer"):
            val = item.get(field, "")
            if val:
                vocab.update(tokenize_words(val))
        table = item.get("table")
        if table:
            for h in table.get("header", []):
                vocab.update(tokenize_words(str(h)))
            for row in table.get("rows", []):
                for cell in row:
                    vocab.update(tokenize_words(str(cell)))
    return vocab


def item_contains_answer(item: Dict[str, Any], answer: str) -> bool:
    """Verify that answer is printed word-for-word in the cited item (text, topic, or table)."""
    ans = answer.strip()
    if not ans:
        return False
    for field in ("text", "topic", "context"):
        val = item.get(field, "") or ""
        if ans in val:
            return True
    table = item.get("table")
    if table:
        for h in table.get("header", []):
            if ans in str(h):
                return True
        for row in table.get("rows", []):
            for cell in row:
                if ans in str(cell):
                    return True
    return False


def validate_card(
    card: Dict[str, Any],
    items_by_id: Dict[str, Dict[str, Any]],
    sheet_vocab: Set[str],
    seen_subject_answers: Set[Tuple[str, str]],
) -> List[str]:
    """Return a list of rejection reasons (empty list if card is valid)."""
    reasons: List[str] = []
    front = card.get("front", "").strip()
    answer = card.get("answer", "").strip()
    label = card.get("label", "").strip()
    subject = card.get("subject", label).strip()
    item_id = card.get("item_id", "")

    # 1. Answer printed on the sheet word-for-word in the cited item
    item = items_by_id.get(item_id)
    if not item:
        reasons.append("missing_item_id")
    elif not item_contains_answer(item, answer):
        reasons.append("answer_not_in_cited_item")

    # 2. Answer length: 1–4 words (names, dates, titles, formulas, paired forces may be up to 6 words; never a sentence)
    ans_words = answer.split()
    max_words = 6
    if len(ans_words) == 0:
        reasons.append("empty_answer")
    elif len(ans_words) > max_words or (answer.endswith(".") and len(ans_words) > 4):
        reasons.append("answer_too_long")

    # 3. Front does not contain the answer (no giveaway)
    if answer:
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(answer) + r"(?![A-Za-z0-9])", re.IGNORECASE)
        if pattern.search(front):
            reasons.append("front_contains_answer")

    # 4. Front names its subject (in the question or label)
    if not label and not subject:
        reasons.append("missing_subject")
    else:
        subj_tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9]+", subject) if len(t) > 2]
        combined = (front + " " + label).lower()
        if subj_tokens and not any(t in combined for t in subj_tokens):
            reasons.append("front_missing_subject")

    # 5. Grammatical checks
    if not front:
        reasons.append("empty_front")
    else:
        first_alpha = next((ch for ch in front if ch.isalpha()), "")
        if first_alpha and not first_alpha.isupper() and card.get("question_type") != "FORMULA":
            reasons.append("does_not_start_with_capital")
        if not (front.endswith("?") or front.endswith(".") or card.get("question_type") == "FORMULA"):
            reasons.append("invalid_ending_punctuation")
        if "<" in front or ">" in front or "{" in front or "}" in front:
            reasons.append("leftover_template_text")
        if front.count("(") != front.count(")") or front.count("[") != front.count("]"):
            reasons.append("unbalanced_brackets")

    # 6. No invented words
    for w in tokenize_words(front):
        if w not in sheet_vocab and w not in ALLOWED_QUESTION_WORDS:
            reasons.append(f"invented_word:{w}")

    # 7. Not trivial
    if answer.lower() in TRIVIAL_WORDS or (len(answer) < 2 and not answer.isalnum()):
        reasons.append("trivial_answer")

    # 8. Not a duplicate: same canonical subject + same normalized answer
    subj_key = canonicalize_subject(subject)
    norm_ans = re.sub(r"[^a-z0-9]+", " ", answer.lower()).strip()
    dedup_key = (subj_key, norm_ans)
    if dedup_key in seen_subject_answers:
        reasons.append("duplicate_fact")

    return reasons
