"""The layout reader and card planner on real sheet layouts.

The Mumbai sheets are Grade 8 revision notes printed from a browser, where every printed line is its own text block
and bullets are drawn dots. The other sheets are small synthetic layout tests. Card checks here confirm structure
(which words become the clue and which the answer); they are not evidence that the cards teach well.
"""

from pathlib import Path

import pymupdf
import pytest

from learn.extraction import extract, text_block_units
from learn.teaching_engine import extract_facts, render_printable_cards_pdf
from learn.teaching_engine.cards import GAP, plan_cards
from learn.teaching_engine.sheet import read_sheet

SHEETS = Path(__file__).parent / "sheets"


def _read(name: str):
    data = (SHEETS / name).read_bytes()
    source = extract(data)
    inventory = extract_facts(source.units)
    return data, source, inventory, read_sheet(inventory, data)


def _cards(name: str):
    return plan_cards(_read(name)[3])


def test_block_unit_map_matches_the_extracted_units():
    data = (SHEETS / "mumbai-leaders.pdf").read_bytes()
    with pymupdf.open(stream=data, filetype="pdf") as document:
        mapped = {unit_id for _, unit_id in text_block_units(document[0], 1)}

    assert mapped == {unit.id for unit in extract(data).units}


def test_wrapped_lines_join_back_into_whole_bullets_with_their_unit_citations():
    _, source, _, sheet = _read("mumbai-leaders.pdf")
    points = {item.text: item for item in sheet.items if item.kind == "point"}

    educated = points[
        "Educated at Elphinstone Institution, Mumbai; founding member of the Indian National Congress (1885), thrice "
        "its President (1886, 1893, 1906), and first Indian elected to the British House of Commons (1892) "
        "(Britannica)."
    ]
    assert educated.unit_ids == ("SRC-P1-U3", "SRC-P1-U4")
    assert educated.topic == 'Dadabhai Naoroji (1825–1917) – "Grand Old Man of India"'
    units = {unit.id: unit.text for unit in source.units}
    assert units["SRC-P1-U4"].startswith("its President (1886, 1893, 1906)")
    assert any("leading the Non-Cooperation (1920), Salt Satyagraha (1930)" in text for text in points)
    assert [item.text for item in sheet.items if item.kind == "topic"] == [
        'Dadabhai Naoroji (1825–1917) – "Grand Old Man of India"',
        "Lokmanya Bal Gangadhar Tilak (1856–1920) – Leader of Assertive Nationalism",
        'Sir Pherozeshah Mehta (1845–1915) – "Lion of Bombay"',
        "Mahatma Gandhi (1869–1948) – Leader of the Mass Freedom Struggle",
    ]
    assert not any("Page 1" in item.text or "Political Leaders" in item.text for item in sheet.items)


def test_comparison_table_is_read_cell_by_cell_and_questions_keep_their_answers():
    sheet = _read("mumbai-leaders.pdf")[3]
    table = next(item.table for item in sheet.items if item.kind == "table")
    questions = [item for item in sheet.items if item.kind == "question"]

    assert table.header == ("Feature", "Dadabhai Naoroji", "Bal Gangadhar Tilak", "Pherozeshah Mehta", "Mahatma Gandhi")
    assert table.rows[0] == (
        "Popular Title",
        "Grand Old Man of India",
        'Lokmanya ("Revered by the People")',
        "Lion of Bombay",
        'Mahatma ("Great Soul"); Father of Nation',
    )
    assert table.rows[2][4] == "Mani Bhavan HQ (1917–34); Gowalia Tank"
    assert questions[0].text == (
        "Who authored Poverty and Un-British Rule in India (1901) and became the first Indian MP in the British "
        "Parliament?"
    )
    assert questions[0].answer == 'Dadabhai Naoroji ("Grand Old Man of India").'
    assert questions[2].text.endswith("where was Gandhi's Mumbai headquarters (1917–1934)?")


def test_cards_from_a_sheet_ask_who_fill_gaps_compare_and_reuse_its_questions():
    cards = _cards("mumbai-leaders.pdf")
    by_kind: dict[str, list] = {}
    for card in cards:
        by_kind.setdefault(card.kind, []).append(card)

    first = by_kind["name"][0]
    assert (first.clue, first.question, first.answer) == (
        '______ (1825–1917) – "Grand Old Man of India"',
        "Who is this?",
        "Dadabhai Naoroji",
    )
    assert any(card.clue == "Championed Swaraj (Self-Rule), Swadeshi, and Boycott" for card in by_kind["riddle"])
    born = next(card for card in by_kind["gap"] if card.answer == "1 August 1920")
    assert born.question == "Which date fits the gap?" and born.about == "Lokmanya Bal Gangadhar Tilak"
    titles = by_kind["compare"][0]
    assert titles.question == "What is each one's Popular Title?"
    assert titles.answer.splitlines()[0] == "Dadabhai Naoroji: Grand Old Man of India"
    assert by_kind["question"][1].answer == "The public Ganesh Chaturthi festival and the Shivaji festival."
    assert by_kind["tip"][0].clue == "Remember the 4 Leaders across the 3 ICSE History Eras …"
    for card in cards:
        assert card.answer and card.answer not in card.clue.replace(GAP, "")


def test_a_sheet_without_colours_or_bold_reads_the_same_way():
    sheet = _read("mumbai-personalities-flat.pdf")[3]
    table = next(item.table for item in sheet.items if item.kind == "table")

    assert len([item for item in sheet.items if item.kind == "topic"]) == 5
    assert table.header[1:] == (
        "Jamsetji Tata",
        "Jyotirao Phule",
        "Savitribai Phule",
        "Dr. B. R. Ambedkar",
        "R. R. M. Roy",
    )
    assert [row[0] for row in table.rows] == ["Role / Title", "Key Institution", "Mumbai / West Link", "Core Impact"]
    assert [item.answer for item in sheet.items if item.kind == "question"][1] == (
        "The Satyashodhak Samaj (Society of Truth Seekers)."
    )


def test_dated_event_headings_keep_their_dates_and_are_not_people():
    names = {card.answer: card for card in _cards("mumbai-events.pdf") if card.kind == "name"}

    salt = names["Salt March (Dandi Satyagraha) & Civil Disobedience"]
    assert salt.clue == "______ (12 March – 6 April 1930)"
    assert names["Non-Cooperation Movement"].question == "What is it?"
    assert names["Quit India Movement"].clue == "______ – August Kranti (8 August 1942)"


def test_side_by_side_panels_become_sorting_cards():
    cards = _cards("comparison-panels.pdf")
    sorting = [card for card in cards if card.kind == "sort"]

    assert len(sorting) == 8
    assert {card.question for card in sorting} == {"Which one is it: WEATHER or CLIMATE?"}
    assert [(card.clue, card.answer) for card in sorting[:2]] == [
        ("Short-term conditions", "WEATHER"),
        ("Long-term patterns", "CLIMATE"),
    ]


def test_sub_headings_term_lists_and_questions_on_one_line():
    cards = _cards("lesson-subheadings.pdf")
    terms = [card for card in cards if card.kind == "term"]
    questions = [card.clue for card in cards if card.kind == "question"]

    assert [card.answer for card in terms] == ["Evaporation", "Condensation", "Precipitation", "Collection"]
    assert terms[0].clue == "Heat from the Sun changes liquid water into water vapour."
    assert {card.about for card in terms} == {"Four main stages"}
    assert questions == ["What causes evaporation?", "How do clouds form?", "Name two forms of precipitation."]
    called = next(card for card in cards if card.answer == "water cycle")
    assert called.clue == "This movement is called the ______."
    assert not any("By the end of this lesson" in card.clue for card in cards)


def test_practice_tables_and_unit_facts_become_questions_with_answers():
    cards = _cards("compact-revision.pdf")
    answers = {card.clue: card.answer for card in cards}

    assert answers["15% of 200"] == "30  (working: 0.15 × 200)"
    assert answers["1 km = ______"] == "1,000 m"
    assert answers["¾ = ______"] == "75%"
    assert "Write 0.4 as a percentage." in answers


def test_equations_hide_the_result_but_never_the_problem_to_solve():
    answers = {card.clue: card.answer for card in _cards("equations.pdf")}

    assert answers["Area of a rectangle: A = ______"] == "l × w"
    assert answers["Area of a triangle: A = ______"] == "½ × b × h"
    assert "3x + 7 = ______" not in answers


def test_text_the_pdf_font_lost_is_left_out_and_noted_for_the_adult():
    data, _, inventory, sheet = _read("missing-script-font.pdf")
    cards = plan_cards(sheet)

    pages = [
        " ".join(page.get_text().split()) for page in pymupdf.open(stream=render_printable_cards_pdf(inventory, data))
    ]
    assert not any("IIII" in text for card in cards for text in (card.clue, card.answer, card.about))
    assert "Some text on page 1 could not be read from the PDF" in pages[-1]


@pytest.mark.parametrize("name", sorted(path.name for path in SHEETS.glob("*.pdf")))
def test_every_sample_sheet_prints_cards_and_an_answer_sheet(name):
    data, _, inventory, _ = _read(name)

    pages = [page.get_text() for page in pymupdf.open(stream=render_printable_cards_pdf(inventory, data))]

    assert len(pages) >= 2 and pages[-1].lstrip().startswith("ANSWER SHEET")
    assert all("SRC-P" not in page for page in pages)


def test_a_printed_timeline_asks_for_each_year_and_for_the_order():
    cards = _cards("full-history-timeline.pdf")
    years = {card.clue: card.answer for card in cards if card.kind == "timeline"}
    order = next(card for card in cards if card.kind == "order")

    assert years == {"Plassey": "1757", "Revolt": "1857", "Congress": "1885", "Independence": "1947"}
    assert order.clue.splitlines() == ["Congress", "Independence", "Plassey", "Revolt"]
    assert order.answer.splitlines() == ["1757: Plassey", "1857: Revolt", "1885: Congress", "1947: Independence"]
    assert cards[0].about == "BIG IDEA" and not cards[0].clue.startswith("BIG IDEA")


def test_table_rows_ask_which_one_a_description_belongs_to():
    rows = [card for card in _cards("full-history-timeline.pdf") if card.kind == "row"]
    forces = [card for card in _cards("full-physics-forces.pdf") if card.kind == "row"]

    first = rows[0]
    assert (first.clue, first.question, first.answer, first.about) == (
        "Taxation, trade, land revenue, access to resources",
        "Which factor is it?",
        "Economic",
        "How it can influence change",
    )
    assert any(card.question == "Which source is it?" and card.answer == "Personal diary" for card in rows)
    assert forces[0].question == "Which situation is it?" and forces[0].answer == "Book resting on table"


def test_computed_results_are_asked_but_values_the_sheet_gives_are_not():
    answers = {card.clue: card.answer for card in _cards("full-physics-forces.pdf")}

    assert answers["Trial D: a = 1.00 ÷ 1.50 ≈ ______"] == "0.67 m/s²"
    assert answers["Resultant force determines acceleration: F = ______"] == "ma"
    assert answers["1 N = ______"] == "1 kg·m/s²"
    assert "Find resultant force and acceleration." in " ".join(answers)  # the sheet's practice task
    assert not any(clue.endswith("radius = ______") for clue in answers)


@pytest.mark.parametrize(
    ("name", "lost"),
    [("full-chemistry-lost-subscripts.pdf", "CaCO"), ("full-finance-lost-rupee.pdf", "600 interest")],
)
def test_letters_the_pdf_font_lost_never_reach_a_card(name, lost):
    data, _, inventory, sheet = _read(name)
    cards = plan_cards(sheet)

    shown = [text for card in cards for text in (card.clue, card.answer, card.about)]
    assert cards and not any("�" in text or lost in text for text in shown)
    assert not any(card.kind == "sort" for card in cards)  # a lost "₹" at the start of a cell is not a bullet
    answer_sheet = pymupdf.open(stream=render_printable_cards_pdf(inventory, data))[-1].get_text()
    assert "could not be read from the PDF" in answer_sheet


def test_a_question_table_and_number_tables_make_the_right_cards():
    cards = _cards("full-stem-checklist.pdf")
    questions = {card.clue: card.answer for card in cards if card.kind == "question"}

    assert questions["Are units consistent?"] == "Mixed units can create false comparisons."
    assert questions["Does correlation prove cause?"] == "No; multiple explanations may fit the same pattern."
    assert not any("Rainfall (mm)" in card.about or card.answer == "Jan" for card in cards)
    assert any(card.clue == "Rainfall range = 240 − 15 = ______" and card.answer == "225 mm" for card in cards)
