"""Offline, source-grounded teaching scaffolds for extracted facts."""

import re
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


def _learning_prompts(fact: Fact) -> tuple[str, str, str, str]:
    quote = fact.statement
    number = next((mention.text for mention in fact.mentions if mention.kind in {"date", "number"}), None)
    term = next((mention.text for mention in fact.mentions if mention.kind == "difficult_term"), None)
    relation = max(
        (mention.text for mention in fact.mentions if mention.kind == "relationship_cue"), key=len, default=None
    )
    if number:
        explanation = (
            f"Find {number} in the source. Put it beside the event or amount it belongs to, then explain what the "
            "number tells you. Do not memorize it without its meaning."
        )
        visual = f"Draw a small timeline or quantity picture for {quote} and label it with the source's exact words."
        link = "What event or amount does this number belong to? Point to the words that tell you."
        check = f"With the source covered, explain what {number} tells you; uncover it and check the event or amount."
    elif term:
        explanation = (
            f"Read how the source explains {term}. Say the meaning without using the term, then explain which words "
            "in the source support your meaning."
        )
        visual = f"Draw one example of {term} using only the source's meaning; label the parts with source words."
        link = f"Can you think of another example of {term}? Ask an adult to check it against the source."
        check = f"Explain {term} in your own words, then compare your meaning with the source."
    elif relation:
        if relation.casefold() in {"is", "are", "was", "were"}:
            expanded = re.search(
                rf"\b{re.escape(relation)}\s+(?:in|on|at|near|from|to|through|into|part of)\b",
                quote,
                re.I,
            )
            if expanded:
                relation = expanded.group()
        left, right = quote.split(relation, 1)
        explanation = (
            f"The source links {left.strip()} with {right.strip().rstrip('.!?')} using “{relation}”. Draw both sides "
            "and join them with an arrow labelled with that exact link. Explain what the arrow means."
        )
        visual = f"Make a labelled relationship sketch for: {quote}"
        link = "What other example do you know of this kind of link? Keep it separate from what the source states."
        check = f"Explain the link “{relation}” without looking, then check that both sides match the source."
    else:
        explanation = (
            f"Read the source once. Find who or what acts, and the action or change the sentence describes. Draw the "
            "action with arrows; explain what happens using the source words. Only give a cause if the source states it."
        )
        visual = f"Draw the action or change in this source idea and label it: {quote}"
        link = "What familiar example helps you picture this? Mark it as your example, not as a fact from the source."
        check = "Explain the idea with your drawing, then check each label against the source."
    return explanation, visual, link, check


def _make_fact_lesson(fact: Fact) -> FactTeaching:
    quote = fact.statement
    explanation, visual, child_link, final_check = _learning_prompts(fact)
    return FactTeaching(
        fact_id=fact.id,
        source_statement=quote,
        source_unit_id=fact.source_unit_id,
        source_page=fact.page,
        kind=_kind(fact),
        child_explanation=explanation,
        memory_link=(
            "Memory scaffold, not a fact: use the labelled drawing to remember the relationship or change. "
            "Check every label against the source."
        ),
        visual_brief=visual,
        child_makes_a_link=child_link,
        recall_rounds=[
            RecallRound(
                support="full",
                mode="look_and_tell",
                prompt=f"Read the source: {quote} Use the drawing to explain the idea and point to its supporting words.",
            ),
            RecallRound(
                support="light",
                mode="draw_from_memory",
                prompt="Use your sketch as a cue to explain the link or change. Then compare every label with the source.",
            ),
            RecallRound(
                support="none",
                mode="teach_a_friend",
                prompt=final_check,
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
