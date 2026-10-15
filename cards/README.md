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
   | Portrait | Up to four of the deck's pictures together, preferring ones the other topics don't share (never the generic crowd, pin, calendar, globe or star) + "Name the city!" | The topic name + the author's summary line |

   When the sheet has summary lines for two or more topics, one more card goes at the end: **"Which city did what?"**. Its back lists each topic's summary line ("Edinburgh = Banking Capital of Scotland"), so the child sees why each place mattered and how the places differ. It also closes the "Mix all" round.

   Cards whose answer the sheet repeats most come first and get a ★.

   A fill-in answer that shares a name with another fact about the same place gets a **"Think:" link** made of that fact's own words. For example, the museum card shows "Think: … shipyard built the RMS Titanic". The linking word can't come from the place's heading, and it must end a name in the other fact, so "Bank" in "Bank of Scotland" doesn't count.

   Every card except the final picture has a small **hint** under the clue: the answer's shape with only first letters showing ("R____ L____", "2__,___"). Short joining words (of, and, the) stay, and answers too short to hint at get no hint. A check confirms each hint matches its answer letter by letter.
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

## Teaching rules for hard names, places and concepts

These came from trying the cards out with the family. Every new card type, trick list or game must follow them.

1. **Hard things get extra help.** New place names, people's names and technical words are what children forget first. Give each one **2–3 supporting clues from different angles**, for example a picture, a sound trick and another fact from the same sheet, rather than one bare card.
2. **One jump only.** A trick must go straight from something the child already knows to the answer:
   - Good: "LAG-an: the river is so laggy" (gamers know *lag*).
   - Bad: snail → slow → "lagging" → Lagan (three jumps, through an adult word).
3. **From the child's world.** Hooks use games, cricket, food, school and YouTube, not adult vocabulary.
4. **Let the child make the trick.** Leave a "my trick: ____" box. A link the child invents sticks better than one handed over, and it can't be too adult.
5. **Tricks are never answers.** Mark them as tricks. The card back keeps the sheet's exact words, because exams mark the book's wording.
6. **A generic picture only says *what kind* of answer it is** (a river, a ship, a date). It doesn't say *which one*. When several cards share a picture (Thames, Rea, Lagan), the clues must tell them apart.

## History: events, causes and results

A sheet can also be laid out as numbered sections with bullets under them, as history notes usually are ("1. CAUSES OF THE UPRISING", "2. COURSE OF THE UPRISING", "3. LEADERS AND CENTRES", "4. RESULTS…"). Each section becomes its own deck, and its heading tells the engine what the bullets are:

| Section heading has… | Cards |
| :--- | :--- |
| causes / reasons | Fill-in cards asking **"Why did it happen?"**, then **"Name them all"**: each cause's bold name, for "state four causes" questions |
| results / consequences / effects / impact | Fill-in cards asking **"What changed after?"**, then "Name them all" |
| course / events / timeline | Fill-in cards, then a **timeline card**: the dated events scrambled with their dates blanked on the front, in date order with dates on the back |
| leaders / people / centres | Fill-in cards that hide the person's name, then a **match card**: names on one line, places on the other |

On any sheet, a sentence with *because / due to / led to / resulted in* becomes a **why card**, for example "The army was reorganised because _____ — Why?". The answer is the sheet's own reason. A bullet with nothing bold and no date becomes a "Finish it." card showing its first few words.

Mixed rounds shuffle only single-fact cards. Whole-topic cards (lists, timelines, pairs, final pictures, the comparison) stay with their deck.

`sample/history-sheet.pdf` is a synthetic example built by `test/fixtures/make_sample.py`. These rules have not yet been tried on a real school history sheet.

## People

A heading is treated as a **person** when its description says what they were (reformer, leader, scientist, king…), gives life years ("(1772–1833)"), or the name starts with a title (Raja, Rani, Swami, Mahatma…). A person's deck gets:

- **"Who am I?" riddles.** The heading's description ("Social reformer (1772–1833)") and facts with nothing bold, with **every part of the name hidden**: "Roy" as well as "Ram Mohan Roy". A check blocks any riddle that shows part of the name.
- **"What problem were they solving?"** For sentences with *against / to stop / to end / to improve / to abolish…*, the card hides what they worked against or for ("Fought against _____ discrimination").
- The usual fill-ins, why cards and a final "Who am I?" picture card.

Across the sheet, people with life years get a **"Who came first?"** card: names scrambled on the front, birth order with years on the back. The "who did what?" card speaks of causes ("Every reformer had their own cause").

`sample/people-sheet.pdf` (three 19th-century reformers) is a synthetic example. Not yet tried on a real school sheet.

## Name fun facts

Some card backs carry a small footer such as **Fun fact:** "-ham" is an old English word for home (Birmingham). Names are among the hardest things to remember, and knowing what a name means makes it stick.

- **Where:** only on backs whose answer is the place name itself (the riddle cards and the final card).
- **Never:** on a card front, as an answer, or in any test of the child. A tip is extra, not from the sheet.
- **Source:** only exact names listed in `engine/nametips.js`. There is no rule like "every -ham means home", because Durham and Oldham would come out wrong.
- **Left out:** names with uncertain or disputed origins (London, Lagan, for now).
- **Famous things:** the same file also lists fun facts about well-known things a child already knows, such as the Titanic and its iceberg. They appear on the back of a card whose answer names that thing, under the same rules.
- **Status:** the four entries (Belfast, Birmingham, Cardiff, Edinburgh) were drafted from standard place-name explanations. A person should confirm them before wide use.

## What it does not do yet

- Tables, practice questions and memory tips are not turned into cards.
- Scanned pages or phone photos are not read (no OCR).
- It has no memory tricks, no "my trick" box, no supporting clues for hard names, no games beyond flip-and-mix, and no progress tracking.
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

The sample PDFs in `sample/` are synthetic. Rebuild them with `python cards/test/fixtures/make_sample.py` from the repo root.

Passing tests show the rules work as designed. They say nothing about whether children learn from the cards.

## Files

| File | Job |
| :--- | :--- |
| `engine/extract.js` | PDF → lines, with bold runs marked |
| `engine/structure.js` | Lines → topics, facts, summary lines; everything else goes into `other` |
| `engine/cards.js` | Facts → cards (answer choice, clue shortening, order, portrait, hints, links) |
| `engine/events.js` | Why, timeline, match and "name them all" cards for history-style topics |
| `engine/nametips.js` | The checked name and thing fun facts |
| `engine/symbols.js` | The sketch library and the word → picture rules |
| `engine/checks.js` | The checks above |
| `engine/render.js` | Card → HTML, shared by the screen and the print sheets; escapes all sheet text |
| `engine/index.js` | `makeDecks(pdfjs, bytes)` → `{sheet, built, check}` |
| `app.js`, `index.html`, `style.css` | The page |
