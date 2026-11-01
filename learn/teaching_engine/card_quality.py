"""No-AI, rule-based 7-criterion card quality checker and Key Facts card writer for the Teaching Engine.

Scope:
- Applies ONLY to Key Facts mode. Detective, Superhero, and Study modes must not change.
- No AI at all: everything is rule-based with provider "deterministic".
- Coverage for Key Facts (replaces Rule A): only what the sheet marks to learn gets a card:
  bold words (answers), bold words printed as one list (one shared card), all-bold sentences,
  and bullet/numbered points. Headings, tables, pictures, unanswered questions, practice Q&A
  sections, and other unmarked prose get none. A sheet that marks nothing gets the usual cards
  with a note.
- Variety (replaces Rule B): reading order; no two cards test the same fact. Key Facts cards
  are fill-in-the-blank ("______"); do not force why/how mixes.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Callable

from learn.teaching_engine.expressions import (
    FAMILIES,
    FAMILY_A,
    FAMILY_B,
    FAMILY_C,
    FAMILY_D,
    FAMILY_E,
    FAMILY_F,
    FAMILY_G,
    FAMILY_H,
    FAMILY_I,
    FAMILY_J,
    FAMILY_K,
    FAMILY_L,
    SUPERLATIVE_CHECK_NOTE,
    check_cut_in_half_span,
    find_all_expressions,
)
from learn.teaching_engine.questions import (
    ALLOWED_TEMPLATE_WORDS,
    CLASS_WORDS,
    PAST_TO_BASE_VERBS,
    QUESTION_WORDS,
    TEMPLATE_PRIORITY_ORDER,
    balance_template_mix,
    check_question_card,
    choose_question_for_fact,
)

CRITERIA: tuple[str, ...] = (
    "grounded",
    "short_answer",
    "clear_question",
    "names_subject",
    "not_furniture",
    "not_table_soup",
    "distinct",
)

MAX_ANSWER_WORDS = 4
MAX_PROPER_NAME_WORDS = 6
MAX_ANSWER_CHARS = 48
DEFAULT_MIN_CRITERION_SCORE = 4
DEFAULT_MIN_AVERAGE_SCORE = 4.2
UNMARKED_SHEET_NOTE = (
    "Sheet marks nothing explicitly (no bold, bullet, or numbered points); generated usual cards from prose."
)

# Leading past/present verbs or participles that indicate a predicate fragment
_FRAGMENT_START_VERBS = frozenset(
    {
        "graduated",
        "studied",
        "born",
        "died",
        "served",
        "worked",
        "founded",
        "established",
        "appointed",
        "elected",
        "became",
        "joined",
        "led",
        "wrote",
        "authored",
        "published",
        "built",
        "constructed",
        "designed",
        "discovered",
        "invented",
        "received",
        "awarded",
        "won",
        "moved",
        "returned",
        "married",
        "helped",
        "organized",
        "organised",
        "campaigned",
        "fought",
        "defeated",
        "ruled",
        "reigned",
        "succeeded",
        "attended",
        "completed",
        "earned",
        "obtained",
        "held",
        "headed",
        "chaired",
        "presided",
        "known",
        "famous",
        "noted",
        "remembered",
        "located",
        "situated",
        "based",
        "includes",
        "including",
        "contains",
        "containing",
        "consists",
        "consisting",
        "provides",
        "providing",
        "ensures",
        "ensuring",
        "leads",
        "leading",
        "caused",
        "causing",
        "resulted",
        "resulting",
        "offered",
        "went",
        "sustained",
        "relies",
        "relied",
        "linked",
        "managed",
        "chosen",
        "adopted",
        "came",
        "takes",
        "spreads",
        "vibrate",
        "alters",
        "produces",
        "rearrange",
        "separates",
        "uses",
    }
)

# Dangling trailing words that make an answer or template slot an incomplete unit
_DANGLING_SLOT_ENDINGS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "with",
        "by",
        "as",
        "into",
        "and",
        "or",
        "but",
        "who",
        "which",
        "that",
        "whose",
        "where",
        "when",
        "while",
        "was",
        "were",
        "is",
        "are",
        "had",
        "has",
        "have",
        "been",
    }
)

# Answer unit boundary constraints:
# Never ends on of / the / in / and / at / to / for / with / by (or dangling prepositions/articles/conjunctions)
_FORBIDDEN_ANSWER_ENDINGS = frozenset(
    {
        "of",
        "the",
        "in",
        "and",
        "at",
        "to",
        "for",
        "from",
        "with",
        "by",
        "or",
        "a",
        "an",
        "on",
        "into",
        "as",
    }
)

# Never starts with at / the / and / of (or leading prepositions/articles/conjunctions)
_FORBIDDEN_ANSWER_STARTS = frozenset(
    {"at", "the", "and", "of", "in", "on", "to", "for", "with", "by", "from", "or", "a", "an"}
)

# Common words (articles, pronouns, linking words, ordinary verbs and adjectives, generic nouns) that must never be blanked as an answer
_FORBIDDEN_COMMON_WORD_ANSWERS = frozenset(
    {
        "if",
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "so",
        "yet",
        "nor",
        "for",
        "of",
        "in",
        "on",
        "at",
        "to",
        "from",
        "with",
        "by",
        "as",
        "into",
        "about",
        "between",
        "among",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "under",
        "over",
        "and why",
        "or why",
        "and how",
        "or how",
        "repeat",
        "repeats",
        "repeating",
        "make",
        "made",
        "makes",
        "making",
        "wear",
        "wears",
        "wearing",
        "included",
        "include",
        "includes",
        "including",
        "law",
        "laws",
        "rule",
        "rules",
        "right",
        "rights",
        "fact",
        "facts",
        "part",
        "parts",
        "type",
        "types",
        "kind",
        "kinds",
        "way",
        "ways",
        "thing",
        "things",
        "point",
        "points",
        "line",
        "lines",
        "word",
        "words",
        "form",
        "forms",
        "use",
        "uses",
        "used",
        "using",
        "take",
        "takes",
        "taken",
        "give",
        "gives",
        "given",
        "keep",
        "keeps",
        "kept",
        "put",
        "puts",
        "find",
        "found",
        "show",
        "shows",
        "shown",
        "tell",
        "look",
        "looks",
        "see",
        "seen",
        "done",
        "does",
        "did",
        "work",
        "works",
        "worked",
        "working",
        "help",
        "helps",
        "helped",
        "need",
        "needs",
        "needed",
        "call",
        "called",
        "know",
        "known",
        "come",
        "comes",
        "came",
        "go",
        "goes",
        "went",
        "get",
        "gets",
        "got",
        "set",
        "sets",
        "let",
        "lets",
        "run",
        "runs",
        "ran",
        "begin",
        "begins",
        "began",
        "start",
        "starts",
        "started",
        "end",
        "ends",
        "ended",
        "turn",
        "turns",
        "turned",
        "move",
        "moves",
        "moved",
        "change",
        "changes",
        "changed",
        "place",
        "places",
        "placed",
        "area",
        "areas",
        "region",
        "regions",
        "country",
        "countries",
        "city",
        "cities",
        "state",
        "states",
        "people",
        "person",
        "group",
        "groups",
        "system",
        "systems",
        "process",
        "processes",
        "method",
        "methods",
        "example",
        "examples",
        "result",
        "results",
        "reason",
        "reasons",
        "cause",
        "causes",
        "effect",
        "effects",
        "value",
        "values",
        "number",
        "numbers",
        "amount",
        "amounts",
        "level",
        "levels",
        "rate",
        "rates",
        "time",
        "times",
        "year",
        "years",
        "day",
        "days",
        "today",
        "now",
        "then",
        "here",
        "there",
        "where",
        "when",
        "why",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "theirs",
        "he",
        "him",
        "his",
        "she",
        "her",
        "hers",
        "we",
        "us",
        "our",
        "ours",
        "you",
        "your",
        "yours",
        "one",
        "ones",
        "two",
        "three",
        "first",
        "second",
        "third",
        "many",
        "much",
        "some",
        "any",
        "all",
        "both",
        "each",
        "every",
        "other",
        "others",
        "another",
        "such",
        "same",
        "different",
        "various",
        "several",
        "most",
        "more",
        "less",
        "least",
        "few",
        "fewer",
        "high",
        "higher",
        "highest",
        "low",
        "lower",
        "lowest",
        "large",
        "larger",
        "largest",
        "small",
        "smaller",
        "smallest",
        "big",
        "bigger",
        "biggest",
        "great",
        "greater",
        "greatest",
        "good",
        "better",
        "best",
        "bad",
        "worse",
        "worst",
        "new",
        "old",
        "young",
        "long",
        "short",
        "important",
        "major",
        "minor",
        "main",
        "key",
        "central",
        "primary",
        "basic",
        "common",
        "general",
        "special",
        "specific",
        "certain",
        "clear",
        "free",
        "full",
        "open",
        "closed",
        "fixed",
        "equal",
        "total",
        "whole",
        "single",
        "double",
        "simple",
        "complex",
        "modern",
        "ancient",
        "historic",
        "historical",
        "famous",
        "known",
        "noted",
        "global",
        "local",
        "national",
        "international",
        "public",
        "private",
        "social",
        "political",
        "economic",
        "cultural",
        "industrial",
        "commercial",
        "financial",
        "scientific",
        "chemical",
        "physical",
        "natural",
        "human",
        "world",
        "life",
        "water",
        "air",
        "land",
        "food",
        "power",
        "energy",
        "growth",
        "development",
        "production",
        "trade",
        "industry",
        "industries",
        "business",
        "service",
        "services",
        "center",
        "centre",
        "centres",
        "hub",
        "port",
        "river",
        "sea",
        "ocean",
        "north",
        "south",
        "east",
        "west",
        "northern",
        "southern",
        "eastern",
        "western",
        "capital",
        "government",
        "parliament",
        "councils",
        "courts",
        "institutions",
        "university",
        "universities",
        "college",
        "colleges",
        "school",
        "schools",
        "research",
        "education",
        "science",
        "technology",
        "engineering",
        "medicine",
        "arts",
        "culture",
        "festivals",
        "tourism",
        "finance",
        "banking",
        "shipping",
        "shipbuilding",
        "textiles",
        "manufacturing",
        "commerce",
        "transport",
        "communication",
        "media",
        "publishing",
        "literature",
        "architecture",
        "heritage",
        "history",
        "geography",
        "civics",
        "physics",
        "chemistry",
        "biology",
        "mathematics",
        "maths",
        "algebra",
        "geometry",
        "symbols",
        "symbol",
        "equation",
        "equations",
        "formula",
        "formulas",
        "unit",
        "units",
        "temperature",
        "materials",
        "material",
        "substance",
        "substances",
        "object",
        "objects",
        "body",
        "bodies",
        "heating",
        "cooling",
        "mixing",
        "balancing",
        "testing",
        "measuring",
        "reading",
        "writing",
        "solving",
        "calculating",
        "sustained",
        "relies",
        "relied",
        "georgian-era",
        "victorian-era",
        "medieval",
        "roman",
        "british",
        "english",
        "scottish",
        "welsh",
        "irish",
        "indian",
        "variable",
        "variables",
        "constant",
        "constants",
        "factor",
        "factors",
        "feature",
        "features",
        "property",
        "properties",
        "characteristic",
        "characteristics",
        "condition",
        "conditions",
        "structure",
        "structures",
        "function",
        "functions",
        "role",
        "roles",
        "purpose",
        "purposes",
        "meaning",
        "definition",
        "term",
        "terms",
        "name",
        "names",
        "title",
        "titles",
        "section",
        "sections",
        "chapter",
        "chapters",
        "page",
        "pages",
        "sheet",
        "sheets",
        "table",
        "tables",
        "list",
        "lists",
        "note",
        "notes",
        "summary",
        "review",
        "revision",
        "practice",
        "exercise",
        "exercises",
        "question",
        "questions",
        "answer",
        "answers",
        "solution",
        "solutions",
        "evaluation",
        "assessment",
        "test",
        "tests",
        "exam",
        "exams",
        "experiment",
        "experiments",
        "observation",
        "observations",
        "conclusion",
        "conclusions",
        "procedure",
        "procedures",
        "step",
        "steps",
        "always",
        "never",
        "often",
        "sometimes",
        "usually",
        "generally",
        "mainly",
        "mostly",
        "also",
        "only",
        "even",
        "still",
        "already",
        "just",
        "very",
        "too",
        "quite",
        "rather",
        "almost",
        "nearly",
        "together",
        "apart",
        "instead",
        "however",
        "therefore",
        "thus",
        "hence",
        "because",
        "since",
        "although",
        "though",
        "while",
        "whereas",
        "whether",
        "unless",
        "until",
        "when",
        "whenever",
        "wherever",
        "final",
        "initial",
        "mixed",
    }
)

# Section titles, category labels, or checklist headers that are NEVER valid Key Facts answers
_SECTION_OR_CATEGORY_LABEL_ANSWERS = frozenset(
    {
        "symbols",
        "algebra",
        "science notation",
        "fraction symbols",
        "speed unit",
        "temperature",
        "equation",
        "formula",
        "formula strings",
        "notation checklist",
        "historic industries",
        "major industries",
        "key industries",
        "key leaders",
        "mumbai key leaders",
        "quick revision notes",
        "revision notes",
        "summary notes",
        "study notes",
        "facts to remember",
        "key terms",
        "practice questions",
        "answer key",
        "worked example",
        "solution",
    }
)

# Cut-off proper noun prefix fragments (e.g. "Man Planning Commission")
_CUTOFF_PROPER_PREFIX_RE = re.compile(
    r"\b(?:Man|Men|Tion|Sion|Ment|Ness|Ship|Ing|Ed|Er|Or|Al|Ic|Ive|Ous)\s+[A-Z][a-z]+\s+[A-Z][a-z]+"
)

# Headings / section labels that must never appear inside a question/clue:
# e.g. "1. QUICK REVISION NOTES", "CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN", "RBS HQ"
_HEADING_IN_QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|\b)\d+[.)]\s+[A-Z]{2,}(?:\s+[A-Z]{2,})+\b"),
    re.compile(
        r"\b(?:QUICK\s+REVISION\s+NOTES|REVISION\s+NOTES|SUMMARY\s+NOTES|STUDY\s+NOTES|CHAPTER\s+OUTLINE|EXPERIMENT\s+DESIGN|KEY\s+NOTES)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b[A-Z][A-Z0-9\s&/]+(?:\s*•\s*[A-Z][A-Z0-9\s&/]+){1,}"),
    re.compile(r"\b(?:RBS\s+HQ|[A-Z]{2,6}\s+HQ)\b"),
    re.compile(r"\b[A-Z]{3,}(?:\s+[A-Z]{3,}){2,}\b"),
)

# Generic offline boilerplate templates that must not be emitted in Key Facts mode
_TEMPLATE_SLOT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^Explain\s+(.+?)\s+and\s+its\s+main\s+features\.?$", re.IGNORECASE),
    re.compile(r"^Explain\s+the\s+concept\s+and\s+significance\s+of\s+(.+?)\.?$", re.IGNORECASE),
    re.compile(
        r"^What\s+is\s+meant\s+by\s+(.+?),\s+and\s+what\s+are\s+its\s+key\s+characteristics\??$",
        re.IGNORECASE,
    ),
    re.compile(
        r"^What\s+(?:reason|cause)(?:,\s*reason,?\s*or\s+mechanism|\s+or\s+cause)?\s+is\s+explained\s+regarding\s+(.+?)(?:,\s+and\s+what\s+is\s+its\s+(?:result|effect))?\??$",
        re.IGNORECASE,
    ),
    re.compile(r"^What\s+is\s+the\s+main\s+difference\s+explained\s+regarding\s+(.+?)\??$", re.IGNORECASE),
    re.compile(r"^How\s+is\s+(.+?)\s+used\s+or\s+applied\??$", re.IGNORECASE),
    re.compile(
        r"^What\s+is\s+the\s+chronological\s+order\s+of\s+events\s+or\s+steps\s+described\s+for\s+(.+?)\??$",
        re.IGNORECASE,
    ),
)

# Practice Questions / Answer Key / Check Your Understanding section headings
_PRACTICE_SECTION_HEADING_RE = re.compile(
    r"^(?:#+\s*)?(?:(?:\d+|[A-Z])[.)]\s*)?(?:"
    r"Practice\s+Questions\b.*|"
    r"Answer\s+Key\b.*|Answers?\s+to\s+Practice\s+Questions\b.*|"
    r"Check\s+Your\s+(?:Understanding|Progress)\b.*|"
    r"Quick\s+Check\b.*|"
    r"Exercises?(?:\s+for\s+Practice)?\b.*|Review\s+Questions\b.*|"
    r"Practice\s+sums\b.*|Practice\s*\(no\s+answers\s+here\)\s*:?|"
    r"Fill\s+in\s+the\s+Blanks\b.*|Answer\s+in\s+One\s+Sentence\b.*|"
    r"One\s+Sentence\s+Answers\b.*|Short\s+Answer\s+Questions\b.*|"
    r"Page\s+\d+\s*[—–\-:]\s*(?:Practice\b.*|Mixed\s+calculation\s+practice.*|Graph\s+reading\s+practice.*|Independent\s+mixed\s+worksheet.*|Word\s+problems.*|Mixed\s+review.*|Challenge\s+problems.*|Answer\s+key.*)"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

# End-of-sheet practice/answer-key headings that remain active through numbered answers
_END_MATTER_PRACTICE_HEADING_RE = re.compile(
    r"^(?:#+\s*)?(?:(?:\d+|[A-Z])[.)]\s*)?(?:"
    r"Practice\s+Questions\b.*|"
    r"Answer\s+Key\b.*|Answers?\s+to\s+Practice\s+Questions\b.*|"
    r"Exercises?(?:\s+for\s+Practice)?\b.*|Review\s+Questions\b.*|"
    r"Fill\s+in\s+the\s+Blanks\b.*|Answer\s+in\s+One\s+Sentence\b.*|"
    r"One\s+Sentence\s+Answers\b.*|Short\s+Answer\s+Questions\b.*"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

# Table and snapshot section headings (never build a question from table text)
_TABLE_SECTION_HEADING_RE = re.compile(
    r"^(?:#+\s*)?(?:\d+[.)]\s*)?(?:"
    r"(?:Comparative|Comparison|Quick\s+Comparison|Summary|Reference)\s+(?:Table|Snapshot)\b.*|"
    r"Page\s+\d+\s*[—–\-:]\s*(?:Answered\s+practice\s+table.*|Unanswered\s+practice\s+table.*|Reference\s+table.*|Data\s+table\b.*|Mixed\s+answer\s+table.*|Symbol\s+and\s+extraction\s+checklist.*)"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

# Source lists / URLs
_SOURCE_OR_URL_LINE_RE = re.compile(
    r"(?:https?://\S+|www\.\S+|\b[a-z0-9.-]+\.(?:org|com|edu|gov|net|uk|in)/\S*|"
    r"^(?:Sources?|References?|Bibliography|Citations?|Further\s+Reading|Image\s+credits?|Photo\s+credits?|Courtesy|Practice\s+source)\b)",
    re.IGNORECASE,
)

# Page labels, worksheet headers, synthetic disclaimers, and footers
_PAGE_HEADER_FOOTER_RE = re.compile(
    r"(?:"
    r"\bPage\s+\d+\s+of\s+\d+\b|"
    r"^Page\s+\d+\s*[—–\-:].*$|"
    r"\bCountry\s*-\s*United\s+Kingdom\s+Page\s+\d+\b|"
    r"\bSheet\s+\d+\s*/\s*\d+\b|"
    r"\bStudent\s*:\s*_+\s*Date\s*:\s*_+|"
    r"_{3,}|"
    r"\bSYNTHETIC\s+SAMPLE\b|"
    r"\bNOT\s+OFFICIAL\s+SCHOOL\s+MATERIAL\b|"
    r"\bRepresentative\s+practice\s+text\b|"
    r"\bNot\s+a\s+syllabus\s+claim\b|"
    r"^End\s+of\s+\d+-page\b.*$|"
    r"^Document\s+feature\s+checklist\s*:.*$|"
    r"^Worksheet\s+test\s+copy\b.*$|"
    r"^Grade\s+\d+\s+(?:Maths|Science|Social\s+Studies|History|Civics|Chemistry|Physics|Biology|Geography)\b.*$|"
    r"^\d+-page\s+document\s+for\s+testing\b.*$|"
    r"^This\s+packet\s+mixes\s+worked\s+examples\b.*$|"
    r"^Answers\s+(?:are\s+not\s+supplied|intentionally\s+omitted)\b.*$|"
    r"^No\s+answer\s+key\s+is\s+printed\b.*$|"
    r"^Check\s+(?:your\s+notation|that\s+units\s+and\s+superscripts)\b.*$|"
    r"^Write\s+units\s+with\s+every\s+numerical\s+answer\b.*$|"
    r"^Confirm\s+the\s+PDF\s+reader\s+preserves\b.*$|"
    r"^Read\s+and\s+recognize\s+these\s+characters\b.*$|"
    r"^Powers\s+and\s+chemical\s+subscripts\s*:.*$|"
    r"^¾\s+2½\b.*$"
    r")",
    re.IGNORECASE,
)

# Individual practice / exercise / student prompt lines (including Q1./Q2. and — Ans:/Ans:)
_PRACTICE_OR_EXERCISE_LINE_RE = re.compile(
    r"(?:^(?:(?:\(\d+\)|\d+[.)]|[a-zA-Z][.)])\s*)?(?:"
    r"Practice\s*:|Try\s*:|Study\s+prompt\s*:|Study\s+Tip\b|MEMORY\s+TIP\s*:|"
    r"Questions?\s*:|Read\s+the\s+(?:graph|subscripts)\b.*|Example\s*\d*\s*:|Worked\s+example\s*:|Solution\s*:|"
    r"(?:Write|Calculate|Evaluate|Find|Solve|Define|State|Describe|Compare|Classify|Distinguish|Explain|Mention|Name|Give|Choose|Identify|Convert|Sketch|Label|Trace|Study\s+the\s+simple\s+circuit|Use\s+particles\s+to\s+explain|Use\s+each\s+term|Use\s+the\s+Time|From\s+the\s+table)\b"
    r")|\bFind\s+(?:its\s+|the\s+)?(?:speed|distance|travel\s+time|average\s+speed|area|A|b|v)\b|"
    r"(?:^|\b)(?:Q\.?\s*\d+\s*[:.)]|Question\s*\d+\s*[:.)]|Ans(?:wer)?\s*\d*\s*[:.)])|"
    r"(?:—|–|-)\s*Ans(?:wer)?\s*[:.])",
    re.IGNORECASE,
)

# Meta section labels / diagram callouts that must be dropped and never set current_subject
_META_SECTION_LABEL_RE = re.compile(
    r"^(?:(?:\d+[.)])\s*)?(?:"
    r"QUICK\s+REVISION\s+NOTES|REVISION\s+NOTES|SUMMARY\s+NOTES|STUDY\s+NOTES|"
    r"Facts\s+to\s+Remember|KEY\s+TERMS|Notation\s+checklist|Formula\s+strings\s*:?|"
    r"Schematic\s*\(not\s+to\s+scale\)|Quick\s+Comparison\s+Snapshot\b.*|"
    r"Cell\s*/\s*battery|Bulb|Connecting\s+wire|Closed\s+path|Current\s+direction\b.*"
    r")\s*:?\s*$",
    re.IGNORECASE,
)

_MEMORY_OR_STUDY_TIP_RE = re.compile(
    r"(?:^(?:[•\-\*▪▸◦]\s*)?(?:Memory\s+tip|Quick\s+tip|Study\s+tip|Exam\s+tip|Study\s+prompt|Mnemonic|Remember(?:\s+this|\s+trick|\s+that)?|Tip|Fun\s+fact|Did\s+you\s+know)\b(?:\s+for\s+Grade\s+\d+)?\s*[:\-–—]?|"
    r"\b(?:Memory\s+tip|Quick\s+tip|Study\s+tip|Exam\s+tip|Study\s+prompt|Mnemonic|Remember\s+this|Remember\s+trick)\s*(?:for\s+Grade\s+\d+\s*)?[:\-–—])",
    re.IGNORECASE,
)

# Sheet furniture patterns: practice Q&A ("Q1.", "Q1:", "— Ans:", "Ans:"), memory tips, source credits, card/page labels, headers/footers
_FURNITURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:^|\b)(?:Q\.?\s*\d+\s*[:.)]|Question\s*\d+\s*[:.)]|Ans(?:wer)?\s*\d*\s*[:.)])", re.IGNORECASE),
    re.compile(r"(?:—|–|-)\s*Ans(?:wer)?\s*[:.]", re.IGNORECASE),
    _MEMORY_OR_STUDY_TIP_RE,
    re.compile(
        r"\((?:Source\s*:?\s*)?(?:Britannica|Wikipedia|Encyclop(?:ae|e)dia\s+Britannica|History\s+of\s+[^)]+|NCERT|ICSE|CBSE|PTI|Reuters|AP|Wikimedia[^)]*|Courtesy[^)]*)\)",
        re.IGNORECASE,
    ),
    re.compile(r"\b(?:Source|Courtesy|Photo\s+credit|Image\s+credit)\s*:\s*[A-Z]", re.IGNORECASE),
    re.compile(
        r"(?:^|\b)(?:FULL\s+CARD|HALF\s+CARD|CARD\s+#?\d+|CASE\s+FILE\s*#?\d*|[A-Z]{2,6}\s+HQ|Page\s+\d+(?:\s+of\s+\d+)?|All\s+rights\s+reserved|Not\s+to\s+be\s+republished|Reprint\s+20\d{2}|Practice\s+Questions|Answer\s+Key|Check\s+Your\s+(?:Progress|Understanding)|Exercises?\s+for\s+Practice|Representative\s+practice\s+text|Not\s+a\s+syllabus\s+claim|SYNTHETIC\s+SAMPLE|Schematic\s*\(not\s+to\s+scale\)|https?://\S+|www\.\S+)\b",
        re.IGNORECASE,
    ),
)

_INLINE_SOURCE_CREDIT_RE = re.compile(
    r"\s*\((?:(?:Source|Ref|Credit|Adapted\s+from)\s*:?\s*[^)]+|Britannica|Wikipedia|Encyclop(?:ae|e)dia\s+Britannica|History\s+of\s+[^)]+|NCERT|ICSE|CBSE|PTI|Reuters|AP|Wikimedia[^)]*|Courtesy[^)]*|HQ\s+in\s+[A-Za-z\s]+)\)",
    re.IGNORECASE,
)

_PICTURE_LINE_RE = re.compile(
    r"^(?:\[(?:Image|Picture|Diagram|Figure|Photo|Map|Illustration)[^\]]*\]|!\[[^\]]*\]\([^)]*\)|(?:Figure|Fig\.?|Picture|Image|Diagram)\s+\d*[:.\-–])",
    re.IGNORECASE,
)

_BOLD_SPAN_RE = re.compile(r"\*\*([^*]+)\*\*|__([^_]+)__|<b>([^<]+)</b>", re.IGNORECASE)
_BULLET_OR_NUMBER_PREFIX_RE = re.compile(r"^(?:[•\-\*▪▸◦Æƒ‹\{]|\(\d+\)|\d+[.)]|[a-zA-Z][.)])\s+")

# Formula patterns: e.g. "F = ma", "a = F ÷ m", "1 N = 1 kg·m/s²", "CaCO₃ + 2HCl → CaCl₂ + H₂O + CO₂", "2H₂ + O₂ → 2H₂O", "F = ______"
_FORMULA_CLUE_RE = re.compile(
    r"(?:^|[:\s])(?:"
    r"(?:[0-9.]+\s*)?[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹¼½¾×÷\*+\-/^()·.\s]+(?:\s*(?:=|→|->)\s*)[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()·.\s]*___+[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()·.\s]*|"
    r"___+\s*(?:=|→|->)\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()·. ]+"
    r")(?:\s*$|[.?])"
)
_FORMULA_LINE_RE = re.compile(
    r"^(?:([A-Za-z][A-Za-z0-9\s’'\-–]{1,35}?)\s*:\s*)?"
    r"((?:1\s+[A-Za-z]+|[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]{0,12}|\d+(?:\.\d+)?\s*[×x]\s*10(?:\^\d+|[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)))\s*=\s*"
    r"((?:\d+(?:\.\d+)?\s+)?[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()·.,]+(?:\s*[×÷\*+\-/·]\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹^()/·.,]+)*)\s*(?:\([^)]*\))?\.?$"
)
_CHEM_EQUATION_LINE_RE = re.compile(
    r"^(?:([A-Za-z][A-Za-z0-9\s’'\-–]{1,30}?)\s*:\s*)?"
    r"([0-9]*[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*(?:\+\s*[0-9]*[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*)*)"
    r"\s*(→|->)\s*"
    r"([0-9]*[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*(?:\+\s*[0-9]*[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹()]*\s*)*)\.?$"
)
_WORKED_CALCULATION_LINE_RE = re.compile(
    r"^(?:(?:Solution|Worked\s+example|Example(?:\s+\d+)?|Trial\s+[A-Za-z0-9]+)\s*:\s*)?"
    r"[^?]*?[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]+\s*=\s*[^=?]+=\s*"
    r"([+\-±]?\d+(?:\.\d+)?\s*(?:°C|°F|K\b|km/h|m/s²|m/s|cm/s|g/cm³|kg/m³|km²|m²|cm²|mm²|m³|cm³|mm|cm|km|m\b|mg|kg|mL|L\b|N\b|J\b|W\b|Pa\b|s\b|min\b|h\b|%))\.?$"
)

# General patterns for Good Answer preference order:
_MONTH_NAMES_PATTERN = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)"
)
_FULL_DATE_RE = re.compile(
    rf"\b(?:\d{{1,2}}(?:st|nd|rd|th)?\s+{_MONTH_NAMES_PATTERN}\s+\d{{4}}|{_MONTH_NAMES_PATTERN}\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}|\d{{1,2}}\s+{_MONTH_NAMES_PATTERN})\b"
)
_YEAR_RE = re.compile(r"\b(?:1[0-9]{3}|20[0-2][0-9])(?:\s*[–\-]\s*(?:\d{2}|\d{4}))?\b")
_NUMBER_WITH_UNIT_RE = re.compile(
    r"(?:(?<=^)|(?<=[\s(\[:=]))((?:£\d+(?:\.\d+)?\s*(?:billion|million|bn)\b|[+\-±]?\d+(?:,\d{3})*(?:\.\d+)?(?:\s*[×x]\s*10[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)?\s*(?:°C|°F|K\b|km/h|m/s²|m/s|cm/s|g/cm³|kg/m³|kg·m/s²|kg\.m/s²|km²|m²|cm²|mm²|m³|cm³|mm|cm|km|m\b|mg|kg|mL|L\b|mol/dm³|mol\b|kJ|J\b|kW|W\b|kPa|Pa\b|Hz|MHz|mA|A\b|kV|V\b|Ω|N\b|s\b|min\b|h\b|hr\b|hrs\b|%|jobs\b|visitors\b)))(?=[\s.,;:)\]]|$)"
)

_STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "from",
        "with",
        "by",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "when",
        "where",
        "why",
        "how",
        "explain",
        "define",
        "name",
        "state",
        "identify",
        "describe",
        "meant",
        "key",
        "main",
        "features",
        "characteristics",
        "regarding",
        "explained",
        "reason",
        "cause",
        "result",
        "difference",
        "used",
        "applied",
        "this",
        "that",
        "these",
        "those",
        "its",
        "their",
        "his",
        "her",
        "and",
        "or",
    }
)


def _get_field(obj: Any, *names: str, default: str = "") -> str:
    """Read a string field from either a dict or an object with attributes."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        for name in names:
            val = obj.get(name)
            if val is not None and str(val).strip():
                return str(val).strip()
        return default
    for name in names:
        val = getattr(obj, name, None)
        if val is not None and str(val).strip():
            return str(val).strip()
    return default


def _get_sheet_text(sheet: Any) -> str:
    """Extract full plain text from a sheet (str, dict, or Sheet object)."""
    if sheet is None:
        return ""
    if isinstance(sheet, str):
        return sheet
    if isinstance(sheet, dict):
        if "text" in sheet and isinstance(sheet["text"], str):
            return sheet["text"]
        if "lines" in sheet and isinstance(sheet["lines"], list):
            return "\n".join(
                _get_field(ln, "text", "raw", "content") if not isinstance(ln, str) else ln
                for ln in sheet["lines"]
            )
        if "pages" in sheet and isinstance(sheet["pages"], list):
            return "\n".join(
                _get_field(pg, "text", "raw_text") if not isinstance(pg, str) else pg
                for pg in sheet["pages"]
            )
    for attr in ("full_text", "text", "raw_text", "content"):
        val = getattr(sheet, attr, None)
        if isinstance(val, str) and val.strip():
            return val
    pages = getattr(sheet, "pages", None)
    if isinstance(pages, list) and pages:
        return "\n".join(
            _get_field(pg, "raw_text", "text", "content") if not isinstance(pg, str) else pg
            for pg in pages
        )
    lines = getattr(sheet, "lines", None)
    if isinstance(lines, list):
        return "\n".join(
            _get_field(ln, "text", "raw", "content") if not isinstance(ln, str) else ln
            for ln in lines
        )
    return str(sheet)


def _normalize_spaces(text: str) -> str:
    s = re.sub(r"\s+", " ", text).strip()
    s = re.sub(r"\b(\d{1,2}),\s+(\d{2}),\s+(\d{3})\b", r"\1,\2,\3", s)
    s = re.sub(r"\b(\d{1,3}),\s+(\d{3})\b", r"\1,\2", s)
    return s


def _strip_bold_markup(text: str) -> str:
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    s = re.sub(r"(?<!_)__([A-Za-z0-9][^_]*?[A-Za-z0-9])__(?!_)", r"\1", s)
    s = re.sub(r"</?b>", "", s, flags=re.IGNORECASE)
    return s


def _extract_clue(card: Any) -> str:
    return _get_field(card, "front", "clue", "question", "prompt", "stem")


def _extract_answer(card: Any) -> str:
    return _get_field(card, "answer", "expected_answer", "back", "target", "solution")


def _extract_evidence(card: Any) -> str:
    return _get_field(card, "source_line", "source_evidence", "line", "evidence", "context")


def _extract_subject(card: Any) -> str:
    subj = _get_field(card, "subject", "subject_label", "heading", "section", "entity", "topic", "title")
    if subj:
        return subj
    lbl = _get_field(card, "label")
    if lbl and lbl.lower() not in {"good", "bad"}:
        return lbl
    return ""


def _is_proper_name_phrase(answer: str) -> bool:
    """Return True if `answer` is a multi-word proper name (e.g. 'Bombay Spinning and Weaving Company', 'Jamsetji Tata', 'Satyashodhak Samaj')."""
    ans_clean = _normalize_spaces(answer).strip(" ,.:;()'\"‘’“”")
    words = [w.strip(",.:;()'\"‘’“”") for w in ans_clean.split() if w.strip(",.:;()'\"‘’“”")]
    if not words:
        return False
    connectors = {"of", "the", "and", "in", "on", "at", "for", "to", "de", "la", "von", "van", "&"}
    cap_words = [
        w
        for w in words
        if w.lower() not in connectors and (w[0].isupper() or re.match(r"^(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|St\.)$", w))
    ]
    if not cap_words:
        return False
    if len(words) == 1:
        w0 = words[0]
        return bool(w0[0].isupper() and w0.lower() not in _FORBIDDEN_COMMON_WORD_ANSWERS and w0.lower() not in _STOP_WORDS)
    non_conn = [w for w in words if w.lower() not in connectors]
    return len(cap_words) == len(non_conn)


def _is_heading_or_label_answer(answer: str, source_line: str = "") -> bool:
    """Return True if `answer` is a heading, section title, or category label."""
    ans_clean = _normalize_spaces(_strip_bold_markup(answer)).strip(" ,.:;()'\"‘’“”")
    if not ans_clean:
        return True
    low = ans_clean.lower()
    if low in _SECTION_OR_CATEGORY_LABEL_ANSWERS:
        return True
    if _META_SECTION_LABEL_RE.match(ans_clean) or _PRACTICE_SECTION_HEADING_RE.match(ans_clean) or _TABLE_SECTION_HEADING_RE.match(ans_clean):
        return True
    if re.match(r"^(?:Section|Chapter|Unit|Part|Page|Table|Figure|Sheet|Exercise|Practice|Question|Answer)\s*\d*$", ans_clean, re.IGNORECASE):
        return True
    # All-caps multi-word heading (e.g. "QUICK REVISION NOTES", "KEY LEADERS")
    if len(ans_clean.split()) >= 2 and ans_clean.isupper() and re.search(r"[A-Z]{3,}", ans_clean):
        return True
    if source_line and ":" in source_line:
        lhs = _normalize_spaces(_strip_bold_markup(_BULLET_OR_NUMBER_PREFIX_RE.sub("", source_line.split(":", 1)[0]))).strip(" ,.:;")
        if lhs.lower() == low and low in _SECTION_OR_CATEGORY_LABEL_ANSWERS:
            return True
    return False


def _is_forbidden_common_word_answer(answer: str) -> bool:
    """Return True if `answer` is a common word/filler ('If', 'Repeat', 'Make', 'Wear', 'and why', 'law', 'included', 'variable', 'Practice', 'Evaluation') rather than a key fact."""
    ans_clean = _normalize_spaces(answer).strip(" ,.:;()'\"‘’“”")
    if not ans_clean:
        return True
    low = ans_clean.lower()
    if low in _FORBIDDEN_COMMON_WORD_ANSWERS or low in _SECTION_OR_CATEGORY_LABEL_ANSWERS:
        return True
    if re.match(r"^(?:and|or|but|if|when|while|because)\s+(?:why|how|when|where|what|who|if|that|so)\b", low):
        return True
    if re.match(r"^[A-Za-z]+(?:’s|'s)$", ans_clean):
        return True
    words = ans_clean.split()
    if len(words) == 1:
        w = words[0].strip(",.:;()'\"‘’“”")
        w_low = w.lower()
        if w_low in _STOP_WORDS and not any(ch.isdigit() for ch in w):
            return True
        if w_low in _FRAGMENT_START_VERBS:
            return True
        if w_low.endswith("-era") or (w_low.endswith("ly") and len(w_low) > 4):
            return True
    return False


def _has_invalid_answer_boundaries(answer: str) -> tuple[bool, str]:
    """Check if `answer` is a cut-off phrase:
    - ending on of / the / in / and / at / to / for / with / by
    - starting with at / the / and / of
    - or ending on a possessive / hyphen modifier.
    """
    ans_clean = _normalize_spaces(answer).strip(" ,.:;()'\"‘’“”")
    words = [w.strip(",.:;()'\"‘’“”") for w in ans_clean.split() if w.strip(",.:;()'\"‘’“”")]
    if not words:
        return True, "answer is empty"
    first_low = words[0].lower()
    last_low = words[-1].lower()
    if first_low in _FORBIDDEN_ANSWER_STARTS:
        return True, f"answer {ans_clean!r} starts with forbidden word {words[0]!r} (not a clean complete unit)"
    if last_low in _FORBIDDEN_ANSWER_ENDINGS:
        if last_low == "at" and len(words) >= 2 and words[-2] in {"+", "-", "=", "±"}:
            return False, ""
        return True, f"answer {ans_clean!r} ends on dangling word {words[-1]!r} (not a complete unit)"
    if re.search(r"(?:’s|'s|-)$", ans_clean):
        return True, f"answer {ans_clean!r} ends on a possessive or hyphen modifier (not a complete unit)"
    return False, ""


def _joins_two_table_cells(answer: str, sheet_text: str = "", evidence: str = "") -> bool:
    """Return True if `answer` joins words across two table cells or a cell plus a heading
    (e.g. 'Mumbai Key Leaders', 'Interpretation Higher', 'London Capital', 'Wolff Scottish Parliament').
    """
    ans_clean = _normalize_spaces(answer)
    if "|" in ans_clean or "\t" in ans_clean:
        return True
    words = ans_clean.split()
    if len(words) < 2:
        return False

    combined_source = f"{evidence}\n{sheet_text}".strip()
    if combined_source:
        for idx in range(1, len(words)):
            left_part = re.escape(" ".join(words[:idx]))
            right_part = re.escape(" ".join(words[idx:]))
            cell_join_pat = rf"\b{left_part}\s*(?:\||\t|\s{{3,}}|\n+)\s*{right_part}\b"
            if re.search(cell_join_pat, combined_source, flags=re.IGNORECASE):
                return True

        norm_source = _normalize_spaces(_strip_bold_markup(combined_source))
        escaped_full = re.escape(_strip_bold_markup(ans_clean))
        if "," not in ans_clean and not re.search(escaped_full, norm_source, flags=re.IGNORECASE):
            if all(
                re.search(r"\b" + re.escape(w.strip(",.:;")) + r"\b", norm_source, flags=re.IGNORECASE)
                for w in words
                if w.strip(",.:;")
            ):
                return True

    if re.search(
        r"\b(?:"
        r"[A-Z][a-z]+\s+Key\s+Leaders|Key\s+Leaders\s+[A-Z][a-z]+|"
        r"[A-Z][a-z]+\s+Summary\s+Table|Personality\s+Year|Year\s+Institution|Institution\s+Role|"
        r"Interpretation\s+Higher|Higher\s+Interpretation|"
        r"London\s+Capital|Edinburgh\s+Capital|Cardiff\s+Capital|Belfast\s+Capital|"
        r"Wolff\s+Scottish\s+Parliament|Harland\s+and\s+Wolff\s+Scottish"
        r")\b",
        ans_clean,
    ):
        return True

    return False


def is_good_answer(answer: str, source_line: str = "", sheet: Any = "") -> tuple[bool, str]:
    """Rule-based checker for whether `answer` is ONE complete, short key fact (Step 2 of Prompt 3).

    Returns (True, "") if valid, or (False, reason) for each "never" rule:
    1. Never empty or ungrounded when sheet/source_line is given.
    2. Never a heading, section title, or label.
    3. Never a cut-off phrase (ending on of/the/in/and/at/to/for/with/by, starting with at/the/and/of,
       a bare month when a full date is on the line, or a truncated proper name on the line).
    4. Never words from two different places joined together (two table cells, or a cell plus a heading).
    5. Never a common word (articles, pronouns, linking words, ordinary verbs/adjectives, generic nouns).
    6. Never a whole sentence or more than 4 words (allow up to 6 only for a proper name that can't be shorter,
       e.g. 'Bombay Spinning and Weaving Company').
    """
    ans_clean = _normalize_spaces(_strip_bold_markup(answer or "")).strip(" ,.:;()'\"‘’“”")
    if not ans_clean:
        return False, "empty answer"

    sheet_text = _get_sheet_text(sheet) if sheet else ""
    line_clean = _normalize_spaces(_strip_bold_markup(source_line or ""))

    # Reject answers containing raw table pipes or tabs
    if "|" in ans_clean or "\t" in ans_clean:
        return False, f"joins multiple table cells ({ans_clean!r})"

    # Allow single-letter formula variables (e.g. "a" in "F = m × a") ONLY when source_line is a symbolic formula
    is_single_formula_var = bool(
        len(ans_clean) == 1
        and ans_clean.isalpha()
        and line_clean
        and _FORMULA_LINE_RE.match(_BULLET_OR_NUMBER_PREFIX_RE.sub("", line_clean).strip())
    )
    is_grammar_target = bool(
        line_clean and any(m["text"].lower() == ans_clean.lower() for m in FAMILY_K.find(line_clean))
    )
    is_cause_effect_target = bool(
        line_clean and any(m["text"].lower() == ans_clean.lower() for m in FAMILY_G.find(line_clean))
    )

    # 1. Never a heading, section title, or label
    if _is_heading_or_label_answer(ans_clean, source_line=line_clean):
        return False, f"heading, section title, or label ({ans_clean!r})"

    # 2. Never an explicit common word or linking phrase ("If", "the", "and why", "Repeat", "Make", "Wear", "included", "variable", "law")
    if not is_single_formula_var and not is_grammar_target and (
        ans_clean.lower() in _FORBIDDEN_COMMON_WORD_ANSWERS
        or re.match(
            r"^(?:and|or|but|if|when|while|because)\s+(?:why|how|when|where|what|who|if|that|so)\b",
            ans_clean.lower(),
        )
    ):
        return False, f"common word ({ans_clean!r})"

    # 3. Never a cut-off phrase or cut-in-half expression span (Step 6 of Prompt 8)
    if not is_single_formula_var:
        bad_bounds, bound_reason = _has_invalid_answer_boundaries(ans_clean)
        if bad_bounds:
            return False, f"cut-off phrase: {bound_reason}"
    if _CUTOFF_PROPER_PREFIX_RE.search(ans_clean):
        return False, f"cut-off proper name prefix ({ans_clean!r})"

    if re.match(rf"^{_MONTH_NAMES_PATTERN}$", ans_clean, re.IGNORECASE):
        if not line_clean or _FULL_DATE_RE.search(line_clean):
            return False, f"cut-off date ({ans_clean!r} instead of full date)"

    cut_half, cut_reason = check_cut_in_half_span(ans_clean, source_line=line_clean)
    if cut_half:
        return False, f"cut-off span ({cut_reason})"

    if line_clean and _is_proper_name_phrase(ans_clean):
        m_ext = re.search(
            r"\b"
            + re.escape(ans_clean)
            + r"\s+(College|University|Samaj|Sabha|Committee|Commission|Assembly|Maidan|Company|Congress|Parliament|Cathedral|Castle|Palace|Dockyard|Canal|Treaty|Act|Mission|Movement|Institute|Association|Society|Bank|Exchange)\b",
            line_clean,
        )
        if m_ext:
            return False, f"cut-off proper name ({ans_clean!r} missing {m_ext.group(1)!r})"

    # 4. Never words from two different places joined together (two table cells, or a cell + heading)
    if _joins_two_table_cells(ans_clean, sheet_text=sheet_text, evidence=line_clean):
        return False, f"joins words from two different places or table cells ({ans_clean!r})"

    # 5. Never a common word (articles, pronouns, linking words, ordinary verbs and adjectives)
    if not is_single_formula_var and not is_grammar_target and _is_forbidden_common_word_answer(ans_clean):
        return False, f"common word ({ans_clean!r})"

    words = [w.strip(",.:;()'\"‘’“”") for w in ans_clean.split() if w.strip(",.:;()'\"‘’“”")]
    word_count = len(words)
    if word_count == 1 and line_clean:
        w0 = words[0]
        sent_body = _BULLET_OR_NUMBER_PREFIX_RE.sub("", line_clean).strip()
        first_sent_word = sent_body.split()[0].strip(",.:;()'\"‘’“”") if sent_body.split() else ""
        raw_has_bold = bool(
            re.search(
                r"(?:\*\*|__|<b>)\s*" + re.escape(w0) + r"\s*(?:\*\*|__|</b>)",
                source_line or "",
                re.IGNORECASE,
            )
        )
        is_def_subj = bool(
            re.match(
                rf"^(?:The\s+)?{re.escape(w0)}\s*(?::|is\b|are\b|refers\s+to\b|states\s+that\b|means\b|=)",
                sent_body,
            )
        )
        if (
            w0 == first_sent_word
            and not raw_has_bold
            and not is_def_subj
            and re.search(r"(?:ing|ed|ies|es|s)$", w0)
            and w0.lower()
            not in {
                "wales",
                "scotland",
                "england",
                "london",
                "belfast",
                "cardiff",
                "edinburgh",
                "glasgow",
                "liverpool",
                "manchester",
                "birmingham",
                "leeds",
                "bristol",
                "oxford",
                "cambridge",
                "newcastle",
                "mumbai",
                "india",
                "speed",
                "subscripts",
                "coefficients",
                "reactants",
                "products",
                "particles",
                "elements",
                "compounds",
                "mixtures",
                "molecules",
                "atoms",
                "indicators",
            }
        ):
            return False, f"common sentence-initial word ({ans_clean!r})"

    # 5. Never a whole sentence or more than 4 words (allow up to 6 only for a proper name that can't be shorter)
    if any(p in ans_clean for p in (";", "?", "!")) or (
        ans_clean.endswith(".") and word_count > 3 and not re.match(r"^(?:[A-Z]\.\s*)+[A-Za-z]+$", ans_clean)
    ):
        return False, f"whole sentence or multi-clause statement ({ans_clean!r})"

    lower_words = [w.lower() for w in words]
    if word_count >= 3 and any(
        w in _FRAGMENT_START_VERBS or w in {"is", "was", "were", "are", "because", "which", "that", "whose"}
        for w in lower_words
    ):
        return False, f"contains a verb/clause instead of a short key fact ({ans_clean!r})"

    max_allowed = (
        MAX_PROPER_NAME_WORDS
        if (_is_proper_name_phrase(ans_clean) or is_cause_effect_target)
        else MAX_ANSWER_WORDS
    )
    if word_count > max_allowed or len(ans_clean) > MAX_ANSWER_CHARS:
        return False, f"more than {max_allowed} words ({word_count} words: {ans_clean!r})"

    # 6. Must appear word-for-word on the source line / sheet when provided
    ref_text = sheet_text or line_clean
    if ref_text:
        c_g, r_g = _score_grounded(ans_clean, ref_text)
        if c_g < 5:
            return False, r_g[0] if r_g else f"answer {ans_clean!r} not word-for-word on sheet"

    return True, ""


def _score_grounded(answer: str, sheet_text: str, is_bold_list: bool = False) -> tuple[int, list[str]]:
    """Criterion 1: answer appears word-for-word on the sheet."""
    if not answer:
        return 1, ["grounded: card has an empty answer"]
    if not sheet_text.strip():
        return 1, ["grounded: sheet text is empty"]

    ans_norm = _normalize_spaces(_strip_bold_markup(answer))
    sheet_norm = _normalize_spaces(_strip_bold_markup(sheet_text))

    # Support shared card for bold words printed as one list (comma-separated bold items)
    if is_bold_list or ("," in ans_norm and len(ans_norm.split(",")) >= 2):
        parts = [p.strip() for p in ans_norm.split(",") if p.strip()]
        if len(parts) >= 2 and all(
            re.search(
                (r"\b" if p[0].isalnum() else "") + re.escape(p) + (r"\b" if p[-1].isalnum() else ""),
                sheet_norm,
                flags=re.IGNORECASE,
            )
            for p in parts
        ):
            return 5, []

    # If the answer joins words from two table cells separated by '|', it is not a single grounded span
    if _joins_two_table_cells(ans_norm, sheet_text=sheet_text):
        return 1, [f"grounded: answer {answer!r} joins words from separate table cells"]

    escaped = re.escape(ans_norm)
    if ans_norm[0].isalnum():
        escaped = r"\b" + escaped
    if ans_norm[-1].isalnum():
        escaped = escaped + r"\b"

    if re.search(escaped, sheet_norm, flags=re.IGNORECASE):
        return 5, []

    if ans_norm.lower() in sheet_norm.lower():
        return 4, ["grounded: answer appears only as a substring inside another token on the sheet"]

    return 1, [f"grounded: answer {answer!r} does not appear word-for-word on the sheet"]


def _score_short_answer(
    answer: str,
    clue: str = "",
    sheet_text: str = "",
    evidence: str = "",
    is_bold_list: bool = False,
) -> tuple[int, list[str]]:
    """Criterion 2: answer is a complete unit (word, name, year, number with unit, formula symbol/result, or short term) and never a common word."""
    if not answer:
        return 1, ["short_answer: answer is empty"]

    ans_clean = _normalize_spaces(answer)
    words = ans_clean.split()
    word_count = len(words)

    # Formula lines: blank one symbol or the result ("F = ______" -> "ma"), never a paragraph answer
    if clue and _FORMULA_CLUE_RE.search(_normalize_spaces(clue)):
        ans_without_decimals = re.sub(r"(?<=\d)\.(?=\d)", "", ans_clean)
        if word_count > 3 or len(ans_clean) > 25 or any(p in ans_without_decimals for p in (".", ";", ",")):
            if not re.match(r"^[+\-±]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:\s+\S+)?$", ans_clean):
                return 1, [
                    f"short_answer: formula card must blank one symbol or result, never a paragraph answer ({ans_clean!r})"
                ]

    if is_bold_list:
        parts = [p.strip() for p in ans_clean.split(",") if p.strip()]
        for p in parts:
            ok, reason = is_good_answer(p, source_line=evidence, sheet=sheet_text)
            if not ok:
                return 1, [f"short_answer: bold list item {p!r} invalid ({reason})"]
        return 5, []

    # Step 6 of Prompt 8: reject any blank that cuts a recognised expression span in half
    cut_half, cut_reason = check_cut_in_half_span(ans_clean, source_line=evidence, clue=clue)
    if cut_half:
        return 1, [f"short_answer: cut-off span ({cut_reason})"]

    ok, reason = is_good_answer(ans_clean, source_line=evidence, sheet=sheet_text)
    if not ok:
        return 1, [f"short_answer: {reason}"]

    return 5, []


def _score_clear_question(clue: str, answer: str = "") -> tuple[int, list[str]]:
    """Criterion 3: no headings/section labels inside a question, grammatical question or fill-the-gap card, no template slot filled with a fragment, no cut-off proper nouns."""
    reasons: list[str] = []
    if not clue:
        return 1, ["clear_question: clue is empty"]

    clue_clean = _normalize_spaces(clue)
    is_formula_clue = bool(_FORMULA_CLUE_RE.search(clue_clean))

    if len(clue_clean) < 8 and not is_formula_clue:
        return 1, ["clear_question: clue is empty or too short"]

    # 1. No headings/section labels inside a question
    # ("1. QUICK REVISION NOTES", "CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN", "RBS HQ")
    for h_pat in _HEADING_IN_QUESTION_PATTERNS:
        m_h = h_pat.search(clue_clean)
        if m_h:
            reasons.append(
                f"clear_question: clue contains a heading or section label {m_h.group(0)!r} ({clue_clean!r})"
            )
            return 1, reasons

    # 2. Formula lines: blank one symbol or the result ("F = ______" -> "ma"), never a paragraph answer
    if is_formula_clue and answer:
        ans_clean = _normalize_spaces(answer)
        ans_without_decimals = re.sub(r"(?<=\d)\.(?=\d)", "", ans_clean)
        if len(ans_clean.split()) > 3 or len(ans_clean) > 25 or any(p in ans_without_decimals for p in (".", ";", ",")):
            if not re.match(r"^[+\-±]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:\s+\S+)?$", ans_clean):
                reasons.append(
                    f"clear_question: formula line must blank one symbol or result, never a paragraph answer ({ans_clean!r})"
                )
                return 1, reasons

    # 3. Check for cut-off proper nouns like "Man Planning Commission"
    if _CUTOFF_PROPER_PREFIX_RE.search(clue_clean):
        reasons.append(f"clear_question: clue contains a cut-off proper noun fragment ({clue_clean!r})")
        return 1, reasons

    # 4. Reject generic offline template stems ("Explain X and its main features.", "What reason or cause is explained regarding X...", etc.)
    for pat in _TEMPLATE_SLOT_PATTERNS:
        m = pat.match(clue_clean)
        if m:
            slot = m.group(1).strip(" ,.:;()'\"‘’“”")
            slot_words = [w.strip(",.:;()'\"‘’“”") for w in slot.split() if w.strip(",.:;()'\"‘’“”")]
            if not slot_words:
                reasons.append("clear_question: template slot is empty")
                return 1, reasons
            first_w = slot_words[0].lower()
            last_w = slot_words[-1].lower()
            if first_w in _FRAGMENT_START_VERBS:
                reasons.append(
                    f"clear_question: template slot {slot!r} starts with verb/participle {slot_words[0]!r}"
                )
                return 1, reasons
            if last_w in _DANGLING_SLOT_ENDINGS:
                reasons.append(f"clear_question: template slot {slot!r} ends with dangling word {slot_words[-1]!r}")
                return 1, reasons
            internal_verbs = {"graduated", "studied", "served", "worked", "founded", "was", "were", "is", "are", "had", "did", "went", "look"}
            if any(w.lower() in internal_verbs for w in slot_words):
                reasons.append(f"clear_question: template slot {slot!r} is a verb/sentence fragment")
                return 1, reasons
            if len(slot_words) >= 3 and all(w[0].isupper() for w in slot_words if w) and first_w in {"man", "men", "boy", "girl", "one", "two", "three"}:
                reasons.append(f"clear_question: template slot {slot!r} has a broken proper-noun prefix")
                return 1, reasons
            reasons.append(f"clear_question: clue uses generic boilerplate template ({clue_clean!r})")
            return 1, reasons

    # 5. Also catch inline verb-phrase or clause fragment stuffed into a template stem
    m_inline = re.match(
        r"^(?:Explain|Describe|Define|What\s+is\s+(?:meant\s+by|the\s+significance\s+of|the\s+role\s+of)?|Who\s+was\s+the\s+significance\s+of)\s+([A-Za-z]+)\b",
        clue_clean,
        re.IGNORECASE,
    )
    if m_inline and m_inline.group(1).lower() in _FRAGMENT_START_VERBS:
        reasons.append(
            f"clear_question: ungrammatical question starts template slot with verb fragment {m_inline.group(1)!r} ({clue_clean!r})"
        )
        return 1, reasons

    # Catch ungrammatical "What is <full finite clause>?" or "How did <noun> is/was <verb>?"
    if re.match(
        r"^What\s+is\s+(?:the\s+)?[A-Za-z0-9\s]{4,}\s+(?:graduated|studied|served|founded|established|chaired|born|died|wrote|authored)\b",
        clue_clean,
        re.IGNORECASE,
    ) or re.search(r"\b(?:did|does)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:was|were|is|are|graduated|chaired|founded)\b", clue_clean):
        reasons.append(f"clear_question: ungrammatical question structure ({clue_clean!r}); use a fill-the-gap card instead")
        return 1, reasons

    # Catch broken word order in Wh-template questions (e.g. "Which body or institution Constituent Assembly of India was chaired by Jurist...")
    if re.match(
        r"^(?:Which|What)\s+[a-z]+(?:\s+or\s+[a-z]+)?\s+[A-Z][A-Za-z0-9’'\-–]+(?:\s+(?:of|the|and|in|for|[A-Z][A-Za-z0-9’'\-–]+))*\s+(?:was|were|is|are|did|has|had|chaired|founded|led)\b",
        clue_clean,
    ):
        reasons.append(f"clear_question: broken word order in question stem ({clue_clean!r})")
        return 1, reasons

    if clue_clean.endswith(("...", "…")):
        reasons.append(f"clear_question: truncated question ending with ellipsis ({clue_clean!r})")
        return 1, reasons

    # 6. Check proper ending: question mark '?' or fill-in-the-blank '___'
    has_blank = "___" in clue_clean or "____" in clue_clean
    ends_valid = (
        clue_clean.endswith("?")
        or is_formula_clue
        or (has_blank and (clue_clean.endswith((".", "___", "____", "'", '"', "’", "”", ")")) or "___" in clue_clean))
    )
    if not ends_valid:
        reasons.append(f"clear_question: clue {clue_clean!r} does not end with '?' or contain a valid fill-in-the-blank")
        return 1, reasons

    # Catch double spaces/punctuation or broken mid-word hyphenation
    if re.search(r"[A-Za-z]-\s+[a-z]", clue_clean) or ".." in clue_clean.replace("...", ""):
        reasons.append("clear_question: clue contains broken hyphenation or malformed punctuation")
        return 1, reasons

    return 5, []


def _score_names_subject(clue: str, answer: str, subject_hint: str = "") -> tuple[int, list[str]]:
    """Criterion 4: the clue identifies who/what it is about without containing the answer."""
    reasons: list[str] = []
    if not clue:
        return 1, ["names_subject: clue is empty"]

    clue_norm = _normalize_spaces(clue)
    ans_norm = _normalize_spaces(answer)
    is_formula_clue = bool(_FORMULA_CLUE_RE.search(clue_norm))

    # 1. Clue must not leak the answer
    if ans_norm:
        escaped_ans = re.escape(ans_norm)
        if ans_norm[0].isalnum():
            escaped_ans = r"\b" + escaped_ans
        if ans_norm[-1].isalnum():
            escaped_ans = escaped_ans + r"\b"
        if re.search(escaped_ans, clue_norm, flags=re.IGNORECASE):
            reasons.append(f"names_subject: clue leaks the answer {ans_norm!r}")
            return 1, reasons

    # Symbolic formula clues like "F = ______" or "2H₂ + O₂ → ______" identify the formula LHS directly
    if is_formula_clue:
        return 5, []

    # 2. Clue must not start with a subjectless verb/participle fragment
    # (e.g. "Situated on the ______ in southeastern England." without saying which city)
    first_clause = re.split(r"[.!?;]", clue_norm, maxsplit=1)[0].strip()
    if re.match(r"^(?:He|She|It|They|His|Her|Their|Him|Them)\b", first_clause, flags=re.IGNORECASE):
        reasons.append(f"names_subject: clue starts with dangling pronoun without naming who/what it is about ({clue_norm!r})")
        return 1, reasons

    clue_body_no_bullet = _BULLET_OR_NUMBER_PREFIX_RE.sub("", clue_norm).strip()
    first_word_clean = clue_body_no_bullet.split()[0].strip(",.:;()'\"‘’“”").lower() if clue_body_no_bullet.split() else ""
    if first_word_clean in _FRAGMENT_START_VERBS or re.match(
        r"^(?:Was\s+a|Was\s+the|Continues\s+to|Home\s+to\s+the|Seat\s+of\s+the|Grew\s+to|Rose\s+as|Made\s+a)\b",
        clue_body_no_bullet,
        flags=re.IGNORECASE,
    ):
        reasons.append(
            f"names_subject: clue starts with predicate fragment {first_word_clean!r} without naming its subject ({clue_norm!r})"
        )
        return 1, reasons

    clue_without_first = re.sub(
        r"^(?:What|Which|Who|Whom|Whose|When|Where|Why|How|In|On|At|During|After|Before|From|To|By|For|Through|Into|Under|Name|Identify|State|Complete)\b\s*",
        "",
        clue_norm,
        flags=re.IGNORECASE,
    )
    has_proper_noun = bool(re.search(r"\b[A-Z][a-z]{2,}\b", clue_without_first))
    content_tokens = [
        w.lower()
        for w in re.findall(r"[A-Za-z]{3,}", clue_norm)
        if w.lower() not in _STOP_WORDS and w.lower() not in _FRAGMENT_START_VERBS
    ]

    # Reject dangling pronouns when no proper noun or subject is named in the clue
    has_dangling_pronoun = bool(
        re.search(r"\b(?:he|she|they|him|her|them|his|hers|their|it)\b", clue_norm, flags=re.IGNORECASE)
    )
    if has_dangling_pronoun and not has_proper_noun:
        reasons.append(f"names_subject: clue uses a pronoun without naming who/what it is about ({clue_norm!r})")
        return 1, reasons

    if subject_hint:
        subj_tokens = [
            w.lower() for w in re.findall(r"[A-Za-z]{3,}", subject_hint) if w.lower() not in _STOP_WORDS
        ]
        if (
            subj_tokens
            and ans_norm.lower() not in subject_hint.strip().lower()
            and not any(t in clue_norm.lower() for t in subj_tokens)
            and not has_proper_noun
            and len(content_tokens) < 4
        ):
            reasons.append(
                f"names_subject: clue does not mention its subject {subject_hint!r} ({clue_norm!r})"
            )
            return 1, reasons

    if not has_proper_noun and len(content_tokens) < 2:
        reasons.append(f"names_subject: clue lacks a clear subject noun or entity ({clue_norm!r})")
        return 1, reasons

    return 5, []


def _extract_practice_section_lines(sheet_text: str) -> set[str]:
    """Return normalized lines that appear under 'Practice Questions' or 'Answer Key' headings on the sheet."""
    if not sheet_text:
        return set()
    in_practice = False
    practice_is_end_matter = False
    practice_lines: set[str] = set()
    for raw_ln in sheet_text.splitlines():
        s = _normalize_spaces(raw_ln)
        if not s:
            continue
        if _PRACTICE_SECTION_HEADING_RE.match(s):
            in_practice = True
            if _END_MATTER_PRACTICE_HEADING_RE.match(s):
                practice_is_end_matter = True
            practice_lines.add(s.lower())
            continue
        if in_practice and not practice_is_end_matter:
            if re.match(r"^Page\s+\d+\s*[—–\-:]", s, re.IGNORECASE):
                in_practice = False
                continue
            if re.match(r"^\d+[.)]\s+[A-Z]", s) and not _PRACTICE_OR_EXERCISE_LINE_RE.search(s) and "?" not in s:
                in_practice = False
                continue
        if in_practice:
            practice_lines.add(s.lower())
            stripped_bullet = _BULLET_OR_NUMBER_PREFIX_RE.sub("", s).strip()
            if stripped_bullet:
                practice_lines.add(stripped_bullet.lower())
                practice_lines.add(_normalize_spaces(_strip_bold_markup(stripped_bullet)).lower())
            practice_lines.add(_normalize_spaces(_strip_bold_markup(s)).lower())
    return practice_lines


def _score_not_furniture(clue: str, answer: str, evidence: str = "", sheet_text: str = "") -> tuple[int, list[str]]:
    """Criterion 5: answer/clue not taken from Practice Questions / Answer Key sections, Q1. / — Ans: lines, memory tips, source credits, card/page labels, or headers/footers."""
    reasons: list[str] = []
    combined_parts = [("clue", clue), ("answer", answer), ("evidence", evidence)]

    for label, text in combined_parts:
        if not text:
            continue
        for pat in _FURNITURE_PATTERNS:
            if pat.search(text):
                reasons.append(f"not_furniture: {label} contains sheet furniture/Q&A/credit/tip ({text!r})")
                return 1, reasons
        if re.search(
            r"\b(?:Remember\s+the\s+order|Make\s+a\s+simple\s+mind-map|Revise\s+the\s+comparative\s+table|Think\s*:\s*[“\"'‘])",
            text,
            re.IGNORECASE,
        ):
            reasons.append(f"not_furniture: {label} is a memory or study tip ({text!r})")
            return 1, reasons

    # Check if the card's source line or clue comes from under a "Practice Questions" or "Answer Key" heading
    practice_lines = _extract_practice_section_lines(sheet_text)
    if practice_lines:
        for label, text in (("evidence", evidence), ("clue", clue)):
            norm_t = _normalize_spaces(text).lower()
            plain_t = _normalize_spaces(_strip_bold_markup(_BULLET_OR_NUMBER_PREFIX_RE.sub("", text))).lower()
            if (norm_t and norm_t in practice_lines) or (plain_t and plain_t in practice_lines):
                reasons.append(
                    f"not_furniture: {label} comes from under a 'Practice Questions' or 'Answer Key' section ({text!r})"
                )
                return 1, reasons

    # Also check if answer itself is a bare source credit or layout label
    if re.match(
        r"^\(?(?:Britannica|Wikipedia|NCERT|ICSE|CBSE|Source|Memory\s+Tip|Study\s+Tip|FULL\s+CARD|HALF\s+CARD|CARD\s*\d*|Practice\s+Questions|Answer\s+Key)\)?$",
        answer.strip(),
        re.IGNORECASE,
    ):
        reasons.append(f"not_furniture: answer {answer!r} is a source credit or layout label")
        return 1, reasons

    return 5, []


def _score_not_table_soup(clue: str, answer: str, evidence: str = "", sheet_text: str = "") -> tuple[int, list[str]]:
    """Criterion 6: answer/clue isn't a run of several table cells or joined words from two table cells."""
    reasons: list[str] = []

    if "|" in (answer or "") or "\t" in (answer or ""):
        return 1, [f"not_table_soup: answer contains multiple pipe/tab-delimited table cells ({answer!r})"]

    for label, text in (("answer", answer), ("clue", clue), ("evidence", evidence)):
        if not text:
            continue
        if text.count("|") >= 2 or len(re.findall(r"\t+|\s{3,}", text)) >= 2:
            if label in ("answer", "clue"):
                reasons.append(f"not_table_soup: {label} contains raw multi-column table cells ({text!r})")
                return 1, reasons

    # Reject answers that join words from two table cells (e.g. "Mumbai Key Leaders")
    if _joins_two_table_cells(answer, sheet_text=sheet_text, evidence=evidence):
        reasons.append(f"not_table_soup: answer {answer!r} joins words from two table cells")
        return 1, reasons

    years_in_ans = re.findall(r"\b(?:1[5-9]\d{2}|20\d{2})\b", answer)
    if len(years_in_ans) >= 2 and not re.match(r"^\d{4}\s*[–\-—]\s*\d{2,4}$", answer.strip()):
        reasons.append(f"not_table_soup: answer {answer!r} concatenates multiple table years/cells")
        return 1, reasons

    ans_tokens = answer.split()
    if len(ans_tokens) >= 4 and sum(1 for t in ans_tokens if any(ch.isdigit() for ch in t)) >= 1 and sum(
        1 for t in ans_tokens if t[0].isupper()
    ) >= 2:
        reasons.append(f"not_table_soup: answer {answer!r} looks like a run of multiple table cells")
        return 1, reasons

    if answer.count(":") >= 1 and len(ans_tokens) >= 3:
        reasons.append(f"not_table_soup: answer {answer!r} contains key-value table/list formatting")
        return 1, reasons

    return 5, []


def is_good_front(
    front: Any,
    answer: str = "",
    source_line: str = "",
    sheet: Any = "",
    subject: str = "",
) -> tuple[bool, str]:
    """Rule-based checker for the front/question of a Key Facts card (Prompt 4 & Step 2 of Prompt 5).

    Accepts either a card dict/object or a front string, and returns (True, "") if valid or
    (False, reason) if any front rule fails:
    - no boilerplate templates, broken word order, or headings/section labels in the question;
    - names its subject without giving the answer away or starting with a dangling pronoun;
    - not taken from practice Q&A, memory tips, source credits, or table rows.
    """
    if isinstance(front, dict) or (not isinstance(front, str) and front is not None):
        card_obj = front
        front_str = _extract_clue(card_obj)
        ans_str = answer or _extract_answer(card_obj)
        ev_str = source_line or _extract_evidence(card_obj)
        subj_str = subject or _extract_subject(card_obj)
    else:
        front_str = str(front or "")
        ans_str = answer
        ev_str = source_line
        subj_str = subject

    sheet_text = _get_sheet_text(sheet) if sheet else ""

    c_clear, r_clear = _score_clear_question(front_str, answer=ans_str)
    if c_clear < 5:
        return False, r_clear[0] if r_clear else "front fails clear_question check"

    c_subj, r_subj = _score_names_subject(front_str, ans_str, subj_str)
    if c_subj < 5:
        return False, r_subj[0] if r_subj else "front fails names_subject check"

    c_furn, r_furn = _score_not_furniture(front_str, "", ev_str, sheet_text=sheet_text)
    if c_furn < 5:
        return False, r_furn[0] if r_furn else "front fails not_furniture check"

    c_tbl, r_tbl = _score_not_table_soup(front_str, "", ev_str, sheet_text=sheet_text)
    if c_tbl < 5:
        return False, r_tbl[0] if r_tbl else "front fails not_table_soup check"

    return True, ""


def _content_tokens(text: str) -> set[str]:
    return {
        w.lower()
        for w in re.findall(r"[A-Za-z0-9]{3,}", text)
        if w.lower() not in _STOP_WORDS
    }


def _strip_subject_prefix_from_clue(clue: str, subject: str) -> str:
    """Strip a leading '<subject>: ' or '<subject> — ' prefix when comparing distinctness of two different facts under the same section."""
    c = _normalize_spaces(clue)
    s = _normalize_spaces(subject)
    if s:
        for sep in (":", "—", "–", "-"):
            prefix = f"{s.lower()}{sep}" if sep == ":" else f"{s.lower()} {sep}"
            if c.lower().startswith(prefix):
                return c[len(prefix) :].strip()
    return c


def _score_distinct(card: Any, prior_cards: list[Any]) -> tuple[int, list[str]]:
    """Criterion 7: no near-duplicate of another card in the same case file (no two cards test the same fact,
    including reciprocal/inverse cards across sentences or prose vs. table).
    """
    if not prior_cards:
        return 5, []

    clue = _normalize_spaces(_extract_clue(card)).lower()
    answer = _normalize_spaces(_extract_answer(card)).lower()
    subj = _extract_subject(card)
    clue_body = _strip_subject_prefix_from_clue(clue, subj).lower()
    clue_tokens = _content_tokens(clue_body) or _content_tokens(clue)

    for idx, other in enumerate(prior_cards):
        other_clue = _normalize_spaces(_extract_clue(other)).lower()
        other_answer = _normalize_spaces(_extract_answer(other)).lower()
        other_subj = _extract_subject(other)
        other_body = _strip_subject_prefix_from_clue(other_clue, other_subj).lower()

        if clue and clue == other_clue:
            return 1, [f"distinct: exact duplicate clue of card #{idx + 1}"]

        if answer and answer == other_answer and (("=" in clue and "=" in other_clue) or ("→" in clue and "→" in other_clue)):
            return 1, [f"distinct: tests the same formula answer ({answer!r}) as card #{idx + 1}"]

        # Same (subject, answer) or overlapping answer tokens for the same subject across prose and table
        if answer and other_answer and subj and other_subj and subj.lower() == other_subj.lower():
            if answer == other_answer:
                return 1, [
                    f"distinct: tests the same answer ({answer!r}) for subject {subj!r} as card #{idx + 1}"
                ]
            cand_is_table = " | " in _extract_evidence(card) or " — " in _extract_clue(card)
            other_is_table = " | " in _extract_evidence(other) or " — " in _extract_clue(other)
            ans_toks = _content_tokens(answer.replace("n. ireland", "northern ireland"))
            other_ans_toks = _content_tokens(other_answer.replace("n. ireland", "northern ireland"))
            if (
                (cand_is_table or other_is_table)
                and ans_toks
                and other_ans_toks
                and (ans_toks <= other_ans_toks or other_ans_toks <= ans_toks)
            ):
                return 1, [
                    f"distinct: overlapping answer ({answer!r} vs {other_answer!r}) for subject {subj!r} as card #{idx + 1}"
                ]

        # Reciprocal / inverse fact repeat:
        # e.g. Card A: "Harland and Wolff shipyard built the ______" (ans: "RMS Titanic")
        #      Card B: "______ shipyard built the RMS Titanic" (ans: "Harland and Wolff")
        if (
            answer
            and other_answer
            and len(answer) >= 2
            and len(other_answer) >= 2
            and answer != other_answer
            and re.search(r"\b" + re.escape(answer) + r"\b", other_body)
            and re.search(r"\b" + re.escape(other_answer) + r"\b", clue_body)
        ):
            shared_ctx = clue_tokens & (_content_tokens(other_body) or _content_tokens(other_clue))
            if shared_ctx or (subj and other_subj and subj.lower() == other_subj.lower()):
                return 1, [
                    f"distinct: tests the same underlying fact in reverse ({answer!r} <-> {other_answer!r}) as card #{idx + 1}"
                ]

        other_tokens = _content_tokens(other_body) or _content_tokens(other_clue)
        if clue_tokens and other_tokens:
            min_len = min(len(clue_tokens), len(other_tokens))
            overlap = len(clue_tokens & other_tokens) / max(1, min_len)
            if answer and answer == other_answer and overlap >= 0.5:
                return 1, [
                    f"distinct: same answer ({answer!r}) and overlapping clue ({overlap:.0%}) with card #{idx + 1}"
                ]
            if min_len >= 3 and overlap >= 0.8:
                return 1, [f"distinct: clue has {overlap:.0%} token overlap with card #{idx + 1}"]

    return 5, []


class CardScoreResult(dict):
    """Unified score_card result supporting both dict access
    (`res["scores"]`, `res["overall"]`, `res["accepted"]`, `res["reasons"]`, `res["grounded"]`, ...)
    and 2-tuple unpacking (`scores, reasons = score_card(card, sheet)`).
    """

    def __iter__(self):
        yield self["scores"]
        yield self["reasons"]


def score_card(
    card: Any,
    sheet: Any,
    *,
    prior_cards: list[Any] | None = None,
) -> CardScoreResult:
    """Step 2 of Prompt 5: Combine is_good_answer (Prompt 3) and is_good_front (Prompt 4) with the
    7 rule-based criteria and return `{scores per criterion 1–5, overall, accepted: true/false, reasons}`.

    A card is accepted ONLY if no rule fails. A failing rule sets that criterion to 1 and the card
    to rejected — no averaging a hard failure away with high scores elsewhere.
    """
    clue = _extract_clue(card)
    answer = _extract_answer(card)
    evidence = _extract_evidence(card)
    subject_hint = _extract_subject(card)
    sheet_text = _get_sheet_text(sheet)
    is_bold_list = bool(isinstance(card, dict) and card.get("is_bold_list"))

    scores: dict[str, int] = {}
    reasons: list[str] = []

    c1, r1 = _score_grounded(answer, sheet_text, is_bold_list=is_bold_list)
    scores["grounded"] = 1 if c1 < 5 else 5
    reasons.extend(r1)

    c2, r2 = _score_short_answer(
        answer,
        clue=clue,
        sheet_text=sheet_text,
        evidence=evidence,
        is_bold_list=is_bold_list,
    )
    scores["short_answer"] = 1 if c2 < 5 else 5
    reasons.extend(r2)

    c3, r3 = _score_clear_question(clue, answer=answer)
    scores["clear_question"] = 1 if c3 < 5 else 5
    reasons.extend(r3)

    c4, r4 = _score_names_subject(clue, answer, subject_hint)
    scores["names_subject"] = 1 if c4 < 5 else 5
    reasons.extend(r4)

    c5, r5 = _score_not_furniture(clue, answer, evidence, sheet_text=sheet_text)
    scores["not_furniture"] = 1 if c5 < 5 else 5
    reasons.extend(r5)

    c6, r6 = _score_not_table_soup(clue, answer, evidence, sheet_text=sheet_text)
    scores["not_table_soup"] = 1 if c6 < 5 else 5
    reasons.extend(r6)

    c7, r7 = _score_distinct(card, prior_cards or [])
    scores["distinct"] = 1 if c7 < 5 else 5
    reasons.extend(r7)

    # Explicitly enforce is_good_answer and is_good_front so no rule failure can ever slip through
    if not is_bold_list:
        ok_ans, ans_reason = is_good_answer(answer, source_line=evidence, sheet=sheet_text)
        if not ok_ans:
            if "grounded:" in ans_reason or "not word-for-word" in ans_reason:
                scores["grounded"] = 1
            elif "table" in ans_reason:
                scores["not_table_soup"] = 1
            else:
                scores["short_answer"] = 1
            if not any(ans_reason in r for r in reasons):
                reasons.append(f"short_answer: {ans_reason}")

    ok_front, front_reason = is_good_front(
        clue,
        answer=answer,
        source_line=evidence,
        sheet=sheet_text,
        subject=subject_hint,
    )
    if not ok_front:
        if front_reason.startswith("names_subject:"):
            scores["names_subject"] = 1
        elif front_reason.startswith("not_furniture:"):
            scores["not_furniture"] = 1
        elif front_reason.startswith("not_table_soup:"):
            scores["not_table_soup"] = 1
        else:
            scores["clear_question"] = 1
        if not any(front_reason in r for r in reasons):
            reasons.append(front_reason)

    # Prompt 9 Step 4: Enforce Checks 1–6 on every question / front
    card_template = _get_field(card, "template")
    if not is_bold_list:
        ok_q, q_reasons = check_question_card(
            clue,
            answer,
            source_sentence=evidence,
            subject_label=subject_hint,
            template=card_template,
            sheet_text=sheet_text,
        )
        if not ok_q:
            for qr in q_reasons:
                if qr.startswith(("check_1_giveaway:", "check_2_subject:")):
                    scores["names_subject"] = 1
                else:
                    scores["clear_question"] = 1
                if not any(qr in r for r in reasons):
                    reasons.append(qr)

    accepted = all(v == 5 for v in scores.values()) and len(reasons) == 0
    overall = round(sum(scores.values()) / max(1, len(scores)), 2) if accepted else 1.0

    result = CardScoreResult(
        scores=scores,
        overall=overall,
        accepted=accepted,
        reasons=reasons,
        **scores,
    )
    return result


def is_card_acceptable(
    scores: dict[str, Any],
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
) -> bool:
    """Return True if no rule failed and all 7 criteria meet the minimum threshold and average score."""
    if not scores:
        return False
    if "accepted" in scores and isinstance(scores.get("scores"), dict):
        crit_scores = scores["scores"]
        if not scores["accepted"]:
            return False
    else:
        crit_scores = {k: v for k, v in scores.items() if k in CRITERIA and isinstance(v, (int, float))}
    if not crit_scores:
        return False
    if any(v < min_criterion_score for v in crit_scores.values()):
        return False
    avg = sum(crit_scores.values()) / len(crit_scores)
    return avg >= min_average_score


_NAME_DATES_TITLE_RE = re.compile(
    r"^(?:(?:\d+|[A-Z])[.)]\s*)?((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|Smt\.|Lokmanya|Mahatma)\s+)?[A-Z][A-Za-z.\s’'\-]{2,38}?)\s*"
    r"\(\s*(\d{3,4}\s*[–\-—]\s*(?:\d{2,4}|present))\s*\)\s*[–—\-:]\s*(.+)$"
)

_DIAGRAM_CALLOUT_LABEL_RE = re.compile(
    r"^(?:Schematic\s*\(not\s+to\s+scale\)|Cell\s*/\s*battery|Bulb|Connecting\s+wire|Closed\s+path|Current\s+direction\b.*)$",
    re.IGNORECASE,
)

_HEADING_CONNECTOR_WORDS = frozenset(
    {
        "of",
        "and",
        "in",
        "on",
        "to",
        "for",
        "the",
        "a",
        "an",
        "with",
        "by",
        "or",
        "at",
        "from",
        "into",
        "around",
        "us",
        "vs",
    }
)


def is_name_with_dates_and_title_line(line: str) -> tuple[bool, str]:
    """Return `(True, clean_subject)` if `line` is a `'Name (dates) – Title'` line
    (e.g. `'Savitribai Phule (1831–1897) – Pioneer of Women\\'s Education in Maharashtra'`).
    Per Prompt 2, such a line counts as BOTH a subject heading AND a fact line.
    """
    s_plain = _normalize_spaces(_strip_bold_markup(_INLINE_SOURCE_CREDIT_RE.sub("", line or "")))
    m = _NAME_DATES_TITLE_RE.match(s_plain)
    if not m:
        return False, ""
    subj = _clean_subject_heading(m.group(1))
    title_part = m.group(3).strip()
    if subj and title_part and len(title_part.split()) >= 2:
        return True, subj
    return False, ""


def is_sheet_furniture_or_heading(line: str) -> bool:
    """Return True if a sheet line is furniture (Q&A, memory tip, credit, card/page label, footer, URL, picture, unanswered question, table text) or a bare/numbered heading."""
    s = _normalize_spaces(line)
    if not s:
        return True
    # A "Name (dates) – Title" line is kept as a fact line (and also sets subject)
    is_ndt, _ = is_name_with_dates_and_title_line(s)
    if is_ndt:
        return False
    s_plain = _strip_bold_markup(s)
    s_no_bullet = re.sub(r"^(?:[•\-\*▪▸◦]|\(\d+\)|\d+[.)])\s*", "", s_plain).strip()
    # Worked calculations with a taught result ("Solution: Speed = 120 ÷ 2 = 60 km/h.") and chemical equations ("Equation: 2H2 + O2 -> 2H2O") are kept as formula facts
    if "?" not in s and not re.search(r"\bFind\s+", s, re.IGNORECASE):
        if _CHEM_EQUATION_LINE_RE.match(s_no_bullet) or _WORKED_CALCULATION_LINE_RE.match(s_no_bullet):
            return False
    if (
        _PRACTICE_SECTION_HEADING_RE.match(s)
        or _TABLE_SECTION_HEADING_RE.match(s)
        or _META_SECTION_LABEL_RE.match(s)
        or _DIAGRAM_CALLOUT_LABEL_RE.match(s)
        or _SOURCE_OR_URL_LINE_RE.search(s)
        or _PAGE_HEADER_FOOTER_RE.search(s)
        or _PRACTICE_OR_EXERCISE_LINE_RE.search(s)
    ):
        return True
    for pat in _FURNITURE_PATTERNS:
        if pat.search(s):
            return True
    if _PICTURE_LINE_RE.search(s):
        return True
    # Any line with table pipes or tabs or unanswered question mark
    if "|" in s or "\t" in s:
        return True
    if "?" in s and "Ans" not in s:
        return True
    # Formula lines (e.g. "F = ma" or "Speed = Distance ÷ Time") are NOT headings
    if _FORMULA_LINE_RE.match(s_no_bullet) or _CHEM_EQUATION_LINE_RE.match(s_no_bullet):
        return False
    # If the line has multiple bold items printed as one list (e.g. "**Cotton**, **Jute**, **Tea**"), it is a marked list, not a heading
    bold_matches = [
        (m.group(1) or m.group(2) or m.group(3)).strip()
        for m in _BOLD_SPAN_RE.finditer(s)
        if (m.group(1) or m.group(2) or m.group(3))
    ]
    if len(bold_matches) >= 2:
        return False
    # Bullet points starting with a bullet glyph ("• ...") are content notes, not section headings
    if re.match(r"^[•▪▸◦\*]\s+", s):
        return False
    # Numbered title or bare heading without a finite verb or colon definition
    # (e.g. "1. LONDON – Capital of the United Kingdom & England", "2. States of Matter", "Prominent Personalities of Mumbai", "Dadabhai Naoroji (1825–1917)")
    s_no_num = re.sub(r"^(?:#+\s*|\(\d+\)\s*|(?:[IVXLCDM]+|\d+|[A-Z])[.)]\s*)", "", s_plain).strip()
    s_no_dates = re.sub(r"\(\s*\d{3,4}\s*[–\-—]\s*\d{2,4}\s*\)", "", s_no_num).strip()
    words = s_no_dates.split()
    if not words:
        return True

    # Incomplete wrapped sentence line ending with comma or dangling article/preposition/conjunction is NOT a heading
    if s_plain.endswith(",") or re.search(
        r"(?:,\s+|\s+)(?:the|a|an|and|or|but|while|where|which|who|whose|when|in|on|at|to|for|with|by|from|as|of|into|during|after|before|under|over|between|through|against|following|including)$",
        s_plain,
        re.IGNORECASE,
    ):
        return False

    # Short Title-Case or ALL-CAPS heading without a trailing full stop (e.g. "2. States of Matter", "4. Changes of State", "8. Physical and Chemical Changes"), or 1–3 word unpunctuated subheading ("Physical change", "Chemical change", "Solids and liquids")
    if (
        not s_plain.endswith(".")
        and ":" not in s_no_dates
        and "=" not in s_no_dates
        and "→" not in s_no_dates
        and "->" not in s_no_dates
        and len(words) <= 10
    ):
        if len(words) <= 3 and s_no_dates[0].isupper():
            return True
        content_words = [
            w.strip(",;()'\"‘’“”–—-")
            for w in words
            if w.strip(",;()'\"‘’“”–—-") and w.strip(",;()'\"‘’“”–—-").lower() not in _HEADING_CONNECTOR_WORDS
        ]
        if content_words and all(w[0].isupper() for w in content_words if w[0].isalpha()):
            return True

    has_verb = bool(
        re.search(
            r"\b(?:is|are|was|were|has|have|had|graduated|studied|born|died|served|worked|founded|established|appointed|elected|became|joined|led|wrote|authored|published|built|discovered|invented|chaired|presided|known|called|states|refers|occurs|dissociates|defied|marched|proclaimed|applied|adopted|came|moved|signed|enacted|launched|started|began|opened|held|met|attended|participated|organized|organised|boycotted|arrested|gathered|passed|declared|announced|demanded|opposed|supported|formed|created|introduced|constructed|designed|completed|saw|witnessed|received|won|achieved|gained|captured|seized|occupied|defeated|abolished|banned|remained|continued|lasted|ended|resulted|caused|triggered|sparked|marked|celebrated|honoured|honored|lived|settled|sailed|crossed|reached|arrived|left|protects?|describes?|introduces?|begins?|derives?|establishes?|makes?|carries|interprets?|resolves?|keeps?|takes?|spreads?|consists?|vibrate|changes?|contains?|separates?|uses?|alters?|produces?|rearrange|form|travels?|covers?|moves?)\b",
            s_no_dates,
            re.IGNORECASE,
        )
    )
    if (
        not has_verb
        and not s_plain.endswith(".")
        and ":" not in s_no_dates
        and "|" not in s_no_dates
        and "=" not in s_no_dates
        and "→" not in s_no_dates
        and "->" not in s_no_dates
        and len(words) <= 10
    ):
        return True
    return False


def _clean_subject_heading(heading: str) -> str:
    """Clean a section/person heading by stripping life-span dates, numbered prefixes, and card/page labels."""
    h = _INLINE_SOURCE_CREDIT_RE.sub("", _strip_bold_markup(heading or ""))
    h = re.sub(r"^(?:#+\s*|(?:[IVXLCDM]+|\d+|[A-Z])[.)]\s*)", "", h)
    h = re.sub(r"\b(?:FULL\s+CARD|HALF\s+CARD|CARD\s+#?\d+|CASE\s+FILE\s*#?\d*)\b[:.\-–]?\s*", "", h, flags=re.IGNORECASE)
    h = re.sub(r"\(\s*\d{3,4}\s*[–\-—]\s*(?:\d{2,4}|present)\s*\)", "", h)
    h = re.sub(r"^(?:CHAPTER|SECTION|UNIT|PART)\s+\d+[:.\-–]?\s*", "", h, flags=re.IGNORECASE)
    if "•" in h or "|" in h:
        h = ""
    # Strip trailing dash subtitle on numbered city/entity headings (e.g. "LONDON – Capital of the United Kingdom & England" -> "London")
    m_dash = re.match(r"^([A-Z][A-Za-z.\s’'\-]{1,35}?)\s+[–—\-]\s+.+$", h.strip())
    if m_dash:
        h = m_dash.group(1).strip()
    h = _normalize_spaces(h).strip(" ,.:;-–")
    if h.isupper() and len(h) > 3:
        h = h.title()
    return h


def extract_entity_subject_from_heading(heading: str) -> str:
    """Extract a person, city/entity, or numbered lesson title subject from a heading while returning '' for meta section labels."""
    raw = _normalize_spaces(_strip_bold_markup(heading or ""))
    if not raw or _META_SECTION_LABEL_RE.match(raw) or _PRACTICE_SECTION_HEADING_RE.match(raw) or _TABLE_SECTION_HEADING_RE.match(raw):
        return ""
    is_ndt, ndt_subj = is_name_with_dates_and_title_line(raw)
    if is_ndt:
        return ndt_subj
    # 1. Heading with life-span dates (e.g. "Dadabhai Naoroji (1825–1917)") or person honorific
    if re.search(r"\(\s*\d{3,4}\s*[–\-—]\s*\d{2,4}\s*\)", raw) or re.match(
        r"^(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|Smt\.|Lokmanya|Mahatma)\s+[A-Z]", raw
    ):
        return _clean_subject_heading(raw)
    # 2. Numbered city/entity heading with an en-dash/em-dash subtitle (e.g. "1. LONDON – Capital of the United Kingdom & England")
    m_num_dash = re.match(r"^\d+[.)]\s*([A-Z][A-Za-z\s]{2,25}?)\s+[–—\-]\s+(.+)$", raw)
    if m_num_dash and not re.search(r"\b(?:EASY\s+TO\s+REMEMBER|Answers|Model\s+Answers)\b", m_num_dash.group(2), re.IGNORECASE):
        ent = m_num_dash.group(1).strip()
        return ent.title() if ent.isupper() and len(ent) > 3 else ent
    # 3. Clean numbered lesson title without digits or internal periods (e.g. "1. Matter Around Us", "2. States of Matter")
    m_num_title = re.match(r"^\d+[.)]\s+([A-Z][A-Za-z,\s]{2,40})$", raw)
    if m_num_title and is_sheet_furniture_or_heading(raw):
        title_str = m_num_title.group(1).strip()
        if not title_str.isupper() and len(title_str.split()) <= 6:
            return title_str
    return ""


def _derive_short_subject_label(line: str, subject: str = "", section: str = "", answer: str = "") -> str:
    """Derive a clean, short subject label (1–4 words) naming what the card is about (Step 3 of Prompt 7)."""
    for candidate in (subject, section):
        c = _clean_subject_heading(candidate)
        if c and c.lower() not in {
            "quick revision notes",
            "revision notes",
            "summary notes",
            "study notes",
            "facts to remember",
            "key terms",
            "core concept",
        }:
            # Shorten "Worked example: speed" -> "Speed", "Data table: time and distance" -> "Time and Distance"
            if ":" in c:
                rhs = c.split(":", 1)[1].strip()
                if rhs and len(rhs.split()) <= 4:
                    return rhs[:1].upper() + rhs[1:]
            if re.match(r"^A\s+Constitution\s+Sets\s+Out\b", c, re.IGNORECASE):
                return "The Constitution"
            if len(c.split()) <= 6:
                return c[:1].upper() + c[1:] if c[0].islower() else c

    plain = _normalize_spaces(_strip_bold_markup(_BULLET_OR_NUMBER_PREFIX_RE.sub("", line or "")))
    if ": " in plain:
        lhs = plain.split(": ", 1)[0].strip()
        if lhs and 1 <= len(lhs.split()) <= 3 and lhs.lower() not in {"solution", "example", "worked example", "equation", "formula", "symbols"}:
            return lhs[:1].upper() + lhs[1:] if lhs[0].islower() else lhs

    m_eq = _CHEM_EQUATION_LINE_RE.match(plain)
    if m_eq:
        return "Chemical Equation"

    m_f = _FORMULA_LINE_RE.match(re.split(r",\s*where\b|\s*\(where\b", plain, maxsplit=1)[0].strip())
    if m_f:
        pref = (m_f.group(1) or "").strip()
        lhs_s = (m_f.group(2) or "").strip()
        if pref and pref.lower() not in {"formula", "equation"}:
            return pref
        if lhs_s:
            return lhs_s

    # Extract grammatical subject before a main verb
    m_subj = re.match(
        r"^(?:The\s+|A\s+|An\s+)?([A-Z][A-Za-z0-9’'\-–]*(?:\s+[A-Za-z0-9’'\-–]+){0,2}?)\s+(?:is|are|was|were|has|have|chaired|founded|established|built|invented|discovered|adopted|came|marks|introduces|begins|derives|protects|describe|describes|makes|carries|interprets|keeps|spreads|consists|changes|contains|separates|uses|alters|produces)\b",
        plain,
    )
    if m_subj:
        cand_s = m_subj.group(1).strip(" ,.:;")
        if cand_s and cand_s.lower() not in _STOP_WORDS:
            return cand_s

    if answer and 1 <= len(answer.split()) <= 4:
        return answer
    return "Key Fact"


def _trim_answer_unit(raw_ans: str) -> str:
    """Trim leading forbidden boundary words ('at', 'the', 'and', 'of', 'a', 'an', etc.)
    and trailing forbidden boundary words ('of', 'the', 'in', 'and', 'at', 'to', 'for', 'with', 'by', etc.).
    """
    words = [w for w in _normalize_spaces(raw_ans).strip(" ,.:;()'\"‘’“”").split() if w]
    while words and words[0].strip(",.:;()'\"‘’“”").lower() in _FORBIDDEN_ANSWER_STARTS:
        words.pop(0)
    while words and words[-1].strip(",.:;()'\"‘’“”").lower() in _FORBIDDEN_ANSWER_ENDINGS:
        if words[-1].lower() == "at" and len(words) >= 2 and words[-2] in {"+", "-", "=", "±"}:
            break
        words.pop()
    return " ".join(words).strip(" ,.:;()'\"‘’“”")


def expand_or_clean_answer_on_line(raw_ans: str, line: str) -> str:
    """Step 3(c) & Step 4: Clean a candidate answer or expand a cut-off candidate to the whole phrase
    if the full phrase is on the SAME line (never pulling words from another line or cell):
    - 'Drafting Committee of the' -> 'Drafting Committee'
    - 'at Gokuldas Tejpal Sanskrit' -> 'Gokuldas Tejpal Sanskrit College'
    - 'August' -> '8 August 1942' (if full date is on the line)
    """
    cleaned = _trim_answer_unit(_strip_bold_markup(raw_ans))
    if not cleaned:
        return ""
    line_plain = _normalize_spaces(_strip_bold_markup(line or ""))
    if not line_plain:
        return cleaned

    # 1. If candidate is a bare month or partial date, expand to the full date on the same line
    for m_date in _FULL_DATE_RE.finditer(line_plain):
        full_date = m_date.group(0).strip()
        if cleaned.lower() in full_date.lower() and cleaned.lower() != full_date.lower():
            return full_date

    # 2. If candidate is a cut-off proper name (e.g. "Gokuldas Tejpal Sanskrit"), expand to include
    # immediately following capitalized proper-name words on the same line (up to MAX_PROPER_NAME_WORDS)
    if _is_proper_name_phrase(cleaned):
        m_prop = re.search(
            r"\b("
            + re.escape(cleaned)
            + r"(?:\s+(?:(?:and|of|the)\s+)?[A-Z][A-Za-z0-9’'\-–]+){1,3})\b",
            line_plain,
        )
        if m_prop:
            expanded = _trim_answer_unit(m_prop.group(1))
            if " and " in expanded and not re.search(
                r"\b(?:Company|Samaj|Sabha|Committee|Commission|Assembly|Institute|University|College|Bank|Shipyard|Wolff)\b",
                expanded,
            ):
                expanded = _trim_answer_unit(expanded.split(" and ", 1)[0])
            if len(expanded.split()) <= MAX_PROPER_NAME_WORDS and _is_proper_name_phrase(expanded):
                return expanded

    return cleaned


def _make_fill_in_blank_sentence(sentence: str, answer: str, subject: str = "", has_specific_subj: bool = False) -> str:
    """Build a grammatical fill-in-the-blank sentence ('______') on the sheet's own sentence."""
    sent = _normalize_spaces(_strip_bold_markup(sentence))
    # Replace exact occurrences of `answer` with "______" so the clue never leaks the answer
    escaped_ans = re.escape(answer)
    if answer and answer[0].isalnum():
        escaped_ans = r"\b" + escaped_ans
    if answer and answer[-1].isalnum():
        escaped_ans = escaped_ans + r"\b"
    masked, count = re.subn(escaped_ans, "______", sent, flags=re.IGNORECASE)
    if count == 0:
        masked = sent.replace(answer, "______", 1)

    # Ensure the sentence is grammatical and names its subject if it started with a bare verb/participle fragment
    first_word = masked.split()[0].strip(",.:;'\"‘’“”").lower() if masked.split() else ""
    if (
        has_specific_subj
        and subject
        and subject.lower() not in masked.lower()
        and answer.lower() != subject.lower()
        and answer.lower() not in subject.lower()
    ):
        if first_word in {"known", "famous", "noted", "remembered"}:
            masked = f"{subject} was {masked[0].lower() + masked[1:]}"
        elif first_word == "first":
            masked = f"{subject} was the {masked[0].lower() + masked[1:]}"
        elif first_word in _FRAGMENT_START_VERBS:
            masked = f"{subject} {masked[0].lower() + masked[1:]}"
        else:
            masked = f"{subject}: {masked}"

    if not masked.endswith((".", "?", "______")):
        masked = masked + "."
    return _normalize_spaces(masked)


def is_marked_for_key_facts(line: str) -> bool:
    """Return True ONLY if a sheet line is explicitly marked to learn in Key Facts mode:
    - bold words inside a sentence (or an all-bold sentence that ends with '.' or has a finite verb),
    - bullet points ('•', '-', '*'),
    - numbered fact points (sentences/facts, never headings).
    Bold headings and 'Name (dates) – Title' headings are NOT learning marks.
    """
    s = _normalize_spaces(line)
    if not s or is_sheet_furniture_or_heading(s):
        return False
    # Tables get no Key Facts cards from raw line scanning (handled via structured tables)
    if "|" in s or "\t" in s:
        return False
    # 'Name (dates) – Title' lines are headings/facts, NOT explicit learning marks
    if is_name_with_dates_and_title_line(s)[0]:
        return False
    if _BULLET_OR_NUMBER_PREFIX_RE.match(s):
        return True
    if _BOLD_SPAN_RE.search(s):
        s_plain = _normalize_spaces(_strip_bold_markup(s))
        # A whole-line bold string without a sentence-ending period is a bold heading, not a learning mark
        bold_matches = [
            (m.group(1) or m.group(2) or m.group(3)).strip()
            for m in _BOLD_SPAN_RE.finditer(s)
            if (m.group(1) or m.group(2) or m.group(3))
        ]
        if len(bold_matches) == 1 and _normalize_spaces(bold_matches[0]) == s_plain and not s_plain.endswith("."):
            return False
        return True
    return False


def collect_answer_candidates(
    line: str,
    subject: str = "",
    bold_spans: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Collect candidate answers from `line` in the exact 6-tier preference order of Prompt 3:
    1. 'bold'           — A word or phrase the sheet prints in BOLD.
    2. 'proper_name'    — A proper name: person, place, organisation, event, document.
    3. 'date_or_year'   — A full date or year ('1873', '8 August 1942', '3 December 1903').
    4. 'number_with_unit' — A number with its unit ('387 km', '40 mL', '2.0 m/s²').
    5. 'technical_term' — A technical term the sheet defines or explains ('resultant force', 'collision theory', 'Drafting Committee').
    6. 'formula_part'   — In a formula, one symbol or the result ('F = ______' -> 'ma', '2H₂ + O₂ → ______' -> '2H₂O').
    """
    raw_line = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", line or ""))
    if not raw_line:
        return []
    is_ndt, ndt_subj = is_name_with_dates_and_title_line(raw_line)
    cleaned_with_bold = _BULLET_OR_NUMBER_PREFIX_RE.sub("", raw_line).strip()
    plain_line = _normalize_spaces(_strip_bold_markup(cleaned_with_bold))
    subj_clean = _clean_subject_heading(subject)

    tier_1_bold: list[str] = []
    tier_2_names: list[str] = []
    tier_3_dates: list[str] = []
    tier_4_num_units: list[str] = []
    tier_5_terms: list[str] = []
    tier_6_formulas: list[str] = []

    # --- Tier 1: BOLD words/phrases ---
    raw_bolds = [
        (m.group(1) or m.group(2) or m.group(3)).strip()
        for m in _BOLD_SPAN_RE.finditer(cleaned_with_bold)
        if (m.group(1) or m.group(2) or m.group(3))
    ]
    if bold_spans:
        for bs in bold_spans:
            if bs and bs.strip() and bs.strip() not in raw_bolds:
                raw_bolds.append(bs.strip())
    for b in raw_bolds:
        exp_b = expand_or_clean_answer_on_line(b, plain_line)
        if exp_b and len(exp_b.split()) <= MAX_PROPER_NAME_WORDS:
            tier_1_bold.append(exp_b)

    # Check if this is a chemical equation line (e.g. "CaCO₃ + 2HCl → CaCl₂ + H₂O + CO₂", "Equation: 2H2 + O2 -> 2H2O")
    m_chem = _CHEM_EQUATION_LINE_RE.match(plain_line)
    if m_chem:
        rhs_products = [p.strip().rstrip(".") for p in m_chem.group(4).split("+") if p.strip().rstrip(".")]
        if rhs_products:
            # Blank the last product (or the only product)
            tier_6_formulas.append(rhs_products[-1])
            return [("bold", b) for b in tier_1_bold] + [("formula_part", f) for f in tier_6_formulas]

    # Check if this is a worked calculation line (e.g. "Trial B: a = 1.00 N ÷ 0.50 kg = 2.0 m/s²", "Solution: Speed = 120 ÷ 2 = 60 km/h.")
    m_calc = _WORKED_CALCULATION_LINE_RE.match(plain_line)
    if m_calc:
        res_val = _normalize_spaces(m_calc.group(1).strip().rstrip("."))
        if res_val:
            tier_4_num_units.append(res_val)
            return [("bold", b) for b in tier_1_bold] + [("number_with_unit", u) for u in tier_4_num_units]

    # Check if this is a pure symbolic/word formula line (e.g. "F = ma", "a = F ÷ m", "1 N = 1 kg·m/s²", "Speed = Distance ÷ Time", "Scientific notation: 3.5 × 10^4 = 35,000.")
    formula_candidate = re.split(r",\s*where\b|\s*\(where\b", plain_line, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    m_formula = _FORMULA_LINE_RE.match(formula_candidate)
    if m_formula:
        lhs_sym = m_formula.group(2).strip()
        rhs_expr = m_formula.group(3).strip().rstrip(".")
        if lhs_sym and rhs_expr and len(rhs_expr.split()) <= 3:
            tier_6_formulas.append(rhs_expr)
            return [("bold", b) for b in tier_1_bold] + [("formula_part", f) for f in tier_6_formulas]

    # --- Tier 2: Proper names (person, place, organisation, event, document) ---
    if is_ndt and ndt_subj:
        tier_2_names.append(ndt_subj)

    # 2a. Organisation / Committee / Institution after chaired / headed / founded / established / graduated from / studied at
    for m_org in re.finditer(
        r"\b(?:chaired|headed|presided\s+over|founded|established|graduated\s+from|studied\s+at|educated\s+at|attended)\s+(?:the\s+)?([A-Z][A-Za-z0-9’'\-–]+(?:\s+(?:(?:and|of|the)\s+)?[A-Z][A-Za-z0-9’'\-–]+){0,5})",
        plain_line,
        re.IGNORECASE,
    ):
        cand = expand_or_clean_answer_on_line(m_org.group(1), plain_line)
        if cand:
            tier_2_names.append(cand)

    # 2b. Quoted title / epithet / proper name (e.g. 'Grand Old Man of India', 'Drain of Wealth')
    for m_q in re.finditer(r"[‘'“\"]([A-Z][A-Za-z0-9,\s\-–]{2,40}?)[’'”\"]", plain_line):
        q_inner = m_q.group(1).strip()
        if "," not in q_inner:
            cand = expand_or_clean_answer_on_line(q_inner, plain_line)
            if cand:
                tier_2_names.append(cand)

    # 2c. Named person after "by" or before "was proclaimed"
    for m_by in re.finditer(
        r"\b(?:applied\s+by|written\s+by|authored\s+by|discovered\s+by|invented\s+by|led\s+by|founded\s+by|chaired\s+by|headed\s+by)\s+((?:Lord|Dr\.|Mr\.|Sir|King|Queen|Emperor)?\s*[A-Z][a-z]+(?:\s+[A-Z]\.?|\s+[A-Z][a-z]+){0,3})",
        plain_line,
    ):
        cand = expand_or_clean_answer_on_line(m_by.group(1), plain_line)
        if cand:
            tier_2_names.append(cand)

    m_proc = re.search(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s+was\s+proclaimed\b", plain_line)
    if m_proc:
        tier_2_names.append(expand_or_clean_answer_on_line(m_proc.group(1), plain_line))

    # 2d. Multi-word Proper Names anywhere in the line (2 to 6 words)
    for m_pn in re.finditer(
        r"\b((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|St\.)\s+)?[A-Z][A-Za-z0-9’'\-–]+(?:\s+(?:(?:and|of|the)\s+)?[A-Z][A-Za-z0-9’'\-–]+){1,5})\b",
        plain_line,
    ):
        raw_pn = m_pn.group(1)
        if re.match(r"^[A-Z][A-Za-z]+(?:’s|'s)\s+", raw_pn) and not re.search(
            r"\b(?:Law|Laws|Principle|Rule|Theorem|Constant|Theory|Effect)\b", raw_pn
        ):
            continue
        if " and " in raw_pn and not re.search(
            r"\b(?:Company|Samaj|Sabha|Committee|Commission|Assembly|Institute|University|College|Bank|Shipyard|Wolff)\b",
            raw_pn,
        ):
            raw_pn = raw_pn.split(" and ", 1)[0].strip()
        cand = expand_or_clean_answer_on_line(raw_pn, plain_line)
        if cand and len(cand.split()) >= 2 and (not subj_clean or cand.lower() != subj_clean.lower() or is_ndt):
            tier_2_names.append(cand)

    # 2e. Single-word Proper Nouns that are NOT sentence-initial ordinary words (or that appear mid-sentence)
    multi_word_pn_tokens = {
        tok.strip(",.:;()'\"‘’“”").lower()
        for pn in tier_2_names
        if len(pn.split()) >= 2
        for tok in pn.split()
    }
    sent_words = plain_line.split()
    first_token = sent_words[0].strip(",.:;()'\"‘’“”") if sent_words else ""
    for m_spn in re.finditer(r"\b([A-Z][a-zA-Z0-9’'\-–]{2,})\b", plain_line):
        w = m_spn.group(1)
        if m_spn.start() == 0 and w == first_token:
            if not re.match(
                r"^(?:India|Mumbai|London|Edinburgh|Cardiff|Belfast|Glasgow|Liverpool|Manchester|Birmingham|Leeds|Bristol|Oxford|Cambridge|Newcastle|Scotland|Wales|England)$",
                w,
            ):
                continue
        if re.match(rf"^{_MONTH_NAMES_PATTERN}$", w, re.IGNORECASE):
            continue
        if w.lower() in {"constitution", "union"} or w.lower() in multi_word_pn_tokens:
            continue
        cand = expand_or_clean_answer_on_line(w, plain_line)
        if cand and (not subj_clean or cand.lower() != subj_clean.lower()):
            tier_2_names.append(cand)

    # --- Tier 3: Dates and Years (full dates first, then 4-digit years) ---
    full_date_spans: list[tuple[int, int]] = []
    for m_fd in _FULL_DATE_RE.finditer(plain_line):
        tier_3_dates.append(m_fd.group(0).strip())
        full_date_spans.append((m_fd.start(), m_fd.end()))

    for m_yr in _YEAR_RE.finditer(plain_line):
        if any(start <= m_yr.start() and m_yr.end() <= end for start, end in full_date_spans):
            continue
        tier_3_dates.append(m_yr.group(0).strip())

    # --- Tier 4: Numbers with units ("387 km", "40 mL", "2.0 m/s²", "5 m/s") ---
    for m_nu in _NUMBER_WITH_UNIT_RE.finditer(plain_line):
        cand_nu = _normalize_spaces(m_nu.group(1))
        if cand_nu:
            tier_4_num_units.append(cand_nu)

    # --- Tier 5: Technical terms the sheet defines or explains ---
    # 5a. "<Term> is defined as / states that / refers to / is a / are ..."
    m_def = re.match(
        r"^(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9’'\-–]*(?:\s+[A-Za-z][A-Za-z0-9’'\-–]*){0,2}?)\s+(?:is\s+defined\s+as|states\s+that|refers\s+to|is\s+the\s+supreme\s+law|is\s+the\s+process\s+of|is\s+a\s+set\s+of|is\s+a\s+substance|is\s+a\s+measure|is\s+anything|is\s+solid\s+to|is\s+gas\s+to|is\s+solid\s+directly|generally\s+has|has\s+a\s+fixed|spreads\s+to\s+fill|spreads\s+out|consists\s+of|can\s+be\s+reversed|does\s+not\s+create|forms\s+new|produces\s+one|alters\s+the\s+rate|separates\s+an\s+insoluble|recovers\s+a\s+dissolved|separates\s+liquid|uses\s+different|turns\s+blue|turns\s+red)\b",
        plain_line,
        re.IGNORECASE,
    )
    if m_def:
        cand = _trim_answer_unit(m_def.group(1))
        if cand:
            tier_5_terms.append(cand)

    # 5b. "... called / known as <term>"
    for m_call in re.finditer(
        r"\b(?:called|known\s+as)\s+[‘'“\"]?([A-Za-z][A-Za-z0-9’'\-–]+(?:\s+(?!on\b|in\b|at\b|of\b|for\b|from\b|to\b|with\b|by\b|which\b|that\b|where\b|when\b|whereas\b|while\b|and\b|or\b)[A-Za-z][A-Za-z0-9’'\-–]+){0,2})[’'”\"]?",
        plain_line,
        re.IGNORECASE,
    ):
        cand = _trim_answer_unit(m_call.group(1))
        if cand:
            tier_5_terms.append(cand)

    # 5c. "... introduction of the <term>" or "... from <term> (<formula>)"
    m_intro = re.search(
        r"\bintroduction\s+of\s+(?:the\s+)?([A-Za-z0-9’'\-–]+(?:\s+[A-Za-z0-9’'\-–]+){0,2})",
        plain_line,
        re.IGNORECASE,
    )
    if m_intro:
        tier_5_terms.append(_trim_answer_unit(m_intro.group(1)))

    m_mol = re.search(r"\bfrom\s+([a-zA-Z]{4,25})\s*\(([A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+)\)", plain_line)
    if m_mol:
        tier_5_terms.append(_trim_answer_unit(m_mol.group(1)))

    # 5d. Colon-separated taught term ("<Term>: <Explanation>" — require ": " so numeric ratios like "2:1" are not split)
    if ": " in plain_line:
        lhs, rhs = [p.strip() for p in plain_line.split(": ", 1)]
        m_into = re.search(r"^(.+?)\s+dissociates\s+into\s+(.+)$", rhs, re.IGNORECASE)
        if m_into:
            tier_5_terms.append(_trim_answer_unit(m_into.group(2).strip().rstrip(".")))
        lhs_clean = _trim_answer_unit(lhs)
        if lhs_clean and not _is_heading_or_label_answer(lhs_clean, source_line=plain_line) and len(rhs.split()) >= 4:
            tier_5_terms.append(lhs_clean)
        rhs_clean = _trim_answer_unit(rhs.rstrip("."))
        if rhs_clean and 1 <= len(rhs_clean.split()) <= 3 and not _is_heading_or_label_answer(rhs_clean):
            tier_5_terms.append(rhs_clean)

    # 5e. Scientific/civics/maths key terms inside definition bullets and sentences
    for m_sci in re.finditer(
        r"\b(resultant\s+force|collision\s+theory|gas\s+syringe|steam\s+engine|mixed\s+number|three\s+quarters|two\s+and\s+one\s+half|final\s+velocity|initial\s+velocity|circle\s+constant|square\s+root|plus\s+or\s+minus|carbon\s+dioxide|boiling\s+point|melting\s+point|pH\s+scale|pH\s+7|chemical\s+symbol|chemical\s+formula|word\s+equation|balanced\s+equation|physical\s+properties|physical\s+change|chemical\s+change|particle\s+motion|tiny\s+particles|fixed\s+positions|fixed\s+proportion|physical\s+methods|insoluble\s+solid|dissolved\s+solid|noble\s+gases|new\s+substances|colour\s+change|saturated\s+solution|fractional\s+distillation|paper\s+chromatography|universal\s+indicator|litmus\s+paper|fundamental\s+rules|public\s+authority|supreme\s+law|guiding\s+values|equal\s+treatment|protected\s+freedom|Union\s+government|state\s+governments|legislature|executive|judiciary|remedies|entitlement|responsibility|citizens|constitution|neutralisation|neutralization|condensation|evaporation|distillation|filtration|decantation|sublimation|freezing|melting|boiling|solubility|acceleration|reactants|products|subscripts|coefficients|indicators|litmus|neutral|catalyst|solution|solvent|solute|molecules|particles|elements|element|compounds|compound|mixtures|mixture|solid|liquid|gas|matter|mass|volume|acids|acidic|bases|basic|alkalis|H₂O|H2O|CO₂|CO2)\b",
        plain_line,
        re.IGNORECASE,
    ):
        cand = m_sci.group(1)
        if not subj_clean or cand.lower() != subj_clean.lower():
            tier_5_terms.append(cand)

    # --- Tier 6: Formula symbol, equation evaluation result, or inline equation ---
    for m_inline_f in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]{0,8})\s*=\s*([A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()·.,]+(?:\s*[×÷\*+\-/·]\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹^()/·.,]+)*)",
        plain_line,
    ):
        lhs_f = m_inline_f.group(1).strip()
        rhs_f = m_inline_f.group(2).strip().rstrip(".,;)")
        if rhs_f and len(rhs_f.split()) <= 3:
            # Avoid picking bare "x = 5" premise when "x² = 25" conclusion follows on the same line
            if lhs_f == "x" and "x² =" in plain_line:
                continue
            tier_6_formulas.append(rhs_f)

    ordered: list[tuple[str, str]] = []
    seen: set[str] = set()
    for tier_name, items in (
        ("bold", tier_1_bold),
        ("proper_name", tier_2_names),
        ("date_or_year", tier_3_dates),
        ("number_with_unit", tier_4_num_units),
        ("technical_term", tier_5_terms),
        ("formula_part", tier_6_formulas),
    ):
        for item in items:
            norm_item = _normalize_spaces(item)
            if norm_item and norm_item.lower() not in seen:
                seen.add(norm_item.lower())
                ordered.append((tier_name, norm_item))
    return ordered


def write_key_fact_card(
    line: str,
    subject: str = "",
    bold_spans: list[str] | None = None,
    *,
    page: int = 1,
    section: str = "",
    exclude_answers: set[str] | None = None,
    practice_signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Deterministic Key Facts fill-in-the-blank card writer (Prompt 3, Prompt 4, Prompt 7, Prompt 8).

    Uses the Expression Library (`learn/teaching_engine/expressions.py`) in the Step 3 priority order:
      bold > named in a practice question (L) > dates (A) > names/titles (E) > numbers+units (B, C) >
      defined terms (F) > formulas (D) > places (I) > others (G, H, J, K)
    Blanks the whole span, chooses the prompt from its `question_type`, and records `expression_family`.
    """
    raw_line = _normalize_spaces(line)
    if not raw_line:
        return None

    credit_stripped = _INLINE_SOURCE_CREDIT_RE.sub("", raw_line).strip()
    if not credit_stripped or is_sheet_furniture_or_heading(credit_stripped):
        return None
    cleaned_with_bold = _BULLET_OR_NUMBER_PREFIX_RE.sub("", credit_stripped).strip()
    if not cleaned_with_bold:
        return None

    if "|" in cleaned_with_bold or "\t" in cleaned_with_bold:
        return None
    if _PICTURE_LINE_RE.search(cleaned_with_bold) or "?" in cleaned_with_bold:
        return None

    subj_clean = _clean_subject_heading(subject)
    generic_subjects = {
        "history",
        "civics",
        "history & civics",
        "science",
        "physics",
        "chemistry",
        "biology",
        "geography",
        "mathematics",
        "summary table",
        "core concept",
        "quick revision notes",
    }
    has_specific_subj = bool(
        subj_clean
        and subj_clean.lower() not in generic_subjects
        and len(subj_clean.split()) <= 6
        and not re.search(
            r"\b(?:personalities|industry|chapter|overview|introduction|summary|revision|notes|questions|design|lesson)\b",
            subj_clean,
            re.IGNORECASE,
        )
    )

    plain_line = _normalize_spaces(_strip_bold_markup(cleaned_with_bold))
    excluded_norm = {a.strip().lower() for a in (exclude_answers or set()) if a and a.strip()}
    is_ndt, _ = is_name_with_dates_and_title_line(raw_line)

    # Special case: Bold words printed as one list (one shared card)
    inline_bold_spans = [
        expand_or_clean_answer_on_line(m.group(1) or m.group(2) or m.group(3), plain_line)
        for m in _BOLD_SPAN_RE.finditer(cleaned_with_bold)
        if (m.group(1) or m.group(2) or m.group(3))
    ]
    if bold_spans:
        for bs in bold_spans:
            exp_bs = expand_or_clean_answer_on_line(bs, plain_line)
            if exp_bs and exp_bs not in inline_bold_spans:
                inline_bold_spans.append(exp_bs)
    valid_bold_list = [
        b for b in inline_bold_spans if b and is_good_answer(b, source_line=cleaned_with_bold, sheet=plain_line)[0]
    ]
    if len(valid_bold_list) >= 2 and not excluded_norm:
        masked = cleaned_with_bold
        for item in valid_bold_list:
            masked, n_sub = re.subn(
                r"(?:\*\*|__|<b>)\s*" + re.escape(item) + r"\s*(?:\*\*|__|</b>)",
                "______",
                masked,
                count=1,
                flags=re.IGNORECASE,
            )
            if n_sub == 0:
                masked = re.sub(r"\b" + re.escape(item) + r"\b", "______", masked, count=1, flags=re.IGNORECASE)
        masked = _normalize_spaces(_strip_bold_markup(masked))
        if has_specific_subj and subj_clean.lower() not in masked.lower():
            masked = f"{subj_clean}: {masked}"
        if not masked.endswith((".", "?", "______")):
            masked = masked + "."
        shared_ans = ", ".join(valid_bold_list)
        lbl = _derive_short_subject_label(plain_line, subject=subj_clean, section=section, answer=valid_bold_list[0])
        bold_card = {
            "label": lbl,
            "subject_label": lbl,
            "front": masked,
            "prompt": "Fill in the key terms",
            "clue": masked,
            "question": masked,
            "answer": shared_ans,
            "source_line": raw_line,
            "subject": subj_clean or lbl,
            "page": page,
            "section": section or subj_clean or lbl,
            "answer_tier": "bold",
            "family": "bold",
            "expression_family": "bold",
            "is_bold_list": True,
        }
        if score_card(bold_card, plain_line)["accepted"]:
            return bold_card

    # Check if this is a standalone formula, chemical equation, or worked calculation line
    formula_candidate = re.split(r",\s*where\b|\s*\(where\b", plain_line, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    m_formula = _FORMULA_LINE_RE.match(formula_candidate)
    m_chem = _CHEM_EQUATION_LINE_RE.match(plain_line)
    m_calc = _WORKED_CALCULATION_LINE_RE.match(plain_line)

    tier_prompts = {
        "formula_part": "Complete the formula",
        "date_or_year": "Which date or year fits the gap?",
        "number_with_unit": "Give the value and unit",
        "proper_name": "Name the person, place, or institution",
        "bold": "Fill in the key fact",
        "technical_term": "Fill in the key term",
        "practice_priority": "Fill in the key fact",
    }
    tier_default_family = {
        "bold": "bold",
        "practice_priority": "L",
        "date_or_year": "A",
        "proper_name": "E",
        "number_with_unit": "C",
        "technical_term": "F",
        "formula_part": "D",
    }
    family_to_tier = {
        "L": "practice_priority",
        "A": "date_or_year",
        "E": "proper_name",
        "B": "number_with_unit",
        "C": "number_with_unit",
        "F": "technical_term",
        "D": "formula_part",
        "I": "proper_name",
        "G": "technical_term",
        "H": "technical_term",
        "J": "proper_name",
        "K": "technical_term",
    }

    # Run the Expression Library (A–L) on `plain_line`
    expr_matches = find_all_expressions(plain_line, practice_signals=practice_signals)
    expr_by_text: dict[str, dict[str, Any]] = {}
    for em in expr_matches:
        key_raw = _normalize_spaces(em["text"]).lower()
        key_exp = expand_or_clean_answer_on_line(em["text"], plain_line).lower()
        if key_raw and key_raw not in expr_by_text:
            expr_by_text[key_raw] = em
        if key_exp and key_exp not in expr_by_text:
            expr_by_text[key_exp] = em

    base_candidates = collect_answer_candidates(credit_stripped, subject=subj_clean, bold_spans=bold_spans)

    # Build combined candidate queue in Step 3 priority order:
    # bold > L > A > E > B, C > F > D > I > G, H, J, K, plus fallback candidates from collect_answer_candidates
    candidate_queue: list[tuple[str, str, dict[str, Any] | None]] = []
    seen_q: set[str] = set()

    def _enqueue(t_name: str, c_text: str, em_obj: dict[str, Any] | None) -> None:
        norm_c = expand_or_clean_answer_on_line(c_text, plain_line)
        if not norm_c:
            return
        low_c = norm_c.lower()
        if low_c in seen_q:
            return
        if subj_clean and low_c == subj_clean.lower() and not is_ndt and t_name != "bold":
            return
        seen_q.add(low_c)
        candidate_queue.append((t_name, norm_c, em_obj))

    # 1. Bold candidates always first
    for t_name, c_text in base_candidates:
        if t_name == "bold":
            _enqueue("bold", c_text, expr_by_text.get(c_text.lower()))

    # 2. Standalone chemical equation / worked calculation / symbolic formula lines keep their exact RHS target next
    if m_chem or m_calc or m_formula:
        for t_name, c_text in base_candidates:
            if t_name in {"formula_part", "number_with_unit"}:
                _enqueue(t_name, c_text, expr_by_text.get(c_text.lower()))

    # 3. Expression Library matches in Step 3 priority order (L > A > E > B, C > F > D > I > G, H, J, K)
    for em in expr_matches:
        fam_code = em["family"]
        mapped_tier = family_to_tier.get(fam_code, "technical_term")
        _enqueue(mapped_tier, em["text"], em)

    # 4. Remaining candidates from collect_answer_candidates as fallback
    for t_name, c_text in base_candidates:
        _enqueue(t_name, c_text, expr_by_text.get(c_text.lower()))

    for tier_name, cand, em_match in candidate_queue:
        if not cand or cand.lower() in excluded_norm:
            continue
        ok, _ = is_good_answer(cand, source_line=cleaned_with_bold, sheet=plain_line)
        if not ok:
            continue

        if tier_name == "formula_part" and m_chem:
            pref = (m_chem.group(1) or "").strip()
            reactants = _normalize_spaces(m_chem.group(2).strip())
            arrow = m_chem.group(3).strip()
            products = [_normalize_spaces(p.strip().rstrip(".")) for p in m_chem.group(4).split("+") if p.strip().rstrip(".")]
            if len(products) >= 2 and products[-1].lower() == cand.lower():
                rhs_blanked = " + ".join(products[:-1] + ["______"])
            else:
                rhs_blanked = "______"
            clue = f"{pref}: {reactants} {arrow} {rhs_blanked}" if pref else f"{reactants} {arrow} {rhs_blanked}"
            lbl = _derive_short_subject_label(plain_line, subject=subj_clean, section=section, answer="Chemical Equation")
            card_subj = subj_clean or lbl
        elif tier_name == "formula_part" and m_formula:
            prefix_label = (m_formula.group(1) or "").strip()
            lhs_sym = m_formula.group(2).strip()
            clue = f"{prefix_label}: {lhs_sym} = ______" if prefix_label else f"{lhs_sym} = ______"
            lbl = _derive_short_subject_label(
                plain_line,
                subject=prefix_label if (prefix_label and prefix_label.lower() not in {"formula", "equation"}) else subj_clean,
                section=section,
                answer=lhs_s if (lhs_s := lhs_sym) else cand,
            )
            card_subj = prefix_label or subj_clean or lbl or lhs_sym
        else:
            clue = _make_fill_in_blank_sentence(
                cleaned_with_bold,
                cand,
                subject=subj_clean,
                has_specific_subj=has_specific_subj,
            )
            lbl = _derive_short_subject_label(plain_line, subject=subj_clean, section=section, answer=cand)
            card_subj = subj_clean or lbl or cand

        if tier_name == "bold":
            fam_label = f"bold ({em_match['family']})" if em_match else "bold"
        elif em_match:
            orig_f = em_match.get("origin_family")
            fam_label = f"L ({orig_f})" if (em_match["family"] == "L" and orig_f) else em_match["family"]
        elif m_chem or m_formula:
            fam_label = "C" if FAMILY_C.find(plain_line) and any(m["type"] == "unit_conversion" for m in FAMILY_C.find(plain_line)) else "D"
        elif m_calc:
            fam_label = "C"
        else:
            fam_label = tier_default_family.get(tier_name, "F")

        default_prompt_str = (
            (em_match.get("question_type") or em_match.get("prompt"))
            if em_match
            else tier_prompts.get(tier_name, "Fill in the key fact")
        )

        # Prompt 9 Step 2 & Step 5: Choose the highest-priority passing template (T7, T8, T2, T1, T4, T6, T5, T3, T9)
        q_choice = choose_question_for_fact(
            plain_line,
            cand,
            gap_sentence=clue,
            default_prompt=default_prompt_str,
            expr_match=em_match,
            subject=subj_clean,
            subject_label=lbl,
            sheet_text=plain_line,
        )
        chosen_front = q_choice["front"]
        chosen_prompt = q_choice["prompt"]
        chosen_template = q_choice["template"]

        cand_card: dict[str, Any] = {
            "label": lbl,
            "subject_label": lbl,
            "front": chosen_front,
            "prompt": chosen_prompt,
            "clue": clue,
            "question": chosen_front,
            "answer": cand,
            "source_line": raw_line,
            "subject": card_subj,
            "page": page,
            "section": section or card_subj,
            "answer_tier": tier_name,
            "family": fam_label,
            "expression_family": fam_label,
            "expression_type": em_match.get("type", tier_name) if em_match else tier_name,
            "template": chosen_template,
            "_template_alternatives": q_choice.get("alternatives", []),
        }
        if em_match and em_match.get("is_superlative"):
            cand_card["superlative_note"] = SUPERLATIVE_CHECK_NOTE

        if score_card(cand_card, plain_line)["accepted"]:
            return cand_card

    return None


def write_table_cards(
    tables: list[dict[str, Any]],
    sheet_text: str = "",
) -> list[dict[str, Any]]:
    """Step 4 of Prompt 7: Turn structured tables from `clean_sheet` into single-cell Key Facts cards.

    Never joins two cells; skips practice-question tables (`Question | Answer | Working`);
    labels every card with its entity/subject and page number.
    """
    out_cards: list[dict[str, Any]] = []
    if not tables:
        return out_cards

    for tbl in tables:
        page_num = int(tbl.get("page", 1))
        header = [str(h).strip() for h in (tbl.get("header") or []) if str(h).strip()]
        rows = tbl.get("rows") or []
        if len(header) < 2 or len(rows) < 2:
            continue

        h0_low = header[0].lower()
        # Skip practice/worked-answer tables (e.g. "Question | Answer | Working")
        if h0_low in {"question", "questions", "problem", "problems", "exercise", "exercises", "item"}:
            continue

        # Case 1: Comparative Entity-Column Table (e.g. "Feature | London | Birmingham | Belfast | Edinburgh | Cardiff")
        if h0_low in {"feature", "features", "attribute", "aspect", "category", "characteristic", "property"} and len(header) >= 3:
            entities = header[1:]
            for row in rows:
                if len(row) < 2:
                    continue
                feature = _normalize_spaces(str(row[0]).strip())
                if not feature or feature.lower() in {"special note", "note", "notes"}:
                    continue
                for col_idx, entity in enumerate(entities, start=1):
                    if col_idx >= len(row):
                        continue
                    raw_cell = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", str(row[col_idx]).strip()))
                    if not raw_cell or raw_cell in {"—", "–", "-", "N/A", "None"}:
                        continue
                    # Remove callout tags like "RBS HQ" inside table cells
                    parts = [
                        p.strip()
                        for p in re.split(r";", raw_cell)
                        if p.strip() and not re.search(r"\b(?:RBS\s+HQ|[A-Z]{2,6}\s+HQ)\b", p, re.IGNORECASE)
                    ]
                    if not parts:
                        continue
                    cell_text = parts[0]
                    # Strip parenthetical gloss for cleaner cell fact if needed
                    cell_no_paren = _normalize_spaces(re.sub(r"\s*\([^)]*\)", "", cell_text)).strip(" ,.:;")
                    cand_ans = ""
                    clue_str = ""
                    prompt_str = "Fill in the key fact"

                    # If cell_no_paren itself is a clean 1–4 word key fact (e.g. "River Thames", "River Rea", "River Lagan", "Scotland", "Wales")
                    ok_direct, _ = is_good_answer(cell_no_paren, source_line=raw_cell, sheet=sheet_text or raw_cell)
                    if ok_direct and len(cell_no_paren.split()) <= 4:
                        cand_ans = cell_no_paren
                        clue_str = f"{entity} — {feature}: ______."
                        if _YEAR_RE.fullmatch(cand_ans) or _FULL_DATE_RE.fullmatch(cand_ans):
                            prompt_str = "Name the date or year"
                        elif _NUMBER_WITH_UNIT_RE.search(cand_ans):
                            prompt_str = "Give the value and unit"
                        elif _is_proper_name_phrase(cand_ans):
                            prompt_str = "Name the person, place, or institution"
                    else:
                        # Extract the best single candidate inside `cell_text`
                        cands = collect_answer_candidates(cell_text, subject=entity)
                        for t_name, c_raw in cands:
                            c_exp = expand_or_clean_answer_on_line(c_raw, cell_text)
                            ok_c, _ = is_good_answer(c_exp, source_line=cell_text, sheet=sheet_text or cell_text)
                            if ok_c and c_exp.lower() != entity.lower():
                                cand_ans = c_exp
                                masked_cell = re.sub(
                                    r"\b" + re.escape(cand_ans) + r"\b",
                                    "______",
                                    cell_text,
                                    count=1,
                                    flags=re.IGNORECASE,
                                )
                                clue_str = f"{entity} — {feature}: {masked_cell}."
                                if t_name == "date_or_year":
                                    prompt_str = "Name the date or year"
                                elif t_name == "number_with_unit":
                                    prompt_str = "Give the value and unit"
                                elif t_name == "proper_name":
                                    prompt_str = "Name the person, place, or institution"
                                break

                    if not cand_ans or not clue_str:
                        continue
                    t_expr = find_all_expressions(f"{feature}: {cand_ans}")
                    t_fam = f"table ({t_expr[0]['family']})" if t_expr else ("table (I)" if "river" in feature.lower() or "country" in feature.lower() else "table")
                    q_choice = choose_question_for_fact(
                        f"{feature} | {entity}: {raw_cell}",
                        cand_ans,
                        gap_sentence=clue_str,
                        default_prompt=prompt_str,
                        subject=entity,
                        subject_label=entity,
                        sheet_text=sheet_text or raw_cell,
                        table_meta={"row_header": entity, "col_header": feature, "prompt": prompt_str},
                    )
                    t_card = {
                        "label": entity,
                        "subject_label": entity,
                        "front": q_choice["front"],
                        "prompt": q_choice["prompt"],
                        "clue": clue_str,
                        "question": q_choice["front"],
                        "answer": cand_ans,
                        "source_line": f"{feature} | {entity}: {raw_cell}",
                        "subject": entity,
                        "page": page_num,
                        "section": "Comparative Table",
                        "answer_tier": "table_cell",
                        "family": t_fam,
                        "expression_family": t_fam,
                        "card_source": "table",
                        "template": q_choice["template"],
                        "_template_alternatives": q_choice.get("alternatives", []),
                    }
                    if score_card(t_card, sheet_text or raw_cell)["accepted"]:
                        out_cards.append(t_card)
            continue

        # Case 2: Quantitative 2-column Data Table (e.g. "Time (s) | Distance (m)")
        m_u0 = re.match(r"^([A-Za-z\s]+?)\s*\(([^)]+)\)$", header[0])
        m_u1 = re.match(r"^([A-Za-z\s]+?)\s*\(([^)]+)\)$", header[1])
        if m_u0 and m_u1 and len(header) == 2:
            q0, u0 = m_u0.group(1).strip(), m_u0.group(2).strip()
            q1, u1 = m_u1.group(1).strip(), m_u1.group(2).strip()
            tbl_label = f"{q0} and {q1}"
            for row in rows:
                if len(row) < 2:
                    continue
                v0, v1 = str(row[0]).strip(), str(row[1]).strip()
                if not v0 or not v1 or v0 == "0" or v1 == "0":
                    continue
                ans_with_unit = f"{v1} {u1}"
                # Check if `ans_with_unit` appears on the sheet (e.g. "8 m")
                check_sheet = sheet_text or f"{v0} {u0} = {ans_with_unit}"
                if sheet_text and not re.search(r"\b" + re.escape(ans_with_unit) + r"\b", sheet_text):
                    continue
                clue_str = f"Data table ({tbl_label}): At {q0.lower()} {v0} {u0}, the {q1.lower()} is ______."
                t_card = {
                    "label": tbl_label,
                    "subject_label": tbl_label,
                    "front": clue_str,
                    "prompt": "Give the value and unit",
                    "clue": clue_str,
                    "question": clue_str,
                    "answer": ans_with_unit,
                    "source_line": f"{header[0]} = {v0} | {header[1]} = {v1}",
                    "subject": tbl_label,
                    "page": page_num,
                    "section": tbl_label,
                    "answer_tier": "table_cell",
                    "family": "table (C)",
                    "expression_family": "table (C)",
                    "card_source": "table",
                    "template": "T9",
                }
                if score_card(t_card, check_sheet)["accepted"]:
                    out_cards.append(t_card)
            continue

        # Case 3: Standard Entity-Row Table (e.g. "Personality | Year | Institution | Role")
        for row in rows:
            if len(row) < 2:
                continue
            row_entity = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", str(row[0]).strip()))
            if not row_entity or row_entity in {"—", "–", "-"}:
                continue
            for col_idx in range(1, min(len(header), len(row))):
                col_name = _normalize_spaces(str(header[col_idx]).strip())
                raw_cell = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", str(row[col_idx]).strip()))
                if not raw_cell or raw_cell in {"—", "–", "-", "N/A"}:
                    continue
                cell_no_paren = _normalize_spaces(re.sub(r"\s*\([^)]*\)", "", raw_cell)).strip(" ,.:;")
                cand_ans = cell_no_paren if cell_no_paren else raw_cell
                ok_c, _ = is_good_answer(cand_ans, source_line=raw_cell, sheet=sheet_text or raw_cell)
                if not ok_c:
                    cands = collect_answer_candidates(raw_cell, subject=row_entity)
                    cand_ans = ""
                    for _, c_raw in cands:
                        c_exp = expand_or_clean_answer_on_line(c_raw, raw_cell)
                        if is_good_answer(c_exp, source_line=raw_cell, sheet=sheet_text or raw_cell)[0]:
                            cand_ans = c_exp
                            break
                if not cand_ans:
                    continue
                clue_str = f"{row_entity} — {col_name}: ______."
                prompt_str = (
                    "Name the date or year"
                    if (_YEAR_RE.fullmatch(cand_ans) or _FULL_DATE_RE.fullmatch(cand_ans))
                    else (
                        "Give the value and unit"
                        if _NUMBER_WITH_UNIT_RE.search(cand_ans)
                        else "Name the person, place, or institution"
                    )
                )
                t_fam = "table (A)" if (_YEAR_RE.fullmatch(cand_ans) or _FULL_DATE_RE.fullmatch(cand_ans)) else ("table (C)" if _NUMBER_WITH_UNIT_RE.search(cand_ans) else "table (E)")
                q_choice = choose_question_for_fact(
                    f"{row_entity} | {col_name}: {raw_cell}",
                    cand_ans,
                    gap_sentence=clue_str,
                    default_prompt=prompt_str,
                    subject=row_entity,
                    subject_label=row_entity,
                    sheet_text=sheet_text or raw_cell,
                    table_meta={"row_header": row_entity, "col_header": col_name, "prompt": prompt_str},
                )
                t_card = {
                    "label": row_entity,
                    "subject_label": row_entity,
                    "front": q_choice["front"],
                    "prompt": q_choice["prompt"],
                    "clue": clue_str,
                    "question": q_choice["front"],
                    "answer": cand_ans,
                    "source_line": f"{row_entity} | {col_name}: {raw_cell}",
                    "subject": row_entity,
                    "page": page_num,
                    "section": col_name,
                    "answer_tier": "table_cell",
                    "family": t_fam,
                    "expression_family": t_fam,
                    "card_source": "table",
                    "template": q_choice["template"],
                    "_template_alternatives": q_choice.get("alternatives", []),
                }
                if score_card(t_card, sheet_text or raw_cell)["accepted"]:
                    out_cards.append(t_card)

    return out_cards


def explain_no_card_reason(line: str, subject: str = "") -> str:
    """Return a concise human-readable reason why `write_key_fact_card(line, subject)` produced no card."""
    raw_line = _normalize_spaces(line)
    if not raw_line:
        return "empty line"
    credit_stripped = _INLINE_SOURCE_CREDIT_RE.sub("", raw_line).strip()
    if is_sheet_furniture_or_heading(credit_stripped):
        return "dropped by input filter (heading, label, practice prompt, or furniture)"
    cleaned_with_bold = _BULLET_OR_NUMBER_PREFIX_RE.sub("", credit_stripped).strip()
    plain_line = _normalize_spaces(_strip_bold_markup(cleaned_with_bold))
    candidates = collect_answer_candidates(credit_stripped, subject=subject)
    if not candidates:
        return "no candidate key fact (only common words, category labels, or raw symbol lists; no bold term, proper name, date, number+unit, defined term, or formula)"
    rejected_reasons: list[str] = []
    for _, raw_cand in candidates:
        cand = expand_or_clean_answer_on_line(raw_cand, plain_line)
        ok, reason = is_good_answer(cand, source_line=cleaned_with_bold, sheet=plain_line)
        if not ok:
            rejected_reasons.append(f"{cand!r} rejected ({reason})")
        else:
            rejected_reasons.append(f"{cand!r} could not form a non-leaking clue with a clear subject")
    return "; ".join(rejected_reasons[:3])


class CleanLinesResult(tuple):
    """Return value of `clean_lines(sheet)`.

    Behaves as a 2-tuple `(kept_lines, removed_lines)` and also exposes `.kept`,
    `.fact_lines`, `.removed`, `.removed_lines`, `.tables`, and `.sheet_has_explicit_marks`.
    """

    def __new__(
        cls,
        kept_lines: list[dict[str, Any]],
        removed_lines: list[dict[str, Any]],
        sheet_has_explicit_marks: bool = False,
        tables: list[dict[str, Any]] | None = None,
    ) -> "CleanLinesResult":
        instance = super().__new__(cls, (kept_lines, removed_lines))
        instance.kept = kept_lines
        instance.kept_lines = kept_lines
        instance.fact_lines = kept_lines
        instance.removed = removed_lines
        instance.removed_lines = removed_lines
        instance.tables = tables or []
        instance.sheet_has_explicit_marks = sheet_has_explicit_marks
        return instance


_URL_ONLY_RE = re.compile(
    r"(?:https?://\S+|www\.\S+|\b[a-z0-9.-]+\.(?:org|com|edu|gov|net|uk|in)/\S*)",
    re.IGNORECASE,
)

_CREDIT_LINE_START_RE = re.compile(
    r"^(?:Sources?|References?|Credits?|Bibliography|Citations?|Further\s+Reading|Image\s+credits?|Photo\s+credits?|Courtesy|Practice\s+source)\s*[:|]",
    re.IGNORECASE,
)


def _classify_fact_kind(line: str) -> str:
    """Classify a kept fact line into one of: 'sentence' | 'bullet' | 'numbered' | 'formula' | 'definition'."""
    s = _normalize_spaces(line)
    plain = _normalize_spaces(_strip_bold_markup(_BULLET_OR_NUMBER_PREFIX_RE.sub("", s)))
    formula_cand = re.split(r",\s*where\b|\s*\(where\b", plain, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    if _FORMULA_LINE_RE.match(formula_cand) or _CHEM_EQUATION_LINE_RE.match(plain) or _WORKED_CALCULATION_LINE_RE.match(plain):
        return "formula"
    if is_name_with_dates_and_title_line(s)[0]:
        return "definition"
    if re.match(r"^[•\-\*▪▸◦Æƒ‹\{]\s+", s):
        return "bullet"
    if re.match(r"^(?:\(\d+\)|\d+[.)]|[a-zA-Z][.)])\s+", s):
        return "numbered"
    if ": " in plain or re.search(r"\b(?:is\s+defined\s+as|refers\s+to|means|is\s+a\s+set\s+of|is\s+anything\s+that)\b", plain, re.IGNORECASE):
        return "definition"
    return "sentence"


def _is_hard_structural_boundary_line(line: str) -> bool:
    """Return True if `line` is a hard structural boundary (empty, table row, new bullet/numbered item,
    'Name (dates) – Title', practice/table/meta section heading, page header/footer, tip, URL, credit,
    picture/diagram callout, standalone formula, or numbered/ALL-CAPS heading) that can NEVER be the
    continuation of a wrapped sentence, even when the previous line ended with a connector word.
    """
    s = _normalize_spaces(line)
    if not s:
        return True
    if "|" in s or "\t" in s or len(re.findall(r"\s{3,}", line)) >= 2:
        return True
    if _BULLET_OR_NUMBER_PREFIX_RE.match(s):
        return True
    if is_name_with_dates_and_title_line(s)[0]:
        return True
    if (
        _TABLE_SECTION_HEADING_RE.match(s)
        or _PRACTICE_SECTION_HEADING_RE.match(s)
        or _PAGE_HEADER_FOOTER_RE.search(s)
        or _MEMORY_OR_STUDY_TIP_RE.search(s)
        or _PRACTICE_OR_EXERCISE_LINE_RE.search(s)
        or _SOURCE_OR_URL_LINE_RE.search(s)
        or _PICTURE_LINE_RE.search(s)
        or _DIAGRAM_CALLOUT_LABEL_RE.match(s)
        or _META_SECTION_LABEL_RE.match(s)
        or any(pat.search(s) for pat in _FURNITURE_PATTERNS)
    ):
        return True
    plain = _normalize_spaces(_strip_bold_markup(s))
    if _FORMULA_LINE_RE.match(plain) or _CHEM_EQUATION_LINE_RE.match(plain):
        return True
    if re.match(r"^(?:#+\s*|(?:[IVXLCDM]+|\d+|[A-Z])[.)]\s+)", plain) or (plain.isupper() and len(plain.split()) >= 2):
        return True
    return False


def _is_structural_non_wrappable_line(line: str) -> bool:
    """Return True if `line` is a standalone structural line (heading, furniture, table row, practice, tip, link, credit, figure, formula, or new bullet/numbered item) that must not be merged as a wrapped continuation."""
    if _is_hard_structural_boundary_line(line):
        return True
    s = _normalize_spaces(line)
    if is_sheet_furniture_or_heading(s):
        return True
    return False


_WRAPPED_CONNECTOR_ENDINGS = frozenset(
    {
        "of",
        "in",
        "to",
        "for",
        "with",
        "on",
        "at",
        "from",
        "by",
        "the",
        "a",
        "an",
        "and",
        "or",
        "as",
        "into",
        "was",
        "is",
        "are",
        "were",
        "has",
        "have",
        "had",
        "that",
        "which",
        "who",
        "whose",
        "where",
        "when",
        "while",
        "during",
        "after",
        "before",
        "under",
        "over",
        "between",
        "through",
        "against",
        "following",
        "including",
        "called",
        "known",
        "near",
        "around",
        "about",
        "nearly",
        "more",
        "less",
        "than",
        "such",
        "their",
        "his",
        "her",
        "its",
        "chaired",
        "founded",
        "established",
        "launched",
        "led",
        "built",
        "wrote",
        "authored",
    }
)


def _merge_wrapped_and_hyphenated_page_lines(raw_lines: list[str]) -> list[str]:
    """Rejoin hyphenated word breaks ('Consti-\\ntution' -> 'Constitution') and wrapped sentences across consecutive lines on the same page."""
    merged: list[str] = []
    i = 0
    n = len(raw_lines)
    while i < n:
        curr = raw_lines[i].strip()
        if not curr:
            i += 1
            continue
        while i + 1 < n:
            nxt = raw_lines[i + 1].strip()
            if not nxt:
                i += 1
                continue
            # 1. Hyphenated word break at end of `curr` (e.g. "Consti-" + "tution came into force.")
            m_hyph = re.search(r"([A-Za-z]{2,})-$", curr)
            m_nxt_word = re.match(r"^([a-z]{2,})\b", nxt)
            if m_hyph and m_nxt_word and not _is_hard_structural_boundary_line(nxt):
                curr = curr[:-1] + nxt
                i += 1
                continue

            # 2. Wrapped sentence across two PDF lines
            curr_body = _BULLET_OR_NUMBER_PREFIX_RE.sub("", curr).strip()
            curr_plain = _strip_bold_markup(curr_body).strip()
            last_word = curr_plain.split()[-1].strip(",;()'\"‘’“”").lower() if curr_plain.split() else ""
            ends_connector = last_word in _WRAPPED_CONNECTOR_ENDINGS or curr_plain.endswith(",")
            nxt_plain = _strip_bold_markup(nxt).strip()
            starts_lower = bool(nxt_plain and nxt_plain[0].islower())

            if (
                curr_body
                and not curr.endswith((".", "!", "?", ":", ";"))
                and not is_name_with_dates_and_title_line(curr)[0]
                and "|" not in curr
                and "\t" not in curr
                and not _FORMULA_LINE_RE.match(curr_plain)
                and not _CHEM_EQUATION_LINE_RE.match(curr_plain)
            ):
                # When `curr` ends with a connector word (e.g. ", the") or `nxt` starts with lowercase,
                # only check `_is_hard_structural_boundary_line(nxt)` so capitalized continuations like
                # "Non-Cooperation Movement in Mumbai." are joined cleanly!
                if (ends_connector or starts_lower) and not _is_hard_structural_boundary_line(nxt):
                    if ends_connector or not is_sheet_furniture_or_heading(curr):
                        curr = f"{curr} {nxt}"
                        i += 1
                        continue
                # Also join a multi-word unpunctuated sentence line (`>= 8` words, not a heading) with a non-heading sentence continuation
                if (
                    len(curr_plain.split()) >= 8
                    and not is_sheet_furniture_or_heading(curr)
                    and not _is_structural_non_wrappable_line(nxt)
                ):
                    curr = f"{curr} {nxt}"
                    i += 1
                    continue
            break
        merged.append(curr)
        i += 1
    return merged


def _split_table_cells(line: str) -> list[str]:
    """Split a table line into individual cell strings without joining across columns."""
    if "|" in line:
        return [c.strip() for c in line.split("|") if c.strip()]
    if "\t" in line:
        return [c.strip() for c in line.split("\t") if c.strip()]
    if len(re.findall(r"\s{3,}", line)) >= 2:
        return [c.strip() for c in re.split(r"\s{3,}", line.strip()) if c.strip()]
    return [line.strip()] if line.strip() else []


def _iter_sheet_lines_with_pages(sheet: Any) -> list[tuple[int, str]]:
    """Extract `(page_number, line_text)` pairs in reading order from `sheet`."""
    out: list[tuple[int, str]] = []
    if sheet is None:
        return out
    if isinstance(sheet, str):
        for raw in sheet.splitlines():
            s = raw.strip()
            if s:
                out.append((1, s))
        return out
    if hasattr(sheet, "pages") and isinstance(getattr(sheet, "pages"), list):
        for idx, page in enumerate(getattr(sheet, "pages"), start=1):
            pno = getattr(page, "page_number", idx) if not isinstance(page, dict) else int(page.get("page_number", idx))
            txt = (
                (getattr(page, "raw_text", "") or getattr(page, "text", ""))
                if not isinstance(page, dict)
                else str(page.get("raw_text", "") or page.get("text", ""))
            )
            for raw in str(txt).splitlines():
                s = raw.strip()
                if s:
                    out.append((pno, s))
        if out:
            return out
    if isinstance(sheet, dict):
        pages = sheet.get("pages")
        if isinstance(pages, list):
            for idx, page in enumerate(pages, start=1):
                if isinstance(page, dict):
                    pno = int(page.get("page_number", idx))
                    txt = str(page.get("raw_text", "") or page.get("text", ""))
                else:
                    pno = int(getattr(page, "page_number", idx))
                    txt = str(getattr(page, "raw_text", "") or getattr(page, "text", ""))
                for raw in txt.splitlines():
                    s = raw.strip()
                    if s:
                        out.append((pno, s))
            if out:
                return out
        raw_text = sheet.get("raw_text") or sheet.get("text") or sheet.get("full_text") or sheet.get("content")
        if isinstance(raw_text, str):
            return _iter_sheet_lines_with_pages(raw_text)
        lines = sheet.get("lines")
        if isinstance(lines, list):
            return _iter_sheet_lines_with_pages(lines)
    if isinstance(sheet, (list, tuple)):
        for item in sheet:
            if isinstance(item, str):
                for raw in item.splitlines():
                    s = raw.strip()
                    if s:
                        out.append((1, s))
            elif isinstance(item, dict):
                pno = int(item.get("page", item.get("page_number", 1)))
                txt = str(item.get("text", item.get("line", item.get("raw_text", ""))))
                for raw in txt.splitlines():
                    s = raw.strip()
                    if s:
                        out.append((pno, s))
        return out
    raw_text = getattr(sheet, "raw_text", None) or getattr(sheet, "text", None) or getattr(sheet, "full_text", None)
    if isinstance(raw_text, str):
        return _iter_sheet_lines_with_pages(raw_text)
    return out


def clean_sheet(pdf: Any) -> dict[str, Any]:
    """Turn a sheet (PDF path, ExtractionResult, dict, list of lines, or text) into:
    {
      "facts": [ {id, page, text, bold_spans, subject, section, kind, is_marked, raw_line} ],
      "removed": [ {page, text, line, reason} ],
      "tables": [ {page, header, rows} ]
    }
    Each removed line gets exactly one reason from:
      "heading", "furniture", "credit", "link", "practice", "tip", "table", "figure".
    """
    extraction_obj = None
    if isinstance(pdf, (str, Path)):
        s_pdf = str(pdf)
        if "\n" not in s_pdf and s_pdf.lower().endswith(".pdf") and Path(s_pdf).exists():
            from question_quality_engine import PDFExtractionEngine

            extraction_obj = PDFExtractionEngine().extract_from_pdf(s_pdf)

    source_input = extraction_obj if extraction_obj is not None else pdf
    raw_page_lines = _iter_sheet_lines_with_pages(source_input)

    # Group lines by page and rejoin hyphenated breaks + wrapped sentences per page
    pages_map: dict[int, list[str]] = {}
    page_order: list[int] = []
    for pno, ln in raw_page_lines:
        if pno not in pages_map:
            pages_map[pno] = []
            page_order.append(pno)
        pages_map[pno].append(ln)

    page_lines: list[tuple[int, str]] = []
    for pno in page_order:
        merged_lines = _merge_wrapped_and_hyphenated_page_lines(pages_map[pno])
        for mln in merged_lines:
            page_lines.append((pno, mln))

    # Detect running headers/footers repeated across 2+ pages
    norm_line_pages: dict[str, set[int]] = {}
    for pno, ln in page_lines:
        norm_key = re.sub(r"\b(?:Page|Sheet)\s+\d+(?:\s*(?:of|/)\s*\d+)?\b", "PAGE_N", ln, flags=re.IGNORECASE).strip()
        if len(norm_key.split()) <= 14:
            norm_line_pages.setdefault(norm_key.lower(), set()).add(pno)

    repeated_furniture_keys = {
        k
        for k, pset in norm_line_pages.items()
        if len(pset) >= 2
        and k.count("|") < 2
        and "\t" not in k
        and k not in {"facts to remember", "check your understanding", "quick check", "key terms", "quick revision notes"}
        and not _FORMULA_LINE_RE.match(k)
        and not _CHEM_EQUATION_LINE_RE.match(k)
    }

    # Also collect any source names listed in "Sources:" / "References:" lines on the sheet
    sheet_source_names: set[str] = set()
    for _, ln in page_lines:
        if _CREDIT_LINE_START_RE.match(ln):
            body = _CREDIT_LINE_START_RE.sub("", ln).strip()
            for part in re.split(r"[;,|]", body):
                clean_part = part.strip(" .()")
                if clean_part and 1 <= len(clean_part.split()) <= 4:
                    sheet_source_names.add(clean_part.lower())

    facts: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []

    current_subject = ""
    current_section = ""
    in_practice_section = False
    practice_is_end_matter = False
    in_table_section = False
    current_table: dict[str, Any] | None = None
    prev_page: int | None = None

    def flush_table() -> None:
        nonlocal current_table
        if current_table and (current_table.get("header") or current_table.get("rows")):
            tables.append(current_table)
        current_table = None

    for page_num, ln in page_lines:
        if prev_page is not None and page_num != prev_page:
            flush_table()
            in_table_section = False
            if in_practice_section and not practice_is_end_matter:
                in_practice_section = False
        prev_page = page_num

        # Strip rhetorical "Why? " prefix when followed by a complete declarative sentence
        m_why = re.match(r"^Why\?\s+([A-Z].+\.)$", ln)
        if m_why and not in_practice_section:
            ln = m_why.group(1).strip()

        # Check for inline parenthetical source/location credits
        inline_matches = [m.group(0).strip() for m in _INLINE_SOURCE_CREDIT_RE.finditer(ln) if m.group(0).strip()]
        s = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", ln))

        # Also check if a trailing parenthetical matches a source from `sheet_source_names`
        m_trail_paren = re.search(r"\s*\(([A-Z][A-Za-z0-9\s&.\-]{1,35})\)\.?\s*$", s)
        if m_trail_paren and m_trail_paren.group(1).strip().lower() in sheet_source_names:
            cred_tok = f"({m_trail_paren.group(1).strip()})"
            inline_matches.append(cred_tok)
            had_dot = s.rstrip().endswith(".")
            s = s[: m_trail_paren.start()].rstrip()
            if had_dot and not s.endswith("."):
                s += "."

        if not s:
            flush_table()
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "credit"})
            continue

        # 6. Table section heading
        if _TABLE_SECTION_HEADING_RE.match(s):
            flush_table()
            in_table_section = True
            current_subject = ""
            m_tbl_topic = re.match(r"^Page\s+\d+\s*[—–\-:]\s*(.+)$", s, re.IGNORECASE)
            if m_tbl_topic:
                current_section = m_tbl_topic.group(1).strip()
            current_table = {"page": page_num, "header": [], "rows": []}
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "table"})
            continue

        # 4. Practice / Answer Key / Exercises section heading
        if _PRACTICE_SECTION_HEADING_RE.match(s):
            flush_table()
            in_table_section = False
            in_practice_section = True
            if _END_MATTER_PRACTICE_HEADING_RE.match(s):
                practice_is_end_matter = True
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "practice"})
            continue

        # 2. Page headers / footers / repeated running furniture across 2+ pages
        norm_key = re.sub(r"\b(?:Page|Sheet)\s+\d+(?:\s*(?:of|/)\s*\d+)?\b", "PAGE_N", s, flags=re.IGNORECASE).strip().lower()
        if _PAGE_HEADER_FOOTER_RE.search(s) or norm_key in repeated_furniture_keys:
            m_page_topic = re.match(r"^Page\s+\d+\s*[—–\-:]\s*(.+)$", s, re.IGNORECASE)
            if m_page_topic:
                flush_table()
                in_table_section = False
                if in_practice_section and not practice_is_end_matter:
                    in_practice_section = False
                topic_str = m_page_topic.group(1).strip()
                if topic_str:
                    current_section = topic_str[:1].upper() + topic_str[1:]
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "furniture"})
            continue

        # Special rule in Type 1: "Name (dates) – Title" counts as a subject heading AND as one fact line
        is_ndt, ndt_subj = is_name_with_dates_and_title_line(s)
        if is_ndt and not in_practice_section and not in_table_section:
            flush_table()
            current_subject = ndt_subj
            for cred in inline_matches:
                removed.append({"page": page_num, "text": cred, "line": cred, "reason": "credit"})
            bold_spans = [
                (m.group(1) or m.group(2) or m.group(3)).strip()
                for m in _BOLD_SPAN_RE.finditer(s)
                if (m.group(1) or m.group(2) or m.group(3))
            ]
            facts.append(
                {
                    "id": len(facts) + 1,
                    "page": page_num,
                    "text": s,
                    "line": s,
                    "raw_line": ln,
                    "bold_spans": bold_spans,
                    "bold": bold_spans,
                    "has_bold": bool(bold_spans),
                    "subject": current_subject,
                    "nearest_subject_heading": current_subject,
                    "section": current_section,
                    "kind": "definition",
                    "is_marked": False,
                    "credits_removed": inline_matches,
                }
            )
            continue

        # 1. Numbered section / topic heading that exits a page-local practice/table block
        if not practice_is_end_matter and re.match(r"^(?:[IVXLCDM]+|\d+)[.)]\s+[A-Z]", s):
            ent_subj = extract_entity_subject_from_heading(s)
            if ent_subj or (
                is_sheet_furniture_or_heading(s)
                and not _PRACTICE_OR_EXERCISE_LINE_RE.search(s)
                and "?" not in s
            ):
                flush_table()
                in_practice_section = False
                in_table_section = False
                if ent_subj:
                    current_subject = ent_subj
                    if not current_section:
                        current_section = ent_subj
                else:
                    current_section = _clean_subject_heading(s) or s
                removed.append({"page": page_num, "text": ln, "line": ln, "reason": "heading"})
                continue

        # 6. Inside a table section or pipe/tab/multi-column table row -> `reason="table"`, structured in `tables`
        is_row_delimited = "|" in s or "\t" in s or len(re.findall(r"\s{3,}", ln)) >= 2
        if in_table_section or is_row_delimited:
            cells = _split_table_cells(s) if is_row_delimited else [s]
            if is_row_delimited and len(cells) >= 2:
                if current_table is None or current_table["page"] != page_num:
                    flush_table()
                    current_table = {"page": page_num, "header": cells, "rows": []}
                elif not current_table["header"]:
                    current_table["header"] = cells
                else:
                    current_table["rows"].append(cells)
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "table"})
            continue

        flush_table()

        # 5. Memory tips and study tips -> `reason="tip"`
        if _MEMORY_OR_STUDY_TIP_RE.search(s):
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "tip"})
            continue

        # 7. Figures, diagrams, and captions -> `reason="figure"` (unless the caption is a full sentence stating a fact)
        if _PICTURE_LINE_RE.search(s) or _DIAGRAM_CALLOUT_LABEL_RE.match(s):
            m_cap = re.match(r"^(?:Figure|Fig\.?|Picture|Image|Diagram)\s+\d*[:.\-–]\s*(.+)$", s, re.IGNORECASE)
            if m_cap:
                cap_body = m_cap.group(1).strip()
                has_cap_verb = bool(
                    re.search(
                        r"\b(?:is|are|was|were|has|have|pumps?|flows?|shows?|illustrates?|connects?|converts?|produces?|absorbs?|contains?|travels?|moves?)\b",
                        cap_body,
                        re.IGNORECASE,
                    )
                )
                if cap_body.endswith(".") and has_cap_verb and len(cap_body.split()) >= 5:
                    s = cap_body
                else:
                    removed.append({"page": page_num, "text": ln, "line": ln, "reason": "figure"})
                    continue
            else:
                removed.append({"page": page_num, "text": ln, "line": ln, "reason": "figure"})
                continue

        # Short rhetorical question subheading (e.g. "What is matter?") outside practice section -> `reason="heading"`
        if (
            not in_practice_section
            and s.endswith("?")
            and len(s.split()) <= 5
            and not re.match(r"^(?:Q\.?\s*\d+|\d+[.)]|\(\d+\)|[a-zA-Z][.)])\b", s, re.IGNORECASE)
        ):
            current_section = s.rstrip("?").strip()
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "heading"})
            continue

        # Keep worked calculations with a taught numerical result ("Solution: Speed = 120 ÷ 2 = 60 km/h.") and chemical equations ("Equation: 2H2 + O2 -> 2H2O")
        s_plain_body = _BULLET_OR_NUMBER_PREFIX_RE.sub("", _strip_bold_markup(s)).strip()
        is_worked_or_chem = bool(
            not in_practice_section
            and "?" not in s
            and not re.search(r"\bFind\s+", s, re.IGNORECASE)
            and (_CHEM_EQUATION_LINE_RE.match(s_plain_body) or _WORKED_CALCULATION_LINE_RE.match(s_plain_body))
        )

        # 4. Inside a practice section or matching Q1./Ans:/Exercise/question patterns -> `reason="practice"`
        if not is_worked_or_chem and (in_practice_section or _PRACTICE_OR_EXERCISE_LINE_RE.search(s) or "?" in s):
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "practice"})
            continue

        # 3a. Links (URLs) -> `reason="link"`
        if _URL_ONLY_RE.search(s):
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "link"})
            continue

        # 3b. Standalone source credit lines ("Sources: ...", "References: ...") -> `reason="credit"`
        if _CREDIT_LINE_START_RE.match(s) or _SOURCE_OR_URL_LINE_RE.search(s):
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "credit"})
            continue

        # 2. Page furniture tags ("FULL CARD", "RBS HQ", "NOTE:", "Sheet 2") -> `reason="furniture"`
        if any(pat.search(s) for pat in _FURNITURE_PATTERNS) or re.match(r"^(?:NOTE| TAG|LABEL|SHEET\s+\d+)\s*:?\s*$", s, re.IGNORECASE):
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "furniture"})
            continue

        # 1. Headings, section titles, ALL-CAPS banners, "•"-joined header bars, and meta section labels -> `reason="heading"`
        if not is_worked_or_chem and (_META_SECTION_LABEL_RE.match(s) or is_sheet_furniture_or_heading(s)):
            ent_subj = extract_entity_subject_from_heading(s)
            if ent_subj:
                current_subject = ent_subj
            clean_sec = _clean_subject_heading(s)
            if clean_sec:
                current_section = clean_sec
            removed.append({"page": page_num, "text": ln, "line": ln, "reason": "heading"})
            continue

        # Record any stripped inline parenthetical credits (e.g. "(Britannica)") under reason="credit"
        for cred in inline_matches:
            removed.append(
                {
                    "page": page_num,
                    "text": cred,
                    "line": cred,
                    "source_line": ln,
                    "kept_text": s,
                    "reason": "credit",
                }
            )

        bold_spans = [
            (m.group(1) or m.group(2) or m.group(3)).strip()
            for m in _BOLD_SPAN_RE.finditer(s)
            if (m.group(1) or m.group(2) or m.group(3))
        ]
        marked = is_marked_for_key_facts(s)
        kind = _classify_fact_kind(s)
        facts.append(
            {
                "id": len(facts) + 1,
                "page": page_num,
                "text": s,
                "line": s,
                "raw_line": ln,
                "bold_spans": bold_spans,
                "bold": bold_spans,
                "has_bold": bool(bold_spans),
                "subject": current_subject,
                "nearest_subject_heading": current_subject,
                "section": current_section,
                "kind": kind,
                "is_marked": marked,
                "credits_removed": inline_matches,
            }
        )

    flush_table()
    marked_count = sum(1 for item in facts if item["is_marked"])
    sheet_has_explicit_marks = bool(
        facts
        and (
            marked_count == len(facts)
            or marked_count >= max(2, len(facts) // 2)
        )
    )
    return {
        "facts": facts,
        "removed": removed,
        "tables": tables,
        "sheet_has_explicit_marks": sheet_has_explicit_marks,
    }


_REASON_TO_LEGACY_TYPE = {
    "heading": "heading",
    "furniture": "page_furniture",
    "figure": "page_furniture",
    "credit": "source_credit",
    "link": "source_credit",
    "practice": "practice_section",
    "tip": "memory_tip",
    "table": "table",
}


def clean_lines(sheet: Any) -> CleanLinesResult:
    """Wrapper around `clean_sheet(sheet)` returning `CleanLinesResult(kept_lines, removed_lines)`."""
    cleaned = clean_sheet(sheet)
    kept_lines = cleaned["facts"]
    removed_lines: list[dict[str, Any]] = []
    for rem in cleaned["removed"]:
        reason_code = rem["reason"]
        legacy_type = _REASON_TO_LEGACY_TYPE.get(reason_code, reason_code)
        entry = dict(rem)
        entry["type"] = legacy_type
        removed_lines.append(entry)
    return CleanLinesResult(
        kept_lines,
        removed_lines,
        sheet_has_explicit_marks=cleaned["sheet_has_explicit_marks"],
        tables=cleaned["tables"],
    )


def preprocess_sheet_lines(sheet: Any) -> tuple[list[tuple[str, str, bool]], bool]:
    """Input-side filter before any card is written (delegates to `clean_sheet(sheet)`)."""
    cleaned = clean_sheet(sheet)
    scanned_items = [
        (item["text"], item["subject"], item["is_marked"])
        for item in cleaned["facts"]
    ]
    return scanned_items, cleaned["sheet_has_explicit_marks"]


_TIER_PRIORITY_RANK: dict[str, int] = {
    "bold": 0,
    "practice_priority": 1,
    "date_or_year": 2,
    "proper_name": 3,
    "number_with_unit": 4,
    "technical_term": 5,
    "formula_part": 6,
    "table_cell": 7,
}


def _split_paragraph_into_sentences(text: str) -> list[str]:
    """Split a multi-sentence paragraph or semicolon/clause-joined fact line into standalone sentences/clauses."""
    plain = _normalize_spaces(text)
    if not plain:
        return []
    # Split on sentence-ending period followed by a capital letter (avoiding honorifics like "Dr.", "Mr.", "St.", "B. R.")
    parts = re.split(r"(?<![A-Z])(?<!\bDr)(?<!\bMr)(?<!\bMs)(?<!\bSt)\.\s+(?=[A-Z])", plain)
    out: list[str] = []
    first_subj = ""
    if parts:
        m_lead = re.match(
            r"^(?:•\s*)?((?:India's\s+Constitution|The\s+Preamble|The\s+Constitution|Fundamental\s+Rights|Fundamental\s+Duties|A\s+constitution|A\s+solid|A\s+liquid|A\s+gas|An\s+element|A\s+compound|A\s+mixture|A\s+physical\s+change|A\s+chemical\s+change|Matter|Materials|Filtration|Evaporation|Distillation|Atoms|[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}))\b",
            parts[0].strip(),
        )
        if m_lead:
            first_subj = m_lead.group(1).strip()

    for idx, p in enumerate(parts):
        s = p.strip()
        if not s:
            continue
        if not s.endswith((".", "?", "!")):
            s += "."
        if idx > 0 and first_subj:
            # Resolve leading pronoun ("It ", "They ") and internal "it came" to the paragraph's leading subject
            if re.match(r"^It\s+", s):
                s = f"{first_subj} " + s[3:]
            elif re.match(r"^They\s+also\s+", s):
                s = f"{first_subj} also " + s[10:]
            elif re.match(r"^They\s+", s):
                s = f"{first_subj} " + s[5:]
            s = re.sub(r"\bit\s+came\s+into\s+effect\b", f"{first_subj} came into effect", s)

        # Check for "<Intro>: <Clause 1>, while <Clause 2>."
        m_while = re.match(r"^([^:]+:\s*[^,]+?),\s+while\s+(.+)\.$", s)
        if m_while:
            intro_prefix = m_while.group(1).split(":", 1)[0].strip()
            out.append(m_while.group(1).strip() + ".")
            out.append(f"{intro_prefix}: {m_while.group(2).strip()}.")
            continue

        # Check for 3-part coordinated role sentence ("The <N1> <V1> <O1>, the <N2> <V2> them/it ..., and the <N3> <V3> ...")
        m_coord3 = re.match(
            r"^(The\s+[a-z]+\s+[a-z]+\s+([a-z]+)),\s+the\s+([a-z]+\s+.+?),\s+and\s+the\s+([a-z]+\s+.+)\.$",
            s,
        )
        if m_coord3:
            c1 = m_coord3.group(1).strip() + "."
            obj_noun = m_coord3.group(2).strip()
            c2_raw = re.sub(r"\bcarries\s+them\s+out\b", f"carries out {obj_noun}", m_coord3.group(3).strip())
            c2 = f"The {c2_raw}."
            c3 = f"The {m_coord3.group(4).strip()}."
            subj_ctx = (first_subj[0].lower() + first_subj[1:]) if first_subj.startswith("The ") else first_subj
            prefix_ctx = f"Under {subj_ctx}, " if subj_ctx else ""
            for c_part in (c1, c2, c3):
                out.append(f"{prefix_ctx}{c_part[0].lower() + c_part[1:]}" if prefix_ctx else c_part)
            continue

        out.append(s)

        # Also if a sentence states both "by <Agent>" AND "on <Full Date>", yield a date-focused clause for secondary top-up
        m_by_date = re.match(
            rf"^(.+?)\s+by\s+(?:the\s+)?[A-Z][A-Za-z\s]+\s+(on\s+\d{{1,2}}\s+{_MONTH_NAMES_PATTERN}\s+\d{{4}}\.)$",
            s,
        )
        if m_by_date:
            out.append(f"{m_by_date.group(1).strip()} {m_by_date.group(2).strip()}")

    return out


def plan_key_facts_cards(
    sheet: Any,
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
    target_min: int = 15,
    target_max: int = 25,
    hard_cap: int = 30,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate a 15-minute Key Facts set (15–25 target, hard cap 30) spread across all sections and pages,
    including formulas and up to 1/3 single-cell table cards, with subject labels and no repeated facts.
    """
    cleaned = clean_sheet(sheet)
    sheet_has_explicit_marks = cleaned["sheet_has_explicit_marks"]
    sheet_text = _get_sheet_text(sheet)

    primary_candidates: list[dict[str, Any]] = []
    secondary_candidates: list[dict[str, Any]] = []
    dropped_report: list[dict[str, Any]] = []

    pages_present = {int(item.get("page", 1)) for item in cleaned["facts"]} | {
        int(t.get("page", 1)) for t in cleaned["tables"]
    }
    is_real_multi_section_sheet = len(pages_present) >= 2 or len(cleaned["facts"]) >= 10

    # Family L: Link the sheet's own practice questions back to kept fact lines to mark them HIGH PRIORITY
    practice_removed_texts = [
        rem["text"] for rem in cleaned["removed"] if rem.get("reason") == "practice" and rem.get("text")
    ]
    fact_texts = [item["text"] for item in cleaned["facts"]]
    practice_signals_by_fact_idx = (
        FAMILY_L.match_questions_to_facts(practice_removed_texts, fact_texts)
        if practice_removed_texts and fact_texts
        else {}
    )

    order_counter = 0
    for fact_idx, item in enumerate(cleaned["facts"]):
        ln = item["text"]
        subj = item["subject"]
        sec = item.get("section", "")
        page_num = int(item.get("page", 1))
        is_marked = item["is_marked"]
        b_spans = item.get("bold_spans") or []
        item_practice_signals = practice_signals_by_fact_idx.get(fact_idx, [])
        if sheet_has_explicit_marks and not is_marked:
            continue

        # On unmarked multi-page prose sheets where paragraphs contain multiple sentences,
        # split paragraphs into standalone sentences first so every card front is one whole sentence.
        if is_real_multi_section_sheet and not sheet_has_explicit_marks and len(cleaned["facts"]) < target_min:
            sent_units = _split_paragraph_into_sentences(ln)
            if not sent_units:
                sent_units = [ln]
        else:
            sent_units = [ln]

        for unit_idx, unit_ln in enumerate(sent_units):
            order_counter += 1
            card = write_key_fact_card(
                unit_ln,
                subject=subj,
                bold_spans=b_spans,
                page=page_num,
                section=sec,
                practice_signals=item_practice_signals,
            )
            if card is None:
                if unit_idx == 0:
                    dropped_report.append(
                        {
                            "clue": "",
                            "answer": "",
                            "source_line": ln,
                            "scores": {},
                            "average": 0.0,
                            "reasons": [f"no_card: {explain_no_card_reason(unit_ln, subject=subj)}"],
                        }
                    )
                continue

            if not sheet_has_explicit_marks:
                card["note"] = UNMARKED_SHEET_NOTE
            card["_order"] = order_counter
            card["_unit_ln"] = unit_ln
            card["_b_spans"] = b_spans
            card["_practice_signals"] = item_practice_signals
            primary_candidates.append(card)

            if is_real_multi_section_sheet:
                used_ans = {card["answer"]}
                for extra_pass in range(2):
                    sec_card = write_key_fact_card(
                        unit_ln,
                        subject=subj,
                        bold_spans=b_spans,
                        page=page_num,
                        section=sec,
                        exclude_answers=used_ans,
                        practice_signals=item_practice_signals,
                    )
                    if sec_card is None:
                        break
                    used_ans.add(sec_card["answer"])
                    if not sheet_has_explicit_marks:
                        sec_card["note"] = UNMARKED_SHEET_NOTE
                    sec_card["_order"] = order_counter + (extra_pass + 1) * 0.1
                    secondary_candidates.append(sec_card)

    # First-pass deduplication and quality validation on primary prose/formula cards in reading order
    valid_primary: list[dict[str, Any]] = []
    seen_facts: set[tuple[str, str]] = set()
    seen_answers_global: set[str] = set()

    def _try_accept_candidate(cand: dict[str, Any], current_accepted: list[dict[str, Any]], record_drop: bool = True) -> bool:
        ans_low = _normalize_spaces(cand.get("answer", "")).lower()
        subj_low = _normalize_spaces(cand.get("subject", "")).lower()
        fact_key = (subj_low, ans_low)
        # If this candidate's answer was already used elsewhere on the sheet, try picking an alternative candidate on the same line
        if (fact_key in seen_facts or ans_low in seen_answers_global) and cand.get("_unit_ln"):
            alt_card = write_key_fact_card(
                cand["_unit_ln"],
                subject=cand.get("subject", ""),
                bold_spans=cand.get("_b_spans") or [],
                page=int(cand.get("page", 1)),
                section=cand.get("section", ""),
                exclude_answers=seen_answers_global | {ans_low},
                practice_signals=cand.get("_practice_signals") or [],
            )
            if alt_card is not None:
                if not sheet_has_explicit_marks:
                    alt_card["note"] = UNMARKED_SHEET_NOTE
                alt_card["_order"] = cand.get("_order", 0)
                cand = alt_card
                ans_low = _normalize_spaces(cand.get("answer", "")).lower()
                subj_low = _normalize_spaces(cand.get("subject", "")).lower()
                fact_key = (subj_low, ans_low)

        # Never repeat the same answer twice in the set
        if fact_key in seen_facts or ans_low in seen_answers_global:
            if record_drop:
                dropped_report.append(
                    {
                        "clue": _extract_clue(cand),
                        "answer": _extract_answer(cand),
                        "source_line": _extract_evidence(cand),
                        "scores": {"distinct": 1},
                        "average": 1.0,
                        "reasons": [f"distinct: duplicate fact {ans_low!r} already tested in the set"],
                    }
                )
            return False

        scores, reasons = score_card(cand, sheet, prior_cards=current_accepted)
        if is_card_acceptable(
            scores,
            min_criterion_score=min_criterion_score,
            min_average_score=min_average_score,
        ):
            cand.pop("_unit_ln", None)
            cand.pop("_b_spans", None)
            cand.pop("_practice_signals", None)
            current_accepted.append(cand)
            seen_facts.add(fact_key)
            seen_answers_global.add(ans_low)
            return True
        if record_drop:
            dropped_report.append(
                {
                    "clue": _extract_clue(cand),
                    "answer": _extract_answer(cand),
                    "source_line": _extract_evidence(cand),
                    "scores": scores,
                    "average": round(sum(scores.values()) / max(1, len(scores)), 2),
                    "reasons": reasons,
                }
            )
        return False

    for cand in primary_candidates:
        _try_accept_candidate(cand, valid_primary, record_drop=True)

    # If the sheet has fewer than `target_min` (15) cards and secondary candidates exist, top up from secondary candidates
    if is_real_multi_section_sheet and len(valid_primary) < target_min and secondary_candidates:
        for sec_cand in secondary_candidates:
            if len(valid_primary) >= target_max:
                break
            _try_accept_candidate(sec_cand, valid_primary, record_drop=False)

    # Step 4: Generate single-cell table cards and cap them at <= 1/3 of the final set
    # (`T <= (P + T) / 3  <=>  T <= P // 2`, or up to `hard_cap // 3` if `P == 0`)
    table_candidates = write_table_cards(cleaned["tables"], sheet_text=sheet_text)
    max_table_cards = (len(valid_primary) // 2) if len(valid_primary) > 0 else (hard_cap // 3)
    max_table_cards = min(max_table_cards, target_max // 3, 5)
    valid_table_cards: list[dict[str, Any]] = []
    if max_table_cards > 0 and table_candidates:
        # Spread table cards across different entities/rows
        by_entity: dict[str, list[dict[str, Any]]] = {}
        entity_order: list[str] = []
        for idx_t, tc in enumerate(table_candidates):
            tc["_order"] = 10000 + idx_t
            ent_key = tc.get("label", "") or tc.get("subject", "") or str(idx_t)
            if ent_key not in by_entity:
                by_entity[ent_key] = []
                entity_order.append(ent_key)
            by_entity[ent_key].append(tc)

        probe_pool = list(valid_primary)
        added_table = 0
        made_progress = True
        while added_table < max_table_cards and made_progress:
            made_progress = False
            for ent_key in entity_order:
                if added_table >= max_table_cards:
                    break
                while by_entity[ent_key]:
                    tc = by_entity[ent_key].pop(0)
                    if not sheet_has_explicit_marks:
                        tc["note"] = UNMARKED_SHEET_NOTE
                    if _try_accept_candidate(tc, probe_pool, record_drop=False):
                        valid_table_cards.append(tc)
                        added_table += 1
                        made_progress = True
                        break

    all_accepted = valid_primary + valid_table_cards

    # Step 2: If total cards exceed `target_max` (25, hard cap `hard_cap` = 30), select in priority order
    # while spreading across all headings/sections and pages (round-robin across section/page buckets).
    cap_limit = min(target_max, hard_cap)
    if len(all_accepted) > cap_limit:
        buckets: dict[tuple[int, str], list[dict[str, Any]]] = {}
        bucket_order: list[tuple[int, str]] = []
        for c in all_accepted:
            b_key = (int(c.get("page", 1)), str(c.get("label") or c.get("subject") or c.get("section") or ""))
            if b_key not in buckets:
                buckets[b_key] = []
                bucket_order.append(b_key)
            buckets[b_key].append(c)

        for b_key in bucket_order:
            buckets[b_key].sort(
                key=lambda x: (
                    _TIER_PRIORITY_RANK.get(str(x.get("answer_tier", "technical_term")), 5),
                    float(x.get("_order", 0)),
                )
            )

        selected: list[dict[str, Any]] = []
        while len(selected) < cap_limit:
            progressed = False
            for b_key in bucket_order:
                if len(selected) >= cap_limit:
                    break
                if buckets[b_key]:
                    selected.append(buckets[b_key].pop(0))
                    progressed = True
            if not progressed:
                break
        all_accepted = selected

    # Sort final set in reading order (by page, then source order) and strip internal `_order` key
    all_accepted.sort(key=lambda x: (int(x.get("page", 1)), float(x.get("_order", 0))))
    for c in all_accepted:
        c.pop("_order", None)

    # Prompt 9 Step 2 & Step 5: Balance template mix (<= 3 in a row of same template, <= 60% per template)
    all_accepted = balance_template_mix(all_accepted)

    return all_accepted, dropped_report


def _make_plain_fallback_card(card: Any) -> Any:
    """Build a plain reading/fact card for Detective-mode Rule A fallback when requested."""
    evidence = _extract_evidence(card) or _extract_clue(card)
    subject = _extract_subject(card)
    if isinstance(card, dict):
        fallback = dict(card)
        fallback["card_type"] = "plain"
        fallback["kind"] = "plain"
        fallback["clue"] = evidence
        fallback["question"] = evidence
        fallback["answer"] = ""
        if subject:
            fallback["subject"] = subject
        return fallback

    try:
        import copy

        fallback_obj = copy.copy(card)
        for attr, val in (("card_type", "plain"), ("kind", "plain"), ("clue", evidence), ("question", evidence), ("answer", "")):
            if hasattr(fallback_obj, attr):
                setattr(fallback_obj, attr, val)
        return fallback_obj
    except Exception:
        return {"card_type": "plain", "clue": evidence, "answer": "", "source_line": evidence, "subject": subject}


def filter_cards_after_plan(
    cards: list[Any],
    sheet: Any,
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
    fallback_builder: Callable[[Any], Any] | None = None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Filter planned cards with score_card(), keeping fallback support for Detective mode."""
    accepted: list[Any] = []
    accepted_quiz_cards: list[Any] = []
    dropped_report: list[dict[str, Any]] = []
    builder = fallback_builder or _make_plain_fallback_card

    for card in cards:
        card_kind = _get_field(card, "card_type", "kind", "type").lower()
        if card_kind in ("plain", "fact", "reading", "note") or not _extract_answer(card):
            accepted.append(card)
            continue

        scores, reasons = score_card(card, sheet, prior_cards=accepted_quiz_cards)
        if is_card_acceptable(
            scores,
            min_criterion_score=min_criterion_score,
            min_average_score=min_average_score,
        ):
            accepted.append(card)
            accepted_quiz_cards.append(card)
        else:
            dropped_report.append(
                {
                    "clue": _extract_clue(card),
                    "answer": _extract_answer(card),
                    "source_line": _extract_evidence(card),
                    "scores": scores,
                    "average": round(sum(scores.values()) / max(1, len(scores)), 2),
                    "reasons": reasons,
                }
            )
            accepted.append(builder(card))

    return accepted, dropped_report


def format_dropped_cards_report(dropped_report: list[dict[str, Any]], sheet_name: str = "") -> str:
    """Format a concise CLI/batch_report summary of dropped cards and their failure reasons."""
    header = f"Card Quality Report{f' ({sheet_name})' if sheet_name else ''}: {len(dropped_report)} card(s) dropped"
    if not dropped_report:
        return f"{header} (all cards passed)."
    lines = [header]
    for idx, item in enumerate(dropped_report, start=1):
        clue = item.get("clue", "")
        ans = item.get("answer", "")
        avg = item.get("average", 0.0)
        reasons = "; ".join(item.get("reasons", []))
        lines.append(f"  {idx}. [avg={avg:.2f}] Q: {clue!r} | A: {ans!r} -> {reasons}")
    return "\n".join(lines)
