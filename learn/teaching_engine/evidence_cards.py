"""Detective Mode case papers: everyday-scene Evidence cards written by a model, checked against the sheet.

The card format and the model's recipe come from the owner's Detective Mode prototype (a separate Next.js app,
``src/lib/paper/prompts.ts`` and ``validate.ts``): a short everyday title, 2-3 sentences of evidence in a scene a
child can picture, one direct-but-curious question, and a 1-2 word answer kept on a sealed key.

Unlike the prototype, the model writes cards from the sheet's numbered lines (no separate concept-map call) and code
checks each card against the sheet, not just its format:

- every card names the line(s) it teaches, and its answer must be printed in one of them;
- every line of the sheet is taught by some card;
- the answer never appears in the card's title, evidence or question;
- 1-3 word answers, a question ending in "?", 1-4 evidence sentences, text that fits the printed card.

A sheet whose cards break a rule goes back to the model once with the problems listed. If it still fails, or no
model is available, that sheet's cards are made from the rule-based study cards for the same lines, so the set is
always complete. The evidence sentences themselves are the model's own words: code checks their answer and source
line, not every fact in them, and the answer key names the source lines so a parent can check.
"""

import re
from dataclasses import dataclass, field

import pymupdf

from .ai_cards import KIND_WORDS
from .cards import _ORANGE, _PAGE_HEIGHT, _PAGE_WIDTH, _Type, plan_cards
from .detective import Fact

TASK = "write_evidence_cards"
CARDS_PER_SHEET = 8
LINES_PER_SHEET = 9  # sheet lines the model turns into one sheet of cards: about one card per line
MAX_LINES_PER_CARD = 2  # a card teaches one concept; two lines only when they say the same thing
MAX_ANSWER_WORDS = 3
MAX_EVIDENCE_WORDS = 45  # what fits a printed card at a readable size
MAX_QUESTION_WORDS = 22

SYSTEM = f"""You are the bureau's printable case-paper writer for Class 7-8 students. You turn curriculum sheets into
printable detective cards that a child solves with paper and pencil: read the card, think, write an answer, check the
separate key.

THE CARD RECIPE (non-negotiable):
1. ONE CONCEPT PER CARD. Never stack several facts or concepts onto one card.
2. EVIDENCE: exactly 2-3 short, clear sentences. Everyday words. If a sentence feels long, split it or cut it.
3. FAMILIAR SITUATIONS: cold bottles, puddles, mirrors, village wells, cooking pots, school bags, rain, taps,
   grandmothers, cricket. Everyday life only. Historical or civic facts still get a scene a child can picture.
4. QUESTION: direct but curious, exactly one sentence ending with "?". Model: "The bottle is sealed, yet drops appear
   outside. Where did the water come from?"
5. ANSWER: 1-2 words, at most 3 for a name (e.g. "Condensation", "River Thames", "Harland and Wolff"), copied exactly
   as printed in one of the card's lines. The question must lead straight to that answer.
6. SIMPLE LANGUAGE: the child already has a whole chapter to learn, so a card must add no reading load. Write for a
   tired 12-year-old: everyday words a Class 5 child knows, one idea per sentence, about 10-12 words per sentence,
   warm and friendly. Retell the lines in your own easy words; never copy hard words like "preeminent", "apparatus",
   "metropolitan" or "prominence" onto a card. Only the answer must match the lines exactly.
7. SUPPLEMENTARY FACTS: small extra facts from the lines (numbers, names, side notes) are folded into a related card's
   evidence, never given their own filler card.
8. NO FABRICATION: every fact must come from the lines. Do not invent statistics, people, dates or processes.
9. COVERAGE: teach every important concept on the sheet, not a summary of it. Write ONE CARD PER LINE; join two
   lines on one card only when they say the same thing, never more than two. Each card lists the ids of the lines
   it teaches, and every line must be taught by a card.

EXAMPLES of the style (from a Water chapter):
- "The Sweating Bottle". Evidence: "A cold bottle of water sits on the table, still sealed. Nobody has opened it. Yet
  tiny drops of water slowly appear all over the outside." Question: "The bottle is sealed, yet drops appear
  outside. Where did the water come from?" Answer: "Water vapour".
- "The Vanishing Puddle". Evidence: "After the morning rain, a wide puddle lies in the courtyard. By afternoon it has
  shrunk to a wet patch. By evening the ground is dry." Question: "Nobody wiped the puddle away. What is this quiet
  disappearing act called?" Answer: "Evaporation".
- "The Well That Digs Deeper". Evidence: "Grandfather says the village well found water at twenty feet in his
  youth. Today the diggers go down sixty. Each summer, the well fills slower." Question: "What is the hidden level
  below which the ground stays soaked with water called?" Answer: "Water table".

SELF-CHECK: the answer words must NOT appear in the card's title, evidence or question.

Reply with one JSON object only, no commentary:
{{"case_title": "The Case of ...", "cards": [{{"lines": ["F3"], "title": "3-6 everyday words", "evidence": "2-3
sentences.", "question": "One sentence?", "answer": "1-2 words from the lines", "key_why": "One short sentence: why
the answer follows."}}]}}
Use at most {CARDS_PER_SHEET} cards."""


@dataclass(frozen=True)
class EvidenceCard:
    number: int
    title: str
    evidence: str
    question: str
    answer: str
    key_why: str
    lines: tuple[str, ...]
    page: int
    by_model: bool = True
    topic: str = ""


@dataclass
class EvidenceSet:
    title: str
    sheets: list[list[EvidenceCard]]
    notes: list[str] = field(default_factory=list)
    model_sheets: int = 0
    facts: dict[str, Fact] = field(default_factory=dict)


def _norm(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.casefold()).strip()


def _contains(haystack: str, needle: str) -> bool:
    return bool(needle) and f" {_norm(needle)} " in f" {_norm(haystack)} "


def check_card(card: dict, facts: dict[str, Fact], allowed: list[str]) -> list[str]:
    """Every rule one model card breaks."""
    where = f"Card “{card.get('title') or '?'}”"
    problems = []
    lines = card.get("lines")
    if not isinstance(lines, list) or not lines or any(line not in allowed for line in lines):
        return [f"{where}: “lines” must list ids of lines on this sheet."]
    texts = {key: card.get(key) for key in ("title", "evidence", "question", "answer", "key_why")}
    for key, value in texts.items():
        if not isinstance(value, str) or not value.strip():
            problems.append(f"{where}: missing {key}.")
    if problems:
        return problems
    answer = texts["answer"].strip()
    words = answer.split()
    name = all(word[:1].isupper() or word.casefold() in {"and", "of", "the"} for word in words)
    if len(words) > MAX_ANSWER_WORDS or (len(words) == MAX_ANSWER_WORDS and not name):
        problems.append(f"{where}: the answer “{answer}” must be 1-2 words (3 only for a name).")
    if not any(_contains(facts[line].text, answer) or _contains(facts[line].suspect, answer) for line in lines):
        problems.append(f"{where}: the answer “{answer}” is not printed in its lines {', '.join(lines)}.")
    front = f"{texts['title']} {texts['evidence']} {texts['question']}"
    hints = {word.casefold() for word in KIND_WORDS}  # "Which river…?" may hint at "River Thames"
    leaked = [word for word in _norm(answer).split() if len(word) >= 4 and word not in hints and _contains(front, word)]
    if _contains(front, answer) or leaked:
        problems.append(f"{where}: the answer “{answer}” appears on the card front.")
    if not texts["question"].strip().endswith("?"):
        problems.append(f"{where}: the question must end with “?”.")
    sentences = len([part for part in re.split(r"[.!?]+", texts["evidence"]) if len(part.strip()) > 3])
    if not 1 <= sentences <= 4:
        problems.append(f"{where}: evidence should be 2-3 short sentences (found {sentences}).")
    if len(texts["title"].split()) > 7:
        problems.append(f"{where}: the title should be 3-6 words.")
    if len(texts["evidence"].split()) > MAX_EVIDENCE_WORDS:
        problems.append(f"{where}: the evidence is too long; keep it to {MAX_EVIDENCE_WORDS} words.")
    if len(texts["question"].split()) > MAX_QUESTION_WORDS:
        problems.append(f"{where}: the question is too long; keep it to {MAX_QUESTION_WORDS} words.")
    return problems


def _cards_from(reply, facts: dict[str, Fact], lines: list[str]) -> tuple[list[dict], list[str]]:
    cards = reply.get("cards") if isinstance(reply, dict) else None
    if not isinstance(cards, list) or not cards:
        return [], ['The reply has no "cards" list.']
    problems = [
        problem for card in cards for problem in check_card(card if isinstance(card, dict) else {}, facts, lines)
    ]
    if len(cards) > CARDS_PER_SHEET:
        problems.append(f"{len(cards)} cards; use at most {CARDS_PER_SHEET}.")
    least = min(CARDS_PER_SHEET, len(lines)) - 1
    if len(cards) < least:
        problems.append(f"Only {len(cards)} cards for {len(lines)} lines; write at least {least}, one per line.")
    for card in cards:
        if isinstance(card, dict) and len(card.get("lines") or []) > MAX_LINES_PER_CARD:
            problems.append(f"Card “{card.get('title')}” teaches {len(card['lines'])} lines; one concept per card.")
    taught = {line for card in cards if isinstance(card, dict) for line in card.get("lines") or []}
    missing = [line for line in lines if line not in taught]
    if missing:
        problems.append("These lines are taught by no card: " + ", ".join(missing) + ".")
    answers = [_norm(card.get("answer", "")) for card in cards if isinstance(card, dict)]
    if len(set(answers)) != len(answers):
        problems.append("Two cards have the same answer; give each card its own concept.")
    return cards, problems


def _plain_cards(sheet, facts: dict[str, Fact], lines: list[str], standard: int) -> list[dict]:
    """Cards for these lines from the rule-based study cards, when no model card set passed."""
    units = {unit for line in lines for unit in facts[line].unit_ids}
    by_unit = {unit: line for line in lines for unit in facts[line].unit_ids}
    made = []
    for card in plan_cards(sheet, standard):
        shared = [unit for unit in card.unit_ids if unit in units]
        if not shared or not card.answer:
            continue
        made.append(
            {
                "lines": list(dict.fromkeys(by_unit[unit] for unit in shared)),
                "title": card.about or "Case file",
                "evidence": card.clue,
                "question": card.question,
                "answer": card.answer,
                "key_why": "From the sheet.",
            }
        )
    covered = {line for card in made for line in card["lines"]}
    for line in lines:
        if line not in covered and (plain := _line_card(facts[line])):
            made.append(plain)
    return made


def _line_card(fact: Fact) -> dict | None:
    """A plain card for one line: its date, number or name hidden, or the topic it is about."""
    from .detective import _hidden, _name_gap, _value_gap

    card = {"lines": [fact.id], "key_why": "From the sheet."}
    gap = _value_gap(fact) or _name_gap(fact, (fact.suspect,))
    if gap:
        _, answer, shown = gap
        title, question = fact.suspect or "Case file", "What goes in the gap?"
        return {**card, "title": title, "evidence": shown, "question": question, "answer": answer}
    if fact.suspect:
        question = "Which topic is this line about?"
        return {**card, "title": "Who or what is this?", "evidence": _hidden(fact), "question": question,
                "answer": fact.suspect}  # fmt: skip
    return None


def write_case_papers(sheet, llm=None, standard: int = 8, limit: int | None = None) -> EvidenceSet:
    """The sheet's lines as Evidence cards, 8 to a sheet, model-written where they pass every check."""
    from .ai_cards import study_lines

    facts_list, topics = study_lines(sheet)
    if not facts_list:
        raise ValueError("No lines were found on this sheet to make Detective cards from.")
    facts = {fact.id: fact for fact in facts_list}
    ids = [fact.id for fact in facts_list]
    groups = [ids[start : start + LINES_PER_SHEET] for start in range(0, len(ids), LINES_PER_SHEET)]
    result = EvidenceSet("The Case of the Study Sheet", [], facts=facts)
    reachable, asked = llm is not None, 0
    raw_sheets: list[tuple[list[dict], bool]] = []
    for lines in groups:
        cards: list[dict] = []
        if reachable and (limit is None or asked < limit):
            asked += 1
            listing = "\n".join(f"{line} [{facts[line].suspect or '-'}] {facts[line].text}" for line in lines)
            prompt = f"TOPICS: {', '.join(topics) or '-'}\n\nLINES:\n{listing}"
            try:
                reply = llm.json(TASK, SYSTEM, prompt)
                cards, problems = _cards_from(reply, facts, lines)
                if problems:
                    listed = "\n".join(f"- {problem}" for problem in problems)
                    retry = (
                        f"{prompt}\n\nYour cards broke these rules. Fix only these problems and reply with the full "
                        f"set again.\n{listed}\n\nYOUR CARDS:\n{cards}"
                    )
                    reply = llm.json(TASK, SYSTEM, retry)
                    cards, problems = _cards_from(reply, facts, lines)
                if not problems:
                    if isinstance(reply, dict) and isinstance(reply.get("case_title"), str) and not result.sheets:
                        result.title = reply["case_title"].strip()[:70] or result.title
                    raw_sheets.append((cards, True))
                    result.model_sheets += 1
                    result.sheets.append([])
                    continue
                result.notes.append(
                    f"Lines {lines[0]}–{lines[-1]}: the model's cards broke the rules twice, so plain cards are used."
                )
            except Exception as error:  # noqa: BLE001 - any model failure falls back to plain cards
                reachable = False
                result.notes.append(f"The model could not be used ({error}); plain cards are used.")
        raw_sheets.append((_plain_cards(sheet, facts, lines, standard), False))
        result.sheets.append([])
    number = 0
    for index, (cards, by_model) in enumerate(raw_sheets):
        made = []
        for card in cards:
            number += 1
            lines = tuple(card["lines"])
            made.append(
                EvidenceCard(
                    number,
                    card["title"].strip(),
                    re.sub(r"\s+", " ", card["evidence"]).strip(),
                    re.sub(r"\s+", " ", card["question"]).strip(),
                    card["answer"].strip(),
                    card["key_why"].strip(),
                    lines,
                    facts[lines[0]].page,
                    by_model,
                    facts[lines[0]].suspect,
                )
            )
        result.sheets[index] = made
    # Plain cards for a group of lines can run past eight; they continue on the next sheet.
    result.sheets = [
        cards[start : start + CARDS_PER_SHEET]
        for cards in result.sheets
        for start in range(0, len(cards), CARDS_PER_SHEET)
    ]
    if limit is not None and asked < len(groups) and reachable:
        result.notes.append(f"The model was asked about {asked} of {len(groups)} sheets (limit {limit}).")
    return result


# Printing, in the look of the owner's Detective Mode case papers: cream paper, maroon typewriter headings, cards with
# a topic tag and a shaded question strip, and after each sheet a sealed answer key with a score guide.

_PAPER = (0.98, 0.965, 0.95)
_MAROON = (0.50, 0.20, 0.17)
_ROSE = (0.95, 0.85, 0.82)
_RULE = (0.80, 0.62, 0.58)
_TEXT = (0.20, 0.17, 0.16)
_SOFT = (0.45, 0.40, 0.38)
_TYPE, _TYPE_BOLD = "cour", "cobo"  # Courier: the case-file typewriter
_TYPEWRITER = {False: pymupdf.Font(_TYPE), True: pymupdf.Font(_TYPE_BOLD)}
_MARGIN, _TOP = 36.0, 108.0
_COLUMNS, _ROWS = 2, 4
_CARD_W = (_PAGE_WIDTH - 2 * _MARGIN) / _COLUMNS
_CARD_H = (_PAGE_HEIGHT - _TOP - 30) / _ROWS
SCORES = (("all right", "CASE CLOSED", "a true detective"), ("most right", "SHARP EYE", "reread a card or two"),
          ("a few right", "KEEP GOING", "read the little stories again, slowly"))  # fmt: skip


def _typed(shape, text: str, size: float, x: float, y: float, colour, bold: bool = True, spaced: bool = False) -> float:
    """Typewriter text at (x, baseline y); ``spaced`` letter-spaces small labels. Returns the text's width."""
    font = _TYPEWRITER[bold]
    if spaced:
        text = " ".join(text)
    shape.insert_text((x, y), text, fontname=_TYPE_BOLD if bold else _TYPE, fontsize=size, color=colour)
    return font.text_length(text, fontsize=size)


def _typed_fit(text: str, width: float, largest: float, smallest: float = 7.0) -> float:
    size = largest
    while size > smallest and _TYPEWRITER[True].text_length(text, fontsize=size) > width:
        size -= 0.5
    return size


def _fits(kind: _Type, text: str, box: pymupdf.Rect, largest: float, smallest: float, bold: bool):
    """(size, lines) at the largest size that fits; raises when even the smallest size would cut the text."""
    size, lines = kind.fit(text, box, largest, smallest, bold)
    if lines and lines[-1].endswith(" …") and not text.endswith("…"):
        raise ValueError(f"Card text is too long to print: {text[:60]}…")
    return size, lines


def _paper(document, kind: _Type):
    page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
    kind.prepare(page)
    shape = page.new_shape()
    shape.draw_rect(page.rect)
    shape.finish(color=None, fill=_PAPER)
    return page, shape


def _page_header(shape, kind: _Type, label: str, title: str, right: str, sub: str, intro: str) -> None:
    _typed(shape, label, 7.5, _MARGIN, 40, _MAROON, spaced=True)
    _typed(shape, title, _typed_fit(title, _PAGE_WIDTH - 2 * _MARGIN - 150, 19), _MARGIN, 64, _MAROON)
    width = _TYPEWRITER[True].text_length(right, fontsize=10)
    _typed(shape, right, 10, _PAGE_WIDTH - _MARGIN - width, 44, _MAROON)
    kind.draw(shape, [kind.printable(sub)], 7.5, 0, 50, False, _SOFT, align_right=_PAGE_WIDTH - _MARGIN)
    lines = kind.wrap(kind.printable(intro), 8.5, _PAGE_WIDTH - 2 * _MARGIN)
    kind.draw(shape, lines, 8.5, _MARGIN, 74, False, _SOFT)


def _footer(shape, kind: _Type, text: str) -> None:
    shape.draw_line((_MARGIN, _PAGE_HEIGHT - 26), (_PAGE_WIDTH - _MARGIN, _PAGE_HEIGHT - 26))
    shape.finish(color=_RULE, width=0.6)
    line = kind.printable(" ".join(text.upper()))
    width = kind.width(line, 6.5)
    kind.draw(shape, [line], 6.5, (_PAGE_WIDTH - width) / 2, _PAGE_HEIGHT - 22, False, _SOFT)


def _box(position: int) -> pymupdf.Rect:
    column, row = position % _COLUMNS, position // _COLUMNS
    x, y = _MARGIN + column * _CARD_W, _TOP + row * _CARD_H
    return pymupdf.Rect(x, y, x + _CARD_W, y + _CARD_H)


def _draw_card(shape, kind: _Type, card: EvidenceCard, box: pymupdf.Rect) -> None:
    inner = box + (12, 10, -12, -8)
    _typed(shape, f"CARD {card.number:02d}", 9.5, inner.x0, inner.y0 + 9, _TEXT)
    if card.topic:
        tag = kind.printable(" ".join(card.topic.upper()[:18]), True)
        width = kind.width(tag, 6.5, True) + 12
        pill = pymupdf.Rect(inner.x1 - width, inner.y0 - 1, inner.x1, inner.y0 + 12)
        shape.draw_rect(pill)
        shape.finish(color=_RULE, fill=_ROSE, width=0.5)
        kind.draw(shape, [tag], 6.5, pill.x0 + 6, pill.y0 + 1.5, True, _MAROON)
    title = card.title.upper()
    _typed(shape, title, _typed_fit(title, inner.width, 9.5), inner.x0, inner.y0 + 23, _MAROON)
    _typed(shape, "EVIDENCE", 6, inner.x0, inner.y0 + 33, _SOFT, spaced=True)
    strip = pymupdf.Rect(box.x0 + 0.5, box.y1 - 52, box.x1 - 0.5, box.y1 - 0.5)
    shape.draw_rect(strip)
    shape.finish(color=None, fill=_ROSE)
    evidence_box = pymupdf.Rect(inner.x0, inner.y0 + 36, inner.x1, strip.y0 - 3)
    size, lines = _fits(kind, card.evidence, evidence_box, 9.5, 7, False)
    kind.draw(shape, lines, size, evidence_box.x0, evidence_box.y0, False, _TEXT)
    question_box = pymupdf.Rect(inner.x0 + 12, strip.y0 + 5, inner.x1, strip.y1 - 16)
    size, lines = _fits(kind, card.question, question_box, 8.5, 6.5, True)
    _typed(shape, "Q.", 8.5, inner.x0, question_box.y0 + size, _MAROON)
    kind.draw(shape, lines, size, question_box.x0, question_box.y0, True, _TEXT)
    kind.draw(shape, ["Y O U R   A N S W E R"], 6, inner.x0, strip.y1 - 13, True, _SOFT)
    shape.draw_line((inner.x0 + 72, strip.y1 - 6), (inner.x1, strip.y1 - 6))
    shape.finish(color=_SOFT, width=0.6, dashes="[2 1] 0")


def _stamp(shape, text: str, centre: pymupdf.Point) -> None:
    width = _TYPEWRITER[True].text_length(text, fontsize=16) + 24
    box = pymupdf.Rect(centre.x - width / 2, centre.y - 15, centre.x + width / 2, centre.y + 15)
    turn = pymupdf.Matrix(-4)
    shape.draw_quad(box.quad.morph(centre, turn))
    shape.finish(color=_MAROON, width=1.6)
    shape.insert_text((box.x0 + 12, centre.y + 5.5), text, fontname=_TYPE_BOLD, fontsize=16, color=_MAROON,
                      morph=(centre, turn))  # fmt: skip


def _key_page(document, kind: _Type, papers: EvidenceSet, index: int, cards: list[EvidenceCard]) -> None:
    total = len(papers.sheets)
    page, shape = _paper(document, kind)
    _page_header(
        shape,
        kind,
        "DETECTIVE MODE · CASE PAPERS",
        f"Answer Key · Sheet {index}",
        f"SHEET {index} OF {total}",
        papers.title,
        "For the parent. Keep this page folded away; open it only after every answer is written down.",
    )
    y, width = 104.0, _PAGE_WIDTH - 2 * _MARGIN - 40
    for card in cards:
        why = kind.wrap(kind.printable(card.key_why), 8, width)
        source = "; ".join(f"p. {papers.facts[line].page}: {papers.facts[line].text}" for line in card.lines)
        proof = kind.wrap(kind.printable(f"Sheet says: {source}"), 6.5, width)
        if y + 34 + 9.8 * len(why) + 8 * len(proof) > _PAGE_HEIGHT - 150:
            break  # eight rows fit; this only guards unusually long source lines
        number = pymupdf.Rect(_MARGIN, y + 2, _MARGIN + 22, y + 20)
        shape.draw_rect(number)
        shape.finish(color=_RULE, fill=_ROSE, width=0.5)
        _typed(shape, f"{card.number:02d}", 8.5, number.x0 + 4, number.y0 + 12.5, _MAROON, bold=False)
        _typed(shape, card.title.upper()[:48], 6.5, _MARGIN + 34, y + 7, _MAROON, bold=False, spaced=False)
        answer_width = _typed(shape, card.answer, 12, _MARGIN + 34, y + 21, _TEXT)
        shape.draw_line((_MARGIN + 40 + answer_width, y + 21), (_PAGE_WIDTH - _MARGIN, y + 21))
        shape.finish(color=_RULE, width=0.5, dashes="[1 1.5] 0")
        y = kind.draw(shape, why, 8, _MARGIN + 34, y + 25, False, _SOFT)
        y = kind.draw(shape, proof, 6.5, _MARGIN + 34, y, False, _SOFT) + 5
        shape.draw_line((_MARGIN, y), (_PAGE_WIDTH - _MARGIN, y))
        shape.finish(color=_RULE, width=0.5)
        y += 4
    base = _PAGE_HEIGHT - 140
    _typed(shape, "YOUR SCORE", 9, _MARGIN, base, _TEXT, spaced=True)
    for row, (got, rank, advice) in enumerate(SCORES):
        line = base + 16 + row * 15
        _typed(shape, got, 8.5, _MARGIN, line, _MAROON, bold=False)
        kind.draw(shape, [rank], 8.5, _MARGIN + 92, line - 8.5, True, _TEXT)
        kind.draw(shape, [kind.printable(advice)], 8, _MARGIN + 190, line - 8, False, _SOFT)
    if index == total:
        _stamp(shape, "CASE CLOSED", pymupdf.Point(_PAGE_WIDTH - _MARGIN - 90, base + 22))
        if papers.notes:
            notes = [line for note in papers.notes for line in kind.wrap(kind.printable(note), 7, width)][:3]
            kind.draw(shape, notes, 7, _MARGIN, base + 62, False, _ORANGE)
    _footer(shape, kind, f"Detective Mode · {papers.title} · sheet {index} of {total} · every clue from the sheet")
    shape.commit()


def render_case_papers_pdf(papers: EvidenceSet) -> bytes:
    """Each sheet's cards on one page (one-sided), then its sealed answer key on the next."""
    kind = _Type()
    document = pymupdf.open()
    total = len(papers.sheets)
    for index, cards in enumerate(papers.sheets, start=1):
        page, shape = _paper(document, kind)
        topics = list(dict.fromkeys(card.topic for card in cards if card.topic))
        _page_header(
            shape,
            kind,
            "DETECTIVE MODE · CASE PAPERS",
            papers.title if index == 1 else f"{papers.title} · {index}",
            f"SHEET {index} OF {total}",
            " · ".join(topics)[:70],
            "Read each little story. Think for a moment. Write your answer in one or two words. "
            "The key waits on the next page, so no peeking.",
        )
        for position, card in enumerate(cards):
            box = _box(position)
            shape.draw_rect(box)
            shape.finish(color=_RULE, width=0.6, dashes="[2 2] 0")
            _draw_card(shape, kind, card, box)
        shape.commit()
        _key_page(document, kind, papers, index, cards)
    document.set_metadata({"title": "Learn ICSE Standard 8 detective case papers", "author": "Learn Teaching Engine"})
    if kind.embedded:
        document.subset_fonts()
    result = document.tobytes(garbage=4, deflate=True)
    document.close()
    return result
