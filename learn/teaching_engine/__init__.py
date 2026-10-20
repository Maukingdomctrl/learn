"""Stage 1 source-faithful extraction for the teaching engine."""

from .cards import extract_source_visuals, render_printable_cards_pdf
from .detective import render_printable_case_file_pdf
from .facts import Fact, FactInventory, Mention, extract_facts
from .lesson import TeachingEngineError, TeachingLesson, create_teaching_lesson
from .printable import render_teaching_pdf

__all__ = [
    "Fact",
    "FactInventory",
    "Mention",
    "TeachingEngineError",
    "TeachingLesson",
    "create_teaching_lesson",
    "extract_facts",
    "extract_source_visuals",
    "render_printable_case_file_pdf",
    "render_printable_cards_pdf",
    "render_teaching_pdf",
]
