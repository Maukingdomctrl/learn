#!/usr/bin/env python3
"""
tests/test_expressions.py
Unit tests for engine/expressions.py (Families A–L), atomic span protection,
and the strict guard that fails if any name from the practice sheets appears
in any code word list or regex in engine/*.py.
"""
from __future__ import annotations

import ast
import glob
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learn.teaching_engine.key_facts.entities import find_item_spans
from learn.teaching_engine.key_facts.expressions import (
    FAMILIES,
    FAMILY_A,
    FAMILY_B,
    FAMILY_C,
    FAMILY_D,
    FAMILY_E,
    FAMILY_F,
    FAMILY_G,
    FAMILY_H,
    FAMILY_I,
    FAMILY_J,
    FAMILY_K,
    FAMILY_L,
    SUPERLATIVE_CHECK_NOTE,
    check_cut_in_half_span,
    find_all_expressions,
)


class TestNoSheetSpecificWordsInCode(unittest.TestCase):
    """Step 1: Fail if any name or sheet-specific word from the practice sheets appears in any code word list or regex."""

    FORBIDDEN_SHEET_WORDS = {
        # Warned in Round 2 & Round 3 prompts
        "hippodrome", "senedd", "titanic", "preamble", "samaj", "sabha", "satyagraha",
        "shipyard", "sati", "newton", "drag", "lokmanya", "mahatma", "pandit", "netaji",
        "swami", "smt", "vikram", "shaka", "saka",
        # Proper names of people, places, rivers, specific institutions from the 8 sheets
        "jamsetji", "nusserwanji", "tata", "jyotirao", "savitribai", "phule",
        "bhimrao", "ambedkar", "mohan", "elphinstone", "chinchpokli", "alexandra",
        "swadeshi", "colaba", "satyashodhak", "rajgriha", "dadar", "brahmo", "prarthana",
        "mumbai", "maharashtra", "bengaluru",
        "london", "birmingham", "belfast", "edinburgh", "cardiff", "england", "scotland",
        "wales", "ireland", "thames", "rea", "lagan", "harland", "wolff",
        "dalhousie", "jhansi", "nagpur", "enfield", "mangal", "pandey", "barrackpore",
        "meerut", "delhi", "bahadur", "zafar", "lakshmibai", "nana", "saheb", "kanpur",
        "begum", "hazrat", "mahal", "lucknow", "kunwar", "bihar", "victoria", "mughal",
        "richter",
    }

    def test_no_practice_sheet_names_in_engine_word_lists_or_regexes(self) -> None:
        # Also dynamically collect multi-word proper names from topic headers of all 8 practice sheets
        sheet_paths = sorted(
            glob.glob(str(ROOT / "data" / "*.reader.json"))
            + glob.glob(str(ROOT / "data" / "round2" / "*.reader.json"))
        )
        self.assertGreaterEqual(len(sheet_paths), 8)

        generic_allowed = {
            "the", "of", "in", "and", "to", "for", "on", "at", "by", "with", "from",
            "father", "mother", "pioneer", "architect", "founder", "leader", "head",
            "capital", "city", "cities", "river", "state", "country", "region",
            "house", "lower", "upper", "parliament", "president", "supreme", "court",
            "high", "highest", "union", "judiciary", "people", "movement", "growth",
            "towns", "sudden", "shaking", "ground", "earthquakes", "migration",
            "urbanisation", "causes", "uprising", "course", "leaders", "centres",
            "results", "great", "geometry", "equations", "mathematical", "symbols",
            "sample", "notes", "class", "grade", "history", "civics", "geography",
            "physics", "forces", "mass", "acceleration", "probability", "expected",
            "frequency", "finance", "financial", "mathematics", "literacy", "social",
            "equality", "education", "women", "women's", "industry", "renaissance",
            "constitution", "indian", "modern", "india", "united", "kingdom",
            "northern", "west", "midlands", "eastern", "western", "southern",
        }

        dynamic_proper_tokens: set[str] = set()
        for sp in sheet_paths:
            with open(sp, "r", encoding="utf-8") as f:
                data = json.load(f)
            for it in data.get("items", []):
                if it.get("kind") == "topic":
                    txt = it.get("text") or ""
                    left = re.split(r"\s+[–—-]\s+", txt, maxsplit=1)[0]
                    for w in re.findall(r"[A-Za-z]{4,}", left):
                        wl = w.lower()
                        if wl not in generic_allowed:
                            dynamic_proper_tokens.add(wl)

        forbidden_all = self.FORBIDDEN_SHEET_WORDS | dynamic_proper_tokens

        engine_files = sorted((ROOT / "learn" / "teaching_engine" / "key_facts").glob("*.py"))
        self.assertTrue(len(engine_files) >= 6)

        for py_path in engine_files:
            source = py_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(py_path))
            docstring_nodes: set[int] = set()
            for parent in ast.walk(tree):
                if isinstance(parent, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (
                        parent.body
                        and isinstance(parent.body[0], ast.Expr)
                        and isinstance(parent.body[0].value, ast.Constant)
                    ):
                        docstring_nodes.add(id(parent.body[0].value))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if id(node) in docstring_nodes:
                        continue
                    val = node.value
                    tokens = {w.lower() for w in re.findall(r"[A-Za-z]{3,}", val)}
                    leaked = tokens & forbidden_all
                    self.assertEqual(
                        leaked,
                        set(),
                        msg=f"Forbidden sheet-specific word(s) {sorted(leaked)} found in {py_path.name} string literal: {val!r}",
                    )


class TestExpressionLibraryFamilies(unittest.TestCase):
    """Test each expression family A–L and every numbered bullet."""

    def test_a1_full_dates_any_order_pass_and_fail(self) -> None:
        for date_str in ("8 August 1942", "August 8, 1942", "8th August 1942", "08/08/1942", "26-01-1950"):
            sent = f"The municipal charter was signed on {date_str} in the town hall."
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1, msg=f"Expected 1 full_date match for {date_str!r}, got {matches}")
            self.assertEqual(matches[0]["text"], date_str)
            self.assertEqual(sent[matches[0]["span"][0] : matches[0]["span"][1]], date_str)
            self.assertEqual(matches[0]["type"], "full_date")
            texts = [m["text"] for m in FAMILY_A.find(sent)]
            self.assertNotIn("August", texts)

        no_date_matches = [m for m in FAMILY_A.find("The charter was signed during the summer session.") if m["bullet"] == 1]
        self.assertEqual(no_date_matches, [])

    def test_a2_month_year_and_day_month_pass_and_fail(self) -> None:
        m1 = [m for m in FAMILY_A.find("Heavy monsoon rains began in August 1942 across the valley.") if m["bullet"] == 2]
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "August 1942")
        self.assertEqual(m1[0]["type"], "month_year")

        m2 = [m for m in FAMILY_A.find("Schools celebrate the annual harvest festival on 15 August every year.") if m["bullet"] == 2]
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2[0]["text"], "15 August")
        self.assertEqual(m2[0]["type"], "day_month")

        m_full = [m for m in FAMILY_A.find("The assembly met on 8 August 1942 in the courtyard.") if m["bullet"] == 2]
        self.assertEqual(m_full, [])

    def test_a3_years_with_preposition_keep_preposition_on_card_pass_and_fail(self) -> None:
        for phrase, expected_years in (
            ("The library opened in 1873 near the harbour.", ["1873"]),
            ("The railway line was completed by 1905.", ["1905"]),
            ("The canal was built from 1917 to 1934.", ["1917", "1934"]),
            ("Negotiations took place between 1857 and 1858.", ["1857", "1858"]),
            ("The observatory has operated since 1947.", ["1947"]),
            ("The old coinage remained valid until 1950.", ["1950"]),
            ("The tramway ran on steam till 1919.", ["1919"]),
        ):
            matches = [m for m in FAMILY_A.find(phrase) if m["bullet"] == 3]
            self.assertEqual([m["text"] for m in matches], expected_years, msg=f"Failed on {phrase!r}")
            for m in matches:
                self.assertFalse(
                    any(prep in m["text"].lower() for prep in ("in", "by", "from", "between", "since", "until", "till"))
                )

    def test_a4_year_ranges_and_spans_pass_and_fail(self) -> None:
        for sent, expected in (
            ("The expedition journal covers the period 1917–1934.", "1917–1934"),
            ("Meera Bai (1839–1904) founded the rural weaving school.", "1839–1904"),
            ("The lighthouse keeper served for 17 years on the island.", "17 years"),
            ("The astronomical clock has ticked for over 300 years.", "300 years"),
            ("Volunteers completed the 24-day coastal march.", "24-day"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 4]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        self.assertEqual([m for m in FAMILY_A.find("The botany club meets in Room 104.") if m["bullet"] == 4], [])

    def test_a5_centuries_and_parts_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Steamships transformed ocean travel in the 19th century.", "19th century"),
            ("Botanical gardens expanded during the nineteenth century.", "the nineteenth century"),
            ("Aviation advanced rapidly in the early 20th century.", "early 20th century"),
            ("Satellite mapping began in the latter half of the 20th century.", "the latter half of the 20th century"),
            ("Electric streetlamps arrived at the turn of the century.", "turn of the century"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 5]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected)
            self.assertEqual(matches[0]["question_type"], "Which century…?")

        self.assertEqual([m for m in FAMILY_A.find("The 19th regiment camped near the bridge.") if m["bullet"] == 5], [])

    def test_a6_decades_and_eras_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Radio broadcasting expanded during the 1930s.", "1930s"),
            ("Aeronautical workshops opened in the mid-1930s.", "mid-1930s"),
            ("Miniature painting flourished during the Classical period.", "Classical period"),
            ("Hymns were composed in the Vedic age.", "Vedic age"),
            ("Cave paintings survive from the Stone Age.", "Stone Age"),
            ("Copper and tin were alloyed during the Bronze Age.", "Bronze Age"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 6]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        self.assertEqual([m for m in FAMILY_A.find("Water boils when heated in a kettle.") if m["bullet"] == 6], [])

    def test_a7_era_markers_pass_and_fail(self) -> None:
        for sent, expected in (
            ("The Macedonian army crossed the river in 326 BC.", "326 BC"),
            ("The northern sultanate was established in AD 1206.", "AD 1206"),
            ("Rock edicts were carved in 250 BCE.", "250 BCE"),
            ("The port town prospered around 1206 CE.", "1206 CE"),
            ("The astrolabe was crafted in c. 1500.", "c. 1500"),
            ("Paper mills appeared in circa 1500.", "circa 1500"),
            ("Spice traders built the fort around 1600.", "1600"),
            ("The battle near the mango grove occurred about 1757.", "1757"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 7]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        self.assertEqual([m for m in FAMILY_A.find("Triangle ABC has three acute angles.") if m["bullet"] == 7], [])

    def test_a8_named_calendars_pass_and_fail(self) -> None:
        m1 = [m for m in FAMILY_A.find("The inscription is dated to Vikram Samvat 2080.") if m["bullet"] == 8]
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "Vikram Samvat 2080")

        m2 = [m for m in FAMILY_A.find("The national calendar follows the Shaka era 78 AD.") if m["bullet"] == 8]
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2[0]["text"], "Shaka era 78 AD")

        self.assertEqual([m for m in FAMILY_A.find("A leap year has 366 days.") if m["bullet"] == 8], [])

    def test_a9_relative_time_words_pair_event_with_date_pass_and_fail(self) -> None:
        sent = "Following the cyclone of 1864, new seawalls were built along the harbour."
        matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 9]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "1864")
        self.assertEqual(matches[0]["relative_marker"].lower(), "following")

        self.assertEqual([m for m in FAMILY_A.find("Wash your hands after handling soil samples.") if m["bullet"] == 9], [])

    def test_a10_time_of_day_and_durations_pass_and_fail(self) -> None:
        for sent, expected in (
            ("The morning assembly bell rings at 8:30 am.", "8:30 am"),
            ("The ferry crossing takes two hours in calm weather.", "two hours"),
            ("Earth completes one rotation in 24 hours.", "24 hours"),
            ("A standard calendar year contains 365 days.", "365 days"),
            ("The lunar tide cycle repeats every a fortnight.", "a fortnight"),
        ):
            matches = [m for m in FAMILY_A.find(sent) if m["bullet"] == 10]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        self.assertEqual([m for m in FAMILY_A.find("Mix cement and sand in a 1 : 2 ratio.") if m["bullet"] == 10], [])

    def test_b1_plain_grouped_and_indian_numbers_pass_and_fail(self) -> None:
        for sent, expected in (
            ("The auditorium has 72 seats in the front gallery.", "72"),
            ("The district recorded a population of 286,000.", "286,000"),
            ("The cooperative enrolled 2,86,000 farmers across the state.", "2,86,000"),
            ("The reservoir stores 1.5 lakh litres of rainwater.", "1.5 lakh"),
            ("The afforestation drive planted 3 crore saplings.", "3 crore"),
            ("Over a million migrating birds visit the wetland.", "a million"),
            ("More than two billion stars populate the galaxy.", "two billion"),
        ):
            matches = FAMILY_B.find(sent)
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")
            self.assertNotIn("286", [m["text"] for m in matches])

    def test_b2_number_words_pass_and_fail(self) -> None:
        for word in ("one", "twelve", "first", "second", "third", "tenth", "a dozen", "a hundred", "half", "a quarter", "double", "twice"):
            sent = f"The basket contained {word} of the harvested apples."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 2]
            self.assertTrue(any(m["text"] == word for m in matches), msg=f"Expected {word!r} in {matches}")

        self.assertEqual([m for m in FAMILY_B.find("Copper conducts heat rapidly.") if m["bullet"] == 2], [])

    def test_b3_ordinals_and_ranks_not_superlative_note_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Surat is the 7th most populous city in the region.", "7th most populous city"),
            ("Pune is the second largest city in the state.", "second largest city"),
            ("Coventry is the eleventh-largest city in the country.", "eleventh-largest city"),
            ("Kandla became the No. 1 port on the western coast.", "No. 1 port"),
        ):
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 3]
            self.assertEqual(len(matches), 1, msg=f"Failed on {sent!r}: {matches}")
            self.assertEqual(matches[0]["text"], expected)
            self.assertFalse(matches[0].get("is_superlative"))
            for em in find_all_expressions(sent):
                self.assertNotIn("note", em)

        self.assertEqual([m for m in FAMILY_B.find("Jupiter is the largest planet in the solar system.") if m["bullet"] == 3], [])

    def test_b4_approximations_keep_qualifier_on_card_pass_and_fail(self) -> None:
        for qual in ("about", "around", "nearly", "over", "more than", "less than", "approximately", "almost", "at least", "up to"):
            sent = f"The botanical garden attracts {qual} 286,000 tourists every winter."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 4]
            self.assertTrue(len(matches) >= 1, msg=f"Expected B4 match for {qual!r} in {sent!r}")
            self.assertTrue(matches[0]["text"].startswith("286,000"))
            self.assertFalse(matches[0]["text"].lower().startswith(qual))

    def test_b5_percentages_fractions_ratios_pass_and_fail(self) -> None:
        for expr in ("70%", "70 per cent", "3/4", "three-fourths", "1 : 2", "2 out of 5"):
            sent = f"Water covers {expr} of the experimental plot."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 5]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expr)

        self.assertEqual([m for m in FAMILY_B.find("The treaty was signed on 08/08/1942.") if m["bullet"] == 5], [])

    def test_b6_money_pass_and_fail(self) -> None:
        for expr in ("₹500", "Rs. 500", "INR 500", "£1.6 billion", "$20", "50 paise"):
            sent = f"The museum entry ticket costs {expr} for adults."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 6]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expr)

        self.assertEqual([m for m in FAMILY_B.find("The highway is 500 km long.") if m["bullet"] == 6], [])

    def test_b7_counts_with_nouns_pass_and_fail(self) -> None:
        for expr, expected_q in (
            ("72 delegates", "How many delegates…?"),
            ("78 volunteers", "How many volunteers…?"),
            ("5 cities", "How many cities…?"),
            ("28 states", "How many states…?"),
            ("8 union territories", "How many union territories…?"),
            ("7 continents", "How many continents…?"),
            ("206 bones", "How many bones…?"),
        ):
            sent = f"The survey recorded {expr} in the annual register."
            matches = [m for m in FAMILY_B.find(sent) if m["bullet"] == 7]
            self.assertEqual(len(matches), 1, msg=f"Failed on {expr!r}: {matches}")
            self.assertEqual(matches[0]["text"], expr)
            self.assertEqual(matches[0]["question_type"], expected_q)

        self.assertEqual([m for m in FAMILY_B.find("The school opened in 1947.") if m["bullet"] == 7], [])

    def test_c1_si_and_common_units_never_split_number_from_unit_pass_and_fail(self) -> None:
        for expr in ("387 km", "40 mL", "2.0 m/s²", "25 °C", "15 N", "50 Hz", "4.2 light years"):
            sent = f"The instrument recorded a reading of {expr} during the trial."
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expr)
            self.assertNotIn(expr.split()[-1], [m["text"] for m in matches if m["text"] != expr])

    def test_c2_area_and_volume_units_pass_and_fail(self) -> None:
        for expr in ("250 km²", "45 sq km", "120 square kilometres", "18 m³", "50 cubic metres"):
            sent = f"The protected forest covers {expr} on the plateau."
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 2]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expr)

        self.assertEqual([m for m in FAMILY_C.find("The river flows for 250 km.") if m["bullet"] == 2], [])

    def test_c3_geography_measures_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Mount Everest rises to 8,848 m above sea level.", "8,848 m above sea level"),
            ("The Tropic of Cancer lies at 23.5° N latitude.", "23.5° N"),
            ("Standard Time is calculated along 82.5° E longitude.", "82.5° E"),
            ("Monsoon winds blow towards the north-east in summer.", "north-east"),
        ):
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 3]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expected)

        self.assertEqual([m for m in FAMILY_C.find("A right angle measures 90°.") if m["bullet"] == 3], [])

    def test_c4_unit_conversions_pass_and_fail(self) -> None:
        for sent, expected_rhs in (
            ("In SI units, 1 N = 1 kg·m/s².", "1 kg·m/s²"),
            ("Metric length conversion: 1 km = 1000 m.", "1000 m"),
            ("Mass conversion: 500 g = 0.500 kg.", "0.500 kg"),
        ):
            matches = [m for m in FAMILY_C.find(sent) if m["bullet"] == 4]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expected_rhs)

        self.assertEqual([m for m in FAMILY_C.find("F = ma") if m["bullet"] == 4], [])

    def test_d1_physics_and_maths_formulas_pass_and_fail(self) -> None:
        for sent, expected_rhs in (
            ("F = ma", "ma"),
            ("V = I × R", "I × R"),
            ("a = F ÷ m", "F ÷ m"),
            ("P = 2(l + w)", "2(l + w)"),
            ("A = πr²", "πr²"),
            ("speed = distance ÷ time", "distance ÷ time"),
        ):
            matches = [m for m in FAMILY_D.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expected_rhs)

        self.assertEqual([m for m in FAMILY_D.find("P = 2(l + w") if m["bullet"] == 1], [])

    def test_d2_chemical_formulas_and_equations_keep_subscripts_pass_and_fail(self) -> None:
        for tok in ("H₂O", "CO₂", "CaCO₃"):
            sent = f"The laboratory flask contained pure {tok} during the test."
            matches = [m for m in FAMILY_D.find(sent) if m["type"] == "chemical_formula"]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], tok)

        eq_matches = [m for m in FAMILY_D.find("2H₂ + O₂ → 2H₂O") if m["type"] == "chemical_equation"]
        self.assertEqual(len(eq_matches), 1)
        self.assertEqual(eq_matches[0]["text"], "2H₂O")

        self.assertEqual([m for m in FAMILY_D.find("The solution turned blue.") if m["bullet"] == 2], [])

    def test_d3_element_symbols_and_names_pass_and_fail(self) -> None:
        m1 = [m for m in FAMILY_D.find("Alkali metal symbol: Na – sodium.") if m["bullet"] == 3]
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "sodium")

        m2 = [m for m in FAMILY_D.find("The chemical symbol for iron is Fe.") if m["bullet"] == 3]
        self.assertEqual(len(m2), 1)
        self.assertEqual(m2[0]["text"], "Fe")

        self.assertEqual([m for m in FAMILY_D.find("Rao (1900–1970) – Poet") if m["bullet"] == 3], [])

    def test_d4_maths_facts_pass_and_fail(self) -> None:
        for sent, expected in (
            ("The interior angles of a triangle add up to 180°.", "180°"),
            ("In geometry, a right angle is 90°.", "90°"),
            ("For circle calculations, π ≈ 3.14.", "3.14"),
            ("By definition, a square has 4 equal sides.", "4 equal sides"),
        ):
            matches = [m for m in FAMILY_D.find(sent) if m["bullet"] == 4]
            self.assertTrue(any(m["text"] == expected for m in matches))

        self.assertEqual([m for m in FAMILY_D.find("The line lies at 23.5° N.") if m["bullet"] == 4], [])

    def test_e1_naming_verbs_pass_and_fail(self) -> None:
        for verb_phrase in ("is called", "is known as", "also known as", "is termed", "is referred to as", "nicknamed", "popularly called", "hailed as"):
            sent = f"The outer protective layer of the stem {verb_phrase} epidermis."
            matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 1]
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], "epidermis")

        self.assertEqual([m for m in FAMILY_E.find("The stem transports water to the leaves.") if m["bullet"] == 1], [])

    def test_e2_roles_passive_and_active_pass_and_fail(self) -> None:
        m_pass = [m for m in FAMILY_E.find("The rural university was founded by Rabindranath Tagore in 1921.") if m["bullet"] == 2]
        self.assertEqual(len(m_pass), 1)
        self.assertEqual(m_pass[0]["text"], "Rabindranath Tagore")

        m_act = [m for m in FAMILY_E.find("Alexander Fleming discovered penicillin in 1928.") if m["bullet"] == 2]
        self.assertEqual(len(m_act), 1)
        self.assertEqual(m_act[0]["text"], "Alexander Fleming")

        self.assertEqual([m for m in FAMILY_E.find("The turbine was turned by steam.") if m["bullet"] == 2], [])

    def test_e3_titles_and_epithets_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Sardar Patel is remembered as the Iron Man of India.", "Iron Man of India"),
            ("Sarojini Naidu was honoured as the Nightingale of India.", "Nightingale of India"),
            ("Subhas Chandra Bose served as the first Mayor of Calcutta.", "first Mayor"),
        ):
            matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 3]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        self.assertEqual([m for m in FAMILY_E.find("The farmer was the father of two children.") if m["bullet"] == 3], [])

    def test_e4_name_plus_dates_headings_pass_and_fail(self) -> None:
        sent = "Anandi Gopal Joshi (1865–1887) – Pioneer of Medical Education"
        matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 4]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "Anandi Gopal Joshi")

        self.assertEqual([m for m in FAMILY_E.find("Anandi Gopal Joshi studied medicine in Pennsylvania.") if m["bullet"] == 4], [])

    def test_e5_organisations_documents_events_article_21_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Article 21 guarantees the protection of life and personal liberty.", "Article 21"),
            ("Recognised regional languages are listed in the Eighth Schedule.", "Eighth Schedule"),
            ("The Battle of Buxar was fought in 1764.", "Battle of Buxar"),
            ("Tagore established the Visva Bharati in 1921.", "Visva Bharati"),
            ("The Chipko Movement protected Himalayan forests.", "Chipko Movement"),
        ):
            matches = [m for m in FAMILY_E.find(sent) if m["bullet"] == 5]
            self.assertTrue(any(m["text"] == expected for m in matches), msg=f"Expected {expected!r} in {matches}")

        self.assertEqual([m for m in FAMILY_E.find("The word 'an' is an indefinite article.") if m["bullet"] == 5], [])

    def test_f1_definitions_pass_and_fail(self) -> None:
        for sent, expected in (
            ("Photosynthesis is the process by which green plants make food using sunlight.", "Photosynthesis"),
            ("Transpiration: loss of water vapour from aerial parts of a plant.", "Transpiration"),
            ("Ornithology is the study of birds in their natural habitats.", "Ornithology"),
        ):
            matches = [m for m in FAMILY_F.find(sent) if m["bullet"] == 1]
            self.assertTrue(any(m["text"] == expected for m in matches))

        self.assertEqual([m for m in FAMILY_F.find("It is a warm day in the village.") if m["bullet"] == 1], [])

    def test_f2_kinds_and_parts_max_one_card_per_list_pass_and_fail(self) -> None:
        sent = "Root vegetables such as carrot, radish and beetroot store starch underground."
        matches = [m for m in FAMILY_F.find(sent) if m["bullet"] == 2]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "carrot")

        self.assertEqual([m for m in FAMILY_F.find("Sunlight warms the upper layer of the pond.") if m["bullet"] == 2], [])

    def test_f3_properties_after_term_pass_and_fail(self) -> None:
        sent = "Quartz has a hexagonal crystal structure."
        matches = [m for m in FAMILY_F.find(sent) if m["bullet"] == 3]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["text"], "Quartz")

        self.assertEqual([m for m in FAMILY_F.find("They have four wings.") if m["bullet"] == 3], [])

    def test_g_cause_effect_purpose_max_6_words_pass_and_fail(self) -> None:
        m_cause = FAMILY_G.find("Sea breezes blow inland due to unequal heating of land.")
        self.assertEqual(len(m_cause), 1)
        self.assertEqual(m_cause[0]["text"], "unequal heating of land")

        m_effect = FAMILY_G.find("Deforestation on steep slopes leads to severe soil erosion.")
        self.assertEqual(len(m_effect), 1)
        self.assertEqual(m_effect[0]["text"], "severe soil erosion")

        long_sent = "Plants wilt because the surrounding soil loses moisture rapidly whenever hot dry summer winds blow continuously."
        self.assertEqual(FAMILY_G.find(long_sent), [])

    def test_h_sequence_and_process_keeps_order_word_pass_and_fail(self) -> None:
        m1 = FAMILY_H.find("The water cycle begins with evaporation from oceans and lakes.")
        self.assertEqual(len(m1), 1)
        self.assertEqual(m1[0]["text"], "evaporation")

        m2 = FAMILY_H.find("Metamorphosis stages: Egg → Larva → Pupa → Adult.")
        self.assertTrue(any(m["text"] == "Larva" for m in m2))

        self.assertEqual(FAMILY_H.find("2H₂ + O₂ → 2H₂O"), [])

    def test_i_place_and_location_river_vs_place_pass_and_fail(self) -> None:
        m_riv = FAMILY_I.find("Nasik is situated on the banks of the River Godavari.")
        self.assertTrue(any(m["text"] == "River Godavari" and m["question_type"] == "Which river…?" for m in m_riv))

        m_place = FAMILY_I.find("The Tea Board has its headquarters in Kolkata.")
        self.assertTrue(any(m["text"] == "Kolkata" and m["question_type"] == "Which place…?" for m in m_place))

        self.assertEqual(FAMILY_I.find("Laws are debated in the Parliament."), [])

    def test_j_comparisons_and_superlatives_note_once_never_on_ordinals_pass_and_fail(self) -> None:
        m_sup = FAMILY_J.find("Jupiter is the largest planet in the solar system.")
        self.assertEqual(len(m_sup), 1)
        self.assertEqual(m_sup[0]["text"], "Jupiter")
        self.assertTrue(m_sup[0]["is_superlative"])
        self.assertEqual(m_sup[0]["note"], SUPERLATIVE_CHECK_NOTE)

        self.assertFalse(FAMILY_J.has_true_superlative("Coventry is the eleventh-largest city in the country."))

    def test_k_language_and_grammar_pass_and_fail(self) -> None:
        for sent, expected in (
            ("The opposite of 'ancient' is 'modern'.", "modern"),
            ("The plural of 'cactus' is 'cacti'.", "cacti"),
            ("The past tense of 'teach' is 'taught'.", "taught"),
            ("The word 'bright' rhymes with 'light'.", "light"),
        ):
            matches = FAMILY_K.find(sent)
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]["text"], expected)

        self.assertEqual(FAMILY_K.find("Sound waves require a medium to travel."), [])

    def test_l_reading_sheet_questions_and_matching_to_facts_pass_and_fail(self) -> None:
        for q_line, expected_asks in (
            ("1. Who founded the rural university in 1921?", "person"),
            ("2. When was the municipal charter signed?", "date"),
            ("3. How many delegates attended the convention?", "number"),
            ("4. Which river flows through Nasik?", "river"),
            ("5. Define transpiration.", "term"),
            ("6. Fill in the blanks: Nasik is situated on the ________________.", "place"),
            ("7. True or False: Quartz has a hexagonal crystal structure.", "term"),
        ):
            m_q = FAMILY_L.find(q_line)
            self.assertEqual(len(m_q), 1)
            self.assertTrue(m_q[0]["skip_as_card"])
            self.assertEqual(m_q[0]["asks_for"], expected_asks)

        facts = [
            "The convention was held in the town hall.",
            "The rural university was founded by Rabindranath Tagore in 1921.",
        ]
        signals = FAMILY_L.match_questions_to_facts(
            ["When was the rural university founded by Rabindranath Tagore?"], facts
        )
        self.assertIn(1, signals)
        exprs = find_all_expressions(facts[1], practice_signals=signals[1])
        self.assertEqual(exprs[0]["family"], "L")
        self.assertEqual(exprs[0]["text"], "1921")

        self.assertEqual(FAMILY_L.find("Copper is a good conductor of electricity."), [])

    def test_cut_in_half_span_detection_and_find_item_spans(self) -> None:
        is_cut, reason = check_cut_in_half_span(
            "August",
            source_line="The movement was launched on 8 August 1942.",
            clue="The movement was launched on 8 ______ 1942.",
        )
        self.assertTrue(is_cut, msg=reason)

        is_cut_num, reason_num = check_cut_in_half_span(
            "286",
            source_line="The city has a population of 286,000.",
            clue="The city has a population of ______,000.",
        )
        self.assertTrue(is_cut_num, msg=reason_num)

        is_cut_unit, reason_unit = check_cut_in_half_span(
            "km",
            source_line="The river is 387 km long.",
            clue="The river is 387 ______ long.",
        )
        self.assertTrue(is_cut_unit, msg=reason_unit)

        item = {
            "id": "I1",
            "kind": "point",
            "text": "On 8 August 1942, 286,000 people walked 387 km carrying pure H₂O.",
        }
        spans = find_item_spans(item)
        span_texts = {s["text"] for s in spans}
        self.assertIn("8 August 1942", span_texts)
        self.assertIn("286,000", span_texts)
        self.assertIn("387 km", span_texts)
        self.assertIn("H₂O", span_texts)


if __name__ == "__main__":
    unittest.main(verbosity=2)
