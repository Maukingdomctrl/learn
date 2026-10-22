"""The model layer for Detective cards, against a scripted fake model (no key, no network, no credits).

These tests show that model choices become the same printed cards as the rule-based ones, that anything not made of
the sheet's own words is refused, and that every failure falls back to the rule-based cards. They say nothing about
how good a real model's choices are.
"""

from pathlib import Path

import pytest
from conftest import ScriptedLLM

from learn import config as C
from learn.extraction import extract
from learn.llm import JUNE_KEY_FROM_NETWORK, AnthropicLLM, LLMError
from learn.teaching_engine import extract_facts
from learn.teaching_engine.ai_cards import TASK, CardError, _Builder, sheet_prompt, write_with_model
from learn.teaching_engine.detective import check_case_file, plan_case_file, render_case_file_pdf
from learn.teaching_engine.sheet import read_sheet

UK = Path(__file__).parent / "sheets" / "uk-cities-comparative-table.pdf"


@pytest.fixture(scope="module")
def uk():
    data = UK.read_bytes()
    return plan_case_file(read_sheet(extract_facts(extract(data).units), data))


def _spec(card, facts) -> dict:
    """The model reply that asks for this rule-based card."""
    kind, first = card.kind, (card.covers[0] if card.covers else "")
    if kind in {"match", "which", "who"}:
        return {"kind": kind, "lines": list(card.covers)}
    if kind == "fill":
        return {"kind": kind, "line": first, "hide": card.answer[0].split(": ", 1)[0]}
    if kind == "pick":
        hide = card.answer[0].split(": ", 1)[0]
        options = [part.split(") ", 1)[1] for part in card.lines[1].split("   ")]
        return {"kind": kind, "line": first, "hide": hide, "wrong": [o for o in options if o != hide]}
    if kind == "number":
        return {"kind": kind, "line": first, "number": card.lines[0]}
    if kind == "finish":
        return {"kind": kind, "line": first, "shown": card.lines[0].removesuffix(" …")}
    if kind == "mistake":
        return {"kind": kind, "line": first, "wrong_name": card.lines[0].split(": ", 1)[0]}
    if kind == "timeline":
        events = []
        for answer in card.answer:
            words = answer.split(". ", 1)[1]
            line = next(f for f in card.covers if words in facts[f].text)
            events.append({"line": line, "words": words})
        return {"kind": kind, "events": events}
    raise AssertionError(kind)


def _replies(case_file) -> list[dict]:
    """One good reply per sheet: the rule-based cards, asked for by name."""
    return [
        {"cards": [_spec(card, case_file.facts) for card in sheet.cards if card.kind != "notes"]}
        for case in case_file.cases
        for sheet in case.sheets
    ]


def test_model_choices_become_checked_cards_for_every_sheet(uk):
    llm = ScriptedLLM({TASK: _replies(uk) + [{}]})
    result = write_with_model(uk, llm)
    assert result.ai_sheets == result.sheets == 4 and result.notes == []
    assert check_case_file(result.case_file) == []
    assert render_case_file_pdf(result.case_file).startswith(b"%PDF")
    for before, after in zip(uk.cases, result.case_file.cases, strict=True):
        for old, new in zip(before.sheets, after.sheets, strict=True):
            assert [c.kind for c in old.cards] == [c.kind for c in new.cards]
            assert {f for c in old.cards for f in c.covers} == {f for c in new.cards for f in c.covers}


def test_the_model_sees_only_its_sheet_and_the_earlier_one(uk):
    llm = ScriptedLLM({TASK: _replies(uk) + [{}]})
    write_with_model(uk, llm)
    sheets = [sheet for case in uk.cases for sheet in case.sheets]
    assert len(llm.calls) == len(sheets)
    for (task, prompt), sheet in zip(llm.calls, sheets, strict=True):
        allowed = set(sheet.lines) | set(sheet.review)
        for fact_id in uk.facts:
            assert (f"{fact_id} [" in prompt) == (fact_id in allowed)
        assert task == TASK


def test_a_bad_choice_is_sent_back_once_with_its_problems(uk):
    good = _replies(uk)[0]
    bad = {"cards": [dict(good["cards"][0])] + good["cards"][1:]}
    first_line = uk.cases[0].sheets[0].lines[1]
    bad["cards"][0] = {"kind": "fill", "line": first_line, "hide": "words that are not there"}
    llm = ScriptedLLM({TASK: [bad, good, {}]})
    result = write_with_model(uk, llm, limit=1)
    assert result.ai_sheets == 1 and len(llm.calls) == 2
    assert "is not in line" in llm.calls[1][1] and "Choose the cards again" in llm.calls[1][1]


def test_a_sheet_that_fails_twice_keeps_its_rule_based_cards(uk):
    bad = {"cards": [{"kind": "fill", "line": "F1", "hide": "nothing like this"}]}
    llm = ScriptedLLM({TASK: [bad, bad, {}]})
    result = write_with_model(uk, llm, limit=1)
    assert result.ai_sheets == 0
    assert any("failed checks twice" in note for note in result.notes)
    assert result.case_file.cases[0].sheets[0].cards == uk.cases[0].sheets[0].cards
    assert check_case_file(result.case_file) == []


def test_an_unreachable_model_stops_asking_and_prints_the_rule_based_cards(uk):
    class Down:
        calls = 0

        def json(self, task, system, prompt):
            self.calls += 1
            raise LLMError("Claude API credentials are not configured (set JUNE_API_KEY).")

    down = Down()
    result = write_with_model(uk, down)
    assert down.calls == 1 and result.ai_sheets == 0
    assert any("JUNE_API_KEY" in note for note in result.notes)
    assert result.case_file == uk


def test_the_sheet_limit_keeps_test_runs_cheap(uk):
    llm = ScriptedLLM({TASK: _replies(uk) + [{}]})
    result = write_with_model(uk, llm, limit=1)
    assert len(llm.calls) == 1 and result.ai_sheets == 1
    assert any("1 of 4 sheets" in note for note in result.notes)
    assert C.cards_sheet_limit() == 1


def test_rule_b_holds_for_model_cards(uk):
    sheet = uk.cases[0].sheets[0]
    fills = [
        {"kind": "fill", "line": line, "hide": uk.facts[line].text.split()[-1].rstrip(".")} for line in sheet.lines
    ]
    llm = ScriptedLLM({TASK: [{"cards": fills[:7]}, {"cards": fills[:7]}, {}]})
    result = write_with_model(uk, llm, limit=1)
    assert result.ai_sheets == 0
    assert "fill-the-gap cards, more than 2" in llm.calls[1][1]


# Each choice the builder must refuse.


@pytest.fixture(scope="module")
def builder(uk):
    case = uk.cases[0]
    return _Builder(uk.facts, case.sheets[1].lines, case.sheets[1].review, case.suspects)


def _line(uk, suspect, sheet=1, contains=""):
    lines = uk.cases[0].sheets[sheet].lines
    return next(f for f in lines if uk.facts[f].suspect == suspect and contains in uk.facts[f].text)


@pytest.mark.parametrize(
    "make_spec, message",
    [
        (lambda uk: {"kind": "draw", "line": "F1"}, "unknown kind"),
        (lambda uk: {"kind": "fill", "line": _line(uk, "Belfast"), "hide": "Paris"}, "is not in line"),
        (lambda uk: {"kind": "fill", "line": _line(uk, "London", 0), "hide": "Thames"}, "not on this sheet"),
        (
            lambda uk: {
                "kind": "fill",
                "line": _line(uk, "Belfast", 1, "Lagan"),
                "hide": "Situated on the River Lagan; population",
            },
            "hides too much",
        ),
        (
            lambda uk: {
                "kind": "pick",
                "line": _line(uk, "Belfast", 1, "Lagan"),
                "hide": "Lagan",
                "wrong": ["Seine", "Thames"],
            },
            "is not on the sheet",
        ),
        (
            lambda uk: {
                "kind": "pick",
                "line": _line(uk, "Belfast", 1, "Lagan"),
                "hide": "Lagan",
                "wrong": ["Lagan", "Thames"],
            },
            "wrong choice is the answer",
        ),
        (lambda uk: {"kind": "number", "line": _line(uk, "Belfast", 1, "Lagan"), "number": "999"}, "not a number"),
        (lambda uk: {"kind": "finish", "line": _line(uk, "Belfast"), "shown": "Once upon a time"}, "is not how"),
        (
            lambda uk: {"kind": "mistake", "line": _line(uk, "Belfast", 1, "Lagan"), "wrong_name": "Belfast"},
            "another suspect",
        ),
        (
            lambda uk: {"kind": "mistake", "line": _line(uk, "Belfast", 1, "Lagan"), "wrong_name": "Paris"},
            "another suspect",
        ),
        (
            lambda uk: {"kind": "which", "lines": [f for f in uk.cases[0].sheets[1].lines[:3]]},
            "two suspects",
        ),
    ],
)
def test_the_builder_refuses_choices_not_made_of_the_sheet(uk, builder, make_spec, message):
    with pytest.raises(CardError, match=message):
        builder.build(make_spec(uk))


def test_the_builder_refuses_a_timeline_out_of_order(uk):
    case = uk.cases[1]
    cardiff = next(f for f in case.sheets[-1].lines if "1905" in uk.facts[f].text)
    builder = _Builder(uk.facts, case.sheets[-1].lines, case.sheets[-1].review, case.suspects)
    events = [
        {"line": cardiff, "words": "proclaimed capital of Wales in 1955"},
        {"line": cardiff, "words": "Made a city in 1905"},
    ]
    with pytest.raises(CardError, match="earliest first"):
        builder.build({"kind": "timeline", "events": events})
    card = builder.build({"kind": "timeline", "events": events[::-1]})
    assert card.answer == ("1. Made a city in 1905", "2. proclaimed capital of Wales in 1955")


def test_prompt_lists_the_sheet_and_review_lines(uk):
    sheet = uk.cases[0].sheets[1]
    prompt = sheet_prompt(uk, sheet, uk.cases[0].suspects)
    assert "THIS SHEET:" in prompt and "EARLIER SHEET:" in prompt
    assert prompt.count("[Belfast]") >= 1 and "SUSPECTS: London, Birmingham, Belfast" in prompt


# The card model's client settings


def test_cards_go_to_june_with_haiku_at_low_effort_and_no_fallbacks(monkeypatch):
    monkeypatch.setenv("LEARN_PROVIDER", "june")
    monkeypatch.setenv("JUNE_API_KEY", "test-key-not-real")
    monkeypatch.delenv("LEARN_CARDS_MODEL", raising=False)
    monkeypatch.delenv("LEARN_CARDS_EFFORT", raising=False)
    llm = AnthropicLLM.for_cards()
    assert llm.model == "anthropic/claude-haiku-5.5" and llm.effort == llm.check_effort == "low"
    assert not llm.fallbacks and llm.key_name == "JUNE_API_KEY"
    assert str(llm.client.base_url).startswith("https://api.blockchain.info/ai/api")


def test_cards_default_to_the_claude_api_with_haiku(monkeypatch):
    monkeypatch.delenv("LEARN_PROVIDER", raising=False)
    monkeypatch.delenv("LEARN_CARDS_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-real")
    llm = AnthropicLLM.for_cards()
    assert llm.model == "claude-haiku-5-5" and llm.effort == "low" and not llm.fallbacks


def test_june_without_a_key_sends_a_bearer_header_for_the_network_secret_to_fill(monkeypatch):
    monkeypatch.setenv("LEARN_PROVIDER", "june")
    monkeypatch.delenv("JUNE_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm = AnthropicLLM.for_cards()
    assert llm.client.auth_token == JUNE_KEY_FROM_NETWORK and llm.client.api_key is None
    assert str(llm.client.base_url).startswith("https://api.blockchain.info/ai/api")


def test_the_builder_refuses_a_timeline_event_without_a_date(uk):
    sheet = uk.cases[0].sheets[0]
    birmingham = [f for f in sheet.lines if uk.facts[f].suspect == "Birmingham"]
    steam = next(f for f in birmingham if "steam engine" in uk.facts[f].text)
    market = next(f for f in birmingham if "medieval" in uk.facts[f].text)
    builder = _Builder(uk.facts, sheet.lines, sheet.review, uk.cases[0].suspects)
    undated = [
        {"line": market, "words": "Was a medium-sized market town in the medieval period"},
        {"line": steam, "words": "The industrial steam engine"},
    ]
    with pytest.raises(CardError, match="no date or period"):
        builder.build({"kind": "timeline", "events": undated})
    dated = [undated[0], {"line": market, "words": "grew to international prominence in the 18th century"}]
    assert builder.build({"kind": "timeline", "events": dated}).answer[0].startswith("1. Was a medium-sized")


def test_a_hidden_river_name_keeps_the_word_river_as_a_hint(uk):
    sheet = uk.cases[0].sheets[0]
    thames = next(f for f in sheet.lines if "River Thames" in uk.facts[f].text)
    builder = _Builder(uk.facts, sheet.lines, sheet.review, uk.cases[0].suspects)
    card = builder.build({"kind": "fill", "line": thames, "hide": "River Thames"})
    assert "the River ________ in" in card.lines[0] and card.answer[0].startswith("Thames:")
