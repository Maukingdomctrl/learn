"""Offline, source-grounded teaching scaffolds for extracted facts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .facts import Fact, FactInventory


class TeachingEngineError(ValueError):
    """Raised when a teaching lesson cannot preserve its source inventory."""


RecallMode = Literal["look_and_tell", "draw_from_memory", "teach_a_friend"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RecallRound(_StrictModel):
    support: Literal["full", "light", "none"]
    mode: RecallMode
    prompt: str


class FactTeaching(_StrictModel):
    fact_id: str
    source_statement: str
    source_unit_id: str
    source_page: int
    kind: str
    child_explanation: str
    memory_link: str
    memory_link_is_scaffold: Literal[True] = True
    visual_brief: str
    child_makes_a_link: str
    recall_rounds: list[RecallRound]


class TopicTeaching(_StrictModel):
    name: str
    child_entry: str
    visual_anchor: str
    fact_lessons: list[FactTeaching]


class HeldFact(_StrictModel):
    fact_id: str
    source_statement: str
    source_unit_id: str
    source_page: int
    review_flags: list[str]


class TeachingLesson(_StrictModel):
    title: str
    opening_hook: str
    topics: list[TopicTeaching]
    held_for_review: list[HeldFact]

    def fact_ids(self) -> list[str]:
        return [fact.fact_id for topic in self.topics for fact in topic.fact_lessons]


def _kind(fact: Fact) -> str:
    kinds = {mention.kind for mention in fact.mentions}
    if "date" in kinds or "number" in kinds:
        return "number_date"
    if "difficult_term" in kinds:
        return "definition"
    if "place_candidate" in kinds:
        return "place_or_relationship"
    if "entity" in kinds:
        return "person_place_or_institution"
    if "relationship_cue" in kinds:
        return "relationship"
    return "source_statement"


def _make_fact_lesson(fact: Fact) -> FactTeaching:
    quote = fact.statement
    return FactTeaching(
        fact_id=fact.id,
        source_statement=quote,
        source_unit_id=fact.source_unit_id,
        source_page=fact.page,
        kind=_kind(fact),
        child_explanation=(
            "Read the source idea together. In your own words, say what it tells you; keep the quoted source "
            "nearby so its meaning is not changed."
        ),
        memory_link=(
            "Memory scaffold, not a fact: picture the important words from this sentence as labels on a simple "
            "drawing. Choose a different picture if this one does not help."
        ),
        visual_brief=(
            "Draw a small, simple picture for this sentence. Use only names, numbers, and relationships stated "
            "in the source; label the drawing with the exact source words."
        ),
        child_makes_a_link="What picture, place, or personal connection would help you remember this source idea?",
        recall_rounds=[
            RecallRound(
                support="full",
                mode="look_and_tell",
                prompt=f"Look at the source: {quote} Point to the words that carry its main idea and tell it back.",
            ),
            RecallRound(
                support="light",
                mode="draw_from_memory",
                prompt="Use the key words as a cue. Sketch the idea, then compare your labels with the source.",
            ),
            RecallRound(
                support="none",
                mode="teach_a_friend",
                prompt=(
                    "With the source turned over, explain the idea in your own words. Then check it against the source."
                ),
            ),
        ],
    )


def create_teaching_lesson(
    inventory: FactInventory,
    approved_fact_ids: set[str] | None = None,
) -> TeachingLesson:
    """Build a deterministic lesson scaffold without network access or model credentials.

    Source claims are reproduced verbatim. Flagged claims remain in ``held_for_review`` unless explicitly
    approved. Explanations and memory activities are deliberately procedural: this offline engine does not
    invent missing curriculum knowledge or independently paraphrase claims.
    """
    approved = approved_fact_ids or set()
    held = [fact for fact in inventory.facts if fact.review_flags and fact.id not in approved]
    eligible = [fact for fact in inventory.facts if fact not in held]
    topics = [
        TopicTeaching(
            name=f"Source idea {number}",
            child_entry="Let’s explore one idea at a time. Read the source sentence, then make it your own.",
            visual_anchor="Use one clearly labelled drawing to hold this source idea in mind.",
            fact_lessons=[_make_fact_lesson(fact)],
        )
        for number, fact in enumerate(eligible, start=1)
    ]
    return TeachingLesson(
        title="A source-based lesson",
        opening_hook="Let’s turn the ideas in your source into things you can explain, picture, and remember.",
        topics=topics,
        held_for_review=[
            HeldFact(
                fact_id=fact.id,
                source_statement=fact.statement,
                source_unit_id=fact.source_unit_id,
                source_page=fact.page,
                review_flags=list(fact.review_flags),
            )
            for fact in held
        ],
    )
