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
    "founded", "found", "founder", "founding", "established", "establish", "opened", "open",
    "started", "start", "built", "build", "invented", "invent", "discovered", "discover",
    "wrote", "write", "authored", "author", "published", "publish",
    "led", "lead", "leader", "leaders",
    "appointed", "appoint", "appoints", "elected", "elect", "elects",
    "chaired", "chair", "presided", "preside", "presiding", "officer",
    "member", "members", "president", "term", "retire", "retires", "retirement",
    "capital", "located", "situated", "held", "river", "city", "cities", "town", "towns",
    "place", "places", "society",
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


def is_chemical_formula_or_symbol(ans: str, source_text: str = "") -> bool:
    """Return True if `ans` is a chemical formula (e.g. CO2, H2O, O2, C6H12O6, NaCl, H₂SO₄) or chemical symbol."""
    a = (ans or "").strip(" .,;:")
    if not a:
        return False
    # Multi-atom formula with digits/subscripts: e.g. CO2, H2O, O2, C6H12O6, H₂O, CaCO₃, 6CO2
    if re.fullmatch(
        r"\d*(?:[A-Z][a-z]?(?:[₀-₉]+|\d+)*)*[A-Z][a-z]?(?:[₀-₉]+|\d+)(?:[A-Z][a-z]?(?:[₀-₉]+|\d+)*)*(?:\((?:aq|s|l|g)\))?",
        a,
    ):
        return True
    # Multi-element compound formula without digits (two or more Element symbols glued together, e.g. NaCl, NaOH, HCl, CaO, MgO, FeS, AgBr)
    if re.fullmatch(r"(?:[A-Z][a-z]?){2,4}(?:\((?:aq|s|l|g)\))?", a) and any(ch.islower() for ch in a):
        # Ensure at least two uppercase letters and no spaces
        if sum(1 for ch in a if ch.isupper()) >= 2:
            return True
    # Single element symbol (1–2 letters like O, H, C, Na, Fe, Au, Ag, Cl) when source_text mentions symbol/formula/element
    if re.fullmatch(r"[A-Z][a-z]?", a) and source_text and re.search(r"\b(?:symbol|formula|element|chemical|gas|atom|ion)\b", source_text, re.IGNORECASE):
        return True
    return False


def is_chemical_substance_or_formula(ans: str, source_text: str = "") -> bool:
    """Round 5 Fix 3: Return True if `ans` is or contains a chemical formula or a substance name
    with its formula (e.g. 'carbon dioxide (CO2)', 'glucose (C6H12O6)', 'CO2', 'H2O', 'O2', 'C6H12O6', 'NaCl').
    Excludes math/physics equations with '=' or reaction arrows '→'.
    """
    from .expressions import FAMILY_D

    a = (ans or "").strip(" .,;:")
    if not a or "=" in a or "→" in a or "->" in a or "⇌" in a:
        return False
    if is_chemical_formula_or_symbol(a, source_text):
        return True
    # Substance name with formula in parentheses, e.g. 'carbon dioxide (CO2)', 'glucose (C6H12O6)', 'sodium chloride (NaCl)'
    for m_paren in re.finditer(r"\(\s*([0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s*\)", a):
        if is_chemical_formula_or_symbol(m_paren.group(1), a):
            return True
    # Formula followed by substance name in parentheses, e.g. 'CO2 (carbon dioxide)'
    m_lead = re.match(r"^([0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]+)\s*\([A-Za-z\s]+\)$", a)
    if m_lead and is_chemical_formula_or_symbol(m_lead.group(1), a):
        return True
    # Any chemical formula token inside the answer phrase (e.g. '6 molecules of CO2')
    for tok in re.findall(r"[0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]+", a):
        if is_chemical_formula_or_symbol(tok, source_text):
            return True
    if any(m["type"] in ("chemical_formula", "element_symbol", "state_symbol") for m in FAMILY_D.find(a)):
        return True
    return False


def _is_place_in_list_context(ans: str, src: str) -> bool:
    """Fix 4: Places inside lists ('Main centres: ______, Ahmedabad and Coimbatore',
    'Main states: ______ and Maharashtra', 'in Mumbai, Pune and Nagpur'):
    if the label or other list items indicate places, the answer is a place -> 'Which place fits the gap?'.
    """
    if not ans or not src or not ans[0].isupper() or any(ch.isdigit() for ch in ans):
        return False

    place_list_cue_words = (
        "centres", "centers", "states", "cities", "towns", "ports",
        "regions", "districts", "countries", "provinces", "capitals",
        "areas", "places", "locations", "rivers",
    )

    # 1. Explicit place list header or cue before ':' or 'such as' / 'like' / 'including' / 'in' / 'across'
    m_colon = re.match(r"^([^:]{1,45}):\s*(.+)$", src)
    if m_colon:
        hdr_low = m_colon.group(1).lower()
        body = m_colon.group(2).strip().rstrip(".")
        if any(w in hdr_low for w in place_list_cue_words) and ans in body:
            return True
        items = [x.strip() for x in re.split(r",\s*(?:and\s+)?|\s+and\s+", body) if x.strip()]
        if len(items) >= 2 and ans in items and all(it[0].isupper() and len(it.split()) <= 3 for it in items):
            if any(w in hdr_low for w in ("main", "major", "important", "leading", "key", "principal", "chief", "found", "grown", "produced", "distributed", "concentrated")):
                return True

    # 2. Coordinated list in prose: e.g. 'in/at/across/around/including/such as/like <Item1>, <Item2> and <Item3>'
    m_coord = re.search(
        r"\b(?:in|at|to|from|across|around|between|including|such\s+as|like|centres|centers|states|cities|towns|ports|regions|areas)\s+(?:are\s+|is\s+|include\s+)?([A-Z][A-Za-z\s]+?(?:,\s*[A-Z][A-Za-z\s]+?)*\s+and\s+[A-Z][A-Za-z\s]+)",
        src,
    )
    if m_coord and ans in m_coord.group(1):
        list_parts = [x.strip() for x in re.split(r",\s*(?:and\s+)?|\s+and\s+", m_coord.group(1)) if x.strip()]
        other_parts = [p for p in list_parts if p != ans]
        if other_parts and all(p[0].isupper() and len(p.split()) <= 3 for p in other_parts):
            return True

    return False


def classify_gap_prompt(
    answer: str,
    category: str = "",
    relation: str = "",
    source_text: str = "",
) -> str:
    """Change C & Round 4 Fix 3/4: Classify each gap answer with the expression library and pick the prompt:
      - chemical formula / symbol -> 'Which formula fits the gap?'
      - person -> 'Who fits the gap?'
      - city/state/country/place (including places in lists) -> 'Which place fits the gap?'
      - year -> 'Which year fits the gap?'
      - date -> 'Which date fits the gap?'
      - century -> 'Which century fits the gap?'
      - number/quantity/money -> 'Which number fits the gap?'
      - organisation/event/document/act -> 'Which name fits the gap?'
      - term -> 'Which term fits the gap?'
      - 'Which word fits the gap?' only when none fits.
    """
    from .expressions import FAMILY_A, FAMILY_D, FAMILY_E, FAMILY_I

    ans = (answer or "").strip(" .,;:")
    cat = (category or "").lower()
    rel = (relation or "").upper()
    src = (source_text or "").strip()

    if not ans:
        return "Which word fits the gap?"

    # 0a. Round 5 Fix 3: Chemical formula or substance name with its formula ('carbon dioxide (CO2)', 'glucose (C6H12O6)', 'CO2')
    # uses 'Which substance fits the gap?' — never 'Which number...' (checked BEFORE number check!)
    if is_chemical_substance_or_formula(ans, src):
        return "Which substance fits the gap?"

    # 0b. Physics/math formulas and chemical equations with '=' or '→'
    if (
        any(
            m["type"] in ("chemical_equation", "physics_math_formula")
            and m["text"].strip() == ans
            for m in FAMILY_D.find(ans)
        )
        or (cat == "formula" and ("=" in ans or "→" in ans))
    ):
        return "Which formula fits the gap?"

    # 1. Century
    if "century" in ans.lower() or any(m["type"] == "century" for m in FAMILY_A.find(ans)):
        return "Which century fits the gap?"

    # 2. Full date / month+year / day+month
    if any(m["type"] in ("full_date", "month_year", "day_month") for m in FAMILY_A.find(ans)):
        return "Which date fits the gap?"

    # 3. Year / year range / lifespan / decade
    if (
        re.fullmatch(r"(?:1\d{3}|20\d{2})(?:[–-](?:1\d{3}|20\d{2}|\d{2}))?", ans)
        or cat == "date"
        or any(m["type"] in ("year", "year_range", "decade") for m in FAMILY_A.find(ans))
    ):
        return "Which year fits the gap?"

    # 4. Person
    if (
        cat == "person"
        or rel in (
            "PERSON", "PRESIDING_OFFICER", "APPOINTED_BY", "LED_BY", "PROCLAIMED_AS",
            "TITLE_TO_PERSON", "LED_AT_PLACE", "ACTOR_ON_DATE", "PASSIVE_AGENT", "WORKED_ALONGSIDE",
        )
        or any(m["type"] == "person_or_title" for m in FAMILY_E.find(ans))
    ):
        return "Who fits the gap?"

    # 5. City / state / country / place
    is_place_in_context = _is_place_in_list_context(ans, src)
    if src and ans[0].isupper() and not any(ch.isdigit() for ch in ans):
        if re.search(r"\b(?:at|in|to|from|near|outside)\s+(?:the\s+)?" + re.escape(ans) + r"\b", src):
            is_place_in_context = True
        elif re.search(r"\b(?:centre|capital|city|port|heart|region)\s+of\s+(?:the\s+)?" + re.escape(ans) + r"\b", src, re.IGNORECASE):
            is_place_in_context = True

    if (
        cat == "place"
        or rel in (
            "CAPITAL_OF", "SITUATED_ON", "LOCATED_IN", "REGION", "RESIDENCE",
            "HEADQUARTERS_IN", "FINANCIAL_CENTRE_OF", "LARGEST_OUTSIDE", "REFORMER_IN", "PLACE", "LED_WHERE",
        )
        or ans.startswith("River ")
        or any(m["type"] == "place" for m in FAMILY_I.find(f"in {ans}"))
        or (
            is_place_in_context
            and not any(
                w in ans
                for w in (
                    "Act", "Proclamation", "Treaty", "Charter", "Constitution", "Company",
                    "College", "University", "School", "Bank", "Committee", "Assembly",
                    "Parliament", "Court", "Council", "Museum", "Centre", "Mill", "Crown",
                    "Dynasty", "dynasty", "Revolution", "Rebellion", "Uprising", "Movement",
                )
            )
        )
    ):
        return "Which place fits the gap?"

    # 6. Organisation / event / document / act
    if (
        cat in ("organisation", "document", "event")
        or any(m["type"] == "organisation_document_event" for m in FAMILY_E.find(ans))
        or any(
            w in ans
            for w in (
                "Act", "Proclamation", "Treaty", "Charter", "Constitution", "Company",
                "College", "University", "School", "Bank", "Committee", "Assembly",
                "Parliament", "Court", "Council", "Museum", "Centre", "Center", "Mill",
                "Crown", "Dynasty", "dynasty", "Revolution", "Rebellion", "Uprising",
                "Movement", "Society", "Congress", "League",
            )
        )
    ):
        return "Which name fits the gap?"

    # 7. Number / quantity / money
    if (
        cat in ("number", "quantity")
        or any(ch.isdigit() or ch in "½¾¼⅓⅔" for ch in ans)
    ):
        return "Which number fits the gap?"

    # 8. Term vs. generic word
    # Single lowercase modifier/direction words get 'Which word fits the gap?';
    # noun terms, multi-word concepts, titles, and scientific/civic terms get 'Which term fits the gap?'.
    words = ans.split()
    single_word_modifiers = {
        "constant", "equal", "unequal", "proportional", "inversely",
        "upward", "downward", "forward", "backward", "directly", "indirectly",
    }
    if len(words) == 1 and ans.lower() in single_word_modifiers:
        return "Which word fits the gap?"
    if cat in ("term", "title", "formula") or len(words) >= 2 or ans[0].isupper():
        return "Which term fits the gap?"
    return "Which term fits the gap?"


def make_gap_prompt(
    category: str,
    answer: str = "",
    relation: str = "",
    source_text: str = "",
) -> str:
    """Return a clean prompt for GAP cards based on answer and category."""
    if answer:
        return classify_gap_prompt(answer, category=category, relation=relation, source_text=source_text)
    if category == "formula":
        return "Which formula fits the gap?"
    if category == "date":
        return "Which year fits the gap?"
    if category == "person":
        return "Who fits the gap?"
    if category == "place":
        return "Which place fits the gap?"
    if category in ("organisation", "document", "event"):
        return "Which name fits the gap?"
    if category in ("number", "quantity"):
        return "Which number fits the gap?"
    if category in ("term", "title"):
        return "Which term fits the gap?"
    return "Which word fits the gap?"


def _format_subjectless_gap_sentence(subj: str, front: str) -> str:
    """Format a gap sentence without ever adding 'In <subject>, ...'.
    Keep the sheet's sentence as is (capitalized) and rely on the card label to name the subject,
    or prepend '<subj> ' / '<subj> was ' only when the fragment starts with a verb or role noun.
    """
    s_front = (front or "").strip()
    if not s_front:
        return s_front
    # Strip any legacy 'In <subj>, ' prefix if present in source_text
    if subj and s_front.lower().startswith(f"in {subj.lower()}, "):
        s_front = s_front[len(subj) + 5 :].strip()
    elif subj and s_front.lower().startswith(f"in the {subj.lower()}, "):
        s_front = s_front[len(subj) + 9 :].strip()

    first_word = s_front.split()[0].rstrip(".,;:") if s_front.split() else ""
    fw_low = first_word.lower()

    # If the sentence starts with a finite verb (e.g. 'Worked to...', 'Founded...', 'Continues to...')
    # and the subject is not already in the sentence, either keep the sheet's own sentence capitalized
    # and rely on the card label, or if it starts with 'was/is/were' or 'a/an/the <role> of', prepend subject.
    if subj and subj.lower() not in s_front.lower() and not s_front.startswith("______"):
        if fw_low in ("was", "is", "were", "are", "became", "remained"):
            s_front = f"{subj} {s_front[0].lower() + s_front[1:]}"
        elif re.match(r"^(?:an?|the)\s+(?:founding\s+member|member|founder|leader|pioneer|president|chairman|author|writer)\s+of\b", s_front, re.IGNORECASE):
            s_front = f"{subj} was {s_front[0].lower() + s_front[1:]}"
        elif s_front[0].islower():
            s_front = s_front[0].upper() + s_front[1:]
    elif s_front and s_front[0].islower():
        s_front = s_front[0].upper() + s_front[1:]

    if not s_front.endswith(".") and not s_front.endswith("?"):
        s_front += "."
    return s_front


_CLAUSE_VERB_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|has|have|had|can|could|will|would|shall|should|may|might|must|"
    r"do|does|did|founded|established|started|began|opened|built|wrote|authored|published|invented|"
    r"discovered|led|chaired|headed|moved|passed|adopted|signed|joined|became|won|received|graduated|"
    r"died|fell|rose|grew|came|took|made|gave|held|met|fought|defeated|captured|recaptured|ruled|"
    r"abolished|introduced|formed|created|organised|organized|proclaimed|declared|launched|co-launched|"
    r"co-founded|entered|reached|visited|returned|left|sent|brought|taught|worked|served|lived|"
    r"use|uses|used|keep|kept|repeat|take|takes|absorb|absorbs|release|releases|produce|produces|"
    r"convert|converts|converted|campaigned|retire|retires|protects|supports|determines|means|refers)\b",
    re.IGNORECASE,
)


def trim_clue_clause(src: str, ans: str, max_words: int = 20) -> str:
    """Round 5 Fix 4: Trim every clue to at most `max_words` (20) words:
    keep the clause with the gap; drop trailing clauses after ';' or ', and' that don't hold the answer.
    """
    from .facts import split_into_clauses

    s = (src or "").strip()
    a = (ans or "").strip()
    if not s or not a:
        return s

    chosen = s

    # 1. Semicolon ';' clauses: always drop trailing clauses after ';' that don't hold `ans`,
    # and if `ans` is in a later clause after ';', keep the clause holding `ans`
    # (unless the first clause has a '<Header>:' subject prefix and the full string is already <= max_words).
    if ";" in chosen:
        semi_parts = [p.strip() for p in chosen.split(";") if p.strip()]
        ans_semi_idx = next((i for i, p in enumerate(semi_parts) if a in p), -1)
        if ans_semi_idx != -1:
            if ans_semi_idx == 0:
                chosen = semi_parts[0]
            else:
                kept_UpTo = "; ".join(semi_parts[: ans_semi_idx + 1])
                if (
                    ":" in semi_parts[0]
                    and len(semi_parts[ans_semi_idx].split()) < 4
                    and len(kept_UpTo.split()) <= max_words
                ):
                    chosen = kept_UpTo
                else:
                    chosen = semi_parts[ans_semi_idx]

    # 2. Trailing ', and ' clauses: drop trailing clauses after ', and ' that don't hold `ans`
    # (when the part before ', and ' is a clause with a verb or '=' or when total words > max_words).
    if ", and " in chosen:
        ca_parts = chosen.split(", and ")
        ans_ca_idx = next((i for i, p in enumerate(ca_parts) if a in p), -1)
        if ans_ca_idx != -1:
            before_and = ", and ".join(ca_parts[: ans_ca_idx + 1]).strip()
            after_and = ", and ".join(ca_parts[ans_ca_idx + 1 :]).strip()
            if after_and and a not in after_and:
                if (
                    _CLAUSE_VERB_RE.search(before_and)
                    or "=" in before_and
                    or len(chosen.split()) > max_words
                ):
                    chosen = before_and
            if ans_ca_idx > 0 and len(chosen.split()) > max_words:
                chosen = ca_parts[ans_ca_idx].strip()

    # 3. If still > max_words, split by sentence/clause splitter and keep clause with `ans`
    if len(chosen.split()) > max_words:
        clauses = split_into_clauses(chosen)
        for cl in clauses:
            if a in cl:
                chosen = cl.strip()
                break

    # 4. If still > max_words, split on comma + conjunction/participle/relative clause or dash boundary
    if len(chosen.split()) > max_words:
        sub_parts = [
            p.strip()
            for p in re.split(
                r",\s+(?=(?:later|inspiring|which|where|when|while|although|because|since|as|and|but|or|so|helping|leading|making|giving|allowing|to\b))|\s+[–—-]\s+",
                chosen,
            )
            if p.strip()
        ]
        for sp in sub_parts:
            if a in sp:
                chosen = sp
                break

    # 5. If still > max_words, drop parenthetical remarks that don't contain `ans`
    if len(chosen.split()) > max_words and "(" in chosen and ")" in chosen:
        stripped_parens = re.sub(
            r"\s*\([^)]*\)",
            lambda m: m.group(0) if a in m.group(0) else "",
            chosen,
        ).strip()
        if a in stripped_parens:
            chosen = stripped_parens

    # 6. Hard cap at max_words around `ans`
    words = chosen.split()
    if len(words) > max_words:
        ans_first = a.split()[0]
        ans_idx = next((i for i, w in enumerate(words) if ans_first in w), len(words) - 1)
        start_w = max(0, min(ans_idx - (max_words - 4), len(words) - max_words))
        chosen = " ".join(words[start_w : start_w + max_words]).strip(" ,;:")

    return chosen


def trim_year_clause(src: str, ans: str, max_words: int = 20) -> str:
    """Backward-compatible alias for trim_clue_clause (<= 20 words)."""
    return trim_clue_clause(src, ans, max_words=max_words)


def _enforce_max_clue_words(front: str, max_words: int = 20) -> str:
    """Ensure a formatted clue `front` has at most `max_words` words while keeping '______' and ending punctuation."""
    words = (front or "").split()
    if len(words) <= max_words:
        return front
    end_punct = "." if front.endswith(".") else ("?" if front.endswith("?") else ".")
    gap_idx = next((i for i, w in enumerate(words) if "______" in w), len(words) - 1)
    start_w = max(0, min(gap_idx - (max_words - 4), len(words) - max_words))
    trimmed = " ".join(words[start_w : start_w + max_words]).strip(" ,;:.?")
    if trimmed and trimmed[0].islower() and not trimmed.startswith("______"):
        trimmed = trimmed[0].upper() + trimmed[1:]
    return trimmed + end_punct


def _build_gap_from_source(subj: str, ans: str, src: str, category: str, relation: str = "") -> Dict[str, str]:
    """Construct a clean T9 GAP fallback card from source_text without any 'In <subject>, ...' prefix,
    trimmed to at most 20 words (Round 5 Fix 4).
    """
    prompt_str = classify_gap_prompt(ans, category=category, relation=relation, source_text=src)
    use_src = trim_clue_clause(src, ans, max_words=20)
    pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(ans) + r"(?![A-Za-z0-9])")
    if pattern.search(use_src):
        front = pattern.sub("______", use_src, count=1)
    else:
        front = use_src.replace(ans, "______", 1)
    front = _format_subjectless_gap_sentence(subj, front)
    front = _enforce_max_clue_words(front, max_words=20)
    return {
        "front": front,
        "prompt": prompt_str,
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
        alternatives.append({"front": f"{subj} is called ______.", "prompt": make_gap_prompt("title", ans, rel, src), "question_type": "GAP"})
    elif rel == "TITLE_TO_PERSON":
        title_str = meta.get("title", subj)
        t_clean = title_str[4:] if title_str.lower().startswith("the ") else title_str
        front = f"Who is called the {t_clean}?"
        q_type = "WHO"
        prompt = "Name the person"
    elif rel == "ROLE_DEFINITION":
        front = f"{subj} is the ______."
        q_type = "GAP"
        prompt = make_gap_prompt("title", ans, rel, src)
        alternatives.append({"front": f"What is {mid_s} called?", "prompt": "", "question_type": "TITLE"})
    elif rel == "TERM_FROM_DEFINITION":
        defn = meta.get("definition", "").strip().rstrip(".")
        if len(defn.split()) <= 12:
            front = f"What is the name for {defn}?"
        else:
            front = f"What is {defn} called?"
        q_type = "WHAT"
        alternatives.append({"front": f"What is {defn} called?", "prompt": "", "question_type": "TITLE"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "ALSO_CALLED":
        front = f"What is the {mid_plain} also called?"
        q_type = "TITLE"
        alternatives.append({"front": f"What is another name for the {mid_plain}?", "prompt": "", "question_type": "WHAT"})
    elif rel == "SUMMARY_EQUALS":
        # Change D: For lines like '<X> = <Y> (...)', make a gap card on the sheet's own line;
        # never 'In the comparison, what does X equal?'
        front = src.replace(ans, "______", 1)
        if not front.endswith(".") and not front.endswith("?"):
            front += "."
        q_type = "GAP"
        prompt = make_gap_prompt("term", ans, rel, src)
    elif rel == "TERM_LENGTH":
        front = f"What is the term of {mid_s}?"
        q_type = "HOW_MANY"
        alternatives.append({"front": f"How long is the term of {mid_s}?", "prompt": "", "question_type": "HOW_MANY"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "MEM_TERM_LENGTH":
        front = f"How long is a member's term in {mid_s}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "PRESIDING_OFFICER":
        front = f"Who is the presiding officer of {mid_s}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "MIN_AGE":
        role_w = meta.get("role", "")
        if role_w:
            front = f"What is the minimum age for a {role_w} of {mid_s}?"
        else:
            front = f"What is the minimum age for {mid_s}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "RETIRE_AGE":
        grp = meta.get("group", "members")
        front = f"At what age do {grp} of {mid_s} retire?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "PASSIVE_AGENT":
        act_v = meta.get("active_verb", "appoints")
        t_grp = meta.get("target_group", "")
        if t_grp:
            front = f"Who {act_v} the {t_grp} of {mid_s}?"
        else:
            front = f"Who {act_v} {mid_s}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "MEASURED_ON":
        if subj.endswith("s"):
            front = f"On which scale are {subj} measured?"
        else:
            front = f"On which scale is {mid_s} measured?"
        q_type = "WHAT"
        alternatives.append({"front": "It is measured on the ______.", "prompt": make_gap_prompt("term", ans, rel, src), "question_type": "GAP"})
    elif rel == "PROTECTS":
        ben = meta.get("beneficiary", "citizens")
        front = f"What does {mid_s} protect for {ben}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
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
        alternatives.append({"front": f"In {place}, ______ led the {ev_n}.", "prompt": "Who fits the gap?", "question_type": "GAP"})
    elif rel == "ACTOR_ON_DATE":
        dt = meta.get("date", "")
        act = meta.get("action", "")
        front = f"On {dt}, who {act}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "EVENT_ON_DATE":
        trimmed_src = trim_year_clause(src, ans, max_words=20)
        front = trimmed_src.replace(ans, "______", 1)
        if not front.endswith("."):
            front += "."
        q_type = "GAP"
        prompt = make_gap_prompt("date", ans, rel, src)
    elif rel == "PROCLAIMED_AS":
        grp = meta.get("group", "rebels")
        role = meta.get("role", "emperor")
        front = f"Who did the {grp} proclaim as their {role}?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "RECAPTURED_IN":
        actor = meta.get("actor", "")
        verb = meta.get("verb", "recaptured")
        base_v = PAST_TO_BASE_VERBS.get(verb.lower(), verb.lower())
        if actor and base_v:
            front = f"When did the {actor} {base_v} {subj}?"
            q_type = "WHEN"
            alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
        else:
            front = src.replace(ans, "______", 1)
            if not front.endswith("."):
                front += "."
            q_type = "GAP"
            prompt = make_gap_prompt("date", ans, rel, src)
    elif rel == "ENDED_RULE_BY_DOC":
        front = f"Which Act ended the rule of the {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "BECAME_ROLE":
        front = f"What did the {subj} become?"
        q_type = "TITLE"
        alternatives.append({"front": f"What role did the {subj} become?", "prompt": "", "question_type": "WHAT"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "LIST_FACTOR":
        fl = meta.get("factor_label", "cause")
        if fl in ("political", "economic", "military"):
            front = f"What was one {fl} cause of {mid_plain}?"
        elif fl == "immediate cause":
            front = f"What was the immediate cause of {mid_plain}?"
        else:
            front = f"What is one of the {fl} of {mid_plain}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "COLON_EQUATION_RHS":
        prefix = meta.get("prefix", "")
        lhs = meta.get("lhs", "").strip()
        label_part = meta.get("label_part", "").strip()
        front = f"{prefix} ______."
        q_type = "GAP"
        prompt = make_gap_prompt(fact.get("category", "number"), ans, rel, src)
        if meta.get("is_formula") == "1" and lhs:
            alternatives.append({"front": f"What is the formula for {lhs}?", "prompt": "", "question_type": "FORMULA"})
        elif lhs:
            alternatives.append({"front": f"What does {lhs} equal?", "prompt": "", "question_type": "HOW_MANY"})
            alternatives.append({"front": f"Complete: {prefix} ______.", "prompt": "Complete the formula", "question_type": "FORMULA"})
    elif rel == "CALCULATED_ON":
        front = f"What is {subj.lower()} calculated on?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "TABLE_CELL":
        col_h = meta.get("col_header", "value")
        row_k = meta.get("row_key", subj)
        if col_h.lower() in ("fraction", "probability") and "/" not in col_h:
            front = f"What is the {col_h} for {row_k}?"
        else:
            front = f"Which {col_h} goes with {row_k}?"
        q_type = "TABLE"
        if any(ch.isdigit() for ch in ans):
            alternatives.append({"front": f"How much is the {col_h} for {row_k}?", "prompt": "", "question_type": "HOW_MANY"})
        alternatives.append({"front": f"What is the {col_h} for {row_k}?", "prompt": "", "question_type": "WHAT"})
        alternatives.append({"front": f"{row_k} — {col_h}: ______.", "prompt": make_gap_prompt(cat, ans, rel, src), "question_type": "GAP"})
    elif rel == "REGARDED_AS_FIRST":
        place = meta.get("place", "")
        if place:
            front = f"What is {subj} regarded as {place}'s first?"
        else:
            front = f"What is {subj} regarded as the first of?"
        q_type = "TITLE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "FOUNDED":
        front = f"Which organisation did {subj} found?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "FOUNDED_IN":
        front = f"In which year was the {subj} founded?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "GRADUATED_FROM":
        front = f"Which college did {subj} graduate from?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "GRADUATED_IN":
        front = f"In which year did {subj} graduate?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "FOUNDED_ENTITY_IN":
        ek = meta.get("entity_kind", "organisation")
        front = f"In which year did {subj} found a {ek}?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "CONVERTED_INTO":
        so = meta.get("source_obj", "building")
        front = f"What did {subj} convert an {so} into?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "ESTABLISHED":
        front = f"What did {subj} establish?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "WROTE":
        front = f"What did {subj} write?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "OPENED":
        front = f"What did {subj} open?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "OPENED_ON":
        front = f"On what date did the {subj} open?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "FIRST_WITH":
        place = meta.get("place", "")
        if place:
            front = f"The {subj} was the first in {place} with what?"
        else:
            front = f"The {subj} was the first with what?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "LAID_FOUNDATIONS_FOR":
        front = f"What did {subj} lay foundations for?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "REFORMER_IN":
        front = f"Where was {subj} a social reformer and writer?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "PURPOSE":
        front = f"What was the purpose of the {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "WORKED_ALONGSIDE":
        front = f"Who did {subj} work alongside?"
        q_type = "WHO"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "STARTED_IN":
        front = f"In which year were {subj} started?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "RESIDENCE":
        front = f"What was the residence of {subj}?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "LOCATED_IN":
        front = f"Where is {mid_s} located?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "CHAIRED":
        front = f"Which committee did {subj} chair?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "PART_OF":
        front = f"What was the {subj} part of?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "PRECURSOR_TO":
        front = f"What was the {subj} a precursor to?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "INSPIRED":
        front = f"Which organisation did the {subj} inspire?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "CAMPAIGNED_FOR":
        front = f"What did {subj} campaign for?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "YEAR":
        front = f"In which year was the {subj}?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "CAPITAL_OF":
        front = f"What is {subj} the capital of?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "SITUATED_ON":
        front = f"Which river is {subj} situated on?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "FINANCIAL_CENTRE_OF":
        front = f"What is {subj} the financial centre of?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "REGION":
        front = f"Which region is {subj} a major city of?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "LARGEST_OUTSIDE":
        front = f"Outside which city is {subj} the largest city?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "PROMINENCE_IN":
        front = f"In which century did {subj} grow to international prominence?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "AT_HEART_OF":
        front = f"What was {subj} at the heart of?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "INVENTION":
        front = f"What was invented in {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "SUPERLATIVE_ROLE":
        place = meta.get("place", "")
        if place:
            front = f"What is {subj} in the {place}?"
        else:
            front = f"What is {subj} known as?"
        q_type = "TITLE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "VISITORS_PER_YEAR":
        front = f"How many visitors does {subj} get each year?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "POPULATION":
        front = f"What is the population of {subj}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "HISTORIC_INDUSTRY":
        front = f"What is a historic industry of {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "BUILT":
        front = f"What did {subj} build?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "FACILITY_IN":
        fk = meta.get("facility_kind", "facility")
        front = f"Which {fk} is in {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "INDUSTRY_SINCE":
        since = meta.get("since", "")
        if since:
            front = f"Which industry has {subj} sustained since the {since}?"
        else:
            front = f"Which major industry has {subj} sustained?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "HOME_TO":
        front = f"What is {subj} home to?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "RANK":
        place = meta.get("place", "")
        if place:
            front = f"What is the population rank of {subj} in the {place}?"
        else:
            front = f"What is the population rank of {subj}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "FINANCIAL_RANK":
        place = meta.get("place", "")
        if place:
            front = f"What rank is {subj} as a financial centre in the {place}?"
        else:
            front = f"What rank is {subj} as a financial centre?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "BANKING_FOR":
        front = f"For how long has {subj} been a centre of banking?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "HEADQUARTERS_IN":
        front = f"Where does the {subj} have its global headquarters?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "SUPPORTS":
        sec = meta.get("sector", "")
        if sec:
            front = f"How many jobs does {sec} support in {subj}?"
        else:
            front = f"How many jobs does {subj} support?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "WORTH":
        sec = meta.get("sector", "")
        if sec:
            front = f"How much is {sec} worth to the {subj} economy?"
        else:
            front = f"How much is {subj} worth to the city economy?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "ARCHITECTURE_INCLUDES":
        front = f"What famous area is part of the architecture of {subj}?"
        q_type = "WHERE"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "SEAT_OF":
        front = f"What is {subj} the seat of?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "SMALL_TOWN_UNTIL":
        front = f"Until which century was {subj} a small town?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "MOST_IMPORTANT":
        front = f"What did {subj} become the world's most important?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "MADE_CITY_IN":
        front = f"In which year was {subj} made a city?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "PROCLAIMED_CAPITAL_IN":
        place = meta.get("place", "")
        if place:
            front = f"In which year was {subj} proclaimed capital of {place}?"
        else:
            front = f"In which year was {subj} proclaimed a capital?"
        q_type = "WHEN"
        alternatives.append(_build_gap_from_source(subj, ans, src, "date", rel))
    elif rel == "DETERMINES":
        front = f"What does {subj} determine?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "FORMULA":
        front = f"What is the formula for {subj}?"
        q_type = "FORMULA"
        alternatives.append(_build_gap_from_source(subj, ans, src, "formula", rel))
    elif rel == "DEFINITION_FORMULA":
        front = f"What is the definition of {subj}?"
        q_type = "FORMULA"
        alternatives.append(_build_gap_from_source(subj, ans, src, "formula", rel))
    elif rel == "CALC_RESULT":
        front = f"What is the calculated result for {subj}?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "UNIT_OF":
        front = f"What is the unit of {subj}?"
        q_type = "WHAT"
        alternatives.append({"front": f"Which unit goes with {subj}?", "prompt": "", "question_type": "TABLE"})
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "CONVERT_TO":
        fu = meta.get("from_unit", "units")
        front = f"What are {fu} converted to {subj}?"
        q_type = "WHAT"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    elif rel == "EQUALS_VALUE":
        front = f"What does {subj} equal?"
        q_type = "HOW_MANY"
        alternatives.append(_build_gap_from_source(subj, ans, src, cat, rel))
    else:
        prompt = make_gap_prompt(cat, ans, rel, src)
        use_src = trim_clue_clause(src, ans, max_words=20)
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(ans) + r"(?![A-Za-z0-9])")
        if pattern.search(use_src):
            front = pattern.sub("______", use_src, count=1)
        else:
            front = use_src.replace(ans, "______", 1)
        front = _format_subjectless_gap_sentence(subj, front)
        front = _enforce_max_clue_words(front, max_words=20)
        q_type = "GAP"
        if meta.get("alt_what"):
            alternatives.append({"front": _enforce_max_clue_words(meta["alt_what"], max_words=20), "prompt": "", "question_type": "WHAT"})
        if meta.get("alt_how_many"):
            alternatives.append({"front": _enforce_max_clue_words(meta["alt_how_many"], max_words=20), "prompt": "", "question_type": "HOW_MANY"})

    front = _enforce_max_clue_words(front, max_words=20)

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


def generate_reinforcement_card(fact: Dict[str, Any], card_id: str = "TEMP_REV") -> Dict[str, Any] | None:
    """Change G: Build a reverse-direction reinforcement card for a core fact
    (e.g. 'Who founded the Satyashodhak Samaj?' <-> 'Which organisation did Jyotirao Phule found?').
    """
    subj = (fact.get("subject") or "").strip()
    rel = fact.get("relation", "")
    ans = (fact.get("object") or "").strip()
    src = fact.get("source_text", "")
    meta = fact.get("meta") or {}
    if not subj or not ans or subj.lower() == ans.lower():
        return None

    is_person_subj = (
        subj[0].isupper()
        and len(subj.split()) >= 2
        and not subj.lower().startswith("the ")
        and not any(ch.isdigit() for ch in subj)
    )

    rev_front = ""
    rev_prompt = ""
    rev_qtype = ""
    rev_ans = ""
    rev_subj = ""

    if rel == "FOUNDED" and is_person_subj:
        org_mid = ans if ans.lower().startswith("the ") else f"the {ans}"
        rev_front = f"Who founded {org_mid}?"
        rev_prompt = "Name the person"
        rev_qtype = "WHO"
        rev_ans = subj
        rev_subj = ans
    elif rel == "ESTABLISHED" and is_person_subj:
        org_mid = ans if ans.lower().startswith("the ") else f"the {ans}"
        rev_front = f"Who established {org_mid}?"
        rev_prompt = "Name the person"
        rev_qtype = "WHO"
        rev_ans = subj
        rev_subj = ans
    elif rel == "CHAIRED" and is_person_subj:
        org_mid = ans if ans.lower().startswith("the ") else f"the {ans}"
        rev_front = f"Who chaired {org_mid}?"
        rev_prompt = "Name the person"
        rev_qtype = "WHO"
        rev_ans = subj
        rev_subj = ans
    elif rel == "WROTE" and is_person_subj:
        rev_front = f"Who wrote {ans}?"
        rev_prompt = "Name the person"
        rev_qtype = "WHO"
        rev_ans = subj
        rev_subj = ans
    elif rel == "IS_CALLED" and is_person_subj and re.match(
        r"^(?:the\s+)?(?:Father|Mother|Founder|Architect|Pioneer|Grand\s+Old\s+Man|Iron\s+Man|Nightingale|Lion|Bard)\s+of\b",
        ans,
        re.IGNORECASE,
    ):
        t_clean = ans[4:] if ans.lower().startswith("the ") else ans
        rev_front = f"Who is called the {t_clean}?"
        rev_prompt = "Name the person"
        rev_qtype = "WHO"
        rev_ans = subj
        rev_subj = ans
    elif rel == "TITLE_TO_PERSON" and ans[0].isupper() and len(ans.split()) >= 2:
        t_clean = subj[4:] if subj.lower().startswith("the ") else subj
        rev_front = f"What is {ans} called?"
        rev_prompt = ""
        rev_qtype = "TITLE"
        rev_ans = t_clean
        rev_subj = ans
    elif rel == "LED_AT_PLACE":
        ev_n = meta.get("event_noun", "revolt")
        place = meta.get("place", subj)
        if place and place != ans:
            rev_front = f"Where did {ans} lead the {ev_n}?"
            rev_prompt = ""
            rev_qtype = "WHERE"
            rev_ans = place
            rev_subj = ans

    if not rev_front or not rev_ans or not rev_subj:
        return None

    return {
        "id": card_id,
        "fact_id": fact["id"],
        "item_id": fact["item_id"],
        "page": fact["page"],
        "label": shorten_label(rev_subj),
        "front": rev_front,
        "prompt": rev_prompt,
        "answer": rev_ans,
        "question_type": rev_qtype,
        "source_text": src,
        "subject": rev_subj,
        "status": "candidate",
        "_alternatives": [],
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

    # Pass 3: Enforce no single question_type > 60% of the sheet (and TABLE <= 1/3 of the sheet)
    counts = {}
    for c in cards:
        qt = c["question_type"]
        counts[qt] = counts.get(qt, 0) + 1

    for t_over, cnt in list(counts.items()):
        limit = max(1, n // 3) if (t_over == "TABLE" and n >= 3) else max_per_type
        if cnt <= limit:
            continue
        for idx in range(n - 1, -1, -1):
            if counts[t_over] <= limit:
                break
            if cards[idx]["question_type"] != t_over:
                continue
            for opt in options_per_card[idx]:
                alt_t = opt["question_type"]
                alt_limit = max(1, n // 3) if (alt_t == "TABLE" and n >= 3) else max_per_type
                if (
                    alt_t != t_over
                    and counts.get(alt_t, 0) + 1 <= alt_limit
                    and not creates_run_of_4(idx, alt_t)
                ):
                    counts[t_over] -= 1
                    counts[alt_t] = counts.get(alt_t, 0) + 1
                    apply_opt(idx, opt)
                    break

    for c in cards:
        c.pop("_alternatives", None)

    return cards
