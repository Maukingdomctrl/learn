"""Read a study sheet into ordered, source-cited items for the card game.

The PDF reader works from printed lines, not text blocks. Many PDFs store every printed line as its own block, so
one sentence, bullet or table cell can be spread over several blocks. Line positions, sizes and bullet marks (typed
or drawn) show where each heading, bullet, table row and question starts. Without a PDF, or on a page with no text
layer, the reader falls back to the fact inventory.

Items hold only the sheet's own words: wrapped lines are joined, list markers are kept apart from the text, and
nothing is reworded.
"""

import re
from dataclasses import dataclass, field
from functools import cached_property
from itertools import pairwise
from statistics import median

import pymupdf

from ..extraction import MIN_PAGE_CHARS, text_block_units
from .facts import BULLETS, FactInventory

# "1.", "2)", "Q3.", "Question 4:", "(a)", "(iv)" or a section letter "B." before a word.
_MARKER = re.compile(
    r"^(?P<marker>"
    r"Q(?:uestion)?\s?\.?\s?\d{1,2}\s?[.):]?"
    r"|\d{1,2}\s?[.)]"
    r"|\((?:[a-z]|[ivx]{1,4}|\d{1,2})\)"
    r"|[A-H][.)](?=\s+[A-Z][a-z])"
    r")\s+(?=\S)"
)
_SUB_MARKER = re.compile(r"^(?:\d{1,2}\)|\((?:[a-z]|[ivx]{1,4}|\d{1,2})\))\s")
_TIP = re.compile(
    r"^(?:memory\s+tip|study\s+tip|exam\s+tip|quick\s+tip|tip|think|remember|mnemonic|trick)\b\s*[:\-–—]\s*", re.I
)
_INLINE_ANSWER = re.compile(r"\s*[—–-]{1,2}\s*Ans(?:wer)?\s*[:.\-–—]\s*|\s+Ans(?:wer)?\s*:\s*")
_WRITE_IN = re.compile(r"[\s_.…]*")  # an answer line left empty to write on
# "Complete the name: United ______.  Answer: ________": a line left to write the answer on makes it a question.
_ASKS_FOR_ANSWER = re.compile(r"\bAns(?:wer)?\s*:\s*[_.…]{3,}\s*$")
_NUMBERED_ANSWER = re.compile(r"(?P<marker>\d{1,3}[.)])\s+(?P<answer>\S.*)")
_LEADING_ANSWER = re.compile(r"^(?:[—–-]{1,2}\s*)?Ans(?:wer)?\s*[:.\-–—]\s*")
_SUMMARY = re.compile(r"^(?P<name>[^=]{2,80}?)\s+=\s+(?P<rest>\S.*)$")
_SENTENCE_END = re.compile(r"[.!?][\"'”’)\]]*$")
_CONTINUES_AFTER = re.compile(
    r"(?:\b(?:a|an|the|of|in|on|at|to|for|from|by|with|and|or|nor|but|as|its|his|her|their|that|which|who|whose|"
    r"into|onto|than|via|between|under|over|after|before|during|about)|[,(\-–—/&+])$",
    re.I,
)
_PAGE_NUMBER = re.compile(r"(?:page|pg\.?|p\.)\s*\d+(?:\s*(?:of|/)\s*\d+)?|\d+\s*(?:of|/)\s*\d+", re.I)
# A running footer, alone or glued to the end of the text above it: "Grade 8 Social Studies | … Page 2".
_FOOTER = re.compile(r"^(?:Page\s+\d+\b.*\|.*|.*\|.*\bPage\s+\d+)$", re.I)
_FOOTER_TAIL = re.compile(
    r"\s+(?:Grade|Class|Standard|Std\.?)\s+\d{1,2}\b[^.!?]{0,80}?\|[^.!?]{0,80}?\bPage\s+\d+\s*$", re.I
)
# An upper-case section heading run into the text after it, as text extraction can leave a table heading.
_LEADING_HEADING = re.compile(r"^(?:\d{1,2}\.\s+)?[A-Z][A-Z0-9&'’()\-–—:,/ ]{3,}?[A-Z)](?=\s+[A-Z][a-z])")
_SECTION_KINDS = (
    ("qa", re.compile(r"\bQUESTIONS?\b.*\b(?:ANSWERS?|ANSWER\s*KEY)\b|\bQ\s?&\s?A\b", re.I)),
    ("answers", re.compile(r"\bANSWER\s*KEY\b|\bANSWERS\b|\bSOLUTIONS\b", re.I)),
    (
        "questions",
        re.compile(
            r"\bQUESTIONS?\b|\bPRACTICE\b|\bEXERCISES?\b|\bWORKSHEET\b|\bQUIZ\b|\bFILL IN THE BLANKS\b|\bQUICK CHECK\b"
            r"|\bCHECK YOUR(?:SELF| UNDERSTANDING)\b|\bEXIT TICKET\b|\bTRY TH(?:IS|ESE)\b|\bYOUR TURN\b|\bHOMEWORK\b"
            r"|\bTEST YOURSELF\b",
            re.I,
        ),
    ),
    ("table", re.compile(r"\bTABLE\b|\bCOMPARATIVE\b|\bCOMPARISON\b|\bAT A GLANCE\b", re.I)),
    ("tips", re.compile(r"\bTIPS?\b|\bMNEMONICS?\b", re.I)),
    (
        "notes",
        re.compile(r"\bNOTES\b|\bREVISION\b|\bSUMMARY\b|\bKEY (?:POINTS|IDEAS|FACTS|TERMS)\b|\bOVERVIEW\b", re.I),
    ),
)
# Headings that label a kind of content ("Remember", "Key idea", "Four main stages") rather than name a topic.
GENERIC_HEADING = re.compile(
    r"^(?:remember|note|notes|example|examples|key ideas?|key points?|summary|introduction|conclusion|activit(?:y|ies)|"
    r"exercises?|quick check|check|think|did you know|fun facts?|important|learning (?:goals|objectives)|objectives?|"
    r"goals?|vocabulary|glossary|key ?words|key terms|definitions?|answers?|questions?|compare|contrast|review|recap|"
    r"tips?|hints?|warning|caution|overview|background|discussion|explanation|steps|procedure|method|materials|"
    r"results?|observations?|aim|practice|homework|exit ticket|common mistakes?|common errors|common traps|"
    r"interpretation|analysis|evaluation|variables|safety|data|calculations?|worked|experiment|investigation|"
    r"theory|hypothesis|apparatus|reasoning|evidence|applications?|uses|advantages|disadvantages)\b",
    re.I,
)
_QUESTION_START = re.compile(
    r"^(?:Q(?:uestion)?\s*\d*\s*[:.]|(?:What|Why|How|When|Where|Which|Who|Whom|Whose|Is|Are|Do|Does|Did|Can|Could|"
    r"Would|Should|Will|If)\b|(?:Explain|Describe|State|Name|Give|List|Define|Compare|Mention|Write|Find|Calculate|"
    r"Solve|Identify|Discuss)\b)"
)
_INLINE_MARKER = re.compile(r"(?<=\s)(?:Q\s?)?(\d{1,2})[.)]\s+(?=\S)")
_YEAR_LABEL = re.compile(r"(?:c\.\s*)?\d{3,4}(?:\s*(?:BCE|BC|CE|AD))?|\d{1,2}\s+[A-Z][a-z]+\s+\d{4}")
# A boxed call-out label run into its text: "BIG IDEA • Change is caused by several connected factors."
_CALLOUT = re.compile(r"^(?P<label>[A-Z][A-Z0-9 &'’/-]{1,40}?)\s*•\s+(?=\S)")
# A task set by the sheet: "Practice: Predict what could happen if …"
_TASK = re.compile(
    r"^(?:practice|exam practice|task|exercise|activity|challenge|try this|your turn|extended response|homework)"
    r"\s*[\d.]*\s*:\s*",
    re.I,
)
# A question number printed on its own line above the question, as model-answer sheets print them: "Question 3".
_QUESTION_NUMBER = re.compile(r"^(?:Q|Ques\.?|Question)\s*(?P<number>\d{1,2})\s*[.):]?$", re.I)
# The same label run into the text before it, as text extraction can leave it: "… → glucose Question 3 Explain …".
_RUN_IN_QUESTION = re.compile(r"\s+(?=Question\s+\d{1,2}\s+[A-Z‘“'\"(])")
_LEADING_QUESTION = re.compile(r"^(?P<label>Question\s+\d{1,2})\s+(?=[A-Z‘“'\"(])")
# "Note: Water is also a reactant, but the question asks for the gas." explains the answer to whoever checks it.
_COMMENT = re.compile(r"^(?:notes?|n\.?\s?b\.?)\s*[:–—-]\s", re.I)


@dataclass(frozen=True)
class Table:
    header: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    kind: str = "grid"  # grid | panels (bullet lists side by side) | timeline (years with the events beside them)


@dataclass(frozen=True)
class Item:
    """One piece of the sheet, in reading order, in the sheet's own words."""

    kind: str  # title | section | heading | group | topic | point | summary | question | answer | tip | table
    text: str  # without the list marker; a question's own answer is moved to ``answer``
    page: int
    unit_ids: tuple[str, ...]
    marker: str = ""
    section: str = ""  # the kind of section the item sits in: notes | table | questions | answers | qa | tips
    group: str = ""  # section letter that question and answer numbers belong to ("A", "B")
    topic: str = ""  # text of the topic heading a point belongs to
    context: str = ""  # the sub-heading above an item, such as "Four main stages"
    answer: str = ""  # a question's answer; a model answer printed under it keeps one line per point
    table: Table | None = None
    top: float = 0.0  # position on the page, when read from the PDF layout
    bottom: float = 0.0

    @property
    def number(self) -> str:
        found = re.search(r"\d+", self.marker)
        return found.group() if found else ""


@dataclass(frozen=True)
class Picture:
    """A picture printed on the sheet. Its image is drawn only when a card asks for it.

    Drawing every photo and map of a long chapter up front took most of the time and memory of reading the sheet,
    yet only pictures beside a named topic ever reach a card.
    """

    page: int
    rect: tuple[float, float, float, float]
    source: bytes = field(repr=False, compare=False)  # the sheet's PDF, shared, never copied

    @cached_property
    def image(self) -> bytes:
        with pymupdf.open(stream=self.source, filetype="pdf") as document:
            clip = pymupdf.Rect(self.rect)
            return (
                document[self.page - 1].get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=clip, alpha=False).tobytes("png")
            )

    @cached_property
    def is_code(self) -> bool:
        """A QR code: square-ish, almost only pure black on white, its edges straight up and down from row to row.

        A photo or a map has greys and colours; a seal, a drawing or lettering has curved edges.
        """
        x0, y0, x1, y1 = self.rect
        if not 0.6 <= (x1 - x0) / max(y1 - y0, 1.0) <= 1.6 or max(x1 - x0, y1 - y0) > 300:
            return False
        with pymupdf.open(stream=self.source, filetype="pdf") as document:
            pixmap = document[self.page - 1].get_pixmap(
                matrix=pymupdf.Matrix(3, 3), clip=pymupdf.Rect(self.rect), colorspace=pymupdf.csGRAY, alpha=False
            )
        width, pixels = pixmap.width, pixmap.samples
        if width < 2 or not pixels:
            return False
        dark = sum(value < 80 for value in pixels) / len(pixels)
        light = sum(value > 175 for value in pixels) / len(pixels)
        if dark < 0.15 or light < 0.5 or dark + light < 0.85:
            return False
        rows = [pixels[top : top + width] for top in range(0, len(pixels) - width + 1, 2 * width)]
        edges = [{x for x in range(1, width) if (row[x] < 128) != (row[x - 1] < 128)} for row in rows]
        found = sum(len(row) for row in edges[:-1])
        if found < 8 * (len(edges) - 1):
            return False  # too few black and white changes along a row for the squares of a code
        straight = sum(any(x + step in below for step in (-1, 0, 1)) for row, below in pairwise(edges) for x in row)
        return straight >= 0.75 * found


@dataclass(frozen=True)
class Sheet:
    items: tuple[Item, ...]
    pictures: tuple[Picture, ...] = ()


@dataclass
class _Line:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    size: float
    units: tuple[str, ...]
    bullet: bool = False


@dataclass
class _Paragraph:
    text: str
    page: int
    units: list[str]
    bullet: bool = False
    size: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    table: Table | None = None
    lines: list[_Line] = field(default_factory=list)


def join_lines(first: str, second: str) -> str:
    """Join a wrapped line to the next one: "Non-" + "Cooperation" stays "Non-Cooperation"."""
    first, second = first.rstrip(), second.lstrip()
    if not first:
        return second
    if first[-1] in "-–—/" and len(first) > 1 and not first[-2].isspace():
        return first + second
    return f"{first} {second}"


def _ends_sentence(text: str) -> bool:
    return bool(_SENTENCE_END.search(text.rstrip()))


def split_marker(text: str) -> tuple[str, str]:
    match = _MARKER.match(text)
    if not match:
        return "", text
    return match["marker"].strip(), text[match.end() :]


def _upper_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    return sum(char.isupper() for char in letters) / len(letters) if len(letters) >= 4 else 0.0


_CHAPTER = re.compile(r"^(?:chapter|unit|lesson)\b", re.I)


def _section_kind(text: str) -> str:
    return next((kind for kind, pattern in _SECTION_KINDS if pattern.search(text)), "")


def _title_case(text: str) -> bool:
    words = [word for word in re.findall(r"[A-Za-z][\w'’-]*", text) if len(word) > 3]
    return bool(words) and len(text.split()) <= 9 and all(word[0].isupper() for word in words)


# ---------------------------------------------------------------- PDF layout


def _page_lines(page: pymupdf.Page, pno: int) -> list[_Line]:
    units = [(rect + (-1, -1, 1, 1), unit_id) for rect, unit_id in text_block_units(page, pno)]
    lines: list[_Line] = []
    lone_bullets: list[pymupdf.Rect] = []
    # Text only: the default "dict" also copies every image's pixels, which a long illustrated chapter cannot afford.
    text_only = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    for block in page.get_text("dict", sort=True, flags=text_only)["blocks"]:
        if block.get("type") != 0:
            continue
        for raw in block["lines"]:
            spans = [span for span in raw["spans"] if span["text"].strip()]
            if not spans or abs(raw["dir"][0]) < 0.5:
                continue  # sideways text (a running title printed up the margin) would cut through the paragraphs
            # A dingbat font at the start of a line draws its bullet; inside the text it stands in for a letter the
            # main font lacked (some PDF makers print a box instead of "₃" or "₹"), so that letter is lost.
            chunks, dingbat_bullet = [], False
            for index, span in enumerate(raw["spans"]):
                chunk = span["text"]
                if "dingbat" in span["font"].casefold() and chunk.strip():
                    after = next((later for later in raw["spans"][index + 1 :] if later["text"].strip()), None)
                    spaced = (
                        after is None
                        or after["text"][:1].isspace()
                        or (after["bbox"][0] - span["bbox"][2] >= 0.25 * span["size"])
                    )
                    if not "".join(chunks).strip() and spaced:  # "■ Text": a bullet; "■600": a lost "₹"
                        dingbat_bullet = True
                        continue
                    chunk = "".join(char if char.isspace() else "\ufffd" for char in chunk)
                chunks.append(chunk)
            text = " ".join("".join(chunks).split())
            box = pymupdf.Rect(spans[0]["bbox"])
            for span in spans[1:]:
                box |= span["bbox"]
            if not text or all(char in BULLETS for char in text.replace(" ", "")):
                lone_bullets.append(box)
                continue
            sizes: dict[float, int] = {}
            for span in spans:
                sizes[round(span["size"], 1)] = sizes.get(round(span["size"], 1), 0) + len(span["text"].strip())
            centre = pymupdf.Point((box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2)
            unit = next((unit_id for rect, unit_id in units if centre in rect), "")
            line = _Line(text, box.x0, box.y0, box.x1, box.y1, max(sizes, key=sizes.get), (unit,) if unit else ())
            line.bullet = dingbat_bullet
            if text[0] in BULLETS:
                line.text = text.lstrip(BULLETS + " ")
                line.bullet = True
            lines.append(line)
    dots = lone_bullets + [
        drawing["rect"]
        for drawing in page.get_drawings()
        if drawing.get("fill") is not None
        and 1.5 <= drawing["rect"].width <= 7
        and 1.5 <= drawing["rect"].height <= 7
        and abs(drawing["rect"].width - drawing["rect"].height) <= 1.5
    ]
    for dot in dots:
        middle = (dot.y0 + dot.y1) / 2
        for line in lines:
            if line.y0 - 1 <= middle <= line.y1 + 1 and 0 <= line.x0 - dot.x1 <= 18:
                line.bullet = True
                break
    lines.sort(key=lambda line: (round(line.y0, 0), line.x0))
    return lines


def _join_justified(lines: list[_Line]) -> list[_Line]:
    """Put back together a justified line that PDF text extraction split at its widened word gaps.

    "Akbar | also | instituted" printed on one baseline becomes "Akbar also instituted" when the pieces together
    span exactly the width of a whole line just above or below them. Cells of a table, side by side on one row, do not
    line up with a single full-width line, so they stay apart.
    """
    rows: list[list[_Line]] = []
    for line in lines:
        last = rows[-1][-1] if rows else None
        if (
            last is not None
            and abs(line.y0 - last.y0) <= 1.5
            and abs(line.size - last.size) <= 0.3
            and 0 < line.x0 - last.x1 <= 8 * line.size
            and not line.bullet
        ):
            rows[-1].append(line)
        else:
            rows.append([line])
    whole = [row[0] for row in rows if len(row) == 1]
    joined: list[_Line] = []
    for row in rows:
        if len(row) == 1:
            joined.append(row[0])
            continue
        first, final = row[0], row[-1]
        nearby = [
            other
            for other in whole
            if abs(other.x0 - first.x0) <= 2
            and abs(other.x1 - final.x1) <= 2
            and abs(other.size - first.size) <= 0.3
            and 0 < abs(other.y0 - first.y0) <= 4 * (first.y1 - first.y0)
        ]
        # Text wrapped beside a picture is narrower than a whole line: a fragment still continues the line when it
        # starts in lower case after one that does not end a sentence, under the same left margin as its neighbours.
        margin = any(
            abs(other.x0 - first.x0) <= 2 and 0 < abs(other.y0 - first.y0) <= 4 * (first.y1 - first.y0)
            for other in lines
            if other is not first
        )
        flowing = all(piece.text[:1].islower() and not _ends_sentence(before.text) for before, piece in pairwise(row))
        if not nearby and not (margin and flowing):
            joined.extend(row)
            continue
        text = " ".join(line.text for line in row)
        units = tuple(dict.fromkeys(unit for line in row for unit in line.units))
        top, bottom = min(piece.y0 for piece in row), max(piece.y1 for piece in row)
        merged = _Line(text, first.x0, top, final.x1, bottom, first.size, units)
        merged.bullet = first.bullet
        joined.append(merged)
    return joined


def _is_furniture(line: _Line, height: float) -> bool:
    text = line.text.strip()
    in_margin = line.y0 >= height * 0.94 or line.y1 <= height * 0.045
    if _PAGE_NUMBER.fullmatch(text):
        return True
    if (line.y0 >= height * 0.9 or line.y1 <= height * 0.08) and re.fullmatch(r"\d{1,3}", text):
        return True
    return in_margin and len(text) <= 120


def _bands(lines: list[_Line]) -> list[list[_Line]]:
    """Lines printed on the same baseline, top to bottom."""
    bands: list[list[_Line]] = []
    for line in sorted(lines, key=lambda line: (line.y0, line.x0)):
        if bands and line.y0 < max(other.y1 for other in bands[-1]) - 0.5 * (line.y1 - line.y0):
            bands[-1].append(line)
        else:
            bands.append([line])
    return [sorted(band, key=lambda line: line.x0) for band in bands]


def _column(line: _Line, starts: list[float], ends: list[float]) -> int | None:
    """The table column a line starts in and stays inside, if any."""
    for index, start in enumerate(starts):
        if abs(line.x0 - start) <= 2.5 and line.x1 <= ends[index] + 3:
            return index
    return None


def _find_table(lines: list[_Line], right: float) -> tuple[Table, list[_Line]] | None:
    """A grid under a header row of three or more columns, or bullet lists side by side under short headings."""
    for band in _bands(lines):
        if len(band) < 2 or any(line.bullet for line in band):
            continue
        if any(len(line.text) > 60 for line in band) or any(b.x0 - a.x1 < 6 for a, b in pairwise(band)):
            continue
        narrow = any(len(line.text) > 30 or len(line.text.split()) > 4 for line in band)
        if len(band) == 2 and (narrow or band[1].x0 - band[0].x1 < 40):
            continue
        starts = [line.x0 for line in band]
        ends = [*starts[1:], right + 40]
        top = band[0].y0
        members: list[tuple[_Line, int]] = []
        for line in sorted((line for line in lines if line.y0 >= top - 1), key=lambda line: (line.y0, line.x0)):
            index = _column(line, starts, ends)
            if index is None:
                break
            members.append((line, index))
        heights = sorted(line.y1 - line.y0 for line, _ in members)
        gap = 0.35 * heights[len(heights) // 2] if heights else 3.0
        rows: list[list[tuple[_Line, int]]] = []
        bottom = -1e9
        for line, index in members:
            # A new bullet in a column that already has text in this row starts the next row of the panels.
            bulleted = line.bullet and rows and any(other == index for _, other in rows[-1])
            if not rows or line.y0 > bottom + gap or bulleted:
                rows.append([])
                bottom = line.y1
            rows[-1].append((line, index))
            bottom = max(bottom, line.y1)
        panels = any(line.bullet for line, _ in members)
        first_column = [line.text for line, index in members if index == 0]
        if len(rows) < 3 or (len(starts) == 2 and not panels and max(map(len, first_column)) > 40):
            continue  # two columns of long lines are running text, not a table
        cells = []
        for row in rows:
            texts = [""] * len(starts)
            for line, index in sorted(row, key=lambda pair: (pair[0].y0, pair[0].x0)):
                texts[index] = join_lines(texts[index], line.text)
            cells.append(tuple(texts))
        body = [row for row in cells[1:] if sum(bool(cell) for cell in row) >= (1 if panels else 2)]
        if len(body) < 2:
            continue
        kind = "panels" if panels else "grid"
        return Table(header=cells[0], rows=tuple(body), kind=kind), [line for line, _ in members]
    return None


def _ruled_tables(page: pymupdf.Page, lines: list[_Line]) -> list[tuple[Table, list[_Line]]]:
    """Tables printed with ruled cell borders, read by PyMuPDF from the borders themselves.

    Wrapped cell text ("West Midlands," over "England") and empty-looking columns defeat the line-position reader in
    ``_find_table``; the drawn grid does not. Tables without borders still go to ``_find_table``.
    """
    try:
        found = page.find_tables().tables
    except Exception:  # an unusual drawing must never stop the sheet from being read
        return []
    tables = []
    for grid in found:
        cells = [[" ".join((cell or "").split()) for cell in row] for row in grid.extract()]
        cells = [row for row in cells if any(row)]
        filled = [column for column in range(len(cells[0]) if cells else 0) if any(row[column] for row in cells)]
        cells = [[row[column] for column in filled] for row in cells]  # border-only columns at the edges
        if len(cells) < 3 or len(cells[0]) < 3 or sum(bool(cell) for cell in cells[0]) < 3:
            continue
        box = pymupdf.Rect(grid.bbox)
        members = [line for line in lines if pymupdf.Point((line.x0 + line.x1) / 2, (line.y0 + line.y1) / 2) in box]
        if members:
            tables.append((Table(header=tuple(cells[0]), rows=tuple(map(tuple, cells[1:]))), members))
    return tables


def _find_timeline(lines: list[_Line]) -> tuple[Table, list[_Line]] | None:
    """Three or more years printed in a row, each with a short label centred above or below it."""
    bands = _bands(lines)
    for index, band in enumerate(bands):
        if len(band) < 3 or not all(_YEAR_LABEL.fullmatch(line.text) for line in band):
            continue
        height = max(line.y1 - line.y0 for line in band)
        near = [other for other in bands[max(0, index - 1) : index + 2] if other is not band]
        for labels in near:
            if len(labels) != len(band) or abs(labels[0].y0 - band[0].y0) > 4 * height:
                continue
            spacing = min(b.x0 - a.x0 for a, b in pairwise(band))
            centres = [(line.x0 + line.x1) / 2 for line in labels]
            pairs = []
            for year in band:
                middle = (year.x0 + year.x1) / 2
                nearest = min(range(len(labels)), key=lambda i: abs(centres[i] - middle))
                if abs(centres[nearest] - middle) > 0.35 * spacing or len(labels[nearest].text.split()) > 5:
                    break
                pairs.append((year.text, labels[nearest].text))
            if len(pairs) == len(band) and len({label for _, label in pairs}) == len(pairs):
                return Table(header=("Year", "Event"), rows=tuple(pairs), kind="timeline"), [*band, *labels]
    return None


def _layout_paragraphs(page: pymupdf.Page, pno: int, lines: list[_Line]) -> list[_Paragraph]:
    height = page.rect.height
    content = [line for line in lines if not _is_furniture(line, height)]
    if not content:
        return []
    right = sorted(line.x1 for line in content)[int(0.9 * (len(content) - 1))]
    left = sorted(line.x0 for line in content)[int(0.1 * (len(content) - 1))]
    tables: list[tuple[Table, list[_Line]]] = []
    remaining = content
    while (found := _find_timeline(remaining) or _find_table(remaining, right)) is not None:
        tables.append(found)
        used = {id(line) for line in found[1]}
        remaining = [line for line in remaining if id(line) not in used]
    # Where cells of a bordered table were left over as loose lines, the line reader lost the grid; read that table
    # from its drawn borders instead.
    # Only on a page where the line reader found a table: reading the borders of every map and drawing in a long
    # illustrated chapter costs more time and memory than the free host has.
    for ruled, members in _ruled_tables(page, content) if tables else []:
        inside = {id(line) for line in members}
        leaked = sum(id(line) in inside for line in remaining)
        if leaked < max(3, 0.25 * len(inside)):
            continue  # the line reader kept the table together; a stray caption inside the border is no reason
        tables = [table for table in tables if not inside & {id(line) for line in table[1]}]
        tables.append((ruled, members))
        remaining = [line for line in remaining if id(line) not in inside]
    remaining = _join_justified(remaining)  # after the tables: their cells are meant to stay apart

    gaps = [
        b.y0 - a.y1
        for a, b in pairwise(remaining)
        if abs(a.size - b.size) <= 0.3 and abs(a.x0 - b.x0) <= 3 and -1 <= b.y0 - a.y1 <= 10
    ]
    typical = median(gaps) if gaps else 3.0
    heights = [line.y1 - line.y0 for line in remaining] or [10.0]
    gap_limit = typical + max(2.0, 0.25 * median(heights))

    paragraphs: list[_Paragraph] = []
    current: _Paragraph | None = None
    early = right - max(80.0, 0.18 * (right - left))
    for line in remaining:
        # A caption printed beside a paragraph interleaves with its lines; the paragraph still takes its next line.
        earlier = [paragraph for paragraph in paragraphs[-4:] if paragraph is not current]
        resumed = next(
            (
                paragraph
                for paragraph in reversed(earlier)
                if abs(paragraph.size - line.size) <= 0.3
                and current is not None
                and abs(current.size - line.size) > 0.75
                and _continues(paragraph, line, gap_limit, right, early)
            ),
            None,
        )
        if resumed is not None and not (current is not None and _continues(current, line, gap_limit, right, early)):
            current = resumed
        if current is not None and _continues(current, line, gap_limit, right, early):
            current.text = join_lines(current.text, line.text)
            current.lines.append(line)
            current.bottom = max(current.bottom, line.y1)
            current.units.extend(unit for unit in line.units if unit not in current.units)
            continue
        current = _Paragraph(line.text, pno, list(line.units), line.bullet, line.size, line.y0, line.y1, lines=[line])
        paragraphs.append(current)
    paragraphs = _without_labels([part for paragraph in paragraphs for part in _split_inline(paragraph)])
    for table, members in tables:
        units: list[str] = []
        for line in members:
            units.extend(unit for unit in line.units if unit not in units)
        top, bottom = min(line.y0 for line in members), max(line.y1 for line in members)
        paragraphs.append(_Paragraph("", pno, units, top=top, bottom=bottom, table=table))
    paragraphs.sort(key=lambda paragraph: paragraph.top)
    return paragraphs


_BARE_NUMBER = re.compile(r"[\d.,]+")
LABEL_WORDS = 8


def _without_labels(paragraphs: list[_Paragraph]) -> list[_Paragraph]:
    """Drop the words printed inside a map, chart or timeline: they label a picture and are not sentences to learn.

    A bare number ("1520" on a chart's axis) is never a fact on its own. A label is a few words in a smaller type than
    the page's text, with no full stop, printed level with another such label.
    """
    weights: dict[float, int] = {}
    for paragraph in paragraphs:
        weights[paragraph.size] = weights.get(paragraph.size, 0) + len(paragraph.text)
    body = max(weights, key=weights.__getitem__, default=0.0)

    def small_words(paragraph: _Paragraph) -> bool:
        return (
            paragraph.size < body - 0.5
            and len(paragraph.text.split()) <= LABEL_WORDS
            and not _ends_sentence(paragraph.text)
        )

    candidates = [paragraph for paragraph in paragraphs if small_words(paragraph)]
    small = {id(paragraph) for paragraph in candidates}

    def label(paragraph: _Paragraph) -> bool:
        if _BARE_NUMBER.fullmatch(paragraph.text.strip()):
            return True
        return id(paragraph) in small and any(
            other is not paragraph and other.top < paragraph.bottom and paragraph.top < other.bottom
            for other in candidates
        )

    return [paragraph for paragraph in paragraphs if paragraph.table is not None or not label(paragraph)]


def _wraps(last: _Line, line: _Line) -> bool:
    """Text wrapped round a picture: the left edge moves, but the sentence runs on under the same right edge."""
    return abs(line.x1 - last.x1) <= 0.5 * line.size and line.text[:1].islower() and not _ends_sentence(last.text)


def _continues(paragraph: _Paragraph, line: _Line, gap_limit: float, right: float, early: float) -> bool:
    last, first = paragraph.lines[-1], paragraph.lines[0]
    if line.bullet or _MARKER.match(line.text) or _TIP.match(line.text) or abs(line.size - paragraph.size) > 0.75:
        return False
    if _ends_sentence(last.text) and line.text.endswith(":") and line.x1 < early:
        return False  # "… after they have died." then "When animals are alive:" heads what follows
    # Lines may overlap a little when their boxes are taller than the line spacing; a line on the same baseline may not.
    if (line.y0 < last.y1 - 2 and line.y0 - last.y0 < 0.6 * (last.y1 - last.y0)) or line.y0 - last.y1 > gap_limit:
        return False
    if _wraps(last, line):
        return True
    if any(abs(earlier.x0 - line.x0) <= 3 for earlier in paragraph.lines[1:]):
        first = line  # back under the left edge of the lines above, after text wrapped round a picture
    if line.x0 < first.x0 - 3:
        indented_first = (
            len(paragraph.lines) == 1
            and not first.bullet
            and not _MARKER.match(first.text)
            and first.x0 - line.x0 <= 40  # a first-line indent, not a centred line
        )
        if not (indented_first and not _ends_sentence(last.text)):
            return False
    if line.x0 > first.x0 + 40:
        return False
    # A line that stops well short of the margin was ended on purpose: a formula, a list line, a heading.
    # Narrow text (a caption, a box) has its own right edge: a lower-case line no wider than the last runs on from it.
    narrow = line.text[:1].islower() and not _ends_sentence(last.text) and line.x1 <= last.x1 + 3
    if last.x1 < early and not _CONTINUES_AFTER.search(last.text) and not narrow:
        return False
    # A short line that ends a sentence closes its paragraph.
    return not (_ends_sentence(last.text) and last.x1 < right - 40 and line.text[:1].isupper())


def _split_inline(paragraph: _Paragraph) -> list[_Paragraph]:
    """Items numbered on one line ("1. What causes evaporation?  2. How do clouds form?") become one item each.

    A label in front of the list ("Exercise 9.1: 1. Find …") becomes an item of its own.
    """
    first = _MARKER.match(paragraph.text)
    number = re.search(r"\d+", first["marker"]) if first else None
    cuts: list[int] = []
    if number is None:
        start = re.search(r"(?<=:)\s+(?:Q\s?)?1[.)]\s+(?=\S)", paragraph.text)
        if start is None:
            return [paragraph]
        cuts.append(start.start() + 1)
        number = re.search(r"1", start.group())
    expected = int(number.group()) + 1
    for match in _INLINE_MARKER.finditer(paragraph.text):
        if cuts and match.start() < cuts[0]:
            continue
        if int(match.group(1)) == expected and _ends_sentence(paragraph.text[: match.start()]):
            cuts.append(match.start())
            expected += 1
    if not cuts:
        return [paragraph]
    parts = []
    for start, end in pairwise([0, *cuts, len(paragraph.text)]):
        part = _Paragraph(paragraph.text[start:end].strip(), paragraph.page, list(paragraph.units), paragraph.bullet)
        part.size, part.top, part.bottom, part.lines = paragraph.size, paragraph.top, paragraph.bottom, paragraph.lines
        parts.append(part)
    return parts


def _page_pictures(source: bytes, page: pymupdf.Page, pno: int) -> list[Picture]:
    """Where pictures are printed, from the page's drawing log.

    The log names each image placement without decoding the image; asking PyMuPDF for image rectangles decodes every
    photo and map, which on a long illustrated chapter takes more memory than the free host has.
    """
    pictures: list[Picture] = []
    seen: set[tuple[int, ...]] = set()
    for kind, box in page.get_bboxlog():
        rect = pymupdf.Rect(box) & page.rect
        key = tuple(round(value) for value in rect)
        if "image" not in kind or rect.width < 24 or rect.height < 24 or key in seen:
            continue
        if rect.get_area() >= 0.6 * page.rect.get_area():
            continue  # a background printed under the whole page: its "picture" is the page itself
        seen.add(key)
        pictures.append(Picture(pno, tuple(rect), source))
    return pictures


# ---------------------------------------------------------------- fact inventory


def _inventory_paragraphs(inventory: FactInventory, pages: set[int] | None) -> list[_Paragraph]:
    paragraphs: list[_Paragraph] = []
    for fact in inventory.facts:
        if pages is not None and fact.page not in pages:
            continue
        statement = _FOOTER_TAIL.sub("", fact.statement)
        if _FOOTER.match(statement):
            continue
        # "… glucose + oxygen Question 3 Explain why …": the question's number goes on a line of its own.
        texts: list[str] = []
        for part in _RUN_IN_QUESTION.split(statement):
            label = _LEADING_QUESTION.match(part)
            texts.extend([label["label"], part[label.end() :]] if label else [part])
        for text in texts:
            heading = _LEADING_HEADING.match(text)
            if heading and _section_kind(heading.group()) and len(heading.group().split()) >= 2:
                paragraphs.append(_Paragraph(heading.group(), fact.page, [fact.source_unit_id]))
                text = text[heading.end() :].strip()
            if not text.strip():
                continue
            previous = paragraphs[-1] if paragraphs else None
            joins = (
                previous is not None
                and previous.page == fact.page
                and not previous.table
                and not _ends_sentence(previous.text)
                and not _QUESTION_NUMBER.match(previous.text)
                and text[:1] not in BULLETS
                and not _MARKER.match(text)
                and (text[:1].islower() or text[:1] in ")]," or bool(_CONTINUES_AFTER.search(previous.text)))
            )
            if joins:
                previous.text = join_lines(previous.text, text)
                if fact.source_unit_id not in previous.units:
                    previous.units.append(fact.source_unit_id)
                continue
            bullet = text[:1] in BULLETS
            paragraphs.append(
                _Paragraph(text.lstrip(BULLETS + " ") if bullet else text, fact.page, [fact.source_unit_id], bullet)
            )
    return paragraphs


# ---------------------------------------------------------------- structure


def summary_parts(text: str) -> tuple[str, str] | None:
    """ "Belfast = Shipbuilding & Titanic" → ("Belfast", "Shipbuilding & Titanic"); equations are not summaries."""
    match = _SUMMARY.match(text)
    if not match:
        return None
    name, rest = match["name"].strip(), match["rest"].strip()
    if len(name.split()) > 6 or not name[:1].isalpha() or re.search(r"[\d+×÷*/^<>:;=]", name):
        return None
    if rest[:1].isdigit() or re.search(r"[=×÷−^√²³]|\d\s*[/+]\s*\d", rest):
        return None  # "base = 8 cm" and "speed = frequency × wavelength" are measurements and formulas
    return name, rest


def names_topic(text: str) -> bool:
    """Whether a heading names a thing ("LONDON", "Dadabhai Naoroji – …") rather than a kind of content."""
    marker, body = split_marker(text)
    del marker
    if GENERIC_HEADING.match(body):
        return False
    name = re.split(r"\s+[–—-]\s+|:\s+|\s*\(", body, maxsplit=1)[0]
    return _upper_ratio(name) >= 0.75 or _title_case(name) or bool(re.match(r"[A-Z]\w*$", name))


def _heading_like(text: str) -> bool:
    formula = re.search(r"[=×÷√]", text)
    return len(text) <= 160 and not _ends_sentence(text) and summary_parts(text) is None and not formula


def _classify(paragraphs: list[_Paragraph]) -> list[Item]:
    items: list[Item] = []
    section = group = topic = context = ""
    started = False
    weights: dict[float, int] = {}
    for paragraph in paragraphs:
        if paragraph.size and paragraph.table is None:
            weights[paragraph.size] = weights.get(paragraph.size, 0) + len(paragraph.text)
    body_size = max(weights, key=weights.get) if weights else 0.0
    # Smaller print after the last line of main text is a credit or a note about the sheet itself ("Model answers
    # based on the textbook …"), not something to learn.
    last_body = max(
        (
            index
            for index, paragraph in enumerate(paragraphs)
            if paragraph.table is not None or not paragraph.size or paragraph.size >= body_size * 0.9
        ),
        default=-1,
    )
    # A model-answer sheet prints "Question 3" on its own line, then the question, then the answer's points.
    asked, asked_size = "", 0.0
    answering: int | None = None  # the question whose model answer is being read

    def add(kind: str, paragraph: _Paragraph, text: str, marker: str = "", note: str = "", **extra) -> None:
        text = text.strip()
        items.append(
            Item(
                kind,
                text,
                paragraph.page,
                tuple(paragraph.units),
                marker=marker,
                section=section,
                group=group,
                topic=topic if kind in {"point", "summary"} else "",
                context=(note or context) if kind in {"point", "summary", "question"} else "",
                top=paragraph.top,
                bottom=paragraph.bottom,
                **extra,
            )
        )

    for index, paragraph in enumerate(paragraphs):
        if paragraph.table is not None:
            started, topic, answering = True, "", None
            cells = [cell for row in (paragraph.table.header, *paragraph.table.rows) for cell in row if cell.strip()]
            numbered = [_NUMBERED_ANSWER.fullmatch(cell.strip()) for cell in cells]
            if section == "answers" and numbered and all(numbered):
                # An answer key printed in columns ("1. Renaissance   2. Reformation") is a list of answers.
                for found in numbered:
                    add("answer", paragraph, found["answer"], found["marker"])
                continue
            add("table", paragraph, "", table=paragraph.table)
            continue
        if index > last_body and body_size and paragraph.size and paragraph.size <= body_size * 0.85:
            continue
        marker, body = split_marker(paragraph.text)
        following = next((other for other in paragraphs[index + 1 :] if other.table is None), None)
        number = _QUESTION_NUMBER.match(paragraph.text.strip())
        if number and not paragraph.bullet:
            started, topic, context = True, "", ""
            asked, asked_size, answering = f"Question {number['number']}", paragraph.size, None
            continue
        if asked:
            label, asked = asked, ""
            if section == "answers":
                add("answer", paragraph, _LEADING_ANSWER.sub("", paragraph.text), label)
                answering = len(items) - 1
                continue
            if not paragraph.bullet and not marker:
                question, answer = _split_answer(paragraph.text)
                add("question", paragraph, question, label, answer=answer)
                answering = len(items) - 1 if section != "questions" else None
                continue
        if not started:
            # The sheet's title block: up to three unnumbered lines at the top of the first page.
            subtitle = bool(items) and items[-1].kind == "title" and bool(re.search(r"\s[|•]\s", body))
            title = (
                index <= 2
                and paragraph.page == paragraphs[0].page
                and not marker
                and not paragraph.bullet
                and not _ends_sentence(body)
                and following is not None
                and not following.bullet
                and (subtitle or _heading_like(split_marker(following.text)[1]))
            )
            if title:
                add("title", paragraph, body)
                continue
            started = True
        callout, note = _CALLOUT.match(body), ""
        if callout and _ends_sentence(body):
            note, body = callout["label"].strip(), body[callout.end() :]
        tip = _TIP.match(body)
        if tip and not marker:
            add("tip", paragraph, body[tip.end() :], marker=tip.group().strip(" :-–—"))
            continue
        task = _TASK.match(body)
        if task and not marker and section != "answers":
            question, answer = _split_answer(body[task.end() :])
            add("question", paragraph, question, answer=answer)
            continue
        in_lists = section in {"questions", "answers", "qa"}
        if in_lists and re.fullmatch(r"[A-H][.)]", marker) and _heading_like(body):
            group = marker[0]
            add("group", paragraph, body, marker)
            continue
        kind = _section_kind(body)
        upper = _upper_ratio(body) >= 0.75 and len(body) <= 120 and not paragraph.bullet
        words = len(body.split())
        # A questions section ends at the next chapter, or where ordinary prose resumes: a textbook prints
        # "Questions and activities" at the end of one chapter and the next chapter's text follows.
        chapter = bool(_CHAPTER.match(body)) or (
            bool(body_size) and paragraph.size >= body_size * 1.6 and _heading_like(body) and words <= 12
        )
        prose = (
            not marker
            and words >= 15
            and _ends_sentence(body)
            and not body.rstrip().endswith("?")
            and not _QUESTION_START.match(body)
            and (not body_size or abs(paragraph.size - body_size) <= body_size * 0.1)
        )
        if section == "questions" and answering is None and (chapter or prose):
            section, group, topic, context = "", "", "", ""
        elif chapter and section in {"answers", "qa"} and answering is None:
            section, group, topic, context = "", "", "", ""
        sized = bool(body_size) and paragraph.size >= body_size * 1.12 and words <= 12
        heading = _heading_like(body) and not paragraph.bullet
        shaped = heading and (upper or sized or (_title_case(body) and not marker) or (words <= 4 and not marker))
        # Inside a model answer only a heading as large as the question numbers starts something new.
        large = upper or not (paragraph.size and asked_size) or paragraph.size >= asked_size - 0.3
        if kind and shaped and (not (in_lists and marker) or (upper and kind != section)):
            if answering is None or large:
                section, group, topic, context, answering = kind, "", "", "", None
                add("section", paragraph, body, marker)
                continue
        sub_heading = heading and words <= 10 and body.endswith(":")
        if answering is not None and not (heading and large and not (sub_heading and not paragraph.size)):
            owner = items[answering]
            line = _LEADING_ANSWER.sub("", paragraph.text)
            if owner.kind == "question" and not owner.answer and not paragraph.bullet and body.endswith("?"):
                items[answering] = _extend(owner, paragraph, text=join_lines(owner.text, body))
                continue  # the question goes on: "… this statement." then "What does it tell you?"
            line = f"• {line}" if paragraph.bullet else line
            if owner.kind == "answer":
                items[answering] = _extend(owner, paragraph, text=f"{owner.text}\n{line}")
                continue
            items[answering] = _extend(owner, paragraph, answer=f"{owner.answer}\n{line}".strip())
            if sub_heading:
                context = body.rstrip(":").strip()  # "When animals are alive:" heads the points under it
            elif not _COMMENT.match(body):
                add("point", paragraph, body, marker, note)
            continue
        answering = None
        last = items[-1] if items else None
        # "1)" under a numbered answer is part of that answer, not a new one.
        sub_item = bool(_SUB_MARKER.match(paragraph.text)) and last is not None and last.marker.endswith(".")
        if section in {"questions", "qa"}:
            if marker and not (sub_item and last.kind == "question"):
                question, answer = _split_answer(body)
                add("question", paragraph, question, marker, answer=answer)
            elif last is not None and last.kind == "question" and (_LEADING_ANSWER.match(body) or sub_item):
                answer = _LEADING_ANSWER.sub("", paragraph.text) if not sub_item else paragraph.text
                items[-1] = _extend(last, paragraph, answer=join_lines(last.answer, answer))
            elif _QUESTION_START.match(body) and "?" in body:
                question, answer = _split_answer(body)
                add("question", paragraph, question, answer=answer)
            continue  # instructions such as "Answer the following questions:" make no card
        if section == "answers":
            if marker and not sub_item:
                add("answer", paragraph, body, marker)
            elif last is not None and last.kind == "answer":
                items[-1] = _extend(last, paragraph, text=join_lines(last.text, paragraph.text))
            continue
        if heading and section in {"", "notes", "tips", "table"}:
            next_marker = split_marker(following.text)[0] if following is not None else ""
            followed_by_point = following is not None and (
                following.bullet
                or (bool(marker) and not next_marker and not _heading_like(following.text))
                or (sized and not _heading_like(following.text))
            )
            if followed_by_point and names_topic(paragraph.text) and ";" not in body and words <= 14:
                section = "notes" if section == "table" else section  # notes can resume after a table
                topic, context = body, ""
                add("topic", paragraph, body, marker)
                continue
            if followed_by_point or upper or sized:
                # A sub-heading such as "Four main stages": it labels what follows but names no answer.
                section = "notes" if section == "table" else section
                topic, context = "", body
                add("heading", paragraph, body, marker)
                continue
        if summary_parts(body) is not None:
            add("summary", paragraph, body, marker, note)
        elif (
            re.match(r"Q(?:uestion)?\b", marker, re.I)
            or (_QUESTION_START.match(body) and "?" in body)
            or _ASKS_FOR_ANSWER.search(body)
        ):
            question, answer = _split_answer(body)
            add("question", paragraph, question, marker, note, answer=answer)
        elif section != "table":  # loose text around a table is usually a stray cell
            add("point", paragraph, body, marker, note)
    return items


def _split_answer(text: str) -> tuple[str, str]:
    parts = _INLINE_ANSWER.split(text, maxsplit=1)
    if len(parts) == 2 and _WRITE_IN.fullmatch(parts[1]):
        return parts[0].strip(), ""  # "… onward?  Answer: ________" leaves a line to write on, not a gap to fill
    if len(parts) == 2 and parts[1].strip():
        return parts[0].strip(), parts[1].strip()
    return text.strip(), ""


def _extend(item: Item, paragraph: _Paragraph, **changes) -> Item:
    units = tuple(dict.fromkeys([*item.unit_ids, *paragraph.units]))
    values = {**item.__dict__, "unit_ids": units, "bottom": max(item.bottom, paragraph.bottom), **changes}
    return Item(**values)


def read_sheet(inventory: FactInventory, source_pdf: bytes | None = None, pages: set[int] | None = None) -> Sheet:
    """Read the sheet from the PDF's printed layout, using the inventory for pages without a text layer."""
    if not source_pdf:
        return Sheet(tuple(_classify(_inventory_paragraphs(inventory, pages))))
    paragraphs: list[_Paragraph] = []
    pictures: list[Picture] = []
    with pymupdf.open(stream=source_pdf, filetype="pdf") as document:
        for page in document:
            pno = page.number + 1
            if pages is not None and pno not in pages:
                continue
            lines = _page_lines(page, pno)
            found = (
                _layout_paragraphs(page, pno, lines) if sum(len(line.text) for line in lines) >= MIN_PAGE_CHARS else []
            )
            paragraphs.extend(found or _inventory_paragraphs(inventory, {pno}))
            pictures.extend(_page_pictures(source_pdf, page, pno))
    return Sheet(tuple(_classify(_without_running_lines(paragraphs))), tuple(pictures))


def _running_key(text: str) -> str:
    """Page numbers aside, a header reads the same on every page; numbered questions do not."""
    return re.sub(r"\bpage\s+\d+(?:\s+of\s+\d+)?", "page #", " ".join(text.casefold().split()))


def _without_running_lines(paragraphs: list[_Paragraph]) -> list[_Paragraph]:
    """Drop page headers and footers: short lines printed on two or more pages ("Page 1 of 2" counts as one)."""
    pages: dict[str, set[int]] = {}
    for paragraph in paragraphs:
        if len(paragraph.text.split()) <= 14:
            pages.setdefault(_running_key(paragraph.text), set()).add(paragraph.page)
    running = {key for key, found in pages.items() if len(found) >= 2}
    return [paragraph for paragraph in paragraphs if _running_key(paragraph.text) not in running]
