// Cards for topics that are not places: causes, results, a course of events, people.
// Same rule as everywhere: every word on a card comes from the sheet, plus fixed prompts.

import { BLANK } from './cards.js';

const MAX_WORDS = 14;

/** What a cause or result card asks, by the label the sheet gave its section or bullet. */
export const ASK_BY_LABEL = {
  cause: 'Why did it happen?',
  result: 'What changed after?',
};

const BECAUSE = /\s(because|due to|as a result of)\s/;
const LED_TO = /\s(led to|resulted in|so that)\s/;

/**
 * A sentence that holds its own "why": "The army was reorganised because the British wanted…".
 * The reason (or the outcome, for "led to") is hidden; the rest of the sentence is the question.
 */
export function whyCard(fact, entity) {
  const m = fact.text.match(BECAUSE) || fact.text.match(LED_TO);
  if (!m) return null;
  const before = fact.text.slice(0, m.index);
  const answer = fact.text
    .slice(m.index + m[0].length)
    .replace(/[.\s]+$/, '')
    .trim();
  const lead = before.split(' ');
  const shown = lead.length > 8 ? `… ${lead.slice(-8).join(' ')}` : before;
  const isWhy = BECAUSE.test(fact.text);
  return {
    id: fact.id,
    entity,
    kind: 'why',
    clue: `${shown} ${m[1]} ${BLANK}`,
    ask: isWhy ? 'Why?' : 'What happened next?',
    answer,
    exact: fact.text,
    page: fact.page,
  };
}

/** A sentence's opening words, for facts with nothing bold to hide: "Jhansi and Nagpur were …" */
export function recallClue(text) {
  const words = text.replace(/[.\s]+$/, '').split(' ');
  const n = Math.min(5, Math.max(2, Math.ceil(words.length / 2)));
  return `${words.slice(0, n).join(' ')} …`;
}

const MONTHS = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
const DATE = new RegExp(
  `\\b(?:(\\d{1,2})\\s+)?(${MONTHS.join('|')})\\s+(1[0-9]{3}|20[0-9]{2})\\b|\\b(1[0-9]{3}|20[0-9]{2})\\b`,
  'i',
);

/** The first date in a sentence and a number to sort by: "29 March 1857" -> 18570329. */
export function findDate(text) {
  const m = text.match(DATE);
  if (!m) return null;
  if (m[4]) return { text: m[0], sort: Number(m[4]) * 10000 };
  const month = MONTHS.indexOf(m[2].toLowerCase()) + 1;
  return { text: m[0], sort: Number(m[3]) * 10000 + month * 100 + Number(m[1] || 0) };
}

function sentenceWithBlank(text, part) {
  const words = text.replace(part, BLANK).split(' ');
  return words.length > MAX_WORDS ? `${words.slice(0, MAX_WORDS).join(' ')} …` : words.join(' ');
}

/**
 * "Put these in order": three or more dated facts. The front lists them without dates in a fixed scrambled
 * order (alphabetical); the back lists them in date order with the dates back in.
 */
export function timelineCard(facts, entity) {
  const dated = facts
    .map((f, i) => ({ f, i, date: findDate(f.text) }))
    .filter((x) => x.date);
  if (dated.length < 3 || new Set(dated.map((x) => x.date.sort)).size < 2) return null;
  const front = dated.map((x) => sentenceWithBlank(x.f.text, x.date.text)).sort((a, b) => a.localeCompare(b));
  const back = [...dated]
    .sort((a, b) => a.date.sort - b.date.sort || a.i - b.i)
    .map((x) => sentenceWithBlank(x.f.text, x.date.text).replace(BLANK, x.date.text));
  return {
    id: `${slug(entity)}-timeline`,
    entity,
    kind: 'timeline',
    clue: 'Put these in order.',
    ask: 'Which came first?',
    answer: 'In order',
    exact: '',
    frontLines: front,
    lines: back,
    page: dated[0].f.page,
    symbol: 'calendar',
  };
}

/** "Match the pairs": three or more facts that each pair two bold names (a leader and a place). */
export function matchCard(facts, entity) {
  const pairs = facts.filter((f) => f.keys.length === 2).map((f) => ({ f, a: f.keys[0], b: f.keys[1] }));
  if (pairs.length < 3) return null;
  const left = pairs.map((p) => p.a);
  const right = pairs.map((p) => p.b).sort((x, y) => x.localeCompare(y));
  return {
    id: `${slug(entity)}-match`,
    entity,
    kind: 'match',
    clue: 'Match each pair.',
    ask: '',
    answer: 'Pairs',
    exact: '',
    frontLines: [left.join(' · '), right.join(' · ')],
    lines: pairs.map((p) => p.f.text.replace(/[.\s]+$/, '')),
    page: pairs[0].f.page,
    symbol: 'person',
  };
}

/**
 * The last card of a topic: name them all, as an exam asks ("State four causes"). It lists each fact's
 * first bold name; facts with nothing bold are left out. No card when fewer than two names remain.
 */
export function listCard(facts, entity) {
  const items = [...new Set(facts.map((f) => f.keys[0]).filter(Boolean))];
  if (items.length < 2) return null;
  return {
    id: `${slug(entity)}-list`,
    entity,
    kind: 'list',
    clue: `${entity}: name them all.`,
    ask: `How many can you name? (${items.length})`,
    answer: entity,
    exact: '',
    lines: items,
    page: facts[0]?.page || 1,
    symbol: null,
    symbols: [],
  };
}

function slug(s) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}
