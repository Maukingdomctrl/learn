"""Stage 1 source-faithful extraction for the teaching engine."""

from .facts import Fact, FactInventory, Mention, extract_facts
from .cards import extract_source_visuals, render_printable_cards_pdf
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
    "render_printable_cards_pdf",
    "render_teaching_pdf",
]
