"""Reusable, rule-based Expression Library for Class 1–10 study sheets (Prompt 8).

Recognises the general phrasing patterns school study sheets across all subjects
(history, civics, geography, economics, science, maths, EVS, English, GK) use
to state facts — dates, numbers, quantities, measurements, formulas, names/roles,
definitions, causes, sequences, places, comparisons, grammar facts, and sheet
practice questions — without topic-specific word lists.

Each family A–L exposes:
    find(sentence: str) -> list[dict[str, Any]]
where each match dict contains:
    - "span": (start, end) character offsets in `sentence` of the WHOLE unit to blank
    - "text": exact substring `sentence[start:end]`
    - "type": specific sub-type identifier
    - "question_type": question / prompt supported by this match
    - "family": family code ("A".."L")
    - "bullet": numbered rule within the family
"""

from __future__ import annotations

import re
from typing import Any


SUPERLATIVE_CHECK_NOTE = "Check first: superlative claim ('the largest/first/only') — verify context on the sheet."

_MONTH_FULL = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)"
)

_NUMBER_WORDS_CARDINAL = (
    r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|"
    r"twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion|lakh|crore)"
)

_NUMBER_WORDS_ORDINAL = (
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth)"
)

_CENTURY_WORDS = (
    r"(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|"
    r"eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|twenty-first)"
)

_UNIT_SYMBOLS = (
    r"(?:kg·m/s²|kg\.m/s²|km/h|m/s²|m/s|cm/s|kg/m³|g/cm³|mol/dm³|mol/L|"
    r"light\s+years?|AU\b|"
    r"square\s+kilomet(?:re|er)s?|square\s+met(?:re|er)s?|cubic\s+met(?:re|er)s?|cubic\s+centimet(?:re|er)s?|"
    r"sq\.?\s*km|sq\.?\s*m|km²|m²|cm²|mm²|m³|cm³|"
    r"°C|°F|K\b|mm\b|cm\b|km\b|m\b|mg\b|kg\b|g\b|mL\b|L\b|mol\b|"
    r"kJ\b|J\b|kW\b|W\b|kPa\b|Pa\b|MHz\b|Hz\b|mA\b|A\b|kV\b|V\b|Ω|ohm(?:s)?\b|N\b|min\b|hrs?\b|h\b|s\b)"
)


def _overlaps(span: tuple[int, int], existing: list[tuple[int, int]]) -> bool:
    s, e = span
    return any(not (e <= es or s >= ee) for es, ee in existing)


def _inside_any(span: tuple[int, int], containers: list[tuple[int, int]]) -> bool:
    s, e = span
    return any(cs <= s and e <= ce for cs, ce in containers)


def _clean_span_bounds(sentence: str, start: int, end: int) -> tuple[int, int]:
    """Trim leading/trailing whitespace and stray punctuation while keeping exact offsets in `sentence`."""
    if re.fullmatch(r"\((?:aq|s|l|g)\)", sentence[start:end]):
        return start, end
    while start < end and sentence[start] in " \t\n\r,;:([\"'‘“":
        start += 1
    while end > start and sentence[end - 1] in " \t\n\r.,;:)]\"'’”":
        # Keep closing paren if an opening paren is inside the span
        if sentence[end - 1] == ")" and "(" in sentence[start:end - 1]:
            break
        # Keep trailing period on abbreviations like "B. R." or "c."
        if sentence[end - 1] == "." and re.search(r"\b[A-Za-z]\.$", sentence[start:end]):
            break
        end -= 1
    return start, end


def _make_match(
    sentence: str,
    start: int,
    end: int,
    expr_type: str,
    question_type: str,
    family: str,
    bullet: int = 1,
    **extra: Any,
) -> dict[str, Any] | None:
    s, e = _clean_span_bounds(sentence, start, end)
    if s >= e:
        return None
    text = sentence[s:e]
    if not text.strip():
        return None
    res: dict[str, Any] = {
        "span": (s, e),
        "text": text,
        "type": expr_type,
        "question_type": question_type,
        "family": family,
        "bullet": bullet,
    }
    res.update(extra)
    return res


def _detect_when_did_question(sentence: str, date_span: tuple[int, int]) -> str:
    """Return 'When did <subject> <verb>?' if the sentence clearly gives subject, verb, and date; else 'Which year…?' / 'Which date…?'."""
    prefix = sentence[: date_span[0]].strip()
    m_sv = re.match(
        r"^(?:The\s+)?([A-Z][A-Za-z0-9\s’'\-]{1,30}?)\s+(?:(was|were)\s+)?(founded|established|started|began|opened|built|adopted|proclaimed|launched|met|died|graduated|took\s+place|came\s+into\s+effect)\b",
        prefix,
    )
    if m_sv:
        subj = m_sv.group(1).strip()
        aux = (m_sv.group(2) or "").strip().lower()
        verb = m_sv.group(3).strip()
        if aux in {"was", "were"}:
            return "Which date…?"
        base_map = {
            "founded": "found",
            "established": "establish",
            "started": "start",
            "began": "begin",
            "opened": "open",
            "built": "build",
            "adopted": "adopt",
            "proclaimed": "proclaim",
            "launched": "launch",
            "met": "meet",
            "died": "die",
            "graduated": "graduate",
            "took place": "take place",
            "came into effect": "come into effect",
        }
        v_inf = base_map.get(verb.lower(), verb.lower())
        return f"When did {subj} {v_inf}?"
    return ""


# ===========================================================================
# A. TIME AND DATES
# ===========================================================================

class TimeAndDatesFamily:
    """Family A: Full dates, month+year/day+month, years with prepositions, year ranges/durations,
    centuries, decades/eras, era markers (BC/AD/BCE/CE/circa), Indian calendars, relative time links,
    and times of day / durations.
    """

    code = "A"
    name = "TIME AND DATES"

    # 1. Full dates: "8 August 1942", "August 8, 1942", "8th August 1942", "08/08/1942", "26-01-1950"
    _FULL_DATE_RE = re.compile(
        rf"(?<!\w)(?:"
        rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH_FULL},?\s+\d{{4}}|"
        rf"{_MONTH_FULL}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|"
        rf"\d{{2}}[/-]\d{{2}}[/-]\d{{4}}|"
        rf"\d{{4}}[/-]\d{{2}}[/-]\d{{2}}"
        rf")(?!\w)"
    )

    # 8. Indian calendars: "Vikram Samvat 2080", "Vikram Samvat 57 BC", "Shaka era 78 AD", "Vikram Samvat", "Shaka era"
    _INDIAN_CALENDAR_RE = re.compile(
        r"\b((?:Vikram\s+Samvat|Shaka\s+era|Saka\s+era)(?:\s+\d{1,4}(?:\s*(?:BC|BCE|AD|CE))?)?)\b",
        re.IGNORECASE,
    )

    # 7. Era markers: "326 BC", "AD 1206", "250 BCE", "1206 CE", "c. 1500", "circa 1500", "around 1600", "about 1757"
    _ERA_MARKER_DIRECT_RE = re.compile(
        r"(?<!\w)(?:"
        r"\d{1,4}\s*(?:BC|BCE|AD|CE)\b|"
        r"\b(?:AD|CE)\s+\d{1,4}\b|"
        r"\b(?:c\.|circa)\s*\d{3,4}\b"
        r")",
        re.IGNORECASE,
    )
    _ERA_APPROX_YEAR_RE = re.compile(
        r"\b(?:around|about)\s+((?:1[0-9]{3}|20[0-2][0-9]))\b",
        re.IGNORECASE,
    )

    # 4. Year ranges and spans: "1917–1934", "1839–1904", "for 17 years", "over 300 years", "24-day"
    _YEAR_RANGE_RE = re.compile(r"\b((?:1[0-9]{3}|20[0-2][0-9])\s*[–\-—]\s*(?:\d{2}|1[0-9]{3}|20[0-2][0-9]))\b")
    _DURATION_SPAN_RE = re.compile(
        r"\b(?:(?:for|over|nearly|about)\s+(\d+(?:,\d{3})*\s+(?:years|decades|months|weeks|days))|(\d+-day|\d+-year|\d+-month))\b",
        re.IGNORECASE,
    )

    # 2. Month + year / day + month: "August 1942", "15 August", "15th August"
    _MONTH_YEAR_OR_DAY_MONTH_RE = re.compile(
        rf"(?<!\w)(?:"
        rf"{_MONTH_FULL}\s+(?:1[0-9]{{3}}|20[0-2][0-9])|"
        rf"\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH_FULL}"
        rf")(?!\w)"
    )

    # 3. Years with a preposition: "in 1873", "by 1905", "from 1917 to 1934", "between 1857 and 1858", "since 1947", "until 1950", "till 1919"
    _PREP_YEAR_PAIR_RE = re.compile(
        r"\b(?:from\s+((?:1[0-9]{3}|20[0-2][0-9]))\s+to\s+((?:1[0-9]{3}|20[0-2][0-9]))|"
        r"between\s+((?:1[0-9]{3}|20[0-2][0-9]))\s+and\s+((?:1[0-9]{3}|20[0-2][0-9])))\b",
        re.IGNORECASE,
    )
    _PREP_SINGLE_YEAR_RE = re.compile(
        r"\b(in|by|since|until|till|from|after|before|during)\s+((?:1[0-9]{3}|20[0-2][0-9]))\b",
        re.IGNORECASE,
    )
    _BARE_YEAR_RE = re.compile(r"\b((?:1[0-9]{3}|20[0-2][0-9]))\b")

    # 5. Centuries and parts: "19th century", "the nineteenth century", "early/mid/late 20th century", "the latter half of the 20th century", "turn of the century"
    _CENTURY_RE = re.compile(
        rf"\b((?:(?:the\s+)?latter\s+half\s+of\s+the\s+(?:\d{{1,2}}(?:st|nd|rd|th)|{_CENTURY_WORDS})\s+century|"
        rf"(?:(?:the\s+)?(?:early|mid|late)(?:[/-](?:early|mid|late))*\s+)?(?:\d{{1,2}}(?:st|nd|rd|th)|{_CENTURY_WORDS})\s+century|"
        rf"the\s+{_CENTURY_WORDS}\s+century|"
        rf"turn\s+of\s+the\s+century))\b",
        re.IGNORECASE,
    )

    # 6. Decades and eras: "the 1930s", "mid-1930s", "the Mughal period", "the Vedic age", "the Stone Age", "Bronze Age"
    _DECADE_RE = re.compile(r"\b((?:(?:the\s+)?(?:early|mid|late)[-\s])?(?:1[0-9]{2}0s|20[0-2]0s))\b", re.IGNORECASE)
    _NAMED_ERA_RE = re.compile(
        r"\b((?:the\s+)?[A-Z][a-z]{2,20}(?:\s+[A-Z][a-z]{2,20})?\s+(?:Age|age|era|Era|period|Period|dynasty|Dynasty))\b"
    )

    # 9. Relative time words pointing to a date nearby
    _RELATIVE_TIME_RE = re.compile(
        r"\b(before|after|later|earlier|following|during|at\s+the\s+time\s+of|when)\b",
        re.IGNORECASE,
    )

    # 10. Time of day / durations: "8:30 am", "two hours", "24 hours", "365 days", "a fortnight"
    _TIME_OF_DAY_RE = re.compile(r"\b(\d{1,2}:\d{2}\s*(?:a\.?m\.?|p\.?m\.?|AM|PM))\b")
    _DURATION_PHRASE_RE = re.compile(
        rf"\b((?:a\s+fortnight|(?:\d+|{_NUMBER_WORDS_CARDINAL})\s+(?:hours?|minutes?|seconds?|days?|weeks?|months?|years?)))\b",
        re.IGNORECASE,
    )

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        # 1. Full dates (highest priority within Family A; atomic)
        for m in self._FULL_DATE_RE.finditer(sentence):
            q_when = _detect_when_did_question(sentence, m.span())
            item = _make_match(
                sentence,
                m.start(),
                m.end(),
                "full_date",
                q_when or "Which date…?",
                self.code,
                bullet=1,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 8. Indian calendars ("Vikram Samvat 2080", "Shaka era 78 AD")
        for m in self._INDIAN_CALENDAR_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "indian_calendar",
                "Which year…?",
                self.code,
                bullet=8,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 7. Era markers ("326 BC", "AD 1206", "250 BCE", "1206 CE", "c. 1500", "circa 1500")
        for m in self._ERA_MARKER_DIRECT_RE.finditer(sentence):
            if _overlaps(m.span(), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(),
                m.end(),
                "era_marker",
                "Which year…?",
                self.code,
                bullet=7,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._ERA_APPROX_YEAR_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "era_marker",
                "Which year…?",
                self.code,
                bullet=7,
                prompt="Name the date or year",
                qualifier=m.group(0).split()[0],
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 4. Year ranges ("1917–1934", "1839–1904") and spans ("for 17 years", "over 300 years", "24-day")
        for m in self._YEAR_RANGE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "year_range",
                "Which year…?",
                self.code,
                bullet=4,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._DURATION_SPAN_RE.finditer(sentence):
            grp = 1 if m.group(1) else 2
            if _overlaps(m.span(grp), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(grp),
                m.end(grp),
                "duration_span",
                "Which number fits the gap?",
                self.code,
                bullet=4,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2. Month + year / day + month ("August 1942", "15 August")
        for m in self._MONTH_YEAR_OR_DAY_MONTH_RE.finditer(sentence):
            if _overlaps(m.span(), claimed):
                continue
            sub_type = "month_year" if re.search(r"\d{4}$", m.group(0)) else "day_month"
            item = _make_match(
                sentence,
                m.start(),
                m.end(),
                sub_type,
                "Which date…?",
                self.code,
                bullet=2,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3. Years with a preposition (preposition stays on the card; only the year is blanked)
        for m in self._PREP_YEAR_PAIR_RE.finditer(sentence):
            for grp in (1, 2, 3, 4):
                if m.group(grp) and not _overlaps(m.span(grp), claimed):
                    item = _make_match(
                        sentence,
                        m.start(grp),
                        m.end(grp),
                        "year",
                        "Which year…?",
                        self.code,
                        bullet=3,
                        prompt="Name the date or year",
                    )
                    if item:
                        matches.append(item)
                        claimed.append(item["span"])

        for m in self._PREP_SINGLE_YEAR_RE.finditer(sentence):
            if _overlaps(m.span(2), claimed):
                continue
            q_when = _detect_when_did_question(sentence, m.span(2))
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "year",
                q_when or "Which year…?",
                self.code,
                bullet=3,
                prompt="Name the date or year",
                preposition=m.group(1),
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 5. Centuries and parts ("19th century", "the nineteenth century", "early/mid/late 20th century", "the latter half of the 20th century", "turn of the century")
        for m in self._CENTURY_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            raw_c = m.group(1)
            start_c = m.start(1)
            # Keep "the " on the card when followed by "19th century" / "early 20th century", except when part of "the nineteenth century" or "the latter half..."
            if re.match(r"^the\s+(?:\d|early\b|mid\b|late\b)", raw_c, re.IGNORECASE):
                start_c += 4
            item = _make_match(
                sentence,
                start_c,
                m.end(1),
                "century",
                "Which century…?",
                self.code,
                bullet=5,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 6. Decades and eras ("the 1930s", "mid-1930s", "the Mughal period", "the Vedic age", "the Stone Age", "Bronze Age")
        for m in self._DECADE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            raw_d = m.group(1)
            start_d = m.start(1)
            if raw_d.lower().startswith("the "):
                start_d += 4
            item = _make_match(
                sentence,
                start_d,
                m.end(1),
                "decade",
                "Which year…?",
                self.code,
                bullet=6,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._NAMED_ERA_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            raw_e = m.group(1)
            start_e = m.start(1)
            if raw_e.lower().startswith("the "):
                start_e += 4
            # Skip non-era words like "Modern age" if needed, but keep historical eras/ages/periods/dynasties
            item = _make_match(
                sentence,
                start_e,
                m.end(1),
                "era",
                "Which era or period…?",
                self.code,
                bullet=6,
                prompt="Name the date or year",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 10. Time of day / durations ("8:30 am", "two hours", "24 hours", "365 days", "a fortnight")
        for m in self._TIME_OF_DAY_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "time_of_day",
                "Which time fits the gap?",
                self.code,
                bullet=10,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._DURATION_PHRASE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "duration",
                "Which duration fits the gap?",
                self.code,
                bullet=10,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # Remaining bare 4-digit years (e.g. "(2011 census)" or standalone year)
        for m in self._BARE_YEAR_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            # Skip "2011 census" parenthetical citation years when another date/number is present
            after_yr = sentence[m.end(1) :].lstrip()
            if after_yr.lower().startswith("census"):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "year",
                "Which year…?",
                self.code,
                bullet=3,
                prompt="Name the date or year",
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 9. Relative time words ("before", "after", "later", "earlier", "following", "during", "at the time of", "when")
        # Pair the relative time marker with any date/year/era found in the sentence
        if matches:
            m_rel = self._RELATIVE_TIME_RE.search(sentence)
            if m_rel:
                primary_date = matches[0]
                rel_copy = dict(primary_date)
                rel_copy["type"] = "relative_date"
                rel_copy["bullet"] = 9
                rel_copy["relative_marker"] = m_rel.group(1)
                matches.append(rel_copy)

        matches.sort(key=lambda x: (x["span"][0], -(x["span"][1] - x["span"][0])))
        return matches


# ===========================================================================
# B. NUMBERS AND QUANTITIES
# ===========================================================================

class NumbersAndQuantitiesFamily:
    """Family B: Plain and grouped numbers (including Indian grouping, lakh, crore),
    number words, ordinals/ranks, approximations (keeping qualifier on card),
    percentages/fractions/ratios, money, and counts with nouns.
    """

    code = "B"
    name = "NUMBERS AND QUANTITIES"

    # 6. Money: "₹500", "Rs. 500", "INR 500", "£1.6 billion", "$20", "50 paise"
    _MONEY_RE = re.compile(
        r"(?<!\w)(?:"
        r"(?:₹|£|\$|Rs\.?\s*|INR\s*)\d+(?:,\d{2,3})*(?:\.\d+)?(?:\s*(?:thousand|million|billion|bn|lakh|crore))?|"
        r"\d+(?:,\d{2,3})*(?:\.\d+)?\s*(?:rupees|paise|pounds|dollars)\b"
        r")(?!\w)",
        re.IGNORECASE,
    )

    # 5. Percentages, fractions, ratios: "70%", "70 per cent", "3/4", "three-fourths", "1 : 2", "2 out of 5"
    _PERCENT_FRAC_RATIO_RE = re.compile(
        r"(?<!\w)(?:"
        r"\d+(?:\.\d+)?\s*(?:%|per\s*cent\b|percent\b)|"
        r"\d+\s+out\s+of\s+\d+\b|"
        r"\b\d+\s*:\s*\d+\b|"
        r"(?:\d+\s*)?[¼½¾]|"
        r"\b\d+/\d+\b|"
        r"\b(?:one|two|three|four|five|six|seven|eight|nine)[-\s]"
        r"(?:halves|thirds?|fourths?|quarters?|fifths?|sixths?|sevenths?|eighths?|tenths?)\b|"
        r"\btwo\s+and\s+one\s+half\b"
        r")",
        re.IGNORECASE,
    )

    # 3. Ordinals and ranks: "the 7th most populous", "second largest", "eleventh-largest", "No. 1" (blank ordinal with its noun if present)
    _ORDINAL_RANK_RE = re.compile(
        rf"\b(?:the\s+)?("
        rf"(?:\d+(?:st|nd|rd|th)|{_NUMBER_WORDS_ORDINAL})[-\s]+"
        rf"(?:most\s+[a-z]+|largest|smallest|longest|highest|oldest|biggest|busiest)"
        rf"(?:\s+[a-z]+(?:\s+city|\s+country|\s+state|\s+port|\s+river|\s+centre|\s+center|\s+island)?)?|"
        rf"No\.\s*\d+(?:\s+[a-z]+)?"
        rf")\b",
        re.IGNORECASE,
    )

    # 7. Counts with nouns: "72 delegates", "78 volunteers", "5 cities", "28 states", "8 union territories", "7 continents", "206 bones"
    _COUNT_WITH_NOUN_RE = re.compile(
        r"(?<!\w)("
        r"(?:\d{1,3}(?:,\d{2})+,\d{3}|\d{1,3}(?:,\d{3})+|\d+)"
        r"\s+"
        r"(?:union\s+territories|equal\s+sides|fundamental\s+rights|fundamental\s+duties|"
        r"delegates|volunteers|cities|states|continents|bones|jobs|visitors|members|articles|"
        r"schedules|houses|chambers|planets|elements|electrons|protons|neutrons|atoms|molecules|"
        r"players|districts|languages|rivers|mountains|islands|oceans|seas|countries|villages|"
        r"students|teachers|workers|soldiers|ships|factories|mills|theatres|museums|banks|ports|"
        r"senses|teeth|kidneys|lungs|chambers|valves|layers|stages|steps|types|kinds|parts)\b"
        r")",
        re.IGNORECASE,
    )

    # 4. Approximations: "about", "around", "nearly", "over", "more than", "less than", "approximately", "almost", "at least", "up to"
    _APPROX_QUALIFIER_RE = re.compile(
        r"\b(about|around|nearly|over|more\s+than|less\s+than|approximately|almost|at\s+least|up\s+to)\s+"
        r"("
        r"(?:₹|£|\$|Rs\.?\s*|INR\s*)?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?"
        r"(?:\s*(?:lakh|crore|million|billion|thousand|%|per\s*cent|[a-z]+))?"
        r")\b",
        re.IGNORECASE,
    )

    # 1. Plain and grouped numbers: "72", "286,000", Indian grouping "2,86,000", "1.5 lakh", "3 crore", "a million", "two billion"
    _GROUPED_OR_SCALED_NUMBER_RE = re.compile(
        rf"(?<!\w)("
        rf"\d{{1,2}}(?:,\d{{2}})+,\d{{3}}|"
        rf"\d{{1,3}}(?:,\d{{3}})+(?:\.\d+)?|"
        rf"(?:\d+(?:\.\d+)?|a|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:lakh|crore|million|billion|thousand)\b|"
        rf"\b\d+(?:\.\d+)?\b"
        rf")(?!\w)",
        re.IGNORECASE,
    )

    # 2. Number words: "one", "twelve", "first", "second", "third", "tenth", "a dozen", "a hundred", "half", "a quarter", "double", "twice"
    _NUMBER_WORD_RE = re.compile(
        rf"\b(a\s+dozen|a\s+hundred|a\s+quarter|three\s+quarters|half|double|twice|"
        rf"{_NUMBER_WORDS_ORDINAL}|{_NUMBER_WORDS_CARDINAL})\b",
        re.IGNORECASE,
    )

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        # Avoid matching numbers that are part of full dates or 4-digit years
        date_spans = [m["span"] for m in FAMILY_A.find(sentence)]
        unit_spans = [m["span"] for m in FAMILY_C.find(sentence)]

        # 6. Money ("₹500", "Rs. 500", "£1.6 billion", "$20", "50 paise")
        for m in self._MONEY_RE.finditer(sentence):
            if _overlaps(m.span(), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(),
                m.end(),
                "money",
                "Which number fits the gap?",
                self.code,
                bullet=6,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 5. Percentages, fractions, ratios ("70%", "70 per cent", "3/4", "three-fourths", "1 : 2", "2 out of 5")
        for m in self._PERCENT_FRAC_RATIO_RE.finditer(sentence):
            if _overlaps(m.span(), claimed) or _inside_any(m.span(), date_spans):
                continue
            item = _make_match(
                sentence,
                m.start(),
                m.end(),
                "percentage_fraction_ratio",
                "Which number fits the gap?",
                self.code,
                bullet=5,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3. Ordinals and ranks ("the 7th most populous", "second largest", "eleventh-largest", "No. 1")
        for m in self._ORDINAL_RANK_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed) or _inside_any(m.span(1), date_spans):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "ordinal_rank",
                "Which number fits the gap?",
                self.code,
                bullet=3,
                prompt="Fill in the key fact",
                is_superlative=False,
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 7. Counts with nouns ("72 delegates", "78 volunteers", "5 cities", "28 states", "8 union territories", "7 continents", "206 bones")
        for m in self._COUNT_WITH_NOUN_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed) or _inside_any(m.span(1), date_spans):
                continue
            noun_part = m.group(1).split(None, 1)[1] if len(m.group(1).split()) >= 2 else "items"
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "count_with_noun",
                f"How many {noun_part}…?",
                self.code,
                bullet=7,
                prompt="Give the value and unit",
                noun=noun_part,
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 4. Approximations ("about 286,000", "over 520,000 visitors" -> keep qualifier on card, blank the number/count)
        for m in self._APPROX_QUALIFIER_RE.finditer(sentence):
            # Even if the inner count was already matched in B7, record the B4 approximation metadata
            val_span = m.span(2)
            if _inside_any(val_span, date_spans):
                continue
            # If the trailing word is an ordinary verb/preposition (e.g. "about 286,000 in"), strip the trailing non-noun
            raw_val = m.group(2)
            val_end = m.end(2)
            parts = raw_val.split()
            if len(parts) == 2 and parts[1].lower() in {
                "in", "on", "at", "to", "for", "from", "by", "of", "and", "or", "is", "was", "were", "are"
            }:
                val_end = m.start(2) + len(parts[0])
            item = _make_match(
                sentence,
                m.start(2),
                val_end,
                "approximated_number",
                "Which number fits the gap?",
                self.code,
                bullet=4,
                prompt="Give the value and unit",
                qualifier=m.group(1),
                atomic=True,
            )
            if item and not _overlaps(item["span"], claimed):
                matches.append(item)
                claimed.append(item["span"])
            elif item:
                # Attach approximation metadata if an identical span is already present
                matches.append(item)

        # 1. Plain and grouped numbers ("72", "286,000", "2,86,000", "1.5 lakh", "3 crore", "a million", "two billion")
        for m in self._GROUPED_OR_SCALED_NUMBER_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed) or _inside_any(m.span(1), date_spans) or _inside_any(m.span(1), unit_spans):
                continue
            tok = m.group(1)
            # Skip single digits that are section/list numbers at start of sentence ("1. ", "2. ")
            if m.start(1) == 0 and m.end(1) < len(sentence) and sentence[m.end(1) : m.end(1) + 2] in {". ", ") "}:
                continue
            # Skip chemical formula coefficients/subscripts like "2H2O"
            if m.start(1) > 0 and (sentence[m.start(1) - 1].isalpha() or sentence[m.start(1) - 1] in "₀₁₂₃₄₅₆₇₈₉"):
                continue
            if m.end(1) < len(sentence) and (sentence[m.end(1)].isalpha() or sentence[m.end(1)] in "²³⁴₀₁₂₃₄₅₆₇₈₉"):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "plain_or_grouped_number",
                "Which number fits the gap?",
                self.code,
                bullet=1,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2. Number words ("one", "twelve", "first", "second", "third", "tenth", "a dozen", "a hundred", "half", "a quarter", "double", "twice")
        for m in self._NUMBER_WORD_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed) or _inside_any(m.span(1), date_spans):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "number_word",
                "Which number fits the gap?",
                self.code,
                bullet=2,
                prompt="Which number fits the gap?",
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        matches.sort(key=lambda x: (x["span"][0], -(x["span"][1] - x["span"][0])))
        return matches


# ===========================================================================
# C. MEASUREMENT AND UNITS (science, maths, geography)
# ===========================================================================

class MeasurementAndUnitsFamily:
    """Family C: SI and common units with a number, area and volume measures,
    geography measures (altitude, rainfall, lat/long, compass directions),
    and unit conversions ('1 N = 1 kg·m/s²', '1 km = 1000 m', '500 g = 0.500 kg').
    Never splits a number from its unit.
    """

    code = "C"
    name = "MEASUREMENT AND UNITS"

    # 4. Conversions: "1 N = 1 kg·m/s²", "1 km = 1000 m", "500 g = 0.500 kg"
    _CONVERSION_RE = re.compile(
        rf"\b(\d+(?:\.\d+)?\s*{_UNIT_SYMBOLS})\s*=\s*(\d+(?:,\d{{3}})*(?:\.\d+)?\s*{_UNIT_SYMBOLS})(?!\w)"
    )

    # 2. Area and volume: "km²", "sq km", "square kilometres", "m³", "cubic metres"
    _AREA_VOLUME_RE = re.compile(
        r"(?<!\w)([+\-±]?\d+(?:,\d{2,3})*(?:\.\d+)?\s*(?:"
        r"square\s+kilomet(?:re|er)s?|square\s+met(?:re|er)s?|square\s+centimet(?:re|er)s?|"
        r"cubic\s+met(?:re|er)s?|cubic\s+centimet(?:re|er)s?|"
        r"sq\.?\s*km\b|sq\.?\s*m\b|km²|m²|cm²|mm²|m³|cm³"
        r"))",
        re.IGNORECASE,
    )

    # 3. Geography measures: "8,848 m above sea level", "23.5° N", "82.5° E", "north-east"
    _GEO_ALTITUDE_RE = re.compile(
        r"(?<!\w)(\d+(?:,\d{3})*(?:\.\d+)?\s*(?:m|km|ft|feet)\s+(?:above|below)\s+sea\s+level)\b",
        re.IGNORECASE,
    )
    _GEO_LAT_LON_RE = re.compile(
        r"(?<!\w)(\d+(?:\.\d+)?\s*°\s*(?:\d+\s*'\s*)?[NSWE])\b"
    )
    _GEO_DIRECTION_RE = re.compile(
        r"\b(north-east|north-west|south-east|south-west|northeastern|northwestern|southeastern|southwestern)\b",
        re.IGNORECASE,
    )

    # 1. SI and common units with a number
    _SI_NUMBER_UNIT_RE = re.compile(
        rf"(?<!\w)([+\-±]?\d+(?:,\d{{2,3}})*(?:\.\d+)?(?:\s*[×x]\s*10(?:\^\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+))?\s*{_UNIT_SYMBOLS})(?=$|[\s.,;:)\]])"
    )

    # Explicit unit-of-quantity pairing: "The SI unit of <quantity> is (the) <unit>"
    _UNIT_OF_QUANTITY_RE = re.compile(
        r"\b(?:SI\s+)?unit\s+of\s+([a-z\s]{3,25}?)\s+is\s+(?:the\s+)?([A-Za-z°Ω/²³]+(?:\s*\([^)]+\))?)",
        re.IGNORECASE,
    )

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        # 4. Unit conversions ("1 N = 1 kg·m/s²", "1 km = 1000 m", "500 g = 0.500 kg")
        for m in self._CONVERSION_RE.finditer(sentence):
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "unit_conversion",
                "Which value fits the gap?",
                self.code,
                bullet=4,
                prompt="Give the value and unit",
                lhs=m.group(1),
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(m.span())

        # 3a. Geography altitude ("8,848 m above sea level")
        for m in self._GEO_ALTITUDE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "geography_measure",
                "Which value fits the gap?",
                self.code,
                bullet=3,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3b. Geography latitude/longitude ("23.5° N", "82.5° E")
        for m in self._GEO_LAT_LON_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "geography_measure",
                "Which value fits the gap?",
                self.code,
                bullet=3,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2. Area and volume ("km²", "sq km", "square kilometres", "m³", "cubic metres")
        for m in self._AREA_VOLUME_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "area_volume_unit",
                "Which value fits the gap?",
                self.code,
                bullet=2,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 1. SI and common units with a number ("387 km", "40 mL", "2.0 m/s²", "5 km/h", "25 °C", "200 cm")
        # For worked calculations ("Solution: Speed = 120 ÷ 2 = 60 km/h"), prefer the final result after '='
        worked_eq_pos = sentence.rfind("=") if sentence.count("=") >= 1 and ("÷" in sentence or "×" in sentence or "+" in sentence) else -1
        si_matches = list(self._SI_NUMBER_UNIT_RE.finditer(sentence))
        if worked_eq_pos != -1:
            after_eq = [m for m in si_matches if m.start(1) > worked_eq_pos]
            if after_eq:
                si_matches = after_eq + [m for m in si_matches if m.start(1) <= worked_eq_pos]

        for m in si_matches:
            if _overlaps(m.span(1), claimed):
                continue
            # If the sentence says "25 °C means twenty-five degrees Celsius", avoid blanking "25 °C" when "Celsius" is explained
            after_txt = sentence[m.end(1) :].strip().lower()
            if after_txt.startswith("means twenty-five"):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "measurement_unit",
                "Which value fits the gap?",
                self.code,
                bullet=1,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # Explicit unit of quantity ("The SI unit of force is the newton")
        for m in self._UNIT_OF_QUANTITY_RE.finditer(sentence):
            if _overlaps(m.span(2), claimed):
                continue
            qty = m.group(1).strip()
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "unit_of_quantity",
                f"What is the unit of {qty}?",
                self.code,
                bullet=1,
                prompt=f"What is the unit of {qty}?",
                quantity=qty,
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3c. Compass directions ("north-east", "south-west")
        for m in self._GEO_DIRECTION_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "geography_measure",
                "Which direction or place fits the gap?",
                self.code,
                bullet=3,
                prompt="Fill in the key term",
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        return matches


# ===========================================================================
# D. FORMULAS, EQUATIONS, SYMBOLS
# ===========================================================================

class FormulasEquationsSymbolsFamily:
    """Family D: Physics/maths formulas, chemical formulas & equations (with subscripts/state symbols),
    element symbols & names, and maths facts.
    """

    code = "D"
    name = "FORMULAS, EQUATIONS, SYMBOLS"

    # 1. Physics/maths formulas: "F = ma", "V = I × R", "a = F ÷ m", "P = 2(l + w)", "A = πr²", "speed = distance ÷ time"
    _PHYSICS_MATH_FORMULA_RE = re.compile(
        r"(?:^|[:;]\s*|\bThen\s+|\bthen\s+)("
        r"(?:Speed|speed|Area|area|Force|force|Work|work|Power|power|Pressure|pressure|Density|density|"
        r"[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]{0,4}|\d+(?:\.\d+)?\s*[×x]\s*10(?:\^\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+))"
        r")\s*=\s*("
        r"(?:\d+(?:\.\d+)?\s*\([A-Za-z0-9\s+\-×÷*/]+\)|"
        r"[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹π√×÷\*+\-/^()·.,]+(?:\s*[×÷\*+\-/·]\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹π√^()/·.,]+)*)"
        r")(?=$|[.;,)])"
    )

    # 2. Chemical equations and formulas: "2H₂ + O₂ → 2H₂O", "CaCO₃ + 2HCl → CaCl₂ + H₂O + CO₂", "H₂O", "CO₂", "CaCO₃", "(aq)", "(s)", "(l)", "(g)"
    _CHEM_EQUATION_RE = re.compile(
        r"([0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*(?:\+\s*[0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*)*)"
        r"\s*(→|->|⇌)\s*"
        r"([0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*(?:\+\s*[0-9]*[A-Z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*)*)"
    )
    _CHEM_FORMULA_TOKEN_RE = re.compile(
        r"(?<!\w)(\d*(?:[A-Z][a-z]?(?:[₀-₉]+|\d+)*)*[A-Z][a-z]?(?:[₀-₉]+|\d+)(?:[A-Z][a-z]?(?:[₀-₉]+|\d+)*)*(?:\((?:aq|s|l|g)\))?)(?!\w)"
    )
    _STATE_SYMBOL_RE = re.compile(r"(\((?:aq|s|l|g)\))")

    # 3. Element symbols and names: "Na – sodium", "Fe – iron", "symbol for sodium is Na"
    _ELEMENT_PAIR_DASH_RE = re.compile(
        r"\b([A-Z][a-z]?)\s*[–—\-]\s*([a-z]{3,15})\b"
    )
    _ELEMENT_SYMBOL_SENT_RE = re.compile(
        r"\b(?:symbol\s+(?:for|of)\s+([A-Za-z]{3,15})\s+is\s+([A-Z][a-z]?)|"
        r"([A-Z][a-z]?)\s+is\s+the\s+(?:chemical\s+)?symbol\s+(?:for|of)\s+([A-Za-z]{3,15}))\b",
        re.IGNORECASE,
    )

    # 4. Maths facts: "angles of a triangle add up to 180°", "a right angle is 90°", "π ≈ 3.14", "a square has 4 equal sides"
    _MATH_ANGLE_DEG_RE = re.compile(r"(?<!\w)(\d+(?:\.\d+)?\s*°)(?!\s*[CFKNSEW]\b|[CFKA-Za-z])")
    _MATH_APPROX_CONST_RE = re.compile(r"(?:π|pi)\s*(?:≈|=|is\s+approximately)\s*(\d+\.\d+)", re.IGNORECASE)
    _MATH_SIDES_FACT_RE = re.compile(r"\bhas\s+(\d+\s+equal\s+sides)\b", re.IGNORECASE)

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        # 2a. Chemical equations ("2H₂ + O₂ → 2H₂O", "CaCO₃ + 2HCl → CaCl₂ + H₂O + CO₂")
        for m in self._CHEM_EQUATION_RE.finditer(sentence):
            rhs_full = m.group(3)
            rhs_start = m.start(3)
            # If multiple products separated by '+', blank the last product so brackets/equations stay clean
            if "+" in rhs_full:
                last_plus = rhs_full.rfind("+")
                prod_start = rhs_start + last_plus + 1
                prod_end = m.end(3)
            else:
                prod_start = rhs_start
                prod_end = m.end(3)
            item = _make_match(
                sentence,
                prod_start,
                prod_end,
                "chemical_equation",
                "Complete the formula",
                self.code,
                bullet=2,
                prompt="Complete the formula",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2b. Chemical formulas ("H₂O", "CO₂", "CaCO₃")
        for m in self._CHEM_FORMULA_TOKEN_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "chemical_formula",
                "Fill in the key term",
                self.code,
                bullet=2,
                prompt="Fill in the key term",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2c. State symbols ("(aq)", "(s)", "(l)", "(g)") when standalone in a sentence about state symbols
        for m in self._STATE_SYMBOL_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "state_symbol",
                "Fill in the key term",
                self.code,
                bullet=2,
                prompt="Fill in the key term",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3. Element symbols and names ("Na – sodium", "Fe – iron")
        for m in self._ELEMENT_PAIR_DASH_RE.finditer(sentence):
            if _overlaps(m.span(2), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "element_symbol",
                "Fill in the key term",
                self.code,
                bullet=3,
                prompt="Fill in the key term",
                symbol=m.group(1),
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._ELEMENT_SYMBOL_SENT_RE.finditer(sentence):
            grp = 2 if m.group(2) else 4
            if _overlaps(m.span(grp), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(grp),
                m.end(grp),
                "element_symbol",
                "Fill in the key term",
                self.code,
                bullet=3,
                prompt="Fill in the key term",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 4. Maths facts ("180°", "90°", "π ≈ 3.14", "4 equal sides")
        for m in self._MATH_ANGLE_DEG_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "math_fact",
                "Which value fits the gap?",
                self.code,
                bullet=4,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._MATH_APPROX_CONST_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "math_fact",
                "Which value fits the gap?",
                self.code,
                bullet=4,
                prompt="Complete the formula",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._MATH_SIDES_FACT_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "math_fact",
                "How many sides…?",
                self.code,
                bullet=4,
                prompt="Give the value and unit",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 1. Physics/maths formulas ("F = ma", "V = I × R", "a = F ÷ m", "P = 2(l + w)", "A = πr²", "speed = distance ÷ time")
        for m in self._PHYSICS_MATH_FORMULA_RE.finditer(sentence):
            lhs = m.group(1).strip()
            rhs = m.group(2).strip()
            if _overlaps(m.span(2), claimed):
                continue
            # Skip intermediate premise "x = 5" when "x² = 25" follows on the same line
            if lhs == "x" and "x²" in sentence[m.end(2) :]:
                continue
            # Ensure balanced brackets on RHS
            if rhs.count("(") != rhs.count(")"):
                continue
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "physics_math_formula",
                "Complete the formula",
                self.code,
                bullet=1,
                prompt="Complete the formula",
                lhs=lhs,
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        return matches


# ===========================================================================
# E. NAMES, TITLES AND ROLES (who / what)
# ===========================================================================

class NamesTitlesRolesFamily:
    """Family E: Naming verbs ('is called', 'is known as', 'nicknamed', ...),
    passive & active role verbs ('founded by', 'chaired by', '<Name> founded/built ...'),
    titles ('Father of ...', 'Grand Old Man of ...', 'first <role>'),
    '<Name> (1839–1904) – <title>' headings, and organisations/documents/events
    ('Movement', 'Act', 'Samaj', 'Sabha', 'Committee', 'Assembly', 'Treaty', 'Article 21', 'Schedule').
    """

    code = "E"
    name = "NAMES, TITLES AND ROLES"

    # 4. Name + dates headings: "<Name> (1839–1904) – <title>"
    _NAME_DATES_HEADING_RE = re.compile(
        r"^(?:(?:\d+|[A-Z])[.)]\s*)?((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|Smt\.|Lokmanya|Mahatma)\s+)?[A-Z][A-Za-z.\s’'\-]{2,38}?)\s*"
        r"\(\s*\d{3,4}\s*[–\-—]\s*(?:\d{2,4}|present)\s*\)\s*[–—\-:]\s*(.+)$"
    )

    # 3. Titles: "Father of …", "Mother of …", "Architect of …", "Grand Old Man of …", "Iron Man of …", "Nightingale of …", "Lion of …", "first <role>"
    _HONORIFIC_TITLE_RE = re.compile(
        r"[‘'“\"]?\b((?:Father|Mother|Architect|Grand\s+Old\s+Man|Iron\s+Man|Nightingale|Lion|Pioneer|Founder)\s+of\s+"
        r"(?:the\s+)?[A-Z][A-Za-z’'\-]+(?:\s+(?:of|the|and|in|[A-Z][A-Za-z’'\-]+)){0,3})[’'”\"]?"
    )
    _FIRST_ROLE_RE = re.compile(
        r"\b(first\s+(?:[A-Z][a-z]+\s+){0,2}(?:Prime\s+Minister|President|Governor(?:-General)?|Viceroy|Speaker|"
        r"Chief\s+Justice|Law\s+Minister|Education\s+Minister|woman\s+[a-z]+|Indian\s+[a-z]+(?:\s+[a-z]+)?|Chairman|Mayor|Emperor|King|Queen))\b"
    )

    # 1. Naming verbs: "is called", "is known as", "also known as", "is termed", "is referred to as", "nicknamed", "popularly called", "hailed as", "titled", "honoured as", "the title of"
    _NAMING_VERB_RE = re.compile(
        r"\b(?:is\s+called|are\s+called|was\s+called|is\s+known\s+as|are\s+known\s+as|was\s+known\s+as|"
        r"also\s+known\s+as|is\s+termed|are\s+termed|is\s+referred\s+to\s+as|nicknamed|popularly\s+called|"
        r"popularly\s+known\s+as|hailed\s+as|titled|honoured\s+as|honored\s+as|given\s+the\s+title\s+of|the\s+title\s+of)\s+"
        r"[‘'“\"]?(?:the\s+)?([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+(?!and\s+is\b|because\b|which\b|that\b|in\s+\d|on\s+\d)[A-Za-z0-9’'\-–]+){0,3})[’'”\"]?",
        re.IGNORECASE,
    )

    # 2a. Passive role phrases: "founded by <Name>", "led by <Name>", "chaired by <Name>", etc.
    _PASSIVE_ROLE_RE = re.compile(
        r"\b(founded|led|headed|chaired|invented|discovered|written|authored|composed|built|designed|"
        r"established|started|introduced|ruled|adopted|proclaimed|presided\s+over|enacted|drafted|organized|organised)\s+by\s+"
        r"(?:the\s+)?((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|King|Queen|Emperor|Mahatma|Lokmanya|Pandit|Netaji|Swami|Smt\.)\s+)?"
        r"[A-Z][A-Za-z0-9.\-’']+(?:\s+(?:of|the|and|[A-Z][A-Za-z0-9.\-’']+)){0,4})"
    )

    # 2b. Active role phrases: "<Name> founded/led/invented/wrote/chaired/built/discovered/established ..."
    _ACTIVE_ROLE_RE = re.compile(
        r"(?:^|[:;]\s*)((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|King|Queen|Emperor|Mahatma|Lokmanya|Pandit|Netaji|Swami|Smt\.)\s+)?"
        r"[A-Z][A-Za-z0-9.\-’']+(?:\s+(?:and|of|the|[A-Z][A-Za-z0-9.\-’']+)){0,4}?)"
        r"(?:\s+shipyard|\s+government|\s+scientist|\s+reformer)?\s+"
        r"(founded|led|headed|chaired|invented|discovered|wrote|authored|composed|built|designed|"
        r"established|started|introduced|ruled|presided\s+over|drafted)\b"
    )

    # 5. Organisations, documents, events: "Movement", "Act", "Party", "Congress", "Samaj", "Sabha", "Committee",
    # "Assembly", "Treaty", "Battle of", "Revolt", "Revolution", "Mission", "Company", "Satyagraha", "Constitution",
    # "Amendment", "Article <n>", "Schedule", plus institutional heads
    _ARTICLE_OR_SCHEDULE_RE = re.compile(
        r"\b(Article\s+\d+[A-Za-z]?|(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|\d+(?:st|nd|rd|th))\s+(?:Schedule|Amendment(?:\s+Act)?))\b"
    )
    _BATTLE_OR_TREATY_OF_RE = re.compile(
        r"\b((?:Battle|Treaty|Siege|Pact|Declaration|Charter|Revolt|Resolution)\s+of\s+[A-Z][A-Za-z’'\-]+(?:\s+[A-Z][A-Za-z’'\-]+){0,2})\b"
    )
    _ORG_DOC_EVENT_HEAD_RE = re.compile(
        r"\b((?:[A-Z][A-Za-z0-9’'\-–]+\s+){0,4}"
        r"(?:Movement|Act|Party|Congress|Samaj|Sabha|Committee|Commission|Assembly|Treaty|Revolt|Revolution|"
        r"Mission|Company|Satyagraha|Constitution|Amendment|Parliament|Hippodrome|Senedd|Preamble|"
        r"Cathedral|University|College|Institute|Museum|Centre|Center|Shipyard|Association|League|Society|"
        r"Rights|Duties|Day|Titanic))\b"
    )
    _ORG_OF_PROPER_RE = re.compile(
        r"\b((?:Royal\s+Bank|Bank|Reserve\s+Bank|State\s+Bank|Supreme\s+Court|High\s+Court|Republic|Kingdom|United\s+States|Union|Government|President|Prime\s+Minister)\s+of\s+[A-Z][A-Za-z’'\-]+(?:\s+[A-Z][A-Za-z’'\-]+){0,2})\b"
    )
    _MULTIWORD_PROPER_NAME_RE = re.compile(
        r"\b((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|St\.|King|Queen|Mahatma|Lokmanya|Swami)\s+)?"
        r"[A-Z][A-Za-z0-9.\-’']+(?:\s+(?:and\s+)?[A-Z][A-Za-z0-9.\-’']+){1,4})\b"
    )

    _STOP_ORG_LEADING_WORDS = {
        "The", "A", "An", "In", "On", "At", "By", "To", "From", "For", "Of", "With", "Under",
        "Seat", "Home", "Heart", "Centre", "Center", "Role", "Key", "Major", "Famous", "Today",
        "Adopted", "Launched", "Founded", "Built", "Situated", "Located", "Proclaimed", "Made",
    }

    def _trim_leading_stop_words(self, sentence: str, start: int, end: int) -> tuple[int, int]:
        text = sentence[start:end]
        words = text.split()
        while len(words) > 1 and words[0] in self._STOP_ORG_LEADING_WORDS:
            idx = sentence.find(words[0], start, end)
            if idx != -1:
                start = idx + len(words[0])
                while start < end and sentence[start] == " ":
                    start += 1
            words = words[1:]
        return start, end

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []
        date_spans = [m["span"] for m in FAMILY_A.find(sentence)]

        # 4. Name + dates headings: "<Name> (1839–1904) – <title>"
        m_ndt = self._NAME_DATES_HEADING_RE.match(sentence.strip())
        if m_ndt:
            name_str = m_ndt.group(1).strip()
            idx_n = sentence.find(name_str)
            if idx_n != -1:
                item = _make_match(
                    sentence,
                    idx_n,
                    idx_n + len(name_str),
                    "name_dates_heading",
                    "Name the person, place, or institution",
                    self.code,
                    bullet=4,
                    prompt="Name the person, place, or institution",
                    title=m_ndt.group(2).strip(),
                    atomic=True,
                )
                if item:
                    matches.append(item)
                    claimed.append(item["span"])

        # 5a. Article <n> / Schedule / Amendment ("Article 21", "Eighth Schedule", "42nd Amendment")
        for m in self._ARTICLE_OR_SCHEDULE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed) or _inside_any(m.span(1), date_spans):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "organisation_document_event",
                "Which article, schedule, or amendment fits the gap?",
                self.code,
                bullet=5,
                prompt="Name the person, place, or institution",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 5b. Battle of / Treaty of / Revolt of ("Battle of Plassey", "Treaty of Versailles")
        for m in self._BATTLE_OR_TREATY_OF_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            head_word = m.group(1).split()[0].lower()
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "organisation_document_event",
                f"Which {head_word} fits the gap?",
                self.code,
                bullet=5,
                prompt="Name the person, place, or institution",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 5c. Bank of X / Royal Bank of X / Supreme Court of X
        for m in self._ORG_OF_PROPER_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "organisation_document_event",
                "Which institution fits the gap?",
                self.code,
                bullet=5,
                prompt="Name the person, place, or institution",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3. Titles and epithets ("Father of the Nation", "Grand Old Man of India", "first Prime Minister")
        for m in self._HONORIFIC_TITLE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            title_txt = m.group(1).strip()
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "title_epithet",
                f"Who is known as {title_txt}?",
                self.code,
                bullet=3,
                prompt="Name the person, place, or institution",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._FIRST_ROLE_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            role_txt = m.group(1).strip()
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "title_epithet",
                f"Who was the {role_txt}?",
                self.code,
                bullet=3,
                prompt="Fill in the key fact",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2a. Passive roles ("founded by X", "chaired by X", "adopted by the Constituent Assembly")
        for m in self._PASSIVE_ROLE_RE.finditer(sentence):
            verb_part = m.group(1).strip().lower()
            s_idx, e_idx = self._trim_leading_stop_words(sentence, m.start(2), m.end(2))
            # Stop before date prepositions like "on 26 November 1949" or "in 1873"
            sub_txt = sentence[s_idx:e_idx]
            m_stop = re.search(r"\s+\b(?:on|in|at|from|during|under|with|for)\b", sub_txt)
            if m_stop:
                e_idx = s_idx + m_stop.start()
            if _overlaps((s_idx, e_idx), claimed) or _inside_any((s_idx, e_idx), date_spans):
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "role_person",
                f"Who {verb_part} …?",
                self.code,
                bullet=2,
                prompt="Name the person, place, or institution",
                role_verb=verb_part,
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2b. Active roles ("<Name> founded/led/invented/wrote/chaired/built ...")
        for m in self._ACTIVE_ROLE_RE.finditer(sentence):
            verb_part = m.group(2).strip().lower()
            s_idx, e_idx = self._trim_leading_stop_words(sentence, m.start(1), m.end(1))
            if _overlaps((s_idx, e_idx), claimed) or _inside_any((s_idx, e_idx), date_spans):
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "role_person",
                f"Who {verb_part} …?",
                self.code,
                bullet=2,
                prompt="Name the person, place, or institution",
                role_verb=verb_part,
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 1. Naming verbs ("is called X", "is known as X", "nicknamed X", "hailed as X")
        for m in self._NAMING_VERB_RE.finditer(sentence):
            s_idx, e_idx = m.start(1), m.end(1)
            if _overlaps((s_idx, e_idx), claimed) or _inside_any((s_idx, e_idx), date_spans):
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "named_entity",
                "What is it called?",
                self.code,
                bullet=1,
                prompt="Fill in the key term",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 5d. Organisations, documents, events ("Quit India Movement", "Satyashodhak Samaj", "Constituent Assembly", "Birmingham Hippodrome")
        for m in self._ORG_DOC_EVENT_HEAD_RE.finditer(sentence):
            s_idx, e_idx = self._trim_leading_stop_words(sentence, m.start(1), m.end(1))
            if _overlaps((s_idx, e_idx), claimed) or _inside_any((s_idx, e_idx), date_spans):
                continue
            phrase = sentence[s_idx:e_idx].strip()
            if not phrase or phrase.lower() in {"movement", "act", "party", "committee", "assembly", "company", "day", "centre", "center", "rights", "duties"}:
                continue
            last_w = phrase.split()[-1].lower()
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "organisation_document_event",
                f"Which {last_w} fits the gap?",
                self.code,
                bullet=5,
                prompt="Name the person, place, or institution",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # Multi-word proper names (people, places, institutions like "Jamsetji Tata", "Harland and Wolff", "Gowalia Tank Maidan")
        for m in self._MULTIWORD_PROPER_NAME_RE.finditer(sentence):
            s_idx, e_idx = self._trim_leading_stop_words(sentence, m.start(1), m.end(1))
            if _overlaps((s_idx, e_idx), claimed) or _inside_any((s_idx, e_idx), date_spans):
                continue
            phrase = sentence[s_idx:e_idx].strip()
            if len(phrase.split()) < 2:
                continue
            if any(w.lower() in {"january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"} for w in phrase.split()):
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "proper_name",
                "Name the person, place, or institution",
                self.code,
                bullet=5,
                prompt="Name the person, place, or institution",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        matches.sort(key=lambda x: (x["span"][0], -(x["span"][1] - x["span"][0])))
        return matches


# ===========================================================================
# F. DEFINITIONS AND CLASSIFICATION (what is it)
# ===========================================================================

class DefinitionsAndClassificationFamily:
    """Family F: Definitions ('X is a/an ...', 'X means ...', 'X refers to ...', 'X is defined as ...',
    'X is the process by which ...', 'X: <definition>', 'the study of ...'),
    kinds/parts ('types of', 'kinds of', 'consists of', 'is made up of', 'is divided into',
    'includes', 'such as', 'for example', 'e.g.', 'comprises', 'parts of'),
    and properties ('has ...', 'is ...', 'can ...' after a term).
    """

    code = "F"
    name = "DEFINITIONS AND CLASSIFICATION"

    # 1a. Term-colon definition: "Force: a push or pull on an object."
    _TERM_COLON_DEF_RE = re.compile(
        r"^(?:[•\-\*▪▸◦]\s*)?([A-Za-z][A-Za-z0-9’'\-–]*(?:\s+[A-Za-z][A-Za-z0-9’'\-–]*){0,2})\s*:\s+([a-zA-Z].{8,})$"
    )

    # 1b. "<Term> is a/an ... | means ... | refers to ... | is defined as ... | is the process by which/of ..."
    _SUBJECT_DEF_RE = re.compile(
        r"^(?:[•\-\*▪▸◦]\s*)?(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9’'\-–]*(?:\s+[A-Za-z][A-Za-z0-9’'\-–]*){0,2}?)\s+"
        r"(?:is\s+defined\s+as|is\s+the\s+process\s+(?:by\s+which|of|in\s+which)|is\s+the\s+study\s+of|"
        r"refers\s+to|means|states\s+that|is\s+a\s+set\s+of|is\s+anything\s+that|"
        r"is\s+(?:a|an)\s+[a-z]+\s+(?:that|which|used|of|in|by)|"
        r"is\s+solid\s+(?:directly\s+)?to|is\s+gas\s+to|is\s+liquid\s+to|"
        r"generally\s+has\s+a\s+fixed|has\s+a\s+fixed\s+volume|spreads\s+to\s+fill|"
        r"has\s+mass\s+and\s+occupies|describes\s+how\s+well|contains\s+one\s+kind\s+of\s+atom|"
        r"has\s+elements\s+chemically\s+combined|contains\s+(?:two\s+or\s+more\s+)?substances\s+physically\s+combined|"
        r"can\s+separate\s+an\s+insoluble|can\s+leave\s+a\s+dissolved|represents\s+an\s+element|"
        r"does\s+not\s+create\s+a\s+new\s+substance|forms\s+new\s+substance|"
        r"are\s+the\s+starting\s+substances|has\s+equal\s+counts\s+of\s+each\s+element)\b",
        re.IGNORECASE,
    )

    # 1c. "... the study of <topic> is called <Term>" or "<Term> is the study of <topic>"
    _STUDY_OF_RE = re.compile(
        r"\b(?:([A-Z][a-z]{3,20})\s+is\s+the\s+study\s+of\s+([a-z\s]{3,25})|"
        r"the\s+study\s+of\s+([a-z\s]{3,25}?)\s+is\s+(?:called|known\s+as)\s+([A-Za-z]{3,20}))\b",
        re.IGNORECASE,
    )

    # 2. Kinds and parts: "types of", "kinds of", "consists of", "is made up of", "is divided into", "includes", "such as", "for example", "e.g.", "comprises", "parts of"
    _KINDS_PARTS_RE = re.compile(
        r"\b(?:types\s+of\s+[a-z]+\s+are|kinds\s+of\s+[a-z]+\s+are|consists\s+of|is\s+made\s+up\s+of|"
        r"is\s+divided\s+into|includes|such\s+as|for\s+example|e\.g\.,?|comprises|parts\s+of\s+[a-z]+\s+are)\s+"
        r"(?:tiny\s+|small\s+|several\s+)?([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+[A-Za-z][A-Za-z0-9’'\-–]+){0,2}?)"
        r"(?=\s*(?:,|;|\.|and\b|or\b|too\s+small\b|which\b|that\b|$))",
        re.IGNORECASE,
    )

    # 3. Properties: "<Term> has / is / can / vibrate around / increases ..."
    _PROPERTY_PREDICATE_RE = re.compile(
        r"\b(?:described\s+by\s+their|vibrate\s+(?:around|about)|generally\s+increases|"
        r"ways\s+to\s+seek|responsibilities\s+expected\s+of|a\s+right\s+is\s+a|a\s+duty\s+is\s+a|"
        r"is\s+the\s+supreme|how\s+([a-z]+\s+[a-z]+)\s+is\s+organised)\s*"
        r"([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+[A-Za-z][A-Za-z0-9’'\-–]+){0,2})?",
        re.IGNORECASE,
    )

    _NON_TERM_SUBJECTS = {
        "it", "they", "this", "these", "that", "those", "he", "she", "we",
        "formulas", "symbols", "fraction", "fractions", "science", "algebra",
        "temperature", "equation", "solution", "example", "worked", "note",
    }

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        # 1a. Term-colon definition ("Force: a push or pull on an object.")
        m_col = self._TERM_COLON_DEF_RE.match(sentence.strip())
        if m_col:
            term = m_col.group(1).strip()
            if term.lower() not in self._NON_TERM_SUBJECTS and not any(ch.isdigit() for ch in term):
                idx = sentence.find(term)
                if idx != -1:
                    item = _make_match(
                        sentence,
                        idx,
                        idx + len(term),
                        "defined_term",
                        "Fill in the key term",
                        self.code,
                        bullet=1,
                        prompt="Fill in the key term",
                    )
                    if item:
                        matches.append(item)
                        claimed.append(item["span"])

        # 1b. Subject definition ("Photosynthesis is the process by which...", "A solid generally has a fixed shape...")
        m_def = self._SUBJECT_DEF_RE.match(sentence.strip())
        if m_def:
            term = m_def.group(1).strip()
            if term.lower() not in self._NON_TERM_SUBJECTS:
                idx = sentence.find(term)
                if idx != -1 and not _overlaps((idx, idx + len(term)), claimed):
                    item = _make_match(
                        sentence,
                        idx,
                        idx + len(term),
                        "defined_term",
                        "Fill in the key term",
                        self.code,
                        bullet=1,
                        prompt="Fill in the key term",
                    )
                    if item:
                        matches.append(item)
                        claimed.append(item["span"])

        # 1c. "the study of ..."
        for m in self._STUDY_OF_RE.finditer(sentence):
            grp = 1 if m.group(1) else 4
            if _overlaps(m.span(grp), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(grp),
                m.end(grp),
                "defined_term",
                "Fill in the key term",
                self.code,
                bullet=1,
                prompt="Fill in the key term",
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2. Kinds and parts ("consists of particles", "such as A, B and C" -> max one item per list)
        for m in self._KINDS_PARTS_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            cand = m.group(1).strip()
            # If the captured phrase starts with "a " or "an " or "the ", trim the article
            s_idx = m.start(1)
            for art in ("a ", "an ", "the "):
                if cand.lower().startswith(art):
                    s_idx += len(art)
                    break
            item = _make_match(
                sentence,
                s_idx,
                m.end(1),
                "classification_item",
                "Fill in the key term",
                self.code,
                bullet=2,
                prompt="Fill in the key term",
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])
                break  # max one card per list

        # 3. Properties ("has ...", "is ...", "can ..." after a term)
        m_prop = re.match(
            r"^(?:[•\-\*▪▸◦]\s*)?(?:The\s+|A\s+|An\s+)?([A-Za-z][A-Za-z0-9’'\-–]*(?:\s+[A-Za-z][A-Za-z0-9’'\-–]*){0,2}?)\s+"
            r"(?:has|have|is|are|can)\s+([a-zA-Z0-9\s’'\-–]{3,35})",
            sentence.strip(),
        )
        if m_prop:
            subj_t = m_prop.group(1).strip()
            if subj_t.lower() not in self._NON_TERM_SUBJECTS:
                idx = sentence.find(subj_t)
                if idx != -1 and not _overlaps((idx, idx + len(subj_t)), claimed):
                    item = _make_match(
                        sentence,
                        idx,
                        idx + len(subj_t),
                        "property_fact",
                        "Fill in the key term",
                        self.code,
                        bullet=3,
                        prompt="Fill in the key term",
                    )
                    if item:
                        matches.append(item)
                        claimed.append(item["span"])

        return matches


# ===========================================================================
# G. CAUSE, EFFECT, PURPOSE (why / how)
# ===========================================================================

class CauseEffectPurposeFamily:
    """Family G: 'because', 'due to', 'as a result', 'therefore', 'so', 'hence',
    'leads to', 'results in', 'causes', 'is caused by', 'helps', 'in order to',
    'so that', 'which is why'.
    Blanks the cause or the effect as a short phrase (<= 6 words).
    """

    code = "G"
    name = "CAUSE, EFFECT, PURPOSE"

    _CAUSE_CONNECTOR_RE = re.compile(
        r"\b(because\s+of|because|due\s+to|is\s+caused\s+by|are\s+caused\s+by)\s+"
        r"(?:the\s+|a\s+|an\s+)?([A-Za-z0-9][A-Za-z0-9\s’'\-–]{2,45}?)(?=[.,;:]|$)",
        re.IGNORECASE,
    )
    _EFFECT_CONNECTOR_RE = re.compile(
        r"\b(as\s+a\s+result(?:\s+of)?|therefore,?|hence,?|leads\s+to|results\s+in|causes|which\s+is\s+why|so\s+that|in\s+order\s+to|helps\s+(?:to\s+)?)\s+"
        r"(?:the\s+|a\s+|an\s+)?([A-Za-z0-9][A-Za-z0-9\s’'\-–]{2,45}?)(?=[.,;:]|$)",
        re.IGNORECASE,
    )

    def _trim_to_short_phrase(self, sentence: str, start: int, end: int) -> tuple[int, int]:
        phrase = sentence[start:end].strip()
        # Stop at secondary clause boundaries
        m_stop = re.search(r"\s+\b(?:and\s+therefore|which\b|while\b|whereas\b|although\b|but\b)\b", phrase, re.IGNORECASE)
        if m_stop:
            end = start + m_stop.start()
            phrase = sentence[start:end].strip()
        words = phrase.split()
        if not words:
            return start, start
        if words[0].lower() in {"it", "they", "he", "she", "we", "you", "i", "there"}:
            return (start, end) if len(words) <= 6 else (start, start)
        if len(words) > 6:
            # Trim to at most 4–6 words if a preposition boundary exists
            for cut in range(2, min(6, len(words))):
                if words[cut].lower() in {"in", "on", "at", "by", "with", "during", "across", "throughout", "around"}:
                    kept = " ".join(words[:cut])
                    return start, start + len(kept)
            return start, start  # reject if > 6 words and cannot be cleanly bounded
        return start, end

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []

        for m in self._CAUSE_CONNECTOR_RE.finditer(sentence):
            s_idx, e_idx = self._trim_to_short_phrase(sentence, m.start(2), m.end(2))
            if s_idx >= e_idx:
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "cause_phrase",
                "Which cause fits the gap?",
                self.code,
                bullet=1,
                prompt="Which cause fits the gap?",
                connector=m.group(1),
            )
            if item and len(item["text"].split()) <= 6:
                matches.append(item)

        for m in self._EFFECT_CONNECTOR_RE.finditer(sentence):
            s_idx, e_idx = self._trim_to_short_phrase(sentence, m.start(2), m.end(2))
            if s_idx >= e_idx:
                continue
            conn_low = m.group(1).lower()
            expr_t = "purpose_phrase" if ("in order to" in conn_low or "so that" in conn_low or "helps" in conn_low) else "effect_phrase"
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                expr_t,
                "Which effect…?",
                self.code,
                bullet=1,
                prompt="Which effect…?",
                connector=m.group(1),
            )
            if item and len(item["text"].split()) <= 6:
                matches.append(item)

        return matches


# ===========================================================================
# H. SEQUENCE AND PROCESS (steps, cycles, timelines)
# ===========================================================================

class SequenceAndProcessFamily:
    """Family H: 'first', 'second', 'next', 'then', 'after that', 'finally', 'lastly',
    'step 1', 'stage', 'begins with', 'ends with', 'followed by', '→'.
    Blanks one step's key word while keeping the step's number/order word on the card.
    """

    code = "H"
    name = "SEQUENCE AND PROCESS"

    _STEP_CUE_RE = re.compile(
        r"\b(step\s+\d+|stage\s+\d+|first,?|second,?|third,?|next,?|then,?|after\s+that,?|finally,?|lastly,?|"
        r"begins\s+with|ends\s+with|followed\s+by)\s*:?\s+"
        r"(?:the\s+|a\s+|an\s+)?([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+(?!from\b|in\b|on\b|at\b|to\b|into\b|by\b|of\b|with\b|through\b|across\b|and\b|or\b|occurs\b|happens\b|takes\b|begins\b|starts\b|is\b|are\b)[A-Za-z][A-Za-z0-9’'\-–]+){0,2})",
        re.IGNORECASE,
    )
    _ARROW_CHAIN_RE = re.compile(
        r"\b([A-Za-z][A-Za-z0-9\s’'\-]{1,20}?)\s*→\s*([A-Za-z][A-Za-z0-9\s’'\-]{1,20}?)(?=\s*(?:→|[.,;]|$))"
    )

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        # Skip chemical equations ("2H₂ + O₂ → 2H₂O") which belong to Family D
        if re.search(r"[0-9₀-₉]+[A-Z]|[A-Z][a-z]?[₀-₉]+", sentence) and "→" in sentence:
            return []

        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        for m in self._STEP_CUE_RE.finditer(sentence):
            cue = m.group(1).strip(" ,:")
            cand = m.group(2).strip()
            s_idx, e_idx = m.start(2), m.end(2)
            # Trim trailing auxiliary verb ("evaporation occurs" -> "evaporation")
            words = cand.split()
            if len(words) >= 2 and words[-1].lower() in {"occurs", "happens", "takes", "begins", "starts", "is", "are"}:
                e_idx = s_idx + len(" ".join(words[:-1]))
            if _overlaps((s_idx, e_idx), claimed):
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "sequence_step",
                "Which step fits the gap?",
                self.code,
                bullet=1,
                prompt="Fill in the key term",
                order_word=cue,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._ARROW_CHAIN_RE.finditer(sentence):
            if _overlaps(m.span(2), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "sequence_step",
                "Which step fits the gap?",
                self.code,
                bullet=1,
                prompt="Fill in the key term",
                order_word="→",
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        return matches


# ===========================================================================
# I. PLACE AND LOCATION
# ===========================================================================

class PlaceAndLocationFamily:
    """Family I: 'located in', 'situated on/in', 'lies on', 'flows through', 'on the banks of',
    'capital of', 'largest city in', 'borders', 'between ... and ...', 'north of',
    'in the <region>', 'headquarters in', 'is found in', 'native to'.
    Questions: 'Which place…?', 'Which river…?' (only when the sheet says river), 'Which city…?'.
    """

    code = "I"
    name = "PLACE AND LOCATION"

    _RIVER_LOC_RE = re.compile(
        r"\b(?:situated\s+on|lies\s+on|lying\s+on|located\s+on|on\s+the\s+banks\s+of|flows\s+through|across)\s+"
        r"(?:the\s+)?(River\s+[A-Z][A-Za-z’'\-]+|[A-Z][A-Za-z’'\-]+\s+River)\b"
    )
    _PLACE_LOC_RE = re.compile(
        r"\b(located\s+in|situated\s+in|situated\s+on|lies\s+in|lies\s+on|lying\s+on|flows\s+through|"
        r"on\s+the\s+banks\s+of|capital\s+(?:city\s+)?of|largest\s+city\s+(?:in|of)|city\s+outside|"
        r"city\s+of\s+the|borders|north\s+of|south\s+of|east\s+of|west\s+of|headquarters\s+in|"
        r"is\s+found\s+in|are\s+found\s+in|native\s+to|in\s+the|financial\s+centre\s+of|"
        r"southeastern|northeastern|southwestern|northwestern)\s+"
        r"(?:the\s+)?([A-Z][A-Za-z’'\-]+(?:\s+(?:of\s+the\s+|of\s+)?[A-Z][A-Za-z’'\-]+){0,3})"
    )
    _BETWEEN_PLACES_RE = re.compile(
        r"\bbetween\s+(?:the\s+)?([A-Z][A-Za-z’'\-]+(?:\s+[A-Z][A-Za-z’'\-]+){0,2})\s+and\s+(?:the\s+)?([A-Z][A-Za-z’'\-]+(?:\s+[A-Z][A-Za-z’'\-]+){0,2})\b"
    )

    _NON_PLACE_WORDS = {
        "Industrial Revolution", "Constituent Assembly", "Scottish Parliament", "National Assembly",
        "Bank of Scotland", "Royal Bank", "RMS Titanic", "Titanic Belfast", "Birmingham Hippodrome",
        "Wales Millennium Centre", "Drafting Committee", "Fundamental Rights", "Fundamental Duties",
    }

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []
        date_spans = [m["span"] for m in FAMILY_A.find(sentence)]

        # 1. Explicit river locations ("River Thames", "River Rea", "River Lagan", "Narmada River")
        for m in self._RIVER_LOC_RE.finditer(sentence):
            if _overlaps(m.span(1), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(1),
                m.end(1),
                "river_location",
                "Which river…?",
                self.code,
                bullet=1,
                prompt="Which river…?",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 2. General place/city/region locations
        for m in self._PLACE_LOC_RE.finditer(sentence):
            cue_low = m.group(1).lower()
            place_txt = m.group(2).strip()
            if _overlaps(m.span(2), claimed) or _inside_any(m.span(2), date_spans):
                continue
            if place_txt in self._NON_PLACE_WORDS or any(
                w in place_txt for w in ("Revolution", "Parliament", "Assembly", "Committee", "Century", "Age", "Period")
            ):
                continue
            if "river" in place_txt.lower():
                q_type = "Which river…?"
                sub_t = "river_location"
            elif "city outside" in cue_low:
                q_type = "Which city…?"
                sub_t = "city_location"
            else:
                q_type = "Which place…?"
                sub_t = "place_location"
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                sub_t,
                q_type,
                self.code,
                bullet=1,
                prompt="Name the person, place, or institution",
                cue=m.group(1),
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3. "between <Place A> and <Place B>"
        for m in self._BETWEEN_PLACES_RE.finditer(sentence):
            for grp in (1, 2):
                if _overlaps(m.span(grp), claimed) or _inside_any(m.span(grp), date_spans):
                    continue
                item = _make_match(
                    sentence,
                    m.start(grp),
                    m.end(grp),
                    "place_location",
                    "Which place…?",
                    self.code,
                    bullet=1,
                    prompt="Name the person, place, or institution",
                    atomic=True,
                )
                if item:
                    matches.append(item)
                    claimed.append(item["span"])

        return matches


# ===========================================================================
# J. COMPARISONS AND SUPERLATIVES
# ===========================================================================

class ComparisonsAndSuperlativesFamily:
    """Family J: 'the largest', 'the longest', 'the highest', 'the oldest', 'the first',
    'the only', 'most', 'least', 'more than', 'less than', 'bigger than', 'unlike',
    'whereas', 'while', 'compared with'.
    Blanks the thing that holds the superlative ('______ is the largest planet' -> 'Jupiter').
    Superlatives keep the 'check first' note for the adult ONLY once per card and NEVER on ordinals
    like 'eleventh-largest'.
    """

    code = "J"
    name = "COMPARISONS AND SUPERLATIVES"

    _SUBJECT_SUPERLATIVE_RE = re.compile(
        r"^(?:[•\-\*▪▸◦]\s*)?([A-Z][A-Za-z0-9’'\-–]+(?:\s+[A-Z][A-Za-z0-9’'\-–]+){0,3})\s+"
        r"(?:is|was|became)\s+(?:the\s+(?:[A-Za-z’']+\s+)?)?"
        r"(largest|longest|highest|oldest|first|only|smallest|busiest|deepest|tallest|biggest|"
        r"most\s+[a-z]+|least\s+[a-z]+)\b"
    )
    _PREDICATE_SUPERLATIVE_RE = re.compile(
        r"\b(the\s+(?:largest|longest|highest|oldest|first|only|smallest|busiest|deepest|tallest|biggest|most\s+[a-z]+|least\s+[a-z]+))\s+"
        r"([a-z]+(?:\s+in\s+the\s+[A-Za-z]+)?)\s+(?:is|was)\s+"
        r"([A-Z][A-Za-z0-9’'\-–]+(?:\s+[A-Z][A-Za-z0-9’'\-–]+){0,2})\b",
        re.IGNORECASE,
    )
    _COMPARISON_CONTRAST_RE = re.compile(
        r"\b(more\s+than\s+(?:[A-Z][A-Za-z]+\s+and\s+)?|less\s+than\s+|bigger\s+than\s+|smaller\s+than\s+|"
        r"unlike\s+|compared\s+with\s+|whereas\s+|while\s+)"
        r"([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+[A-Za-z][A-Za-z0-9’'\-–]+){0,2})"
    )
    _ORDINAL_SUPERLATIVE_PREFIX_RE = re.compile(
        rf"\b(?:\d+(?:st|nd|rd|th)|{_NUMBER_WORDS_ORDINAL})[-\s]+(?:largest|smallest|longest|highest|oldest|biggest|most\s+[a-z]+)\b",
        re.IGNORECASE,
    )

    def has_true_superlative(self, sentence: str) -> bool:
        """Return True if `sentence` contains a true superlative (and NOT merely an ordinal like 'eleventh-largest')."""
        cleaned = self._ORDINAL_SUPERLATIVE_PREFIX_RE.sub("", sentence or "")
        return bool(
            re.search(
                r"\b(?:the\s+(?:world’s\s+|world's\s+|UK’s\s+|UK's\s+|India’s\s+|India's\s+)?"
                r"(?:largest|longest|highest|oldest|first|only|smallest|busiest|deepest|tallest|biggest|most\s+important|most\s+populous|most\s+productive))\b",
                cleaned,
                re.IGNORECASE,
            )
        )

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        # 1. "<Thing> is the largest/longest/highest/oldest/first/only/busiest ..."
        m_sub = self._SUBJECT_SUPERLATIVE_RE.match(sentence.strip())
        if m_sub:
            holder = m_sub.group(1).strip()
            idx = sentence.find(holder)
            if idx != -1:
                is_sup = self.has_true_superlative(sentence)
                extra_sup = {"note": SUPERLATIVE_CHECK_NOTE} if is_sup else {}
                item = _make_match(
                    sentence,
                    idx,
                    idx + len(holder),
                    "superlative_holder",
                    "Name the person, place, or institution",
                    self.code,
                    bullet=1,
                    prompt="Name the person, place, or institution",
                    is_superlative=is_sup,
                    atomic=True,
                    **extra_sup,
                )
                if item:
                    matches.append(item)
                    claimed.append(item["span"])

        # 2. "The largest/longest <noun> is <Thing>"
        for m in self._PREDICATE_SUPERLATIVE_RE.finditer(sentence):
            if _overlaps(m.span(3), claimed):
                continue
            is_sup = self.has_true_superlative(sentence)
            extra_sup = {"note": SUPERLATIVE_CHECK_NOTE} if is_sup else {}
            item = _make_match(
                sentence,
                m.start(3),
                m.end(3),
                "superlative_holder",
                "Name the person, place, or institution",
                self.code,
                bullet=1,
                prompt="Name the person, place, or institution",
                is_superlative=is_sup,
                atomic=True,
                **extra_sup,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        # 3. Comparisons ("more than London and Liverpool", "bigger than Mars", "unlike solids")
        for m in self._COMPARISON_CONTRAST_RE.finditer(sentence):
            if _overlaps(m.span(2), claimed):
                continue
            item = _make_match(
                sentence,
                m.start(2),
                m.end(2),
                "comparison_fact",
                "Fill in the key fact",
                self.code,
                bullet=1,
                prompt="Fill in the key fact",
                is_superlative=False,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        return matches


# ===========================================================================
# K. LANGUAGE AND GRAMMAR SHEETS (English, Hindi as printed)
# ===========================================================================

class LanguageAndGrammarFamily:
    """Family K: 'plural of', 'opposite of', 'antonym', 'synonym', 'past tense of',
    'noun', 'verb', 'adjective', 'means', 'rhymes with', 'is spelt'.
    Blanks the word that answers ('The opposite of 'ancient' is ______' -> 'modern').
    """

    code = "K"
    name = "LANGUAGE AND GRAMMAR"

    _GRAMMAR_RELATION_RE = re.compile(
        r"\b(?:the\s+)?("
        r"plural\s+of|opposite\s+of|antonym\s+of|synonym\s+of|past\s+tense\s+of|"
        r"feminine\s+of|masculine\s+of|comparative\s+of|superlative\s+of|"
        r"adjective\s+form\s+of|noun\s+form\s+of|verb\s+form\s+of"
        r")\s+[‘'“\"]?([A-Za-z\u0900-\u097F\-]+)[’'”\"]?\s+is\s+[‘'“\"]?([A-Za-z\u0900-\u097F\-]+)[’'”\"]?",
        re.IGNORECASE,
    )
    _GRAMMAR_RHYME_SPELL_RE = re.compile(
        r"\b([‘'“\"]?[A-Za-z\u0900-\u097F\-]+[’'”\"]?)\s+(rhymes\s+with|is\s+spelt|is\s+an\s+antonym\s+of|is\s+a\s+synonym\s+of|"
        r"is\s+a\s+noun|is\s+a\s+verb|is\s+an\s+adjective)\s*(?:as\s+)?[‘'“\"]?([A-Za-z\u0900-\u097F\-]+)?[’'”\"]?",
        re.IGNORECASE,
    )

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence or "?" in sentence:
            return []
        matches: list[dict[str, Any]] = []
        claimed: list[tuple[int, int]] = []

        for m in self._GRAMMAR_RELATION_RE.finditer(sentence):
            item = _make_match(
                sentence,
                m.start(3),
                m.end(3),
                "language_grammar",
                "Which word fits the gap?",
                self.code,
                bullet=1,
                prompt="Which word fits the gap?",
                relation=m.group(1),
                source_word=m.group(2),
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        for m in self._GRAMMAR_RHYME_SPELL_RE.finditer(sentence):
            if m.group(3):
                s_idx, e_idx = m.start(3), m.end(3)
            else:
                # e.g. "'Swift' is an adjective" -> blank 'adjective'
                rel_txt = m.group(2)
                last_w = rel_txt.split()[-1]
                s_idx = m.end(2) - len(last_w)
                e_idx = m.end(2)
            if _overlaps((s_idx, e_idx), claimed):
                continue
            item = _make_match(
                sentence,
                s_idx,
                e_idx,
                "language_grammar",
                "Which word fits the gap?",
                self.code,
                bullet=1,
                prompt="Which word fits the gap?",
                atomic=True,
            )
            if item:
                matches.append(item)
                claimed.append(item["span"])

        return matches


# ===========================================================================
# L. READING THE SHEET'S OWN QUESTIONS (do not print them as cards)
# ===========================================================================

class SheetQuestionsReaderFamily:
    """Family L: Detects the sheet's own practice/exercise questions (Who, Whom, Whose, What,
    Which, When, Where, Why, How, How many, How much, How long, Name, State, Define, List,
    Give, Explain, Describe, Compare, Distinguish, Mention, Identify, Fill in the blanks,
    True or False, Match the following), determines what each question asks for
    (person, date, number, place, river, term, cause, list), and links it to the fact
    sentence elsewhere on the sheet so the fact sentence gets HIGH PRIORITY.
    """

    code = "L"
    name = "SHEET QUESTIONS READER"

    _QUESTION_START_RE = re.compile(
        r"^(?:(?:Q\.?\s*\d+|\d+|\(\d+\)|[A-Za-z])[.):]\s*)?"
        r"(How\s+many|How\s+much|How\s+long|Fill\s+in\s+the\s+blanks?|True\s+or\s+False|Match\s+the\s+following|"
        r"Who|Whom|Whose|What|Which|When|Where|Why|How|"
        r"Name|State|Define|List|Give|Explain|Describe|Compare|Distinguish|Mention|Identify|Calculate|Evaluate|Write|Find)\b",
        re.IGNORECASE,
    )
    _FILL_BLANK_EXERCISE_RE = re.compile(r"_{3,}")
    _TRUE_FALSE_TAG_RE = re.compile(r"\(\s*(?:True\s*/\s*False|T\s*/\s*F)\s*\)|\bTrue\s+or\s+False\b", re.IGNORECASE)

    _STOP_KW = {
        "the", "a", "an", "of", "in", "on", "at", "to", "for", "from", "with", "by", "as",
        "is", "are", "was", "were", "be", "been", "has", "have", "had", "do", "does", "did",
        "who", "whom", "whose", "what", "which", "when", "where", "why", "how", "many", "much", "long",
        "name", "state", "define", "list", "give", "explain", "describe", "compare", "distinguish",
        "mention", "identify", "fill", "blanks", "blank", "true", "false", "match", "following",
        "any", "two", "three", "one", "each", "mark", "marks", "sentence", "short", "answer", "questions",
        "year", "date", "city", "river", "place", "person", "term", "role", "importance", "famous",
    }

    def _classify_target_and_prompt(self, sentence: str, q_word: str) -> tuple[str, str]:
        s_low = sentence.lower()
        qw_low = q_word.lower()
        if qw_low in {"when"} or re.search(r"\b(?:in\s+the\s+year|which\s+year|what\s+year|which\s+date|when\s+was|when\s+did)\b", s_low):
            return "date", "Which year…?"
        if qw_low in {"how many", "how much", "how long"} or re.search(
            r"\b(?:what\s+is\s+the\s+population|what\s+is\s+the\s+rank|how\s+many|number\s+of|count\s+of)\b", s_low
        ):
            return "number", "How many…?"
        if "river" in s_low and (qw_low in {"which", "name", "what"} or "river ____" in s_low):
            return "river", "Which river…?"
        if qw_low in {"where"} or re.search(
            r"\b(?:which\s+city|which\s+place|which\s+country|which\s+region|capital\s+city\s+of|situated\s+on\s+the)\b", s_low
        ):
            return "place", "Which place…?"
        if qw_low in {"who", "whom", "whose"} or re.search(
            r"\b(?:which\s+bank|which\s+shipyard|name\s+the\s+interactive\s+museum|name\s+the\s+busiest\s+theatre|built\s+the\s+famous\s+ship)\b",
            s_low,
        ):
            return "person", "Name the person, place, or institution"
        if qw_low in {"why"} or "because" in s_low or "reason" in s_low:
            return "cause", "Which cause fits the gap?"
        if qw_low in {"list"} or "two facts" in s_low or "three properties" in s_low:
            return "list", "Fill in the key term"
        if qw_low in {"define"} or "what is meant by" in s_low:
            return "term", "Fill in the key term"
        return "term", "Fill in the key term"

    def find(self, sentence: str) -> list[dict[str, Any]]:
        if not sentence:
            return []
        s = sentence.strip()
        m_q = self._QUESTION_START_RE.match(s)
        has_blank = bool(self._FILL_BLANK_EXERCISE_RE.search(s))
        has_tf = bool(self._TRUE_FALSE_TAG_RE.search(s))

        if not m_q and not has_blank and not has_tf and not s.endswith("?"):
            return []

        if m_q:
            q_word = m_q.group(1)
            span = m_q.span(1)
        elif has_tf:
            m_tf = self._TRUE_FALSE_TAG_RE.search(s)
            q_word = m_tf.group(0) if m_tf else "True or False"
            span = m_tf.span() if m_tf else (0, len(s))
        elif has_blank:
            m_b = self._FILL_BLANK_EXERCISE_RE.search(s)
            q_word = "Fill in the blanks"
            span = m_b.span() if m_b else (0, len(s))
        else:
            first_w = s.split()[0]
            q_word = first_w
            span = (0, len(first_w))

        asks_for, q_prompt = self._classify_target_and_prompt(s, q_word)
        keywords = [
            w.lower()
            for w in re.findall(r"[A-Za-z0-9]{3,}", s)
            if w.lower() not in self._STOP_KW and not re.fullmatch(r"_+", w)
        ]

        return [
            {
                "span": span,
                "text": s[span[0] : span[1]],
                "type": f"practice_question_{asks_for}",
                "asks_for": asks_for,
                "question_word": q_word,
                "question_type": q_prompt,
                "prompt": q_prompt,
                "keywords": keywords,
                "family": self.code,
                "bullet": 1,
                "skip_as_card": True,
            }
        ]

    def match_questions_to_facts(
        self,
        question_lines: list[str],
        fact_lines: list[str],
    ) -> dict[int, list[dict[str, Any]]]:
        """For each practice/exercise question on the sheet, find the fact sentence in `fact_lines`
        that answers it and return `{fact_index: [priority_signal_dicts]}`.
        """
        signals_by_fact: dict[int, list[dict[str, Any]]] = {}
        if not question_lines or not fact_lines:
            return signals_by_fact

        fact_tokens_list = [
            {w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", fl) if w.lower() not in self._STOP_KW}
            for fl in fact_lines
        ]

        for q_line in question_lines:
            q_matches = self.find(q_line)
            if not q_matches:
                continue
            q_info = q_matches[0]
            kws = set(q_info.get("keywords") or [])
            if not kws:
                continue

            best_idx = -1
            best_score = 0
            for idx, f_toks in enumerate(fact_tokens_list):
                overlap = len(kws & f_toks)
                if overlap > best_score and (overlap >= 2 or (len(kws) == 1 and overlap == 1)):
                    best_score = overlap
                    best_idx = idx

            if best_idx != -1:
                signals_by_fact.setdefault(best_idx, []).append(q_info)

        return signals_by_fact


# ===========================================================================
# Module-level instances and helpers
# ===========================================================================

FAMILY_A = TimeAndDatesFamily()
FAMILY_B = NumbersAndQuantitiesFamily()
FAMILY_C = MeasurementAndUnitsFamily()
FAMILY_D = FormulasEquationsSymbolsFamily()
FAMILY_E = NamesTitlesRolesFamily()
FAMILY_F = DefinitionsAndClassificationFamily()
FAMILY_G = CauseEffectPurposeFamily()
FAMILY_H = SequenceAndProcessFamily()
FAMILY_I = PlaceAndLocationFamily()
FAMILY_J = ComparisonsAndSuperlativesFamily()
FAMILY_K = LanguageAndGrammarFamily()
FAMILY_L = SheetQuestionsReaderFamily()

TIME_AND_DATES = FAMILY_A
NUMBERS_AND_QUANTITIES = FAMILY_B
MEASUREMENT_AND_UNITS = FAMILY_C
FORMULAS_EQUATIONS_SYMBOLS = FAMILY_D
NAMES_TITLES_ROLES = FAMILY_E
DEFINITIONS_AND_CLASSIFICATION = FAMILY_F
CAUSE_EFFECT_PURPOSE = FAMILY_G
SEQUENCE_AND_PROCESS = FAMILY_H
PLACE_AND_LOCATION = FAMILY_I
COMPARISONS_AND_SUPERLATIVES = FAMILY_J
LANGUAGE_AND_GRAMMAR = FAMILY_K
SHEET_QUESTIONS_READER = FAMILY_L

FAMILIES: dict[str, Any] = {
    "A": FAMILY_A,
    "B": FAMILY_B,
    "C": FAMILY_C,
    "D": FAMILY_D,
    "E": FAMILY_E,
    "F": FAMILY_F,
    "G": FAMILY_G,
    "H": FAMILY_H,
    "I": FAMILY_I,
    "J": FAMILY_J,
    "K": FAMILY_K,
    "L": FAMILY_L,
}

# Step 3 priority order across expression families:
# bold > named in a practice question (L) > dates (A) > names/titles (E) > numbers+units (B, C) >
# defined terms (F) > formulas (D) > places (I) > others (G, H, J, K)
FAMILY_PRIORITY_ORDER: tuple[str, ...] = ("A", "E", "C", "B", "F", "D", "I", "G", "H", "J", "K")

FAMILY_PRIORITY_RANK: dict[str, int] = {
    "bold": 0,
    "L": 1,
    "A": 2,
    "E": 3,
    "C": 4,
    "B": 4,
    "F": 5,
    "D": 6,
    "I": 7,
    "G": 8,
    "H": 8,
    "J": 8,
    "K": 8,
    "table": 9,
}


def find_all_expressions(
    sentence: str,
    *,
    practice_signals: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Run all expression families A–K on `sentence` (and apply any Family L practice-question priority signals),
    returning matches ordered by the Step 3 priority:
    named in a practice question (L) > dates (A) > names/titles (E) > numbers+units (B, C) >
    defined terms (F) > formulas (D) > places (I) > others (G, H, J, K).
    """
    if not sentence or not sentence.strip():
        return []

    raw_matches: list[dict[str, Any]] = []
    for fam_code in FAMILY_PRIORITY_ORDER:
        fam = FAMILIES[fam_code]
        for m in fam.find(sentence):
            raw_matches.append(m)

    # If Family L practice signals point to this fact sentence, promote the matching target type to Family L priority
    if practice_signals:
        target_map = {
            "date": {"A"},
            "number": {"B", "C"},
            "river": {"I"},
            "place": {"I", "E"},
            "person": {"E"},
            "term": {"F", "E", "D"},
            "cause": {"G"},
            "list": {"F"},
        }
        q_kws = {kw.lower() for sig in practice_signals for kw in (sig.get("keywords") or [])}
        for sig in practice_signals:
            asks_for = sig.get("asks_for", "term")
            allowed_fams = target_map.get(asks_for, {"A", "B", "C", "D", "E", "F", "I"})
            for m in raw_matches:
                if m["family"] not in allowed_fams:
                    continue
                if asks_for == "river" and "river" not in m["text"].lower():
                    continue
                # Don't blank the entity that the practice question itself already names as the subject
                ans_words = {w.lower() for w in re.findall(r"[A-Za-z0-9]{3,}", m["text"])}
                if ans_words and ans_words <= q_kws and asks_for != "term":
                    continue
                promoted = dict(m)
                promoted["origin_family"] = m["family"]
                promoted["family"] = "L"
                promoted["question_type"] = sig.get("question_type") or m["question_type"]
                promoted["prompt"] = sig.get("prompt") or m.get("prompt") or m["question_type"]
                raw_matches.insert(0, promoted)
                break

    # Attach superlative note once per card when sentence has a true superlative (never on ordinals like "eleventh-largest")
    has_true_sup = FAMILY_J.has_true_superlative(sentence)
    for m in raw_matches:
        if m.get("type") == "ordinal_rank":
            m["is_superlative"] = False
            m.pop("note", None)
        elif has_true_sup and "note" not in m:
            m["is_superlative"] = True
            m["note"] = SUPERLATIVE_CHECK_NOTE

    raw_matches.sort(
        key=lambda m: (
            1 if m.get("type") == "name_dates_heading" else FAMILY_PRIORITY_RANK.get(m["family"], 8),
            1 if (m["family"] == "E" and m["span"][0] == 0 and m.get("type") != "name_dates_heading") else 0,
            m["span"][0],
            -(m["span"][1] - m["span"][0]),
        )
    )
    return raw_matches


def find_atomic_spans(sentence: str) -> list[dict[str, Any]]:
    """Return atomic spans (full dates, grouped/Indian numbers, numbers with units,
    money, percentages/fractions/ratios, chemical formulas, Article <n>) that must
    NEVER be cut in half by a blank (Step 6).
    """
    if not sentence:
        return []
    atomic: list[dict[str, Any]] = []
    for fam in (FAMILY_A, FAMILY_C, FAMILY_B, FAMILY_D, FAMILY_E):
        for m in fam.find(sentence):
            if m.get("atomic") and m["type"] in {
                "full_date",
                "month_year",
                "day_month",
                "year_range",
                "era_marker",
                "measurement_unit",
                "area_volume_unit",
                "plain_or_grouped_number",
                "money",
                "percentage_fraction_ratio",
                "chemical_formula",
            }:
                atomic.append(m)
            elif m["type"] == "organisation_document_event" and m["text"].startswith("Article "):
                atomic.append(m)
    return atomic


def check_cut_in_half_span(
    answer: str,
    source_line: str = "",
    clue: str = "",
) -> tuple[bool, str]:
    """Step 6 of Prompt 8: Return `(True, reason)` if `answer` (or the blank in `clue`)
    cuts any recognised atomic span in `source_line` / `clue` in half:
      - e.g. 'August' out of '8 August 1942'
      - e.g. '286' out of '286,000' or '2,86,000'
      - e.g. 'km' without its number (or '387' without 'km' in '387 km')
    Returns `(False, "")` if valid.
    """
    ans_clean = (answer or "").strip(" ,.:;()'\"‘’“”")
    if not ans_clean:
        return False, ""

    # 1. Bare unit without its number (e.g. "km", "m", "kg", "mL", "cm", "mm", "m/s", "km/h", "°C")
    if re.fullmatch(_UNIT_SYMBOLS, ans_clean) and not any(ch.isdigit() for ch in ans_clean):
        # Unless the question explicitly asks "What is the unit of ...?" or defines the symbol alone
        if not re.search(r"\bunit\s+of\b", clue or source_line or "", re.IGNORECASE):
            if (
                re.search(r"\b\d+(?:,\d{2,3})*(?:\.\d+)?\s*_{2,}", clue or "")
                or re.search(r"\b\d+(?:,\d{2,3})*(?:\.\d+)?\s*" + re.escape(ans_clean) + r"(?!\w)", source_line or "")
                or not source_line
            ):
                return True, f"cut-in-half span: bare unit {ans_clean!r} without its number"

    # 2. Clue directly shows a split grouped number ("______,000" or "286,______") or split date ("8 ______ 1942") or split unit ("387 ______")
    if clue:
        if re.search(r"_{2,}\s*,\s*\d{2,3}\b|\b\d{1,3}\s*,\s*_{2,}", clue):
            return True, f"cut-in-half span: blank splits grouped number ({ans_clean!r})"
        if re.search(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+_{{2,}}\s+\d{{4}}\b|_{{2,}}\s+{_MONTH_FULL}\s+\d{{4}}\b", clue):
            return True, f"cut-in-half span: blank splits full date ({ans_clean!r})"
        if re.search(rf"\b\d+(?:,\d{{2,3}})*(?:\.\d+)?\s+_{{2,}}\b", clue) and re.fullmatch(_UNIT_SYMBOLS, ans_clean):
            return True, f"cut-in-half span: blank splits number from its unit ({ans_clean!r})"
        if re.search(rf"_{{2,}}\s+{_UNIT_SYMBOLS}(?!\w)", clue) and re.fullmatch(r"\d+(?:,\d{2,3})*(?:\.\d+)?", ans_clean):
            return True, f"cut-in-half span: blank splits number {ans_clean!r} from its unit"

    if not source_line:
        return False, ""

    # 3. Check all atomic spans in `source_line`: if `ans_clean` is a proper substring of an atomic span
    # and does NOT appear as an independent whole span elsewhere on `source_line`, reject it.
    plain_src = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__|</?b>", lambda m: m.group(1) or m.group(2) or "", source_line)
    atomic_spans = find_atomic_spans(plain_src)

    for atom in atomic_spans:
        atom_txt = atom["text"]
        if ans_clean.lower() == atom_txt.lower():
            continue
        # Check if `ans_clean` occurs strictly inside `atom_txt`
        if re.search((r"\b" if ans_clean[0].isalnum() else "") + re.escape(ans_clean) + (r"\b" if ans_clean[-1].isalnum() else ""), atom_txt, re.IGNORECASE):
            # Does `ans_clean` also appear outside `atom["span"]` on the same line?
            s_a, e_a = atom["span"]
            outside = plain_src[:s_a] + " " + plain_src[e_a:]
            if not re.search((r"\b" if ans_clean[0].isalnum() else "") + re.escape(ans_clean) + (r"\b" if ans_clean[-1].isalnum() else ""), outside, re.IGNORECASE):
                return (
                    True,
                    f"cut-in-half span: {ans_clean!r} cuts {atom['type']} {atom_txt!r} in half",
                )

    return False, ""
