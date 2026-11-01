"""Validates candidate study cards against the source sheet, vocabulary, and grammar rules."""
from __future__ import annotations

import re
from typing import Any

from .entities import (
    ORG_HEAD_WORDS,
    SINGULAR_AND_ENTITY_HEADS,
    WORK_CUE_BEFORE_RE,
    expand_full_person_name,
    expand_multiword_proper_name,
)
from .expressions import check_cut_in_half_span
from .facts import canonicalize_subject
from .questions import (
    ALLOWED_QUESTION_WORDS,
    _has_dangling_ending,
    _is_fragment_clue,
    _is_institution_or_organisation_answer,
    is_chemical_substance_or_formula,
)
from .relations import (
    _CLAUSE_AUX_OR_VERB_RE,
    _COMPOUND_SINGLE_NAMES,
    _LEADING_QUANTIFIER_RE,
    _PLURAL_CATEGORY_FOLLOWERS_RE,
)

TRIVIAL_WORDS = {
    "the",
    "a",
    "an",
    "if",
    "make",
    "centre",
    "members",
    "and",
    "or",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "their",
    "his",
    "her",
    "also",
    "very",
    "more",
    "most",
    "other",
    "some",
    "any",
    "each",
    "every",
    "both",
    "all",
}


def tokenize_words(text: str) -> list[str]:
    """Extract alphabetic word tokens from text for vocabulary checking."""
    cleaned = (text or "").replace("______", " ").replace("’", "'").replace("‘", "'")
    tokens: list[str] = []
    for w in re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", cleaned):
        wl = w.lower()
        tokens.append(wl)
        if wl.endswith("'s"):
            tokens.append(wl[:-2])
    return tokens


def build_sheet_vocabulary(reader_json: dict[str, Any]) -> set[str]:
    """Collect all lowercase word tokens printed anywhere on the sheet."""
    vocab: set[str] = set()
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


def item_contains_answer(item: dict[str, Any], answer: str) -> bool:
    """Verify that answer is printed word-for-word in the cited item (text, topic, or table)
    and does not split a number across a comma or decimal point.
    """
    ans = (answer or "").strip()
    if not ans:
        return False

    surfaces: list[str] = []
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
            before_ch = surf[idx - 1] if idx > 0 else ""
            after_ch = surf[end_idx] if end_idx < len(surf) else ""
            if ans[0].isdigit() and (
                before_ch.isdigit()
                or (before_ch in (",", ".") and idx >= 2 and surf[idx - 2].isdigit())
            ):
                idx = surf.find(ans, idx + 1)
                continue
            if ans[-1].isdigit() and (
                after_ch.isdigit()
                or (after_ch in (",", ".") and end_idx + 1 < len(surf) and surf[end_idx + 1].isdigit())
            ):
                idx = surf.find(ans, idx + 1)
                continue
            return True
    return False


def _is_multi_item_list_answer(answer: str, rel: str, source_text: str, front: str) -> bool:
    """Return True if answer contains multiple list items instead of a single item."""
    if (
        rel
        in (
            "FORMULA",
            "DEFINITION_FORMULA",
            "COLON_EQUATION_RHS",
            "SUMMARY_EQUALS",
            "HISTORIC_INDUSTRY",
            "INDUSTRY_SINCE",
            "LAID_FOUNDATIONS_FOR",
            "FACILITY_IN",
            "WROTE",
        )
        or "=" in answer
        or "→" in answer
    ):
        return False
    if " and " not in answer and ", " not in answer:
        return False
    if re.search(r",\s*\d{4}\b", answer) or re.fullmatch(r"[\d,\s.%₹£$+-]+", answer):
        return False
    if answer.lower().strip() in _COMPOUND_SINGLE_NAMES:
        return False

    if "______" in front:
        before_gap, after_gap = front.split("______", 1)
        if _PLURAL_CATEGORY_FOLLOWERS_RE.match(after_gap):
            return True
        if WORK_CUE_BEFORE_RE.search(before_gap):
            return False
    if source_text and answer in source_text:
        before_src, after_src = source_text.split(answer, 1)
        if _PLURAL_CATEGORY_FOLLOWERS_RE.match(after_src):
            return True
        if WORK_CUE_BEFORE_RE.search(before_src):
            return False

    words = [w.strip(".,;:()'\"’‘") for w in answer.split() if w.strip(".,;:()'\"’‘")]
    if words and (words[-1] in ORG_HEAD_WORDS or any(w in SINGULAR_AND_ENTITY_HEADS for w in words)):
        return False

    parts = [p.strip() for p in re.split(r",\s*(?:and\s+)?|\s+and\s+", answer) if p.strip()]
    if len(parts) >= 2:
        if ", " in answer:
            return True
        if parts[0][0].isupper() and parts[1][0].isupper() and (not words or words[-1] not in ORG_HEAD_WORDS):
            return True
    return False


def _is_non_key_fact_phrase(answer: str, q_type: str, rel: str) -> bool:
    """Return True if answer is a modifier phrase ('Less CO2') or clause ('both gases are produced')."""
    if (
        q_type == "FORMULA"
        or rel in ("FORMULA", "DEFINITION_FORMULA", "COLON_EQUATION_RHS", "SUMMARY_EQUALS", "PURPOSE")
        or "=" in answer
        or "→" in answer
    ):
        return False
    if _LEADING_QUANTIFIER_RE.match(answer.strip()):
        return True
    if _CLAUSE_AUX_OR_VERB_RE.search(answer.strip()):
        return True
    return False


def validate_card(
    card: dict[str, Any],
    items_by_id: dict[str, dict[str, Any]],
    sheet_vocab: set[str],
    seen_subject_answers: set[tuple[str, str]],
    max_clue_words: int = 20,
) -> list[str]:
    """Return a list of rejection reasons (empty list if card is valid)."""
    reasons: list[str] = []
    front = (card.get("front", "") or "").strip()
    answer = (card.get("answer", "") or "").strip()
    label = (card.get("label", "") or "").strip()
    subject = (card.get("subject", label) or "").strip()
    prompt = (card.get("prompt", "") or "").strip()
    q_type = card.get("question_type", "")
    rel = card.get("relation", "")
    source_text = card.get("source_text", "")
    item_id = card.get("item_id", "")

    # 0. Reject any card containing Unicode replacement character \ufffd or split numbers/dates/units
    if "\ufffd" in front or "\ufffd" in label or "\ufffd" in answer:
        reasons.append("broken_glyph")
    if re.fullmatch(r"0\d+", answer):
        reasons.append("split_number")
    is_cut, _ = check_cut_in_half_span(
        answer,
        source_line=source_text,
        clue=front if "______" in front else "",
    )
    if is_cut:
        reasons.append("split_span")

    # 0b. B2 & B6 checks on answer
    if answer and _is_multi_item_list_answer(answer, rel, source_text, front):
        reasons.append("list_answer_multiple_items")
    if answer and _is_non_key_fact_phrase(answer, q_type, rel):
        reasons.append("non_key_fact_phrase")

    # 1. Answer printed on the sheet word-for-word in the cited item (without splitting a number)
    item = items_by_id.get(item_id)
    if not item:
        reasons.append("missing_item_id")
    elif not item_contains_answer(item, answer):
        reasons.append("answer_not_in_cited_item")

    # 1b. Change E: Full names — reject surname-only or shortened person answers when full name is printed
    if item and (q_type == "WHO" or prompt in ("Name the person", "Who fits the gap?")):
        expanded_name = expand_full_person_name(
            answer,
            source_text,
            item.get("text", ""),
            item.get("topic", ""),
        )
        if expanded_name != answer:
            reasons.append("shortened_person_name")

    # 2. Answer length: 1–6 words (names, dates, titles, formulas may be up to 6 non-operator tokens)
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
        if (
            not front.startswith("______")
            and first_alnum
            and first_alnum.isalpha()
            and not first_alnum.isupper()
            and q_type != "FORMULA"
        ):
            reasons.append("does_not_start_with_capital")
        if not (front.endswith("?") or front.endswith(".") or q_type == "FORMULA"):
            reasons.append("invalid_ending_punctuation")
        if ("______" in front or front.endswith(".")) and _has_dangling_ending(front):
            reasons.append("dangling_clue_ending")
        if _is_fragment_clue(front):
            reasons.append("fragment_clue")
        if answer and answer[0].isupper() and "______" in front:
            reconstructed = front.replace("______", answer, 1)
            expanded_proper = expand_multiword_proper_name(answer, source_text or reconstructed)
            if expanded_proper != answer and expanded_proper in reconstructed:
                reasons.append("split_proper_name")
        if answer and "______" not in front and front.endswith("?"):
            m_rep = re.match(
                r"^([A-Za-z][A-Za-z\s-]{1,25}?)\s+(of|in|on|at|to|for|by|from)\s+(.+)$",
                answer,
                re.IGNORECASE,
            )
            if m_rep:
                q_low = front.lower()
                prefix_words = [
                    w.lower()
                    for w in re.findall(r"[A-Za-z]+", m_rep.group(1))
                    if w.lower() not in ("the", "a", "an")
                ]
                prep_w = m_rep.group(2).lower()
                if (
                    prefix_words
                    and all(re.search(rf"\b{re.escape(pw)}\b", q_low) for pw in prefix_words)
                    and re.search(rf"\b{re.escape(prep_w)}\b", q_low)
                ):
                    reasons.append("answer_repeats_question_words")
        if "<" in front or ">" in front or "{" in front or "}" in front:
            reasons.append("leftover_template_text")
        if front.count("(") != front.count(")") or front.count("[") != front.count("]"):
            reasons.append("unbalanced_brackets")
        for s_cand in (subject, label):
            sc = (s_cand or "").strip()
            if sc and (
                front.lower().startswith(f"in {sc.lower()}, ")
                or front.lower().startswith(f"in the {sc.lower()}, ")
            ):
                reasons.append("in_subject_prefix")
                break
        is_year_card = q_type == "WHEN" or prompt in (
            "Which year fits the gap?",
            "Which date fits the gap?",
            "Which century fits the gap?",
            "Give the date or year",
        )
        if len(front.split()) > max_clue_words:
            reasons.append("clue_too_long")
            if is_year_card:
                reasons.append("year_clue_too_long")

    # 5b. Prompt checks (B4: ends with '?'; B5: institution not place; Round 5 Fix 3: substance not number)
    if prompt and not prompt.endswith("?"):
        reasons.append("prompt_missing_question_mark")
    if prompt == "Which place fits the gap?" and _is_institution_or_organisation_answer(answer, source_text):
        reasons.append("institution_with_place_prompt")
    if prompt == "Which number fits the gap?" and is_chemical_substance_or_formula(answer, source_text):
        reasons.append("chemical_substance_with_number_prompt")

    # 6. Nothing invented: check EVERY word in front, label, AND answer against sheet_vocab | ALLOWED_QUESTION_WORDS
    for _field_name, field_val in (("front", front), ("label", label), ("answer", answer)):
        for w in tokenize_words(field_val):
            if w not in sheet_vocab and w not in ALLOWED_QUESTION_WORDS:
                reasons.append(f"invented_word:{w}")

    # 7. Not trivial
    if answer.lower() in TRIVIAL_WORDS or (
        len(answer) < 2 and not answer.isalnum() and answer not in ("½", "¾", "¼")
    ):
        reasons.append("trivial_answer")

    # 8. Not a duplicate: same canonical subject + same normalized answer
    subj_key = canonicalize_subject(subject)
    norm_ans = re.sub(r"[^a-z0-9½¾¼]+", " ", answer.lower()).strip()
    dedup_key = (subj_key, norm_ans)
    if dedup_key in seen_subject_answers:
        reasons.append("duplicate_fact")

    return reasons
