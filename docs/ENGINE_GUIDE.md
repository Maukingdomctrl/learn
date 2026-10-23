# Card engine guide

How the study-card engine decides its questions, and the rules for changing it without making the cards worse. Read this before you edit the engine, whether you are a person or an AI tool.

The engine is rule-based. It uses no AI, needs no API key, and runs on the free Render plan. The site calls it through `learn/teaching_web.py` → `render_printable_cards_pdf()` in `learn/teaching_engine/cards.py`.

## Where the "brain" is

All three files are in `learn/teaching_engine/`. Line numbers are approximate and shift as the code changes.

### `cards.py`: decides the questions (start here)

| Where | What it does |
| :--- | :--- |
| `_QUESTIONS` (~line 43) | The wording of every question ("What is it?", "Which year fits the gap?"…), for Standards 7, 8 and 9 |
| `plan_cards()` (~line 768) | **The main brain.** Walks the sheet item by item and picks a card type for each |
| `_point_cards()` (~line 708) | For each sentence: riddle, gap, term, equation, finish-the-sentence… |
| `_gap()` (~line 245) | Picks which date, year or number to blank |
| `_hide_name()` (~line 208) | Hides the answer's name, so a riddle doesn't give it away |
| `_finish()`, `_key_cloze()`, `_recall_question()` (~lines 341–376) | Other card shapes |
| `_table_cards()` (~line 586) | Cards made from tables |
| `_practice_prompt()`, `_practice_reinforcement()` (~lines 1031–1102) | The fill-in-the-blank pages |
| `render_cards_pdf()` (~line 1298) | Page order and printing |
| `render_printable_cards_pdf()` (~line 1377) | What the site calls: reads the sheet, plans the cards, prints them |

### `sheet.py`: reads the PDF

| Where | What it does |
| :--- | :--- |
| `read_sheet()` (~line 773) | Turns the PDF layout into items in reading order |
| `_classify()` (~line 581) | Decides whether each item is a title, topic, point, question, answer, tip or table |
| `_is_furniture()`, `_without_running_lines()` | Drop headers, footers and page numbers |

### `facts.py`: the basics

- `split_sentences()` splits text into sentences.
- `REVIEW_CUES` lists words like "largest" that add a "check this" note for the adult.

## Rules for any change

1. **Engine changes leave the upload page alone.** Don't edit `learn/templates/teaching_upload.html.j2` as part of an engine change. Change it only when the task is about the page itself (its design, wording or accessibility), and check it at phone, tablet and desktop widths.
2. **One short answer per card.** An answer is a word, name, year or number, taken word-for-word from the sheet. No paragraphs, and no facts that aren't on the sheet.
3. **Keep the page order.** All the cards first, then the fill-in-the-blanks, then the answer sheet at the end.
4. **Work for every subject.** The rules must work for any ICSE Class 8 subject without being told which one. Add no topic-specific rules (no "water cycle" or "city" special cases).
5. **Never weaken a test.** Run the tests before and after every change, and never delete or weaken a test to make it pass.
6. **Small steps.** One rule per change, then check the output on the real sheets before the next change.

## How to check a change

```bash
pytest -q                 # all tests must pass
ruff check .              # lint
ruff format --check .     # formatting
```

The tests are in `tests/test_teaching_print.py`, `tests/test_teaching_sheet.py` and `tests/test_teaching_engine.py`. The sample sheets are in `cards/sample/`.

To see the cards for one sheet:

```bash
python - <<'EOF'
from learn.extraction import extract
from learn.teaching_engine import extract_facts
from learn.teaching_engine.sheet import read_sheet
from learn.teaching_engine.cards import plan_cards

pdf = open("cards/sample/history-sheet.pdf", "rb").read()
for card in plan_cards(read_sheet(extract_facts(extract(pdf).units), pdf)):
    print(f"[{card.kind}] {card.question} | {card.clue} -> {card.answer}")
EOF
```

## Testing on many sheets at once

To see how the engine does on a whole folder of PDFs (hundreds or thousands), without changing it:

```bash
python -m learn.teaching_engine.batch_report path/to/sheets --out card_report
```

It reads every PDF in the folder and its subfolders, offline and with no AI. It writes:

- `card_report/summary.md`: totals, the most common problems, and the worst 20 sheets
- `card_report/sheets.csv`: one row per PDF, with card counts, flags, time taken and any error
- `card_report/cards.csv`: every card with its flags, to open in Excel and filter

Flags mark likely problems: `vague` ("What is this about?"), `title_answer`, `long_answer`, `fragment` and `repeat`. They check a card's shape only, so read a sample of flagged and unflagged cards by eye. Keep the PDFs out of the repo.

## The safest way to improve it: real sheets as tests

Every rule change helps one sheet and can quietly hurt another. To stop that:

1. Add real sheets to `cards/sample/`.
2. For each one, write a test listing the exact cards you want: question, clue, answer.
3. A change is only accepted if all those tests still pass.

Once that's in place, any AI can try improvements, and the tests reject the ones that break cards you've already approved.

## Prompt to give another AI tool

> You are improving the rule-based study-card engine in this repository. Read `docs/ENGINE_GUIDE.md` and `CLAUDE.md` first and follow their rules exactly. The engine is in `learn/teaching_engine/cards.py` (questions), `sheet.py` (reading the PDF) and `facts.py` (sentences). Do not use AI or network calls in the engine. Do not edit `learn/templates/teaching_upload.html.j2`. Every card must have one short answer copied word-for-word from the sheet. Keep the page order: all cards, then fill-in-the-blanks, then the answer sheet. Make one small change at a time, run `pytest -q`, `ruff check .` and `ruff format --check .`, and show me the cards for each sample sheet in `cards/sample/` before and after. Never delete or weaken a test. The change I want is: <describe it here>.
