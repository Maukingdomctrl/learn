import json

import pymupdf
import pytest

from learn.extraction import SourceUnit
from learn.teaching_engine import create_teaching_lesson, extract_facts
from learn.teaching_engine.__main__ import main


def test_preserves_each_sentence_and_links_exact_page_and_span():
    source = SourceUnit("SRC-P3-U2", 3, "London is the capital of the UK. It is on the River Thames.", "text")

    inventory = extract_facts([source])

    assert [fact.statement for fact in inventory.facts] == [
        "London is the capital of the UK.",
        "It is on the River Thames.",
    ]
    for fact in inventory.facts:
        assert source.text[fact.start : fact.end] == fact.statement
        assert fact.source_unit_id == source.id
        assert fact.page == 3
    assert inventory.source_text == ((source.id, source.text),)


def test_identifies_places_entities_dates_numbers_terms_and_relationships():
    source = SourceUnit(
        "SRC-P2-U1",
        2,
        "Birmingham is in England. The Industrial Revolution began in the 18th century, 1760. "
        "A watershed means an area that drains into one river.",
        "text",
    )

    inventory = extract_facts([source])
    mentions = [(mention.kind, mention.text) for fact in inventory.facts for mention in fact.mentions]

    assert ("entity", "Birmingham") in mentions
    assert ("place_candidate", "England") in mentions
    assert ("entity", "Industrial Revolution") in mentions
    assert ("number", "18th") in mentions
    assert ("number", "1760") in mentions
    assert ("date", "1760") in mentions
    assert ("difficult_term", "watershed") in mentions
    assert any(kind == "relationship_cue" for kind, _ in mentions)


def test_flags_questionable_attribution_without_rewriting_source():
    sentence = "The industrial steam engine was invented in Birmingham."
    source = SourceUnit("SRC-P4-U1", 4, sentence, "text")

    fact = extract_facts([source]).facts[0]

    assert fact.statement == sentence
    assert fact.review_flags == ("verify_attribution_or_absolute_claim",)


def test_flags_corrupted_extracted_characters_without_rewriting_source():
    sentence = "QUICK COMPARISON � Lok Sabha has a five-year term."
    fact = extract_facts([SourceUnit("SRC-P1-U1", 1, sentence, "text")]).facts[0]

    assert fact.statement == sentence
    assert fact.review_flags == ("verify_extracted_text",)


def test_retains_every_source_unit_even_when_it_has_no_sentences():
    units = [SourceUnit("SRC-P1-U1", 1, "Heading", "text"), SourceUnit("SRC-P1-U2", 1, "   ", "text")]

    inventory = extract_facts(units)

    assert inventory.source_unit_ids == tuple(unit.id for unit in units)
    assert inventory.source_text == tuple((unit.id, unit.text) for unit in units)


def test_sentence_splitting_keeps_decimal_and_abbreviation_periods():
    source = SourceUnit("SRC-P1-U1", 1, "The value is 3.5 cm. E.g. this example is short.", "text")

    inventory = extract_facts([source])

    assert [fact.statement for fact in inventory.facts] == ["The value is 3.5 cm.", "E.g. this example is short."]


def test_list_markers_and_bullets_start_statements_without_becoming_statements():
    units = [
        SourceUnit(
            "SRC-P1-U1",
            1,
            "1. QUICK REVISION NOTES 1. LONDON – Capital of the United Kingdom & England "
            "• Situated on the River Thames in southeastern England.",
            "text",
        ),
        SourceUnit(
            "SRC-P1-U2",
            1,
            "ANSWER KEY A. Fill in the Blanks - Answers 1. River Thames 2. West Midlands 3. 1695 "
            "B. One Sentence Answers 1. Belfast is the capital city of Northern Ireland.",
            "text",
        ),
    ]

    inventory = extract_facts(units)
    statements = [fact.statement for fact in inventory.facts]

    assert statements == [
        "1. QUICK REVISION NOTES",
        "1. LONDON – Capital of the United Kingdom & England",
        "• Situated on the River Thames in southeastern England.",
        "ANSWER KEY",
        "A. Fill in the Blanks - Answers",
        "1. River Thames",
        "2. West Midlands",
        "3. 1695",
        "B. One Sentence Answers",
        "1. Belfast is the capital city of Northern Ireland.",
    ]
    for fact in inventory.facts:
        unit = next(unit for unit in units if unit.id == fact.source_unit_id)
        assert unit.text[fact.start : fact.end] == fact.statement


def test_initials_and_abbreviations_do_not_end_sentences_but_numbers_out_of_sequence_do():
    text = (
        "Dr. B. R. Ambedkar chaired the Drafting Committee. A. O. Hume was General Secretary. "
        "Capital of N. Ireland is Belfast. Asia's oldest exchange (est. 1875) is here. "
        "The answer is 8. The next one is 9. Vitamin C. It helps."
    )

    statements = [fact.statement for fact in extract_facts([SourceUnit("SRC-P1-U1", 1, text, "text")]).facts]

    assert statements == [
        "Dr. B. R. Ambedkar chaired the Drafting Committee.",
        "A. O. Hume was General Secretary.",
        "Capital of N. Ireland is Belfast.",
        "Asia's oldest exchange (est. 1875) is here.",
        "The answer is 8.",
        "The next one is 9.",
        "Vitamin C.",
        "It helps.",
    ]


def test_numbered_question_block_is_preserved_as_one_source_fact():
    text = "Question 7 ?Although plants produce carbon dioxide.? What does this tell you about the two processes?"
    facts = extract_facts([SourceUnit("SRC-P3-U1", 3, text, "text")]).facts

    assert [fact.statement for fact in facts] == [text]


def test_teaching_engine_is_offline_and_builds_supported_source_sequence():
    units = [
        SourceUnit("SRC-P1-U1", 1, "Birmingham is in England.", "text"),
        SourceUnit("SRC-P2-U1", 2, "The industrial steam engine was invented in Birmingham.", "text"),
    ]
    inventory = extract_facts(units)
    eligible = [fact for fact in inventory.facts if not fact.review_flags]
    lesson = create_teaching_lesson(inventory)

    assert lesson.fact_ids() == [eligible[0].id]
    taught = lesson.topics[0].fact_lessons[0]
    assert taught.source_statement == eligible[0].statement
    assert taught.source_unit_id == eligible[0].source_unit_id
    assert taught.memory_link_is_scaffold is True
    assert [round_.support for round_ in taught.recall_rounds] == ["full", "light", "none"]
    assert [round_.mode for round_ in taught.recall_rounds] == ["look_and_tell", "draw_from_memory", "teach_a_friend"]
    assert lesson.held_for_review[0].source_statement == units[1].text


def test_teaching_engine_approval_can_release_a_flagged_fact():
    inventory = extract_facts([SourceUnit("SRC-P4-U1", 4, "The industrial steam engine was invented here.", "text")])
    fact = inventory.facts[0]

    lesson = create_teaching_lesson(inventory, approved_fact_ids={fact.id})

    assert lesson.fact_ids() == [fact.id]
    assert lesson.held_for_review == []


def test_teaching_engine_preserves_complete_fact_coverage_without_model():
    inventory = extract_facts([SourceUnit("SRC-P1-U1", 1, "London is in England. It is on the River Thames.", "text")])

    lesson = create_teaching_lesson(inventory)

    assert lesson.fact_ids() == [fact.id for fact in inventory.facts]
    assert [topic.fact_lessons[0].source_statement for topic in lesson.topics] == [
        fact.statement for fact in inventory.facts
    ]


def test_pdf_command_writes_lesson_without_api_key(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    output = tmp_path / "lesson.json"

    assert main([sample_pdf, "--out", str(output)]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["lesson"]["topics"]


def test_pdf_command_rejects_a_learn_generated_pdf(tmp_path):
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "Generated cards")
    document.set_metadata({"title": "Learn ICSE Standard 8 Detective game", "author": "Learn Teaching Engine"})
    source = tmp_path / "generated.pdf"
    document.save(source)
    document.close()

    with pytest.raises(ValueError, match="already a Learn-generated PDF"):
        main([str(source), "--out", str(tmp_path / "lesson.json")])
