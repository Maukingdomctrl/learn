from learn import timing
from learn.models import Lesson
from learn.textutil import count_words, written_words


def test_methodology_worked_example_6_5():
    """Reproduce the Section 6.5 worked example: 903.3 s = 15.06 min."""
    blocks = [
        ("Discover", 165, 1, 2, 0),
        ("Reinforce", 88, 0, 4, 0),
        ("Vary", 55, 0, 2, 8),
        ("Apply", 77, 1, 2, 16),
        ("Recall", 33, 0, 2, 20),
    ]
    totals = [timing.compute(w, v, i, s, wr) for s, w, v, i, wr in blocks]
    assert [round(t, 1) for t in totals] == [150.0, 148.0, 128.2, 238.5, 178.6]
    t_lesson = 60 + sum(totals)
    assert round(t_lesson, 1) == 903.3
    assert round(t_lesson / 60, 2) == 15.05  # 903.29 s; the methodology rounds the displayed values to 15.06


def test_word_counting_rules():
    assert count_words("Area = 1/2 × 8 × 5 = 20 cm²") == 3  # expression counts as one word
    assert count_words("The ____ meets the base.") == 4  # blanks are not words
    assert written_words("20") == 0 and written_words("B") == 0
    assert written_words("height") == 1
    assert written_words("The area is half of base times height.") == 8


def test_lesson_timing_counts_each_activity_once(lesson_data):
    lesson = Lesson.model_validate(lesson_data)
    t = timing.lesson_timing(lesson)
    by = {s.stage: s for s in t.stages}
    # mark-only CHOOSE answers add no handwriting time
    assert by["Discover"].written_words == 0
    # table words are not in reading time: one table = 30 s visual
    assert by["Discover"].visuals == 1 and by["Discover"].t_visual == 30
    assert abs(t.t_lesson - (60 + sum(s.total for s in t.stages))) < 1e-9
    assert 780 <= t.t_lesson <= 990


def test_sketch_time_counted_once(lesson_data):
    recall = lesson_data["stages"][4]
    recall["activity_type"] = "SKETCH"
    recall["items"][0]["sketch_criteria"] = "Draw 1 triangle and label its base and height."
    lesson = Lesson.model_validate(lesson_data)
    st = timing.stage_timing(lesson, lesson.stage("Recall"))
    assert st.sketch_items == 1
    assert st.t_items == 45 + 20
