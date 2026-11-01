"""
Stage 6: output.py
Stable JSON interface assembly, priority-based selection (max 30 cards per sheet),
and Step 4 question-type mixing (no question_type > 60% and no more than 3 in a row).
"""
from __future__ import annotations

import re
from typing import Dict, List, Any, Set, Tuple

from .relations import extract_relations_from_item
from .questions import generate_card, generate_reinforcement_card, balance_question_mix
from .validate import build_sheet_vocabulary, validate_card
from .facts import canonicalize_subject, resolve_sheet_title
from .expressions import FAMILY_L


def collect_practice_signals(items: List[Dict[str, Any]]) -> str:
    """Collect text and Family L keywords from the sheet's own practice questions/answers to boost importance."""
    chunks: List[str] = []
    for it in items:
        if it.get("kind") in ("question", "answer") or it.get("section") in ("questions", "answers", "qa"):
            q_text = it.get("text", "") or ""
            a_text = it.get("answer", "") or ""
            chunks.append(q_text)
            chunks.append(a_text)
            for m_l in FAMILY_L.find(q_text):
                chunks.extend(m_l.get("keywords") or [])
    return " ".join(chunks).lower()


def run_pipeline(reader_json: Dict[str, Any], max_cards: int = 30) -> Dict[str, Any]:
    """Run all 6 stages deterministically on a reader_json dict and return the output dict."""
    sheet_name = reader_json.get("sheet", "")
    items = reader_json.get("items", [])
    items_by_id: Dict[str, Dict[str, Any]] = {it["id"]: it for it in items if "id" in it}
    sheet_vocab = build_sheet_vocabulary(reader_json)
    practice_text = collect_practice_signals(items)
    sheet_title = resolve_sheet_title(reader_json)

    # Stage 1-3: Extract facts from items (propagating active topic/heading to points under it)
    qa_inline_re = re.compile(
        r"^(?:(?:Q(?:uestion)?\.?\s*\d*|\d+)[.):]?\s*.+?\?\s*)?(?:Model\s+)?(?:Answer|Ans)\.?\s*[:—-]\s*.+$",
        re.IGNORECASE,
    )
    qa_question_only_re = re.compile(
        r"^(?:(?:Q(?:uestion)?\.?\s*\d+|\(\d+\)|\d+[.)])\s+.+\?|(?:Who|What|When|Where|Which|Why|How|Name|State|Define|Mention|Give)\b.+\?)$",
        re.IGNORECASE,
    )
    regular_note_count = 0
    qa_item_count = 0
    for it in items:
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
        (it.get("text") or "").strip()
        for it in items
        if it.get("kind") in ("point", "summary")
    )
    raw_facts: List[Dict[str, Any]] = []
    active_topic = ""
    last_question_text = ""
    for item in items:
        ikind = item.get("kind", "")
        itext = (item.get("text") or "").strip()
        if ikind in ("topic", "heading") and itext:
            active_topic = itext
            last_question_text = ""
        elif (
            (ikind == "question" and itext and not (item.get("answer") or "").strip())
            or (ikind in ("point", "summary") and qa_question_only_re.match(itext) and not qa_inline_re.match(itext))
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
            if not (new_item.get("topic") or "").strip() and not (new_item.get("context") or "").strip() and active_topic:
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

    facts_out: List[Dict[str, Any]] = []
    priorities: Dict[str, int] = {}
    for idx, rf in enumerate(raw_facts, start=1):
        fid = f"F{idx}"
        obj_lower = rf["object"].lower()
        in_practice = 1 if (len(obj_lower) >= 3 and obj_lower in practice_text) else 0
        priorities[fid] = rf.get("priority", 1) + in_practice
        fact_dict: Dict[str, Any] = {
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

    # Stage 4 & 5: Validate all candidate cards first
    valid_candidates: List[Tuple[int, int, Dict[str, Any], Dict[str, Any]]] = []
    rejected_cards: List[Dict[str, Any]] = []
    seen_subject_answers: Set[Tuple[str, str]] = set()

    for order_idx, fact_entry in enumerate(facts_out):
        cand = generate_card(fact_entry, card_id="TEMP")
        reasons = validate_card(cand, items_by_id, sheet_vocab, seen_subject_answers)
        if not reasons:
            subj_key = canonicalize_subject(fact_entry["subject"])
            norm_ans = re.sub(r"[^a-z0-9½¾¼]+", " ", fact_entry["object"].lower()).strip()
            seen_subject_answers.add((subj_key, norm_ans))
            prio = priorities.get(fact_entry["id"], 1)
            valid_candidates.append((prio, order_idx, cand, fact_entry))
        else:
            rejected_cards.append({
                "front": cand["front"],
                "answer": cand["answer"],
                "reasons": reasons,
            })

    # Selection: if more than max_cards valid candidates exist, keep highest priority while preserving sheet order
    if len(valid_candidates) > max_cards:
        ranked = sorted(valid_candidates, key=lambda x: (-x[0], x[1]))
        kept_indices = {x[1] for x in ranked[:max_cards]}
        selected = []
        for prio, order_idx, cand, fact_entry in valid_candidates:
            if order_idx in kept_indices:
                selected.append(cand)
            else:
                rejected_cards.append({
                    "front": cand["front"],
                    "answer": cand["answer"],
                    "reasons": ["below_selection_priority_cutoff"],
                })
    else:
        selected = [x[2] for x in valid_candidates]

    # Change G: Reinforcement — a core fact may get up to 2 cards asking from different directions,
    # never the same question or gap twice, at least 3 cards apart, both counting toward the 30-card cap.
    if 3 <= len(selected) < max_cards:
        facts_by_id = {f["id"]: f for f in facts_out}
        existing_fronts = {c["front"].lower() for c in selected}
        reinforcements_added = 0
        max_reinforcements = min(2, max_cards - len(selected))
        snapshot = list(enumerate(selected))
        for prim_idx_orig, prim_card in snapshot:
            if reinforcements_added >= max_reinforcements or len(selected) >= max_cards:
                break
            fact_obj = facts_by_id.get(prim_card.get("fact_id", ""))
            if not fact_obj:
                continue
            rev_card = generate_reinforcement_card(fact_obj, card_id="TEMP_REV")
            if not rev_card:
                continue
            if rev_card["front"].lower() in existing_fronts:
                continue
            reasons = validate_card(rev_card, items_by_id, sheet_vocab, seen_subject_answers)
            if reasons:
                continue
            # Find current index of prim_card and end of its page block
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

    # Fix 2 (Round 5): Year/date limit (<= 40%) must SWAP, not DROP:
    # if a line's year card is over the limit, make a card from another key fact in that line
    # (organisation, place, title, book, number) instead. Every point that had a card in Round 3 must still have one.
    def _is_year_date_card(c: Dict[str, Any]) -> bool:
        return c.get("question_type") == "WHEN" or c.get("prompt") in (
            "Which year fits the gap?",
            "Which date fits the gap?",
            "Which century fits the gap?",
            "Give the date or year",
        )

    def _find_or_build_non_year_swap(
        year_card: Dict[str, Any],
        existing_fronts_set: Set[str],
    ) -> Dict[str, Any] | None:
        from .entities import (
            classify_answer_entity,
            expand_full_person_name,
            expand_multiword_proper_name,
            expand_substance_with_formula,
            find_all_expressions,
        )

        iid = year_card.get("item_id", "")
        item_obj = items_by_id.get(iid) or {}
        subj = year_card.get("subject") or year_card.get("label") or "Study sheet"
        src_line = (year_card.get("source_text") or item_obj.get("text") or "").strip()
        full_text = (item_obj.get("text") or src_line).strip()
        bold_list = item_obj.get("bold") or []

        # 1. Check existing non-date facts extracted for this item_id in facts_out
        for f_cand in facts_out:
            if f_cand["item_id"] != iid or f_cand.get("category") == "date":
                continue
            cand_card = generate_card(f_cand, card_id="TEMP_SWAP")
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
                if not validate_card(opt_c, items_by_id, sheet_vocab, seen_subject_answers):
                    return opt_c

        # 2. Extract another key fact from the same line (organisation, place, title, book, number, person, term)
        candidate_spans: List[str] = []
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
        for text_surface in (src_line, full_text):
            if not text_surface:
                continue
            exprs = find_all_expressions(text_surface)
            for t_name in non_date_expr_types:
                for sp in exprs:
                    if sp["type"] == t_name:
                        candidate_spans.append(sp["text"].strip(" .,;:"))

            # Quoted book/newspaper/work titles
            for m_q in re.finditer(r"['‘\"“]([A-Z][A-Za-z0-9'’\s-]{1,35})['’\"”]", text_surface):
                candidate_spans.append(m_q.group(1).strip())

            # Capitalised name/place/book/organisation after verb or preposition
            for m_cap in re.finditer(
                r"\b(?:founded|co-founded|established|started|co-started|opened|launched|co-launched|built|formed|created|wrote|authored|published|edited|signed|passed|enacted|led|chaired|presided\s+over|at|in|to|from|near|called|known\s+as)\s+(?:the\s+|an?\s+)?(?:(?:book|newspaper|journal|weekly|work|city|town|port|state)\s+(?:of\s+)?)?([A-Z][A-Za-z0-9'’\s-]{1,35}?)(?=\s+(?:in|on|at|during|by|to|for|and|which|that)\b|[.,;()]|$)",
                text_surface,
            ):
                candidate_spans.append(m_cap.group(1).strip())

            # Any other capitalised proper noun phrase in the line (not at index 0 unless followed by another Cap word)
            for m_prop in re.finditer(r"\b([A-Z][A-Za-z'’-]+(?:\s+(?:of|the|and|[A-Z][A-Za-z'’-]+)){0,3})\b", text_surface):
                cand_p = m_prop.group(1).strip()
                if m_prop.start() > 0 or len(cand_p.split()) >= 2:
                    candidate_spans.append(cand_p)

            # Object noun phrase after verb before year/date
            for m_obj in re.finditer(
                r"\b(?:founded|established|started|opened|built|formed|created|signed|passed|launched|wrote|published)\s+(?:the\s+|an?\s+)?([a-z][a-z\s-]{2,28}?)\s+(?:in|on|at|during)\b",
                text_surface,
            ):
                candidate_spans.append(m_obj.group(1).strip())

            # Subject noun phrase before verb when topic is generic (e.g. 'The western railway began in 1830.')
            m_subj_np = re.match(
                r"^(?:The|An?)\s+([A-Za-z][A-Za-z\s-]{2,30}?)\s+(?:was|were|began|opened|started|ended|took|signed|founded|established)\b",
                text_surface,
            )
            if m_subj_np:
                candidate_spans.append(m_subj_np.group(1).strip())

        seen_cands: Set[str] = set()
        for raw_span in candidate_spans:
            sp_clean = (raw_span or "").strip(" .,;:")
            if not sp_clean or sp_clean.lower() in seen_cands:
                continue
            seen_cands.add(sp_clean.lower())
            sp_clean = expand_substance_with_formula(sp_clean, src_line, full_text)
            if sp_clean and sp_clean[0].isupper() and not any(ch.isdigit() for ch in sp_clean) and "=" not in sp_clean:
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
            swap_cand = generate_card(synth_fact, card_id="TEMP_SWAP")
            if _is_year_date_card(swap_cand):
                continue
            if swap_cand["front"].lower() in existing_fronts_set:
                continue
            if not validate_card(swap_cand, items_by_id, sheet_vocab, seen_subject_answers):
                return swap_cand

        return None

    def _enforce_year_cap_by_swapping(cards_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(cards_list) < 3:
            return cards_list
        max_year_cards = int(len(cards_list) * 0.40)
        year_indices = [i for i, c in enumerate(cards_list) if _is_year_date_card(c)]
        if len(year_indices) <= max_year_cards:
            return cards_list

        existing_fronts_set = {c["front"].lower() for c in cards_list}
        excess_count = len(year_indices) - max_year_cards

        # Try swapping excess year cards from the end of year_indices first; if an excess year card
        # has no other fact in its line, we can also swap an earlier year card that DOES have another fact.
        candidate_year_order = list(reversed(year_indices[max_year_cards:])) + list(reversed(year_indices[:max_year_cards]))
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

        # If still over the limit (only when lines had literally no other extractable token),
        # only drop a year card if its item_id already has another card in cards_list.
        year_indices_after = [i for i, c in enumerate(cards_list) if _is_year_date_card(c)]
        if len(year_indices_after) > max_year_cards:
            item_counts: Dict[str, int] = {}
            for c in cards_list:
                iid = c.get("item_id", "")
                item_counts[iid] = item_counts.get(iid, 0) + 1
            drop_set: Set[int] = set()
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
                        rejected_cards.append({
                            "front": c["front"],
                            "answer": c["answer"],
                            "reasons": ["year_share_cap_40pct"],
                        })
                    else:
                        kept_cards.append(c)
                cards_list = kept_cards

        return cards_list

    selected = _enforce_year_cap_by_swapping(selected)

    # Step 4: Mix question shapes across selected cards (no type > 60%, no > 3 in a row, >= 3 types)
    selected = balance_question_mix(
        selected,
        validate_fn=lambda alt_card: validate_card(alt_card, items_by_id, sheet_vocab, set()),
    )

    # Change B: Table cards are at most a third of the whole set (when non-table cards also exist)
    non_table_count = sum(1 for c in selected if c["question_type"] != "TABLE")
    if non_table_count > 0:
        max_table_total = max(1, len(selected) // 3)
        table_indices = [i for i, c in enumerate(selected) if c["question_type"] == "TABLE"]
        if len(table_indices) > max_table_total:
            drop_set = set(table_indices[max_table_total:])
            kept_selected = []
            for i, c in enumerate(selected):
                if i in drop_set:
                    rejected_cards.append({
                        "front": c["front"],
                        "answer": c["answer"],
                        "reasons": ["table_share_cap"],
                    })
                else:
                    kept_selected.append(c)
            selected = kept_selected

    selected = _enforce_year_cap_by_swapping(selected)

    accepted_cards: List[Dict[str, Any]] = []
    for c_idx, cand in enumerate(selected, start=1):
        accepted_cards.append({
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
        })

    return {
        "sheet": sheet_name,
        "facts": facts_out,
        "cards": accepted_cards,
        "rejected": rejected_cards,
    }
