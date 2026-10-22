"""Let a model choose the Detective cards, while code keeps every word on them from the sheet.

The rule-based planner (``detective.py``) still decides everything around the cards: the suspects, how the sheet's
lines are cut into card sheets, the culprit and the Big Clues. For each card sheet, the model is shown only that
sheet's numbered lines (and the case's earlier sheet, for review) and picks the cards: which lines each card tests
and which words to hide. It never writes card text itself. Code builds every card from the sheet's own words,
exactly as the rule-based cards are built, so the printed cards look the same and pass the same checks.

A sheet whose cards break a rule goes back to the model once, with the problems listed. If it still fails, or the
model cannot be reached, that sheet keeps its rule-based cards and the run says so. Nothing is ever printed
without passing ``check_case_file``.
"""

import re
from dataclasses import dataclass, field, replace

from .detective import (
    _BLANK,
    _TIME,
    _WRITE,
    GAP,
    LABELS,
    MAX_FILLS,
    SHEET_CARDS,
    TASKS,
    WHICH_ONE_LINES,
    WHO_LINES,
    CaseCard,
    CaseFile,
    CaseSheet,
    Fact,
    _hidden,
    _ordered,
    _Planner,
    _when,
    sheet_problems,
)

TASK = "write_cards"
STUDY_CARDS = 8  # cards on one printed study-card sheet
STUDY_LINES = 12  # sheet lines the model is shown at once for study cards
MAX_HIDDEN_WORDS = 6  # the most words a gap may hide
# The first word of a name that says what kind of place it is; it stays on the card as a hint ("River ____").
KIND_WORDS = frozenset("River Mount Mt Lake Sea Ocean Bay Gulf Cape Fort Port Lord Sir Mahatma".split())
AI_KINDS = ("match", "which", "pick", "timeline", "fill", "number", "who", "finish", "mistake")


def system_prompt(count: int, game: str, review: bool) -> str:
    """The model's instructions for choosing ``count`` cards for one sheet."""
    review_rule = (
        '- Lines under EARLIER SHEET may appear only in "which" and "mistake" cards, as review.\n' if review else ""
    )
    return f"""You choose the cards for one sheet of {game} for Indian school children in Standard 7-8.

The child studies a sheet of numbered lines. Each line belongs to a topic (a city, a person, a process); the topic is
in square brackets. You choose {count} cards that help the child remember every line. Code prints them using the
sheet's own words, so you never write a clue or an answer yourself: you only say which lines a card uses and which
words of a line to hide. Copy any words you hide exactly as they appear in the line, with the same capitals and
punctuation.

Rules:
- Every line under THIS SHEET must be used by at least one card.
- Use at least 5 different kinds when the lines allow. At most {MAX_FILLS} "fill" cards and at most 2 cards of any
  other kind.
- Hide what a child should remember: a name, place, term, date, number or key phrase of 1-{MAX_HIDDEN_WORDS} words.
  Never hide small words such as "the", "major" or "one".
- Leave a kind word such as "River" or "Mount" showing as a hint: hide "Thames", not "River Thames".
- A timeline event must contain its date or period ("in 1905", "in the 18th century", "in the medieval period").
- "match", "which", "who" and "mistake" need lines of at least two topics.
{review_rule}
Card kinds (JSON):
- {{"kind": "match", "lines": [2-4 ids of different topics]}}: the child matches each topic to its line.
- {{"kind": "which", "lines": [2-{WHICH_ONE_LINES} ids, at least 2 topics]}}: the child names whose line each is.
- {{"kind": "pick", "line": id, "hide": "words", "wrong": [2-3 other words from the sheet of the same kind]}}
- {{"kind": "fill", "line": id, "hide": "words"}}
- {{"kind": "timeline", "events": [{{"line": id, "words": "part of the line"}}, ...]}}: 2-4 events, earliest first.
- {{"kind": "number", "line": id, "number": "a number printed in the line"}}: the child says what it counts.
- {{"kind": "who", "lines": [2-{WHO_LINES} ids of one topic]}}: the child names the topic from its lines.
- {{"kind": "finish", "line": id, "shown": "the first words of the line"}}: the child finishes the sentence.
- {{"kind": "mistake", "line": id, "wrong_name": "another topic"}}: the line is printed under the wrong name.

Reply with one JSON object only: {{"cards": [ ... up to {count} cards ... ]}}"""


SYSTEM = system_prompt(SHEET_CARDS - 1, "a Detective study game", review=True)
STUDY_SYSTEM = system_prompt(STUDY_CARDS, "study cards", review=False)

EXAMPLE = """Example, for a sheet with these lines:
L1 [London] Situated on the River Thames in southeastern England.
L2 [London] Continues to serve as the financial centre of Europe and a centre of innovation.
L3 [Birmingham] The industrial steam engine (one of the most important inventions in British history) was invented here.
L4 [Birmingham] Was a market town in the medieval period; grew to international prominence in the 18th century.
L5 [Birmingham] Birmingham Hippodrome is the UK's busiest theatre (over 520,000 visitors each year).
Good cards include:
{"kind": "fill", "line": "L1", "hide": "Thames"}
{"kind": "pick", "line": "L2", "hide": "Europe", "wrong": ["England", "Wales"]}
{"kind": "fill", "line": "L3", "hide": "steam engine"}
{"kind": "timeline", "events": [{"line": "L4", "words": "Was a market town in the medieval period"},
  {"line": "L4", "words": "grew to international prominence in the 18th century"}]}
{"kind": "number", "line": "L5", "number": "520,000"}
{"kind": "mistake", "line": "L2", "wrong_name": "Birmingham"}"""


class CardError(ValueError):
    pass


@dataclass
class AIResult:
    case_file: CaseFile
    notes: list[str] = field(default_factory=list)
    ai_sheets: int = 0
    sheets: int = 0


class _Builder:
    """Turns one model card choice into a printed card, refusing anything not made of the sheet's own words."""

    def __init__(self, facts: dict[str, Fact], lines: tuple[str, ...], review: tuple[str, ...], suspects):
        self.facts, self.lines, self.review, self.suspects = facts, lines, review, tuple(suspects)
        self.source = " \n ".join(fact.text for fact in facts.values()).casefold()

    def line(self, value, review: bool = False) -> Fact:
        allowed = (*self.lines, *self.review) if review else self.lines
        if value not in allowed:
            raise CardError(f"line {value!r} is not on this sheet")
        return self.facts[value]

    def lines_of(self, values, least: int, most: int, review: bool = False) -> list[Fact]:
        if not isinstance(values, list) or not least <= len(values) <= most or len(set(values)) != len(values):
            raise CardError(f"needs {least}-{most} different lines")
        return [self.line(value, review) for value in values]

    def hide(self, fact: Fact, words) -> tuple[str, str]:
        """(line with the words hidden, the hidden words). "River Thames" hides only "Thames", keeping the hint."""
        if not isinstance(words, str) or not words.strip() or words not in fact.text:
            raise CardError(f"“{words}” is not in line {fact.id} as printed")
        first, _, rest = words.partition(" ")
        if first in KIND_WORDS and rest:
            words = rest
        if len(words.split()) > MAX_HIDDEN_WORDS or len(words.split()) * 2 > len(fact.text.split()):
            raise CardError(f"“{words}” hides too much of line {fact.id}")
        return fact.text.replace(words, _BLANK, 1), words

    def build(self, spec: dict) -> CaseCard:
        kind = spec.get("kind") if isinstance(spec, dict) else None
        if kind not in AI_KINDS:
            raise CardError(f"unknown kind {kind!r}")
        return getattr(self, kind)(spec)

    def match(self, spec) -> CaseCard:
        chosen = self.lines_of(spec.get("lines"), 2, 4)
        if len({fact.suspect for fact in chosen}) != len(chosen):
            raise CardError("a MATCH card needs lines of different suspects")
        names = [fact.suspect for fact in chosen]
        descriptions = [_hidden(fact) for fact in chosen]
        shown = descriptions[1:] + descriptions[:1]
        letters = "ABCD"
        lines = [f"{number}. {name}{_WRITE}" for number, name in enumerate(names, start=1)]
        lines += [f"{letters[index]}. {text}" for index, text in enumerate(shown)]
        answer = [
            f"{number} → {letters[shown.index(text)]}: {names[number - 1]} – {text}"
            for number, text in enumerate(descriptions, start=1)
        ]
        covers = tuple(fact.id for fact in chosen)
        return CaseCard("match", TASKS["match"], tuple(lines), tuple(answer), covers, chosen[0].page)

    def which(self, spec) -> CaseCard:
        chosen = self.lines_of(spec.get("lines"), 2, WHICH_ONE_LINES, review=True)
        if len({fact.suspect for fact in chosen}) < 2 or not any(fact.id in self.lines for fact in chosen):
            raise CardError("a WHICH ONE? card needs two suspects and a line of this sheet")
        own = {self.facts[line].suspect for line in self.lines}
        options = sorted({fact.suspect for fact in chosen} | own)
        lines = [f"{number}. {_hidden(fact)}{_WRITE}" for number, fact in enumerate(chosen, start=1)]
        lines.append("Choose from: " + " · ".join(options))
        answer = [f"{number}. {fact.suspect}" for number, fact in enumerate(chosen, start=1)]
        covers = tuple(fact.id for fact in chosen)
        return CaseCard("which", TASKS["which"], tuple(lines), tuple(answer), covers, chosen[0].page)

    def pick(self, spec) -> CaseCard:
        fact = self.line(spec.get("line"))
        line, hidden = self.hide(fact, spec.get("hide"))
        wrong = spec.get("wrong")
        if not isinstance(wrong, list) or not 2 <= len(wrong) <= 3:
            raise CardError("a PICK ONE card needs 2-3 wrong choices")
        for choice in wrong:
            if not isinstance(choice, str) or choice.casefold() not in self.source:
                raise CardError(f"the choice “{choice}” is not on the sheet")
            if choice.casefold() == hidden.casefold():
                raise CardError("a wrong choice is the answer")
        options = sorted({hidden, *wrong}, key=str.casefold)
        choices = "   ".join(f"({letter}) {option}" for letter, option in zip("abcd", options, strict=False))
        answer = (f"{hidden}: {fact.text}",)
        return CaseCard("pick", TASKS["pick"], (line, choices), answer, (fact.id,), fact.page, fact.suspect)

    def fill(self, spec) -> CaseCard:
        fact = self.line(spec.get("line"))
        line, hidden = self.hide(fact, spec.get("hide"))
        answer = (f"{hidden}: {fact.text}",)
        return CaseCard("fill", TASKS["fill"], (line,), answer, (fact.id,), fact.page, fact.suspect)

    def timeline(self, spec) -> CaseCard:
        events = spec.get("events")
        if not isinstance(events, list) or not 2 <= len(events) <= 4:
            raise CardError("a TIMELINE card needs 2-4 events")
        texts, times, chosen = [], [], []
        for event in events:
            fact = self.line(event.get("line") if isinstance(event, dict) else None)
            words = event.get("words")
            if not isinstance(words, str) or words not in fact.text or len(words.split()) < 3:
                raise CardError(f"a TIMELINE event is not part of line {fact.id} as printed")
            when = _TIME.search(words)
            if not when:
                raise CardError(f"the TIMELINE event “{words}” has no date or period, so its order is not on the sheet")
            texts.append(words.strip().rstrip(".;"))
            times.append(_when(when))
            chosen.append(fact)
        if times != sorted(times):
            raise CardError("the TIMELINE events are not earliest first")
        suspects = {fact.suspect for fact in chosen}
        about = chosen[0].suspect if len(suspects) == 1 else ""
        shown = list(reversed(texts))
        lines = [f"(    ) {text.replace(about, GAP) if about else text}".replace(GAP, _BLANK) for text in shown]
        answer = tuple(f"{number}. {text}" for number, text in enumerate(texts, start=1))
        covers = tuple(dict.fromkeys(fact.id for fact in chosen))
        return CaseCard("timeline", TASKS["timeline"], tuple(lines), answer, covers, chosen[0].page, about)

    def number(self, spec) -> CaseCard:
        fact = self.line(spec.get("line"))
        value = spec.get("number")
        if not isinstance(value, str) or not re.search(r"\d", value) or value not in fact.text:
            raise CardError(f"“{value}” is not a number printed in line {fact.id}")
        return CaseCard(
            "number", TASKS["number"], (value,), (fact.text,), (fact.id,), fact.page, fact.suspect, write_lines=2
        )

    def who(self, spec) -> CaseCard:
        chosen = self.lines_of(spec.get("lines"), 2, WHO_LINES)
        if len({fact.suspect for fact in chosen}) != 1:
            raise CardError("a WHO AM I? card needs lines of one suspect")
        if len({self.facts[line].suspect for line in self.lines}) < 2:
            raise CardError("a WHO AM I? card needs two suspects on the sheet")
        lines = tuple(f"Clue {number}: {_hidden(fact)}" for number, fact in enumerate(chosen, start=1))
        covers = tuple(fact.id for fact in chosen)
        return CaseCard("who", TASKS["who"], lines, (chosen[0].suspect,), covers, chosen[0].page, write_lines=1)

    def finish(self, spec) -> CaseCard:
        fact = self.line(spec.get("line"))
        shown = spec.get("shown")
        if not isinstance(shown, str) or not fact.text.startswith(shown) or len(shown.split()) < 2:
            raise CardError(f"“{shown}” is not how line {fact.id} starts")
        rest = fact.text[len(shown) :].strip()
        if len(rest.split()) < 2:
            raise CardError(f"FINISH IT leaves too little of line {fact.id} to write")
        answer = (f"… {rest}", f"The sheet says: {fact.text}")
        return CaseCard(
            "finish", TASKS["finish"], (f"{shown.strip()} …",), answer, (fact.id,), fact.page, fact.suspect, 1
        )

    def mistake(self, spec) -> CaseCard:
        fact = self.line(spec.get("line"), review=True)
        wrong = spec.get("wrong_name")
        if wrong not in self.suspects or wrong == fact.suspect:
            raise CardError("SPOT THE MISTAKE needs another suspect's name")
        if any(re.search(rf"\b{re.escape(name)}\b", fact.text, re.I) for name in self.suspects):
            raise CardError(f"line {fact.id} names a suspect, which gives the answer away")
        answer = (f"{fact.suspect}, not {wrong}. The sheet says: {fact.text}",)
        return CaseCard(
            "mistake", TASKS["mistake"], (f"{wrong}: {fact.text}",), answer, (fact.id,), fact.page, write_lines=1
        )


def sheet_prompt(case_file: CaseFile, case_sheet: CaseSheet, suspects) -> str:
    """Only this sheet's lines and the case's earlier sheet: never the rest of the chapter."""
    facts = case_file.facts

    def listing(ids) -> str:
        return "\n".join(f"{line} [{facts[line].suspect}] {facts[line].text}" for line in ids)

    parts = [EXAMPLE, f"SUSPECTS: {', '.join(suspects)}", f"THIS SHEET:\n{listing(case_sheet.lines)}"]
    if case_sheet.review:
        parts.append(f"EARLIER SHEET:\n{listing(case_sheet.review)}")
    return "\n\n".join(parts)


def _cards_from(case_file: CaseFile, case_sheet: CaseSheet, suspects, reply: dict, where: str):
    """(cards, problems) for one model reply."""
    builder = _Builder(case_file.facts, case_sheet.lines, case_sheet.review, suspects)
    specs = reply.get("cards") if isinstance(reply, dict) else None
    if not isinstance(specs, list):
        return (), ['The reply has no "cards" list.']
    cards, problems = [], []
    for number, spec in enumerate(specs, start=1):
        try:
            cards.append(builder.build(spec))
        except CardError as error:
            problems.append(f"Card {number}: {error}.")
    own = [case_file.facts[line] for line in case_sheet.lines]
    planner = _Planner([])
    cards.append(planner.notes(own))
    ordered = tuple(_ordered(cards))
    problems += sheet_problems(ordered, case_file.facts, where)
    kinds = [card.kind for card in ordered]
    for kind in set(kinds) - {"fill", "notes"}:
        if kinds.count(kind) > 2:
            problems.append(f"{where}: {kinds.count(kind)} {LABELS[kind]} cards, more than 2.")
    covered = {fact for card in ordered for fact in card.covers}
    missing = [line for line in case_sheet.lines if line not in covered]
    if missing:
        problems.append("These lines are on no card: " + ", ".join(missing) + ".")
    return ordered, problems


def write_with_model(case_file: CaseFile, llm, limit: int | None = None) -> AIResult:
    """The case file with each sheet's cards chosen by the model where they pass every check.

    ``limit`` caps how many sheets the model is asked about (two calls at most each); the others keep their
    rule-based cards. It keeps test runs cheap.
    """
    result = AIResult(case_file)
    asked = 0
    cases = []
    reachable = True
    for case in case_file.cases:
        sheets = []
        for number, case_sheet in enumerate(case.sheets, start=1):
            where = f"Case {case.number}, sheet {number}"
            result.sheets += 1
            if not reachable or not case_sheet.lines or (limit is not None and asked >= limit):
                sheets.append(case_sheet)
                continue
            asked += 1
            prompt = sheet_prompt(case_file, case_sheet, case.suspects)
            cards, problems = (), ["not asked"]
            try:
                reply = llm.json(TASK, SYSTEM, prompt)
                cards, problems = _cards_from(case_file, case_sheet, case.suspects, reply, where)
                if problems:
                    listed = "\n".join(f"- {problem}" for problem in problems)
                    retry = f"{prompt}\n\nYour cards had these problems. Choose the cards again.\n{listed}"
                    cards, problems = _cards_from(
                        case_file, case_sheet, case.suspects, llm.json(TASK, SYSTEM, retry), where
                    )
            except Exception as error:  # noqa: BLE001 - any model failure falls back to the rule-based cards
                reachable = False
                result.notes.append(f"The model could not be used ({error}); the rule-based cards are printed.")
                sheets.append(case_sheet)
                continue
            if problems:
                result.notes.append(
                    f"{where}: the model's cards failed checks twice, so the rule-based cards are printed."
                )
                sheets.append(case_sheet)
            else:
                result.ai_sheets += 1
                sheets.append(replace(case_sheet, cards=cards))
        cases.append(replace(case, sheets=tuple(sheets)))
    if limit is not None and asked < result.sheets and reachable:
        result.notes.append(f"The model was asked about {asked} of {result.sheets} sheets (limit {limit}).")
    result.case_file = replace(case_file, cases=tuple(cases))
    return result


# Study cards: the same choices, printed as the site's study cards.

STUDY_TASK = "write_study_cards"
# The one plain question printed in each study card's strip.
STUDY_QUESTIONS = {
    "match": "Which description goes with each name?",
    "which": "Whose fact is each one?",
    "pick": "Which word fills the gap?",
    "timeline": "What is the right order?",
    "fill": "What goes in the gap?",
    "number": "What does this number count?",
    "who": "Who or what is this?",
    "finish": "How does this sentence end?",
    "mistake": "Which name is wrong?",
}


@dataclass
class StudyResult:
    cards: list
    notes: list[str] = field(default_factory=list)
    ai_sheets: int = 0
    sheets: int = 0


def _table_lines(table) -> list[str]:
    """One line per table row (or per panel item), in the table's own words: "Trial B: Force: 1.00 N; Mass: 0.50 kg"."""

    def filled(cell: str) -> bool:
        return bool(cell.strip()) and cell.strip() not in {"—", "–", "-"}

    header = list(table.header)
    if table.kind == "panels":  # bullet lists side by side under short headings
        cells = [(header[col], row[col]) for row in table.rows for col in range(min(len(header), len(row)))]
        return [f"{name}: {cell}" for name, cell in cells if filled(cell)]
    lines = []
    for row in table.rows:
        if not row or not filled(row[0]):
            continue
        pairs = [f"{name}: {cell}" for name, cell in zip(header[1:], row[1:], strict=False) if filled(cell)]
        if table.kind == "timeline" or not any(header[1:]):
            pairs = [cell for cell in row[1:] if filled(cell)]
        if pairs:
            lines.append(f"{row[0]}: {'; '.join(pairs)}")
    return lines


def study_lines(sheet) -> tuple[list[Fact], tuple[str, ...]]:
    """The sheet's lines with their topics: the Detective suspects when there are two. Otherwise every point,
    every table row and every practice question printed with its answer, so a sheet whose facts sit in tables or
    model answers is covered too."""
    from .detective import _display, suspects_from

    suspects = suspects_from(sheet)
    if len(suspects) >= 2:
        return [fact for suspect in suspects for fact in suspect.facts], tuple(s.name for s in suspects)
    from .cards import parse_heading

    facts: list[Fact] = []
    points = {item.text.strip() for item in sheet.items if item.kind in {"point", "summary"}}

    def add(topic: str, text: str, item) -> None:
        facts.append(Fact(f"F{len(facts) + 1}", topic, text, item.page, unit_ids=item.unit_ids))

    for item in sheet.items:
        topic = _display(parse_heading(item.topic).name) if item.topic else ""
        if item.kind in {"point", "summary"} and item.text.strip():
            add(topic, item.text, item)
        elif item.kind == "table" and item.table is not None:
            for line in _table_lines(item.table):
                add(topic or item.context, line, item)
        elif item.kind == "question" and item.answer.strip():
            answers = [line.strip(" •-") for line in item.answer.splitlines() if line.strip(" •-")]
            if answers and not any(answer in points for answer in answers):  # model answers already read as points
                add(topic, f"{item.text} Answer: {' '.join(answers)}", item)
    return facts, tuple(dict.fromkeys(fact.suspect for fact in facts if fact.suspect))


def _study_card(card: CaseCard, facts: dict[str, Fact]):
    """A model-chosen card in the study cards' form: one plain question, the sheet's words, a short answer."""
    from .cards import GAP as CARD_GAP
    from .cards import Card

    if card.kind in {"fill", "pick"}:
        answer = card.answer[0].split(": ", 1)[0]
    elif card.kind == "mistake":
        answer = card.answer[0].split(". ", 1)[0]
    elif card.kind in {"number", "finish"}:
        answer = card.answer[0]
    else:
        answer = "; ".join(card.answer)
    units = tuple(dict.fromkeys(unit for line in card.covers if line in facts for unit in facts[line].unit_ids))
    clue = "\n".join(card.lines).replace(_BLANK, CARD_GAP)
    return Card(f"ai_{card.kind}", STUDY_QUESTIONS[card.kind], clue, answer, card.page, units, card.about)


def _study_from(facts: dict[str, Fact], lines: list[str], suspects, reply: dict):
    """(cards, problems) for one model reply about one group of lines."""
    builder = _Builder(facts, tuple(lines), (), suspects)
    specs = reply.get("cards") if isinstance(reply, dict) else None
    if not isinstance(specs, list):
        return [], ['The reply has no "cards" list.']
    built, problems = [], []
    for number, spec in enumerate(specs, start=1):
        try:
            built.append(builder.build(spec))
        except CardError as error:
            problems.append(f"Card {number}: {error}.")
    kinds = [card.kind for card in built]
    if len(built) > STUDY_CARDS:
        problems.append(f"{len(built)} cards, more than {STUDY_CARDS}.")
    for kind in set(kinds):
        most = MAX_FILLS if kind == "fill" else 2
        if kinds.count(kind) > most:
            problems.append(f"{kinds.count(kind)} {LABELS[kind]} cards, more than {most}.")
    covered = {line for card in built for line in card.covers}
    missing = [line for line in lines if line not in covered]
    if missing:
        problems.append("These lines are on no card: " + ", ".join(missing) + ".")
    return [_study_card(card, facts) for card in built], problems


def write_study_cards(sheet, llm, limit: int | None = None, standard: int = 8) -> StudyResult:
    """The sheet's study cards, with each group of lines' cards chosen by the model where they pass every check.

    The rule-based cards are planned first. Each group of up to ``STUDY_LINES`` lines the model handles replaces the
    rule-based cards made from the same source units; tables, practice questions and any group the model fails on
    keep their rule-based cards.
    """
    from .cards import plan_cards

    rule_cards = plan_cards(sheet, standard)
    facts, suspects = study_lines(sheet)
    by_id = {fact.id: fact for fact in facts}
    ids = [fact.id for fact in facts]
    groups = [ids[start : start + STUDY_LINES] for start in range(0, len(ids), STUDY_LINES)]
    result = StudyResult(rule_cards, sheets=len(groups))
    chosen: dict[int, list] = {}
    asked = 0
    for number, lines in enumerate(groups):
        if limit is not None and asked >= limit:
            break
        asked += 1
        listing = "\n".join(f"{line} [{by_id[line].suspect or '-'}] {by_id[line].text}" for line in lines)
        prompt = f"{EXAMPLE}\n\nTOPICS: {', '.join(suspects) or '-'}\n\nTHIS SHEET:\n{listing}"
        try:
            cards, problems = _study_from(by_id, lines, suspects, llm.json(STUDY_TASK, STUDY_SYSTEM, prompt))
            if problems:
                listed = "\n".join(f"- {problem}" for problem in problems)
                retry = f"{prompt}\n\nYour cards had these problems. Choose the cards again.\n{listed}"
                cards, problems = _study_from(by_id, lines, suspects, llm.json(STUDY_TASK, STUDY_SYSTEM, retry))
        except Exception as error:  # noqa: BLE001 - any model failure keeps the rule-based cards
            result.notes.append(f"The model could not be used ({error}); the rule-based cards are printed.")
            break
        if problems:
            result.notes.append(
                f"Lines {lines[0]}–{lines[-1]}: the model's cards failed checks twice; rule-based cards kept."
            )
        else:
            chosen[number] = cards
    units = {number: {unit for line in groups[number] for unit in by_id[line].unit_ids} for number in chosen}
    merged, placed = [], set()
    for card in rule_cards:
        group = next((number for number, used in units.items() if used & set(card.unit_ids)), None)
        if group is None:
            merged.append(card)
        elif group not in placed:
            merged.extend(chosen[group])
            placed.add(group)
    for number in chosen:
        if number not in placed:
            merged.extend(chosen[number])
    result.cards, result.ai_sheets = merged, len(chosen)
    if limit is not None and len(chosen) < len(groups):
        result.notes.append(
            f"The model chose the cards for {len(chosen)} of {len(groups)} groups of lines (limit {limit})."
        )
    return result
