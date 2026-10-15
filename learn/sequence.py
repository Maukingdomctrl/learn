"""Student-facing reading order.

The renderer prints each stage in exactly this order, so timing (printed words) and the
Section 5.3 reading limits are computed from the same sequence the child sees.
Table contents are excluded: they are counted as visuals (Section 6.2).
"""

from dataclasses import dataclass

from .config import RECALL_BANNER
from .models import Item, Stage


@dataclass
class Chunk:
    kind: str  # "text" | "instruction" | "mark"
    text: str = ""
    item_number: int = 0


def item_chunks(item: Item) -> list[Chunk]:
    out = [Chunk("text", item.prompt)]
    for opt in item.options:
        out.append(Chunk("text", opt))
    if item.peer_work:
        out.append(Chunk("text", item.peer_work.intro))
        out.extend(Chunk("text", s) for s in item.peer_work.steps)
    if item.sentence_stem:
        out.append(Chunk("text", item.sentence_stem))
    if item.keywords:
        out.append(Chunk("text", "Use: " + " ".join(item.keywords)))
    if item.sketch_criteria:
        out.append(Chunk("text", item.sketch_criteria))
    out.append(Chunk("mark", item_number=item.number))
    return out


def stage_sequence(stage: Stage) -> list[Chunk]:
    seq: list[Chunk] = []
    if stage.stage == "Discover":
        if stage.hook:
            seq.append(Chunk("text", stage.hook))
        seq.append(Chunk("instruction", stage.instruction))
        if stage.items:
            seq.extend(item_chunks(stage.items[0]))
        if stage.body_text:
            seq.append(Chunk("text", stage.body_text))
        seq.extend(Chunk("text", line) for line in stage.worked_example)
        for item in stage.items[1:]:
            seq.extend(item_chunks(item))
        return seq

    if stage.stage == "Recall":
        seq.append(Chunk("text", RECALL_BANNER))
    seq.append(Chunk("instruction", stage.instruction))
    if stage.body_text:
        seq.append(Chunk("text", stage.body_text))
    if stage.options:
        seq.append(Chunk("text", " ".join(stage.options)))
    if stage.word_bank:
        seq.append(Chunk("text", " ".join(stage.word_bank)))
    if stage.groups:
        seq.append(Chunk("text", " ".join(stage.groups)))
    if stage.example:
        seq.append(Chunk("text", stage.example.prompt))
        seq.append(Chunk("text", stage.example.answer))
    for item in stage.items:
        seq.extend(item_chunks(item))
    if stage.hint_pointer:
        seq.append(Chunk("text", stage.hint_pointer))
    return seq
