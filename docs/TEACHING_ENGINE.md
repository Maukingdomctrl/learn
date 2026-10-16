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

The upload page offers two prominent game buttons: Detective and Superhero. Choose ICSE Standard 7, 8, or 9; Standard 8 is selected by default. The two games print the same cards with different colours and titles. The standard changes only the wording of each question: "Which year goes in the gap?" (7), "Which year fits the gap?" (8), "Supply the missing year." (9).

The print preview is collapsed by default to keep the page focused on choosing a game. Select “Preview before printing” to open the preview panel, choose a game, and create a preview PDF. The preview can be hidden again without changing the game buttons. The separate command-line interface continues to produce JSON when requested.

The `/library` page is a separate, curated starter collection of openly licensed social-studies visuals, grouped under Indian Studies and UK comparison. Each entry links to its Wikimedia Commons file page and license, with creator credit. The gallery loads images directly from Commons in the visitor's browser; Learn does not download, bundle, or persist those images. Internet access is needed to view them. The topic labels are broad study suggestions, not an official claim that a topic belongs to every ICSE school's Standard 7–9 sequence. The UK comparison collection is supplemental, not an ICSE syllabus endorsement. Images are not yet automatically inserted into generated game PDFs; those continue to use images embedded in the uploaded source PDF.

To use `learn.mauforge.com`, first deploy and test the Render URL, then add that custom domain to the Render service and follow the DNS record Render provides in Cloudflare. DNS records should be taken from the live Render dashboard rather than guessed. Keep the hostname behind Cloudflare Access if access should remain private.

## Game cards

**How the sheet is read.** The card game reads the uploaded PDF's printed lines (`learn/teaching_engine/sheet.py`), not only its text blocks, because sheets printed from a browser store every printed line as its own block. Line positions, font sizes and bullet marks, typed (•) or drawn as dots, show where each item starts:

- Wrapped lines are joined back into whole bullets and sentences ("Non-" + "Cooperation" stays "Non-Cooperation").
- Page headers, footers, page numbers, the sheet's title lines and bare list numbers ("1.") are left out.
- A numbered heading followed by bullets ("1. Dadabhai Naoroji (1825–1917) – "Grand Old Man of India"") is a topic, and its bullets belong to it. A sub-heading such as "Four main stages" labels what follows without naming an answer.
- Comparison tables are read cell by cell under their header row. Bullet lists printed side by side under short headings ("WEATHER", "CLIMATE") are read as panels, and a row of years with short labels centred under them as a timeline.
- A box drawn in a dingbat font in place of a letter the PDF's font lacked (a subscript, "₹") marks that letter as lost; at the start of a line, followed by a space, it is a bullet.
- A call-out label run into its text ("BIG IDEA • Change is caused by …") becomes the card's context line, and a task the sheet sets ("Practice: …", "Extended response: …") becomes a practice question.
- Practice questions keep their answers: "— Ans: …" after the question, or the same number in a later answer key ("A. Fill in the Blanks – Answers 1. River Thames").
- A model-answer sheet prints "Question 3" on a line of its own, then the question, then the answer's points. The question keeps every point, sub-heading ("When animals are alive:") and note under it as its answer, one line each, until the next question number or a heading printed as large. The points also make cards of their own; a "Note:" line stays on the answer sheet only.
- Small print after the sheet's last line of main text, such as a credit ("Model answers based on the textbook …"), is left out.
- Pages without a text layer, and calls without a PDF, use the fact inventory instead.

**What a card asks.** Each card asks one plain question. Every clue and answer is a run of the sheet's own words, with some words hidden behind a gap; the only added words are the fixed questions and labels.

| Card | Made from | Front | Answer sheet |
| :--- | :--- | :--- | :--- |
| Name it | A topic heading | The heading with the name hidden: "______ (1825–1917) – "Grand Old Man of India"". *Who is this?* | Dadabhai Naoroji |
| Riddle | A bullet under a topic | The bullet with every capitalised use of the topic's name hidden. *Who is this about?* | The topic's name |
| Fill the gap | A bullet with a defined term, date, year, number or century | The bullet with one value hidden: a term defined with "is called" or "means" first, then a full date, a year outside brackets, a number with a unit | The hidden value |
| What is it called? | "Term: meaning" lines listed under no named topic | The meaning | The term |
| What goes in the gap? | A formula, a fact such as "1 km = 1,000 m", or an arrow chain | The line with its result, or a middle step, hidden | The hidden part |
| Finish the sentence | Any other whole sentence | Its first words, cut where the rest starts a phrase ("Dead animals are decomposed …"), never inside brackets; a sentence with "because" stops there | The rest |
| Compare | A "Feature \| A \| B" table row | The things compared. *What is each one's Popular Title?* | Each one's value |
| Which one? | A row of a "Concept \| Rule \| Example" table | One description. *Which concept is it?* | The row's name |
| Timeline | A printed timeline | One event. *Which year goes with it?* One more card lists the events to put in time order | The year; the order |
| Which one is it? | Side-by-side panels | One line. *Which one is it: WEATHER or CLIMATE?* | The panel's heading |
| Practice question | The sheet's own questions, tasks, question tables and worked examples | The question | The sheet's answer (a model answer keeps one line per point), or a note that the sheet has none |
| Memory tip | A "Memory tip" or "Think" line | The tip's opening words. *Say the rest of the tip.* | The whole tip |
| Picture | A picture printed beside a topic | The picture. *Who is this?* | The topic's name |

Some things make no card:

- a picture the sheet does not place beside a topic;
- text with letters the PDF's own font could not encode (lost boxes, or runs such as "IIIII"). The answer sheet names the page so an adult can check it by eye;
- columns of measurements, values the sheet gives rather than works out ("radius = 7 cm"), and labels from a diagram ("base = 8 cm");
- class, grade and page numbers, which are never answers.

**How it prints.** Cards print one-sided, eight 85 × 68.8 mm cards to an A4 page, with dashed cut lines. A card shows only its number, an optional line saying what it is about, the clue and the question: no source codes, rules or writing boxes. The answer sheet follows on its own pages, with each card's number, answer and the page of the study sheet, plus notes for the adult. A claim containing "first", "largest", "invented", "only" or a similar word is still played, but its answer-sheet entry says: "Check first: the sheet says “first”. Confirm it in the textbook before learning it."

Text prints in FiraGO from `pymupdf-fonts` (SIL Open Font Licence), which covers dashes, arrows, the rupee sign and Indian names; only the letters used are embedded. Without that package the cards fall back to Helvetica, with ASCII stand-ins such as "->".

Learn-generated card PDFs are rejected as input, so printed questions and answers cannot become study facts. The app does not invent or fetch pictures.

**Limits.** The reading rules were tuned on the sheets in `tests/sheets/` and `cards/sample/`, plus the extracted text of a UK cities sheet: Grade 8 revision sheets printed from a browser, one-page history, civics, chemistry, physics and maths sheets, and small synthetic layout tests. Two columns of running text, scanned pages and unfamiliar layouts are likely to come out worse. Cards repeat the sheet's own words, so mistakes in the sheet appear on the cards. The cards have not been tried with children.

## Tests

```bash
pytest tests/test_teaching_engine.py tests/test_teaching_sheet.py tests/test_teaching_print.py tests/test_extraction.py -q
```

Tests make no network or model calls. They use synthetic source units and the sample sheets in `tests/sheets/`. They check source fidelity, page links, heuristic mentions, review holds, complete coverage and support fading, and for the cards: how each sample sheet is read, which words become the clue and which the answer, that answers stay off the cards, and that text stays inside its card. Passing tests show the cards are built as described, not that they teach well. No child pilot has been run.
