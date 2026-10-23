"""Detective Mode case papers, against a scripted fake model (no key, no network, no credits).

These tests check that each card's answer is printed in the lines it cites, that every line is taught, that the
language rules hold, that an upload is one model request and that broken cards fall back to plain cards. They say
nothing about how well a real model writes: the evidence sentences are the model's own words.
"""

import re
from pathlib import Path

import pymupdf
import pytest
from conftest import ScriptedLLM

from learn.extraction import extract
from learn.llm import LLMError
from learn.teaching_engine import extract_facts
from learn.teaching_engine.ai_cards import study_lines
from learn.teaching_engine.detective import Fact
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
            "Rohan opens a map of the country. One city has a red star. It leads the whole country.",
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
    papers = write_case_papers(uk_sheet, llm)
    assert len(llm.calls) == 1 and papers.model_cards == 8 and papers.title == "The Case of the Two Big Cities"
    first = papers.sheets[0]
    assert [c.answer for c in first][:2] == ["London", "River Thames"] and all(c.by_model for c in first)
    assert all(len(sheet) <= CARDS_PER_SHEET for sheet in papers.sheets)
    taught = {line for sheet in papers.sheets for c in sheet for line in c.lines}
    assert {f"F{n}" for n in range(1, 10)} <= taught  # every line of the model's sheet is on a card
    left_out = len(set(papers.facts) - taught)
    assert not left_out or any(f"{left_out} of {len(papers.facts)} lines" in note for note in papers.notes)
    pdf = render_case_papers_pdf(papers)
    with pymupdf.open(stream=pdf, filetype="pdf") as document:
        texts = [page.get_text() for page in document]
    assert len(texts) == 2 * len(papers.sheets)  # each sheet's cards, then its key
    assert "Which river flows through this city?" in texts[0] and "River Thames" not in texts[0]
    assert "SHEET 1 OF" in texts[1] and "River Thames" in texts[1] and "Sheet says: p. 1" in texts[1]
    assert "CASE CLOSED" in texts[-1]


def test_one_request_carries_every_line_of_the_upload(uk_sheet, facts):
    llm = ScriptedLLM({TASK: [GOOD, {}]})
    write_case_papers(uk_sheet, llm)
    assert len(facts) > 9 and len(llm.calls) == 1  # more lines than one printed sheet, still one request
    prompt = llm.calls[0][1]
    assert all(f"\n{line} [" in prompt for line in facts)
    assert f"one card for each of these {len(facts)}" in prompt


@pytest.mark.parametrize(
    "change, message",
    [
        ({"answer": "Paris"}, "not printed in its lines"),
        ({"evidence": "Boats float on the River Thames. It is wide."}, "appears on the card front"),
        ({"answer": "the river thames"}, "1-2 words"),
        ({"question": "Which river flows through this city"}, "must end with"),
        ({"lines": ["F40"]}, "ids of lines on this sheet"),
        ({"evidence": "Boats float past Big Ben. The wide water runs through the big city."}, "names Big, Ben are not"),
        (
            {"evidence": "Boats float past a clock tower built in 1859. The water runs through the city."},
            "numbers 1859",
        ),
    ],
)
def test_each_broken_rule_is_named(facts, change, message):
    broken = {**GOOD["cards"][1], **change}
    allowed = [f"F{n}" for n in range(1, 13)]
    assert any(message in problem for problem in check_card(broken, facts, allowed))
    assert check_card(GOOD["cards"][1], facts, allowed) == []


def test_a_set_that_misses_lines_keeps_its_good_cards_and_is_not_sent_back(uk_sheet):
    partial = {"cards": GOOD["cards"][:3]}
    llm = ScriptedLLM({TASK: [partial, {}]})
    papers = write_case_papers(uk_sheet, llm)
    assert len(llm.calls) == 1
    assert any("broke a rule, so plain cards teach them" in note for note in papers.notes)
    first = papers.sheets[0]
    assert [c.answer for c in first if c.by_model] == ["London", "River Thames", "Southeastern England"]
    assert papers.model_cards == 3 and not all(c.by_model for c in first)
    taught = {line for sheet in papers.sheets for c in sheet for line in c.lines}
    assert {"F1", "F2", "F4"} <= taught  # the model's three good cards
    assert all(c.question != "Answer it." and not c.evidence.endswith("…") for s in papers.sheets for c in s)
    assert render_case_papers_pdf(papers).startswith(b"%PDF")


def test_a_set_with_no_good_card_falls_back_to_plain_cards(uk_sheet):
    broken = {"cards": [{**c, "answer": "Paris"} for c in GOOD["cards"]]}
    papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [broken, {}]}))
    assert papers.model_cards == 0
    assert not any(c.by_model for sheet in papers.sheets for c in sheet)


def test_extra_and_repeated_cards_are_dropped_without_a_second_call(uk_sheet):
    extra = {**GOOD, "cards": [*GOOD["cards"], GOOD["cards"][1], {**GOOD["cards"][0], "title": "Ninth"}]}
    llm = ScriptedLLM({TASK: [extra, {}]})
    papers = write_case_papers(uk_sheet, llm)
    assert len(llm.calls) == 1 and papers.model_cards == len(GOOD["cards"])
    assert [c.answer for c in papers.sheets[0]] == [c["answer"] for c in GOOD["cards"]]


def test_one_bad_card_is_dropped_and_the_others_are_kept(uk_sheet):
    leaky = {**GOOD["cards"][4], "evidence": "Children far away love popular culture from this city."}
    reply = {**GOOD, "cards": [*GOOD["cards"][:4], leaky, *GOOD["cards"][5:]]}
    llm = ScriptedLLM({TASK: [reply, {}]})
    papers = write_case_papers(uk_sheet, llm)
    assert len(llm.calls) == 1  # F6 was taught only by the leaky card, and nothing is sent back
    cards = [c for sheet in papers.sheets for c in sheet]
    assert papers.model_cards == 7
    assert not any("popular culture" in c.evidence for c in cards)  # the leaky card never prints


def test_without_a_model_every_line_still_gets_a_plain_card(uk_sheet):
    class Down:
        def json(self, task, system, prompt):
            raise LLMError("Claude API credentials are not configured (set JUNE_API_KEY).")

    papers = write_case_papers(uk_sheet, Down())
    assert papers.model_cards == 0 and any("JUNE_API_KEY" in note for note in papers.notes)
    assert all(1 <= len(sheet) <= CARDS_PER_SHEET for sheet in papers.sheets)
    assert render_case_papers_pdf(write_case_papers(uk_sheet)).startswith(b"%PDF")


def test_a_card_may_not_bundle_many_lines(uk_sheet):
    bundled = {"cards": [{**GOOD["cards"][0], "lines": ["F1", "F3", "F4"]}, *GOOD["cards"][1:2], *GOOD["cards"][3:]]}
    llm = ScriptedLLM({TASK: [bundled, {}]})
    papers = write_case_papers(uk_sheet, llm)
    assert len(llm.calls) == 1 and any("teaches 3 lines; one concept per card" in p for p in papers.problems)
    assert not any(c.by_model and len(c.lines) > 2 for sheet in papers.sheets for c in sheet)


@pytest.mark.parametrize(
    "name, expected",
    [
        ("full-history-timeline.pdf", 15),  # a timeline and two grids: one line per row
        ("comparison-panels.pdf", 9),  # two panels side by side: one line per bullet
        ("full-physics-forces.pdf", 12),
    ],
)
def test_tables_become_lines_so_their_facts_get_cards(name, expected):
    data = (UK.parent / name).read_bytes()
    lines, _ = study_lines(read_sheet(extract_facts(extract(data).units), data))
    assert len(lines) == expected
    papers = write_case_papers(read_sheet(extract_facts(extract(data).units), data))
    taught = {line for sheet in papers.sheets for c in sheet for line in c.lines}
    answers = [c.answer for sheet in papers.sheets for c in sheet]
    assert len(answers) == len(set(answers))  # plain cards: no answer twice
    assert all(c.question != "Answer it." and not c.evidence.endswith("…") for s in papers.sheets for c in s)
    left_out = len(lines) - len(taught)
    assert not left_out or any(f"{left_out} of {len(lines)} lines" in note for note in papers.notes)


def test_scene_names_and_sheet_facts_are_allowed(facts):
    allowed = [f"F{n}" for n in range(1, 10)]
    scene = {**GOOD["cards"][1], "evidence": "Asha watches boats in southeastern England. The water runs past London."}
    assert check_card(scene, facts, allowed) == []
    owned = {**scene, "evidence": "Boats pass Asha’s school. The water runs past London's tall towers."}
    assert check_card(owned, facts, allowed) == []  # a scene name or a sheet name with "'s" is still that name
    outside = {**scene, "evidence": "Boats pass Shakespeare's theatre. The water runs past London's tall towers."}
    assert any("names Shakespeare are not" in problem for problem in check_card(outside, facts, allowed))


def test_the_prompts_own_examples_keep_the_card_rules():
    from learn.teaching_engine.evidence_cards import SYSTEM

    water = {
        "F1": Fact("F1", "Water", "Water vapour in the air turns into drops on a cold surface.", 1),
        "F2": Fact("F2", "Water", "Evaporation dries a puddle.", 1),
        "F3": Fact("F3", "Water", "The water table is the level below which the ground is soaked.", 1),
    }
    style = SYSTEM.replace("\n  ", " ")
    examples = re.findall(r'- "(.+?)"\. Evidence: "(.+?)" Question: "(.+?)" Answer: "(.+?)"\.', style)
    assert len(examples) == 3
    for line, (title, evidence, question, answer) in zip(water, examples, strict=True):
        example = card([line], title, evidence, question, answer)
        assert check_card(example, water, list(water)) == [], title


def test_why_a_sheet_fell_back_is_recorded(uk_sheet):
    partial = {"cards": GOOD["cards"][:3]}
    papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [partial, {}]}))
    assert any("taught by no card" in problem for problem in papers.problems)


SCIENCE = {
    "F1": Fact("F1", "Photosynthesis", "Plants take in CO2 and give out oxygen.", 1),
    "F2": Fact("F2", "Area", "The area of a rectangle is A = l × w.", 1),
    "F3": Fact("F3", "Congress", "The Indian National Congress first met on 28 December 1885.", 1),
}


@pytest.mark.parametrize(
    "good, bad, message",
    [
        # A formula or a date may be a longer answer, if printed; other long answers may not.
        (
            card(["F2"], "Tiles", "Asha tiles a floor.", "How do you find the area?", "A = l × w"),
            card(["F2"], "Tiles", "Asha tiles a floor.", "How do you find it?", "area of a rectangle"),
            "must be 1-2 words",
        ),
        (
            card(
                ["F3"],
                "First Meeting",
                "Riya reads an old notice.",
                "When did the Congress first meet?",
                "28 December 1885",
            ),  # fmt: skip
            card(["F3"], "First Meeting", "Riya reads an old notice.", "Who first met?", "Indian National Congress x"),
            "must be 1-2 words",
        ),
        # CO2 is read as CO2, not as the number 2; a formula the sheet does not print is still caught.
        (
            card(["F1"], "Leafy Air", "Plants in the garden take in CO2 all day.", "What do they give out?", "Oxygen"),
            card(["F1"], "Leafy Air", "Plants in the garden take in H2O all day.", "What do they give out?", "Oxygen"),
            "numbers H2O",
        ),
        # Everyday words like Earth and Sun are not outside facts; a real name not on the sheet still is.
        (
            card(
                ["F1"], "Green Kitchen", "Under the Sun, plants on Earth make food.", "What do they give out?", "Oxygen"
            ),  # fmt: skip
            card(
                ["F1"], "Green Kitchen", "Under the Sun, Mr Darwin's plants grow.", "What do they give out?", "Oxygen"
            ),  # fmt: skip
            "names Mr, Darwin",
        ),
    ],
)
def test_dates_formulas_and_everyday_words_pass_while_the_rule_still_bites(good, bad, message):
    allowed = list(SCIENCE)
    assert check_card(good, SCIENCE, allowed) == []
    assert any(message in problem for problem in check_card(bad, SCIENCE, allowed))


def test_a_busy_model_is_asked_once_and_noted_once(uk_sheet):
    class Busy:
        calls = 0

        def json(self, task, system, prompt):
            Busy.calls += 1
            raise LLMError("busy")

    papers = write_case_papers(uk_sheet, Busy())
    assert Busy.calls == 1
    busy = [note for note in papers.notes if "busy" in note]
    assert busy == ["The model could not be used (busy); plain cards are used."]
    numbers = [c.number for sheet in papers.sheets for c in sheet]
    assert numbers == list(range(1, len(numbers) + 1))


def test_only_a_long_sheet_is_split_into_requests_that_run_at_once(uk_sheet, facts):
    import threading
    import time

    class Slow:
        running = most = 0
        lock = threading.Lock()

        def __init__(self):
            self.prompts = []

        def json(self, task, system, prompt):
            with self.lock:
                Slow.running += 1
                Slow.most = max(Slow.most, Slow.running)
                self.prompts.append(prompt)
            time.sleep(0.2)
            with self.lock:
                Slow.running -= 1
            raise LLMError("busy")

    whole = Slow()
    write_case_papers(uk_sheet, whole, lines_per_request=len(facts))
    assert len(whole.prompts) == 1  # a sheet within the limit is one request
    split = Slow()
    papers = write_case_papers(uk_sheet, split, lines_per_request=len(facts) - 1)
    assert len(split.prompts) == 2 and Slow.most == 2  # two requests, with the model at the same time
    sizes = sorted(prompt.count("\nF") for prompt in split.prompts)
    assert sum(sizes) == len(facts) and sizes[1] - sizes[0] <= 1  # every line once, split evenly
    busy = [note for note in papers.notes if "busy" in note]
    assert busy == ["The model could not be used (busy); plain cards are used."]  # said once, not per request


def test_model_and_plain_cards_run_in_the_sheets_order(uk_sheet, facts):
    reply = {"cards": [GOOD["cards"][7], GOOD["cards"][1]]}  # F8 and F2, out of order
    papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [reply, {}]}))
    cards = [c for sheet in papers.sheets for c in sheet]
    order = list(facts)
    firsts = [min(order.index(line) for line in c.lines) for c in cards]
    assert papers.model_cards == 2 and not all(c.by_model for c in cards)
    assert firsts == sorted(firsts)  # plain cards sit among the model's, where their lines are on the sheet


def test_no_topic_name_is_printed_on_the_cards_or_their_sheet(uk_sheet):
    """A topic is often the answer ("Which city…?" London), so no tag, header or title names one."""
    papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [GOOD, {}]}))
    with pymupdf.open(stream=render_case_papers_pdf(papers), filetype="pdf") as document:
        front = "".join(document[0].get_text().split()).casefold()  # spaced capitals count too
    assert "london" not in front and "birmingham" not in front  # GOOD's own text names neither
    plain = write_case_papers(uk_sheet)  # no model: plain cards only
    topics = {fact.suspect.casefold() for fact in study_lines(uk_sheet)[0] if fact.suspect}
    assert not [c.title for s in plain.sheets for c in s if any(topic in c.title.casefold() for topic in topics)]


def test_a_case_title_that_names_a_topic_or_an_answer_is_not_printed(uk_sheet):
    for title in ("The Case of London Town", "The Case of the River Thames"):
        papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [{**GOOD, "case_title": title}, {}]}))
        assert papers.title == "The Case of the Study Sheet"
    papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [GOOD, {}]}))
    assert papers.title == "The Case of the Two Big Cities"


@pytest.mark.parametrize("name", ["uk-cities-comparative-table.pdf", "full-physics-forces.pdf", "mumbai-events.pdf"])
def test_every_printed_sheet_but_the_last_is_full(name):
    data = (UK.parent / name).read_bytes()
    papers = write_case_papers(read_sheet(extract_facts(extract(data).units), data))  # plain cards
    sizes = [len(sheet) for sheet in papers.sheets]
    assert all(size == CARDS_PER_SHEET for size in sizes[:-1]) and 1 <= sizes[-1] <= CARDS_PER_SHEET
    numbers = [c.number for sheet in papers.sheets for c in sheet]
    assert numbers == list(range(1, len(numbers) + 1))


@pytest.mark.parametrize(
    "plain, usable",
    [
        (
            {
                "evidence": "On ______, sepoys rose in revolt.",
                "question": "Which date fits the gap?",
                "answer": "10 May 1857",
            },
            True,
        ),  # fmt: skip
        (
            {
                "evidence": "Rani Lakshmibai led the fight at Jhansi.",
                "question": "What is this about?",
                "answer": "Rani Lakshmibai",
            },
            True,
        ),  # fmt: skip
        (
            {"evidence": "Plants act as …", "question": "Finish the sentence.", "answer": "… a larger carbon sink."},
            False,
        ),  # fmt: skip
        (
            {"evidence": "Explain why photosynthesis matters.", "question": "Answer it.", "answer": "Because it does"},
            False,
        ),  # fmt: skip
        ({"evidence": "A line.", "question": "What is it?", "answer": "a long phrase of many words"}, False),
    ],
)
def test_only_plain_cards_with_a_real_question_and_a_short_answer_are_printed(plain, usable):
    from learn.teaching_engine.evidence_cards import _usable_plain

    assert _usable_plain(plain) is usable


def test_a_question_whose_answers_are_already_points_is_not_a_line_again():
    data = (UK.parent / "carbon-cycle-answers.pdf").read_bytes()
    lines, _ = study_lines(read_sheet(extract_facts(extract(data).units), data))
    assert not any(" Answer: " in line.text for line in lines)  # its bullet points carry the answer once


def test_model_cards_may_share_an_answer_when_they_teach_different_lines(uk_sheet):
    town = card(["F10"], "Old Market Town", "Rohan reads an old map of a small market town.",
                "Which city grew from this town?", "Birmingham")  # fmt: skip
    papers = write_case_papers(uk_sheet, ScriptedLLM({TASK: [{**GOOD, "cards": [*GOOD["cards"], town]}, {}]}))
    birmingham = [c for sheet in papers.sheets for c in sheet if c.answer == "Birmingham" and c.by_model]
    assert len(birmingham) == 2  # two lines, two questions, one answer: both cards stay
