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
