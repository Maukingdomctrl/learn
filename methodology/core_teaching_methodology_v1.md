# Core Teaching Methodology Specification — Version 1 (`CORE_TEACHING_METHODOLOGY_V1.md`)

**Document Status:** Version 1.0 — Practical, Internally Consistent Engineering & Pedagogical Specification  
**Target Medium:** Printed Landscape A4 Pages ($297\text{ mm} \times 210\text{ mm}$) + Standard Graphite Pencil (Zero Screen Interaction)  
**Target Duration:** ~15 Minutes per Single-Session Lesson (Accepted Engineering Corridor: $13.0\text{ to }16.5\text{ minutes}$)  
**Learner Context:** Real-World Children in First-Time Exposure to Supplied Curriculum Material (Stateless; No Student Profiles, Uploaded Responses, or Adaptive Follow-Up)

## 1. Version History & Revision Summary

| Version | Date | Scope of Changes |
| :--- | :--- | :--- |
| **v0.1** | 2026-10-15 | Initial draft of the 12 core teaching principles, 5-stage progression, paper-based activity taxonomy, behavioral timing formula, failure catalog, and pre-acceptance checklist. |
| **v0.2** | 2026-10-15 | Added real-world child robustness mechanisms (confusion, boredom, frustration, careless mistakes, overload) and automated vs. human review tiers. |
| **v1.0 (Current)** | 2026-10-15 | **Version 1 Consolidation & Contradiction Resolution:**<br>1. **Resolved Timing Contradictions:** Unified stage durations, fixed orientation time ($1.0\text{ min}$), capped single-stage duration at $\le 4.0\text{ min}$, unified grade-band reading/handwriting speeds, and aligned active cognitive time shares ($35\%\text{–}45\%$ for *Apply + Recall*) with the $13.0\text{–}16.5\text{ minute}$ acceptance corridor.<br>2. **Resolved Count & Span Conflicts:** Standardized on 5–6 activity blocks per lesson (1 per stage, or 6 for chunked taxonomy lessons), 8–15 total scored student actions, unified passive reading ceilings ($45 / 80 / 120\text{ words}$), and unified handwriting caps ($15 / 40 / 75\text{ words}$).<br>3. **Resolved Progression vs. Adaptation Conflicts:** Defined how scaffolding fades across all four subject-specific sequence variants without contradicting the 5-stage requirement.<br>4. **Resolved Page Budget vs. Recall Isolation Conflicts:** Standardized Student Output on a fixed **2-Page Landscape A4 layout** (Page 1: *Discover & Reinforce*; Page 2: *Vary, Apply & Recall*) plus a separate **Page 3 Parent Answer Key**, eliminating fragile paper-folding mechanics and ensuring *Recall* is physically separated from *Discover* in both duplex and single-sided printing.<br>5. **Simplified V1 Verification Architecture:** Replaced over-engineered multi-agent/DAG/pixel-sliding-window systems with an implementable 3-tier pipeline (**A. Deterministic Software Checks**, **B. AI-Assisted Quality Checks**, **C. Human Validation**) with explicit pass/fail criteria and a bounded 2-retry policy. |

## 2. Revised Epistemic Framework & Non-Guarantee Contract

### 2.1 Three-Tier Governance Classification
Not every educational theory is a universal law, and not every numerical threshold in this document is proven science. To guide engineering and instructional design honestly, every requirement in Version 1 carries one of three explicit classifications:

| Classification Tag | Definition | Examples in Version 1 | Governance Rule |
| :--- | :--- | :--- | :--- |
| **`[Evidence-Informed Principle]`** | Instructional design principles supported by cognitive psychology and classroom research, recognizing that effectiveness still depends on learner age, prior knowledge, and subject domain. | Working memory constraints (Cognitive Load Theory), pairing visuals with concise text (Dual Coding), fading worked examples for novices, active retrieval practice over passive re-reading, and variation of surface features. | **Guides pedagogical design.** Must be preserved in the lesson structure, while adapting implementation details to the subject and grade band. |
| **`[Mandatory V1 Product Constraint]`** | Fixed product-definition, safety, and architectural boundaries established for Version 1 of this product. | Landscape A4 print format, graphite pencil only, zero external tools or screens, stateless operation (no student profiles), source-grounded content, separate answer key, and honest non-guarantee framing. | **Strict V1 engineering requirement.** Any violation blocks lesson delivery. |
| **`[Provisional V1 Heuristic — Requires Testing]`** | Practical engineering estimates, numerical thresholds, time weights, word caps, and layout dimensions chosen to make Version 1 buildable and testable. | The $13.0\text{–}16.5\text{ minute}$ corridor, grade-band WPM reading/writing speeds, passive reading word caps ($45/80/120\text{ words}$), handwriting caps ($15/40/75\text{ words}$), and $\ge 30\%$ whitespace. | **Tunable configuration parameters.** Enforced as software thresholds in V1, but must be empirically calibrated through observational testing with real children. |

### 2.2 Explicit Non-Guarantee Contract (`[Mandatory V1 Product Constraint]`)
1. **No Guarantee of Mastery:** A single 15-minute worksheet cannot guarantee long-term retention or subject mastery, which require spaced practice, feedback, and consolidation over time. The objective of a Version 1 lesson is **Initial Comprehension and Guided First Application**: helping a child encounter new curriculum material for the first time, understand its core mechanism, and apply it with fading support.
2. **No Guarantee of Engagement:** Real-world children experience fluctuating attention, fatigue, and frustration. This methodology treats **attention as a fragile design constraint** (reducing friction, confusion, and monotony) and **learning as the primary objective**, never claiming that any worksheet format guarantees excitement or focus.
3. **Prohibited Claims:** Student worksheets and parent answer keys must never claim that completing the lesson guarantees mastery, fluency, or exam readiness.

## 3. Core Teaching Rules & Real-World Learner Robustness

Real-world children vary widely in reading fluency, prior knowledge, attention span, fine-motor stamina, and academic confidence. Because Version 1 is stateless (no personal profiles or historical student data), every generated lesson must embed universal scaffolding directly on the page.

### Rule 1: Strict Source Grounding and Transparent Scope Handling
* **Classification:** `[Mandatory V1 Product Constraint]`
* **Requirement:**
  1. All domain facts, definitions, formulas, dates, classifications, and technical terms taught or tested in the lesson must derive from the uploaded curriculum PDF.
  2. The system may generate original instructional scaffolding—such as everyday analogies, step-by-step worked breakdowns, and practice scenarios—provided that analogies are explicitly labeled as comparisons (*"Think of it like..."*) and are never tested as literal curriculum facts in *Apply* or *Recall*.
  3. **Transparent Handling of Missing or Insufficient Information:** If the uploaded PDF is illegible, missing pages, or references undefined concepts without providing enough information to build a coherent 15-minute lesson, the software must either:
     * Restrict the lesson scope strictly to the sub-concepts that *are* fully supported in the PDF and note this scope in the parent header, or
     * Halt generation and return a clear message to the parent explaining which curriculum details are missing or unreadable, rather than inventing facts to fill the gap.
* **Why It Matters:** Inventing unsupported facts or using alternative terminology contradicts classroom instruction and erodes parent trust.
* **How Enforced in V1:** Deterministic check **`DET-02`** (verifies every factual claim node in the lesson JSON cites a valid `source_chunk_id` from the parsed PDF) + AI-assisted check **`AI-01`** (audits claims against cited PDF chunks for unsupported additions or contradictions, and verifies analogies are quarantined from assessment items).

### Rule 2: First-Time Learning and Prerequisite Completeness
* **Classification:** `[Evidence-Informed Principle]` + `[Mandatory V1 Product Constraint]`
* **Requirement:** Assume the child is encountering the target curriculum concept for the first time.
  1. Every domain term, symbol, unit, or multi-step procedure used in Stages 2–5 must either be explicitly introduced and unpacked in Stage 1 (*Discover*) or belong to foundational knowledge at least one full grade band below the target grade.
  2. **Ancillary Skill Buffer:** When teaching a new concept (e.g., science formulas or multi-step math procedures), keep secondary calculations and non-domain vocabulary simple (`Target_Grade - 1` difficulty) so a child does not get stuck on tough arithmetic or vocabulary while trying to learn a new concept.
  3. **Phonetic Support for Complex Terms:** Any newly introduced curriculum term of $\ge 4$ syllables (or non-phonetic scientific/historical root) must include a simple inline pronunciation guide on first mention (e.g., **photosynthesis** *[foh-toh-SIN-thuh-sis]*).
* **Why It Matters:** First-time learners lack expert schemas to bridge unstated steps. Hidden prerequisites trigger immediate confusion and force the child to ask a parent for help.
* **How Enforced in V1:** AI-assisted check **`AI-02`** (scans Stages 2–5 for undefined domain terms, unexplained symbols, or secondary arithmetic/vocabulary that exceeds `Target_Grade - 1` complexity).

### Rule 3: Low-Friction Entry and Self-Explanatory Instructions
* **Classification:** `[Evidence-Informed Principle]` (Extraneous Load Reduction) + `[Provisional V1 Heuristic — Requires Testing]` (Word caps)
* **Requirement:** Make every activity effortless to understand and begin without adult help:
  1. **Action-Object-Location Instruction Syntax:** Write instructions as direct, active imperatives specifying what physical mark to make, on what target, and where (e.g., *"Circle the two magnets that push apart in Box A"*).
  2. **Authoritative Instruction Length & Verb Cap:** Each instruction sentence must contain at most **2 sequential action verbs** and must not exceed:
     * **Grades 1–2:** $\le 12\text{ words}$ per sentence.
     * **Grades 3–5:** $\le 18\text{ words}$ per sentence.
     * **Grades 6+:** $\le 22\text{ words}$ per sentence.
  3. **Mandatory Visual "Worked Start" (`Ex:`):** Every structured activity block (matching, sorting table, diagram labelling, faded step, error-spotting, or logic path) must include a pre-completed example item (`Ex:`) rendered in light grey simulated pencil script so a hesitant reader can see the expected action visually before reading.
* **Why It Matters:** Real-world children often stall not because the concept is too hard, but because convoluted directions obscure what they are supposed to do.
* **How Enforced in V1:** Deterministic checks **`DET-03`** (enforces instruction word-count ceilings and verifies presence of a non-null `worked_start` field on structured activities) + AI-assisted check **`AI-03`** (evaluates instruction clarity, action-verb count, and age-appropriateness).

### Rule 4: Active Pencil Participation and Manageable Reading Spans
* **Classification:** `[Evidence-Informed Principle]` (Generation & Active Encoding) + `[Provisional V1 Heuristic — Requires Testing]` (Word ceilings & 60s threshold)
* **Requirement:** The child must do more than passively read:
  1. **First Pencil Action Within 60 Seconds:** Stage 1 (*Discover*) must require a simple, high-confidence observation mark (e.g., circling a key part of the worked example or tracing an arrow) within the first **$60\text{ seconds}$** of active stage time.
  2. **Authoritative Passive Reading Span Ceiling:** No continuous block of instructional text may exceed the following word ceilings before requiring an explicit pencil action:
     * **Grades 1–2:** Maximum **$45\text{ words}$** per continuous reading block.
     * **Grades 3–5:** Maximum **$80\text{ words}$** per continuous reading block.
     * **Grades 6+:** Maximum **$120\text{ words}$** per continuous reading block.
* **Why It Matters:** Long paragraphs cause short-attention or lower-fluency readers to skim, zone out, or skip straight to guessing answers.
* **How Enforced in V1:** Deterministic check **`DET-04`** (counts words in every continuous text block between student action items and calculates time to first action).

### Rule 5: Robustness Against Confusion, Boredom, Frustration, Careless Mistakes, and Shame
* **Classification:** `[Evidence-Informed Principle]` + `[Mandatory V1 Product Constraint]`
* **Requirement:** Every lesson must incorporate five specific defensive design buffers:
  1. **Anti-Confusion Buffer (Visual Dual-Coding):** In *Discover*, pair concise text with an annotated diagram, sequence strip, or comparison table where labels sit directly adjacent to the visual feature ($\le 15\text{ words}$ per callout label) rather than in a detached legend.
  2. **Anti-Boredom Buffer (Format Variation Without Objective Drift):** Use at least **3 different paper-based activity mechanics** across the lesson (with no two consecutive stages using the exact same mechanic) while keeping $100\%$ of activities aligned to the same core learning objective.
  3. **Anti-Frustration Buffer (Low-Floor Ramp & Inline Hint Pointers):** Design Stage 1 and Stage 2 Item 1 for high first-try success, and include a non-stigmatizing reference pointer in Stages 3 and 4 (e.g., *"Stuck? Look back at Step 1 Box B"*) so a child can recover independently without quitting.
  4. **Anti-Careless-Mistake Buffer:**
     * **Ban Negative-Stem Trap Questions:** Never use multiple-choice or selection prompts framed around negation traps (*"Which of the following is NOT..."* or *"All of these EXCEPT..."*).
     * **Pre-Printed Units & Structured Workspaces:** Always pre-print measurement units inside answer blanks (`___ cm`, `___ seconds`) and provide step-by-step workspace boxes for multi-step calculations so students do not lose marks to forgotten units or misaligned columns.
  5. **Psychological Safety (Zero Shame, Timers, or Manipulative Rewards):**
     * Never print countdown clocks, speed challenges (*"Finish in 15 minutes!"*), point/score boxes (`Score: ___/10`), or judgmental difficulty labels (*"This one is easy!"*) on the student sheets.
     * Frame error-spotting tasks (*Vary*) around a fictional third-person peer (*"Maya solved this problem below, but one step has a mix-up..."*) so the child analyzes mistakes safely without personal embarrassment.
* **Why It Matters:** Children with low confidence shut down when tricked by negative stems, pressured by timers, or shamed by red-pen scoring mechanics.
* **How Enforced in V1:** Deterministic checks **`DET-05`** (scans for banned negative-stem tokens `NOT`/`EXCEPT`, banned timer/score/evaluative terms, and verifies $\ge 3$ distinct activity mechanic types with no adjacent duplicates) + AI-assisted check **`AI-04`** (verifies third-person error framing, supportive tone, and presence of inline reference pointers).

### Rule 6: Genuine Understanding Over Mechanical Copying
* **Classification:** `[Evidence-Informed Principle]` (Retrieval Practice & Transfer) + `[Mandatory V1 Product Constraint]`
* **Requirement:**
  1. **Zero Decorative Games:** Word searches, anagrams, letter-substitution codes, unlabelled mazes, and decorative coloring tasks are strictly banned. Every activity must require processing the curriculum concept to solve.
  2. **Asymmetric Matching & Word Banks:** Every matching activity or word-bank completion task must include **at least 1 plausible distractor option** ($|\text{Options}| \ge |\text{Prompts}| + 1$, or explicitly allow many-to-one reuse) so the final item cannot be solved automatically by process of elimination.
  3. **Anti-Copy Paraphrasing & Physical Recall Isolation:** Questions in *Reinforce*, *Vary*, *Apply*, and *Recall* must never use verbatim fill-in-the-blank sentences lifted from *Discover*. Furthermore, **Stage 5 (*Recall*) must always be placed on Student Page 2** while **Stage 1 (*Discover*) is on Student Page 1**, preventing direct visual copying of definitions.
* **Why It Matters:** A child can fill out a traditional worksheet in 5 minutes by matching sentence shapes and eliminating the last word-bank option without understanding a single concept.
* **How Enforced in V1:** Deterministic checks **`DET-06`** (blocks banned activity enums, verifies $|\text{Options}| \ge |\text{Prompts}| + 1$ in matching/word-bank schemas, verifies Stage 1 is on Page 1 and Stage 5 is on Page 2, and rejects prompts sharing any contiguous $\ge 5$-word exact substring with *Discover* explanations) + AI-assisted check **`AI-05`** (checks that activities require conceptual understanding rather than surface guessing).

### Rule 7: Print-First Autonomy and Landscape A4 Ergonomics
* **Classification:** `[Mandatory V1 Product Constraint]` + `[Provisional V1 Heuristic — Requires Testing]` (Dimensions)
* **Requirement:**
  1. **Pencil-and-Paper Only:** The lesson must require only printed Landscape A4 pages ($297\text{ mm} \times 210\text{ mm}$) and a standard graphite pencil—no scissors, glue, rulers (unless printed on the page edge), colored pencils, dice, screens, or audio.
  2. **Monochrome-Safe Visuals:** All diagrams and visual comparisons must remain clear when printed in black-and-white/greyscale, using distinct patterns (stripes, dots, cross-hatching), line weights, and direct text labels rather than color hue (*"the red circle vs. the green circle"*).
  3. **Grade-Appropriate Handwriting & Workspace Sizing:** Write-in boxes and blanks must provide ruled baseline guides and sufficient physical space for children's handwriting:
     * **Grades 1–2:** Minimum **$12\text{ mm}$** line height; $\ge 14\text{ pt}$ body font.
     * **Grades 3–5:** Minimum **$9\text{ mm}$** line height; $\ge 12\text{ pt}$ body font.
     * **Grades 6+:** Minimum **$7.5\text{ mm}$** line height; $\ge 10.5\text{ pt}$ body font.
     * **Whitespace Floor:** Maintain at least **$30\%$ open background whitespace** on each page so the sheet feels approachable and uncluttered.
* **Why It Matters:** Cramped blanks cause physical frustration and messy erasures; color-dependent diagrams fail on monochrome home printers.
* **How Enforced in V1:** Deterministic checks **`DET-07`** (scans for prohibited external-material words/color-only references, enforces CSS/layout template line heights and font sizes by grade band, and verifies rendered PDF page count, dimensions, whitespace ratio $\ge 30\%$, and zero text clipping/overflow).

### Rule 8: Answerability and Separate Parent Answer Key
* **Classification:** `[Mandatory V1 Product Constraint]`
* **Requirement:** Every student prompt must have a clear, unambiguous intended answer (or explicit evaluation criterion for short synthesis/sketch items) grounded in the lesson content. The system must generate a **separate Page 3 Parent Answer Key & Scope Guide** containing:
  1. The exact canonical answer for every item.
  2. Acceptable alternative phrasings for short-answer items.
  3. A 1-sentence plain-language explanation of *why* the answer is correct (so parents can support their child without reading the entire curriculum PDF).
  4. An honest scope note stating which slice of the uploaded curriculum was covered in this 15-minute lesson and reminding the parent that single-session completion represents initial comprehension, not permanent mastery.
* **Why It Matters:** Ambiguous questions frustrate children, and parents need a fast, reliable key to check work without re-solving every problem themselves.
* **How Enforced in V1:** Deterministic check **`DET-08`** (verifies every `item_id` on Pages 1–2 has a corresponding complete entry in the Page 3 `answer_key` object) + AI-assisted check **`AI-06`** (an independent AI solver pass attempts all student items using *only* Pages 1–2 and must match the answer key without flagging ambiguity).

## 4. Reusable Lesson Architecture & Sequence Adaptations

### 4.1 The Five Mandatory Functional Stages (`[Evidence-Informed Principle]`)
Every Version 1 lesson must contain five functional stages (**Discover, Reinforce, Vary, Apply, Recall**). Across a fixed **2-Page Landscape A4 Student Worksheet**, the canonical layout and cognitive progression are:

| Stage | Location | Pedagogical Purpose | Required Support Level | Allowed Item Count (`[Provisional V1 Heuristic]`) | Target Stage Duration (`[Provisional V1 Heuristic]`) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Header & Orientation** | Page 1, Top Banner | State clear lesson topic, scope banner (*"Part 1 of N"*), and orient the child. | — | 0 scored items | **$1.0\text{ min}$** (Fixed overhead) |
| **1. Discover** | Page 1, Left Column | Spark curiosity with an opening hook, present a dual-coded visual + verbal explanation, and walk through a complete worked example with 1 guided observation action. | **Maximum Support:** Full worked model provided; child marks/notices a key feature. | **1–2** guided observation actions | **$3.0\text{ min}$** *(Range: $2.5\text{–}3.5\text{ min}$)* |
| **2. Reinforce** | Page 1, Right Column | Lock in basic comprehension of the definition, rule, or steps using high-support scaffolding and a pre-filled Worked Start (`Ex:`). | **High Support:** Word bank (with $\ge 1$ distractor), faded final step, or asymmetric matching. | **2–4** scaffolded items | **$3.0\text{ min}$** *(Range: $2.5\text{–}3.5\text{ min}$)* |
| **3. Vary** | Page 2, Top-Left Zone | Practise the same concept in a shifted format, reverse direction, or third-person *Spot-the-Mistake* activity to prevent surface memorization. | **Moderate Support:** Format shifted; includes inline reference pointer (*"Check Step 1"*). | **2–3** varied items | **$2.5\text{ min}$** *(Range: $2.0\text{–}3.0\text{ min}$)* |
| **4. Apply** | Page 2, Top-Right / Center Zone | Use the knowledge to solve a realistic problem or explain a novel scenario in a structured workspace. | **Low Support:** Workspace grid, pre-printed units, or sentence stem provided; no answer bank. | **1–2** application problems | **$3.5\text{ min}$** *(Range: $3.0\text{–}4.0\text{ min}$)* |
| **5. Recall** | Page 2, Bottom-Right Isolated Box | Retrieve the core concept or rule from memory without copying from Page 1. Includes directive: *"Keep Page 1 flipped face-down!"* | **Zero Content Support:** Isolated on Page 2; cue-free retrieval or *"Teach It Back"* summary. | **1–2** retrieval prompts | **$2.0\text{ min}$** *(Range: $1.5\text{–}2.5\text{ min}$)* |
| **TOTAL** | **2 Student Pages** *(+ Page 3 Key)* | **Initial Encoding $\rightarrow$ Guided Practice $\rightarrow$ Transfer & Retrieval** | **Monotonic Fade across Core Spine** | **8–15 total scored items across 5–6 blocks** | **$15.0\text{ min}$ Target** *(Corridor: $13.0\text{–}16.5\text{ min}$)* |

*Note on Optional Fast-Finisher Buffer:* Page 2 may include one small, ungraded footer box labeled **`[Optional Bonus Thought]`** containing a 1-sentence *"What if?"* reflection question for children who finish early. This optional box is excluded from the 8–15 scored item count and the 15-minute timing calculation.

### 4.2 Resolving the Five-Stage Requirement with Subject-Specific Adaptations
To avoid conflict between the mandatory 5-stage rule and domain-specific teaching needs, Version 1 defines **four valid sequence variants**. Every variant includes all five functional stage types (`Discover`, `Reinforce`, `Vary`, `Apply`, `Recall`) and preserves progressive scaffolding fade:

1. **Variant 1 — Canonical Conceptual Sequence (`Discover → Reinforce → Vary → Apply → Recall`):**
   * *Used for:* Conceptual science, history, social studies, reading comprehension.
   * *Scaffolding Rule:* Strict decreasing support from Stage 1 to Stage 5 (`Discover > Reinforce > Vary > Apply > Recall == 0`).
2. **Variant 2 — Procedural Forward-First Sequence (`Discover → Reinforce → Apply → Vary → Recall`):**
   * *Used for:* Procedural mathematics (e.g., fraction operations, multi-step equations) and grammar rules.
   * *Rationale (`[Evidence-Informed Principle]`):* Novices learning an algorithm must consolidate the forward procedure (*Discover $\rightarrow$ Reinforce $\rightarrow$ Apply*) before attempting reversed parameters or error-spotting (*Vary*), which cause procedural confusion if introduced before forward execution is stable.
   * *Scaffolding Rule:* `Discover > Reinforce > [Apply, Vary] > Recall == 0`. Both *Apply* (Page 2 Top-Left) and *Vary* (Page 2 Top-Right) operate at low/moderate support above *Recall*.
3. **Variant 3 — Phenomenon / Predict-First Sequence (`Vary [30s Prediction Probe] → Discover → Reinforce → Vary [Consolidation] → Apply → Recall`):**
   * *Used for:* Counter-intuitive physical phenomena or inquiry topics (e.g., buoyancy, simple machines).
   * *Rationale (`[Evidence-Informed Principle]`):* Opening with a 30-second contrasting-case prediction (*"Which block will slide faster? Circle your guess"*) creates an information gap that primes attention for *Discover*.
   * *Scaffolding Rule:* The opening prediction probe is embedded as the curiosity hook of Stage 1 on Page 1 ($\le 45\text{ seconds}$, zero penalty for wrong intuition), followed immediately by the canonical `Discover → Reinforce → Vary → Apply → Recall` fade.
4. **Variant 4 — Chunked Terminology Micro-Cycles (`[Discover A → Reinforce A] → [Discover B → Reinforce B] → Vary [Contrast A vs. B] → Apply → Recall`):**
   * *Used for:* Classification sets or dense vocabulary (e.g., 4–5 cell organelles or 3 rock types).
   * *Rationale (`[Evidence-Informed Principle]`):* Presenting 5 new terms simultaneously in one block overloads working memory. Splitting Page 1 into two short micro-cycles of 2–3 terms each (`Block 1A/2A` and `Block 1B/2B`, totaling **6 activity blocks** across the lesson) allows encoding before contrasting all terms together in *Vary* on Page 2.
   * *Scaffolding Rule:* Each micro-cycle fades internally (`Discover_A > Reinforce_A` and `Discover_B > Reinforce_B`), and Page 2 fades strictly across `Vary > Apply > Recall == 0`.

## 5. Paper-Based Activity Selection & Handwriting Rules

### 5.1 Authoritative Activity Block & Item Counts (`[Provisional V1 Heuristic — Requires Testing]`)
* **Activity Blocks per Lesson:** Exactly **5 activity blocks** for Variants 1–3 (one per stage) or **6 activity blocks** for Variant 4 (two Discover/Reinforce pairs on Page 1 + Vary, Apply, Recall on Page 2).
* **Sub-Items per Activity Block:** **1 to 4 sub-items** per block (specifically: `1–2` in *Discover*, `2–4` in *Reinforce*, `2–3` in *Vary*, `1–2` in *Apply*, and `1–2` in *Recall*).
* **Total Scored Pencil Actions per Lesson:** **8 to 15 items** across the entire lesson.
* **Mechanic Diversity Rule:** Every lesson must use **at least 3 different mechanics** from the Approved Paper Taxonomy below, and **no two consecutive blocks** may use the same mechanic.

### 5.2 Approved Paper-and-Pencil Activity Taxonomy (`[Mandatory V1 Product Constraint]`)

| Mechanic Enum | Activity Description | Permitted Stages | Mandatory V1 Design & Anti-Gaming Rules |
| :--- | :--- | :--- | :--- |
| **`M1_ANNOTATION`** | Circle, underline, or tick target features on a diagram, worked example, or contrasting pair. | *Discover*, *Reinforce*, *Vary* | Provide $\ge 3$ selectable targets spaced $\ge 6\text{ mm}$ apart so selection is never a 50/50 guess. |
| **`M2_ASYMMETRIC_MATCH`** | Draw pencil lines connecting items in Column A to definitions/functions in Column B. | *Reinforce*, *Vary* | **Must be asymmetric:** Column B must have $\ge 1$ extra distractor option ($|B| \ge |A| + 1$) to prevent solving the last item by elimination. Max 4 items in Column A. |
| **`M3_DIAGRAM_LABEL`** | Write terms or draw directional arrows into callout boxes on a system/process diagram. | *Discover*, *Reinforce*, *Apply* | Include a Word Bank (with $\ge 1$ distractor) in *Reinforce*; omit the Word Bank in *Apply*. Pre-fill Box 1 (`Ex:`). |
| **`M4_CATEGORY_SORT`** | Sort a pool of 3–6 items into a 2- or 3-column table or Venn diagram. | *Reinforce*, *Vary* | Allow sorting via short 1–2 word labels or letter codes (`A, B, C`) so handwriting volume stays low. Pre-fill 1 item (`Ex:`). |
| **`M5_FADED_STEP`** | Complete the missing intermediate or final step(s) in a multi-step math or rule procedure. | *Discover*, *Reinforce* | Show earlier steps fully worked; pre-print operators (`=`, `+`) and measurement units inside the answer blank. |
| **`M6_SPOT_MISTAKE`** | Identify and fix a realistic misconception in a fictional peer's worked solution. | *Vary*, *Apply* | Frame in third person (*"Leo wrote..."*). Require two actions: (1) circle the faulty step, and (2) write the correction. |
| **`M7_RULE_PATH`** | Trace a path through a grid/bridge where valid moves follow the curriculum rule. | *Vary*, *Apply* | Every step decision must test the target concept (e.g., equivalent fractions). Include a pre-drawn start arrow (`Ex:`). |
| **`M8_MODEL_SKETCH`** | Draw simple arrows, particles, or bar models inside a pre-framed reference box. | *Apply*, *Recall* | Specify exact visual criteria (*"Draw 5 dots to show..."*) inside a pre-drawn frame so artistic skill is never required. |
| **`M9_SHORT_SYNTHESIS`** | Complete a causal sentence stem or write a 1–2 sentence *"Teach It Back"* explanation. | *Apply*, *Recall* | Provide ruled lines, a target keyword checklist (`Use: [ ] term1 [ ] term2`), and sentence starters for Grades 1–4. |

### 5.3 Authoritative Grade-Band Reading, Handwriting, and Ergonomic Caps (`[Provisional V1 Heuristic — Requires Testing]`)

To ensure consistency across all software modules, Version 1 enforces one unified table of grade-band limits:

| Parameter | Grades 1–2 *(Ages 6–8)* | Grades 3–5 *(Ages 8–11)* | Grades 6+ *(Ages 11+)* |
| :--- | :--- | :--- | :--- |
| **Max Passive Reading Span** *(words before a pencil action)* | **$45\text{ words}$** | **$80\text{ words}$** | **$120\text{ words}$** |
| **Max Instruction Sentence Length** | **$12\text{ words}$** | **$18\text{ words}$** | **$22\text{ words}$** |
| **Max Total Student Handwriting Volume** *(across entire lesson)* | **$\le 15\text{ words}$** *(1-word blanks & marks)* | **$\le 40\text{ words}$** *(short phrases & 1-sentence synthesis)* | **$\le 75\text{ words}$** *(concise steps & 1–2 sentence synthesis)* |
| **Max Handwriting Motor Time Share** ($T_{\text{motor\_write}} / T_{\text{stages}}$) | **$\le 30\%$** | **$\le 30\%$** | **$\le 30\%$** |
| **Minimum Write-In Line Height** *(on Landscape A4)* | **$12\text{ mm}$** *(with dashed midline)* | **$9\text{ mm}$** | **$7.5\text{ mm}$** |
| **Minimum Body Font Size** | **$14\text{ pt}$** | **$12\text{ pt}$** | **$10.5\text{ pt}$** |

## 6. Authoritative 15-Minute Timing Model & Scope Slicing

### 6.1 The Deterministic Time Estimation Formula (`[Provisional V1 Heuristic — Requires Testing]`)
Children read instructional text, inspect diagrams, think through novel steps, and write by hand significantly slower than adults. Version 1 calculates total predicted lesson duration $T_{\text{lesson}}$ deterministically from the lesson JSON structure:

$$T_{\text{lesson}} = T_{\text{orientation}} + \sum_{k=1}^{K} \left( T_{\text{read}}(k) + T_{\text{visual}}(k) + T_{\text{think}}(k) + T_{\text{motor}}(k) \right)$$

Where $K \in \{5, 6\}$ is the number of activity blocks, andActive Stage Time is defined as $T_{\text{stages}} = T_{\text{lesson}} - T_{\text{orientation}}$.

#### Authoritative V1 Timing Weights by Grade Band

| Component | Calculation Rule | Grades 1–2 | Grades 3–5 | Grades 6–8 | Grades 9+ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **$T_{\text{orientation}}$** | Fixed allowance per lesson for page setup, name, and step transitions | **$60\text{ sec}$ ($1.0\text{ min}$)** | **$60\text{ sec}$ ($1.0\text{ min}$)** | **$60\text{ sec}$ ($1.0\text{ min}$)** | **$60\text{ sec}$ ($1.0\text{ min}$)** |
| **$T_{\text{read}}(k)$** | $\frac{\text{Total Printed Words in Block } k}{\text{Instructional Reading WPM}}$ | **$35\text{ WPM}$** ($1.71\text{ s/wd}$) | **$70\text{ WPM}$** ($0.86\text{ s/wd}$) | **$110\text{ WPM}$** ($0.55\text{ s/wd}$) | **$135\text{ WPM}$** ($0.44\text{ s/wd}$) |
| **$T_{\text{visual}}(k)$** | Fixed inspection time per diagram / worked model in Block $k$ | **$25\text{ sec}$** (simple)<br>**$40\text{ sec}$** (process/table) | **$25\text{ sec}$** (simple)<br>**$40\text{ sec}$** (process/table) | **$20\text{ sec}$** (simple)<br>**$35\text{ sec}$** (process/table) | **$20\text{ sec}$** (simple)<br>**$35\text{ sec}$** (process/table) |
| **$T_{\text{think}}(k)$** | Cognitive deliberation time per scored sub-item in Block $k$: | | | | |
| | • *Discover* item (guided notice): | **$10\text{ sec}$** | **$10\text{ sec}$** | **$10\text{ sec}$** | **$10\text{ sec}$** |
| | • *Reinforce* item (scaffolded): | **$20\text{ sec}$** | **$20\text{ sec}$** | **$20\text{ sec}$** | **$20\text{ sec}$** |
| | • *Vary* item (shifted format / error spot): | **$30\text{ sec}$** | **$30\text{ sec}$** | **$35\text{ sec}$** | **$35\text{ sec}$** |
| | • *Apply* item (independent problem): | **$45\text{ sec}$** | **$50\text{ sec}$** | **$55\text{ sec}$** | **$60\text{ sec}$** |
| | • *Recall* item (cue-free retrieval): | **$35\text{ sec}$** | **$40\text{ sec}$** | **$45\text{ sec}$** | **$45\text{ sec}$** |
| **$T_{\text{motor}}(k)$** | Physical pencil execution per sub-item: | | | | |
| | • Discrete mark (circle, line, tick): | **$5\text{ sec/mark}$** | **$4\text{ sec/mark}$** | **$3\text{ sec/mark}$** | **$3\text{ sec/mark}$** |
| | • Simple model sketch / arrow drawing: | **$25\text{ sec}$** | **$25\text{ sec}$** | **$20\text{ sec}$** | **$20\text{ sec}$** |
| | • Handwriting ($\frac{\text{Expected Written Words}}{\text{Handwriting WPM}}$): | **$5\text{ WPM}$** ($12.0\text{ s/wd}$) | **$11\text{ WPM}$** ($5.45\text{ s/wd}$) | **$17\text{ WPM}$** ($3.53\text{ s/wd}$) | **$22\text{ WPM}$** ($2.73\text{ s/wd}$) |

### 6.2 Authoritative Timing Corridor & Balance Constraints (`[Provisional V1 Heuristic — Requires Testing]`)
Every generated lesson must satisfy all four timing equations simultaneously:
1. **Total Lesson Duration Corridor:**
   $$13.0\text{ minutes} \le T_{\text{lesson}} \le 16.5\text{ minutes} \quad (\text{Target: } 15.0\text{ minutes})$$
2. **Per-Block Duration Cap:** No individual activity block $k$ may exceed **$4.0\text{ minutes}$** ($T_{\text{block}}(k) \le 240\text{ seconds}$).
3. **Time to First Pencil Mark:** The cumulative time in Block 1 (*Discover*) up to and including the first guided pencil mark must be **$\le 60\text{ seconds}$**.
4. **Higher-Order Cognitive Time Share (*Apply + Recall*):** The combined duration of Stage 4 (*Apply*) and Stage 5 (*Recall*) must represent **$35\%$ to $45\%$ of Active Stage Time** ($0.35 \le \frac{T_{\text{Apply}} + T_{\text{Recall}}}{T_{\text{stages}}} \le 0.45$).
   * *Mathematical Verification at Target:* With $T_{\text{orientation}} = 1.0\text{ min}$ and $T_{\text{stages}} = 14.0\text{ min}$ ($Discover = 3.0\text{m}$, $Reinforce = 3.0\text{m}$, $Vary = 2.5\text{m}$, $Apply = 3.5\text{m}$, $Recall = 2.0\text{m}$), $T_{\text{Apply}} + T_{\text{Recall}} = 5.5\text{ min}$, which is **$39.3\%$** of $14.0\text{ min}$, and every stage is $\le 4.0\text{ min}$.

### 6.3 Curriculum Scope Reduction Rule (`[Mandatory V1 Product Constraint]`)
1. **Concept Budget Ceiling:** A single 15-minute lesson may teach at most **1 core concept** (comprising at most **3 tightly linked sub-concepts** or **5 new domain vocabulary terms**).
2. **Scope Slicing Over Compression:** When an uploaded curriculum PDF contains more material than fits within the concept ceiling and the $16.5\text{ minute}$ upper bound, the software **must never compress or delete scaffolding stages**. Instead, the curriculum parser slices the PDF into sequential topic units, generates a complete 5-stage lesson for **Unit 1 (the foundational entry topic)**, and prints a clear scope banner on Page 1 and Page 3: *"Scope Note: This 15-minute lesson covers Part 1 of your uploaded material ([Focused Topic Name])."*

## 7. Common Teaching-Design Failures the System Must Prevent

| Failure ID | Failure Name | Description & Impact on Child | Primary Prevention Gate |
| :--- | :--- | :--- | :--- |
| **F1** | **The Wall-of-Text Lesson** | Dense paragraphs of explanation exceed reading stamina; children skip reading and guess randomly. | **`DET-04`** (Enforces $45/80/120$-word passive reading cap and $\le 60\text{s}$ first pencil action). |
| **F2** | **Verbatim "Ctrl+F" Copying** | Questions repeat exact sentence frames from a visible explanation above; child copies words without comprehension. | **`DET-06`** (Blocks $\ge 5$-word exact substring overlap and isolates *Recall* on Page 2) + **`AI-05`**. |
| **F3** | **The Unscaffolded Cliff** | Lesson jumps straight from a brief definition to a complex open problem with no worked example or faded practice. | **`DET-01`** (Requires 5 stages + `worked_example` field) + **`AI-03`** (Verifies scaffolding fade). |
| **F4** | **Decorative Edutainment Bloat** | Word searches, anagrams, unlabelled mazes, or coloring tasks consume time without teaching the concept. | **`DET-06`** (Schema-level ban on non-approved mechanics) + **`AI-05`** (Objective alignment check). |
| **F5** | **Unstated Prerequisite or Math Trap** | Lesson uses undefined symbols, unstated terminology, or messy decimal/fraction arithmetic not taught in the source. | **`AI-02`** (Audits prerequisites and checks secondary math/vocabulary against `Target_Grade - 1`). |
| **F6** | **Symmetric Elimination Gaming** | A 3-item matching or word-bank task has exactly 3 options, making the last answer automatic without thought. | **`DET-06`** (Enforces $|\text{Options}| \ge |\text{Prompts}| + 1$ across all matching and word-bank blocks). |
| **F7** | **Parent-Dependent Instructions** | Complex multi-clause directions or unfamiliar table layouts force the child to ask an adult *"What do I do here?"* | **`DET-03`** (Instruction word cap + mandatory grey `Ex:` Worked Start) + **`AI-03`**. |
| **F8** | **Careless-Mistake Trick Questions** | Negative stems (*"Which is NOT..."*), missing units, or ungridded math workspaces cause avoidable errors. | **`DET-05`** (Bans negative-stem traps, requires unit strings on numerical answers). |
| **F9** | **Print & Ergonomic Breakdown** | Cramped blanks frustrate young writers; color-coded diagrams turn into indistinguishable grey blobs on monochrome printers; text overflows onto a 3rd page. | **`DET-07`** (Enforces grade line heights, monochrome-safe styling, $\ge 30\%$ whitespace, and strict 2-page student layout). |
| **F10** | **Shame, Timers, or False Mastery Claims** | Stopwatch icons, point scores, *"Easy!"* labels, or claims of guaranteed mastery pressure children and mislead parents. | **`DET-05`** & **`DET-08`** (Lexicon ban on timers, scores, evaluative labels, and mastery guarantees). |

## 8. Version 1 Technical Verification Architecture

To make Version 1 practical and reliable to implement, quality control is divided into **three distinct verification categories**. The architecture avoids speculative multi-agent networks or complex computer-vision graphs where simpler deterministic or structured AI checks suffice, and openly distinguishes deterministic guarantees from fallible AI judgments and human validation.

### 8.1 Category A: Deterministic Software Checks (`DET-01` to `DET-08`)
Deterministic checks are executed in application code (schema validators, token counters, regex filters, arithmetic formulas, and headless PDF layout inspection). They are **100% reproducible** and run on every lesson draft in milliseconds.

| Check ID | 1. What Is Checked | 2. How It Is Checked (V1 Implementation) | 3. Pass / Fail Condition | 4. Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`DET-01`** | **Required Schema & Stage Structure** | JSON Schema validator checks the generated lesson payload against the V1 Lesson Schema. | **Pass:** Contains all 5 functional stages (`Discover, Reinforce, Vary, Apply, Recall`) in one of the 4 approved sequence variants; `5 <= activity_blocks <= 6`; `1 <= sub_items_per_block <= 4`; `8 <= total_scored_items <= 15`; Stage 1 includes a non-empty `worked_example` object.<br>**Fail:** Any missing stage, invalid sequence, or out-of-range item count. | Reject JSON payload; return specific schema error path to generator for targeted repair (Max 2 retries). |
| **`DET-02`** | **Source Citation Mapping & Scope Metadata** | Code inspects every factual statement, definition, and terminology entry in the lesson JSON. | **Pass:** 100% of domain fact objects contain a valid, non-empty `source_chunk_id` pointing to an extracted text/diagram span in the uploaded PDF, and `scope_metadata` lists `selected_unit` and `total_units`.<br>**Fail:** Any uncited domain claim or missing scope metadata. | If PDF extraction yielded $< 50$ words of usable text, abort and prompt parent for clearer PDF. Otherwise, regenerate uncited block with strict chunk binding. |
| **`DET-03`** | **Instruction Length & Worked-Start Presence** | Code splits `instruction_text` into sentences, counts words per sentence, and checks the `worked_start` field on structured blocks (`M2–M7`). | **Pass:** Every instruction sentence $\le 12\text{ words}$ (G1–2), $\le 18\text{ words}$ (G3–5), or $\le 22\text{ words}$ (G6+); 100% of structured activities (`M2–M7`) have a non-empty `worked_start` example item.<br>**Fail:** Instruction exceeds word cap or `worked_start` is missing. | Auto-populate `worked_start` from Item 0 or trigger targeted rewrite of the over-length instruction sentence. |
| **`DET-04`** | **Passive Reading Caps & First-Action Timing** | Code counts words in every continuous text block prior to a student action and computes time to first action using the Section 6.1 formula. | **Pass:** Continuous text blocks $\le 45\text{ words}$ (G1–2), $\le 80\text{ words}$ (G3–5), $\le 120\text{ words}$ (G6+); time to first action in *Discover* $\le 60\text{ sec}$.<br>**Fail:** Any text block exceeds cap or first action $> 60\text{ sec}$. | Trigger targeted rewrite of Stage 1 to shorten prose or insert an earlier guided observation mark. |
| **`DET-05`** | **Mechanic Diversity, Safety & Error-Trap Lexicon** | Code inspects `mechanic_type` array and runs regex/token blocklists across all student-facing text. | **Pass:** $\ge 3$ distinct approved mechanic types used; no two adjacent blocks share the same `mechanic_type`; zero matches for negative-stem traps (`/\b(NOT|EXCEPT)\b/`), timer/score words (`timer, stopwatch, minutes left, score:, points`), evaluative labels (`easy, simple, obvious`), or mastery guarantees (`guaranteed, mastered, 100% fluent`).<br>**Fail:** Duplicate adjacent mechanic or blocklist token match. | Strip/replace prohibited phrasing or regenerate the offending activity block with an unused mechanic enum. |
| **`DET-06`** | **Anti-Gaming Asymmetry & Anti-Copy Isolation** | Code compares option vs. prompt counts on `M2_ASYMMETRIC_MATCH` and word banks, checks stage page assignments, and runs a 5-gram exact substring comparison between *Discover* text and Stages 2–5 prompts. | **Pass:** $|\text{Options}| \ge |\text{Prompts}| + 1$ on all matching/word-bank blocks; *Discover* and *Reinforce* assigned to `page: 1`; *Vary, Apply, Recall* assigned to `page: 2`; zero shared contiguous $\ge 5$-word substrings between *Discover* sentences and assessment prompts.<br>**Fail:** Symmetric matching ($|Options| == |Prompts|$), *Recall* on Page 1, or verbatim substring copy detected. | Deterministically inject 1 curriculum-valid distractor from the glossary, force page break before *Vary*, or trigger prompt paraphrasing. |
| **`DET-07`** | **Timing Formula, Handwriting Cap & Landscape A4 Layout** | Code evaluates the Section 6.1 timing equations, sums expected written words, scans for external material words, and compiles the HTML/CSS template via headless Chromium to PDF. | **Pass:** $13.0\text{ min} \le T_{\text{lesson}} \le 16.5\text{ min}$; max block $\le 4.0\text{ min}$; $0.35 \le (T_{\text{Apply}}+T_{\text{Recall}})/T_{\text{stages}} \le 0.45$; expected written words $\le 15/40/75$ and $T_{\text{motor\_write}}/T_{\text{stages}} \le 0.30$; zero external tool words (`scissors, glue, cut, red, green, blue, ruler, dice`); compiled PDF has exactly **2 Student Pages + 1 Answer Key Page** at $297\text{ mm} \times 210\text{ mm}$, CSS grade line heights/fonts applied, zero DOM bounding-box overflow/clipping, and $\ge 30\%$ white pixels.<br>**Fail:** Timing outside corridor, handwriting cap exceeded, external tool word found, or DOM overflow/page spill detected. | If $T_{\text{lesson}} > 16.5\text{ min}$ or DOM overflows 2 pages: prune 1 sub-item from *Reinforce* or *Vary* and re-compile. If handwriting cap exceeded: convert written item to `M4_CATEGORY_SORT` or `M3_DIAGRAM_LABEL`. |
| **`DET-08`** | **Answer Key & Rubric Completeness** | Code cross-references every `item_id` on Student Pages 1–2 against the Page 3 `answer_key` array. | **Pass:** 100% of student items have a non-empty `canonical_answer`, `parent_explanation`, and (for open items) `acceptable_variants`; numerical answers include pre-printed `unit` strings.<br>**Fail:** Any orphaned item or missing answer key field. | Regenerate the missing answer key object before proceeding to Category B checks. |

### 8.2 Category B: AI-Assisted Quality Checks (`AI-01` to `AI-06`)
**Important Epistemic Caveat:** AI-assisted checks use a separate, structured LLM evaluation call to assess semantic qualities that deterministic code cannot measure. **AI judgments are probabilistic and fallible—they must never be treated as guaranteed proof of pedagogical perfection.** In Version 1, they serve as an automated semantic filter to catch obvious hallucinations, ambiguous questions, and scaffolding flaws before delivery.

To reduce correlated blind spots, all Category B checks run in an **independent reviewer prompt** (with temperature `0.0`) that receives only the structured artifact under test, never the generator's internal reasoning chain.

| Check ID | 1. What Is Checked | 2. How It Is Checked (V1 Implementation) | 3. Pass / Fail Condition | 4. Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`AI-01`** | **Factual Grounding & Analogy Quarantine** | Reviewer model compares every explanation and question against the extracted text/descriptions of the cited `source_chunk_id` spans from the uploaded PDF. | **Pass:** All taught facts and definitions are supported by the cited source chunks with zero factual contradictions; any everyday analogy is clearly framed as a comparison and not tested as a literal curriculum fact.<br>**Fail:** Any unsupported factual claim, contradiction, or analogy detail tested in *Apply/Recall*. | Rewrite the flagged statement/item using only the cited source span (Max 2 retries; if still failing, halt delivery and issue Source Ambiguity Report). |
| **`AI-02`** | **First-Time Learner Prerequisites & Secondary Complexity** | Reviewer audits whether a first-time learner at `Target_Grade` has all definitions, symbols, and steps needed to complete Stages 2–5 based on Stage 1. | **Pass:** Zero undefined domain terms or symbols appear in Stages 2–5; secondary arithmetic and general vocabulary sit at or below `Target_Grade - 1` difficulty; terms $\ge 4$ syllables have phonetic guides.<br>**Fail:** Unexplained prerequisite leap or overly complex secondary math/vocabulary identified. | Inject the missing definition/step into *Discover* or simplify the secondary arithmetic numbers in the flagged problem. |
| **`AI-03`** | **Instruction Clarity & Scaffolding Progression** | Reviewer evaluates every activity instruction and checks the progression across the 5 stages. | **Pass:** Instructions are concrete, age-appropriate, and contain $\le 2$ sequential actions; *Discover* models the concept clearly; *Vary* genuinely shifts format/direction compared to *Reinforce*; support fades toward *Recall*.<br>**Fail:** Confusing/abstract instruction, missing conceptual bridge, or *Vary* merely repeats *Reinforce* without structural variation. | Rewrite the flagged instruction or regenerate the *Vary* block using a different representation angle. |
| **`AI-04`** | **Robustness & Psychological Tone** | Reviewer audits the curiosity hook, third-person error framing (*Vary*), and inline support pointers (*Vary/Apply*). | **Pass:** Opening hook poses a relevant curiosity question resolved by the lesson; error-spotting tasks attribute mistakes neutrally to a fictional peer; Stages 3–4 include a clear *"Look back at Step 1"* reference pointer.<br>**Fail:** Hook is unrelated to objective, tone is condescending/punitive, or reference pointer is missing. | Regenerate the hook, rewrite peer framing neutrally, or insert the reference pointer. |
| **`AI-05`** | **Objective Alignment & Cognitive Depth** | Reviewer evaluates whether each activity requires understanding the target learning objective rather than surface guessing or mechanical busywork. | **Pass:** Every activity directly exercises the core learning objective; distractors in matching/word-banks are plausible misconceptions rather than absurd throwaways; sub-items within a block vary meaningful parameters.<br>**Fail:** Activity is solvable via trivial surface cues, distractors are implausible, or sub-items are repetitive clones. | Replace weak distractors or regenerate redundant sub-items to vary parameters. |
| **`AI-06`** | **Independent Blind-Solver Answerability Check** | An isolated AI solver prompt is given **only** the rendered text/diagram descriptions of Student Pages 1–2 (without the source PDF or Page 3 Answer Key) and asked to solve every item and flag any ambiguity. | **Pass:** Blind solver's answers match 100% of the Page 3 `canonical_answer` (or `acceptable_variants`) and flags `0` items as ambiguous or unanswerable.<br>**Fail:** Blind solver produces a different answer, identifies two equally valid answers where only one is keyed, or cannot answer using the information on Pages 1–2. | Rewrite the ambiguous prompt/options or expand the `acceptable_variants` rubric on Page 3, then re-run `AI-06` (Max 2 retries). |

### 8.3 Bounded Retry Policy & Failure Escalation (`[Mandatory V1 Product Constraint]`)
To prevent infinite regeneration loops or silent delivery of defective worksheets:
1. **Targeted Node Repair (Maximum 2 Retries):** When any `DET` or `AI` check fails, the pipeline localizes the defect to the specific stage or item and executes at most **2 targeted regeneration/repair attempts**, re-running all downstream checks after each repair.
2. **Hard Circuit Breaker & Failure Report:** If any blocking check still fails after **2 repair attempts**, the software **blocks delivery of the lesson** and outputs a structured **Generation Failure Report** (identifying the exact failed check ID, the problematic source PDF span or layout constraint, and whether the parent needs to upload a clearer/more complete curriculum document).

### 8.4 Category C: Human Validation Protocol (`HUM-01` to `HUM-04`)
Because deterministic code and AI reviewers cannot experience real child attention, physical pencil ergonomics, or genuine conceptual understanding, Version 1 establishes a practical **Stateless Human Validation Protocol** (requiring no student accounts, no uploaded student worksheets, and no adaptive follow-up lessons):

| Validation ID | What Requires Human Judgment | Why Software/AI Cannot Guarantee This Alone | Practical V1 Human Validation Method |
| :--- | :--- | :--- | :--- |
| **`HUM-01`** | **Instruction Comprehensibility & Zero-Parent-Help Startup** | Readability formulas and AI reviewers cannot prove that a real 7-year-old will immediately grasp a table layout or visual convention without asking a parent *"What do I do?"* | **Silent-Observer Print Trials (Pre-Release & Benchmark Set):** Test benchmark lessons across grade bands with real children using printed Landscape A4 sheets and a pencil. An observer records every instance where a child hesitates $>20\text{ seconds}$ or asks an adult for instruction clarification. Any activity template causing $>15\%$ startup hesitation is redesigned. |
| **`HUM-02`** | **Real-World Duration & Attention Sustainability** | The Section 6.1 timing weights ($WPM$, $T_{\text{think}}$, $T_{\text{motor}}$) are provisional estimates. Only real-world observation shows whether a "15-minute" calculated lesson actually takes 12 minutes or 24 minutes in practice, and where boredom or fatigue sets in. | **Stopwatch Calibration Trials:** Measure actual start-to-finish completion times and visible off-task behaviors across a sample of $N \ge 10$ children per grade band on benchmark lessons. Use observed median and 75th-percentile times to recalibrate the software's numerical timing weights in Section 6.1. |
| **`HUM-03`** | **Visual Diagram Intuitiveness & Physical Pencil/Eraser Ergonomics** | Headless PDF checks confirm zero text overlap and $\ge 30\%$ whitespace, but cannot judge whether a black-and-white diagram visually communicates a concept clearly, or whether write-in boxes smudge/tear when erased with a real pencil. | **Physical Print-and-Solve QA (Weekly Stratified Sample):** Curriculum reviewers physically print a stratified sample of generated lessons on standard monochrome home printers and complete every item by hand with a graphite pencil and eraser, auditing diagram clarity, line-drawing ergonomics, and answer-key accuracy. |
| **`HUM-04`** | **Genuine First-Time Understanding & Application** | Passing an AI blind-solver check proves a worksheet is *logically solvable*, not that a child who didn't know the concept 15 minutes ago now understands it. | **Post-Lesson Oral Spot-Check (During Benchmark Trials):** Immediately after a child completes a printed trial worksheet, an educator removes the paper and asks 2 brief oral transfer questions on the concept. If children complete the worksheet accurately but fail the oral spot-check, the *Reinforce/Vary/Recall* scaffolding templates are tightened to eliminate surface pattern-matching. |

## 9. Version 1 Pre-Delivery Acceptance Checklist

A candidate lesson must pass **100% of Automated Gates (Gates 1–6)** before it can be delivered as final. Gate 7 governs ongoing human quality assurance of the generation templates and timing parameters.

### Gate 1: Source Grounding & Scope Integrity (Blocking)
* [ ] **1.1 Source Citation Completeness (`DET-02`):** Every domain fact, definition, formula, and term in the lesson JSON cites a valid `source_chunk_id` from the uploaded PDF, and scope metadata is populated.
* [ ] **1.2 Semantic Entailment & Analogy Quarantine (`AI-01`):** AI reviewer confirms zero unsupported domain claims, zero contradictions with the PDF, and zero analogy details tested as curriculum facts.

### Gate 2: Five-Stage Architecture & First-Time Scaffolding (Blocking)
* [ ] **2.1 Valid 5-Stage Sequence & Item Counts (`DET-01`):** Lesson contains all 5 stages (`Discover, Reinforce, Vary, Apply, Recall`) in an approved Section 4.2 variant across **5–6 activity blocks**, with **1–4 sub-items per block** and **8–15 total scored items**.
* [ ] **2.2 Worked Example & Prerequisite Closure (`DET-01`, `AI-02`):** Stage 1 includes a complete worked example/model; zero undefined domain terms appear in Stages 2–5; secondary math/vocabulary is $\le \text{Target\_Grade} - 1$; terms $\ge 4$ syllables include phonetic glosses.
* [ ] **2.3 Progressive Scaffolding & Genuine Variation (`AI-03`):** Support fades across the core spine to zero content hints in *Recall*, and *Vary* shifts format, direction, or error-analysis framing.

### Gate 3: Learner Robustness, Clarity & Psychological Safety (Blocking)
* [ ] **3.1 Concise Instructions & Visual Worked Starts (`DET-03`, `AI-03`):** All instruction sentences obey grade word caps ($\le 12 / 18 / 22\text{ words}$) and verb caps ($\le 2$ actions), and 100% of structured activities (`M2–M7`) render a grey `Ex:` Worked Start.
* [ ] **3.2 Active Reading Spans & 60s First Mark (`DET-04`):** Continuous reading blocks never exceed $45 / 80 / 120\text{ words}$ without a pencil action, and the first pencil mark occurs within $\le 60\text{ seconds}$.
* [ ] **3.3 Error-Trap & Shame Prevention (`DET-05`, `AI-04`):** Zero negative-stem traps (`NOT`/`EXCEPT`), zero timers/scores/evaluative labels (`Easy!`), neutral third-person framing on *Spot-the-Mistake*, and inline *"Look back at Step 1"* reference pointers in Stages 3–4.

### Gate 4: Purposeful Paper Activities & Anti-Copy Isolation (Blocking)
* [ ] **4.1 Mechanic Diversity & Approved Taxonomy (`DET-05`, `DET-06`):** Uses $\ge 3$ approved Section 5.2 mechanics with no identical mechanic in adjacent blocks; zero word searches, anagrams, unlabelled mazes, or decorative coloring.
* [ ] **4.2 Asymmetric Options & Conceptual Depth (`DET-06`, `AI-05`):** All matching and word-bank tasks have $|\text{Options}| \ge |\text{Prompts}| + 1$, and activities require conceptual processing rather than surface guessing.
* [ ] **4.3 Physical & Lexical Recall Isolation (`DET-06`):** Stage 1 (*Discover*) is on Page 1; Stage 5 (*Recall*) is on Page 2 with a *"Flip Page 1 face-down"* prompt; zero prompts share a $\ge 5$-word exact substring with *Discover* explanations.

### Gate 5: Realistic 15-Minute Timing & Motor Budget (Blocking)
* [ ] **5.1 Authoritative Timing Corridor (`DET-07`):** Calculated $T_{\text{lesson}} \in [13.0, 16.5]\text{ minutes}$ (including $1.0\text{ min}$ orientation); every activity block is $\le 4.0\text{ minutes}$; *Apply + Recall* account for $35\%\text{–}45\%$ of Active Stage Time.
* [ ] **5.2 Handwriting Motor Cap (`DET-07`):** Total expected student writing is $\le 15\text{ words}$ (G1–2), $\le 40\text{ words}$ (G3–5), or $\le 75\text{ words}$ (G6+), and handwriting time is $\le 30\%$ of Active Stage Time.

### Gate 6: Print-First Landscape A4 Fidelity & Answerability (Blocking)
* [ ] **6.1 Fixed 2-Page Student Layout & Ergonomics (`DET-07`):** Renders cleanly onto **2 Student Landscape A4 Pages ($297\text{ mm} \times 210\text{ mm}$) + 1 Answer Key Page** with $\ge 30\%$ whitespace, grade-compliant line heights ($12 / 9 / 7.5\text{ mm}$) and font sizes ($14 / 12 / 10.5\text{ pt}$), monochrome-safe visuals, zero external tools, and zero text clipping/overflow.
* [ ] **6.2 Complete Answer Key & Blind-Solver Convergence (`DET-08`, `AI-06`):** Every student item has a complete entry + parent explanation on Page 3, pre-printed units on numerical blanks, honest non-guarantee scope framing, and $100\%$ convergence with the independent `AI-06` blind solver.

### Gate 7: Human Validation & Calibration Governance (Operational Requirement)
* [ ] **7.1 Benchmark Child Testing & Print Audits (`HUM-01` to `HUM-04`):** Activity templates, diagram styles, and timing weights are validated through physical monochrome print audits and silent-observer benchmark trials with real children, with failed 2-retry lessons routed to human exception review.

## 10. Outstanding Assumptions & Questions Requiring Real-World Testing

Because Version 1 avoids speculative over-claiming, the following product assumptions are explicitly flagged as **provisional hypotheses** that must be tested during initial pilot deployments:

1. **Calibration of Grade-Band Reading, Thinking, and Handwriting Speeds (Section 6.1):**
   * *Assumption:* Instructional reading speeds ($35 / 70 / 110 / 135\text{ WPM}$), stage deliberation times ($10\text{–}60\text{ sec}$), and handwriting speeds ($5 / 11 / 17 / 22\text{ WPM}$) accurately predict a 13.0-to-16.5-minute real-world completion window.
   * *Testing Required:* Stopwatch observation of real children across reading percentiles (`HUM-02`) to determine whether the formula systematically underestimates diagram inspection time or handwriting hesitation in younger grades.
2. **Effectiveness of the "Flip Page 1 Face-Down" Directive in Single-Sided Printing (Section 4.1 & Rule 6):**
   * *Assumption:* Placing *Discover* on Page 1 and *Recall* on Page 2 physically prevents look-back copying when printed duplex, and children printing single-sided will follow the instruction to flip Page 1 face-down (or be blocked from verbatim copying by paraphrased synthesis prompts).
   * *Testing Required:* Observe in home/classroom trials whether children using two single-sided sheets still peek back at Page 1 during Step 5, and whether paraphrased synthesis prompts are sufficient to ensure generative processing even if they glance back.
3. **Self-Sufficiency of Visual "Worked Starts" (`Ex:`) for Grades 1–2 Emergent Readers (Rule 3 & Section 5.3):**
   * *Assumption:* Pairing a $\le 12$-word instruction with an action icon and a grey pre-completed `Ex:` item allows a Grade 1–2 child to start and complete structured paper activities without parent explanation.
   * *Testing Required:* Measure parent-help requests during Grade 1–2 benchmark sessions (`HUM-01`) to identify which activity mechanics (`M1–M9`) are genuinely self-explanatory for 6-to-7-year-olds and which require simpler visual conventions.
4. **Automated Diagram Generation Clarity in Monochrome Print (Rule 7 & `HUM-03`):**
   * *Assumption:* Programmatically generated SVG/HTML diagrams using patterns and direct callout labels can clearly represent spatial and scientific concepts across diverse curriculum PDFs on black-and-white printers.
   * *Testing Required:* Audit what percentage of uploaded curriculum topics can be represented accurately using clean programmatic diagram primitives (flowcharts, comparison tables, bar models, labeled containers) versus topics that require extracting or adapting original figures from the source PDF.
5. **Single-Slice Satisfaction When Parents Upload Multi-Week Curriculum Chapters (Section 6.3):**
   * *Assumption:* When a parent uploads a 20-page chapter PDF and receives a 15-minute lesson covering *Part 1 (Foundational Concept)* with a clear Scope Banner, the parent understands and values the focused depth rather than expecting the entire chapter compressed into two pages.
   * *Testing Required:* Validate parent comprehension and expectations around automatic scope-slicing notices on Page 1 and Page 3.
