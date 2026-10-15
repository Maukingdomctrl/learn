"""Render the offline teaching plan as a print-ready A4 PDF in memory."""

from collections.abc import Iterable

import pymupdf

from .lesson import HeldFact, TeachingLesson

_PAGE_WIDTH = 595.28
_PAGE_HEIGHT = 841.89
_LEFT = 42
_RIGHT = 42
_CONTENT_WIDTH = _PAGE_WIDTH - _LEFT - _RIGHT
_CONTENT_BOTTOM = 790
_INK = (0.13, 0.20, 0.17)
_GREEN = (0.15, 0.36, 0.28)
_MUTED = (0.37, 0.43, 0.39)
_PAPER = (0.97, 0.96, 0.91)
_LINE = (0.84, 0.87, 0.82)
_ORANGE = (0.70, 0.37, 0.16)


_ADVANCES: dict[tuple[str, str], float] = {}


def _text_width(text: str, font: pymupdf.Font, size: float) -> float:
    # Font.text_length crosses into MuPDF once per character on every call; caching the
    # per-character advance keeps wrapping a long source from taking minutes.
    total = 0.0
    for char in text:
        key = (font.name, char)
        advance = _ADVANCES.get(key)
        if advance is None:
            advance = _ADVANCES[key] = font.text_length(char, fontsize=1)
        total += advance
    return total * size


def _wrap(text: str, width: float, font: pymupdf.Font, size: float) -> list[str]:
    lines: list[str] = []
    space = _text_width(" ", font, size)
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        line_width = _text_width(line, font, size)
        for word in words[1:]:
            word_width = _text_width(word, font, size)
            if line_width + space + word_width <= width:
                line = f"{line} {word}"
                line_width += space + word_width
            else:
                lines.append(line)
                line = word
                line_width = word_width
        lines.append(line)
    return lines


def render_teaching_pdf(lesson: TeachingLesson, warnings: Iterable[str] = ()) -> bytes:
    """Create a multipage A4 PDF without writing the PDF or lesson to disk."""
    document = pymupdf.open()
    regular = pymupdf.Font("helv")
    bold = pymupdf.Font("hebo")
    # Draw each page into one Shape and commit it once: page.insert_text/draw_rect re-read the
    # page's content stream on every call, which made long lessons time out on the host.
    canvas = None
    y = 0.0

    def box(rect: pymupdf.Rect, color=None, fill=None, width: float = 1) -> None:
        canvas.draw_rect(rect)
        canvas.finish(color=color, fill=fill, width=width)

    def new_page(continued: bool = False) -> None:
        nonlocal canvas, y
        if canvas is not None:
            canvas.commit()
        canvas = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT).new_shape()
        box(pymupdf.Rect(0, 0, _PAGE_WIDTH, 68), color=None, fill=_GREEN)
        canvas.insert_text(
            (_LEFT, 32),
            "LEARN  /  TEACHING ENGINE",
            fontname="hebo",
            fontsize=9,
            color=(0.88, 0.93, 0.88),
        )
        heading = "Ideas to learn and remember" + (" · continued" if continued else "")
        canvas.insert_text((_LEFT, 54), heading, fontname="hebo", fontsize=17, color=(1, 1, 1))
        y = 88

    def ensure(height: float) -> None:
        if canvas is None:
            new_page()
        elif y + height > _CONTENT_BOTTOM:
            new_page(continued=True)

    def paragraph(text: str, size: float = 9.5, color=_INK, font=regular, leading: float | None = None) -> None:
        nonlocal y
        leading = leading or size * 1.38
        lines = _wrap(text, _CONTENT_WIDTH, font, size)
        for line in lines:
            ensure(leading)
            canvas.insert_text((_LEFT, y + size), line, fontname=font.name, fontsize=size, color=color)
            y += leading

    def section(label: str, text: str, color=_GREEN) -> None:
        nonlocal y
        ensure(29)
        canvas.insert_text((_LEFT, y + 8), label.upper(), fontname="hebo", fontsize=7.2, color=color)
        y += 12
        paragraph(text, size=9.2)
        y += 5

    def quote(text: str, page_no: int) -> None:
        nonlocal y
        pad_x, pad_y = 11, 9
        lines = _wrap(text, _CONTENT_WIDTH - pad_x * 2, bold, 10.2)
        height = len(lines) * 13.3 + pad_y * 2 + 12
        ensure(height + 8)
        top = y
        box(
            pymupdf.Rect(_LEFT, top, _PAGE_WIDTH - _RIGHT, top + height),
            color=None,
            fill=_PAPER,
        )
        canvas.insert_text(
            (_LEFT + pad_x, top + pad_y + 8),
            f"SOURCE  ·  PAGE {page_no}",
            fontname="hebo",
            fontsize=6.8,
            color=_MUTED,
        )
        line_y = top + pad_y + 23
        for line in lines:
            canvas.insert_text((_LEFT + pad_x, line_y), line, fontname="hebo", fontsize=10.2, color=_INK)
            line_y += 13.3
        y = top + height + 7

    def fact_card(number: int, fact) -> None:
        nonlocal y
        ensure(70)
        box(
            pymupdf.Rect(_LEFT, y, _PAGE_WIDTH - _RIGHT, y + 23),
            color=None,
            fill=(0.91, 0.95, 0.91),
        )
        canvas.insert_text(
            (_LEFT + 9, y + 15.5),
            f"IDEA {number}  ·  {fact.source_unit_id}",
            fontname="hebo",
            fontsize=8,
            color=_GREEN,
        )
        y += 31
        quote(fact.source_statement, fact.source_page)
        section("Understand", fact.child_explanation)
        section("Memory picture · scaffold, not a fact", fact.memory_link, _ORANGE)
        section("Draw it", fact.visual_brief)
        ensure(48)
        box(
            pymupdf.Rect(_LEFT, y, _PAGE_WIDTH - _RIGHT, y + 37),
            color=_LINE,
            fill=(1, 1, 1),
            width=0.8,
        )
        canvas.insert_text(
            (_LEFT + 9, y + 23),
            "Your sketch",
            fontname="heit",
            fontsize=8,
            color=_MUTED,
        )
        y += 44
        section("Make your own link", fact.child_makes_a_link)
        ensure(18)
        canvas.insert_text(
            (_LEFT, y + 8), "REMEMBER IT  ·  FADE THE SUPPORT", fontname="hebo", fontsize=7.2, color=_GREEN
        )
        y += 13
        for recall in fact.recall_rounds:
            paragraph(f"{recall.support.upper()}  /  {recall.mode.replace('_', ' ')}: {recall.prompt}", size=8.5)
            y += 2
        y += 9

    new_page()
    paragraph(lesson.opening_hook, size=10, color=_MUTED)
    y += 10
    index = 0
    for topic in lesson.topics:
        for fact in topic.fact_lessons:
            index += 1
            fact_card(index, fact)

    if lesson.held_for_review:
        ensure(65)
        box(
            pymupdf.Rect(_LEFT, y, _PAGE_WIDTH - _RIGHT, y + 25),
            color=None,
            fill=(0.98, 0.92, 0.87),
        )
        canvas.insert_text(
            (_LEFT + 9, y + 17),
            "PAUSE  ·  SOURCE CLAIMS TO VERIFY BEFORE TEACHING",
            fontname="hebo",
            fontsize=8,
            color=_ORANGE,
        )
        y += 34
        for held in lesson.held_for_review:
            held_fact(held, paragraph, ensure)

    for warning in warnings:
        section("Source note", warning, _ORANGE)

    canvas.commit()
    total_pages = len(document)
    for number, output_page in enumerate(document, start=1):
        output_canvas = output_page.new_shape()
        output_canvas.draw_line((_LEFT, 811), (_PAGE_WIDTH - _RIGHT, 811))
        output_canvas.finish(color=_LINE, width=0.6)
        output_canvas.insert_text(
            (_LEFT, 827),
            "Source-linked learning plan  ·  Check flagged claims against the cited page",
            fontname="helv",
            fontsize=7,
            color=_MUTED,
        )
        output_canvas.insert_text(
            (_PAGE_WIDTH - _RIGHT - 48, 827),
            f"{number} / {total_pages}",
            fontname="hebo",
            fontsize=7,
            color=_MUTED,
        )
        output_canvas.commit()
    document.set_metadata({"title": lesson.title, "author": "Learn Teaching Engine"})
    pdf_bytes = document.tobytes(garbage=4, deflate=True)
    document.close()
    return pdf_bytes


def held_fact(held: HeldFact, paragraph, ensure) -> None:
    ensure(46)
    paragraph(f"{held.source_statement}  [source page {held.source_page}]", size=9.2, font=pymupdf.Font("hebo"))
    paragraph(f"Review flags: {', '.join(held.review_flags)}", size=8.3, color=_ORANGE)
    paragraph(f"Fact reference: {held.fact_id}", size=7.8, color=_MUTED)
    paragraph("", size=5)
