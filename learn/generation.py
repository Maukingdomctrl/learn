"""Model prompts: concept selection (steps 3-4), lesson generation (step 5), repair (step 9).

The model writes lesson content only. Code computes timing, source pages, and every check.
"""

import json

from pydantic import ValidationError

from . import config as C
from .grounding import SourceIndex
from .llm import LLM, LLMError
from .models import Lesson


class GenerationError(Exception):
    pass


SYSTEM = (
    "You write printable paper-and-pencil lessons for Standard 7-8 students (ages 12-14) who are "
    "meeting a topic for the first time. You use ONLY facts, terms and methods found in the numbered source "
    "units you are given. You never add outside knowledge, even if it is correct. When the source is not "
    "enough, you say so instead of filling gaps. You reply with a single JSON object and nothing else."
)

SELECT_PROMPT = """Choose what one ~15-minute lesson should teach from this curriculum source.

Standard: {standard}
Parent's topic request: {topic}

Rules (methodology Section 3.2-3.4):
- If the parent named a topic, use it. Otherwise choose the FIRST teachable concept in document order.
- Teach 1 concept, or at most 3 closely related sub-concepts.
- Sufficiency test - the concept is teachable only if the source provides ALL of:
  (a) an explanation or definition (not just a mention, heading or review question);
  (b) enough information to write correct answers for at least 7 scored items without outside knowledge;
  (c) for a procedure, the steps of the method or a worked example from which the steps are clear.
- If no concept passes, set "status" to "insufficient" and explain in plain language what is missing and
  what the parent could upload instead. Report it when the explanation depends on missing/unreadable pages
  or figures, or the source contradicts itself.

Source units:
{units}

Reply with JSON:
{{
  "status": "ok" | "insufficient",
  "concept": "short name",
  "sub_concepts": ["..."],
  "is_procedure": true | false,
  "explanation_unit_ids": ["SRC-..."],
  "procedure_unit_ids": ["SRC-..."],
  "supporting_unit_ids": ["SRC-..."],
  "can_support_7_items": true | false,
  "not_covered": "what else is in the selected material but left for another lesson",
  "source_issues": ["apparent errors in the source, left out of the lesson"],
  "insufficiency_reason": "plain-language reason if insufficient, else empty",
  "parent_action": "what the parent can do if insufficient, else empty"
}}"""

LESSON_RULES = f"""LESSON RULES (follow exactly; code checks every rule):

Structure - exactly 5 stages in this order, scored items numbered 1,2,3... continuously across stages:
1 Discover (Page 1 left): hook (a question/puzzle from a situation a 12-14 year old recognises, answered by the
  lesson), instruction, item 1 (a simple first mark such as circling a prediction), then body_text (clear
  explanation), worked_example (one complete worked example or annotated model, one line per step), optional
  table visual, optional item 2. Items: 1-2. Types: ANNOTATE, CHOOSE, COMPLETE_STEPS.
2 Reinforce (Page 1 right): guided practice with high support. Items: 2-4. First item easy.
  Types: ANNOTATE, CHOOSE, MATCH, FILL_IN, SORT, COMPLETE_STEPS.
3 Vary (Page 2 top left): same idea in a different format (new values, reversed direction, new case, or a
  fictional peer's mistake). Not Reinforce with just new numbers. Items: 2-3. hint_pointer REQUIRED.
  Types: ANNOTATE, CHOOSE, MATCH, FILL_IN, SORT, SPOT_MISTAKE.
4 Apply (Page 2 top right): independent practice in a context not seen in Discover; no word bank.
  Items: 1-2. hint_pointer REQUIRED. Types: FILL_IN, COMPLETE_STEPS, SPOT_MISTAKE, SOLVE, SHORT_ANSWER, SKETCH.
5 Recall (Page 2 bottom right box): retrieve the main rule/definition/method from memory or a fresh short
  problem; must not be answerable by copying a sentence from Page 2. hint_pointer must be null.
  Items: 1-2. Types: SOLVE, SHORT_ANSWER, SKETCH.
Total scored items: {C.TOTAL_ITEM_RANGE[0]}-{C.TOTAL_ITEM_RANGE[1]}.
Use at least 3 different activity types; consecutive stages must use different types.

Activity types:
- ANNOTATE: child circles/ticks targets. item.options = targets (at least 3 when outside Discover).
  Answer = the target text to circle (several targets separated by "; ").
- CHOOSE: item.options = 3-4 options, exactly one correct; answer = the exact correct option text.
  No "all of the above" / "none of the above".
- MATCH: stage.options = column B (at least number of prompts + 1, excluding the Ex answer); each item prompt is
  a column A entry; answer = the exact option text. Max 4 items. stage.example REQUIRED (one pre-drawn pair).
- FILL_IN: each item prompt contains a blank written as "____". Optional stage.word_bank (size >= blanks + 1;
  not allowed in Apply). stage.example REQUIRED (prompt with blank + filled answer).
- SORT: stage.groups = 2-3 group names; each item prompt is one thing to sort (3-6 items incl. example);
  answer = exact group name. stage.example REQUIRED (one pre-sorted thing).
- COMPLETE_STEPS: a worked procedure with missing steps; each item prompt is one step containing "____";
  stage.example REQUIRED = Step 1 shown done. Use item.unit for units.
- SPOT_MISTAKE: item.peer_work = {{intro: third person e.g. "Ravi solved this and made one mistake:", steps:[...],
  mistake_step: 1-based index of the ONE wrong step}}; prompt asks to circle the wrong step and write it
  correctly; answer = the corrected step.
- SOLVE: problem solved in a workspace; item.unit = unit printed in the answer blank (or null).
- SHORT_ANSWER: 1-2 sentences; optional item.sentence_stem and item.keywords (checklist words, Recall only).
- SKETCH: simple drawing in a frame; item.sketch_criteria = countable criteria ("Draw 3 arrows that show...").

Text limits (counted by code; a number or expression like "1/2 x 8 x 5 = 20" counts as 1 word):
- Each instruction sentence <= {C.MAX_INSTRUCTION_WORDS} words, at most {C.MAX_ACTIONS_PER_INSTRUCTION} action verbs,
  verb first.
- Every other sentence <= {C.MAX_SENTENCE_WORDS} words.
- Words before the first pencil mark (hook + Discover instruction + item 1 text) <= {C.MAX_WORDS_BEFORE_FIRST_MARK}.
- Continuous reading between two pencil marks <= {C.MAX_READING_RUN_WORDS} words.
- Total words the child must write (answer lengths of FILL_IN, COMPLETE_STEPS, SPOT_MISTAKE, SOLVE,
  SHORT_ANSWER answers) <= {C.MAX_WRITTEN_WORDS}. A single number or letter counts as 0.
- Every technical term used after Discover must be explained in Discover.
- No negative-stem trick questions ("Which is NOT...", "EXCEPT"). No timers, scores, points, rewards, "Easy!".
- No word searches, crosswords, anagrams, mazes, colouring. No instruction may refer to colour.
- No item may be answerable by copying a Discover sentence word for word. Items in a stage must differ.
- Only pencil needed. Only tables as visuals (no pictures). A table counts as {C.VISUAL_S} s of viewing time.

Timing (computed by code, seconds): {C.ORIENTATION_S} orientation + per stage: printed words/{C.READING_WPM} wpm x 60
+ tables x {C.VISUAL_S} + items x weight (Discover 15, Reinforce 25, Vary 35, Apply 55, Recall 45; SKETCH +20)
+ written words/{C.WRITING_WPM} wpm x 60. Lesson total must be {C.T_MIN_S}-{C.T_MAX_S} s (target {C.T_TARGET_S}).
Stage caps: {C.BLOCK_CAP_S["Discover"]} s each, Apply {C.BLOCK_CAP_S["Apply"]} s.
Layout: everything must fit on two landscape A4 pages in two columns (Page 1: Discover | Reinforce;
Page 2: Vary | Apply above the Recall box). Keep prose short. Each column is about 175 mm tall.
Page 2 right column holds Apply AND the Recall box. Space budget: Apply heading ~15 mm, each SOLVE item ~50 mm,
each SHORT_ANSWER ~10 mm + 8 mm per ruled line (1 line per 8 answer words + 1 spare), each SKETCH ~60 mm,
Recall box heading ~20 mm. Two SOLVE items in Apply leave room for only one short Recall item.
Page 2 left (Vary): each SPOT_MISTAKE item ~45 mm. Keep each item prompt to one line where possible.

Grounding:
- Every core claim, term, and answer-key entry cites source_unit_ids from the list. Cite the units that
  actually support it.
- Allowed scaffolding: re-worded explanations, step-by-step breakdowns of source methods, new practice
  values/scenarios that apply exactly the source's method with numbers no harder than the source's examples,
  analogies marked is_analogy=true ("Think of it like...") which are never tested.
- Not allowed: facts, terms, methods, formulas or examples from outside the source.
- Apparent source errors: leave them out and list them in answer_key.source_issues.

Answer key: one entry per scored item: answer, accepted_alternatives (for written answers: the key points that
must be present), reason (one sentence), source_unit_ids, and calculation = a plain arithmetic expression
(numbers, + - * / ** ( ) sqrt pi) that reproduces every numeric answer, else null.
scope_covered: what this lesson covers. not_covered: what in the selected material was left out.
"""

SCHEMA_EXAMPLE = {
    "standard": 7,
    "title": "...",
    "scope_line": "Today: ...",
    "concepts": [{"name": "...", "source_unit_ids": ["SRC-P1-U2"]}],
    "core_claims": [{"text": "...", "source_unit_ids": ["SRC-P1-U2"], "is_analogy": False}],
    "terms": [{"term": "...", "definition": "...", "source_unit_ids": ["SRC-P1-U3"]}],
    "stages": [
        {
            "stage": "Discover",
            "activity_type": "CHOOSE",
            "hook": "...",
            "instruction": "...",
            "body_text": "...",
            "worked_example": ["Step 1: ...", "Step 2: ..."],
            "visuals": [{"caption": "...", "headers": ["..."], "rows": [["..."]], "source_unit_ids": ["SRC-P1-U4"]}],
            "example": None,
            "hint_pointer": None,
            "options": [],
            "word_bank": [],
            "groups": [],
            "items": [
                {
                    "number": 1,
                    "prompt": "...",
                    "options": ["...", "...", "..."],
                    "unit": None,
                    "sentence_stem": None,
                    "keywords": [],
                    "peer_work": None,
                    "sketch_criteria": None,
                }
            ],
        },
        {
            "stage": "Reinforce",
            "activity_type": "MATCH",
            "instruction": "...",
            "example": {"prompt": "...", "answer": "..."},
            "options": ["...", "...", "...", "..."],
            "items": [{"number": 2, "prompt": "..."}, {"number": 3, "prompt": "..."}],
        },
        {
            "stage": "Vary",
            "activity_type": "SPOT_MISTAKE",
            "instruction": "...",
            "hint_pointer": "Stuck? Look at ... on Page 1.",
            "items": [
                {
                    "number": 4,
                    "prompt": "...",
                    "peer_work": {"intro": "...", "steps": ["...", "..."], "mistake_step": 2},
                }
            ],
        },
        {
            "stage": "Apply",
            "activity_type": "SOLVE",
            "instruction": "...",
            "hint_pointer": "Stuck? ...",
            "items": [{"number": 6, "prompt": "...", "unit": "cm"}],
        },
        {
            "stage": "Recall",
            "activity_type": "SHORT_ANSWER",
            "instruction": "...",
            "hint_pointer": None,
            "items": [{"number": 8, "prompt": "...", "keywords": ["...", "..."]}],
        },
    ],
    "answer_key": {
        "entries": [
            {
                "item_number": 1,
                "answer": "...",
                "accepted_alternatives": [],
                "reason": "...",
                "calculation": None,
                "source_unit_ids": ["SRC-P1-U2"],
            }
        ],
        "scope_covered": "...",
        "not_covered": "...",
        "source_issues": [],
        "shortened_lesson_note": None,
    },
}

GENERATE_PROMPT = """Write the lesson.

Standard: {standard}
Concept selection: {selection}

{rules}

JSON shape (fill every field; items/entries abbreviated here):
{schema}

Source units (the ONLY allowed source of facts, terms and methods):
{units}

Reply with the complete lesson JSON object only."""

REPAIR_PROMPT = """The lesson below failed automated checks. Return a corrected COMPLETE lesson JSON.

Failed checks:
{failures}

Code-computed timing (seconds): {timing}

How to fix timing or layout problems (methodology 6.4), in this order:
Too long / a stage over its cap / a page overflows:
 1. Shorten prose (explanation, story context, instructions) without removing taught content.
 2. In Reinforce or Vary, replace a written-answer item with MATCH, CHOOSE or SORT.
 3. Remove an item that tests the same thing as another item in the same stage (never below a stage's
    minimum; keep at least one item per taught sub-concept).
 4. Narrow the scope to fewer sub-concepts and state this in answer_key.not_covered.
Too short:
 1. Add a grounded item to Vary or Apply (within the stage maximum), testing a different case.
 2. Add a grounded item to Reinforce (within the stage maximum).
 3. Replace a CHOOSE/ANNOTATE item in Reinforce or Vary with FILL_IN, COMPLETE_STEPS or SPOT_MISTAKE.
 Never pad with filler text. If the source genuinely cannot support more grounded items, keep the lesson as it
 is and set answer_key.shortened_lesson_note to: "This lesson is about N minutes, shorter than usual, because
 the uploaded material covers a limited amount on this topic." (N = whole minutes).
Fix every other failure directly. Keep item numbering continuous and the answer key in sync.
Never add content that is not supported by the source units.

{rules}

Current lesson:
{lesson}

Source units:
{units}

Reply with the complete corrected lesson JSON object only."""


def select_concept(llm: LLM, index: SourceIndex, standard: int, topic: str) -> dict:
    prompt = SELECT_PROMPT.format(standard=standard, topic=topic or "(none - choose)", units=index.prompt_block())
    return llm.json("select_concept", SYSTEM, prompt)


def _to_lesson(llm: LLM, task: str, prompt: str) -> Lesson:
    data = llm.json(task, SYSTEM, prompt)
    try:
        return Lesson.model_validate(data)
    except ValidationError as e:
        errors = "; ".join(f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()[:15])
        retry = f"{prompt}\n\nYour previous JSON did not match the required shape: {errors}. Reply with corrected JSON."
        try:
            return Lesson.model_validate(llm.json(task, SYSTEM, retry))
        except ValidationError as e2:
            raise GenerationError(f"model output did not match the lesson schema: {e2.errors()[:3]}") from e2


def generate_lesson(llm: LLM, index: SourceIndex, standard: int, selection: dict) -> Lesson:
    prompt = GENERATE_PROMPT.format(
        standard=standard,
        selection=json.dumps(selection, ensure_ascii=False),
        rules=LESSON_RULES,
        schema=json.dumps(SCHEMA_EXAMPLE, indent=1),
        units=index.prompt_block(),
    )
    try:
        lesson = _to_lesson(llm, "generate_lesson", prompt)
    except LLMError as e:
        raise GenerationError(str(e)) from e
    return lesson


def repair_lesson(llm: LLM, index: SourceIndex, lesson: Lesson, failures: list[str], timing: dict) -> Lesson:
    prompt = REPAIR_PROMPT.format(
        failures="\n".join(f"- {f}" for f in failures),
        timing=json.dumps(timing),
        rules=LESSON_RULES,
        lesson=lesson.model_dump_json(indent=1),
        units=index.prompt_block(),
    )
    try:
        return _to_lesson(llm, "repair_lesson", prompt)
    except LLMError as e:
        raise GenerationError(str(e)) from e
