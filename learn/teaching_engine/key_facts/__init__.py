"""Rule-based Key Facts engine for turning study-sheet items into recall cards."""
from __future__ import annotations

from typing import Any

from .output import KeyFactCard, plan_key_facts, run_pipeline

__all__ = ["KeyFactCard", "plan_key_facts", "run"]


def run(reader_json: dict[str, Any]) -> dict[str, Any]:
    """Run the Key Facts engine on a reader JSON dictionary and return the JSON result."""
    return run_pipeline(reader_json)
