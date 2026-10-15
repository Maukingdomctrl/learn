# Teaching Engine — Stage 1: Source Fact Inventory

Stage 1 converts the existing PDF extractor's `SourceUnit` records into a traceable inventory. It is a separate Python module at `learn/teaching_engine/`; it does not change lesson generation, card generation, the user interface, or print layout.

```python
from learn.extraction import extract
from learn.teaching_engine import extract_facts

source = extract("curriculum.pdf")
inventory = extract_facts(source.units)
data = inventory.to_dict()
```

Each fact is a sentence-sized, verbatim excerpt with a stable fact ID, source unit ID, one-based PDF page, and character offsets into that unit's extracted text. The inventory also retains the full text for every input unit, including headings or blank units that do not produce a sentence record. Mentions mark candidates for technical terms, entities, possible places, dates, numbers, and relationship cues. These labels are deterministic heuristics for review; they do not establish that a word is difficult or that a name is a place.

Attribution, priority, and absolute claims such as “invented,” “first,” “largest,” “only,” “always,” or “never” receive `verify_attribution_or_absolute_claim`. The extractor preserves the original wording and does not fact-check, correct, or add material. Review flags require a person to check the cited page against an appropriate reference before using the claim.

Sentence-sized excerpts provide an auditable inventory of extracted text, not a guarantee that each sentence expresses exactly one atomic fact or that OCR recovered the PDF correctly. Scanned-page OCR warnings from `learn.extraction` remain relevant. Check coverage and review the source pages before downstream teaching or card generation. The child-centred plan generator is documented in [`TEACHING_ENGINE.md`](TEACHING_ENGINE.md).

Run the focused tests with `pytest tests/test_teaching_engine.py tests/test_extraction.py`.
