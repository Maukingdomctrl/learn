"""Run the card engine over a folder of study-sheet PDFs and report where it goes wrong.

    python -m learn.teaching_engine.batch_report path/to/sheets --out card_report

Offline and free: no AI, no network. The PDFs are only read, never copied. Writes `summary.md` (totals, the most
common problems, the worst sheets), `sheets.csv` (one row per PDF) and `cards.csv` (every card with its flags).

The flags are checks on the shape of a card, not on whether it teaches well: a flagged card is probably bad, but an
unflagged card is not proven good. Read a sample of each by eye.
"""

import argparse
import csv
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from ..extraction import extract
from .cards import Card, plan_cards, reject_generated_pdf
from .facts import extract_facts
from .sheet import read_sheet

SLOW_SECONDS = 20.0
LONG_ANSWER_WORDS = 6
REPEATS_PER_SHEET = 3
# Card kinds whose answer is meant to be whole: a practice question's model answer, a comparison, an order.
_WHOLE_ANSWERS = {"question", "compare", "order", "tip", "picture", "teach", "learn"}

FLAGS = {
    "vague": 'asks "What is this about?"',
    "title_answer": "the answer is a heading or title printed on the sheet",
    "long_answer": f"the answer is longer than {LONG_ANSWER_WORDS} words",
    "fragment": "the clue starts mid-sentence or is under 3 words",
    "repeat": f"the same answer is used more than {REPEATS_PER_SHEET} times on the sheet",
}


@dataclass
class SheetResult:
    path: str
    pages: int = 0
    seconds: float = 0.0
    error: str = ""
    cards: list[Card] = field(default_factory=list)
    flags: list[list[str]] = field(default_factory=list)  # one list per card


def card_flags(card: Card, titles: set[str], answer_counts: Counter) -> list[str]:
    """The likely problems with one card, as flag names from FLAGS."""
    found = []
    answer = " ".join(card.answer.split())
    if card.question.rstrip("?").casefold() in {"what is this about", "who is this about"}:
        found.append("vague")
    if answer.casefold() in titles:
        found.append("title_answer")
    if card.kind not in _WHOLE_ANSWERS and len(answer.split()) > LONG_ANSWER_WORDS:
        found.append("long_answer")
    clue = card.clue.strip().lstrip("…").strip()
    if card.kind != "picture" and (len(clue.split()) < 3 or re.match(r"[a-z]", clue)):
        found.append("fragment")
    if answer and answer_counts[answer.casefold()] > REPEATS_PER_SHEET:
        found.append("repeat")
    return found


def check_sheet(path: Path, name: str = "") -> SheetResult:
    result = SheetResult(name or str(path))
    started = time.perf_counter()
    try:
        data = path.read_bytes()
        reject_generated_pdf(data)
        source = extract(data)
        sheet = read_sheet(extract_facts(source.units), data)
        result.pages = len({item.page for item in sheet.items})
        result.cards = plan_cards(sheet)
        titles = {
            " ".join(item.text.split()).casefold()
            for item in sheet.items
            if item.kind in {"title", "section", "heading", "topic", "group"} and item.text
        }
        counts = Counter(" ".join(card.answer.split()).casefold() for card in result.cards)
        result.flags = [card_flags(card, titles, counts) for card in result.cards]
    except Exception as error:  # one broken PDF must not stop a run over a thousand
        result.error = f"{type(error).__name__}: {error}"[:300]
    result.seconds = time.perf_counter() - started
    return result


def _sheet_problems(result: SheetResult) -> list[str]:
    problems = []
    if result.error:
        problems.append("error")
    elif not result.cards:
        problems.append("no_cards")
    if result.seconds > SLOW_SECONDS:
        problems.append("slow")
    return problems


def write_report(results: list[SheetResult], out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    with (out / "cards.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sheet", "card", "page", "kind", "question", "clue", "answer", "flags"])
        for result in results:
            for number, (card, flags) in enumerate(zip(result.cards, result.flags, strict=True), start=1):
                row = [result.path, number, card.page, card.kind, card.question, card.clue, card.answer]
                writer.writerow([*row, " ".join(flags)])
    with (out / "sheets.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sheet", "pages", "cards", "flagged_cards", "seconds", "problems", *FLAGS, "error"])
        for result in results:
            counts = Counter(flag for flags in result.flags for flag in flags)
            flagged = sum(bool(flags) for flags in result.flags)
            row = [result.path, result.pages, len(result.cards), flagged, f"{result.seconds:.1f}"]
            writer.writerow([*row, " ".join(_sheet_problems(result)), *(counts[f] for f in FLAGS), result.error])
    (out / "summary.md").write_text(_summary(results), encoding="utf-8")


def _summary(results: list[SheetResult]) -> str:
    cards = sum(len(result.cards) for result in results)
    flagged = sum(bool(flags) for result in results for flags in result.flags)
    flag_counts = Counter(flag for result in results for flags in result.flags for flag in flags)
    problems = Counter(problem for result in results for problem in _sheet_problems(result))
    lines = [
        "# Card engine report",
        "",
        f"- Sheets read: {len(results)}",
        f"- Cards made: {cards}",
        f"- Cards flagged: {flagged} ({flagged / cards:.0%})" if cards else "- Cards flagged: 0",
        f"- Sheets that failed: {problems['error']}; made no cards: {problems['no_cards']}; "
        f"slower than {SLOW_SECONDS:.0f} s: {problems['slow']}",
        "",
        "Flags check the shape of a card only. Read a sample of flagged and unflagged cards by eye.",
        "",
        "## Most common problems",
        "",
        "| Flag | Cards | Meaning |",
        "| :--- | ---: | :--- |",
    ]
    lines += [f"| `{flag}` | {flag_counts[flag]} | {meaning} |" for flag, meaning in FLAGS.items()]

    def share(result: SheetResult) -> float:
        return sum(bool(flags) for flags in result.flags) / len(result.cards) if result.cards else 0.0

    worst = sorted((result for result in results if result.cards), key=share, reverse=True)[:20]
    lines += [
        "",
        "## Worst 20 sheets (share of cards flagged)",
        "",
        "| Sheet | Cards | Flagged |",
        "| :--- | ---: | ---: |",
    ]
    lines += [f"| {result.path} | {len(result.cards)} | {share(result):.0%} |" for result in worst]
    failed = [result for result in results if result.error]
    if failed:
        lines += ["", "## Sheets that failed", ""]
        lines += [f"- {result.path}: {result.error}" for result in failed]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the card engine on a folder of study-sheet PDFs.")
    parser.add_argument("folder", help="folder of PDFs; subfolders are included")
    parser.add_argument("--out", default="card_report", help="folder to write the report into")
    args = parser.parse_args(argv)

    folder = Path(args.folder)
    paths = sorted(folder.rglob("*.pdf"), key=lambda path: str(path).casefold())
    if not paths:
        print(f"No PDFs found in {args.folder}")
        return 1
    results = []
    for number, path in enumerate(paths, start=1):
        result = check_sheet(path, str(path.relative_to(folder)))
        results.append(result)
        status = result.error or f"{len(result.cards)} cards"
        print(f"[{number}/{len(paths)}] {path.name}: {status} ({result.seconds:.1f} s)")
    write_report(results, Path(args.out))
    print(f"Report written to {Path(args.out) / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
