"""Parameters from methodology Section 10 (provisional) plus runtime settings.

Every number here is a starting value from CORE_TEACHING_METHODOLOGY_FINAL.md.
None has been calibrated with children.
"""

import os

STAGES = ("Discover", "Reinforce", "Vary", "Apply", "Recall")

# Section 6 timing model
READING_WPM = 110
WRITING_WPM = 17
ORIENTATION_S = 60
VISUAL_S = 30
SKETCH_S = 20
ITEM_WEIGHTS_S = {"Discover": 15, "Reinforce": 25, "Vary": 35, "Apply": 55, "Recall": 45}
T_MIN_S = 780
T_MAX_S = 990
T_TARGET_S = 900
RULE_S_FLOOR_S = 600
BLOCK_CAP_S = {"Discover": 210, "Reinforce": 210, "Vary": 210, "Apply": 270, "Recall": 210}
MAX_WRITTEN_WORDS = 65

# Section 4.1 item limits
STAGE_ITEM_RANGES = {"Discover": (1, 2), "Reinforce": (2, 4), "Vary": (2, 3), "Apply": (1, 2), "Recall": (1, 2)}
TOTAL_ITEM_RANGE = (7, 13)

# Section 5.3 text limits
MAX_INSTRUCTION_WORDS = 22
MAX_ACTIONS_PER_INSTRUCTION = 2
MAX_SENTENCE_WORDS = 25
MAX_WORDS_BEFORE_FIRST_MARK = 65
MAX_READING_RUN_WORDS = 120

# Section 7.2 layout
PAGE_W_MM = 297
PAGE_H_MM = 210
MARGIN_MM = 12
MIN_FONT_PT = 10.5
MIN_LINE_MM = 7.5
WORDS_PER_LINE = 8
MIN_LINE_LEN_MM = 80
MIN_NUM_BLANK_MM = 25
MIN_SOLVE_MM = 35

# Section 8.3
MAX_REPAIR_ROUNDS = 2

# Teaching plan (generation step before the lesson): 2-3 incremental learning steps.
PLAN_STEP_RANGE = (2, 3)
# Visual types a plan may name. PR A renders only "table"; the others are planned visual-engine types.
VISUAL_TYPES = ("shape", "number_line", "bar_model", "flow_sequence", "table", "none")
# Source units on the same page either side of each selected unit that generation also sees.
CONTEXT_NEIGHBORS = 1

# Model tasks that write lesson content use LEARN_EFFORT; analysis and review tasks use LEARN_CHECK_EFFORT.
WRITING_TASKS = {"plan_lesson", "generate_lesson", "repair_lesson"}

# Section 5.1: activity types allowed per stage
ALLOWED_STAGES = {
    "ANNOTATE": {"Discover", "Reinforce", "Vary"},
    "CHOOSE": {"Discover", "Reinforce", "Vary"},
    "MATCH": {"Reinforce", "Vary"},
    "FILL_IN": {"Reinforce", "Vary", "Apply"},
    "SORT": {"Reinforce", "Vary"},
    "COMPLETE_STEPS": {"Discover", "Reinforce", "Apply"},
    "SPOT_MISTAKE": {"Vary", "Apply"},
    "SOLVE": {"Apply", "Recall"},
    "SHORT_ANSWER": {"Apply", "Recall"},
    "SKETCH": {"Apply", "Recall"},
}
EXAMPLE_REQUIRED = {"MATCH", "FILL_IN", "SORT", "COMPLETE_STEPS"}
# Types whose answers are marks or letters only (no handwriting time, Section 6.2)
MARK_ONLY_TYPES = {"ANNOTATE", "CHOOSE", "MATCH", "SORT"}

RECALL_BANNER = "Turn Page 1 face down before you start this box."


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip() or default


def model_name() -> str:
    return env("LEARN_MODEL", "claude-opus-5-5")


def model_effort() -> str:
    return env("LEARN_EFFORT", "high")


def check_effort() -> str:
    return env("LEARN_CHECK_EFFORT", "medium")


def _int_env(name: str, default: int) -> int:
    try:
        value = int(env(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


def max_output_tokens() -> int:
    """Output budget for a model response, thinking included (thinking counts toward max_tokens)."""
    return _int_env("LEARN_MAX_TOKENS", 32000)


def retry_output_tokens() -> int:
    """Budget for the single retry of a response cut off at max_tokens. Clamped to the model's own limit."""
    return _int_env("LEARN_MAX_TOKENS_RETRY", 64000)


def provider() -> str:
    """Where the card writer's model is called: anthropic (the Claude API) or june (June's Anthropic-format API)."""
    return env("LEARN_PROVIDER", "anthropic").lower()


def june_base_url() -> str:
    return env("JUNE_BASE_URL", "https://api.blockchain.info/ai/api")


def cards_model() -> str:
    """The model that chooses cards. Through June the test default is Gemini 3.8 Flash; June names models with a
    provider prefix and dots."""
    default = "google/gemini-3.8-flash" if provider() == "june" else "claude-haiku-5-5"
    return env("LEARN_CARDS_MODEL", default)


def cards_effort() -> str:
    """Thinking effort for choosing cards: medium for Gemini 3.8 Flash, low for Haiku (from the first live tests)."""
    return env("LEARN_CARDS_EFFORT", "medium" if "gemini" in cards_model() else "low")


def evidence_effort() -> str:
    """Thinking effort for writing Evidence cards. Low turns Gemini's thinking off: in the first live test it wrote
    cards as good as at medium for about a tenth of the output tokens."""
    return env("LEARN_EVIDENCE_EFFORT", "low")


def cards_max_tokens() -> int:
    """Output budget for one card sheet, thinking included; a cut-off response is retried once at twice this."""
    return _int_env("LEARN_CARDS_MAX_TOKENS", 8000)


def cards_sheet_limit() -> int:
    """How many card sheets per run the model is asked about; the rest keep rule-based cards. Keeps tests cheap."""
    return _int_env("LEARN_CARDS_AI_SHEETS", 1)


def ocr_backend() -> str:
    """auto | tesseract | claude | off"""
    return env("LEARN_OCR", "auto").lower()


def output_dir() -> str:
    return env("LEARN_OUTPUT_DIR", "output")


def load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines from a local .env file without overriding variables already set."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and value and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass


def detective_ai_sheets() -> int:
    """On the website, how many sheets of Detective cards the model writes per upload; the rest are plain cards.
    Each sheet is one or two model calls, and the page waits at most two minutes for the PDF."""
    return _int_env("LEARN_DETECTIVE_AI_SHEETS", 3)


def detective_daily_limit() -> int:
    """On the website, how many uploads a day may use the model for Detective cards. After that, and whenever no key
    is set, the Detective button makes the rule-based case file. Counted in memory, so a restart resets it."""
    return _int_env("LEARN_DETECTIVE_DAILY_LIMIT", 20)
