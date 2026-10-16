"""Deterministic, traceable inventory of statements and source-text candidates."""

import re
from dataclasses import asdict, dataclass

from ..extraction import SourceUnit

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[\"'“‘([{A-Z0-9])")
# Bullet glyphs, including the private-use bullets that Word's Symbol and Wingdings fonts leave in PDF text.
BULLETS = "•●○◦▪■□‣∙➢➤►▶❖✓✔\uf0b7\uf0a7\uf076\uf0d8\uf0fc"
_BEFORE_BULLET = re.compile(rf"\s+(?=[{BULLETS}])")
# "1.", "2)", "Q3." or a section letter "B." before a word: the start of a list item.
_LIST_MARKER = re.compile(r"(?:(?P<q>Q\s?)?(?P<number>\d{1,2})[.)]|(?P<letter>[A-H])\.(?=\s+[A-Z][a-z]))(?=\s+\S)")
_MARKER_ONLY = re.compile(r"(?:Q\s?)?\d{1,2}[.)]|[A-Z]\.|\(?[a-z]\)")
_ABBREVIATIONS = frozenset(
    "dr mr mrs ms st sr jr prof rev hon no nos vs approx est fig figs vol ch govt pvt ltd co inc dept "
    "jan feb mar apr jun jul aug sep sept oct nov dec e.g i.e viz cf al".split()
)
# Words after which a capital letter and a full stop name a label ("Vitamin C.") rather than an initial ("N. Ireland").
_LETTER_LABELS = frozenset("vitamin plan grade class group section part type category point step option phase".split())
_PATTERNS: dict[str, re.Pattern[str]] = {
    "date": re.compile(
        r"\b(?:\d{1,2}(?:st|nd|rd|th)?\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"(?:\s+\d{1,2}(?:st|nd|rd|th)?)?(?:,?\s+\d{4})?\b|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b(?:1[0-9]{3}|20[0-9]{2})\b",
        re.IGNORECASE,
    ),
    "number": re.compile(
        r"(?<![\w/])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?(?:/\d+)?(?:st|nd|rd|th)?%?|"
        r"zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
        r"thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million)\b",
        re.IGNORECASE,
    ),
    "technical_term": re.compile(
        r"\b([A-Za-z][\w-]*(?:\s+[A-Za-z][\w-]*){0,4})\s+"
        r"(?:means|refers to|is defined as|are defined as|is called|are called)\b",
        re.IGNORECASE,
    ),
    "entity": re.compile(r"\b(?:[A-Z][\w'’-]*)(?:\s+(?:of|the|and|[A-Z][\w'’-]*)){0,5}\b"),
    "place_candidate": re.compile(
        r"\b(?:in|at|near|from|to|within|across)\s+((?:the\s+)?[A-Z][\w'’-]*(?:\s+(?:of|the|and|[A-Z][\w'’-]*)){0,4})"
    ),
}
_RELATIONS = (
    "is located in",
    "are located in",
    "is in",
    "are in",
    "flows through",
    "flows into",
    "drains into",
    "is part of",
    "are part of",
    "is known as",
    "is called",
    "was invented in",
    "were invented in",
    "was discovered in",
    "were discovered in",
    "because",
    "therefore",
    "resulting in",
    "results in",
    "causes",
    "caused",
    "leads to",
    "made from",
    "consists of",
    "compared with",
    "larger than",
    "smaller than",
    "capital of",
    "is",
    "are",
    "was",
    "were",
    "has",
    "have",
    "had",
    "began",
    "begins",
    "became",
    "grew",
    "developed",
)
REVIEW_CUES = re.compile(
    r"\b(?:invented|first|oldest|largest|smallest|most populous|only|always|never)\b", re.IGNORECASE
)
_DIFFICULT_CUES = re.compile(r"\b(?:important|key|significant|technical|special|difficult|known as)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Mention:
    kind: str
    text: str
    source_unit_id: str
    page: int
    start: int
    end: int


@dataclass(frozen=True)
class Fact:
    id: str
    statement: str
    source_unit_id: str
    page: int
    start: int
    end: int
    mentions: tuple[Mention, ...]
    review_flags: tuple[str, ...]


@dataclass(frozen=True)
class FactInventory:
    facts: tuple[Fact, ...]
    source_unit_ids: tuple[str, ...]
    source_text: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _ListState:
    """The last list numbers seen, so a "2." or "B." inside a unit only starts an item when it continues a list."""

    number: int = 0
    question: int = 0
    letter: str = ""

    def starts_item(self, text: str, marker: re.Match[str]) -> bool:
        at_start = not text[: marker.start()].strip()
        if not at_start and not text[marker.start() - 1].isspace():
            return False  # inside a number or word, such as "2012."
        if marker["letter"]:
            letter = marker["letter"]
            previous = text[: marker.start()].split()[-1:] or [""]
            if previous[0].casefold() in _LETTER_LABELS:
                return False
            follows = bool(self.letter) and ord(letter) == ord(self.letter) + 1
            if at_start or follows or (letter == "A" and previous[0].isupper()):
                self.letter = letter
                return True
            return False
        number = int(marker["number"])
        last = self.question if marker["q"] else self.number
        if at_start or number in (1, last + 1):
            if marker["q"]:
                self.question = number
            else:
                self.number = number
            return True
        return False


def _closes_abbreviation(text: str, end: int) -> bool:
    """True when the full stop just before ``end`` belongs to an abbreviation or an initial, not a sentence."""
    match = re.search(r"(?:^|(?<=[\s(]))([\w.]+)\.$", text[:end])
    if not match:
        return False
    word = match.group(1)
    if word.casefold() in _ABBREVIATIONS:
        return True
    if len(word) == 1 and word.isupper():
        previous = re.findall(r"\w+", text[: match.start()])[-1:]
        return not (previous and previous[0].casefold() in _LETTER_LABELS)
    return False


def _sentence_spans(text: str, state: _ListState | None = None) -> list[tuple[int, int]]:
    if re.match(r"\s*(?:question|q\.)\s*\d+\b", text, re.IGNORECASE):
        start = len(text) - len(text.lstrip())
        end = len(text.rstrip())
        return [(start, end)] if start < end else []
    state = state or _ListState()
    # A bullet or a list marker starts a new statement; a sentence ends at . ! or ? unless the full stop closes an
    # abbreviation ("Dr.", "est.") or an initial ("N. Ireland", "B. R. Ambedkar").
    cuts = {match.end() for match in _BEFORE_BULLET.finditer(text)}
    cuts.update(marker.start() for marker in _LIST_MARKER.finditer(text) if state.starts_item(text, marker))
    cuts.update(
        boundary.end() for boundary in _SENTENCE_END.finditer(text) if not _closes_abbreviation(text, boundary.start())
    )
    spans: list[tuple[int, int]] = []
    start = 0
    for cut in [*sorted(cuts), len(text)]:
        if cut < len(text) and _MARKER_ONLY.fullmatch(text[start:cut].strip()):
            continue  # keep "1." with the item it numbers
        end = cut
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if start < end:
            spans.append((start, end))
        start = cut
    return spans


def split_sentences(text: str) -> list[str]:
    """The sentences of a passage, split the way the inventory splits source units."""
    return [text[start:end] for start, end in _sentence_spans(text)]


def _mentions(statement: str, unit: SourceUnit, offset: int) -> tuple[Mention, ...]:
    found: dict[tuple[int, int, str], Mention] = {}

    def add(kind: str, start: int, end: int) -> None:
        if start >= end:
            return
        key = (start, end, kind)
        found[key] = Mention(kind, statement[start:end], unit.id, unit.page, offset + start, offset + end)

    for kind, pattern in _PATTERNS.items():
        for match in pattern.finditer(statement):
            if kind == "technical_term":
                start, end = match.span(1)
                article = re.match(r"(?:the|a|an)\s+", statement[start:end], re.IGNORECASE)
                if article:
                    start += article.end()
                add("difficult_term", start, end)
            elif kind == "place_candidate":
                add("place_candidate", *match.span(1))
            elif kind == "entity":
                start, end = match.span()
                article = re.match(r"(?:the|a|an)\s+", statement[start:end], re.IGNORECASE)
                if article:
                    start += article.end()
                entity = statement[start:end]
                sentence_pronoun = re.match(r"(?:it|this|that|these|those|they|he|she|we|i)\b", entity, re.IGNORECASE)
                if (
                    entity
                    and not (match.start() == 0 and sentence_pronoun)
                    and (match.start() != 0 or article is not None or len(entity) > 1 or entity.isupper())
                ):
                    add("entity", start, end)
            else:
                add(kind, *match.span())
    for cue in _DIFFICULT_CUES.finditer(statement):
        add("difficult_term_candidate", *cue.span())
    lowered = statement.casefold()
    for relation in _RELATIONS:
        for match in re.finditer(rf"(?<!\w){re.escape(relation)}(?!\w)", lowered):
            add("relationship_cue", *match.span())
    return tuple(sorted(found.values(), key=lambda item: (item.start, item.end, item.kind)))


def extract_facts(units: list[SourceUnit]) -> FactInventory:
    """Split extracted source units into verbatim sentence-sized evidence records.

    Mentions are heuristic review candidates. They are never normalised, corrected, or supplemented.
    """
    facts: list[Fact] = []
    lists = _ListState()
    for unit in units:
        for sequence, (start, end) in enumerate(_sentence_spans(unit.text, lists), start=1):
            statement = unit.text[start:end]
            flags: list[str] = []
            if "\ufffd" in statement:
                flags.append("verify_extracted_text")
            if REVIEW_CUES.search(statement):
                flags.append("verify_attribution_or_absolute_claim")
            facts.append(
                Fact(
                    id=f"{unit.id}-F{sequence}",
                    statement=statement,
                    source_unit_id=unit.id,
                    page=unit.page,
                    start=start,
                    end=end,
                    mentions=_mentions(statement, unit, start),
                    review_flags=tuple(flags),
                )
            )
    return FactInventory(
        facts=tuple(facts),
        source_unit_ids=tuple(unit.id for unit in units),
        source_text=tuple((unit.id, unit.text) for unit in units),
    )
