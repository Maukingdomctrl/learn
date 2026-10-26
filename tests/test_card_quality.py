"""Unit tests for learn/teaching_engine/card_quality.py and offline Key Facts generation."""

from __future__ import annotations

from pathlib import Path
import unittest

from learn.teaching_engine.card_quality import (
    filter_cards_after_plan,
    format_dropped_cards_report,
    is_card_acceptable,
    plan_key_facts_cards,
    score_card,
    write_key_fact_card,
)
from question_quality_engine import generate_questions

SAMPLE_MUMBAI_SHEET = """
FULL CARD
Prominent Personalities of Mumbai

Dadabhai Naoroji (1825–1917)
Known as the 'Grand Old Man of India' (Britannica).
Graduated from Elphinstone College in Mumbai.
Authored Poverty and Un-British Rule in India in 1901.
First Indian elected to the British House of Commons in 1892.

Pherozeshah Mehta (1845–1915)
Known as the 'Lion of Bombay'.
Served as Municipal Commissioner and President of the Indian National Congress in 1890.

Dr. B. R. Ambedkar (1891–1956)
Chaired the Drafting Committee of the Indian Constitution.

Summary Table
Personality | Year | Institution | Role
Dadabhai Naoroji | 1892 | Elphinstone College | Member of Parliament
C. D. Deshmukh | 1950 | Planning Commission | Finance Minister

Memory tip: Naoroji = Numbers & Drain of Wealth (Britannica)
Q1: Who was called the Grand Old Man of India? Ans: Dadabhai Naoroji
""".strip()


class TestCardQualityCriteria(unittest.TestCase):
    """Test each of the 7 rule-based criteria with a passing card and a targeted failing mutation."""

    def test_criterion_1_grounded_pass_and_fail(self) -> None:
        good_card = {
            "clue": "From which college in Mumbai did Dadabhai Naoroji graduate?",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        scores, reasons = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["grounded"], 5)
        self.assertTrue(is_card_acceptable(scores), msg=f"Unexpected reasons: {reasons}")

        # Failing mutation: answer not on the sheet
        bad_card = dict(good_card, answer="St. Xavier's College")
        bad_scores, bad_reasons = score_card(bad_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(bad_scores["grounded"], 1)
        self.assertFalse(is_card_acceptable(bad_scores))
        self.assertTrue(any("grounded:" in r for r in bad_reasons))

    def test_criterion_2_short_answer_pass_and_fail(self) -> None:
        good_card = {
            "clue": "In which year did Dadabhai Naoroji author Poverty and Un-British Rule in India?",
            "answer": "1901",
            "source_line": "Authored Poverty and Un-British Rule in India in 1901.",
            "subject": "Dadabhai Naoroji",
        }
        scores, reasons = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["short_answer"], 5)
        self.assertTrue(is_card_acceptable(scores), msg=f"Unexpected reasons: {reasons}")

        # Failing mutation: full sentence answer instead of a short term/year/name
        bad_card = dict(
            good_card,
            answer="Graduated from Elphinstone College in Mumbai.",
        )
        bad_scores, bad_reasons = score_card(bad_card, SAMPLE_MUMBAI_SHEET)
        self.assertLessEqual(bad_scores["short_answer"], 2)
        self.assertFalse(is_card_acceptable(bad_scores))
        self.assertTrue(any("short_answer:" in r for r in bad_reasons))

    def test_criterion_3_clear_question_pass_and_fail(self) -> None:
        good_card = {
            "clue": "Which committee of the Indian Constitution was chaired by Dr. B. R. Ambedkar?",
            "answer": "Drafting Committee",
            "source_line": "Chaired the Drafting Committee of the Indian Constitution.",
            "subject": "Dr. B. R. Ambedkar",
        }
        scores, reasons = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["clear_question"], 5)
        self.assertTrue(is_card_acceptable(scores), msg=f"Unexpected reasons: {reasons}")

        # Failing mutation 1: template slot filled with a verb fragment
        bad_fragment = dict(
            good_card,
            clue="Explain Graduated from Elphinstone College and its main features.",
            answer="Elphinstone College",
        )
        s1, r1 = score_card(bad_fragment, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s1["clear_question"], 1)
        self.assertFalse(is_card_acceptable(s1))
        self.assertTrue(any("clear_question:" in r for r in r1))

        # Failing mutation 2: cut-off proper noun ("Man Planning Commission")
        bad_cutoff = dict(
            good_card,
            clue="What reason or cause is explained regarding Man Planning Commission, and what is its result?",
            answer="Finance Minister",
        )
        s2, r2 = score_card(bad_cutoff, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s2["clear_question"], 1)
        self.assertFalse(is_card_acceptable(s2))
        self.assertTrue(any("clear_question:" in r for r in r2))

        # Failing mutation 3: generic offline boilerplate ("Explain Indian Industry and its main features." / "Explain FULL CARD and its main features.")
        for bad_template in (
            "Explain Indian Industry and its main features.",
            "Explain FULL CARD and its main features.",
        ):
            s_tpl, r_tpl = score_card(dict(good_card, clue=bad_template), SAMPLE_MUMBAI_SHEET)
            self.assertEqual(s_tpl["clear_question"], 1)
            self.assertFalse(is_card_acceptable(s_tpl))
            self.assertTrue(any("clear_question:" in r for r in r_tpl))

    def test_criterion_4_names_subject_pass_and_fail(self) -> None:
        good_card = {
            "clue": "By what title or epithet was Pherozeshah Mehta known?",
            "answer": "Lion of Bombay",
            "source_line": "Known as the 'Lion of Bombay'.",
            "subject": "Pherozeshah Mehta",
        }
        scores, reasons = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["names_subject"], 5)
        self.assertTrue(is_card_acceptable(scores), msg=f"Unexpected reasons: {reasons}")

        # Failing mutation A: dangling pronoun without naming who it is about
        bad_pronoun = dict(
            good_card,
            clue="By what title was he known?",
            subject="Pherozeshah Mehta",
        )
        s_pro, r_pro = score_card(bad_pronoun, SAMPLE_MUMBAI_SHEET)
        self.assertLessEqual(s_pro["names_subject"], 2)
        self.assertFalse(is_card_acceptable(s_pro))
        self.assertTrue(any("names_subject:" in r for r in r_pro))

        # Failing mutation B: clue leaks the answer
        bad_leak = dict(
            good_card,
            clue="Why was Pherozeshah Mehta called the Lion of Bombay?",
        )
        s_leak, r_leak = score_card(bad_leak, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_leak["names_subject"], 1)
        self.assertFalse(is_card_acceptable(s_leak))
        self.assertTrue(any("leaks the answer" in r for r in r_leak))

    def test_criterion_5_not_furniture_pass_and_fail(self) -> None:
        good_card = {
            "clue": "In which year was Dadabhai Naoroji first elected to the British House of Commons?",
            "answer": "1892",
            "source_line": "First Indian elected to the British House of Commons in 1892.",
            "subject": "Dadabhai Naoroji",
        }
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["not_furniture"], 5)

        # Failing mutation 1: taken from sheet's practice Q&A line
        bad_qa = {
            "clue": "Q1: Who was called the Grand Old Man of India?",
            "answer": "Dadabhai Naoroji",
            "source_line": "Q1: Who was called the Grand Old Man of India? Ans: Dadabhai Naoroji",
        }
        s_qa, r_qa = score_card(bad_qa, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_qa["not_furniture"], 1)
        self.assertFalse(is_card_acceptable(s_qa))
        self.assertTrue(any("not_furniture:" in r for r in r_qa))

        # Failing mutation 2: taken from memory tip
        bad_tip = {
            "clue": "What does the Memory tip: Naoroji = Numbers & Drain of Wealth help recall?",
            "answer": "Dadabhai Naoroji",
            "source_line": "Memory tip: Naoroji = Numbers & Drain of Wealth (Britannica)",
        }
        s_tip, _ = score_card(bad_tip, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_tip["not_furniture"], 1)

        # Failing mutation 3: source credit like "(Britannica)" or card label "FULL CARD"
        for furniture_ans in ("(Britannica)", "FULL CARD"):
            bad_credit = {
                "clue": "Which source is cited at the end of the Dadabhai Naoroji note?",
                "answer": furniture_ans,
                "source_line": "Memory tip: Naoroji = Numbers & Drain of Wealth (Britannica)",
            }
            s_cred, _ = score_card(bad_credit, SAMPLE_MUMBAI_SHEET)
            self.assertEqual(s_cred["not_furniture"], 1)

    def test_criterion_6_not_table_soup_pass_and_fail(self) -> None:
        good_card = {
            "clue": "Which institution is associated with C. D. Deshmukh in 1950?",
            "answer": "Planning Commission",
            "source_line": "C. D. Deshmukh | 1950 | Planning Commission | Finance Minister",
            "subject": "C. D. Deshmukh",
        }
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["not_table_soup"], 5)

        # Failing mutation: answer is a jumbled run of several table cells
        bad_table = dict(
            good_card,
            answer="Dadabhai Naoroji | 1892 | Elphinstone College | Member of Parliament",
        )
        s_tbl, r_tbl = score_card(bad_table, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_tbl["not_table_soup"], 1)
        self.assertFalse(is_card_acceptable(s_tbl))
        self.assertTrue(any("not_table_soup:" in r for r in r_tbl))

    def test_criterion_7_distinct_pass_and_fail(self) -> None:
        card_a = {
            "clue": "From which college in Mumbai did Dadabhai Naoroji graduate?",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        card_b_distinct = {
            "clue": "In which year was Dadabhai Naoroji first elected to the British House of Commons?",
            "answer": "1892",
            "source_line": "First Indian elected to the British House of Commons in 1892.",
            "subject": "Dadabhai Naoroji",
        }
        scores_ok, _ = score_card(card_b_distinct, SAMPLE_MUMBAI_SHEET, prior_cards=[card_a])
        self.assertEqual(scores_ok["distinct"], 5)

        # Failing mutation: near-duplicate of card_a with same answer
        card_b_dup = {
            "clue": "Which college in Mumbai did Dadabhai Naoroji graduate from?",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        scores_dup, r_dup = score_card(card_b_dup, SAMPLE_MUMBAI_SHEET, prior_cards=[card_a])
        self.assertEqual(scores_dup["distinct"], 1)
        self.assertFalse(is_card_acceptable(scores_dup))
        self.assertTrue(any("distinct:" in r for r in r_dup))

    def test_filter_cards_after_plan_preserves_rule_a_with_plain_fallback(self) -> None:
        planned = [
            {
                "clue": "From which college in Mumbai did Dadabhai Naoroji graduate?",
                "answer": "Elphinstone College",
                "source_line": "Graduated from Elphinstone College in Mumbai.",
                "subject": "Dadabhai Naoroji",
            },
            {
                "clue": "Explain Graduated from Elphinstone College and its main features.",
                "answer": "Graduated from Elphinstone College in Mumbai.",
                "source_line": "Authored Poverty and Un-British Rule in India in 1901.",
                "subject": "Dadabhai Naoroji",
            },
        ]
        filtered, dropped = filter_cards_after_plan(planned, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(filtered[1]["card_type"], "plain")
        self.assertEqual(filtered[1]["answer"], "")
        self.assertIn("Authored Poverty and Un-British Rule in India in 1901.", filtered[1]["clue"])
        report_text = format_dropped_cards_report(dropped, sheet_name="mumbai-personalities-flat.pdf")
        self.assertIn("1 card(s) dropped", report_text)

    def test_key_facts_writer_and_deterministic_engine_produce_no_boilerplate_templates(self) -> None:
        # 1. Test plan_key_facts_cards on SAMPLE_MUMBAI_SHEET
        accepted_cards, dropped = plan_key_facts_cards(SAMPLE_MUMBAI_SHEET)
        self.assertEqual(len(dropped), 0, msg=f"Unexpected dropped cards: {dropped}")
        quiz_cards = [c for c in accepted_cards if c.get("answer")]
        self.assertGreaterEqual(len(quiz_cards), 6)
        for card in quiz_cards:
            self.assertNotIn("and its main features", card["clue"])
            self.assertNotIn("FULL CARD", card["clue"])
            self.assertNotIn("Britannica", card["clue"])
            self.assertNotIn("Britannica", card["answer"])
            self.assertNotIn("Memory tip", card["clue"])
            self.assertNotIn("Q1:", card["clue"])
            scores, reasons = score_card(card, SAMPLE_MUMBAI_SHEET)
            self.assertTrue(is_card_acceptable(scores), msg=f"Card failed quality check: {card} -> {reasons}")

        # 2. Verify headings/furniture return None from write_key_fact_card
        for skip_line in (
            "FULL CARD",
            "Indian Industry",
            "Prominent Personalities of Mumbai",
            "Memory tip: Naoroji = Numbers & Drain of Wealth (Britannica)",
            "Q1: Who was called the Grand Old Man of India? Ans: Dadabhai Naoroji",
        ):
            self.assertIsNone(write_key_fact_card(skip_line))

        # 3. Verify generate_questions with provider='deterministic' on SAMPLE_MUMBAI_SHEET
        gen = generate_questions(
            extracted_text=SAMPLE_MUMBAI_SHEET,
            class_level=8,
            subject="History & Civics",
            question_count=5,
            options={"provider": "deterministic"},
        )
        self.assertIn(gen["status"], ("ok", "partial"))
        self.assertGreaterEqual(len(gen["questions"]), 4)
        for q in gen["questions"]:
            self.assertNotIn("and its main features", q["question"])
            self.assertNotIn("FULL CARD", q["question"])
            self.assertNotIn("Britannica", q["question"])
            self.assertNotIn("Britannica", q["answer"])
            self.assertLessEqual(len(q["answer"].split()), 5)

    def test_existing_sample_cards_and_sheets_if_present(self) -> None:
        for folder in (Path("tests/sheets"), Path("cards/sample")):
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.json")):
                self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
