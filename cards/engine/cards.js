// Facts -> cards. Fixed rules only. Every word on a card back is copied from the sheet;
// a card front is a piece of the same sentence with one part hidden, plus a fixed prompt.

import { pickSymbol } from './symbols.js';

const MAX_CLUE_WORDS = 10;
export const BLANK = '_____';

/**
 * @returns {{title, kindWord, decks: Deck[]}}
 * Deck = { entity, cards: Card[] }
 * Card = { id, entity, kind: 'hook'|'cloze'|'who'|'portrait', clue, ask, answer, exact, page, symbol, symbols, star }
 */
export function buildDecks(sheet) {
  const lowerText = sheet.text.toLowerCase();
  const names = sheet.entities.map((e) => e.display);
  const who = sheet.kindWord ? `Which ${sheet.kindWord}?` : 'Who am I?';

  const decks = sheet.entities.map((e) => {
    const hook = {
      id: `${slugOf(e.display)}-hook`,
      entity: e.display,
      kind: 'hook',
      clue: hideNames(e.descriptor, names),
      ask: who,
      answer: e.display,
      exact: e.descriptor,
      page: e.page,
      symbol: pickSymbol(e.descriptor),
      star: false,
    };

    const body = e.facts.map((f, i) => {
      const key = chooseKey(f, e.display, lowerText);
      const score = key ? count(lowerText, key.toLowerCase()) : 0;
      const front = key
        ? { kind: 'cloze', clue: clozeClue(f.text, key), ask: '', answer: key }
        : { kind: 'who', clue: shortClue(hideNames(f.text, names)), ask: who, answer: e.display };
      return {
        id: f.id,
        entity: e.display,
        ...front,
        exact: f.text,
        page: f.page,
        symbol: pickSymbol(f.text, key || ''),
        star: score >= 3,
        order: i,
        score,
      };
    });
    // The author's emphasis comes first: most-repeated answers lead, otherwise keep the sheet's order.
    body.sort((a, b) => b.score - a.score || a.order - b.order);

    const symbols = [];
    for (const c of [hook, ...body]) {
      if (c.symbol && !symbols.includes(c.symbol)) symbols.push(c.symbol);
      if (symbols.length === 4) break;
    }
    const portrait = {
      id: `${slugOf(e.display)}-portrait`,
      entity: e.display,
      kind: 'portrait',
      clue: '',
      ask: sheet.kindWord ? `Name the ${sheet.kindWord}!` : 'Name me!',
      answer: e.display,
      exact: sheet.summaries.get(e.display) || e.descriptor,
      page: e.page,
      symbol: null,
      symbols,
      star: false,
    };
    return { entity: e.display, cards: [hook, ...body.map(({ order, score, ...c }) => c), portrait] };
  });

  return { title: sheet.title, kindWord: sheet.kindWord, decks };
}

/**
 * Prefer what the author printed in bold. Without bold, only a date or a number is hidden;
 * otherwise the card becomes a "which place?" riddle instead of guessing which word matters.
 */
export function chooseKey(fact, entity, lowerText) {
  const fromEmphasis = fact.keys
    .filter((k) => fact.text.includes(k) && k.split(' ').length <= 6)
    .sort((a, b) => count(lowerText, b.toLowerCase()) - count(lowerText, a.toLowerCase()));
  if (fromEmphasis.length) return fromEmphasis[0];
  const candidates = [
    ...matchAll(fact.text, /\b\d{1,2}(?:st|nd|rd|th) century\b/g),
    ...matchAll(fact.text, /£?\b\d{1,3}(?:,\d{3})+\b|£\d+(?:\.\d+)?\s?(?:billion|million)/g),
    ...matchAll(fact.text, /\b(?:1[0-9]{3}|20[0-9]{2})\b/g),
  ].filter((k) => k.toLowerCase() !== entity.toLowerCase());
  return candidates[0] || null;
}

/** The clause holding the answer, with the answer blanked; at most ~10 words. Brackets become "…". */
export function clozeClue(fullText, key) {
  const at0 = fullText.indexOf(key);
  const unbracket = (s) => s.replace(/\s*\([^)]*\)\s*/g, ' … ');
  const text = unbracket(fullText.slice(0, at0)) + key + unbracket(fullText.slice(at0 + key.length));
  const at = text.indexOf(key);
  const before = text.slice(0, at);
  const after = text.slice(at + key.length);
  const start = lastBoundary(before);
  const endRel = firstBoundary(after);
  let lw = before
    .slice(Math.max(start, 0))
    .replace(/^[\s,;:–—]+/, '')
    .split(' ')
    .filter(Boolean);
  let rw = after
    .slice(0, endRel === -1 ? after.length : endRel)
    .replace(/[\s,;:.–—]+$/, '')
    .split(' ')
    .filter(Boolean);
  // Too little to go on (e.g. "… the _____"): borrow up to five words from before the boundary, punctuation kept.
  if (lw.length + rw.length < 3 && start > 0) {
    lw = before.split(' ').filter(Boolean).slice(-(lw.length + 5));
  }
  let cutLeft = start > 0 && lw.join(' ') !== before.trim().replace(/^[\s,;:–—]+/, '');
  let cutRight = endRel !== -1 && after.slice(endRel).replace(/[\s.…]+/g, '') !== '';
  while (lw.length + rw.length + 1 > MAX_CLUE_WORDS && (lw.length > 3 || rw.length > 3)) {
    if (lw.length >= rw.length) {
      lw = lw.slice(1);
      cutLeft = true;
    } else {
      rw = rw.slice(0, -1);
      cutRight = true;
    }
  }
  const left = lw.join(' ');
  const right = rw.join(' ');
  const clue = `${cutLeft ? '… ' : ''}${left ? left + ' ' : ''}${BLANK}${right ? ' ' + right : ''}${cutRight ? ' …' : ''}`;
  return clue
    .replace(/(…\s*)+/g, '… ')
    .replace(/\s+/g, ' ')
    .replace(/\s*…\s*$/, ' …')
    .trim();
}

function lastBoundary(s) {
  let best = -1;
  for (const m of s.matchAll(/[;:]|\s[–—]\s|,\s/g)) best = m.index + m[0].length;
  return best;
}

function firstBoundary(s) {
  const m = s.match(/[;:]|\s[–—]\s|,\s(?!and\b)/);
  return m ? m.index : -1;
}

/** A 'which place?' clue must not give the answer away. */
export function hideNames(text, names) {
  let out = text;
  for (const n of names) out = out.replace(new RegExp(`\\b${escapeRe(n)}\\b`, 'gi'), BLANK);
  return out;
}

function shortClue(text) {
  const words = text.replace(/[.\s]+$/, '').split(' ');
  if (words.length <= MAX_CLUE_WORDS) return words.join(' ');
  const firstClause = text.split(/\s[–—]\s|;|:\s|\(/)[0].trim().split(' ');
  if (firstClause.length <= MAX_CLUE_WORDS && firstClause.length >= 3) return firstClause.join(' ') + ' …';
  return words.slice(0, MAX_CLUE_WORDS - 1).join(' ') + ' …';
}

function matchAll(text, re) {
  return [...text.matchAll(re)].map((m) => m[0]);
}

export function count(haystack, needle) {
  if (!needle) return 0;
  let n = 0;
  let i = haystack.indexOf(needle);
  while (i !== -1) {
    n++;
    i = haystack.indexOf(needle, i + needle.length);
  }
  return n;
}

function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function slugOf(s) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}
