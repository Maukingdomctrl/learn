# Core Teaching Methodology Specification — Version 1.1 (`CORE_TEACHING_METHODOLOGY_V1_1.md`)

**Document Status:** Version 1.1 — Consolidated, Internally Consistent Pedagogical & Engineering Specification  
**Target Medium:** Printed Landscape A4 Pages ($297\text{ mm} \times 210\text{ mm}$) + Standard Graphite Pencil (Zero Screen Interaction)  
**Target Duration:** ~15 Minutes per Single-Session Lesson (Provisional Engineering Corridor: $13.0\text{ to }16.5\text{ minutes}$)  
**Output Format:** Fixed 2-Page Student Worksheet + Separate Page 3 Parent Answer Key & Scope Guide  
**Learner Context:** Real-World Children in First-Time Exposure to Supplied Curriculum Material (Stateless; No Student Profiles, Uploaded Responses, or Adaptive Follow-Up)

## 1. Version History

| Version | Date | Summary of Revisions |
| :--- | :--- | :--- |
| **v0.1** | 2026-10-15 | Initial draft of the 12 core teaching principles, 5-stage progression, paper-based activity taxonomy, timing formula, failure catalog, and pre-acceptance checklist. |
| **v0.2** | 2026-10-15 | Added real-world child robustness buffers (confusion, boredom, frustration, careless mistakes, cognitive overload) and multi-tier verification gates. |
| **v1.0** | 2026-10-15 | Consolidated timing tables, standardized on a 2-page Landscape A4 student worksheet plus Page 3 Answer Key, and separated deterministic, AI-assisted, and human checks. |
| **v1.1 (Current)** | 2026-10-15 | **Contradiction Resolution & V1 Implementation Simplification:** Resolved stage-sequence vs. block-count conflicts (Variants 1–4), aligned stage item sums ($7\text{–}15$ total scored items), unified non-overlapping grade bands (`G1_2`, `G3_5`, `G6_8`, `G9_PLUS`), replaced destructive item deletion on timing/layout overflow with a safe adjustment hierarchy, standardized `worked_start` (`Ex:`) rules across all structured mechanics, replaced brittle keyword blocklists and pixel-counting checks with contextual AI validation and DOM box-model checks, enabled multimodal support for diagram-heavy PDFs ($<50$ words), and clarified source claim traceability. See Section 11 for the full Change Log. |

## 2. Epistemic Framework & Explicit Limitations

### 2.1 Three-Tier Governance Classification
To prevent treating provisional product numbers as scientific laws—or treating core learning principles as optional styling—every rule in Version 1.1 carries one of three explicit classifications:

| Classification Tag | Definition | Examples in Version 1.1 | Governance Rule |
| :--- | :--- | :--- | :--- |
| **`[Evidence-Informed Principle]`** | Instructional design principles grounded in cognitive psychology and learning sciences, recognizing that real-world effectiveness depends on learner age, domain, and context. | Working memory constraints (Cognitive Load Theory), pairing visuals with concise text (Dual Coding), fading worked examples for novices, active retrieval practice over passive re-reading, and varying problem formats. | **Guides pedagogical design.** Preserved across all lessons, with implementation adapted to the subject and grade band. |
| **`[Mandatory V1 Product Constraint]`** | Fixed product-scope, safety, and architectural boundaries defining Version 1 of this product. | Landscape A4 print format, graphite pencil only, zero external tools or screens, 2 student pages + 1 answer key page, stateless operation, source-grounded claims, and non-guarantee framing. | **Strict V1 engineering requirement.** Any violation blocks lesson delivery. |
| **`[Provisional V1 Heuristic — Requires Testing]`** | Practical engineering estimates, numerical thresholds, timing weights, word caps, and layout dimensions chosen as buildable starting points for Version 1. | The $13.0\text{–}16.5\text{ minute}$ corridor, grade-band WPM reading/writing speeds, passive reading word caps ($45/80/120\text{ words}$), handwriting caps ($15/40/65/80\text{ words}$), and $\le 70\%$ content box area. | **Tunable configuration parameters.** Enforced in software for V1, but must be empirically calibrated through observational testing with real children. |

### 2.2 Explicit Non-Guarantee Contract (`[Mandatory V1 Product Constraint]`)
1. **No Guarantee of Mastery:** A single 15-minute worksheet cannot guarantee permanent retention or mastery, which require distributed practice, feedback, and consolidation over time. The objective of a Version 1.1 lesson is **Initial Comprehension and Guided First Application**: helping a child encounter new curriculum material for the first time, grasp its core mechanism, and apply it with fading support.
2. **No Guarantee of Engagement:** Real-world children experience fluctuating attention, fatigue, and frustration. This methodology treats **attention as a design constraint** (minimizing friction, confusion, and monotony) and **learning as the primary objective**, never claiming that any worksheet format guarantees excitement or focus.
3. **No Automated Guarantee of Educational Quality:** Passing all deterministic software checks (`DET`) and AI-assisted checks (`AI`) filters out structural, factual, and layout defects, but **does not guarantee educational quality or child comprehension**. Ongoing human review and observational child testing (`HUM`) remain essential.

### 2.3 Primary Input Key: Non-Overlapping Grade Bands (`[Mandatory V1 Product Constraint]`)
To eliminate ambiguous or overlapping age ranges, all rules, timing weights, and ergonomic specifications in Version 1.1 are indexed by **four non-overlapping Grade Bands**. Typical approximate ages are listed for reference only; when a parent selects a grade (or when the system infers it from the curriculum PDF), the software maps the lesson deterministically to one of these four keys:

| Grade Band Key | Target School Grades | Reference Age Range (Non-Overlapping) | Primary Developmental Profile |
| :--- | :--- | :--- | :--- |
| **`G1_2`** | **Grades 1–2** | Ages 6–7 | Emergent/early readers; developing fine-motor control; requires large ruled lines, minimal writing, and heavy visual scaffolding. |
| **`G3_5`** | **Grades 3–5** | Ages 8–10 | Developing instructional reading fluency; capable of short-phrase writing, diagram labelling, and guided multi-step procedures. |
| **`G6_8`** | **Grades 6–8** | Ages 11–13 | Fluent readers; capable of abstract rules, multi-step symbolic procedures, error analysis, and 1–2 sentence causal explanations. |
| **`G9_PLUS`** | **Grades 9+** | Ages 14+ | Advanced readers; capable of formal notation, multi-variable problem solving, and concise analytical synthesis. |

## 3. Core Teaching Rules & Real-World Learner Robustness

Real-world children vary widely in reading ability, prior knowledge, attention span, and confidence. Because Version 1.1 operates without student profiles, every generated worksheet embeds universal design buffers directly on the page.

### Rule 1: Source Grounding, Multimodal Extraction, and Traceability
* **Classification:** `[Mandatory V1 Product Constraint]`
* **Requirement:**
  1. **Multimodal Source Ingestion (Supporting Diagram-Heavy PDFs):** The ingestion pipeline extracts both text blocks and visual/diagram content (via OCR and vision-language descriptions) from the uploaded curriculum PDF, indexing each extracted paragraph, equation, table, or diagram as a numbered **Source Unit (`SRC-P{page}-U{index}`)**. A diagram-heavy or math-heavy PDF with fewer than 50 words of prose is **valid and accepted** provided multimodal extraction identifies at least one coherent curriculum concept, visual model, or worked example. Generation halts for source insufficiency *only* when both text and visual extraction fail to recover a usable instructional topic (e.g., blank, corrupted, or unreadable scans).
  2. **Explicit Separation of Source Claims vs. Pedagogical Scaffolding:**
     * **Source-Grounded Claims & Terminology:** Every domain fact, definition, formula, historical date, classification, and technical term taught in the lesson must be stored in the lesson JSON with a `source_unit_ids` array pointing to the specific `SRC-...` unit(s) that support it. The system must never invent unsupported domain facts or silently introduce external terminology.
     * **Generated Pedagogical Scaffolding:** The system may generate original instructional framing—including curiosity hooks, step-by-step worked breakdowns, new numerical values/scenarios for practice problems (following the exact rule in the cited `SRC-...` unit), and everyday analogies—provided that any analogy is explicitly marked (`is_analogy: true`, phrased as *"Think of it like..."*) and is **never tested as a literal curriculum fact** in *Apply* or *Recall*.
  3. **Transparent Handling of Incomplete Curriculum PDFs:** If an uploaded PDF references a sub-topic without providing enough information to teach it (e.g., listing a review question whose explanation was on an un-uploaded page), the system must restrict the lesson to the concepts that *are* supported in the PDF and state the covered scope clearly on Page 1 and Page 3.
* **Why It Matters:** Parents trust the system to teach the school's actual curriculum accurately, including visual/diagrammatic handouts, without hallucinating outside facts.
* **How Enforced in V1.1:** Deterministic check **`DET-02`** (verifies valid `source_unit_ids` references and multimodal topic presence) + AI-assisted check **`AI-01`** (verifies factual entailment against cited `SRC` units, checks that practice items follow the source method, and confirms analogies are not tested as facts).

### Rule 2: First-Time Learning and Prerequisite Completeness
* **Classification:** `[Evidence-Informed Principle]` + `[Mandatory V1 Product Constraint]`
* **Requirement:** Assume the child is learning the target material for the first time:
  1. **Zero Unexplained Domain Terms:** Every technical term, symbol, or unit used in Stages 2–5 must either be explicitly defined and illustrated in *Discover* or belong to foundational knowledge at least one grade band below the target grade.
  2. **Secondary Skill Buffer:** When teaching a new concept (e.g., a physics relationship or multi-step method), keep secondary arithmetic and general reading vocabulary at or below `Target_Grade - 1` complexity so peripheral calculation or decoding struggles do not block concept learning.
  3. **Pronunciation Guides:** Newly introduced domain terms of $\ge 4$ syllables (or non-phonetic roots) must include a simple inline pronunciation guide on first mention (e.g., **metamorphosis** *[met-uh-MOR-fuh-sis]*).
* **Why It Matters:** Skipping intermediate definitions or using difficult secondary numbers causes novices to stall and guess.
* **How Enforced in V1.1:** AI-assisted check **`AI-02`** (audits Stages 2–5 against Stage 1 definitions and checks secondary vocabulary/arithmetic complexity).

### Rule 3: Low-Friction Instructions and Uniform `worked_start` (`Ex:`) Modelling
* **Classification:** `[Evidence-Informed Principle]` (Extraneous Load Reduction) + `[Provisional V1 Heuristic — Requires Testing]` (Word caps)
* **Requirement:** Make every activity effortless to understand and start without adult explanation:
  1. **Direct Imperative Syntax:** Write instructions using concrete *Action–Object–Location* phrasing (e.g., *"Draw a line from each planet in Column A to its description in Column B"*).
  2. **Instruction Sentence Caps:** Each instruction sentence must contain at most **2 sequential action verbs** and stay within grade-band word limits:
     * **`G1_2`:** $\le 12\text{ words}$ per sentence.
     * **`G3_5`:** $\le 18\text{ words}$ per sentence.
     * **`G6_8` & `G9_PLUS`:** $\le 22\text{ words}$ per sentence.
  3. **Authoritative Definition & Rules for `worked_start` (`Ex:`):**
     * A `worked_start` is a **dedicated, ungraded demonstration element (`Item 0 / Ex:`)** rendered in light grey simulated pencil script (`Done for you`) that visually models the required pencil action before the child begins the scored items.
     * Because `worked_start` is an ungraded visual example, it is **never counted** toward the 7–15 scored student items, never subtracted from required distractors, and never generated by stealing a scored student question.
     * **Applicability Across Activity Mechanics:**
       * **Multi-Item Structured Mechanics (`M2_ASYMMETRIC_MATCH`, `M3_DIAGRAM_LABEL`, `M4_CATEGORY_SORT`, `M7_RULE_PATH`):** Must always include an explicit `worked_start` object showing 1 pre-drawn connection line, 1 pre-filled diagram callout, 1 pre-sorted item, or 1 pre-traced starting step.
       * **Step-Completion & Error-Analysis Mechanics (`M5_FADED_STEP`, `M6_SPOT_MISTAKE`):** Must include a `worked_start` consisting of either a pre-completed `Ex:` item or **explicit Step-1 visual modelling** (in `M5`, Step 1 is fully worked and labeled `Step 1 [Done for you]`; in `M6`, the first valid line or an example annotation is marked in grey pencil script to show how to circle and correct the error).
       * **Direct Selection & Open Framing Mechanics (`M1_ANNOTATION`, `M8_MODEL_SKETCH`, `M9_SHORT_SYNTHESIS`):** Do not require a separate `Ex:` problem; instead, `M1` bolds the action verb (`**Circle**`), `M8` provides a pre-drawn reference frame/starter element, and `M9` provides a sentence starter (`G1_2` and `G3_5`) or a target keyword checklist (`Use: [ ] term1 [ ] term2`).
* **Why It Matters:** Children frequently freeze at a new worksheet table or grid because they are unsure what physical mark is expected. A consistent visual `Ex:` removes startup confusion.
* **How Enforced in V1.1:** Deterministic check **`DET-03`** (validates instruction sentence word counts and checks that every `M2–M7` block contains a non-null `worked_start` object separate from the scored `items` array) + AI-assisted check **`AI-03`** (verifies instruction clarity and `worked_start` alignment).

### Rule 4: Active Pencil Participation and Manageable Reading Spans
* **Classification:** `[Evidence-Informed Principle]` (Active Encoding) + `[Provisional V1 Heuristic — Requires Testing]` (Word caps)
* **Requirement:**
  1. **Immediate First Pencil Action:** The opening curiosity hook in *Discover* must lead to a simple, high-confidence observation mark (e.g., circling a feature on a contrasting pair or worked example) after no more than **$35\text{ words}$ (`G1_2`)**, **$50\text{ words}$ (`G3_5`)**, or **$65\text{ words}$ (`G6_8` / `G9_PLUS`)** of introductory text (corresponding to $\le 60\text{ seconds}$ of reading and inspection).
  2. **Authoritative Passive Reading Span Ceiling:** No continuous block of instructional prose anywhere in the lesson may exceed the following word ceilings without an interleaved pencil action:
     * **`G1_2`:** Maximum **$45\text{ words}$**.
     * **`G3_5`:** Maximum **$80\text{ words}$**.
     * **`G6_8` & `G9_PLUS`:** Maximum **$120\text{ words}$**.
* **Why It Matters:** Breaking explanations into short blocks followed immediately by a pencil action prevents passive eye-scanning and maintains attention.
* **How Enforced in V1.1:** Deterministic check **`DET-04`** (counts words in the opening hook before `item[0]` and in every continuous prose block between student actions).

### Rule 5: Robustness Against Confusion, Boredom, Frustration, Careless Mistakes, and Shame
* **Classification:** `[Evidence-Informed Principle]` + `[Mandatory V1 Product Constraint]`
* **Requirement:**
  1. **Visual Dual-Coding (Anti-Confusion):** In *Discover*, pair concise text with an annotated diagram, sequence strip, or visual comparison table where callout labels ($\le 15\text{ words}$ per label) sit directly adjacent to the visual feature rather than in a separate numbered legend.
  2. **Mechanic Variation Without Objective Drift (Anti-Boredom):** Use at least **3 distinct paper mechanics** across the lesson, with no two consecutive activity blocks sharing the same mechanic, while keeping all blocks anchored to the same learning objective.
  3. **Low-Floor Entry & Inline Hint Pointers (Anti-Frustration):** Ensure Stage 1 and Stage 2 Item 1 offer high first-try success, and include a brief, non-stigmatizing reference pointer in Stages 3 and 4 (e.g., *"Hint: Look back at Step 1 Box B"*) so a stuck child knows where to look without calling a parent.
  4. **Careless-Mistake Guards:**
     * **No Negative-Stem Trick Questions:** Do not ask questions where the child must select a *false* or *excluded* statement (e.g., *"Which of the following is NOT true?"* or *"All of these EXCEPT..."*). Natural negation within explanations or domain facts (*"Sponges do not have backbones"*) is permitted.
     * **Pre-Printed Units & Structured Workspaces:** Always pre-print measurement units inside numerical answer blanks (`___ cm`) and provide structured step boxes for multi-step calculations.
  5. **Psychological Safety (Zero Shame, Timers, or Manipulative Rewards):**
     * Never display countdown timers, speed challenges (*"Finish in 15 minutes!"*), point/score boxes (`Score: ___/10`), manipulative extrinsic rewards, or condescending difficulty labels (*"This is easy!"*).
     * Frame error-spotting tasks (`M6_SPOT_MISTAKE`) around a fictional third-person peer (*"Sam tried solving this problem, but made one mix-up..."*) so the child critiques an external error safely.
* **Why It Matters:** Protecting confidence and eliminating trick questions keeps real-world children engaged through challenging steps.
* **How Enforced in V1.1:** Deterministic check **`DET-05`** (enforces mechanic diversity, pre-printed unit fields, and blocks UI score/timer patterns) + Contextual AI checks **`AI-03`** and **`AI-04`** (detects negative-stem trick questions, verifies supportive tone, and checks third-person error framing and hint pointers without falsely blocking domain terms like *"simple machines"* or *"boiling point"*).

### Rule 6: Genuine Understanding Over Mechanical Copying
* **Classification:** `[Evidence-Informed Principle]` (Retrieval Practice & Transfer) + `[Mandatory V1 Product Constraint]`
* **Requirement:**
  1. **Ban on Non-Conceptual Busywork:** Word searches, anagrams, letter-substitution ciphers, unlabelled mazes, and decorative coloring tasks are prohibited.
  2. **Asymmetric Matching & Word Banks:** Every matching task (`M2`) and word-bank task (`M3`) must include **at least 1 extra plausible distractor option** among the student-solved options ($|\text{Student Options}| \ge |\text{Student Prompts}| + 1$) so the last item cannot be solved by elimination.
  3. **Contextual Anti-Copying & Page-2 Recall Isolation:** Questions in Stages 2–5 must paraphrase *Discover* explanations rather than using verbatim fill-in-the-blank sentences. Furthermore, all *Discover* explanations are placed on **Student Page 1**, while Stage 5 (*Recall*) is placed on **Student Page 2** with a top banner instructing single-sided users: *"Flip Page 1 face-down before starting Step 5 (Memory Check)!"*
* **Why It Matters:** Prevents students from completing the worksheet by copying visible sentence patterns or guessing the last remaining word-bank choice.
* **How Enforced in V1.1:** Deterministic check **`DET-06`** (enforces approved mechanic enums, verifies $|\text{Student Options}| \ge |\text{Student Prompts}| + 1$ excluding `worked_start`, and verifies Page 1 vs. Page 2 stage placement) + AI-assisted check **`AI-05`** (evaluates prompts contextually to ensure they require comprehension rather than verbatim copying, and checks that sub-items vary meaningful parameters).

### Rule 7: Print-First Autonomy and Landscape A4 Ergonomics
* **Classification:** `[Mandatory V1 Product Constraint]` + `[Provisional V1 Heuristic — Requires Testing]` (Dimensions)
* **Requirement:**
  1. **Pencil-and-Paper Only:** Student activities must require only the 2 printed Landscape A4 pages ($297\text{ mm} \times 210\text{ mm}$) and a standard graphite pencil—no scissors, glue, external rulers, colored pencils, dice, or screens.
  2. **Monochrome-Safe Visuals:** All diagrams and visual elements must remain clear when printed in black-and-white/greyscale, using distinct patterns (stripes, dots, cross-hatching), line weights, and direct text labels rather than relying on color hue to distinguish features.
  3. **Grade-Appropriate Handwriting & Layout Sizing:**
     * **`G1_2`:** Minimum **$12\text{ mm}$** write-in line height (with dashed midline); $\ge 14\text{ pt}$ body font.
     * **`G3_5`:** Minimum **$9\text{ mm}$** write-in line height; $\ge 12\text{ pt}$ body font.
     * **`G6_8` & `G9_PLUS`:** Minimum **$7.5\text{ mm}$** write-in line height; $\ge 10.5\text{ pt}$ body font.
     * **Visual Breathing Room:** Content containers (cards, text boxes, tables, diagrams) must occupy **$\le 70\%$ of the page canvas area** (leaving $\ge 30\%$ open margins, gutters, and padding) with zero text clipping or page overflow.
* **Why It Matters:** Ensures legibility, comfortable handwriting space, and reliable printing on any home monochrome printer.
* **How Enforced in V1.1:** Deterministic check **`DET-07`** (verifies CSS typography/line heights, 2 student pages + 1 answer key page at $297\text{ mm} \times 210\text{ mm}$, zero DOM box-model overflow, and $\le 70\%$ content box area) + Contextual AI check **`AI-03`** (ensures instructions never ask the student to use external tools or identify items by color alone, without falsely blocking domain terms like *"red blood cells"*).

### Rule 8: Answerability and Separate Page 3 Parent Answer Key
* **Classification:** `[Mandatory V1 Product Constraint]`
* **Requirement:** Every scored student item on Pages 1–2 must have a clear, unambiguous target answer (or explicit evaluation criteria for synthesis/sketch items) supported by the lesson content. **Page 3 (Parent Answer Key & Scope Guide)** is generated as a separate page containing:
  1. The canonical answer for every scored item.
  2. Acceptable alternative phrasings for short-answer items.
  3. A 1-sentence plain-language explanation of *why* the answer is correct.
  4. A transparent Scope & Non-Guarantee Note stating which slice of the uploaded curriculum was covered and reminding the parent that a single 15-minute lesson builds initial comprehension rather than permanent mastery.
* **Why It Matters:** Gives parents a fast, self-contained grading guide and prevents student frustration from vague questions.
* **How Enforced in V1.1:** Deterministic check **`DET-08`** (verifies 1-to-1 item ID coverage and required rubric fields on Page 3) + AI-assisted check **`AI-06`** (an independent AI solver attempts Pages 1–2 without access to Page 3 or the source PDF to flag any ambiguous or unanswerable items).

## 4. Reusable Lesson Architecture, Sequence Variants & Page Layout

### 4.1 Canonical Five-Stage Spine and Fixed 2-Page Student Layout
Every Version 1.1 lesson includes all five functional stages (**Discover, Reinforce, Vary, Apply, Recall**) distributed across a fixed **2-Page Landscape A4 Student Worksheet** (plus Page 3 Parent Answer Key):

| Stage | Page Location | Pedagogical Purpose | Support Level | Scored Sub-Items (`[Provisional V1 Heuristic]`) | Target Stage Duration (`[Provisional V1 Heuristic]`) | Max Block Duration Cap |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Header & Setup** | Page 1, Top Banner | State lesson title, scope banner (*"Part 1 of N"*), and orient the child. | — | 0 scored items | **$1.0\text{ min}$** (Fixed overhead) | — |
| **1. Discover** | Page 1, Left Zone | Spark curiosity with a short hook, present a dual-coded visual + verbal explanation, and walk through a complete worked example with a guided observation mark. | **Maximum:** Complete worked model provided; child marks/notices a key feature. | **1–2** guided observation items | **$3.0\text{ min}$** | **$\le 3.5\text{ min}$** |
| **2. Reinforce** | Page 1, Right Zone | Consolidate basic comprehension of the definition, rule, or steps using high-support scaffolding and a grey `Ex:` Worked Start. | **High:** Word bank (with $\ge 1$ distractor), faded final step, or asymmetric matching. | **2–4** scaffolded items | **$3.0\text{ min}$** | **$\le 3.5\text{ min}$** |
| **3. Vary** | Page 2, Top-Left Zone | Practise the same concept in a shifted format, reverse direction, or third-person *Spot-the-Mistake* activity. | **Moderate:** Format shifted; includes inline reference pointer (*"Check Step 1"*). | **2–3** varied items | **$2.5\text{ min}$** | **$\le 3.5\text{ min}$** |
| **4. Apply** | Page 2, Top-Right / Center Zone | Use the knowledge to solve a realistic problem or explain a novel scenario in a structured workspace. | **Low:** Workspace grid, pre-printed units, or sentence stem provided; no word bank. | **1–2** application problems | **$3.5\text{ min}$** | **$\le 4.5\text{ min}$** |
| **5. Recall** | Page 2, Bottom-Right Isolated Box | Retrieve the core concept or rule from memory without copying from Page 1. Includes banner: *"Flip Page 1 face-down before Step 5!"* | **Zero Content Hints:** Isolated on Page 2; cue-free retrieval or *"Teach It Back"* summary. | **1–2** retrieval prompts | **$2.0\text{ min}$** | **$\le 3.5\text{ min}$** |
| **TOTAL** | **Pages 1–2** *(+ Page 3 Key)* | **Initial Encoding $\rightarrow$ Guided Practice $\rightarrow$ Transfer & Retrieval** | **Progressive Fade to Cue-Free Recall** | **7–15 total scored items** | **$15.0\text{ min}$ Target** *(Corridor: $13.0\text{–}16.5\text{ min}$)* | **$\le 16.5\text{ min}$ Total** |

*Optional Fast-Finisher Buffer:* Page 2 may include one ungraded footer box labeled **`[Optional Bonus Thought]`** with a 1-sentence *"What if?"* reflection question. It is excluded from the 7–15 scored item count and the 15-minute timing calculation.

### 4.2 Authoritative Stage Sequence Variants (Resolving Sequence, Block Count, and Layout Rules)
To accommodate different curriculum subjects without contradicting page layout or block-count validation rules, Version 1.1 defines **four valid sequence variants**. Every variant contains all five functional stage types (`Discover, Reinforce, Vary, Apply, Recall`), keeps all `Discover` and `Reinforce` blocks on **Page 1**, places all `Vary`, `Apply`, and `Recall` blocks on **Page 2**, and totals **7 to 15 scored items**:

| Variant ID & Domain Type | Exact Block Sequence & Page Assignment | Block Count | Scaffolding Fade Rule (`[Evidence-Informed Principle]`) |
| :--- | :--- | :--- | :--- |
| **`V1_CONCEPTUAL`**<br>*Conceptual Science, History, Social Studies, Reading* | **Page 1:** `[1] Discover → [2] Reinforce`<br>**Page 2:** `[3] Vary → [4] Apply → [5] Recall` | **5 blocks** | Strict monotonic fade across all 5 blocks:<br>`Discover > Reinforce > Vary > Apply > Recall (0)`. |
| **`V2_PROCEDURAL`**<br>*Procedural Math Operations & Grammar Rules* | **Page 1:** `[1] Discover (Worked Example) → [2] Reinforce (Faded Step)`<br>**Page 2:** `[3] Apply (Forward Execution) → [4] Vary (Reverse / Spot-Mistake) → [5] Recall (Rule Summary)` | **5 blocks** | Novices stabilize forward execution (`Apply`) before tackling reversed parameters or error-spotting (`Vary`). Both `Apply` and `Vary` have lower support than `Reinforce` and higher support than `Recall (0)`. |
| **`V3_INQUIRY`**<br>*Counter-Intuitive Phenomena & Inquiry Topics* | **Page 1:** `[1] Discover (Opens with 2-Case Prediction Hook + Model Resolution) → [2] Reinforce`<br>**Page 2:** `[3] Vary → [4] Apply → [5] Recall` | **5 blocks** | The 30-second contrasting-case prediction is **Item 1 inside Block 1 (`Discover`)** on Page 1, immediately resolved by the worked model in `Discover`, followed by the canonical fade `Discover > Reinforce > Vary > Apply > Recall (0)`. |
| **`V4_TAXONOMY`**<br>*Classification Sets & Dense Vocabulary (3–5 Terms)* | **Page 1:** `[1A] Discover Part A → [2A] Reinforce Part A → [1B] Discover Part B → [2B] Reinforce Part B`<br>**Page 2:** `[3] Vary (Contrast A vs. B) → [4] Apply → [5] Recall` | **7 blocks** *(4 compact blocks on Page 1; 3 on Page 2)* | Splits 3–5 new terms into two bite-sized micro-cycles on Page 1 (`1A→2A` and `1B→2B`, each with $1\text{–}2$ items) to prevent working-memory overload, then integrates A and B on Page 2 (`Vary > Apply > Recall (0)`). Total scored items across all 7 blocks remain within **$7\text{–}15\text{ items}$**. |

## 5. Paper-Based Activity Taxonomy & Grade-Band Ergonomics

### 5.1 Approved Paper-and-Pencil Activity Taxonomy (`[Mandatory V1 Product Constraint]`)
Every activity block must use one of the 9 approved paper mechanics below. Across a lesson, at least **3 distinct mechanics** must be used, and **no two consecutive blocks** may use the same mechanic.

| Mechanic Enum | Activity Description | Permitted Stages | `worked_start` (`Ex:`) Rule | Specific Design & Anti-Gaming Rules |
| :--- | :--- | :--- | :--- | :--- |
| **`M1_ANNOTATION`** | Circle, underline, or tick target features on a diagram, worked example, or contrasting pair. | *Discover*, *Reinforce*, *Vary* | Not required (`**Circle**` verb bolded). | In *Discover* hooks/models, **2 contrasting cases** are permitted (e.g., Ship A vs. Nail B). In *Reinforce* and *Vary*, provide **$\ge 3$ selectable targets** spaced $\ge 6\text{ mm}$ apart so selection is never a 50/50 guess. |
| **`M2_ASYMMETRIC_MATCH`** | Draw pencil lines connecting prompts in Column A to options in Column B. | *Reinforce*, *Vary* | **Required:** 1 pre-drawn grey `Ex:` connection line. | **Asymmetric after `Ex:`:** Excluding the pre-drawn `Ex:` pair, Column B must have $\ge 1$ extra distractor option ($|\text{Student Options}| \ge |\text{Student Prompts}| + 1$). Max 4 student prompts. |
| **`M3_DIAGRAM_LABEL`** | Write terms or draw directional arrows into callout boxes on a system/process diagram. | *Discover*, *Reinforce*, *Vary*, *Apply* | **Required:** Box 0 pre-filled in grey `Ex:` script. | In *Discover/Reinforce*, include a Word Bank with $\ge 1$ extra distractor ($|\text{Bank}| \ge |\text{Blank Boxes}| + 1$). In *Apply*, omit the Word Bank. |
| **`M4_CATEGORY_SORT`** | Sort a pool of 3–6 items into a 2- or 3-column table or Venn diagram. | *Reinforce*, *Vary* | **Required:** 1 item pre-sorted in grey `Ex:` script. | Allow sorting via short 1–2 word labels or letter codes (`A, B, C`) to minimize handwriting fatigue. |
| **`M5_FADED_STEP`** | Complete missing intermediate or final step(s) in a multi-step math or rule procedure. | *Discover*, *Reinforce*, *Apply* | **Required:** Step 1 shown fully worked (`Step 1 [Done for you]`). | Fade support progressively (leave final step blank in *Reinforce*; leave 2 steps blank in *Apply*). Pre-print operators (`=`, `+`) and measurement units inside answer blanks. |
| **`M6_SPOT_MISTAKE`** | Identify and fix a realistic misconception in a fictional peer's worked solution. | *Vary*, *Apply* | **Required:** Pre-marked `Ex:` callout on Step 1 or sample fix. | Frame in neutral third person (*"Maya wrote..."*). Require two actions: (1) circle the faulty step, and (2) write the corrected step or reason. |
| **`M7_RULE_PATH`** | Trace a path through a grid/bridge where valid moves follow the curriculum rule. | *Vary*, *Apply* | **Required:** First step pre-traced with a grey `Ex:` arrow. | Every branch point must require applying the target curriculum rule; dead ends provide immediate self-correction. |
| **`M8_MODEL_SKETCH`** | Draw simple arrows, particles, or bar models inside a pre-framed reference box. | *Apply*, *Recall* | Pre-drawn reference frame / starter element. | Specify exact countable criteria (*"Draw 4 arrows to show..."*) inside a pre-drawn container so artistic talent is never assessed. |
| **`M9_SHORT_SYNTHESIS`** | Complete a causal sentence frame or write a 1–2 sentence *"Teach It Back"* explanation. | *Apply*, *Recall* | Sentence stem (`G1_2`/`G3_5`) or keyword checklist (`G6_8`+). | Provide ruled baselines and a target keyword checklist (`Use: [ ] term1 [ ] term2`). For `G1_2` and `G3_5`, provide a structured sentence starter (*"This happens because..."*). |

### 5.2 Authoritative Grade-Band Limits Table (`[Provisional V1 Heuristic — Requires Testing]`)

All four non-overlapping grade bands are governed by this single unified parameter table:

| Parameter | `G1_2` (Grades 1–2) | `G3_5` (Grades 3–5) | `G6_8` (Grades 6–8) | `G9_PLUS` (Grades 9+) |
| :--- | :--- | :--- | :--- | :--- |
| **Max Words Before First Pencil Action** *(in Discover Hook)* | **$35\text{ words}$** | **$50\text{ words}$** | **$65\text{ words}$** | **$65\text{ words}$** |
| **Max Passive Reading Span** *(words between pencil actions)* | **$45\text{ words}$** | **$80\text{ words}$** | **$120\text{ words}$** | **$120\text{ words}$** |
| **Max Instruction Sentence Length** | **$12\text{ words}$** | **$18\text{ words}$** | **$22\text{ words}$** | **$22\text{ words}$** |
| **Max Total Student Handwriting Volume** *(across entire lesson)* | **$\le 15\text{ words}$** | **$\le 40\text{ words}$** | **$\le 65\text{ words}$** | **$\le 80\text{ words}$** |
| **Max Handwriting Motor Time Share** ($T_{\text{write}} / T_{\text{stages}}$) | **$\le 30\%$** | **$\le 30\%$** | **$\le 30\%$** | **$\le 30\%$** |
| **Minimum Write-In Line Height** *(Landscape A4)* | **$12\text{ mm}$** *(dashed midline)* | **$9\text{ mm}$** | **$7.5\text{ mm}$** | **$7.5\text{ mm}$** |
| **Minimum Body Font Size** | **$14\text{ pt}$** | **$12\text{ pt}$** | **$10.5\text{ pt}$** | **$10.5\text{ pt}$** |
| **Instructional Reading Speed ($\text{WPM}_{\text{read}}$)** | **$35\text{ WPM}$** ($1.71\text{ s/wd}$) | **$70\text{ WPM}$** ($0.86\text{ s/wd}$) | **$110\text{ WPM}$** ($0.55\text{ s/wd}$) | **$135\text{ WPM}$** ($0.44\text{ s/wd}$) |
| **Handwriting Speed ($\text{WPM}_{\text{write}}$)** | **$5\text{ WPM}$** ($12.0\text{ s/wd}$) | **$11\text{ WPM}$** ($5.45\text{ s/wd}$) | **$17\text{ WPM}$** ($3.53\text{ s/wd}$) | **$22\text{ WPM}$** ($2.73\text{ s/wd}$) |

## 6. Simplified 15-Minute Timing Model & Safe Adjustment Rules

### 6.1 Practical 4-Component Timing Calculation (`[Provisional V1 Heuristic — Requires Testing]`)
To make timing calculation simple, deterministic, and free of subjective visual sub-classifications, Version 1.1 computes predicted duration $T_{\text{lesson}}$ directly from four countable JSON properties:

$$T_{\text{lesson}} = T_{\text{orientation}} + \sum_{k=1}^{K} \left( T_{\text{read}}(k) + T_{\text{visual}}(k) + T_{\text{items}}(k) + T_{\text{write}}(k) \right)$$

Where Active Stage Time is $T_{\text{stages}} = T_{\text{lesson}} - T_{\text{orientation}}$, and for each activity block $k \in \{1 \dots K\}$:
1. **$T_{\text{orientation}}$ (Fixed Setup & Transition Overhead):** **$60\text{ seconds}$ ($1.0\text{ min}$)** per lesson across all grade bands.
2. **$T_{\text{read}}(k)$ (Block Reading Time):** $\frac{\text{Total Student-Facing Printed Words in Block } k}{\text{WPM}_{\text{read}}(\text{grade\_band})}$ (using Section 5.2 speeds).
3. **$T_{\text{visual}}(k)$ (Diagram & Worked-Model Inspection Time):** Fixed **$30\text{ seconds}$** per instructional diagram, data table, or multi-step worked example model present in Block $k$.
4. **$T_{\text{items}}(k)$ (Combined Cognitive Deliberation + Discrete Pencil Action Time per Scored Sub-Item):**
   * **Discover item** (guided observation mark): **$15\text{ sec}$** per item.
   * **Reinforce item** (scaffolded match/sort/label/step): **$25\text{ sec}$** per item.
   * **Vary item** (shifted format / spot-the-mistake): **$35\text{ sec}$** per item.
   * **Apply item** (independent problem / scenario): **$55\text{ sec}$** per item (plus **$+20\text{ sec}$** if `mechanic_type == M8_MODEL_SKETCH`).
   * **Recall item** (cue-free retrieval check): **$45\text{ sec}$** per item (plus **$+20\text{ sec}$** if `mechanic_type == M8_MODEL_SKETCH`).
   *(Note: Ungraded `worked_start` examples and the optional bonus footer are excluded from $T_{\text{items}}$).*
5. **$T_{\text{write}}(k)$ (Handwriting Execution Time):** $\frac{\text{Expected Student Written Words in Block } k}{\text{WPM}_{\text{write}}(\text{grade\_band})}$ (using Section 5.2 speeds, where a multi-digit number or symbolic equation step counts as 1 written word).

### 6.2 Timing Corridor & Stage Balance Constraints (`[Provisional V1 Heuristic — Requires Testing]`)
Every generated lesson must satisfy:
1. **Total Duration Corridor:** $13.0\text{ minutes} \le T_{\text{lesson}} \le 16.5\text{ minutes}$ (Target: $15.0\text{ minutes}$).
2. **Per-Block Duration Cap:** Stages 1, 2, 3, and 5 blocks must each be **$\le 3.5\text{ minutes}$** ($210\text{ sec}$); Stage 4 (*Apply*) must be **$\le 4.5\text{ minutes}$** ($270\text{ sec}$).
3. **Higher-Order Cognitive Share (*Apply + Recall*):** Stage 4 (*Apply*) + Stage 5 (*Recall*) must account for **$35\%$ to $45\%$ of Active Stage Time** ($0.35 \le \frac{T_{\text{Apply}} + T_{\text{Recall}}}{T_{\text{stages}}} \le 0.45$).

### 6.3 Safe Timing & Overflow Adjustment Hierarchy (Never Arbitrarily Deleting Core Learning)
When a draft lesson falls outside $[13.0, 16.5]\text{ minutes}$, violates the *Apply + Recall* balance, or overflows the 2-page student canvas, the software **must never blindly delete random items in code**. Instead, it triggers a targeted adjustment pass following this strict pedagogical priority order:

| Condition | Safe Pedagogical Adjustment Hierarchy (Executed in Order) |
| :--- | :--- |
| **Case 1: Lesson Too Long ($T_{\text{lesson}} > 16.5\text{ min}$) or Overflows 2 Pages** | **Step 1 (Tighten Text & Motor Load First):** Condense instructional prose and story context by $20\text{–}30\%$, and convert high-handwriting prompts (`M9`) in *Reinforce/Vary* into low-motor mechanics (`M2` matching or `M4` letter-code sorting) while keeping all concepts and stages intact.<br>**Step 2 (Consolidate Redundant Sub-Items Only):** If still $>16.5\text{ min}$, reduce a 4-item block in *Reinforce* or *Vary* to 2–3 items *only* when multiple items test the exact same sub-concept—never dropping any stage below its minimum item count (`Section 4.1`) or removing test coverage of a taught sub-concept.<br>**Step 3 (Narrow Curriculum Scope):** If the lesson still exceeds $16.5\text{ min}$ at minimum item counts, the curriculum slice is too broad. Return to the Scope Slicer and narrow the lesson from 2–3 sub-concepts down to 1 foundational sub-concept. |
| **Case 2: Lesson Too Short ($T_{\text{lesson}} < 13.0\text{ min}$)** | **Step 1 (Deepen Practice & Application):** Add 1 varied practice item to *Vary* (up to 3 items) or 1 problem scenario to *Apply* (up to 2 items) testing a different angle or boundary condition of the taught concept.<br>**Step 2 (Upgrade Cognitive Engagement):** If item counts are already near the upper bound, upgrade a passive recognition item in *Reinforce* or *Vary* into a faded-step completion (`M5`), diagram labelling (`M3`), or error-spotting (`M6`) task. Never pad time by adding filler prose or decorative games. |
| **Case 3: *Apply + Recall* Share Outside $35\%\text{–}45\%$** | **If $< 35\%$:** Trim 1 redundant item or excess prose from *Discover/Reinforce* and add 1 structured step or synthesis prompt to *Apply*.<br>**If $> 45\%$:** Convert an overly long written response in *Apply* to a structured table/diagram completion (`M3`/`M8`) or add 1 scaffolded practice item to *Reinforce*. |

## 7. Common Teaching-Design Failures the System Must Prevent

| Failure ID | Failure Name | Description & Impact on Child | V1.1 Prevention Mechanism |
| :--- | :--- | :--- | :--- |
| **F1** | **The Wall-of-Text Lesson** | Dense paragraphs exceed reading stamina; children skip reading and guess. | **`DET-04`** ($35/50/65$-word opening hook cap + $45/80/120$-word passive reading ceiling). |
| **F2** | **Mechanical Copying ("Ctrl+F")** | Prompts repeat exact sentence frames from a visible explanation; child copies without reading for meaning. | **`DET-06`** (Isolates *Recall* on Page 2 while *Discover* is on Page 1) + **`AI-05`** (Contextual anti-copy check). |
| **F3** | **The Unscaffolded Cliff** | Lesson jumps from a brief definition to a hard open problem with no worked example or faded steps. | **`DET-01`** (Requires 5 stages + `worked_example`) + **`AI-03`** (Verifies progressive scaffolding fade). |
| **F4** | **Decorative Edutainment Bloat** | Word searches, anagrams, unlabelled mazes, or coloring waste time without teaching the concept. | **`DET-05`** (Schema-level restriction to `M1–M9` enums) + **`AI-05`** (Objective alignment check). |
| **F5** | **Unstated Prerequisite or Math Trap** | Lesson uses undefined terms/symbols or difficult decimal/fraction arithmetic not taught in the source. | **`AI-02`** (Audits prerequisite definitions and checks secondary math/vocabulary against `Target_Grade - 1`). |
| **F6** | **Symmetric Elimination Gaming** | A 3-item matching or word-bank task has 3 options, making the final answer automatic by elimination. | **`DET-06`** (Enforces $|\text{Student Options}| \ge |\text{Student Prompts}| + 1$ excluding `worked_start`). |
| **F7** | **Parent-Dependent Instructions** | Complex directions or unfamiliar grids force the child to ask an adult *"What do I do here?"* | **`DET-03`** (Instruction word cap + dedicated grey `Ex:` `worked_start` on `M2–M7`) + **`AI-03`**. |
| **F8** | **Careless-Mistake Trick Questions** | Negative stems (*"Which is NOT..."*), missing units, or ungridded math spaces cause avoidable errors. | **`DET-08`** (Pre-printed units on numerical blanks) + **`AI-03`** (Contextually blocks negative-stem trick questions). |
| **F9** | **Print & Layout Breakdown** | Cramped blanks frustrate writers; color-dependent diagrams fail on monochrome printers; text overflows 2 pages. | **`DET-07`** (DOM box-model overflow check, $\le 70\%$ content box area, grade line heights) + **`AI-03`** (Blocks color-dependent instructions). |
| **F10** | **Shame, Timers, or False Guarantees** | Countdown clocks, point scores, *"Easy!"* labels, or mastery guarantees pressure children and mislead parents. | **`DET-05`** (Blocks UI score/timer fields) + **`AI-04`** (Contextual tone & non-guarantee check). |

## 8. Version 1.1 Technical Verification Architecture

**Foundational Principle:** Automated checks (both deterministic code and AI reviewers) are **defect filters, not guarantees of educational quality**. Version 1.1 separates verification into **Category A (Deterministic Software Checks)**, **Category B (Contextual AI-Assisted Checks)**, and **Category C (Human Validation)**.

### 8.1 Category A: Deterministic Software Checks (`DET-01` to `DET-08`)
Deterministic checks run in application code over the lesson JSON and the headless Chromium DOM layout before PDF export.

| Check ID | 1. What Is Checked | 2. How It Is Checked | 3. Pass / Fail Condition | 4. Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`DET-01`** | **Stage Sequence, Block Counts & Item Counts** | JSON Schema validator checks stage types, variant ID (`V1`–`V4`), block counts, and scored item arrays. | **Pass:** Contains all 5 functional stages (`Discover, Reinforce, Vary, Apply, Recall`) matching an approved Section 4.2 sequence (`5 blocks` for `V1–V3`; `7 blocks` for `V4`); `1 <= scored_items_per_block <= 4` matching stage ranges; `7 <= total_scored_items <= 15`; `Discover` includes a non-empty `worked_example`.<br>**Fail:** Missing stage, invalid sequence, or item count out of bounds. | Return schema violation path to generator for targeted structural repair (Max 2 retries). |
| **`DET-02`** | **Multimodal Source Units & Citation Links** | Code verifies ingested `SRC-P{page}-U{index}` units (from text + vision extraction) and checks `source_unit_ids` arrays in the lesson JSON. | **Pass:** Ingested PDF yields $\ge 1$ valid `SRC` unit (text or diagram); 100% of `core_claims`, `domain_terms`, and `activity_blocks` reference at least one valid `source_unit_id`; `scope_metadata` is populated.<br>**Fail:** Zero extractable `SRC` units (blank/corrupted PDF) or any uncited `core_claim`/`domain_term`. | If PDF has $0$ usable `SRC` units across both text and vision parsing, halt and prompt parent for a readable PDF. Otherwise, bind or regenerate uncited claim. |
| **`DET-03`** | **Instruction Word Caps & Uniform `worked_start` Schema** | Code splits `instruction_text` into sentences, counts words, and checks the `worked_start` object on `M2–M7` blocks. | **Pass:** Every instruction sentence is $\le 12\text{ words}$ (`G1_2`), $\le 18\text{ words}$ (`G3_5`), or $\le 22\text{ words}$ (`G6_8`/`G9_PLUS`); 100% of `M2–M7` blocks contain a non-empty `worked_start` object that is distinct from the scored `items` array.<br>**Fail:** Instruction sentence exceeds word cap or `worked_start` is null/missing on `M2–M7`. | Trigger targeted rewrite of the over-length instruction or generate a dedicated `worked_start` (`Ex:`) item without altering scored `items`. |
| **`DET-04`** | **Opening Hook & Passive Reading Span Caps** | Code counts words in the opening hook before `item[0]` and in every continuous prose block between student actions. | **Pass:** Opening text before first pencil action is $\le 35\text{ words}$ (`G1_2`), $\le 50\text{ words}$ (`G3_5`), or $\le 65\text{ words}$ (`G6_8`/`G9_PLUS`); all continuous prose spans are $\le 45\text{ words}$ (`G1_2`), $\le 80\text{ words}$ (`G3_5`), or $\le 120\text{ words}$ (`G6_8`/`G9_PLUS`).<br>**Fail:** Any prose span exceeds its grade-band ceiling. | Condense the exceeding text block or split it with an interleaved guided observation prompt. |
| **`DET-05`** | **Mechanic Diversity, Non-Duplication & UI Safety Patterns** | Code checks the sequence of `mechanic_type` enums, checks for duplicate item stems/operands within a block, and checks for prohibited UI fields. | **Pass:** Uses $\ge 3$ distinct `M1–M9` enums; no two consecutive blocks use the same `mechanic_type`; zero duplicate prompt strings or identical numerical operand sets within a block; zero UI score/timer patterns (`Score: ___`, `Time limit:`, `Stopwatch`, `word search`, `crossword`).<br>**Fail:** Adjacent duplicate mechanic, duplicate item stem, or prohibited UI pattern. | Regenerate the offending block with an unused mechanic enum or strip prohibited UI fields. |
| **`DET-06`** | **Asymmetric Options & Page-2 Recall Isolation** | Code counts student prompts vs. unmatched student options in `M2` and `M3` (excluding `worked_start`) and verifies page assignments. | **Pass:** $|\text{Student Options}| \ge |\text{Student Prompts}| + 1$ in all `M2` and word-bank `M3` blocks; in `M1` (*Reinforce/Vary*), $|\text{Targets}| \ge 3$; all `Discover` and `Reinforce` blocks are assigned to `page: 1`; all `Vary, Apply, Recall` blocks are assigned to `page: 2` with the *"Flip Page 1 face-down"* banner present.<br>**Fail:** Symmetric options, $<3$ targets in scored `M1`, or incorrect page assignment. | Inject 1 plausible curriculum distractor into options or enforce page assignment rules. |
| **`DET-07`** | **Simplified Timing Model, Handwriting Cap & DOM Box-Model Layout** | Code computes the Section 6.1 timing formula, sums expected written words, and inspects the rendered HTML/CSS DOM in headless Chromium. | **Pass:** $13.0\text{ min} \le T_{\text{lesson}} \le 16.5\text{ min}$; Stages 1,2,3,5 blocks $\le 3.5\text{ min}$ and *Apply* $\le 4.5\text{ min}$; $0.35 \le (T_{\text{Apply}}+T_{\text{Recall}})/T_{\text{stages}} \le 0.45$; written words $\le 15 / 40 / 65 / 80$ and $T_{\text{write}}/T_{\text{stages}} \le 0.30$; compiled output is **2 Student Pages + 1 Answer Key Page** ($297\text{ mm} \times 210\text{ mm}$) with grade CSS fonts/line heights, zero DOM container overflow (`scrollHeight <= clientHeight`), and total content container bounding-box area **$\le 70\%$ of page area** ($\ge 30\%$ open space).<br>**Fail:** Timing, handwriting cap, DOM overflow, or content density violation. | Execute the **Section 6.3 Safe Adjustment Hierarchy** (condensing prose/motor load first, consolidating redundant sub-items second, or narrowing curriculum scope third; or expanding *Vary/Apply* if $<13.0\text{ min}$). |
| **`DET-08`** | **Answer Key & Pre-Printed Unit Completeness** | Code cross-checks every scored `item_id` on Pages 1–2 against the Page 3 `answer_key` array and checks numerical answer fields. | **Pass:** 100% of scored items have a non-empty `canonical_answer`, `parent_explanation`, and (for `M8`/`M9`) `acceptable_variants`; all numerical answer blanks specify a pre-printed `unit` string (when applicable); Page 3 includes the Scope & Non-Guarantee Note.<br>**Fail:** Missing answer key entry, missing explanation, or missing unit field. | Populate missing answer key or unit fields before running Category B checks. |

### 8.2 Category B: Contextual AI-Assisted Quality Checks (`AI-01` to `AI-06`)
**Important Limitation:** Category B checks use an independent, zero-temperature LLM reviewer prompt to evaluate contextual and semantic rules that deterministic code cannot parse. Because AI reviewers can hallucinate or miss subtle flaws, they are treated as **probabilistic quality filters**, never as proof of educational validity.

| Check ID | 1. What Is Checked | 2. How It Is Checked | 3. Pass / Fail Condition | 4. Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`AI-01`** | **Source Claim Grounding & Analogy Quarantine** | Reviewer compares each lesson block's `core_claims`, `domain_terms`, and practice rules against the text and visual descriptions of its cited `SRC-P{page}-U{index}` units. | **Pass:** All taught facts, definitions, formulas, and terms are supported by the cited `SRC` units without contradiction; practice problems apply the exact source method; analogies (`is_analogy: true`) are framed as comparisons and never tested as literal facts in *Apply/Recall*.<br>**Fail:** Unsupported fact, contradiction, external method, or tested analogy detail. | Rewrite the flagged claim/item strictly from the cited `SRC` unit (Max 2 retries). |
| **`AI-02`** | **First-Time Prerequisites & Secondary Complexity** | Reviewer checks whether Stages 2–5 require any domain term, symbol, or operation not explained in *Discover*, and evaluates secondary math/vocabulary difficulty. | **Pass:** Zero unexplained domain terms or symbols in Stages 2–5; secondary calculations and general vocabulary sit at or below `Target_Grade - 1` difficulty; terms $\ge 4$ syllables have inline pronunciation guides.<br>**Fail:** Unexplained prerequisite or overly difficult secondary calculation/wording. | Add the missing definition to *Discover* or simplify the secondary numbers/vocabulary. |
| **`AI-03`** | **Contextual Instruction Clarity, No Trick Stems & Print Autonomy** | Reviewer evaluates all student instructions and question stems in context (avoiding false positives on domain nouns like *"simple machines"* or *"red blood cells"*). | **Pass:** Instructions are concrete, age-appropriate, contain $\le 2$ sequential actions, and align with the `worked_start` (`Ex:`); zero negative-stem trick questions (*"Which is NOT..."* / *"EXCEPT"*); zero instructions requiring external tools (scissors, glue, rulers, colored pencils) or color-dependent identification (*"Circle the red box"*); progressive scaffolding fades appropriately across the chosen Section 4.2 variant.<br>**Fail:** Ambiguous instruction, negative-stem trick question, external-tool/color dependency, or broken scaffolding progression. | Rewrite the flagged instruction/question stem or regenerate the misaligned stage block. |
| **`AI-04`** | **Contextual Tone, Curiosity Hook & Psychological Safety** | Reviewer evaluates the opening hook, peer error-spotting framing (`M6`), inline hint pointers, and overall tone in context. | **Pass:** Opening hook poses a relevant question resolved by the lesson; `M6` attributes errors neutrally to a fictional peer; Stages 3–4 include an inline reference pointer (*"Check Step 1"*); zero shaming, evaluative bragging (*"This is easy!"*), speed pressure, or mastery guarantees.<br>**Fail:** Unrelated hook, condescending/shaming language, missing reference pointer, or mastery guarantee claim. | Rewrite the flagged text segment to restore supportive, neutral framing. |
| **`AI-05`** | **Contextual Anti-Copying & Meaningful Sub-Item Variation** | Reviewer compares Stage 2–5 prompts against Stage 1 text and compares sub-items within each activity block. | **Pass:** Prompts require conceptual comprehension rather than verbatim sentence copying from Stage 1; sub-items within each block vary meaningful parameters (different cases, values, or perspectives) rather than repeating near-identical clones; matching/word-bank distractors are plausible.<br>**Fail:** Prompt is solvable by verbatim copying, sub-items are repetitive clones, or distractors are nonsensical. | Paraphrase the copyable prompt or regenerate redundant sub-items/distractors. |
| **`AI-06`** | **Independent Blind-Solver Answerability Review** | An isolated AI solver prompt is given **only** Student Pages 1–2 (without the source PDF or Page 3 Answer Key) and asked to solve every scored item and flag any ambiguity. | **Pass:** Solver's responses match 100% of the Page 3 `canonical_answer` (or `acceptable_variants`) and flags `0` items as ambiguous, underspecified, or unanswerable from Pages 1–2.<br>**Fail:** Solver arrives at a conflicting answer, identifies multiple valid options where only one is keyed, or flags an item as unanswerable. | Clarify the ambiguous question stem/options or update Page 3 `acceptable_variants`, then re-run `AI-06` (Max 2 retries). |

### 8.3 Bounded Retry Policy & Failure Reporting (`[Mandatory V1 Product Constraint]`)
1. **Targeted Repair (Maximum 2 Retries):** When any `DET` or `AI` check fails, the software localizes the failure to the specific block or item and executes at most **2 targeted repair attempts**, re-running all checks after each attempt.
2. **Hard Stop & Structured Failure Report:** If any blocking check still fails after **2 repair attempts**, the system **blocks delivery of the worksheet** and generates a structured **Failure Report** logging the failed check ID (`DET-xx` / `AI-xx`), the offending block, and a clear user/operator message (e.g., requesting a clearer curriculum scan or flagging the template for human inspection).

### 8.4 Category C: Stateless Human Validation Protocol (`HUM-01` to `HUM-04`)
Because automated checks cannot verify real child comprehension, attention, or physical paper usability, Version 1.1 mandates four practical human validation workflows that operate **without** student profiles, uploaded student work, or adaptive follow-up lessons:

| Validation ID | Quality Evaluated by Humans | Why Automated Checks Are Insufficient | Practical V1.1 Validation Protocol |
| :--- | :--- | :--- | :--- |
| **`HUM-01`** | **Real Child Instruction Comprehension & Startup Autonomy** | Word caps and AI checks cannot guarantee that a 7-year-old will understand a table layout or `Ex:` convention without asking a parent *"What do I do?"* | **Silent-Observer Benchmark Trials:** Test printed benchmark lessons across all 4 grade bands with real children. Observers log any block where a child hesitates $>20\text{ seconds}$ or asks an adult to explain the instructions. Templates with $>15\%$ hesitation are redesigned. |
| **`HUM-02`** | **Real-World Duration & Attention Sustainability** | Section 6.1 timing weights are provisional estimates; only real children show whether a calculated 15-minute lesson actually takes 15 minutes and holds focus. | **Stopwatch Calibration Sessions:** Time $N \ge 10$ children per grade band completing printed benchmark lessons. Use observed median and 75th-percentile durations to recalibrate the reading, item, and handwriting weights in Section 5.2 and Section 6.1. |
| **`HUM-03`** | **Monochrome Diagram Clarity & Physical Pencil/Eraser Usability** | DOM box checks verify layout fit, but cannot judge whether a diagram makes visual sense in black-and-white or whether write-in boxes smudge/tear when erased. | **Weekly Physical Print-and-Solve QA:** Curriculum reviewers print a stratified sample of generated PDFs on standard monochrome printers and complete them by hand with a graphite pencil and eraser. |
| **`HUM-04`** | **Actual First-Time Understanding & Application** | Passing `AI-06` proves a worksheet is logically solvable by an AI, not that a child who was unfamiliar with the topic 15 minutes ago now understands it. | **Post-Worksheet Oral Spot-Check (During Benchmark Trials):** Immediately after a child finishes a benchmark worksheet, an educator removes the sheet and asks 2 brief oral transfer questions. If students complete the sheet accurately but fail the oral check, activity scaffolding is tightened to eliminate surface pattern-matching. |

## 9. Version 1.1 Pre-Delivery Acceptance Checklist

Every generated lesson must pass **Gates 1–6 (Automated Blocking Gates)** before delivery. Gate 7 defines the ongoing human validation requirement.

### Gate 1: Multimodal Source Grounding & Traceability (Blocking)
* [ ] **1.1 Valid Source Units & Citation Links (`DET-02`):** Uploaded PDF yields $\ge 1$ valid `SRC-P{page}-U{index}` unit (via text or vision/diagram extraction); 100% of `core_claims`, `domain_terms`, and `activity_blocks` cite valid `source_unit_ids`; scope metadata is populated.
* [ ] **1.2 Contextual Entailment & Analogy Quarantine (`AI-01`):** AI reviewer confirms zero unsupported domain claims or contradictions, confirms practice problems follow the source method, and verifies analogies (`is_analogy: true`) are never tested in *Apply/Recall*.

### Gate 2: Five-Stage Architecture & Prerequisite Completeness (Blocking)
* [ ] **2.1 Approved Stage Sequence & Item Counts (`DET-01`):** Contains all 5 functional stages (`Discover, Reinforce, Vary, Apply, Recall`) matching an approved Section 4.2 variant (`5 blocks` for `V1–V3`; `7 blocks` for `V4`), with `1–4` scored items per block and **`7–15` total scored items**.
* [ ] **2.2 Worked Model & Prerequisite Closure (`DET-01`, `AI-02`):** `Discover` includes a complete worked example/model; zero unexplained domain terms or symbols appear in Stages 2–5; secondary math/vocabulary is $\le \text{Target\_Grade} - 1$; new terms $\ge 4$ syllables include pronunciation guides.
* [ ] **2.3 Progressive Scaffolding Fade (`AI-03`):** Support fades across the chosen Section 4.2 variant down to zero content hints in *Recall*, and *Vary* shifts format, direction, or error-analysis framing.

### Gate 3: Low-Friction Entry, Clarity & Psychological Safety (Blocking)
* [ ] **3.1 Concise Instructions & Uniform `worked_start` (`DET-03`, `AI-03`):** All instruction sentences obey grade word caps ($\le 12 / 18 / 22\text{ words}$) and verb caps ($\le 2$ actions), and 100% of `M2–M7` blocks contain a dedicated, ungraded grey `Ex:` `worked_start` object.
* [ ] **3.2 Immediate First Mark & Passive Reading Ceilings (`DET-04`):** Introductory text before the first pencil action is $\le 35 / 50 / 65\text{ words}$, and no continuous prose block exceeds $45 / 80 / 120\text{ words}$ without an interleaved pencil action.
* [ ] **3.3 Contextual Guardrails Against Trick Stems & Shame (`DET-05`, `AI-03`, `AI-04`):** Zero negative-stem trick questions, zero UI timers/scores/evaluative labels (*"Easy!"*), neutral third-person framing on `M6_SPOT_MISTAKE`, and inline *"Check Step 1"* hint pointers in Stages 3–4.

### Gate 4: Purposeful Paper Mechanics & Anti-Copy Isolation (Blocking)
* [ ] **4.1 Mechanic Diversity & Approved Taxonomy (`DET-05`):** Uses $\ge 3$ distinct `M1–M9` mechanics with no identical mechanic in consecutive blocks; zero word searches, anagrams, unlabelled mazes, or decorative coloring.
* [ ] **4.2 Asymmetric Options & Non-Repetitive Sub-Items (`DET-05`, `DET-06`, `AI-05`):** Matching (`M2`) and word-bank (`M3`) blocks have $|\text{Student Options}| \ge |\text{Student Prompts}| + 1$ (excluding `worked_start`); scored `M1` blocks have $\ge 3$ targets; sub-items vary meaningful parameters.
* [ ] **4.3 Page-2 Recall Isolation & Contextual Anti-Copying (`DET-06`, `AI-05`):** All `Discover/Reinforce` blocks are on Page 1; all `Vary/Apply/Recall` blocks are on Page 2 with the *"Flip Page 1 face-down"* banner; prompts require comprehension rather than verbatim copying.

### Gate 5: Simplified 15-Minute Timing & Safe Adjustment (Blocking)
* [ ] **5.1 Authoritative Timing Corridor & Stage Balance (`DET-07`):** Calculated $T_{\text{lesson}} \in [13.0, 16.5]\text{ minutes}$ (including $1.0\text{ min}$ orientation); Stages 1,2,3,5 blocks $\le 3.5\text{ min}$ and *Apply* $\le 4.5\text{ min}$; *Apply + Recall* represent $35\%\text{–}45\%$ of Active Stage Time.
* [ ] **5.2 Handwriting Motor Budget (`DET-07`):** Expected student writing is $\le 15 / 40 / 65 / 80\text{ words}$ by grade band (`G1_2` to `G9_PLUS`), and handwriting time $T_{\text{write}}$ is $\le 30\%$ of Active Stage Time.
* [ ] **5.3 Non-Destructive Adjustment Verification (`DET-07`):** Any timing or overflow adjustment followed the Section 6.3 hierarchy without deleting required stages or dropping below minimum item counts.

### Gate 6: Landscape A4 Layout Fidelity & Answerability (Blocking)
* [ ] **6.1 Fixed 2-Page Student Layout & Box-Model Ergonomics (`DET-07`, `AI-03`):** Compiles cleanly to **2 Student Landscape A4 Pages ($297\text{ mm} \times 210\text{ mm}$) + 1 Answer Key Page** with grade-compliant line heights ($12 / 9 / 7.5\text{ mm}$) and font sizes ($14 / 12 / 10.5\text{ pt}$), zero DOM container overflow, $\le 70\%$ content box area ($\ge 30\%$ open space), monochrome-safe visuals, and zero external tool requirements.
* [ ] **6.2 Complete Answer Key & Blind-Solver Review (`DET-08`, `AI-06`):** Every scored item has a complete entry + parent explanation on Page 3, pre-printed units on numerical blanks, honest non-guarantee scope framing, and zero unresolved ambiguity flags from the `AI-06` blind solver.

### Gate 7: Human Validation & Calibration (Operational Requirement)
* [ ] **7.1 Ongoing Human Review (`HUM-01` to `HUM-04`):** Templates and timing weights are validated via silent-observer child trials, stopwatch calibration, post-lesson oral spot-checks, and physical monochrome print audits, with 2-retry failures routed to a structured Failure Report.

## 10. Outstanding Assumptions Requiring Real-World Testing

The following provisional assumptions require empirical validation through the Category C Human Validation Protocol (`HUM-01` to `HUM-04`):

1. **Accuracy of Simplified Grade-Band Timing Weights (Section 5.2 & Section 6.1):** Whether the provisional reading speeds ($35/70/110/135\text{ WPM}$), fixed $30\text{s}$ visual inspection weight, stage item times ($15\text{–}55\text{s}$), and handwriting speeds ($5/11/17/22\text{ WPM}$) accurately predict real-world 13.0–16.5 minute completion times across diverse learners (`HUM-02`).
2. **Single-Sided Printing Compliance with the Page-2 Recall Banner (Rule 6 & Section 4.1):** Whether children working on two single-sided sheets follow the *"Flip Page 1 face-down before Step 5"* instruction, and whether paraphrased synthesis prompts prevent surface copying even if a child glances back (`HUM-01`, `HUM-04`).
3. **Grade 1–2 Startup Autonomy with Visual `worked_start` (`Ex:`) Examples (Rule 3):** Which of the 9 paper mechanics (`M1–M9`) 6-to-7-year-old emergent readers can begin independently using a $\le 12$-word instruction and a grey `Ex:` example without parent help (`HUM-01`).
4. **Monochrome Visual Clarity on Diagram-Heavy Topics (Rule 1 & Rule 7):** Whether automated monochrome SVG/HTML diagrams and extracted PDF figures remain consistently intuitive across subjects when printed on basic home laser/inkjet printers (`HUM-03`).
5. **Parent Reception of Automatic Curriculum Scope Slicing (Section 6.3):** Whether parents uploading multi-lesson curriculum PDFs find the Page 1/Page 3 Scope Note clear and helpful when the generated 15-minute worksheet covers only the first foundational sub-unit.

## 11. Version 1.1 Change Log (Summary of Corrections & Rationale)

| Correction Area | What Changed from V1.0 to V1.1 | Why the Correction Was Necessary |
| :--- | :--- | :--- |
| **1. Stage Sequences, Block Counts & Item Sums** | • Fixed Variant 3 (`V3_INQUIRY`) to have **5 blocks** (embedding the 2-case prediction probe inside Block 1 *Discover*) rather than listing `Vary` twice.<br>• Fixed Variant 4 (`V4_TAXONOMY`) block count from `6` to **`7 blocks`** (`1A, 2A, 1B, 2B` on Page 1 + `3, 4, 5` on Page 2) so the math ($4 + 3 = 7$) matches the stage list.<br>• Adjusted total scored items from `8–15` to **`7–15 items`** so a lesson using the minimum items per stage ($1+2+2+1+1 = 7$) no longer fails `DET-01`.<br>• Permitted **2 contrasting cases** in `M1_ANNOTATION` for *Discover* hooks while retaining $\ge 3$ options in *Reinforce/Vary*. | V1.0 had mathematical contradictions between the stage item ranges (which summed to 7 minimum), the Variant 3/4 stage lists (which had 6 and 7 stages while claiming 5 and 6 blocks), and the `M1` $\ge 3$-option rule (which conflicted with 2-case curiosity hooks). |
| **2. Safe Timing & Overflow Adjustment** | • Replaced the `DET-07` rule *"prune 1 sub-item from Reinforce or Vary"* with the **Section 6.3 Safe Adjustment Hierarchy** (1. condense prose & convert high-motor items to low-motor mechanics; 2. consolidate redundant sub-items without dropping below stage minimums or losing concept coverage; 3. narrow curriculum scope; plus explicit expansion rules when $T_{\text{lesson}} < 13.0\text{ min}$).<br>• Increased *Apply* single-block cap to **$\le 4.5\text{ min}$** (keeping Stages 1,2,3,5 at $\le 3.5\text{ min}$). | Blindly deleting an item in code risked removing the only question testing a sub-concept or violating minimum stage counts, and V1.0 lacked a repair path for lessons under $13.0\text{ minutes}$. |
| **3. Uniform `worked_start` (`Ex:`) Definition & Rules** | • Defined `worked_start` as a **dedicated, ungraded demonstration element (`Item 0 / Ex:`)** across all `M2–M7` structured mechanics.<br>• Removed the buggy `DET-03` fallback (*"Auto-populate `worked_start` from Item 0"*).<br>• Clarified that `M2`/`M3` asymmetry ($|\text{Student Options}| \ge |\text{Student Prompts}| + 1$) is counted *after* excluding the pre-solved `Ex:` item. | Converting a scored item into `Ex:` in V1.0 reduced the student's scored items and broke asymmetric distractor math, and V1.0 listed `Ex:` inconsistently across the taxonomy table. |
| **4. Contextual Validation Over Brittle Keyword Blocklists** | • Removed raw regex bans on words like `NOT`, `simple`, `point`, `cut`, `red`, `green`, `blue`, and `ruler` from `DET-05`/`DET-07`.<br>• Kept deterministic regex strictly for unambiguous UI patterns (`Score: ___`, `Stopwatch`, `word search`) and moved negative-stem trick detection, external-tool requirements, and color-dependent instructions to contextual AI checks (`AI-03`, `AI-04`). | Raw word blocklists falsely rejected legitimate curriculum topics such as *"simple machines"*, *"boiling point"*, *"red blood cells"*, *"green plants"*, or *"cutting a magnet"*. |
| **5. Multimodal Support for Diagram-Heavy PDFs ($<50$ Words)** | • Removed the `DET-02` rule rejecting any PDF with $<50$ extracted words.<br>• Added multimodal ingestion (text + vision/diagram extraction) so diagram-heavy or equation-heavy PDFs are accepted whenever $\ge 1$ coherent instructional `SRC` unit is extracted. | Early-grade worksheets, geometry handouts, and science cycle diagrams often contain $<50$ words of text alongside rich visual models. |
| **6. Source Claim Extraction, Traceability & Verification** | • Defined a clear 3-step pipeline: (1) index PDF text and diagrams into numbered `SRC-P{page}-U{index}` units; (2) separate `core_claims`/`domain_terms` (which must cite `source_unit_ids`) from `pedagogical_scaffolding` (practice numbers and `is_analogy: true` comparisons); (3) verify citation links in `DET-02` and semantic entailment in `AI-01`. | V1.0 required `source_chunk_id` on every fact without specifying how diagram content, practice problem numbers, and analogies were distinguished and verified. |
| **7. Non-Overlapping Grade Bands** | • Replaced overlapping age brackets (`Ages 6–8`, `Ages 8–11`, `Ages 11+`) and inconsistent 3-band vs. 4-band tables with **4 non-overlapping Grade Band keys** (`G1_2` [Ages 6–7], `G3_5` [Ages 8–10], `G6_8` [Ages 11–13], `G9_PLUS` [Ages 14+]) across all tables. | In V1.0, 8-year-olds and 11-year-olds fell into two different bands simultaneously, and Section 5.3 had 3 bands while Section 6.1 had 4 bands. |
| **8. Simplified Repetition, Whitespace & Timing Checks** | • **Repetition:** Replaced brittle 5-gram substring matching with deterministic duplicate-stem/mechanic checks (`DET-05`) + contextual AI anti-copy and variation review (`AI-05`).<br>• **Whitespace:** Replaced rasterized white-pixel counting with DOM box-model verification (`scrollHeight <= clientHeight` and content container area $\le 70\%$ of page area in `DET-07`).<br>• **Timing & First Action:** Unified $T_{\text{visual}}$ to a single $30\text{s}$ weight per visual model, combined item thinking + discrete mark time into a single per-stage weight ($15/25/35/55/45\text{s}$), and enforced first-action immediacy via a deterministic opening word cap ($35/50/65\text{ words}$ in `DET-04`). | Exact 5-gram matching flagged valid domain phrases; white-pixel counting was skewed by shaded boxes and diagram backgrounds; and the V1.0 60-second first-action formula mathematically failed `G1_2` lessons whenever a diagram ($25\text{–}40\text{s}$) was present. |
| **9. Honest Separation of `DET`, `AI`, and `HUM` Checks** | • Explicitly stated in Section 2.2 and Section 8 that no automated check (`DET` or `AI`) guarantees educational quality.<br>• Reframed `AI-06` as an AI-Assisted Answerability & Ambiguity Review rather than an infallible proof. | Ensures engineering and product teams treat automated gates as defect filters that must be paired with human print audits and child testing (`HUM-01` to `HUM-04`). |
