# Learn Card Engine — Build Log

**Started:** 15 October 2026
**Baseline:** After PR C (#9), merged into `main`
**Status:** Planning and repository inspection
**Rule:** Record decisions, changes, commands, tests, and known limitations here as work progresses.

---

## 1. Verified Project Baseline

The following PRs were reported merged into `main`:

- **PR A (#7):** Model-call logging, focused source context, teaching plan, bounded retry on truncated model output.
- **PR B (#8):** Deterministic SVG renderer for five diagram types and D8 grounding/layout checks.
- **PR C (#9):** Partly completed practice diagrams, answers derived from diagram specifications, and D9 visual-progression checks.

PR C merge commit: `cbf0d0fb5bc4ae0061ba4efaad4f7dfe460d4e5e`

The PR C report stated that 128 tests passed and Ruff checks were clean. These results have not been independently rerun as part of this card-engine project.

**Known limitation:** The existing lesson pipeline has not been demonstrated to produce reliable, high-quality output from the live model and real curriculum PDFs. Tests using fixtures do not establish real-world teaching quality.

## 2. Product Goal

Build a focused engine that transforms an existing lesson or extracted curriculum text into a printable educational card deck.

The intended workflow is:

1. Read an existing lesson or extract text from a supplied PDF.
2. Select source-supported facts suitable for teaching and a mystery.
3. Create teaching cards that explain the facts before the game begins.
4. Create progressive clue cards that lead to a solvable answer.
5. Provide an answer/reveal card and parent solutions.
6. Arrange the cards into a printable PDF deck with cut lines.

The child uses paper and pencil. A screen is not required for the activity.

## 3. Core Design Constraints

- Source-grounded: never invent facts, clues, or answers.
- Teach before testing: the child must receive the information needed to solve the mystery.
- Solvable: the answer must be supported by the supplied material and confirmed by the answer key.
- Ink-efficient: white backgrounds, predominantly black outline artwork, minimal solid fills, and no colour-dependent meaning.
- Print-first: readable text, consistent card sizes, practical cut lines, and ordinary-printer compatibility.
- Local-first: the basic card-generation workflow should not require paid AI API calls.
- Minimal dependencies: inspect and reuse the existing project infrastructure before installing anything.
- Keep the card engine separate from the existing lesson-generation workflow until the standalone deck works.

## 4. Existing Infrastructure to Inspect and Potentially Reuse

These are candidates for reuse, not yet verified implementation decisions:

- Existing PDF text extraction.
- Existing PDF layout and export code.
- Existing deterministic SVG diagram renderer.
- Existing source-grounding and answer-validation ideas.
- Existing project test and lint setup.

Inspect the code and dependency files before deciding whether any replacement or new package is necessary.

## 5. Open-Source Visual Candidates

No new libraries or assets have been installed or selected yet.

- **Tabler Icons:** https://tabler.io/icons
  Candidate for consistent outline icons. SVG files may be copied as static assets rather than adding a runtime dependency.

- **Openclipart:** https://openclipart.org/
  Candidate for recognisable objects and scenes. Check the licence and suitability of each selected asset.

- **Open Doodles:** https://www.opendoodles.com/
  Optional source for decorative hand-drawn illustrations, if they fit the print style.

Reuse the existing PDF renderer if practical. Consider an SVG-to-PDF converter only if the current stack cannot render the selected SVG assets adequately.

## 6. Agreed Working Rules

- Work with ChatGPT and the existing repository; no Opus session is required for this phase.
- Do not buy API credits or make paid model calls for the basic card-engine path.
- Do not install dependencies until the current stack has been inspected.
- Do not commit the private UK cities curriculum PDF to the public repository.
- Use a small synthetic fixture for automated tests where possible.
- Build and test one complete standalone card deck before integrating it with the website.
- Do not expand the lesson-generation pipeline unless a demonstrated requirement calls for it.
- Record each meaningful decision, implementation change, dependency, test result, and unresolved issue in this file.
- Distinguish completed work from proposed work. Never label a step complete without evidence.

## 7. Work Log

### 2026-10-15 — Initial planning

**Completed**
- Reviewed `docs/PROJECT_OVERVIEW.md`.
- Chose this separate file for card-engine planning and implementation records.
- Defined the intended card-deck workflow and core constraints.
- Identified candidate visual-asset sources.

**Not yet done**
- Inspect current PDF, extraction, and SVG-rendering implementation.
- Inspect dependency files and package availability.
- Choose the minimum visual-asset approach.
- Build a standalone example deck.
- Test printing, card layout, clue solvability, and answer correctness.
- Connect the working engine to the website.

**Dependencies installed for this work:** None.
**Card-engine implementation changes:** None.
**Standalone deck tested:** No.

## 8. Next Step

Inspect the existing source tree and dependency files to determine what PDF and SVG capabilities are already available. Do not install anything until that inspection is complete.

After inspection, update this log with the observed facts and the smallest justified next step.

### Dependency inspection — 2026-10-15

**Observed in the active `.venv`:**
- `pypdf` 6.20.1 is installed (BSD-3-Clause).
- `PyMuPDF` 1.28.2 is installed (AGPL-3.0 or Artifex commercial licence); consider licensing before relying on it in a distributed product.
- `reportlab`, `cairosvg`, `svglib`, `Pillow`, and `pdfplumber` were not found by `pip show`.

**Decision:** No package has been installed. Inspect the current dependencies and PDF/SVG implementation before choosing any additions.

### Rendering inspection — 2026-10-15

**Observed in the existing implementation:**
- `learn/rendering.py` uses Jinja2 HTML templates and Playwright with headless Chromium to generate PDFs.
- It measures page layout and overflow in the browser before returning the generated PDFs.
- The renderer embeds existing SVG drawings from `learn/visuals/svg.py`.
- `pypdf` reads generated PDF dimensions and extracts text for inspection.

**Decision:** Reuse the existing HTML/CSS, Playwright, and SVG pipeline for the card engine unless a concrete limitation is demonstrated. Do not install ReportLab, CairoSVG, svglib, or image-processing dependencies merely to create the first deck.

**Next:** Inspect the existing templates, styles, and static assets for reusable card layouts and illustrations.

### Template and asset inventory — 2026-10-15

**Observed:**
- Four HTML/Jinja templates exist: `student.html.j2`, `key.html.j2`, `result.html.j2`, and `upload.html.j2`.
- The file search found no separate CSS, SVG asset, or raster-image files in the searched locations.
- Existing diagrams are generated by Python SVG code.

**Decision:** Inspect the current template styling before creating card-specific styles or adding visual assets. No dependencies installed.

### Student-template inspection — 2026-10-15

**Observed in `learn/templates/student.html.j2`:**
- The existing lesson output uses landscape A4 pages.
- Styling is embedded in the HTML template; no separate stylesheet was found in the inspected file inventory.
- The template uses black text, white backgrounds, borders, writing lines, and existing SVG diagrams.
- The existing renderer uses Playwright and Chromium to produce PDFs.

**Decision:** Keep the existing lesson templates unchanged. The card deck should eventually use its own template and rendering entry point while reusing the existing Playwright PDF approach.

**Child-safety and quality priorities:**
- Explain the relevant facts before presenting mystery clues.
- Keep every clue answerable from the supplied teaching material.
- Verify the answer/reveal card against the source.
- Use age-appropriate language and readable print sizes.
- Inspect the final PDF for clipped text, ambiguous clues, and missing answers before treating it as usable.

**Dependencies installed:** None.
**Existing application code changed:** No.
**Card deck produced and tested:** No.

### First card-deck specification — 2026-10-15

**Status: Planned; not implemented or tested.**

**Prototype:** Birmingham Mystery Deck, using locally reviewed facts from the existing UK cities curriculum material. Keep the source PDF out of the public repository.

**Format:** Two landscape A4 sheets, four cut-out cards per sheet, dashed cut lines, white backgrounds, predominantly black outline illustrations.

**Sheet 1 — Teach before play**
- Three teaching cards explaining source-supported facts.
- One instruction card explaining how to play.

**Sheet 2 — Solve the mystery**
- Three progressive clues, from broad to decisive.
- One answer/reveal card with the answer, explanation, and parent-facing source references. The parent removes this card before play.

**Non-negotiable quality requirements**
- Every factual statement and clue must be traceable to the source.
- Teaching cards must provide the knowledge needed to solve the mystery.
- The clues must lead fairly to one supported answer.
- The answer card must explain why the clues support that answer.
- The rendered PDF must be checked for text clipping, readability, cut lines, and ink-heavy artwork.

**Implementation constraints**
- Reuse the existing Playwright/Chromium PDF rendering infrastructure.
- No paid AI API calls for the basic workflow.
- No new package installations until a concrete need is demonstrated.
- Use static open-source SVG artwork only after checking the asset licence and print suitability.

**Completion gate:** Do not call the prototype complete until the PDF has been generated, inspected, and its factual accuracy and clue solvability have been checked.

**Current status:** Specification only; no card-engine code, assets, or PDFs have been created by this step.

### Source identity check — 2026-10-15

**Verified:** The two six-page curriculum PDFs have identical SHA-256 hashes (`1a7de081f95fbb24b833a3ad2f54ac5e05a571a49e9416c22deefe0c013ecea6`) and identical size (15,506 bytes).

**Decision:** Use `output/16a9d5b93d3d4150a150aa910a82c662/source.pdf` as the canonical local source. Keep curriculum PDFs out of the public repository.


### Birmingham Mystery Deck — draft card copy — 2026-10-15

**Status: Draft only. Not implemented, rendered, or child-tested.**

#### Card 1 — Where is Birmingham?
Birmingham is a city in the West Midlands, England. The River Rea flows through it.

#### Card 2 — Before the factories
In medieval times, Birmingham was a medium-sized market town. A market town is a place where people gather to buy and sell goods. Birmingham grew to international prominence in the 18th century.

#### Card 3 — Machines change how things are made
The Industrial Revolution was a period when machines and factories changed how many goods were made. Steam engines already existed. In Birmingham, Matthew Boulton and James Watt developed improved, more efficient steam engines for industrial machinery.

#### Card 4 — How to play
Read the three teaching cards first. Keep the answer card aside. Read the clues in order and write your guess after each clue. Score 3 points for solving after Clue 1, 2 after Clue 2, or 1 after Clue 3.

#### Card 5 — Clue 1
I am a city in England's West Midlands.

#### Card 6 — Clue 2
A river called the Rea flows through me. Long ago, I was a medieval market town.

#### Card 7 — Clue 3
In my city, Matthew Boulton and James Watt worked together to improve steam engines for industrial machinery.

#### Card 8 — Answer and parent notes
**Answer: Birmingham.**

Clue 1 identifies the region. Clue 2 adds the River Rea and the city's market-town history. Clue 3 points to the Boulton and Watt partnership.

**Source note:** The supplied curriculum supports the location, River Rea and market-town history. Birmingham City Council's Archives of Soho supports the more precise account of Boulton and Watt's work. The statement that the steam engine was invented in Birmingham should not be repeated as written.

#### Fact-check references
- Birmingham City Council, Archives of Soho — Steam engines:
  https://www.birmingham.gov.uk/info/50165/birmingham_connection/1579/archives_of_soho/7
- Birmingham City Council, Archives of Soho — James Watt:
  https://www.birmingham.gov.uk/info/50165/birmingham_connection/1579/archives_of_soho/3
- HISTORY.com — Industrial Revolution:
  https://www.history.com/articles/industrial-revolution

#### Review still required
- Confirm the age and reading level for the intended children.
- Review whether the clues are sufficiently distinctive and fair.
- Check every source-derived fact against the local curriculum PDF.
- Keep curriculum facts separate from supplemental external explanations.
- Design and inspect the monochrome illustrations and printable card layout.
- Verify the answer/reveal card and source references in the rendered PDF.

**Code changes:** None.
**Dependencies installed:** None.
**PDF generated:** No.
**Child testing:** Not performed.

### Printable card visual specification — 2026-10-15

**Status: Design decision; not yet implemented or tested.**

- Paper: A4 landscape, two sheets.
- Grid: four equal cards per sheet, 2 × 2.
- Content: three teaching cards and one instruction card on sheet 1; three progressive clue cards and one parent-only answer/reveal card on sheet 2.
- Printing: white background, black outline artwork, no colour-dependent information, minimal ink coverage.
- Card design: clear numbered label, readable title, short body text, one relevant illustration where useful, and consistent spacing.
- Cutting: dashed guides between cards.
- Answer card: explicitly marked “PARENT ONLY — REMOVE BEFORE PLAY”.
- Rendering: reuse Playwright/Chromium and the existing HTML-to-PDF approach; keep this feature separate from the existing lesson templates.
- Assets: investigate a small set of Tabler SVG icons as static files; record asset source and licence. No npm package or new Python dependency planned.
- Review: inspect the actual PDF for readability, clipped content, card boundaries, and ink coverage before approval.

**Changes made:** Build log only.
**Dependencies installed:** None.
**Card PDF generated:** No.

### Product clarification — source-first visual associations — 2026-10-15

**This decision supersedes the earlier proposal to depend on external illustration libraries for the core workflow.**

The supplied sheets are the complete content source for ordinary card generation. Learn must not search the web, search stock artwork, or add outside facts during this workflow.

**Required behaviour:**
- Extract supplied text, images, diagrams, tables, labels, and formulas.
- Associate existing visuals with their relevant explanations and facts.
- Preserve original visual material wherever possible.
- Use these associations to create teaching cards and progressive visual clue cards.
- Keep formulas, symbols, labels, units, and equations faithful to the source.
- Generate the answer/reveal card from the same source-supported associations.
- Do not silently invent missing content or correct/replace source claims.
- Flag ambiguous or unsupported associations for review instead of guessing.
- External fact-checking is a separate, explicitly requested mode.

**Implementation direction:**
- Inspect local PDF extraction capabilities for text, embedded images, and page layout.
- Reuse existing Playwright/Chromium, HTML/CSS, and SVG rendering.
- Do not install visual libraries or search for replacement artwork unless a demonstrated requirement arises.

**Status:** Design decision only. Association logic has not been implemented or tested.

### MVP subject scope — 2026-10-15

**Status: Scope decision; not yet implemented or tested.**

The first card-engine version targets Grade 8 material in three subjects only:

1. **Geography:** maps, locations, rivers, landforms, labels, and visual identification.
2. **History:** historical images, people, inventions, timelines, and event associations.
3. **Chemistry:** formulas, symbols, labelled diagrams, structures, and concept relationships.

**Shared workflow:**
- Use only the sheets supplied for the current task.
- Extract and associate relevant text, images, diagrams, labels, and formulas.
- Produce explanatory teaching cards before progressive visual clue cards.
- Include an answer/reveal card grounded in the same material.
- Preserve formulas, units, symbols, and source wording accurately.
- Flag material that cannot be interpreted reliably; do not invent missing information.
- Do not perform web searches or make paid AI calls during ordinary generation.

**Out of scope for v0.1:** General-purpose support for every school subject, external content discovery, and automatic supplementation of missing source material.

The earlier Birmingham card copy remains a review draft, not approved source-faithful output. Any fact changes or external corrections must remain explicitly labelled for review rather than silently substituted into generated cards.

**Dependencies installed:** None.
**Card-engine implementation:** Not started.
