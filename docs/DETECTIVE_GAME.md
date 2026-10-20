# Detective game — design (draft for review)

Status: **proposal only.** Nothing here is built yet. Today "Detective" is only a title and colour on the plain study cards (`learn/teaching_engine/cards.py`). This document is for agreeing how the game should work before any code is written.

The game is rule-based and needs no AI. AI may be added later, but the game must work without it.

## Who uses it

- **Parent:** uploads one chapter PDF at a time, as the child reaches it in school. A chapter is usually 5–8 pages; a 300-page book has about 40–50 chapters.
- **Child (Standard 7–8):** plays with the printed cards, a pencil and the chapter itself.
- The site keeps no accounts and stores no uploads. Progress is kept on paper by the parent.

## 1. Case File: what one chapter upload makes

One uploaded chapter becomes one **Case File**: a set of printed cards plus a separate answer sheet for the parent.

**Cards are one-sided.** Nothing is printed on the back. Every card has a header strip naming what kind of card it is:

| Card | What it does |
| :--- | :--- |
| **HOW TO PLAY** | The rules, in a few short lines. One per Case File. |
| **CASE** | The mystery: "Who or what is this?" One per case. |
| **CLUE** | One clue, copied word-for-word from the chapter, with the answer hidden. Three per case, from vague to specific. |
| **SUSPECTS** | 3–4 possible answers: the right one and others of the same kind (people with people, years with years) taken from the same chapter. The child crosses out the ones the clues rule out. |
| **EVIDENCE** | "Find the proof on page N of your chapter. Copy the line that proves it." Sends the child back to the source. |
| **COLD CASE** | "Pull 5 old cards from your Case Box and solve them again." Review of earlier chapters. One per Case File. |

After the cards: a **CASE CLOSED** answer sheet for the parent, giving each answer, the line that proves it and its page.

A chapter gives about 6–10 cases, one per main topic, plus a **Chapter Big Case** that ties them together. Its pieces are unlocked as cases are solved.

**Scoring a case:** solved after 1 clue = 3 stars, after 2 = 2, after 3 = 1. Stars count only once the parent has checked the answer against the CASE CLOSED sheet. This rewards thinking, not speed.

**Rules carried over from the card engine** (see `docs/ENGINE_GUIDE.md`):
- Every clue, suspect and answer is word-for-word from the uploaded chapter. The only added words are fixed card labels and instructions.
- It works for any subject, with no topic-specific rules.
- Cards come first and the answer sheet comes last.
- When a chapter has no clear topics to build cases from, fall back to plain study cards and say so.

## 2. Remembering earlier chapters

The site does not remember past uploads, so review is physical:
- Solved cards go into the child's **Case Box** (any box or envelope).
- The COLD CASE card in each new Case File sends the child back to the box. Cards answered right go to the back, and cards answered wrong come to the front, so they return sooner.
- Re-solving old cards earns stars too.

## 3. Detective Log Sheet

A printable sheet, downloaded once from the home page. It is the only record of progress.

- One row per chapter: chapter name, date, stars earned (out of the number of cases), parent's initials.
- Milestone boxes printed on the sheet. The parent ticks them and hands out the reward.
- A printable page of rank badges to cut out, and a certificate with the child's name written by hand.

## 4. Reward ladder

| Milestone | Reward |
| :--- | :--- |
| Each case solved | 1–3 stars |
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
5. **Rewards page.** Until the quiz exists, freebies sit on a public Rewards page. The parent decides when one has been earned, as with a sticker chart.

## Build order

1. Case File cards and the CASE CLOSED sheet. This is where the learning happens.
2. Log Sheet, badges and certificate.
3. Rewards page with original or openly licensed pictures.
4. Online quiz.
5. Frame and canvas printing (needs the frame and canvas details and a supplier).

Nothing in this design has been tested with children yet.
