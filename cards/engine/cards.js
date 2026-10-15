// Facts -> cards. Fixed rules only. Every word on a card back is copied from the sheet;
// a card front is a piece of the same sentence with one part hidden, plus a fixed prompt.

import { nameTip, thingFact } from './nametips.js';
import { pickSymbol } from './symbols.js';

const MAX_CLUE_WORDS = 10;
export const GENERIC_SYMBOLS = new Set(['people', 'pin', 'calendar', 'globe', 'star']);
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
      symbols: [], // filled in below, once every deck is known
      star: false,
    };
    // Link a hard answer to another fact about the same place that shares a name with it:
    // "Titanic Belfast" museum -> "… shipyard built the RMS Titanic". Both come from the sheet.
    for (const c of body) {
      if (c.kind !== 'cloze') continue;
      const link = linkFor(c, e);
      if (link) c.link = link;
      const fact = thingFact(c.answer);
      if (fact) c.tip = fact;
    }
    const cards = [hook, ...body.map(({ order, score, ...c }) => c), portrait];
    // A name tip goes on backs whose answer is the place name itself, where the child is learning that name.
    const tip = nameTip(e.display);
    if (tip) for (const c of cards) if (c.answer === e.display) c.tip = tip;
    return { entity: e.display, cards };
  });

  // Every card except the final picture gets a small hint: the answer's shape, first letters only.
  for (const d of decks) for (const c of d.cards) if (c.kind !== 'portrait') c.hint = letterHint(c.answer);

  // Prefer pictures the other places on the sheet don't have: four capitals all have a crown,
  // but only Belfast has the ship. Shared pictures fill in only when nothing distinctive is left.
  const decksWith = new Map();
  for (const d of decks) {
    for (const sym of new Set(d.cards.map((c) => c.symbol).filter(Boolean))) {
      decksWith.set(sym, (decksWith.get(sym) || 0) + 1);
    }
  }
  for (const d of decks) {
    const portrait = d.cards[d.cards.length - 1];
    const candidates = [];
    for (const c of d.cards) {
      if (c.symbol && !GENERIC_SYMBOLS.has(c.symbol) && !candidates.includes(c.symbol)) candidates.push(c.symbol);
    }
    portrait.symbols = candidates
      .map((sym, i) => ({ sym, i, shared: decksWith.get(sym) }))
      .sort((a, b) => a.shared - b.shared || a.i - b.i)
      .slice(0, 4)
      .sort((a, b) => a.i - b.i)
      .map((x) => x.sym);
  }

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

const SMALL_WORDS = new Set(['of', 'and', 'the', 'in', 'on', 'for', 'a', 'an', '&']);

/**
 * The answer's shape with only first letters showing: "River Lagan" -> "R____ L____", "286,000" -> "2__,___".
 * Small joining words stay ("H______ and W____"); punctuation and spaces stay. Null when a hint would give it away.
 */
export function letterHint(answer) {
  const text = String(answer).trim();
  if (text.replace(/[^A-Za-z0-9]/g, '').length < 3) return null;
  let firstOfNumber = true;
  const hint = text
    .split(' ')
    .map((word) => {
      if (SMALL_WORDS.has(word.toLowerCase())) return word;
      let shown = false;
      return [...word]
        .map((ch) => {
          if (!/[A-Za-z0-9]/.test(ch)) {
            if (ch === '-') shown = false; // "eleventh-largest" -> "e_______-l______"
            return ch;
          }
          if (/[0-9]/.test(ch)) {
            if (firstOfNumber) {
              firstOfNumber = false;
              return ch;
            }
            return '_';
          }
          if (!shown) {
            shown = true;
            return ch;
          }
          return '_';
        })
        .join('');
    })
    .join(' ');
  return hint === text ? null : hint;
}

const LINK_WORDS = 5;

/** A few words from another fact about the same place that mention a name inside this card's answer. */
export function linkFor(card, entity) {
  // Words in the place's own heading ("Northern Ireland", "Scotland") are on every card about it: no link.
  const heading = `${entity.display} ${entity.descriptor}`.toLowerCase();
  const names = (card.answer.match(/\b[A-Z][a-zA-Z’'-]{3,}\b/g) || []).filter((w) => !heading.includes(w.toLowerCase()));
  for (const name of names) {
    for (const f of entity.facts) {
      if (f.id === card.id || f.text.includes(card.answer)) continue;
      const words = f.text.split(' ');
      const at = words.findIndex((w) => w.replace(/[^A-Za-z’'-]/g, '') === name);
      if (at === -1) continue;
      // The word must end a name there ("RMS Titanic"), not start one ("Bank of Scotland"): a cut name confuses.
      const nextWord = words[at + 1] || '';
      if (/^(of|and|&)$/i.test(nextWord) || (/^[A-Z]/.test(nextWord) && !/[,;:.)–—]$/.test(words[at]))) continue;
      const piece = words
        .slice(Math.max(0, at - (LINK_WORDS - 1)), at + 1)
        .join(' ')
        .replace(/[,;:.]+$/, '');
      return (at >= LINK_WORDS ? '… ' : '') + piece;
    }
  }
  return null;
}
