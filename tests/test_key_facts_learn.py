"""Pytest-style tests for the Learn Key Facts package interface and KeyFactCard output."""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import glob
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from learn.teaching_engine.key_facts import KeyFactCard, plan_key_facts, run

ALLOWED_KINDS = {"gap", "question", "term", "name", "equation", "row", "compare"}


@dataclass
class _MockTable:
    """Plain table object matching Learn's reader table attributes."""

    header: list[str]
    rows: list[list[str]]
    kind: str | None = None


@dataclass
class _MockItem:
    """Plain item object (not a dict) with Learn's reader Item attributes."""

    kind: str
    text: str
    page: int = 1
    unit_ids: list[str] | tuple[str, ...] = ()
    marker: str | None = None
    section: str | None = None
    group: str | None = None
    topic: str | None = None
    context: str | None = None
    answer: str | None = None
    options: list[str] | None = None
    table: _MockTable | None = None
    top: float | None = None
    bottom: float | None = None
    bullet: str | None = None
    bold: list[str] | tuple[str, ...] = ()


def test_key_fact_card_dataclass_fields() -> None:
    """Verify KeyFactCard is a frozen dataclass with the exact eight Learn fields."""
    assert is_dataclass(KeyFactCard)
    field_names = tuple(f.name for f in fields(KeyFactCard))
    assert field_names == (
        "kind",
        "question",
        "clue",
        "answer",
        "page",
        "unit_ids",
        "about",
        "checks",
    )


def test_plan_key_facts_with_plain_item_objects() -> None:
    """Feed plain Item objects (not dicts) into plan_key_facts and check KeyFactCard fields."""
    items = [
        _MockItem(
            kind="heading",
            text="Gopal Krishna Gokhale",
            page=1,
            unit_ids=["U1"],
        ),
        _MockItem(
            kind="point",
            text="Co-launched the Home Rule Movement in 1916.",
            page=1,
            unit_ids=["U1", "U2"],
            topic="Bal Gangadhar Tilak",
            bold=["Home Rule Movement"],
        ),
        _MockItem(
            kind="point",
            text="Founded the Servants of India Society in 1905.",
            page=1,
            unit_ids=["U3"],
            topic="Gopal Krishna Gokhale",
            bold=["Servants of India Society"],
        ),
        _MockItem(
            kind="point",
            text="Outside London, the largest city in the United Kingdom.",
            page=2,
            unit_ids=["U4"],
            topic="Birmingham",
        ),
        _MockItem(
            kind="point",
            text="Eleventh-largest city in the United Kingdom.",
            page=2,
            unit_ids=["U5"],
            topic="Cardiff",
        ),
        _MockItem(
            kind="table",
            text="Steel Plants",
            page=2,
            unit_ids=["U6"],
            topic="Steel Plants",
            table=_MockTable(
                header=["Plant", "State"],
                rows=[["Bhilai", "Chhattisgarh"], ["Rourkela", "Odisha"]],
                kind="comparison",
            ),
        ),
    ]

    cards = plan_key_facts(items, standard=8)
    assert len(cards) >= 5

    for card in cards:
        assert isinstance(card, KeyFactCard)
        assert card.kind in ALLOWED_KINDS
        assert isinstance(card.question, str) and card.question
        assert isinstance(card.clue, str) and card.clue
        assert isinstance(card.answer, str) and card.answer
        assert isinstance(card.page, int) and card.page >= 1
        assert isinstance(card.unit_ids, tuple)
        assert isinstance(card.about, str) and card.about
        assert card.about.lower() != card.answer.lower()
        assert isinstance(card.checks, tuple)
        if "______" in card.clue:
            assert card.question != "Answer it."
        else:
            assert card.question == "Answer it."

    hrm_cards = [c for c in cards if c.answer == "Home Rule Movement"]
    assert len(hrm_cards) == 1
    assert hrm_cards[0].unit_ids == ("U1", "U2")
    assert hrm_cards[0].kind == "gap"

    birmingham_cards = [c for c in cards if c.about == "Birmingham"]
    assert len(birmingham_cards) == 1
    assert birmingham_cards[0].checks == (
        "Check first: the sheet says “largest”. Confirm it in the textbook before learning it.",
    )

    cardiff_cards = [c for c in cards if c.about == "Cardiff"]
    assert len(cardiff_cards) == 1
    assert cardiff_cards[0].checks == ()


def test_eight_data_sheets_outputs_match_identically() -> None:
    """Confirm that run() and plan_key_facts() produce the exact same cards on all 8 data sheets."""
    sheet_paths = sorted(
        glob.glob(str(ROOT / "data" / "*.reader.json"))
        + glob.glob(str(ROOT / "data" / "round2" / "*.reader.json"))
    )
    assert len(sheet_paths) == 8

    expected_counts = {
        "full-physics-forces.reader.json": 19,
        "mumbai-personalities-flat.reader.json": 30,
        "uk-cities-comparative-table.reader.json": 30,
        "civics-sheet.reader.json": 24,
        "equations.reader.json": 9,
        "full-finance-lost-rupee.reader.json": 11,
        "history-sheet.reader.json": 20,
        "processes-sheet.reader.json": 18,
    }

    for path_str in sheet_paths:
        path = Path(path_str)
        data = json.loads(path.read_text(encoding="utf-8"))
        out = run(data)
        json_cards = out["cards"]
        assert len(json_cards) == expected_counts[path.name]

        planned = plan_key_facts(data["items"], standard=8)
        assert len(planned) == len(json_cards)

        for jc, kc in zip(json_cards, planned, strict=True):
            assert isinstance(kc, KeyFactCard)
            assert kc.kind in ALLOWED_KINDS
            assert kc.clue == jc["front"]
            assert kc.answer == jc["answer"]
            assert kc.page == jc["page"]
            assert kc.about == jc["about"]
            assert kc.about.lower() != kc.answer.lower()
            if "______" in kc.clue:
                assert kc.question == jc["prompt"]
            else:
                assert kc.question == "Answer it."


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    """Allow unittest discovery to run plain pytest-style test_* functions in this module."""
    _ = (loader, tests, pattern)
    suite = unittest.TestSuite()
    for name, obj in list(globals().items()):
        if name.startswith("test_") and callable(obj):
            suite.addTest(unittest.FunctionTestCase(obj))
    return suite
