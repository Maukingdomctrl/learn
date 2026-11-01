#!/usr/bin/env python3
"""
tests/test_regression.py
Freezes the good cards discovered in the Step 2 Prototype so that subsequent
pattern improvements never cause an earlier good card to disappear.
"""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engine


# Good cards from Step 2 Prototype (subject token, expected answer substring/exact)
FROZEN_STEP2_GOOD_CARDS = {
    "mumbai-personalities-flat.reader.json": [
        ("Tata", "1839–1904"),
        ("Tata", "Father of Indian Industry"),
        ("Tata", "Taj Mahal Hotel"),
        ("Taj Mahal Hotel", "3 December 1903"),
        ("Jyotirao Phule", "1827–1890"),
        ("Jyotirao Phule", "Pioneer of Social Equality"),
        ("Satyashodhak Samaj", "1873"),
        ("Satyashodhak Samaj", "Society of Truth Seekers"),
        ("Savitribai Phule", "1831–1897"),
        ("Savitribai Phule", "Pioneer of Women's Education"),
        ("Ambedkar", "1891–1956"),
        ("Ambedkar", "Architect of the Indian Constitution"),
        ("Roy", "1772–1833"),
        ("Roy", "Father of the Indian Renaissance"),
        ("Brahmo Sabha", "1828"),
    ],
    "uk-cities-comparative-table.reader.json": [
        ("London", "United Kingdom & England"),
        ("London", "River Thames"),
        ("Birmingham", "River Rea"),
        ("Belfast", "Northern Ireland"),
        ("Belfast", "River Lagan"),
        ("Belfast", "Titanic Belfast"),
        ("Edinburgh", "Scotland"),
        ("Edinburgh", "Scottish Parliament"),
        ("Cardiff", "Wales"),
        ("Cardiff", "Wales Millennium Centre"),
    ],
    "full-physics-forces.reader.json": [
        ("F = ma", "F = ma"),
    ],
}


class TestStep2Regression(unittest.TestCase):
    def test_step2_good_cards_preserved(self) -> None:
        for filename, expected_list in FROZEN_STEP2_GOOD_CARDS.items():
            path = ROOT / "data" / filename
            with open(path, "r", encoding="utf-8") as f:
                reader_json = json.load(f)
            result = engine.run(reader_json)
            cards = result["cards"]
            for subj_hint, expected_ans in expected_list:
                matched = any(
                    (expected_ans.lower() in c["answer"].lower() or c["answer"].lower() in expected_ans.lower())
                    and (subj_hint.lower() in (c["label"] + " " + c["front"] + " " + c["answer"]).lower())
                    for c in cards
                )
                self.assertTrue(
                    matched,
                    f"Regression in {filename}: lost frozen Step 2 good card ({subj_hint} -> {expected_ans})",
                )

    def test_determinism_byte_identical(self) -> None:
        for filename in FROZEN_STEP2_GOOD_CARDS:
            path = ROOT / "data" / filename
            with open(path, "r", encoding="utf-8") as f:
                reader_json = json.load(f)
            out1 = json.dumps(engine.run(reader_json), sort_keys=True, ensure_ascii=False)
            out2 = json.dumps(engine.run(reader_json), sort_keys=True, ensure_ascii=False)
            self.assertEqual(out1, out2, f"Output is not byte-identical for {filename}")


if __name__ == "__main__":
    unittest.main()
