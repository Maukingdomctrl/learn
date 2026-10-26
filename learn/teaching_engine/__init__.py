"""Teaching engine package."""

from learn.teaching_engine.card_quality import (
    DEFAULT_MIN_AVERAGE_SCORE,
    DEFAULT_MIN_CRITERION_SCORE,
    MAX_ANSWER_CHARS,
    MAX_ANSWER_WORDS,
    filter_cards_after_plan,
    format_dropped_cards_report,
    is_card_acceptable,
    score_card,
)

__all__ = [
    "DEFAULT_MIN_AVERAGE_SCORE",
    "DEFAULT_MIN_CRITERION_SCORE",
    "MAX_ANSWER_CHARS",
    "MAX_ANSWER_WORDS",
    "filter_cards_after_plan",
    "format_dropped_cards_report",
    "is_card_acceptable",
    "score_card",
]
