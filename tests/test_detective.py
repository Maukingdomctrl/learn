"""The Detective case file: card sheets that cover the whole sheet, varied cards, and a checked mystery.

These tests check structure (which lines reach which card, the order of the cards, the Big Clues), not whether the
game teaches well: no child has played it yet.
"""

from dataclasses import replace
from pathlib import Path

import pymupdf
import pytest

from learn.extraction import extract
from learn.teaching_engine import extract_facts, render_printable_case_file_pdf
from learn.teaching_engine.__main__ import main
from learn.teaching_engine.detective import (
    MAX_FILLS,
    SHEET_CARDS,
    STAGE,
    check_case_file,
    plan_case_file,
    render_case_file_pdf,
)
from learn.teaching_engine.sheet import read_sheet

SHEETS = Path(__file__).parent / "sheets"
SAMPLES = Path(__file__).parents[1] / "cards" / "sample"
UK = SHEETS / "uk-cities-comparative-table.pdf"


def _plan(path: Path):
    data = path.read_bytes()
    return plan_case_file(read_sheet(extract_facts(extract(data).units), data))


@pytest.fixture(scope="module")
def uk():
    return _plan(UK)


def _with_card(case_file, case: int, sheet: int, position: int, card):
    """The case file with one card replaced (or removed, when card is None)."""
    cases = list(case_file.cases)
    sheets = list(cases[case].sheets)
    cards = list(sheets[sheet].cards)
    if card is None:
        del cards[position]
    else:
        cards[position] = card
    sheets[sheet] = replace(sheets[sheet], cards=tuple(cards))
    cases[case] = replace(cases[case], sheets=tuple(sheets))
    return replace(case_file, cases=tuple(cases))


def _with_clue(case_file, case: int, sheet: int, clue):
    cases = list(case_file.cases)
    sheets = list(cases[case].sheets)
    sheets[sheet] = replace(sheets[sheet], clue=clue)
    cases[case] = replace(cases[case], sheets=tuple(sheets))
    return replace(case_file, cases=tuple(cases))


def test_uk_cities_make_two_cases_of_two_full_varied_sheets(uk):
    assert check_case_file(uk) == []
    assert [len(case.sheets) for case in uk.cases] == [2, 2]
    first = uk.cases[0]
    assert first.suspects[:2] == ("London", "Birmingham")
    covered_first = {uk.facts[f].suspect for card in first.sheets[0].cards for f in card.covers}
    assert covered_first == {"London", "Birmingham"}  # sheet 1 is London and Birmingham, as in the trial game
    for case in uk.cases:
        for case_sheet in case.sheets:
            kinds = [card.kind for card in case_sheet.cards]
            assert len(kinds) == SHEET_CARDS and kinds[-1] == "notes"
            assert kinds.count("fill") <= MAX_FILLS
            assert all(a != b for a, b in zip(kinds, kinds[1:], strict=False))
            assert [STAGE[kind] for kind in kinds] == sorted(STAGE[kind] for kind in kinds)
            assert len(set(kinds)) >= 5


def test_every_line_of_the_sheet_is_on_a_card(uk):
    covered = {fact for case in uk.cases for sheet in case.sheets for card in sheet.cards for fact in card.covers}
    assert covered == set(uk.facts)
    texts = {fact.text for fact in uk.facts.values()}
    assert "Situated on the River Thames in southeastern England." in texts
    assert "Home to the Wales Millennium Centre – a thriving creative capital with rich cultural heritage." in texts


def test_cards_hide_the_answer_and_keep_the_sheets_words(uk):
    cards = [card for case in uk.cases for sheet in case.sheets for card in sheet.cards]
    for card in cards:
        if card.kind == "who":
            assert all(card.answer[0] not in line for line in card.lines)
    timeline = next(card for card in cards if card.kind == "timeline" and card.about == "Cardiff")
    assert timeline.answer == (
        "1. Was a small town until the early 19th century",
        "2. Made a city in 1905",
        "3. proclaimed capital of Wales in 1955",
    )
    picks = [card for card in cards if card.kind == "pick"]
    assert picks and all(card.answer[0].split(":")[0] in card.lines[1] for card in picks)


def test_the_culprit_is_on_the_last_sheet_and_the_big_clues_hide_its_name(uk):
    for case in uk.cases:
        assert case.culprit in case.suspects
        last = {uk.facts[f].suspect for card in case.sheets[-1].cards for f in card.covers}
        assert case.culprit in last
        for case_sheet in case.sheets:
            assert uk.facts[case_sheet.clue.fact].suspect == case.culprit
            assert case.culprit not in case_sheet.clue.text
        assert len({sheet.clue.fact for sheet in case.sheets}) == len(case.sheets)


@pytest.mark.parametrize(
    "path",
    [*sorted(SAMPLES.glob("*.pdf")), *sorted(SHEETS.glob("mumbai-*.pdf")), UK],
    ids=lambda path: path.name,
)
def test_a_topic_sheet_makes_a_checked_case_file_or_a_plain_refusal(path):
    try:
        case_file = _plan(path)
    except ValueError as error:
        assert "study cards" in str(error)
        return
    assert check_case_file(case_file) == []


def test_a_sheet_without_topics_is_refused_with_a_reason():
    with pytest.raises(ValueError, match="at least two topics"):
        _plan(SHEETS / "equations.pdf")


# Targeted mutations: each breaks one rule and must be caught.


def test_check_catches_a_line_on_no_card(uk):
    sheet = uk.cases[0].sheets[0]
    position, card = next(
        (index, card)
        for index, card in enumerate(sheet.cards)
        if any(
            all(fact not in other.covers for c in uk.cases for s in c.sheets for other in s.cards if other is not card)
            for fact in card.covers
        )
    )
    problems = check_case_file(_with_card(uk, 0, 0, position, None))
    assert any(problem.startswith("Rule A") for problem in problems)
    assert any(f"{SHEET_CARDS - 1} cards" in problem for problem in problems)


def test_check_catches_too_many_fills_and_repeats(uk):
    sheet = uk.cases[0].sheets[0]
    fill = next(card for case in uk.cases for s in case.sheets for card in s.cards if card.kind == "fill")
    mutated = uk
    for position in range(1, 1 + MAX_FILLS + 1):
        mutated = _with_card(mutated, 0, 0, position, replace(fill, covers=sheet.cards[position].covers))
    problems = check_case_file(mutated)
    assert any("fill-the-gap cards" in problem for problem in problems)
    assert any("in a row" in problem for problem in problems)


def test_check_catches_cards_out_of_order_and_notes_not_last(uk):
    cards = list(uk.cases[0].sheets[0].cards)
    mutated = _with_card(_with_card(uk, 0, 0, 0, cards[-1]), 0, 0, len(cards) - 1, cards[0])
    problems = check_case_file(mutated)
    assert any("easier than the card before it" in problem for problem in problems)
    assert any("not CASE NOTES" in problem for problem in problems)


def test_check_catches_words_not_on_the_sheet(uk):
    position, card = next((index, card) for index, card in enumerate(uk.cases[0].sheets[0].cards) if card.kind == "who")
    changed = replace(card, lines=(*card.lines[:-1], "Clue 3: Home to the tallest tower in the world."))
    problems = check_case_file(_with_card(uk, 0, 0, position, changed))
    assert any("is not the sheet's own words" in problem for problem in problems)


def test_check_catches_a_big_clue_about_someone_else_or_naming_the_culprit(uk):
    case = uk.cases[0]
    other = next(fact for fact in uk.facts.values() if fact.suspect != case.culprit and not fact.heading)
    wrong = replace(case.sheets[0].clue, fact=other.id, text=other.text)
    assert any("not about the culprit" in p for p in check_case_file(_with_clue(uk, 0, 0, wrong)))
    named = replace(case.sheets[0].clue, text=uk.facts[case.sheets[0].clue.fact].text.replace("________", "Belfast"))
    named = replace(named, text=f"{case.culprit}: {uk.facts[named.fact].text}")
    problems = check_case_file(_with_clue(uk, 0, 0, named))
    assert any("names the culprit" in p or "not the sheet's own words" in p for p in problems)
    again = replace(case.sheets[1].clue, fact=case.sheets[0].clue.fact, text=case.sheets[0].clue.text)
    assert any("used twice" in p for p in check_case_file(_with_clue(uk, 0, 1, again)))


def test_check_catches_a_culprit_found_before_the_last_sheet(uk):
    case = uk.cases[0]
    first_sheet_only = next(
        name
        for name in case.suspects
        if name not in {uk.facts[f].suspect for card in case.sheets[-1].cards for f in card.covers}
    )
    mutated = replace(uk, cases=(replace(case, culprit=first_sheet_only), *uk.cases[1:]))
    assert any("found too soon" in problem for problem in check_case_file(mutated))


def test_a_case_file_that_fails_its_checks_is_never_printed(uk):
    broken = _with_card(uk, 0, 0, 0, None)
    with pytest.raises(ValueError, match="failed its checks"):
        render_case_file_pdf(broken)


# Printing


def test_the_pdf_prints_boards_one_sided_card_sheets_then_the_answers(uk):
    data = UK.read_bytes()
    pdf = render_printable_case_file_pdf(extract_facts(extract(data).units), data)
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        texts = [page.get_text() for page in document]
        sizes = {(round(page.rect.width), round(page.rect.height)) for page in document}
    assert sizes == {(595, 842)}
    sheets = sum(len(case.sheets) for case in uk.cases)
    boards = [i for i, text in enumerate(texts) if "WHO IS THE HIDDEN SUSPECT?" in text]
    card_pages = [i for i, text in enumerate(texts) if "CARD 1 OF 8" in text]
    answers = [i for i, text in enumerate(texts) if "CASE CLOSED: ANSWERS FOR THE PARENT" in text]
    assert len(boards) == len(uk.cases) and len(card_pages) == sheets
    assert answers and min(answers) > max(card_pages + boards)  # answers come last
    assert len(texts) == len(boards) + len(card_pages) + len(answers)  # nothing printed on a back
    for index in card_pages:
        assert "CARD 8 OF 8" in texts[index] and "CASE NOTES" in texts[index]
    student = " ".join(texts[i] for i in boards + card_pages)
    assert "THE HIDDEN SUSPECT:" not in student and "read this out" not in student  # the answers stay apart
    card_lines = [line for i in card_pages for line in texts[i].splitlines()]
    assert not [line for line in card_lines if line.startswith("?")]  # no symbol the font lacks


def test_command_line_prints_a_case_file_or_explains_why_not(tmp_path, capsys):
    out = tmp_path / "case.pdf"
    assert main([str(UK), "--out", str(tmp_path / "plan.json"), "--case-file", str(out)]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    refused = tmp_path / "none.pdf"
    assert main([str(SHEETS / "equations.pdf"), "--out", str(tmp_path / "p.json"), "--case-file", str(refused)]) == 2
    assert not refused.exists() and "No Detective case file" in capsys.readouterr().out
