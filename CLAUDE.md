# Learn — guidance for Claude

Learn turns one curriculum PDF into a printable ~15-minute lesson for Standard 7–8: exactly 2 landscape A4 student pages plus a separate 1–2 page parent answer key. Nothing is delivered unless every check passes.

## Source of truth
- `methodology/CORE_TEACHING_METHODOLOGY_FINAL.md` is the specification. Follow it.
- Other files in `methodology/` are history only.
- If the spec contradicts itself or blocks implementation, report it to the user. Never silently change the spec, or code around it.
- Numbers from methodology §10 live in `learn/config.py`. Change them only there.

## Commands
```bash
pip install -r requirements-dev.txt && playwright install chromium   # setup
pre-commit install             # ruff check --fix + ruff format on each commit (.pre-commit-config.yaml)
pytest -q                      # all tests (~20 s, includes real Chromium rendering)
ruff check .                   # lint (config in ruff.toml)
ruff format .                  # format; CI runs pytest, ruff check and ruff format --check on every PR
python -m learn.cli some.pdf --standard 7    # one run (needs ANTHROPIC_API_KEY)
uvicorn learn.web:app          # local web UI
```

In Claude Code cloud sessions, `.claude/hooks/session-start.sh` does the setup: it creates `.venv`, installs `requirements-dev.txt`, and points `CHROMIUM_EXECUTABLE` at the preinstalled browser. Don't run `playwright install` there. The hook runs asynchronously: right at the start of a session, `.venv` may not be ready yet. If `pytest` or `ruff` is missing, run `.claude/hooks/session-start.sh` yourself and wait for it.

## Layout
Pipeline in `learn/pipeline.py`:

extract → select + sufficiency → focus → teaching plan → generate → timing → render → checks → repair (≤2 rounds) → deliver or report

| Area | Files |
| :--- | :--- |
| PDF → source units `SRC-P{page}-U{n}`, OCR | `extraction.py` |
| Page ranges, source index, sufficiency check | `grounding.py` |
| Prompts | `generation.py` |
| Model client | `llm.py` |
| Lesson schema (§9) | `models.py` |
| Reading order shared by timing and the checks | `sequence.py` |
| Timing (§6) | `timing.py` |
| Answer arithmetic | `calc.py` |
| HTML → PDF, layout measurement | `rendering.py` + `templates/` |
| Visual specs, deterministic SVG, D8 helpers | `visuals/specs.py`, `visuals/svg.py`, `visuals/checks.py` |
| Practice diagrams: label slots, derived answers, D9 | `visuals/practice.py` |
| Checks D1–D9 and A1–A4 | `validation.py` |
| UI | `web.py`, `cli.py` |

## Rules that must not regress
- **Never deliver partial or unvalidated PDFs.**
  - Rendering writes to `work/`. Only a fully passing round is copied to `deliver/`.
  - The web server serves `deliver/` files only.
- **Never invent curriculum content.**
  - Every claim, term, table and answer-key entry cites existing source units (D2).
  - When the source is thin, stop with a limitation report.
- **Timing is computed in code** from the lesson data. Never trust a model's estimate.
  - `sequence.py` defines the order the template prints.
  - If you change `templates/student.html.j2`, keep `sequence.py` in step with it.
- **Numeric answers carry a `calculation`.** `calc.py` re-evaluates it (D7). Keep the evaluator restricted: no `eval`, no names beyond `sqrt`/`pi`.
- **The A2 blind solver gets only the student-PDF text.** Never the key, never the source.
- **Visuals are drawn by code, never by the model.**
  - SVG must be deterministic: same spec, same output.
  - Pencil-style line art only: black outlines, white fill (`INK_FILLS`), small black arrowheads and dots.
  - Each type has a fixed size budget.
  - Labels come from the spec, so the picture can't contradict its numbers.
  - Keep older tables without `kind` loading.
- **Hidden-label answers come from the diagram spec** (`fill_visual_answers`), never from the model. Support must fade (D9): labelled in Discover, partly completed in Reinforce, no more help in Vary or Apply, no diagram in Recall.
- **Model calls go through `LLM.json(task, system, prompt)`.** This keeps every call replaceable by the scripted fake in `tests/conftest.py`.
- **After selection, the model sees only the focused source** (`SourceIndex.focus`). Never pass the whole PDF to planning, generation or repair. D2 rejects citations outside the focus.
- **Output limits:** thinking counts toward `max_tokens`. Retry a cut-off response at most once, clamp to the model's limit, and log every request (`AnthropicLLM.call_log` → `report.model_calls`).
- **Errors become reports.** Missing credentials and unexpected exceptions produce a stopped `Report`, never a crash.

Keep the ruff `rev` in `.pre-commit-config.yaml` equal to the ruff pin in `requirements-dev.txt`, which CI uses.

## Teaching Engine and Detective game (`learn/teaching_engine/`)
The offline engine behind the public site (`learn/teaching_web.py`, deployed on Render with the `Dockerfile` and `requirements-teaching.txt`). It needs no API key, and the methodology spec doesn't govern it.
- `sheet.py` reads the uploaded PDF's layout; `cards.py` plans and prints the study cards. Follow `docs/ENGINE_GUIDE.md`: don't change the upload page template, add no topic-specific rules, never weaken a test.
- `detective.py` makes the Detective case file (design in `docs/DETECTIVE_GAME.md`). Rule A: every line of the sheet is on a card. Rule B: card variety and order. `check_case_file` gates printing.
- `ai_cards.py` lets a model choose a case file's cards. The model only picks lines and words to hide; code builds every card from the sheet's own words and falls back to the rule-based cards on any failure.
  - It runs only with `--ai` on the command line, for at most `LEARN_CARDS_AI_SHEETS` sheets (default 1). The website doesn't call it yet.
  - `LEARN_PROVIDER=june` sends calls to June's Anthropic-format API. The key comes from the environment's network secret for `api.blockchain.info`, or from `JUNE_API_KEY`.
  - `LEARN_PROVIDER=google` sends calls to Gemini on Google's OpenAI-style API (`OpenAIStyleLLM` in `llm.py`, plain httpx). The key comes from a network secret for `generativelanguage.googleapis.com`, or from `GOOGLE_API_KEY`. Get card models from `llm.card_llm()`, never by building a client directly.
  - Live runs so far: Haiku 5.5 (through June and the Anthropic API) and Gemini (through June and Google) have written Detective case papers for sample and test sheets. No child or parent has used the cards yet. Don't claim more.
- `evidence_cards.py` makes Detective Mode case papers (`--case-papers`): the model writes everyday-scene Evidence cards from the sheet's numbered lines, and `check_card` holds each card to the sheet.
  - The sheet is the only truth. The answer must be printed in the card's lines, and any number or capitalised name on a card must be on the sheet; only `SCENE_NAMES` and `EVERYDAY_NAMES` are exempt. Don't loosen these checks to raise the model's pass rate.
  - Cards that pass are kept one by one. Lines no passing card teaches get plain rule-based cards.
  - Word checks can't catch an invented ordinary sentence ("they marched with their weapons"), so with `LEARN_EVIDENCE_REVIEW` on (the default) a second request reviews each group's cards against their lines. Flagged cards are dropped, and their lines go back to the model once. A word-overlap rule was tried and rejected: it flagged a third of the good, simplified sentences.
  - One model call per group of lines writes both parts of the printout. The model labels each card `mode` (`card_mode` decides for unlabelled and plain cards). Detective cards, whose answer is a name, place, date or number, print first in the case-paper look. Hero cards, whose answer is an idea, print after them in the Hero Academy look (`hero_papers.py`). Every line is taught once, so no question repeats.
  - The website's Detective button calls it when the chosen provider's key is set (`config.card_key_name()`), for up to `LEARN_DETECTIVE_AI_SHEETS` sheets per upload, `LEARN_DETECTIVE_WORKERS` at a time, and `LEARN_DETECTIVE_DAILY_LIMIT` uploads a day. Uploads over `LEARN_DETECTIVE_MAX_PAGES` pages are refused before any model call. A repeat of the same upload is served from memory.
  - Without a key, past the limit, or with no good model card, the button makes the rule-based case file, with a note telling the parent why. Every Detective upload logs one line (model, calls, tokens, time).
  - Website tests replace the model with a fake that fails at once (`tests/test_teaching_web.py`). Never let a test reach a real model: a network secret can fill in a real key.
- Tests: `tests/test_detective.py`, `tests/test_ai_cards.py`, `tests/test_evidence_cards.py` (scripted fake model), and the `test_teaching_*.py` files.

## Cards (`cards/`)
A separate browser-only tool: study-sheet PDF → picture flashcards, no AI. It shares no code with `learn/`, and the methodology spec doesn't govern it. See `cards/README.md`.
- The uploaded PDF is the fact sheet. Teach the engine how to ask, never what the facts are. Samples in `cards/sample/` only test rules and must never feed content into cards.
- Test with `cd cards && npm ci && npm test` (CI runs this too).
- Card backs must stay word-for-word from the sheet. Clue fronts may add only fixed prompts. `engine/checks.js` enforces both, and a failed check blocks showing and printing.
- When you change a check, add a passing case and a targeted failing mutation in `cards/test/engine.test.js`.
- Pictures are Tabler icons copied into `engine/icons.js` by `scripts/build-icons.mjs` (keep the MIT notice), or drawn in `engine/symbols.js`. Nothing is fetched at run time. No match means a "draw it!" box, not a guess.
- Photos come only from images printed in the uploaded PDF (`engine/photos.js`), and only `data:image/` URLs reach a card.
- The pdf.js version is pinned in both `cards/package.json` and `cards/app.js`. Change them together.
- All sheet text goes through `esc()` before it reaches the page.
- Name fun facts (`engine/nametips.js`, shown as "Fun fact") are the one thing not from the sheet: back-footer only, never an answer, exact names only (no suffix rules), uncertain origins left out.
- Follow the teaching rules for hard names in `cards/README.md`: 2–3 supporting clues, one-jump tricks from the child's world, a "my trick" box, and tricks are never answers.

## Tests
- Tests must not need an API key or network. Use `ScriptedLLM` and the synthetic fixtures in `tests/fixtures.py`.
- The fixtures are synthetic and the fake model's outputs are canned. Don't present test results as evidence of lesson quality.
- When you add or change a check, add a passing case and a targeted failing mutation in `tests/test_checks.py` (or `test_render.py` for layout).
- Never skip or weaken a test to get CI green.

## Honesty
- No lesson has yet been generated with the live model, and nothing has been tested with children. Don't claim otherwise in code, docs or PRs.
- Keep the check status table in `README.md` accurate when checks change.
