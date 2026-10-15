# Learn — Core Teaching Methodology (Final, Version 1)

**Status:** Implementation baseline for the first working version. This document replaces `core_teaching_methodology.md`, `_v1.md`, `_v1_1.md` and `_v1_2.md` for build purposes; those files are kept for history only.
**Testing status:** Not yet tested in a working product or with children. Every number marked *provisional* in Section 10 is a starting value to be tuned during pilot testing.

---

## 1. Scope

### 1.1 What Version 1 does
A parent uploads one curriculum PDF and selects the child's Standard (7 or 8). Learn produces:

1. **Student lesson:** exactly **2 landscape A4 pages** (297 × 210 mm), completed with a pencil only, in about **15 minutes**.
2. **Parent answer key:** a separate document of **1–2 landscape A4 pages**.

The child uses no screen. The lesson teaches **one concept, or a small set of closely related concepts**, to a child meeting the material **for the first time**.

### 1.2 Target learner
- Standards 7–8 (ages approximately 12–14).
- Fluent reader; can follow multi-step procedures and write 1–2 sentence explanations.
- No prior knowledge of the target concept is assumed.

### 1.3 Out of scope for Version 1
Student profiles, adaptive or follow-up lessons, automatic difficulty progression, uploading or grading student work, other Standards, multiple PDFs per lesson, colour printing, and any activity needing tools other than a pencil (an eraser is fine).

### 1.4 What the lesson does and does not claim
The lesson aims for **initial understanding and guided first practice**. Neither the student pages nor the answer key may claim the lesson guarantees mastery, exam readiness, or long-term retention.

---

## 2. Generation Pipeline

| Step | What happens | Stops with a report if… |
| :--- | :--- | :--- |
| 1. Input | Parent uploads a PDF, selects Standard 7 or 8 (required), and may optionally name a topic or page range. | No PDF, or no Standard selected. |
| 2. Extract | Extract text from every page (OCR for scanned pages). Split it into numbered **source units** `SRC-P{page}-U{n}` (a paragraph, worked example, table, definition box, or figure caption). Record figures and what they show where this can be determined. | No usable text is recovered from the PDF. |
| 3. Check sufficiency | Apply the sufficiency test (Section 3.3) to the candidate concept. | The test fails (Section 3.4). |
| 4. Select scope | Choose the concept(s) to teach (Section 3.2). | — |
| 5. Plan | Generate the lesson as structured data (Section 9): stages, items, answer key, source citations. | — |
| 6. Estimate time | Compute the timing model (Section 6). Adjust if outside limits (Section 6.4). | Cannot reach the time window without inventing content (Section 6.4). |
| 7. Render | Render student pages and answer key from HTML/CSS to PDF using a fixed template (Section 7). | — |
| 8. Validate | Run every check in Section 8 on the rendered output. | — |
| 9. Repair | Fix failures, then **re-render and re-run all checks**. Maximum **2 repair rounds**. | Any check still fails after round 2. |
| 10. Deliver | Deliver both PDFs to the parent. | — |

Whenever generation stops, the parent receives a short **limitation report**: what failed, in plain language, and what they can do (for example, "upload the pages that explain this topic" or "this page is unreadable, please rescan it"). Partial or unvalidated lessons are never delivered.

---

## 3. Source Grounding

### 3.1 Grounding rules
1. **Every fact, definition, formula, rule, date, classification and technical term** taught or tested must be supported by one or more source units, recorded in the lesson data as `source_unit_ids`.
2. **Every answer** in the answer key must be derivable from the source, either directly or by applying a method the source teaches.
3. **Allowed generated content (scaffolding):**
   - Hooks, explanations re-worded for the age group, and step-by-step breakdowns of source methods.
   - New practice values or scenarios, **provided they apply exactly the method or rule the source teaches** and use numbers no harder than the source's own examples (for example, no decimals if the source uses only whole numbers).
   - Everyday analogies, marked `is_analogy: true` and introduced with words such as "Think of it like…". An analogy is **never tested** as if it were a curriculum fact.
4. **Not allowed:** facts, terms, methods, formulas or examples from outside the source, even if correct. If a standard term is missing from the source, do not introduce it.
5. **Apparent source errors:** if the source appears to contain a factual or arithmetic error, do not silently correct it and do not teach it. Leave that point out of the lesson and note it in the answer key ("The source on page 4 states X; this looks incorrect, so it was not included").

### 3.2 Choosing what to teach
1. If the parent named a topic or page range, use it.
2. Otherwise choose the **first teachable concept in document order** that passes the sufficiency test. Prefer a foundational concept over one that depends on earlier material.
3. Teach **1 concept, or at most 3 closely related sub-concepts** (for example, "acute, right and obtuse angles"). If the selected material contains more than fits the time window, narrow it and state on the answer key what was covered and what was left for another lesson.

### 3.3 Sufficiency test
A concept is teachable only if the source provides all of the following:
- (a) an explanation or definition of the concept (not just a mention, heading, or review question);
- (b) enough information to produce correct answers for **at least 7 scored items** without outside knowledge;
- (c) for a procedure (for example, a calculation method), the steps of the method or a worked example from which the steps are clear.

### 3.4 When the source is insufficient or unclear
Stop and report instead of filling gaps. Report when:
- the concept is mentioned but not explained (test 3.3a fails);
- the explanation depends on pages or figures that are missing or unreadable;
- the source is self-contradictory on a point the lesson would need;
- the only way to reach the minimum item count or time window is to add outside content.

If the source supports a smaller lesson than intended, follow Section 6.4, Rule S.

---

## 4. Lesson Structure

### 4.1 Five stages, fixed order
Every lesson has five stages, completed in this order. Support fades from full modelling to no help.

| # | Stage | Page and position | Purpose | Support | Scored items |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | **Discover** | Page 1, left column | Hook, clear explanation, and **one complete worked example** (or annotated model for a non-procedural concept). The child makes 1–2 simple marks that check they noticed the key idea. | Full: everything is shown. | 1–2 |
| 2 | **Reinforce** | Page 1, right column | Guided practice on the core idea. | High: word bank, matching, partly-done steps, or done-for-you example. | 2–4 |
| 3 | **Vary** | Page 2, top left | The same idea in a different format: new values, reversed direction, a new case, or spotting a peer's mistake. | Moderate: a hint pointer to Page 1 (Section 5.3). | 2–3 |
| 4 | **Apply** | Page 2, top right | Independent practice: solve a problem or explain a new situation. | Low: structured workspace, pre-printed units or sentence stem; no word bank; one hint pointer. | 1–2 |
| 5 | **Recall** | Page 2, bottom right, in a boxed area | Retrieve the main idea from memory. | None. Banner: **"Turn Page 1 face down before you start this box."** | 1–2 |
| | **Total** | | | | **7–13** |

**Item definition:** one **scored item** is one answer the parent can mark right or wrong and that has its own answer-key entry (one blank, one matching line, one multiple-choice question, one problem's final answer, one short written response). Done-for-you examples are not scored items.

**Numbering:** scored items are numbered 1, 2, 3… continuously across both pages. Done-for-you examples are labelled "Ex" and not numbered.

### 4.2 Stage rules
1. **Discover**
   - Opens with a short hook: a question or puzzle from a situation a 12–14-year-old recognises, which the lesson then answers.
   - The child's first pencil mark comes within the first **65 words** of the lesson (for example, circling a prediction or a feature in a picture).
   - Includes one complete worked example or model taken from, or directly following, the source.
   - Uses a diagram, table or labelled picture **only when it carries teaching content**. Labels sit next to the feature they name.
2. **Reinforce** — the first item should be answerable by almost every child who read Discover.
3. **Vary** — must not be the same task as Reinforce with only the numbers changed. Change the format, the direction (for example, given the answer, find the input), or the case.
4. **Apply** — uses a context the child has not seen in Discover. For a procedural topic, the child performs the full method. For a conceptual topic, the child explains or uses the idea in a new situation.
5. **Recall** — asks for the main rule, definition or method in the child's own words or as a fresh short problem. It must not be answerable by copying a sentence from Page 2.

### 4.3 Printing and Recall isolation
The answer key tells the parent to **print single-sided** so Page 1 can be turned face down before Recall.

---

## 5. Activity Design Rules

### 5.1 Approved activity types
Every stage uses exactly one activity type from this list.

| Type | What the child does | Allowed stages | Done-for-you example (`Ex`) | Rules |
| :--- | :--- | :--- | :--- | :--- |
| `ANNOTATE` | Circle, underline or tick features in a picture, example or pair of cases. | Discover, Reinforce, Vary | Not needed (action verb in bold). | When scored outside Discover: at least 3 possible targets. |
| `CHOOSE` | Multiple choice. | Discover, Reinforce, Vary | Not needed. | 3–4 options, exactly one correct. No "all of the above" / "none of the above". |
| `MATCH` | Draw lines from column A to column B. | Reinforce, Vary | Required: 1 pre-drawn line. | Options ≥ prompts + 1. Max 4 scored prompts. |
| `FILL_IN` | Fill blanks in sentences, a table or diagram labels. | Reinforce, Vary, Apply | Required: 1 filled blank. | With a word bank: bank size ≥ blanks + 1. No word bank in Apply. |
| `SORT` | Sort 3–6 items into 2–3 labelled groups. | Reinforce, Vary | Required: 1 item pre-sorted. | Child may write letter codes instead of words. |
| `COMPLETE_STEPS` | Fill missing steps in a worked procedure. | Discover, Reinforce, Apply | Required: Step 1 shown done. | Pre-print operators and units in blanks. |
| `SPOT_MISTAKE` | Find and fix a mistake in a fictional peer's work. | Vary, Apply | Not needed. | Third person ("Ravi solved this and made one mistake…"). Exactly one mistake. Child circles it and writes the correction. |
| `SOLVE` | Solve a problem in a provided workspace. | Apply, Recall | Not needed. | Structured workspace; pre-printed units in the final answer blank. |
| `SHORT_ANSWER` | Write 1–2 sentences. | Apply, Recall | Not needed. | Ruled lines. In Recall, may give a short keyword checklist ("Use: ☐ term1 ☐ term2"). |
| `SKETCH` | Draw a simple labelled sketch, bar model or arrows in a pre-drawn box. | Apply, Recall | Pre-drawn frame. | Countable criteria ("Draw 3 arrows that show…"). Drawing skill is never assessed. |

Done-for-you examples are printed in grey and clearly labelled "Ex — done for you".

### 5.2 Variety
- The lesson uses **at least 3 different activity types**.
- **Consecutive stages may not use the same activity type.**

### 5.3 Clarity and readability (measurable)
| Rule | Limit |
| :--- | :--- |
| Words in any single instruction sentence | ≤ 22 |
| Actions per instruction sentence | ≤ 2 (for example, "Circle… and write…") |
| Words in any other student-facing sentence | ≤ 25 |
| Words before the first pencil mark | ≤ 65 |
| Continuous reading between pencil marks | ≤ 120 words |
| Total words the child is expected to write (from the answer key) | ≤ 65 |

Additional rules:
- Instructions use direct verb-first phrasing ("Draw a line from each term to its meaning").
- Every technical term used in Reinforce, Vary, Apply or Recall is explained in Discover.
- Vary and Apply each include one hint pointer to the relevant part of Page 1 ("Stuck? Look at the worked example on Page 1"). Recall has no hint.
- Pre-print units in numeric answer blanks (`______ cm`).

### 5.4 Engagement without decoration
- Engagement comes from the hook, realistic contexts, variety of activity types, and the peer-mistake format, **not** from clip art, cartoons, themes or borders.
- No word searches, crosswords, anagrams, mazes, colouring, or other tasks that do not practise the concept.
- No trick questions with negative stems ("Which is NOT…", "All of these EXCEPT…"). Negation inside normal content is fine.
- No timers, scores, point boxes, rewards, or labels such as "Easy!".
- Questions must require understanding, not copying a visible sentence. A fill-in-the-blank that repeats a Discover sentence word for word is not allowed.
- Items within a stage must differ meaningfully (different case, value or angle), not be near-duplicates.

---

## 6. Timing Model

All timing is computed **in seconds**. Minutes appear only for display (seconds ÷ 60).

### 6.1 Formula
For each stage *k* (Discover, Reinforce, Vary, Apply, Recall):

```
T_block(k) = T_read(k) + T_visual(k) + T_items(k) + T_write(k)

T_read(k)   = printed_words(k) / 110 words per min × 60      (= 0.545 s per word)
T_visual(k) = visuals(k) × 30 s
T_items(k)  = scored_items(k) × w(stage)  +  sketch_items(k) × 20 s
T_write(k)  = written_words(k) / 17 words per min × 60       (= 3.53 s per word)

T_stages = sum of T_block over the 5 stages
T_lesson = 60 s (orientation) + T_stages
```

Item weights `w(stage)`: Discover 15 s, Reinforce 25 s, Vary 35 s, Apply 55 s, Recall 45 s.

### 6.2 What each term counts (avoids double counting)
Each piece of student activity is counted **in exactly one term**:

| Term | Counts | Does not count |
| :--- | :--- | :--- |
| Orientation (60 s, fixed) | Reading the title and scope line, turning pages, turning Page 1 face down. | Anything inside a stage. |
| `T_read` | All printed student-facing words in the stage: instructions, explanation, worked-example text, item prompts, options, word banks, done-for-you examples. A number or a symbolic expression counts as 1 word. | Words inside a diagram or table (covered by `T_visual`); the page title and scope line (covered by orientation). |
| `T_visual` | Each diagram, table or labelled picture, including reading the words inside it. | A worked example written as lines of text (counted in `T_read`). |
| `T_items` | Thinking time plus simple marks: circling, ticking, drawing a matching line, writing a single letter, or writing a single number. | Writing words or multi-number answers (counted in `T_write`). |
| Sketch add-on (20 s) | Extra drawing time for each `SKETCH` item, counted **once**, here only. | — |
| `T_write` | Words the child is expected to write, taken from the length of the answer-key answer. Each number or equation step counts as 1 word. A single letter, single number, tick, circle or line counts as 0 here because it is already in `T_items`. | Anything already counted above. |

### 6.3 Limits
| Limit | Value |
| :--- | :--- |
| Total lesson time `T_lesson` | **780–990 s (13.0–16.5 min)**, target 900 s (15.0 min) |
| Each Discover, Reinforce, Vary, Recall block | ≤ 210 s (3.5 min) |
| Apply block | ≤ 270 s (4.5 min) |
| Written words (whole lesson) | ≤ 65 (≈ 229 s of writing at 17 words per min) |

### 6.4 Adjusting when outside the limits
Adjust in this order, then re-render and re-run **all** checks (Section 8.3). Never delete items blindly.

**Too long (`T_lesson` > 990 s, a block over its cap, or the pages overflow):**
1. Shorten prose (explanation, story context, instructions) without removing taught content.
2. In Reinforce or Vary, replace a written-answer item with a low-writing type (`MATCH`, `CHOOSE`, `SORT`).
3. Remove an item that tests the same thing as another item in the same stage. Never go below a stage's minimum item count, and keep at least one item for each taught sub-concept.
4. Narrow the scope to fewer sub-concepts and state this on the answer key.

**Too short (`T_lesson` < 780 s):**
1. Add a grounded item to Vary or Apply (within the stage maximum), testing a different case.
2. Add a grounded item to Reinforce (within the stage maximum).
3. Replace a recognition item (`CHOOSE`, `ANNOTATE`) in Reinforce or Vary with a more active type (`FILL_IN`, `COMPLETE_STEPS`, `SPOT_MISTAKE`).
   Never pad with filler text or decorative tasks.

**Rule S (source too thin):** if the lesson is still under 780 s only because the source does not support more grounded items, deliver it if `T_lesson` ≥ 600 s (10 min) and all other checks pass, and state at the top of the answer key: "This lesson is about N minutes, shorter than usual, because the uploaded material covers a limited amount on this topic." Below 600 s, stop and send a limitation report.

### 6.5 Worked example (arithmetic verified)
A Standard 7 lesson, 12 scored items:

| Stage | Printed words → `T_read` | Visuals → `T_visual` | Items × weight → `T_items` | Written words → `T_write` | `T_block` |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Discover | 165 → 165/110×60 = 90.0 s | 1 → 30 s | 2 × 15 = 30 s | 0 → 0.0 s | **150.0 s** |
| Reinforce | 88 → 48.0 s | 0 → 0 s | 4 × 25 = 100 s | 0 → 0.0 s | **148.0 s** |
| Vary | 55 → 30.0 s | 0 → 0 s | 2 × 35 = 70 s | 8 → 8/17×60 = 28.2 s | **128.2 s** |
| Apply | 77 → 42.0 s | 1 → 30 s | 2 × 55 = 110 s | 16 → 56.5 s | **238.5 s** |
| Recall | 33 → 18.0 s | 0 → 0 s | 2 × 45 = 90 s | 20 → 70.6 s | **178.6 s** |

- `T_stages` = 150.0 + 148.0 + 128.2 + 238.5 + 178.6 = **843.3 s**
- `T_lesson` = 60 + 843.3 = **903.3 s = 15.06 min** → inside 780–990 s ✔
- Block caps: Discover, Reinforce, Vary, Recall all ≤ 210 s ✔; Apply 238.5 s ≤ 270 s ✔
- Written words: 0 + 0 + 8 + 16 + 20 = **44** ≤ 65 ✔
- Items: 2 + 4 + 2 + 2 + 2 = **12**, within 7–13 and within each stage's range ✔

(Values are rounded to 0.1 s for display; the totals above match the sum of the displayed values.)

---

## 7. Print Layout

### 7.1 Student pages (fixed template)
- **Page 1:** title line and one-line scope ("Today: how to find the area of a triangle"); left column = Discover; right column = Reinforce.
- **Page 2:** top left = Vary; top right = Apply; bottom right = Recall box with its "Turn Page 1 face down" banner. The child's name/date line may go top right of Page 1.
- Landscape A4, 297 × 210 mm, **exactly 2 pages**.

### 7.2 Measurable layout rules
| Rule | Value |
| :--- | :--- |
| Page margins | ≥ 12 mm on all sides |
| Body text size | ≥ 10.5 pt |
| Ruled write-in line height | ≥ 7.5 mm |
| Written-answer space | at least 1 ruled line per 8 expected written words, plus 1 spare line; lines ≥ 80 mm long |
| Numeric answer blank | ≥ 25 mm wide |
| Workspace for `SOLVE` | ≥ 35 mm high per problem |
| Text clipping or overflow | none |
| Colour | none required: everything must be readable in black and white; use labels, line styles or patterns instead of colour; no instruction refers to colour |

### 7.3 Parent answer key (separate PDF, 1–2 landscape A4 pages)
1. **Header:** lesson title, Standard, concept(s) covered, source pages used, estimated time.
2. **Before you start (3–4 short bullets):** print single-sided; the child works alone for about 15 minutes; Page 1 is turned face down before the Recall box; check answers together afterwards.
3. **Answers**, one row per scored item, numbered to match the student pages:
   - correct answer;
   - accepted alternatives (for written answers: the key points that must be present);
   - one-sentence reason it is correct;
   - source page reference ("Source: p. 3").
4. **Scope and limitations:** what was covered, what in the selected material was not covered, any apparent source errors that were left out (Section 3.1.5), and Rule S's shortened-lesson note if it applies.
5. A one-line reminder that one lesson builds initial understanding, not mastery.

---

## 8. Validation

Validation runs on the **rendered** output. A lesson is delivered only when every check passes.

### 8.1 Deterministic checks (code)
| ID | Check | Pass condition |
| :--- | :--- | :--- |
| D1 | Structure | 5 stages in the order of Section 4.1; item counts within each stage's range; total 7–13; Discover contains a worked example or model; Standard is 7 or 8. |
| D2 | Citations | Every core claim, technical term and answer-key entry has ≥ 1 `source_unit_id` that exists in the extracted source. |
| D3 | Activity rules | Each stage's type is allowed for that stage (Section 5.1); ≥ 3 distinct types; no two consecutive stages share a type; `Ex` present where required; options ≥ prompts + 1 for `MATCH` and word-bank `FILL_IN`; `CHOOSE` has 3–4 options with exactly one marked correct; scored `ANNOTATE` outside Discover has ≥ 3 targets. |
| D4 | Text limits | All limits in Section 5.3; no banned patterns (score boxes, timers, "NOT"/"EXCEPT" as a capitalised question stem, word search, crossword). |
| D5 | Timing | Section 6 formula computed; all limits in Section 6.3 met (or Rule S applied and noted in the key). |
| D6 | Layout | Student PDF is exactly 2 pages, answer key 1–2 pages, all landscape A4; no overflow or clipping in the rendered HTML; all Section 7.2 measurements met; Recall box and banner on Page 2; hint pointers present in Vary and Apply. |
| D7 | Answer-key completeness and arithmetic | Every scored item has exactly one key entry with an answer, a reason, and a source page; numbering matches the student pages. For numeric answers, the key stores the calculation (for example `0.5 * 8 * 5`) and code recomputes it; the result must equal the stated answer. |

### 8.2 AI-assisted checks (separate model calls)
AI checks are fallible filters, not proof of quality. Each runs as a separate call with only the inputs listed.

| ID | Check | Inputs | Pass condition |
| :--- | :--- | :--- | :--- |
| A1 | Grounding and factual correctness | Lesson content, answer key, cited source units | Every taught claim and every answer is supported by its cited units; practice items use the source's method; no outside facts or terms; no analogy is tested; nothing contradicts the source. |
| A2 | Blind solve | **Student pages only** (rendered text and images). No answer key, no source. | The solver answers every item **using only the student pages** and flags any item that is ambiguous, has more than one defensible answer, or needs knowledge not on the pages. Pass = zero flags. |
| A3 | Key agreement | A2's answers, the answer key, cited source units | Every A2 answer matches the key's answer or accepted alternatives. Any mismatch is resolved by fixing the item or the key, whichever is wrong, then re-checking. |
| A4 | Clarity and age fit | Student pages | Instructions are clear without adult help; no unexplained technical terms; language suits ages 12–14; hook is relevant and answered by the lesson; no trick questions; no copy-the-sentence items; items within a stage differ meaningfully; support fades across stages; tone is neutral and respectful. |

Note on A2: a model may already know the topic and answer from outside knowledge. Its prompt must instruct it to flag any item it could not answer from the pages alone.

### 8.3 Repair and revalidation
1. On any failure, apply a targeted fix (Section 6.4 for timing or layout; otherwise rewrite the failing item, text or key entry).
2. After **every** fix: re-render and re-run **all** D and A checks. A fix is never assumed to have worked.
3. At most **2 repair rounds**. If anything still fails, stop and send a limitation report to the parent; log the failing check IDs and items for the team.

### 8.4 Pilot calibration (team activity, not a per-lesson gate)
Before relying on the timing numbers, the team should:
- Time a sample of Standard 7–8 children completing printed lessons; compare actual times with `T_lesson` and adjust the provisional values in Section 10.
- Note where children hesitate or ask what to do, and revise the template or instructions.
- Print sample lessons on ordinary home black-and-white printers and complete them by hand.
- Have a parent or teacher review a sample of answer keys for correctness and usability.

---

## 9. Lesson Data (minimum fields)
The generator produces structured data; the renderer and checks read only this data plus the extracted source.

```
lesson:
  standard: 7 | 8
  title, scope_line
  concepts: [ { name, source_unit_ids } ]
  core_claims: [ { text, source_unit_ids, is_analogy } ]
  terms: [ { term, definition, source_unit_ids } ]
  stages: [            # exactly 5, in order
    { stage: Discover|Reinforce|Vary|Apply|Recall,
      activity_type, instruction, body_text, visuals: [ ... ],
      example: { ... } | null,          # done-for-you Ex, not scored
      hint_pointer: text | null,
      items: [ { number, prompt, options?, unit?, expected_written_words, is_sketch } ] }
  ]
answer_key:
  entries: [ { item_number, answer, accepted_alternatives, reason,
               calculation?, source_unit_ids, source_page } ]
  scope_covered, not_covered, source_issues, shortened_lesson_note?
timing: { per_stage: [...], T_stages, T_lesson }   # computed by code, not by the model
```

---

## 10. Provisional Parameters (tune after pilot)
All values below are starting estimates for Standards 7–8 and have not been measured with children.

| Parameter | Value |
| :--- | :--- |
| Reading speed | 110 words/min |
| Writing speed | 17 words/min |
| Orientation | 60 s |
| Visual inspection | 30 s per diagram/table |
| Item weights | Discover 15 s, Reinforce 25 s, Vary 35 s, Apply 55 s, Recall 45 s |
| Sketch add-on | 20 s per `SKETCH` item |
| Time window | 780–990 s; target 900 s; Rule S floor 600 s |
| Block caps | 210 s (Apply 270 s) |
| Written words | ≤ 65 |
| Text limits | Section 5.3 |
| Layout values | Section 7.2 |
| Repair rounds | 2 |
