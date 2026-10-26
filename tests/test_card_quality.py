"""Unit tests for learn/teaching_engine/card_quality.py."""

from __future__ import annotations

from pathlib import Path
import unittest

from learn.teaching_engine.card_quality import (
    filter_cards_after_plan,
    format_dropped_cards_report,
    is_card_acceptable,
    score_card,
)

SAMPLE_MUMBAI_SHEET = """
Prominent Personalities of Mumbai

Dadabhai Naoroji (1825–1917)
Known as the 'Grand Old Man of India'.
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
            "clue": "In which year was Dadabhai Naoroji elected to the British House of Commons?",
            "answer": "1892",
            "source_line": "First Indian elected to the British House of Commons in 1892.",
            "subject": "Dadabhai Naoroji",
        }
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["short_answer"], 5)
        self.assertTrue(is_card_acceptable(scores))

        # Failing mutation: long multi-word sentence answer
        bad_card = dict(
            good_card,
            answer="Graduated from Elphinstone College in Mumbai and authored Poverty and Un-British Rule in India.",
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
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["clear_question"], 5)
        self.assertTrue(is_card_acceptable(scores))

        # Failing mutation 1: template slot filled with verb fragment ("Graduated from Elphinstone College")
        bad_verb_slot = {
            "clue": "Explain Graduated from Elphinstone College and its main features.",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        s1, r1 = score_card(bad_verb_slot, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s1["clear_question"], 1)
        self.assertFalse(is_card_acceptable(s1))
        self.assertTrue(any("clear_question:" in r for r in r1))

        # Failing mutation 2: cut-off proper noun ("Man Planning Commission")
        bad_cutoff = {
            "clue": "What reason or cause is explained regarding Man Planning Commission, and what is its result?",
            "answer": "Planning Commission",
            "source_line": "C. D. Deshmukh | 1950 | Planning Commission | Finance Minister",
            "subject": "C. D. Deshmukh",
        }
        s2, r2 = score_card(bad_cutoff, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s2["clear_question"], 1)
        self.assertFalse(is_card_acceptable(s2))
        self.assertTrue(any("clear_question:" in r for r in r2))

    def test_criterion_4_names_subject_pass_and_fail(self) -> None:
        good_card = {
            "clue": "By what title was Pherozeshah Mehta popularly known?",
            "answer": "Lion of Bombay",
            "source_line": "Known as the 'Lion of Bombay'.",
            "subject": "Pherozeshah Mehta",
        }
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["names_subject"], 5)
        self.assertTrue(is_card_acceptable(scores))

        # Failing mutation A: clue leaks the answer
        leaked_card = dict(
            good_card,
            clue="Why was Pherozeshah Mehta called the Lion of Bombay?",
        )
        s_leak, r_leak = score_card(leaked_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_leak["names_subject"], 1)
        self.assertFalse(is_card_acceptable(s_leak))
        self.assertTrue(any("leaks the answer" in r for r in r_leak))

        # Failing mutation B: pronoun-only clue that never names who it is about
        pronoun_card = dict(
            good_card,
            clue="From which college did he graduate?",
            answer="Elphinstone College",
            subject="Dadabhai Naoroji",
        )
        s_pron, r_pron = score_card(pronoun_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_pron["names_subject"], 1)
        self.assertFalse(is_card_acceptable(s_pron))
        self.assertTrue(any("names_subject:" in r for r in r_pron))

    def test_criterion_5_not_furniture_pass_and_fail(self) -> None:
        good_card = {
            "clue": "In which year did Dadabhai Naoroji author Poverty and Un-British Rule in India?",
            "answer": "1901",
            "source_line": "Authored Poverty and Un-British Rule in India in 1901.",
            "subject": "Dadabhai Naoroji",
        }
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["not_furniture"], 5)
        self.assertTrue(is_card_acceptable(scores))

        # Failing mutation A: taken from sheet's practice Q&A line
        qa_card = {
            "clue": "Q1: Who was called the Grand Old Man of India?",
            "answer": "Dadabhai Naoroji",
            "source_line": "Q1: Who was called the Grand Old Man of India? Ans: Dadabhai Naoroji",
        }
        s_qa, r_qa = score_card(qa_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_qa["not_furniture"], 1)
        self.assertFalse(is_card_acceptable(s_qa))
        self.assertTrue(any("not_furniture:" in r for r in r_qa))

        # Failing mutation B: taken from memory tip / "(Britannica)" source credit
        credit_card = {
            "clue": "Which reference source is cited in the memory tip for Dadabhai Naoroji (Britannica)?",
            "answer": "Britannica",
            "source_line": "Memory tip: Naoroji = Numbers & Drain of Wealth (Britannica)",
        }
        s_cred, r_cred = score_card(credit_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_cred["not_furniture"], 1)
        self.assertFalse(is_card_acceptable(s_cred))
        self.assertTrue(any("not_furniture:" in r for r in r_cred))

    def test_criterion_6_not_table_soup_pass_and_fail(self) -> None:
        good_card = {
            "clue": "Which institution was C. D. Deshmukh associated with in 1950?",
            "answer": "Planning Commission",
            "source_line": "C. D. Deshmukh joined the Planning Commission in 1950.",
            "subject": "C. D. Deshmukh",
        }
        scores, _ = score_card(good_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(scores["not_table_soup"], 5)
        self.assertTrue(is_card_acceptable(scores))

        # Failing mutation: answer is a jumbled run of several table cells
        soup_card = {
            "clue": "What details are listed for Dadabhai Naoroji in the summary table?",
            "answer": "1892 | Elphinstone College | Member of Parliament",
            "source_line": "Dadabhai Naoroji | 1892 | Elphinstone College | Member of Parliament",
            "subject": "Dadabhai Naoroji",
        }
        s_soup, r_soup = score_card(soup_card, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s_soup["not_table_soup"], 1)
        self.assertFalse(is_card_acceptable(s_soup))
        self.assertTrue(any("not_table_soup:" in r for r in r_soup))

    def test_criterion_7_distinct_pass_and_fail(self) -> None:
        first_card = {
            "clue": "From which college in Mumbai did Dadabhai Naoroji graduate?",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        second_distinct_card = {
            "clue": "Which committee of the Indian Constitution did Dr. B. R. Ambedkar chair?",
            "answer": "Drafting Committee",
            "source_line": "Chaired the Drafting Committee of the Indian Constitution.",
            "subject": "Dr. B. R. Ambedkar",
        }
        scores_ok, _ = score_card(second_distinct_card, SAMPLE_MUMBAI_SHEET, prior_cards=[first_card])
        self.assertEqual(scores_ok["distinct"], 5)
        self.assertTrue(is_card_acceptable(scores_ok))

        # Failing mutation: near-duplicate of first_card
        near_dup_card = {
            "clue": "Which college in Mumbai did Dadabhai Naoroji graduate from?",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        scores_dup, reasons_dup = score_card(near_dup_card, SAMPLE_MUMBAI_SHEET, prior_cards=[first_card])
        self.assertEqual(scores_dup["distinct"], 1)
        self.assertFalse(is_card_acceptable(scores_dup))
        self.assertTrue(any("distinct:" in r for r in reasons_dup))

    def test_filter_cards_after_plan_preserves_rule_a_with_plain_fallback(self) -> None:
        planned = [
            {
                "card_type": "quiz",
                "clue": "From which college in Mumbai did Dadabhai Naoroji graduate?",
                "answer": "Elphinstone College",
                "source_line": "Graduated from Elphinstone College in Mumbai.",
                "subject": "Dadabhai Naoroji",
            },
            {
                "card_type": "quiz",
                "clue": "Explain Graduated from Elphinstone College and its main features.",
                "answer": "Graduated from Elphinstone College in Mumbai.",
                "source_line": "Authored Poverty and Un-British Rule in India in 1901.",
                "subject": "Dadabhai Naoroji",
            },
        ]
        filtered, dropped = filter_cards_after_plan(planned, SAMPLE_MUMBAI_SHEET)
        # Rule A: total card count is preserved because dropped quiz card falls back to a plain card
        self.assertEqual(len(filtered), 2)
        self.assertEqual(len(dropped), 1)
        self.assertEqual(filtered[0]["card_type"], "quiz")
        self.assertEqual(filtered[1]["card_type"], "plain")
        self.assertEqual(
            filtered[1]["clue"],
            "Authored Poverty and Un-British Rule in India in 1901.",
        )
        report_text = format_dropped_cards_report(dropped, sheet_name="mumbai-personalities-flat.pdf")
        self.assertIn("1 card(s) dropped", report_text)
        self.assertIn("clear_question:", report_text)

    def test_existing_sample_cards_and_sheets_if_present(self) -> None:
        sample_dir = Path("cards/sample")
        sheets_dir = Path("tests/sheets")
        if not sample_dir.exists() and not sheets_dir.exists():
            return
        for p in sorted(sample_dir.glob("*.json")) if sample_dir.exists() else []:
            self.assertTrue(p.is_file())


if __name__ == "__main__":
    unittest.main()
