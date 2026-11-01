"""
Learn Key Facts Engine — Stable JSON Interface
engine.run(reader_json) -> dict
"""
from __future__ import annotations
from typing import Dict, Any
from .output import run_pipeline


def run(reader_json: Dict[str, Any]) -> Dict[str, Any]:
    """Entry point for the Key Facts engine."""
    return run_pipeline(reader_json)
