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
    regular_note_count = 0
    qa_item_count = 0
    for it in items:
        ik = it.get("kind", "")
        isec = (it.get("section") or "").strip()
        itxt = (it.get("text") or "").strip()
        if ik in ("question", "answer") or isec in ("questions", "answers", "qa") or qa_inline_re.match(itxt):
            qa_item_count += 1
        elif ik in ("point", "summary", "table") and itxt:
            regular_note_count += 1

    allow_qa = qa_item_count > 0 and (regular_note_count <= 5 or qa_item_count >= regular_note_count)

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
        elif ikind == "question" and itext and not (item.get("answer") or "").strip():
            last_question_text = itext
        elif ikind == "answer" and last_question_text:
            item = dict(item, _question_text=last_question_text)
            if active_topic and not (item.get("topic") or "").strip():
                item["topic"] = active_topic
            if "id" in item:
                items_by_id[item["id"]] = item
        elif ikind in ("point", "summary", "question") and not (item.get("topic") or "").strip() and not (item.get("context") or "").strip() and active_topic:
            item = dict(item, topic=active_topic)
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
