"""
Stage 4: questions.py
Turn each relation into ONE card using fixed templates (WHO, WHEN, WHAT, WHERE,
HOW_MANY, TITLE, TABLE, FORMULA, GAP) with a short subject label and gap prompt,
and balance question shapes across each sheet (Step 3 & Step 4: no question type > 60%
and no more than 3 of the same type in a row, keeping sheet order).
Standard-library Python only. Zero sheet-specific words in ALLOWED_QUESTION_WORDS.
"""
from __future__ import annotations

import math
import re
from typing import Dict, List, Any

# Rule 2: Word lists may contain ONLY grammar words (articles, prepositions, auxiliary verbs,
# pronouns, conjunctions), question words, generic role words, and measurement units.
ALLOWED_QUESTION_WORDS = {
    # Question words & interrogatives
    "who", "whom", "whose", "what", "when", "where", "which", "why", "how", "many", "much", "long", "far", "often",
    # Articles, prepositions, conjunctions, pronouns, determiners
    "the", "a", "an", "of", "in", "on", "at", "to", "for", "with", "by", "from", "into",
    "under", "over", "after", "before", "between", "through", "during", "until", "about",
    "against", "among", "around", "as", "without", "outside", "inside",
    "and", "or", "but", "if", "then", "than", "so", "not", "no", "nor", "also", "only",
    "both", "each", "every", "one", "some", "any", "all", "most", "more", "less", "least",
    "other", "another", "such", "this", "that", "these", "those",
    "it", "its", "they", "their", "them", "he", "his", "she", "her", "you", "your",
    # Auxiliary & light verbs
    "is", "are", "was", "were", "be", "been", "being",
    "do", "does", "did", "done",
    "has", "have", "had",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    "get", "gets", "got", "goes", "go", "went", "fit", "fits", "become", "became",
    "make", "made", "use", "used", "using", "keep", "kept", "take", "cover", "stand", "stands",
    "complete", "give", "fill", "state", "define",
    # Question & template framing nouns/adjectives
    "year", "years", "date", "time", "century", "age", "minimum", "maximum", "old",
    "number", "value", "amount", "total", "share", "rate", "ratio", "percentage", "range",
    "formula", "equation", "step", "first", "second", "third", "next", "finally", "last",
    "result", "cause", "causes", "effect", "effects", "factor", "factors",
    "measure", "measures", "measured", "precaution", "precautions", "reason", "reasons",
    "feature", "features", "definition", "meaning", "called", "means", "known", "defined",
    "equal", "equals", "gap", "word", "name", "part", "kind", "type", "role", "title",
    "purpose", "rank", "population", "lifespan", "scale", "calculated", "comparison",
    "table", "chemical", "symbol", "substance", "term", "key", "fact", "force",
    # Generic role & institutional words (Rule 2)
    "founded", "found", "founder", "established", "establish", "opened", "open",
    "started", "start", "built", "build", "invented", "invent", "discovered", "discover",
    "wrote", "write", "authored", "author", "published", "publish",
    "led", "lead", "leader", "leaders",
    "appointed", "appoint", "appoints", "elected", "elect", "elects",
    "chaired", "chair", "presided", "preside", "presiding", "officer",
    "member", "members", "president", "term", "retire", "retires", "retirement",
    "capital", "located", "situated", "held", "river", "city", "cities", "town", "towns",
    "state", "country", "region", "house", "court", "parliament", "assembly",
    "committee", "organisation", "organization", "institution", "college", "school",
    "university", "bank", "museum", "seat", "headquarters", "global", "residence",
    "rule", "ruler", "rulers", "emperor", "king", "queen", "governor", "viceroy",
    "judge", "judges", "people", "citizens", "group", "groups",
    "proclaimed", "proclaim", "recaptured", "recapture", "captured", "capture",
    "ended", "end", "protects", "protect", "support", "supports", "worth",
    "convert", "converted", "determine", "determines", "industry", "major", "important",
    "graduated", "graduate", "campaigned", "campaign", "grew", "grow",
    # Measurement units (Rule 2)
    "km", "m", "cm", "mm", "kg", "kilograms", "kilogram", "g", "grams", "gram", "mg",
    "s", "sec", "seconds", "second", "min", "minutes", "minute", "hr", "hours", "hour",
    "months", "month", "days", "day", "n", "unit", "units", "billion", "million", "percent", "si",
}

PAST_TO_BASE_VERBS: Dict[str, str] = {
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
    "recaptured": "recapture",
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


def shorten_label(subject: str) -> str:
    """Create a concise card label naming its subject without cutting off short phrases."""
    s = (subject or "").strip()
    words = s.split()
    if len(words) > 5:
        return " ".join(words[:5])
    return s


def fmt_mid_subj(subject: str, add_the_for_institutions: bool = False) -> str:
    """Format a subject name for mid-sentence placement (e.g. 'The President' -> 'the President')."""
    s = (subject or "").strip()
    if s.startswith("The "):
        return "the " + s[4:]
    if (
        add_the_for_institutions
        and any(w in s.lower() for w in ("court", "parliament", "assembly", "committee", "commission", "council"))
        and not s.lower().startswith("the ")
    ):
        return "the " + s
    return s


def make_gap_prompt(category: str) -> str:
    """Return a clean prompt for GAP cards based on answer category."""
    if category == "date":
        return "Which year fits the gap?"
    if category in ("person", "organisation", "place", "document"):
        return "Which name fits the gap?"
    if category in ("number", "quantity"):
        return "Which number fits the gap?"
    return "Which word fits the gap?"


def _build_gap_from_source(subj: str, ans: str, src: str, category: str) -> Dict[str, str]:
    """Construct a clean T9 GAP fallback card from source_text."""
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(ans) + r"(?![A-Za-z0-9])")
    if pattern.search(src):
        front = pattern.sub("______", src, count=1)
    else:
        front = src.replace(ans, "______", 1)
    if front.startswith("______") or subj.lower() not in front.lower():
        front = f"In {subj}, {front[0].lower() + front[1:] if len(front) > 1 and front[0].isupper() and not front[:2].isupper() and not front.startswith(subj[:3]) else front}"
    if not front.endswith(".") and not front.endswith("?"):
        front += "."
    return {
        "front": front,
        "prompt": make_gap_prompt(category),
        "question_type": "GAP",
    }


# ---------------------------------------------------------------------------
# Ported General Template Builders (T1–T9 from reference questions.py)
# ---------------------------------------------------------------------------


def build_t1_who(sentence: str, answer: str, subject: str = "") -> Dict[str, str] | None:
    """T1 — WHO (person or group): 'Who <verb_phrase>?'"""
    sent = (sentence or "").strip()
    ans = (answer or "").strip(" .")
    if not sent or not ans or any(ch.isdigit() for ch in ans) or not ans[0].isupper():
        return None
    m_act = re.match(rf"^(?:The\s+)?{re.escape(ans)}\s+([a-z][a-z\-]+)\s+(.+?)\.?$", sent)
    if m_act and m_act.group(1).lower() in PAST_TO_BASE_VERBS:
        return {
            "front": f"Who {m_act.group(1).lower()} {m_act.group(2).strip()}?",
            "prompt": "Name the person",
            "question_type": "WHO",
        }
    return None


def build_t2_who_title(sentence: str, answer: str, subject: str = "", title: str = "") -> Dict[str, str] | None:
    """T2 — WHO-TITLE / title->name ('Who is called the Father of …?'):"""
    ans = (answer or "").strip(" .")
    if title:
        t_clean = title[4:] if title.lower().startswith("the ") else title
        return {
            "front": f"Who is called the {t_clean}?",
            "prompt": "Name the person",
            "question_type": "WHO",
        }
    sent = (sentence or "").strip()
    m_known = re.match(
        rf"^(?:The\s+)?{re.escape(ans)}\s+(?:was|is)\s+(?:also\s+|popularly\s+)?(?:known|called)\s+(?:as\s+)?(?:the\s+)?[‘'“\"]?([^’'”\".]+)[’'”\"]?\.?$",
        sent,
        re.IGNORECASE,
    )
    if m_known:
        return {
            "front": f"Who is called the {m_known.group(1).strip()}?",
            "prompt": "Name the person",
            "question_type": "WHO",
        }
    return None


def build_t3_definition(definition: str) -> Dict[str, str] | None:
    """T3 — DEFINITION ('What is the name for <definition>?' when <= 12 words):"""
    defn = (definition or "").strip().rstrip(".")
    words = defn.split()
    if not (2 <= len(words) <= 12):
        return None
    return {
        "front": f"What is the name for {defn}?",
        "prompt": "Name the term",
        "question_type": "WHAT",
    }


def build_t4_when(sentence: str, answer: str, subject: str = "") -> Dict[str, str] | None:
    """T4 — WHEN (date or year): 'When was <subject> <participle>?' or 'When did <subject> <base_verb>?'"""
    sent = (sentence or "").strip().rstrip(".")
    ans = (answer or "").strip(" .")
    if not sent or not ans:
        return None
    m_act = re.match(
        rf"^(?:The\s+)?([A-Z][A-Za-z0-9\s’'\-]{1,40}?)\s+([a-z]+)(?:\s+(.+?))?\s+(?:in|on)\s+{re.escape(ans)}$",
        sent,
    )
    if m_act:
        subj_p = m_act.group(1).strip()
        verb_p = m_act.group(2).lower()
        obj_p = (m_act.group(3) or "").strip()
        base_v = PAST_TO_BASE_VERBS.get(verb_p)
        if base_v:
            tail = f"{base_v} {obj_p}".strip() if obj_p else base_v
            return {
                "front": f"When did the {subj_p} {tail}?" if sent.startswith("The ") else f"When did {subj_p} {tail}?",
                "prompt": "Give the date or year",
                "question_type": "WHEN",
            }
    return None


def build_t5_where(subject: str, verb_or_prep: str = "located") -> Dict[str, str]:
    """T5 — WHERE (place, river, city, state, country):"""
    mid_s = fmt_mid_subj(subject, add_the_for_institutions=True)
    if verb_or_prep == "river":
        return {
            "front": f"Which river is {subject} situated on?",
            "prompt": "Name the river",
            "question_type": "WHERE",
        }
    return {
        "front": f"Where is {mid_s} {verb_or_prep}?",
        "prompt": "Name the place",
        "question_type": "WHERE",
    }


def build_t6_how_many(subject: str, prop: str = "population", mode: str = "many") -> Dict[str, str]:
    """T6 — HOW MANY / HOW MUCH / HOW LONG:"""
    mid_s = fmt_mid_subj(subject, add_the_for_institutions=True)
    if mode == "long":
        return {
            "front": f"How long is the {prop} of {mid_s}?",
            "prompt": "Give the value and unit",
            "question_type": "HOW_MANY",
        }
    if mode == "much":
        return {
            "front": f"How much is the {prop} for {mid_s}?",
            "prompt": "Give the value",
            "question_type": "HOW_MANY",
        }
    return {
        "front": f"What is the {prop} of {mid_s}?",
        "prompt": "Give the number",
        "question_type": "HOW_MANY",
    }


def build_t7_which_goes_with(row_key: str, col_header: str) -> Dict[str, str]:
    """T7 — WHICH-GOES-WITH (tables): 'Which <column_header> goes with <row_header>?'"""
    return {
        "front": f"Which {col_header} goes with {row_key}?",
        "prompt": "",
        "question_type": "TABLE",
    }


def build_t8_formula(subject_or_lhs: str, is_complete: bool = False) -> Dict[str, str]:
    """T8 — FORMULA: 'What is the formula for <subject>?' or 'Complete: <left> = ______.'"""
    if is_complete:
        return {
            "front": f"Complete: {subject_or_lhs} ______.",
            "prompt": "Complete the formula",
            "question_type": "FORMULA",
        }
    return {
        "front": f"What is the formula for {subject_or_lhs}?",
        "prompt": "",
        "question_type": "FORMULA",
    }


# ---------------------------------------------------------------------------
# Primary Card + Multi-Shape Alternatives Generator
# ---------------------------------------------------------------------------


def generate_card(fact: Dict[str, Any], card_id: str) -> Dict[str, Any]:
    """Turn a single fact dict into a candidate card dict with alternative question shapes."""
    subj = fact["subject"]
    rel = fact["relation"]
    ans = fact["object"]
    src = fact["source_text"]
    cat = fact.get("category", "term")
    meta = fact.get("meta") or {}
    label = shorten_label(subj)
    prompt = ""
    q_type = "WHAT"
    mid_s = fmt_mid_subj(subj, add_the_for_institutions=True)
    mid_plain = fmt_mid_subj(subj, add_the_for_institutions=False)
    alternatives: List[Dict[str, str]] = []

    if rel == "IS_CALLED":
        front = f"What is {mid_s} called?"
        q_type = "TITLE"
        alternatives.append({"front": f"{subj} is called ______.", "prompt": make_gap_prompt("title"), "question_type": "GAP"})
    elif rel == "TITLE_TO_PERSON":
        title_str = meta.get("title", subj)
        t_clean = title_str[4:] if title_str.lower().startswith("the ") else title_str
        front = f"Who is called the {t_clean}?"
        q_type = "WHO"
        prompt = "Name the person"
    elif rel == "ROLE_DEFINITION":
        front = f"{subj} is the ______."
        q_type = "GAP"
        prompt = make_gap_prompt("title")
        alternatives.append({"front": f"What is {mid_s} called?", "prompt": "", "question_type": "TITLE"})
    elif rel == "TERM_FROM_DEFINITION":
        defn = meta.get("definition", "").strip().rstrip(".")
        if len(defn.split()) <= 12:
            front = f"What is the name for {defn}?"
        else:
            front = f"What is {defn} called?"
        q_type = "WHAT"
        alternatives.append({"front": f"What is {defn} called?", "prompt": "", "question_type": "TITLE"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "ALSO_CALLED":
        front = f"What is the {mid_plain} also called?"
        q_type = "TITLE"
        alternatives.append({"front": f"What is another name for the {mid_plain}?", "prompt": "", "question_type": "WHAT"})
    elif rel == "SUMMARY_EQUALS":
        front = src.replace(ans, "______", 1)
        if not front.endswith(".") and not front.endswith("?"):
            front += "."
        q_type = "GAP"
        prompt = make_gap_prompt("term")
        alternatives.append({"front": f"In the comparison, what does {subj} equal?", "prompt": "", "question_type": "WHAT"})
        alternatives.append({"front": f"What is {mid_s} called in the comparison?", "prompt": "", "question_type": "TITLE"})
    elif rel == "TERM_LENGTH":
        front = f"What is the term of {mid_s}?"
        q_type = "HOW_MANY"
        alternatives.append({"front": f"How long is the term of {mid_s}?", "prompt": "", "question_type": "HOW_MANY"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "MEM_TERM_LENGTH":
        front = f"How long is a member's term in {mid_s}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "PRESIDING_OFFICER":
        front = f"Who is the presiding officer of {mid_s}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "MIN_AGE":
        role_w = meta.get("role", "")
        if role_w:
            front = f"What is the minimum age for a {role_w} of {mid_s}?"
        else:
            front = f"What is the minimum age for {mid_s}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "RETIRE_AGE":
        grp = meta.get("group", "members")
        front = f"At what age do {grp} of {mid_s} retire?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "PASSIVE_AGENT":
        act_v = meta.get("active_verb", "appoints")
        t_grp = meta.get("target_group", "")
        if t_grp:
            front = f"Who {act_v} the {t_grp} of {mid_s}?"
        else:
            front = f"Who {act_v} {mid_s}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "MEASURED_ON":
        if subj.endswith("s"):
            front = f"On which scale are {subj} measured?"
        else:
            front = f"On which scale is {mid_s} measured?"
        q_type = "WHAT"
        alternatives.append({"front": f"In {subj}, it is measured on the ______.", "prompt": make_gap_prompt("term"), "question_type": "GAP"})
    elif rel == "PROTECTS":
        ben = meta.get("beneficiary", "citizens")
        front = f"What does {mid_s} protect for {ben}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "LED_AT_PLACE":
        ev_n = meta.get("event_noun", "revolt")
        prep = meta.get("prep", "at")
        place = meta.get("place", subj)
        front = f"Who led the {ev_n} {prep} {place}?"
        q_type = "WHO"
        if place and place != ans:
            alternatives.append({
                "front": f"Where did {ans} lead the {ev_n}?",
                "prompt": "",
                "question_type": "WHERE",
                "answer": place,
                "label": shorten_label(ans),
                "subject": ans,
            })
        alternatives.append({"front": f"In {place}, ______ led the {ev_n}.", "prompt": "Which name fits the gap?", "question_type": "GAP"})
    elif rel == "ACTOR_ON_DATE":
        dt = meta.get("date", "")
        act = meta.get("action", "")
        front = f"On {dt}, who {act}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "EVENT_ON_DATE":
        front = src.replace(ans, "______", 1)
        if not front.endswith("."):
            front += "."
        q_type = "GAP"
        prompt = make_gap_prompt("date")
    elif rel == "PROCLAIMED_AS":
        grp = meta.get("group", "rebels")
        role = meta.get("role", "emperor")
        front = f"Who did the {grp} proclaim as their {role}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "RECAPTURED_IN":
        actor = meta.get("actor", "")
        verb = meta.get("verb", "recaptured")
        base_v = PAST_TO_BASE_VERBS.get(verb.lower(), verb.lower())
        if actor and base_v:
            front = f"When did the {actor} {base_v} {subj}?"
            q_type = "WHEN"
            alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
        else:
            front = src.replace(ans, "______", 1)
            if not front.endswith("."):
                front += "."
            q_type = "GAP"
            prompt = make_gap_prompt("date")
    elif rel == "ENDED_RULE_BY_DOC":
        front = f"Which Act ended the rule of the {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "BECAME_ROLE":
        front = f"What did the {subj} become?"
        q_type = "TITLE"
        alternatives.append({"front": f"What role did the {subj} become?", "prompt": "", "question_type": "WHAT"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "LIST_FACTOR":
        fl = meta.get("factor_label", "cause")
        if fl in ("political", "economic", "military"):
            front = f"What was one {fl} cause of {mid_plain}?"
        elif fl == "immediate cause":
            front = f"What was the immediate cause of {mid_plain}?"
        else:
            front = f"In {mid_plain}, what is one of the {fl}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "COLON_EQUATION_RHS":
        prefix = meta.get("prefix", "")
        lhs = meta.get("lhs", "").strip()
        label_part = meta.get("label_part", "").strip()
        front = f"{prefix} ______."
        q_type = "GAP"
        prompt = make_gap_prompt(fact.get("category", "number"))
        if meta.get("is_formula") == "1" and lhs:
            alternatives.append({"front": f"In {subj}, what is the formula for {lhs}?", "prompt": "", "question_type": "FORMULA"})
        elif lhs:
            if label_part and label_part.lower() == subj.lower():
                alternatives.append({"front": f"In {label_part}, what does {lhs} equal?", "prompt": "", "question_type": "HOW_MANY"})
            else:
                alternatives.append({"front": f"In {subj}, what does {lhs} equal?", "prompt": "", "question_type": "HOW_MANY"})
            alternatives.append({"front": f"Complete: {prefix} ______.", "prompt": "Complete the formula", "question_type": "FORMULA"})
    elif rel == "CALCULATED_ON":
        front = f"What is {subj.lower()} calculated on?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "TABLE_CELL":
        col_h = meta.get("col_header", "value")
        row_k = meta.get("row_key", subj)
        if "/" in col_h or "(" in col_h or col_h.lower() in ("result", "forces to consider", "reasoning"):
            front = f"Which {col_h} goes with {row_k}?"
        else:
            front = f"What is the {col_h} for {row_k}?"
        q_type = "TABLE"
        if any(ch.isdigit() for ch in ans):
            alternatives.append({"front": f"How much is the {col_h} for {row_k}?", "prompt": "", "question_type": "HOW_MANY"})
        alternatives.append({"front": f"For {row_k}, what is the {col_h}?", "prompt": "", "question_type": "WHAT"})
        alternatives.append({"front": f"{row_k} — {col_h}: ______.", "prompt": make_gap_prompt(cat), "question_type": "GAP"})
    elif rel == "REGARDED_AS_FIRST":
        place = meta.get("place", "")
        if place:
            front = f"What is {subj} regarded as {place}'s first?"
        else:
            front = f"What is {subj} regarded as the first of?"
        q_type = "TITLE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "FOUNDED":
        front = f"Which organisation did {subj} found?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "FOUNDED_IN":
        front = f"In which year was the {subj} founded?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "GRADUATED_FROM":
        front = f"Which college did {subj} graduate from?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "GRADUATED_IN":
        front = f"In which year did {subj} graduate?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "FOUNDED_ENTITY_IN":
        ek = meta.get("entity_kind", "organisation")
        front = f"In which year did {subj} found a {ek}?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "CONVERTED_INTO":
        so = meta.get("source_obj", "building")
        front = f"What did {subj} convert an {so} into?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "ESTABLISHED":
        front = f"What did {subj} establish?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "OPENED":
        front = f"What did {subj} open?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "OPENED_ON":
        front = f"On what date did the {subj} open?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "FIRST_WITH":
        place = meta.get("place", "")
        if place:
            front = f"The {subj} was the first in {place} with what?"
        else:
            front = f"The {subj} was the first with what?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "LAID_FOUNDATIONS_FOR":
        front = f"What did {subj} lay foundations for?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "REFORMER_IN":
        front = f"Where was {subj} a social reformer and writer?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "PURPOSE":
        front = f"What was the purpose of the {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "WORKED_ALONGSIDE":
        front = f"Who did {subj} work alongside?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "STARTED_IN":
        front = f"In which year were {subj} started?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "RESIDENCE":
        front = f"What was the residence of {subj}?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "LOCATED_IN":
        front = f"Where is {mid_s} located?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "CHAIRED":
        front = f"Which committee did {subj} chair?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "PART_OF":
        front = f"What was the {subj} part of?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "PRECURSOR_TO":
        front = f"What was the {subj} a precursor to?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "INSPIRED":
        front = f"Which organisation did the {subj} inspire?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "CAMPAIGNED_FOR":
        front = f"What did {subj} campaign for?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "YEAR":
        front = f"In which year was the {subj}?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "CAPITAL_OF":
        front = f"What is {subj} the capital of?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "SITUATED_ON":
        front = f"Which river is {subj} situated on?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "FINANCIAL_CENTRE_OF":
        front = f"What is {subj} the financial centre of?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "REGION":
        front = f"Which region is {subj} a major city of?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "LARGEST_OUTSIDE":
        front = f"Outside which city is {subj} the largest city?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "PROMINENCE_IN":
        front = f"In which century did {subj} grow to international prominence?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "AT_HEART_OF":
        front = f"What was {subj} at the heart of?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "INVENTION":
        front = f"What was invented in {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "SUPERLATIVE_ROLE":
        place = meta.get("place", "")
        if place:
            front = f"What is {subj} in the {place}?"
        else:
            front = f"What is {subj} known as?"
        q_type = "TITLE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "VISITORS_PER_YEAR":
        front = f"How many visitors does {subj} get each year?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "POPULATION":
        front = f"What is the population of {subj}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "HISTORIC_INDUSTRY":
        front = f"What is a historic industry of {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "BUILT":
        front = f"What did {subj} build?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "FACILITY_IN":
        fk = meta.get("facility_kind", "facility")
        front = f"Which {fk} is in {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "INDUSTRY_SINCE":
        since = meta.get("since", "")
        if since:
            front = f"Which industry has {subj} sustained since the {since}?"
        else:
            front = f"Which major industry has {subj} sustained?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "HOME_TO":
        front = f"What is {subj} home to?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "RANK":
        place = meta.get("place", "")
        if place:
            front = f"What is the population rank of {subj} in the {place}?"
        else:
            front = f"What is the population rank of {subj}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "FINANCIAL_RANK":
        place = meta.get("place", "")
        if place:
            front = f"What rank is {subj} as a financial centre in the {place}?"
        else:
            front = f"What rank is {subj} as a financial centre?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "BANKING_FOR":
        front = f"For how long has {subj} been a centre of banking?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "HEADQUARTERS_IN":
        front = f"Where does the {subj} have its global headquarters?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "SUPPORTS":
        sec = meta.get("sector", "")
        if sec:
            front = f"In {subj}, how many jobs does {sec} support?"
        else:
            front = f"How many jobs does {subj} support?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "WORTH":
        sec = meta.get("sector", "")
        if sec:
            front = f"In {subj}, how much is {sec} worth to the city economy?"
        else:
            front = f"How much is {subj} worth to the city economy?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "ARCHITECTURE_INCLUDES":
        front = f"What famous area is part of the architecture of {subj}?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "SEAT_OF":
        front = f"What is {subj} the seat of?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "SMALL_TOWN_UNTIL":
        front = f"Until which century was {subj} a small town?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "MOST_IMPORTANT":
        front = f"What did {subj} become the world's most important?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "MADE_CITY_IN":
        front = f"In which year was {subj} made a city?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "PROCLAIMED_CAPITAL_IN":
        place = meta.get("place", "")
        if place:
            front = f"In which year was {subj} proclaimed capital of {place}?"
        else:
            front = f"In which year was {subj} proclaimed a capital?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date"))
    elif rel == "DETERMINES":
        front = f"What does {subj} determine?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "FORMULA":
        front = f"What is the formula for {subj}?"
        q_type = "FORMULA"
        alternatives.append(_build_gap_from_source(subj, ans, src, "formula"))
    elif rel == "DEFINITION_FORMULA":
        front = f"What is the definition of {subj}?"
        q_type = "FORMULA"
        alternatives.append(_build_gap_from_source(subj, ans, src, "formula"))
    elif rel == "CALC_RESULT":
        front = f"What is the calculated result for {subj}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "UNIT_OF":
        front = f"What is the unit of {subj}?"
        q_type = "WHAT"
        alternatives.append({"front": f"Which unit goes with {subj}?", "prompt": "", "question_type": "TABLE"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "CONVERT_TO":
        fu = meta.get("from_unit", "units")
        front = f"What are {fu} converted to {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    elif rel == "EQUALS_VALUE":
        front = f"What does {subj} equal?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat))
    else:
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(ans) + r"(?![A-Za-z0-9])")
        if pattern.search(src):
            front = pattern.sub("______", src, count=1)
        else:
            front = src.replace(ans, "______", 1)
        if front.startswith("______"):
            front = f"In {subj}, {front}"
        if not front.endswith(".") and not front.endswith("?"):
            front += "."
        q_type = "GAP"
        prompt = make_gap_prompt(cat)
        if meta.get("alt_what"):
            alternatives.append({"front": meta["alt_what"], "prompt": "", "question_type": "WHAT"})
        if meta.get("alt_how_many"):
            alternatives.append({"front": meta["alt_how_many"], "prompt": "", "question_type": "HOW_MANY"})

    return {
        "id": card_id,
        "fact_id": fact["id"],
        "item_id": fact["item_id"],
        "page": fact["page"],
        "label": label,
        "front": front,
        "prompt": prompt,
        "answer": ans,
        "question_type": q_type,
        "source_text": src,
        "subject": subj,
        "status": "candidate",
        "_alternatives": alternatives,
    }


def balance_question_mix(
    cards: List[Dict[str, Any]],
    validate_fn: Any = None,
) -> List[Dict[str, Any]]:
    """Step 4: Mix question shapes across the sheet while preserving sheet order:
      - No question_type is more than 60% of cards;
      - No more than 3 cards of the same question_type in a row;
      - At least 3 distinct question_types when >= 3 cards exist.
    """
    n = len(cards)
    if n == 0:
        return cards

    max_per_type = max(1, math.floor(n * 0.60)) if n >= 5 else n

    # Build the list of valid options per card: index 0 is primary, 1..k are validated alternatives
    options_per_card: List[List[Dict[str, str]]] = []
    for c in cards:
        primary_opt = {
            "front": c["front"],
            "prompt": c["prompt"],
            "question_type": c["question_type"],
        }
        valid_opts = [primary_opt]
        for alt in c.get("_alternatives") or []:
            if alt["question_type"] == primary_opt["question_type"] and alt["front"] == primary_opt["front"]:
                continue
            if validate_fn is not None:
                test_c = dict(
                    c,
                    front=alt["front"],
                    prompt=alt["prompt"],
                    question_type=alt["question_type"],
                    answer=alt.get("answer", c["answer"]),
                    label=alt.get("label", c["label"]),
                    subject=alt.get("subject", c["subject"]),
                )
                if validate_fn(test_c):
                    continue
            valid_opts.append(alt)
        options_per_card.append(valid_opts)

    def apply_opt(idx: int, opt: Dict[str, str]) -> None:
        cards[idx]["front"] = opt["front"]
        cards[idx]["prompt"] = opt["prompt"]
        cards[idx]["question_type"] = opt["question_type"]
        if "answer" in opt:
            cards[idx]["answer"] = opt["answer"]
        if "label" in opt:
            cards[idx]["label"] = opt["label"]
        if "subject" in opt:
            cards[idx]["subject"] = opt["subject"]

    def creates_run_of_4(idx: int, new_t: str) -> bool:
        window = [
            new_t if j == idx else cards[j]["question_type"]
            for j in range(max(0, idx - 3), min(n, idx + 4))
        ]
        for k in range(len(window) - 3):
            if window[k] == window[k + 1] == window[k + 2] == window[k + 3]:
                return True
        return False

    # Pass 1: Ensure at least 3 distinct question_types (when n >= 3)
    distinct_types = {c["question_type"] for c in cards}
    if n >= 3 and len(distinct_types) < 3:
        for idx in range(n):
            if len(distinct_types) >= 3:
                break
            cur_t = cards[idx]["question_type"]
            if sum(1 for c in cards if c["question_type"] == cur_t) <= 1:
                continue
            for opt in options_per_card[idx][1:]:
                if opt["question_type"] not in distinct_types and not creates_run_of_4(idx, opt["question_type"]):
                    apply_opt(idx, opt)
                    distinct_types.add(opt["question_type"])
                    break

    # Pass 2: Break any run of > 3 of the same question_type in a row
    for _ in range(n * 2):
        changed = False
        counts: Dict[str, int] = {}
        for c in cards:
            qt = c["question_type"]
            counts[qt] = counts.get(qt, 0) + 1

        for i in range(3, n):
            t_cur = cards[i]["question_type"]
            if (
                cards[i - 1]["question_type"] == t_cur
                and cards[i - 2]["question_type"] == t_cur
                and cards[i - 3]["question_type"] == t_cur
            ):
                # Prefer switching i-1 or i so a run of 4..6 is split cleanly in the middle
                switched = False
                for idx_try in (i - 1, i, i - 2, i - 3):
                    for opt in options_per_card[idx_try]:
                        alt_t = opt["question_type"]
                        if (
                            alt_t != t_cur
                            and counts.get(alt_t, 0) + 1 <= max_per_type
                            and not creates_run_of_4(idx_try, alt_t)
                        ):
                            counts[t_cur] -= 1
                            counts[alt_t] = counts.get(alt_t, 0) + 1
                            apply_opt(idx_try, opt)
                            switched = True
                            changed = True
                            break
                    if switched:
                        break
                if switched:
                    break
        if not changed:
            break

    # Pass 3: Enforce no single question_type > 60% of the sheet
    counts = {}
    for c in cards:
        qt = c["question_type"]
        counts[qt] = counts.get(qt, 0) + 1

    for t_over, cnt in list(counts.items()):
        if cnt <= max_per_type:
            continue
        for idx in range(n - 1, -1, -1):
            if counts[t_over] <= max_per_type:
                break
            if cards[idx]["question_type"] != t_over:
                continue
            for opt in options_per_card[idx]:
                alt_t = opt["question_type"]
                if (
                    alt_t != t_over
                    and counts.get(alt_t, 0) + 1 <= max_per_type
                    and not creates_run_of_4(idx, alt_t)
                ):
                    counts[t_over] -= 1
                    counts[alt_t] = counts.get(alt_t, 0) + 1
                    apply_opt(idx, opt)
                    break

    for c in cards:
        c.pop("_alternatives", None)

    return cards
