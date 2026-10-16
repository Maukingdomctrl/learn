import sys
from pathlib import Path
from time import perf_counter

import pymupdf
import pytest

try:
    import pymupdf_fonts  # noqa: F401

    _HAS_EXTENDED_PDF_FONT = True
except ImportError:
    _HAS_EXTENDED_PDF_FONT = False

from learn.extraction import choose_ocr, extract
from learn.grounding import SourceUnit
from learn.teaching_engine import (
    create_teaching_lesson,
    extract_facts,
    extract_source_visuals,
    render_printable_cards_pdf,
    render_teaching_pdf,
)
from learn.teaching_engine.cards import _CARD_HEIGHT, _CARD_WIDTH, _LEFT, _TOP, GAP, plan_cards, render_cards_pdf
from learn.teaching_engine.sheet import read_sheet

SAMPLES = Path(__file__).parents[1] / "cards" / "sample"

# The extracted text of the UK cities sheet whose old cards printed "1.", page footers and "?" for every bullet.
UK_SHEET = [
    (
        1,
        "IMPORTANT CITIES OF THE UNITED KINGDOM Grade 8 Social Studies | Notes + Comparative Table + "
        "Practice Questions",
    ),
    (
        1,
        "1. QUICK REVISION NOTES 1. LONDON – Capital of the United Kingdom & England "
        "• Situated on the River Thames in southeastern England.",
    ),
    (1, "• Metropolitan area covers much of southeastern England."),
    (1, "2. BIRMINGHAM – West Midlands, England • Major city of the West Midlands, lying on the River Rea."),
    (1, "• Largest and most populous British city outside London."),
    (
        1,
        "• Was a medium-sized market town in the medieval period; grew to international prominence in the "
        "18th century.",
    ),
    (1, "• Birmingham Hippodrome is the UK's busiest theatre (over 520,000 visitors each year)."),
    (
        1,
        "• Main engine of growth in the Welsh economy; centre for white-collar professions. "
        "Grade 8 Social Studies | Country - United Kingdom Page 1",
    ),
    (
        3,
        "2. COMPARATIVE TABLE - EASY TO REMEMBER Feature London Birmingham Belfast Edinburgh Cardiff Northern Ireland "
        "Scotland Wales Country / Region England (UK Capital)",
    ),
    (3, "Largest in N. Ireland; 2nd on Ireland island 2nd in Scotland; 7th in UK"),
    (3, "• Belfast = Shipbuilding & Titanic (Lagan + Harland & Wolff)"),
    (
        4,
        "3. PRACTICE QUESTIONS A. Fill in the Blanks (1 mark each) "
        "1. London is situated on the tidal ________________ in southeastern England.",
    ),
    (4, "2. Birmingham is a major city of the ________________, England."),
    (4, "B. Answer in One Sentence (1 mark each) 1. Name the capital city of Northern Ireland."),
    (4, "2. Which river flows through Birmingham?"),
    (
        5,
        "4. ANSWER KEY A. Fill in the Blanks - Answers 1. River Thames 2. West Midlands "
        "B. One Sentence Answers 1. Belfast is the capital city of Northern Ireland.",
    ),
    (5, "2. The River Rea flows through Birmingham."),
]


def _units(rows):
    counts: dict[int, int] = {}
    units = []
    for page, text in rows:
        counts[page] = counts.get(page, 0) + 1
        units.append(SourceUnit(f"SRC-P{page}-U{counts[page]}", page, text, "text"))
    return units


def _page_texts(pdf_bytes: bytes) -> list[str]:
    return [" ".join(page.get_text().split()) for page in pymupdf.open(stream=pdf_bytes, filetype="pdf")]


def _cards(rows, standard=8):
    return plan_cards(read_sheet(extract_facts(_units(rows))), standard)


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


def test_cards_print_the_question_only_and_the_answers_on_a_separate_sheet():
    rows = [
        (2, "1. LONDON – Capital of the United Kingdom & England"),
        (2, "• Situated on the River Thames in southeastern England."),
        (2, "• The city hosted the Olympic Games in 2012."),
        (2, "2. BELFAST – Capital of Northern Ireland"),
        (2, "• Population about 286,000 (2011 census)."),
    ]

    pages = _page_texts(render_printable_cards_pdf(extract_facts(_units(rows))))
    cards_page, answer_sheet = pages[0], pages[-1]

    assert len(pages) == 3
    assert cards_page.startswith("DETECTIVE CASE FILE")
    assert pages[1].startswith("FILL IN THE BLANKS")
    dash = "–" if _HAS_EXTENDED_PDF_FONT else "-"
    assert f"______ {dash} Capital of the United Kingdom & England" in cards_page
    assert "The city hosted the Olympic Games in ______." in cards_page
    assert "Which year fits the gap?" in cards_page
    assert "Situated on the River Thames in southeastern England." in cards_page
    assert "What is this about?" in cards_page
    assert "2012" not in cards_page and "286,000" not in cards_page
    assert answer_sheet.startswith("ANSWER SHEET")
    for answer in ("LONDON", "2012", "BELFAST", "286,000", "p. 2"):
        assert answer in answer_sheet


def test_cards_carry_no_source_codes_game_rules_or_raw_review_flags():
    inventory = extract_facts(
        [SourceUnit("SRC-P1-U1", 1, "The steam engine was invented by James Watt in 1769.", "text")]
    )

    pages = _page_texts(render_printable_cards_pdf(inventory))

    for clutter in (
        "SRC-P1",
        "verify_attribution",
        "CASE POINT",
        "memory hook",
        "SKETCH",
        "SOURCE IDEA",
        "Review flag",
    ):
        assert all(clutter not in page for page in pages)
    assert "1769" not in pages[0]
    assert "Check first: the sheet says" in pages[-1] and "invented" in pages[-1]


def test_non_person_topic_facts_become_specific_recall_cards_not_topic_riddles():
    cards = _cards(
        [
            (1, "THE WATER CYCLE"),
            (1, "• The Sun warms water in oceans, lakes and rivers."),
            (1, "• Some liquid water changes into water vapour and rises."),
            (1, "• This change is evaporation."),
            (1, "• Plants also release water vapour from their leaves."),
            (1, "• As moist air rises, it cools."),
            (1, "• Rain, snow and hail are forms of precipitation."),
            (1, "• Some rainwater flows over land."),
        ]
    )

    assert all(card.question != "What is this about?" for card in cards)
    assert all(card.answer != "THE WATER CYCLE" for card in cards)
    assert any(card.clue == "Some liquid water changes into water vapour and rises." and card.answer == "evaporation" for card in cards)
    learning = {card.question: card.answer for card in cards if card.kind == "learn"}
    assert learning["Imagine a puddle in sunshine. What happens to its water?"] == (
        "Heat from the Sun changes liquid water into water vapour."
    )
    assert any(
        card.kind == "learn" and card.question == "How do plants add water vapour to the water cycle?"
        for card in cards
    )
    assert any(card.kind == "recall" and card.answer == "As moist air rises, it cools." for card in cards)
    assert any(
        card.kind == "learn" and card.answer == "The sheet names rain, snow and hail as forms of precipitation."
        for card in cards
    )


def test_named_process_cards_keep_the_explanation_with_the_name():
    rows = [
        (1, "Water moves continuously between Earth's surface and atmosphere."),
        (1, "This movement is called the water cycle."),
        (1, "Some liquid water changes into water vapour and rises."),
        (1, "This change is evaporation."),
        (1, "Plants also release water vapour from their leaves."),
        (1, "This process is called transpiration."),
        (1, "Water vapour changes into tiny liquid droplets around small particles in the air."),
        (1, "This change is condensation."),
        (1, "The Sun warms water in oceans, lakes and rivers."),
        (1, "As moist air rises, it cools."),
        (1, "Rain, snow and hail are forms of precipitation."),
        (1, "Some rainwater flows over land."),
        (1, "Rivers carry water back towards the oceans."),
    ]

    cards = _cards(rows)
    process_cards = [card for card in cards if card.answer in {"water cycle", "evaporation", "transpiration", "condensation"}]
    assert [(card.clue, card.answer) for card in process_cards] == [
        ("Water moves continuously between Earth's surface and atmosphere.", "water cycle"),
        ("Some liquid water changes into water vapour and rises.", "evaporation"),
        ("Plants also release water vapour from their leaves.", "transpiration"),
        ("Water vapour changes into tiny liquid droplets around small particles in the air.", "condensation"),
    ]
    assert all("What is this" in card.question for card in process_cards)


def test_water_cycle_cards_prompt_prediction_cause_and_connection():
    cards = _cards(
        [
            (1, "THE WATER CYCLE"),
            (1, "• The Sun warms water in oceans, lakes and rivers."),
            (1, "• Some liquid water changes into water vapour and rises."),
            (1, "• This change is evaporation."),
            (1, "• As moist air rises, it cools."),
            (1, "• Water vapour cools and forms tiny droplets in clouds."),
            (1, "• Rain, snow and hail are forms of precipitation."),
            (1, "• Some rainwater flows over land."),
            (1, "• Rivers carry water back towards the oceans."),
        ]
    )
    learning = [card for card in cards if card.kind == "learn"]

    assert [card.question for card in learning] == [
        "Imagine a puddle in sunshine. What happens to its water?",
            "Why do tiny water droplets form as moist air rises and cools?",
        "What can fall from clouds as precipitation? Name the forms in your sheet.",
        "After rain falls on land, where can the water go next?",
    ]
    assert learning[0].answer == "Heat from the Sun changes liquid water into water vapour."
    assert "tiny droplets" in learning[1].answer
    assert learning[2].answer == "The sheet names rain, snow and hail as forms of precipitation."
    assert learning[3].answer == "Rainwater flows over land, and rivers carry water back towards the oceans."


def test_source_supported_water_cycle_printout_adds_a_diagram_page():
    cards = _cards(
        [
            (1, "Water moves continuously between Earth's surface and atmosphere."),
            (1, "This movement is called the water cycle."),
            (1, "Some liquid water changes into water vapour and rises."),
            (1, "This change is evaporation."),
            (1, "The Sun warms water in oceans, lakes and rivers."),
            (1, "As moist air rises, it cools."),
            (1, "Water vapour changes into tiny liquid droplets around particles in the air."),
            (1, "This change is condensation."),
            (1, "Rain, snow and hail are forms of precipitation."),
            (1, "Some rainwater flows over land."),
            (1, "Rivers carry water back towards the oceans."),
        ]
    )

    pages = _page_texts(render_cards_pdf(cards))

    assert "HOW WATER CIRCULATES" in pages[-1]
    assert "EVAPORATION" in pages[-1]
    assert "CONDENSATION" in pages[-1]
    assert "PRECIPITATION" in pages[-1]
    assert "COLLECTION" in pages[-1]


def test_four_weak_water_cycle_cards_become_explain_and_connect_prompts():
    cards = _cards(
        [
            (1, "Water moves continuously between Earth's surface and atmosphere."),
            (1, "This movement is called the water cycle."),
            (1, "Some liquid water changes into water vapour and rises."),
            (1, "This change is evaporation."),
            (1, "The Sun warms water in oceans, lakes and rivers."),
            (1, "As moist air rises, it cools."),
            (1, "Water vapour changes into tiny liquid droplets around particles in the air."),
            (1, "This change is condensation."),
            (1, "Rain, snow and hail are forms of precipitation."),
            (1, "Some rainwater flows over land."),
            (1, "Rivers carry water back towards the oceans."),
        ]
    )

    assert cards[2].question == "Imagine a puddle in sunshine. What happens to its water?"
    assert cards[3].question == "Why do tiny water droplets form as moist air rises and cools?"
    assert cards[5].question == "What can fall from clouds as precipitation? Name the forms in your sheet."
    assert cards[6].question == "After rain falls on land, where can the water go next?"
    assert "tiny liquid droplets" in cards[3].answer
    assert "carry water back" in cards[6].answer
    pages = _page_texts(render_cards_pdf(cards))
    assert pages[1].startswith("FILL IN THE BLANKS")
    assert "This movement is called ________________." in pages[1]
    assert "forms of ________________." in pages[1]
    assert pages[2].startswith("ANSWER SHEET")
    assert "FILL-IN-THE-BLANK ANSWERS" in pages[2]


def test_abstract_topic_titles_and_unreadable_process_lines_are_not_printed_as_cards():
    cards = _cards(
        [
            (1, "Evaporation, Condensation and Rainfall"),
            (1, "• A simple model is: heating ? evaporation ? cooling ? condensation ? precipitation."),
        ]
    )

    assert cards == []


def test_uk_sheet_cards_drop_list_numbers_titles_footers_and_table_fragments():
    cards = _cards(UK_SHEET)
    shown = [text for card in cards for text in (card.clue, card.answer, card.about)]

    assert not any(text.strip() in {"1.", "2.", "3.", "A.", "B."} for text in shown)
    assert not any("Grade 8 Social Studies" in text or "QUICK REVISION" in text for text in shown)
    assert not any("COMPARATIVE TABLE" in text or "2nd on Ireland island" in text for text in shown)
    assert not any("?" in card.clue and not card.clue.rstrip().endswith("?") for card in cards)
    riddles = {card.clue: card.answer for card in cards if card.kind == "riddle"}
    assert riddles["Metropolitan area covers much of southeastern England."] == "LONDON"
    assert riddles["Major city of the West Midlands, lying on the River Rea."] == "BIRMINGHAM"
    names = {card.answer: card.clue for card in cards if card.kind == "name"}
    assert names["LONDON"] == "______ – Capital of the United Kingdom & England"
    gaps = {card.answer: card for card in cards if card.kind == "gap"}
    assert gaps["18th"].question == "Which century fits the gap?" and gaps["18th"].about == "BIRMINGHAM"
    assert "______ visitors" in gaps["520,000"].clue
    assert any(card.kind == "summary" and card.answer == "Belfast" for card in cards)


def test_uk_sheet_practice_questions_take_their_answers_from_the_answer_key():
    questions = {card.clue: card for card in _cards(UK_SHEET) if card.kind == "question"}

    tidal = questions["London is situated on the tidal ______ in southeastern England."]
    assert tidal.question == "Fill the gap." and tidal.answer == "River Thames"
    assert questions["Birmingham is a major city of the ______, England."].answer == "West Midlands"
    assert (
        questions["Name the capital city of Northern Ireland."].answer
        == "Belfast is the capital city of Northern Ireland."
    )
    assert questions["Which river flows through Birmingham?"].answer == "The River Rea flows through Birmingham."
    assert "ANSWER KEY" not in questions and "River Thames" not in questions


def test_flagged_claims_stay_on_the_card_with_a_plain_note_for_the_adult():
    cards = _cards(UK_SHEET)
    largest = next(card for card in cards if "most populous British city" in card.clue)

    assert largest.answer == "BIRMINGHAM"
    assert largest.checks and "“largest”" in largest.checks[0] and "“most populous”" in largest.checks[0]
    assert all("verify_" not in check for card in cards for check in card.checks)


def test_standards_ask_the_same_question_in_their_own_words():
    rows = [(1, "1. LONDON – Capital of the United Kingdom & England"), (1, "• It grew quickly after 1850.")]

    questions = {standard: [card.question for card in _cards(rows, standard)] for standard in (7, 8, 9)}

    assert questions[7] == ["What is it?", "Which year goes in the gap?"]
    assert questions[8] == ["What is it?", "Which year fits the gap?"]
    assert questions[9] == ["Identify it.", "Supply the missing year."]


def test_printable_cards_reject_empty_inventory_and_shrink_rather_than_fail_on_long_text():
    with pytest.raises(ValueError, match="No source facts"):
        render_printable_cards_pdf(extract_facts([]))

    statement = "Rivers carry water to the sea " * 40 + "in the end."
    pdf_bytes = render_printable_cards_pdf(extract_facts([SourceUnit("SRC-P1-U1", 1, statement, "text")]))

    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    card = pymupdf.Rect(_LEFT, _TOP, _LEFT + _CARD_WIDTH, _TOP + _CARD_HEIGHT)
    words = [pymupdf.Rect(word[:4]) for word in document[0].get_text("words") if word[1] > _TOP]
    assert words and all(card.contains(word) for word in words)  # the clue shrinks and stops inside its card
    assert "in the end." in document[-1].get_text()


def test_printable_cards_reject_a_learn_generated_pdf():
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Generated cards")
    document.set_metadata({"title": "Learn ICSE Standard 8 Detective game", "author": "Learn Teaching Engine"})
    source_pdf = document.tobytes()
    document.close()

    with pytest.raises(ValueError, match="already a Learn-generated PDF"):
        render_printable_cards_pdf(extract_facts([]), source_pdf)


def test_detective_and_superhero_games_print_picture_cards_named_by_the_sheet():
    source_pdf = (SAMPLES / "people-sheet.pdf").read_bytes()
    inventory = extract_facts(extract(source_pdf).units)

    detective = _page_texts(render_printable_cards_pdf(inventory, source_pdf, "detective", {1}, 8))
    superhero = _page_texts(render_printable_cards_pdf(inventory, source_pdf, "superhero", {1}, 7))
    pictures = [card for card in plan_cards(read_sheet(inventory, source_pdf)) if card.kind == "picture"]

    assert len(extract_source_visuals(source_pdf, pages={1})) == 3
    assert [card.answer for card in pictures] == ["RAJA RAM MOHAN ROY", "ISHWAR CHANDRA VIDYASAGAR", "JYOTIRAO PHULE"]
    assert all(card.question == "Who is this?" and card.image for card in pictures)
    assert detective[0].startswith("DETECTIVE CASE FILE")
    assert superhero[0].startswith("SUPERHERO POWER-UP GAME")
    assert "Picture from your sheet" in " ".join(detective)
    assert "ICSE STANDARD" not in " ".join(superhero)


@pytest.mark.parametrize("filename", ["civics-sheet.pdf", "industries-sheet.pdf"])
def test_card_layout_fits_long_source_rows_and_comparison_tables(filename):
    source_pdf = (SAMPLES / filename).read_bytes()
    ocr, ocr_name = choose_ocr("auto")
    source = extract(source_pdf, ocr, ocr_name)

    pdf_bytes = render_printable_cards_pdf(extract_facts(source.units), source_pdf)

    document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert pdf_bytes.startswith(b"%PDF")
    assert document.page_count >= 2
    assert "ANSWER SHEET" in document[-1].get_text()
    for page in document:  # every printed word stays inside the page
        for x0, y0, x1, y1, *_ in page.get_text("words"):
            assert 0 <= x0 and x1 <= page.rect.width and 0 <= y0 and y1 <= page.rect.height


def test_class_grade_and_page_numbers_never_become_answers():
    rows = [
        (2, "Class 8 Geography | Industries sample Page 2 COMPARATIVE TABLE Feature Cotton Textile Industry"),
        (2, "Grade 8 pupils read about 12 cities in 2019."),
    ]

    assert [card.answer for card in _cards(rows)] == ["2019"]


def test_a_numbered_question_stays_whole_and_is_not_turned_into_a_gap():
    for statement in (
        "Question 7: Which city is the capital of the UK?",
        "Question 7 ?Although plants produce carbon dioxide.? What does this tell you about the two processes?",
    ):
        cards = _cards([(3, statement)])

        assert len(cards) == 1 and cards[0].kind == "question"
        assert GAP not in cards[0].clue
        assert cards[0].clue.endswith("?")


def test_question_numbers_run_into_the_text_still_start_their_question():
    rows = [
        (1, "Question 2 Describe how carbon gets into glucose."),
        (1, "• Carbon dioxide is used to make glucose in the leaves."),
        (1, "Word equation: carbon dioxide + water → glucose Question 3 Explain why plants are a carbon sink."),
        (1, "• Plants take in more carbon dioxide than they give out."),
    ]

    questions = {card.clue: card.answer for card in _cards(rows) if card.kind == "question"}

    assert questions == {
        "Describe how carbon gets into glucose.": "• Carbon dioxide is used to make glucose in the leaves.",
        "Explain why plants are a carbon sink.": "• Plants take in more carbon dioxide than they give out.",
    }


def test_finish_cards_cut_before_a_phrase_and_never_inside_brackets():
    cards = _cards(
        [
            (1, "Dead animals are decomposed by bacteria and fungi in the soil."),
            (1, "Respiration continues (plants need energy all the time)."),
            (1, "Plants are still a useful sink because photosynthesis is faster than respiration."),
        ]
    )

    assert [(card.clue, card.answer) for card in cards] == [
        ("Dead animals are decomposed …", "… by bacteria and fungi in the soil."),
        ("Plants are still a useful sink because …", "… photosynthesis is faster than respiration."),
    ]


def test_printing_keeps_formula_symbols_without_changing_the_source_fact():
    statement = "Photosynthesis: CO₂ + H₂O → glucose + O₂"
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, statement, "text")])

    pages = _page_texts(render_printable_cards_pdf(inventory))

    assert inventory.facts[0].statement == statement
    formula = "Photosynthesis: CO₂ + H₂O → ______" if _HAS_EXTENDED_PDF_FONT else "Photosynthesis: CO2 + H2O -> ______"
    assert formula in pages[0]
    product = "glucose + O₂" if _HAS_EXTENDED_PDF_FONT else "glucose + O2"
    assert product in pages[-1]
    assert "CO?" not in pages[0] and "H?O" not in pages[0]


@pytest.mark.parametrize("game_mode", ["detective", "superhero"])
def test_typed_bullets_never_print_as_question_marks(game_mode):
    statement = (
        "• Key role in the Industrial Revolution; global industrial centre until the latter half of the 20th century."
    )
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, statement, "text")])

    pages = _page_texts(render_printable_cards_pdf(inventory, game_mode=game_mode))

    assert "Key role in the Industrial Revolution" in pages[0]
    assert "the latter half of the ______ century." in pages[0]
    assert "•" not in pages[0] and "? Key role" not in pages[0]
    assert "20th" in pages[-1]


def test_many_cards_render_quickly():
    statements = [f"The river number {n} reaches the sea after {n + 10} km of flowing." for n in range(150)]
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, " ".join(statements), "text")])

    started = perf_counter()
    pdf_bytes = render_printable_cards_pdf(inventory)
    elapsed = perf_counter() - started

    assert pymupdf.open(stream=pdf_bytes, filetype="pdf").page_count >= 20
    assert elapsed < 20, f"rendering took {elapsed:.1f} s"


def test_long_lesson_pdf_renders_without_host_timeout():
    sentence = "The river Ganga flows to the Bay of Bengal. Farmers grow rice in the fertile delta. "
    units = [SourceUnit(id=f"unit-{number}", page=number, text=sentence * 12, method="text") for number in range(1, 41)]
    lesson = create_teaching_lesson(extract_facts(units))

    started = perf_counter()
    pdf_bytes = render_teaching_pdf(lesson)
    elapsed = perf_counter() - started

    assert pymupdf.open(stream=pdf_bytes, filetype="pdf").page_count > 100
    assert elapsed < 20, f"rendering took {elapsed:.1f} s"


def test_without_the_font_package_cards_fall_back_to_safe_ascii_symbols(monkeypatch):
    monkeypatch.setitem(sys.modules, "pymupdf_fonts", None)  # import pymupdf_fonts now raises ImportError
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, "Grass → Grasshopper → Frog → Snake", "text")])

    pages = _page_texts(render_printable_cards_pdf(inventory))

    assert "Grass -> Grasshopper -> ______ -> Snake" in pages[0]
    assert "Frog" in pages[-1]
