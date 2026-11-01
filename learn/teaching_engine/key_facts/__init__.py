"""Rule-based Key Facts engine for turning study-sheet items into recall cards."""
from __future__ import annotations

from typing import Any

from .output import KeyFactCard, plan_key_facts, plan_key_facts_with_notes, run_pipeline

__version__ = "0.6.0"
__all__ = ["KeyFactCard", "__version__", "plan_key_facts", "plan_key_facts_with_notes", "run"]


def run(reader_json: dict[str, Any]) -> dict[str, Any]:
    """Run the Key Facts engine on a reader JSON dictionary and return the JSON result."""
    return run_pipeline(reader_json)
