"""Key Facts: cards on what a sheet marks to learn (bold words, bold sentences, bullets, numbered points), no AI."""

import re
from pathlib import Path

import pymupdf
import pymupdf_fonts  # noqa: F401  (registers FiraGO, which prints "•" and "–")
import pytest

from learn.extraction import extract
from learn.teaching_engine import extract_facts, render_printable_cards_pdf
from learn.teaching_engine.cards import GAP, UNMARKED_NOTE, plan_cards, plan_printable_cards
from learn.teaching_engine.sheet import _add_bold, _bold_runs, _Line, read_sheet

ROOT = Path(__file__).parents[1]
SAMPLES = ROOT / "cards" / "sample"
EXAMPLE = ROOT / "learn" / "teaching_engine" / "sample" / "example-sheet.pdf"
SHEETS = Path(__file__).parent / "sheets"


def _sheet_pdf(*pages) -> bytes:
    """A study sheet, one list of lines per page: a heading is a string ("# " for the page's title), any other line
    runs of (text, bold)."""
    regular, bold = pymupdf.Font("figo"), pymupdf.Font("figbo")
    document = pymupdf.open()
    for lines in pages:
        page = document.new_page()
        page.insert_font(fontname="F0", fontbuffer=regular.buffer)
        page.insert_font(fontname="F1", fontbuffer=bold.buffer)
        y = 60.0
        for line in lines:
            if isinstance(line, str):
                title = line.startswith("# ")
                page.insert_text((60, y + 10), line.removeprefix("# "), fontname="F1", fontsize=18 if title else 14)
                y += 40 if title else 34
                continue
            x = 60.0
            for text, heavy in line:
                page.insert_text((x, y), text, fontname="F1" if heavy else "F0", fontsize=11)
                x += (bold if heavy else regular).text_length(text, fontsize=11)
            y += 20
    data = document.tobytes()
    document.close()
    return data


def _sheet(pdf: bytes):
    return read_sheet(extract_facts(extract(pdf).units), pdf)


def _key_facts(pdf: bytes):
    return plan_cards(_sheet(pdf), key_facts=True)


def _words(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


SAMPLE_NAMES = ("civics", "history", "industries", "people", "processes", "resources", "sample")


def test_the_reader_keeps_the_words_each_line_prints_in_bold():
    sheet = _sheet(
        _sheet_pdf(
            [
                "PHOTOSYNTHESIS",
                [("• Green plants make their own food by ", False), ("photosynthesis", True), (".", False)],
                [("• They use ", False), ("sunlight", True), (", ", False), ("water", True), (" and ", False)]
                + [("carbon dioxide", True), (" from the air.", False)],
                [("• Oxygen is given out into the air.", False)],
            ]
        )
    )
    points = [item for item in sheet.items if item.kind == "point"]

    assert [item.bold for item in points] == [("photosynthesis",), ("sunlight", "water", "carbon dioxide"), ()]
    assert all(item.bullet for item in points)
    assert next(item for item in sheet.items if item.kind == "topic").bold == ("PHOTOSYNTHESIS",)


def test_bold_words_wrapped_onto_the_next_line_are_one_run_but_two_sentences_are_not():
    def line(chunks, bold):
        found = _Line("".join(chunks), 0, 0, 1, 1, 11, ())
        found.bold, found.bold_start, found.bold_end = _bold_runs(chunks, bold)
        return found

    first = line(["• Roy is called the ", "Father of the"], [False, True])
    runs = list(first.bold)
    _add_bold(runs, first.bold_end, line(["Indian Renaissance", "."], [True, False]))
    assert runs == ["Father of the Indian Renaissance"]

    first = line(["Food is made by ", "photosynthesis."], [False, True])
    runs = list(first.bold)
    _add_bold(runs, first.bold_end, line(["Chlorophyll", " is green."], [True, False]))
    assert runs == ["photosynthesis.", "Chlorophyll"]  # a run that ends its sentence takes nothing from the next


def test_key_facts_ask_every_bold_term_on_the_sample_sheets():
    for name in SAMPLE_NAMES:
        pdf = (SAMPLES / f"{name}-sheet.pdf").read_bytes()
        sheet = _sheet(pdf)
        answers = " | ".join(card.answer for card in plan_cards(sheet, key_facts=True))
        terms = [run for item in sheet.items if item.kind == "point" for run in item.bold]
        assert terms and [term for term in terms if term not in answers] == [], name


def test_no_key_facts_card_shows_its_own_answer_or_another_cards_answer_in_its_label():
    for name in SAMPLE_NAMES:
        cards = _key_facts((SAMPLES / f"{name}-sheet.pdf").read_bytes())
        answers = {_words(card.answer) for card in cards} - {""}
        shown = [card for card in cards if f" {_words(card.answer)} " in f" {_words(card.clue)} "]
        assert [card for card in shown if card.kind in {"gap", "term"}] == [], name
        assert [card.about for card in cards if any(f" {a} " in f" {_words(card.about)} " for a in answers)] == []
    # Topics stay on the labels: no "Who is this about?" card answers them.
    people = _key_facts((SAMPLES / "people-sheet.pdf").read_bytes())
    founded = next(card for card in people if card.answer == "Brahmo Samaj")
    assert founded.about == "RAJA RAM MOHAN ROY" and founded.clue == f"Founded the {GAP} in 1828."
    assert not any(card.question in {"Who is this about?", "What is this about?"} for card in people)


def test_bold_words_printed_as_a_list_are_asked_together_on_one_card():
    cards = _key_facts(EXAMPLE.read_bytes())
    listed = next(card for card in cards if card.answer == "sunlight, water and carbon dioxide")
    assert listed.clue == f"They use {GAP}, {GAP} and {GAP} from the air."
    assert listed.question == "Which words fit the gaps?"
    assert not any(card.answer in {"sunlight", "water", "carbon dioxide"} for card in cards)

    industries = _key_facts((SAMPLES / "industries-sheet.pdf").read_bytes())
    centres = next(card for card in industries if card.answer == "Mumbai, Ahmedabad and Coimbatore")
    assert centres.question == "Which names fit the gaps?"

    # Bold words joined by other words are separate facts, each on its own card.
    sample = _key_facts((SAMPLES / "sample-sheet.pdf").read_bytes())
    built = {card.answer: card.clue for card in sample if "shipyard built" in card.clue}
    assert built["Harland and Wolff"].startswith(f"{GAP} shipyard built the RMS Titanic")
    assert built["RMS Titanic"].startswith(f"Harland and Wolff shipyard built the {GAP}")


def test_a_bold_label_asks_for_the_term_its_point_describes():
    cards = _key_facts((SHEETS / "lesson-subheadings.pdf").read_bytes())
    terms = {card.answer: card for card in cards if card.kind == "term"}

    assert set(terms) == {"Evaporation", "Condensation", "Precipitation", "Collection"}
    assert terms["Evaporation"].question == "What is it called?"
    assert terms["Evaporation"].clue == "Heat from the Sun changes liquid water into water vapour."


def test_sentences_printed_all_in_bold_get_the_usual_card_and_unmarked_prose_gets_none():
    pdf = _sheet_pdf(
        [
            "Early Nationalism",
            [("In the late nineteenth century, educated Indians began demanding a greater role.", False)],
            "Facts to Remember",
            [("• ", False), ("The Indian National Congress was founded in 1885.", True)],
            [("• ", False), ("India is a democratic republic.", True)],
            [("• ", False), ("The Right to Education covers children aged 6–14 years.", True)],
            "Check Your Understanding",
            [("1. In which year was the Indian National Congress founded?", False)],
            [("2. Name one method of non-violent protest.", False)],
        ]
    )
    asked = {card.clue: card.answer for card in _key_facts(pdf)}

    assert asked == {
        f"The Indian National Congress was founded in {GAP}.": "1885",
        f"India is a democratic {GAP}.": "republic",  # the word the fact ends on, not half the sentence
        f"The Right to Education covers children aged {GAP} years.": "6–14",
    }
    usual = {card.clue for card in plan_cards(_sheet(pdf))}
    assert any(clue.startswith("In the late nineteenth century") for clue in usual)  # the usual cards ask the prose


def test_a_bold_word_said_for_emphasis_or_a_bold_label_such_as_note_is_not_asked():
    pdf = _sheet_pdf(
        [
            "Resources",
            [("• Coal is ", False), ("not", True), (" renewable, but sunlight is.", False)],
            [("Note:", True), (" Check the page numbers in your textbook.", False)],
        ]
    )
    cards = _key_facts(pdf)
    assert not any(card.answer in {"not", "Note"} for card in cards)
    # The bullet still gets a card: it ends on a verb, so its subject is shown and the rest asked for.
    assert any(card.clue == "Coal …" and card.answer == "… is not renewable, but sunlight is." for card in cards)


def test_a_heading_each_page_repeats_among_its_text_stays_but_a_running_header_goes():
    """One-page sheets put together, as in a parent's PDF: the same headings at the same height on every page."""

    def page(topic, fact, question):
        return [
            [("Standard 8 | Civics", False)],
            f"# {topic}",
            [(f"{topic} is explained in this part of the chapter.", False)],
            "Facts to Remember",
            [("• ", False), (fact, True)],
            "Check Your Understanding",
            [(f"1. {question}", False)],
            [("2. Explain it in your own words.", False)],
        ]

    first = page("Parliament", "A proposed law is called a bill.", "What is a bill?")
    second = page("Local Government", "The Gram Sabha includes the voters of a village.", "Who is in the Gram Sabha?")
    sheet = _sheet(_sheet_pdf(first, second))
    texts = [item.text for item in sheet.items]

    assert texts.count("Facts to Remember") == 2 and texts.count("Check Your Understanding") == 2
    assert "Standard 8 | Civics" not in texts
    questions = [item.text for item in sheet.items if item.kind == "question"]
    assert questions[0] == "What is a bill?" and "Who is in the Gram Sabha?" in questions
    bill, gram_sabha = plan_cards(sheet, key_facts=True)  # each page's fact to remember, and nothing else
    assert bill.answer == "bill" and gram_sabha.clue.startswith("The Gram Sabha includes")


def test_key_facts_print_their_cards_once_and_the_parent_can_take_cards_out():
    pdf = EXAMPLE.read_bytes()
    inventory = extract_facts(extract(pdf).units)
    document = pymupdf.open(stream=render_printable_cards_pdf(inventory, pdf, "facts"), filetype="pdf")
    pages = [page.get_text() for page in document]

    assert pages[0].startswith("KEY FACTS") and "ANSWER SHEET" in pages[-1]
    assert not any("FILL IN THE BLANKS" in page or "FILL-IN-THE-BLANK" in page for page in pages)
    assert document.metadata["title"] == "Learn ICSE Standard 8 key facts cards"

    kept = pymupdf.open(stream=render_printable_cards_pdf(inventory, pdf, "facts", skip=frozenset({1})))
    text = "".join(page.get_text() for page in kept)
    assert "Green plants make their own food" not in text and "photosynthesis" not in kept[-1].get_text()
    assert "1" in kept[0].get_text() and "They use" in text  # the rest are numbered from 1 again
    with pytest.raises(ValueError, match="Keep at least one card"):
        render_printable_cards_pdf(inventory, pdf, "facts", skip=frozenset(range(1, 100)))


def test_a_sheet_that_marks_nothing_gets_cards_for_every_line_with_a_note_saying_why():
    lines = [
        "Rivers of India",
        [("The Ganga rises at Gangotri in the Himalayas and flows for about 2,525 km to the Bay of Bengal.", False)],
        [("The Godavari is the longest river of peninsular India and flows into the Bay of Bengal.", False)],
    ]
    pdf = _sheet_pdf(lines)
    cards, notes = plan_printable_cards(extract_facts(extract(pdf).units), pdf, "facts")
    assert cards and UNMARKED_NOTE in notes

    marked = _sheet_pdf([*lines, [("• The ", False), ("Yamuna", True), (" joins the Ganga at Prayagraj.", False)]])
    cards, notes = plan_printable_cards(extract_facts(extract(marked).units), marked, "facts")
    assert [card.answer for card in cards] == ["Yamuna"] and UNMARKED_NOTE not in notes


def _dates_sheet() -> bytes:
    return _sheet_pdf(
        [
            "The Constituent Assembly",
            [("The Assembly first met on ", False), ("9 December 1946", True), (".", False)],
            "Adoption of the Constitution",
            [
                ("The Constituent Assembly adopted the Constitution on ", False),
                ("26 November 1949", True),
                (".", False),
            ],
            [("It came into effect on ", False), ("26 January 1950", True), (", when India became a republic.", False)],
            "Key Dates",
            [("• ", False), ("9 December 1946", True), (" – First meeting of the Constituent Assembly", False)],
            [("• ", False), ("Dr. B. R. Ambedkar", True), (" – Chairman of the Drafting Committee", False)],
            [("• ", False), ("26 January", True), (" – Republic Day", False)],
            [("• ", False), ("Evaporation:", True), (" Heat from the Sun changes water into water vapour.", False)],
            "Republic Day",
            [("The Constitution was written by the Assembly. It came into effect on ", False)]
            + [("26 January 1950", True), (".", False)],
        ]
    )


def test_a_bold_date_label_asks_when_and_a_bold_name_asks_who():
    cards = _key_facts(_dates_sheet())
    labels = {card.answer: (card.question, card.clue) for card in cards if card.kind == "term"}

    assert labels == {
        "9 December 1946": ("When did it happen?", "First meeting of the Constituent Assembly"),
        "Dr. B. R. Ambedkar": ("Who is this?", "Chairman of the Drafting Committee"),
        "26 January": ("When is it?", "Republic Day"),  # a day that comes round every year
        "Evaporation": ("What is it called?", "Heat from the Sun changes water into water vapour."),
    }


def test_a_gap_shows_its_own_sentence_when_the_point_has_other_bold_answers():
    clues = [card.clue for card in _key_facts(_dates_sheet()) if card.kind == "gap"]

    # Each date's card shows only its sentence, so neither prints the other's answer.
    assert f"The Constituent Assembly adopted the Constitution on {GAP}." in clues
    assert f"It came into effect on {GAP}, when India became a republic." in clues
    # With one bold answer, the whole point is shown: its first sentence says what "It" is.
    assert f"The Constitution was written by the Assembly. It came into effect on {GAP}." in clues


def test_a_bold_fact_hides_the_word_it_ends_on_or_asks_for_what_follows_its_subject():
    facts = [
        "Filtration can separate an insoluble solid from a liquid.",
        "Evaporation can leave a dissolved solid behind.",
        "Distillation involves evaporation followed by condensation.",
        "A chemical symbol represents an element.",
        "Subscripts in a formula show the number of atoms of the preceding element.",
        "A physical change does not create a new substance.",
        "A chemical change forms new substance(s).",
        "Unknown chemicals must not be tasted.",
        "Municipal bodies manage civic services in urban areas.",
        "Values below 7 are acidic; values above 7 are basic.",
        "Fundamental Rights are guaranteed by the Constitution of India.",
    ]
    cards = _key_facts(_sheet_pdf(["Separating mixtures", *[[("• ", False), (fact, True)] for fact in facts]]))
    asked = {card.clue: card.answer for card in cards}

    assert asked == {
        f"Filtration can separate an insoluble solid from {GAP}.": "a liquid",  # "a" or "an" go in the gap
        f"Evaporation can leave a dissolved {GAP} behind.": "solid",  # "behind" stays after the gap
        f"Distillation involves evaporation followed by {GAP}.": "condensation",
        f"A chemical symbol represents {GAP}.": "an element",
        f"Subscripts in a formula show the number of atoms of the preceding {GAP}.": "element",
        # Ending on a general word ("substance") or a verb: the subject is shown and the rest asked for.
        "A physical change …": "… does not create a new substance.",
        "A chemical change …": "… forms new substance(s).",
        "Unknown chemicals …": "… must not be tasted.",
        # Ending on a general phrase ("in urban areas"): the word before it is hidden.
        f"Municipal bodies manage civic {GAP} in urban areas.": "services",
        # Two halves joined by ";" are two facts, each without the other's answer.
        f"Values below 7 are {GAP}": "acidic",
        f"values above 7 are {GAP}.": "basic",
        f"Fundamental Rights are guaranteed by the {GAP}.": "Constitution of India",  # a name, hidden whole
    }
    questions = {card.answer: card.question for card in cards}
    assert questions["a liquid"] == "Which term fits the gap?" and questions["solid"] == "Which term fits the gap?"
    assert questions["Constitution of India"] == "Which name fits the gap?"
    assert questions["… does not create a new substance."] == "Finish the sentence."


def test_a_two_word_term_the_sheet_repeats_is_hidden_whole():
    pdf = _sheet_pdf(
        [
            "Plants and the air",
            [("Plants take in carbon dioxide and India is a democratic republic in this test.", False)],
            "Facts to Remember",
            [("• ", False), ("Plants act as a net sink for carbon dioxide.", True)],
            [("• ", False), ("India is a democratic republic.", True)],
            [("• ", False), ("Indicators help identify acidic or basic solutions.", True)],
            [("• ", False), ("Some solutions are basic solutions.", True)],
        ]
    )
    asked = {card.clue: card.answer for card in _key_facts(pdf)}

    assert asked[f"Plants act as a net sink for {GAP}."] == "carbon dioxide"  # printed together twice on the sheet
    assert asked[f"India is a democratic {GAP}."] == "republic"  # the whole term would leave "India is" alone
    assert asked[f"Indicators help identify acidic or basic {GAP}."] == "solutions"  # "basic" pairs with "acidic"


def test_a_task_or_a_line_to_the_reader_is_not_a_fact_to_hide_a_word_in():
    tasks = ["Discuss in groups how plants grow.", "Check your answers with a partner.", "Why do leaves fall?"]
    pdf = _sheet_pdf(["Activities", *[[("• ", False), (task, False)] for task in tasks]])
    cards = plan_printable_cards(extract_facts(extract(pdf).units), pdf, "facts")[0]

    assert not any(card.kind == "gap" and card.clue.startswith(("Discuss", "Check", "Why")) for card in cards)
