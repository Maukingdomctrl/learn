# Home page sample

The home page shows these files so a parent can see what Learn prints before uploading anything.

- `example-sheet.pdf` is a one-page study sheet written for Learn ("How green plants make food"). It is not taken from a textbook or a school's sheet, so it can be shown publicly. It was laid out with `build()` from `cards/test/fixtures/make_sample.py`.
- `case-papers.pdf` is real output: Detective case papers that the card model wrote from that sheet on 2026-10-23, with
  `LEARN_PROVIDER=june python -m learn.teaching_engine learn/teaching_engine/sample/example-sheet.pdf --case-papers case-papers.pdf --ai`.
  The model was `google/gemini-3.8-flash` through June. It made one call, and all 8 cards passed `check_card`.

To refresh the sample after the case-paper design changes, run the same command and replace `case-papers.pdf`. `tests/test_teaching_web.py` checks that every answer in it is a line of the example sheet.
