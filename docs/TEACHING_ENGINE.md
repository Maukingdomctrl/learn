# Learn Teaching Engine

The teaching engine is a local Python module, separate from card generation, the user interface, and the older printable-lesson pipeline. It needs no API key, model, network connection, or paid service.

```python
from learn.extraction import extract
from learn.teaching_engine import create_teaching_lesson, extract_facts

source = extract("UK_Important_Cities_Grade8.pdf")
inventory = extract_facts(source.units)
lesson = create_teaching_lesson(inventory)
print(lesson.model_dump_json(indent=2))
```

Or run it directly on a PDF and save the plan as JSON:

```bash
python -m learn.teaching_engine curriculum.pdf --out teaching_lesson.json [--pages 3-5]
```

## What it does

- Preserves each extracted source statement exactly, with its source unit and page.
- Holds extractor-flagged claims for review unless their fact IDs are explicitly approved.
- Gives each fact a child-facing prompt to explain the idea in their own words without silently paraphrasing a curriculum claim.
- Suggests a simple drawing using only words and relationships already present in the source.
- Offers a clearly labelled, generic memory scaffold and invites the child to make a personal association.
- Sequences three varied retrieval activities from full support to independent recall.

## Deliberate offline limits

This first offline version uses deterministic templates. It does not invent curriculum facts, compose topic-specific analogies, interpret images, or independently judge whether an explanation is correct. Its explanations teach the learner to unpack the exact source sentence; its memory scaffold is generic by design. This keeps the no-key version from adding unsupported claims. Review flagged facts and inspect the cited PDF pages, especially where diagrams carry information.

The older upload-to-printable-PDF workflow is separate and remains unchanged; it still uses its existing model integration. Running this teaching engine does not call that workflow or require its API key.

## Web app and Render deployment

The standalone upload page runs locally with:

```bash
uvicorn learn.teaching_web:app --reload
```

The repository's `render.yaml` defines a Render web service that launches only `learn.teaching_web:app` and installs `requirements-teaching.txt`, which excludes the Anthropic SDK and Playwright. In Render, create a new Blueprint from the GitHub repository and review the service before applying it. No AI/API secret or app password is needed.

The app has a 30 MB upload limit. It does not save uploaded PDFs or generated plans to app-managed storage: extraction reads the uploaded PDF in memory, and a print-ready A4 PDF is returned directly as the response. The upload page can render a side-window preview of the same generated PDF before download; the preview is held in the browser only and is rebuilt after any input changes. There is no database, object-storage bucket, job history, or server-side output archive. The HTTP upload framework may transiently buffer request data on the Render instance while processing; visitors' PDFs still travel to Render for processing. Render's free service can sleep while idle. The web app is public and requires no username or password. The app makes no paid AI calls.

The upload page offers two prominent game buttons: Detective and Superhero. Choose ICSE Standard 7, 8, or 9; Standard 8 is selected by default. Game sheets contain eight 85 × 68.8 mm cards per A4 sheet, with mirrored backs for duplex printing on the long edge. Detective cards make source-grounded evidence clues; Superhero cards turn retrieval into category-based “powers” and teammate teaching missions. Both modes include the PDF's own embedded images as separately page-cited visual-evidence cards; the app does not invent or fetch pictures. Every fact card back keeps its exact source sentence, page number, and unit ID. Oversized non-question text fragments are split into contiguous, page-cited excerpts so table extraction cannot prevent card generation; source questions stay intact. Candidate answers avoid obvious class, grade, standard, page, and question-number labels; question text is kept together and not converted into cloze blanks. Source facts remain unchanged in the inventory, while common formula symbols are represented with readable ASCII equivalents in print. Learn-generated card PDFs are rejected as input so printed prompts, answer sides, and labels cannot recursively become study facts. Extracted replacement characters are preserved and marked “Verify first,” rather than silently corrected. Children can add their own memory hook or sketch. Claims flagged by the extractor remain marked “Verify first.”

The print preview is collapsed by default to keep the page focused on choosing a game. Select “Preview before printing” to open the preview panel, choose a game, and create a preview PDF. The preview can be hidden again without changing the game buttons. The separate command-line interface continues to produce JSON when requested.

The `/library` page is a separate, curated starter collection of openly licensed social-studies visuals, grouped under Indian Studies and UK comparison. Each entry links to its Wikimedia Commons file page and license, with creator credit. The gallery loads images directly from Commons in the visitor's browser; Learn does not download, bundle, or persist those images. Internet access is needed to view them. The topic labels are broad study suggestions, not an official claim that a topic belongs to every ICSE school's Standard 7–9 sequence. The UK comparison collection is supplemental, not an ICSE syllabus endorsement. Images are not yet automatically inserted into generated game PDFs; those continue to use images embedded in the uploaded source PDF.

To use `learn.mauforge.com`, first deploy and test the Render URL, then add that custom domain to the Render service and follow the DNS record Render provides in Cloudflare. DNS records should be taken from the live Render dashboard rather than guessed. Keep the hostname behind Cloudflare Access if access should remain private.

## Tests

```bash
pytest tests/test_teaching_engine.py tests/test_extraction.py -q
```

Tests use synthetic source units and no network/model calls. They check source fidelity, page links, heuristic mentions, review holds, complete coverage, and support fading. No child pilot has been run.
