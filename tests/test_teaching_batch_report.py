import csv
from collections import Counter
from pathlib import Path

from learn.teaching_engine.batch_report import card_flags, main
from learn.teaching_engine.cards import Card

SAMPLES = Path(__file__).parents[1] / "cards" / "sample"


def _card(question: str, clue: str, answer: str, kind: str = "gap") -> Card:
    return Card(kind, question, clue, answer, 1)


def test_flags_point_at_the_likely_problem_and_leave_a_clean_card_alone():
    titles = {"ratios compare quantities"}
    counts = Counter({"london": 5, "18th": 1, "ratios compare quantities": 1})

    def flags(card):
        return card_flags(card, titles, counts)

    assert flags(_card("Which century fits the gap?", "Grew to prominence in the ______ century.", "18th")) == []
    assert flags(
        _card("What is this about?", "Equivalent ratios have the same value.", "Ratios Compare Quantities")
    ) == [
        "vague",
        "title_answer",
    ]
    assert "long_answer" in flags(_card("Finish it.", "Ratios are …", "… a way to compare two quantities by division"))
    assert "fragment" in flags(_card("Finish it.", "… the same value.", "x"))
    assert "repeat" in flags(_card("What is this about?", "Situated on the River Thames.", "LONDON"))


def test_a_folder_run_writes_the_summary_and_both_tables_and_survives_a_broken_pdf(tmp_path, capsys):
    folder = tmp_path / "sheets" / "history"
    folder.mkdir(parents=True)
    (folder / "history.pdf").write_bytes((SAMPLES / "history-sheet.pdf").read_bytes())
    (folder / "broken.pdf").write_bytes(b"not a pdf")
    out = tmp_path / "report"

    assert main([str(tmp_path / "sheets"), "--out", str(out)]) == 0

    sheets = {row["sheet"]: row for row in csv.DictReader((out / "sheets.csv").open(encoding="utf-8"))}
    assert set(sheets) == {str(Path("history") / "broken.pdf"), str(Path("history") / "history.pdf")}
    assert sheets[str(Path("history") / "broken.pdf")]["problems"] == "error"
    assert int(sheets[str(Path("history") / "history.pdf")]["cards"]) > 0
    cards = list(csv.DictReader((out / "cards.csv").open(encoding="utf-8")))
    assert cards and all(card["sheet"].endswith("history.pdf") for card in cards)
    summary = (out / "summary.md").read_text(encoding="utf-8")
    assert "Sheets read: 2" in summary and "Sheets that failed: 1" in summary
