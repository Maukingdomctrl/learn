"""Input-side cleaner (`clean_lines`) for Key Facts mode (Prompt 2)."""

from __future__ import annotations

from learn.teaching_engine.card_quality import (
    CleanLinesResult,
    clean_lines,
    preprocess_sheet_lines,
)

__all__ = [
    "CleanLinesResult",
    "clean_lines",
    "preprocess_sheet_lines",
]
