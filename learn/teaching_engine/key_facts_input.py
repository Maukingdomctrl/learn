"""Input-side cleaner (`clean_sheet` and `clean_lines`) for Key Facts mode (Prompt 2)."""

from __future__ import annotations

from learn.teaching_engine.card_quality import (
    CleanLinesResult,
    clean_lines,
    clean_sheet,
    is_name_with_dates_and_title_line,
    preprocess_sheet_lines,
)

__all__ = [
    "CleanLinesResult",
    "clean_lines",
    "clean_sheet",
    "is_name_with_dates_and_title_line",
    "preprocess_sheet_lines",
]

