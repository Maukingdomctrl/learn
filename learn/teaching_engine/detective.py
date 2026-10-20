"""Turn a study sheet into a Detective Case File: one-sided card sheets that build up to a mystery.

The design is in ``docs/DETECTIVE_GAME.md``. Each topic on the sheet (a city, a person, a process) is a suspect.
A card sheet holds eight cards; when the child gets all eight right, the parent reads out a Big Clue about the
hidden culprit. Two sheets make a case: two Big Clues, and the child names the culprit with proof from the sheet.

Two rules decide the cards:

- **Rule A, full coverage:** every point and topic heading on the sheet is tested by at least one card.
- **Rule B, variety:** at most two fill-the-gap cards a sheet, never the same type twice in a row, recognising
  before recalling before producing, and free recall (case notes) last.

Every clue is a line of the sheet with words hidden behind a gap. The one exception is SPOT THE MISTAKE, which
prints a point under another suspect's name for the child to correct; the answer sheet gives the line as printed.
``check_case_file`` enforces all of this, and ``render_case_file_pdf`` prints nothing that fails it.
"""

import re
from dataclasses import dataclass, field

import pymupdf

from .cards import (
    _CARDS_PER_PAGE,
    _INK,
    _LEFT,
    _MUTED,
    _ORANGE,
    _PAGE_HEIGHT,
    _PAGE_WIDTH,
    _QUANTITY,
    _THEMES,
    _YEAR,
    GAP,
    _card_box,
    _cut_lines,
    _finish,
    _gap,
    _hide_name,
    _Type,
    parse_heading,
    reject_generated_pdf,
)
from .facts import FactInventory
from .sheet import Sheet, read_sheet

SHEET_CARDS = _CARDS_PER_PAGE  # cards on one printed sheet; all must be right to earn a Big Clue
CASE_SHEETS = 2  # sheets in one case
MAX_FILLS = 2  # fill-the-gap cards allowed on one sheet
MAX_SAME = 2  # cards of any one type allowed on one sheet
SHEET_FACTS = 12  # lines one sheet aims to cover; sheets are sized evenly around this
WHICH_ONE_LINES = 4  # points on one WHICH ONE? card
WHO_LINES = 3  # clues on one WHO AM I? card
NOTES_FACTS = 3  # facts asked for on the CASE NOTES card
VARIETY_PENALTY = 1.5  # facts a card must cover over another type to be chosen again on the same sheet

LABELS = {
    "match": "MATCH",
    "which": "WHICH ONE?",
    "pick": "PICK ONE",
    "timeline": "TIMELINE",
    "fill": "FILL THE GAP",
    "number": "NUMBER DETECTIVE",
    "who": "WHO AM I?",
    "finish": "FINISH IT",
    "mistake": "SPOT THE MISTAKE",
    "notes": "CASE NOTES",
}
# The fixed instruction printed under each card's label; the only words on a card not taken from the sheet.
TASKS = {
    "match": "Match each name to its description. Write the letter beside the number.",
    "which": "Whose fact is it? Write the name after each one.",
    "timeline": "Number these from 1 (earliest) to the latest.",
    "mistake": "One name is wrong. Cross it out and write the right name.",
    "pick": "Circle the word that fills the gap.",
    "fill": "Write the missing word or number in the gap.",
    "number": "What does this number count? Write it below.",
    "who": "Read the clues. Which suspect is this?",
    "finish": "Finish the sentence from your sheet.",
    "notes": "Without looking at your sheet, write {count} facts about {suspect}.",
}
# Recognise (0) before recall (1) before produce (2); case notes (3) close every sheet.
STAGE = {
    "match": 0,
    "which": 0,
    "pick": 0,
    "timeline": 1,
    "fill": 1,
    "number": 1,
    "who": 1,
    "finish": 1,
    "mistake": 2,
    "notes": 3,
}
_BLANK = "________"
_WRITE = "  → ______"  # where the child writes a name or letter after a line
_RUN = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*")
# A time that dates an event: "in the 18th century", "in 1905", "until the early 19th century", "in the medieval
# period". A number in brackets ("(2011 census)") or a word like "medieval tenements" does not.
_TIME = re.compile(
    r"\b(?:in|until|by|from)\s+(?:the\s+)?(?:(?P<part>early|mid|late|latter half of the)[\s-]+)?"
    r"(?:(?P<century>\d{1,2})(?:st|nd|rd|th)\s+century|(?P<year>1[0-9]{3}|20[0-9]{2})\b|(?P<medieval>medieval)\s+period)",
    re.I,
)
_PART = {"early": 15, "mid": 50, "late": 85, "latter half of the": 75}


@dataclass(frozen=True)
class Fact:
    """One line the case must cover: a topic's heading description or one of its points, as printed."""

    id: str
    suspect: str
    text: str
    page: int
    heading: bool = False


@dataclass(frozen=True)
class Suspect:
    name: str
    facts: tuple[Fact, ...]


@dataclass(frozen=True)
class CaseCard:
    kind: str
    task: str  # the fixed instruction printed under the card's label
    lines: tuple[str, ...]  # what the card shows, in the sheet's words with gaps
    answer: tuple[str, ...]  # the answer-sheet entry
    covers: tuple[str, ...]  # ids of the facts the card tests
    page: int
    about: str = ""  # the suspect a card is about, when the card names it
    write_lines: int = 0  # ruled lines to write on

    @property
    def label(self) -> str:
        return LABELS[self.kind]


@dataclass(frozen=True)
class BigClue:
    text: str  # a culprit's point with its name hidden
    fact: str  # id of the point


@dataclass(frozen=True)
class CaseSheet:
    cards: tuple[CaseCard, ...]
    clue: BigClue
    lines: tuple[str, ...] = ()  # ids of the sheet's own lines, which its cards must cover
    review: tuple[str, ...] = ()  # ids of the case's earlier sheet, which its cards may bring back


@dataclass(frozen=True)
class Case:
    number: int
    suspects: tuple[str, ...]
    culprit: str
    sheets: tuple[CaseSheet, ...]


@dataclass(frozen=True)
class CaseFile:
    suspects: tuple[Suspect, ...]
    cases: tuple[Case, ...]
    facts: dict[str, Fact] = field(default_factory=dict)


def _display(name: str) -> str:
    return name.title() if name.isupper() and len(name) > 3 else name


def suspects_from(sheet: Sheet) -> list[Suspect]:
    """The sheet's topics, each with its heading description and its points, in reading order."""
    order: list[str] = []
    headings: dict[str, tuple[str, int]] = {}
    points: dict[str, list[tuple[str, int]]] = {}
    for item in sheet.items:
        if item.kind == "topic":
            order.append(item.text)
            headings[item.text] = (item.text, item.page)
            points.setdefault(item.text, [])
        elif item.kind == "point" and item.topic in headings:
            points[item.topic].append((item.text, item.page))
    suspects, number = [], 0
    for topic in order:
        heading = parse_heading(topic)
        name = _display(heading.name)
        facts = []
        description = re.sub(r"^\s*(?:[–—-]|:)\s*", "", heading.after).strip()
        if description:
            number += 1
            facts.append(Fact(f"F{number}", name, _hide_name(description, name), headings[topic][1], True))
        for text, page in points[topic]:
            number += 1
            facts.append(Fact(f"F{number}", name, text, page))
        if len(facts) >= 2:
            suspects.append(Suspect(name, tuple(facts)))
    return suspects


def _hidden(fact: Fact) -> str:
    """The line with its suspect's name hidden, so it never gives the answer away."""
    return _hide_name(fact.text, fact.suspect).replace(GAP, _BLANK)


def _runs(text: str) -> list[re.Match[str]]:
    """Capitalised names inside a line, not its first word: "River Thames", "West Midlands", "Europe"."""
    return [match for match in _RUN.finditer(text) if match.start() > 0]


def _name_gap(fact: Fact, names: tuple[str, ...]) -> tuple[str, str, str] | None:
    """(prefix, answer, line with the answer hidden): the last word of a name in the line, keeping its first words.

    "Situated on the River Thames" → ("River", "Thames", "Situated on the River ________").
    """
    for match in _runs(fact.text):
        words = match.group().split()
        if any(word.casefold() in {name.casefold() for name in names} for word in words):
            continue
        answer = words[-1]
        start = match.end() - len(answer)
        return " ".join(words[:-1]), answer, f"{fact.text[:start]}{_BLANK}{fact.text[match.end() :]}"
    return None


def _value_gap(fact: Fact) -> tuple[str, str, str] | None:
    found = _gap(fact.text)
    if not found or found[0] == "word":
        return None
    kind, answer, clue = found
    return kind, answer, clue.replace(GAP, _BLANK)


class _Planner:
    def __init__(self, suspects: list[Suspect]) -> None:
        self.names = tuple(suspect.name for suspect in suspects)
        self.all_facts = [fact for suspect in suspects for fact in suspect.facts]
        self.review: list[Fact] = []  # the case's earlier sheet, which WHICH ONE? and SPOT THE MISTAKE mix in
        self.reviewed: dict[str, int] = {}  # how often each review line has been used on this sheet

    # Each builder makes one card from the sheet's facts, testing uncovered facts first, or returns None.

    def match(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        headings = sorted((fact for fact in facts if fact.heading), key=lambda fact: fact.id not in todo)[:4]
        if len(headings) < 2:
            return None
        headings.sort(key=lambda fact: fact.id)
        names = [fact.suspect for fact in headings]
        descriptions = [fact.text.replace(GAP, _BLANK) for fact in headings]
        shown = descriptions[1:] + descriptions[:1]  # never beside its own name
        letters = "ABCD"
        lines = [f"{number}. {name}{_WRITE}" for number, name in enumerate(names, start=1)]
        lines += [f"{letters[index]}. {text}" for index, text in enumerate(shown)]
        answer = [f"{number} → {letters[shown.index(text)]}: {names[number - 1]} – {text}"
                  for number, text in enumerate(descriptions, start=1)]  # fmt: skip
        return CaseCard(
            "match",
            TASKS["match"],
            tuple(lines),
            tuple(answer),
            tuple(fact.id for fact in headings),
            headings[0].page,
        )

    def which(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        points = sorted((fact for fact in facts if len(fact.text.split()) <= 18), key=lambda fact: fact.id not in todo)
        chosen, seen = [], set()
        for fact in points:  # one from each suspect first, so the card is a real choice
            if fact.suspect not in seen and len(chosen) < WHICH_ONE_LINES:
                chosen.append(fact)
                seen.add(fact.suspect)
        for fact in points:
            if fact not in chosen and len(chosen) < WHICH_ONE_LINES:
                chosen.append(fact)
        if len(seen) < 2:  # one suspect on this sheet: one line from the case's earlier sheet makes it a choice
            review = [fact for fact in self.review if fact.suspect not in seen and len(fact.text.split()) <= 18]
            if not review or not chosen:
                return None
            pick = min(review, key=lambda fact: (self.reviewed.get(fact.id, 0), fact.id))
            chosen = [*chosen[: WHICH_ONE_LINES - 1], pick]
        if not any(fact.id in todo for fact in chosen):
            return None
        chosen.sort(key=lambda fact: fact.id)
        options = sorted({fact.suspect for fact in chosen} | {fact.suspect for fact in facts})
        lines = [f"{number}. {_hidden(fact)}{_WRITE}" for number, fact in enumerate(chosen, start=1)]
        lines.append("Choose from: " + " · ".join(options))
        answer = [f"{number}. {fact.suspect}" for number, fact in enumerate(chosen, start=1)]
        return CaseCard(
            "which",
            TASKS["which"],
            tuple(lines),
            tuple(answer),
            tuple(fact.id for fact in chosen),
            chosen[0].page,
        )

    def pick(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        for fact in sorted((f for f in facts if not f.heading), key=lambda f: f.id not in todo):
            found = self._choices(fact)
            if found:
                line, answer, options = found
                return CaseCard(
                    "pick",
                    TASKS["pick"],
                    (line, "   ".join(f"({letter}) {option}" for letter, option in zip("abcd", options, strict=False))),
                    (f"{answer}: {fact.text}",),
                    (fact.id,),
                    fact.page,
                    fact.suspect,
                )
        return None

    def _choices(self, fact: Fact) -> tuple[str, str, list[str]] | None:
        value = _value_gap(fact)
        if value:
            kind, answer, line = value
            pattern = {"year": _YEAR, "number": _QUANTITY}.get(kind)
            if pattern is None:
                return None
            pool = {match.group() for other in self.all_facts for match in pattern.finditer(other.text)}
        else:
            found = _name_gap(fact, self.names)
            if not found:
                return None
            prefix, answer, line = found
            if not prefix:
                return None  # a lone name has no others of its kind to choose from, so it is a FILL THE GAP
            pool = set()
            for other in self.all_facts:
                for match in _runs(other.text):
                    words = match.group().split()
                    if " ".join(words[:-1]) == prefix and words[-1].casefold() not in map(str.casefold, self.names):
                        pool.add(words[-1])
        others = sorted(pool - {answer})[:3]
        if len(others) < 2:
            return None
        return line, answer, sorted([answer, *others])

    def timeline(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        by_suspect: dict[str, list[tuple[int, str, Fact]]] = {}
        for fact in facts:
            if fact.heading:
                continue
            for clause in re.split(r";\s*", fact.text):
                when = _TIME.search(clause)
                if when and len(clause.split()) >= 3:
                    by_suspect.setdefault(fact.suspect, []).append((_when(when), clause.strip().rstrip("."), fact))
        options = [events for events in by_suspect.values() if len({key for key, _, _ in events}) >= 2]
        options.sort(key=lambda events: not any(fact.id in todo for _, _, fact in events))
        if not options:
            return None
        events = sorted(options[0], key=lambda event: event[0])[:4]
        suspect = events[0][2].suspect
        shown = list(reversed(events))
        lines = [f"(    ) {_hide_name(text, suspect).replace(GAP, _BLANK)}" for _, text, _ in shown]
        answer = [f"{number}. {text}" for number, (_, text, _) in enumerate(events, start=1)]
        covers = tuple(dict.fromkeys(fact.id for _, _, fact in events))
        return CaseCard(
            "timeline",
            TASKS["timeline"],
            tuple(lines),
            tuple(answer),
            covers,
            events[0][2].page,
            suspect,
        )

    def fill(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        for fact in sorted((f for f in facts if not f.heading), key=lambda f: f.id not in todo):
            found = _value_gap(fact) or _name_gap(fact, self.names)
            if found:
                _, answer, line = found
                return CaseCard(
                    "fill",
                    TASKS["fill"],
                    (line,),
                    (f"{answer}: {fact.text}",),
                    (fact.id,),
                    fact.page,
                    fact.suspect,
                )
        return None

    def number(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        for fact in sorted((f for f in facts if not f.heading), key=lambda f: f.id not in todo):
            found = _QUANTITY.search(fact.text)
            if found:
                return CaseCard(
                    "number",
                    TASKS["number"],
                    (found.group(),),
                    (fact.text,),
                    (fact.id,),
                    fact.page,
                    fact.suspect,
                    write_lines=2,
                )
        return None

    def who(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        if len({fact.suspect for fact in facts}) < 2:
            return None  # with one suspect on the sheet the answer is known
        by_suspect: dict[str, list[Fact]] = {}
        for fact in facts:
            if len(fact.text.split()) <= 20:
                by_suspect.setdefault(fact.suspect, []).append(fact)
        ranked = sorted(by_suspect.values(), key=lambda group: -sum(fact.id in todo for fact in group))
        for group in ranked:
            chosen = sorted(group, key=lambda fact: fact.id not in todo)[:WHO_LINES]
            if len(chosen) >= 2:
                chosen.sort(key=lambda fact: fact.id)
                suspect = chosen[0].suspect
                return CaseCard(
                    "who",
                    TASKS["who"],
                    tuple(f"Clue {number}: {_hidden(fact)}" for number, fact in enumerate(chosen, start=1)),
                    (suspect,),
                    tuple(fact.id for fact in chosen),
                    chosen[0].page,
                    write_lines=1,
                )
        return None

    def finish(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        for fact in sorted((f for f in facts if not f.heading), key=lambda f: f.id not in todo):
            found = _finish(fact.text)
            if found:
                start, rest = found
                return CaseCard(
                    "finish",
                    TASKS["finish"],
                    (start,),
                    (rest, f"The sheet says: {fact.text}"),
                    (fact.id,),
                    fact.page,
                    fact.suspect,
                    write_lines=1,
                )
        return None

    def mistake(self, facts: list[Fact], todo: set[str]) -> CaseCard | None:
        suspects = list(dict.fromkeys(fact.suspect for fact in [*facts, *self.review]))
        if len(suspects) < 2:
            return None
        names = {name.casefold() for name in self.names}
        for fact in sorted((f for f in facts if not f.heading), key=lambda f: f.id not in todo):
            if any(re.search(rf"\b{re.escape(name)}\b", fact.text, re.I) for name in names):
                continue  # a line that names a suspect would give the answer away
            wrong = suspects[(suspects.index(fact.suspect) + 1) % len(suspects)]
            return CaseCard(
                "mistake",
                TASKS["mistake"],
                (f"{wrong}: {fact.text}",),
                (f"{fact.suspect}, not {wrong}. The sheet says: {fact.text}",),
                (fact.id,),
                fact.page,
                write_lines=1,
            )
        return None

    def notes(self, facts: list[Fact]) -> CaseCard:
        counts: dict[str, list[Fact]] = {}
        for fact in facts:
            if not fact.heading:
                counts.setdefault(fact.suspect, []).append(fact)
        suspect, points = max(counts.items(), key=lambda pair: len(pair[1]))
        return CaseCard(
            "notes",
            TASKS["notes"].format(count=NOTES_FACTS, suspect=suspect),
            (),
            ("Any 3 of these:", *(fact.text for fact in points)),
            (),
            points[0].page,
            suspect,
            write_lines=NOTES_FACTS,
        )

    # The order builders are tried in for each card slot: recognise first, varied, fill-the-gap sparing.
    ORDER = ("match", "which", "pick", "timeline", "number", "who", "fill", "finish", "mistake")

    def plan_sheet(self, facts: list[Fact], review: list[Fact] | None = None) -> list[CaseCard] | None:
        """Eight cards covering every given fact, or None when one sheet cannot.

        Each slot takes the card that tests the most untested facts, less a penalty for each card of its type
        already on the sheet, so cards stay varied while covering as much as they can. Once every fact is covered,
        the spare slots test the least-tested facts again in another way.
        """
        self.review, self.reviewed = list(review or []), {}
        tested = {fact.id: 0 for fact in facts}
        cards: list[CaseCard] = []
        if not facts:
            return None
        while len(cards) < SHEET_CARDS - 1:
            card = self._next(facts, tested, cards)
            if card is None:
                break
            cards.append(card)
            for fact_id in card.covers:
                if fact_id in tested:
                    tested[fact_id] += 1
                else:
                    self.reviewed[fact_id] = self.reviewed.get(fact_id, 0) + 1
        if not all(tested.values()) or len(cards) < SHEET_CARDS - 1:
            return None
        cards.append(self.notes(facts))
        return _ordered(cards)

    def _next(self, facts: list[Fact], tested: dict[str, int], cards: list[CaseCard]) -> CaseCard | None:
        used = [card.kind for card in cards]
        made = {(card.kind, card.covers) for card in cards}
        least = min(tested.values())
        wanted = {fact_id for fact_id, count in tested.items() if count == least}
        best, best_score = None, None
        for kind in dict.fromkeys(self.ORDER):
            if used.count(kind) >= (MAX_FILLS if kind == "fill" else MAX_SAME):
                continue
            others = sum(STAGE[other] == STAGE[kind] and other != kind for other in used)
            if used.count(kind) > others:
                continue  # another card of this kind could not be kept apart from the first
            card = getattr(self, kind)(facts, wanted)
            if card is None or (card.kind, card.covers) in made:
                continue
            new = len(set(card.covers) & wanted)
            # A card testing nothing new only goes on when nothing else can: it may let a second card of a
            # covering kind go on without sitting next to the first.
            score = (bool(new), new - VARIETY_PENALTY * used.count(kind), -self.ORDER.index(kind))
            if best_score is None or score > best_score:
                best, best_score = card, score
        return best


def _when(match: re.Match[str]) -> int:
    if match["medieval"]:
        return 1200
    if match["year"]:
        return int(match["year"])
    century = (int(match["century"]) - 1) * 100
    return century + _PART.get((match["part"] or "").casefold(), 50)


def _ordered(cards: list[CaseCard]) -> list[CaseCard]:
    """Easiest stage first; within a stage, the kind with most cards left goes next unless it just went."""
    ordered: list[CaseCard] = []
    for stage in sorted({STAGE[card.kind] for card in cards}):
        left = [card for card in cards if STAGE[card.kind] == stage]
        while left:
            previous = ordered[-1].kind if ordered else ""
            counts = {kind: sum(card.kind == kind for card in left) for kind in dict.fromkeys(c.kind for c in left)}
            choices = [kind for kind in counts if kind != previous] or list(counts)
            kind = max(choices, key=lambda k: counts[k])
            card = next(card for card in left if card.kind == kind)
            ordered.append(card)
            left.remove(card)
    return ordered


def _pack(planner: _Planner, suspects: list[Suspect]) -> list[tuple[list[Fact], list[CaseCard]]]:
    """Cut the sheet's lines, in reading order, into card sheets of about the same size.

    Each cut is made at the start of a topic when one is close, so a topic stays on one sheet where it can, and
    otherwise at an even share. A cut is kept only when its sheet makes eight cards covering every line; the second
    sheet of a case may mix in lines from the first as review. When no cut works, more sheets are tried.
    """
    facts = [fact for suspect in suspects for fact in suspect.facts]
    total = len(facts)
    starts, position = set(), 0
    for suspect in suspects:
        starts.add(position)
        position += len(suspect.facts)

    def cut(count: int, begin: int, sheets: list) -> list[tuple[list[Fact], list[CaseCard]]] | None:
        """The remaining lines cut into ``count`` sheets, trying the best cut first and backing off when a later
        sheet cannot be made."""
        if count == 0:
            return sheets if begin == total else None
        key = (count, begin, len(sheets) % CASE_SHEETS and sheets[-1][0][0].id)
        if key in failed:
            return None
        if count == 1:
            ends = [total]
        else:
            ideal = begin + round((total - begin) / count)
            near = sorted((start for start in starts if abs(start - ideal) <= 3), key=lambda s: abs(s - ideal))
            ends = [*near, *sorted(range(ideal - 2, ideal + 3), key=lambda end: abs(end - ideal))]
        review = sheets[-1][0] if len(sheets) % CASE_SHEETS else []
        for end in dict.fromkeys(ends):
            if begin < end <= total and (count == 1 or end < total):
                plan = planner.plan_sheet(facts[begin:end], review)
                if plan is not None:
                    found = cut(count - 1, end, [*sheets, (facts[begin:end], plan)])
                    if found is not None:
                        return found
        failed.add(key)
        return None

    failed: set[tuple] = set()
    target = max(1, -(-total // SHEET_FACTS))
    for count in [*range(target, min(total, 2 * target) + 1), *range(target - 1, 0, -1)]:
        sheets = cut(count, 0, [])
        if sheets is not None:
            return sheets
    raise ValueError("No card sheets could be made from this sheet. Use the study cards instead.")


def _big_clue(culprit: str, facts: list[Fact], names: tuple[str, ...], avoid: set[str]) -> BigClue | None:
    """A culprit's point, its name hidden, naming no other suspect; the most distinctive one first."""
    candidates = []
    for fact in facts:
        if fact.suspect != culprit or fact.heading or fact.id in avoid:
            continue
        others = [name for name in names if name != culprit]
        if any(re.search(rf"\b{re.escape(name)}\b", fact.text, re.I) for name in others):
            continue
        candidates.append((-len(_runs(fact.text)), len(fact.text), fact))
    if not candidates:
        return None
    fact = min(candidates, key=lambda candidate: candidate[:2])[2]
    return BigClue(_hidden(fact), fact.id)


def plan_case_file(sheet: Sheet) -> CaseFile:
    """Suspects from the sheet's topics, card sheets covering every line, and a hidden culprit for each case."""
    suspects = suspects_from(sheet)
    if len(suspects) < 2:
        raise ValueError(
            "A Detective case needs at least two topics, each with a heading and its own points. "
            "Use the study cards for this sheet instead."
        )
    planner = _Planner(suspects)
    sheets = _pack(planner, suspects)
    facts = {fact.id: fact for suspect in suspects for fact in suspect.facts}
    cases = []
    for start in range(0, len(sheets), CASE_SHEETS):
        group = sheets[start : start + CASE_SHEETS]
        case_facts = [fact for sheet_facts, _ in group for fact in sheet_facts]
        names = tuple(dict.fromkeys(fact.suspect for fact in case_facts))
        last = [fact for fact in group[-1][0] if not fact.heading]
        culprits = sorted(
            dict.fromkeys(fact.suspect for fact in last),
            key=lambda name: -sum(fact.suspect == name for fact in last),
        )
        made = None
        for culprit in culprits:
            clues, used = [], set()
            for _ in group:
                clue = _big_clue(culprit, case_facts, names, used)
                if clue is None:
                    break
                clues.append(clue)
                used.add(clue.fact)
            if len(clues) == len(group) and len(names) >= 2:
                made = (culprit, clues)
                break
        if made is None:
            raise ValueError("No mystery could be built from this part of the sheet. Use the study cards instead.")
        culprit, clues = made
        case_sheets, review = [], ()
        for (sheet_facts, cards), clue in zip(group, clues, strict=True):
            lines = tuple(fact.id for fact in sheet_facts)
            case_sheets.append(CaseSheet(tuple(cards), clue, lines, review))
            review = lines
        cases.append(Case(len(cases) + 1, names, culprit, tuple(case_sheets)))
    return CaseFile(tuple(suspects), tuple(cases), facts)


def _pattern(line: str) -> re.Pattern[str]:
    """A shown line as a pattern over the sheet's text: each gap may stand for any words."""
    pieces = re.split(r"_{3,}", line)
    return re.compile(r".+?".join(re.escape(piece) for piece in pieces), re.S)


def _shown_text(card: CaseCard) -> list[str]:
    """The sheet's own words on a card, without numbering and fixed labels."""
    if card.kind in {"match", "notes", "number"}:
        return []
    texts = []
    for line in card.lines:
        if line.startswith("Choose from: ") or (card.kind == "pick" and line.startswith("(a)")):
            continue
        line = re.sub(r"^(?:\d+\.\s|Clue \d+:\s|\(\s+\)\s)", "", line).removesuffix(" …").removesuffix(_WRITE)
        if card.kind == "mistake":
            line = line.split(": ", 1)[1]
        texts.append(line)
    return texts


def sheet_problems(cards: tuple[CaseCard, ...], facts: dict[str, Fact], where: str) -> list[str]:
    """Rule B and the sheet's own words, for one card sheet."""
    problems: list[str] = []
    source = " \n ".join(fact.text for fact in facts.values())
    if len(cards) != SHEET_CARDS:
        problems.append(f"{where}: {len(cards)} cards, not {SHEET_CARDS}.")
    kinds = [card.kind for card in cards]
    if kinds.count("fill") > MAX_FILLS:
        problems.append(f"{where}: {kinds.count('fill')} fill-the-gap cards, more than {MAX_FILLS}.")
    for index in range(1, len(kinds)):
        if kinds[index] == kinds[index - 1]:
            problems.append(f"{where}: two {LABELS[kinds[index]]} cards in a row.")
        if STAGE[kinds[index]] < STAGE[kinds[index - 1]]:
            problems.append(f"{where}: card {index + 1} is easier than the card before it.")
    if kinds and kinds[-1] != "notes":
        problems.append(f"{where}: the last card is not CASE NOTES.")
    for position, card in enumerate(cards, start=1):
        unknown = [fact for fact in card.covers if fact not in facts]
        if unknown:
            problems.append(f"{where}, card {position}: tests facts that are not on the sheet: {unknown}.")
        for text in _shown_text(card):
            if not _pattern(text).search(source):
                problems.append(f"{where}, card {position}: “{text}” is not the sheet's own words.")
        if not card.answer:
            problems.append(f"{where}, card {position}: no answer.")
    return problems


def check_case_file(case_file: CaseFile) -> list[str]:
    """Every problem with a case file. Nothing is printed unless this is empty."""
    problems: list[str] = []
    facts = case_file.facts
    covered: set[str] = set()
    for case in case_file.cases:
        if len(case.suspects) < 2:
            problems.append(f"Case {case.number}: fewer than two suspects.")
        if case.culprit not in case.suspects:
            problems.append(f"Case {case.number}: the culprit is not one of the suspects.")
        last = case.sheets[-1].cards if case.sheets else ()
        if case.culprit not in {facts[f].suspect for card in last for f in card.covers if f in facts}:
            problems.append(f"Case {case.number}: the culprit is not on its last sheet, so it is found too soon.")
        clue_facts = set()
        for number, case_sheet in enumerate(case.sheets, start=1):
            where = f"Case {case.number}, sheet {number}"
            problems += sheet_problems(case_sheet.cards, facts, where)
            for card in case_sheet.cards:
                covered.update(card.covers)
            clue = case_sheet.clue
            fact = facts.get(clue.fact)
            if fact is None or fact.suspect != case.culprit:
                problems.append(f"{where}: the Big Clue is not about the culprit.")
            elif not _pattern(clue.text).fullmatch(fact.text):
                problems.append(f"{where}: the Big Clue is not the sheet's own words.")
            elif re.search(rf"\b{re.escape(case.culprit)}\b", clue.text, re.I):
                problems.append(f"{where}: the Big Clue names the culprit.")
            if clue.fact in clue_facts:
                problems.append(f"{where}: the same Big Clue is used twice.")
            clue_facts.add(clue.fact)
    missing = [fact_id for fact_id in facts if fact_id not in covered]
    if missing:
        problems.append("Rule A: these lines are on no card: " + "; ".join(facts[f].text for f in missing))
    return problems


# Printing


def _draw_case_card(shape, kind: _Type, card: CaseCard, number: int, box: pymupdf.Rect, theme: dict) -> None:
    colour, tint = theme["colour"], theme["tint"]
    strip = pymupdf.Rect(box.x0 + 10, box.y0 + 10, box.x1 - 10, box.y0 + 30)
    shape.draw_rect(strip, radius=0.25)
    shape.finish(color=None, fill=tint)
    kind.draw(shape, [kind.printable(card.label, True)], 10, strip.x0 + 8, strip.y0 + 3, True, colour)
    count = kind.printable(f"CARD {number} OF {SHEET_CARDS}", True)
    kind.draw(shape, [count], 7, 0, strip.y0 + 5, True, _MUTED, align_right=strip.x1 - 8)
    task = card.task if not card.about else f"{card.about}. {card.task}"
    task_box = pymupdf.Rect(box.x0 + 16, strip.y1 + 4, box.x1 - 16, strip.y1 + 30)
    size, lines = kind.fit(task, task_box, 9, 7, True)
    y = kind.draw(shape, lines, size, task_box.x0, task_box.y0, True, _INK)
    write = card.write_lines * 17
    body = pymupdf.Rect(box.x0 + 16, y + 4, box.x1 - 16, box.y1 - 12 - write)
    if card.lines:
        size, lines = kind.fit("\n".join(card.lines), body, 11, 6.5, False)
        kind.draw(shape, lines, size, body.x0, body.y0, False, _INK)
    for line in range(card.write_lines):
        y = box.y1 - 14 - (card.write_lines - 1 - line) * 17
        shape.draw_line((box.x0 + 16, y), (box.x1 - 16, y))
        shape.finish(color=_MUTED, width=0.6)


def _board_page(document, kind: _Type, case: Case, theme: dict) -> None:
    page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
    kind.prepare(page)
    shape = page.new_shape()
    margin, width = 52.0, _PAGE_WIDTH - 104.0
    y = kind.draw(shape, [f"CASE {case.number}: WHO IS THE HIDDEN SUSPECT?"], 18, margin, 46, True, theme["colour"])
    rules = [
        "HOW TO PLAY",
        f"1. Solve the {SHEET_CARDS} cards on each sheet. Write your answers on the cards.",
        "2. Your parent checks them. A card you got wrong gets one more try.",
        f"3. All {SHEET_CARDS} right? You earn a star, and your parent reads you a Big Clue.",
        "4. Cross out every suspect the clues rule out.",
        f"5. After {len(case.sheets)} Big Clues, name the hidden suspect and find the proof on your sheet.",
    ]
    y += 14
    for index, rule in enumerate(rules):
        lines = kind.wrap(kind.printable(rule, index == 0), 11, width, index == 0)
        y = kind.draw(shape, lines, 11, margin, y + 3, index == 0, theme["colour"] if index == 0 else _INK)
    y = kind.draw(shape, ["SUSPECTS"], 12, margin, y + 22, True, theme["colour"]) + 6
    for name in case.suspects:
        shape.draw_rect(pymupdf.Rect(margin, y + 2, margin + 12, y + 14))
        shape.finish(color=_INK, width=0.8)
        y = kind.draw(shape, [kind.printable(name)], 12, margin + 22, y, False, _INK) + 8
    for number in range(1, len(case.sheets) + 1):
        y = kind.draw(shape, [f"BIG CLUE {number}"], 12, margin, y + 16, True, theme["colour"])
        note = f"Your parent reads it out when all {SHEET_CARDS} cards on sheet {number} are right. Write it here."
        y = kind.draw(shape, [kind.printable(note)], 8.5, margin, y + 2, False, _MUTED)
        for _ in range(2):
            y += 22
            shape.draw_line((margin, y), (margin + width, y))
            shape.finish(color=_MUTED, width=0.6)
        shape.draw_rect(pymupdf.Rect(margin, y + 10, margin + 12, y + 22))
        shape.finish(color=_INK, width=0.8)
        y = kind.draw(shape, ["Star earned"], 10, margin + 20, y + 9, True, _INK)
    y = kind.draw(shape, ["MY ACCUSATION"], 12, margin, y + 18, True, theme["colour"])
    for label in ("The hidden suspect is:", "My proof (page and line):"):
        y = kind.draw(shape, [label], 10, margin, y + 10, False, _INK)
        shape.draw_line((margin + 140, y), (margin + width, y))
        shape.finish(color=_MUTED, width=0.6)
    shape.commit()


def _sheet_page(document, kind: _Type, case: Case, number: int, theme: dict) -> None:
    case_sheet = case.sheets[number - 1]
    page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
    kind.prepare(page)
    shape = page.new_shape()
    left = f"{theme['title']}  ·  CASE {case.number}  ·  SHEET {number} OF {len(case.sheets)}"
    kind.draw(shape, [kind.printable(left, True)], 7.5, _LEFT, 17, True, _MUTED)
    note = kind.printable("Cut along the dashed lines. Answers are with your parent.")
    kind.draw(shape, [note], 7.5, 0, 17, False, _MUTED, align_right=_PAGE_WIDTH - _LEFT)
    _cut_lines(shape, len(case_sheet.cards))
    for position, card in enumerate(case_sheet.cards):
        _draw_case_card(shape, kind, card, position + 1, _card_box(position), theme)
    shape.commit()


def _answer_pages(document, kind: _Type, case_file: CaseFile, theme: dict) -> None:
    margin, width = 46.0, _PAGE_WIDTH - 92.0
    state = {"y": 0.0, "shape": None}

    def new_page() -> None:
        if state["shape"] is not None:
            state["shape"].commit()
        page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        kind.prepare(page)
        state["shape"] = page.new_shape()
        y = kind.draw(state["shape"], ["CASE CLOSED: ANSWERS FOR THE PARENT"], 15, margin, 34, True, theme["colour"])
        note = "Keep these pages away from the cards. “p.” is the page of the study sheet."
        state["y"] = kind.draw(state["shape"], [kind.printable(note)], 8, margin, y + 2, False, _MUTED) + 10

    def write(lines: list[str], size: float, bold: bool, colour, indent: float = 0.0, page_ref: str = "") -> None:
        wrapped = [part for line in lines for part in kind.wrap(kind.printable(line, bold), size, width - indent - 40)]
        if state["y"] + len(wrapped) * size * 1.22 > _PAGE_HEIGHT - 40:
            new_page()
        if page_ref:
            kind.draw(state["shape"], [page_ref], 8, 0, state["y"] + 1, False, _MUTED, align_right=margin + width)
        state["y"] = kind.draw(state["shape"], wrapped, size, margin + indent, state["y"], bold, colour) + 3

    def keep(lines: int) -> None:
        """Start a new page unless about this many lines still fit, so a card's answer stays with its label."""
        if state["y"] + lines * 12.5 > _PAGE_HEIGHT - 40:
            new_page()

    new_page()
    for case in case_file.cases:
        keep(6)
        write([f"CASE {case.number}"], 13, True, theme["colour"])
        for number, case_sheet in enumerate(case.sheets, start=1):
            write([f"Sheet {number}"], 11, True, theme["colour"])
            for position, card in enumerate(case_sheet.cards, start=1):
                keep(len(card.answer) + 2)
                write([f"{position}. {card.label}"], 9.5, True, _INK, 0, f"p. {card.page}")
                write(list(card.answer), 9.5, False, _INK, 18)
            heading = f"BIG CLUE {number}: read this out when all {SHEET_CARDS} cards are right:"
            write([heading, f"“{case_sheet.clue.text}”"], 10, True, _ORANGE)
        proofs = [case_file.facts[case_sheet.clue.fact] for case_sheet in case.sheets]
        write([f"THE HIDDEN SUSPECT: {case.culprit}"], 11, True, theme["colour"])
        write([f"Proof, p. {fact.page}: {fact.text}" for fact in proofs], 9.5, False, _INK, 18)
        state["y"] += 8
    state["shape"].commit()


def render_case_file_pdf(case_file: CaseFile, standard: int = 8) -> bytes:
    """Each case: its board, its card sheets (one-sided), then every answer at the end."""
    problems = check_case_file(case_file)
    if problems:
        raise ValueError("The case file failed its checks: " + " ".join(problems))
    theme, kind = _THEMES["detective"], _Type()
    document = pymupdf.open()
    for case in case_file.cases:
        _board_page(document, kind, case, theme)
        for number in range(1, len(case.sheets) + 1):
            _sheet_page(document, kind, case, number, theme)
    _answer_pages(document, kind, case_file, theme)
    title = f"Learn ICSE Standard {standard} detective case file"
    document.set_metadata({"title": title, "author": "Learn Teaching Engine"})
    if kind.embedded:
        document.subset_fonts()
    result = document.tobytes(garbage=4, deflate=True)
    document.close()
    return result


def render_printable_case_file_pdf(
    inventory: FactInventory, source_pdf: bytes | None = None, pages: set[int] | None = None, standard: int = 8
) -> bytes:
    """Read the sheet, plan its case file, check it and print it."""
    if source_pdf:
        reject_generated_pdf(source_pdf)
    sheet = read_sheet(inventory, source_pdf, pages)
    return render_case_file_pdf(plan_case_file(sheet), standard)
