# Question Quality Specification (Key Facts Mode)

## Scope

- **Applies ONLY to Key Facts mode.** Detective, Superhero, and Study modes must not change.
- **No AI at all.** Everything is rule-based with provider `"deterministic"` and no AI prompts or external LLM calls.
- **Coverage for Key Facts (replaces Rule A):** Only what the sheet marks to learn gets a card:
  - Bold words (`**term**` or `__term__` or `<b>term</b>` -> answers)
  - Bold words printed as one list (one shared card)
  - All-bold sentences
  - Bullet and numbered points
  - Headings, tables, pictures, unanswered questions, practice Q&A sections, and other unmarked prose get none.
  - A sheet that marks nothing gets the usual cards with a note (`"note": "Sheet contains no explicit learning markers (bold/bullets/numbered points); generated fallback cards from prose."`).
- **Variety (replaces Rule B):** Cards follow reading order; no two cards test the same fact. Key Facts cards are fill-in-the-blank (`______`); do not force why/how mixes.

---

## Target Style

Key Facts cards use clean fill-in-the-blank sentences or concise factual prompts where the blanked span is a single complete key fact copied word-for-word from the sheet:

```text
"Dr. B. R. Ambedkar chaired the ______ of the Constituent Assembly of India." -> "Drafting Committee"
```

Formula lines blank a single symbol or the result, never a paragraph answer:

```text
"F = ______" -> "ma"
```

---

## Clear and Complete (Enforced in Code & Rubric)

1. **No headings or section labels inside a question:**
   - Rejects questions/clues containing section headers, banner bars, or label prefixes such as:
     - `"1. QUICK REVISION NOTES"`
     - `"CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN"`
     - `"RBS HQ"`
2. **Grammatical question or fill-the-gap sentence:**
   - Never stuff a sentence fragment or verb phrase into a boilerplate template slot (e.g., `"Explain ... and its main features."`).
   - If a grammatical wh-question cannot be formed cleanly, use a fill-the-gap card (`______`) on the sheet's own sentence.
3. **Answer is a complete unit:**
   - Never ends on dangling prepositions, articles, or conjunctions (`of`, `the`, `in`, `and`, `at`, `to`, `for`, `from`, `with`, `by`, `or`).
   - Never starts with `at` or `the`.
   - Never joins words from two table cells.
   - Rejected examples: `"Drafting Committee of the"`, `"Brahmo Sabha in"`, `"Mumbai Key Leaders"`.
4. **Blank only a key fact (bold words first):**
   - Blank only a name, date, year, number with unit, or taught term (prioritizing **bold** words first).
   - Never blank a common word, imperative verb, or filler phrase (`"If"`, `"Repeat"`, `"Make"`, `"Wear"`, `"and why"`, `"law"`, `"included"`).
5. **Skip Practice Questions & Answer Key sections:**
   - Skip everything under `"Practice Questions"` or `"Answer Key"` headings.
   - Skip and reject any line or card containing `"Q1."` or `"— Ans:"` (as well as `"Q1:"`, `"Ans:"`, memory tips, and source credits like `"(Britannica)"`).
6. **Formula lines:**
   - Blank one symbol or the RHS result (e.g., `"F = ______"` -> `"ma"`), never a paragraph answer.

---

## Seven Rule-Based Criteria (`score_card(card, sheet)`)

Each candidate card is scored `1`–`5` on seven deterministic criteria:

1. **`grounded`**: The answer appears word-for-word on the sheet.
2. **`short_answer`**: A complete unit (1–5 words) that is a key fact (name, date, year, number with unit, formula symbol/result, or taught term)—never starting with `at`/`the`, never ending on `of`/`the`/`in`/`and`/`at`, and never a common word (`"If"`, `"Repeat"`, `"Make"`, `"Wear"`, `"and why"`, `"law"`, `"included"`).
3. **`clear_question`**: Grammatical fill-in-the-blank (`______`) or question (`?`) with no headings/section labels (`"1. QUICK REVISION NOTES"`, `"CHEMISTRY • BALANCED EQUATIONS • DATA • EXPERIMENT DESIGN"`, `"RBS HQ"`), no boilerplate templates, and no cut-off proper nouns (`"Man Planning Commission"`). Formula cards blank one symbol or result (`"F = ______"` -> `"ma"`), never a paragraph.
4. **`names_subject`**: The clue identifies who or what it is about without leaking the answer.
5. **`not_furniture`**: Neither clue nor answer comes from `"Practice Questions"` / `"Answer Key"` sections, lines with `"Q1."` or `"— Ans:"`, memory tips, source credits (`"(Britannica)"`), or page/card labels (`"FULL CARD"`).
6. **`not_table_soup`**: Neither answer nor clue joins words across two or more table cells (e.g., `"Mumbai Key Leaders"` or pipe-separated rows).
7. **`distinct`**: Reading order preserved; no two cards test the same fact or near-duplicate clue.
