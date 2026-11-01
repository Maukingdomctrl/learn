"""Pytest-style tests for Key Facts card fixes (B1-B6) and Learn live fit (C1-C5)."""
from __future__ import annotations

import json
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learn.teaching_engine.key_facts import (
    KeyFactCard,
    __version__,
    plan_key_facts,
    plan_key_facts_with_notes,
    validate,
)

ALLOWED_KINDS = {"gap", "question", "term", "name", "equation", "row", "compare"}


@dataclass
class _Item:
    """Plain reader Item object (not a dict) matching Learn's reader attributes."""

    kind: str
    text: str
    page: int = 1
    unit_ids: tuple[str, ...] = ()
    marker: str | None = None
    section: str | None = None
    group: str | None = None
    topic: str | None = None
    context: str | None = None
    answer: str | None = None
    options: tuple[str, ...] | None = None
    table: object | None = None
    top: float | None = None
    bottom: float | None = None
    bullet: str | bool | None = None
    bold: tuple[str, ...] = ()


def test_package_version() -> None:
    """Verify __version__ is 0.6.0."""
    assert __version__ == "0.6.0"


# ---------------------------------------------------------------------------
# B. CARD FIXES (B1-B6: one passing + one failing made-up test each)
# ---------------------------------------------------------------------------


def test_b1_trimmed_clue_no_dangling_ending_pass_and_fail() -> None:
    """B1: Trimmed clues must not end on a dangling word ('...siphoned off.', '...and founder of.')."""
    # PASS: Long sentence with a purpose/trailing clause trims cleanly at the clause boundary
    items = [
        _Item(
            kind="point",
            text=(
                "Dadabhai Naoroji developed the Drain of Wealth theory in Poverty and "
                "Un-British Rule in India to show how India's wealth was siphoned off to Britain."
            ),
            page=1,
            unit_ids=("U1",),
            topic="Dadabhai Naoroji",
            bullet="•",
            bold=("Drain of Wealth",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) >= 1
    for c in cards:
        assert not c.clue.endswith("siphoned off.")
        assert not c.clue.endswith("founder of.")
        assert len(c.clue.split()) <= 20

    # FAIL: Candidate card whose clue ends on a dangling phrase ('...siphoned off.' or '...and founder of.') is rejected
    item_dict = {
        "id": "B1",
        "kind": "point",
        "text": items[0].text,
        "topic": "Dadabhai Naoroji",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    dangling_card = {
        "id": "C_B1",
        "fact_id": "F_B1",
        "item_id": "B1",
        "page": 1,
        "label": "Dadabhai Naoroji",
        "subject": "Dadabhai Naoroji",
        "front": (
            "Dadabhai Naoroji developed the ______ theory to show how India's wealth was siphoned off."
        ),
        "prompt": "Which name fits the gap?",
        "answer": "Drain of Wealth",
        "question_type": "GAP",
        "source_text": items[0].text,
    }
    reasons = validate.validate_card(dangling_card, {"B1": item_dict}, vocab, set())
    assert "dangling_clue_ending" in reasons


def test_b2_list_answer_single_item_pass_and_fail() -> None:
    """B2: A list answer must be ONE item ('Revived public ______ festivals' -> one item)."""
    # PASS: 'Revived public Ganesh Chaturthi and Shivaji festivals' blanks ONE item ('Ganesh Chaturthi')
    items = [
        _Item(
            kind="point",
            text="Revived public Ganesh Chaturthi and Shivaji festivals to unite the people.",
            page=1,
            unit_ids=("U1",),
            topic="Bal Gangadhar Tilak",
            bullet="•",
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) == 1
    assert cards[0].answer == "Ganesh Chaturthi"
    assert "and Shivaji" not in cards[0].answer

    # FAIL: Candidate card answering 'Ganesh Chaturthi and Shivaji' is rejected by validate_card
    item_dict = {
        "id": "B2",
        "kind": "point",
        "text": items[0].text,
        "topic": "Bal Gangadhar Tilak",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    multi_item_card = {
        "id": "C_B2",
        "fact_id": "F_B2",
        "item_id": "B2",
        "page": 1,
        "label": "Bal Gangadhar Tilak",
        "subject": "Bal Gangadhar Tilak",
        "front": "Revived public ______ festivals to unite the people.",
        "prompt": "Which name fits the gap?",
        "answer": "Ganesh Chaturthi and Shivaji",
        "question_type": "GAP",
        "source_text": items[0].text,
    }
    reasons = validate.validate_card(multi_item_card, {"B2": item_dict}, vocab, set())
    assert "list_answer_multiple_items" in reasons


def test_b3_same_answer_at_most_twice_in_different_directions_pass_and_fail() -> None:
    """B3: Don't ask the same answer more than twice per sheet; keep the 2 best, in different directions."""
    # PASS: 4 items with answer 'CO2' produce at most 2 'CO2' cards, in different directions
    items = [
        _Item(
            kind="point",
            text="Aerobic respiration releases CO2 into the atmosphere.",
            page=1,
            unit_ids=("U1",),
            topic="Respiration",
            bullet="•",
            bold=("CO2",),
        ),
        _Item(
            kind="point",
            text="Complete combustion of carbon fuels produces CO2.",
            page=1,
            unit_ids=("U2",),
            topic="Combustion",
            bullet="•",
            bold=("CO2",),
        ),
        _Item(
            kind="point",
            text="Green plants absorb CO2 through leaf pores during photosynthesis.",
            page=1,
            unit_ids=("U3",),
            topic="Photosynthesis",
            bullet="•",
            bold=("CO2",),
        ),
        _Item(
            kind="point",
            text="Thermal decomposition of calcium carbonate releases CO2.",
            page=1,
            unit_ids=("U4",),
            topic="Decomposition",
            bullet="•",
            bold=("CO2",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    co2_cards = [c for c in cards if c.answer == "CO2"]
    # FAIL check: never 3 or 4 cards with the same answer
    assert len(co2_cards) <= 2
    assert len(co2_cards) == 2
    # Kept 2 cards must be in different directions (one question card and one gap card)
    kinds = {c.kind for c in co2_cards}
    assert "gap" in kinds
    assert "question" in kinds


def test_b4_every_prompt_ends_with_question_mark_pass_and_fail() -> None:
    """B4: Every prompt ends with '?' ('Which substance fits the gap?')."""
    # PASS: Every generated card question / prompt ends with '?' (or 'Answer it.' for question cards)
    items = [
        _Item(
            kind="point",
            text="Plants take in carbon dioxide (CO2) through tiny pores.",
            page=1,
            unit_ids=("U1",),
            topic="Photosynthesis",
            bullet="•",
            bold=("carbon dioxide (CO2)",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) == 1
    assert cards[0].question == "Which substance fits the gap?"
    assert cards[0].question.endswith("?")

    # FAIL: Candidate card whose prompt does not end with '?' is rejected by validate_card
    item_dict = {
        "id": "B4",
        "kind": "point",
        "text": items[0].text,
        "topic": "Photosynthesis",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    bad_prompt_card = {
        "id": "C_B4",
        "fact_id": "F_B4",
        "item_id": "B4",
        "page": 1,
        "label": "Photosynthesis",
        "subject": "Photosynthesis",
        "front": "Plants take in ______ through tiny pores.",
        "prompt": "Which substance fits the gap",
        "answer": "carbon dioxide (CO2)",
        "question_type": "GAP",
        "source_text": items[0].text,
    }
    reasons = validate.validate_card(bad_prompt_card, {"B4": item_dict}, vocab, set())
    assert "prompt_missing_question_mark" in reasons


def test_b5_institutions_are_not_places_pass_and_fail() -> None:
    """B5: Institutions/colleges/organisations are not places:
    'Educated at ______, Mumbai' -> 'Which name fits the gap?'.
    """
    # PASS: 'Educated at Elphinstone Institution, Mumbai' uses 'Which name fits the gap?'
    items = [
        _Item(
            kind="point",
            text="Educated at Elphinstone Institution, Mumbai.",
            page=1,
            unit_ids=("U1",),
            topic="Dadabhai Naoroji",
            bullet="•",
            bold=("Elphinstone Institution",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) == 1
    assert cards[0].answer == "Elphinstone Institution"
    assert cards[0].question == "Which name fits the gap?"

    # FAIL: Candidate card asking 'Which place fits the gap?' for 'Elphinstone Institution' is rejected
    item_dict = {
        "id": "B5",
        "kind": "point",
        "text": items[0].text,
        "topic": "Dadabhai Naoroji",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    bad_inst_card = {
        "id": "C_B5",
        "fact_id": "F_B5",
        "item_id": "B5",
        "page": 1,
        "label": "Dadabhai Naoroji",
        "subject": "Dadabhai Naoroji",
        "front": "Educated at ______, Mumbai.",
        "prompt": "Which place fits the gap?",
        "answer": "Elphinstone Institution",
        "question_type": "GAP",
        "source_text": items[0].text,
    }
    reasons = validate.validate_card(bad_inst_card, {"B5": item_dict}, vocab, set())
    assert "institution_with_place_prompt" in reasons


def test_b6_answers_must_be_key_fact_not_phrase_pass_and_fail() -> None:
    """B6: Answers must be a key fact, not a phrase like 'Less CO2' or 'both gases are produced'."""
    # PASS: 'Less CO2 is released during clean combustion' extracts 'CO2', and 'both gases are produced' is skipped
    items = [
        _Item(
            kind="point",
            text="Less CO2 is released during clean fuel combustion.",
            page=1,
            unit_ids=("U1",),
            topic="Clean Fuel",
            bullet="•",
            bold=("Less CO2",),
        ),
        _Item(
            kind="point",
            text="In this reaction, both gases are produced.",
            page=1,
            unit_ids=("U2",),
            topic="Clean Fuel",
            bullet="•",
            bold=("both gases are produced",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) == 1
    assert cards[0].answer == "CO2"
    assert all(c.answer not in ("Less CO2", "both gases are produced") for c in cards)

    # FAIL: Candidate cards with answers 'Less CO2' or 'both gases are produced' are rejected
    item_dict = {
        "id": "B6",
        "kind": "point",
        "text": "Less CO2 is released and both gases are produced.",
        "topic": "Clean Fuel",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    for bad_ans in ("Less CO2", "both gases are produced"):
        bad_card = {
            "id": "C_B6",
            "fact_id": "F_B6",
            "item_id": "B6",
            "page": 1,
            "label": "Clean Fuel",
            "subject": "Clean Fuel",
            "front": "In Clean Fuel, ______ is noted.",
            "prompt": "Which substance fits the gap?",
            "answer": bad_ans,
            "question_type": "GAP",
            "source_text": item_dict["text"],
        }
        reasons = validate.validate_card(bad_card, {"B6": item_dict}, vocab, set())
        assert "non_key_fact_phrase" in reasons


# ---------------------------------------------------------------------------
# C. FIT WITH LEARN'S LIVE KEY FACTS (C1-C5: one passing + one failing case each)
# ---------------------------------------------------------------------------


def test_c1_check_first_notes_pass_and_fail() -> None:
    """C1: Fill KeyFactCard.checks (at most 1 note) for trigger words; no note for ordinals."""
    items = [
        # Passing trigger case with multiple trigger words ('largest' and 'most populous') -> at most ONE note
        _Item(
            kind="point",
            text="Largest and most populous UK city outside London.",
            page=1,
            unit_ids=("U1",),
            topic="Birmingham",
            bullet="•",
        ),
        # Failing trigger case: ordinal superlatives ('eleventh-largest', 'seventh most populous') -> NO note
        _Item(
            kind="point",
            text="The seventh most populous in the United Kingdom.",
            page=1,
            unit_ids=("U2",),
            topic="Edinburgh",
            bullet="•",
        ),
        _Item(
            kind="point",
            text="The eleventh-largest city in the United Kingdom.",
            page=1,
            unit_ids=("U3",),
            topic="Cardiff",
            bullet="•",
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    birm = [c for c in cards if c.about == "Birmingham"]
    assert len(birm) == 1
    assert len(birm[0].checks) == 1
    assert birm[0].checks == (
        "Check first: the sheet says “largest”. Confirm it in the textbook before learning it.",
    )

    edin = [c for c in cards if c.about == "Edinburgh"]
    assert len(edin) == 1
    assert edin[0].checks == ()

    cardiff = [c for c in cards if c.about == "Cardiff"]
    assert len(cardiff) == 1
    assert cardiff[0].checks == ()


def test_c2_parent_notes_with_and_without_formatting() -> None:
    """C2: plan_key_facts_with_notes returns the parent note when nothing is bold, bullet, or numbered."""
    # Case 1 (Trigger): Nothing on the sheet is bold, bullet, or numbered point -> returns parent note
    plain_items = [
        _Item(
            kind="point",
            text="Founded the Satyashodhak Samaj in 1873.",
            page=1,
            unit_ids=("U1",),
            topic="Jyotirao Phule",
            bullet=None,
            marker=None,
            bold=(),
        ),
    ]
    cards_plain, notes_plain = plan_key_facts_with_notes(plain_items, standard=8)
    assert len(cards_plain) >= 1
    assert notes_plain == (
        "Nothing on these pages is printed in bold or as a bullet or numbered point, "
        "so Key Facts made study cards from every line instead.",
    )
    # plan_key_facts keeps returning only list[KeyFactCard]
    only_cards = plan_key_facts(plain_items, standard=8)
    assert isinstance(only_cards, list)
    assert only_cards == cards_plain

    # Case 2 (Non-trigger): Sheet has bold or bullet formatting -> notes tuple is empty ()
    formatted_items = [
        _Item(
            kind="point",
            text="Founded the Satyashodhak Samaj in 1873.",
            page=1,
            unit_ids=("U1",),
            topic="Jyotirao Phule",
            bullet="•",
            bold=("Satyashodhak Samaj",),
        ),
    ]
    cards_fmt, notes_fmt = plan_key_facts_with_notes(formatted_items, standard=8)
    assert len(cards_fmt) >= 1
    assert notes_fmt == ()


def test_c3_standard_setting_valid_and_invalid() -> None:
    """C3: plan_key_facts accepts 7, 8, or 9 (with 16/20/24 word limits) and raises ValueError otherwise."""
    long_item = [
        _Item(
            kind="point",
            text=(
                "During the nineteenth century industrial transformation across western India, "
                "cowasjee Nanabhoy Davar established the first steam cotton spinning mill at Tardeo in Bombay."
            ),
            page=1,
            unit_ids=("U1",),
            topic="Cotton Mills",
            bullet="•",
            bold=("Tardeo",),
        ),
    ]
    cards_7 = plan_key_facts(long_item, standard=7)
    cards_8 = plan_key_facts(long_item, standard=8)
    cards_9 = plan_key_facts(long_item, standard=9)
    assert len(cards_7) == 1 and len(cards_7[0].clue.split()) <= 16
    assert len(cards_8) == 1 and len(cards_8[0].clue.split()) <= 20
    assert len(cards_9) == 1 and len(cards_9[0].clue.split()) <= 24
    assert len(cards_9[0].clue.split()) > len(cards_7[0].clue.split())

    # Failing cases: any standard other than 7, 8, or 9 raises ValueError("Choose ICSE Standard 7, 8, or 9.")
    for bad_std in (6, 10, 0, True, "8"):
        raised = False
        try:
            plan_key_facts(long_item, standard=bad_std)  # type: ignore[arg-type]
        except ValueError as exc:
            raised = True
            assert str(exc) == "Choose ICSE Standard 7, 8, or 9."
        assert raised


def test_c4_stable_sheet_order_and_determinism() -> None:
    """C4: Cards are in sheet order, and running plan_key_facts twice gives the exact same list."""
    items = [
        _Item(
            kind="point",
            text="Founded the Satyashodhak Samaj in 1873.",
            page=1,
            unit_ids=("U1",),
            topic="Jyotirao Phule",
            bullet="•",
        ),
        _Item(
            kind="point",
            text="Chaired the Drafting Committee of the Constituent Assembly.",
            page=2,
            unit_ids=("U2",),
            topic="Dr. Bhimrao Ramji Ambedkar",
            bullet="•",
        ),
        _Item(
            kind="point",
            text="Founded the Servants of India Society in 1905.",
            page=3,
            unit_ids=("U3",),
            topic="Gopal Krishna Gokhale",
            bullet="•",
        ),
    ]
    first_run = plan_key_facts(items, standard=8)
    second_run = plan_key_facts(items, standard=8)
    assert first_run == second_run
    pages = [c.page for c in first_run]
    assert pages == sorted(pages)
    # Negative check: reversed input order produces a different page order
    reversed_run = plan_key_facts(list(reversed(items)), standard=8)
    assert [c.unit_ids for c in first_run] != [c.unit_ids for c in reversed_run]


def test_c5_card_kinds_and_question_field_pass_and_fail() -> None:
    """C5: Card kinds use only Learn's 7 values; question cards have question='Answer it.' and clue=question."""
    items = [
        # Produces a question card ('Which organisation did Jyotirao Phule found?') and a gap/year card
        _Item(
            kind="point",
            text="Founded the Satyashodhak Samaj in 1873.",
            page=1,
            unit_ids=("U1",),
            topic="Jyotirao Phule",
            bullet="•",
        ),
        # Produces a gap card
        _Item(
            kind="point",
            text="Co-launched the Home Rule Movement in 1916.",
            page=1,
            unit_ids=("U2",),
            topic="Bal Gangadhar Tilak",
            bullet="•",
            bold=("Home Rule Movement",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) >= 2
    question_cards = [c for c in cards if "______" not in c.clue]
    gap_cards = [c for c in cards if "______" in c.clue]
    assert len(question_cards) >= 1
    assert len(gap_cards) >= 1

    for qc in question_cards:
        assert isinstance(qc, KeyFactCard)
        assert qc.kind in ALLOWED_KINDS
        assert qc.kind != "gap"
        assert qc.question == "Answer it."
        assert qc.clue.endswith("?")

    for gc in gap_cards:
        assert isinstance(gc, KeyFactCard)
        assert gc.kind in ALLOWED_KINDS
        assert gc.question != "Answer it."
        assert gc.question.endswith("?")


# ---------------------------------------------------------------------------
# V8 POLISH FIXES (1-4: one passing + one failing test each)
# ---------------------------------------------------------------------------


def test_v8_fix1_parent_note_ignores_headings_titles_tables_pass_and_fail() -> None:
    """Fix 1: Parent note shown when no point/summary is bold, bulleted, or numbered
    (headings, titles, section numbers, and table cells do not count).
    """
    # PASS (Note shown): Sheet has numbered/bold headings, titles, and table cells,
    # but every point/summary item is plain prose.
    prose_sheet_items = [
        _Item(
            kind="title",
            text="1. Forces and Motion",
            page=1,
            marker="1.",
            bold=("Forces and Motion",),
        ),
        _Item(
            kind="heading",
            text="2. Newton's Second Law",
            page=1,
            marker="2.",
            bold=("Newton's Second Law",),
        ),
        _Item(
            kind="point",
            text="Force equals mass multiplied by acceleration: F = m × a.",
            page=1,
            unit_ids=("U1",),
            topic="Newton's Second Law",
            bullet=None,
            marker=None,
            bold=(),
        ),
        _Item(
            kind="summary",
            text="The SI unit of force is the newton (N).",
            page=1,
            unit_ids=("U2",),
            topic="Newton's Second Law",
            bullet=None,
            marker=None,
            bold=(),
        ),
    ]
    cards_prose, notes_prose = plan_key_facts_with_notes(prose_sheet_items, standard=8)
    assert len(cards_prose) >= 1
    assert notes_prose == (
        "Nothing on these pages is printed in bold or as a bullet or numbered point, "
        "so Key Facts made study cards from every line instead.",
    )

    # Also verify on the real plain-prose physics sheet
    with open(ROOT / "data" / "full-physics-forces.reader.json", encoding="utf-8") as fh:
        physics_data = json.load(fh)
    _, physics_notes = plan_key_facts_with_notes(physics_data["items"], standard=8)
    assert physics_notes == (
        "Nothing on these pages is printed in bold or as a bullet or numbered point, "
        "so Key Facts made study cards from every line instead.",
    )

    # FAIL (Note NOT shown): When a point/summary item is bulleted or bold, no parent note is returned
    bullet_sheet_items = [
        _Item(
            kind="heading",
            text="1. Newton's Second Law",
            page=1,
            marker="1.",
            bold=("Newton's Second Law",),
        ),
        _Item(
            kind="point",
            text="The SI unit of force is the newton (N).",
            page=1,
            unit_ids=("U1",),
            topic="Newton's Second Law",
            bullet="•",
            bold=(),
        ),
    ]
    _, notes_bullet = plan_key_facts_with_notes(bullet_sheet_items, standard=8)
    assert notes_bullet == ()


def test_v8_fix2_book_document_act_titles_one_name_pass_and_fail() -> None:
    """Fix 2: Titles of books/documents/acts in a line ('Authored Poverty and Un-British Rule in India')
    are one name: never blank part of it.
    """
    # PASS: The full 6-word book title 'Poverty and Un-British Rule in India' is blanked as one name
    items = [
        _Item(
            kind="point",
            text="Authored Poverty and Un-British Rule in India (1901), setting out the Drain of Wealth theory.",
            page=1,
            unit_ids=("U1",),
            topic="Dadabhai Naoroji",
            bullet="•",
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    answers = {c.answer for c in cards}
    assert "Poverty and Un-British Rule in India" in answers
    assert "Poverty" not in answers
    assert "Poverty and Un-British Rule" not in answers
    assert "Un-British Rule" not in answers

    # FAIL: Candidate card that blanks only part of the book title is rejected with 'split_proper_name'
    item_dict = {
        "id": "P_BOOK",
        "kind": "point",
        "text": "Authored Poverty and Un-British Rule in India",
        "topic": "Dadabhai Naoroji",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    partial_title_card = {
        "id": "C_SPLIT_BOOK",
        "fact_id": "F_SPLIT_BOOK",
        "item_id": "P_BOOK",
        "page": 1,
        "label": "Dadabhai Naoroji",
        "subject": "Dadabhai Naoroji",
        "front": "Dadabhai Naoroji authored ______ in India.",
        "prompt": "Which name fits the gap?",
        "answer": "Poverty and Un-British Rule",
        "question_type": "GAP",
        "relation": "GAP_CUSTOM",
        "source_text": item_dict["text"],
    }
    reasons = validate.validate_card(partial_title_card, {"P_BOOK": item_dict}, vocab, set())
    assert "split_proper_name" in reasons


def test_v8_fix3_answer_does_not_repeat_question_words_pass_and_fail() -> None:
    """Fix 3: An answer must not repeat words from its own question:
    'What is Belfast the capital of?' -> 'Northern Ireland', not 'Capital of Northern Ireland'.
    """
    # PASS: Topic header 'Belfast – Capital of Northern Ireland' produces answer 'Northern Ireland'
    items = [
        _Item(
            kind="topic",
            text="Belfast – Capital of Northern Ireland",
            page=1,
            unit_ids=("U1",),
            topic="Belfast",
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    cap_cards = [c for c in cards if c.clue == "What is Belfast the capital of?"]
    assert len(cap_cards) == 1
    assert cap_cards[0].answer == "Northern Ireland"

    # FAIL: Candidate card whose answer repeats 'Capital of' from 'What is Belfast the capital of?' is rejected
    item_dict = {
        "id": "I_CAP",
        "kind": "topic",
        "text": "Belfast – Capital of Northern Ireland",
        "topic": "Belfast",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    repeating_card = {
        "id": "C_REP",
        "fact_id": "F_REP",
        "item_id": "I_CAP",
        "page": 1,
        "label": "Belfast",
        "subject": "Belfast",
        "front": "What is Belfast the capital of?",
        "prompt": "",
        "answer": "Capital of Northern Ireland",
        "question_type": "WHERE",
        "relation": "CAPITAL_OF",
        "source_text": item_dict["text"],
    }
    reasons = validate.validate_card(repeating_card, {"I_CAP": item_dict}, vocab, set())
    assert "answer_repeats_question_words" in reasons


def test_v8_fix4_no_fragment_clues_pass_and_fail() -> None:
    """Fix 4: No fragment clues: a clue must contain a verb or a '<term>: <value>' pattern
    ('Capital and ______.' is not a clue).
    """
    # PASS: Line 'Capital and largest city of Northern Ireland; situated on the River Lagan.'
    # with bold=['largest city of Northern Ireland'] produces only complete question/verb clues,
    # never 'Capital and ______.'
    items = [
        _Item(
            kind="point",
            text="Capital and largest city of Northern Ireland; situated on the River Lagan.",
            page=1,
            unit_ids=("U1",),
            topic="Belfast",
            bullet="•",
            bold=("largest city of Northern Ireland",),
        ),
    ]
    cards = plan_key_facts(items, standard=8)
    assert len(cards) >= 1
    for c in cards:
        assert c.clue != "Capital and ______."
        assert not validate._is_fragment_clue(c.clue)

    # FAIL: Candidate card with fragment clue 'Capital and ______.' is rejected with 'fragment_clue'
    item_dict = {
        "id": "I_FRAG",
        "kind": "point",
        "text": "Capital and largest city of Northern Ireland",
        "topic": "Belfast",
    }
    vocab = validate.build_sheet_vocabulary({"items": [item_dict]})
    fragment_card = {
        "id": "C_FRAG",
        "fact_id": "F_FRAG",
        "item_id": "I_FRAG",
        "page": 1,
        "label": "Belfast",
        "subject": "Belfast",
        "front": "Capital and ______.",
        "prompt": "Which place fits the gap?",
        "answer": "largest city of Northern Ireland",
        "question_type": "GAP",
        "relation": "GAP_CUSTOM",
        "source_text": item_dict["text"],
    }
    reasons = validate.validate_card(fragment_card, {"I_FRAG": item_dict}, vocab, set())
    assert "fragment_clue" in reasons


def load_tests(
    loader: unittest.TestLoader,
    tests: unittest.TestSuite,
    pattern: str | None,
) -> unittest.TestSuite:
    """Allow unittest discovery to run plain pytest-style test_* functions in this module."""
    _ = (loader, tests, pattern)
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            suite.addTest(unittest.FunctionTestCase(obj))
    return suite
