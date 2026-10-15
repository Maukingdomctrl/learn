"""Stage 1 source-faithful extraction for the teaching engine."""

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
    "render_teaching_pdf",
]
