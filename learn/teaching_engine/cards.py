"""Turn a study sheet into printable question cards, with the answers on a separate sheet.

Every card asks one plain question about the sheet's own words: name the topic of a heading, say who or what a
point is about, fill a date or number gap, finish a sentence, answer one of the sheet's practice questions, compare
a table row, or recall a memory tip. Cards print one-sided, eight to an A4 page, and the answer sheet follows on its
own pages so it can be kept away from the cards. Clues and answers are runs of the sheet's text with words hidden
behind a gap; the only added words are the fixed questions and labels.
"""

import re
from dataclasses import dataclass
from hashlib import sha256

import pymupdf

from .facts import BULLETS, REVIEW_CUES, FactInventory, split_sentences
from .sheet import GENERIC_HEADING, Item, Sheet, names_topic, read_sheet, summary_parts

GAP = "______"
_PAGE_WIDTH = 595.28
_PAGE_HEIGHT = 841.89
_CARD_WIDTH = 241.0  # 85 mm
_CARD_HEIGHT = 195.0  # 68.8 mm
_LEFT = (_PAGE_WIDTH - 2 * _CARD_WIDTH) / 2
_TOP = 40.0
_CARDS_PER_PAGE = 8
_INK = (0.12, 0.16, 0.14)
_MUTED = (0.42, 0.46, 0.43)
_CUT = (0.70, 0.73, 0.71)
_ORANGE = (0.69, 0.33, 0.10)
_THEMES = {
    "detective": {"title": "DETECTIVE CASE FILE", "colour": (0.13, 0.36, 0.27), "tint": (0.91, 0.95, 0.92)},
    "superhero": {"title": "SUPERHERO POWER-UP GAME", "colour": (0.32, 0.25, 0.62), "tint": (0.93, 0.92, 0.98)},
    "study": {"title": "STUDY CARDS", "colour": (0.09, 0.24, 0.20), "tint": (0.93, 0.95, 0.91)},
}
_ABSTRACT_TOPIC = re.compile(
    r"\b(?:cycle|process|system|stage|stages|step|steps|change|changes|evaporation|condensation|"
    r"precipitation|transpiration|rainfall|photosynthesis|respiration|reproduction|circulation|"
    r"energy|matter|force|weather|climate)\b",
    re.I,
)
# Plain questions for Standards 7, 8 and 9.
_QUESTIONS = {
    "who": ("Who is this?", "Who is this?", "Identify this person."),
    "what": ("What is it?", "What is it?", "Identify it."),
    "who_about": ("Who is it?", "Who is this about?", "Identify the person described."),
    "what_about": ("What is it?", "What is this about?", "Identify what is described."),
    "date": ("Which date goes in the gap?", "Which date fits the gap?", "Supply the missing date."),
    "year": ("Which year goes in the gap?", "Which year fits the gap?", "Supply the missing year."),
    "number": ("Which number goes in the gap?", "Which number fits the gap?", "Supply the missing number."),
    "century": ("Which century goes in the gap?", "Which century fits the gap?", "Supply the missing century."),
    "finish": ("How does it end?", "Finish the sentence.", "Complete the statement."),
    "question": ("Answer it.", "Answer it.", "Answer as you would in the exam."),
    "fill": ("Fill the gap.", "Fill the gap.", "Complete the statement."),
    "compare": ("What is each one's {}?", "What is each one's {}?", "State the {} of each."),
    "tip": ("Say the whole tip.", "Say the rest of the tip.", "Recall the complete memory tip."),
    "term": ("What is it called?", "What is it called?", "Name the term described."),
    "name": ("Which name goes in the gap?", "Which name fits the gap?", "Supply the missing name."),
    "word": ("Which word goes in the gap?", "Which term fits the gap?", "Supply the missing term."),
    "equation": ("What goes in the gap?", "What goes in the gap?", "Complete it."),
    "chain": ("What goes in the gap?", "What comes in the gap?", "Supply the missing step."),
    "sort": ("Which one is it: {}?", "Which one is it: {}?", "Classify it: {}?"),
    "which": ("Which {} is it?", "Which {} is it?", "Identify the {}."),
    "year_of": ("Which year is it?", "Which year goes with it?", "Give its year."),
    "order": ("Put them in order.", "Put them in time order.", "Arrange them chronologically."),
}


def reject_generated_pdf(source_pdf: bytes) -> None:
    with pymupdf.open(stream=source_pdf, filetype="pdf") as document:
        metadata = document.metadata or {}
    title = metadata.get("title") or ""
    if metadata.get("author") == "Learn Teaching Engine" and (
        title.startswith("Learn ICSE Standard") or title in {"Learn detective game", "Learn superhero game"}
    ):
        raise ValueError("This is already a Learn-generated PDF. Upload the original curriculum PDF instead.")


_CHAIN = re.compile(r"(\s*(?:→|->|⟶|➜|➝)\s*)")
# Words a sentence's second half often starts with: "Dead animals are decomposed | by bacteria and fungi".
_PHRASE_START = frozenset(
    "by that which who whom whose to in on for with because so and from into at as when where while after before "
    "during through than but or of until since unless if".split()
)
_INLINE_SEPARATOR = re.compile(r"\s+[•|]\s+")
# Sub-headings whose text states goals for the lesson rather than facts to learn.
_NO_CARDS = re.compile(r"^(?:learning (?:goals|objectives|outcomes)|objectives?|aims?|success criteria)\b", re.I)
_DEFINED_TERM = re.compile(
    r"\b(?:is|are|was|were)\s+(?:called|known as|termed|named)\s+(?:the\s+|an?\s+)?"
    r"(?P<term>[A-Za-z][\w'’-]*(?:\s+[\w'’-]+){0,3}?)(?=\s*[.,;:]|\s*$)"
    r"|^(?P<lead>[A-Z][\w'’-]*(?:\s+[a-z][\w'’-]*)?)"
    r"(?=\s+(?:means|refers to|is defined as|are defined as)\s+(?:the|a|an)\b)"
)
_LABELLED = re.compile(r"^(?P<label>[A-Za-z][\w'’()/& -]{0,40}?)\s*(?::|\s[—–])\s+(?P<text>\S.*)$")
_LIST_LABEL = re.compile(r"^(?:vocabulary|glossary|key ?words|key terms|terms|words|definitions)\s*:\s*", re.I)
_MATH = re.compile(r"[=×÷√²³½¼¾±≤≥]|\d\s*[+*/^]\s*\d|\b\d+\s*:\s*\d+\b")
_JUNK_WORD = re.compile(r"([^\W\d_])\1{3,}\W*")  # "IIIII", not a "______" blank
_QUESTION_LABEL = re.compile(r"^(?:Q(?:uestion)?|Explain|Think)\s*\d*\s*:\s*", re.I)
# A worked example: "Example 1: Find the area … Solution: Area = … = 20 cm²."
_WORKED = re.compile(
    r"^Example\s*[\d.]*\s*:\s*(?P<task>.+?)\s+(?:Solution|Answer|Ans)\s*[:.]\s*(?P<solution>.+)$", re.I
)
_MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
_FULL_DATE = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{_MONTHS})\s+\d{{4}}\b|\b(?:{_MONTHS})\s+\d{{1,2}},?\s+\d{{4}}\b"
)
_YEAR = re.compile(r"(?<![\d,.£$₹/:–—-])(?:1[0-9]{3}|20[0-9]{2})(?![\d,]|\s*[–—-]\s*\d)")
_CENTURY = re.compile(r"\b\d{1,2}(?:st|nd|rd|th)(?=\s+century\b)", re.I)
_UNITS = (
    r"%|per\s?cent|km|kilometres?|kilometers?|miles?|metres?|meters?|kg|tonnes?|days?|years?|months?|weeks?|"
    r"hours?|minutes?|delegates|volunteers|members|people|persons|visitors|jobs|companies|states|seats|million|"
    r"billion|bn|lakh|crore|cities|times|mills|acres|hectares|feet|ft"
)
_QUANTITY = re.compile(
    rf"(?<![\w.,£$₹-])(?:\d{{1,3}}(?:,\d{{3}})+|\d+(?:\.\d+)?(?=[\s-]?(?:{_UNITS})\b))(?![\d,])", re.I
)
_HEADING_SEPARATOR = re.compile(r"\s+[–—-]\s+|:\s+")
_PERSON_TITLE = re.compile(
    r"^(?:Dr|Sir|Mahatma|Lokmanya|Raja|Rani|Maharaja|Maharani|Swami|Pandit|Pt|Shri|Sri|Smt|Mr|Mrs|Ms|Lord|Lady|"
    r"King|Queen|Emperor|Empress|Sultan|Nawab|Begum|Guru|Sant|Saint|Netaji|Sardar|Lala|Acharya|Maulana|Chhatrapati)\b",
    re.I,
)
_LIFE_YEARS = re.compile(r"\((?:c\.\s*|b\.\s*)?(\d{4})\s*[–—-]\s*(\d{2,4})\)")
_PERSON_WORDS = re.compile(
    r"\b(?:reformer|leader|scientist|poet|writer|author|king|queen|emperor|ruler|founder|father|mother|"
    r"educationist|educator|teacher|nationalist|jurist|economist|philosopher|saint|industrialist|pioneer|"
    r"freedom fighter|statesman|revolutionary|explorer|inventor|artist|musician|barrister)\b",
    re.I,
)
_NOT_PERSON = re.compile(
    r"\b(?:movement|industry|industries|company|act|revolt|war|mission|satyagraha|march|congress|party|empire|raj|"
    r"rule|dynasty|era|period|revolution|kingdom|sultanate|republic|struggle|session|committee|treaty|pact|plan|"
    r"policy|city|river|state|sabha|court|parliament|bank|exchange|services|field|steel|textile|petroleum|"
    r"engineering|causes|results|course|types|conservation)\b",
    re.I,
)
_NAME_STOPWORDS = frozenset("of the and in on at to for a an da de di van von".split())
_SUBSTITUTES = str.maketrans(
    {
        "→": "->", "←": "<-", "↔": "<->", "⇒": "=>", "–": "-", "—": "-", "−": "-", "‘": "'", "’": "'",
        "“": '"', "”": '"', "…": "...", "•": "-", "≤": "<=", "≥": ">=", "≠": "!=", "₹": "Rs.", "₂": "2",
        "₃": "3", "₄": "4", "₅": "5", "²": "2", "³": "3",
    }
)  # fmt: skip


@dataclass(frozen=True)
class SourceVisual:
    page: int
    image: bytes


@dataclass(frozen=True)
class Card:
    """One printed card and its answer-sheet entry."""

    kind: str  # name riddle gap term equation chain finish question compare row sort timeline order summary tip picture
    question: str  # the one plain question printed on the card
    clue: str  # the sheet's words shown on the card; "" for a picture
    answer: str  # the answer-sheet entry, in the sheet's words
    page: int
    unit_ids: tuple[str, ...] = ()
    about: str = ""  # a short line saying what the card is about; never the answer
    checks: tuple[str, ...] = ()  # notes for the adult checking answers
    image: bytes | None = None


@dataclass(frozen=True)
class Heading:
    name: str
    after: str  # the rest of the heading as printed, starting right after the name
    person: bool


def parse_heading(text: str) -> Heading:
    """Split "Dadabhai Naoroji (1825–1917) – "Grand Old Man of India"" into the name and the rest."""
    depth, quoted, cut = 0, False, len(text)
    for index, char in enumerate(text):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth = max(0, depth - 1)
        elif char == '"':
            quoted = not quoted
        elif char in "“”":
            quoted = char == "“"
        elif depth == 0 and not quoted and _HEADING_SEPARATOR.match(text, index):
            cut = index
            break
    name = text[:cut].strip()
    dated = re.search(r"\s*\([^()]*\d[^()]*\)\s*$", name)
    if dated and dated.start() > 0:
        name = name[: dated.start()].strip()
    after = text[len(name) :] if text.startswith(name) else ""
    life = _LIFE_YEARS.search(text)
    lived = False
    if life:
        born, died = int(life.group(1)), life.group(2)
        died = int(died) if len(died) == 4 else int(str(born)[:2] + died)
        lived = 20 <= died - born <= 110
    person = not _NOT_PERSON.search(name) and bool(_PERSON_TITLE.match(name) or lived or _PERSON_WORDS.search(after))
    return Heading(name, after, person)


def _ask(kind: str, standard: int, *values: str) -> str:
    return _QUESTIONS[kind][standard - 7].format(*values)


def _hide_name(text: str, name: str) -> str:
    """Hide every capitalised use of the name's words, so a riddle never shows its answer."""
    words = {
        word.strip(".").casefold()
        for word in re.findall(r"[A-Za-z][\w'’.-]*", name)
        if word.casefold() not in _NAME_STOPWORDS
        and len(word.strip(".")) >= 3
        and not re.fullmatch(_MONTHS, word.strip("."), re.I)  # "Salt March" must not blank "12 March"
    }
    if not words:
        return text
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(word) for word in sorted(words, key=len, reverse=True)) + r")\b", re.I
    )
    hidden = pattern.sub(lambda match: GAP if match.group()[0].isupper() else match.group(), text)
    return re.sub(rf"{GAP}(?:[\s-]+{GAP})+", GAP, hidden)


def _clauses(text: str) -> list[str]:
    """Long points split at top-level semicolons into clauses that each fit one card."""
    if len(text) <= 120:
        return [text]
    parts, depth, start = [], 0, 0
    for index, char in enumerate(text):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == ";" and depth <= 0:
            parts.append(text[start : index + 1])
            start = index + 1
    parts.append(text[start:])
    clauses = [part.strip().rstrip(";").strip() for part in parts]
    clauses = [clause for clause in clauses if len(clause.split()) >= 4]
    return clauses or [text]


def _gap(text: str) -> tuple[str, str, str] | None:
    """The most memorable date or number in a clause: (kind, answer, clue with the answer hidden)."""

    def in_brackets(match: re.Match[str]) -> bool:
        return text[: match.start()].count("(") > text[: match.start()].count(")")

    def in_list(match: re.Match[str]) -> bool:
        return bool(
            re.search(r"\d{4}\s*,\s*$", text[: match.start()]) or re.match(r"\s*,\s*\d{4}", text[match.end() :])
        )

    defined = _DEFINED_TERM.search(text)
    if defined:
        name = "term" if defined["term"] else "lead"
        start, end = defined.span(name)
        return "word", defined[name], f"{text[:start]}{GAP}{text[end:]}"
    years = [match for match in _YEAR.finditer(text) if not in_list(match)]
    choices = [
        ("date", list(_FULL_DATE.finditer(text))),
        ("year", [match for match in years if not in_brackets(match)]),
        ("number", list(_QUANTITY.finditer(text))),
        ("year", years),
        ("century", list(_CENTURY.finditer(text))),
    ]
    for kind, matches in choices:
        if matches:
            match = matches[0]
            return kind, match.group(), f"{text[: match.start()]}{GAP}{text[match.end() :]}"
    return None


def _readable(text: str) -> bool:
    """False for text the PDF lost: letters its font could not encode, extracted as "IIIII" or as U+FFFD."""
    return "\ufffd" not in text and not any(_JUNK_WORD.fullmatch(word) for word in text.split())


def lost_text_pages(sheet: Sheet) -> list[int]:
    """Pages where some of the sheet's text could not be read from the PDF, so it is on no card."""
    pages = set()
    for item in sheet.items:
        cells = [cell for row in (item.table.header, *item.table.rows) for cell in row] if item.table else []
        if not all(_readable(text) for text in (item.text, item.answer, *cells)):
            pages.add(item.page)
    return sorted(pages)


def _labelled(text: str) -> tuple[str, str] | None:
    """ "Evaporation: Heat from the Sun …" → ("Evaporation", "Heat from the Sun …")."""
    match = _LABELLED.match(_LIST_LABEL.sub("", text))
    if not match:
        return None
    label = match["label"].strip()
    words = label.split()
    if len(words) > 4 or re.search(r"\d", label) or GENERIC_HEADING.match(label) or GENERIC_HEADING.match(words[-1]):
        return None
    return label, match["text"].strip()


def _equation(piece: str) -> tuple[str, str] | None:
    """ "1 km = 1,000 m" → ("1 km = ______", "1,000 m"): the result is the answer, not the first number."""
    if "=" not in piece or not _MATH.search(piece):
        return None
    split = max(piece.rfind("="), piece.rfind("≈"))
    left, right = piece[:split], piece[split + 1 :]
    right = right.strip().rstrip(".")
    if not right or len(right.split()) > 7 or not left.strip():
        return None
    measured = re.fullmatch(r"[\d.,]+\s*[A-Za-z/°%·²³]{0,6}", right)
    given = re.split(r"[=≈,;:]|\b(?:and|so|then)\b", left)[-1]
    if measured and not re.search(r"[\d¼½¾⅓⅔⅛+\-−×÷*/^√]", given):
        return None  # "radius = 7 cm" or "x = 6" states a value; "1 km = 1,000 m" and "240 − 15 = 225 mm" teach one
    if _labelled(piece) is None and re.search(r"\d[a-z]\b|\b[a-z]\s*[+\-−×*/]", left):
        return None  # "3x + 7 = 25" is an equation to solve, not a fact to recall; "1 m = 100 cm" is a fact
    return f"{left.rstrip()} {piece[split]} {GAP}", right


def _chain(piece: str) -> tuple[str, str] | None:
    """ "Grass → Grasshopper → Frog → Snake" with a middle step hidden; "CO₂ + H₂O → glucose" with the result hidden."""
    parts = _CHAIN.split(piece.rstrip("."))
    steps, arrows = [step.strip() for step in parts[0::2]], parts[1::2]
    if len(steps) < 2 or any(not step or len(step.split()) > 6 or ";" in step for step in steps):
        return None  # "Alive → respiration releases CO2; Dead → …" runs two chains together
    hidden = len(steps) // 2 if len(steps) > 2 else 1
    shown = [GAP if index == hidden else step for index, step in enumerate(steps)]
    clue = shown[0] + "".join(arrow + step for arrow, step in zip(arrows, shown[1:], strict=True))
    return clue, steps[hidden]


def _reason(text: str) -> tuple[str, str] | None:
    """ "Plants are still a useful sink because …": the reason the sheet gives is the answer."""
    found = re.search(r"\sbecause\s", text)
    if found is None or len(text[: found.start()].split()) < 3 or len(text[found.end() :].split()) < 2:
        return None
    return text[: found.end()].rstrip() + " …", "… " + text[found.end() :].strip()


def _finish(text: str) -> tuple[str, str] | None:
    """The first part of a sentence as the clue and the rest as the answer, cut where the rest is a whole phrase."""
    reason = _reason(text)
    if reason is not None:
        return reason
    words = text.split()
    if len(words) < 6 or _MATH.search(text) or not re.search(r"[.!?][\"'”’)]*$", text):
        return None  # only whole sentences: a line without a full stop is a heading or a fragment
    cuts, depth = [], 0
    for index, word in enumerate(words):
        if depth <= 0 and 3 <= index <= len(words) - 3:
            cuts.append(index)  # never inside brackets: "Respiration continues (plants | need energy)" is no cut
        depth += word.count("(") + word.count("[") - word.count(")") - word.count("]")
    if not cuts:
        return None
    middle = [index for index in cuts if 0.3 * len(words) <= index <= 0.7 * len(words)] or cuts
    natural = [
        index
        for index in middle
        if words[index].casefold().strip("(\"'“‘") in _PHRASE_START or words[index - 1].endswith((",", ";"))
    ]
    shown = min(natural or middle, key=lambda index: abs(index - 0.45 * len(words)))
    return " ".join(words[:shown]) + " …", "… " + " ".join(words[shown:])


FINISH_WORDS = 6  # the most words a "Finish the sentence" answer may have
# A name: capitalised words, joined by "of", "the" or "and" ("Battle of Panipat", "Bay of Bengal").
_NAME = re.compile(
    r"(?<![\w'’-])[A-Z][\w'’-]*[a-z\u00C0-\u024F\u1E00-\u1EFF](?:\s+(?:(?:of|the|and)\s+)?[A-Z][\w'’-]*[a-z])*(?!\w)"
)


def _name_gap(text: str, about: str = "") -> tuple[str, str] | None:
    """The longest name printed in a sentence, hidden: never its first word, a figure number or a name said twice."""
    first = re.match(r"\W*(?:[^\s:]+(?:\s+[^\s:]+){0,2}:\s+)?\S+", text)  # "Evaluation: Friction, …" starts at Friction
    names = []
    for match in _NAME.finditer(text):
        name = match.group()
        if first is not None and match.start() < first.end():
            continue  # a capital at the start of a sentence marks the sentence, not a name
        if name.casefold() in {"fig", "i"} or text.count(name) > 1 or (about and name.casefold() in about.casefold()):
            continue
        names.append(match)
    if not names:
        return None
    match = max(names, key=lambda found: len(found.group().split()))
    return f"{text[: match.start()]}{GAP}{text[match.end() :]}", match.group()


def _key_cloze(text: str) -> tuple[str, str] | None:
    forms = re.search(r"\bare forms of (?P<answer>[A-Za-z][A-Za-z'’-]{2,})(?P<end>[.!?]?)$", text)
    if forms is not None:
        return f"{text[: forms.start('answer')]}{GAP}{forms['end']}", forms["answer"]
    match = re.search(r"\b(?:is|are|was|were)\s+(?P<answer>[A-Za-z][A-Za-z'’-]{2,})(?P<end>[.!?]?)$", text)
    if match is None:
        return None
    return f"{text[: match.start('answer')]}{GAP}{match['end']}", match["answer"]


def _recall_question(text: str) -> str | None:
    patterns = (
        (
            r"^Plants? also release (?P<object>.+?) from (?P<place>[^.!?]+)[.!?]$",
            "What do plants release from {place}?",
        ),
        (
            r"^Together,\s*(?P<subject>.+?)\s+add\s+(?P<object>.+?)\s+to\s+(?P<place>[^.!?]+)[.!?]$",
            "What do {subject} add to {place}?",
        ),
        (r"^(?P<subject>[^.!?]+?)\s+warms?\s+(?P<object>[^.!?]+)[.!?]$", "What does {subject} warm?"),
        (
            r"^(?P<subject>[^.!?]+?)\s+moves?\s+(?:continuously\s+)?(?P<detail>[^.!?]+)[.!?]$",
            "Where does {subject} move?",
        ),
        (r"^(?P<subject>[^.!?]+?)\s+changes?\s+into\s+(?P<answer>[^.!?]+)[.!?]$", "What does {subject} change into?"),
        (r"^(?P<subject>[^.!?]+?)\s+release\s+(?P<object>[^.!?]+)[.!?]$", "What does {subject} release?"),
        (
            r"^(?P<subject>[^.!?]+?)\s+add\s+(?P<object>[^.!?]+?)\s+to\s+(?P<place>[^.!?]+)[.!?]$",
            "What do {subject} add to {place}?",
        ),
        (r"^As\s+(?P<context>[^,]+),\s+(?P<answer>[^.!?]+)[.!?]$", "What happens as {context}?"),
        (r"^(?P<subject>[^.!?]+?)\s+form\s+(?P<object>[^.!?]+)[.!?]$", "What do {subject} form?"),
        (r"^(?P<subject>[^.!?]+?)\s+can\s+(?P<action>[^.!?]+)[.!?]$", "What can {subject} do?"),
        (r"^When\s+(?P<context>[^,]+),\s+(?P<answer>[^.!?]+)[.!?]$", "What happens when {context}?"),
        (r"^(?P<subject>[^.!?]+?)\s+flows?\s+(?P<detail>[^.!?]+)[.!?]$", "Where does {subject} flow?"),
        (
            r"^Some\s+enters?\s+(?P<place>[^.!?]+?)\s+and\s+may\s+become\s+(?P<answer>[^.!?]+)[.!?]$",
            "What may some water become?",
        ),
        (
            r"^(?P<subject>[^.!?]+?)\s+carry\s+(?P<object>[^.!?]+?)(?:\s+back)?\s+towards\s+(?P<place>[^.!?]+)[.!?]$",
            "What do {subject} carry towards {place}?",
        ),
        (r"^(?P<subject>[^.!?]+?)\s+can\s+involve\s+(?P<object>[^.!?]+)[.!?]$", "What can {subject} involve?"),
    )
    for pattern, template in patterns:
        match = re.match(pattern, text, re.I)
        if match:
            values = {
                key: value.rstrip(" .")[:1].lower() + value.rstrip(" .")[1:]
                for key, value in match.groupdict().items()
                if value
            }
            return template.format(**values)
    return None


_NAMED_PROCESS = re.compile(
    r"^This\s+(?P<kind>change|movement|process)\s+(?:is|was)\s+(?:called\s+)?"
    r"(?P<name>[A-Za-z][\w'’-]*(?:\s+[\w'’-]+){0,3})[.!?]?$",
    re.I,
)


def _named_process(text: str) -> tuple[str, str] | None:
    match = _NAMED_PROCESS.match(text.strip())
    if match is None:
        return None
    name = re.sub(r"^(?:the|a|an)\s+", "", match["name"].strip(), flags=re.I).rstrip(".")
    return match["kind"].casefold(), name


def _supports_named_process(explanation: str, kind: str) -> bool:
    patterns = {
        "change": r"\b(?:change\w*|turn\w* into|become\w*)\b",
        "movement": r"\b(?:move\w*|flow\w*|travel\w*|circulat\w*)\b",
        "process": r"\b(?:release\w*|add\w*|produce\w*|form\w*)\b",
    }
    return bool(re.search(patterns[kind], explanation, re.I))


def _paired_process_card(explanation: Item, naming: Item) -> Card | None:
    named = _named_process(naming.text)
    if named is None:
        return None
    kind, name = named
    if not _supports_named_process(explanation.text, kind):
        return None
    question = {
        "change": "What is this change called?",
        "movement": "What is this movement called?",
        "process": "What is this process called?",
    }[kind]
    unit_ids = tuple(dict.fromkeys((*explanation.unit_ids, *naming.unit_ids)))
    source = f"{explanation.text} {naming.text}"
    return Card(
        "teach",
        question,
        explanation.text,
        name,
        explanation.page,
        unit_ids,
        "Use the full explanation",
        _checks(source),
    )


def _paired_cooling_card(explanation: Item, outcome: Item) -> Card | None:
    first = re.sub(r"\W+", " ", explanation.text.casefold())
    second = re.sub(r"\W+", " ", outcome.text.casefold())
    if not re.search(r"\bmoist air rises it cools\b", first):
        return None
    if not re.search(r"\bwater vapour\b", second) or not re.search(r"\b(?:droplets|clouds)\b", second):
        return None
    source = f"{explanation.text} {outcome.text}"
    return Card(
        "learn",
        "Why do tiny water droplets form as moist air rises and cools?",
        source,
        source,
        explanation.page,
        tuple(dict.fromkeys((*explanation.unit_ids, *outcome.unit_ids))),
        "Connect cause and result",
        _checks(source),
    )


def _joined_process_card(item: Item) -> Card | None:
    sentences = split_sentences(item.text.replace("\ufffd", " "))
    if len(sentences) < 2:
        return None
    naming = _named_process(sentences[-1])
    if naming is None:
        return None
    explanation = " ".join(sentences[:-1])
    kind, name = naming
    if not _supports_named_process(explanation, kind):
        return None
    question = {
        "change": "What is this change called?",
        "movement": "What is this movement called?",
        "process": "What is this process called?",
    }[kind]
    return _card("teach", question, explanation, name, item, "Use the full explanation", item.text)


def _water_learning_card(item: Item, piece: str) -> Card | None:
    normalized = re.sub(r"\W+", " ", piece.casefold()).strip()
    prompts = (
        (
            ("sun warms water", "sun heats water", "heat from the sun"),
            "Imagine a puddle in sunshine. What happens to its water?",
            "Heat from the Sun changes liquid water into water vapour.",
            "The Sun warms water in oceans lakes and rivers",
        ),
        (
            ("water vapour cools and forms tiny droplets",),
            "When moist air rises and cools, what happens to the water vapour?",
            "As moist air rises, it cools. Water vapour cools and forms tiny droplets around particles in the air.",
            "water vapour cools and forms tiny droplets",
        ),
        (
            ("plants also release water vapour from their leaves", "plants release water vapour from their leaves"),
            "How do plants add water vapour to the water cycle?",
            "Plants also release water vapour from their leaves.",
            "plants also release water vapour from their leaves",
        ),
        (
            ("rain snow and hail are forms of precipitation", "water falls as rain snow"),
            "What can fall from clouds as precipitation? Name the forms in your sheet.",
            "The sheet names rain, snow and hail as forms of precipitation.",
            "rain snow and hail are forms of precipitation",
        ),
        (
            ("rivers carry water back towards the oceans",),
            "After rain falls on land, where can the water go next?",
            "Rainwater flows over land, and rivers carry water back towards the oceans.",
            "rivers carry water back towards the oceans",
        ),
    )
    for matches, question, answer, key in prompts:
        if any(match in normalized for match in matches):
            if "rivers carry water back" in key and "rivers carry water back" not in normalized:
                return _card("learn", question, piece, piece, item, "Think, then explain", piece)
            return _card("learn", question, piece, answer, item, "Think, then explain", piece)
    return None


def _checks(text: str) -> tuple[str, ...]:
    notes = []
    cues = list(dict.fromkeys(match.group().casefold() for match in REVIEW_CUES.finditer(text)))
    if cues:
        quoted = ", ".join(f"“{cue}”" for cue in cues)
        notes.append(f"Check first: the sheet says {quoted}. Confirm it in the textbook before learning it.")
    return tuple(notes)


def _card(kind: str, question: str, clue: str, answer: str, item: Item, about: str = "", source: str = "") -> Card:
    about = about if _readable(about) else ""
    return Card(kind, question, clue, answer, item.page, item.unit_ids, about, _checks(source or item.text))


def _tip_card(item: Item, standard: int) -> Card | None:
    body = item.text
    for separator in re.finditer(r"\s+[—–-]\s+|:\s+", body):
        lead, rest = body[: separator.start()], body[separator.end() :]
        if len(lead.split()) >= 3 and len(rest.split()) >= 3:
            return _card("tip", _ask("tip", standard), f"{lead} …", body, item, about=item.marker or "Memory tip")
    finished = _finish(body)
    if finished is None:
        return None
    return _card("tip", _ask("tip", standard), finished[0], body, item, about=item.marker or "Memory tip")


def _numeric(cell: str) -> bool:
    """A measurement or calculation ("0.50", "4/8 = 1/2", "90 g") rather than words to learn."""
    return bool(re.search(r"\d", cell)) and not re.search(r"[A-Za-z]{4,}", cell)


def _table_cards(item: Item, standard: int) -> list[Card]:
    table = item.table
    header, rows = table.header, table.rows
    labels = [cell.strip().casefold() for cell in header]
    if table.kind == "timeline":
        return _timeline_cards(item, standard)
    if table.kind == "panels":  # "WEATHER | CLIMATE" lists: sort each line into its list
        options = [cell.strip() for cell in header if cell.strip()]
        choice = " or ".join(options) if len(options) == 2 else ", ".join(options[:-1]) + " or " + options[-1]
        return [
            _card(
                "sort",
                _ask("sort", standard, choice),
                _hide_name(cell, header[column]),
                header[column].strip(),
                item,
                source=cell,
            )
            for row in rows
            for column, cell in enumerate(row)
            if cell.strip() and header[column].strip()
        ]
    asks = [index for index, label in enumerate(labels) if re.fullmatch(r"questions?|problems?|sums?|tasks?", label)]
    replies = [index for index, label in enumerate(labels) if re.fullmatch(r"answers?|solutions?|results?", label)]
    if asks and not replies and len(header) == 2:
        replies = [1 - asks[0]]  # "Question | Why it matters": the other column answers it
    if asks and replies:  # a practice table: each row is a question and its answer
        working = [index for index, label in enumerate(labels) if re.fullmatch(r"working|method|steps?|hints?", label)]
        cards = []
        for row in rows:
            question, answer = row[asks[0]].strip(), row[replies[0]].strip()
            if question and answer:
                if working and row[working[0]].strip():
                    answer = f"{answer}  (working: {row[working[0]].strip()})"
                cards.append(
                    _card("question", _ask("question", standard), question, answer, item, "Practice question", answer)
                )
        return cards
    if not header[0].strip() or labels[0] in {"feature", "features", "aspect", "aspects", "basis", "point", "points"}:
        return _compare_cards(item, standard)
    return _row_cards(item, standard)


def _compare_cards(item: Item, standard: int) -> list[Card]:
    """A "Feature | A | B | C" table: one card per feature, naming each thing compared."""
    header, rows = item.table.header, item.table.rows
    names = list(header[1:])
    cards = []
    for row in rows:
        label, values = row[0].strip(), list(row[1:])
        pairs = [
            (name, value) for name, value in zip(names, values, strict=False) if name.strip() and value.strip(" -–—")
        ]
        if not label or len(pairs) < 2 or all(_numeric(value) for _, value in pairs):
            continue
        for start in range(0, len(pairs), 5):
            chunk = pairs[start : start + 5]
            if len(chunk) < 2:
                chunk = pairs[-2:]
            clue = "\n".join(name for name, _ in chunk)
            answer = "\n".join(f"{name}: {value}" for name, value in chunk)
            claims = " ".join(value for _, value in chunk)  # check the values, not the names in the header
            question = _ask("compare", standard, label)
            cards.append(_card("compare", question, clue, answer, item, about="Compare", source=claims))
    return cards


def _row_cards(item: Item, standard: int) -> list[Card]:
    """A "Concept | Rule | Example" table: each row's description asks which one it describes."""
    header, rows = item.table.header, item.table.rows
    words = header[0].split()
    noun = (
        " ".join(word if word.isupper() and len(word) > 1 else word.lower() for word in words)
        if len(words) <= 3
        else ""
    )
    columns = [
        column
        for column in range(1, len(header))
        if sum(len(row[column].split()) >= 2 and not _numeric(row[column]) for row in rows) >= max(2, len(rows) // 2)
    ][:2]
    cards = []
    for row in rows:
        name = row[0].strip()
        for column in columns:
            cell = row[column].strip()
            if not name or len(cell.split()) < 2 or _numeric(cell):
                continue
            question = _ask("which", standard, noun) if noun else _ask("what_about", standard)
            cards.append(_card("row", question, _hide_name(cell, name), name, item, header[column].strip(), cell))
    return cards


def _timeline_cards(item: Item, standard: int) -> list[Card]:
    """Each event on a printed timeline asks for its year; one more card asks for the whole order."""
    pairs = item.table.rows
    cards = [_card("timeline", _ask("year_of", standard), event, year, item, "Timeline") for year, event in pairs]
    shuffled = sorted(event for _, event in pairs)  # alphabetical: a fixed order that is not the answer
    answer = "\n".join(f"{year}: {event}" for year, event in pairs)
    if shuffled != [event for _, event in pairs]:
        cards.append(_card("order", _ask("order", standard), "\n".join(shuffled), answer, item, "Timeline", answer))
    return cards


def _pieces(text: str) -> list[str]:
    """A point as card-sized pieces: its sentences, and long sentences split at semicolons.

    Short facts printed on one line between bullets or bars ("1 km = 1,000 m • 1 m = 100 cm") are separate pieces.
    """
    parts = _INLINE_SEPARATOR.split(text)
    if len(parts) > 1 and all(len(part.split()) <= 8 for part in parts):
        return [part.strip() for part in parts if part.strip()]
    sentences = [sentence.lstrip(BULLETS + " ") for sentence in split_sentences(text)]
    return [clause for sentence in sentences if sentence for clause in _clauses(sentence)]


def _vocabulary(pieces: list[str]) -> bool:
    labelled = [_labelled(piece) for piece in pieces]
    found = [label for label in labelled if label is not None]
    return len(found) >= 2 and len(found) >= 0.6 * len(pieces) and len({label for label, _ in found}) == len(found)


# An activity or an opinion asked of the class, not a question with one answer to check.
_ACTIVITY = re.compile(
    r"\b(?:let's|let us|find out|discuss|imagine|in groups|(?:do|did|have|can) you (?:think|know|ever|find))\b",
    re.IGNORECASE,
)
_TO_THE_READER = re.compile(r"\b(?:you|your|yourself)\b", re.IGNORECASE)


def _open_task(text: str) -> bool:
    """An activity for the class ("Discuss in groups.", "What do you think …?")."""
    return bool(_ACTIVITY.search(text))


def _point_cards(item: Item, heading: Heading | None, pieces: list[str], terms: bool, standard: int) -> list[Card]:
    cards = []
    about = heading.name if heading else item.context
    for piece in pieces:
        # A question or a word to the reader printed in the text is not a fact to finish or fill in.
        asks = _open_task(piece) or bool(_TO_THE_READER.search(piece)) or piece.endswith("?")
        if asks or _named_process(piece) is not None:
            continue
        joined = _joined_process_card(item) if piece == item.text else None
        if joined is not None:
            cards.append(joined)
            continue
        labelled = _labelled(piece)
        equation = _equation(piece)
        if equation is not None:
            clue, answer = equation  # "Area of a rectangle: A = ______"
            cards.append(_card("equation", _ask("equation", standard), clue, answer, item, about, source=piece))
            continue
        chain = _chain(piece)
        if chain is not None:
            clue, answer = chain
            cards.append(_card("chain", _ask("chain", standard), clue, answer, item, about, source=piece))
            continue
        if labelled and terms:
            label, text = labelled  # "Producer: makes its own food" under "Remember these terms"
            cards.append(
                _card("term", _ask("term", standard), _hide_name(text, label), label, item, about, source=piece)
            )
            continue
        learning = _water_learning_card(item, piece)
        if learning is not None:
            cards.append(learning)
            continue
        if re.search(r"\brainwater flows over land\b", piece, re.I):
            continue
        gap = _gap(piece)
        if gap is not None:
            kind, answer, clue = gap
            cards.append(_card("gap", _ask(kind, standard), clue, answer, item, about, source=piece))
            continue
        if heading is not None and not _MATH.search(piece):
            # Only a heading that names a person or a thing ("LONDON – Capital of …") is an answer to guess; a
            # chapter title such as "Ratios Compare Quantities" is not, so its sentences get other cards.
            names_thing = heading.person or bool(heading.after.strip(" –—-:"))
            if names_thing and not _ABSTRACT_TOPIC.search(heading.name):
                hidden = _hide_name(piece, heading.name)
                if len(hidden.replace(GAP, "").split()) >= 3:
                    question = _ask("who_about" if heading.person else "what_about", standard)
                    cards.append(_card("riddle", question, hidden, heading.name, item, source=piece))
                continue
            cloze = _key_cloze(piece)
            if cloze is not None:
                cards.append(_card("gap", _ask("word", standard), cloze[0], cloze[1], item, about, source=piece))
                continue
            recall_question = _recall_question(piece)
            if recall_question is not None:
                cards.append(_card("recall", "Answer in your own words.", recall_question, piece, item, source=piece))
                continue
            if names_thing or _ABSTRACT_TOPIC.search(heading.name):
                continue
        finished = _finish(piece)
        if finished is not None:
            named = _name_gap(piece, about) if len(finished[1].split()) - 1 > FINISH_WORDS else None
            if named is not None:
                # Half a long sentence is a hard answer to check; a name printed in it is one word or a few.
                cards.append(_card("gap", _ask("name", standard), named[0], named[1], item, about, source=piece))
            else:
                cards.append(
                    _card("finish", _ask("finish", standard), finished[0], finished[1], item, about, source=piece)
                )
    return cards


def plan_cards(sheet: Sheet, standard: int = 8) -> list[Card]:
    """One plain question per card, in the order of the sheet."""
    items = list(sheet.items)
    headings = {
        item.text: parse_heading(item.text) for item in items if item.kind == "topic" and names_topic(item.text)
    }
    answers: dict[tuple[str, str], str] = {}
    for item in items:
        if item.kind == "answer" and item.number:
            answers.setdefault((item.group, item.number), item.text)
    answer_groups = {group for group, _ in answers}
    pieces = {id(item): _pieces(item.text) for item in items if item.kind == "point"}
    cards: list[Card] = []
    consumed: set[int] = set()
    for index, item in enumerate(items):
        if index in consumed:
            continue
        if item.kind == "topic" and item.text in headings:
            heading = headings[item.text]
            if (
                heading.after.strip(" –—-:")
                and len(heading.name.split()) <= 8
                and not _ABSTRACT_TOPIC.search(heading.name)
            ):
                clue = GAP + _hide_name(heading.after, heading.name)
                cards.append(
                    _card("name", _ask("who" if heading.person else "what", standard), clue, heading.name, item)
                )
        elif item.kind == "point" and (worked := _WORKED.match(item.text)) is not None:
            task, solution = worked["task"], worked["solution"]
            question = _ask("question", standard)
            cards.append(_card("question", question, task, solution, item, "Worked example", solution))
        elif item.kind == "point" and not _NO_CARDS.match(item.context):
            if index + 1 < len(items) and items[index + 1].kind == "point" and items[index + 1].topic == item.topic:
                paired = _paired_process_card(item, items[index + 1]) or _paired_cooling_card(item, items[index + 1])
                if paired is not None:
                    cards.append(paired)
                    consumed.add(index + 1)
                    if (
                        paired.kind == "learn"
                        and index + 2 < len(items)
                        and items[index + 2].kind == "point"
                        and items[index + 2].topic == item.topic
                        and (named := _paired_process_card(items[index + 1], items[index + 2])) is not None
                    ):
                        cards.append(named)
                        consumed.add(index + 2)
                    continue
            heading = headings.get(item.topic)
            # "Term: meaning" lines listed together, with no named topic above them, are vocabulary to learn.
            siblings = [
                piece
                for other in items[max(0, index - 6) : index + 7]
                if other.kind == "point" and other.topic == item.topic and other.context == item.context
                for piece in pieces[id(other)][:1]
            ]
            terms = heading is None and (_vocabulary(pieces[id(item)]) or _vocabulary(siblings))
            cards.extend(_point_cards(item, heading, pieces[id(item)], terms, standard))
        elif item.kind == "summary":
            name, rest = summary_parts(item.text)
            heading = next((h for h in headings.values() if h.name.casefold() == name.casefold()), None)
            person = heading.person if heading else bool(_PERSON_TITLE.match(name))
            question = _ask("who_about" if person else "what_about", standard)
            cards.append(_card("summary", question, _hide_name(rest, name), name, item))
        elif item.kind == "question":
            text = _QUESTION_LABEL.sub("", item.text)
            clue = re.sub(r"_{3,}|\.{5,}|…{2,}", GAP, text)
            answer = item.answer or answers.get((item.group, item.number), "")
            if not answer and len(answer_groups) == 1:
                answer = answers.get((next(iter(answer_groups)), item.number), "")
            if answer.casefold().startswith(item.text.casefold()):
                answer = answer[len(item.text) :].strip()
            if not answer and _open_task(text):
                continue  # "What do you think …? Discuss in groups." has no answer to check
            question = _ask("fill" if GAP in clue else "question", standard)
            cards.append(_card("question", question, clue, answer, item, "Practice question", answer or item.text))
        elif item.kind == "table" and item.table is not None:
            cards.extend(_table_cards(item, standard))
        elif item.kind == "tip" and (tip := _tip_card(item, standard)) is not None:
            cards.append(tip)
    cards.extend(_picture_cards(sheet, headings, standard))
    return [card for card in cards if _readable(card.clue) and _readable(card.answer)]


def _picture_cards(sheet: Sheet, headings: dict[str, Heading], standard: int) -> list[Card]:
    """A picture printed beside a topic becomes "Who is this?"; pictures the sheet does not name are left out."""
    spans: list[tuple[int, float, float, Item]] = []
    for item in sheet.items:
        if item.kind == "topic" and item.text in headings:
            spans.append((item.page, item.top, item.bottom, item))
        elif (
            item.kind in {"point", "summary"}
            and spans
            and item.topic == spans[-1][3].text
            and item.page == spans[-1][0]
        ):
            page, top, bottom, topic = spans[-1]
            spans[-1] = (page, top, max(bottom, item.bottom), topic)
    cards = []
    for picture in sheet.pictures:
        _, top, _, bottom = picture.rect
        overlaps = [
            (min(bottom, end) - max(top, start), topic) for page, start, end, topic in spans if page == picture.page
        ]
        overlap, topic = max(overlaps, key=lambda pair: pair[0], default=(0.0, None))
        if topic is None or overlap <= 0 or picture.is_code:
            continue
        heading = headings[topic.text]
        question = _ask("who" if heading.person else "what", standard)
        cards.append(
            Card(
                "picture",
                question,
                "",
                heading.name,
                picture.page,
                topic.unit_ids,
                "Picture from your sheet",
                (),
                picture.image,
            )
        )
    return cards


# ---------------------------------------------------------------- printing


class _Type:
    """FiraGO when pymupdf-fonts is installed (it covers – — → ₹ and Indian names); built-in Helvetica otherwise."""

    def __init__(self) -> None:
        try:
            import pymupdf_fonts  # noqa: F401  (registers FiraGO with PyMuPDF)

            self.regular, self.bold = pymupdf.Font("figo"), pymupdf.Font("figbo")
            self.names = {False: "F0", True: "F1"}
            self.embedded = True
        except (ImportError, RuntimeError):
            self.regular, self.bold = pymupdf.Font("helv"), pymupdf.Font("hebo")
            self.names = {False: "helv", True: "hebo"}
            self.embedded = False
        self._advances: dict[tuple[bool, str], float] = {}

    def prepare(self, page: pymupdf.Page) -> None:
        if self.embedded:
            page.insert_font(fontname="F0", fontbuffer=self.regular.buffer)
            page.insert_font(fontname="F1", fontbuffer=self.bold.buffer)

    def printable(self, text: str, bold: bool = False) -> str:
        font = self.bold if bold else self.regular
        chars = []
        for char in text:
            if char == "\n" or (font.has_glyph(ord(char)) if self.embedded else ord(char) < 256):
                chars.append(char)
            else:
                swapped = char.translate(_SUBSTITUTES)
                chars.append(swapped if swapped != char else "?")
        return "".join(chars)

    def width(self, text: str, size: float, bold: bool = False) -> float:
        font = self.bold if bold else self.regular
        total = 0.0
        for char in text:
            advance = self._advances.get((bold, char))
            if advance is None:
                advance = self._advances[(bold, char)] = font.text_length(char, fontsize=1)
            total += advance
        return total * size

    def wrap(self, text: str, size: float, width: float, bold: bool = False) -> list[str]:
        lines: list[str] = []
        for paragraph in text.split("\n"):
            line = ""
            for word in paragraph.split():
                while len(word) > 1 and self.width(word, size, bold) > width:  # a word longer than a line is broken
                    cut = next((i for i in range(len(word) - 1, 0, -1) if self.width(word[:i], size, bold) <= width), 1)
                    if line:
                        lines.append(line)
                        line = ""
                    lines.append(word[:cut])
                    word = word[cut:]
                candidate = f"{line} {word}" if line else word
                if self.width(candidate, size, bold) <= width:
                    line = candidate
                else:
                    lines.append(line)
                    line = word
            lines.append(line)
        return lines

    def fit(self, text: str, box: pymupdf.Rect, largest: float, smallest: float, bold: bool) -> tuple[float, list[str]]:
        """The largest size at which the text fits the box; at the smallest size, overflow ends in "…"."""
        text = self.printable(text, bold)
        size = largest
        while True:
            lines = self.wrap(text, size, box.width, bold)
            if len(lines) * size * 1.22 <= box.height or size <= smallest:
                break
            size = max(smallest, round(size - 0.5, 1))
        room = max(1, int(box.height // (size * 1.22)))
        if len(lines) > room:
            lines = lines[:room]
            while lines[-1] and self.width(lines[-1] + " …", size, bold) > box.width:
                lines[-1] = lines[-1].rsplit(" ", 1)[0] if " " in lines[-1] else lines[-1][:-1]
            lines[-1] = f"{lines[-1]} …"
        return size, lines

    def draw(
        self, shape, lines: list[str], size: float, x: float, y: float, bold: bool, colour, align_right: float = 0
    ):
        for line in lines:
            y += size
            left = align_right - self.width(line, size, bold) if align_right else x
            shape.insert_text((left, y), line, fontname=self.names[bold], fontsize=size, color=colour)
            y += size * 0.22
        return y


def _card_box(position: int) -> pymupdf.Rect:
    column, row = position % 2, position // 2
    x, y = _LEFT + column * _CARD_WIDTH, _TOP + row * _CARD_HEIGHT
    return pymupdf.Rect(x, y, x + _CARD_WIDTH, y + _CARD_HEIGHT)


def _draw_card(page, shape, kind: _Type, card: Card, number: int, box: pymupdf.Rect, theme: dict) -> None:
    colour, tint = theme["colour"], theme["tint"]
    centre = pymupdf.Point(box.x0 + 24, box.y0 + 24)
    shape.draw_circle(centre, 11)
    shape.finish(color=None, fill=colour)
    label = str(number)
    size = 9.5 if number < 100 else 8
    shape.insert_text(
        (centre.x - kind.width(label, size, True) / 2, centre.y + size * 0.35),
        label,
        fontname=kind.names[True],
        fontsize=size,
        color=(1, 1, 1),
    )
    if card.about:
        about_box = pymupdf.Rect(box.x0 + 42, box.y0 + 15, box.x1 - 16, box.y0 + 36)
        size, lines = kind.fit(card.about, about_box, 9, 7, True)
        kind.draw(shape, lines[:2], size, about_box.x0, about_box.y0 + (2 if len(lines) == 1 else -2), True, colour)
    clue_box = pymupdf.Rect(box.x0 + 18, box.y0 + 44, box.x1 - 18, box.y1 - 46)
    if card.image is not None:
        page.insert_image(clue_box, stream=card.image, keep_proportion=True)
    else:
        size, lines = kind.fit(card.clue, clue_box, 14, 7, True)
        height = len(lines) * size * 1.22
        kind.draw(shape, lines, size, clue_box.x0, clue_box.y0 + max(0, (clue_box.height - height) / 2) - 2, True, _INK)
    strip = pymupdf.Rect(box.x0 + 12, box.y1 - 40, box.x1 - 12, box.y1 - 12)
    shape.draw_rect(strip, radius=0.25)
    shape.finish(color=None, fill=tint)
    inner = strip + (9, 4, -9, -4)
    size, lines = kind.fit(card.question, inner, 10, 7.5, True)
    height = len(lines) * size * 1.22
    kind.draw(shape, lines, size, inner.x0, inner.y0 + (inner.height - height) / 2 - 1, True, colour)


def _cut_lines(shape, count: int) -> None:
    for position in range(count):
        shape.draw_rect(_card_box(position))
    shape.finish(color=_CUT, width=0.5, dashes="[3 3] 0")


def _practice_prompt(card: Card) -> tuple[str, str]:
    clue = card.clue.strip()
    answer = card.answer.strip()
    blank = "________________"
    if GAP in clue:
        return clue.replace(GAP, blank), answer
    if card.kind == "teach":
        label = re.search(r"this\s+(change|movement|process)", card.question, re.I)
        if label:
            return f"{clue}\nThis {label[1]} is called {blank}.", answer
    if card.kind == "learn":
        text = answer
        preferred = (
            "water vapour",
            "liquid water",
            "tiny liquid droplets",
            "precipitation",
            "oceans",
            "rain",
            "snow",
            "hail",
        )
        for target in preferred:
            match = re.search(rf"\b{re.escape(target)}\b", text, re.I)
            if match:
                return f"{text[: match.start()]}{blank}{text[match.end() :]}", match.group()
    if answer and re.search(rf"\b{re.escape(answer)}\b", clue, re.I):
        return re.sub(rf"\b{re.escape(answer)}\b", blank, clue, count=1, flags=re.I), answer
    return f"{card.question.rstrip('?').rstrip('.')} {blank}.", answer


def _has_blank(card: Card) -> bool:
    """A fill-in card only when the blank stands for words left out of the card, not after its own question."""
    prompt, _ = _practice_prompt(card)
    return not prompt.startswith(card.question.rstrip("?").rstrip("."))


def _practice_worksheet_pages(document: pymupdf.Document, kind: _Type, cards: list[Card], theme: dict) -> None:
    margin, width = 48.0, _PAGE_WIDTH - 96.0
    page = shape = None
    y = 0.0

    def new_page(first: bool) -> None:
        nonlocal page, shape, y
        if shape is not None:
            shape.commit()
        page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        kind.prepare(page)
        shape = page.new_shape()
        title = "FILL IN THE BLANKS" if first else "FILL IN THE BLANKS (CONTINUED)"
        y = kind.draw(shape, [title], 17, margin, 40, True, theme["colour"])
        y = (
            kind.draw(
                shape,
                ["Write the missing name, year or key word. Try these before checking the answer sheet."],
                9,
                margin,
                y + 3,
                False,
                _MUTED,
            )
            + 18
        )

    new_page(True)
    for number, card in enumerate(cards, start=1):
        prompt, _ = _practice_prompt(card)
        lines = kind.wrap(kind.printable(prompt), 11, width - 42)
        height = len(lines) * 14 + 12
        if y + height > _PAGE_HEIGHT - 42:
            new_page(False)
        kind.draw(shape, [f"{number}."], 10, margin, y, True, theme["colour"])
        bottom = kind.draw(shape, lines, 11, margin + 28, y, False, _INK)
        y = max(bottom, y + 11) + 9
    shape.commit()


def _practice_reinforcement(card: Card) -> tuple[str, str]:
    answer = card.answer.strip()
    if card.kind == "teach":
        if answer.casefold() == "water cycle":
            return "What does the water cycle describe?", card.clue
        if answer.casefold() == "evaporation":
            return "What happens to liquid water during evaporation?", card.clue
        if answer.casefold() == "condensation":
            return "What happens as water vapour cools?", card.clue
        if answer.casefold() == "transpiration":
            return "How do plants add water vapour to the air?", card.clue
        return "Explain the idea in your own words.", card.clue
    if card.kind == "learn":
        return card.question, answer
    year = re.search(r"\b(?:1[0-9]{3}|20[0-9]{2})\b", answer)
    if year:
        prompt, _ = _practice_prompt(card)
        return f"What event or fact is linked to {year.group()}?", prompt.replace("________________", answer)
    if card.question and card.question not in {"Answer it.", "What is this about?"}:
        return card.question, answer
    return "Explain this fact in your own words.", answer


def _practice_pages(document: pymupdf.Document, kind: _Type, cards: list[Card], theme: dict) -> None:
    practice_cards = []
    for card in filter(_has_blank, cards):
        prompt, answer = _practice_prompt(card)
        question, explanation = _practice_reinforcement(card)
        practice_cards.append(
            Card(
                "cloze",
                question,
                prompt,
                answer,
                card.page,
                card.unit_ids,
                "Fill in the blank",
                (*card.checks, f"Follow-up answer: {explanation}"),
            )
        )
    sheets = (len(practice_cards) + _CARDS_PER_PAGE - 1) // _CARDS_PER_PAGE
    for sheet in range(sheets):
        group = practice_cards[sheet * _CARDS_PER_PAGE : (sheet + 1) * _CARDS_PER_PAGE]
        page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        kind.prepare(page)
        shape = page.new_shape()
        title = f"FILL IN THE BLANKS  ·  SHEET {sheet + 1} OF {sheets}"
        kind.draw(shape, [kind.printable(title, True)], 7.5, _LEFT, 17, True, _MUTED)
        note = "Cut along the dashed lines. Write the missing name, year or key word."
        kind.draw(shape, [kind.printable(note)], 7.5, 0, 17, False, _MUTED, align_right=_LEFT + 2 * _CARD_WIDTH)
        _cut_lines(shape, len(group))
        first = sheet * _CARDS_PER_PAGE + 1
        for position, card in enumerate(group):
            _draw_card(page, shape, kind, card, first + position, _card_box(position), theme)
        shape.commit()


def _header(shape, kind: _Type, theme: dict, sheet: int, sheets: int, first: int, last: int) -> None:
    left = f"{theme['title']}  ·  SHEET {sheet} OF {sheets}  ·  CARDS {first}–{last}"
    kind.draw(shape, [kind.printable(left, True)], 7.5, _LEFT, 17, True, _MUTED)
    note = kind.printable("Cut along the dashed lines. The answers are at the end.")
    kind.draw(shape, [note], 7.5, 0, 17, False, _MUTED, align_right=_LEFT + 2 * _CARD_WIDTH)


def _answer_pages(document, kind: _Type, cards: list[Card], theme: dict, notes: tuple[str, ...]) -> None:
    margin, width = 46.0, _PAGE_WIDTH - 92.0
    page = shape = None
    y = 0.0

    def new_page(first: bool) -> None:
        nonlocal page, shape, y
        if shape is not None:
            shape.commit()
        page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        kind.prepare(page)
        shape = page.new_shape()
        title = "ANSWER SHEET" if first else "ANSWER SHEET (CONTINUED)"
        y = kind.draw(shape, [title], 15, margin, 34, True, theme["colour"])
        note = (
            f"{theme['title'].title()}  ·  {len(cards)} cards  ·  Keep this page away from the cards. "
            "“p.” is the page of your study sheet."
        )
        y = kind.draw(shape, [kind.printable(note)], 8, margin, y + 2, False, _MUTED) + 12

    new_page(True)
    for number, card in enumerate(cards, start=1):
        answer = card.answer or "The sheet gives no answer for this question. Answer it from your notes."
        if card.kind == "learn":
            answer = f"Explain: {answer}"
        size, lines = 10.0, kind.wrap(kind.printable(answer, True), 10, width - 70, True)
        checks = [line for check in card.checks for line in kind.wrap(kind.printable(check), 8, width - 70)]
        height = len(lines) * 12.2 + len(checks) * 9.8 + 8
        if y + height > _PAGE_HEIGHT - 40:
            new_page(False)
        kind.draw(shape, [str(number)], 10, 0, y, True, theme["colour"], align_right=margin + 22)
        kind.draw(shape, [f"p. {card.page}"], 8, 0, y + 1, False, _MUTED, align_right=margin + width)
        bottom = kind.draw(shape, lines, size, margin + 32, y, True, _INK if card.answer else _MUTED)
        if checks:
            bottom = kind.draw(shape, checks, 8, margin + 32, bottom + 1, False, _ORANGE)
        y = bottom + 7
    if any(map(_has_blank, cards)):
        if y + 38 > _PAGE_HEIGHT - 40:
            new_page(False)
        y = kind.draw(shape, ["FILL-IN-THE-BLANK ANSWERS"], 12, margin + 32, y + 5, True, theme["colour"]) + 8
        for number, card in enumerate(filter(_has_blank, cards), start=1):
            _, answer = _practice_prompt(card)
            question, explanation = _practice_reinforcement(card)
            blank_lines = kind.wrap(kind.printable(f"Blank: {answer}", True), 9.5, width - 70, True)
            follow_up_lines = kind.wrap(kind.printable(f"{question} {explanation}", True), 9.5, width - 70, True)
            if explanation.strip().casefold() == answer.strip().casefold():
                follow_up_lines = []  # "Explain this fact in your own words. LONDON" only repeats the blank's answer
            lines = [*blank_lines, *follow_up_lines]
            if y + len(lines) * 11.6 + 6 > _PAGE_HEIGHT - 40:
                new_page(False)
            kind.draw(shape, [str(number)], 9.5, 0, y, True, theme["colour"], align_right=margin + 22)
            bottom = kind.draw(shape, lines, 9.5, margin + 32, y, True, _INK)
            y = bottom + 6
    for note in notes:
        lines = kind.wrap(kind.printable(note), 8.5, width - 32)
        if y + len(lines) * 10.4 + 8 > _PAGE_HEIGHT - 40:
            new_page(False)
        y = kind.draw(shape, lines, 8.5, margin + 32, y + 4, False, _ORANGE) + 4
    shape.commit()


def _has_water_cycle_evidence(cards: list[Card]) -> bool:
    source = re.sub(r"\W+", " ", " ".join(f"{card.clue} {card.answer}" for card in cards).casefold())
    return (
        all(term in source for term in ("evaporation", "condensation", "precipitation", "water vapour"))
        and ("rivers carry water back" in source or ("rainwater flows" in source and "over land" in source))
        and ("sun warms water" in source or "heat from the sun" in source)
    )


def _water_cycle_diagram(document: pymupdf.Document, kind: _Type) -> None:
    page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
    kind.prepare(page)
    shape = page.new_shape()
    kind.draw(shape, ["HOW WATER CIRCULATES"], 17, 65, 55, True, _INK)
    kind.draw(
        shape,
        ["Follow the arrows. Use your source sheet to explain each step."],
        9.5,
        65,
        78,
        False,
        _MUTED,
    )

    nodes = [
        (
            pymupdf.Rect(180, 135, 415, 245),
            "1  EVAPORATION",
            "Heat from the Sun changes liquid water into water vapour.",
        ),
        (
            pymupdf.Rect(350, 325, 540, 445),
            "2  CONDENSATION",
            "Water vapour cools and forms tiny droplets around particles in the air.",
        ),
        (pymupdf.Rect(180, 555, 415, 665), "3  PRECIPITATION", "Rain, snow and hail are forms of precipitation."),
        (pymupdf.Rect(55, 325, 245, 445), "4  COLLECTION", "Water gathers in rivers, lakes, oceans and underground."),
    ]
    fills = ((0.91, 0.95, 0.92), (0.91, 0.94, 0.98), (0.97, 0.93, 0.88), (0.90, 0.95, 0.97))
    for (box, label, detail), fill in zip(nodes, fills, strict=True):
        shape.draw_rect(box, radius=0.12)
        shape.finish(color=_CUT, fill=fill, width=0.8)
        kind.draw(shape, [label], 10, box.x0 + 12, box.y0 + 20, True, _THEMES["detective"]["colour"])
        body_box = pymupdf.Rect(box.x0 + 12, box.y0 + 34, box.x1 - 12, box.y1 - 8)
        size, lines = kind.fit(detail, body_box, 9.5, 7.5, False)
        kind.draw(shape, lines, size, body_box.x0, body_box.y0 + 2, False, _INK)

    def arrow(start: tuple[float, float], end: tuple[float, float]) -> None:
        start_point, end_point = pymupdf.Point(*start), pymupdf.Point(*end)
        shape.draw_line(start_point, end_point)
        shape.finish(color=_THEMES["detective"]["colour"], width=2)
        dx, dy = end_point.x - start_point.x, end_point.y - start_point.y
        length = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / length, dy / length
        for side in (-1, 1):
            wing = pymupdf.Point(end_point.x - 11 * ux + side * 5 * uy, end_point.y - 11 * uy - side * 5 * ux)
            shape.draw_line(end_point, wing)
            shape.finish(color=_THEMES["detective"]["colour"], width=2)

    arrow((415, 205), (420, 325))
    arrow((420, 445), (415, 555))
    arrow((180, 610), (170, 445))
    arrow((150, 325), (180, 205))
    centre = pymupdf.Rect(225, 330, 360, 440)
    shape.draw_oval(centre)
    shape.finish(color=_CUT, fill=(0.98, 0.98, 0.94), width=1)
    size, lines = kind.fit("WATER CYCLE", centre + (12, 24, -12, -20), 12, 9, True)
    kind.draw(shape, lines, size, centre.x0 + 12, centre.y0 + 42, True, _INK)
    shape.commit()


def render_cards_pdf(
    cards: list[Card], game_mode: str = "detective", standard: int = 8, notes: tuple[str, ...] = ()
) -> bytes:
    """Print the cards eight to an A4 page, fronts only, then the answer sheet and any notes for the adult."""
    theme = _THEMES[game_mode]
    kind = _Type()
    document = pymupdf.open()
    sheets = (len(cards) + _CARDS_PER_PAGE - 1) // _CARDS_PER_PAGE
    for sheet in range(sheets):
        group = cards[sheet * _CARDS_PER_PAGE : (sheet + 1) * _CARDS_PER_PAGE]
        page = document.new_page(width=_PAGE_WIDTH, height=_PAGE_HEIGHT)
        kind.prepare(page)
        shape = page.new_shape()
        first = sheet * _CARDS_PER_PAGE + 1
        _header(shape, kind, theme, sheet + 1, sheets, first, first + len(group) - 1)
        _cut_lines(shape, len(group))
        for position, card in enumerate(group):
            _draw_card(page, shape, kind, card, first + position, _card_box(position), theme)
        shape.commit()
    _practice_pages(document, kind, cards, theme)
    _answer_pages(document, kind, cards, theme, notes)
    if _has_water_cycle_evidence(cards):
        _water_cycle_diagram(document, kind)
    document.set_metadata(
        {"title": f"Learn ICSE Standard {standard} {game_mode} game", "author": "Learn Teaching Engine"}
    )
    if kind.embedded:
        document.subset_fonts()
    result = document.tobytes(garbage=4, deflate=True)
    document.close()
    return result


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
                    image_bytes = page.get_pixmap(matrix=pymupdf.Matrix(2, 2), clip=placement, alpha=False).tobytes(
                        "png"
                    )
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
    """Read the sheet (its PDF layout when given, else the inventory), plan the cards and print them."""
    if game_mode not in _THEMES:
        raise ValueError("Choose study cards, Detective or Superhero.")
    if standard not in {7, 8, 9}:
        raise ValueError("Choose ICSE Standard 7, 8, or 9.")
    if source_pdf:
        reject_generated_pdf(source_pdf)
    if not inventory.facts and not source_pdf:
        raise ValueError("No source facts were found to turn into cards.")
    sheet = read_sheet(inventory, source_pdf, pages)
    cards = plan_cards(sheet, standard)
    if not cards:
        raise ValueError(
            "No source facts were found to turn into cards. The selected pages need bullet points, sentences or "
            "practice questions."
        )
    lost = lost_text_pages(sheet)
    notes = tuple(
        f"Some text on page {page} could not be read from the PDF (its font has no letters for it), so it is on "
        "no card. Check that page by eye."
        for page in lost
    )
    return render_cards_pdf(cards, game_mode, standard, notes)
