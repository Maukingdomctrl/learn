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

extract → select + sufficiency → generate → timing → render → checks → repair (≤2 rounds) → deliver or report

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
| Checks D1–D7 and A1–A4 | `validation.py` |
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
- **Model calls go through `LLM.json(task, system, prompt)`.** This keeps every call replaceable by the scripted fake in `tests/conftest.py`.
- **Errors become reports.** Missing credentials and unexpected exceptions produce a stopped `Report`, never a crash.

Keep the ruff `rev` in `.pre-commit-config.yaml` equal to the ruff pin in `requirements-dev.txt`, which CI uses.

## Tests
- Tests must not need an API key or network. Use `ScriptedLLM` and the synthetic fixtures in `tests/fixtures.py`.
- The fixtures are synthetic and the fake model's outputs are canned. Don't present test results as evidence of lesson quality.
- When you add or change a check, add a passing case and a targeted failing mutation in `tests/test_checks.py` (or `test_render.py` for layout).
- Never skip or weaken a test to get CI green.

## Honesty
- No lesson has yet been generated with the live model, and nothing has been tested with children. Don't claim otherwise in code, docs or PRs.
- Keep the check status table in `README.md` accurate when checks change.
