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

import re
from typing import Any, Callable

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
        r"(?:^|\b)(?:FULL\s+CARD|HALF\s+CARD|CARD\s+#?\d+|CASE\s+FILE\s*#?\d*|[A-Z]{2,6}\s+HQ|Page\s+\d+(?:\s+of\s+\d+)?|All\s+rights\s+reserved|Not\s+to\s+be\s+republished|Reprint\s+20\d{2}|Practice\s+Questions|Answer\s+Key|Check\s+Your\s+(?:Progress|Understanding)|Exercises?\s+for\s+Practice|Representative\s+practice\s+text|Not\s+a\s+syllabus\s+claim|SYNTHETIC\s+SAMPLE)\b",
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

# Formula patterns: e.g. "F = ma", "E = mc^2", "V = IR", "Speed = Distance ÷ Time", "F = ______"
_FORMULA_CLUE_RE = re.compile(
    r"(?:^|[:\s])(?:[A-Za-z][A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹]*\s*=\s*___+|___+\s*=\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^() ]+)(?:\s*$|[.?])"
)
_FORMULA_LINE_RE = re.compile(
    r"^(?:([A-Za-z][A-Za-z0-9\s’'\-–]{1,35}?)\s*:\s*)?([A-Za-z][A-Za-z0-9₀-₉]{0,12})\s*=\s*([A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()]+(?:\s*[×÷\*+\-/]\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹^()]+)*)\s*(?:\([^)]*\))?\.?$"
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
    r"(?:(?<=^)|(?<=[\s(\[:=]))([+\-±]?\d+(?:\.\d+)?(?:\s*[×x]\s*10[⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺]+)?\s*(?:°C|°F|K\b|km/h|m/s²|m/s|cm/s|g/cm³|kg/m³|km²|m²|cm²|mm²|m³|cm³|mm|cm|km|mg|kg|mL|L\b|mol/dm³|mol\b|kJ|J\b|kW|W\b|kPa|Pa\b|Hz|MHz|mA|A\b|kV|V\b|Ω|N\b|s\b|min\b|h\b|hr\b|hrs\b|%))(?=[\s.,;:)\]]|$)"
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
    return re.sub(r"\s+", " ", text).strip()


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
    return _get_field(card, "subject", "heading", "section", "entity", "topic", "title")


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

    # 1. Never a heading, section title, or label
    if _is_heading_or_label_answer(ans_clean, source_line=line_clean):
        return False, f"heading, section title, or label ({ans_clean!r})"

    # 2. Never an explicit common word or linking phrase ("If", "the", "and why", "Repeat", "Make", "Wear", "included", "variable", "law")
    if ans_clean.lower() in _FORBIDDEN_COMMON_WORD_ANSWERS or re.match(
        r"^(?:and|or|but|if|when|while|because)\s+(?:why|how|when|where|what|who|if|that|so)\b",
        ans_clean.lower(),
    ):
        return False, f"common word ({ans_clean!r})"

    # 3. Never a cut-off phrase
    bad_bounds, bound_reason = _has_invalid_answer_boundaries(ans_clean)
    if bad_bounds:
        return False, f"cut-off phrase: {bound_reason}"
    if _CUTOFF_PROPER_PREFIX_RE.search(ans_clean):
        return False, f"cut-off proper name prefix ({ans_clean!r})"

    if re.match(rf"^{_MONTH_NAMES_PATTERN}$", ans_clean, re.IGNORECASE):
        if not line_clean or _FULL_DATE_RE.search(line_clean):
            return False, f"cut-off date ({ans_clean!r} instead of full date)"

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
    if _is_forbidden_common_word_answer(ans_clean):
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

    max_allowed = MAX_PROPER_NAME_WORDS if _is_proper_name_phrase(ans_clean) else MAX_ANSWER_WORDS
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
        if word_count > 3 or len(ans_clean) > 25 or any(p in ans_clean for p in (".", ";", ",")):
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
        if len(ans_clean.split()) > 3 or len(ans_clean) > 25 or any(p in ans_clean for p in (".", ";", ",")):
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

    # Symbolic formula clues like "F = ______" identify the formula LHS symbol directly
    if is_formula_clue:
        return 5, []

    # 2. Clue must identify a concrete subject (a proper noun, named entity, or >=2 specific content nouns)
    # and must not rely on a dangling pronoun ("He graduated from ___", "Why did she do this?")
    first_clause = re.split(r"[.!?;]", clue_norm, maxsplit=1)[0].strip()
    if re.match(r"^(?:He|She|It|They|His|Her|Their|Him|Them)\b", first_clause, flags=re.IGNORECASE):
        reasons.append(f"names_subject: clue starts with dangling pronoun without naming who/what it is about ({clue_norm!r})")
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
        r"^\(?(?:Britannica|Wikipedia|NCERT|ICSE|CBSE|Source|Memory\s+Tip|FULL\s+CARD|HALF\s+CARD|CARD\s*\d*|Practice\s+Questions|Answer\s+Key)\)?$",
        answer.strip(),
        re.IGNORECASE,
    ):
        reasons.append(f"not_furniture: answer {answer!r} is a source credit or layout label")
        return 1, reasons

    return 5, []


def _score_not_table_soup(clue: str, answer: str, evidence: str = "", sheet_text: str = "") -> tuple[int, list[str]]:
    """Criterion 6: answer/clue isn't a run of several table cells or joined words from two table cells."""
    reasons: list[str] = []

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
    """Strip a leading '<subject>: ' prefix when comparing distinctness of two different facts under the same section."""
    c = _normalize_spaces(clue)
    s = _normalize_spaces(subject)
    if s and c.lower().startswith(s.lower() + ":"):
        return c[len(s) + 1 :].strip()
    return c


def _score_distinct(card: Any, prior_cards: list[Any]) -> tuple[int, list[str]]:
    """Criterion 7: no near-duplicate of another card in the same case file (no two cards test the same fact)."""
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

        if answer and answer == other_answer and "=" in clue and "=" in other_clue:
            return 1, [f"distinct: tests the same formula answer ({answer!r}) as card #{idx + 1}"]

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


def is_sheet_furniture_or_heading(line: str) -> bool:
    """Return True if a sheet line is furniture (Q&A, memory tip, credit, card/page label, footer, URL, picture, unanswered question, table text) or a bare/numbered heading."""
    s = _normalize_spaces(line)
    if not s:
        return True
    if (
        _PRACTICE_SECTION_HEADING_RE.match(s)
        or _TABLE_SECTION_HEADING_RE.match(s)
        or _META_SECTION_LABEL_RE.match(s)
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
    s_plain = _strip_bold_markup(s)
    if _FORMULA_LINE_RE.match(re.sub(r"^(?:[•\-\*▪▸◦]|\(\d+\)|\d+[.)])\s*", "", s_plain)):
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
    s_no_num = re.sub(r"^(?:#+\s*|\(\d+\)\s*|\d+[.)]\s*)", "", s_plain).strip()
    s_no_dates = re.sub(r"\(\s*\d{3,4}\s*[–\-—]\s*\d{2,4}\s*\)", "", s_no_num).strip()
    words = s_no_dates.split()
    has_verb = bool(
        re.search(
            r"\b(?:is|are|was|were|has|have|had|graduated|studied|born|died|served|worked|founded|established|appointed|elected|became|joined|led|wrote|authored|published|built|discovered|invented|chaired|presided|known|called|states|refers|occurs|dissociates|defied|marched|proclaimed|applied|adopted|came|moved|signed|enacted|protects?|describes?|introduces?|begins?|derives?|establishes?|makes?|carries|interprets?|resolves?|keeps?|takes?|spreads?|consists?|vibrate|changes?|contains?|separates?|uses?|alters?|produces?|rearrange|form|travels?|covers?|moves?)\b",
            s_no_dates,
            re.IGNORECASE,
        )
    )
    if not has_verb and ":" not in s_no_dates and "|" not in s_no_dates and "=" not in s_no_dates and len(words) <= 10:
        return True
    return False


def _clean_subject_heading(heading: str) -> str:
    """Clean a section/person heading by stripping life-span dates, numbered prefixes, and card/page labels."""
    h = _INLINE_SOURCE_CREDIT_RE.sub("", _strip_bold_markup(heading or ""))
    h = re.sub(r"^(?:#+\s*|\d+[.)]\s*)", "", h)
    h = re.sub(r"\b(?:FULL\s+CARD|HALF\s+CARD|CARD\s+#?\d+|CASE\s+FILE\s*#?\d*)\b[:.\-–]?\s*", "", h, flags=re.IGNORECASE)
    h = re.sub(r"\(\s*\d{3,4}\s*[–\-—]\s*\d{2,4}\s*\)", "", h)
    h = re.sub(r"^(?:CHAPTER|SECTION|UNIT|PART)\s+\d+[:.\-–]?\s*", "", h, flags=re.IGNORECASE)
    if "•" in h or "|" in h:
        h = ""
    # Strip trailing dash subtitle on numbered city/entity headings (e.g. "LONDON – Capital of the United Kingdom & England" -> "London")
    m_dash = re.match(r"^([A-Z][A-Za-z\s]{1,25}?)\s+[–—\-]\s+.+$", h.strip())
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
    """Return True if a sheet line is explicitly marked to learn in Key Facts mode (bold words, bold list, all-bold sentence, or bullet/numbered point)."""
    s = _normalize_spaces(line)
    if not s or is_sheet_furniture_or_heading(s):
        return False
    # Tables get no Key Facts cards
    if "|" in s or "\t" in s:
        return False
    if _BOLD_SPAN_RE.search(s):
        return True
    if _BULLET_OR_NUMBER_PREFIX_RE.match(s):
        return True
    return False


def collect_answer_candidates(line: str, subject: str = "") -> list[tuple[str, str]]:
    """Collect candidate answers from `line` in the exact 6-tier preference order of Prompt 3:
    1. 'bold'           — A word or phrase the sheet prints in BOLD.
    2. 'proper_name'    — A proper name: person, place, organisation, event, document.
    3. 'date_or_year'   — A full date or year ('1873', '8 August 1942', '3 December 1903').
    4. 'number_with_unit' — A number with its unit ('387 km', '40 mL', '2.0 m/s²').
    5. 'technical_term' — A technical term the sheet defines or explains ('resultant force', 'collision theory', 'Drafting Committee').
    6. 'formula_part'   — In a formula, one symbol or the result ('F = ______' -> 'ma').
    """
    raw_line = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", line or ""))
    if not raw_line:
        return []
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
    for b in raw_bolds:
        exp_b = expand_or_clean_answer_on_line(b, plain_line)
        if exp_b and len(exp_b.split()) <= MAX_PROPER_NAME_WORDS:
            tier_1_bold.append(exp_b)

    # Check if this is a pure symbolic/word formula line (e.g. "F = ma", "Speed = Distance ÷ Time", "Area of a rectangle: A = l × b")
    formula_candidate = re.split(r",\s*where\b|\s*\(where\b", plain_line, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    m_formula = _FORMULA_LINE_RE.match(formula_candidate)
    if m_formula:
        lhs_sym = m_formula.group(2).strip()
        rhs_expr = m_formula.group(3).strip().rstrip(".")
        if lhs_sym and rhs_expr and len(rhs_expr.split()) <= 3:
            tier_6_formulas.append(rhs_expr)
            return [("bold", b) for b in tier_1_bold] + [("formula_part", f) for f in tier_6_formulas]

    # --- Tier 2: Proper names (person, place, organisation, event, document) ---
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
    for m_q in re.finditer(r"[‘'“\"]([A-Z][A-Za-z0-9\s\-–]{2,40}?)[’'”\"]", plain_line):
        cand = expand_or_clean_answer_on_line(m_q.group(1), plain_line)
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

    # 2d. Multi-word Proper Names anywhere in the line (2 to 6 words, e.g. "Jamsetji Tata", "Satyashodhak Samaj", "Gowalia Tank Maidan", "Bombay Spinning and Weaving Company")
    for m_pn in re.finditer(
        r"\b((?:(?:Dr\.|Mr\.|Mrs\.|Ms\.|Sir|Lord|St\.)\s+)?[A-Z][A-Za-z0-9’'\-–]+(?:\s+(?:(?:and|of|the)\s+)?[A-Z][A-Za-z0-9’'\-–]+){1,5})\b",
        plain_line,
    ):
        raw_pn = m_pn.group(1)
        # Do not glue a possessive noun ("India's Constitution", "Scotland's Parliament") unless it is a named scientific law/principle ("Boyle's Law", "Archimedes' Principle")
        if re.match(r"^[A-Z][A-Za-z]+(?:’s|'s)\s+", raw_pn) and not re.search(
            r"\b(?:Law|Laws|Principle|Rule|Theorem|Constant|Theory|Effect)\b", raw_pn
        ):
            continue
        # Do not join two separate proper names across "and" ("London and Liverpool") unless followed by an institution/company head noun
        if " and " in raw_pn and not re.search(
            r"\b(?:Company|Samaj|Sabha|Committee|Commission|Assembly|Institute|University|College|Bank|Shipyard|Wolff)\b",
            raw_pn,
        ):
            raw_pn = raw_pn.split(" and ", 1)[0].strip()
        cand = expand_or_clean_answer_on_line(raw_pn, plain_line)
        if cand and len(cand.split()) >= 2 and (not subj_clean or cand.lower() != subj_clean.lower()):
            tier_2_names.append(cand)

    # 2e. Single-word Proper Nouns that are NOT sentence-initial ordinary words (or that appear mid-sentence)
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
        if w.lower() == "constitution":
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
        r"^(?:A|An|The)?\s*([A-Za-z][A-Za-z0-9’'\-–]*(?:\s+[A-Za-z][A-Za-z0-9’'\-–]*){0,2}?)\s+(?:is\s+defined\s+as|states\s+that|refers\s+to|is\s+the\s+supreme\s+law|is\s+the\s+process\s+of|is\s+a\s+substance|is\s+a\s+measure|is\s+anything|generally\s+has|has\s+a\s+fixed|spreads\s+out|consists\s+of|can\s+be\s+reversed|produces\s+one|alters\s+the\s+rate|separates\s+an\s+insoluble|recovers\s+a\s+dissolved|separates\s+liquid|uses\s+different|turns\s+blue|turns\s+red)\b",
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

    # 5e. Scientific/civics key terms inside definition bullets
    for m_sci in re.finditer(
        r"\b(resultant\s+force|collision\s+theory|gas\s+syringe|steam\s+engine|mixed\s+number|final\s+velocity|initial\s+velocity|boiling\s+point|melting\s+point|pH\s+scale|chemical\s+symbol|chemical\s+formula|word\s+equation|balanced\s+equation|physical\s+change|chemical\s+change|saturated\s+solution|fractional\s+distillation|paper\s+chromatography|universal\s+indicator|litmus\s+paper|Union\s+government|state\s+governments|legislature|executive|judiciary|neutralisation|neutralization|condensation|evaporation|distillation|filtration|sublimation|solubility|acceleration|reactants|products|subscripts|coefficients|catalyst|solution|solvent|solute|molecules|particles|elements|compounds|mixtures|solid|liquid|gas|matter|mass|volume|acids|bases|alkalis)\b",
        plain_line,
        re.IGNORECASE,
    ):
        cand = m_sci.group(1)
        if not subj_clean or cand.lower() != subj_clean.lower():
            tier_5_terms.append(cand)

    # --- Tier 6: Formula symbol or result inside a sentence (e.g. "F = ma" or "v = u + at") ---
    for m_inline_f in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9₀-₉]{0,8})\s*=\s*([A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹×÷\*+\-/^()]+(?:\s*[×÷\*+\-/]\s*[A-Za-z0-9₀-₉⁰¹²³⁴⁵⁶⁷⁸⁹^()]+)+)",
        plain_line,
    ):
        rhs_f = m_inline_f.group(2).strip().rstrip(".,;)")
        if rhs_f and len(rhs_f.split()) <= 3:
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


def write_key_fact_card(line: str, subject: str = "") -> dict[str, Any] | None:
    """Deterministic Key Facts fill-in-the-blank card writer (Step 3 of Prompt 3).

    For each sheet line:
    a) collects candidate answers in the 6-tier preference order
       (bold > proper_name > date_or_year > number_with_unit > technical_term > formula_part);
    b) takes the first candidate that passes is_good_answer(cand, line, line);
    c) expands a cut-off candidate to the whole phrase if the full phrase is on the same line;
    d) if no candidate passes, makes NO card for that line.
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

    # Special case: Bold words printed as one list (one shared card)
    bold_spans = [
        expand_or_clean_answer_on_line(m.group(1) or m.group(2) or m.group(3), plain_line)
        for m in _BOLD_SPAN_RE.finditer(cleaned_with_bold)
        if (m.group(1) or m.group(2) or m.group(3))
    ]
    valid_bold_list = [
        b for b in bold_spans if b and is_good_answer(b, source_line=cleaned_with_bold, sheet=plain_line)[0]
    ]
    if len(valid_bold_list) >= 2:
        masked = cleaned_with_bold
        for item in valid_bold_list:
            masked = re.sub(
                r"(?:\*\*|__|<b>)\s*" + re.escape(item) + r"\s*(?:\*\*|__|</b>)",
                "______",
                masked,
                count=1,
                flags=re.IGNORECASE,
            )
        masked = _normalize_spaces(_strip_bold_markup(masked))
        if has_specific_subj and subj_clean.lower() not in masked.lower():
            masked = f"{subj_clean}: {masked}"
        if not masked.endswith((".", "?", "______")):
            masked = masked + "."
        shared_ans = ", ".join(valid_bold_list)
        bold_card = {
            "front": masked,
            "prompt": "Fill in the key terms",
            "clue": masked,
            "question": masked,
            "answer": shared_ans,
            "source_line": raw_line,
            "subject": subj_clean,
            "is_bold_list": True,
        }
        if score_card(bold_card, plain_line)["accepted"]:
            return bold_card

    # Check if this is a standalone formula line
    formula_candidate = re.split(r",\s*where\b|\s*\(where\b", plain_line, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    m_formula = _FORMULA_LINE_RE.match(formula_candidate)

    tier_prompts = {
        "formula_part": "Complete the formula",
        "date_or_year": "Name the date or year",
        "number_with_unit": "Give the value and unit",
        "proper_name": "Name the person, place, or institution",
        "bold": "Fill in the key fact",
        "technical_term": "Fill in the key term",
    }

    # Collect candidates in the 6-tier preference order and pick the first that passes score_card
    candidates = collect_answer_candidates(credit_stripped, subject=subj_clean)
    for tier_name, raw_cand in candidates:
        cand = expand_or_clean_answer_on_line(raw_cand, plain_line)
        ok, _ = is_good_answer(cand, source_line=cleaned_with_bold, sheet=plain_line)
        if not ok:
            continue

        if tier_name == "formula_part" and m_formula:
            prefix_label = (m_formula.group(1) or "").strip()
            lhs_sym = m_formula.group(2).strip()
            clue = f"{prefix_label}: {lhs_sym} = ______" if prefix_label else f"{lhs_sym} = ______"
            card_subj = prefix_label or subj_clean or lhs_sym
        else:
            clue = _make_fill_in_blank_sentence(
                cleaned_with_bold,
                cand,
                subject=subj_clean,
                has_specific_subj=has_specific_subj,
            )
            card_subj = subj_clean or cand

        cand_card = {
            "front": clue,
            "prompt": tier_prompts.get(tier_name, "Fill in the key fact"),
            "clue": clue,
            "question": clue,
            "answer": cand,
            "source_line": raw_line,
            "subject": card_subj,
            "answer_tier": tier_name,
        }
        if score_card(cand_card, plain_line)["accepted"]:
            return cand_card

    return None


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
    `.fact_lines`, `.removed`, `.removed_lines`, and `.sheet_has_explicit_marks`.
    """

    def __new__(
        cls,
        kept_lines: list[dict[str, Any]],
        removed_lines: list[dict[str, Any]],
        sheet_has_explicit_marks: bool = False,
    ) -> "CleanLinesResult":
        instance = super().__new__(cls, (kept_lines, removed_lines))
        instance.kept = kept_lines
        instance.kept_lines = kept_lines
        instance.fact_lines = kept_lines
        instance.removed = removed_lines
        instance.removed_lines = removed_lines
        instance.sheet_has_explicit_marks = sheet_has_explicit_marks
        return instance


def _iter_sheet_lines_with_pages(sheet: Any) -> list[tuple[int, str]]:
    """Extract `(page_number, raw_line)` pairs from a sheet string, list, dict, or PDFExtractionResult."""
    if hasattr(sheet, "pages") and isinstance(getattr(sheet, "pages"), list):
        out: list[tuple[int, str]] = []
        for idx, page in enumerate(sheet.pages, start=1):
            pno = int(getattr(page, "page_number", idx) or idx)
            raw = str(getattr(page, "raw_text", "") or getattr(page, "text", "") or "")
            if raw.strip():
                for ln in raw.splitlines():
                    if ln.strip():
                        out.append((pno, ln.strip()))
            elif hasattr(page, "lines") and isinstance(page.lines, list):
                for ln in page.lines:
                    txt = getattr(ln, "text", ln)
                    if str(txt).strip():
                        out.append((pno, str(txt).strip()))
        if out:
            return out

    if isinstance(sheet, dict) and isinstance(sheet.get("pages"), list):
        out = []
        for idx, page in enumerate(sheet["pages"], start=1):
            if isinstance(page, dict):
                pno = int(page.get("page_number", idx) or idx)
                raw = str(page.get("raw_text") or page.get("text") or "")
                for ln in raw.splitlines():
                    if ln.strip():
                        out.append((pno, ln.strip()))
            elif isinstance(page, str):
                for ln in page.splitlines():
                    if ln.strip():
                        out.append((idx, ln.strip()))
        if out:
            return out

    sheet_text = _get_sheet_text(sheet)
    out = []
    current_page = 1
    for raw_ln in sheet_text.splitlines():
        ln = raw_ln.strip()
        if not ln:
            continue
        m_page = re.search(r"\bPage\s+(\d+)\b", ln, re.IGNORECASE)
        if m_page and _PAGE_HEADER_FOOTER_RE.search(ln):
            current_page = int(m_page.group(1))
        out.append((current_page, ln))
    return out


def clean_lines(sheet: Any) -> CleanLinesResult:
    """Input-side cleaner for Key Facts mode (Prompt 2).

    Removes the 6 non-fact categories before any card is written:
      1. `heading`: numbered titles, ALL-CAPS headings, short bold/title headings, bullet-joined header bars
         (while remembering the nearest entity heading as `subject` / `nearest_subject_heading`).
      2. `page_furniture`: page numbers, running headers/footers, "Page 1 …" lines, "FULL CARD", "RBS HQ"-style tags.
      3. `source_credit`: parenthetical credits like "(Britannica)", "(Wikipedia)", "(History of the INC)",
         URLs, and "Source(s): …" lines. Inline credits are stripped while keeping the rest of the fact sentence.
      4. `practice_section`: everything under "Practice Questions" / "Answer Key" / "Exercises" headings,
         plus any line containing "Q1."/"Q2." or "— Ans:"/"Ans:" or question prompts.
      5. `memory_tip`: lines starting with "Memory Tip", "Study Tip", "Remember", or "Tip:".
      6. `table`: table sections, pipe/tab-delimited table rows, and multi-column table lines.

    Returns `CleanLinesResult(kept_lines, removed_lines)`.
    """
    page_lines = _iter_sheet_lines_with_pages(sheet)

    kept_lines: list[dict[str, Any]] = []
    removed_lines: list[dict[str, Any]] = []
    current_subject = ""
    in_practice_section = False
    practice_is_end_matter = False
    in_table_section = False

    for page_num, ln in page_lines:
        # Check for inline parenthetical source/location credits first
        inline_matches = [m.group(0).strip() for m in _INLINE_SOURCE_CREDIT_RE.finditer(ln) if m.group(0).strip()]
        s = _normalize_spaces(_INLINE_SOURCE_CREDIT_RE.sub("", ln))
        if not s:
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "source_credit",
                    "reason": "line consisted solely of parenthetical source credit",
                }
            )
            continue

        # 6. Table section heading
        if _TABLE_SECTION_HEADING_RE.match(s):
            in_table_section = True
            current_subject = ""
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "table",
                    "reason": "table section heading",
                }
            )
            continue

        # 4. Practice / Answer Key / Exercises section heading
        if _PRACTICE_SECTION_HEADING_RE.match(s):
            in_practice_section = True
            if _END_MATTER_PRACTICE_HEADING_RE.match(s):
                practice_is_end_matter = True
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "practice_section",
                    "reason": "practice questions / answer key section heading",
                }
            )
            continue

        # 2. Page headers / footers / "Page 1 — ..." lines
        if _PAGE_HEADER_FOOTER_RE.search(s):
            if re.match(r"^Page\s+\d+\s*[—–\-:]", s, re.IGNORECASE):
                in_table_section = False
                if in_practice_section and not practice_is_end_matter:
                    in_practice_section = False
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "page_furniture",
                    "reason": "page header, footer, or page number label",
                }
            )
            continue

        # 1. Numbered section / topic heading that may exit a page-local practice/table block
        if not practice_is_end_matter and re.match(r"^\d+[.)]\s+[A-Z]", s):
            ent_subj = extract_entity_subject_from_heading(s)
            if ent_subj or (
                is_sheet_furniture_or_heading(s)
                and not _PRACTICE_OR_EXERCISE_LINE_RE.search(s)
                and "?" not in s
            ):
                in_practice_section = False
                in_table_section = False
                current_subject = ent_subj
                removed_lines.append(
                    {
                        "line": ln,
                        "page": page_num,
                        "type": "heading",
                        "reason": (
                            f"numbered heading (saved subject context {ent_subj!r})"
                            if ent_subj
                            else "numbered section heading"
                        ),
                    }
                )
                continue

        # Inside a table section or pipe/tab/multi-column table row -> Type 6 (`table`)
        if in_table_section or "|" in s or "\t" in s or len(re.findall(r"\s{3,}", ln)) >= 2:
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "table",
                    "reason": "table row or line inside table section",
                }
            )
            continue

        # 5. Memory tips and study tips -> Type 5 (`memory_tip`)
        if _MEMORY_OR_STUDY_TIP_RE.search(s):
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "memory_tip",
                    "reason": "memory tip or study tip line",
                }
            )
            continue

        # Inside a practice section or matching Q1./Ans:/Exercise/question patterns -> Type 4 (`practice_section`)
        if in_practice_section or _PRACTICE_OR_EXERCISE_LINE_RE.search(s) or "?" in s:
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "practice_section",
                    "reason": "practice question, answer-key line, or exercise prompt",
                }
            )
            continue

        # 3. Standalone source credit / URL line -> Type 3 (`source_credit`)
        if _SOURCE_OR_URL_LINE_RE.search(s):
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "source_credit",
                    "reason": "source credit list or URL line",
                }
            )
            continue

        # 2. Picture / diagram placeholder or page furniture tag ("FULL CARD", "RBS HQ", worksheet blank header) -> Type 2 (`page_furniture`)
        if _PICTURE_LINE_RE.search(s) or any(pat.search(s) for pat in _FURNITURE_PATTERNS):
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "page_furniture",
                    "reason": "page furniture, card tag, or diagram label",
                }
            )
            continue

        # 1. Headings, section titles, ALL-CAPS banners, "•"-joined header bars, and meta section labels -> Type 1 (`heading`)
        if _META_SECTION_LABEL_RE.match(s) or is_sheet_furniture_or_heading(s):
            ent_subj = extract_entity_subject_from_heading(s)
            if ent_subj:
                current_subject = ent_subj
            removed_lines.append(
                {
                    "line": ln,
                    "page": page_num,
                    "type": "heading",
                    "reason": (
                        f"heading/title (saved subject context {ent_subj!r})"
                        if ent_subj
                        else "heading or section label"
                    ),
                }
            )
            continue

        # If inline parenthetical credits (e.g., "(Britannica)") were stripped from this kept fact sentence,
        # record each stripped credit in `removed_lines` under type="source_credit" while keeping the sentence.
        for cred in inline_matches:
            removed_lines.append(
                {
                    "line": cred,
                    "source_line": ln,
                    "kept_text": s,
                    "page": page_num,
                    "type": "source_credit",
                    "reason": f"inline source credit {cred!r} removed while keeping fact sentence",
                }
            )

        bold_spans = [
            (m.group(1) or m.group(2) or m.group(3)).strip()
            for m in _BOLD_SPAN_RE.finditer(s)
            if (m.group(1) or m.group(2) or m.group(3))
        ]
        marked = is_marked_for_key_facts(s)
        kept_lines.append(
            {
                "text": s,
                "line": s,
                "raw_line": ln,
                "page": page_num,
                "subject": current_subject,
                "nearest_subject_heading": current_subject,
                "bold": bold_spans,
                "has_bold": bool(bold_spans),
                "is_marked": marked,
                "credits_removed": inline_matches,
            }
        )

    sheet_has_explicit_marks = any(item["is_marked"] for item in kept_lines)
    return CleanLinesResult(kept_lines, removed_lines, sheet_has_explicit_marks=sheet_has_explicit_marks)


def preprocess_sheet_lines(sheet: Any) -> tuple[list[tuple[str, str, bool]], bool]:
    """Input-side filter before any card is written (delegates to `clean_lines(sheet)`)."""
    cleaned = clean_lines(sheet)
    scanned_items = [
        (item["text"], item["subject"], item["is_marked"])
        for item in cleaned.kept_lines
    ]
    return scanned_items, cleaned.sheet_has_explicit_marks


def plan_key_facts_cards(
    sheet: Any,
    *,
    min_criterion_score: int = DEFAULT_MIN_CRITERION_SCORE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Generate Key Facts cards from a sheet using `clean_lines(sheet)` (leaving Detective, Superhero, and Study modes untouched)."""
    cleaned = clean_lines(sheet)
    sheet_has_explicit_marks = cleaned.sheet_has_explicit_marks

    accepted_cards: list[dict[str, Any]] = []
    dropped_report: list[dict[str, Any]] = []
    seen_facts: set[tuple[str, str]] = set()

    for item in cleaned.kept_lines:
        ln = item["text"]
        subj = item["subject"]
        is_marked = item["is_marked"]
        if sheet_has_explicit_marks and not is_marked:
            continue

        card = write_key_fact_card(ln, subject=subj)
        if card is None:
            dropped_report.append(
                {
                    "clue": "",
                    "answer": "",
                    "source_line": ln,
                    "scores": {},
                    "average": 0.0,
                    "reasons": [f"no_card: {explain_no_card_reason(ln, subject=subj)}"],
                }
            )
            continue

        if not sheet_has_explicit_marks:
            card["note"] = UNMARKED_SHEET_NOTE

        fact_key = (
            _normalize_spaces(card.get("subject", "")).lower(),
            _normalize_spaces(card.get("answer", "")).lower(),
        )
        if fact_key in seen_facts:
            dropped_report.append(
                {
                    "clue": _extract_clue(card),
                    "answer": _extract_answer(card),
                    "source_line": _extract_evidence(card),
                    "scores": {"distinct": 1},
                    "average": 1.0,
                    "reasons": [f"distinct: duplicate fact {fact_key[1]!r} already tested in reading order"],
                }
            )
            continue

        scores, reasons = score_card(card, sheet, prior_cards=accepted_cards)
        if is_card_acceptable(
            scores,
            min_criterion_score=min_criterion_score,
            min_average_score=min_average_score,
        ):
            accepted_cards.append(card)
            seen_facts.add(fact_key)
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

    return accepted_cards, dropped_report


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
