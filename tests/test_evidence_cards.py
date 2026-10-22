"""Detective Mode case papers, against a scripted fake model (no key, no network, no credits).

These tests check that each card's answer is printed in the lines it cites, that every line is taught, that the
language rules hold and that broken sets fall back to plain cards. They say nothing about how well a real model
writes: the evidence sentences are the model's own words.
"""

from pathlib import Path

import pymupdf
import pytest
from conftest import ScriptedLLM

from learn.extraction import extract
from learn.llm import LLMError
from learn.teaching_engine import extract_facts
from learn.teaching_engine.ai_cards import study_lines
from learn.teaching_engine.evidence_cards import (
    CARDS_PER_SHEET,
    TASK,
    check_card,
    render_case_papers_pdf,
    write_case_papers,
)
from learn.teaching_engine.sheet import read_sheet

UK = Path(__file__).parent / "sheets" / "uk-cities-comparative-table.pdf"


def card(lines, title, evidence, question, answer, why="It is on the sheet."):
    return {
        "lines": lines,
        "title": title,
        "evidence": evidence,
        "question": question,
        "answer": answer,
        "key_why": why,
    }


# A good set for the first sheet's 9 lines (London F1-F6, Birmingham F7-F9): one card per line, in the recipe's style.
GOOD = {
    "case_title": "The Case of the Two Big Cities",
    "cards": [
        card(
            ["F1", "F3"],
            "The Red Star on the Map",
            "Rohan opens a map of Britain. One city has a red star. It leads the whole country.",
            "Which city has the red star?",
            "London",
        ),
        card(
            ["F2"],
            "Boats by the Clock Tower",
            "Boats float past a tall clock tower. The wide water runs through the big city.",
            "Which river flows through this city?",
            "River Thames",
        ),
        card(
            ["F4"],
            "Houses Without End",
            "From a plane you see houses for miles. The city spreads over a big corner of the country.",
            "Which part of the country does it cover?",
            "Southeastern England",
        ),
        card(
            ["F5"],
            "Banks in Glass Towers",
            "Big banks in glass towers look after money for many countries. They are all on one continent.",
            "Which continent does this city serve with money?",
            "Europe",
        ),
        card(
            ["F6"],
            "Songs Heard Everywhere",
            "Children far away sing songs and watch films made in this city.",
            "What is this kind of influence called?",
            "Popular culture",
        ),
        card(
            ["F7"],
            "The Middle of the Map",
            "Put your finger in the middle of England. A big city sits there.",
            "Which region is this city in?",
            "West Midlands",
        ),
        card(
            ["F8"],
            "The Small Stream",
            "A small stream flows past busy streets in the middle of England.",
            "Which river is this?",
            "River Rea",
        ),
        card(
            ["F9"],
            "Second Biggest",
            "Only the capital has more people than this city.",
            "Which city is this?",
            "Birmingham",
        ),
    ],
}


@pytest.fixture(scope="module")
def uk_sheet():
    data = UK.read_bytes()
    return read_sheet(extract_facts(extract(data).units), data)


@pytest.fixture(scope="module")
def facts(uk_sheet):
    return {fact.id: fact for fact in study_lines(uk_sheet)[0]}


def test_a_good_set_becomes_the_first_sheet_with_its_sealed_key(uk_sheet):
    llm = ScriptedLLM({TASK: [GOOD, {}]})
    papers = write_case_papers(uk_sheet, llm, limit=1)
    assert papers.model_sheets == 1 and papers.title == "The Case of the Two Big Cities"
    first = papers.sheets[0]
    assert [c.answer for c in first][:2] == ["London", "River Thames"] and all(c.by_model for c in first)
    assert all(len(sheet) <= CARDS_PER_SHEET for sheet in papers.sheets)
    taught = {line for sheet in papers.sheets for c in sheet for line in c.lines}
    assert taught == set(papers.facts)  # every line of the sheet is on some card
    pdf = render_case_papers_pdf(papers)
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        texts = [page.get_text() for page in document]
    assert len(texts) == 2 * len(papers.sheets)  # each sheet's cards, then its key
    assert "Which river flows through this city?" in texts[0] and "River Thames" not in texts[0]
    assert "SHEET 1 OF" in texts[1] and "River Thames" in texts[1] and "Sheet says: p. 1" in texts[1]
    assert "CASE CLOSED" in texts[-1]


def test_the_model_sees_only_its_sheet_of_lines(uk_sheet):
    llm = ScriptedLLM({TASK: [GOOD, {}]})
    write_case_papers(uk_sheet, llm, limit=1)
    prompt = llm.calls[0][1]
    assert "\nF9 [Birmingham]" in prompt and "\nF10 [" not in prompt


@pytest.mark.parametrize(
    "change, message",
    [
        ({"answer": "Paris"}, "not printed in its lines"),
        ({"evidence": "Boats float on the River Thames. It is wide."}, "appears on the card front"),
        ({"answer": "the river thames"}, "1-2 words"),
        ({"question": "Which river flows through this city"}, "must end with"),
        ({"lines": ["F40"]}, "ids of lines on this sheet"),
    ],
)
def test_each_broken_rule_is_named(facts, change, message):
    broken = {**GOOD["cards"][1], **change}
    allowed = [f"F{n}" for n in range(1, 13)]
    assert any(message in problem for problem in check_card(broken, facts, allowed))
    assert check_card(GOOD["cards"][1], facts, allowed) == []


def test_a_set_that_misses_a_line_is_sent_back_then_falls_back_to_plain_cards(uk_sheet):
    partial = {"cards": GOOD["cards"][:3]}
    llm = ScriptedLLM({TASK: [partial, partial, {}]})
    papers = write_case_papers(uk_sheet, llm, limit=1)
    assert "taught by no card" in llm.calls[1][1] and "write at least 7, one per line" in llm.calls[1][1]
    assert papers.model_sheets == 0 and any("broke the rules twice" in note for note in papers.notes)
    assert not any(c.by_model for sheet in papers.sheets for c in sheet)
    assert render_case_papers_pdf(papers).startswith(b"%PDF")


def test_without_a_model_every_line_still_gets_a_plain_card(uk_sheet):
    class Down:
        def json(self, task, system, prompt):
            raise LLMError("Claude API credentials are not configured (set JUNE_API_KEY).")

    papers = write_case_papers(uk_sheet, Down())
    assert papers.model_sheets == 0 and any("JUNE_API_KEY" in note for note in papers.notes)
    assert all(1 <= len(sheet) <= CARDS_PER_SHEET for sheet in papers.sheets)
    assert render_case_papers_pdf(write_case_papers(uk_sheet)).startswith(b"%PDF")


def test_a_card_may_not_bundle_many_lines(uk_sheet):
    bundled = {"cards": [{**GOOD["cards"][0], "lines": ["F1", "F3", "F4"]}, *GOOD["cards"][1:2], *GOOD["cards"][3:]]}
    llm = ScriptedLLM({TASK: [bundled, GOOD, {}]})
    papers = write_case_papers(uk_sheet, llm, limit=1)
    assert papers.model_sheets == 1 and "teaches 3 lines; one concept per card" in llm.calls[1][1]
