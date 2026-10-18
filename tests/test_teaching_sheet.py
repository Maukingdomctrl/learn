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
    assert any(card.clue.startswith("Water changes state, but the total amount") for card in cards)
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


def test_model_answers_printed_under_their_questions_become_their_answers():
    sheet = _read("carbon-cycle-answers.pdf")[3]
    questions = [item for item in sheet.items if item.kind == "question"]
    cards = plan_cards(sheet)

    assert [item.number for item in questions] == ["1", "2", "3", "4", "5", "6", "7"]
    assert questions[0].text == "Name the gas that is a reactant in photosynthesis."
    assert questions[0].answer.splitlines() == [
        "• Carbon dioxide (CO2)",
        "Note: Water is also a reactant, but the question asks for the gas.",
    ]
    assert questions[4].answer.splitlines()[:2] == [
        "When animals are alive:",
        "• Animals carry out respiration (aerobic respiration).",
    ]
    assert questions[6].text.endswith("about the reactions of photosynthesis and respiration in plants?")
    assert all(card.answer for card in cards if card.kind == "question")
    decomposed = next(card for card in cards if card.clue.startswith("Dead animals are decomposed"))
    assert decomposed.about == "After animals have died"
    assert decomposed.answer == "… by bacteria and fungi (decomposers)."
    assert any(card.clue == "In respiration, glucose + oxygen → ______" for card in cards)
    shown = [card.clue for card in cards]
    assert not any(clue.startswith("Note:") or "Model answers based on" in clue for clue in shown)


def test_a_question_table_and_number_tables_make_the_right_cards():
    cards = _cards("full-stem-checklist.pdf")
    questions = {card.clue: card.answer for card in cards if card.kind == "question"}

    assert questions["Are units consistent?"] == "Mixed units can create false comparisons."
    assert questions["Does correlation prove cause?"] == "No; multiple explanations may fit the same pattern."
    assert not any("Rainfall (mm)" in card.about or card.answer == "Jan" for card in cards)
    assert any(card.clue == "Rainfall range = 240 − 15 = ______" and card.answer == "225 mm" for card in cards)


def _ruled_table_pdf() -> bytes:
    """A bordered comparison table like a revision sheet's: wrapped cells ("~" breaks a line), a "—" and nine rows."""
    rows = [
        "Feature | London | Birmingham | Belfast | Cardiff",
        "Country / Region | England (UK Capital) | West Midlands,~England | Northern Ireland | Wales",
        "Status | Capital of UK &~England | Largest city outside~London | Capital of N. Ireland | Capital of Wales",
        "River | River Thames | River Rea | River Lagan | —",
        "Population Rank | Largest in UK | 2nd largest in UK~(outside London) | Largest in N.~Ireland | 11th in UK",
        "Key Role | Political, economic &~cultural hub | Heart of Industrial~Revolution; steam~engine"
        " | Shipbuilding~(Titanic) | Top coal port in~19th century",
        "Landmark | Financial centre of~Europe | Birmingham~Hippodrome | Titanic Belfast~Museum"
        " | Wales Millennium~Centre",
        "Economy | Finance, innovation,~culture | Industry, technology,~culture | Industry, aerospace,~arts"
        " | Retail, finance,~media",
        "Special Note | Covers SE England | Grew to prominence in~18th century | Pop. ~286,000 (2011)"
        " | Made city 1905;~capital 1955",
    ]
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 40), "COMPARATIVE TABLE", fontsize=12)
    widths, y = [80, 110, 110, 100, 100], 60
    for row in rows:
        cells = [cell.strip().replace("~", "\n") for cell in row.split("|")]
        height = 12 + 9 * max(cell.count("\n") + 1 for cell in cells)
        x = 40
        for width, text in zip(widths, cells, strict=True):
            box = pymupdf.Rect(x, y, x + width, y + height)
            page.draw_rect(box, color=(0, 0, 0), width=0.7)
            page.insert_textbox(box + (4, 3, -4, -2), text, fontsize=7.5)
            x += width
        y += height
    data = document.tobytes()
    document.close()
    return data


def test_a_bordered_table_is_read_whole_from_its_drawn_grid():
    source_pdf = _ruled_table_pdf()
    sheet = read_sheet(extract_facts(extract(source_pdf).units), source_pdf)
    tables = [item.table for item in sheet.items if item.kind == "table"]

    assert len(tables) == 1
    assert tables[0].header == ("Feature", "London", "Birmingham", "Belfast", "Cardiff")
    first = ("Country / Region", "England (UK Capital)", "West Midlands, England", "Northern Ireland", "Wales")
    assert tables[0].rows[0] == first
    assert len(tables[0].rows) == 8 and tables[0].rows[-1][0] == "Special Note"
    # No piece of the table leaks out as a point of its own ("England", "18th century").
    assert not [item.text for item in sheet.items if item.kind in {"point", "heading", "topic"}]


def test_a_table_the_line_reader_breaks_up_is_read_from_its_borders():
    """The UK cities sheet's comparison table wraps cells over several lines; the line reader used to keep three rows
    and leak the rest as fragments ("RBS HQ", "Centre; Capital since") that became nonsense cards."""
    sheet = _read("uk-cities-comparative-table.pdf")[3]
    tables = [item.table for item in sheet.items if item.kind == "table" and item.page == 3]
    cards = plan_cards(sheet)

    assert len(tables) == 1
    assert tables[0].header == ("Feature", "London", "Birmingham", "Belfast", "Edinburgh", "Cardiff")
    assert [row[0] for row in tables[0].rows][-1] == "Special Note" and len(tables[0].rows) == 8
    assert not [item.text for item in sheet.items if item.page == 3 and item.kind in {"point", "heading"}]
    assert not any(card.answer in {"Status", "River"} or "RBS HQ" in card.clue for card in cards)


def _two_chapter_pdf() -> bytes:
    """Chapter 1 ends with "Questions and activities"; chapter 2 follows with a large title and prose."""
    document = pymupdf.open()
    page = document.new_page()
    y = 60

    def write(text: str, size: float, gap: float = 6) -> None:
        nonlocal y
        page.insert_text((50, y), text, fontsize=size)
        y += size + gap

    write("Rivers carry water from the hills to the sea and shape the land along the way.", 12)
    write("Questions and activities", 16, 10)
    write("1. Name two rivers that flow into the Bay of Bengal.", 12)
    write("2. Why do rivers bend more in their middle course?", 12, 18)
    write("CHAPTER", 16)
    write("Reshaping the Map", 30, 14)
    write("The Delhi Sultanate was founded in 1206 and ruled much of north India for three centuries.", 12)
    write("Its sultans built forts, mosques and markets, and collected taxes from the farmers of the land.", 12)
    data = document.tobytes()
    document.close()
    return data


def test_a_new_chapter_ends_the_questions_section_of_the_last_one():
    source_pdf = _two_chapter_pdf()
    sheet = read_sheet(extract_facts(extract(source_pdf).units), source_pdf)
    questions = [item.text for item in sheet.items if item.kind == "question"]
    points = [item.text for item in sheet.items if item.kind == "point"]

    assert len(questions) == 2
    assert any("Delhi Sultanate was founded in 1206" in text for text in points)
    assert any("collected taxes" in text for text in points)


def _justified_page_pdf() -> bytes:
    """A justified paragraph whose middle line the PDF split at a wide word gap, and a title printed up the margin."""
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((50, 60), "Farmers in the river plains grow rice and wheat on the rich soil that", fontsize=11)
    page.insert_text((50, 75), "floods leave behind every", fontsize=11)
    page.insert_text((210, 75), "year, and they sell the grain in the town", fontsize=11)
    page.insert_text((50, 90), "markets that sit along the old trade roads near the river.", fontsize=11)
    page.insert_text(
        (50, 120), "Traders carried the grain on boats down the river to the ports on the coast.", fontsize=11
    )
    page.insert_text((20, 140), "Our Pasts and Present Lives", fontsize=9, rotate=90)
    data = document.tobytes()
    document.close()
    return data


def test_split_justified_lines_and_sideways_margin_text_leave_the_paragraph_whole():
    source_pdf = _justified_page_pdf()
    sheet = read_sheet(extract_facts(extract(source_pdf).units), source_pdf)
    texts = [item.text for item in sheet.items]

    assert texts[0] == (
        "Farmers in the river plains grow rice and wheat on the rich soil that floods leave behind every year, "
        "and they sell the grain in the town markets that sit along the old trade roads near the river."
    )
    assert not [text for text in texts if "Pasts and Present" in text]
