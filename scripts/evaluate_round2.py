#!/usr/bin/env python3
"""
Evaluates the Key Facts Engine on the 5 Round-2 sheets (and optionally saves baseline).
Computes point coverage (% of point/summary items that produced at least one accepted card),
lists all accepted cards, and lists every point/summary item with no accepted card + reason.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import engine
from engine.facts import resolve_sheet_title
from engine.relations import extract_relations_from_item
from engine.questions import generate_card
from engine.validate import build_sheet_vocabulary, validate_card


def evaluate_sheet(reader_path: str) -> dict:
    with open(reader_path, "r", encoding="utf-8") as f:
        reader = json.load(f)

    res = engine.run(reader)
    cards = res["cards"]
    rejected = res["rejected"]

    items = reader.get("items", [])
    items_by_id = {it["id"]: it for it in items if "id" in it}
    sheet_vocab = build_sheet_vocabulary(reader)
    sheet_title = resolve_sheet_title(reader)

    item_to_cards: dict[str, list[dict]] = {}
    for c in cards:
        iid = c.get("item_id")
        if iid:
            item_to_cards.setdefault(iid, []).append(c)

    point_items = [
        it for it in items
        if it.get("kind") in ("point", "summary")
        and it.get("section") not in ("questions", "answers", "qa", "tips")
    ]

    covered_points = []
    uncovered_points = []
    seen_dummy: set[tuple[str, str]] = set()
    for it in point_items:
        iid = it["id"]
        if item_to_cards.get(iid):
            covered_points.append(iid)
        else:
            raw_rels = extract_relations_from_item(it, sheet_title=sheet_title)
            if not raw_rels:
                if "\ufffd" in (it.get("text") or ""):
                    reason = "skipped in relations.py (contains broken PDF replacement glyph \\ufffd)"
                else:
                    reason = "no relation pattern matched in relations.py"
            else:
                reasons_all = []
                for idx, rf in enumerate(raw_rels, start=1):
                    rf_copy = dict(rf, id=f"TEMP_{idx}")
                    cand = generate_card(rf_copy, card_id="TEMP")
                    r_list = validate_card(cand, items_by_id, sheet_vocab, seen_dummy)
                    if r_list:
                        reasons_all.extend(r_list)
                    else:
                        reasons_all.append("deduplicated_against_earlier_point")
                reason = f"rejected in validate.py ({', '.join(sorted(set(reasons_all)))})"
            uncovered_points.append({
                "id": iid,
                "topic": it.get("topic"),
                "text": it.get("text"),
                "reason": reason,
            })

    total_pts = len(point_items)
    cov_pct = (len(covered_points) / total_pts * 100.0) if total_pts else 100.0

    return {
        "sheet": reader.get("sheet"),
        "file": os.path.basename(reader_path),
        "card_count": len(cards),
        "total_points": total_pts,
        "covered_points": len(covered_points),
        "point_coverage_pct": round(cov_pct, 1),
        "cards": cards,
        "rejected": rejected,
        "uncovered_points": uncovered_points,
    }


def main():
    round2_dir = os.path.join(ROOT, "data", "round2")
    paths = sorted(glob.glob(os.path.join(round2_dir, "*.reader.json")))
    results = [evaluate_sheet(p) for p in paths]

    if "--save-baseline" in sys.argv:
        out_path = os.path.join(ROOT, "data", "round2_baseline.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Saved baseline to {out_path}")

    if "--save-final" in sys.argv:
        out_path = os.path.join(ROOT, "data", "round2_final.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Saved final Round 2 evaluation to {out_path}")

    for r in results:
        print("=" * 72)
        print(
            f"SHEET: {r['file']} | Cards: {r['card_count']} | "
            f"Point Coverage: {r['covered_points']}/{r['total_points']} ({r['point_coverage_pct']}%)"
        )
        for c in r["cards"]:
            print(
                f"  [CARD] ({c['question_type']}) label={c['label']!r} | "
                f"front={c['front']!r} -> answer={c['answer']!r} (p.{c['page']}, {c['item_id']})"
            )
        for u in r["uncovered_points"]:
            print(f"  [NO CARD] {u['id']} ({u['reason']}): {u['text']}")


if __name__ == "__main__":
    main()
