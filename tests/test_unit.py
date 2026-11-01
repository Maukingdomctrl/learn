#!/usr/bin/env python3
"""
tests/test_unit.py
Unit tests for each stage (facts.py, entities.py, relations.py, questions.py, validate.py, output.py)
using made-up sentences (zero lines from the 3 study sheets), with one passing and one failing case
per pattern.
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
        # Passing case: topic with lifespan and epithet title with trailing location
        parsed_pass = facts.parse_topic_header(
            "Vikram Ambalal Sarabhai (1919–1971) – Father of the Indian Space Programme in Gujarat"
        )
        self.assertEqual(parsed_pass["subject"], "Vikram Ambalal Sarabhai")
        self.assertEqual(parsed_pass["lifespan"], "1919–1971")
        self.assertEqual(parsed_pass["subtitle"], "Father of the Indian Space Programme")
        self.assertEqual(parsed_pass["subtitle_kind"], "IS_CALLED")

        # Failing case: topic with comma-separated region instead of epithet title
        parsed_fail = facts.parse_topic_header("MANCHESTER – North West, England")
        self.assertEqual(parsed_fail["subject"], "Manchester")
        self.assertNotEqual(parsed_fail["subtitle_kind"], "IS_CALLED")
        self.assertEqual(parsed_fail["subtitle_kind"], "REGION_HEADER")

    def test_topic_header_capital_pass_and_fail(self) -> None:
        # Passing case: 'Capital of <Place>'
        parsed_pass = facts.parse_topic_header("OTTAWA – Capital of Canada")
        self.assertEqual(parsed_pass["subject"], "Ottawa")
        self.assertEqual(parsed_pass["subtitle"], "Canada")
        self.assertEqual(parsed_pass["subtitle_kind"], "CAPITAL_OF")

        # Failing case: empty topic string
        parsed_fail = facts.parse_topic_header("   ")
        self.assertEqual(parsed_fail["subject"], "")
        self.assertEqual(parsed_fail["subtitle_kind"], "")

    def test_clause_splitting_pass_and_fail(self) -> None:
        # Passing case: semicolons and sentences with honorific 'Dr.' preserved
        text_pass = "Dr. Homi Bhabha directed the institute in 1945; he later chaired the Atomic Energy Commission."
        clauses = facts.split_into_clauses(text_pass)
        self.assertEqual(len(clauses), 2)
        self.assertIn("Dr. Homi Bhabha directed the institute in 1945", clauses[0])

        # Failing case: empty string produces no clauses
        self.assertEqual(facts.split_into_clauses(""), [])


class TestStage2Entities(unittest.TestCase):
    """Stage 2 (entities.py): Atomic recognition of DATE, FORMULA, QUANTITY, NUMBER, TITLE, ORGANISATION, PLACE."""

    def test_date_patterns_pass_and_fail(self) -> None:
        # Passing case: full date, lifespan, century, decade, year kept as single atomic DATE entities
        ents = entities.extract_entities(
            "Opened on 15 August 1947 during the 20th century after the mid-1920s (1889–1964)."
        )
        date_texts = [e["text"] for e in ents if e["type"] == "DATE"]
        self.assertIn("15 August 1947", date_texts)
        self.assertIn("20th century", date_texts)
        self.assertIn("mid-1920s", date_texts)
        self.assertIn("1889–1964", date_texts)

        # Failing case: 3-digit room number is not a DATE
        ents_fail = entities.extract_entities("Room 404 had no calendar.")
        self.assertEqual([e for e in ents_fail if e["type"] == "DATE"], [])

    def test_formula_and_quantity_pass_and_fail(self) -> None:
        # Passing case: formula and quantity kept atomic
        ents = entities.extract_entities("Voltage law: V = IR. Power supports 45,000 jobs worth £3.2 billion.")
        types_by_text = {e["text"]: e["type"] for e in ents}
        self.assertEqual(types_by_text.get("V = IR"), "FORMULA")
        self.assertEqual(types_by_text.get("45,000 jobs"), "QUANTITY")
        self.assertEqual(types_by_text.get("£3.2 billion"), "QUANTITY")

        # Failing case: ordinary prose without numbers or '=' has no FORMULA or QUANTITY
        ents_fail = entities.extract_entities("Copper wires conduct thermal energy efficiently.")
        self.assertEqual([e for e in ents_fail if e["type"] in ("FORMULA", "QUANTITY")], [])

    def test_organisation_and_place_pass_and_fail(self) -> None:
        # Passing case: River <Name> and <Name> College/Museum
        ents = entities.extract_entities("Situated on the River Severn near Balliol College and Ashmolean Museum.")
        types_by_text = {e["text"]: e["type"] for e in ents}
        self.assertEqual(types_by_text.get("River Severn"), "PLACE")
        self.assertEqual(types_by_text.get("Balliol College"), "ORGANISATION")

        # Failing case: lowercase common nouns are not matched as proper PLACE or ORGANISATION
        ents_fail = entities.extract_entities("The small river flowed past the old college.")
        self.assertEqual([e for e in ents_fail if e["type"] in ("PLACE", "ORGANISATION")], [])


class TestStage3Relations(unittest.TestCase):
    """Stage 3 (relations.py): General verb/phrase and table patterns."""

    def test_founded_clause_pass_and_fail(self) -> None:
        # Passing case: 'Founded the <Org> (<Alt>) in <Year> to <Purpose>'
        item_pass = {
            "id": "I10",
            "page": 1,
            "kind": "point",
            "topic": "Rabindranath Tagore (1861–1941) – Bard of Bengal",
            "text": "Founded the Visva Bharati (Abode of Peace) in 1921 to promote rural reconstruction without rote learning.",
            "bold": [],
        }
        rel_list = relations.extract_relations_from_item(item_pass)
        by_rel = {r["relation"]: r["object"] for r in rel_list}
        self.assertEqual(by_rel.get("FOUNDED"), "Visva Bharati")
        self.assertEqual(by_rel.get("FOUNDED_IN"), "1921")
        self.assertEqual(by_rel.get("ALSO_CALLED"), "Abode of Peace")
        self.assertEqual(by_rel.get("PURPOSE"), "to promote rural reconstruction")

        # Failing case: practice question item is ignored even if it contains 'founded'
        item_fail = {
            "id": "I99",
            "page": 2,
            "kind": "question",
            "section": "questions",
            "text": "Founded the Visva Bharati (Abode of Peace) in 1921.",
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_situated_and_home_to_pass_and_fail(self) -> None:
        # Passing case: 'Situated on the River <Name>' and 'Home to the <Org>'
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

        # Failing case: tip item is never extracted
        item_fail = {
            "id": "I12",
            "page": 1,
            "kind": "tip",
            "text": "Situated on the River Avon; Home to the Clifton Suspension Bridge.",
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])

    def test_scientific_determines_and_units_pass_and_fail(self) -> None:
        # Passing case: scientific law and unit definition
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

        # Failing case: heading item is ignored
        item_fail = {
            "id": "I21",
            "page": 1,
            "kind": "heading",
            "text": "Net current determines potential: V = IR.",
        }
        self.assertEqual(relations.extract_relations_from_item(item_fail), [])


class TestStage4Questions(unittest.TestCase):
    """Stage 4 (questions.py): Template generation and GAP fallback."""

    def test_template_question_pass_and_fallback_gap(self) -> None:
        # Passing case: known relation uses specific template
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

        # Fallback case: unknown relation falls back cleanly to GAP card with prompt
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

        # Failing case: front contains the answer (giveaway)
        bad_giveaway = dict(good_card, front="Is Glasgow situated on the River Clyde?")
        reasons = validate.validate_card(bad_giveaway, self.items_by_id, self.vocab, seen)
        self.assertIn("front_contains_answer", reasons)

    def test_unprinted_answer_and_invented_word_fail(self) -> None:
        seen = set()
        # Failing case 1: answer not printed word-for-word in cited item
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

        # Failing case 2: invented word on front not in sheet or ALLOWED_QUESTION_WORDS
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

        # Trivial answer ('the') fails
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


if __name__ == "__main__":
    unittest.main()
