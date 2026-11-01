"""Assembles, validates, balances, and formats Key Facts study cards from sheet items."""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .entities import (
    classify_answer_entity,
    expand_full_person_name,
    expand_multiword_proper_name,
    expand_substance_with_formula,
    find_all_expressions,
)
from .expressions import FAMILY_L
from .facts import canonicalize_subject, resolve_sheet_title
from .questions import balance_question_mix, generate_card, generate_reinforcement_card
from .relations import extract_relations_from_item
from .validate import build_sheet_vocabulary, validate_card

CARD_KINDS = ("gap", "question", "term", "name", "equation", "row", "compare")

_PROSE_ITEM_KINDS = ("point", "summary", "paragraph", "body", "line", "text", "prose")

_STANDARD_MAX_CLUE_WORDS = {
    7: 16,
    8: 20,
    9: 24,
}

_NO_FORMATTING_PARENT_NOTE = (
    "Nothing on these pages is printed in bold or as a bullet or numbered point, "
    "so Key Facts made study cards from every line instead."
)

_ORDINAL_SUPERLATIVE_RE = re.compile(
    r"\b(?:\d+(?:nd|rd|th)|1\dth|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth)"
    r"[-\s]+(?:largest|smallest|longest|highest|oldest|biggest|busiest|most\s+[a-z]+)\b",
    re.IGNORECASE,
)

_CHECK_TRIGGER_RE = re.compile(
    r"\b(?:invented|first|oldest|largest|smallest|most populous|only|always|never)\b",
    re.IGNORECASE,
)

_NUMBERED_MARKER_RE = re.compile(
    r"^(?:\(\d+\)|\d+[.):]|[a-zA-Z][.)]|[ivxIVX]+[.)])$",
)


@dataclass(frozen=True)
class KeyFactCard:
    """A single printable Key Facts study card."""

    kind: str
    question: str
    clue: str
    answer: str
    page: int
    unit_ids: tuple[str, ...]
    about: str
    checks: tuple[str, ...]


@dataclass(frozen=True)
class _ReaderTable:
    """Table data attached to a study-sheet item."""

    header: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    kind: str | None = None


@dataclass(frozen=True)
class _ReaderItem:
    """Structured item produced by the Learn PDF reader."""

    kind: str = ""
    text: str = ""
    page: int = 1
    unit_ids: tuple[str, ...] = ()
    marker: str | None = None
    section: str | None = None
    group: str | None = None
    topic: str | None = None
    context: str | None = None
    answer: str | None = None
    options: tuple[str, ...] | None = None
    table: _ReaderTable | None = None
    top: float | int | None = None
    bottom: float | int | None = None
    bullet: str | int | None = None
    bold: tuple[str, ...] = ()
    id: str | None = None


def _validate_standard(standard: int) -> int:
    """Validate ICSE standard (7, 8, or 9) and return the maximum clue word count."""
    if type(standard) is not int or standard not in _STANDARD_MAX_CLUE_WORDS:
        raise ValueError("Choose ICSE Standard 7, 8, or 9.")
    return _STANDARD_MAX_CLUE_WORDS[standard]


def _get_field(obj: Any, name: str, default: Any = None) -> Any:
    """Read an attribute from an object or a key from a dictionary."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _dict_to_reader_item(raw: Any, index: int) -> Any:
    """Convert a JSON item dictionary into a _ReaderItem object if it is a dict."""
    if not isinstance(raw, dict):
        return raw
    raw_table = raw.get("table")
    table_obj: _ReaderTable | None = None
    if isinstance(raw_table, dict):
        header = tuple(str(h) for h in (raw_table.get("header") or ()))
        rows = tuple(tuple(str(c) for c in r) for r in (raw_table.get("rows") or ()))
        table_obj = _ReaderTable(header=header, rows=rows, kind=raw_table.get("kind"))
    elif raw_table is not None:
        header = tuple(str(h) for h in (getattr(raw_table, "header", None) or ()))
        rows = tuple(tuple(str(c) for c in r) for r in (getattr(raw_table, "rows", None) or ()))
        table_obj = _ReaderTable(header=header, rows=rows, kind=getattr(raw_table, "kind", None))

    raw_opts = raw.get("options")
    opts_tuple = tuple(str(o) for o in raw_opts) if raw_opts is not None else None

    return _ReaderItem(
        kind=str(raw.get("kind") or ""),
        text=str(raw.get("text") or ""),
        page=int(raw.get("page") or 1),
        unit_ids=tuple(str(u) for u in (raw.get("unit_ids") or ())),
        marker=raw.get("marker"),
        section=raw.get("section"),
        group=raw.get("group"),
        topic=raw.get("topic"),
        context=raw.get("context"),
        answer=raw.get("answer"),
        options=opts_tuple,
        table=table_obj,
        top=raw.get("top"),
        bottom=raw.get("bottom"),
        bullet=raw.get("bullet"),
        bold=tuple(str(b) for b in (raw.get("bold") or ())),
        id=raw.get("id") or f"I{index}",
    )


def _item_to_dict(item: Any, index: int) -> dict[str, Any]:
    """Read an Item object via getattr(item, name, default) into an internal pipeline dictionary."""
    item_id = _get_field(item, "id", None) or f"I{index}"
    kind = _get_field(item, "kind", "") or ""
    text = _get_field(item, "text", "") or ""
    page_raw = _get_field(item, "page", 1)
    page = int(page_raw) if page_raw is not None else 1
    unit_ids_raw = _get_field(item, "unit_ids", None) or ()
    unit_ids = tuple(str(u) for u in unit_ids_raw)
    bold_raw = _get_field(item, "bold", None) or ()
    bold = [str(b) for b in bold_raw]

    out: dict[str, Any] = {
        "id": str(item_id),
        "kind": str(kind),
        "text": str(text),
        "page": page,
        "unit_ids": unit_ids,
        "bold": bold,
    }

    opt_attrs = (
        "marker",
        "section",
        "group",
        "topic",
        "context",
        "answer",
        "options",
        "top",
        "bottom",
        "bullet",
    )
    for opt_attr in opt_attrs:
        val = _get_field(item, opt_attr, None)
        if val is not None:
            out[opt_attr] = val

    tbl = _get_field(item, "table", None)
    if tbl is not None:
        header = list(_get_field(tbl, "header", None) or [])
        rows = [list(r) for r in (_get_field(tbl, "rows", None) or [])]
        tbl_dict: dict[str, Any] = {"header": header, "rows": rows}
        tbl_kind = _get_field(tbl, "kind", None)
        if tbl_kind is not None:
            tbl_dict["kind"] = tbl_kind
        out["table"] = tbl_dict

    return out


def _has_sheet_formatting(item_dicts: list[dict[str, Any]]) -> bool:
    """Return True if any point/summary item on the sheet is printed in bold or as a bullet or numbered point."""
    for it in item_dicts:
        if it.get("kind") not in _PROSE_ITEM_KINDS:
            continue
        if any(str(b).strip() for b in (it.get("bold") or ())):
            return True
        bullet_val = it.get("bullet")
        if bullet_val is not None and bullet_val is not False and str(bullet_val).strip() != "":
            return True
        marker_str = str(it.get("marker") or "").strip()
        if marker_str and (
            marker_str in ("•", "-", "–", "—", "*", "▪", "◦")
            or _NUMBERED_MARKER_RE.match(marker_str)
        ):
            return True
    return False


def _build_checks(source_text: str) -> tuple[str, ...]:
    """Build adult check notes when the source sentence uses absolute or superlative claims (max 1 note)."""
    cleaned = _ORDINAL_SUPERLATIVE_RE.sub("", source_text or "")
    match = _CHECK_TRIGGER_RE.search(cleaned)
    if not match:
        return ()
    word = re.sub(r"\s+", " ", match.group(0).strip().lower())
    return (f"Check first: the sheet says “{word}”. Confirm it in the textbook before learning it.",)


def _classify_card_kind(cand: dict[str, Any]) -> str:
    """Classify an accepted card into one of Learn's seven card kinds."""
    qtype = cand.get("question_type", "")
    front = cand.get("front", "")
    prompt = cand.get("prompt", "")
    answer = cand.get("answer", "")
    relation = cand.get("relation", "")

    if qtype == "TABLE":
        return "row"
    if qtype == "FORMULA" or prompt == "Which formula fits the gap?":
        return "equation"
    if (
        " = " in front
        and qtype == "GAP"
        and not any(ch.isdigit() for ch in answer)
        and not any(op in front for op in ("+", "−", "×", "÷", "²", "³", "/"))
    ):
        return "compare"
    if relation in ("LARGEST_OUTSIDE", "FINANCIAL_RANK", "RANK"):
        return "compare"
    if ("=" in front or "=" in answer) and (
        any(ch.isdigit() for ch in front)
        or any(ch.isdigit() for ch in answer)
        or any(op in front for op in ("+", "−", "×", "÷", "²", "³"))
    ):
        return "equation"
    if "______" in front:
        return "gap"
    if qtype == "WHO" or prompt in ("Name the person", "Who fits the gap?"):
        return "name"
    if qtype == "WHAT_CALLED":
        return "term"
    return "question"


def _to_key_fact_card(cand: dict[str, Any], items_by_id: dict[str, dict[str, Any]]) -> KeyFactCard:
    """Convert an accepted internal card dictionary into a frozen KeyFactCard."""
    front = cand["front"]
    prompt = (cand.get("prompt") or "").strip()
    if prompt and not prompt.endswith("?"):
        prompt = f"{prompt}?"
    question = (prompt or "Which word fits the gap?") if "______" in front else "Answer it."
    item_obj = items_by_id.get(cand.get("item_id", ""), {})
    raw_uids = item_obj.get("unit_ids") or ()
    unit_ids = tuple(str(u) for u in raw_uids)
    about = cand.get("label") or "Study sheet"
    if about.strip().lower() == cand["answer"].strip().lower():
        about = "Study sheet"
    checks = _build_checks(cand.get("source_text", ""))
    kind = _classify_card_kind(cand)
    return KeyFactCard(
        kind=kind,
        question=question,
        clue=front,
        answer=cand["answer"],
        page=int(cand.get("page", 1)),
        unit_ids=unit_ids,
        about=about,
        checks=checks,
    )


def _collect_practice_signals(items: list[dict[str, Any]]) -> str:
    """Collect text and Family L keywords from the sheet's own practice questions and answers."""
    chunks: list[str] = []
    for it in items:
        if it.get("kind") in ("question", "answer") or it.get("section") in ("questions", "answers", "qa"):
            q_text = it.get("text", "") or ""
            a_text = it.get("answer", "") or ""
            chunks.append(q_text)
            chunks.append(a_text)
            for m_l in FAMILY_L.find(q_text):
                chunks.extend(m_l.get("keywords") or [])
    return " ".join(chunks).lower()


def _execute_pipeline(
    item_dicts: list[dict[str, Any]],
    sheet_name: str = "",
    max_cards: int = 30,
    max_clue_words: int = 20,
) -> dict[str, Any]:
    """Run all 6 stages deterministically on normalized item dictionaries."""
    has_formatting = _has_sheet_formatting(item_dicts)
    parent_notes: tuple[str, ...] = () if has_formatting or not item_dicts else (_NO_FORMATTING_PARENT_NOTE,)

    normalized_items: list[dict[str, Any]] = []
    for it in item_dicts:
        ik = it.get("kind", "")
        if ik in ("paragraph", "body", "line", "text", "prose"):
            normalized_items.append(dict(it, kind="point"))
        else:
            normalized_items.append(it)

    reader_json = {"sheet": sheet_name, "items": normalized_items}
    items_by_id: dict[str, dict[str, Any]] = {it["id"]: it for it in normalized_items if "id" in it}
    sheet_vocab = build_sheet_vocabulary(reader_json)
    practice_text = _collect_practice_signals(normalized_items)
    sheet_title = resolve_sheet_title(reader_json)

    qa_inline_re = re.compile(
        r"^(?:(?:Q(?:uestion)?\.?\s*\d*|\d+)[.):]?\s*.+?\?\s*)?(?:Model\s+)?(?:Answer|Ans)\.?\s*[:—-]\s*.+$",
        re.IGNORECASE,
    )
    qa_question_only_re = re.compile(
        r"^(?:(?:Q(?:uestion)?\.?\s*\d+|\(\d+\)|\d+[.)])\s+.+\?|"
        r"(?:Who|What|When|Where|Which|Why|How|Name|State|Define|Mention|Give)\b.+\?)$",
        re.IGNORECASE,
    )
    regular_note_count = 0
    qa_item_count = 0
    for it in normalized_items:
        ik = it.get("kind", "")
        isec = (it.get("section") or "").strip()
        itxt = (it.get("text") or "").strip()
        if (
            ik in ("question", "answer")
            or isec in ("questions", "answers", "qa")
            or qa_inline_re.match(itxt)
            or qa_question_only_re.match(itxt)
        ):
            qa_item_count += 1
        elif ik in ("point", "summary", "table") and itxt:
            regular_note_count += 1

    allow_qa = qa_item_count > 0 and (regular_note_count == 0 or qa_item_count > regular_note_count)

    sheet_prose = " ".join(
        (it.get("text") or "").strip() for it in normalized_items if it.get("kind") in ("point", "summary")
    )
    raw_facts: list[dict[str, Any]] = []
    active_topic = ""
    last_question_text = ""
    for item in normalized_items:
        ikind = item.get("kind", "")
        itext = (item.get("text") or "").strip()
        if ikind in ("topic", "heading") and itext:
            active_topic = itext
            last_question_text = ""
        elif (
            (ikind == "question" and itext and not (item.get("answer") or "").strip())
            or (
                ikind in ("point", "summary")
                and qa_question_only_re.match(itext)
                and not qa_inline_re.match(itext)
            )
        ):
            last_question_text = itext
            if ikind in ("point", "summary"):
                continue
        elif ikind == "answer" and last_question_text:
            item = dict(item, _question_text=last_question_text)
            if active_topic and not (item.get("topic") or "").strip():
                item["topic"] = active_topic
            if "id" in item:
                items_by_id[item["id"]] = item
            last_question_text = ""
        elif ikind in ("point", "summary", "question"):
            new_item = dict(item)
            if last_question_text and not new_item.get("_question_text"):
                new_item["_question_text"] = last_question_text
                last_question_text = ""
            if (
                not (new_item.get("topic") or "").strip()
                and not (new_item.get("context") or "").strip()
                and active_topic
            ):
                new_item["topic"] = active_topic
            item = new_item
            if "id" in item:
                items_by_id[item["id"]] = item
        item_facts = extract_relations_from_item(
            item,
            sheet_title=sheet_title,
            sheet_prose=sheet_prose,
            allow_qa=allow_qa,
        )
        raw_facts.extend(item_facts)

    facts_out: list[dict[str, Any]] = []
    priorities: dict[str, int] = {}
    for idx, rf in enumerate(raw_facts, start=1):
        fid = f"F{idx}"
        obj_lower = rf["object"].lower()
        in_practice = 1 if (len(obj_lower) >= 3 and obj_lower in practice_text) else 0
        priorities[fid] = rf.get("priority", 1) + in_practice
        fact_dict: dict[str, Any] = {
            "id": fid,
            "item_id": rf["item_id"],
            "page": rf["page"],
            "source_text": rf["source_text"],
            "subject": rf["subject"],
            "relation": rf["relation"],
            "object": rf["object"],
            "entities": rf["entities"],
            "category": rf["category"],
        }
        if "meta" in rf:
            fact_dict["meta"] = rf["meta"]
        facts_out.append(fact_dict)

    valid_candidates: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    rejected_cards: list[dict[str, Any]] = []
    seen_subject_answers: set[tuple[str, str]] = set()

    for order_idx, fact_entry in enumerate(facts_out):
        cand = generate_card(fact_entry, card_id="TEMP", max_clue_words=max_clue_words)
        cand["relation"] = fact_entry.get("relation", "")
        reasons = validate_card(
            cand,
            items_by_id,
            sheet_vocab,
            seen_subject_answers,
            max_clue_words=max_clue_words,
        )
        if not reasons:
            subj_key = canonicalize_subject(fact_entry["subject"])
            norm_ans = re.sub(r"[^a-z0-9½¾¼]+", " ", fact_entry["object"].lower()).strip()
            seen_subject_answers.add((subj_key, norm_ans))
            prio = priorities.get(fact_entry["id"], 1)
            cand["_priority"] = prio
            valid_candidates.append((prio, order_idx, cand, fact_entry))
        else:
            rejected_cards.append(
                {
                    "front": cand["front"],
                    "answer": cand["answer"],
                    "reasons": reasons,
                }
            )

    if len(valid_candidates) > max_cards:
        ranked = sorted(valid_candidates, key=lambda x: (-x[0], x[1]))
        kept_indices = {x[1] for x in ranked[:max_cards]}
        selected = []
        for _prio, order_idx, cand, _fact_entry in valid_candidates:
            if order_idx in kept_indices:
                selected.append(cand)
            else:
                rejected_cards.append(
                    {
                        "front": cand["front"],
                        "answer": cand["answer"],
                        "reasons": ["below_selection_priority_cutoff"],
                    }
                )
    else:
        selected = [x[2] for x in valid_candidates]

    if 3 <= len(selected) < max_cards:
        facts_by_id = {f["id"]: f for f in facts_out}
        existing_fronts = {c["front"].lower() for c in selected}
        reinforcements_added = 0
        max_reinforcements = min(2, max_cards - len(selected))
        snapshot = list(enumerate(selected))
        for _prim_idx_orig, prim_card in snapshot:
            if reinforcements_added >= max_reinforcements or len(selected) >= max_cards:
                break
            fact_obj = facts_by_id.get(prim_card.get("fact_id", ""))
            if not fact_obj:
                continue
            rev_card = generate_reinforcement_card(fact_obj, card_id="TEMP_REV")
            if not rev_card:
                continue
            rev_card["relation"] = fact_obj.get("relation", "")
            if rev_card["front"].lower() in existing_fronts:
                continue
            reasons = validate_card(
                rev_card,
                items_by_id,
                sheet_vocab,
                seen_subject_answers,
                max_clue_words=max_clue_words,
            )
            if reasons:
                continue
            cur_prim_idx = next((i for i, c in enumerate(selected) if c is prim_card), -1)
            if cur_prim_idx == -1:
                continue
            target_page = prim_card["page"]
            insert_pos = len(selected)
            for idx_s in range(cur_prim_idx + 1, len(selected)):
                if selected[idx_s]["page"] > target_page:
                    insert_pos = idx_s
                    break
            if insert_pos - cur_prim_idx >= 3:
                subj_key = canonicalize_subject(rev_card["subject"])
                norm_ans = re.sub(r"[^a-z0-9½¾¼]+", " ", rev_card["answer"].lower()).strip()
                seen_subject_answers.add((subj_key, norm_ans))
                existing_fronts.add(rev_card["front"].lower())
                selected.insert(insert_pos, rev_card)
                reinforcements_added += 1

    def _is_year_date_card(c: dict[str, Any]) -> bool:
        return c.get("question_type") == "WHEN" or c.get("prompt") in (
            "Which year fits the gap?",
            "Which date fits the gap?",
            "Which century fits the gap?",
            "Give the date or year",
        )

    def _find_or_build_non_year_swap(
        year_card: dict[str, Any],
        existing_fronts_set: set[str],
    ) -> dict[str, Any] | None:
        iid = year_card.get("item_id", "")
        item_obj = items_by_id.get(iid) or {}
        subj = year_card.get("subject") or year_card.get("label") or "Study sheet"
        src_line = (year_card.get("source_text") or item_obj.get("text") or "").strip()
        full_text = (item_obj.get("text") or src_line).strip()
        bold_list = item_obj.get("bold") or []

        for f_cand in facts_out:
            if f_cand["item_id"] != iid or f_cand.get("category") == "date":
                continue
            cand_card = generate_card(f_cand, card_id="TEMP_SWAP", max_clue_words=max_clue_words)
            cand_card["relation"] = f_cand.get("relation", "")
            opts = [cand_card] + [
                dict(
                    cand_card,
                    front=alt["front"],
                    prompt=alt["prompt"],
                    question_type=alt["question_type"],
                    answer=alt.get("answer", cand_card["answer"]),
                    label=alt.get("label", cand_card["label"]),
                    subject=alt.get("subject", cand_card["subject"]),
                )
                for alt in (cand_card.get("_alternatives") or [])
            ]
            for opt_c in opts:
                if _is_year_date_card(opt_c):
                    continue
                if opt_c["front"].lower() in existing_fronts_set:
                    continue
                if not validate_card(
                    opt_c,
                    items_by_id,
                    sheet_vocab,
                    seen_subject_answers,
                    max_clue_words=max_clue_words,
                ):
                    return opt_c

        candidate_spans: list[str] = []
        for b_tok in bold_list:
            b_clean = (b_tok or "").strip(" .,;:")
            if b_clean and b_clean != year_card.get("answer"):
                candidate_spans.append(b_clean)

        non_date_expr_types = (
            "organisation_document_event",
            "title_epithet",
            "named_entity",
            "proper_name",
            "place",
            "place_location",
            "city_location",
            "river",
            "river_location",
            "role_person",
            "person_or_title",
            "chemical_formula",
            "physics_math_formula",
            "formula",
            "measurement_unit",
            "area_volume_unit",
            "geography_measure",
            "unit_conversion",
            "plain_or_grouped_number",
            "indian_number",
            "percentage",
            "percentage_fraction_ratio",
            "fraction",
            "ratio",
            "money",
            "count_with_noun",
            "duration",
            "duration_span",
            "defined_term",
            "classification_item",
        )
        cap_after_verb_re = re.compile(
            r"\b(?:founded|co-founded|established|started|co-started|opened|launched|co-launched|"
            r"built|formed|created|wrote|authored|published|edited|signed|passed|enacted|led|"
            r"chaired|presided\s+over|at|in|to|from|near|called|known\s+as)\s+"
            r"(?:the\s+|an?\s+)?(?:(?:book|newspaper|journal|weekly|work|city|town|port|state)\s+(?:of\s+)?)?"
            r"([A-Z][A-Za-z0-9'’\s-]{1,35}?)"
            r"(?=\s+(?:in|on|at|during|by|to|for|and|which|that)\b|[.,;()]|$)"
        )
        obj_before_year_re = re.compile(
            r"\b(?:founded|established|started|opened|built|formed|created|signed|passed|launched|wrote|published)\s+"
            r"(?:the\s+|an?\s+)?([a-z][a-z\s-]{2,28}?)\s+(?:in|on|at|during)\b"
        )
        subj_np_re = re.compile(
            r"^(?:The|An?)\s+([A-Za-z][A-Za-z\s-]{2,30}?)\s+"
            r"(?:was|were|began|opened|started|ended|took|signed|founded|established)\b"
        )
        for text_surface in (src_line, full_text):
            if not text_surface:
                continue
            exprs = find_all_expressions(text_surface)
            for t_name in non_date_expr_types:
                for sp in exprs:
                    if sp["type"] == t_name:
                        candidate_spans.append(sp["text"].strip(" .,;:"))

            for m_q in re.finditer(r"['‘\"“]([A-Z][A-Za-z0-9'’\s-]{1,35})['’\"”]", text_surface):
                candidate_spans.append(m_q.group(1).strip())

            for m_cap in cap_after_verb_re.finditer(text_surface):
                candidate_spans.append(m_cap.group(1).strip())

            for m_prop in re.finditer(
                r"\b([A-Z][A-Za-z'’-]+(?:\s+(?:of|the|and|[A-Z][A-Za-z'’-]+)){0,3})\b",
                text_surface,
            ):
                cand_p = m_prop.group(1).strip()
                if m_prop.start() > 0 or len(cand_p.split()) >= 2:
                    candidate_spans.append(cand_p)

            for m_obj in obj_before_year_re.finditer(text_surface):
                candidate_spans.append(m_obj.group(1).strip())

            m_subj_np = subj_np_re.match(text_surface)
            if m_subj_np:
                candidate_spans.append(m_subj_np.group(1).strip())

        seen_cands: set[str] = set()
        for raw_span in candidate_spans:
            sp_clean = (raw_span or "").strip(" .,;:")
            if not sp_clean or sp_clean.lower() in seen_cands:
                continue
            seen_cands.add(sp_clean.lower())
            sp_clean = expand_substance_with_formula(sp_clean, src_line, full_text)
            if (
                sp_clean
                and sp_clean[0].isupper()
                and not any(ch.isdigit() for ch in sp_clean)
                and "=" not in sp_clean
            ):
                sp_clean = expand_multiword_proper_name(sp_clean, src_line, full_text)
            if (
                not sp_clean
                or sp_clean.lower() == subj.lower()
                or sp_clean == year_card.get("answer")
                or not (1 <= len(sp_clean.split()) <= 6)
            ):
                continue
            info_c = classify_answer_entity(sp_clean, "GAP_CUSTOM", bold_list)
            if info_c["category"] == "date":
                continue
            if info_c["category"] == "person":
                sp_clean = expand_full_person_name(sp_clean, src_line, full_text, item_obj.get("topic", ""))
            use_line = src_line if sp_clean in src_line else full_text
            synth_fact = {
                "id": f"{year_card.get('fact_id', 'F')}_SWAP",
                "item_id": iid,
                "page": year_card.get("page", 1),
                "source_text": use_line,
                "subject": subj,
                "relation": "GAP_CUSTOM",
                "object": sp_clean,
                "category": info_c["category"],
            }
            swap_cand = generate_card(synth_fact, card_id="TEMP_SWAP", max_clue_words=max_clue_words)
            swap_cand["relation"] = "GAP_CUSTOM"
            if _is_year_date_card(swap_cand):
                continue
            if swap_cand["front"].lower() in existing_fronts_set:
                continue
            if not validate_card(
                swap_cand,
                items_by_id,
                sheet_vocab,
                seen_subject_answers,
                max_clue_words=max_clue_words,
            ):
                return swap_cand

        return None

    def _enforce_year_cap_by_swapping(cards_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if len(cards_list) < 3:
            return cards_list
        max_year_cards = int(len(cards_list) * 0.40)
        year_indices = [i for i, c in enumerate(cards_list) if _is_year_date_card(c)]
        if len(year_indices) <= max_year_cards:
            return cards_list

        existing_fronts_set = {c["front"].lower() for c in cards_list}
        excess_count = len(year_indices) - max_year_cards

        candidate_year_order = list(reversed(year_indices[max_year_cards:])) + list(
            reversed(year_indices[:max_year_cards])
        )
        swapped_so_far = 0
        for y_idx in candidate_year_order:
            if swapped_so_far >= excess_count:
                break
            y_card = cards_list[y_idx]
            swap_card = _find_or_build_non_year_swap(y_card, existing_fronts_set)
            if swap_card is not None:
                subj_key = canonicalize_subject(swap_card["subject"])
                norm_ans = re.sub(r"[^a-z0-9½¾¼]+", " ", swap_card["answer"].lower()).strip()
                seen_subject_answers.add((subj_key, norm_ans))
                existing_fronts_set.add(swap_card["front"].lower())
                cards_list[y_idx] = swap_card
                swapped_so_far += 1

        year_indices_after = [i for i, c in enumerate(cards_list) if _is_year_date_card(c)]
        if len(year_indices_after) > max_year_cards:
            item_counts: dict[str, int] = {}
            for c in cards_list:
                iid = c.get("item_id", "")
                item_counts[iid] = item_counts.get(iid, 0) + 1
            drop_set: set[int] = set()
            for y_idx in reversed(year_indices_after):
                if len(year_indices_after) - len(drop_set) <= max_year_cards:
                    break
                iid = cards_list[y_idx].get("item_id", "")
                if item_counts.get(iid, 1) > 1:
                    drop_set.add(y_idx)
                    item_counts[iid] -= 1
            if drop_set:
                kept_cards = []
                for i, c in enumerate(cards_list):
                    if i in drop_set:
                        rejected_cards.append(
                            {
                                "front": c["front"],
                                "answer": c["answer"],
                                "reasons": ["year_share_cap_40pct"],
                            }
                        )
                    else:
                        kept_cards.append(c)
                cards_list = kept_cards

        return cards_list

    def _try_switch_card_direction(card_obj: dict[str, Any], target_is_gap: bool) -> bool:
        for alt in card_obj.get("_alternatives") or []:
            alt_is_gap = "______" in alt["front"]
            if alt_is_gap == target_is_gap:
                test_c = dict(
                    card_obj,
                    front=alt["front"],
                    prompt=alt["prompt"],
                    question_type=alt["question_type"],
                    answer=alt.get("answer", card_obj["answer"]),
                    label=alt.get("label", card_obj["label"]),
                    subject=alt.get("subject", card_obj["subject"]),
                )
                if not validate_card(
                    test_c,
                    items_by_id,
                    sheet_vocab,
                    set(),
                    max_clue_words=max_clue_words,
                ):
                    card_obj["front"] = test_c["front"]
                    card_obj["prompt"] = test_c["prompt"]
                    card_obj["question_type"] = test_c["question_type"]
                    card_obj["answer"] = test_c["answer"]
                    card_obj["label"] = test_c["label"]
                    card_obj["subject"] = test_c["subject"]
                    return True
        if not target_is_gap and "______" in card_obj["front"]:
            # Synthesize a direct question from the gap sentence using only printed words + 'what'
            raw_front = card_obj["front"].strip()
            if raw_front.startswith("______"):
                q_front = "What" + raw_front[6:].rstrip(".") + "?"
            else:
                q_front = raw_front.replace("______", "what", 1).rstrip(".") + "?"
            test_q = dict(
                card_obj,
                front=q_front,
                prompt="",
                question_type="WHAT",
            )
            if not validate_card(
                test_q,
                items_by_id,
                sheet_vocab,
                set(),
                max_clue_words=max_clue_words,
            ):
                card_obj["front"] = q_front
                card_obj["prompt"] = ""
                card_obj["question_type"] = "WHAT"
                return True
        return False

    def _enforce_max_two_per_answer(cards_list: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_answer: dict[str, list[int]] = {}
        for idx, c in enumerate(cards_list):
            norm_a = re.sub(r"[^a-z0-9½¾¼]+", " ", c["answer"].lower()).strip()
            if norm_a:
                by_answer.setdefault(norm_a, []).append(idx)

        drop_indices: set[int] = set()
        for _norm_a, idxs in by_answer.items():
            if len(idxs) <= 2:
                continue
            q_idxs = [i for i in idxs if "______" not in cards_list[i]["front"]]
            g_idxs = [i for i in idxs if "______" in cards_list[i]["front"]]
            q_ranked = sorted(q_idxs, key=lambda i: (-cards_list[i].get("_priority", 1), i))
            g_ranked = sorted(g_idxs, key=lambda i: (-cards_list[i].get("_priority", 1), i))

            if q_ranked and g_ranked:
                keep_pair = {q_ranked[0], g_ranked[0]}
            else:
                all_ranked = sorted(idxs, key=lambda i: (-cards_list[i].get("_priority", 1), i))
                keep_list = sorted(all_ranked[:2])
                keep_pair = set(keep_list)
                # Ensure the 2 kept cards are in different directions (one question, one gap)
                c0_gap = "______" in cards_list[keep_list[0]]["front"]
                c1_gap = "______" in cards_list[keep_list[1]]["front"]
                if c0_gap == c1_gap:
                    target_gap = not c0_gap
                    if not _try_switch_card_direction(cards_list[keep_list[1]], target_gap):
                        _try_switch_card_direction(cards_list[keep_list[0]], target_gap)

            for i in idxs:
                if i not in keep_pair:
                    drop_indices.add(i)

        if not drop_indices:
            return cards_list

        kept_out: list[dict[str, Any]] = []
        for idx, c in enumerate(cards_list):
            if idx in drop_indices:
                rejected_cards.append(
                    {
                        "front": c["front"],
                        "answer": c["answer"],
                        "reasons": ["answer_repeated_more_than_twice"],
                    }
                )
            else:
                kept_out.append(c)
        return kept_out

    selected = _enforce_max_two_per_answer(selected)

    selected = _enforce_year_cap_by_swapping(selected)

    selected = balance_question_mix(
        selected,
        validate_fn=lambda alt_card: validate_card(
            alt_card,
            items_by_id,
            sheet_vocab,
            set(),
            max_clue_words=max_clue_words,
        ),
    )

    non_table_count = sum(1 for c in selected if c["question_type"] != "TABLE")
    if non_table_count > 0:
        max_table_total = max(1, len(selected) // 3)
        table_indices = [i for i, c in enumerate(selected) if c["question_type"] == "TABLE"]
        if len(table_indices) > max_table_total:
            drop_set = set(table_indices[max_table_total:])
            kept_selected = []
            for i, c in enumerate(selected):
                if i in drop_set:
                    rejected_cards.append(
                        {
                            "front": c["front"],
                            "answer": c["answer"],
                            "reasons": ["table_share_cap"],
                        }
                    )
                else:
                    kept_selected.append(c)
            selected = kept_selected

    selected = _enforce_year_cap_by_swapping(selected)

    accepted_cards: list[dict[str, Any]] = []
    key_fact_cards: list[KeyFactCard] = []
    for c_idx, cand in enumerate(selected, start=1):
        cand.pop("_priority", None)
        kf_card = _to_key_fact_card(cand, items_by_id)
        key_fact_cards.append(kf_card)
        accepted_cards.append(
            {
                "id": f"C{c_idx}",
                "fact_id": cand["fact_id"],
                "item_id": cand["item_id"],
                "page": cand["page"],
                "label": cand["label"],
                "front": cand["front"],
                "prompt": cand["prompt"],
                "answer": cand["answer"],
                "question_type": cand["question_type"],
                "source_text": cand["source_text"],
                "status": "accepted",
                "kind": kf_card.kind,
                "question": kf_card.question,
                "clue": kf_card.clue,
                "about": kf_card.about,
                "checks": list(kf_card.checks),
                "unit_ids": list(kf_card.unit_ids),
            }
        )

    return {
        "sheet": sheet_name,
        "facts": facts_out,
        "cards": accepted_cards,
        "rejected": rejected_cards,
        "_key_fact_cards": key_fact_cards,
        "_notes": parent_notes,
    }


def plan_key_facts_with_notes(
    items: Sequence[Any],
    standard: int = 8,
) -> tuple[list[KeyFactCard], tuple[str, ...]]:
    """Plan Key Facts study cards and parent notes from a sequence of Learn reader Item objects."""
    max_clue_words = _validate_standard(standard)
    item_dicts = [_item_to_dict(item, idx) for idx, item in enumerate(items, start=1)]
    res = _execute_pipeline(
        item_dicts,
        sheet_name="",
        max_cards=30,
        max_clue_words=max_clue_words,
    )
    return list(res["_key_fact_cards"]), tuple(res["_notes"])


def plan_key_facts(items: Sequence[Any], standard: int = 8) -> list[KeyFactCard]:
    """Plan Key Facts study cards from a sequence of Learn reader Item objects."""
    cards, _notes = plan_key_facts_with_notes(items, standard=standard)
    return cards


def run_pipeline(reader_json: dict[str, Any], max_cards: int = 30) -> dict[str, Any]:
    """Convert reader JSON dictionaries into reader Item objects and return the JSON result."""
    sheet_name = reader_json.get("sheet", "")
    raw_items = reader_json.get("items", [])
    reader_items = [_dict_to_reader_item(it, idx) for idx, it in enumerate(raw_items, start=1)]
    item_dicts = [_item_to_dict(it, idx) for idx, it in enumerate(reader_items, start=1)]
    res = _execute_pipeline(item_dicts, sheet_name=sheet_name, max_cards=max_cards)
    return {
        "sheet": res["sheet"],
        "facts": res["facts"],
        "cards": res["cards"],
        "rejected": res["rejected"],
    }
