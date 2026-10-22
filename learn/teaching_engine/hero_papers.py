"""Superhero Mode: the same model-written, sheet-checked cards as the Detective case papers, printed in the look of
the owner's Hero Academy prototype (a separate Next.js app, ``src/lib/paper/pdf.ts``).

The cards are written once (``write_case_papers``), in one model call per group of lines. Cards whose answer is a fact
(a name, place, date or number) print as the detective part; cards whose answer is an idea print here, after it, so
no question appears twice.

Each sheet: white paper, navy dashed challenge cards in a 2 x 4 grid, red "CHALLENGE No." and "FIELD REPORT" labels, a
cream question box, then a "Secret Files" answer page with a training guide, hero ranks and a MISSION COMPLETE stamp.
"""

import re

import pymupdf

from .cards import _ORANGE, _PAGE_HEIGHT, _PAGE_WIDTH, _Type
from .evidence_cards import _MARGIN, _TOP, _TYPEWRITER, EvidenceCard, EvidenceSet, _box, _fits, _typed, _typed_fit

_INK = (0.08, 0.10, 0.20)
_NAVY = (0.36, 0.42, 0.62)
_RED = (0.86, 0.20, 0.18)
_CREAM = (1.0, 0.95, 0.86)
_GREY = (0.45, 0.47, 0.55)
_TRAINING = (
    "READ the field report on a card. Picture the scene.",
    "THINK: what is really going on there?",
    "WRITE your answer on the line. One or two words.",
    "CHECK the Secret Files only at the end.",
)


def mission_title(papers: EvidenceSet) -> str:
    """The set's title as a mission: "The Case of the Great Uprising" becomes "Mission: The Great Uprising"."""
    name = re.sub(r"^the case of\s+", "", papers.title.strip(), flags=re.I) or "The Study Sheet"
    return f"Mission: {name[:1].upper()}{name[1:]}"


def _page(document, kind: _Type):
    page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
    kind.prepare(page)
    return page, page.new_shape()


def _header(shape, kind: _Type, label: str, title: str, right: str, sub: str, label_colour, title_colour) -> None:
    _typed(shape, label, 12, _MARGIN, 44, label_colour, spaced=True)
    width = _TYPEWRITER[False].text_length(right, fontsize=8)
    _typed(shape, right, 8, _PAGE_WIDTH - _MARGIN - width, 44, _GREY, bold=False)
    kind.draw(shape, [kind.printable(title.upper(), True)], 10, _MARGIN, 52, True, title_colour)
    kind.draw(shape, kind.wrap(kind.printable(sub), 7.5, _PAGE_WIDTH - 2 * _MARGIN)[:2], 7.5, _MARGIN, 66, False, _GREY)
    shape.draw_line((_MARGIN, _TOP - 12), (_PAGE_WIDTH - _MARGIN, _TOP - 12))
    shape.finish(color=_INK, width=1.2)


def _footer(shape, kind: _Type) -> None:
    line = " ".join("READ - THINK - WRITE - CHECK THE SECRET FILES")
    kind.draw(shape, [line], 6.5, (_PAGE_WIDTH - kind.width(line, 6.5)) / 2, _PAGE_HEIGHT - 24, False, _GREY)


def _draw_challenge(shape, kind: _Type, card: EvidenceCard, box: pymupdf.Rect) -> None:
    box = box + (4, 4, -4, -4)
    shape.draw_rect(box)
    shape.finish(color=_NAVY, width=0.9, dashes="[4 3] 0")
    inner = box + (12, 12, -12, -8)
    _typed(shape, f"CHALLENGE No. {card.number:02d}", 7.5, inner.x0, inner.y0 + 7, _RED)
    title = card.title.upper()
    _typed(shape, title, _typed_fit(title, inner.width, 9), inner.x0, inner.y0 + 21, _INK)
    _typed(shape, "FIELD REPORT", 5, inner.x0, inner.y0 + 31, _GREY, bold=False, spaced=True)
    question = pymupdf.Rect(inner.x0 - 4, box.y1 - 56, inner.x1 + 4, box.y1 - 20)
    report = pymupdf.Rect(inner.x0, inner.y0 + 34, inner.x1, question.y0 - 3)
    size, lines = _fits(kind, card.evidence, report, 9, 6.5, False)
    kind.draw(shape, lines, size, report.x0, report.y0, False, _INK)
    shape.draw_rect(question, radius=0.15)
    shape.finish(color=_NAVY, fill=_CREAM, width=0.6)
    _typed(shape, "?", 9, question.x0 + 5, question.y0 + 12, _RED)
    size, lines = _fits(kind, card.question, question + (16, 4, -6, -3), 8.5, 6, True)
    kind.draw(shape, lines, size, question.x0 + 16, question.y0 + 4, True, _INK)
    _typed(shape, "YOUR ANSWER:", 5.5, inner.x0, box.y1 - 8, _GREY, bold=False, spaced=True)
    shape.draw_line((inner.x0 + 80, box.y1 - 9), (inner.x1, box.y1 - 9))
    shape.finish(color=_GREY, width=0.5, dashes="[2 1] 0")


def _stamp(shape, centre: pymupdf.Point) -> None:
    big, small = "MISSION COMPLETE", "HERO ACADEMY TRAINING DIVISION"
    big_width = _TYPEWRITER[True].text_length(big, fontsize=13)
    small_width = _TYPEWRITER[True].text_length(small, fontsize=5.5)
    half = max(big_width, small_width) / 2 + 14
    turn = pymupdf.Matrix(-8)
    box = pymupdf.Rect(centre.x - half, centre.y - 20, centre.x + half, centre.y + 20)
    shape.draw_quad(box.quad.morph(centre, turn))
    shape.finish(color=_RED, width=2)
    for text, size, width, drop in ((big, 13, big_width, 2), (small, 5.5, small_width, 13)):
        shape.insert_text((centre.x - width / 2, centre.y + drop), text, fontname="cobo", fontsize=size, color=_RED,
                          morph=(centre, turn))  # fmt: skip


def _secret_files(
    document, kind: _Type, papers: EvidenceSet, index: int, total: int, cards: list[EvidenceCard], notes: bool
) -> None:
    page, shape = _page(document, kind)
    intro = "For the parent. Open this page only after every answer on the sheet is written down."
    sheet = f"SHEET {index} OF {total}"
    _header(shape, kind, "SECRET FILES - ANSWERS", mission_title(papers), sheet, intro, _RED, _INK)
    y, width = float(_TOP), _PAGE_WIDTH - 2 * _MARGIN - 44
    for card in cards:
        source = "; ".join(f"p. {papers.facts[line].page}: {papers.facts[line].text}" for line in card.lines)
        why = kind.wrap(kind.printable(card.key_why), 7.5, width)
        proof = kind.wrap(kind.printable(f"Sheet says: {source}"), 6.5, width)
        if y + 22 + 9 * len(why) + 8 * len(proof) > _PAGE_HEIGHT - 190:
            break  # eight rows fit; this only guards unusually long source lines
        _typed(shape, f"No. {card.number:02d}", 8, _MARGIN, y + 9, _RED)
        _typed(shape, card.title.upper()[:44], 7.5, _MARGIN + 44, y + 9, _INK)
        answer = card.answer.upper()
        size = _typed_fit(answer, 170, 10.5, 7)
        _typed(shape, answer, size, _PAGE_WIDTH - _MARGIN - _TYPEWRITER[True].text_length(answer, fontsize=size),
               y + 9, _RED)  # fmt: skip
        y = kind.draw(shape, why, 7.5, _MARGIN + 44, y + 12, False, _INK)
        y = kind.draw(shape, proof, 6.5, _MARGIN + 44, y, False, _GREY) + 6
        shape.draw_line((_MARGIN, y), (_PAGE_WIDTH - _MARGIN, y))
        shape.finish(color=_GREY, width=0.5, dashes="[3 2] 0")
        y += 6
    guide = pymupdf.Rect(_MARGIN, y + 6, _PAGE_WIDTH - _MARGIN, y + 84)
    shape.draw_rect(guide, radius=0.06)
    shape.finish(color=_NAVY, fill=_CREAM, width=0.6)
    _typed(shape, "HOW TO TRAIN", 7, guide.x0 + 12, guide.y0 + 15, _RED, spaced=True)
    kind.draw(shape, list(_TRAINING), 8, guide.x0 + 12, guide.y0 + 20, False, _INK)
    third = max(1, len(cards) // 3)
    ranks = (f"HERO RANK: 0-{third} KEEP TRAINING - {third + 1}-{max(third + 1, len(cards) - 2)} RISING HERO - "
             f"{max(third + 2, len(cards) - 1)}-{len(cards)} LEGEND")  # fmt: skip
    line = " ".join(ranks)
    kind.draw(shape, [line], 6, (_PAGE_WIDTH - kind.width(line, 6)) / 2, guide.y1 + 10, False, _GREY)
    if index == total:
        _stamp(shape, pymupdf.Point(_PAGE_WIDTH - _MARGIN - 100, _PAGE_HEIGHT - 74))
        if notes and papers.notes:
            lines = [line for note in papers.notes for line in kind.wrap(kind.printable(note), 7, width)][:3]
            kind.draw(shape, lines, 7, _MARGIN, guide.y1 + 24, False, _ORANGE)
    _footer(shape, kind)
    shape.commit()


def add_hero_pages(
    document, kind: _Type, papers: EvidenceSet, sheets: list[list[EvidenceCard]], subject: str, notes: bool
) -> None:
    """The hero part: each sheet's challenge cards on one page (one-sided), then its Secret Files page on the next.
    ``notes`` prints the set's notes on the last page, when no detective part came before to carry them."""
    total = len(sheets)
    for index, cards in enumerate(sheets, start=1):
        page, shape = _page(document, kind)
        topics = " · ".join(dict.fromkeys(card.topic for card in cards if card.topic))
        _header(shape, kind, "HERO ACADEMY", mission_title(papers), f"SHEET {index} OF {total}",
                " · ".join(part for part in (subject.upper(), topics) if part)[:110], _INK, _RED)  # fmt: skip
        for position, card in enumerate(cards):
            _draw_challenge(shape, kind, card, _box(position))
        _footer(shape, kind)
        shape.commit()
        _secret_files(document, kind, papers, index, total, cards, notes)
