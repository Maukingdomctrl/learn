// Tests use the synthetic sample sheet and hand-made line data. No network, no AI.
// Passing tests show the rules behave as designed, not that the cards teach well; only children can tell us that.

import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import * as pdfjs from 'pdfjs-dist/legacy/build/pdf.mjs';

import { BLANK, GENERIC_SYMBOLS, buildDecks, chooseKey, clozeClue, hideNames, letterHint } from '../engine/cards.js';
import { checkDecks } from '../engine/checks.js';
import { groupLines } from '../engine/extract.js';
import { makeDecks } from '../engine/index.js';
import { backHtml, esc, frontHtml } from '../engine/render.js';
import { dropRunningHeaders, parseSheet, splitFacts } from '../engine/structure.js';
import { nameTip, thingFact } from '../engine/nametips.js';
import { ART, pickSymbol, portraitSvg, svg } from '../engine/symbols.js';

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const FONTS = here('../node_modules/pdfjs-dist/standard_fonts/');

async function sample() {
  const data = new Uint8Array(readFileSync(here('../sample/sample-sheet.pdf')));
  return makeDecks(pdfjs, data, { standardFontDataUrl: FONTS });
}

/** Builds Line objects like extract.js does. Text inside **stars** is emphasised. */
function lines(rows) {
  return rows.map(([page, text, size = 9.5]) => {
    const segments = text
      .split(/(\*\*.+?\*\*)/)
      .filter(Boolean)
      .map((t) => (t.startsWith('**') ? { text: t.slice(2, -2), emph: true } : { text: t, emph: false }));
    return { page, y: 0, size, segments, text: segments.map((s) => s.text).join('') };
  });
}

const CITY_ROWS = [
  [1, 'IMPORTANT CITIES OF THE UNITED KINGDOM', 18],
  [1, '1. BELFAST – Capital of Northern Ireland', 12],
  [1, '• Situated on the **River Lagan**; population about **286,000** (2011 census).'],
  [1, '• Key role in the Industrial Revolution.'],
  [1, '2. BIRMINGHAM – West Midlands, England', 12],
  [1, '• At the heart of the **Industrial Revolution**.'],
  [1, '• Grew to international prominence in the 18th century.'],
  [1, '3. PRACTICE QUESTIONS', 13],
  [1, '1. Which river flows through Belfast?'],
];

// ---------- the sample sheet, end to end ----------

test('sample sheet: two decks, every fact on a card, all checks pass', async () => {
  const { sheet, built, check } = await sample();
  assert.deepEqual(
    built.decks.map((d) => d.entity),
    ['Belfast', 'Edinburgh', 'All cities'],
  );
  assert.equal(check.ok, true, check.problems.join('\n'));
  for (const e of sheet.entities) {
    const ids = built.decks.find((d) => d.entity === e.display).cards.map((c) => c.id);
    for (const f of e.facts) assert.ok(ids.includes(f.id), `no card for ${f.id}`);
  }
});

test('sample sheet: bold words become the hidden answers, word for word', async () => {
  const { built } = await sample();
  const belfast = built.decks[0].cards;
  const answers = belfast.filter((c) => c.kind === 'cloze').map((c) => c.answer);
  assert.ok(answers.includes('River Lagan'));
  assert.ok(answers.includes('286,000'));
  assert.ok(answers.includes('Harland and Wolff'));
  const lagan = belfast.find((c) => c.answer === 'River Lagan');
  assert.equal(lagan.exact, 'Situated on the River Lagan');
  assert.equal(lagan.clue, `Situated on the ${BLANK}`);
});

test('sample sheet: deck starts with the heading riddle and ends with the portrait', async () => {
  const { built, sheet } = await sample();
  const cards = built.decks[0].cards;
  assert.equal(cards[0].kind, 'hook');
  assert.equal(cards[0].clue, 'Capital of Northern Ireland');
  assert.equal(cards[0].ask, 'Which city?');
  const last = cards[cards.length - 1];
  assert.equal(last.kind, 'portrait');
  assert.equal(last.exact, sheet.summaries.get('Belfast'));
  assert.ok(last.symbols.length >= 2 && last.symbols.length <= 4);
});

test('wrapped bullet lines join into one fact', async () => {
  const { sheet } = await sample();
  const edinburgh = sheet.entities.find((e) => e.display === 'Edinburgh');
  assert.ok(edinburgh.facts.some((f) => f.text.endsWith('cobbled wynds and Georgian-era buildings.')));
});

test('running headers and page numbers are dropped', async () => {
  const { sheet } = await sample();
  assert.ok(!sheet.text.includes('Page 1'));
  assert.ok(!sheet.other.some((t) => t.startsWith('Grade 8 Social Studies | Sample sheet')));
});

// ---------- structure ----------

test('headings, bullets, summaries and other lines are told apart', () => {
  const sheet = parseSheet(
    lines([...CITY_ROWS, [2, '• Belfast = Shipbuilding & Titanic'], [2, 'MEMORY TIP: ships and money']]),
  );
  assert.equal(sheet.kindWord, 'city');
  assert.deepEqual(
    sheet.entities.map((e) => [e.display, e.descriptor]),
    [
      ['Belfast', 'Capital of Northern Ireland'],
      ['Birmingham', 'West Midlands, England'],
    ],
  );
  assert.equal(sheet.summaries.get('Belfast'), 'Belfast = Shipbuilding & Titanic');
  assert.ok(sheet.other.includes('3. PRACTICE QUESTIONS'));
  assert.ok(sheet.other.includes('1. Which river flows through Belfast?'));
  assert.ok(sheet.other.includes('MEMORY TIP: ships and money'));
});

test('a bullet with ";" becomes separate facts that keep their bold words', () => {
  const [line] = lines([[1, 'Situated on the **River Lagan**; population about **286,000** (2011 census).']]);
  const facts = splitFacts({ page: 1, segments: line.segments }, 'Belfast', 'belfast-1');
  assert.deepEqual(
    facts.map((f) => [f.id, f.text, f.keys]),
    [
      ['belfast-1a', 'Situated on the River Lagan', ['River Lagan']],
      ['belfast-1b', 'population about 286,000 (2011 census).', ['286,000']],
    ],
  );
});

test('lines on every page are treated as headers, single-page text is kept', () => {
  const rows = lines([
    [1, 'Grade 8 | Notes'],
    [1, 'Page 1'],
    [1, 'Real text'],
    [2, 'Grade 8 | Notes'],
    [2, 'Page 2'],
  ]);
  assert.deepEqual(
    dropRunningHeaders(rows).map((l) => l.text),
    ['Real text'],
  );
});

test('extraction marks a second font at body size as emphasis, not headings', () => {
  const item = (x, text, font, size = 9.5, y = 100) => ({ page: 1, x, y, size, width: text.length * 4, text, font });
  const out = groupLines([
    item(10, 'A big heading', 'B', 14, 200),
    item(10, 'Situated on the', 'R'),
    item(80, 'River Lagan', 'B'),
    item(130, 'in town and more body text here', 'R'),
  ]);
  assert.equal(out[0].text, 'A big heading');
  assert.equal(out[0].segments[0].emph, false);
  assert.deepEqual(
    out[1].segments.map((s) => s.emph),
    [false, true, false],
  );
  assert.equal(out[1].text, 'Situated on the River Lagan in town and more body text here');
});

// ---------- cards ----------

test('bold words win; without bold only a date or number is hidden; otherwise no key', () => {
  const lower = 'the industrial revolution industrial revolution';
  assert.equal(chooseKey({ text: 'At the heart of the Industrial Revolution', keys: ['Industrial Revolution'] }, 'X', lower), 'Industrial Revolution');
  assert.equal(chooseKey({ text: 'Made a city in 1905', keys: [] }, 'X', lower), '1905');
  assert.equal(chooseKey({ text: 'Grew in the 18th century', keys: [] }, 'X', lower), '18th century');
  assert.equal(chooseKey({ text: 'Key role in the Industrial Revolution', keys: [] }, 'X', lower), null);
});

test('cloze clue keeps the clause, skips brackets and stays short', () => {
  assert.equal(
    clozeClue('The industrial steam engine (one of the most important inventions) was invented here.', 'industrial steam engine'),
    `The ${BLANK} … was invented here`,
  );
  const long = 'Centre for industry, arts, higher education, business and law – the economic engine of Northern Ireland.';
  const clue = clozeClue(long, 'economic engine of Northern Ireland');
  assert.ok(clue.endsWith(BLANK), clue);
  assert.ok(clue.split(' ').length <= 11, clue);
  assert.ok(clue.includes('law – the'), 'borrowed words keep their punctuation');
});

test('"which city?" clues never show a city name', () => {
  assert.equal(hideNames('Cardiff handled more than London', ['London', 'Cardiff']), `${BLANK} handled more than ${BLANK}`);
  const sheet = parseSheet(lines(CITY_ROWS));
  const built = buildDecks(sheet);
  for (const c of built.decks.flatMap((d) => d.cards)) {
    if (c.kind === 'who' || c.kind === 'hook') for (const d of built.decks) assert.ok(!c.clue.includes(d.entity), c.clue);
  }
});

test('a riddle the sheet also links to another place says so on the back', () => {
  const sheet = parseSheet(lines(CITY_ROWS));
  const built = buildDecks(sheet);
  const check = checkDecks(sheet, built);
  const card = built.decks[0].cards.find((c) => c.clue.startsWith('Key role in the Industrial Revolution'));
  assert.equal(card.kind, 'who');
  assert.deepEqual(card.alsoTrue, ['Birmingham']);
  assert.match(backHtml(card), /Also linked: Birmingham/);
  assert.ok(check.ok);
});

// ---------- checks: each one passes on good decks and catches a targeted mutation ----------

function cityDecks() {
  const sheet = parseSheet(lines(CITY_ROWS));
  return { sheet, built: buildDecks(sheet) };
}

test('check passes on untouched decks', () => {
  const { sheet, built } = cityDecks();
  const check = checkDecks(sheet, built);
  assert.equal(check.ok, true, check.problems.join('\n'));
});

test('check fails when a card back is not word-for-word from the sheet', () => {
  const { sheet, built } = cityDecks();
  built.decks[0].cards[1].exact = 'Situated on the River Thames';
  const check = checkDecks(sheet, built);
  assert.equal(check.ok, false);
  assert.match(check.problems.join('\n'), /not word-for-word/);
});

test('check fails when a clue adds words that are not in the sheet', () => {
  const { sheet, built } = cityDecks();
  const card = built.decks[0].cards.find((c) => c.kind === 'cloze');
  card.clue = `A lovely river called the ${BLANK}`;
  assert.match(checkDecks(sheet, built).problems.join('\n'), /clue text not found/);
});

test('check fails when a riddle gives the answer away', () => {
  const { sheet, built } = cityDecks();
  built.decks[0].cards[0].clue = 'Belfast is the capital of Northern Ireland';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /gives the answer away/);
});

test('check fails when a fact has no card', () => {
  const { sheet, built } = cityDecks();
  built.decks[1].cards = built.decks[1].cards.filter((c) => c.kind !== 'cloze');
  assert.match(checkDecks(sheet, built).problems.join('\n'), /no card for/);
});

test('check fails when the hidden answer is not in its sentence', () => {
  const { sheet, built } = cityDecks();
  built.decks[0].cards.find((c) => c.kind === 'cloze').answer = 'River Thames';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /is not in its sentence/);
});

test('a sheet without headed bullet lists is not printable', () => {
  const sheet = parseSheet(lines([[1, 'Just a title', 18], [1, 'Some plain paragraph text.']]));
  const check = checkDecks(sheet, buildDecks(sheet));
  assert.equal(check.ok, false);
  assert.match(check.problems[0], /No topics found/);
});

// ---------- pictures ----------

test('pictures follow the words; nothing fitting means no picture', () => {
  assert.equal(pickSymbol('Situated on the River Lagan'), 'river');
  assert.equal(pickSymbol('Harland and Wolff shipyard built the RMS Titanic'), 'ship');
  assert.equal(pickSymbol('Made a city in 1905', '1905'), 'calendar');
  assert.equal(pickSymbol('centre for white-collar professions'), null);
  assert.match(svg(null), /draw it!/);
});

test('pictures are deterministic and every library drawing renders', () => {
  for (const name of Object.keys(ART)) {
    const a = svg(name);
    assert.equal(a, svg(name), name);
    assert.ok(a.startsWith('<svg') && a.endsWith('</svg>'), name);
    assert.ok(!a.includes('NaN') && !a.includes('undefined'), name);
  }
  assert.equal(portraitSvg(['ship', 'river', 'crown']), portraitSvg(['ship', 'river', 'crown']));
});

// ---------- rendering ----------

test('sheet text is escaped before it reaches the page', () => {
  assert.equal(esc('<img src=x onerror=alert(1)>'), '&lt;img src=x onerror=alert(1)&gt;');
  const card = {
    kind: 'cloze',
    entity: '<b>X</b>',
    clue: `<script>bad()</script> ${BLANK}`,
    ask: '',
    answer: '<i>a</i>',
    exact: '<i>a</i>',
    page: 1,
    symbol: null,
    star: false,
  };
  const html = frontHtml(card) + backHtml(card);
  assert.ok(!html.includes('<script>') && !html.includes('<i>') && !html.includes('<b>X'));
  assert.match(frontHtml(card), /class="blank"/);
});

// ---------- name tips ----------

test('name tips go only on backs whose answer is the place name, never on fronts', () => {
  const { built } = cityDecks();
  const birmingham = built.decks.find((d) => d.entity === 'Birmingham').cards;
  const withTip = birmingham.filter((c) => c.tip);
  assert.ok(withTip.length >= 2, 'hook and portrait carry the tip');
  for (const c of withTip) assert.equal(c.answer, 'Birmingham');
  for (const c of birmingham.filter((c) => c.kind === 'cloze')) assert.equal(c.tip, undefined);
  const card = withTip[0];
  assert.match(backHtml(card), /Fun fact/);
  assert.doesNotMatch(frontHtml(card), /home/);
});

test('name tips come only from the checked list, never from a rule on the ending', () => {
  assert.match(nameTip('Birmingham'), /home/);
  assert.equal(nameTip('Durham'), null);
  assert.equal(nameTip('Oldham'), null);
  assert.equal(nameTip('London'), null);
});

test('a name tip is not part of the exact-words check and does not break it', () => {
  const { sheet, built } = cityDecks();
  const check = checkDecks(sheet, built);
  assert.equal(check.ok, true, check.problems.join('\n'));
});

test('the final picture card never uses pictures that fit every place (crowd, pin, calendar…)', async () => {
  const { built } = await sample();
  for (const d of built.decks) {
    const portrait = d.cards[d.cards.length - 1];
    for (const sym of portrait.symbols) assert.ok(!GENERIC_SYMBOLS.has(sym), `${d.entity}: ${sym}`);
  }
  const belfast = built.decks.find((d) => d.entity === 'Belfast').cards;
  assert.equal(belfast.find((c) => c.answer === '286,000').symbol, 'people', 'the population card itself keeps its crowd');
});

test('the final picture card prefers pictures the other places do not share', () => {
  const sheet = parseSheet(
    lines([
      [1, 'IMPORTANT CITIES', 18],
      [1, '1. ALPHA – Capital of the North', 12],
      [1, '• Famous for **shipbuilding**.'],
      [1, '2. BETA – Capital of the South', 12],
      [1, '• Famous for **coal** mining.'],
    ]),
  );
  const built = buildDecks(sheet);
  const alpha = built.decks[0].cards.at(-1);
  assert.equal(alpha.symbols[0], 'crown', 'shared pictures may still appear, in deck order');
  assert.ok(alpha.symbols.includes('ship'));
  assert.ok(!alpha.symbols.includes('coal'));
});

// ---------- hints ----------

test('hints show only first letters and the answer shape', () => {
  assert.equal(letterHint('River Lagan'), 'R____ L____');
  assert.equal(letterHint('Harland and Wolff'), 'H______ and W____');
  assert.equal(letterHint('286,000'), '2__,___');
  assert.equal(letterHint('eleventh-largest'), 'e_______-l______');
  assert.equal(letterHint('UK'), null, 'too short: a hint would give it away');
});

test('every card but the final picture carries a hint on its front', async () => {
  const { built } = await sample();
  for (const d of built.decks) {
    for (const c of d.cards) {
      if (c.kind === 'portrait' || c.kind === 'compare') assert.equal(c.hint, undefined);
      else {
        assert.ok(c.hint, c.id);
        assert.match(frontHtml(c), /Hint:/);
      }
    }
  }
});

test('check fails when a hint does not match its answer', () => {
  const { sheet, built } = cityDecks();
  built.decks[0].cards.find((c) => c.answer === 'River Lagan').hint = 'R____ T_____';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /does not match/);
});

// ---------- links and thing fun facts ----------

test('the museum card links to the Titanic fact on the same sheet and gets the iceberg fun fact', async () => {
  const { built, check } = await sample();
  assert.ok(check.ok, check.problems.join('\n'));
  const museum = built.decks[0].cards.find((c) => c.answer === 'Titanic Belfast');
  assert.equal(museum.link, '… shipyard built the RMS Titanic');
  assert.match(frontHtml(museum), /Think: … shipyard built the RMS Titanic/);
  assert.match(museum.tip, /iceberg/);
  assert.doesNotMatch(frontHtml(museum), /iceberg/);
});

test('thing fun facts match whole words only', () => {
  assert.match(thingFact('RMS Titanic'), /iceberg/);
  assert.equal(thingFact('Titanica'), null);
  assert.equal(thingFact('River Lagan'), null);
});

test('check fails when a link is not from the sheet or gives the answer away', () => {
  const { sheet, built } = cityDecks();
  const card = built.decks[0].cards.find((c) => c.kind === 'cloze');
  card.link = 'a famous ship that sank';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /link text not found/);
  card.link = `Situated on the ${card.answer}`;
  assert.match(checkDecks(sheet, built).problems.join('\n'), /link gives the answer away/);
});

// ---------- comparison card ----------

test('a "who did what?" card lists every place\'s job in the sheet\'s own words', async () => {
  const { built, check } = await sample();
  assert.ok(check.ok, check.problems.join('\n'));
  const last = built.decks.at(-1);
  assert.equal(last.entity, 'All cities');
  const [card] = last.cards;
  assert.equal(card.kind, 'compare');
  assert.deepEqual(card.lines, ['Belfast = Shipbuilding & Titanic', 'Edinburgh = Banking Capital of Scotland']);
  assert.match(backHtml(card), /Banking Capital of Scotland/);
});

test('check fails when a job line is not from the sheet', async () => {
  const { sheet, built } = await sample();
  built.decks.at(-1).cards[0].lines[0] = 'Belfast = Biggest city in the world';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /not word-for-word/);
});

// ---------- events (history sample) ----------

async function history() {
  const data = new Uint8Array(readFileSync(here('../sample/history-sheet.pdf')));
  return makeDecks(pdfjs, data, { standardFontDataUrl: FONTS });
}

test('history sample: numbered sections become topics with their labels; all checks pass', async () => {
  const { sheet, built, check } = await history();
  assert.equal(check.ok, true, check.problems.join('\n'));
  assert.deepEqual(
    sheet.entities.map((e) => [e.display, e.type, e.label]),
    [
      ['Causes of the Uprising', 'aspect', 'cause'],
      ['Course of the Uprising', 'aspect', 'course'],
      ['Leaders and Centres', 'aspect', 'people'],
      ['Results of the Uprising', 'aspect', 'result'],
    ],
  );
  for (const e of sheet.entities) {
    const ids = built.decks.find((d) => d.entity === e.display).cards.map((c) => c.id);
    for (const f of e.facts) assert.ok(ids.includes(f.id), `no card for ${f.id}`);
  }
});

test('cause and result cards ask why and what changed', async () => {
  const { built } = await history();
  const lapse = built.decks[0].cards.find((c) => c.answer === 'Doctrine of Lapse');
  assert.equal(lapse.ask, 'Why did it happen?');
  const crown = built.decks[3].cards.find((c) => c.answer === 'British Crown');
  assert.equal(crown.ask, 'What changed after?');
});

test('a sentence with "because" or "led to" becomes a why card hiding its own reason or outcome', async () => {
  const { built } = await history();
  const results = built.decks[3].cards;
  const army = results.find((c) => c.kind === 'why' && c.ask === 'Why?');
  assert.equal(army.clue, `The army was reorganised because ${BLANK}`);
  assert.equal(army.answer, 'the British wanted to prevent another revolt');
  const mughal = results.find((c) => c.kind === 'why' && c.ask === 'What happened next?');
  assert.equal(mughal.answer, 'the end of the Mughal dynasty');
  assert.equal(results.filter((c) => c.exact.startsWith('The army was reorganised')).length, 1, 'no duplicate card');
});

test('dated facts give a timeline: scrambled without dates on the front, in date order on the back', async () => {
  const { built } = await history();
  const t = built.decks[1].cards.find((c) => c.kind === 'timeline');
  assert.ok(t.frontLines.every((l) => l.includes(BLANK)));
  assert.deepEqual(
    t.lines.map((l) => l.match(/\d{1,2} \w+ 1857|September 1857/)[0]),
    ['29 March 1857', '10 May 1857', 'September 1857'],
  );
  assert.match(frontHtml(t), /class="lines"/);
});

test('pairs of bold names give a match card; leader cards hide the leader', async () => {
  const { built } = await history();
  const leaders = built.decks[2].cards;
  const m = leaders.find((c) => c.kind === 'match');
  assert.equal(m.frontLines[0], 'Rani Lakshmibai · Nana Saheb · Begum Hazrat Mahal · Kunwar Singh');
  assert.equal(m.frontLines[1], 'Bihar · Jhansi · Kanpur · Lucknow');
  assert.ok(m.lines.includes('Nana Saheb led the revolt at Kanpur'));
  assert.equal(leaders[0].answer, 'Rani Lakshmibai');
});

test('"name them all" lists each fact\'s first bold name, for exam-style "state four causes"', async () => {
  const { built } = await history();
  const list = built.decks[0].cards.at(-1);
  assert.equal(list.kind, 'list');
  assert.deepEqual(list.lines, ['Doctrine of Lapse', 'land revenue', 'paid less', 'Enfield rifle']);
  assert.equal(list.ask, 'How many can you name? (4)');
});

test('check fails when a timeline line is not from the sheet', async () => {
  const { sheet, built } = await history();
  built.decks[1].cards.find((c) => c.kind === 'timeline').lines[0] = 'On 1 April 1857, the rebels took Agra.';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /not word-for-word/);
});

test('check fails when a match card front adds a name that is not on the sheet', async () => {
  const { sheet, built } = await history();
  built.decks[2].cards.find((c) => c.kind === 'match').frontLines[0] += ' · Tantia Tope';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /card front is not from the sheet: "Tantia Tope"/);
});

test('check fails when a why card answer is not in its sentence', async () => {
  const { sheet, built } = await history();
  built.decks[3].cards.find((c) => c.kind === 'why').answer = 'the British were afraid';
  assert.match(checkDecks(sheet, built).problems.join('\n'), /is not in its sentence/);
});

test('history sketches: revolt, acts, rifles and leaders get their own pictures', () => {
  assert.equal(pickSymbol('the cartridges of the new Enfield rifle were rumoured to be greased', 'Enfield rifle'), 'rifle');
  assert.equal(pickSymbol("Queen Victoria's Proclamation of 1858", "Queen Victoria's Proclamation"), 'scroll');
  assert.equal(pickSymbol('Nana Saheb led the revolt at Kanpur', 'Nana Saheb'), 'person');
  assert.equal(pickSymbol('sepoys at Meerut rose in revolt', 'Meerut'), 'sword');
  assert.equal(pickSymbol('At the heart of the Industrial Revolution', 'Industrial Revolution'), 'factory');
});
