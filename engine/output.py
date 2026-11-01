"""
Stage 6: output.py
Stable JSON interface assembly and priority-based selection (max 30 cards per sheet).
Prefers: bold words; core facts (names+roles, dates, titles, places, defined terms, formulas);
facts the sheet's own practice questions ask about. Spreads cards across all topics and pages.
"""
from __future__ import annotations
import re
from typing import Dict, List, Any, Set, Tuple
from .relations import extract_relations_from_item
from .questions import generate_card
from .validate import build_sheet_vocabulary, validate_card
from .facts import canonicalize_subject


def collect_practice_signals(items: List[Dict[str, Any]]) -> str:
    """Collect text from the sheet's own practice questions/answers to boost importance."""
    chunks: List[str] = []
    for it in items:
        if it.get("kind") in ("question", "answer") or it.get("section") in ("questions", "answers", "qa"):
            chunks.append(it.get("text", "") or "")
            chunks.append(it.get("answer", "") or "")
    return " ".join(chunks).lower()


def run_pipeline(reader_json: Dict[str, Any], max_cards: int = 30) -> Dict[str, Any]:
    """Run all 6 stages deterministically on a reader_json dict and return the output dict."""
    sheet_name = reader_json.get("sheet", "")
    items = reader_json.get("items", [])
    items_by_id: Dict[str, Dict[str, Any]] = {it["id"]: it for it in items if "id" in it}
    sheet_vocab = build_sheet_vocabulary(reader_json)
    practice_text = collect_practice_signals(items)

    # Stage 1-3: Extract facts from items
    raw_facts: List[Dict[str, Any]] = []
    for item in items:
        item_facts = extract_relations_from_item(item)
        raw_facts.extend(item_facts)

    facts_out: List[Dict[str, Any]] = []
    priorities: Dict[str, int] = {}
    for idx, rf in enumerate(raw_facts, start=1):
        fid = f"F{idx}"
        obj_lower = rf["object"].lower()
        in_practice = 1 if (len(obj_lower) >= 3 and obj_lower in practice_text) else 0
        priorities[fid] = rf.get("priority", 1) + in_practice
        facts_out.append({
            "id": fid,
            "item_id": rf["item_id"],
            "page": rf["page"],
            "source_text": rf["source_text"],
            "subject": rf["subject"],
            "relation": rf["relation"],
            "object": rf["object"],
            "entities": rf["entities"],
            "category": rf["category"],
        })

    # Stage 4 & 5: Validate all candidate cards first
    valid_candidates: List[Tuple[int, int, Dict[str, Any], Dict[str, Any]]] = []
    rejected_cards: List[Dict[str, Any]] = []
    seen_subject_answers: Set[Tuple[str, str]] = set()

    for order_idx, fact_entry in enumerate(facts_out):
        cand = generate_card(fact_entry, card_id="TEMP")
        reasons = validate_card(cand, items_by_id, sheet_vocab, seen_subject_answers)
        if not reasons:
            subj_key = canonicalize_subject(fact_entry["subject"])
            norm_ans = re.sub(r"[^a-z0-9]+", " ", fact_entry["object"].lower()).strip()
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
        # Sort by (-priority, order_idx)
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
