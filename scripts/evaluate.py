#!/usr/bin/env python3
"""
scripts/evaluate.py
Evaluates the Learn Key Facts Engine on the 3 real reference study sheets.
Reports:
 - Important-fact recall (core and all)
 - Fact precision (with doubtful facts listed)
 - Question correctness
 - Question clarity (validate.py checks + teacher reword candidates)
 - Duplicate rate
 - Source traceability
"""
from __future__ import annotations
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learn.teaching_engine import key_facts as engine
from learn.teaching_engine.key_facts.facts import canonicalize_subject
from learn.teaching_engine.key_facts.questions import ALLOWED_QUESTION_WORDS
from learn.teaching_engine.key_facts.validate import (
    build_sheet_vocabulary,
    item_contains_answer,
    tokenize_words,
)


SHEETS = [
    ("mumbai-personalities-flat", "data/mumbai-personalities-flat.reader.json", "data/mumbai-personalities-flat.reference_facts.json"),
    ("uk-cities-comparative-table", "data/uk-cities-comparative-table.reader.json", "data/uk-cities-comparative-table.reference_facts.json"),
    ("full-physics-forces", "data/full-physics-forces.reader.json", "data/full-physics-forces.reference_facts.json"),
]


def norm_str(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"^(?:the|a|an)\s+", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def answers_match(card_ans: str, ref_ans: str) -> bool:
    ca = norm_str(card_ans)
    ra = norm_str(ref_ans)
    if not ca or not ra:
        return False
    if ca == ra:
        return True
    # Allow unit suffix or minor prefix match only when core tokens match (e.g. '2.0 m/s²' vs '2.0' or 'industrial steam engine' vs 'steam engine')
    if ca.endswith(" " + ra) or ra.endswith(" " + ca) or ca.startswith(ra + " ") or ra.startswith(ca + " "):
        return True
    return False


def subjects_compatible(card: Dict[str, Any], fact_by_id: Dict[str, Dict[str, Any]], ref: Dict[str, Any]) -> bool:
    """Check whether card is about the same subject as ref."""
    ref_subj = ref.get("subject", "").lower()
    ref_tokens = [t for t in re.findall(r"[a-z0-9]+", ref_subj) if len(t) > 2 and t not in ("the", "for", "and", "with", "before", "using")]
    linked_fact = fact_by_id.get(card.get("fact_id", ""), {})
    haystack = " ".join([
        card.get("label", ""),
        card.get("front", ""),
        linked_fact.get("subject", ""),
        linked_fact.get("relation", ""),
    ]).lower()

    if not ref_tokens:
        return True
    # Check if any meaningful token from ref_subj appears in haystack
    if any(t in haystack for t in ref_tokens):
        return True
    # Also check if cited item matches source_item and answer is unique to that item
    if card.get("item_id") == ref.get("source_item"):
        return True
    return False


def evaluate_sheet(slug: str, reader_path: Path, ref_path: Path) -> Dict[str, Any]:
    with open(reader_path, "r", encoding="utf-8") as f:
        reader_json = json.load(f)
    with open(ref_path, "r", encoding="utf-8") as f:
        ref_json = json.load(f)

    out = engine.run(reader_json)
    cards = out["cards"]
    facts = out["facts"]
    rejected = out["rejected"]
    ref_facts = ref_json["facts"]

    items_by_id = {it["id"]: it for it in reader_json.get("items", []) if "id" in it}
    fact_by_id = {fc["id"]: fc for fc in facts}
    sheet_vocab = build_sheet_vocabulary(reader_json)

    # 1. Important-fact recall (core and all)
    # Use 1-to-1 matching so one card cannot satisfy two different reference facts with identical answers
    used_card_ids = set()
    covered_refs = []
    missed_refs = []

    # Match core facts first, then secondary; prefer exact answer match over substring match
    for importance_pass in ("core", "secondary"):
        for rf in ref_facts:
            if rf.get("importance") != importance_pass:
                continue
            matched_card = None
            # Pass 1: exact normalized answer match
            for c in cards:
                if c["id"] in used_card_ids:
                    continue
                if norm_str(c["answer"]) == norm_str(rf["answer"]) and subjects_compatible(c, fact_by_id, rf):
                    matched_card = c
                    break
            # Pass 2: compatible prefix/suffix answer match
            if not matched_card:
                for c in cards:
                    if c["id"] in used_card_ids:
                        continue
                    if answers_match(c["answer"], rf["answer"]) and subjects_compatible(c, fact_by_id, rf):
                        matched_card = c
                        break
            if matched_card:
                used_card_ids.add(matched_card["id"])
                covered_refs.append({"ref": rf, "card_id": matched_card["id"], "card_answer": matched_card["answer"]})
            else:
                missed_refs.append(rf)

    core_refs = [rf for rf in ref_facts if rf.get("importance") == "core"]
    covered_core_ids = {cr["ref"]["id"] for cr in covered_refs if cr["ref"].get("importance") == "core"}
    core_recall = (len(covered_core_ids) / len(core_refs) * 100.0) if core_refs else 100.0
    all_recall = (len(covered_refs) / len(ref_facts) * 100.0) if ref_facts else 100.0

    # 2. Fact precision: spot-check extracted facts against reference list and sheet item text
    valid_facts = 0
    doubtful_facts = []
    for fc in facts:
        it = items_by_id.get(fc["item_id"])
        in_sheet = bool(it and item_contains_answer(it, fc["object"]))
        matches_ref = any(answers_match(fc["object"], rf["answer"]) for rf in ref_facts)
        if in_sheet and (matches_ref or len(fc["object"].split()) <= 6):
            valid_facts += 1
        else:
            doubtful_facts.append(fc)
    fact_precision = (valid_facts / len(facts) * 100.0) if facts else 0.0

    # 3. Question correctness: answer printed in cited item and answers the front without giveaway
    correct_cards = 0
    incorrect_cards = []
    for c in cards:
        it = items_by_id.get(c["item_id"])
        in_item = bool(it and item_contains_answer(it, c["answer"]))
        no_giveaway = c["answer"].lower() not in c["front"].lower()
        has_q = len(c["front"].strip()) > 3
        if in_item and no_giveaway and has_q:
            correct_cards += 1
        else:
            incorrect_cards.append(c)
    question_correctness = (correct_cards / len(cards) * 100.0) if cards else 0.0

    # 4. Question clarity & invented words check
    clear_cards = 0
    reword_candidates = []
    invented_words_found = []
    for c in cards:
        words = tokenize_words(c["front"])
        inv = [w for w in words if w not in sheet_vocab and w not in ALLOWED_QUESTION_WORDS]
        if inv:
            invented_words_found.extend(inv)
        # Check if a teacher might reword (e.g. very long gap card > 28 words)
        if len(c["front"].split()) > 28:
            reword_candidates.append({"id": c["id"], "front": c["front"], "reason": "long_clause"})
        if not inv and (c["front"].endswith("?") or c["front"].endswith(".") or c["question_type"] == "FORMULA"):
            clear_cards += 1
    question_clarity = (clear_cards / len(cards) * 100.0) if cards else 0.0

    # 5. Duplicate rate
    seen_pairs = set()
    dup_count = 0
    for c in cards:
        fc = fact_by_id.get(c["fact_id"], {})
        subj_key = canonicalize_subject(fc.get("subject") or c["label"])
        ans_key = norm_str(c["answer"])
        pair = (subj_key, ans_key)
        if pair in seen_pairs:
            dup_count += 1
        seen_pairs.add(pair)
    duplicate_rate = (dup_count / len(cards) * 100.0) if cards else 0.0

    # 6. Source traceability
    traceable_count = 0
    for c in cards:
        it = items_by_id.get(c["item_id"])
        if it and it.get("page") == c.get("page") and c.get("source_text"):
            traceable_count += 1
    traceability = (traceable_count / len(cards) * 100.0) if cards else 0.0

    return {
        "slug": slug,
        "sheet": out["sheet"],
        "metrics": {
            "core_recall": round(core_recall, 1),
            "core_covered": len(covered_core_ids),
            "core_total": len(core_refs),
            "all_recall": round(all_recall, 1),
            "all_covered": len(covered_refs),
            "all_total": len(ref_facts),
            "fact_precision": round(fact_precision, 1),
            "question_correctness": round(question_correctness, 1),
            "question_clarity": round(question_clarity, 1),
            "duplicate_rate": round(duplicate_rate, 1),
            "traceability": round(traceability, 1),
            "invented_words_count": len(invented_words_found),
            "invented_words": sorted(set(invented_words_found)),
            "facts_count": len(facts),
            "cards_count": len(cards),
            "rejected_count": len(rejected),
        },
        "missed_core_facts": [rf for rf in missed_refs if rf.get("importance") == "core"],
        "missed_secondary_facts": [rf for rf in missed_refs if rf.get("importance") != "core"],
        "doubtful_facts": doubtful_facts,
        "reword_candidates": reword_candidates,
        "output": out,
    }


def main() -> None:
    all_results = {}
    for slug, r_rel, ref_rel in SHEETS:
        res = evaluate_sheet(slug, ROOT / r_rel, ROOT / ref_rel)
        all_results[slug] = res
        m = res["metrics"]
        print(f"=== {slug} ({res['sheet']}) ===")
        print(
            f"  Core Recall: {m['core_recall']}% ({m['core_covered']}/{m['core_total']}) | "
            f"All Recall: {m['all_recall']}% ({m['all_covered']}/{m['all_total']})"
        )
        print(
            f"  Fact Precision: {m['fact_precision']}% | Question Correctness: {m['question_correctness']}% | "
            f"Clarity: {m['question_clarity']}%"
        )
        print(
            f"  Duplicate Rate: {m['duplicate_rate']}% | Traceability: {m['traceability']}% | "
            f"Invented Words: {m['invented_words_count']}"
        )
        print(f"  Extracted Facts: {m['facts_count']} | Accepted Cards: {m['cards_count']} | Rejected: {m['rejected_count']}")
        if res["missed_core_facts"]:
            print("  Missed Core Facts:")
            for mc in res["missed_core_facts"]:
                print(f"    - [{mc['id']}] ({mc['source_item']}) {mc['subject']} --{mc['relation']}--> {mc['answer']}")

    if "--save-prototype" in sys.argv:
        out_path = ROOT / "data" / "prototype_v1_eval.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"Saved prototype evaluation to {out_path}")

    if "--save-final" in sys.argv:
        out_path = ROOT / "data" / "final_eval.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"Saved final evaluation to {out_path}")


if __name__ == "__main__":
    main()
