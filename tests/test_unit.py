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
            "front": "______ is the largest planet in the Solar System.",
            "prompt": "Which word fits the gap?",
            "answer": "Jupiter",
            "question_type": "GAP",
            "source_text": sheet["items"][0]["text"],
        }
        self.assertEqual(validate.validate_card(base_card, items_by_id, vocab, set()), [])

        # 1. Invented word in front
        bad_front = dict(base_card, front="______ is the largest astrophysical planet in the Solar System.")
        r_front = validate.validate_card(bad_front, items_by_id, vocab, set())
        self.assertIn("invented_word:astrophysical", r_front)

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


class TestRound3ChangesAtoH(unittest.TestCase):
    """Step 3: One passing and one failing unit test for each of Changes A–H using MADE-UP sentences/tables."""

    def test_change_a_points_under_headings_pass_and_fail(self) -> None:
        sheet = {
            "sheet": "synthetic-heading-points",
            "items": [
                {
                    "id": "H1",
                    "page": 1,
                    "kind": "heading",
                    "text": "1. Vikram Sarabhai (1919–1971) — Father of the Indian Space Programme",
                },
                {
                    "id": "P1",
                    "page": 1,
                    "kind": "point",
                    "text": "Founded the Physical Research Laboratory in 1947.",
                },
                {
                    "id": "P2",
                    "page": 1,
                    "kind": "point",
                    "text": "His efforts led to the Aryabhata Satellite Launch of 1975.",
                },
                {
                    "id": "T1",
                    "page": 1,
                    "kind": "tip",
                    "text": "Remember to revise all dates carefully.",
                },
            ],
        }
        res = output.run_pipeline(sheet)
        cards = res["cards"]
        answers = {c["answer"] for c in cards}
        # PASS: Points P1 and P2 under heading H1 produce cards using Vikram Sarabhai as subject, alongside heading cards
        self.assertIn("Physical Research Laboratory", answers)
        self.assertIn("1947", answers)
        self.assertIn("Aryabhata Satellite Launch", answers)
        self.assertIn("Father of the Indian Space Programme", answers)
        self.assertIn("1919–1971", answers)
        # FAIL: Tip item T1 under heading produces 0 facts/cards
        self.assertFalse(any(c["item_id"] == "T1" for c in cards))

    def test_change_b_tables_who_what_where_vs_measurements_pass_and_fail(self) -> None:
        # PASS 1: Who-what-where table of names/places -> 'Which <column> goes with <row>?'
        who_table_item = {
            "id": "TB1",
            "page": 1,
            "kind": "table",
            "table": {
                "header": ["Dam", "River", "State"],
                "rows": [
                    ["Hirakud Dam", "River Mahanadi", "Odisha"],
                    ["Bhakra Nangal Dam", "River Sutlej", "Himachal Pradesh"],
                ],
            },
        }
        facts_who = relations.extract_relations_from_item(who_table_item)
        self.assertEqual(len(facts_who), 4)
        c0 = questions.generate_card(dict(facts_who[0], id="F1"), "C1")
        self.assertEqual(c0["front"], "Which River goes with Hirakud Dam?")
        self.assertEqual(c0["answer"], "River Mahanadi")

        # PASS 2: Measurement table WITH extremum stated in sheet prose -> at most 2 cards (highest & lowest)
        meas_table_item = {
            "id": "TB2",
            "page": 1,
            "kind": "table",
            "table": {
                "header": ["Month", "Rainfall (mm)"],
                "rows": [
                    ["May", "18"],
                    ["June", "140"],
                    ["July", "320"],
                    ["August", "290"],
                ],
            },
        }
        facts_meas_stated = relations.extract_relations_from_item(
            meas_table_item,
            sheet_prose="July receives the highest rainfall while May receives the lowest rainfall.",
        )
        self.assertEqual(len(facts_meas_stated), 2)
        self.assertEqual({f["object"] for f in facts_meas_stated}, {"18", "320"})

        # FAIL: Measurement table WITHOUT extremum stated in sheet prose -> 0 cards (never quiz every cell)
        facts_meas_unstated = relations.extract_relations_from_item(
            meas_table_item,
            sheet_prose="Monsoon winds blow across the coast every summer.",
        )
        self.assertEqual(facts_meas_unstated, [])

    def test_change_c_gap_prompts_match_answer_pass_and_fail(self) -> None:
        # PASS: Each answer type gets its specific prompt
        self.assertEqual(questions.classify_gap_prompt("Dr. Rajendra Prasad", category="person"), "Who fits the gap?")
        self.assertEqual(
            questions.classify_gap_prompt("Jamshedpur", category="place", source_text="set up at Jamshedpur in 1907"),
            "Which place fits the gap?",
        )
        self.assertEqual(questions.classify_gap_prompt("1907", category="date"), "Which year fits the gap?")
        self.assertEqual(questions.classify_gap_prompt("15 August 1947", category="date"), "Which date fits the gap?")
        self.assertEqual(questions.classify_gap_prompt("19th century", category="date"), "Which century fits the gap?")
        self.assertEqual(questions.classify_gap_prompt("250 km", category="quantity"), "Which number fits the gap?")
        self.assertEqual(questions.classify_gap_prompt("Widow Remarriage Act", category="document"), "Which name fits the gap?")
        self.assertEqual(questions.classify_gap_prompt("chlorophyll", category="term"), "Which term fits the gap?")

        # FAIL: None of those typed answers gets 'Which word fits the gap?'
        for ans, cat in (
            ("Dr. Rajendra Prasad", "person"),
            ("Jamshedpur", "place"),
            ("1907", "date"),
            ("15 August 1947", "date"),
            ("19th century", "date"),
            ("250 km", "quantity"),
            ("Widow Remarriage Act", "document"),
            ("chlorophyll", "term"),
        ):
            self.assertNotEqual(questions.classify_gap_prompt(ans, category=cat), "Which word fits the gap?")

    def test_change_d_comparison_lines_gap_pass_and_fail(self) -> None:
        item = {
            "id": "I1",
            "page": 1,
            "kind": "summary",
            "topic": "Types of Industry",
            "text": "Agro-based Industry = cotton to cloth (uses plant products).",
        }
        rels = relations.extract_relations_from_item(item)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        # PASS: Gap card on the sheet's own line
        self.assertEqual(card["front"], "Agro-based Industry = ______ (uses plant products).")
        self.assertEqual(card["answer"], "cotton to cloth")
        self.assertEqual(card["prompt"], "Which term fits the gap?")
        # FAIL: Never 'In the comparison, what does X equal?' in primary or alternatives
        self.assertNotIn("In the comparison", card["front"])
        for alt in card.get("_alternatives", []):
            self.assertNotIn("In the comparison", alt["front"])

    def test_change_e_full_names_pass_and_fail(self) -> None:
        item = {
            "id": "I1",
            "page": 1,
            "kind": "point",
            "topic": "Social Reformers",
            "text": "Ishwar Chandra Vidyasagar is called the Pioneer of Modern Bengali Prose.",
        }
        rels = relations.extract_relations_from_item(item)
        self.assertEqual(len(rels), 1)
        card = questions.generate_card(dict(rels[0], id="F1"), "C1")
        # PASS: Full printed name is used as answer
        self.assertEqual(card["front"], "Who is called the Pioneer of Modern Bengali Prose?")
        self.assertEqual(card["answer"], "Ishwar Chandra Vidyasagar")

        # FAIL: Shortened surname-only answer 'Vidyasagar' is rejected by validate_card
        items_by_id = {"I1": item}
        vocab = validate.build_sheet_vocabulary({"items": [item]})
        bad_card = dict(card, answer="Vidyasagar")
        reasons = validate.validate_card(bad_card, items_by_id, vocab, set())
        self.assertIn("shortened_person_name", reasons)

    def test_change_f_qa_layouts_and_short_sheets_pass_and_fail(self) -> None:
        qa_sheet = {
            "sheet": "synthetic-qa",
            "items": [
                {
                    "id": "Q1",
                    "page": 1,
                    "kind": "point",
                    "text": "Q1. Where was the first jute mill set up? Answer: The first jute mill was set up at Rishra in 1855.",
                },
                {
                    "id": "Q2",
                    "page": 1,
                    "kind": "point",
                    "text": "Q2. Who founded the Servants of India Society? Answer: Gopal Krishna Gokhale founded the Servants of India Society in 1905.",
                },
            ],
        }
        res_qa = output.run_pipeline(qa_sheet)
        qa_cards = res_qa["cards"]
        qa_answers = {c["answer"] for c in qa_cards}
        # PASS: Extracts short factual answers from inside the model answers
        self.assertIn("Rishra", qa_answers)
        self.assertIn("1855", qa_answers)
        self.assertIn("Servants of India Society", qa_answers)
        # FAIL: Never copies the raw Q1 question prefix onto a card
        for c in qa_cards:
            self.assertFalse(c["front"].startswith("Q1."))
            self.assertFalse(c["front"].startswith("Q2."))

        # PASS: Short revision sheet (2 lines, no headings) gets a card for each line
        short_sheet = {
            "sheet": "short-revision",
            "items": [
                {
                    "id": "S1",
                    "page": 1,
                    "kind": "point",
                    "text": "Transpiration is the loss of water vapour from plant leaves.",
                },
                {
                    "id": "S2",
                    "page": 1,
                    "kind": "point",
                    "text": "The Hirakud Dam is situated on the River Mahanadi.",
                },
            ],
        }
        res_short = output.run_pipeline(short_sheet)
        self.assertEqual(len(res_short["cards"]), 2)

    def test_change_g_reinforcement_pass_and_fail(self) -> None:
        sheet = {
            "sheet": "synthetic-reinforcement",
            "items": [
                {
                    "id": "I1",
                    "page": 1,
                    "kind": "heading",
                    "text": "Pandita Ramabai (1858–1922) — Pioneer of Women's Education",
                },
                {
                    "id": "I2",
                    "page": 1,
                    "kind": "point",
                    "text": "Founded the Sharada Sadan in 1889.",
                },
            ],
        }
        res = output.run_pipeline(sheet)
        cards = res["cards"]
        fronts = [c["front"] for c in cards]
        # PASS: Core fact gets both forward and reverse-direction cards, at least 3 cards apart
        self.assertIn("Which organisation did Pandita Ramabai found?", fronts)
        self.assertIn("Who founded the Sharada Sadan?", fronts)
        idx_fwd = fronts.index("Which organisation did Pandita Ramabai found?")
        idx_rev = fronts.index("Who founded the Sharada Sadan?")
        self.assertGreaterEqual(abs(idx_rev - idx_fwd), 3)

        # FAIL: Never the same question or gap twice
        self.assertEqual(len(fronts), len(set(fronts)))

    def test_change_h_question_variety_pass_and_fail(self) -> None:
        # Build 6 consecutive GAP cards that have valid WHAT/HOW_MANY alternatives
        raw_cards = []
        for idx in range(1, 7):
            raw_cards.append({
                "id": f"C{idx}",
                "fact_id": f"F{idx}",
                "item_id": f"I{idx}",
                "page": 1,
                "label": f"Topic {idx}",
                "front": f"Topic {idx} has value ______.",
                "prompt": "Which term fits the gap?",
                "answer": f"term{idx}",
                "question_type": "GAP",
                "source_text": f"Topic {idx} has value term{idx}.",
                "subject": f"Topic {idx}",
                "status": "selected",
                "_alternatives": [
                    {
                        "front": f"What is the value in Topic {idx}?",
                        "prompt": "",
                        "question_type": "WHAT" if idx % 2 == 0 else "HOW_MANY",
                    }
                ],
            })
        mixed = questions.balance_question_mix(raw_cards)
        qtypes = [c["question_type"] for c in mixed]
        # PASS: At least 3 distinct types, GAP <= 60%, and order of items preserved
        self.assertGreaterEqual(len(set(qtypes)), 3)
        self.assertLessEqual(qtypes.count("GAP"), 3)
        self.assertEqual([c["item_id"] for c in mixed], ["I1", "I2", "I3", "I4", "I5", "I6"])
        # FAIL: No 4 consecutive cards share the same question_type
        for i in range(len(qtypes) - 3):
            self.assertFalse(qtypes[i] == qtypes[i + 1] == qtypes[i + 2] == qtypes[i + 3])


class TestRound4Polish(unittest.TestCase):
    """Round 4 Polish: 5 focused fixes with one passing and one failing made-up test each."""

    def test_fix1_no_in_subject_prefix_pass_and_fail(self) -> None:
        # PASS 1: Subjectless sentence either starts with subject + verb ('Dadabhai Naoroji was a founding member of ...')
        # or keeps the sheet's sentence as is ('Worked to expose the ______.'), relying on the card label.
        item_member = {
            "id": "P1",
            "page": 1,
            "kind": "point",
            "topic": "1. Dadabhai Naoroji (1825–1917) — Grand Old Man of India",
            "text": "Founding member of the Indian National Congress in 1885.",
        }
        rels_p1 = relations.extract_relations_from_item(item_member)
        self.assertEqual(len(rels_p1), 1)
        card_p1 = questions.generate_card(dict(rels_p1[0], id="F1"), "C1")
        self.assertEqual(card_p1["front"], "Dadabhai Naoroji was a founding member of the ______ in 1885.")
        self.assertEqual(card_p1["label"], "Dadabhai Naoroji")

        item_worked = {
            "id": "P2",
            "page": 1,
            "kind": "point",
            "topic": "1. Dadabhai Naoroji (1825–1917) — Grand Old Man of India",
            "text": "Worked to expose the drain of wealth.",
        }
        rels_p2 = relations.extract_relations_from_item(item_worked)
        self.assertEqual(len(rels_p2), 1)
        card_p2 = questions.generate_card(dict(rels_p2[0], id="F2"), "C2")
        self.assertEqual(card_p2["front"], "Worked to expose the ______.")
        self.assertEqual(card_p2["label"], "Dadabhai Naoroji")

        # FAIL: Card with 'In <person>, ...' prefix is rejected by validate_card
        sheet = {"sheet": "made-up-fix1.pdf", "items": [item_member, item_worked]}
        items_by_id = {"P1": item_member, "P2": item_worked}
        vocab = validate.build_sheet_vocabulary(sheet)
        bad_card = dict(card_p2, front="In Dadabhai Naoroji, worked to expose the ______.")
        reasons = validate.validate_card(bad_card, items_by_id, vocab, set())
        self.assertIn("in_subject_prefix", reasons)

    def test_fix2_year_cards_cap_preference_and_trimming_pass_and_fail(self) -> None:
        # PASS 1: When a line has both an organisation/place and a year in the fallback, prefer the non-year fact
        item_pref = {
            "id": "P1",
            "page": 1,
            "kind": "point",
            "topic": "Maritime Trade",
            "text": "Merchants signed the Treaty of Surat during 1612.",
        }
        rels_pref = relations.extract_relations_from_item(item_pref)
        self.assertEqual(rels_pref[0]["object"], "Treaty of Surat")

        # PASS 2: Year card clue is trimmed to the clause holding the year (<= 20 words),
        # and at most 40% of a card set are year/date cards.
        long_src = (
            "The royal observatory was constructed on the high granite ridge overlooking the harbour in 1894; "
            "it later housed three large refracting telescopes and a library of star charts for navigators."
        )
        trimmed = questions.trim_year_clause(long_src, "1894", max_words=20)
        self.assertIn("1894", trimmed)
        self.assertLessEqual(len(trimmed.split()), 20)

        sheet_years = {
            "sheet": "made-up-fix2.pdf",
            "items": [
                {"id": "I1", "page": 1, "kind": "point", "topic": "History", "text": "The northern treaty was signed in 1802."},
                {"id": "I2", "page": 1, "kind": "point", "topic": "History", "text": "The southern canal opened in 1815."},
                {"id": "I3", "page": 1, "kind": "point", "topic": "History", "text": "The western railway began in 1830."},
                {"id": "I4", "page": 1, "kind": "point", "topic": "History", "text": "The eastern university was founded in 1845."},
                {"id": "I5", "page": 1, "kind": "point", "topic": "History", "text": "The central museum was situated on the River Severn."},
                {"id": "I6", "page": 1, "kind": "point", "topic": "History", "text": "The Royal Botanical Society was located in Bristol."},
                {"id": "I7", "page": 1, "kind": "point", "topic": "History", "text": "Charles Darwin wrote the Origin of Species."},
            ],
        }
        res_y = output.run_pipeline(sheet_years)
        cards_y = res_y["cards"]
        yr_cnt = sum(
            1
            for c in cards_y
            if c["question_type"] == "WHEN"
            or c.get("prompt") in ("Which year fits the gap?", "Which date fits the gap?", "Which century fits the gap?", "Give the date or year")
        )
        self.assertLessEqual(yr_cnt / len(cards_y), 0.4001)

        # FAIL: Year card clue > 20 words is rejected by validate_card
        item_long = {"id": "L1", "page": 1, "kind": "point", "topic": "History", "text": long_src}
        vocab_l = validate.build_sheet_vocabulary({"items": [item_long]})
        bad_year_card = {
            "id": "C1",
            "fact_id": "F1",
            "item_id": "L1",
            "page": 1,
            "label": "History",
            "subject": "History",
            "front": long_src.replace("1894", "______"),
            "prompt": "Which year fits the gap?",
            "answer": "1894",
            "question_type": "GAP",
            "source_text": long_src,
        }
        reasons_l = validate.validate_card(bad_year_card, {"L1": item_long}, vocab_l, set())
        self.assertIn("year_clue_too_long", reasons_l)

    def test_fix3_chemical_formulas_and_symbols_prompt_pass_and_fail(self) -> None:
        # PASS: Chemical formulas and symbols (CO2, H2O, O2, C6H12O6, NaCl) get 'Which formula fits the gap?'
        for chem in ("CO2", "H2O", "O2", "C6H12O6", "NaCl", "H₂SO₄"):
            prompt = questions.classify_gap_prompt(
                chem,
                source_text=f"Plants use or produce {chem} during the chemical reaction.",
            )
            self.assertEqual(prompt, "Which formula fits the gap?", f"Failed for {chem}: got {prompt}")
            # FAIL: Never 'Which number fits the gap?'
            self.assertNotEqual(prompt, "Which number fits the gap?")

        # Also test full card generation on a made-up chemistry point
        item_chem = {
            "id": "C1",
            "page": 1,
            "kind": "point",
            "topic": "Photosynthesis",
            "text": "Green leaves absorb CO2 from the air to synthesize C6H12O6.",
            "bold": ["CO2"],
        }
        rels_c = relations.extract_relations_from_item(item_chem)
        self.assertEqual(len(rels_c), 1)
        card_c = questions.generate_card(dict(rels_c[0], id="F1"), "C1")
        self.assertEqual(card_c["answer"], "CO2")
        self.assertEqual(card_c["prompt"], "Which formula fits the gap?")
        self.assertNotEqual(card_c["prompt"], "Which number fits the gap?")

    def test_fix4_places_inside_lists_pass_and_fail(self) -> None:
        # PASS: Places inside lists get 'Which place fits the gap?'
        item_centres = {
            "id": "P1",
            "page": 1,
            "kind": "point",
            "topic": "Cotton Textile Industry",
            "text": "Main centres: Surat, Ahmedabad and Coimbatore.",
        }
        rels_1 = relations.extract_relations_from_item(item_centres)
        self.assertEqual(len(rels_1), 1)
        card_1 = questions.generate_card(dict(rels_1[0], id="F1"), "C1")
        self.assertEqual(card_1["front"], "Main centres: ______, Ahmedabad and Coimbatore.")
        self.assertEqual(card_1["answer"], "Surat")
        self.assertEqual(card_1["prompt"], "Which place fits the gap?")

        item_states = {
            "id": "P2",
            "page": 1,
            "kind": "point",
            "topic": "Sugar Industry",
            "text": "Main states: Uttar Pradesh and Tamil Nadu.",
        }
        rels_2 = relations.extract_relations_from_item(item_states)
        self.assertEqual(len(rels_2), 1)
        card_2 = questions.generate_card(dict(rels_2[0], id="F2"), "C2")
        self.assertEqual(card_2["front"], "Main states: ______ and Tamil Nadu.")
        self.assertEqual(card_2["answer"], "Uttar Pradesh")
        self.assertEqual(card_2["prompt"], "Which place fits the gap?")

        # FAIL: Non-place list ('Push factors: lack of jobs, poverty and droughts') does NOT get 'Which place fits the gap?'
        prompt_non_place = questions.classify_gap_prompt(
            "lack of jobs",
            category="term",
            source_text="Push factors: lack of jobs, poverty and droughts.",
        )
        self.assertNotEqual(prompt_non_place, "Which place fits the gap?")

    def test_fix5_qa_and_timeline_sheets_coverage_pass_and_fail(self) -> None:
        # PASS 1: Q&A sheet (multi-item questions followed by model answers + inline Q&A) achieves >= 50% point coverage
        qa_sheet = {
            "sheet": "made-up-qa-sheet.pdf",
            "items": [
                {"id": "H1", "page": 1, "kind": "heading", "text": "Revision Questions and Model Answers"},
                {"id": "Q1", "page": 1, "kind": "point", "text": "Q1. Where was the first cotton mill set up?"},
                {"id": "A1", "page": 1, "kind": "point", "text": "Ans: The first cotton mill was set up at Mumbai in 1854."},
                {"id": "Q2", "page": 1, "kind": "point", "text": "Q2. Who wrote the book Geetanjali?"},
                {"id": "A2", "page": 1, "kind": "point", "text": "Answer: Rabindranath Tagore wrote the book Geetanjali."},
                {"id": "QA3", "page": 1, "kind": "point", "text": "Q3. Which river is Surat situated on? — Surat is situated on the River Tapi."},
            ],
        }
        res_qa = output.run_pipeline(qa_sheet)
        qa_cards = res_qa["cards"]
        qa_answers = {c["answer"] for c in qa_cards}
        self.assertIn("Mumbai", qa_answers)
        self.assertIn("Geetanjali", qa_answers)
        self.assertIn("River Tapi", qa_answers)
        # Answer points A1, A2, QA3 all covered (>= 50% of all points on the sheet)
        covered_ids = {c["item_id"] for c in qa_cards}
        point_ids = {it["id"] for it in qa_sheet["items"] if it["kind"] == "point"}
        self.assertGreaterEqual(len(covered_ids & point_ids) / len(point_ids), 0.50)

        # PASS 2: Timeline sheet (bullet rows + timeline table) achieves >= 50% point coverage
        timeline_sheet = {
            "sheet": "made-up-timeline-sheet.pdf",
            "items": [
                {"id": "H1", "page": 1, "kind": "heading", "text": "Important Events Timeline"},
                {"id": "T1", "page": 1, "kind": "point", "topic": "Timeline", "text": "1875 — Swami Dayanand Saraswati founded the Arya Samaj."},
                {"id": "T2", "page": 1, "kind": "point", "topic": "Timeline", "text": "1897: Swami Vivekananda established the Ramakrishna Mission."},
                {"id": "T3", "page": 1, "kind": "point", "topic": "Timeline", "text": "1905 — Partition of Bengal was announced by Lord Curzon."},
                {
                    "id": "TB1",
                    "page": 1,
                    "kind": "table",
                    "topic": "Chronology",
                    "table": {
                        "header": ["Year", "Historical Event"],
                        "rows": [
                            ["1919", "Jallianwala Bagh Massacre took place in Amritsar."],
                            ["1920", "Non-Cooperation Movement was launched by Mahatma Gandhi."],
                        ],
                    },
                },
            ],
        }
        res_tl = output.run_pipeline(timeline_sheet)
        tl_cards = res_tl["cards"]
        tl_answers = {c["answer"] for c in tl_cards}
        self.assertTrue({"Arya Samaj", "1875"} & tl_answers)
        self.assertTrue({"Ramakrishna Mission", "1897"} & tl_answers)
        self.assertTrue({"Partition of Bengal", "Lord Curzon", "1905"} & tl_answers)
        tl_covered = {c["item_id"] for c in tl_cards}
        tl_points = {"T1", "T2", "T3", "TB1"}
        self.assertGreaterEqual(len(tl_covered & tl_points) / len(tl_points), 0.75)

        # FAIL: Unanswered question-only sheet (no answers provided) produces 0 cards (never turns raw questions into cards)
        unanswered_sheet = {
            "sheet": "unanswered-questions.pdf",
            "items": [
                {"id": "U1", "page": 1, "kind": "point", "text": "Q1. Where was the first cotton mill set up?"},
                {"id": "U2", "page": 1, "kind": "point", "text": "Q2. Why are monsoon winds important for agriculture?"},
            ],
        }
        res_unans = output.run_pipeline(unanswered_sheet)
        self.assertEqual(res_unans["cards"], [])


if __name__ == "__main__":
    unittest.main()

