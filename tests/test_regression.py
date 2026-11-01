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

from learn.teaching_engine import key_facts as engine


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
        ("Resultant force", "acceleration"),
        ("Resultant force", "constant"),
        ("Trial B", "2.0"),
        ("Trial D", "0.67"),
        ("Falling object", "drag"),
        ("Car braking", "opposes velocity"),
        ("Satellite", "Gravity"),
        ("1 N", "1 N = 1 kg·m/s²"),
        ("Speed", "m/s"),
        ("Acceleration", "m/s²"),
        ("F = ma", "kilograms"),
        ("500 g", "0.500 kg"),
        ("Evaluation", "Friction"),
        ("Evaluation", "motion sensor"),
    ],
}

FROZEN_ROUND2_GOOD_CARDS = {
    "civics-sheet.reader.json": [
        ("Lok Sabha", "Lower House of Parliament"),
        ("Lok Sabha", "directly elected"),
        ("Lok Sabha", "5 years"),
        ("Lok Sabha", "the Speaker"),
        ("Lok Sabha", "25 years"),
        ("Rajya Sabha", "Upper House of Parliament"),
        ("Rajya Sabha", "State Legislative Assemblies"),
        ("Rajya Sabha", "permanent house"),
        ("Rajya Sabha", "6 years"),
        ("Rajya Sabha", "2 years"),
        ("Rajya Sabha", "the Vice-President of India"),
        ("Rajya Sabha", "30 years"),
        ("President", "Head of the State"),
        ("President", "electoral college"),
        ("President", "5 years"),
        ("President", "35 years"),
        ("President", "Supreme Commander"),
        ("Supreme Court", "Highest court of India"),
        ("Supreme Court", "New Delhi"),
        ("Supreme Court", "the President"),
        ("Supreme Court", "65"),
        ("Supreme Court", "Fundamental Rights"),
        ("Supreme Court", "guardian of the Constitution"),
        ("Lok Sabha", "people's house"),
    ],
    "equations.reader.json": [
        ("3x + 7", "25"),
        ("3x", "18"),
        ("x =", "6"),
        ("Area of a rectangle", "A = l × w"),
        ("Perimeter of a rectangle", "P = 2(l + w)"),
        ("Area of a triangle", "A = ½ × b × h"),
        ("Powers", "8"),
        ("Negative numbers", "5"),
        ("Comparison", "¾"),
    ],
    "full-finance-lost-rupee.reader.json": [
        ("Probability", "favourable outcomes ÷ total outcomes"),
        ("Probability", "0 to 1"),
        ("Red", "4/8 = 1/2"),
        ("Expected frequency", "30"),
        ("Simple interest", "I = Prt"),
        ("Simple interest", "600 interest"),
        ("Compound interest", "5,624.32 approx"),
        ("Simple interest", "original principal"),
        ("Compound interest", "principal plus accumulated interest"),
        ("Financial mathematics", "biased"),
    ],
    "history-sheet.reader.json": [
        ("Political", "Doctrine of Lapse"),
        ("Economic", "land revenue"),
        ("Military", "paid less"),
        ("Immediate cause", "Enfield rifle"),
        ("Mangal Pandey", "Mangal Pandey"),
        ("Meerut", "10 May 1857"),
        ("emperor", "Bahadur Shah Zafar"),
        ("Delhi", "September 1857"),
        ("Jhansi", "Rani Lakshmibai"),
        ("Kanpur", "Nana Saheb"),
        ("Begum Hazrat Mahal", "Lucknow"),
        ("Bihar", "Kunwar Singh"),
        ("East India Company", "Government of India Act, 1858"),
        ("Results", "British Crown"),
        ("Governor-General", "Viceroy"),
        ("1858", "Queen Victoria's Proclamation"),
        ("army", "prevent another revolt"),
        ("uprising", "Mughal dynasty"),
    ],
    "processes-sheet.reader.json": [
        ("Migration", "Migration"),
        ("Push factors", "lack of jobs"),
        ("Pull factors", "better jobs"),
        ("Effects", "crowded cities"),
        ("Movement from villages to cities", "rural-urban migration"),
        ("Urbanisation", "Urbanisation"),
        ("Causes", "industries"),
        ("Effects", "traffic jams"),
        ("Measures", "planned cities"),
        ("Earthquakes", "earthquake"),
        ("Causes", "tectonic plates"),
        ("Earthquakes", "epicentre"),
        ("Earthquakes", "Richter scale"),
        ("Effects", "collapse of buildings"),
        ("Precautions", "strong table"),
        ("Migration", "people move"),
        ("Urbanisation", "cities grow"),
        ("Earthquakes", "the ground shakes"),
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

    def test_round2_good_cards_preserved(self) -> None:
        for filename, expected_list in FROZEN_ROUND2_GOOD_CARDS.items():
            path = ROOT / "data" / "round2" / filename
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
                    f"Regression in {filename}: lost frozen Round 2 good card ({subj_hint} -> {expected_ans})",
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

