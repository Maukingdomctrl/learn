# Detective game — design (draft for review)

Status: **step 1 is built, without AI** (`learn/teaching_engine/detective.py`): the Case File cards, the case board and the CASE CLOSED answers, with Rules A and B checked in code. It runs from the command line (`python -m learn.teaching_engine sheet.pdf --case-file case.pdf`). The upload page still prints the older Detective-themed study cards. Everything else in this document is still a proposal.

The game must work without AI. Claude Haiku may write the cards later (see §1.5), but code checks every card, and the rule-based engine is the fallback.

A trial game was played by hand on `UK_Important_Cities_Grade8.pdf` (London and Birmingham) to shape these rules. It has not been tested with children.

## Who uses it

- **Parent:** uploads one chapter PDF at a time, as the child reaches it in school. A chapter is usually 5–8 pages; a 300-page book has about 40–50 chapters.
- **Child (Standard 7–8):** plays with the printed cards, a pencil and the chapter itself.
- The site keeps no accounts and stores no uploads. Progress is kept on paper by the parent.

## 1. Case File: what one chapter upload makes

### 1.1 The mystery

Each case has a hidden culprit (a city, person, process…) chosen from the topics on the sheets. Every topic of the same kind is a **suspect**; the child crosses suspects out as evidence comes in.

### 1.2 Sheets, cards and Big Clues

| Unit | Rule |
| :--- | :--- |
| **Sheet** | One printed card page with **8 cards**. |
| **Card** | One question about the source. The child writes the answer in a blank space on the card. |
| **Sheet mastered** | All 8 cards answered correctly (a second try counts, see §2). Earns ⭐ 1 star and **one Big Clue**. |
| **Big Clue** | A line from the sheet about the culprit, with its name hidden. It rules suspects out using facts from sheets already mastered. |
| **Case closed** | After **2 sheets** (16 cards, 2 Big Clues) the child names the culprit and gives the proof lines. |

The child may accuse early, but the case closes only after both sheets.

**Printing:** cards are one-sided; nothing is printed on the back. Each card has a header strip naming its type. Gaps are blank lines long enough to write in, and the word in front of the gap stays as a hint ("the River ________").

After the cards: a **CASE CLOSED** answer sheet for the parent, giving each answer, the line that proves it and its page.

### 1.3 Rule A: full coverage

Code numbers every line on the sheet's part of the source and checks that each one is tested by at least one card. One card may cover several lines (a MATCH or WHICH-ONE card), so 8 cards can cover 11 or more lines. The trial game used fill-the-gap cards only and missed 3 of 11 lines; a varied set covered all 11.

### 1.4 Rule B: variety and rising difficulty

- At most 2 fill-the-gap cards per sheet, and never the same type twice in a row.
- Cards move from **recognise** (pick or match) to **recall** (write) to **produce** (explain, free recall).
- The last card on a sheet is free recall: "Without looking, write 3 facts about …".

Card types:

| Type | The child… |
| :--- | :--- |
| **MATCH** | draws lines between linked words (city ↔ river ↔ region) |
| **WHICH ONE?** | marks which topic each fact belongs to |
| **TIMELINE** | puts events in order |
| **FILL THE GAP** | writes the hidden word |
| **PICK ONE** | circles the right answer from 3–4 words on the sheet |
| **NUMBER DETECTIVE** | says what a number on the sheet counts |
| **WHO AM I?** | names the topic from 2–3 lines |
| **FINISH IT** | finishes a sentence from the sheet (added because sheets about causes or stages have few names or numbers to ask about) |
| **SPOT THE MISTAKE** | crosses out and fixes one swapped fact *(open question: see below)* |
| **CASE NOTES** | writes 3 facts from memory |

Every clue, choice and answer comes from the sheet. The only added words are fixed card labels and instructions.

**Open question:** SPOT THE MISTAKE puts one topic's fact under another topic's name ("Birmingham is the financial centre of Europe"). Every fact is still from the sheet, but the line is not printed as the sheet prints it. Proposed: allow it, and the answer sheet shows the exact correct line.

### 1.5 Writing the cards with Claude Haiku

- Haiku gets the sheet's lines numbered, the list of card types and worked example cards (the trial game's cards are a good start), and returns the cards as structured data.
- Code checks each card: the hidden answer and clue lines are exact sheet text; wrong choices are other words from the same sheet; Rules A and B hold; each Big Clue rules suspects out using only sheets already mastered.
- A failing card is sent back once with the problems listed, then replaced by the rule-based engine.
- The call goes through `LLM.json`, so tests use the scripted fake. A test set built from real sheets (starting with the UK cities PDF) measures Haiku's cards before children see them.

### 1.6 Other rules

- It works for any subject, with no topic-specific rules.
- Cards come first and the answer sheet comes last.
- When a chapter has no clear topics to build a case from, fall back to plain study cards and say so.

## 2. Remembering earlier chapters

The site does not remember past uploads, so review is physical:
- Solved cards go into the child's **Case Box** (any box or envelope).
- A card answered wrong gets one second try with a stronger hint. Right on the second try still counts, but the card is marked for review.
- A **COLD CASE** card in each new Case File says "Pull 5 old cards from your Case Box and solve them again." Cards answered right go to the back, and cards answered wrong come to the front, so they return sooner.
- Re-solving old cards earns stars too.

## 3. Detective Log Sheet

A printable sheet, downloaded once from the home page. It is the only record of progress.

- One row per chapter: chapter name, date, stars earned (out of the number of cases), parent's initials.
- Milestone boxes printed on the sheet. The parent ticks them and hands out the reward.
- A printable page of rank badges to cut out, and a certificate with the child's name written by hand.

## 4. Reward ladder

| Milestone | Reward |
| :--- | :--- |
| Each sheet mastered | ⭐ 1 star + a Big Clue |
| Each case closed (2 sheets) | Case stamp on the Log Sheet |
| Chapter solved | Chapter badge |
| Every 5 chapters | A freebie (see §5) |
| Every 10 chapters | New rank: Cadet → Detective → Inspector → Chief Inspector |
| Whole book | Detective Commander + certificate |

The first rewards must come quickly. The gaps between rewards widen only once the habit is set.

## 5. Freebies and the online quiz (to be decided)

**Proposal:** a parent uploads a finished Case File, the child takes a short online quiz built from it, and passing unlocks a reward: a downloadable picture, or a print on a custom frame or canvas of the family's choice.

Open points:
1. **Game characters (PUBG, Free Fire, Call of Duty).** These characters belong to Krafton, Garena and Activision. Printing them, and especially selling them on frames, needs a licence from the owner. Without one, the rewards should be original characters, such as our own detective cast drawn in a game style, or openly licensed art. Also, Call of Duty is rated 18+ and PUBG/Free Fire are rated 16+ in many places, and Free Fire is banned in India. A parent-facing product for 12–13-year-olds should not promote them.
2. **Screen time.** The product is screen-free for the child. A quiz of a few minutes, done once per Case File, is a small exception, but it should stay short.
3. **Building the quiz.** The quiz can be built from the Case File's own text, without AI. The site already recognises its own generated PDFs (`cards.py`), so it can tell a Case File from a fresh chapter.
4. **Printed frames.** Selling frames means payments, delivery addresses and a supplier. Checkout must be done by the parent, never the child, and we should store only what delivery needs.
5. **Choosing the print with AI (Claude Haiku).** Haiku writes text, not pictures, so it chooses rather than draws:
   - It picks the artwork from **our own catalogue** of owned or licensed pictures, matched to the chapter and the child's rank. Code rejects any pick that is not in the catalogue, so the AI can never put an unlicensed character on a frame.
   - It writes the personal caption ("Agent Aarav, Chief Inspector, History Book 1") from the details the parent gives. Code checks its length and wording before printing.
   - The parent sees the finished design and approves it before ordering.
   - The call goes through the same model client as the rest of Learn (`LLM.json`), so it can be tested with the scripted fake.
6. **Showcase on the home page.** A "Rewards you can earn" section on the public home page (`site/index.html`) shows a few framed examples, rank badges and posters, so children see the goal before they start. It uses only catalogue art, with the frame and canvas designs supplied by the owner.
7. **Rewards page.** Until the quiz exists, freebies sit on a public Rewards page. The parent decides when one has been earned, as with a sticker chart.

## How the built version decides (step 1)

- **Suspects** are the sheet's topic headings with their points. A sheet needs at least two topics; otherwise the parent is told to use the study cards.
- **Sheet size:** the sheet's lines are cut, in reading order, into card sheets of about 12 lines each, cutting at the start of a topic when one is close. A cut is kept only when its 8 cards cover every line (Rule A).
- **Choosing cards:** each card slot takes the card that tests the most untested lines, less a penalty for each card of its type already on the sheet. A type may appear at most twice, and a second card of a type is only allowed when it can be kept apart from the first.
- **Review:** the second sheet of a case may mix one line from the first sheet into WHICH ONE? and SPOT THE MISTAKE, so earlier facts come back.
- **Culprit:** a topic on the case's last sheet. Each Big Clue is one of its points, with its name hidden, that names no other suspect.
- **Leftover sheet:** when a chapter makes an odd number of sheets, the last case has one sheet and one Big Clue.
- `check_case_file` re-checks everything (8 cards, Rule A, Rule B, words from the sheet, Big Clues) and nothing is printed unless it passes.
- The case board and CASE CLOSED pages print once per case file; the cards print one-sided, 8 to an A4 page.

Of the sample sheets in the repository, 9 of 11 with topics make a case file; a short sheet (7 lines) and one whose topic names overlap ("Phule", "Savitribai Phule") are refused with a message. These are checks of structure only.

## Build order

1. Case File cards and the CASE CLOSED sheet. This is where the learning happens.
2. Log Sheet, badges and certificate.
3. Rewards page with original or openly licensed pictures.
4. Online quiz.
5. Frame and canvas printing (needs the frame and canvas details and a supplier).

Nothing in this design has been tested with children yet.
