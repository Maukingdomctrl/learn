"""Unit tests for learn/teaching_engine/card_quality.py and offline Key Facts generation."""

from __future__ import annotations

from pathlib import Path
import unittest

from learn.teaching_engine.card_quality import (
    UNMARKED_SHEET_NOTE,
    clean_lines,
    collect_answer_candidates,
    expand_or_clean_answer_on_line,
    filter_cards_after_plan,
    format_dropped_cards_report,
    is_card_acceptable,
    is_good_answer,
    plan_key_facts_cards,
    score_card,
    write_key_fact_card,
)
from learn.teaching_engine.key_facts_input import clean_lines as clean_lines_input
from question_quality_engine import (
    PDFExtractionEngine,
    QuestionQualityRubric,
    RubricConfig,
    generate_questions,
)

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
    """Test each of the 7 rule-based criteria and all Clear and Complete rules."""

    def setUp(self) -> None:
        self.rubric = QuestionQualityRubric(RubricConfig())
        self.extraction = PDFExtractionEngine().extract_from_text(SAMPLE_MUMBAI_SHEET)

    def _eval_in_rubric(self, question: str, answer: str, evidence: str = "Chaired the Drafting Committee of the Indian Constitution.") -> dict:
        candidate = {
            "question_id": "q_test",
            "question": question,
            "answer": answer,
            "question_type": "recall",
            "difficulty": "easy",
            "learning_point": evidence,
            "source_evidence": evidence,
            "source_page": 1,
        }
        return self.rubric.score_single_question(
            candidate,
            extraction=self.extraction,
            class_level=8,
            subject="History & Civics",
        )

    def test_criterion_1_grounded_pass_and_fail(self) -> None:
        good_card = {
            "clue": "Dadabhai Naoroji graduated from ______ in Mumbai.",
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
            "clue": "Dadabhai Naoroji authored Poverty and Un-British Rule in India in ______.",
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
        # Target style fill-in-the-blank card
        target_sheet = "Dr. B. R. Ambedkar chaired the Drafting Committee of the Constituent Assembly of India."
        target_card = write_key_fact_card(target_sheet)
        self.assertIsNotNone(target_card)
        assert target_card is not None
        self.assertEqual(
            target_card["clue"],
            "Dr. B. R. Ambedkar chaired the ______ of the Constituent Assembly of India.",
        )
        self.assertEqual(target_card["answer"], "Drafting Committee")
        scores, reasons = score_card(target_card, target_sheet)
        self.assertEqual(scores["clear_question"], 5)
        self.assertTrue(is_card_acceptable(scores), msg=f"Unexpected reasons: {reasons}")

        # Failing mutation 1: template slot filled with a verb fragment
        bad_fragment = {
            "clue": "Explain Graduated from Elphinstone College and its main features.",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        s1, r1 = score_card(bad_fragment, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s1["clear_question"], 1)
        self.assertFalse(is_card_acceptable(s1))
        self.assertTrue(any("clear_question:" in r for r in r1))

        # Failing mutation 2: cut-off proper noun ("Man Planning Commission")
        bad_cutoff = {
            "clue": "What reason or cause is explained regarding Man Planning Commission, and what is its result?",
            "answer": "Finance Minister",
            "source_line": "C. D. Deshmukh | 1950 | Planning Commission | Finance Minister",
            "subject": "C. D. Deshmukh",
        }
        s2, r2 = score_card(bad_cutoff, SAMPLE_MUMBAI_SHEET)
        self.assertEqual(s2["clear_question"], 1)
        self.assertFalse(is_card_acceptable(s2))
        self.assertTrue(any("clear_question:" in r for r in r2))

        # Failing mutation 3: generic offline boilerplate ("Explain Indian Industry and its main features." / "Explain FULL CARD and its main features.")
        for bad_template in (
            "Explain Indian Industry and its main features.",
            "Explain FULL CARD and its main features.",
        ):
            s_tpl, r_tpl = score_card(dict(bad_fragment, clue=bad_template), SAMPLE_MUMBAI_SHEET)
            self.assertEqual(s_tpl["clear_question"], 1)
            self.assertFalse(is_card_acceptable(s_tpl))
            self.assertTrue(any("clear_question:" in r for r in r_tpl))

    def test_criterion_4_names_subject_pass_and_fail(self) -> None:
        good_card = {
            "clue": "Pherozeshah Mehta was known as the '______'.",
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
            clue="He was known as the '______'.",
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
            "clue": "Dadabhai Naoroji was the first Indian elected to the British House of Commons in ______.",
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
            "clue": "Dadabhai Naoroji graduated from ______ in Mumbai.",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        card_b_distinct = {
            "clue": "Dadabhai Naoroji was the first Indian elected to the British House of Commons in ______.",
            "answer": "1892",
            "source_line": "First Indian elected to the British House of Commons in 1892.",
            "subject": "Dadabhai Naoroji",
        }
        scores_ok, _ = score_card(card_b_distinct, SAMPLE_MUMBAI_SHEET, prior_cards=[card_a])
        self.assertEqual(scores_ok["distinct"], 5)

        # Failing mutation: near-duplicate of card_a with same answer
        card_b_dup = {
            "clue": "In Mumbai, Dadabhai Naoroji graduated from ______.",
            "answer": "Elphinstone College",
            "source_line": "Graduated from Elphinstone College in Mumbai.",
            "subject": "Dadabhai Naoroji",
        }
        scores_dup, r_dup = score_card(card_b_dup, SAMPLE_MUMBAI_SHEET, prior_cards=[card_a])
        self.assertEqual(scores_dup["distinct"], 1)
        self.assertFalse(is_card_acceptable(scores_dup))
        self.assertTrue(any("distinct:" in r for r in r_dup))

    def test_clear_and_complete_no_headings_inside_question(self) -> None:
        """Reject questions containing headings/section labels ('1. QUICK REVISION NOTES', 'CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN', 'RBS HQ')."""
        for bad_heading_q in (
            "In 1. QUICK REVISION NOTES, Dadabhai Naoroji graduated from ______.",
            "Under CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN, water decomposes into ______.",
            "At RBS HQ, Dadabhai Naoroji authored Poverty and Un-British Rule in India in ______.",
        ):
            card = {
                "clue": bad_heading_q,
                "answer": "Elphinstone College",
                "source_line": "Graduated from Elphinstone College in Mumbai.",
                "subject": "Dadabhai Naoroji",
            }
            scores, reasons = score_card(card, SAMPLE_MUMBAI_SHEET)
            self.assertEqual(scores["clear_question"], 1, msg=f"Expected rejection for {bad_heading_q}")
            self.assertFalse(is_card_acceptable(scores))
            self.assertTrue(any("heading or section label" in r for r in reasons))

            rubric_res = self._eval_in_rubric(bad_heading_q, "Elphinstone College")
            self.assertEqual(rubric_res["review_status"], "rejected")
            self.assertEqual(rubric_res["quality_scores"]["clarity"], 1)

    def test_clear_and_complete_answer_unit_boundaries_and_table_joins(self) -> None:
        """Reject answers ending on of/the/in/and/at, starting with at/the, or joining words from two table cells ('Drafting Committee of the', 'Brahmo Sabha in', 'Mumbai Key Leaders')."""
        sheet_with_table = (
            SAMPLE_MUMBAI_SHEET
            + "\nRaja Ram Mohan Roy founded the Brahmo Sabha in 1828.\nMumbai | Key Leaders\n"
        )
        for bad_ans in (
            "Drafting Committee of the",
            "Brahmo Sabha in",
            "Mumbai Key Leaders",
            "the Drafting Committee",
            "at Elphinstone College",
        ):
            card = {
                "clue": "Dr. B. R. Ambedkar chaired the ______ of the Indian Constitution.",
                "answer": bad_ans,
                "source_line": "Chaired the Drafting Committee of the Indian Constitution.",
                "subject": "Dr. B. R. Ambedkar",
            }
            scores, _ = score_card(card, sheet_with_table)
            self.assertFalse(is_card_acceptable(scores), msg=f"Expected rejection for answer {bad_ans!r}")
            self.assertTrue(
                scores["short_answer"] == 1 or scores["not_table_soup"] == 1,
                msg=f"Expected short_answer=1 or not_table_soup=1 for {bad_ans!r}, got {scores}",
            )

            rubric_res = self._eval_in_rubric(card["clue"], bad_ans)
            self.assertEqual(rubric_res["review_status"], "rejected", msg=f"Rubric should reject {bad_ans!r}")

    def test_clear_and_complete_never_blank_common_words(self) -> None:
        """Reject cards that blank a common word ('If', 'Repeat', 'Make', 'Wear', 'and why', 'law', 'included')."""
        sheet = (
            "If the circuit is closed, repeat the measurement, make a table, wear safety goggles, "
            "explain what happens and why, state Ohm's law, and list the items included in the kit."
        )
        for common_word in ("If", "Repeat", "Make", "Wear", "and why", "law", "included"):
            card = {
                "clue": f"In the laboratory procedure, ______ is required during the circuit experiment.",
                "answer": common_word,
                "source_line": sheet,
                "subject": "Circuit Experiment",
            }
            scores, reasons = score_card(card, sheet)
            self.assertEqual(
                scores["short_answer"],
                1,
                msg=f"Common word {common_word!r} must score 1 on short_answer; got {scores}",
            )
            self.assertFalse(is_card_acceptable(scores))
            self.assertTrue(any("common word" in r for r in reasons))

            rubric_res = self._eval_in_rubric(card["clue"], common_word, evidence=sheet)
            self.assertEqual(rubric_res["review_status"], "rejected")

    def test_clear_and_complete_skip_practice_questions_answer_key_and_q1_ans(self) -> None:
        """Skip everything under 'Practice Questions' / 'Answer Key' headings and any line containing 'Q1.' or '— Ans:'."""
        sheet = """
Dr. B. R. Ambedkar (1891–1956)
• Chaired the **Drafting Committee** of the Constituent Assembly of India.
• Q1. Who chaired the Drafting Committee? — Ans: Dr. B. R. Ambedkar

Practice Questions
• Dr. Rajendra Prasad was elected permanent President of the **Constituent Assembly** in 1946.

Answer Key
• 1. **Constituent Assembly**
""".strip()

        accepted, _ = plan_key_facts_cards(sheet)
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]["answer"], "Drafting Committee")
        self.assertEqual(
            accepted[0]["clue"],
            "Dr. B. R. Ambedkar chaired the ______ of the Constituent Assembly of India.",
        )

        # Direct score_card and rubric checks on "Q1." and "— Ans:" and Practice Questions section lines
        for bad_line in (
            "Q1. Who chaired the Drafting Committee?",
            "Who chaired the Drafting Committee? — Ans: Dr. B. R. Ambedkar",
            "Dr. Rajendra Prasad was elected permanent President of the ______ in 1946.",
        ):
            bad_card = {
                "clue": bad_line,
                "answer": "Constituent Assembly" if "Rajendra" in bad_line else "Dr. B. R. Ambedkar",
                "source_line": (
                    "Dr. Rajendra Prasad was elected permanent President of the **Constituent Assembly** in 1946."
                    if "Rajendra" in bad_line
                    else bad_line
                ),
                "subject": "Dr. B. R. Ambedkar",
            }
            scores, _ = score_card(bad_card, sheet)
            self.assertEqual(scores["not_furniture"], 1, msg=f"Expected not_furniture=1 for {bad_line!r}")
            self.assertFalse(is_card_acceptable(scores))

        for q_str in ("Q1. Who chaired the Drafting Committee?", "Who chaired it? — Ans: Dr. B. R. Ambedkar"):
            rubric_res = self._eval_in_rubric(q_str, "Dr. B. R. Ambedkar")
            self.assertEqual(rubric_res["review_status"], "rejected")

    def test_clear_and_complete_formula_lines_blank_symbol_not_paragraph(self) -> None:
        """Formula lines: blank one symbol or the result ('F = ______' -> 'ma'), never a paragraph answer."""
        formula_sheet = "• F = ma"
        card = write_key_fact_card("• F = ma")
        self.assertIsNotNone(card)
        assert card is not None
        self.assertEqual(card["clue"], "F = ______")
        self.assertEqual(card["answer"], "ma")

        scores, reasons = score_card(card, formula_sheet)
        self.assertTrue(is_card_acceptable(scores), msg=f"Formula card should pass: {scores} {reasons}")

        # Failing mutation: formula card with a paragraph answer
        bad_formula_card = {
            "clue": "F = ______",
            "answer": "ma, where force equals mass multiplied by acceleration in an inertial frame.",
            "source_line": "F = ma, where force equals mass multiplied by acceleration in an inertial frame.",
            "subject": "F",
        }
        bad_scores, bad_reasons = score_card(
            bad_formula_card,
            "F = ma, where force equals mass multiplied by acceleration in an inertial frame.",
        )
        self.assertEqual(bad_scores["short_answer"], 1)
        self.assertEqual(bad_scores["clear_question"], 1)
        self.assertFalse(is_card_acceptable(bad_scores))
        self.assertTrue(any("paragraph answer" in r for r in bad_reasons))

        rubric_res = self._eval_in_rubric(
            "F = ______",
            "ma, where force equals mass multiplied by acceleration in an inertial frame.",
            evidence="F = ma, where force equals mass multiplied by acceleration in an inertial frame.",
        )
        self.assertEqual(rubric_res["review_status"], "rejected")

    def test_key_facts_coverage_and_variety_marked_vs_unmarked_sheets(self) -> None:
        """Verify Key Facts coverage (bold words, bold list, all-bold sentence, bullets/numbered points) and unmarked fallback note."""
        marked_sheet = """
Constituent Assembly of India
Unmarked introductory prose sentence about the framing of the Constitution in New Delhi.
• Dr. B. R. Ambedkar chaired the **Drafting Committee** of the Constituent Assembly of India.
• The nationalist trio consisted of **Lala Lajpat Rai**, **Bal Gangadhar Tilak**, and **Bipin Chandra Pal**.
**Dr. Rajendra Prasad was elected permanent President of the Constituent Assembly in 1946.**
1. The Constitution came into effect on 26 January 1950.
[Image: Photograph of the Constituent Assembly]
Why was the Constitution adopted on 26 November 1949?
Leader | Role | Year
Dr. B. R. Ambedkar | Chairman | 1947
""".strip()

        cards, dropped = plan_key_facts_cards(marked_sheet)
        self.assertEqual(len(dropped), 0, msg=f"Unexpected dropped cards: {dropped}")
        self.assertEqual(len(cards), 4)
        # 1. Single bold word -> answer
        self.assertEqual(
            cards[0]["clue"],
            "Dr. B. R. Ambedkar chaired the ______ of the Constituent Assembly of India.",
        )
        self.assertEqual(cards[0]["answer"], "Drafting Committee")
        # 2. Bold words printed as one list -> one shared card
        self.assertEqual(
            cards[1]["answer"],
            "Lala Lajpat Rai, Bal Gangadhar Tilak, Bipin Chandra Pal",
        )
        self.assertEqual(cards[1]["clue"].count("______"), 3)
        # 3. All-bold sentence -> gets a card
        self.assertIn("______", cards[2]["clue"])
        # 4. Numbered point -> gets a card in reading order
        self.assertEqual(cards[3]["answer"], "26 January 1950")
        for c in cards:
            self.assertNotIn("note", c)

        # Unmarked sheet gets the usual cards with a note
        unmarked_cards, _ = plan_key_facts_cards(SAMPLE_MUMBAI_SHEET)
        self.assertGreaterEqual(len(unmarked_cards), 6)
        for c in unmarked_cards:
            self.assertEqual(c.get("note"), UNMARKED_SHEET_NOTE)

    def test_filter_cards_after_plan_preserves_rule_a_with_plain_fallback(self) -> None:
        planned = [
            {
                "clue": "Dadabhai Naoroji graduated from ______ in Mumbai.",
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
            self.assertIn("______", card["clue"])
            scores, reasons = score_card(card, SAMPLE_MUMBAI_SHEET)
            self.assertTrue(is_card_acceptable(scores), msg=f"Card failed quality check: {card} -> {reasons}")

        # 2. Verify headings/furniture return None from write_key_fact_card
        for skip_line in (
            "FULL CARD",
            "Indian Industry",
            "Prominent Personalities of Mumbai",
            "Memory tip: Naoroji = Numbers & Drain of Wealth (Britannica)",
            "Q1: Who was called the Grand Old Man of India? Ans: Dadabhai Naoroji",
            "Q1. Who was called the Grand Old Man of India? — Ans: Dadabhai Naoroji",
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

    def test_is_good_answer_rejects_common_words(self) -> None:
        """Step 5 Rule 1: is_good_answer REJECTS common words (articles, pronouns, linking words, ordinary verbs/adjectives, generic nouns)."""
        for bad_common in (
            "If",
            "the",
            "and why",
            "Repeat",
            "Make",
            "Wear",
            "included",
            "variable",
            "law",
            "Practice",
            "Evaluation",
            "One",
            "Major",
            "Sustained",
            "Today",
            "Tourism",
            "Georgian-era",
            "Relies",
            "It",
            "Laws",
            "They",
            "Rights",
            "Materials",
            "Heating",
            "Balancing",
        ):
            ok, reason = is_good_answer(bad_common)
            self.assertFalse(ok, msg=f"Expected is_good_answer to reject common word {bad_common!r}")
            self.assertTrue(reason, msg=f"Expected non-empty reason for rejecting {bad_common!r}")

    def test_is_good_answer_rejects_cutoff_phrases(self) -> None:
        """Step 5 Rule 2: is_good_answer REJECTS cut-off phrases (ending on of/the/in/and/at/to/for/with/by, starting with at/the/and/of, or truncating a proper name/date on the line)."""
        line_gokuldas = "The first session was held at Gokuldas Tejpal Sanskrit College in Mumbai."
        for bad_cutoff, src_line in (
            ("Drafting Committee of the", "Dr. B. R. Ambedkar chaired the Drafting Committee of the Constituent Assembly."),
            ("Brahmo Sabha in", "Raja Ram Mohan Roy founded the Brahmo Sabha in 1828."),
            ("at Gokuldas Tejpal Sanskrit", line_gokuldas),
            ("Gokuldas Tejpal Sanskrit", line_gokuldas),
            ("the Constituent Assembly", "Dr. Rajendra Prasad chaired the Constituent Assembly."),
            ("and Weaving Company", "Cowasjee Nanabhoy Davar founded the Bombay Spinning and Weaving Company."),
            ("of India", "Known as the Grand Old Man of India."),
            ("August", "The Quit India resolution was passed on 8 August 1942 in Mumbai."),
            ("UK’s", "London is the UK’s largest metropolis."),
        ):
            ok, reason = is_good_answer(bad_cutoff, source_line=src_line, sheet=src_line)
            self.assertFalse(ok, msg=f"Expected is_good_answer to reject cut-off phrase {bad_cutoff!r}")
            self.assertIn("cut-off", reason.lower())

    def test_is_good_answer_rejects_words_joined_from_two_places(self) -> None:
        """Step 5 Rule 3: is_good_answer REJECTS words from two different places joined together (two table cells, or a cell plus a heading)."""
        table_sheet = (
            "Mumbai | Key Leaders\n"
            "Interpretation | Higher\n"
            "London | Capital\n"
            "Harland and Wolff | Scottish Parliament\n"
        )
        for bad_join in (
            "Mumbai Key Leaders",
            "Interpretation Higher",
            "London Capital",
            "Wolff Scottish Parliament",
        ):
            ok, reason = is_good_answer(bad_join, source_line=table_sheet, sheet=table_sheet)
            self.assertFalse(ok, msg=f"Expected is_good_answer to reject multi-cell join {bad_join!r}")
            self.assertTrue(
                "two" in reason.lower() or "table" in reason.lower() or "heading" in reason.lower(),
                msg=f"Unexpected reason for {bad_join!r}: {reason}",
            )

    def test_is_good_answer_rejects_whole_sentence_or_over_word_limit(self) -> None:
        """Step 5 Rule 4: is_good_answer REJECTS a whole sentence or >4 words (allowing up to 6 only for a proper name that can't be shorter)."""
        for bad_long in (
            "Graduated from Elphinstone College in Mumbai.",
            "separates an insoluble solid from a liquid",
            "has a fixed volume and shape",
            "rate of change of velocity",
        ):
            ok, reason = is_good_answer(bad_long)
            self.assertFalse(ok, msg=f"Expected is_good_answer to reject >4 word / sentence answer {bad_long!r}")
            self.assertTrue(reason)

        # Allow up to 6 words for a proper name that cannot be shorter
        proper_5_words = "Bombay Spinning and Weaving Company"
        line_5_words = "Cowasjee Nanabhoy Davar founded the Bombay Spinning and Weaving Company in 1854."
        ok_prop, reason_prop = is_good_answer(proper_5_words, source_line=line_5_words, sheet=line_5_words)
        self.assertTrue(ok_prop, msg=f"Expected 5-word proper name to pass, got: {reason_prop}")

    def test_is_good_answer_rejects_headings_and_section_labels(self) -> None:
        """Step 5 Rule 5: is_good_answer REJECTS headings, section titles, and category labels."""
        for bad_heading in (
            "Symbols",
            "Algebra",
            "Science notation",
            "Fraction symbols",
            "Speed unit",
            "Temperature",
            "Equation",
            "Historic industries",
            "QUICK REVISION NOTES",
            "Practice Questions",
            "Answer Key",
        ):
            ok, reason = is_good_answer(bad_heading)
            self.assertFalse(ok, msg=f"Expected is_good_answer to reject heading/label {bad_heading!r}")
            self.assertTrue(reason)

    def test_is_good_answer_accepts_all_required_good_answers(self) -> None:
        """Step 5 Passing Cases: verify all 8 required good answers pass is_good_answer."""
        passing_examples = [
            ("Drafting Committee", "Dr. B. R. Ambedkar chaired the Drafting Committee of the Constituent Assembly."),
            ("1873", "Jyotirao Phule founded the Satyashodhak Samaj in 1873."),
            ("8 August 1942", "The Quit India Movement was launched on 8 August 1942 at Gowalia Tank Maidan."),
            ("387 km", "The River Severn has a total length of 387 km."),
            ("Satyashodhak Samaj", "Jyotirao Phule founded the Satyashodhak Samaj in 1873."),
            ("ma", "F = ma"),
            ("Jamsetji Tata", "Jamsetji Tata founded the Tata Iron and Steel Company."),
            ("gas syringe", "The volume of gas evolved was measured using a gas syringe."),
        ]
        for ans, line in passing_examples:
            ok, reason = is_good_answer(ans, source_line=line, sheet=line)
            self.assertTrue(ok, msg=f"Expected {ans!r} to PASS is_good_answer, but got False ({reason})")

    def test_expand_cutoff_candidates_and_preference_order(self) -> None:
        """Step 3 & Step 4: verify cut-off expansion on the same line and 6-tier candidate preference order."""
        self.assertEqual(
            expand_or_clean_answer_on_line(
                "Drafting Committee of the",
                "Dr. B. R. Ambedkar chaired the Drafting Committee of the Constituent Assembly of India.",
            ),
            "Drafting Committee",
        )
        self.assertEqual(
            expand_or_clean_answer_on_line(
                "at Gokuldas Tejpal Sanskrit",
                "The first session was held at Gokuldas Tejpal Sanskrit College in 1885.",
            ),
            "Gokuldas Tejpal Sanskrit College",
        )
        self.assertEqual(
            expand_or_clean_answer_on_line(
                "August",
                "The Quit India Movement began on 8 August 1942 at Gowalia Tank Maidan.",
            ),
            "8 August 1942",
        )

        # Verify preference order: bold > proper_name > date_or_year > number_with_unit > technical_term > formula_part
        line_multi = "• In 1873, **Jyotirao Phule** founded the Satyashodhak Samaj covering 387 km."
        cands = collect_answer_candidates(line_multi)
        tiers = [t for t, _ in cands]
        self.assertEqual(cands[0], ("bold", "Jyotirao Phule"))
        self.assertIn(("proper_name", "Satyashodhak Samaj"), cands)
        self.assertIn(("date_or_year", "1873"), cands)
        self.assertIn(("number_with_unit", "387 km"), cands)
        self.assertLess(tiers.index("bold"), tiers.index("proper_name"))
        self.assertLess(tiers.index("proper_name"), tiers.index("date_or_year"))
        self.assertLess(tiers.index("date_or_year"), tiers.index("number_with_unit"))

    def test_labelled_cards_agreement_zero_bad_accepted_and_at_most_two_good_rejected(self) -> None:
        """Prompt 5 Step 7: Load fixtures/labelled_cards.json and assert 0 bad cards accepted and <= 2 good cards rejected."""
        import json

        labelled_path = Path("fixtures/labelled_cards.json")
        self.assertTrue(labelled_path.exists(), "fixtures/labelled_cards.json must exist")
        labelled_cards = json.loads(labelled_path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(labelled_cards), 60, "fixtures/labelled_cards.json must contain at least 60 cards")

        missed_bad = []
        wrong_rejections = []
        for item in labelled_cards:
            for req_key in ("front", "prompt", "answer", "source_line", "sheet", "label", "reason"):
                self.assertIn(req_key, item)
            res = score_card(item, item["sheet"])
            self.assertIn("scores", res)
            self.assertIn("overall", res)
            self.assertIn("accepted", res)
            self.assertIn("reasons", res)

            if item["label"] == "bad" and res["accepted"]:
                missed_bad.append((item.get("id"), item["front"], item["answer"]))
            elif item["label"] == "good" and not res["accepted"]:
                wrong_rejections.append((item.get("id"), item["front"], item["answer"], res["reasons"]))

        self.assertEqual(
            len(missed_bad),
            0,
            msg=f"Expected 0 bad cards accepted, but checker accepted: {missed_bad}",
        )
        self.assertLessEqual(
            len(wrong_rejections),
            2,
            msg=f"Expected at most 2 good cards rejected, but checker rejected {len(wrong_rejections)}: {wrong_rejections}",
        )

    def test_step_5_unseen_subject_holdout_biology_cards(self) -> None:
        """Prompt 5 Step 5: Verify checker agreement on 10 unseen Class 8 Biology cards (5 good, 5 bad) without subject-specific rules."""
        from scripts.checker_agreement import STEP_5_NEW_BIOLOGY_CARDS, evaluate_card_set

        self.assertEqual(len(STEP_5_NEW_BIOLOGY_CARDS), 10)
        summary = evaluate_card_set(STEP_5_NEW_BIOLOGY_CARDS)
        self.assertEqual(summary["total_good"], 5)
        self.assertEqual(summary["total_bad"], 5)
        self.assertEqual(len(summary["missed_bad"]), 0, msg=f"Missed bad holdout cards: {summary['missed_bad']}")
        self.assertEqual(
            len(summary["wrong_rejections"]),
            0,
            msg=f"Wrongly rejected good holdout cards: {summary['wrong_rejections']}",
        )

    def test_prompt_2_clean_lines_all_6_types_and_inline_britannica(self) -> None:
        """Prompt 2 Step 4: For each type 1-6, verify the non-fact line is removed and a normal fact line next to it is kept; also verify '(Britannica)' is stripped while the sentence stays."""
        self.assertIs(clean_lines, clean_lines_input)

        # Type 1: Headings and section titles (removed, while entity heading context is remembered for the adjacent fact line)
        sheet_type_1 = "\n".join(
            [
                "1. QUICK REVISION NOTES",
                "CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN",
                "1. Savitribai Phule (1831–1897) – Pioneer of Women's Education in Maharashtra",
                "• Opened India's first school for girls at Bhide Wada in Pune in 1848.",
            ]
        )
        kept_1, removed_1 = clean_lines(sheet_type_1)
        self.assertEqual(len(kept_1), 1)
        self.assertEqual(
            kept_1[0]["text"],
            "• Opened India's first school for girls at Bhide Wada in Pune in 1848.",
        )
        self.assertEqual(kept_1[0]["subject"], "Savitribai Phule")
        self.assertEqual(kept_1[0]["nearest_subject_heading"], "Savitribai Phule")
        self.assertEqual([r["type"] for r in removed_1], ["heading", "heading", "heading"])

        # Type 2: Page furniture (page numbers, running headers/footers, "Page 1 …", "FULL CARD", "RBS HQ")
        sheet_type_2 = "\n".join(
            [
                "Worksheet test copy Page 2 of 20",
                "Page 2 — Formula reference",
                "FULL CARD",
                "RBS HQ",
                "Speed = Distance ÷ Time",
            ]
        )
        kept_2, removed_2 = clean_lines(sheet_type_2)
        self.assertEqual(len(kept_2), 1)
        self.assertEqual(kept_2[0]["text"], "Speed = Distance ÷ Time")
        self.assertEqual([r["type"] for r in removed_2], ["page_furniture", "page_furniture", "page_furniture", "page_furniture"])

        # Type 3: Source credits and links (standalone source line removed; inline "(Britannica)", "(History of the INC)", "(HQ in Edinburgh)" removed while sentence stays)
        sheet_type_3 = "\n".join(
            [
                "Sources: Britannica; Bank of England; UNESCO; UK Parliament",
                "• First Indian elected to the British House of Commons in 1892 (Britannica).",
                "• First President: Womesh Chunder Bonnerjee; 72 delegates attended (History of the INC).",
                "• Centre of banking for over 300 years: Bank of Scotland founded in 1695 (HQ in Edinburgh).",
            ]
        )
        kept_3, removed_3 = clean_lines(sheet_type_3)
        self.assertEqual(len(kept_3), 3)
        self.assertEqual(
            kept_3[0]["text"],
            "• First Indian elected to the British House of Commons in 1892.",
        )
        self.assertNotIn("Britannica", kept_3[0]["text"])
        self.assertEqual(kept_3[0]["credits_removed"], ["(Britannica)"])
        self.assertEqual(
            kept_3[1]["text"],
            "• First President: Womesh Chunder Bonnerjee; 72 delegates attended.",
        )
        self.assertNotIn("History of the INC", kept_3[1]["text"])
        self.assertEqual(
            kept_3[2]["text"],
            "• Centre of banking for over 300 years: Bank of Scotland founded in 1695.",
        )
        self.assertNotIn("HQ in Edinburgh", kept_3[2]["text"])
        self.assertTrue(all(r["type"] == "source_credit" for r in removed_3))
        self.assertGreaterEqual(len(removed_3), 4)

        # Type 4: Practice section ("Practice Questions", "Answer Key", "Q1.", "— Ans:")
        sheet_type_4 = "\n".join(
            [
                "1) London — Capital of the UK & England",
                "• Founded by the Romans as Londinium around 43 AD.",
                "2. PRACTICE QUESTIONS & EXERCISES",
                "Q1. Who was known as the 'Grand Old Man of India'? — Ans: Dadabhai Naoroji",
                "3. ANSWER KEY & SELF-EVALUATION RUBRIC",
                "Ans: 1885",
            ]
        )
        kept_4, removed_4 = clean_lines(sheet_type_4)
        self.assertEqual(len(kept_4), 1)
        self.assertEqual(kept_4[0]["text"], "• Founded by the Romans as Londinium around 43 AD.")
        self.assertEqual(kept_4[0]["subject"], "London")
        practice_removed = [r for r in removed_4 if r["type"] == "practice_section"]
        self.assertEqual(len(practice_removed), 4)

        # Type 5: Memory tips and study tips ("Memory Tip", "Study Tip", "Remember", "Tip:")
        sheet_type_5 = "\n".join(
            [
                "2. Dadabhai Naoroji (1825–1917)",
                "• Authored Poverty and Un-British Rule in India (1901).",
                "Memory Tip: Naoroji = Numbers & Drain of Wealth.",
                "Study Tip: Revise dates in chronological order.",
                "Remember: Always write units with numerical answers.",
                "Tip: Check conservation of atoms on both sides.",
            ]
        )
        kept_5, removed_5 = clean_lines(sheet_type_5)
        self.assertEqual(len(kept_5), 1)
        self.assertEqual(kept_5[0]["text"], "• Authored Poverty and Un-British Rule in India (1901).")
        self.assertEqual(kept_5[0]["subject"], "Dadabhai Naoroji")
        memory_removed = [r for r in removed_5 if r["type"] == "memory_tip"]
        self.assertEqual(len(memory_removed), 4)

        # Type 6: Tables (table section heading and pipe/multi-column table rows removed; normal fact line kept)
        sheet_type_6 = "\n".join(
            [
                "• Law of Conservation of Mass: matter is neither created nor destroyed (Antoine Lavoisier).",
                "4. QUICK COMPARISON TABLE",
                "City | Country | Key River | Notable Institution",
                "London | England | River Thames | UK Parliament at Westminster",
                "Edinburgh   Scotland   Firth of Forth   Scottish Parliament",
            ]
        )
        kept_6, removed_6 = clean_lines(sheet_type_6)
        self.assertEqual(len(kept_6), 1)
        self.assertEqual(
            kept_6[0]["text"],
            "• Law of Conservation of Mass: matter is neither created nor destroyed (Antoine Lavoisier).",
        )
        table_removed = [r for r in removed_6 if r["type"] == "table"]
        self.assertEqual(len(table_removed), 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)

