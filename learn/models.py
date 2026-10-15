"""Lesson data (methodology Section 9). The model produces this; code computes timing and source pages."""
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

StageName = Literal["Discover", "Reinforce", "Vary", "Apply", "Recall"]
ActivityType = Literal[
    "ANNOTATE", "CHOOSE", "MATCH", "FILL_IN", "SORT",
    "COMPLETE_STEPS", "SPOT_MISTAKE", "SOLVE", "SHORT_ANSWER", "SKETCH",
]


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class Table(_Base):
    caption: str = ""
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    source_unit_ids: list[str] = Field(default_factory=list)


class Example(_Base):
    """Done-for-you example ("Ex"). Never scored."""
    prompt: str
    answer: str


class PeerWork(_Base):
    intro: str
    steps: list[str]
    mistake_step: int  # 1-based index of the single wrong step


class Item(_Base):
    number: int
    prompt: str
    options: list[str] = Field(default_factory=list)  # CHOOSE options or ANNOTATE targets
    unit: Optional[str] = None
    sentence_stem: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)
    peer_work: Optional[PeerWork] = None
    sketch_criteria: Optional[str] = None


class Stage(_Base):
    stage: StageName
    activity_type: ActivityType
    instruction: str
    hook: str = ""  # Discover only
    body_text: str = ""  # Discover: the explanation
    worked_example: list[str] = Field(default_factory=list)  # Discover only, one line per step
    visuals: list[Table] = Field(default_factory=list)
    example: Optional[Example] = None
    hint_pointer: Optional[str] = None
    options: list[str] = Field(default_factory=list)  # MATCH column B (excluding the Ex answer)
    word_bank: list[str] = Field(default_factory=list)  # FILL_IN
    groups: list[str] = Field(default_factory=list)  # SORT
    items: list[Item]


class Concept(_Base):
    name: str
    source_unit_ids: list[str] = Field(default_factory=list)


class Claim(_Base):
    text: str
    source_unit_ids: list[str] = Field(default_factory=list)
    is_analogy: bool = False


class Term(_Base):
    term: str
    definition: str
    source_unit_ids: list[str] = Field(default_factory=list)


class KeyEntry(_Base):
    item_number: int
    answer: str
    accepted_alternatives: list[str] = Field(default_factory=list)
    reason: str
    calculation: Optional[str] = None  # arithmetic expression for numeric answers, re-evaluated by code (D7)
    source_unit_ids: list[str] = Field(default_factory=list)


class AnswerKey(_Base):
    entries: list[KeyEntry]
    scope_covered: str
    not_covered: str = ""
    source_issues: list[str] = Field(default_factory=list)
    shortened_lesson_note: Optional[str] = None


class Lesson(_Base):
    standard: Literal[7, 8]
    title: str
    scope_line: str
    concepts: list[Concept]
    core_claims: list[Claim]
    terms: list[Term] = Field(default_factory=list)
    stages: list[Stage]
    answer_key: AnswerKey

    def items(self) -> list[tuple[Stage, Item]]:
        return [(s, i) for s in self.stages for i in s.items]

    def stage(self, name: str) -> Optional[Stage]:
        return next((s for s in self.stages if s.stage == name), None)

    def key_for(self, number: int) -> Optional[KeyEntry]:
        return next((e for e in self.answer_key.entries if e.item_number == number), None)
