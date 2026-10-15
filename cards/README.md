# Learn Cards — first version

A web page that turns a study-sheet PDF into picture cards. Children flip them one at a time on screen, or print them double-sided and cut them out.

- Runs entirely in the browser. The PDF never leaves the device.
- No AI and no accounts. Fixed rules make every decision.
- Separate from the Python lesson engine in `learn/`. It shares no code with it and doesn't follow its methodology spec.

> **Status — read this first.**
> - This is a first prototype. It has **not** been tested with children.
> - It has been tried on one machine-made sheet (UK cities) and on the synthetic sample in `sample/`. Other sheet layouts will often produce no cards. The page then says so.
> - The pictures are simple code-drawn sketches, not illustrations.

## What it does

1. **Reads the PDF** with pdf.js. It keeps the words the author printed in **bold**, because those mark what the author wants remembered.
2. **Finds the topics.** It looks for numbered headings like `1. BELFAST – Capital of Northern Ireland` followed by `•` bullet points. A bullet with `;` becomes separate facts. Lines like `• Belfast = Shipbuilding & Titanic` are kept as the author's summary.
3. **Makes cards for each topic.** Each topic becomes one deck:

   | Card | Front | Back |
   | :--- | :--- | :--- |
   | Riddle | The heading's description + "Which city?" | The topic name and the description |
   | Fill-in | The clause with the bold word blanked (or a date/number when nothing is bold), ≤ ~10 words | The hidden words + the full sentence |
   | Riddle | A fact with no bold word or number, names hidden | The topic name + the full sentence |
   | Portrait | Up to four of the deck's pictures together + "Name the city!" | The topic name + the author's summary line |

   Cards whose answer the sheet repeats most come first and get a ★.
4. **Picks a sketch** for each card from about 25 drawings, by words in the fact (river, ship, crown, factory, bank…). If nothing fits, the card shows a "draw it!" box instead of a wrong picture.
5. **Checks every card before showing or printing it.** If any check fails, nothing is shown and the page lists the problems:
   - every fact has a card;
   - every card back is word-for-word from the sheet;
   - every visible piece of a clue is in the sheet (the only added words are the fixed prompts);
   - a fill-in answer is inside its sentence;
   - a riddle doesn't contain its answer.

   The page also lists notes that don't block printing:
   - a riddle the sheet also links to another topic, which the card back names ("Also linked: Birmingham");
   - lines that are not on any card yet (tables, practice questions, tips).
6. **Plays and prints.**
   - **On screen:** one deck at a time, or "Mix all" shuffles every topic together.
   - **On paper:** A4 sheets with 10 business-card-size cards each (85 × 55 mm) and dashed cut lines. The backs come mirrored for double-sided printing ("flip on long edge").

## What it does not do yet

- Tables, practice questions and memory tips are not turned into cards.
- Scanned pages or phone photos are not read (no OCR).
- It has no memory tricks, no games beyond flip-and-mix, and no progress tracking.
- It can't catch a mistake in the sheet itself. Cards are only as correct as the PDF.

## Run it

It's a static site with no build step. Serve the folder and open it:

```bash
cd cards
python3 -m http.server 8000      # then open http://127.0.0.1:8000
```

The page loads pdf.js 5.4.624 and the fonts from public CDNs (jsDelivr, Google Fonts).

**Deploy (Cloudflare Pages):** connect the repo, set the root directory to `cards`, and leave the build command empty.

## Tests

```bash
cd cards
npm ci
npm test        # node --test; uses the sample PDF and hand-made lines, no network
```

`sample/sample-sheet.pdf` is synthetic. Rebuild it with `python cards/test/fixtures/make_sample.py` from the repo root.

Passing tests show the rules work as designed. They say nothing about whether children learn from the cards.

## Files

| File | Job |
| :--- | :--- |
| `engine/extract.js` | PDF → lines, with bold runs marked |
| `engine/structure.js` | Lines → topics, facts, summary lines; everything else goes into `other` |
| `engine/cards.js` | Facts → cards (answer choice, clue shortening, order, portrait) |
| `engine/symbols.js` | The sketch library and the word → picture rules |
| `engine/checks.js` | The checks above |
| `engine/render.js` | Card → HTML, shared by the screen and the print sheets; escapes all sheet text |
| `engine/index.js` | `makeDecks(pdfjs, bytes)` → `{sheet, built, check}` |
| `app.js`, `index.html`, `style.css` | The page |
