"""Teaching engine package."""

from learn.teaching_engine.card_quality import (
    CRITERIA,
    DEFAULT_MIN_AVERAGE_SCORE,
    DEFAULT_MIN_CRITERION_SCORE,
    MAX_ANSWER_CHARS,
    MAX_ANSWER_WORDS,
    filter_cards_after_plan,
    format_dropped_cards_report,
    is_card_acceptable,
    is_sheet_furniture_or_heading,
    plan_key_facts_cards,
    score_card,
    write_key_fact_card,
)

__all__ = [
    "CRITERIA",
    "DEFAULT_MIN_AVERAGE_SCORE",
    "DEFAULT_MIN_CRITERION_SCORE",
    "MAX_ANSWER_CHARS",
    "MAX_ANSWER_WORDS",
    "filter_cards_after_plan",
    "format_dropped_cards_report",
    "is_card_acceptable",
    "is_sheet_furniture_or_heading",
    "plan_key_facts_cards",
    "score_card",
    "write_key_fact_card",
]
