#!/usr/bin/env python3
"""
tests/test_unit.py
Unit tests for each stage (facts.py, entities.py, relations.py, questions.py, validate.py, output.py)
and for Round 2 general patterns (a)–(i) using made-up sentences (zero lines from the study sheets),
with one passing and one failing case per pattern, plus vocabulary validation on front, label, and answer.
"""
from __future__ import annotations
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine import facts, entities, relations, questions, validate, output


class TestStage1Facts(unittest.TestCase):
    """Stage 1 (facts.py): Topic header parsing, clause splitting, and subject canonicalization."""

    def test_topic_header_epithet_pass_and_fail(self) -> None:
        parsed_pass = facts.parse_topic_header(
            "Vikram Ambalal Sarabhai (1919–1971) – Father of the Indian Space Programme in Gujarat"
        )
        self.assertEqual(parsed_pass["subject"], "Vikram Ambalal Sarabhai")
        self.assertEqual(parsed_pass["lifespan"], "1919–1971")
        self.assertEqual(parsed_pass["subtitle"], "Father of the Indian Space Programme")
        self.assertEqual(parsed_pass["subtitle_kind"], "IS_CALLED")

        parsed_fail = facts.parse_topic_header("MANCHESTER – North West, England")
        self.assertEqual(parsed_fail["subject"], "Manchester")
        self.assertNotEqual(parsed_fail["subtitle_kind"], "IS_CALLED")
        self.assertEqual(parsed_fail["subtitle_kind"], "REGION_HEADER")

    def test_topic_header_capital_pass_and_fail(self) -> None:
        parsed_pass = facts.parse_topic_header("OTTAWA – Capital of Canada")
        self.assertEqual(parsed_pass["subject"], "Ottawa")
        self.assertEqual(parsed_pass["subtitle"], "Canada")
        self.assertEqual(parsed_pass["subtitle_kind"], "CAPITAL_OF")

        parsed_fail = facts.parse_topic_header("   ")
        self.assertEqual(parsed_fail["subject"], "")
        self.assertEqual(parsed_fail["subtitle_kind"], "")

    def test_clause_splitting_pass_and_fail(self) -> None:
        text_pass = "Dr. Homi Bhabha directed the institute in 1945; he later chaired the Atomic Energy Commission."
        clauses = facts.split_into_clauses(text_pass)
        self.assertEqual(len(clauses), 2)
        self.assertIn("Dr. Homi Bhabha directed the institute in 1945", clauses[0])

        self.assertEqual(facts.split_into_clauses(""), [])


class TestStage2Entities(unittest.TestCase):
    """Stage 2 (entities.py): Atomic recognition of DATE, FORMULA, QUANTITY, NUMBER, TITLE, ORGANISATION, PLACE."""

    def test_date_patterns_pass_and_fail(self) -> None:
        ents = entities.extract_entities(
            "Opened on 15 August 1947 during the 20th century after the mid-1920s (1889–1964)."
        )
        date_texts = [e["text"] for e in ents if e["type"] == "DATE"]
        self.assertIn("15 August 1947", date_texts)
        self.assertIn("20th century", date_texts)
        self.assertIn("mid-1920s", date_texts)
        self.assertIn("1889–1964", date_texts)

        ents_fail = entities.extract_entities("Room 404 had no calendar.")
        self.assertEqual([e for e in ents_fail if e["type"] == "DATE"], [])

    def test_formula_and_quantity_pass_and_fail(self) -> None:
        ents = entities.extract_entities("Voltage law: V = IR. Power supports 45,000 jobs worth £3.2 billion.")
        types_by_text = {e["text"]: e["type"] for e in ents}
        self.assertEqual(types_by_text.get("V = IR"), "FORMULA")
        self.assertEqual(types_by_text.get("45,000"), "NUMBER")
        self.assertEqual(types_by_text.get("£3.2 billion"), "QUANTITY")

        ents_fail = entities.extract_entities("Copper wires conduct thermal energy efficiently.")
        self.assertEqual([e for e in ents_fail if e["type"] in ("FORMULA", "QUANTITY")], [])

    def test_organisation_and_place_pass_and_fail(self) -> None:
        ents = entities.extract_entities("Situated on the River Severn near Balliol College and Ashmolean Museum.")
        types_by_text = {e["text"]: e["type"] for e in ents}
        self.assertEqual(types_by_text.get("River Severn"), "PLACE")
        self.assertEqual(types_by_text.get("Balliol College"), "ORGANISATION")

        ents_fail = entities.extract_entities("The small river flowed past the old college.")
        self.assertEqual([e for e in ents_fail if e["type"] in ("PLACE", "ORGANISATION")], [])


class TestStage3Relations(unittest.TestCase):
    """Stage 3 (relations.py): General verb/phrase and table patterns."""

    def test_founded_clause_pass_and_fail(self) -> None:
        item_pass = {
            "id": "I10",
            "page": 1,
            "kind": "point",
            "topic": "Rabindranath Tagore (1861–1941) – Leader of Bengal Literature",
            "text": "Founded the Visva Bharati (Abode of Peace) in 1921 to promote rural reconstruction without rote learning.",
            "bold": [],
        }
        rel_list = relations.extract_relations_from_item(item_pass)
        by_rel = {r["relation"]: r["object"] for r in rel_list}
        self.assertEqual(by_rel.get("FOUNDED"), "Visva Bharati")
        self.assertEqual(by_rel.get("FOUNDED_IN"), "1921")
        self.assertEqual(by_rel.get("ALSO_CALLED"), "Abode of Peace")
        self.assertEqual(by_rel.get("PURPOSE"), "to promote rural reconstruction")

        item_fail = {
            "id": "I99",
            "page": 2,
            "kind": "question",
            "section": "questions",
            "text": "Founded the Visva Bharati (Abode of Peace) in 1921.",
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_situated_and_home_to_pass_and_fail(self) -> None:
        item_pass = {
            "id": "I11",
            "page": 1,
            "kind": "point",
            "topic": "BRISTOL – South West, England",
            "text": "Situated on the River Avon; Home to the Clifton Suspension Bridge.",
            "bold": ["River Avon"],
        }
        rel_list = relations.extract_relations_from_item(item_pass)
        by_rel = {r["relation"]: r["object"] for r in rel_list}
        self.assertEqual(by_rel.get("SITUATED_ON"), "River Avon")
        self.assertEqual(by_rel.get("HOME_TO"), "Clifton Suspension Bridge")

        item_fail = {
            "id": "I12",
            "page": 1,
            "kind": "tip",
            "text": "Situated on the River Avon; Home to the Clifton Suspension Bridge.",
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_scientific_determines_and_units_pass_and_fail(self) -> None:
        item_pass = {
            "id": "I20",
            "page": 1,
            "kind": "point",
            "context": "OHM MODEL",
            "text": "Net current determines potential: V = IR.",
        }
        rel_list = relations.extract_relations_from_item(item_pass)
        by_rel = {r["relation"]: r["object"] for r in rel_list}
        self.assertEqual(by_rel.get("DETERMINES"), "potential")
        self.assertEqual(by_rel.get("FORMULA"), "V = IR")

        item_fail = {
            "id": "I21",
            "page": 1,
            "kind": "heading",
            "text": "Net current determines potential: V = IR.",
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])


class TestRound2GeneralPatterns(unittest.TestCase):
    """Step 5: One passing and one failing test (on made-up sentences) for each general pattern a–i,
    plus strict vocabulary checking on front, label, and answer.
    """

    def test_pattern_a_label_value_pass_and_fail(self) -> None:
        # Passing: 'Term: 4 years' and 'Presiding officer: the Chancellor'
        item_term = {
            "id": "I1",
            "page": 1,
            "kind": "point",
            "topic": "FEDERAL SENATE",
            "text": "Term: 4 years, unless dissolved.",
            "bold": ["4 years"],
        }
        rels = relations.extract_relations_from_item(item_term)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["front"], "What is the term of Federal Senate?")
        self.assertEqual(card["answer"], "4 years")

        # Passing long cause with bold term
        item_cause = {
            "id": "I2",
            "page": 1,
            "kind": "point",
            "topic": "MARITIME REBELLION",
            "text": "Economic: heavy salt taxation drove coastal fishermen into severe debt.",
            "bold": ["salt taxation"],
        }
        rels_c = relations.extract_relations_from_item(item_cause)
        self.assertEqual(len(rels_c), 1)
        self.assertEqual(rels_c[0]["object"], "salt taxation")

        # Failing: tip item with 'Label: value' is ignored
        item_fail = dict(item_term, kind="tip")
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_pattern_b_requirements_and_limits_pass_and_fail(self) -> None:
        # Passing: minimum age and retirement age
        item_age = {
            "id": "I3",
            "page": 1,
            "kind": "point",
            "topic": "FEDERAL SENATE",
            "text": "A senator must be at least 28 years old.",
            "bold": ["28 years"],
        }
        rels = relations.extract_relations_from_item(item_age)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["front"], "What is the minimum age for a senator of Federal Senate?")
        self.assertEqual(card["answer"], "28 years")

        # Failing: prose without an age requirement does not match MIN_AGE
        item_fail = {
            "id": "I4",
            "page": 1,
            "kind": "point",
            "topic": "FEDERAL SENATE",
            "text": "Senators debate bills in the main chamber.",
            "bold": [],
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_pattern_c_passive_and_active_roles_pass_and_fail(self) -> None:
        # Passing: 'Its <group> are appointed by the <Agent>' (resolving 'Its' to topic)
        item_pass = {
            "id": "I5",
            "page": 1,
            "kind": "point",
            "topic": "HIGH TRIBUNAL",
            "text": "Its magistrates are appointed by the Monarch.",
            "bold": ["Monarch"],
        }
        rels = relations.extract_relations_from_item(item_pass)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["front"], "Who appoints the magistrates of High Tribunal?")
        self.assertEqual(card["answer"], "the Monarch")

        # Failing: practice answer item is ignored
        item_fail = dict(item_pass, kind="answer", section="answers")
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_pattern_d_definitions_and_is_called_pass_and_fail(self) -> None:
        # Passing: '<It> is called the <Y>' and '<X> – <Y>' role definition without bad capital 'The'
        item_called = {
            "id": "I6",
            "page": 1,
            "kind": "point",
            "topic": "THE CHANCELLOR – Head of the Cabinet",
            "text": "It is called the keystone of the executive.",
            "bold": ["keystone of the executive"],
        }
        rels = relations.extract_relations_from_item(item_called)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        # 'The Chancellor' is lowercased to 'the Chancellor' mid-sentence
        self.assertEqual(card["front"], "What is the Chancellor called?")
        self.assertEqual(card["answer"], "keystone of the executive")

        # Failing: plain topic header without epithet or role definition produces no card
        item_fail = {
            "id": "I7",
            "page": 1,
            "kind": "topic",
            "text": "CHAPTER OVERVIEW – General notes",
            "bold": [],
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_pattern_e_comparison_summary_equals_pass_and_fail(self) -> None:
        # Passing: left side of '=' becomes subject, never the last heading
        item_pass = {
            "id": "I8",
            "page": 1,
            "kind": "summary",
            "topic": "HIGH TRIBUNAL",
            "text": "National Assembly = elected chamber (4 years, Speaker)",
            "bold": [],
        }
        rels = relations.extract_relations_from_item(item_pass)
        self.assertEqual(len(rels), 1)
        self.assertEqual(rels[0]["subject"], "National Assembly")
        self.assertEqual(rels[0]["object"], "elected chamber")

        # Failing: algebraic equation with digits on LHS is not treated as SUMMARY_EQUALS
        item_math = {
            "id": "I9",
            "page": 1,
            "kind": "point",
            "topic": "ALGEBRA",
            "text": "4y + 2 = 18",
            "bold": [],
        }
        rels_m = relations.extract_relations_from_item(item_math)
        self.assertNotEqual(rels_m[0]["relation"], "SUMMARY_EQUALS")

    def test_pattern_f_steps_and_processes_pass_and_fail(self) -> None:
        # Passing: step instruction with colon and equation
        item_pass = {
            "id": "I10",
            "page": 1,
            "kind": "point",
            "context": "Solve the linear equation",
            "text": "Add 9 to both sides: 4y = 36",
            "bold": [],
        }
        rels = relations.extract_relations_from_item(item_pass)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["front"], "Add 9 to both sides: 4y = ______.")
        self.assertEqual(card["answer"], "36")

        # Failing: generic instruction without math/entities/bold produces no card
        item_fail = {
            "id": "I11",
            "page": 1,
            "kind": "point",
            "context": "Solve the linear equation",
            "text": "Always verify your working carefully before submitting.",
            "bold": [],
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_pattern_g_equations_and_maths_pass_and_fail(self) -> None:
        # Passing: named formula 'Volume of a cuboid: V = l × w × h'
        item_pass = {
            "id": "I12",
            "page": 1,
            "kind": "point",
            "topic": "Mensuration",
            "text": "Volume of a cuboid: V = l × w × h",
            "bold": [],
        }
        rels = relations.extract_relations_from_item(item_pass)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["question_type"], "FORMULA")
        self.assertEqual(card["answer"], "V = l × w × h")

        # Failing 1: broken PDF glyph in math expression is skipped
        item_broken = {
            "id": "I13",
            "page": 1,
            "kind": "point",
            "topic": "Mensuration",
            "text": "Ratios: ½ + \ufffd = \ufffd",
            "bold": [],
        }
        self.assertEqual(relations.extract_relations_from_item(item_broken), [])

        # Failing 2: splitting a comma-formatted number ('000' from '5,000') is rejected by validator
        item_num = {
            "id": "I14",
            "page": 1,
            "kind": "point",
            "topic": "Finance",
            "text": "Principal invested is 5,000 rupees.",
            "bold": [],
        }
        vocab = validate.build_sheet_vocabulary({"items": [item_num]})
        bad_split_card = {
            "id": "C1",
            "fact_id": "F1",
            "item_id": "I14",
            "page": 1,
            "label": "Finance",
            "subject": "Finance",
            "front": "Principal invested is 5,______ rupees.",
            "prompt": "Which number fits the gap?",
            "answer": "000",
            "question_type": "GAP",
            "source_text": item_num["text"],
        }
        reasons = validate.validate_card(bad_split_card, {"I14": item_num}, vocab, set())
        self.assertTrue("split_number" in reasons or "answer_not_in_cited_item" in reasons)

    def test_pattern_h_tables_pass_and_fail(self) -> None:
        # Passing: general grid table extracts row + column -> cell
        item_table = {
            "id": "I15",
            "page": 1,
            "kind": "table",
            "text": "",
            "table": {
                "kind": "grid",
                "header": ["Outcome", "Fraction", "Percentage"],
                "rows": [["Heads", "1/2", "50%"], ["Tails", "1/2", "50%"]],
            },
        }
        rels = relations.extract_relations_from_item(item_table)
        self.assertTrue(len(rels) >= 2)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["question_type"], "TABLE")
        self.assertEqual(card["front"], "What is the Fraction for Heads?")
        self.assertEqual(card["answer"], "1/2")

        # Failing: empty table produces no relations
        item_empty = {"id": "I16", "page": 1, "kind": "table", "text": "", "table": {"header": [], "rows": []}}
        self.assertEqual(relations.extract_relations_from_item(item_empty), [])

    def test_pattern_i_bullet_point_fallback_pass_and_fail(self) -> None:
        # Passing: bullet point with bold term gets a clean GAP card
        item_bold = {
            "id": "I17",
            "page": 1,
            "kind": "point",
            "topic": "Plant Biology",
            "text": "Light energy is absorbed by chlorophyll inside green leaves.",
            "bold": ["chlorophyll"],
        }
        rels = relations.extract_relations_from_item(item_bold)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        self.assertEqual(card["question_type"], "GAP")
        self.assertEqual(card["front"], "Light energy is absorbed by ______ inside green leaves.")
        self.assertEqual(card["answer"], "chlorophyll")

        # Failing: bullet point with no bold term and no matching pattern gets no card
        item_none = {
            "id": "I18",
            "page": 1,
            "kind": "point",
            "topic": "Plant Biology",
            "text": "Leaves vary considerably in shape and texture across habitats.",
            "bold": [],
        }
        self.assertEqual(relations.extract_relations_from_item(item_none), [])

    def test_vocabulary_enforced_on_front_label_and_answer(self) -> None:
        """Fail if any word in front, label, or answer is outside the sheet or fixed word list."""
        sheet = {
            "sheet": "vocab-check.pdf",
            "items": [
                {
                    "id": "I1",
                    "page": 1,
                    "kind": "point",
                    "topic": "Solar System",
                    "text": "Jupiter is the largest planet in the Solar System.",
                    "bold": ["Jupiter"],
                }
            ],
        }
        items_by_id = {"I1": sheet["items"][0]}
        vocab = validate.build_sheet_vocabulary(sheet)

        base_card = {
            "id": "C1",
            "fact_id": "F1",
            "item_id": "I1",
            "page": 1,
            "label": "Solar System",
            "subject": "Solar System",
            "front": "In Solar System, ______ is the largest planet.",
            "prompt": "Which word fits the gap?",
            "answer": "Jupiter",
            "question_type": "GAP",
            "source_text": sheet["items"][0]["text"],
        }
        self.assertEqual(validate.validate_card(base_card, items_by_id, vocab, set()), [])

        # 1. Invented word in front
        bad_front = dict(base_card, front="In astrophysics, ______ is the largest planet.")
        r_front = validate.validate_card(bad_front, items_by_id, vocab, set())
        self.assertIn("invented_word:astrophysics", r_front)

        # 2. Invented word in label (e.g. reference-list label not on sheet)
        bad_label = dict(base_card, label="Keplerian dynamics")
        r_label = validate.validate_card(bad_label, items_by_id, vocab, set())
        self.assertIn("invented_word:keplerian", r_label)

        # 3. Invented word in answer
        bad_ans = dict(base_card, answer="Saturn")
        r_ans = validate.validate_card(bad_ans, items_by_id, vocab, set())
        self.assertIn("invented_word:saturn", r_ans)


class TestStage4Questions(unittest.TestCase):
    """Stage 4 (questions.py): Template generation and GAP fallback."""

    def test_template_question_pass_and_fallback_gap(self) -> None:
        fact_known = {
            "id": "F1",
            "item_id": "I5",
            "page": 1,
            "source_text": "Situated on the River Clyde.",
            "subject": "Glasgow",
            "relation": "SITUATED_ON",
            "object": "River Clyde",
            "category": "place",
        }
        card = questions.generate_card(fact_known, "C1")
        self.assertEqual(card["question_type"], "WHERE")
        self.assertEqual(card["front"], "Which river is Glasgow situated on?")
        self.assertEqual(card["prompt"], "")

        fact_unknown = {
            "id": "F2",
            "item_id": "I6",
            "page": 1,
            "source_text": "Glasgow hosted the exhibition in 1888.",
            "subject": "Glasgow",
            "relation": "CUSTOM_RELATION",
            "object": "1888",
            "category": "date",
        }
        gap_card = questions.generate_card(fact_unknown, "C2")
        self.assertEqual(gap_card["question_type"], "GAP")
        self.assertEqual(gap_card["front"], "Glasgow hosted the exhibition in ______.")
        self.assertEqual(gap_card["prompt"], "Which year fits the gap?")


class TestStage5Validate(unittest.TestCase):
    """Stage 5 (validate.py): Reject giveaways, unprinted answers, invented words, trivial words, duplicates."""

    def setUp(self) -> None:
        self.reader_json = {
            "sheet": "synthetic-test.pdf",
            "items": [
                {
                    "id": "I1",
                    "page": 1,
                    "kind": "point",
                    "text": "Glasgow is situated on the River Clyde and founded the Kelvin Institute in 1892.",
                }
            ],
        }
        self.items_by_id = {"I1": self.reader_json["items"][0]}
        self.vocab = validate.build_sheet_vocabulary(self.reader_json)

    def test_valid_card_passes_and_giveaway_fails(self) -> None:
        seen = set()
        good_card = {
            "id": "C1",
            "fact_id": "F1",
            "item_id": "I1",
            "page": 1,
            "label": "Glasgow",
            "subject": "Glasgow",
            "front": "Which river is Glasgow situated on?",
            "prompt": "",
            "answer": "River Clyde",
            "question_type": "WHERE",
            "source_text": self.reader_json["items"][0]["text"],
        }
        self.assertEqual(validate.validate_card(good_card, self.items_by_id, self.vocab, seen), [])

        bad_giveaway = dict(good_card, front="Is Glasgow situated on the River Clyde?")
        reasons = validate.validate_card(bad_giveaway, self.items_by_id, self.vocab, seen)
        self.assertIn("front_contains_answer", reasons)

    def test_unprinted_answer_and_invented_word_fail(self) -> None:
        seen = set()
        bad_ans = {
            "id": "C2",
            "fact_id": "F2",
            "item_id": "I1",
            "page": 1,
            "label": "Glasgow",
            "subject": "Glasgow",
            "front": "Which river is Glasgow situated on?",
            "prompt": "",
            "answer": "River Shannon",
            "question_type": "WHERE",
            "source_text": self.reader_json["items"][0]["text"],
        }
        self.assertIn(
            "answer_not_in_cited_item",
            validate.validate_card(bad_ans, self.items_by_id, self.vocab, seen),
        )

        bad_inv = {
            "id": "C3",
            "fact_id": "F3",
            "item_id": "I1",
            "page": 1,
            "label": "Glasgow",
            "subject": "Glasgow",
            "front": "Which municipality encompasses Glasgow?",
            "prompt": "",
            "answer": "River Clyde",
            "question_type": "WHERE",
            "source_text": self.reader_json["items"][0]["text"],
        }
        reasons = validate.validate_card(bad_inv, self.items_by_id, self.vocab, seen)
        self.assertTrue(any(r.startswith("invented_word:") for r in reasons))

    def test_duplicate_and_trivial_answer_fail(self) -> None:
        seen = {("glasgow", "river clyde")}
        dup_card = {
            "id": "C4",
            "fact_id": "F4",
            "item_id": "I1",
            "page": 1,
            "label": "Glasgow",
            "subject": "Glasgow",
            "front": "Which river is Glasgow situated on?",
            "prompt": "",
            "answer": "River Clyde",
            "question_type": "WHERE",
            "source_text": self.reader_json["items"][0]["text"],
        }
        self.assertIn(
            "duplicate_fact",
            validate.validate_card(dup_card, self.items_by_id, self.vocab, seen),
        )

        trivial_card = dict(dup_card, answer="the")
        self.assertIn(
            "trivial_answer",
            validate.validate_card(trivial_card, self.items_by_id, self.vocab, set()),
        )


class TestStage6Output(unittest.TestCase):
    """Stage 6 (output.py): End-to-end JSON schema and max_cards cap."""

    def test_end_to_end_pipeline_pass_and_cap(self) -> None:
        synthetic_sheet = {
            "sheet": "synthetic-cap.pdf",
            "items": [
                {
                    "id": "I1",
                    "page": 1,
                    "kind": "topic",
                    "text": "OTTAWA – Capital of Canada",
                },
                {
                    "id": "I2",
                    "page": 1,
                    "kind": "point",
                    "topic": "OTTAWA – Capital of Canada",
                    "text": "Situated on the River Ottawa; Home to the National Gallery.",
                    "bold": ["River Ottawa"],
                },
            ],
        }
        res = output.run_pipeline(synthetic_sheet, max_cards=2)
        self.assertEqual(res["sheet"], "synthetic-cap.pdf")
        self.assertEqual(len(res["facts"]), 3)
        self.assertEqual(len(res["cards"]), 2)
        self.assertEqual(len(res["rejected"]), 1)
        self.assertIn("below_selection_priority_cutoff", res["rejected"][0]["reasons"])


class TestRound3ShapesAndMix(unittest.TestCase):
    """Round 3: New question shapes (title->name, definition <= 12 words, how many/much/long,
    where, which-goes-with, formula) and question mix constraints across all 8 sheets.
    """

    def test_title_to_person_and_short_definition_templates(self) -> None:
        item_title = {
            "id": "I1",
            "page": 1,
            "kind": "point",
            "topic": "MODERN SCIENCE",
            "text": "Ernest Rutherford is known as the Father of Nuclear Physics.",
            "bold": ["Father of Nuclear Physics"],
        }
        rels = relations.extract_relations_from_item(item_title)
        title_to_person = [r for r in rels if r["relation"] == "TITLE_TO_PERSON"]
        self.assertEqual(len(title_to_person), 1)
        card = questions.generate_card(dict(title_to_person[0], id="F1"), "C1")
        self.assertEqual(card["front"], "Who is called the Father of Nuclear Physics?")
        self.assertEqual(card["answer"], "Ernest Rutherford")
        self.assertEqual(card["question_type"], "WHO")

        item_def = {
            "id": "I2",
            "page": 1,
            "kind": "point",
            "topic": "EVAPORATION",
            "text": "Evaporation is the slow change of a liquid into vapour.",
            "bold": ["Evaporation"],
        }
        rels_def = relations.extract_relations_from_item(item_def)
        self.assertEqual(len(rels_def), 1)
        card_def = questions.generate_card(dict(rels_def[0], id="F2"), "C2")
        self.assertEqual(card_def["front"], "What is the name for the slow change of a liquid into vapour?")
        self.assertEqual(card_def["answer"], "Evaporation")
        self.assertEqual(card_def["question_type"], "WHAT")

    def test_all_8_sheets_satisfy_mix_and_whole_span_constraints(self) -> None:
        import glob
        import json
        from collections import Counter

        paths = sorted(glob.glob("data/*.reader.json")) + sorted(glob.glob("data/round2/*.reader.json"))
        self.assertEqual(len(paths), 8)
        for p in paths:
            with open(p, "r", encoding="utf-8") as fh:
                reader_json = json.load(fh)
            out = output.run_pipeline(reader_json)
            cards = out["cards"]
            self.assertGreaterEqual(len(cards), 3, f"{p} produced fewer than 3 cards")
            self.assertLessEqual(len(cards), 30, f"{p} exceeded 30 cards")

            q_types = [c["question_type"] for c in cards]
            counts = Counter(q_types)
            # At least 3 distinct question types per sheet
            self.assertGreaterEqual(len(counts), 3, f"{p} has fewer than 3 distinct question_types: {counts}")
            # No single question_type > 60% of cards
            for qt, cnt in counts.items():
                self.assertLessEqual(
                    cnt / len(cards),
                    0.6001,
                    f"{p} has question_type {qt} at {cnt}/{len(cards)} (> 60%)",
                )
            # No more than 3 of the same question_type in a row
            cur_run = 0
            prev_t = None
            for idx, qt in enumerate(q_types):
                if qt == prev_t:
                    cur_run += 1
                else:
                    cur_run = 1
                    prev_t = qt
                self.assertLessEqual(
                    cur_run,
                    3,
                    f"{p} has > 3 consecutive {qt} cards ending at card index {idx}",
                )


if __name__ == "__main__":
    unittest.main()

