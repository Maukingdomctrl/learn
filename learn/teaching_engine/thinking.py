"""Decide what a sentence is for before asking about it.

The card planner used to blank a word in every sentence. Here each sentence is read for its job on the sheet: a
reason ("… because …"), a result ("… led to …"), a definition of the topic, or a labelled list ("Push factors: a, b and
c"). The question asks for that job: "Why?", "What did it lead to?", "What is migration?", "Name the three push
factors of migration." Labels shared by several topics ("Term:" under Lok Sabha and under the President) become one
card that compares them.

Everything here works from the shape of the sentence, never from the subject, and every answer is the sheet's own
words. Nothing is invented.
"""

import re
from dataclasses import dataclass

_NUMBER_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
_REASON = re.compile(r"\s(?:because(?:\s+of)?|due\s+to|owing\s+to|as\s+a\s+result\s+of)\s", re.I)
_RESULT = re.compile(r"\s(?:led\s+to|leads\s+to|resulted\s+in|results\s+in)\s", re.I)
_LIST_LABEL = re.compile(r"^(?P<label>[A-Z][A-Za-z' -]{2,30}):\s+(?P<body>[^:]+?)\.?$")
# An item in a list is a short noun phrase: no verb-like joining words that would mean it is really a clause.
_NOT_AN_ITEM = re.compile(r"\b(?:for|with|from|by|to|is|are|was|were|which|that|as|unless|if|when|but|or)\b|\d", re.I)
# Headings that name a part of a chapter ("CAUSES OF THE UPRISING", "TYPES OF RESOURCES"), not a thing to identify.
SECTION_TOPIC = re.compile(
    r"^(?:the\s+)?(?P<aspect>causes?|effects?|results?|consequences?|types?|kinds?|features?|uses?|importance|"
    r"course|leaders|conservation|methods?|stages?|steps?|advantages?|disadvantages?|measures?)\b"
    r"(?:\s+(?:of|and)\s+(?P<subject>.+))?",
    re.I,
)
_SMALL_WORDS = {"of", "and", "the", "in", "on", "at", "for", "to", "a", "an"}
_DEFINITION = re.compile(r"^(?:An?\s+|The\s+)?(?P<term>[A-Za-z][A-Za-z -]{2,40}?)\s+(?:is|are)\s+(?P<meaning>.+)$")


@dataclass(frozen=True)
class Thought:
    """A question chosen for a sentence's job, with the clue it shows and the sheet's words as the answer."""

    kind: str  # why | result | define | list
    question: str
    clue: str
    answer: str


def display_name(name: str) -> str:
    """ "IRON AND STEEL INDUSTRY" → "Iron and Steel Industry"; "Lok Sabha" and "RMS Titanic" stay as printed."""
    if not name.isupper():
        return name
    words = name.split()
    shown = [
        word.lower() if index and word.lower() in _SMALL_WORDS else word if len(word) <= 3 and index else word.title()
        for index, word in enumerate(words)
    ]
    return " ".join(shown)


def is_section(topic: str) -> bool:
    return bool(SECTION_TOPIC.match(topic.strip()))


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else text + "."


def reason(piece: str) -> Thought | None:
    """ "Mills are near the fields because sugarcane dries quickly." → "Why?" with the reason as the answer."""
    found = _REASON.search(piece)
    if found is None:
        return None
    fact, why = piece[: found.start()].strip(" ,;"), piece[found.end() :].strip()
    if len(fact.split()) < 3 or len(why.split()) < 2:
        return None
    return Thought("why", "Why? Give the reason.", _sentence(fact), _sentence(why[0].upper() + why[1:]))


def result(piece: str) -> Thought | None:
    """ "His efforts led to the Widow Remarriage Act of 1856." → "What did it lead to?"."""
    found = _RESULT.search(piece)
    if found is None:
        return None
    cause, effect = piece[: found.start()].strip(" ,;"), piece[found.end() :].strip()
    if len(cause.split()) < 2 or len(effect.split()) < 2:
        return None
    joined = piece[found.start() : found.end()].strip()
    return Thought("result", "What did this lead to?", f"{cause} {joined} …", _sentence(effect))


def definition(piece: str, topic: str) -> Thought | None:
    """ "Migration is the movement of people …" under MIGRATION → "What is migration?"."""
    match = _DEFINITION.match(piece.strip())
    if match is None or not topic:
        return None
    term = match["term"].strip()
    if term.casefold() != topic.casefold():
        return None  # only the topic's own definition: "It is located in New Delhi" defines nothing
    meaning = match["meaning"].strip()
    if len(meaning.split()) < 4:
        return None
    shown = display_name(topic)
    return Thought("define", f"What is {shown}?", f"Explain {shown} in one sentence.", _sentence(piece.strip()))


def labelled_list(piece: str, topic: str) -> Thought | None:
    """ "Push factors: lack of jobs, poverty and droughts." → "Name the three push factors of migration."."""
    match = _LIST_LABEL.match(piece.strip())
    if match is None:
        return None
    label, body = match["label"].strip(), match["body"].strip()
    if not label.casefold().endswith("s"):
        return None  # "Term: 5 years, unless dissolved earlier" is one value, not a list to name
    items = [item.strip() for item in re.split(r",\s*|\s+and\s+", body) if item.strip()]
    if not 2 <= len(items) <= 6:
        return None
    if any(len(item.split()) > 3 or _NOT_AN_ITEM.search(item) for item in items):
        return None  # "steel for machines, rails and bridges" is one phrase, not three things to name
    count = _NUMBER_WORDS[len(items)]
    of = f" of {display_name(topic)}" if topic and not is_section(topic) else ""
    question = f"Name the {count} {label.lower()}{of}."
    return Thought("list", question, f"{label}: ({count})", "\n".join(items))


def aspect(piece: str, topic: str) -> Thought | None:
    """ "Political: …" under "CAUSES OF THE UPRISING" → "What was the political cause of the uprising?"."""
    section = SECTION_TOPIC.match(topic.strip())
    match = _LIST_LABEL.match(piece.strip())
    if section is None or match is None or not section["subject"]:
        return None
    kind = section["aspect"].lower()
    kind = kind[:-1] if kind.endswith("s") and not kind.endswith("ss") else kind
    label = match["label"].strip().lower()
    subject = section["subject"].strip().lower()
    named = label if kind in label.split() else f"{label} {kind}"  # "Immediate cause" is already a cause
    body = match["body"].strip()
    question = f"What was the {named} of {subject}?"
    return Thought("aspect", question, named[0].upper() + named[1:], _sentence(body[0].upper() + body[1:]))


def think(piece: str, topic: str = "") -> Thought | None:
    """The best question for a sentence's job, or None when it is a plain fact for the other card types."""
    return (
        labelled_list(piece, topic)
        or aspect(piece, topic)
        or reason(piece)
        or result(piece)
        or definition(piece, topic)
    )


@dataclass(frozen=True)
class Comparison:
    label: str
    values: tuple[tuple[str, str], ...]  # (topic name, the sheet's words after the label)


def comparisons(points: list[tuple[str, str]]) -> list[Comparison]:
    """Labels printed under two or more topics ("Term:" under Lok Sabha and the President) to compare.

    ``points`` are (topic name, sentence) pairs in sheet order.
    """
    found: dict[str, dict[str, str]] = {}
    labels: dict[str, str] = {}
    for topic, piece in points:
        match = re.match(r"^(?P<label>[A-Z][A-Za-z' -]{2,30}):\s+(?P<value>.+)$", piece.strip())
        if match is None or not topic:
            continue
        key = match["label"].strip().casefold().removesuffix("s")  # "Raw material" and "Raw materials" match
        labels.setdefault(key, match["label"].strip())
        found.setdefault(key, {}).setdefault(topic, match["value"].strip().rstrip("."))
    return [Comparison(labels[key], tuple(values.items())) for key, values in found.items() if 2 <= len(values) <= 5]
