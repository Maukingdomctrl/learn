# Core Teaching Methodology Specification (`CORE_TEACHING_METHODOLOGY.md`)

**Document Status:** Foundational Pedagogical & Verification Specification

**Target Medium:** Printed Landscape A4 Pages + Standard Graphite Pencil (Zero Screen Interaction)

**Target Duration:** \~15 Minutes per Single-Session Lesson

**Learner Context:** First-Time Exposure to Supplied Curriculum Material (Stateless; No Student Profiles or Past Response History)

## Epistemic Framework: Established Science vs. Testable Product Heuristics

To prevent engineering teams from treating arbitrary product thresholds as immutable laws—or conversely, treating foundational cognitive limits as negotiable UI preferences—every rule and parameter in this specification is classified into one of two epistemic categories:

| Epistemic Category | Definition | Examples in This Specification | Governance Rule | 
| ----- | ----- | ----- | ----- | 
| **\[Established Educational Principle\]** | Empirically replicated findings from cognitive psychology, instructional design, and learning sciences. | Working memory limits (Sweller's Cognitive Load Theory), Dual Coding (Paivio), Retrieval Practice / Testing Effect (Roediger & Karpicke), Worked Example Effect, Transfer-Appropriate Processing, Backward Design (Wiggins & McTighe). | **Non-negotiable.** Software architecture must never violate these principles. | 
| **\[Proposed Design Choice — Requires Testing\]** | Product-specific operationalizations, numerical thresholds, timing heuristics, and layout constraints tailored to a 15-minute landscape A4 pencil-and-paper format. | Exact minute allocations per stage, words-per-minute reading multipliers, maximum activity counts per page, minimum bounding-box sizes for handwriting, and specific puzzle formats. | **Tunable via empirical validation.** Must be instrumented and calibrated through observational testing with real children across grade bands. | 

## Section A: Educational Principles Governing This Product

A 15-minute printed lesson cannot—and must not claim to—guarantee permanent mastery of a curriculum unit. Instead, its pedagogical contract is **Successful Initial Encoding and Guided First Application**: taking a child from zero familiarity with a specific curriculum slice to accurate comprehension, initial mental model construction, and successful unaided retrieval within a single focused sitting.

### Rule A1: Strict Source Entailment and Zero Hallucination (Principle 1: Source Accuracy)

* **Classification:** **\[Established Educational Principle\]** (Curriculum Alignment & Epistemic Fidelity) + **\[Proposed Design Choice — Requires Testing\]** (Strict boundary rules on external analogies).

* **Rule Definition:** Every factual claim, definition, formula, historical date, classification, and terminology item taught or assessed in the lesson must be directly entailed by the uploaded curriculum PDF. The system may generate original pedagogical scaffolding (such as everyday analogies, simplified step-by-step breakdowns, or novel practice scenarios), provided that:

  1. All underlying domain facts and vocabulary come strictly from the source PDF.

  2. Any everyday analogy (e.g., comparing an electrical circuit to a water pipe) is explicitly marked as a comparison and never tested as a literal curriculum fact.

  3. If the uploaded PDF is incomplete, contradictory, or missing critical definitions required to teach the concept, the system must flag the gap or restrict the lesson scope to what is explicitly supported rather than silently inventing bridge facts.

* **Why It Matters:** Parents and students rely on this product to prepare for school assessments governed by the uploaded curriculum. Introducing external terminology, alternative calculation methods, or unsupported facts creates interference with classroom instruction, confuses first-time learners, and destroys parent trust.

* **How the Software Verifies Compliance:**

  1. **Atomic Claim Extraction & Entailment Check:** Decompose the generated lesson into atomic factual propositions and terminology tokens. Run a natural language inference (NLI) / citation-grounding pass against the source PDF chunks; every domain statement must map to at least one source span with an entailment score above threshold, and zero contradictions.

  2. **Terminology Whitelist Audit:** Extract all domain-specific nouns and technical terms in the generated lesson and verify that each either appears in the source PDF or belongs to a grade-appropriate general-language baseline lexicon.

  3. **Analogy Quarantine Check:** Verify that no question in the *Apply* or *Recall* stages tests details specific to a generated analogy rather than the source concept.

### Rule A2: Zero Unstated Prerequisite Assumption (Principle 2: First-Time Learning)

* **Classification:** **\[Established Educational Principle\]** (Zone of Proximal Development & Prior Knowledge Activation).

* **Rule Definition:** The system must treat the target curriculum concept as completely new to the child. No concept, symbol, or multi-step procedure may be used inside an explanation or activity before it has either been:

  1. Explicitly established as foundational baseline knowledge for the target grade level (e.g., basic addition when teaching multiplication), or

  2. Explicitly defined, illustrated, and unpacked earlier on the page.

* **Why It Matters:** Novices lack the organized schemas that experts use to fill in missing steps. Skipping a single intermediate definition or using an unexplained symbol triggers immediate comprehension failure, causing the child to guess or abandon the worksheet since no adaptive tutor or parent explanation is assumed.

* **How the Software Verifies Compliance:**

  1. **Directed Acyclic Dependency Graph (DAG) Audit:** Build a concept dependency graph from the source material and lesson script. Verify topological ordering: for every node $C_i$ referenced at lesson position $t$, all prerequisite nodes $P(C_i)$ must either exist in the grade-level baseline lexicon or appear at position $t_{prior} < t$.

  2. **Forward-Reference Linter:** Scan all instructional text and questions for undefined symbols, acronyms, or domain terms that appear before their formal introduction block in the *Discover* stage.

### Rule A3: Structured Progressive Scaffolding (Principle 3: Progressive Learning)

* **Classification:** **\[Established Educational Principle\]** (Worked Example Effect, Fading Guidance, & Bloom's Revised Taxonomy).

* **Rule Definition:** Every lesson must transition the learner along a deliberate gradient of cognitive independence: **Discover → Reinforce → Vary → Apply → Recall**. Cognitive support (worked examples, visual hints, word banks, partially completed structures) must be highest at the beginning of the lesson and systematically faded until the child performs unaided retrieval in the final stage.

* **Why It Matters:** Jumping directly from a textbook definition to an open-ended problem overwhelms working memory, while staying entirely within guided recognition tasks creates an "illusion of competence" where the child recognizes answers on the page but cannot reproduce them independently.

* **How the Software Verifies Compliance:**

  1. **Stage-Sequence Validator:** Confirm the presence and order of the five structural blocks (or an explicitly justified domain-specific permutation permitted under Section B).

  2. **Scaffolding-Fade Monotonicity Check:** Score each activity for support density (e.g., presence of worked steps, word banks, traced lines, or multiple-choice options). Verify that support density strictly decreases from *Reinforce* through *Recall*, and that the *Recall* stage contains zero answer banks or verbatim copy prompts above visible source definitions.

### Rule A4: Intrinsic Curiosity and Cognitive Engagement (Principle 4: Attention and Engagement)

* **Classification:** **\[Established Educational Principle\]** (Epistemic Curiosity & Self-Determination Theory) + **\[Proposed Design Choice — Requires Testing\]** (Specific visual and narrative framing formats on landscape A4).

* **Rule Definition:** Engagement must be driven by making the subject matter itself intriguing and conquerable—using a concrete framing question, relatable real-world anomaly, visual micro-story, or structured mystery that the curriculum concept resolves—rather than extrinsic fluff or unrelated cartoons.

* **Why It Matters:** Children working on paper without digital animations or gamified sound effects sustain attention only when they feel a clear sense of purpose ("Why does this work this way?") and visible competence ("I solved that step myself").

* **How the Software Verifies Compliance:**

  1. **Hook-to-Objective Alignment Check:** Verify that the opening hook in *Discover* poses a concrete question or scenario that is directly answered or resolved using the core learning objective by the end of the lesson.

  2. **Seductive Detail Filter:** Flag and reject any narrative text or illustration prompt whose entities have zero semantic connection to the curriculum concept being taught.

### Rule A5: Motor-Cognitive Active Participation (Principle 5: Active Participation)

* **Classification:** **\[Established Educational Principle\]** (Generation Effect & Embodied/Enactive Encoding) + **\[Proposed Design Choice — Requires Testing\]** (Maximum passive reading span before a pencil action is required).

* **Rule Definition:** The child must physically interact with the page using a pencil within the first **60 to 90 seconds** (**\[Proposed Design Choice — Requires Testing\]**) and after every instructional block thereafter. No reading block may exceed **60–120 words** (grade-dependent) without requiring a concrete pencil action (circling, annotating, completing a missing step, connecting, sketching, or writing).

* **Why It Matters:** Passive reading frequently degrades into mechanical eye-scanning without semantic processing. Requiring an immediate physical decision with a pencil forces the child to evaluate what they just read before moving forward.

* **How the Software Verifies Compliance:**

  1. **Passive Span Counter:** Measure the word count of every continuous text block between required pencil-action zones. Reject any layout where contiguous reading exceeds the grade-band ceiling (e.g., 45 words for Grades 1–2, 80 words for Grades 3–5, 120 words for Grades 6–8).

  2. **Action-Verb Presence Check:** Confirm that every lesson stage (including *Discover*) includes at least one explicit, executable pencil directive.

### Rule A6: Strict Objective Alignment and Zero Decorative Bloat (Principle 6: Purposeful Activities)

* **Classification:** **\[Established Educational Principle\]** (Constructive Alignment — Biggs; Coherence Principle — Mayer).

* **Rule Definition:** Every activity, puzzle, diagram annotation, or matching task must directly require the child to process the target learning objective to succeed. An activity is prohibited if a child can complete it using purely visual/mechanical heuristics without understanding the curriculum content (e.g., word searches where students hunt for letter strings without knowing meanings, unlabelled mazes, or color-by-number tasks where the picture is unrelated to the concept).

* **Why It Matters:** In a 15-minute window, every minute spent on a mechanically solvable or decorative puzzle steals scarce cognitive time from comprehension, variation, and retrieval.

* **How the Software Verifies Compliance:**

  1. **Content-Blind Solvability Test (Simulated Heuristic Solver):** Test whether an activity can be solved when domain semantics are masked (e.g., if a matching task can be solved purely by grammatical part-of-speech, string length, or positional symmetry, or if a puzzle requires only letter-matching). If solvable without domain comprehension, reject the activity.

  2. **Objective Traceability Tagging:** Require every activity block in the lesson specification to link to a specific sub-objective ID derived from the curriculum PDF.

### Rule A7: Intrinsic and Extraneous Cognitive Load Management (Principle 7: Cognitive Load)

* **Classification:** **\[Established Educational Principle\]** (Sweller's Cognitive Load Theory & Mayer's Multimedia Learning Principles) + **\[Proposed Design Choice — Requires Testing\]** (Specific landscape A4 spatial density caps and concept-per-lesson ceilings).

* **Rule Definition:** A single 15-minute lesson must introduce at most **1 core concept** (or **2–3 tightly coupled sub-concepts / 3–5 vocabulary terms**, **\[Proposed Design Choice — Requires Testing\]**). Instructions must use syntactic structures at least one grade level below the child's target grade so that working memory is spent on the curriculum concept, not on decoding complex instructions. Visual layouts on landscape A4 must maintain at least **30–35% open whitespace** (**\[Proposed Design Choice — Requires Testing\]**) with unambiguous visual flow indicators (numbered steps, clear directional arrows, bounded workspaces).

* **Why It Matters:** Working memory in children is severely limited. When crowded pages, multi-clause instructions, or excessive new facts overload working memory, schema acquisition halts entirely.

* **How the Software Verifies Compliance:**

  1. **Concept Novelty Counter:** Count the number of newly defined domain terms or distinct procedural rules introduced in the lesson; reject if the count exceeds the grade-band cap.

  2. **Instruction Readability Linter:** Compute readability metrics (e.g., Flesch-Kincaid, sentence length, clause depth) specifically on *activity instructions*; reject instructions containing more than two sequential actions in a single sentence or exceeding grade-level minus 1 readability.

  3. **Whitespace & Bounding-Box Density Analyzer:** Render the landscape A4 layout and verify that non-ink background area $\ge 30\%$ and no two interactive elements violate minimum margin spacing.

### Rule A8: Generative Understanding Over Surface Completion (Principle 8: Recall and Understanding)

* **Classification:** **\[Established Educational Principle\]** (Retrieval Practice / Testing Effect & Levels of Processing).

* **Rule Definition:** Completing the worksheet must require genuine semantic processing and memory retrieval. At least **35–40% of the lesson's cognitive time** (**\[Proposed Design Choice — Requires Testing\]**) must be dedicated to *Apply* and *Recall* tasks where the child cannot succeed merely by copying words from an adjacent paragraph. Additionally, the spatial layout must prevent trivial "look-back copying" during the *Recall* stage (e.g., by placing *Recall* in a dedicated fold-over zone, a subsequent page, or framing prompts that require rephrasing/application rather than verbatim transcription of a visible header).

* **Why It Matters:** Students frequently complete traditional worksheets by pattern-matching keywords between a question and a nearby paragraph—producing a fully filled page with near-zero retention five minutes later.

* **How the Software Verifies Compliance:**

  1. **N-Gram Overlap / Verbatim Copy Detector:** Compare the expected answer strings of *Apply* and *Recall* items against the instructional text visible on the same page. If an item can be answered by copying a contiguous phrase from a nearby sentence without transformation, flag it as surface-level copying.

  2. **Cognitive Taxonomy Classifier:** Classify every question along a simplified cognitive rubric (Recognition vs. Guided Transformation vs. Independent Application vs. Cuing-Free Retrieval) and verify that both Independent Application and Cuing-Free Retrieval are present.

### Rule A9: Deterministic Time Budgeting with Comprehension Priority (Principle 9: Realistic Timing)

* **Classification:** **\[Established Educational Principle\]** (Mastery Framing vs. Pacing Constraints) + **\[Proposed Design Choice — Requires Testing\]** (15-minute target window and component time-estimation formulas).

* **Rule Definition:** Every generated lesson must have a predicted completion time of **13.0 to 16.5 minutes** (**\[Proposed Design Choice — Requires Testing\]**) calculated via a bottom-up behavioral time model (accounting for reading, visual inspection, cognitive deliberation, and physical handwriting speed by grade). If a curriculum PDF contains more material than can be taught thoroughly in 15 minutes, the system **must narrow the scope of the lesson** (slicing the curriculum into a smaller, coherent sub-unit) rather than compressing explanations or rushing activities.

* **Why It Matters:** When a system crams a 45-minute classroom topic into a 15-minute worksheet, it strips out worked examples and scaffolding—destroying first-time comprehension. Conversely, a worksheet that actually takes 35 minutes exhausts the child and breaks the product promise.

* **How the Software Verifies Compliance:**

  1. **Bottom-Up Time Estimator:** Run the deterministic timing formula defined in Section E across all text blocks, visual elements, and pencil responses.

  2. **Scope-Overflow Circuit Breaker:** If the raw curriculum PDF requires more than the maximum concept budget to reach *Apply* and *Recall* within 15 minutes, trigger automatic curriculum slicing before lesson generation and explicitly state the covered sub-scope on the lesson header.

### Rule A10: Self-Contained Print-First Autonomy (Principle 10: Print-First Design)

* **Classification:** **\[Established Educational Principle\]** (Self-Regulated Learning & Cognitive Ergonomics) + **\[Proposed Design Choice — Requires Testing\]** (Landscape A4 physical layout ergonomics).

* **Rule Definition:** Every lesson must be 100% executable using only **printed landscape A4 sheets (297 mm × 210 mm)** and a **standard graphite pencil**.

  1. **Zero External Dependencies:** No scissors, glue, rulers (unless a printed paper ruler is embedded on the page edge), colored pencils, dice, timers, internet lookups, QR codes, or audio prompts.

  2. **Greyscale-Safe Visuals:** All diagrams, shading, and visual distinctions must remain unambiguous when printed on a basic black-and-white home laser or inkjet printer (using hatching, patterns, line weights, and high-contrast shapes rather than color coding).

  3. **Zero Parent-Mediation Requirement:** For children at Grade 2 reading fluency and above, instructions must be self-explanatory (supported by a pre-filled 1st item / "Worked Start" on any non-trivial activity format) so a child can complete the sheet without asking an adult "What am I supposed to do here?" (For Pre-K to Grade 1 emergent readers, visual icon conventions and ultra-minimal decodable prompts must minimize adult reading burden).

* **Why It Matters:** Requiring extra household supplies creates friction that stops a lesson from happening. Relying on color distinctions breaks on monochrome printers. Requiring a parent to interpret cryptic directions turns a self-directed student lesson into a parent tutoring burden.

* **How the Software Verifies Compliance:**

  1. **Prohibited-Tool Lexicon Filter:** Reject any activity containing words or actions requiring external tools (*cut, paste, glue, color in red/blue, measure with a ruler, roll a die, look up, ask an adult, listen, click, tap*).

  2. **Monochrome Contrast & Pattern Audit:** Convert all generated diagrams to 1-bit/8-bit greyscale and verify that every distinct visual region remains distinguishable by texture, pattern, label, or luminance contrast ($\ge 4.5:1$).

  3. **Worked-Start Presence Check:** For any multi-step or custom table/diagram activity, verify that Item #1 is pre-populated in light grey/dashed "example pencil" style to model the expected action visually.

### Rule A11: Deterministic Answerability and Rubric Completeness (Principle 11: Answerability)

* **Classification:** **\[Established Educational Principle\]** (Criterion-Referenced Assessment Validity).

* **Rule Definition:** Every single prompt, blank, matching node, diagram label, and short-answer space must be paired at generation time with an explicit, unambiguous target response or a deterministic evaluation rubric containing:

  1. The exact canonical answer(s) derived from the curriculum PDF.

  2. Acceptable equivalent phrasings or numerical tolerances.

  3. Specific diagnostic misconception traps (if the item is structured choice). No open-ended prompt may ask for unverifiable subjective opinions (e.g., "How do you feel about photosynthesis?") as a measure of learning.

* **Why It Matters:** If a question is vague, admits multiple conflicting interpretations, or lacks a clear criterion based on the lesson text, the child experiences unfair frustration and the downstream answer-key generator cannot produce a reliable grading guide for the parent.

* **How the Software Verifies Compliance:**

  1. **Blind Solver Simulation (Two-Agent Verification):** Pass *only* the generated student worksheet (without the source PDF or internal answer key) to an independent verification agent constrained to the target grade's reasoning level. Require the agent to solve every prompt using only the printed lesson content.

  2. **Ambiguity & Match Audit:** If the independent solver's output disagrees with the intended answer key, or if the solver identifies multiple equally valid answers where only one is keyed, reject or rewrite the item before accepting the lesson.

### Rule A12: High-Leverage Depth Over Mechanical Volume (Principle 12: Quality Over Quantity)

* **Classification:** **\[Established Educational Principle\]** (Deliberate Practice & Overlearning Diminishing Returns within Single Sessions) + **\[Proposed Design Choice — Requires Testing\]** (Cap of 4–6 total activity blocks per 15-minute lesson).

* **Rule Definition:** A 15-minute lesson must contain **4 to 6 distinct, high-value activity blocks** across the five pedagogical stages, with **no more than 2 to 4 sub-items per activity block** (**\[Proposed Design Choice — Requires Testing\]**). Repetitive drill sets (e.g., 15 identical arithmetic equations or 10 fill-in-the-blank sentences testing the same definition) are strictly prohibited. Each sub-item within an activity must vary a meaningful parameter, edge case, or representation.

* **Why It Matters:** Once a child has demonstrated comprehension of a specific pattern twice, ten more identical repetitions induce boredom and mechanical autopilot rather than deeper understanding. Varying the angle across a small number of thoughtful items builds flexible mental schemas within the 15-minute budget.

* **How the Software Verifies Compliance:**

  1. **Item-Count Ceiling Check:** Verify that total distinct student response items across the entire 15-minute lesson fall within **8 to 16 individual pencil actions** (grade- and subject-adjusted), capped at $\le 4$ items per single exercise block.

  2. **Structural Isomorphism Detector:** Compare sub-items within the same activity block; reject any block where $>2$ consecutive sub-items share identical syntactic/mathematical structure without introducing a new feature, boundary condition, or representation shift.

## Section B: Reusable Lesson Progression

Every generated lesson is built around a five-stage cognitive spine (**Discover → Reinforce → Vary → Apply → Recall**). While the sequence adapts when a specific discipline requires a modified entry point, the underlying progression from *high-support encoding* to *independent transfer and retrieval* is invariant.

### 1. Canonical Five-Stage Architecture

| Stage | Pedagogical Objective | Cognitive Mechanism **\[Established Principle\]** | Typical Student Pencil Action | Target Time Share **\[Proposed Choice — Needs Testing\]** | Support / Scaffolding Level | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **1. Discover** | Build an initial, intuitive mental model of the new concept and anchor it to familiar experience. | **Dual Coding & Concrete-Representational-Abstract (CRA) Bridging:** Pairing a visual/concrete anchor with a concise verbal explanation and a worked example. | Trace a path, circle a key difference in a contrasting visual pair, or fill in 1 guided observation in a worked example. | **3.0 – 3.5 min** (\~20–23%) | **Maximum** (90% guided; full visual + verbal model provided). | 
| **2. Reinforce** | Consolidate the core rule, definition, or step-by-step mechanism and verify basic comprehension. | **Guided Encoding & Self-Explanation Effect:** Completing a partially faded worked example or identifying *why* a step works. | Complete missing labels on a diagram, connect cause-to-effect nodes, or finish the final step of a scaffolded example. | **3.0 – 3.5 min** (\~20–23%) | **High** (60–70% guided; structural cues, word banks, or partial steps present). | 
| **3. Vary** | Prevent brittle, surface-bound memorization by practicing the same concept in a shifted representation or non-standard orientation. | **Variation Theory (Marton) & De-contextualization:** Keeping the core invariant concept constant while varying surface features, directionality (forward vs. reverse), or modality (visual ↔ symbolic). | Spot and fix a deliberate error ("Find the Mistake"), translate a diagram into a statement, or solve a reverse-direction prompt. | **3.0 min** (\~20%) | **Moderate** (30–40% guided; hints faded, format shifted). | 
| **4. Apply** | Use the newly learned concept to solve a realistic, novel problem or answer an analytical question. | **Near Transfer & Generative Problem Solving:** Selecting and executing the right concept/procedure in a realistic context without step-by-step hand-holding. | Solve 1–2 realistic scenario problems, construct a diagram/solution from scratch, or write a structured justification. | **3.5 – 4.0 min** (\~23–27%) | **Low** (10% guided; workspace grids provided, but no content hints). | 
| **5. Recall** | Retrieve the essential takeaway, rule, or mechanism from memory without copying from earlier text. | **Retrieval Practice / Testing Effect & Elaborative Interrogation:** Reconstructing knowledge from memory cues to strengthen long-term retention pathways. | Complete a visually separated "Memory Check / Teach It Back" box (summarize key rule in own words, sketch core relationship, or answer 2 cue-free recall prompts). | **2.0 min** (\~13–15%) | **Zero** (0% content scaffolding; isolated from *Discover* text). | 

### 2. Subject-Specific Sequence Adaptations

Principle 3 states: *"Adapt this sequence when the subject requires a different order, but preserve the principle of progressive understanding."* The software must select from four approved progression variants based on the domain classification of the curriculum PDF:

| Curriculum Domain Type | Approved Sequence Variant | Rationale for Adaptation **\[Established Principle\]** | How Progressive Understanding Is Preserved | 
| ----- | ----- | ----- | ----- | 
| **Type 1: Conceptual Science & Social Studies** *(e.g., water cycle, food chains, branches of government)* | **Canonical:** `Discover → Reinforce → Vary → Apply → Recall` | Conceptual schemas require building a mental model of entities and relationships first (*Discover*), locking in terminology (*Reinforce*), testing boundaries/non-examples (*Vary*), analyzing a case (*Apply*), and retrieving the core system (*Recall*). | Direct progression from concrete visual system to abstract causal reasoning and cue-free summary. | 
| **Type 2: Procedural Mathematics & Grammar Rules** *(e.g., adding fractions with unlike denominators, subject-verb agreement)* | **Interleaved Worked-Fading:** `Discover (Worked Example) → Reinforce (Faded Step) → Apply (Standard Execution) → Vary (Reverse / Error-Analysis) → Recall (Rule Articulation)` | In procedural domains, **Cognitive Load Theory (Worked Example Effect)** shows novices must master the forward procedure (*Discover → Reinforce → Apply*) before tackling reversed parameters or error-spotting (*Vary*), which otherwise cause procedural interference if introduced too early. | Support still fades monotonically: full worked example → partial completion → independent forward execution → structural variation/debugging → retrieving the underlying mathematical rule. | 
| **Type 3: Inquiry / Phenomenon-First Concepts** *(e.g., buoyancy, geometric invariants, historical cause-and-effect mysteries)* | **Productive Failure / Predict-First:** `Vary/Probe (Guided Prediction) → Discover (Concept Resolution) → Reinforce → Apply → Recall` | **Productive Failure (Kapur) & Contrasting Cases (Schwartz & Bransford):** Briefly comparing two contrasting cases and making a 30-second prediction *before* reading the formal explanation activates curiosity and highlights the exact critical feature the student needs to notice. | The opening probe is strictly bounded ($\le 60$ seconds, zero penalty for wrong intuition) and immediately resolved in *Discover*, followed by standard *Reinforce → Apply → Recall*. | 
| **Type 4: Dense Terminology, Classification, or Taxonomies** *(e.g., parts of a cell, rock types, vocabulary sets)* | **Chunked Micro-Cycles:** `[Discover A → Reinforce A] → [Discover B → Reinforce B] → Vary (Contrast A vs. B) → Apply → Recall` | Introducing 4–5 distinct definitions simultaneously in a single *Discover* block violates working memory limits. Splitting acquisition into two micro-cycles of 2–3 items before contrasting them in *Vary* prevents lexical interference. | Each sub-group is encoded first, then integrated via discriminative comparison (*Vary*), applied together (*Apply*), and retrieved as a unified whole (*Recall*). | 

### 3. Software Verification of Lesson Progression

1. **Domain-Classifier Routing Check:** Verify that the selected progression template matches the classified curriculum domain type (Type 1–4) and that all five functional components exist.

2. **Look-Back Isolation Check for Recall:** Verify that the *Recall* block is either placed on Sheet 2 / the far-right fold column of Landscape A4 with a printed `"Fold Here or Cover Left Side Before Starting Step 5"` line, or phrased as a transformation/synthesis prompt that cannot be answered by transcribing visible definitions on the same sheet.

## Section C: Rules for Maintaining Attention Without Sacrificing Learning

Without screens, animations, or reward badges, paper lessons maintain attention through **cognitive momentum**: the feeling of curiosity at the start and steady, achievable mastery at every step.

### Rule C1: The "Conflict or Curiosity" Opening Hook

* **Classification:** **\[Established Educational Principle\]** (Information-Gap Theory of Curiosity — Loewenstein).

* **Rule Definition:** Every lesson must open in the top-left zone of the landscape A4 page with a **15-to-30-second Curiosity Hook** that exposes a relatable puzzle, counter-intuitive fact, or everyday question directly resolved by the curriculum topic (e.g., *"Why doesn't a heavy steel ship sink while a tiny steel nail drops to the bottom?"*), accompanied by a concrete visual contrast.

* **Why It Matters:** Opening with a dry textbook header (*"Unit 4.2: Density and Buoyancy Definitions"*) signals tedious schoolwork and suppresses intrinsic motivation before the child picks up the pencil.

* **How the Software Verifies Compliance:**

  1. **Opening Block Structural Linter:** Check that the first text element in *Discover* contains an interrogative sentence or contrasting scenario rather than a bare dictionary definition.

  2. **Semantic Resolution Link:** Verify that the entity or question introduced in the hook is explicitly referenced and resolved by the end of the *Discover* or *Apply* block.

### Rule C2: Visual Dual-Coding Over Prose Explanations

* **Classification:** **\[Established Educational Principle\]** (Paivio's Dual Coding Theory & Mayer's Multimedia Principle).

* **Rule Definition:** Whenever a curriculum concept involves spatial relationships, processes, hierarchies, proportions, or comparisons, the primary explanation in *Discover* must be delivered as an **annotated diagram, sequence strip, or visual comparison table** with callout labels ($\le 15$ words per callout, **\[Proposed Design Choice — Requires Testing\]**), rather than a dense paragraph of prose.

* **Why It Matters:** Processing spatial or relational concepts through text alone consumes high extraneous cognitive load. Pairing concise verbal labels directly with spatial illustrations activates both visual and verbal working memory channels simultaneously.

* **How the Software Verifies Compliance:**

  1. **Prose-to-Visual Ratio Check:** In the *Discover* stage, verify that continuous prose paragraphs do not exceed 50% of the stage's bounding box area and that at least one structured visual representation (diagram, annotated model, contrasting pair, or process flow) is present.

  2. **Spatial Contiguity Check (Mayer):** Verify that diagram labels are placed directly adjacent to (or connected via clean leader lines to) the relevant visual feature, never separated into a distant numbered legend that requires eye-shuttle look-ups.

### Rule C3: Micro-Chunking and High-Frequency Completion Cues

* **Classification:** **\[Established Educational Principle\]** (Goal-Gradient Effect & Sub-Goal Framing) + **\[Proposed Design Choice — Requires Testing\]** (2–4 minute activity rhythm and progress tracker UI on paper).

* **Rule Definition:** No single activity block may require more than **3.5 to 4.0 minutes** of uninterrupted effort. The landscape A4 layout must organize the lesson into clearly numbered, visually bounded zones (**Step 1** through **Step 5**) with a small pencil check-box (`[ ] Done!`) at the corner of each completed zone so the child experiences a tangible sense of progress every 2–3 minutes.

* **Why It Matters:** A continuous, unsegmented page of questions feels endless to a child. Breaking the 15-minute journey into 5 bite-sized visual checkpoints creates regular micro-completions that sustain effort through the final recall task.

* **How the Software Verifies Compliance:**

  1. **Per-Block Duration Cap:** Reject any single activity block whose estimated completion time (per Section E formulas) exceeds 4.0 minutes.

  2. **Visual Checkpoint Audit:** Confirm that each stage container renders a distinct step badge (`1` to `5`) and a physical completion check-box.

### Rule C4: Functional Narrative and Zero "Seductive Details"

* **Classification:** **\[Established Educational Principle\]** (Mayer's Coherence Principle & Harp & Mayer's Seductive Details Effect).

* **Rule Definition:** Stories, characters, or real-world contexts may be used *only* when the narrative mechanics directly embody the curriculum structure (e.g., sharing a pizza fairly to model fractions, or following a detective verifying historical primary sources). Adding tangential jokes, unrelated comic side-quests, or decorative mascots spouting trivia is prohibited.

* **Why It Matters:** Empirical research on the *Seductive Details Effect* demonstrates that interesting but irrelevant details capture a child's attention at the expense of the core lesson—students remember the joke or cartoon character while forgetting the target principle.

* **How the Software Verifies Compliance:**

  1. **Entity-Role Binding Audit:** Verify that every named character, object, or story element in an activity maps directly to a functional variable, parameter, or concept in the learning objective. If removing the narrative sentence leaves the question's logic intact and needed context unchanged, flag as decorative bloat.

### Rule C5: Calibrated "Desirable Difficulty" Escalation

* **Classification:** **\[Established Educational Principle\]** (Bjork's Desirable Difficulties & Vygotsky's Zone of Proximal Development).

* **Rule Definition:** Every lesson must begin with an immediate, high-probability success task in *Discover/Reinforce* ($\ge 90\%$ expected first-try accuracy) to build confidence, then introduce a clearly signaled "Challenge Step" in *Vary* or *Apply* that requires deeper thought (e.g., spotting a common trap or solving a two-step problem).

* **Why It Matters:** If the first task is too hard, the child shuts down immediately; if every task is trivially easy, the child becomes bored and disengages.

* **How the Software Verifies Compliance:**

  1. **Difficulty Curve Monotonicity Check:** Score each activity along three complexity dimensions (number of cognitive steps, degree of scaffolding present, and representational distance from the worked example) and verify a monotonic increase from Stage 1 to Stage 4.

## Section D: Rules for Selecting Appropriate Paper-Based Activities

Because the child interacts exclusively through a graphite pencil on landscape A4 paper, the software must select activity mechanics that maximize **cognitive engagement per unit of physical motor effort**.

### 1. Cognitive-to-Motor Efficiency Ratio (The Golden Rule of Paper Mechanics)

* **Classification:** **\[Established Educational Principle\]** (Extraneous Motor Load vs. Germane Cognitive Load) + **\[Proposed Design Choice — Requires Testing\]** (Handwriting word-count caps by grade).

* **Rule Definition:** The physical effort of writing must never become the bottleneck that exhausts the child or consumes the 15-minute clock. When assessing comprehension, classification, or relational structure, the software must prefer **high-cognition, low-motor mechanics** (matching, sorting into categories, circling/annotating, completing a diagram, or filling a targeted key phrase) over lengthy prose handwriting—reserving full-sentence writing strictly for high-value synthesis in *Apply* or *Recall*.

* **Why It Matters:** For younger learners (especially Grades 1–4), handwriting is not yet fully automatized; writing a two-sentence answer demands intense motor working memory, which crowds out conceptual thinking about the subject matter.

* **How the Software Verifies Compliance:**

  1. **Motor-Load Ratio Check:** Calculate the ratio of estimated handwriting time to total activity time (using Section E parameters). If physical handwriting exceeds **35% of total lesson duration** (or **25% for Grades 1–2**, **\[Proposed Design Choice — Requires Testing\]**), convert redundant written prompts into structured graphic organizers, diagram annotations, or targeted completion items.

### 2. Approved Paper-Based Activity Taxonomy & Selection Matrix

The software must select activities strictly from the approved paper-and-pencil taxonomy below, matching the mechanic to both the **pedagogical stage** and the **curriculum knowledge type**:

| Paper Mechanic | Best Pedagogical Stages | Ideal Curriculum Knowledge Type | Design Rules for Landscape A4 | Anti-Pattern to Prevent | 
| ----- | ----- | ----- | ----- | ----- | 
| **1. Guided Annotation & Circling** *(Circle the active part, underline the cause, mark the outlier)* | *Discover*, *Reinforce*, *Vary* | Visual features, text evidence, structural patterns, error spotting. | Provide clear targets with generous whitespace around selectable elements ($\ge 6\text{ mm}$ gap). Always include at least 3 plausible options so circling isn't a 50/50 coin toss. | Circling a word that is already bolded or visually obvious without reading. | 
| **2. Asymmetric Node Matching / Connecting** *(Draw a pencil line from Concept to Example/Function)* | *Reinforce*, *Vary* | Definitions, cause-and-effect, structure-to-function pairs, symbol-to-meaning. | **Always use Asymmetric Matching** (e.g., 3 items in Column A matched to 4–5 options in Column B, or allowing many-to-one) so the final item cannot be solved by process of elimination. Keep line paths short ($\le 8\text{ cm}$) to avoid messy tangled lines. | 1-to-1 symmetric matching where the last pair is automatic without reading. | 
| **3. Diagram Labelling & Flow Completion** *(Write terms or arrows into empty callout boxes on a system model)* | *Discover*, *Reinforce*, *Apply* | Spatial anatomy, cycles, multi-step processes, hierarchies, apparatus. | Callout boxes must be sized for child handwriting ($\ge 10\text{ mm}$ tall for Grades 1–3; $\ge 8\text{ mm}$ for Grades 4+). Use a Word Bank in *Reinforce* (with 1–2 distractors); remove the Word Bank in *Apply/Recall*. | Tiny boxes that force cramped, illegible writing; ambiguous leader lines. | 
| **4. Categorization & Sorting Tables** *(Sort items from a pool into a 2- or 3-column table or Venn diagram)* | *Reinforce*, *Vary* | Taxonomies, comparing/contrasting properties, rule vs. exception. | Limit sorting pools to 4–6 items. To save motor time for younger grades, allow sorting by writing item letters (`A, B, C`) or short 1–2 word labels into the category boxes. | Requiring students to copy 8-word phrases into tiny table cells. | 
| **5. Faded Worked Examples & Step Completion** *(Complete the missing intermediate step or final calculation)* | *Discover*, *Reinforce* | Mathematical procedures, algorithmic rules, grammar transformations, balancing equations. | Show Step 1 and Step 2 fully worked with brief callout notes; leave Step 3 blank in *Reinforce*, then leave Steps 2–3 blank in the next item. | Leaving all steps blank immediately after showing a rule. | 
| **6. "Spot and Fix the Mistake" (Error Analysis)** *(A fictional student solved this incorrectly; circle the error and write the fix)* | *Vary*, *Apply* | Common misconceptions in math, science reasoning, grammar, or logic. | Model a realistic, high-frequency misconception derived from the curriculum topic. Require two actions: (1) circle *where* it went wrong, and (2) write the corrected step or 1-sentence reason. | Trivial typos or computational slips that don't test the core concept. | 
| **7. Functional Logic Puzzles & Rule Grids** *(Constraint boxes, number/concept bridges, deductive cross-grids, sequence paths)* | *Vary*, *Apply* | Relational logic, math properties, sequence ordering, classification rules. | Every move in the puzzle must require applying the curriculum rule (e.g., "Move only along fractions equivalent to $1/2$"). Include a 1-step "Worked Start" arrow. | Purely recreational puzzles (word searches, standard sudoku, mazes with no content checkpoints). | 
| **8. Generative Sketching / Visual Modelling** *(Draw arrows to show force, sketch the particle arrangement, draw a bar model)* | *Apply*, *Recall* | Physical models, states of matter, fraction visual models, spatial relationships. | Provide a partially framed canvas (e.g., pre-drawn empty containers or axes) and explicit rubric criteria ("Draw 6 circles to show how gas particles spread out") so artistic skill is never graded. | Asking for complex freehand art ("Draw a realistic rainforest ecosystem"). | 
| **9. Structured Short Synthesis / "Teach It Back"** *(Complete a causal sentence frame or explain in 1–2 sentences)* | *Apply*, *Recall* | Conceptual explanations, summarizing a rule, justifying a prediction. | Use structured stems for younger grades (*"This happens because \__\_ leads to \__\_"*) and bounded 2-line boxes with Ruled Baseline Guides for older grades. | Open blank boxes asking *"Write everything you know about X."* | 

### 3. Grade-Band Ergonomic and Developmental Constraints

* **Classification:** **\[Proposed Design Choice — Requires Testing\]** (Grounded in developmental fine-motor and literacy norms).

| Grade Band | Reading & Instruction Rules | Allowed / Preferred Pencil Mechanics | Physical Handwriting & Layout Specs (Landscape A4) | 
| ----- | ----- | ----- | ----- | 
| **Grades 1–2** *(Ages 6–8)* | Max 12 words per instruction sentence. Single-action imperatives (*"Circle the..."*, *"Draw a line to..."*). Always pair instructions with a visual icon + worked 1st item. | Circling, line connecting, sorting via letter codes, drawing simple shapes/arrows, filling 1-word blanks from a word bank. | **Handwriting Cap:** Max 10–15 written words total across the entire lesson. **Line Height:** $12\text{–}14\text{ mm}$ ruled lines with dashed midline. **Font Size:** $\ge 14\text{ pt}$ body text. | 
| **Grades 3–5** *(Ages 8–11)* | Max 18 words per instruction sentence. Clear numbered steps. Minimal technical meta-language. | Asymmetric matching, diagram labelling, sorting tables, faded worked examples, error-spotting, 1-sentence causal explanations. | **Handwriting Cap:** Max 30–45 written words total across the lesson. **Line Height:** $9\text{–}10\text{ mm}$ ruled lines. **Font Size:** $\ge 12\text{ pt}$ body text. | 
| **Grades 6–9+** *(Ages 11–15+)* | Concise, direct academic phrasing. Multi-variable tables and formal notation permitted if introduced in *Discover*. | Full faded-to-independent problem solving, error analysis with justification, model sketching, multi-constraint logic grids, 1–2 sentence *Recall* synthesis. | **Handwriting Cap:** Max 60–80 written words (or equivalent algebraic steps) across the lesson. **Line Height:** $7\text{–}8\text{ mm}$ ruled lines. **Font Size:** $\ge 10.5\text{–}11\text{ pt}$ body text. | 

### 4. Software Verification of Paper-Based Activity Selection

1. **Activity Diversity Check:** Verify that a single 15-minute lesson uses at least **3 distinct activity mechanics** from the taxonomy across its 5 stages (preventing monotonous all-fill-in-the-blank or all-multiple-choice worksheets).

2. **Symmetric Matching Blocker:** Inspect all matching tasks; if $|Column_A| == |Column_B|$ and mapping is bijective (1-to-1), automatically inject 1–2 plausible curriculum-grounded distractors into Column B.

3. **Physical Bounding-Box Validator:** Check the rendered coordinates of every write-in blank, callout box, and ruled line on the $297\text{ mm} \times 210\text{ mm}$ canvas against the Grade-Band Line Height and Minimum Width table (requiring $\ge 8\text{ mm}$ horizontal width per expected character for Grades 1–2, $\ge 5\text{ mm}$ for Grades 3–5, and $\ge 3.5\text{ mm}$ for Grades 6+).

## Section E: Rules for Designing a Realistic 15-Minute Lesson

A 15-minute target duration is an unforgiving constraint. Children read, think, and write far more slowly than adults estimate. To prevent systematic time overruns—or superficial rushing—the software must govern scope and pacing through a **Deterministic Behavioral Time Model**.

### 1. The 4-Component Behavioral Time Formula

* **Classification:** **\[Established Educational Principle\]** (Component Task Analysis & Cognitive-Motor Decomposition) + **\[Proposed Design Choice — Requires Testing\]** (Exact parameter weights per grade band).

For every activity block $i \in \{1 \dots N\}$ in a proposed lesson, the software must calculate its predicted duration $T_i$ as the sum of four distinct behavioral components:

$$
T_{\text{lesson}} = T_{\text{orientation}} + \sum_{i=1}^{N} \left( T_{\text{read}}(i) + T_{\text{visual}}(i) + T_{\text{think}}(i) + T_{\text{motor}}(i) \right)
$$

Where:

1. $T_{\text{orientation}}$ **(Page Setup & Transition Overhead):** Fixed allowance of **60 seconds (1.0 min)** per lesson (**\[Proposed Design Choice — Requires Testing\]**) for orienting to the printed page, writing name/date, and scanning transitions between numbered steps.

2. $T_{\text{read}}(i)$ **(Instructional & Prompt Reading Time):** Calculated as $\frac{\text{Total Words in Block } i}{\text{Effective Instructional WPM}_{\text{grade}}}$. Note that *instructional reading speed* (reading unfamiliar concepts for comprehension) is approximately **50–60% slower** than narrative story reading speed:

   * **Grades 1–2:** $35\text{ WPM}$ effective instructional reading speed.

   * **Grades 3–5:** $70\text{ WPM}$ effective instructional reading speed.

   * **Grades 6–8:** $110\text{ WPM}$ effective instructional reading speed.

   * **Grades 9+:** $140\text{ WPM}$ effective instructional reading speed.

3. $T_{\text{visual}}(i)$ **(Diagram & Worked-Example Inspection Time):**

   * **Simple diagram / contrasting pair (2–4 labels):** $+15\text{ to }25\text{ seconds}$.

   * **Process flow / multi-step worked example (3–5 steps):** $+30\text{ to }45\text{ seconds}$.

   * **Data table or multi-axis chart:** $+30\text{ to }50\text{ seconds}$.

4. $T_{\text{think}}(i)$ **(Cognitive Deliberation & Decision Time per Sub-Item):**

   * **Level 1 (Guided Recognition / Direct Notice in *Discover*):** $+8\text{ to }12\text{ seconds}$ per item.

   * **Level 2 (Scaffolded Transformation / Matching / Sorting in *Reinforce*):** $+15\text{ to }25\text{ seconds}$ per item.

   * **Level 3 (Representation Shift / Error Spotting in *Vary*):** $+25\text{ to }40\text{ seconds}$ per item.

   * **Level 4 (Independent Multi-Step Problem / Scenario in *Apply*):** $+40\text{ to }60\text{ seconds}$ per item.

   * **Level 5 (Cue-Free Memory Retrieval & Formulation in *Recall*):** $+30\text{ to }45\text{ seconds}$ per item.

5. $T_{\text{motor}}(i)$ **(Physical Pencil Execution Time):**

   * **Discrete mark (circle, tick, short connecting line):** $+3\text{ to }5\text{ seconds}$ per mark.

   * **Guided diagram sketch / arrow drawing:** $+15\text{ to }30\text{ seconds}$.

   * **Handwriting words or math symbols (**$\frac{\text{Expected Written Words}}{\text{Handwriting WPM}_{\text{grade}}}$**):**

     * **Grades 1–2:** $4\text{ to }6\text{ words/min}$ ($10\text{–}15\text{ sec}$ per word).

     * **Grades 3–5:** $10\text{ to }14\text{ words/min}$ ($4.5\text{–}6\text{ sec}$ per word).

     * **Grades 6–8:** $16\text{ to }20\text{ words/min}$ ($3\text{–}3.8\text{ sec}$ per word).

     * **Grades 9+:** $22\text{ to }25\text{ words/min}$ ($2.5\text{ sec}$ per word).

### 2. Target Time Budget & Acceptance Corridor

* **Classification:** **\[Proposed Design Choice — Requires Testing\]**

| Stage | Target Time | Permissible Range | Maximum Sub-Items | Page Budget Allocation (2-Page Landscape A4 Standard) | 
| ----- | ----- | ----- | ----- | ----- | 
| **Orientation & Header** | 1.0 min | 0.5 – 1.0 min | — | Page 1, Top Banner | 
| **1. Discover** | 3.0 min | 2.5 – 3.5 min | 1–2 guided notices | Page 1, Left Column / Top-Left Quadrant | 
| **2. Reinforce** | 3.0 min | 2.5 – 3.5 min | 3–4 scaffolded items | Page 1, Right Column / Bottom-Left Quadrant | 
| **3. Vary** | 2.5 min | 2.0 – 3.0 min | 2–3 varied items | Page 1 Bottom-Right or Page 2 Top-Left | 
| **4. Apply** | 3.5 min | 3.0 – 4.5 min | 1–2 deep problems | Page 2, Main Workspace | 
| **5. Recall** | 2.0 min | 1.5 – 2.5 min | 1–2 retrieval checks | Page 2, Isolated Bottom-Right "Memory Lock" Box | 
| **TOTAL LESSON** | **15.0 min** | **13.0 – 16.5 min** | **8 – 15 total actions** | **Max 2 Landscape A4 Pages (Single-Sided or 1 Sheet Duplex)** | 

### 3. Rule E3: Scope-Slicing Over Pedagogical Compression (Protecting Understanding)

* **Classification:** **\[Established Educational Principle\]** (Cognitive Load Ceiling & Mastery Prerequisite Integrity).

* **Rule Definition:** When a parent uploads a multi-page curriculum chapter or dense PDF whose concepts would exceed **16.5 minutes** under the behavioral time model, the software is **strictly forbidden** from shrinking the *Discover* explanation, deleting the worked example, or dropping the *Vary/Recall* stages to make everything fit. Instead, the software must perform **Pre-Generation Curriculum Slicing**:

  1. Decompose the uploaded PDF into a sequence of atomic, self-contained **15-Minute Micro-Objectives** ordered by prerequisite dependency.

  2. Select **Micro-Objective #1** (the foundational entry concept of the document) for the generated 15-minute lesson.

  3. Print a clear **Scope Banner** at the top of the worksheet: *"Lesson 1 of \[N\] from your uploaded curriculum: Focusing today on \[Sub-Objective 1\]."*

* **Why It Matters:** Attempting to teach four distinct sub-topics in 15 minutes forces superficial 3-minute skims of each topic, violating First-Time Learning and Cognitive Load principles. Teaching one foundational concept thoroughly in 15 minutes gives the child genuine comprehension.

* **How the Software Verifies Compliance:**

  1. **Compression Guardrail:** Verify that even when source PDFs exceed 10 pages, the generated lesson still allocates $\ge 40\%$ of its time budget to *Discover + Reinforce* and $\ge 35\%$ to *Apply + Recall* on a single coherent sub-objective.

  2. **Time-Corridor Gate:** Reject any lesson draft whose total calculated $T_{\text{lesson}}$ falls below $13.0\text{ minutes}$ (under-designed/superficial) or above $16.5\text{ minutes}$ (overloaded). If $T_{\text{lesson}} > 16.5\text{ minutes}$, prune secondary sub-concepts or reduce redundant sub-items within an activity block—never delete a core pedagogical stage.

## Section F: Common Teaching-Design Failures the System Must Prevent

Automated lesson generators frequently fail in predictable ways when translating curriculum text into worksheets. The software pipeline must actively detect and block the following **10 Critical Teaching-Design Failures**:

| Failure ID & Name | Pedagogical Root Cause | Concrete Symptom on the Printed Page | Automated Detection & Prevention Mechanism | 
| ----- | ----- | ----- | ----- | 
| **F1: The Encyclopedic Wall-of-Text** | Violates Principle 5 (Active Participation) and Principle 7 (Cognitive Load). | The *Discover* section prints 250 words of dense textbook prose followed by questions at the bottom. The child's eyes glaze over and they skip straight to guessing the blanks. | **Hard Prose Ceiling:** Reject any text block $>60\text{ words}$ (Grades 1–3) or $>100\text{ words}$ (Grades 4+) that lacks an embedded diagram callout or immediate pencil micro-action. | 
| **F2: Verbatim Keyword Matching ("Ctrl+F on Paper")** | Violates Principle 8 (Recall and Understanding). | A paragraph states *"The mitochondria produce energy for the cell,"* and 3 cm below, a question asks *"The \_____\_ produce energy for the cell."* The child copies the shape of the word without comprehending its meaning. | **Syntactic & Lexical Distance Gate:** Require all *Reinforce*, *Vary*, *Apply*, and *Recall* prompts to paraphrase sentence structures and prevent verbatim substring completion when the source sentence is visible on the same sheet. | 
| **F3: The Unscaffolded Cliff ("Explain and Abandon")** | Violates Principle 2 (First-Time Learning) and Principle 3 (Progressive Learning). | The lesson shows a brief 1-sentence definition of a math formula and immediately asks the child to solve a complex multi-step word problem with zero worked examples or intermediate faded steps. | **Worked-Example Prerequisite Check:** Block any procedural or analytical *Apply* problem unless a complete Step-by-Step Worked Example (*Discover*) and a Faded Step Completion task (*Reinforce*) precede it. | 
| **F4: Decorative Edutainment ("The Word-Search Trap")** | Violates Principle 6 (Purposeful Activities) and Principle 9 (Realistic Timing). | The generator inserts a 5-minute crossword puzzle, letter unscramble, or maze where finding the path/letters requires zero conceptual understanding of the subject. | **Zero-Semantic-Value Blocklist:** Permanently ban word searches, anagrams, letter-substitution ciphers, unlabelled mazes, and decorative coloring tasks at the schema level. | 
| **F5: Hidden Prerequisite Leap** | Violates Principle 1 (Source Accuracy) and Principle 2 (First-Time Learning). | A lesson on calculating area of triangles uses decimals ($4.5 \times 3.2$) for a child whose curriculum PDF only uses whole numbers, or uses undefined terminology (*"hypotenuse"*) never introduced in the source. | **Prerequisite & Arithmetic Complexity Auditor:** Constrain numerical operands and secondary vocabulary in generated problems to match or sit below the complexity distribution of examples in the source PDF. | 
| **F6: Symmetric Elimination Gaming** | Violates Principle 6 (Purposeful Activities) and Principle 8 (Recall and Understanding). | A 3-item matching list or 3-word fill-in-the-blank box has exactly 3 slots and 3 word-bank choices, allowing the child to get the hardest item right purely by elimination. | **Asymmetric Distractor Rule:** Every word bank or matching target column must include $\ge 1$ plausible, curriculum-relevant distractor (or permit reuse of options, explicitly noted). | 
| **F7: Parent-Dependent Instructions** | Violates Principle 10 (Print-First Design) and Principle 7 (Cognitive Load). | Instructions use abstract pedagogical jargon (*"Synthesize the causal variables in the matrix below"*) or multi-step conditional logic that forces the child to call a parent for help. | **Instruction Simplicity & Worked-Start Gate:** Enforce grade-minus-1 readability on all instructions and require a pre-filled greyscale example item (`Ex:`) on every structured table, grid, or diagram activity. | 
| **F8: Physical Ergonomic Failure on Landscape A4** | Violates Principle 10 (Print-First Design). | A question expects a 12-word written explanation inside a $30\text{ mm} \times 6\text{ mm}$ unruled box, or uses colour-coded pie charts (`"Compare the red slice to the green slice"`) that print as identical dark grey on a home laser printer. | **Geometry & Monochrome Rendering Validator:** Enforce character-to-millimeter box width ratios, mandatory ruled baseline guides for multi-word responses, and greyscale luminance/pattern differentiation checks. | 
| **F9: Ambiguous or Unkeyable Prompts** | Violates Principle 11 (Answerability). | A question asks *"What do you notice about this picture?"* or *"Write a sentence about magnets"* where dozens of trivial or off-target responses are technically valid. | **Constraint-Specificity & Blind-Solver Gate:** Require every open prompt to specify the exact target dimension and concept constraint (e.g., *"Use the words **poles** and **repel** to explain why Magnet A pushes Magnet B away"*). | 
| **F10: False Mastery Over-Claiming** | Violates System Constraint ("Do not assume that a 15-minute lesson guarantees mastery"). | The lesson summary or parent header claims *"Your child has now mastered Fractions!"* or skips foundational reinforcement to test advanced edge cases appropriate only after weeks of practice. | **Epistemic Humility & Scope Framing Check:** Require lesson footers and answer keys to frame completion as *Initial Comprehension & First Practice*, recommending spaced follow-up rather than claiming complete mastery. | 

## Section G: Pre-Acceptance Evaluation Checklist

Before any generated lesson is accepted for rendering to the parent and child, the software pipeline must execute this **7-Gate Automated Pre-Acceptance Checklist**. A single **FAIL** on any blocking criterion rejects the draft and triggers targeted regeneration of the failing component.

### Gate 1: Source Fidelity & First-Time Learning Audit

* \[ \] **1.1 Zero Hallucinated Facts \[Blocking\]:** 100% of domain definitions, rules, dates, and formulas map via positive entailment to the uploaded curriculum PDF.

* \[ \] **1.2 Zero Unexplained Prerequisites \[Blocking\]:** Every technical term, symbol, or operation used in Stages 2–5 is either explicitly introduced in Stage 1 (*Discover*) or present in the below-grade baseline lexicon.

* \[ \] **1.3 Analogy Boundary Integrity \[Blocking\]:** Any generated real-world analogy is clearly framed as a comparison and is never tested as a literal curriculum fact in *Apply* or *Recall*.

### Gate 2: Five-Stage Progression & Scaffolding Fade Audit

* \[ \] **2.1 Complete Stage Presence \[Blocking\]:** The lesson contains all five functional stages (**Discover, Reinforce, Vary, Apply, Recall**) in the approved sequence for its classified domain type (Section B).

* \[ \] **2.2 Worked Example Presence \[Blocking\]:** *Discover* includes at least one complete, visually annotated worked example or concrete model before asking the child to solve a problem.

* \[ \] **2.3 Monotonic Scaffolding Fade \[Blocking\]:** Hints, word banks, and partial steps decrease strictly from *Reinforce* to *Recall*, with zero word banks or answer cues in *Recall*.

* \[ \] **2.4 Representation Shift in *Vary* \[Blocking\]:** The *Vary* stage shifts at least one structural dimension (directionality, visual-to-symbolic modality, or error analysis) rather than merely repeating *Reinforce* with different numbers/words.

### Gate 3: Attention, Cognitive Load & Reading Density Audit

* \[ \] **3.1 Opening Curiosity Hook \[Blocking\]:** *Discover* begins with a concrete framing question, contrasting case, or relatable mystery resolved by the core lesson concept.

* \[ \] **3.2 Passive Reading Span Cap \[Blocking\]:** No contiguous block of reading exceeds the grade-band word ceiling (45 words for G1–2; 80 words for G3–5; 120 words for G6+) before requiring a physical pencil action.

* \[ \] **3.3 Concept Novelty Cap \[Blocking\]:** The lesson introduces at most 1 primary concept (or $\le 3$ tightly coupled sub-concepts / $\le 5$ vocabulary terms).

* \[ \] **3.4 Instruction Readability Floor \[Blocking\]:** All activity instructions score at or below `Target_Grade - 1` readability and contain at most 2 sequential action verbs per sentence.

* \[ \] **3.5 Zero Seductive Details \[Blocking\]:** Every narrative character, object, or illustration prompt has a direct functional mapping to the target learning objective.

### Gate 4: Paper-First Mechanics & Purposeful Activity Audit

* \[ \] **4.1 Zero Prohibited Mechanics \[Blocking\]:** The lesson contains zero word searches, unlabelled mazes, anagrams, decorative coloring tasks, or Symmetric 1-to-1 Matching lists without distractors.

* \[ \] **4.2 Content-Blind Unsolvability \[Blocking\]:** A heuristic solver masked from domain semantics cannot solve the *Reinforce*, *Vary*, *Apply*, or *Recall* tasks via string length, grammar cues, or elimination alone.

* \[ \] **4.3 Mechanic Diversity \[Blocking\]:** The lesson employs at least 3 distinct pencil mechanics from the Section D taxonomy across its 5 stages.

* \[ \] **4.4 Worked-Start Modelling \[Blocking\]:** Every multi-column table, custom diagram annotation, or logic grid includes a pre-filled greyscale `Example` item so the child can see how to execute the task without adult explanation.

* \[ \] **4.5 Zero External Tools \[Blocking\]:** No instruction requires scissors, glue, rulers, colored pencils, dice, timers, screens, or adult dictation.

### Gate 5: Landscape A4 Physical Layout & Monochrome Print Audit

* \[ \] **5.1 Page Count & Orientation Compliance \[Blocking\]:** The entire lesson fits cleanly within **1 to 2 Landscape A4 pages (**$297\text{ mm} \times 210\text{ mm}$**)** with zero text clipping or orphan overflow.

* \[ \] **5.2 Whitespace & Visual Breathing Room \[Blocking\]:** Open background whitespace constitutes $\ge 30\%$ of each landscape A4 page.

* \[ \] **5.3 Handwriting Ergonomics \[Blocking\]:** Every write-in box and blank meets the grade-band minimum line height ($12\text{–}14\text{ mm}$ for G1–2; $9\text{–}10\text{ mm}$ for G3–5; $7\text{–}8\text{ mm}$ for G6+) and horizontal character width, with ruled baseline guides provided for all multi-word responses.

* \[ \] **5.4 Greyscale Print Fidelity \[Blocking\]:** When rendered in 8-bit greyscale, all diagrams, charts, and visual callouts maintain $\ge 4.5:1$ contrast and rely on patterns/labels/shapes rather than colour hue.

### Gate 6: Realistic 15-Minute Timing & Motor Budget Audit

* \[ \] **6.1 Total Duration Corridor \[Blocking\]:** Predicted lesson duration $T_{\text{lesson}}$ calculated via the Section E 4-component behavioral model falls strictly between **13.0 and 16.5 minutes**.

* \[ \] **6.2 Stage Time Balance \[Blocking\]:** No single activity block exceeds **4.0 minutes**, and *Apply + Recall* account for **35% to 45%** of total cognitive time.

* \[ \] **6.3 Handwriting Motor Cap \[Blocking\]:** Total expected student handwriting remains under the grade-band word cap ($\le 15\text{ words}$ for G1–2; $\le 45\text{ words}$ for G3–5; $\le 80\text{ words}$ for G6+) and consumes $\le 35\%$ of total lesson time.

* \[ \] **6.4 Scope-Slicing Verification \[Blocking\]:** If the uploaded curriculum PDF exceeded the 15-minute concept budget, the lesson explicitly scopes itself to a single coherent foundational sub-unit rather than compressing explanations.

### Gate 7: Answerability, Anti-Copying & Epistemic Humility Audit

* \[ \] **7.1 Blind-Solver Convergence \[Blocking\]:** An independent solver agent given *only* the generated student worksheet converges on the exact canonical answer key for 100% of items without flagging ambiguity.

* \[ \] **7.2 Anti-Copy Isolation in *Recall* \[Blocking\]:** The *Recall* stage cannot be answered by copying a contiguous phrase visible on the same unfolded workspace and is visually isolated (via page break, fold line, or synthesis framing).

* \[ \] **7.3 Answer Key & Rubric Completeness \[Blocking\]:** Every student action is paired in the internal metadata with a canonical answer, acceptable variations, and specific misconception notes for future answer-key generation.

* \[ \] **7.4 Honest Mastery Framing \[Blocking\]:** Lesson headers and completion messages celebrate *first-time understanding and effort* without claiming permanent mastery from a single 15-minute session.