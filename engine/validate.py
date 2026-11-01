"""
Stage 5: validate.py
Reject any card that fails:
 - answer printed on the sheet word-for-word (in the cited item);
 - answer is 1–6 words (names, dates, titles, formulas may be up to 6 words; never a sentence);
 - no split numbers ('5,000' stays whole; never answer '000') and no broken glyphs ('\\ufffd');
 - the front does not contain the answer (no giveaway);
 - the front names its subject (in the question or label);
 - grammatical: starts with a capital, ends with "?" or ".", no leftover template text,
   brackets balanced, no cut-off words;
 - nothing invented: every word in front, label, AND answer must appear in the sheet's
   reader JSON or in ALLOWED_QUESTION_WORDS;
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
from .expressions import check_cut_in_half_span
from .entities import expand_full_person_name

TRIVIAL_WORDS = {
    "the", "a", "an", "if", "make", "centre", "members", "and", "or",
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "is",
    "are", "was", "were", "be", "been", "this", "that", "these", "those",
    "it", "its", "their", "his", "her", "also", "very", "more", "most",
    "other", "some", "any", "each", "every", "both", "all",
}


def tokenize_words(text: str) -> List[str]:
    """Extract alphabetic word tokens from text for vocabulary checking."""
    cleaned = (text or "").replace("______", " ").replace("’", "'").replace("‘", "'")
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
                for tok in tokenize_words(val):
                    vocab.add(tok)
                    if tok.endswith("'s"):
                        vocab.add(tok[:-2])
        table = item.get("table")
        if table:
            for h in table.get("header", []):
                for tok in tokenize_words(str(h)):
                    vocab.add(tok)
            for row in table.get("rows", []):
                for cell in row:
                    for tok in tokenize_words(str(cell)):
                        vocab.add(tok)
    return vocab


def item_contains_answer(item: Dict[str, Any], answer: str) -> bool:
    """Verify that answer is printed word-for-word in the cited item (text, topic, or table)
    and does not split a number across a comma or decimal point.
    """
    ans = (answer or "").strip()
    if not ans:
        return False

    surfaces: List[str] = []
    for field in ("text", "topic", "context", "answer"):
        val = item.get(field, "") or ""
        if val:
            surfaces.append(val)
    table = item.get("table")
    if table:
        for h in table.get("header", []):
            surfaces.append(str(h))
        for row in table.get("rows", []):
            for cell in row:
                surfaces.append(str(cell))

    for surf in surfaces:
        idx = surf.find(ans)
        while idx != -1:
            end_idx = idx + len(ans)
            # Check that a numeric answer does not split a larger number (e.g. '000' inside '5,000')
            before_ch = surf[idx - 1] if idx > 0 else ""
            after_ch = surf[end_idx] if end_idx < len(surf) else ""
            if ans[0].isdigit() and (before_ch.isdigit() or (before_ch in (",", ".") and idx >= 2 and surf[idx - 2].isdigit())):
                idx = surf.find(ans, idx + 1)
                continue
            if ans[-1].isdigit() and (after_ch.isdigit() or (after_ch in (",", ".") and end_idx + 1 < len(surf) and surf[end_idx + 1].isdigit())):
                idx = surf.find(ans, idx + 1)
                continue
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
    front = (card.get("front", "") or "").strip()
    answer = (card.get("answer", "") or "").strip()
    label = (card.get("label", "") or "").strip()
    subject = (card.get("subject", label) or "").strip()
    item_id = card.get("item_id", "")

    # 0. Reject any card containing Unicode replacement character \ufffd or split numbers/dates/units
    if "\ufffd" in front or "\ufffd" in label or "\ufffd" in answer:
        reasons.append("broken_glyph")
    if re.fullmatch(r"0\d+", answer):
        reasons.append("split_number")
    is_cut, _ = check_cut_in_half_span(
        answer,
        source_line=card.get("source_text", ""),
        clue=front if "______" in front else "",
    )
    if is_cut:
        reasons.append("split_span")

    # 1. Answer printed on the sheet word-for-word in the cited item (without splitting a number)
    item = items_by_id.get(item_id)
    if not item:
        reasons.append("missing_item_id")
    elif not item_contains_answer(item, answer):
        reasons.append("answer_not_in_cited_item")

    # 1b. Change E: Full names — reject surname-only or shortened person answers when full name is printed
    if item and (
        card.get("question_type") == "WHO"
        or card.get("prompt") in ("Name the person", "Who fits the gap?")
    ):
        expanded_name = expand_full_person_name(
            answer,
            card.get("source_text", ""),
            item.get("text", ""),
            item.get("topic", ""),
        )
        if expanded_name != answer:
            reasons.append("shortened_person_name")

    # 2. Answer length: 1–6 words (names, dates, titles, formulas may be up to 6 non-operator tokens; never a sentence)
    ans_words = [w for w in answer.split() if w not in ("=", "×", "÷", "+", "-", "−")]
    max_words = 6
    if len(answer.split()) == 0:
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
        first_alnum = next((ch for ch in front if ch.isalnum()), "")
        if first_alnum and first_alnum.isalpha() and not first_alnum.isupper() and card.get("question_type") != "FORMULA":
            reasons.append("does_not_start_with_capital")
        if not (front.endswith("?") or front.endswith(".") or card.get("question_type") == "FORMULA"):
            reasons.append("invalid_ending_punctuation")
        if "<" in front or ">" in front or "{" in front or "}" in front:
            reasons.append("leftover_template_text")
        if front.count("(") != front.count(")") or front.count("[") != front.count("]"):
            reasons.append("unbalanced_brackets")

    # 6. Nothing invented: check EVERY word in front, label, AND answer against sheet_vocab | ALLOWED_QUESTION_WORDS
    for field_name, field_val in (("front", front), ("label", label), ("answer", answer)):
        for w in tokenize_words(field_val):
            if w not in sheet_vocab and w not in ALLOWED_QUESTION_WORDS:
                reasons.append(f"invented_word:{w}")

    # 7. Not trivial
    if answer.lower() in TRIVIAL_WORDS or (len(answer) < 2 and not answer.isalnum() and answer not in ("½", "¾", "¼")):
        reasons.append("trivial_answer")

    # 8. Not a duplicate: same canonical subject + same normalized answer
    subj_key = canonicalize_subject(subject)
    norm_ans = re.sub(r"[^a-z0-9½¾¼]+", " ", answer.lower()).strip()
    dedup_key = (subj_key, norm_ans)
    if dedup_key in seen_subject_answers:
        reasons.append("duplicate_fact")

    return reasons
