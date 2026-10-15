"""Section 6 timing model, computed in code (never taken from the model). All values in seconds."""

from dataclasses import asdict, dataclass

from . import config as C
from .models import Lesson, Stage
from .sequence import stage_sequence
from .textutil import count_words, written_words


@dataclass
class StageTiming:
    stage: str
    printed_words: int
    t_read: float
    visuals: int
    t_visual: float
    items: int
    sketch_items: int
    t_items: float
    written_words: int
    t_write: float
    total: float
    cap: float


@dataclass
class LessonTiming:
    stages: list[StageTiming]
    t_stages: float
    t_lesson: float
    written_words: int

    @property
    def minutes(self) -> float:
        return self.t_lesson / 60

    def to_dict(self) -> dict:
        d = asdict(self)
        d["minutes"] = round(self.minutes, 2)
        return d


def item_written_words(lesson: Lesson, stage: Stage, item_number: int) -> int:
    """Handwriting words for one item, taken from the answer-key answer (Section 6.2)."""
    if stage.activity_type in C.MARK_ONLY_TYPES:
        return 0
    entry = lesson.key_for(item_number)
    return written_words(entry.answer) if entry else 0


def stage_timing(lesson: Lesson, stage: Stage) -> StageTiming:
    printed = sum(count_words(c.text) for c in stage_sequence(stage) if c.kind != "mark")
    t_read = printed / C.READING_WPM * 60
    visuals = len(stage.visuals)
    t_visual = visuals * C.VISUAL_S
    n_items = len(stage.items)
    sketches = n_items if stage.activity_type == "SKETCH" else 0
    t_items = n_items * C.ITEM_WEIGHTS_S[stage.stage] + sketches * C.SKETCH_S
    written = sum(item_written_words(lesson, stage, i.number) for i in stage.items)
    t_write = written / C.WRITING_WPM * 60
    return StageTiming(
        stage=stage.stage,
        printed_words=printed,
        t_read=t_read,
        visuals=visuals,
        t_visual=t_visual,
        items=n_items,
        sketch_items=sketches,
        t_items=t_items,
        written_words=written,
        t_write=t_write,
        total=t_read + t_visual + t_items + t_write,
        cap=C.BLOCK_CAP_S[stage.stage],
    )


def lesson_timing(lesson: Lesson) -> LessonTiming:
    stages = [stage_timing(lesson, s) for s in lesson.stages]
    t_stages = sum(s.total for s in stages)
    return LessonTiming(
        stages=stages,
        t_stages=t_stages,
        t_lesson=C.ORIENTATION_S + t_stages,
        written_words=sum(s.written_words for s in stages),
    )


def compute(printed_words: int, visuals: int, items: int, stage: str, written: int, sketches: int = 0) -> float:
    """Block time from raw counts; used to check the Section 6.5 worked example."""
    return (
        printed_words / C.READING_WPM * 60
        + visuals * C.VISUAL_S
        + items * C.ITEM_WEIGHTS_S[stage]
        + sketches * C.SKETCH_S
        + written / C.WRITING_WPM * 60
    )
