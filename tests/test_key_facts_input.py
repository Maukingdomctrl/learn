"""Unit tests for `clean_sheet(pdf)` in `learn/teaching_engine/key_facts_input.py` (Prompt 2 Detailed — Step 5)."""

from __future__ import annotations

import unittest

from learn.teaching_engine.card_quality import plan_key_facts_cards, write_key_fact_card
from learn.teaching_engine.key_facts_input import clean_lines, clean_sheet


class TestKeyFactsInputCleaner(unittest.TestCase):
    """Tests for `clean_sheet(pdf)` covering all 7 removal categories and text-rejoining rules."""

    def test_type_1_heading_removed_and_adjacent_fact_kept_with_subject_and_section(self) -> None:
        """Type 1 ('heading'): section headings, numbered titles, ALL-CAPS lines, and '•'-joined banners are removed with reason='heading', while setting subject & section for the adjacent fact line."""
        sheet = "\n".join(
            [
                "IMPORTANT CITIES OF THE UNITED KINGDOM",
                "CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN",
                "1. QUICK REVISION NOTES",
                "1. LONDON – Capital of the United Kingdom & England",
                "• Situated on the River Thames in southeastern England.",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 1)
        fact = out["facts"][0]
        self.assertEqual(fact["text"], "• Situated on the River Thames in southeastern England.")
        self.assertEqual(fact["subject"], "London")
        self.assertEqual(fact["section"], "Quick Revision Notes")
        self.assertEqual(fact["kind"], "bullet")
        self.assertEqual([r["reason"] for r in out["removed"]], ["heading", "heading", "heading", "heading"])

    def test_type_2_furniture_removed_and_adjacent_fact_kept(self) -> None:
        """Type 2 ('furniture'): running headers/footers across pages, 'Page 2 — ...', 'FULL CARD', 'RBS HQ', and blank fill lines are removed with reason='furniture', while the adjacent fact is kept."""
        sheet = {
            "pages": [
                {
                    "page_number": 1,
                    "text": "\n".join(
                        [
                            "Grade 8 Social Studies | Country - United Kingdom Page 1",
                            "Worksheet test copy Page 1 of 20",
                            "Student: ____________________ Date: ____________________",
                            "FULL CARD",
                            "RBS HQ",
                            "Speed = Distance ÷ Time",
                        ]
                    ),
                },
                {
                    "page_number": 2,
                    "text": "\n".join(
                        [
                            "Grade 8 Social Studies | Country - United Kingdom Page 2",
                            "Page 2 — Formula reference",
                            "A = l × b",
                        ]
                    ),
                },
            ]
        }
        out = clean_sheet(sheet)
        self.assertEqual([f["text"] for f in out["facts"]], ["Speed = Distance ÷ Time", "A = l × b"])
        self.assertEqual([f["kind"] for f in out["facts"]], ["formula", "formula"])
        self.assertTrue(all(r["reason"] == "furniture" for r in out["removed"]))
        self.assertEqual(len(out["removed"]), 7)

    def test_type_3_credit_and_link_removed_and_inline_britannica_stripped(self) -> None:
        """Type 3 ('credit' and 'link'): source lines and inline '(Britannica)' get reason='credit', URLs get reason='link', and the sentence itself is kept without '(Britannica)'."""
        sheet = "\n".join(
            [
                "Sources: Britannica; Bank of England; UNESCO; History of the INC",
                "https://www.britannica.com/place/London",
                "www.parliament.uk/about/living-heritage/",
                "• First Indian elected to the British House of Commons in 1892 (Britannica).",
                "• Centre of banking for over 300 years: Bank of Scotland founded in 1695 (HQ in Edinburgh).",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 2)
        self.assertEqual(
            out["facts"][0]["text"],
            "• First Indian elected to the British House of Commons in 1892.",
        )
        self.assertNotIn("Britannica", out["facts"][0]["text"])
        self.assertEqual(
            out["facts"][1]["text"],
            "• Centre of banking for over 300 years: Bank of Scotland founded in 1695.",
        )
        self.assertNotIn("HQ in Edinburgh", out["facts"][1]["text"])

        reasons = [r["reason"] for r in out["removed"]]
        self.assertIn("credit", reasons)
        self.assertIn("link", reasons)
        link_items = [r for r in out["removed"] if r["reason"] == "link"]
        self.assertEqual(len(link_items), 2)
        credit_items = [r for r in out["removed"] if r["reason"] == "credit"]
        self.assertGreaterEqual(len(credit_items), 3)
        self.assertTrue(any(r["text"] == "(Britannica)" for r in credit_items))

    def test_type_4_practice_section_removed_and_adjacent_fact_kept(self) -> None:
        """Type 4 ('practice'): everything under 'Practice Questions' / 'Answer Key' / 'Check Your Understanding' and any 'Q1.' or '— Ans:' line is removed with reason='practice', while the adjacent fact line is kept."""
        sheet = "\n".join(
            [
                "4. EDINBURGH – Capital of Scotland",
                "• Home to the Scottish Parliament and the seat of the monarchy in Scotland.",
                "3. PRACTICE QUESTIONS",
                "Q1. Which city is home to the Scottish Parliament? — Ans: Edinburgh",
                "1. Explain why Edinburgh is an important financial centre.",
                "4. ANSWER KEY",
                "1. Edinburgh is the second largest financial centre in the UK after London.",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 1)
        self.assertEqual(
            out["facts"][0]["text"],
            "• Home to the Scottish Parliament and the seat of the monarchy in Scotland.",
        )
        self.assertEqual(out["facts"][0]["subject"], "Edinburgh")
        practice_removed = [r for r in out["removed"] if r["reason"] == "practice"]
        self.assertEqual(len(practice_removed), 5)

    def test_type_5_memory_and_study_tips_removed_and_adjacent_fact_kept(self) -> None:
        """Type 5 ('tip'): 'MEMORY TIP:', 'Study Tip for Grade 8:', 'Remember:', and 'Study prompt:' lines are removed with reason='tip', while the adjacent fact line is kept."""
        sheet = "\n".join(
            [
                "5. CARDIFF – Capital of Wales",
                "• Home to the Wales Millennium Centre – a thriving creative capital with rich cultural heritage.",
                "MEMORY TIP: Remember the order – London → Birmingham → Belfast → Edinburgh → Cardiff.",
                "Study Tip for Grade 8: Make a simple mind-map with the 5 cities in a circle.",
                "Study prompt: Choose one institution named above and explain its role.",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 1)
        self.assertEqual(
            out["facts"][0]["text"],
            "• Home to the Wales Millennium Centre – a thriving creative capital with rich cultural heritage.",
        )
        tip_removed = [r for r in out["removed"] if r["reason"] == "tip"]
        self.assertEqual(len(tip_removed), 3)

    def test_type_6_tables_kept_structured_and_never_in_facts_or_joined_cells(self) -> None:
        """Type 6 ('table'): tables are removed from 'facts' with reason='table', stored structured in 'tables' ({page, header, rows}), and never produce joined cell text."""
        sheet = "\n".join(
            [
                "3. BELFAST – Capital of Northern Ireland",
                "• Harland and Wolff shipyard built the RMS Titanic – once the world’s biggest and most productive shipyard.",
                "2. COMPARATIVE TABLE – EASY TO REMEMBER",
                "Feature | London | Birmingham | Belfast | Edinburgh | Cardiff",
                "Status | Capital of UK & England | Largest city outside London | Capital of N. Ireland | Capital of Scotland | Capital of Wales",
                "Famous Landmark / Fact | Financial centre of Europe | Birmingham Hippodrome | Titanic Belfast Museum; Harland & Wolff | Scottish Parliament; RBS HQ | Wales Millennium Centre",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 1)
        self.assertNotIn("|", out["facts"][0]["text"])
        table_removed = [r for r in out["removed"] if r["reason"] == "table"]
        self.assertEqual(len(table_removed), 4)
        self.assertEqual(len(out["tables"]), 1)
        tbl = out["tables"][0]
        self.assertEqual(tbl["page"], 1)
        self.assertEqual(tbl["header"], ["Feature", "London", "Birmingham", "Belfast", "Edinburgh", "Cardiff"])
        self.assertEqual(len(tbl["rows"]), 2)

        cards, _ = plan_key_facts_cards(sheet)
        self.assertEqual(len(cards), 1)
        self.assertNotIn("|", cards[0]["front"])
        self.assertNotIn("Wolff Scottish Parliament", cards[0]["answer"])

    def test_type_7_figure_labels_and_captions_removed_and_adjacent_fact_kept(self) -> None:
        """Type 7 ('figure'): diagram callout labels ('Cell / battery', 'Bulb', 'Current direction →', 'Schematic (not to scale)') and 'Figure 1:' captions are removed with reason='figure', while adjacent facts are kept."""
        sheet = "\n".join(
            [
                "Force: a push or pull on an object.",
                "Figure 1: Simple electric circuit showing current flow",
                "Cell / battery",
                "Bulb",
                "Connecting wire",
                "Closed path",
                "Current direction →",
                "Schematic (not to scale)",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 1)
        self.assertEqual(out["facts"][0]["text"], "Force: a push or pull on an object.")
        fig_removed = [r for r in out["removed"] if r["reason"] == "figure"]
        self.assertEqual(len(fig_removed), 7)

    def test_wrapped_sentence_and_hyphenated_break_rejoined(self) -> None:
        """A wrapped sentence across two PDF lines comes out as one line, and a hyphenated break ('Consti-\\ntution') is rejoined."""
        sheet = {
            "pages": [
                {
                    "page_number": 1,
                    "text": "\n".join(
                        [
                            "India's Consti-",
                            "tution was adopted by the Constituent Assembly on",
                            "26 November 1949.",
                        ]
                    ),
                }
            ]
        }
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 1)
        self.assertEqual(
            out["facts"][0]["text"],
            "India's Constitution was adopted by the Constituent Assembly on 26 November 1949.",
        )

    def test_name_with_dates_and_title_sets_subject_and_is_kept_as_fact(self) -> None:
        """A 'Name (dates) – Title' line sets `subject` AND is kept in `facts` so it can produce a card."""
        sheet = "\n".join(
            [
                "1. Savitribai Phule (1831–1897) – Pioneer of Women's Education in Maharashtra",
                "• Opened India's first school for girls at Bhide Wada in Pune in 1848.",
            ]
        )
        out = clean_sheet(sheet)
        self.assertEqual(len(out["facts"]), 2)
        self.assertEqual(
            out["facts"][0]["text"],
            "1. Savitribai Phule (1831–1897) – Pioneer of Women's Education in Maharashtra",
        )
        self.assertEqual(out["facts"][0]["subject"], "Savitribai Phule")
        self.assertEqual(
            out["facts"][1]["text"],
            "• Opened India's first school for girls at Bhide Wada in Pune in 1848.",
        )
        self.assertEqual(out["facts"][1]["subject"], "Savitribai Phule")

        card_0 = write_key_fact_card(out["facts"][0]["text"], subject=out["facts"][0]["subject"])
        self.assertIsNotNone(card_0)
        assert card_0 is not None
        self.assertEqual(card_0["answer"], "Savitribai Phule")
        self.assertEqual(
            card_0["front"],
            "______ (1831–1897) – Pioneer of Women's Education in Maharashtra.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
