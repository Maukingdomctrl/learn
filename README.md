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

---

## Setup

Requires Python 3.11+ (developed on 3.13).

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt        # or requirements.txt without the test tools
playwright install chromium                # headless browser used to print the PDFs
cp .env.example .env                       # then put your key in .env
```

Set `ANTHROPIC_API_KEY` in `.env` or your shell. Without a key Learn still runs, but every request stops with a limitation report saying the model is not configured.

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

**Output folder** (`output/<job>/`, set with `LEARN_OUTPUT_DIR`):

| Path | Contents |
| :--- | :--- |
| `deliver/student_lesson.pdf`, `deliver/parent_answer_key.pdf` | Created **only** when every check passed. |
| `work/` | Lesson JSON, HTML and PDFs for each repair round. Kept for debugging; **never** served or delivered. |
| `report.json` | Status, parent message, every check result, computed timing, PDF warnings, log. |

---

## How it works

| Pipeline step (methodology §2) | Module |
| :--- | :--- |
| 1. Input (PDF, Standard 7/8, optional topic or page range) | `learn/web.py`, `learn/cli.py`, `learn/grounding.py` (page ranges) |
| 2. Extract text blocks into source units `SRC-P{page}-U{n}`; OCR for pages with no text layer | `learn/extraction.py` |
| 3–4. Choose the concept; sufficiency test (§3.3) | `learn/generation.py` (model proposes, citing units) + `learn/grounding.py::check_selection` (code verifies the cited units exist) |
| 5. Generate lesson and answer-key data (§9 schema) | `learn/generation.py`, `learn/models.py` |
| 6. Timing (§6), computed in code from the lesson data | `learn/timing.py`, `learn/sequence.py` |
| 7. Render HTML to PDF (fixed template, §7) | `learn/rendering.py`, `learn/templates/*.j2` |
| 8. Validate: D1–D7 in code, A1–A4 as separate model calls | `learn/validation.py`, `learn/calc.py` |
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

### Checks: what is implemented

| ID | Check | How | Status |
| :--- | :--- | :--- | :--- |
| D1 | Structure: 5 stages in order, item counts per stage, total 7–13, hook, worked example, Standard 7/8 | code | Implemented and tested |
| D2 | Citations: every concept, claim, term, table and key entry cites existing source units | code | Implemented and tested |
| D3 | Activity rules (§5.1, §5.2): allowed stages, ≥3 types, no consecutive repeats, required `Ex`, options ≥ prompts + 1, CHOOSE 3–4 options with exactly one correct, ANNOTATE targets, SORT groups, SPOT_MISTAKE single step, SKETCH criteria | code | Implemented and tested |
| D4 | Text limits (§5.3): instruction ≤22 words and ≤2 actions, sentences ≤25 words, ≤65 words before the first mark, ≤120-word reading runs; banned patterns (scores, timers, NOT/EXCEPT stems, word searches…); colour words in instructions | code | Implemented and tested. Action counting uses a fixed verb list (heuristic). |
| D5 | Timing (§6.3) with Rule S (§6.4) | code | Implemented and tested |
| D6 | Layout (§7.2): exactly 2 student pages, 1–2 key pages, landscape A4 measured from the PDFs; no overflow; font ≥10.5 pt; lines ≥7.5 mm and ≥80 mm long; ruled lines per answer; numeric blank ≥25 mm; SOLVE space ≥35 mm; Recall box at bottom right of page 2 with banner; hint pointers; no key content in the student PDF | headless Chromium measurement + PDF inspection | Implemented and tested |
| D7 | Answer key: one entry per item, numbering matches, reason, source page, arithmetic re-verified | code | Implemented and tested |
| A1 | Grounding and factual correctness | model call | Implemented. Exercised only with a scripted fake in tests; **not yet run against the real API**. |
| A2 | Blind solve from student pages only | model call + code (all items answered, zero flags) | Same as A1 |
| A3 | Blind-solver answers agree with the key | model call | Same as A1 |
| A4 | Clarity and age fit | model call | Same as A1 |
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
```

50 tests run in about 20 s. GitHub Actions runs the tests and the ruff lint on every pull request and on pushes to `main` (`.github/workflows/tests.yml`). CI needs no API key. They include real Chromium rendering. What they cover:
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
   - The only visuals in V1 lessons are tables (no generated diagrams).
3. **Timing adjustment (§2 step 6) is folded into the repair loop.** A timing failure is repaired with the §6.4 hierarchy, then re-rendered and fully re-checked, and it counts toward the 2-round limit.
4. **Rule S** is accepted only from repair round 1 onward. It needs a `shortened_lesson_note` and a time of 600–780 s. This stops the first draft from declaring itself "short" instead of being lengthened.
5. **Template labels are not counted as reading words.** These are labels such as "Step 1 · Discover", "Worked example", "Answer:" and "Name/Date". They add a few seconds that the timing model does not count.
6. **Page 2 is tight.**
   - Its right column holds both Apply and the Recall box, about 177 mm in all.
   - Two SOLVE problems (each needs ≥35 mm of workspace) plus two Recall items do not fit.
   - The prompt gives the model a space budget, and D6 rejects overflow. Expect repairs to remove an item in such cases. This follows from the fixed §7.1 layout and may deserve a methodology revision after pilot use.
7. **Methodology rounding:** §6.5 states 15.06 min; 903.29 s ÷ 60 = 15.055, which rounds to 15.05 (15.06 comes from rounding 903.3 first). This makes no practical difference.
8. **OCR quality is untested.** Neither the Tesseract path nor the Claude vision path has been tested on a real scan here. Tesseract was not installable in the development environment, and there was no API key.
9. **Local prototype only.** Requests run synchronously. There are no accounts, no job queue and no clean-up of old output folders.
