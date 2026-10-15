# Learn — V1 prototype

A parent uploads one curriculum PDF and selects Standard 7 or 8. Learn produces:

- a **student lesson**: exactly 2 landscape A4 pages, pencil only, about 15 minutes;
- a separate **parent answer key**: 1–2 landscape A4 pages.

Lessons are delivered **only** if every check in the methodology passes. Otherwise the parent gets a plain-language limitation report.

The specification is [`methodology/CORE_TEACHING_METHODOLOGY_FINAL.md`](methodology/CORE_TEACHING_METHODOLOGY_FINAL.md). The other files in `methodology/` are history only.

> **Status — read this first.**
> - This is a development prototype. It has **not** been tested with children or parents.
> - No lesson has yet been generated with the real Claude API. The development environment had no API key.
> - The automated tests use a synthetic one-page curriculum PDF and a **scripted fake model** (see [Testing](#testing)).
> - All timing numbers are the methodology's provisional values.

**Also in this repo:** `cards/` is a separate, browser-only prototype. It turns a study-sheet PDF into printable picture flashcards with no AI. See [`cards/README.md`](cards/README.md).

The separate Teaching Engine has a traceable source fact inventory ([Stage 1](docs/TEACHING_ENGINE_STAGE_1.md)) and an offline, child-centred lesson planner ([usage](docs/TEACHING_ENGINE.md)). It needs no API key. The API-key setup below applies only to the older printable-lesson workflow.

---

## Setup

Requires Python 3.11+ (developed on 3.13).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt        # or requirements.txt without the test tools
playwright install chromium                # headless browser used to print the PDFs
cp .env.example .env                       # then put your key in .env
pre-commit install                         # optional: run ruff on every commit
```

For the older printable-lesson workflow, set `ANTHROPIC_API_KEY` in `.env` or your shell. The separate Teaching Engine works without it.

**OCR (optional).** Scanned pages with no text layer need OCR.
- If the `tesseract` command is installed (e.g. `apt install tesseract-ocr`), Learn uses it.
- Otherwise Learn falls back to Claude vision transcription.
- Set `LEARN_OCR=off` to disable OCR. Scanned pages are then reported as unreadable.

## Run

**Web UI** (local, single user):

```bash
uvicorn learn.web:app
# open http://127.0.0.1:8000
```

Upload a PDF, choose Standard 7 or 8, and optionally give a topic or a page range (e.g. `3-5`). One request makes several model calls and usually takes a few minutes. The page waits until it is done.

**Command line:**

```bash
python -m learn.cli path/to/curriculum.pdf --standard 7 [--topic "area of a triangle"] [--pages 3-5]
```

The exit code is 0 when a lesson was delivered and 2 when it stopped with a limitation report.

**Offline Teaching Engine** (no API key, model, or network calls):

```bash
python -m learn.teaching_engine path/to/curriculum.pdf --out teaching_lesson.json [--pages 3-5]
```

This writes a source-linked JSON teaching scaffold. It is separate from the older printable-PDF command above.

**Offline Teaching Engine web app:**

```bash
uvicorn learn.teaching_web:app --reload
# open http://127.0.0.1:8000
```

`render.yaml` deploys this separate app using only `requirements-teaching.txt`; it does not launch the old Claude-based printable workflow. See [Render setup](docs/TEACHING_ENGINE.md#web-app-and-render-deployment).

**Output folder** (`output/<job>/`, set with `LEARN_OUTPUT_DIR`):

| Path | Contents |
| :--- | :--- |
| `deliver/student_lesson.pdf`, `deliver/parent_answer_key.pdf` | Created **only** when every check passed. |
| `work/` | Teaching plan, lesson JSON, HTML and PDFs for each repair round. Kept for debugging; **never** served or delivered. |
| `report.json` | Status, parent message, every check result, computed timing, PDF warnings, log; the technical `error` that stopped a run; the focused source units and the teaching plan; and `model_calls`: one record per API request with its task, effort, `max_tokens`, `stop_reason`, input/output/thinking tokens and any error. |

---

## How it works

| Pipeline step (methodology §2) | Module |
| :--- | :--- |
| 1. Input (PDF, Standard 7/8, optional topic or page range) | `learn/web.py`, `learn/cli.py`, `learn/grounding.py` (page ranges) |
| 2. Extract text blocks into source units `SRC-P{page}-U{n}`; OCR for pages with no text layer | `learn/extraction.py` |
| 3–4. Choose the concept; sufficiency test (§3.3) | `learn/generation.py` (model proposes, citing units) + `learn/grounding.py::check_selection` (code verifies the cited units exist) |
| Focus: from here on the model sees only the selected units plus one neighbour either side on the same page | `learn/grounding.py::SourceIndex.focus` |
| 5a. Teaching plan: concept, 2–3 incremental learning steps, one likely misconception, a worked example, a visual type. Code checks its shape, citations (inside the focus) and worked-example arithmetic, re-asking once | `learn/generation.py::plan_lesson`, `learn/grounding.py::check_plan` |
| 5b. Generate lesson and answer-key data (§9 schema) from the plan | `learn/generation.py`, `learn/models.py` |
| 6. Timing (§6), computed in code from the lesson data | `learn/timing.py`, `learn/sequence.py` |
| 7. Render HTML to PDF (fixed template, §7) | `learn/rendering.py`, `learn/templates/*.j2` |
| 7a. Draw visuals: deterministic SVG from validated specs (shape, number line, bar model, flow sequence; tables stay HTML) | `learn/visuals/` |
| 7b. Visual practice: items may carry a diagram with hidden labels; code writes their answer-key values from the diagram spec | `learn/visuals/practice.py` |
| 8. Validate: D1–D9 in code, A1–A4 as separate model calls | `learn/validation.py`, `learn/calc.py`, `learn/visuals/checks.py`, `learn/visuals/practice.py` |
| 9. Repair: at most 2 rounds, each fully re-rendered and re-checked | `learn/pipeline.py` |
| 10. Deliver, or stop with a limitation report | `learn/pipeline.py` |

Design rules the code enforces:
- **The model never sets timing.** Timing is calculated from the printed words, tables, items and answer lengths. These are counted in the same reading order the template prints (`learn/sequence.py`).
- **Source pages in the answer key** are derived in code from the cited source units.
- **Numeric answers are recomputed.**
  - Each numeric answer in the key carries an arithmetic expression (for example `0.5*12*7`).
  - D7 evaluates it with a restricted AST evaluator (`learn/calc.py`) and compares it with the stated answer.
  - A numeric SOLVE or COMPLETE_STEPS answer without a calculation fails D7.
- **The blind solver (A2) sees only the student pages.** It gets the text of the rendered student PDF, never the key or the source. A test asserts this.
- **Every model call is mockable.** Calls go through `learn/llm.py` (`LLM.json(task, system, prompt)`).
- **Output limits are explicit.** On current models thinking counts toward `max_tokens`.
  - Each response gets `LEARN_MAX_TOKENS` (default 32000).
  - A response stopped at `max_tokens` is retried **once** with `LEARN_MAX_TOKENS_RETRY` (default 64000).
  - Both are clamped to the model's own output limit, read from the Models API. If that can't be read, the configured values are used and the report says so.
  - Refusals and API errors are never retried.
  - Writing tasks (plan, lesson, repair) use `LEARN_EFFORT` (default high); selection, OCR and the AI checks use `LEARN_CHECK_EFFORT` (default medium).

### Checks: what is implemented

| ID | Check | How | Status |
| :--- | :--- | :--- | :--- |
| D1 | Structure: 5 stages in order, item counts per stage, total 7–13, hook, worked example, Standard 7/8 | code | Implemented and tested |
| D2 | Citations: every concept, claim, term, table and key entry cites source units from the focused selection the model was given | code | Implemented and tested |
| D3 | Activity rules (§5.1, §5.2): allowed stages, ≥3 types, no consecutive repeats, required `Ex`, options ≥ prompts + 1, CHOOSE 3–4 options with exactly one correct, ANNOTATE targets, SORT groups, SPOT_MISTAKE single step, SKETCH criteria | code | Implemented and tested |
| D4 | Text limits (§5.3): instruction ≤22 words and ≤2 actions, sentences ≤25 words, ≤65 words before the first mark, ≤120-word reading runs; banned patterns (scores, timers, NOT/EXCEPT stems, word searches…); colour words in instructions | code | Implemented and tested. Action counting uses a fixed verb list (heuristic). |
| D5 | Timing (§6.3) with Rule S (§6.4) | code | Implemented and tested |
| D6 | Layout (§7.2): exactly 2 student pages, 1–2 key pages, landscape A4 measured from the PDFs; no overflow; font ≥10.5 pt; lines ≥7.5 mm and ≥80 mm long; ruled lines per answer; numeric blank ≥25 mm; SOLVE space ≥35 mm; Recall box at bottom right of page 2 with banner; hint pointers; no key content in the student PDF | headless Chromium measurement + PDF inspection | Implemented and tested |
| D7 | Answer key: one entry per item, numbering matches, reason, source page, arithmetic re-verified | code | Implemented and tested |
| D8 | Visuals: each has a teaching purpose; valid structure (shape dimensions, number-line range and step, bar parts summing to totals, 2–6 sequence steps, table size); the drawing shows exactly the labels its spec implies; black outlines and white fill only; fixed size budget; grounding is checked on the text actually printed (caption, every string in the SVG including generated shape labels, and table headers and cells): every printed number is in the cited source or the stage's text (axis ticks, jump lengths and computed bar totals exempt); every content word in the caption and labels is in the cited source or the lesson's terms (code-written labels and table column-header words exempt); a shape's unit is used in the cited source or stage text; Discover shows the teaching plan's visual type | code | Implemented and tested. The word check is a heuristic (4+ letter words, simple plural stripping). |
| D9 | Visual progression: practice diagrams only in Reinforce/Vary/Apply and only of a kind Discover demonstrated fully labelled; FILL_IN or SOLVE; hidden labels name real slots; Reinforce leaves at least one label; the share of hidden labels never falls from Reinforce to Vary to Apply; no diagram in Recall; each key answer equals the value read from the diagram; each hidden word is taught in Discover (text or diagram) or offered in the word bank, and each hidden number is stated on the page or produced by the key calculation | code | Implemented and tested |
| A1 | Grounding and factual correctness | model call | Implemented. Exercised only with a scripted fake in tests; **not yet run against the real API**. |
| A2 | Blind solve from student pages only | model call + code (all items answered, zero flags) | Same as A1 |
| A3 | Blind-solver answers agree with the key | model call | Same as A1 |
| A4 | Clarity and age fit; with a teaching plan, also whether the lesson builds through the plan's steps, uses its worked example and addresses its misconception | model call | Same as A1 |
| H (§8.4) | Pilot calibration with children, print tests, parent review | humans | **Not done.** No testing with children has happened. |

The sufficiency test (§3.3) is split three ways:
- The model assesses (a)–(c) and cites the units it relied on.
- Code rejects selections whose cited units don't exist, or that admit (b) is not met.
- After generation, (b) is enforced again by D1 (at least 7 items), D2/A1 (grounding) and A2/A3 (answerable and correct).

---

## Testing

```bash
pytest -q
ruff check .        # lint; rules in ruff.toml
ruff format .       # format (CI runs ruff format --check)
```

128 tests run in about 35 s, including real Chromium rendering. GitHub Actions runs the tests, the ruff lint and a ruff format check on every pull request and on pushes to `main` (`.github/workflows/tests.yml`); CI needs no API key. What the tests cover:
- **Timing:** the methodology's §6.5 worked example is reproduced exactly (903.3 s); word-counting rules; sketch time counted once.
- **Arithmetic evaluator:** correct results; rejects unsafe or invalid input; allows the answer's stated rounding.
- **Extraction:** text PDFs; page ranges; scanned pages with OCR off and with a fake OCR; non-PDF files.
- **Every deterministic check:** passes on a valid lesson, and fails on targeted mutations (wrong stage order, too few items, missing citations, too few MATCH options, a NOT question, colour in an instruction, too long or too short, Rule S, an arithmetic error, a missing key entry).
- **Rendering:** 2 landscape A4 student pages; a 1–2 page landscape A4 key; key text absent from the student PDF; overflow is detected.
- **Pipeline (scripted fake model):**
  - delivers when all checks pass;
  - stops on an insufficient source, or on a selection citing units that don't exist;
  - repairs and re-checks after a failure;
  - stops after exactly 2 repair rounds with nothing delivered;
  - an AI-check failure blocks delivery;
  - missing credentials and unexpected errors produce a report, not a crash.
- **Web:** upload, then download only the delivered files; a non-PDF upload and a bad Standard are rejected.
- **Model client (fake SDK client):** a truncated response is retried once with a larger budget; a second truncation stops with details and no third request; budgets are clamped to the model's limit; no retry when the first budget is already at the limit; Models API failure falls back to configured limits; refusals aren't retried; effort per task; errors are logged.
- **Teaching plan:** the sample plan passes; too many steps, unselected citations, wrong worked-example arithmetic and a missing visual purpose are caught; one re-ask with the problems, then stop; the plan reaches the generation prompt; a bad plan stops the run with nothing delivered.
- **Visual engine:**
  - every type draws the same SVG for the same spec, uses only allowed ink and stays within its size budget;
  - tables written before `kind` existed still load;
  - labels come from the spec's numbers, and rectangles are drawn to proportion, with "(not to scale)" on extreme shapes;
  - D8 catches wrong totals, out-of-range points, uneven steps, ungrounded numbers (including years in labels and captions, and numbers in table headers), ungrounded words in captions and labels, unsupported units, a missing purpose, step-count limits, text too long for its box and ragged tables;
  - Discover must show the plan's visual type;
  - real Chromium draws each visual at its declared size with fonts of at least 10.5 pt;
  - the printed triangle's labels appear in the student PDF text.
- **Visual practice (D9):**
  - label slots and derived answers for every diagram type;
  - the key is filled from the diagram, replacing a wrong model answer;
  - hidden labels print as blanks in drawings and tables, and D8 accepts them;
  - a full progression from labelled to independent passes;
  - every D9 rule is caught (wrong stage or type, undemonstrated kind, unknown or empty slots, fully hidden in Reinforce, support increasing, key mismatch, unteachable numbers and words);
  - the pipeline delivers with the derived key.
- **Focused source:** neighbours stay on the same page; plan and generation prompts contain no unselected units; a lesson citing an unselected unit fails D2; the report carries the model call log and error.

**What the tests do not show.**
- `tests/fixtures.py` holds a **synthetic** "area of a triangle" PDF and a hand-written lesson. Neither is the curriculum PDF the methodology was tested against; that PDF is not in the repository.
- The fake model returns canned answers. The tests prove the code paths and the delivery rules, not the quality of lessons a real model writes.

---

## Known limitations and interpretations

1. **Live model output is unverified.**
   - No end-to-end run against the real Claude API has been done yet.
   - Prompt wording, JSON compliance and repair success rates are unknown until someone runs Learn with a key on real curriculum PDFs.
2. **Figures are not interpreted.**
   - Pages with pictures or diagrams are flagged in the warnings and the answer key, and only their text is used.
   - Lessons use code-drawn visuals instead: the teaching plan picks a shape, number line, bar model, flow sequence, table or none, and `learn/visuals/` draws it deterministically from validated numbers and words.
   - Visuals are pencil-style line art: black outlines, white fill, no shading. Only small arrowheads and point markers are filled.
   - Maps, pictures and free-form diagrams aren't supported.
3. **The teaching plan is a model output.** Code checks its grounding and arithmetic, not whether its learning steps are a good teaching order; A4 reviews that, and A4 is itself a fallible model check.
4. **Focused context depends on the selection.** If the selection step leaves out a unit the lesson needs, generation cannot see it. The plan and lesson then fail their checks and the run stops with a report, rather than inventing the missing material.
5. **Timing adjustment (§2 step 6) is folded into the repair loop.** A timing failure is repaired with the §6.4 hierarchy, then re-rendered and fully re-checked, and it counts toward the 2-round limit.
6. **Rule S** is accepted only from repair round 1 onward. It needs a `shortened_lesson_note` and a time of 600–780 s. This stops the first draft from declaring itself "short" instead of being lengthened.
7. **Template labels are not counted as reading words.** These are labels such as "Step 1 · Discover", "Worked example", "Answer:" and "Name/Date". They add a few seconds that the timing model does not count.
8. **Page 2 is tight.**
   - Its right column holds both Apply and the Recall box, about 177 mm in all.
   - Two SOLVE problems (each needs ≥35 mm of workspace) plus two Recall items do not fit.
   - The prompt gives the model a space budget, and D6 rejects overflow. Expect repairs to remove an item in such cases. This follows from the fixed §7.1 layout and may deserve a methodology revision after pilot use.
9. **Methodology rounding:** §6.5 states 15.06 min; 903.29 s ÷ 60 = 15.055, which rounds to 15.05 (15.06 comes from rounding 903.3 first). This makes no practical difference.
10. **OCR quality is untested.** Neither the Tesseract path nor the Claude vision path has been tested on a real scan here. Tesseract was not installable in the development environment, and there was no API key.
11. **Local prototype only.** Requests run synchronously. There are no accounts, no job queue and no clean-up of old output folders.
12. **Extraction keeps some layout noise.** On a real 6-page Grade 8 notes PDF:
    - running page footers were merged into the last unit of a page;
    - a comparison table came out as flattened text rather than rows and columns.

    Learn grounds lessons in that text as extracted.
