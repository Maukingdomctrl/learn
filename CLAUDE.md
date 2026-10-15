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

## Cards (`cards/`)
A separate browser-only tool: study-sheet PDF → picture flashcards, no AI. It shares no code with `learn/`, and the methodology spec doesn't govern it. See `cards/README.md`.
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
