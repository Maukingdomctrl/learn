"""Render source-grounded, double-sided learning cards as an A4 PDF."""

from dataclasses import dataclass
from hashlib import sha256

import pymupdf

from .facts import Fact, FactInventory, Mention

_PAGE_WIDTH = 595.28
_PAGE_HEIGHT = 841.89
_CARD_WIDTH = 241.0
_CARD_HEIGHT = 195.0
_LEFT = (_PAGE_WIDTH - 2 * _CARD_WIDTH) / 2
_TOP = (_PAGE_HEIGHT - 4 * _CARD_HEIGHT) / 2
_INK = (0.13, 0.20, 0.17)
_GREEN = (0.15, 0.36, 0.28)
_MUTED = (0.39, 0.45, 0.41)
_PAPER = (0.97, 0.96, 0.91)
_LINE = (0.83, 0.86, 0.81)
_ORANGE = (0.70, 0.34, 0.14)
_HERO = (0.31, 0.27, 0.64)


@dataclass(frozen=True)
class SourceVisual:
    page: int
    image: bytes


def _focus(fact: Fact) -> tuple[Mention, str, str] | None:
    priority = {
        "difficult_term": (0, "WORD DETECTIVE", "What does this word mean here?"),
        "date": (1, "TIME DETECTIVE", "Which date fits? Picture it on a timeline."),
        "number": (2, "NUMBER DETECTIVE", "Which number fits? Say what it measures."),
        "place_candidate": (3, "PLACE DETECTIVE", "Which place fits? Say what links it to the idea."),
        "entity": (4, "NAME DETECTIVE", "Which name fits? Tell what the source says."),
    }
    candidates = []
    for mention in fact.mentions:
        if mention.kind not in priority:
            continue
        prefix = fact.statement[: mention.start - fact.start].strip().casefold()
        if mention.kind == "entity" and len(mention.text.split()) == 1 and prefix in ("", "the", "a", "an"):
            continue
        candidates.append(mention)
    if not candidates:
        return None
    mention = min(candidates, key=lambda item: (priority[item.kind][0], -(item.end - item.start), item.start))
    _, label, prompt = priority[mention.kind]
    return mention, label, prompt


def _masked_statement(fact: Fact, focus: Mention | None) -> str:
    if focus is None:
        return fact.statement
    start = focus.start - fact.start
    end = focus.end - fact.start
    return f"{fact.statement[:start]}________{fact.statement[end:]}"


def _wrapped(text: str, font: pymupdf.Font, size: float, width: float) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if font.text_length(candidate, fontsize=size) <= width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def _fit_size(text: str, font: pymupdf.Font, max_size: float, max_width: float, max_height: float) -> float:
    sizes = [size for size in (max_size, 11.0, 9.4, 8.8, 8.2, 7.6, 7.0, 6.4, 5.8) if size <= max_size]
    for size in dict.fromkeys(sizes):
        line_count = len(_wrapped(text, font, size, max_width))
        if line_count * size * 1.25 <= max_height:
            return size
    raise ValueError("A source fact is too long to fit on a card. Select fewer pages or split that source sentence.")


def _draw_text(page, text: str, rect: pymupdf.Rect, fontname: str, max_size: float, color, align=0) -> None:
    font = pymupdf.Font(fontname)
    size = _fit_size(text, font, max_size, rect.width, rect.height)
    result = page.insert_textbox(
        rect,
        text,
        fontname=fontname,
        fontsize=size,
        lineheight=1.25,
        color=color,
        align=align,
    )
    if result < 0:
        raise ValueError("A source fact could not be laid out on the printable cards. Select fewer pages.")


def _card_rect(column: int, row: int) -> pymupdf.Rect:
    x = _LEFT + column * _CARD_WIDTH
    y = _TOP + row * _CARD_HEIGHT
    return pymupdf.Rect(x, y, x + _CARD_WIDTH, y + _CARD_HEIGHT)


def _draw_card_frame(page, rect: pymupdf.Rect, warning: bool = False) -> None:
    page.draw_rect(rect, color=_LINE, fill=(1, 1, 1), width=0.8)
    band = _ORANGE if warning else _GREEN
    page.draw_rect(pymupdf.Rect(rect.x0, rect.y0, rect.x1, rect.y0 + 5), color=None, fill=band)


def _detective_prompt(label: str) -> str:
    prompts = {
        "WORD DETECTIVE": "What does this word mean here?",
        "TIME DETECTIVE": "Which date fits? Picture it on a timeline.",
        "NUMBER DETECTIVE": "Which number fits? Say what it measures.",
        "PLACE DETECTIVE": "Which place fits? Say what links it to the idea.",
        "NAME DETECTIVE": "Which name fits? Tell what the source says.",
        "MEMORY MISSION": "Read the evidence. Cover it, then explain the idea.",
    }
    return prompts[label]


def _hero_prompt(label: str) -> str:
    prompts = {
        "WORD DETECTIVE": "WORD LENS - explain the word as this source uses it.",
        "TIME DETECTIVE": "TIME JUMP - place the date on an imaginary timeline.",
        "NUMBER DETECTIVE": "NUMBER SHIELD - recall the value and what it describes.",
        "PLACE DETECTIVE": "MAP PULSE - recall the place and its source-stated link.",
        "NAME DETECTIVE": "NAME SPARK - recall the name and its source detail.",
        "MEMORY MISSION": "MEMORY BEAM - teach one source idea to a teammate.",
    }
    return prompts[label]


def _mode_prompt(label: str, game_mode: str, standard: int) -> str:
    if standard == 7:
        prompts = {
            "WORD DETECTIVE": "Explain this word to your teammate.",
            "TIME DETECTIVE": "Find the date. Put it on a timeline.",
            "NUMBER DETECTIVE": "Find the number. What does it count?",
            "PLACE DETECTIVE": "Find the place. What is it linked to?",
            "NAME DETECTIVE": "Find the name. What does the source say?",
            "MEMORY MISSION": "Read the clue, cover it, then tell it back.",
        }
    elif standard == 9:
        prompts = {
            "WORD DETECTIVE": "Explain how the source uses this term.",
            "TIME DETECTIVE": "Place the date in sequence and recall its event.",
            "NUMBER DETECTIVE": "Recall the value and identify what it measures.",
            "PLACE DETECTIVE": "Name the place and explain the stated relationship.",
            "NAME DETECTIVE": "Identify the name and its source-stated detail.",
            "MEMORY MISSION": "Reconstruct the idea from memory, then verify the source.",
        }
    else:
        return _detective_prompt(label) if game_mode == "detective" else _hero_prompt(label)
    prompt = prompts[label]
    return f"POWER-UP - {prompt}" if game_mode == "superhero" else prompt


def _draw_visual_front(page, visual: SourceVisual, number: int, position: int, game_mode: str) -> None:
    rect = _card_rect(position % 2, position // 2)
    _draw_card_frame(page, rect)
    inner = pymupdf.Rect(rect.x0 + 12, rect.y0 + 15, rect.x1 - 12, rect.y1 - 10)
    mode_label = "CASE EVIDENCE" if game_mode == "detective" else "HERO POWER-UP"
    page.insert_text((inner.x0, inner.y0 + 8), f"{mode_label} - SOURCE VISUAL", fontname="hebo", fontsize=7.2, color=_GREEN if game_mode == "detective" else _HERO)
    prompt = (
        "Study this exact source image. What do you notice? Check nearby source text before explaining it."
        if game_mode == "detective"
        else "Choose one detail from this source image to help a fact stick. Your memory link is your own."
    )
    _draw_text(page, prompt, pymupdf.Rect(inner.x0, inner.y0 + 15, inner.x1, inner.y0 + 42), "helv", 8.0, _MUTED)
    image_rect = pymupdf.Rect(inner.x0 + 5, inner.y0 + 47, inner.x1 - 5, inner.y0 + 119)
    page.insert_image(image_rect, stream=visual.image, keep_proportion=True)
    page.insert_text((inner.x0, inner.y1 - 8), f"SOURCE PAGE {visual.page}  -  CARD {number + 1:02d}", fontname="helv", fontsize=6.4, color=_MUTED)


def _draw_visual_back(page, visual: SourceVisual, position: int, game_mode: str) -> None:
    rect = _card_rect(position % 2, position // 2)
    _draw_card_frame(page, rect)
    inner = pymupdf.Rect(rect.x0 + 12, rect.y0 + 15, rect.x1 - 12, rect.y1 - 10)
    label = "CASE NOTES - SOURCE IMAGE" if game_mode == "detective" else "HERO NOTES - SOURCE IMAGE"
    page.insert_text((inner.x0, inner.y0 + 8), label, fontname="hebo", fontsize=7.2, color=_GREEN if game_mode == "detective" else _HERO)
    page.insert_text((inner.x0, inner.y0 + 33), f"This image is reproduced from source page {visual.page}.", fontname="helv", fontsize=8.3, color=_INK)
    prompt = "Point to details you can verify in the source. Keep guesses separate from evidence." if game_mode == "detective" else "Invent a hero emblem to remember one verified detail. The emblem is a memory aid, not a source fact."
    _draw_text(page, prompt, pymupdf.Rect(inner.x0, inner.y0 + 47, inner.x1, inner.y0 + 88), "helv", 8.0, _MUTED)
    doodle = pymupdf.Rect(inner.x1 - 42, inner.y1 - 44, inner.x1, inner.y1 - 2)
    page.draw_rect(doodle, color=_LINE, width=0.6)
    page.insert_text((inner.x0, inner.y1 - 8), f"PAGE {visual.page}  -  {game_mode.upper()} SOURCE VISUAL", fontname="helv", fontsize=6.4, color=_MUTED)


def _draw_front(page, fact: Fact, number: int, position: int, game_mode: str, standard: int) -> None:
    rect = _card_rect(position % 2, position // 2)
    warning = bool(fact.review_flags)
    _draw_card_frame(page, rect, warning)
    focus = _focus(fact)
    if warning:
        label = "PAUSE - VERIFY THIS SOURCE CLAIM"
        prompt = "Check the quoted claim with a trusted adult before learning it."
        text = fact.statement
    elif focus:
        mention, label, _ = focus
        prompt = _mode_prompt(label, game_mode, standard)
        text = _masked_statement(fact, mention)
    else:
        label = "MEMORY MISSION"
        prompt = _mode_prompt(label, game_mode, standard)
        text = "Can you tell the idea back?"

    inner = pymupdf.Rect(rect.x0 + 12, rect.y0 + 15, rect.x1 - 12, rect.y1 - 10)
    page.insert_text((inner.x0, inner.y0 + 8), label, fontname="hebo", fontsize=7.2, color=_ORANGE if warning else _GREEN)
    if not warning:
        badge = {"WORD DETECTIVE": "ABC", "TIME DETECTIVE": "DATE", "NUMBER DETECTIVE": "123", "PLACE DETECTIVE": "MAP", "NAME DETECTIVE": "NAME", "MEMORY MISSION": "IDEA"}[label]
        badge_rect = pymupdf.Rect(inner.x1 - 28, inner.y0 - 1, inner.x1, inner.y0 + 17)
        mode_color = _GREEN if game_mode == "detective" else _HERO
        page.draw_circle(((badge_rect.x0 + badge_rect.x1) / 2, (badge_rect.y0 + badge_rect.y1) / 2), 9, color=None, fill=_PAPER)
        page.insert_textbox(badge_rect, badge, fontname="hebo", fontsize=4.8, color=mode_color, align=1)
    prompt_rect = pymupdf.Rect(inner.x0, inner.y0 + 17, inner.x1, inner.y0 + 45)
    _draw_text(page, prompt, prompt_rect, "helv", 8.2, _MUTED)
    clue_rect = pymupdf.Rect(inner.x0, inner.y0 + 48, inner.x1, inner.y0 + 107)
    _draw_text(page, text, clue_rect, "hebo", 12.0, _INK)
    page.insert_text((inner.x0, inner.y1 - 8), f"CARD {number + 1:02d}  -  TURN OVER TO CHECK", fontname="helv", fontsize=6.4, color=_MUTED)


def _draw_back(page, fact: Fact, number: int, position: int, game_mode: str) -> None:
    rect = _card_rect(position % 2, position // 2)
    warning = bool(fact.review_flags)
    _draw_card_frame(page, rect, warning)
    inner = pymupdf.Rect(rect.x0 + 12, rect.y0 + 15, rect.x1 - 12, rect.y1 - 10)
    label = "VERIFY FIRST" if warning else "SOURCE ANSWER"
    mode_color = _ORANGE if warning else (_GREEN if game_mode == "detective" else _HERO)
    page.insert_text((inner.x0, inner.y0 + 8), label, fontname="hebo", fontsize=7.2, color=mode_color)
    quote_rect = pymupdf.Rect(inner.x0, inner.y0 + 20, inner.x1, inner.y0 + 86)
    _draw_text(page, fact.statement, quote_rect, "hebo", 10.0, _INK)
    source = f"Source page {fact.page}  -  {fact.source_unit_id}"
    page.insert_text((inner.x0, inner.y0 + 96), source, fontname="helv", fontsize=6.5, color=_MUTED)
    if warning:
        review = ", ".join(fact.review_flags)
        _draw_text(page, f"Review flag: {review}", pymupdf.Rect(inner.x0, inner.y0 + 104, inner.x1, inner.y0 + 119), "helv", 6.8, _ORANGE)
        page.insert_text((inner.x0, inner.y1 - 8), "Do not treat as confirmed until checked against the source.", fontname="helv", fontsize=6.1, color=_ORANGE)
    else:
        page.insert_text((inner.x0, inner.y0 + 111), "My memory hook:", fontname="hebo", fontsize=6.8, color=_GREEN)
        page.draw_line((inner.x0 + 57, inner.y0 + 114), (inner.x1 - 33, inner.y0 + 114), color=_LINE, width=0.6)
        doodle = pymupdf.Rect(inner.x1 - 29, inner.y0 + 103, inner.x1 - 1, inner.y0 + 131)
        page.draw_rect(doodle, color=_LINE, width=0.6)
        page.insert_text((doodle.x0 + 2, doodle.y1 + 7), "SKETCH", fontname="helv", fontsize=4.8, color=_MUTED)
        page.insert_text((inner.x0, inner.y1 - 8), "Make your own link or picture - not a source fact", fontname="helv", fontsize=6.1, color=_MUTED)


def extract_source_visuals(source_pdf: bytes, pages: set[int] | None = None) -> list[SourceVisual]:
    """Extract distinct embedded source images as in-memory PNGs, linked to their PDF pages."""
    document = pymupdf.open(stream=source_pdf, filetype="pdf")
    visuals: list[SourceVisual] = []
    seen: set[tuple[int, str]] = set()
    for page_index, page in enumerate(document):
        page_number = page_index + 1
        if pages is not None and page_number not in pages:
            continue
        seen_xrefs: set[int] = set()
        for image_info in page.get_images(full=True):
            xref = image_info[0]
            if xref <= 0 or xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                extracted = document.extract_image(xref)
                if extracted["width"] < 24 or extracted["height"] < 24:
                    continue
                pixmap = pymupdf.Pixmap(extracted["image"])
                mask_xref = image_info[1]
                if mask_xref:
                    pixmap = pymupdf.Pixmap(pixmap, pymupdf.Pixmap(document, mask_xref))
                if pixmap.colorspace is not None and pixmap.colorspace.n > 3:
                    pixmap = pymupdf.Pixmap(pymupdf.csRGB, pixmap)
                image_bytes = pixmap.tobytes("png")
            except Exception:
                try:
                    placements = page.get_image_rects(xref)
                    if not placements:
                        raise ValueError("No visible placement")
                    placement = max(placements, key=lambda rect: rect.width * rect.height)
                    image_bytes = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=placement, alpha=False).tobytes("png")
                except Exception:
                    continue
            fingerprint = sha256(image_bytes).hexdigest()
            key = (page_number, fingerprint)
            if key not in seen:
                seen.add(key)
                visuals.append(SourceVisual(page=page_number, image=image_bytes))
    document.close()
    return visuals


def render_printable_cards_pdf(
    inventory: FactInventory,
    source_pdf: bytes | None = None,
    game_mode: str = "detective",
    pages: set[int] | None = None,
    standard: int = 8,
) -> bytes:
    """Create 85 × 68.8 mm two-sided game cards with source facts, citations, and embedded visuals."""
    if game_mode not in {"detective", "superhero"}:
        raise ValueError("Choose either Detective or Superhero game mode.")
    if standard not in {7, 8, 9}:
        raise ValueError("Choose ICSE Standard 7, 8, or 9.")
    if not inventory.facts:
        raise ValueError("No source facts were found to turn into cards.")
    visuals = extract_source_visuals(source_pdf, pages) if source_pdf else []
    entries = [("fact", fact) for fact in inventory.facts]
    entries.extend(("visual", visual) for visual in visuals)
    document = pymupdf.open()
    cards_per_sheet = 8
    sheets = (len(entries) + cards_per_sheet - 1) // cards_per_sheet

    for sheet_number in range(sheets):
        start = sheet_number * cards_per_sheet
        group = entries[start : start + cards_per_sheet]
        for side in ("FRONTS", "BACKS"):
            page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
            mode_title = "DETECTIVE CASE FILE" if game_mode == "detective" else "SUPERHERO POWER-UP GAME"
            heading = f"ICSE STANDARD {standard}  -  {mode_title}  -  SHEET {sheet_number + 1}  -  {side}"
            if side == "BACKS":
                heading += "  -  FLIP ON LONG EDGE"
            page.insert_text((18, 18), heading, fontname="hebo", fontsize=7, color=_MUTED)
            page.insert_text((18, 27), "Solve source clues and cite evidence." if game_mode == "detective" else "Recall a fact, teach a teammate, invent a memory emblem.", fontname="helv", fontsize=6, color=_GREEN if game_mode == "detective" else _HERO)
            for position in range(cards_per_sheet):
                if side == "FRONTS":
                    fact_index = start + position
                else:
                    mirror = position + 1 if position % 2 == 0 else position - 1
                    fact_index = start + mirror
                if fact_index >= start + len(group):
                    continue
                entry_type, entry = entries[fact_index]
                if side == "FRONTS":
                    if entry_type == "fact":
                        _draw_front(page, entry, fact_index, position, game_mode, standard)
                    else:
                        _draw_visual_front(page, entry, fact_index, position, game_mode)
                else:
                    if entry_type == "fact":
                        _draw_back(page, entry, fact_index, position, game_mode)
                    else:
                        _draw_visual_back(page, entry, position, game_mode)
            page.insert_text((_PAGE_WIDTH - 90, _PAGE_HEIGHT - 10), f"{sheet_number + 1} / {sheets}", fontname="helv", fontsize=6.5, color=_MUTED)

    document.set_metadata({"title": f"Learn ICSE Standard {standard} {game_mode} game", "author": "Learn Teaching Engine"})
    result = document.tobytes(garbage=4, deflate=True)
    document.close()
    return result
