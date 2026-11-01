"""Fixed, checked Question Pattern Engine for Key Facts cards (Prompt 9).

Every Key Facts question is built from a fixed template (T1–T9) plus the sheet's
own words and is checked against Checks 1–6 before use. When a question template
(T1–T8) does not fit cleanly, the engine falls back to T9 (fill-the-gap).

Templates (tried in order: T7, T8, T2, T1, T4, T6, T5, T3, T9):
  - T1 — WHO (person or group):
      "Who <verb_phrase>?"
      Prompt: "Name the person" or "Name the group"
  - T2 — WHO-TITLE (sobriquet / title / role):
      "Who was known as the '<Title>'?" or "Who was the <Role> of <Y>?"
      Prompt: "Name the person"
  - T3 — WHAT-CALLED (defined term):
      "What is <definition> called?" or "What is a <definition> called?"
      Prompt: "Name the term"
  - T4 — WHEN (date or year):
      "When was <subject> <past_participle>?" or "When did <subject> <base_verb>?"
      Prompt: "Give the date or year"
  - T5 — WHERE (place, river, building, city, state, country):
      "Where is <subject> <located/situated/held>?" or "On which river is <subject> situated?"
      or "Where was <subject> <founded/held/built/born>?"
      Prompt: "Name the place" or "Name the river"
  - T6 — HOW MANY / HOW MUCH / HOW LONG / HOW FAR (count or measurement):
      "How many <plural_noun> <rest_of_clause>?" or "What is the <property> of <subject>?"
      Prompt: "Give the number" or "Give the number and unit"
  - T7 — WHICH-GOES-WITH (pair / table cell / symbol / capital):
      "What is the capital of <Place>?" / "What does the symbol <X> stand for?" /
      "What is the chemical formula of <Substance>?" / "What is the SI unit of <Quantity>?" /
      "Which <column_header> goes with <row_header>?"
      Prompt: matches the column or pair type
  - T8 — FORMULA:
      "Complete: <left> = ______" or "Complete: <reactants> → ______"
      Prompt: "Complete the formula" or "Complete the equation"
  - T9 — GAP (fallback when T1–T8 return None):
      "<Fact sentence with the answer replaced by ______>"
      Prompt: from Prompt 8's expression family
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Fixed Word Lists (Prompt 9 Step 2)
# ---------------------------------------------------------------------------

QUESTION_WORDS: frozenset[str] = frozenset(
    {
        "who",
        "what",
        "when",
        "where",
        "which",
        "how",
        "many",
        "much",
        "long",
        "far",
        "was",
        "were",
        "is",
        "are",
        "did",
        "does",
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "at",
        "to",
        "by",
        "for",
        "with",
        "from",
        "under",
        "called",
        "known",
        "as",
        "stand",
        "stands",
        "goes",
        "situated",
        "located",
        "held",
        "associated",
        "complete",
        "data",
        "table",
    }
)

PAST_TO_BASE_VERBS: dict[str, str] = {
    "founded": "found",
    "established": "establish",
    "started": "start",
    "began": "begin",
    "opened": "open",
    "built": "build",
    "wrote": "write",
    "authored": "author",
    "published": "publish",
    "invented": "invent",
    "discovered": "discover",
    "led": "lead",
    "chaired": "chair",
    "headed": "head",
    "moved": "move",
    "passed": "pass",
    "adopted": "adopt",
    "signed": "sign",
    "joined": "join",
    "became": "become",
    "won": "win",
    "received": "receive",
    "graduated": "graduate",
    "studied": "study",
    "died": "die",
    "fell": "fall",
    "rose": "rise",
    "grew": "grow",
    "came": "come",
    "took": "take",
    "made": "make",
    "gave": "give",
    "held": "hold",
    "met": "meet",
    "sailed": "sail",
    "marched": "march",
    "fought": "fight",
    "defeated": "defeat",
    "captured": "capture",
    "ruled": "rule",
    "reigned": "reign",
    "abolished": "abolish",
    "introduced": "introduce",
    "formed": "form",
    "created": "create",
    "organised": "organise",
    "organized": "organize",
    "proclaimed": "proclaim",
    "declared": "declare",
    "launched": "launch",
    "entered": "enter",
    "reached": "reach",
    "visited": "visit",
    "returned": "return",
    "left": "leave",
    "sent": "send",
    "brought": "bring",
    "taught": "teach",
    "worked": "work",
    "served": "serve",
    "lived": "live",
}

BASE_TO_PAST_VERBS: dict[str, str] = {v: k for k, v in PAST_TO_BASE_VERBS.items()}

CLASS_WORDS: frozenset[str] = frozenset(
    {
        "river",
        "city",
        "state",
        "country",
        "capital",
        "planet",
        "gas",
        "metal",
        "acid",
        "base",
        "salt",
        "organ",
        "bone",
        "muscle",
        "vitamin",
        "disease",
        "instrument",
        "unit",
        "symbol",
        "formula",
        "equation",
        "law",
        "treaty",
        "act",
        "movement",
        "session",
        "committee",
        "assembly",
        "institution",
        "organisation",
        "organization",
        "sabha",
        "samaj",
        "party",
        "company",
        "college",
        "university",
        "school",
        "bank",
        "theatre",
        "museum",
        "port",
        "shipyard",
        "ship",
        "book",
        "newspaper",
        "journal",
        "term",
        "process",
        "method",
        "substance",
        "element",
        "compound",
        "mixture",
        "force",
        "energy",
        "wave",
        "layer",
        "part",
        "type",
        "group",
        "person",
        "place",
        "number",
        "date",
        "year",
        "century",
        "period",
        "age",
        "quantity",
        "chemical",
        "si",
        "population",
        "area",
        "length",
        "height",
        "distance",
        "speed",
        "melting",
        "boiling",
        "point",
        "atomic",
        "ph",
        "valency",
    }
)

ALLOWED_TEMPLATE_WORDS: frozenset[str] = (
    QUESTION_WORDS
    | frozenset(PAST_TO_BASE_VERBS.keys())
    | frozenset(PAST_TO_BASE_VERBS.values())
    | CLASS_WORDS
)

TEMPLATE_PRIORITY_ORDER: tuple[str, ...] = (
    "T7",
    "T8",
    "T2",
    "T1",
    "T4",
    "T6",
    "T5",
    "T3",
    "T9",
)

_STOP_WORDS_CHECK: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "by",
        "with",
        "from",
        "and",
        "or",
        "as",
    }
)

_PRONOUN_GIVEAWAY_SET: frozenset[str] = frozenset(
    {
        "he",
        "she",
        "it",
        "they",
        "him",
        "her",
        "them",
        "his",
        "hers",
        "its",
        "their",
        "theirs",
        "this",
        "that",
        "these",
        "those",
        "there",
        "here",
    }
)

_PASSIVE_PARTICIPLES: frozenset[str] = frozenset(
    {
        "founded",
        "established",
        "started",
        "opened",
        "built",
        "written",
        "authored",
        "published",
        "invented",
        "discovered",
        "led",
        "chaired",
        "headed",
        "passed",
        "adopted",
        "signed",
        "formed",
        "created",
        "organised",
        "organized",
        "proclaimed",
        "declared",
        "launched",
        "held",
        "born",
        "elected",
        "appointed",
        "made",
        "given",
        "known",
        "called",
        "enacted",
        "constructed",
        "designed",
        "defeated",
        "captured",
        "abolished",
        "introduced",
    }
)

_NAME_DATES_TITLE_LINE_RE = re.compile(
    r"^(?:(?:\d+|[A-Z])[.)]\s*)?((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|Smt\.|Lokmanya|Mahatma)\s+)?[A-Z][A-Za-z.\s’'\-]{2,38}?)\s*"
    r"\(\s*(\d{3,4}\s*[–\-—]\s*(?:\d{2,4}|present))\s*\)\s*[–—\-:]\s*(.+)$"
)


def _norm(text: str) -> str:
    s = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__|</?b>", lambda m: m.group(1) or m.group(2) or "", text or "")
    s = re.sub(r"^(?:[•\-\*▪▸◦Æƒ‹\{]|\(\d+\)|\d+[.)]|[a-zA-Z][.)])\s+", "", s.strip())
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b(\d{1,2}),\s+(\d{2}),\s+(\d{3})\b", r"\1,\2,\3", s)
    s = re.sub(r"\b(\d{1,3}),\s+(\d{3})\b", r"\1,\2", s)
    return s


def _strip_markup_only(text: str) -> str:
    s = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__|</?b>", lambda m: m.group(1) or m.group(2) or "", text or "")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b(\d{1,2}),\s+(\d{2}),\s+(\d{3})\b", r"\1,\2,\3", s)
    s = re.sub(r"\b(\d{1,3}),\s+(\d{3})\b", r"\1,\2", s)
    return s


def _max_words_for_standard(standard: int = 8) -> int:
    if standard <= 5:
        return 12
    if standard <= 8:
        return 20
    return 25


def _tokenize_words(text: str) -> list[str]:
    """Extract lowercase word tokens from `text` (ignoring blanks `______` and punctuation)."""
    cleaned = re.sub(r"_{2,}", " ", text or "")
    tokens: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹’'\-]+", cleaned):
        w = raw.strip("’'-").lower()
        if w.endswith("'s") or w.endswith("’s"):
            w = w[:-2]
        if w:
            tokens.append(w)
    return tokens


def _looks_like_group_answer(answer: str) -> bool:
    return bool(
        re.search(
            r"\b(?:Assembly|Committee|Commission|Congress|Parliament|Sabha|Samaj|Party|Society|Association|League|Council|Senedd|Union|Moderates|Extremists|Nationalists)\b",
            answer or "",
            re.IGNORECASE,
        )
    )


def _lower_first_if_not_proper(phrase: str, source_sentence: str = "") -> str:
    """Lowercase the first word of `phrase` unless it is a proper noun, pronoun 'I', or acronym."""
    p = phrase.strip()
    if not p:
        return p
    words = p.split()
    w0 = words[0]
    w0_clean = w0.strip(",.:;()'\"‘’“”")
    if len(w0_clean) > 1 and w0_clean.isupper():
        return p
    # If `w0_clean` appears capitalized mid-sentence in `source_sentence`, keep it capitalized
    if source_sentence:
        mid_sent = source_sentence[1:] if len(source_sentence) > 1 else ""
        if re.search(r"\b" + re.escape(w0_clean) + r"\b", mid_sent):
            return p
    # Common determiners/words at the start of a sentence that should be lowercased mid-question
    if w0_clean.lower() in {
        "the",
        "a",
        "an",
        "this",
        "that",
        "these",
        "those",
        "its",
        "his",
        "her",
        "their",
        "our",
        "one",
        "two",
        "three",
        "four",
        "five",
        "six",
        "seven",
        "eight",
        "nine",
        "ten",
        "first",
        "second",
        "third",
        "matter",
        "materials",
        "heating",
        "cooling",
        "melting",
        "boiling",
        "evaporation",
        "condensation",
        "freezing",
        "sublimation",
        "filtration",
        "distillation",
        "decantation",
        "solubility",
        "force",
        "speed",
        "acceleration",
        "atoms",
        "molecules",
        "elements",
        "compounds",
        "mixtures",
        "reactants",
        "products",
        "indicators",
        "values",
        "tourism",
        "population",
    }:
        words[0] = w0[0].lower() + w0[1:]
        return " ".join(words)
    return p


# ---------------------------------------------------------------------------
# Template Builders T1 – T9 (Prompt 9 Step 2)
# ---------------------------------------------------------------------------


def build_t1_who(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, str] | None:
    """T1 — WHO (person or group):
      Active:  "<Answer> <verb_phrase>." -> "Who <verb_phrase>?"
      Passive: "<Object> was/were <past_participle> by <Answer> [rest]." -> "Who <past_verb> <object> [rest]?"
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None
    # Never apply T1 to a 'Name (dates) – Title' heading/fact line (must stay T9 gap)
    if _NAME_DATES_TITLE_LINE_RE.match(sent):
        return None
    # Only apply T1 to a proper person/group name (not a technical term, place after 'in/at/on', or date/number)
    if any(ch.isdigit() for ch in ans) or not ans[0].isupper():
        return None
    if expr_match and expr_match.get("family") not in {"E", "L", "bold"}:
        return None
    if expr_match and expr_match.get("type") in {
        "sobriquet_known_as",
        "role_title_of",
        "place_name",
        "organisation_document_event",
    } and not re.match(rf"^(?:The\s+)?{re.escape(ans)}\s+(?:founded|established|built|invented|discovered|wrote|authored|chaired|headed|led|adopted|proclaimed|appointed|elected)\b", sent, re.IGNORECASE):
        if " by " not in sent.lower():
            return None

    prompt = "Name the group" if _looks_like_group_answer(ans) else "Name the person"

    # Case 1 (Active): "<Answer> <verb_phrase>." where <verb_phrase> starts with a known finite verb
    m_act = re.match(
        rf"^(?:The\s+)?{re.escape(ans)}\s+(?:\([^)]*\)\s+)?([a-z][a-z\-]+)\s+(.+?)\.?$",
        sent,
    )
    if m_act:
        verb_w = m_act.group(1).lower()
        rest_vp = m_act.group(2).strip()
        if verb_w in PAST_TO_BASE_VERBS and verb_w not in {"graduated", "studied", "died", "lived", "worked", "served"}:
            # Do not convert simple SVO sentences that tests expect as T9 gap unless they are clear Who-questions
            # Wait: let's check if T1 is valid here:
            front = f"Who {verb_w} {rest_vp}?"
            return {"front": front, "prompt": prompt, "template": "T1"}
        if verb_w in {"was", "were"} and re.match(r"^(?:the\s+)?(?:first|founder|author|leader|president|chairman|creator|inventor|discoverer)\b", rest_vp, re.IGNORECASE):
            front = f"Who {verb_w} {rest_vp}?"
            return {"front": front, "prompt": prompt, "template": "T1"}

    # Case 2 (Passive): "<Obj> was/were <participle> [prep_before] by <Answer> [rest]."
    m_pass = re.match(
        rf"^(.+?)\s+(?:was|were)\s+([a-z]+)\s+(.*?)\bby\s+(?:the\s+)?{re.escape(ans)}(?:\s+(.+?))?\.?$",
        sent,
        re.IGNORECASE,
    )
    if m_pass:
        obj_phrase = _lower_first_if_not_proper(m_pass.group(1).strip(), sent)
        participle = m_pass.group(2).strip().lower()
        mid_phrase = (m_pass.group(3) or "").strip()
        tail_phrase = (m_pass.group(4) or "").strip()
        # Convert passive participle to active past tense if identical or known
        active_past = participle if participle in PAST_TO_BASE_VERBS else None
        if participle == "written":
            active_past = "wrote"
        elif participle == "built":
            active_past = "built"
        elif participle == "led":
            active_past = "led"
        elif participle == "made":
            active_past = "made"
        elif participle == "held":
            active_past = "held"
        if active_past:
            parts = [f"Who {active_past}", obj_phrase]
            if mid_phrase:
                parts.append(mid_phrase)
            if tail_phrase:
                parts.append(tail_phrase)
            front = " ".join(parts).strip() + "?"
            return {"front": front, "prompt": prompt, "template": "T1"}

    # Case 3 (Passive participle at start of sentence): "Launched on <date> by <Answer> ..., the <Subject> ..."
    m_part_lead = re.match(
        rf"^([A-Z][a-z]+)\s+(.+?)\s+by\s+(?:the\s+)?{re.escape(ans)}\b(?:,\s*|\s+)(?:the\s+)?([A-Z][A-Za-z0-9\s’'\-–]+?)(?:\s+(?:was|were|saw|marked|began|started|took)\b.*)?\.?$",
        sent,
    )
    if m_part_lead:
        part_w = m_part_lead.group(1).lower()
        mid_adv = m_part_lead.group(2).strip()
        subj_np = m_part_lead.group(3).strip()
        if part_w in PAST_TO_BASE_VERBS:
            front = f"Who {part_w} the {subj_np} {mid_adv}?"
            return {"front": front, "prompt": prompt, "template": "T1"}

    return None


def build_t2_who_title(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, str] | None:
    """T2 — WHO-TITLE (sobriquet / title / role):
      Pattern: "Who was known as the '<Title>'?" or "Who was the <Role> of <Y>?"
      or "What was <Person> known as?" (when the title itself is the answer).
      Prompt: "Name the person" (or "Give the title or role" when the title is blanked)
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .'\"‘’“”")
    if not sent or not ans:
        return None
    if _NAME_DATES_TITLE_LINE_RE.match(sent):
        return None

    # Subcase A: Answer is the person, sentence has "known as / called '<Title>'"
    m_known_person = re.search(
        rf"^(?:The\s+)?{re.escape(ans)}\s+(?:was|is)\s+(?:also\s+|popularly\s+)?(?:known|called)\s+as\s+(?:the\s+)?[‘'“\"]?([^’'”\".]+)[’'”\"]?\.?$",
        sent,
        re.IGNORECASE,
    )
    if m_known_person:
        title_str = m_known_person.group(1).strip()
        front = f"Who was known as the '{title_str}'?"
        return {"front": front, "prompt": "Name the person", "template": "T2"}

    # Subcase B: Answer is the sobriquent/title in "<Person> was known as the '<Answer>'" or "Known as the '<Answer>'"
    m_known_title = re.search(
        rf"\b(?:known|called)\s+(?:as\s+)?(?:the\s+)?[‘'“\"]?{re.escape(ans)}[’'”\"]?",
        sent,
        re.IGNORECASE,
    )
    if m_known_title and (not expr_match or expr_match.get("type") == "sobriquet_known_as" or "'" in sentence or "‘" in sentence):
        person_name = subject.strip()
        m_p = re.match(r"^([A-Z][A-Za-z.\s’'\-]{2,35}?)\s+(?:was|is)\s+(?:also\s+|popularly\s+)?(?:known|called)\b", sent)
        if m_p:
            person_name = m_p.group(1).strip()
        if person_name and person_name.lower() != ans.lower() and ans.lower() not in person_name.lower():
            front = f"What was {person_name} known as?"
            return {"front": front, "prompt": "Give the title or role", "template": "T2"}

    # Subcase C: "<Role> of <Y>: <Answer>" or "<Answer> was the <first/permanent> <Role> of <Y>"
    m_role_colon = re.match(
        rf"^((?:First|Permanent|Deputy|Acting|Founding)\s+[A-Z][A-Za-z\s]+?)\s*:\s*{re.escape(ans)}\b",
        sent,
    )
    if m_role_colon:
        role_str = m_role_colon.group(1).strip()
        if subject and subject.lower() not in role_str.lower() and subject.lower() != ans.lower():
            front = f"Who was the {role_str} of the {subject}?"
        else:
            front = f"Who was the {role_str}?"
        return {"front": front, "prompt": "Name the person", "template": "T2"}

    m_role_sent = re.match(
        rf"^{re.escape(ans)}\s+(?:was|is)\s+(?:elected\s+|appointed\s+)?(?:the\s+)?((?:first|permanent|founding)\s+[A-Za-z\s]+?\s+of\s+(?:the\s+)?[A-Z][A-Za-z\s]+?)(?:\s+in\s+\d{{4}})?\.?$",
        sent,
        re.IGNORECASE,
    )
    if m_role_sent:
        role_phrase = m_role_sent.group(1).strip()
        front = f"Who was the {role_phrase}?"
        return {"front": front, "prompt": "Name the person", "template": "T2"}

    return None


def build_t3_what_called(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, str] | None:
    """T3 — WHAT-CALLED (defined term):
      Pattern: "What is <definition> called?" or "What is a <definition> called?"
      Use ONLY when the sentence has "<Term> is/means/refers to <definition>",
      "<Term>: <definition>" or "<definition> is called/known as <Term>", and
      the definition is 3–12 words.
      Prompt: "Name the term"
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None
    if any(ch.isdigit() for ch in ans) and not re.search(r"[A-Za-z]", ans):
        return None
    # Skip multi-sentence lines or lines with semicolons so we never stuff a compound sentence into T3
    if ";" in sent or ". " in sent.rstrip("."):
        return None

    defn_text = ""

    # Form 1: "<Term>: <definition>."
    m_colon = re.match(rf"^(?:The\s+|A\s+|An\s+)?{re.escape(ans)}\s*:\s*(.+?)\.?$", sent, re.IGNORECASE)
    if m_colon:
        defn_text = m_colon.group(1).strip()

    # Form 2: "<Term> is/means/refers to/is defined as <definition>."
    if not defn_text:
        m_is = re.match(
            rf"^(?:The\s+|A\s+|An\s+)?{re.escape(ans)}\s+(?:is\s+defined\s+as|refers\s+to|means|is)\s+(.+?)\.?$",
            sent,
            re.IGNORECASE,
        )
        if m_is:
            defn_text = m_is.group(1).strip()

    # Form 3: "<Definition> is called / known as <Term>."
    if not defn_text:
        m_called = re.match(
            rf"^(.+?)\s+(?:is|are)\s+(?:called|known\s+as)\s+(?:a\s+|an\s+|the\s+)?[‘'“\"]?{re.escape(ans)}[’'”\"]?\.?$",
            sent,
            re.IGNORECASE,
        )
        if m_called:
            defn_text = m_called.group(1).strip()

    if not defn_text:
        return None

    # Reject if definition has subordinate clauses or pronouns referring back to the term ("its", "it", "their", "they", "which", "that", "because", "while", "whereas")
    defn_words = defn_text.split()
    if not (3 <= len(defn_words) <= 12):
        return None
    if any(
        w.strip(",.:;()'\"‘’“”").lower() in {"it", "its", "they", "their", "them", "because", "while", "whereas", "although", "though", "if", "when"}
        for w in defn_words
    ):
        return None
    # Definition must start with a noun phrase ("a ...", "an ...", "the ...", "anything ...", "change ...", "distance ...", "solid ...", "gas ...", "liquid ...")
    defn_lower = _lower_first_if_not_proper(defn_text, sent)
    first_w = defn_lower.split()[0].lower()
    if first_w in {"not", "very", "also", "only", "usually", "generally", "commonly", "often"}:
        return None
    # Avoid awkward "What is a push or pull on an object called?"? No, "What is a push or pull on an object called?" is 10 words and super clear!
    # Wait: what about "Melting is solid to liquid" -> "What is solid to liquid called?" vs "What is a change from solid directly to gas called?"
    if re.match(r"^(?:solid|liquid|gas)\s+to\s+(?:solid|liquid|gas)$", defn_lower, re.IGNORECASE):
        return None

    front = f"What is {defn_lower} called?"
    return {"front": front, "prompt": "Name the term", "template": "T3"}


def build_t4_when(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, str] | None:
    """T4 — WHEN (date or year):
      Pattern:
        "When was <subject> <past_participle>?"
        or "When did <subject> <base_verb>?"
      Use ONLY when the verb is 'was/were <participle>' or has a base form in PAST_TO_BASE_VERBS.
      Otherwise return None (fall back to T9).
      Prompt: "Give the date or year"
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None
    if _NAME_DATES_TITLE_LINE_RE.match(sent):
        return None

    # Answer must be a date or year (Family A or date_or_year)
    is_date_or_year = bool(
        (expr_match and expr_match.get("family") == "A")
        or re.fullmatch(r"(?:1\d{3}|20\d{2})(?:\s*[–\-]\s*(?:\d{2}|\d{4}))?", ans)
        or re.search(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\b",
            ans,
            re.IGNORECASE,
        )
    )
    if not is_date_or_year:
        return None

    # Skip multi-sentence lines or lines with semicolons unless we can cleanly isolate the clause containing `ans`
    clauses = [c.strip() for c in re.split(r"[.;]", sent) if c.strip() and ans in c]
    clause = clauses[0] if clauses else sent

    # Strip parenthetical trailing notes like "(HQ in Edinburgh)" or "(2011 census)" if not containing `ans`
    clause_clean = re.sub(r"\s*\([^)]*\)", lambda m: m.group(0) if ans in m.group(0) else "", clause).strip()

    # Check if clause has a colon prefix like "Centre of banking for over 300 years: Bank of Scotland founded in 1695"
    if ": " in clause_clean:
        rhs_part = clause_clean.split(": ", 1)[1].strip()
        if ans in rhs_part:
            clause_clean = rhs_part

    # Pattern 1 (Passive): "<Subject> was/were <participle> [complement] in/on <Answer>"
    m_pass = re.match(
        rf"^([A-Z][A-Za-z0-9’'\-–\s]{{1,45}}?)\s+(was|were)\s+([a-z]+)(?:\s+(.+?))?\s+(?:in|on|around|during)\s+(?:the\s+year\s+)?{re.escape(ans)}$",
        clause_clean,
    )
    if m_pass:
        subj_phrase = _lower_first_if_not_proper(m_pass.group(1).strip(), clause_clean)
        aux = m_pass.group(2).lower()
        participle = m_pass.group(3).lower()
        comp = (m_pass.group(4) or "").strip()
        if participle in _PASSIVE_PARTICIPLES:
            tail = f"{participle} {comp}".strip() if comp else participle
            front = f"When {aux} {subj_phrase} {tail}?"
            return {"front": front, "prompt": "Give the date or year", "template": "T4"}

    # Pattern 2 (Subjectless passive fragment with known `subject`):
    # e.g. "Founded in 1695" or "Bank of Scotland founded in 1695" or "Made a city in 1905" or "Proclaimed capital of Wales in 1955"
    m_part_no_aux = re.match(
        rf"^([A-Z][A-Za-z0-9’'\-–\s]{{1,40}}?)\s+(founded|established|built|opened|adopted|proclaimed|launched|held|formed|created)\s+(?:(.+?)\s+)?(?:in|on)\s+(?:the\s+year\s+)?{re.escape(ans)}$",
        clause_clean,
    )
    if m_part_no_aux:
        subj_p = _lower_first_if_not_proper(m_part_no_aux.group(1).strip(), clause_clean)
        part_w = m_part_no_aux.group(2).lower()
        comp = (m_part_no_aux.group(3) or "").strip()
        tail = f"{part_w} {comp}".strip() if comp else part_w
        if not subj_p.lower().startswith("the ") and re.match(r"^(?:Bank|Royal\s+Bank|University|College|Indian\s+National|Constituent)\b", subj_p):
            subj_p = f"the {subj_p}"
        front = f"When was {subj_p} {tail}?"
        return {"front": front, "prompt": "Give the date or year", "template": "T4"}

    if subject and subject.lower() not in ans.lower():
        m_frag_pass = re.match(
            rf"^(?:Was\s+|Were\s+)?(founded|established|built|opened|adopted|proclaimed|launched|held|made|born|elected|appointed)\s+(?:(.+?)\s+)?(?:in|on)\s+(?:the\s+year\s+)?{re.escape(ans)}$",
            clause_clean,
            re.IGNORECASE,
        )
        if m_frag_pass:
            part_w = m_frag_pass.group(1).lower()
            comp = (m_frag_pass.group(2) or "").strip()
            tail = f"{part_w} {comp}".strip() if comp else part_w
            front = f"When was {subject} {tail}?"
            return {"front": front, "prompt": "Give the date or year", "template": "T4"}

    # Pattern 3 (Active): "<Subject> <past_verb> [object] in/on <Answer>"
    # Use ONLY when <past_verb> is in PAST_TO_BASE_VERBS!
    m_act = re.match(
        rf"^([A-Z][A-Za-z0-9’'\-–\s]{{1,45}}?)\s+([a-z]+)(?:\s+(.+?))?\s+(?:in|on)\s+(?:the\s+year\s+)?{re.escape(ans)}$",
        clause_clean,
    )
    if m_act:
        subj_phrase = _lower_first_if_not_proper(m_act.group(1).strip(), clause_clean)
        past_verb = m_act.group(2).lower()
        rest_obj = (m_act.group(3) or "").strip()
        if past_verb in {"was", "were", "is", "are", "has", "have", "had"}:
            return None
        base_verb = PAST_TO_BASE_VERBS.get(past_verb)
        if not base_verb:
            # Verb not in PAST_TO_BASE_VERBS -> MUST return None (fall back to T9)
            return None
        tail = f"{base_verb} {rest_obj}".strip() if rest_obj else base_verb
        front = f"When did {subj_phrase} {tail}?"
        return {"front": front, "prompt": "Give the date or year", "template": "T4"}

    return None


def build_t5_where(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, str] | None:
    """T5 — WHERE (place, river, building, city, state, country):
      Patterns:
        - "On which river is <subject> situated?"
        - "Where is <subject> <located/situated/held>?"
        - "Where was <subject> <founded/held/built/born>?"
      Prompt: "Name the river" or "Name the place"
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None
    if _NAME_DATES_TITLE_LINE_RE.match(sent):
        return None

    # Subcase 1: River ("Situated on the River Thames...", "<Subject> lies/is situated on the <River>")
    is_river = bool(
        re.search(r"\bRiver\b", ans, re.IGNORECASE)
        or (expr_match and expr_match.get("type") == "river_water_body")
        or re.search(rf"\bon\s+the\s+(?:banks\s+of\s+the\s+)?{re.escape(ans)}\b", sent, re.IGNORECASE)
    )
    if is_river and re.search(r"\b(?:situated|located|lying|lies|stands|built)\s+on\s+(?:the\s+)?(?:banks\s+of\s+(?:the\s+)?)?", sent, re.IGNORECASE):
        subj_name = subject.strip()
        m_s = re.match(r"^([A-Z][A-Za-z\s’'\-]{1,30}?)\s+(?:is\s+)?(?:situated|located|lying|lies|stands)\s+on\b", sent)
        if m_s:
            subj_name = m_s.group(1).strip()
        if subj_name and subj_name.lower() != ans.lower() and ans.lower() not in subj_name.lower():
            front = f"On which river is {subj_name} situated?"
            return {"front": front, "prompt": "Name the river", "template": "T5"}

    # Subcase 2: "<Subject> is located/situated in/at <Answer>."
    m_loc_pres = re.match(
        rf"^([A-Z][A-Za-z0-9\s’'\-–]{{1,45}}?)\s+is\s+(located|situated|held)\s+(?:in|at|on)\s+(?:the\s+)?{re.escape(ans)}\.?$",
        sent,
    )
    if m_loc_pres:
        subj_p = _lower_first_if_not_proper(m_loc_pres.group(1).strip(), sent)
        part_w = m_loc_pres.group(2).lower()
        front = f"Where is {subj_p} {part_w}?"
        return {"front": front, "prompt": "Name the place", "template": "T5"}

    # Subcase 3: "<Subject> was founded/held/built/born/established/signed/opened in/at <Answer>."
    m_loc_past = re.match(
        rf"^([A-Z][A-Za-z0-9\s’'\-–]{{1,45}}?)\s+was\s+(founded|held|built|born|established|signed|opened)\s+(?:in|at)\s+(?:the\s+)?{re.escape(ans)}\.?$",
        sent,
    )
    if m_loc_past:
        subj_p = _lower_first_if_not_proper(m_loc_past.group(1).strip(), sent)
        part_w = m_loc_past.group(2).lower()
        front = f"Where was {subj_p} {part_w}?"
        return {"front": front, "prompt": "Name the place", "template": "T5"}

    return None


def build_t6_how_many(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
) -> dict[str, str] | None:
    """T6 — HOW MANY / HOW MUCH / HOW LONG / HOW FAR (count or measurement):
      Patterns:
        - "How many <plural_noun> <rest_of_clause>?"
        - "What is the <property> of <subject>?" (population, area, length, height, distance, speed, melting point, boiling point, atomic number, pH, valency)
      Prompt: "Give the number" or "Give the number and unit"
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None
    if not any(ch.isdigit() for ch in ans) and not (
        expr_match and expr_match.get("family") in {"B", "C"}
    ):
        return None

    has_unit = bool(
        re.search(r"[A-Za-z°%£₹$]", ans)
        and not re.fullmatch(r"\d{1,3}(?:,\d{2,3})*(?:\.\d+)?", ans)
    )
    prompt = "Give the number and unit" if has_unit else "Give the number"

    # Subcase 1: Property of <subject> ("population about 286,000", "melting point of 3,380 °C", "distance of 387 km")
    m_prop = re.search(
        rf"\b(population|area|length|height|distance|speed|melting\s+point|boiling\s+point|atomic\s+number|valency)\s+(?:of\s+|is\s+|was\s+)?(?:about\s+|around\s+|nearly\s+|over\s+|approximately\s+)?{re.escape(ans)}\b",
        sent,
        re.IGNORECASE,
    )
    if m_prop:
        prop_name = m_prop.group(1).lower()
        subj_name = subject.strip()
        if not subj_name:
            m_s = re.match(r"^(?:The\s+)?([A-Z][A-Za-z0-9\s’'\-]{1,30}?)\s+(?:has|had|covered|covers|is|was)\b", sent)
            if m_s:
                subj_name = m_s.group(1).strip()
        if subj_name and subj_name.lower() not in prop_name and ans.lower() not in subj_name.lower():
            front = f"What is the {prop_name} of {subj_name}?"
            return {"front": front, "prompt": prompt, "template": "T6"}

    # Subcase 2: Count with plural noun ("72 delegates attended", "supports 30,000 jobs")
    # Answer may be "<number> <plural_noun>" (e.g. "72 delegates") or "<number>" before "<plural_noun>"
    clauses = [c.strip() for c in re.split(r"[.;]", sent) if c.strip() and ans in c]
    clause = clauses[0] if clauses else sent

    m_cnt_subj = re.match(
        rf"^(?:About\s+|Around\s+|Nearly\s+|Over\s+)?{re.escape(ans)}\s+([a-z]+s)?\s*([a-z][a-z\s’'\-–]*)$",
        clause,
        re.IGNORECASE,
    )
    if m_cnt_subj:
        extra_noun = (m_cnt_subj.group(1) or "").strip()
        rest_pred = (m_cnt_subj.group(2) or "").strip()
        ans_parts = ans.split()
        if len(ans_parts) == 2 and ans_parts[1].lower().endswith("s") and not extra_noun:
            # Wait: if `ans` is "72 delegates", putting "delegates" in "How many delegates...?" would leak part of `ans`!
            # Only use "How many <plural_noun>" when `ans` is the number alone, OR when `ans` does not contain `<plural_noun>`.
            pass
        elif len(ans_parts) == 1 and extra_noun and rest_pred:
            if subject and subject.lower() not in rest_pred.lower():
                front = f"How many {extra_noun} {rest_pred} in {subject}?"
            else:
                front = f"How many {extra_noun} {rest_pred}?"
            return {"front": front, "prompt": "Give the number", "template": "T6"}

    # Subcase 3: "<Subject> has/contains <ans> <plural_noun>" where `ans` is the number alone
    m_has_cnt = re.match(
        rf"^([A-Z][A-Za-z0-9\s’'\-–]{{1,35}}?)\s+(?:has|have|contains|consists\s+of)\s+{re.escape(ans)}\s+([a-z]+s)\.?$",
        clause,
    )
    if m_has_cnt and len(ans.split()) == 1:
        subj_p = _lower_first_if_not_proper(m_has_cnt.group(1).strip(), clause)
        plural_n = m_has_cnt.group(2).lower()
        front = f"How many {plural_n} does {subj_p} have?"
        return {"front": front, "prompt": "Give the number", "template": "T6"}

    return None


def build_t7_which_goes_with(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
    *,
    table_meta: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """T7 — WHICH-GOES-WITH (pair / table cell / symbol / capital):
      Patterns:
        - "What is the capital of <Place>?"
        - "What does the symbol <X> stand for?"
        - "What is the chemical formula of <Substance>?"
        - "What is the SI unit of <Quantity>?"
        - "Which <column_header> goes with <row_header>?" (for tables)
      Prompt: matches the column or pair type
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None

    # 1. Table cell metadata ("row_header", "col_header")
    if table_meta:
        row_h = (table_meta.get("row_header") or "").strip()
        col_h = (table_meta.get("col_header") or "").strip()
        if row_h and col_h and ans.lower() not in row_h.lower() and ans.lower() not in col_h.lower():
            col_low = col_h.lower()
            if col_low in {"river", "key river"}:
                return {
                    "front": f"On which river is {row_h} situated?",
                    "prompt": "Name the river",
                    "template": "T7",
                }
            if col_low in {"country", "country / region", "state", "region"}:
                return {
                    "front": f"Which {col_low} goes with {row_h}?",
                    "prompt": "Name the place",
                    "template": "T7",
                }
            if re.match(r"^[A-Za-z][A-Za-z\s/]{1,25}$", col_h) and not any(ch.isdigit() for ch in row_h):
                return {
                    "front": f"Which {col_low} goes with {row_h}?",
                    "prompt": table_meta.get("prompt") or f"Give the {col_low}",
                    "template": "T7",
                }

    # 2. Capital of <Place>:
    # e.g. "<City> is the capital of <Place>" or "Capital and largest city of <Place>" (under heading <City>)
    m_cap_ans_place = re.search(
        rf"\bcapital(?:\s+and\s+largest\s+city|\s+city)?\s+(?:of|in)\s+(?:the\s+)?{re.escape(ans)}\b",
        sent,
        re.IGNORECASE,
    )
    if m_cap_ans_place and subject and subject.lower() != ans.lower():
        # Here `ans` is the country/region (e.g. "Northern Ireland", "Scotland", "Wales") and `subject` is the capital city
        # Wait: "What is the capital of <Place>?" has `<City>` as the answer!
        pass

    m_cap_ans_city = re.match(
        rf"^{re.escape(ans)}\s+is\s+the\s+capital(?:\s+city)?\s+of\s+(?:the\s+)?([A-Z][A-Za-z\s]+?)\.?$",
        sent,
    )
    if m_cap_ans_city:
        place_name = m_cap_ans_city.group(1).strip()
        return {
            "front": f"What is the capital of {place_name}?",
            "prompt": "Name the capital",
            "template": "T7",
        }

    # 3. Chemical formula of <Substance>:
    # e.g. "H2O is the formula for water; CO2 is carbon dioxide." or "The chemical formula of <Substance> is <ans>."
    m_chem_f1 = re.search(
        rf"\b{re.escape(ans)}\s+(?:is\s+(?:the\s+)?(?:chemical\s+)?formula\s+(?:for|of)|represents)\s+([a-zA-Z][a-zA-Z\s]{{2,20}}?)(?:\b|\.|;|,|$)",
        sent,
    )
    if m_chem_f1 and any(ch.isdigit() for ch in ans):
        subst = m_chem_f1.group(1).strip().split()[0]
        return {
            "front": f"What is the chemical formula of {subst}?",
            "prompt": "Give the formula",
            "template": "T7",
        }

    m_chem_f2 = re.search(
        rf"\b(?:chemical\s+)?formula\s+(?:of|for)\s+([a-zA-Z][a-zA-Z\s]{{2,20}}?)\s+is\s+{re.escape(ans)}\b",
        sent,
        re.IGNORECASE,
    )
    if m_chem_f2:
        subst = m_chem_f2.group(1).strip()
        return {
            "front": f"What is the chemical formula of {subst}?",
            "prompt": "Give the formula",
            "template": "T7",
        }

    # 4. Symbol stands for:
    # e.g. "± means plus or minus; ≥ means greater than or equal to; π is the circle constant; √ denotes a square root."
    m_sym = re.search(
        rf"(?:^|;\s*)([±≥≤π√∑∆Ω]|[A-Za-z]{{1,2}})\s+(?:means|denotes|stands\s+for|is\s+the)\s+(?:a\s+|an\s+|the\s+)?{re.escape(ans)}\b",
        sent,
    )
    if m_sym:
        sym = m_sym.group(1).strip()
        if sym.lower() != ans.lower():
            return {
                "front": f"What does the symbol {sym} stand for?",
                "prompt": "Give the meaning",
                "template": "T7",
            }

    # 5. SI unit of <Quantity>:
    m_si = re.search(
        rf"\b(?:SI\s+)?unit\s+of\s+([a-zA-Z\s]{{2,25}}?)\s+is\s+(?:the\s+)?{re.escape(ans)}\b",
        sent,
        re.IGNORECASE,
    )
    if m_si:
        qty = m_si.group(1).strip()
        return {
            "front": f"What is the SI unit of {qty}?",
            "prompt": "Give the unit",
            "template": "T7",
        }

    return None


def build_t8_formula(
    sentence: str,
    answer: str,
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
    *,
    precomputed_clue: str = "",
) -> dict[str, str] | None:
    """T8 — FORMULA:
      Pattern: "Complete: <left> = ______" or "Complete: <reactants> → ______"
      Prompt: "Complete the formula" or "Complete the equation"
    """
    sent = _norm(sentence)
    ans = _norm(answer).strip(" .")
    if not sent or not ans:
        return None

    # Only use T8 for symbolic formulas or chemical equations (where '=' or '→' or '->' is present)
    if "=" not in sent and "→" not in sent and "->" not in sent:
        return None

    # Do not turn long prose sentences that happen to contain '=' into T8 unless precomputed_clue is a formula clue
    base_clue = _norm(precomputed_clue) if precomputed_clue else ""
    if base_clue and ("=" in base_clue or "→" in base_clue or "->" in base_clue) and "______" in base_clue:
        # Strip leading "Equation: " or "Formula: " before adding "Complete: "
        body = re.sub(r"^(?:Equation|Formula|Complete)\s*:\s*", "", base_clue, flags=re.IGNORECASE).strip()
        if len(body.split()) <= 12:
            is_chem = "→" in body or "->" in body
            prompt = "Complete the equation" if is_chem else "Complete the formula"
            front = f"Complete: {body}"
            return {"front": front, "prompt": prompt, "template": "T8"}

    return None


def build_t9_gap(
    gap_sentence: str,
    prompt: str = "Fill in the key fact",
) -> dict[str, str]:
    """T9 — GAP (fallback when T1–T8 return None):
      Pattern: "<Fact sentence with the answer replaced by ______>"
      Prompt: from Prompt 8's expression family
    """
    return {
        "front": _strip_markup_only(gap_sentence),
        "prompt": prompt or "Fill in the key fact",
        "template": "T9",
    }


# ---------------------------------------------------------------------------
# Question Quality Checks 1 – 6 (Prompt 9 Step 2 & Step 4)
# ---------------------------------------------------------------------------


def check_question_card(
    front: str,
    answer: str,
    source_sentence: str = "",
    subject_label: str = "",
    *,
    template: str = "",
    standard: int = 8,
    sheet_text: str = "",
) -> tuple[bool, list[str]]:
    """Run all 6 mandatory Prompt 9 checks on a candidate question front:
      Check 1 — Answer not in front (nor any content word >= 4 letters of the answer, except class words like 'River').
      Check 2 — Names its subject (contains subject label or a capitalised/defined noun from the sentence; no dangling pronouns).
      Check 3 — Length and shape (starts with capital or '______'; ends with '?' for T1–T7 or '.'/'______' for T8–T9; max words by standard; at most one '?' and at most one '______' unless bold list).
      Check 4 — Only sheet words + template words (every word in `front` is in `source_sentence`, `subject_label`, `sheet_text`, or `ALLOWED_TEMPLATE_WORDS`).
      Check 5 — Grammar sanity (no double auxiliaries 'did ... was', 'did ... founded', no empty slots, no doubled prepositions, no trailing preposition before '?').
      Check 6 — One clear answer (never a bare 'What happened in <year>?' or 'Write about <X>').
    Returns `(passed, reasons)`.
    """
    reasons: list[str] = []
    f_clean = _strip_markup_only(front)
    a_clean = _strip_markup_only(answer).strip(" ,.:;()'\"‘’“”")

    if not f_clean:
        return False, ["check_3_shape: front is empty"]
    if not a_clean:
        return False, ["check_1_giveaway: answer is empty"]

    # Determine if this is a question card (T1–T7) or a formula/gap card (T8–T9)
    has_blank = "______" in f_clean or "___" in f_clean
    is_wh_template = template in {"T1", "T2", "T3", "T4", "T5", "T6", "T7"} or (
        not template and f_clean.endswith("?") and not has_blank
    )

    # --- Check 1: Answer not in front (giveaway check) ---
    escaped_ans = re.escape(a_clean)
    if a_clean[0].isalnum():
        escaped_ans = r"\b" + escaped_ans
    if a_clean[-1].isalnum():
        escaped_ans = escaped_ans + r"\b"
    if re.search(escaped_ans, f_clean, re.IGNORECASE):
        reasons.append(f"check_1_giveaway: front contains the answer {a_clean!r}")

    # For T1–T8 (or any Wh-question), also check that NO content word (>= 4 letters) of `answer`
    # appears in `front` unless it is a shared class word (e.g. "River" in "On which river is London situated?" -> "River Thames")
    ans_content_words = [
        w
        for w in _tokenize_words(a_clean)
        if len(w) >= 4 and w not in _STOP_WORDS_CHECK and w not in CLASS_WORDS
    ]
    if is_wh_template and ans_content_words:
        front_words_set = set(_tokenize_words(f_clean))
        for aw in ans_content_words:
            if aw in front_words_set:
                reasons.append(
                    f"check_1_giveaway: question front contains content word {aw!r} from answer {a_clean!r}"
                )
                break

    # --- Check 2: Names its subject & no unresolved pronoun ---
    f_tokens = _tokenize_words(f_clean)
    # Check for dangling pronouns ("he", "she", "it", "they", "there", "this", "that") when no antecedent is in the front
    if is_wh_template:
        for pron in ("he", "she", "they", "him", "her", "them", "his", "hers", "their", "it", "its", "this", "that"):
            if pron in f_tokens:
                reasons.append(f"check_2_subject: question contains unresolved pronoun {pron!r} ({f_clean!r})")
                break
    else:
        first_clause = re.split(r"[.!?;]", f_clean, maxsplit=1)[0].strip()
        if re.match(r"^(?:He|She|It|They|His|Her|Their|Him|Them|This|That)\b", first_clause, re.IGNORECASE):
            reasons.append(f"check_2_subject: gap card starts with unresolved pronoun ({f_clean!r})")

    # Must contain the subject label or a capitalised/defined noun from the sentence (unless symbolic formula)
    is_symbolic_formula = bool(re.search(r"(=|→|->)", f_clean) and has_blank)
    if not is_symbolic_formula:
        has_cap_or_noun = bool(
            re.search(r"\b[A-Z][a-z]{2,}\b", f_clean[1:])
            or len([w for w in f_tokens if w not in QUESTION_WORDS and w not in _STOP_WORDS_CHECK]) >= 2
        )
        if not has_cap_or_noun:
            reasons.append(f"check_2_subject: front does not name a clear subject ({f_clean!r})")

    # --- Check 3: Length and shape ---
    if not (f_clean[0].isupper() or f_clean.startswith("______") or f_clean[0].isdigit()):
        reasons.append(f"check_3_shape: front must start with a capital letter or '______' ({f_clean!r})")

    if is_wh_template:
        if not f_clean.endswith("?"):
            reasons.append(f"check_3_shape: question template {template or 'Wh'} must end with '?' ({f_clean!r})")
        if f_clean.count("?") > 1:
            reasons.append(f"check_3_shape: front has more than one '?' ({f_clean!r})")
        if has_blank:
            reasons.append(f"check_3_shape: question template {template or 'Wh'} must not contain '______' ({f_clean!r})")
    else:
        if f_clean.count("?") > 1:
            reasons.append(f"check_3_shape: front has more than one '?' ({f_clean!r})")
        if not (f_clean.endswith(".") or f_clean.endswith("______") or is_symbolic_formula or f_clean.endswith((")", "'", '"', "’", "”"))):
            reasons.append(f"check_3_shape: gap/formula card must end with '.' or '______' ({f_clean!r})")

    word_list = f_clean.split()
    max_w = _max_words_for_standard(standard)
    if is_wh_template and len(word_list) > max_w:
        reasons.append(
            f"check_3_shape: question has {len(word_list)} words, exceeding max {max_w} words for standard {standard}"
        )

    # --- Check 4: Only sheet words + template words ---
    ref_pool_text = " ".join(filter(None, [source_sentence, subject_label, sheet_text]))
    if ref_pool_text.strip():
        sheet_words = set(_tokenize_words(ref_pool_text))
        # Also include base forms of any past-tense verb that appears on the sheet
        for sw in list(sheet_words):
            if sw in PAST_TO_BASE_VERBS:
                sheet_words.add(PAST_TO_BASE_VERBS[sw])
            if sw in BASE_TO_PAST_VERBS:
                sheet_words.add(BASE_TO_PAST_VERBS[sw])
            if sw.endswith("s") and len(sw) > 3:
                sheet_words.add(sw[:-1])
            else:
                sheet_words.add(sw + "s")

        for fw in f_tokens:
            if fw in sheet_words or fw in ALLOWED_TEMPLATE_WORDS:
                continue
            if any(ch.isdigit() for ch in fw):
                continue
            reasons.append(
                f"check_4_vocabulary: word {fw!r} in front is not on the sheet and not in ALLOWED_TEMPLATE_WORDS"
            )
            break

    # --- Check 5: Grammar sanity ---
    # 5a. Double auxiliaries: "did ... was/were/is/are" or "did ... <past_tense_verb>"
    if re.search(
        r"\b(?:did|does)\b[^?]*?\b(?:was|were|is|are|"
        + "|".join(re.escape(k) for k, v in PAST_TO_BASE_VERBS.items() if k != v)
        + r")\b",
        f_clean,
        re.IGNORECASE,
    ):
        reasons.append(f"check_5_grammar: double auxiliary 'did ... <past/finite verb>' in {f_clean!r}")

    # 5b. Doubly repeated prepositions ("in in", "of of", "on on", "to to", "by by", "for for", "the the")
    if re.search(r"\b(in|of|on|to|by|for|at|with|from|the|a|an|is|was|were|are)\s+\1\b", f_clean, re.IGNORECASE):
        reasons.append(f"check_5_grammar: doubled word in {f_clean!r}")

    # 5c. Trailing preposition immediately before '?' in a Wh-question (except "known as?", "stand for?", "called?")
    if is_wh_template:
        last_two = _tokenize_words(f_clean)[-2:] if len(_tokenize_words(f_clean)) >= 2 else []
        if last_two:
            last_w = last_two[-1]
            pair_str = " ".join(last_two)
            if (
                last_w in {"in", "on", "at", "of", "to", "by", "with", "from", "for", "as"}
                and pair_str not in {
                    "known as",
                    "stand for",
                    "stands for",
                    "used for",
                    "made of",
                    "consists of",
                    "composed of",
                    "situated on",
                    "situated in",
                    "located in",
                    "located at",
                }
            ):
                reasons.append(f"check_5_grammar: dangling preposition {last_w!r} before '?' in {f_clean!r}")

    # 5d. Empty slots ("What is  called?", "Who  ?")
    if re.search(r"\b(?:What\s+is\s+called|Who\s+\?|When\s+was\s+\?|Where\s+is\s+\?)", f_clean, re.IGNORECASE):
        reasons.append(f"check_5_grammar: empty template slot in {f_clean!r}")

    # --- Check 6: One clear answer (never open-ended "What happened in <year>?" or "Write about <X>") ---
    if re.match(
        r"^(?:What\s+happened\s+(?:in|on|at|during)|Write\s+about|Tell\s+about|Describe\s+|Discuss\s+)",
        f_clean,
        re.IGNORECASE,
    ):
        reasons.append(f"check_6_clear_answer: open-ended prompt without a single factual answer ({f_clean!r})")

    return len(reasons) == 0, reasons


# ---------------------------------------------------------------------------
# Template Selection & Set-Level Mixing (Prompt 9 Step 2 & Step 5)
# ---------------------------------------------------------------------------


def build_candidate_questions_for_fact(
    sentence: str,
    answer: str,
    *,
    gap_sentence: str = "",
    default_prompt: str = "Fill in the key fact",
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
    subject_label: str = "",
    sheet_text: str = "",
    standard: int = 8,
    table_meta: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Try templates in Prompt 9 priority order:
      T7, T8, T2, T1, T4, T6, T5, T3, T9
    and return all candidates that pass Checks 1–6 in that order.
    """
    subj_ctx = subject or subject_label
    builders = (
        ("T7", lambda: build_t7_which_goes_with(sentence, answer, expr_match, subj_ctx, table_meta=table_meta)),
        ("T8", lambda: build_t8_formula(sentence, answer, expr_match, subj_ctx, precomputed_clue=gap_sentence)),
        ("T2", lambda: build_t2_who_title(sentence, answer, expr_match, subj_ctx)),
        ("T1", lambda: build_t1_who(sentence, answer, expr_match, subj_ctx)),
        ("T4", lambda: build_t4_when(sentence, answer, expr_match, subj_ctx)),
        ("T6", lambda: build_t6_how_many(sentence, answer, expr_match, subj_ctx)),
        ("T5", lambda: build_t5_where(sentence, answer, expr_match, subj_ctx)),
        ("T3", lambda: build_t3_what_called(sentence, answer, expr_match, subj_ctx)),
    )

    passing: list[dict[str, str]] = []
    seen_fronts: set[str] = set()

    for t_code, fn in builders:
        cand = fn()
        if cand is None:
            continue
        ok, _ = check_question_card(
            cand["front"],
            answer,
            source_sentence=sentence,
            subject_label=subject_label or subject,
            template=t_code,
            standard=standard,
            sheet_text=sheet_text,
        )
        if ok and cand["front"] not in seen_fronts:
            seen_fronts.add(cand["front"])
            passing.append(cand)

    # Always evaluate T9 fallback last
    if gap_sentence:
        t9_cand = build_t9_gap(gap_sentence, prompt=default_prompt)
        ok_t9, _ = check_question_card(
            t9_cand["front"],
            answer,
            source_sentence=sentence,
            subject_label=subject_label or subject,
            template="T9",
            standard=standard,
            sheet_text=sheet_text,
        )
        if ok_t9 and t9_cand["front"] not in seen_fronts:
            passing.append(t9_cand)
        elif not passing:
            passing.append(t9_cand)

    return passing


def choose_question_for_fact(
    sentence: str,
    answer: str,
    *,
    gap_sentence: str = "",
    default_prompt: str = "Fill in the key fact",
    expr_match: dict[str, Any] | None = None,
    subject: str = "",
    subject_label: str = "",
    sheet_text: str = "",
    standard: int = 8,
    table_meta: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return the highest-priority passing template dict `{front, prompt, template, alternatives}`."""
    candidates = build_candidate_questions_for_fact(
        sentence,
        answer,
        gap_sentence=gap_sentence,
        default_prompt=default_prompt,
        expr_match=expr_match,
        subject=subject,
        subject_label=subject_label,
        sheet_text=sheet_text,
        standard=standard,
        table_meta=table_meta,
    )
    if not candidates:
        fallback = build_t9_gap(gap_sentence or sentence, prompt=default_prompt)
        return {
            "front": fallback["front"],
            "prompt": fallback["prompt"],
            "template": "T9",
            "alternatives": [],
        }
    best = candidates[0]
    return {
        "front": best["front"],
        "prompt": best["prompt"],
        "template": best["template"],
        "alternatives": candidates[1:],
    }


def _synthesize_wh_alternative_for_gap(card: dict[str, Any]) -> dict[str, str] | None:
    """When a T9 gap card needs to switch to a non-T9 template to satisfy the <=3-in-a-row or <=60% cap,
    try building a clean, checked T7/T3/T6/T5/T4/T1 question from the card's subject label and gap sentence.
    """
    ans = _norm(card.get("answer", "")).strip(" .")
    lbl = _norm(card.get("label") or card.get("subject_label") or card.get("subject") or "").strip(" .")
    src = _norm(card.get("source_line", ""))
    clue = _norm(card.get("clue") or card.get("front") or "")
    if not ans or not src:
        return None

    # Try each template builder with `lbl` as subject if not already in `_template_alternatives`
    for code, fn in (
        ("T3", lambda: build_t3_what_called(src, ans, subject=lbl)),
        ("T4", lambda: build_t4_when(src, ans, subject=lbl)),
        ("T5", lambda: build_t5_where(src, ans, subject=lbl)),
        ("T6", lambda: build_t6_how_many(src, ans, subject=lbl)),
        ("T7", lambda: build_t7_which_goes_with(src, ans, subject=lbl)),
        ("T1", lambda: build_t1_who(src, ans, subject=lbl)),
        ("T2", lambda: build_t2_who_title(src, ans, subject=lbl)),
    ):
        res = fn()
        if res:
            ok, _ = check_question_card(res["front"], ans, source_sentence=src, subject_label=lbl, template=code)
            if ok:
                return res

    # If the sentence has `<Term> <verb_phrase>` where `<Term>` is the answer (e.g. "______ keeps its shape and volume"),
    # and the answer is a 1–3 word noun/term, build a checked T3-style "What is ... called?" or T7-style "Which ...?"
    if clue.startswith("______ ") or (": ______ " in clue):
        after_blank = clue.split("______", 1)[1].strip().rstrip(".")
        after_words = after_blank.split()
        # e.g. "Which term describes ..." is not allowed unless "describes" is on sheet,
        # but "What <verb_phrase>?" (using only words from the sentence + "What") IS 100% sheet words + QUESTION_WORDS!
        if 2 <= len(after_words) <= 12 and after_words[0].lower() in {
            "is",
            "are",
            "was",
            "were",
            "has",
            "keeps",
            "spreads",
            "contains",
            "separates",
            "describes",
            "protects",
            "makes",
            "carries",
            "interprets",
            "alters",
            "produces",
            "forms",
            "changes",
            "uses",
            "involves",
            "means",
            "denotes",
            "represents",
        }:
            q_front = f"What {after_blank}?"
            ok, _ = check_question_card(
                q_front,
                ans,
                source_sentence=src,
                subject_label=lbl,
                template="T3",
            )
            if ok:
                return {
                    "front": q_front,
                    "prompt": card.get("prompt") or "Name the term",
                    "template": "T3",
                }

    return None


def balance_template_mix(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Step 2 & Step 5 of Prompt 9: Balance template choices across the planned set (keeping sheet order):
      1. No more than 3 cards of the same template in a row.
      2. No single template is more than 60% of the set (when alternatives exist).
    Switches extras to the next passing template (stored in `card["_template_alternatives"]` or synthesized).
    """
    n = len(cards)
    if n == 0:
        return cards

    import math

    max_per_template = max(1, math.floor(n * 0.60)) if n >= 5 else n

    # Populate any missing alternatives for T9 cards so T9 runs > 3 can also be broken cleanly
    for c in cards:
        alts = list(c.get("_template_alternatives") or [])
        if c.get("template", "T9") == "T9" and not alts:
            synth = _synthesize_wh_alternative_for_gap(c)
            if synth:
                alts.append(synth)
        c["_template_alternatives"] = alts

    # Pass 1: Enforce no more than 3 cards of the same template in a row
    for i in range(3, n):
        t_cur = cards[i].get("template", "T9")
        if (
            cards[i - 1].get("template", "T9") == t_cur
            and cards[i - 2].get("template", "T9") == t_cur
            and cards[i - 3].get("template", "T9") == t_cur
        ):
            # Try switching card `i` (or `i-1` if `i` has no alternative) to an alternative template != t_cur
            switched = False
            for idx_try in (i, i - 1, i - 2):
                alts = cards[idx_try].get("_template_alternatives") or []
                for alt in alts:
                    if alt["template"] != t_cur:
                        prev_alt = {
                            "front": cards[idx_try]["front"],
                            "prompt": cards[idx_try]["prompt"],
                            "template": cards[idx_try].get("template", "T9"),
                        }
                        cards[idx_try]["front"] = alt["front"]
                        cards[idx_try]["question"] = alt["front"]
                        cards[idx_try]["prompt"] = alt["prompt"]
                        cards[idx_try]["template"] = alt["template"]
                        cards[idx_try]["_template_alternatives"] = [a for a in alts if a is not alt] + [prev_alt]
                        switched = True
                        break
                if switched:
                    break

    # Pass 2: Enforce no single template > 60% of the set
    counts: dict[str, int] = {}
    for c in cards:
        t = c.get("template", "T9")
        counts[t] = counts.get(t, 0) + 1

    for t_over, cnt in list(counts.items()):
        if cnt <= max_per_template:
            continue
        # Walk backwards (or every second occurrence) to switch excess cards of `t_over` to an alternative that is under `max_per_template`
        for idx in range(n - 1, -1, -1):
            if counts[t_over] <= max_per_template:
                break
            c = cards[idx]
            if c.get("template", "T9") != t_over:
                continue
            alts = c.get("_template_alternatives") or []
            for alt in alts:
                alt_t = alt["template"]
                if alt_t != t_over and counts.get(alt_t, 0) + 1 <= max_per_template:
                    # Also check that switching `idx` to `alt_t` does not create 4 in a row of `alt_t`
                    window_templates = [
                        (alt_t if j == idx else cards[j].get("template", "T9"))
                        for j in range(max(0, idx - 3), min(n, idx + 4))
                    ]
                    has_run_of_4 = any(
                        len(set(window_templates[k : k + 4])) == 1
                        for k in range(max(0, len(window_templates) - 3))
                    )
                    if has_run_of_4:
                        continue
                    c["front"] = alt["front"]
                    c["question"] = alt["front"]
                    c["prompt"] = alt["prompt"]
                    c["template"] = alt_t
                    counts[t_over] -= 1
                    counts[alt_t] = counts.get(alt_t, 0) + 1
                    break

    for c in cards:
        c.pop("_template_alternatives", None)

    return cards
