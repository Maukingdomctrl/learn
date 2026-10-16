from pathlib import Path
from time import perf_counter

import pymupdf
import pytest

from learn.extraction import choose_ocr, extract
from learn.grounding import SourceUnit
from learn.teaching_engine import (
    create_teaching_lesson,
    extract_facts,
    extract_source_visuals,
    render_printable_cards_pdf,
    render_teaching_pdf,
)
from learn.teaching_engine.cards import _focus, _split_long_fact


def test_printable_pdf_keeps_source_citations_recall_and_review_flags():
    units = [
        SourceUnit(
            id="unit-1",
            page=2,
            text="London is in England. London stands on the River Thames.",
            method="text",
        ),
        SourceUnit(
            id="unit-2",
            page=3,
            text="The steam engine was invented by James Watt.",
            method="text",
        ),
    ]
    lesson = create_teaching_lesson(extract_facts(units))

    pdf_bytes = render_teaching_pdf(lesson, ["A source page contains a diagram."])
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = "\n".join(page.get_text() for page in document)

    assert pdf_bytes.startswith(b"%PDF")
    assert document.page_count >= 1
    assert "SOURCE" in text
    assert "PAGE 2" in text
    assert "London is in England." in text
    assert "REMEMBER IT" in text
    assert "Your sketch" in text
    assert "PAUSE" in text
    assert "James Watt" in text
    assert "diagram" in text


def test_printable_cards_include_fronts_mirrored_backs_source_pages_and_review_warning():
    statements = [
        "The Thames flows through London.",
        "The industrial steam engine was invented by James Watt.",
        "The population was 8 million in 2020.",
        "Migration means the movement of people.",
        "Children remember source ideas by making a personal picture.",
        "A river flows into the sea.",
        "The city grew near the coast.",
        "A factory makes steel from iron.",
        "The port is located in Belfast.",
        "The railway opened in 1840.",
        "The museum stands beside the river.",
    ]
    units = [SourceUnit("SRC-P2-U1", 2, " ".join(statements), "text")]
    inventory = extract_facts(units)

    pdf_bytes = render_printable_cards_pdf(inventory)
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    fronts = document[0].get_text()
    backs = document[1].get_text()
    all_fronts = fronts + document[2].get_text()
    second_sheet_fronts = document[2].get_text()

    assert pdf_bytes.startswith(b"%PDF")
    assert document.page_count == 4
    assert "PLACE DETECTIVE" in all_fronts
    assert "________" in fronts
    assert "SOURCE IDEA" in second_sheet_fronts
    assert "SOURCE ANSWER" in backs
    assert "The Thames flows through London." in backs
    assert "Source page 2" in backs
    assert "My memory hook" in backs
    assert "SKETCH" in backs
    assert "VERIFY FIRST" in backs
    assert "verify_attribution_or_absolute_claim" in backs


def test_printable_cards_reject_empty_inventory_and_split_oversized_source_fact():
    empty = extract_facts([])
    with pytest.raises(ValueError, match="No source facts"):
        render_printable_cards_pdf(empty)

    statement = ("longword " * 300) + "."
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, statement, "text")])
    segments = _split_long_fact(inventory.facts[0])

    assert len(segments) > 1
    assert "".join(segment.statement for segment in segments) == statement
    pdf_bytes = render_printable_cards_pdf(inventory)
    assert pdf_bytes.startswith(b"%PDF")


def test_detective_and_superhero_games_use_different_prompts_and_source_visuals():
    source_pdf = Path("cards/sample/people-sheet.pdf").read_bytes()
    visuals = extract_source_visuals(source_pdf, pages={1})
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, "Migration means the movement of people.", "text")])

    detective_pdf = render_printable_cards_pdf(inventory, source_pdf, "detective", {1}, 8)
    superhero_pdf = render_printable_cards_pdf(inventory, source_pdf, "superhero", {1}, 7)
    detective = pymupdf.open(stream=detective_pdf, filetype="pdf")
    superhero = pymupdf.open(stream=superhero_pdf, filetype="pdf")
    detective_text = "\n".join(page.get_text() for page in detective)
    superhero_text = "\n".join(page.get_text() for page in superhero)

    assert len(visuals) == 3
    assert "DETECTIVE CASE FILE" in detective_text
    assert "name the missing evidence" in detective_text
    assert "CASE POINT" in detective_text
    assert "What does this word mean here?" in detective_text
    assert "SOURCE VISUAL" in detective_text
    assert "SUPERHERO POWER-UP GAME" in superhero_text
    assert "POWER-UP - Explain this word to your teammate." in superhero_text
    assert "teach a teammate" in superhero_text
    assert "POWER:" in superhero_text
    assert "ICSE STANDARD" not in superhero_text
    assert "TURN OVER TO CHECK" not in superhero_text
    assert "PAGE 1" in superhero_text


@pytest.mark.parametrize("filename", ["civics-sheet.pdf", "industries-sheet.pdf"])
def test_card_layout_fits_long_source_rows_and_comparison_tables(filename):
    source_pdf = (Path(__file__).parents[1] / "cards" / "sample" / filename).read_bytes()
    ocr, ocr_name = choose_ocr("auto")
    source = extract(source_pdf, ocr, ocr_name)

    pdf_bytes = render_printable_cards_pdf(extract_facts(source.units), source_pdf)

    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert pdf_bytes.startswith(b"%PDF")
    assert document.page_count >= 2
    assert "SOURCE ANSWER" in "\n".join(page.get_text() for page in document)


def test_card_focus_does_not_turn_class_or_page_numbers_into_quiz_answers():
    source = SourceUnit(
        "SRC-P2-U1",
        2,
        "Class 8 Geography | Industries sample Page 2 COMPARATIVE TABLE Feature Cotton Textile Industry",
        "text",
    )
    fact = extract_facts([source]).facts[0]

    focus = _focus(fact)

    assert focus is None or focus[0].text not in {"8", "2"}


@pytest.mark.parametrize(
    "statement",
    [
        "Respiration produces carbon dioxide.",
        "QUICK REVISION - Key Ideas for the Carbon Cycle",
        "Question 7: Which two processes release carbon dioxide?",
    ],
)
def test_card_focus_preserves_headings_and_arbitrary_capitalized_words(statement):
    fact = extract_facts([SourceUnit("SRC-P2-U1", 2, statement, "text")]).facts[0]

    assert _focus(fact) is None


def test_card_focus_keeps_a_full_question_unmasked_even_with_a_numbered_prefix():
    statement = "Question 7: Which city is the capital of the UK?"
    inventory = extract_facts([SourceUnit("SRC-P2-U1", 2, statement, "text")])
    front = pymupdf.open(stream=render_printable_cards_pdf(inventory), filetype="pdf")[0].get_text()

    assert "SOURCE QUESTION" in front
    assert statement in " ".join(front.split())
    assert "________" not in front


@pytest.mark.parametrize(
    ("statement", "expected_label", "expected_target"),
    [
        ("Migration means the movement of people.", "WORD DETECTIVE", "Migration"),
        ("The industrial steam engine was invented in 1760.", "TIME DETECTIVE", "1760"),
        ("The population was 8 million in 2020.", "TIME DETECTIVE", "2020"),
    ],
)
def test_card_focus_blanks_only_supported_terms_and_values(statement, expected_label, expected_target):
    fact = extract_facts([SourceUnit("SRC-P2-U1", 2, statement, "text")]).facts[0]

    focus = _focus(fact)

    assert focus is not None
    assert focus[1] == expected_label
    assert focus[0].text == expected_target


def test_numbered_question_stays_together_and_is_not_turned_into_a_cloze():
    question = "Question 7 ?Although plants produce carbon dioxide.? What does this tell you about the two processes?"
    inventory = extract_facts([SourceUnit("SRC-P3-U1", 3, question, "text")])

    assert len(inventory.facts) == 1
    assert _focus(inventory.facts[0]) is None

    pdf_bytes = render_printable_cards_pdf(inventory)
    front = pymupdf.open(stream=pdf_bytes, filetype="pdf")[0].get_text()

    assert "SOURCE QUESTION" in front
    assert "Question 7" in front
    assert "________" not in front
    assert _split_long_fact(inventory.facts[0]) == (inventory.facts[0],)


def test_long_table_fragment_is_split_into_exact_cited_card_excerpts():
    statement = (
        "Heart of Industrial Revolution; steam engine Financial centre of Europe Scottish Parliament; RBS HQ "
        "Famous Landmark / Fact Birmingham Hippodrome (busiest theatre) Titanic Belfast Museum; Harland & Wolff "
        "Wales Millennium Centre; Capital since 1955 Modern Economy Finance, innovation, culture Industry, technology, "
        "culture Industry, aerospace, arts, education Finance, banking, tourism (£1.6 bn) Retail, finance, media, "
        "tourism Special Note Metropolitan area covers SE England Grew to prominence in 18th century Pop. ~286,000 "
        "(2011); economic engine of NI"
    )
    fact = extract_facts([SourceUnit("SRC-P3-U5", 3, statement, "text")]).facts[0]

    segments = _split_long_fact(fact)
    pdf_bytes = render_printable_cards_pdf(extract_facts([SourceUnit("SRC-P3-U5", 3, statement, "text")]))
    output_text = " ".join(
        "\n".join(page.get_text() for page in pymupdf.open(stream=pdf_bytes, filetype="pdf")).split()
    )

    assert len(segments) > 1
    assert "".join(segment.statement for segment in segments) == statement
    assert all(segment.page == fact.page and segment.source_unit_id == fact.source_unit_id for segment in segments)
    assert "Heart of Industrial Revolution" in output_text
    assert "economic engine of NI" in output_text


def test_printing_uses_safe_formula_symbols_without_changing_source_fact():
    statement = "Photosynthesis: CO₂ + H₂O → glucose + O₂"
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, statement, "text")])
    pdf_bytes = render_printable_cards_pdf(inventory)
    printed_text = "\n".join(page.get_text() for page in pymupdf.open(stream=pdf_bytes, filetype="pdf"))

    assert inventory.facts[0].statement == statement
    normalized_text = " ".join(printed_text.split())
    assert "CO2 + H2O" in normalized_text
    assert "->" in normalized_text
    assert "glucose + O2" in normalized_text


@pytest.mark.parametrize("game_mode", ["detective", "superhero"])
def test_card_text_layout_retries_a_smaller_size_when_actual_wrapping_differs(game_mode):
    statement = (
        "• Key role in the Industrial Revolution; global industrial centre until the latter half of the 20th century."
    )
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, statement, "text")])

    pdf_bytes = render_printable_cards_pdf(inventory, game_mode=game_mode)
    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    text = " ".join("\n".join(page.get_text() for page in document).split())

    assert "Key role in the Industrial Revolution" in text
    assert "global industrial centre until the latter half" in text


def test_long_lesson_pdf_renders_without_host_timeout():
    sentence = "The river Ganga flows to the Bay of Bengal. Farmers grow rice in the fertile delta. "
    units = [SourceUnit(id=f"unit-{number}", page=number, text=sentence * 12, method="text") for number in range(1, 41)]
    lesson = create_teaching_lesson(extract_facts(units))

    started = perf_counter()
    pdf_bytes = render_teaching_pdf(lesson)
    elapsed = perf_counter() - started

    assert pymupdf.open(stream=pdf_bytes, filetype="pdf").page_count > 100
    assert elapsed < 20, f"rendering took {elapsed:.1f} s"
