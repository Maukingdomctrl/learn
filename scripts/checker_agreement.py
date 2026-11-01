"""Step 3 & Step 5 of Prompt 5: Measure agreement between score_card() and teacher labels
on fixtures/labelled_cards.json, plus run the 10-card unseen-subject (Class 8 Biology) holdout test.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from learn.teaching_engine.card_quality import score_card

LABELLED_CARDS_PATH = ROOT_DIR / "fixtures" / "labelled_cards.json"

# ---------------------------------------------------------------------------
# Step 5: 10 NEW cards (5 good, 5 bad) from a Class 8 Biology passage not in fixtures/sheets/
# ---------------------------------------------------------------------------

UNSEEN_BIOLOGY_SHEET = """
Chapter 4: Cell Structure and Photosynthesis

1. Discovery and Structure of the Cell
• Robert Hooke discovered cells in 1665 while examining a thin slice of cork under a microscope.
• The **mitochondria** are the powerhouses of the cell because they release energy during cellular respiration.
• Plant cells have a rigid **cell wall** made of cellulose outside the cell membrane.
• Chloroplasts contain a green pigment called **chlorophyll** that traps sunlight for photosynthesis.
• Tiny pores called **stomata** on the underside of leaves control gas exchange and transpiration.
""".strip()

STEP_5_NEW_BIOLOGY_CARDS: list[dict[str, Any]] = [
    # 5 Good Cards
    {
        "id": "bio_good_01",
        "front": "______ discovered cells in 1665 while examining a thin slice of cork under a microscope.",
        "prompt": "Name the person, place, or institution",
        "answer": "Robert Hooke",
        "source_line": "• Robert Hooke discovered cells in 1665 while examining a thin slice of cork under a microscope.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "good",
        "reason": "Blanks the 2-word proper name 'Robert Hooke' with a clear, unambiguous clue.",
    },
    {
        "id": "bio_good_02",
        "front": "Robert Hooke discovered cells in ______ while examining a thin slice of cork under a microscope.",
        "prompt": "Name the date or year",
        "answer": "1665",
        "source_line": "• Robert Hooke discovered cells in 1665 while examining a thin slice of cork under a microscope.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "good",
        "reason": "Blanks the 4-digit year '1665' while naming Robert Hooke.",
    },
    {
        "id": "bio_good_03",
        "front": "The ______ are the powerhouses of the cell because they release energy during cellular respiration.",
        "prompt": "Fill in the key fact",
        "answer": "mitochondria",
        "source_line": "• The **mitochondria** are the powerhouses of the cell because they release energy during cellular respiration.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "good",
        "reason": "Blanks the bolded 1-word organelle 'mitochondria'.",
    },
    {
        "id": "bio_good_04",
        "front": "Plant cells have a rigid ______ made of cellulose outside the cell membrane.",
        "prompt": "Fill in the key fact",
        "answer": "cell wall",
        "source_line": "• Plant cells have a rigid **cell wall** made of cellulose outside the cell membrane.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "good",
        "reason": "Blanks the bolded 2-word structure 'cell wall'.",
    },
    {
        "id": "bio_good_05",
        "front": "Chloroplasts contain a green pigment called ______ that traps sunlight for photosynthesis.",
        "prompt": "Fill in the key fact",
        "answer": "chlorophyll",
        "source_line": "• Chloroplasts contain a green pigment called **chlorophyll** that traps sunlight for photosynthesis.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "good",
        "reason": "Blanks the bolded 1-word pigment 'chlorophyll'.",
    },
    # 5 Bad Cards
    {
        "id": "bio_bad_01",
        "front": "Explain Discovery and Structure of the Cell and its main features.",
        "prompt": "Explain Discovery and Structure of the Cell and its main features.",
        "answer": "Robert Hooke",
        "source_line": "1. Discovery and Structure of the Cell",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "bad",
        "reason": "Boilerplate 'Explain ___ and its main features.' template built from a heading.",
    },
    {
        "id": "bio_bad_02",
        "front": "Plant cells have a rigid ______ outside the cell membrane.",
        "prompt": "Fill in the key fact",
        "answer": "cell wall made of",
        "source_line": "• Plant cells have a rigid **cell wall** made of cellulose outside the cell membrane.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "bad",
        "reason": "Cut-off answer ending on preposition 'of' ('cell wall made of').",
    },
    {
        "id": "bio_bad_03",
        "front": "He discovered cells in ______ while examining a thin slice of cork.",
        "prompt": "Name the date or year",
        "answer": "1665",
        "source_line": "• Robert Hooke discovered cells in 1665 while examining a thin slice of cork under a microscope.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "bad",
        "reason": "Missing subject: starts with dangling pronoun 'He' without naming Robert Hooke.",
    },
    {
        "id": "bio_bad_04",
        "front": "Tiny pores called stomata on the underside of ______ control gas exchange.",
        "prompt": "Fill in the key fact",
        "answer": "stomata",
        "source_line": "• Tiny pores called **stomata** on the underside of leaves control gas exchange and transpiration.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "bad",
        "reason": "Answer 'stomata' is given away in the front of the card.",
    },
    {
        "id": "bio_bad_05",
        "front": "The mitochondria are the powerhouses of the cell ______ they release energy during cellular respiration.",
        "prompt": "Fill in the key fact",
        "answer": "because",
        "source_line": "• The **mitochondria** are the powerhouses of the cell because they release energy during cellular respiration.",
        "sheet": UNSEEN_BIOLOGY_SHEET,
        "label": "bad",
        "reason": "Blanks common conjunction word 'because' instead of a key fact.",
    },
]


def evaluate_card_set(cards: list[dict[str, Any]]) -> dict[str, Any]:
    missed_bad: list[dict[str, Any]] = []
    wrong_rejections: list[dict[str, Any]] = []
    total_bad = 0
    total_good = 0

    for item in cards:
        label = item.get("label", "").strip().lower()
        res = score_card(item, item.get("sheet", ""))
        accepted = bool(res["accepted"])
        if label == "bad":
            total_bad += 1
            if accepted:
                missed_bad.append({"card": item, "result": res})
        elif label == "good":
            total_good += 1
            if not accepted:
                wrong_rejections.append({"card": item, "result": res})

    return {
        "missed_bad": missed_bad,
        "wrong_rejections": wrong_rejections,
        "total_bad": total_bad,
        "total_good": total_good,
    }


def main() -> None:
    labelled_cards = json.loads(LABELLED_CARDS_PATH.read_text(encoding="utf-8"))
    summary = evaluate_card_set(labelled_cards)

    print("=== CHECKER AGREEMENT REPORT (fixtures/labelled_cards.json) ===")
    print(f"Total labelled cards: {len(labelled_cards)} ({summary['total_good']} good, {summary['total_bad']} bad)")
    print()

    print(f"1. Bad cards ACCEPTED (missed bad cards): {len(summary['missed_bad'])} / {summary['total_bad']}")
    if not summary["missed_bad"]:
        print("   None (0 bad cards accepted).")
    else:
        for entry in summary["missed_bad"]:
            c = entry["card"]
            r = entry["result"]
            print(f"   - [{c.get('id')}] front={c['front']!r} | answer={c['answer']!r} | overall={r['overall']} | label_reason={c['reason']}")

    print()
    print(f"2. Good cards REJECTED (wrong rejections): {len(summary['wrong_rejections'])} / {summary['total_good']}")
    if not summary["wrong_rejections"]:
        print("   None (0 good cards rejected).")
    else:
        for entry in summary["wrong_rejections"]:
            c = entry["card"]
            r = entry["result"]
            print(f"   - [{c.get('id')}] front={c['front']!r} | answer={c['answer']!r} | checker_reasons={r['reasons']}")

    print()
    print(
        f"Totals: missed bad = {len(summary['missed_bad'])} / {summary['total_bad']}, "
        f"wrong rejections = {len(summary['wrong_rejections'])} / {summary['total_good']}"
    )

    print()
    print("=== STEP 5: UNSEEN SUBJECT HOLDOUT (Class 8 Biology — 5 good, 5 bad) ===")
    bio_summary = evaluate_card_set(STEP_5_NEW_BIOLOGY_CARDS)
    correct_good = bio_summary["total_good"] - len(bio_summary["wrong_rejections"])
    correct_bad = bio_summary["total_bad"] - len(bio_summary["missed_bad"])
    total_correct = correct_good + correct_bad
    print(
        f"Holdout accuracy: {total_correct} / {len(STEP_5_NEW_BIOLOGY_CARDS)} "
        f"(good accepted: {correct_good}/{bio_summary['total_good']}, "
        f"bad rejected: {correct_bad}/{bio_summary['total_bad']})"
    )
    for item in STEP_5_NEW_BIOLOGY_CARDS:
        res = score_card(item, item["sheet"])
        verdict = "ACCEPTED" if res["accepted"] else "REJECTED"
        reasons_str = "; ".join(res["reasons"]) if res["reasons"] else "all 7 criteria = 5"
        print(
            f"  - [{item['id']}] label={item['label'].upper():4s} -> checker={verdict:8s} "
            f"(overall={res['overall']:.2f}) | A={item['answer']!r} | {reasons_str}"
        )


if __name__ == "__main__":
    main()
