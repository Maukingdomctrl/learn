# Learn Cards — first version

A web page that turns a study-sheet PDF into picture cards. Children flip them one at a time on screen, or print them double-sided and cut them out.

- Runs entirely in the browser. The PDF never leaves the device.
- No AI and no accounts. Fixed rules make every decision.
- Separate from the Python lesson engine in `learn/`. It shares no code with it and doesn't follow its methodology spec.

> **The uploaded PDF is the fact sheet.** Every fact on every card comes from the PDF the parent or child uploads, and the checks block anything else. The engine only learns *how to ask*: what a question looks like for a place, a person, a cause or an institution. It never learns *what the facts are*. The sample PDFs in `sample/` exist only to test those rules. The one exception is the small checked list of "Fun facts" (see below), which is printed as a footer and never tested.

> **Status — read this first.**
> - This is a first prototype. It has **not** been tested with children.
> - It has been tried on one machine-made sheet (UK cities) and on the synthetic sample in `sample/`. Other sheet layouts will often produce no cards. The page then says so.
> - The pictures are simple icons, not illustrations. Photos appear only when the PDF itself contains them.

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
4. **Picks a picture** for each card, by words in the fact (river, ship, crown, factory, bank…). The pictures are outline icons from [Tabler Icons](https://tabler.io/icons) (MIT licence), copied into `engine/icons.js` by `scripts/build-icons.mjs` so nothing is downloaded at run time. One or two with no Tabler match (the rifle) are drawn by code. If nothing fits, the card shows a "draw it!" box instead of a wrong picture.
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

To make people stick, not just be quizzed once, each person's deck also gets:

- **Ages:** for each dated fact in their life, "Born 1820. How old, about?" → "about 36", with the sum on the back (1856 − 1820 = 36). It uses only the sheet's years and says "about" because birthdays can make it a year out. A check confirms every sum.
- **Both directions:** after the "what did they do?" cards and the ages, each piece of work comes back as "Founded the Brahmo Samaj in 1828 — Who am I?".
- **From memory:** the three most-repeated answers return near the end with no hint and no picture, just a "?".
- **A reminder line:** every card back about the person repeats their summary line from the sheet ("Remember: Raja Ram Mohan Roy = Brahmo Samaj + end of Sati"). Places get the same reminder when the sheet has summary lines.

Across the sheet, people with life years also get a **lifeline card**: a drawn time line with a bar for each life and a dot for each dated fact, so the child can see who lived at the same time. The back lists each life and its dated facts. There's also a **"Who came first?"** card: names scrambled on the front, birth order with years on the back. The "who did what?" card speaks of causes ("Every reformer had their own cause").

`sample/people-sheet.pdf` (three 19th-century reformers) is a synthetic example. Not yet tried on a real school sheet.

## Industries

A heading is an **industry** when its name says INDUSTRY ("SUGAR INDUSTRY") or its description starts with agro-, mineral-, forest- or marine-based. Bullets keep their own labels: "Raw material(s):", "Main/Other centres:" or "Main states:", "Products:". An industry's deck gets:

- **The riddle is the raw material:** "Raw material: sugarcane — Which industry?"
- **Fill-ins that ask by label:** "What does it need?" (raw material), "Where?" (centres), "What does it make?" (products).
- **"Why here?":** a *because* sentence about a location ("Mills are near the fields because _____") asks "Why here?". So does a bold word inside such a reason.
- **The final card is the chain:** *raw material → ? → product*, drawn from the sheet's bold words, with "Name the industry!" on the front and the summary line on the back.

Across the sheet:
- **"Which group?":** sorts the industries by the kind their headings give (agro-based or mineral-based).
- **"Where are they?":** matches each industry's first centre (places scrambled) to the industry.
- The comparison card reads "Each industry turns its own raw material into its own product."

`sample/industries-sheet.pdf` (cotton textiles, iron and steel, sugar) is a synthetic example. Not yet tried on a real school sheet.

## Civics: institutions

A heading is an **institution** when its name is one, such as PARLIAMENT, LOK SABHA, RAJYA SABHA, PRESIDENT, SUPREME COURT, HIGH COURT, CONSTITUTION, ELECTION COMMISSION, COUNCIL OF MINISTERS, PANCHAYAT or MUNICIPAL…, or when its description says "House of…", "court" or "Head of the State".

Each sentence is labelled by what it says, and the fill-in asks the matching question:
- **Chosen:** elected / appointed → *Who chooses them?*
- **Term:** "Term:", or a number of years → *For how long?*
- **Age:** "at least 25 years old", "age of 65" → *How old?*
- **In charge:** presiding officer / Speaker / chairman → *Who is in charge?*
- **Job:** protects / powers / functions / commander / guardian → *What does it do?*

The riddle is the heading's description ("Lower House of Parliament — Which one am I?"), and the final card asks "Name it!".

Across the sheet, **"Numbers to know"** lists every bold number once, smallest first ("2 years · 5 years · … · 65"). The back gives each fact behind them with its institution. That's the kind of detail exams ask for.

`sample/civics-sheet.pdf` (Lok Sabha, Rajya Sabha, the President, the Supreme Court) is a synthetic example with stable facts only. Not yet tried on a real school sheet.

## Geography: processes

A heading is a **process** when its name is one: MIGRATION, URBANISATION, POPULATION, EARTHQUAKES, FLOODS, CYCLONES, DROUGHTS, LANDSLIDES, TSUNAMIS, SOIL EROSION, DEFORESTATION, POLLUTION, GLOBAL WARMING, CLIMATE CHANGE, VOLCANOES, DISASTERS…

- **Definition first:** a bullet that defines the topic ("Migration is…", "An earthquake is…") opens the deck as "_____ is the movement of people… — What is it called?". The descriptor riddle is then left out, so the same thing isn't asked twice.
- **Fill-ins by label:** "Push factors:" → *What pushes people out?*; "Pull factors:" → *What pulls people in?*; "Causes:" → *Why does it happen?*; "Effects:" → *What does it lead to?*; "Measures:" / "Precautions:" / "Prevention:" → *What should be done?*
- **"Cause or effect?":** mixes the bold causes and effects to sort. "Causes" and "Effects" are the card's only own words; every item is checked against the sheet.
- **The final card is the chain** *cause → ? → effect*, from the first bold cause and effect.

`sample/processes-sheet.pdf` (migration, urbanisation, earthquakes) is a synthetic example. Not yet tried on a real school sheet.

## Groups: resources, soils, rocks…

In a topic section, bullets shaped like **"Group: a, b and c"** ("Renewable resources: solar energy, wind energy and water") are read as groups with their items, exactly as written. Two or more of them give a **"Which group?"** sort card: every item mixed on the front, each under its group on the back. The topic then ends with that sort instead of "name them all". "Name them all" now appears only for causes and results.

Sections about conservation or saving ask *What should be done?*

`sample/resources-sheet.pdf` is a synthetic example. Not yet tried on a real school sheet.

## Photos from the sheet

If the PDF itself prints a photo (a portrait beside a person's heading, a picture of a city), the riddle card and the final card for that person or place show it instead of an icon, in black and white.

- **Which photo:** the largest image between the heading (with a little room above it) and the next heading on the same page. Images smaller than half an inch (bullets, logos) are ignored. Each photo is used once. Topic sections such as "Causes" get none.
- **Source:** photos come only from the uploaded PDF, so they can't show the wrong person, and nothing is downloaded. Photos from the internet (e.g. Wikimedia) are not used. They would need a checked list of exact files, and this sandbox can't reach Wikimedia to check any.
- **On the page:** the photo is drawn in the browser at most 600 pixels wide. A photo that can't be decoded is left out and the icon is used instead.
- **Sample:** the portraits in `sample/people-sheet.pdf` are drawn grey silhouettes, not real photos.

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
| `engine/symbols.js` | Word → picture rules, the few hand-drawn pictures, the final-card layout |
| `engine/icons.js` | Generated: the Tabler icons the cards use, with their licence. Rebuild with `node scripts/build-icons.mjs` |
| `engine/checks.js` | The checks above |
| `engine/render.js` | Card → HTML, shared by the screen and the print sheets; escapes all sheet text |
| `engine/photos.js` | Finds images printed in the PDF and gives each to the heading it sits beside |
| `engine/index.js` | `makeDecks(pdfjs, bytes)` → `{sheet, built, check}` |
| `app.js`, `index.html`, `style.css` | The page |
