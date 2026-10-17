"""The planning step: each sentence's job decides the question. Synthetic sentences; not evidence of lesson quality."""

from learn.teaching_engine.thinking import (
    aspect,
    comparisons,
    definition,
    display_name,
    is_section,
    labelled_list,
    reason,
    result,
    think,
)


def test_a_because_sentence_asks_why_and_answers_with_the_sheets_reason():
    thought = reason("Mills are near the fields because sugarcane dries quickly after cutting.")

    assert thought.question == "Why? Give the reason."
    assert thought.clue == "Mills are near the fields."
    assert thought.answer == "Sugarcane dries quickly after cutting."
    assert reason("Mills are near the fields and sugarcane dries quickly.") is None


def test_a_led_to_sentence_asks_what_it_led_to():
    thought = result("His efforts led to the Widow Remarriage Act of 1856.")

    assert thought.question == "What did this lead to?"
    assert thought.answer == "the Widow Remarriage Act of 1856."
    assert result("His efforts helped widows remarry.") is None


def test_only_the_topics_own_definition_becomes_what_is_it():
    thought = definition("Migration is the movement of people from one place to another.", "MIGRATION")

    assert thought.question == "What is Migration?"
    assert definition("It is located in New Delhi and is very old.", "SUPREME COURT") is None
    assert definition("Migration is the movement of people.", "URBANISATION") is None


def test_a_labelled_list_asks_for_its_count_and_a_phrase_is_not_split_into_items():
    thought = labelled_list("Push factors: lack of jobs, poverty and droughts in villages.", "MIGRATION")

    assert thought.question == "Name the three push factors of Migration."
    assert thought.answer.split("\n") == ["lack of jobs", "poverty", "droughts in villages"]
    assert labelled_list("Products: steel for machines, rails and bridges.", "STEEL") is None
    assert labelled_list("Term: 5 years, unless dissolved earlier.", "LOK SABHA") is None
    assert labelled_list("Renewable resources: solar energy and water.", "TYPES OF RESOURCES").question == (
        "Name the two renewable resources."
    )


def test_a_point_under_a_causes_heading_asks_for_that_kind_of_cause():
    thought = aspect("Economic: heavy land revenue pushed peasants into debt.", "CAUSES OF THE UPRISING")

    assert thought.question == "What was the economic cause of the uprising?"
    assert thought.answer == "Heavy land revenue pushed peasants into debt."
    assert aspect("Immediate cause: greased cartridges.", "CAUSES OF THE UPRISING").question == (
        "What was the immediate cause of the uprising?"
    )
    assert aspect("Economic: heavy land revenue.", "LOK SABHA") is None


def test_section_headings_are_not_things_to_identify():
    assert is_section("CAUSES OF THE UPRISING") and is_section("TYPES OF RESOURCES")
    assert not is_section("LOK SABHA") and not is_section("IRON AND STEEL INDUSTRY")
    assert display_name("IRON AND STEEL INDUSTRY") == "Iron and Steel Industry"
    assert display_name("RMS Titanic") == "RMS Titanic"


def test_a_label_printed_under_two_topics_becomes_one_comparison():
    found = comparisons(
        [
            ("LOK SABHA", "Presiding officer: the Speaker."),
            ("LOK SABHA", "Members are directly elected."),
            ("RAJYA SABHA", "Presiding officer: the Vice-President of India."),
            ("SUPREME COURT", "Judges: appointed by the President."),
        ]
    )

    assert [(c.label, c.values) for c in found] == [
        ("Presiding officer", (("LOK SABHA", "the Speaker"), ("RAJYA SABHA", "the Vice-President of India")))
    ]


def test_a_plain_fact_is_left_for_the_other_card_types():
    assert think("The Tata Iron and Steel Company was set up at Jamshedpur in 1907.", "IRON AND STEEL") is None


def test_a_glossary_sentence_shows_the_meaning_and_asks_for_the_term():
    from learn.teaching_engine.thinking import term_definition

    thought = term_definition("A watershed is higher land that separates neighbouring drainage basins.")

    assert thought.question == "What is it called?"
    assert thought.clue == "Higher land that separates neighbouring drainage basins."
    assert thought.answer == "watershed"
    assert term_definition("The river is long.") is None
    assert term_definition("Erosion is stronger on the outer bank of a bend.") is None


def test_tasks_the_sheet_sets_are_not_facts():
    from learn.teaching_engine.thinking import is_instruction

    assert is_instruction("Explain how a watershed can affect where rainwater travels.")
    assert is_instruction("Trace the sequence: source, tributary, mouth.")
    assert not is_instruction("Tributaries join a larger river.")


def test_headers_printed_on_every_page_are_dropped_but_numbered_questions_stay():
    from learn.teaching_engine.sheet import _Paragraph, _without_running_lines

    paragraphs = [
        _Paragraph("GEOGRAPHY | Rivers and drainage", 1, []),
        _Paragraph("Practice source | Page 1 of 2", 1, []),
        _Paragraph("Question 1", 1, []),
        _Paragraph("GEOGRAPHY | Rivers and drainage", 2, []),
        _Paragraph("Practice source | Page 2 of 2", 2, []),
        _Paragraph("Question 2", 2, []),
    ]

    assert [p.text for p in _without_running_lines(paragraphs)] == ["Question 1", "Question 2"]
