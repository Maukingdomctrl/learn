// Facts -> cards. Fixed rules only. Every word on a card back is copied from the sheet;
// a card front is a piece of the same sentence with one part hidden, plus a fixed prompt.

import {
  ageCards,
  ASK_BY_LABEL,
  lifelineCard,
  listCard,
  matchCard,
  PURPOSE_ASK,
  peopleTimelineCard,
  purposeCard,
  purposeOf,
  recallClue,
  timelineCard,
  whyCard,
} from './events.js';
import { nameTip, thingFact } from './nametips.js';
import { pickSymbol } from './symbols.js';

const MAX_CLUE_WORDS = 10;
export const GENERIC_SYMBOLS = new Set(['people', 'pin', 'calendar', 'globe', 'star']);
export const BLANK = '_____';

/**
 * @returns {{title, kindWord, decks: Deck[]}}
 * Deck = { entity, cards: Card[] }
 * Card = { id, entity, kind, clue, ask, answer, exact, page, symbol, symbols, star, hint?, tip?, link?, lines?, frontLines? }
 * kind: places use 'hook' | 'cloze' | 'who' | 'portrait'; other topics use 'cloze' | 'recall' | 'list' | 'timeline' | 'match';
 * either may add 'why' (a sentence's own because/led to) and the sheet-level 'compare'.
 */
export function buildDecks(sheet) {
  const lowerText = sheet.text.toLowerCase();
  const names = sheet.entities.map((e) => e.display);
  const who = sheet.kindWord ? `Which ${sheet.kindWord}?` : 'Who am I?';

  const decks = sheet.entities.map((e) => {
    if (e.type === 'aspect') return topicDeck(e, lowerText);
    const person = e.type === 'person';
    // A riddle about a person must hide every part of their name ("Roy", "Ram Mohan Roy").
    const hidden = person ? [...names, ...nameParts(e.display)] : names;
    const ask = person ? 'Who am I?' : who;
    const hook = {
      id: `${slugOf(e.display)}-hook`,
      entity: e.display,
      kind: 'hook',
      clue: hideNames(e.descriptor, hidden),
      ask,
      answer: e.display,
      exact: e.descriptor,
      page: e.page,
      symbol: pickSymbol(e.descriptor) || (person ? 'person' : null),
      star: false,
    };

    const body = e.facts.map((f, i) => {
      const key = chooseKey(f, e.display, lowerText);
      const score = key ? count(lowerText, key.toLowerCase()) : 0;
      // For people, the question that matters is what problem they took on.
      const purpose = person ? purposeOf(f.text) : null;
      let front;
      if (key) {
        const aboutProblem = purpose && purpose.answer.includes(key);
        front = { kind: 'cloze', clue: clozeClue(f.text, key), ask: aboutProblem ? PURPOSE_ASK : '', answer: key };
      } else if (purpose) {
        front = { ...purposeCard(f, e.display) };
      } else {
        front = { kind: 'who', clue: shortClue(hideNames(f.text, hidden)), ask, answer: e.display };
      }
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
      ask: person ? 'Who am I?' : sheet.kindWord ? `Name the ${sheet.kindWord}!` : 'Name me!',
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
    // because/led to cards, unless the fact's own card already hides the same thing.
    const whys = e.facts
      .map((f) => {
        const c = whyCard(f, e.display);
        const main = body.find((b) => b.id === f.id);
        return c && !(main.answer && c.answer.includes(main.answer)) && main.kind !== 'why' ? c : null;
      })
      .filter(Boolean)
      .map((c) => ({ ...c, id: `${c.id}-why`, symbol: pickSymbol(c.exact), star: false }));
    const facts = body.map(({ order, score, ...c }) => c);
    const extra = [];
    if (person) {
      extra.push(...ageCards(e));
      // Both directions: the work -> who did it, as well as the person -> their work. They come after
      // the ages, so the answer isn't still on screen from the card before.
      for (const c of facts) {
        if (c.kind !== 'cloze') continue;
        const f = e.facts.find((x) => x.id === c.id);
        extra.push({
          id: `${c.id}-who`,
          entity: e.display,
          kind: 'who',
          clue: shortClue(hideNames(f.text, hidden)),
          ask: 'Who am I?',
          answer: e.display,
          exact: f.text,
          page: f.page,
          symbol: c.symbol,
          star: false,
        });
      }
      // Once more from memory: the most repeated answers come back without hint or picture.
      for (const c of [...facts].filter((x) => x.kind === 'cloze').slice(0, 3)) {
        extra.push({ ...c, id: `${c.id}-again`, kind: 'again', symbol: null, star: false });
      }
    }
    const cards = [hook, ...facts, ...whys, ...extra, portrait];
    // The place's or person's one-line summary from the sheet, on the back of every card about them.
    const identity = sheet.summaries.get(e.display);
    if (identity) for (const c of cards) if (c.kind !== 'portrait') c.identity = identity;
    // A name tip goes on backs whose answer is the place name itself, where the child is learning that name.
    const tip = nameTip(e.display);
    if (tip) for (const c of cards) if (c.answer === e.display) c.tip = tip;
    return { entity: e.display, cards };
  });

  // Short answers get a small hint: the answer's shape, first letters only. Long answers (a whole reason)
  // and the final cards get none.
  for (const d of decks) {
    for (const c of d.cards) {
      if (['hook', 'cloze', 'who'].includes(c.kind) && c.answer.split(' ').length <= 5) c.hint = letterHint(c.answer);
    }
  }

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
    if (portrait.kind !== 'portrait' && portrait.kind !== 'list') continue; // timelines and pairs keep their own picture
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

  // "Why this city and not the others?": every place had its own job. The author's summary lines say so,
  // side by side on one card (brackets left out to keep it short; the words stay the sheet's own).
  const jobs = decks
    .filter((d) => sheet.summaries.has(d.entity))
    .map((d) => sheet.summaries.get(d.entity).replace(/\s*\([^)]*\)\s*$/, ''));
  const people = sheet.entities.some((e) => e.type === 'person');
  if (jobs.length >= 2) {
    const group = sheet.kindPlural ? `All ${sheet.kindPlural}` : 'All together';
    const compare = {
      id: 'compare',
      entity: group,
      kind: 'compare',
      clue: people ? `Every ${sheet.kindWord || 'one'} had their own cause.` : `Every ${sheet.kindWord || 'one'} had its own job.`,
      ask: sheet.kindWord ? `Which ${sheet.kindWord} did what?` : 'Who did what?',
      answer: people ? 'Each one’s cause' : 'Each one’s job',
      exact: '',
      lines: jobs,
      page: decks[0].cards[0].page,
      symbol: null,
      symbols: compareSymbols(decks),
      star: false,
    };
    decks.push({ entity: group, cards: [compare], compare: true });
  }
  const lifeline = lifelineCard(sheet.entities);
  if (lifeline) decks.push({ entity: lifeline.entity, cards: [lifeline], compare: true });
  const born = peopleTimelineCard(sheet.entities);
  if (born) decks.push({ entity: born.entity, cards: [born], compare: true });

  return { title: sheet.title, kindWord: sheet.kindWord, decks };
}

/**
 * A topic that is not a place ("Causes of the Uprising"): one card per fact in the sheet's order,
 * then a timeline, a matching card and a "name them all" card where the facts allow it.
 */
function topicDeck(e, lowerText) {
  const body = e.facts.map((f) => {
    // For people, the person is the thing to learn: hide the first bold name ("_____ led the revolt at Kanpur").
    const key = f.label === 'people' && f.keys[0] ? f.keys[0] : chooseKey(f, e.display, lowerText);
    const why = whyCard(f, e.display);
    if (!key && why) return { ...why, symbol: pickSymbol(f.text), star: false };
    const front = key
      ? { kind: 'cloze', clue: clozeClue(f.text, key), ask: ASK_BY_LABEL[f.label] || '', answer: key }
      : { kind: 'recall', clue: recallClue(f.text), ask: 'Finish it.', answer: f.text };
    return {
      id: f.id,
      entity: e.display,
      ...front,
      exact: f.text,
      page: f.page,
      symbol: pickSymbol(f.text, key || ''),
      star: key ? count(lowerText, key.toLowerCase()) >= 3 : false,
    };
  });
  for (const c of body) {
    if (c.kind !== 'cloze') continue;
    const fact = thingFact(c.answer);
    if (fact) c.tip = fact;
  }
  // A fact with both a bold name and a because/led to also gets the "why?" card.
  const whys = e.facts
    .filter((f) => chooseKey(f, e.display, lowerText))
    .map((f) => whyCard(f, e.display))
    .filter(Boolean)
    .map((c) => ({ ...c, id: `${c.id}-why`, symbol: pickSymbol(c.exact), star: false }));
  const timeline = timelineCard(e.facts, e.display);
  const match = matchCard(e.facts, e.display);
  // Course of events ends with its timeline, people with their pairs; other topics with "name them all".
  const last = match || (timeline ? null : listCard(e.facts, e.display));
  return { entity: e.display, cards: [...body, ...whys, ...[timeline, last].filter(Boolean)] };
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

const TITLE_WORDS = new Set(['raja', 'rani', 'swami', 'mahatma', 'sir', 'lord', 'dr', 'begum', 'maharaja', 'maharani', 'sant', 'guru']);

/** The parts of a person's name worth hiding: "Raja Ram Mohan Roy" -> Ram Mohan Roy, Mohan, Roy, Ram… */
export function nameParts(name) {
  const words = name.split(' ').filter((w) => !TITLE_WORDS.has(w.toLowerCase()));
  const out = [];
  for (let i = 0; i < words.length; i++) for (let j = words.length; j > i; j--) out.push(words.slice(i, j).join(' '));
  return out.filter((p) => p.replace(/[^A-Za-z]/g, '').length >= 3).sort((a, b) => b.length - a.length);
}

/** One picture per place or person for the comparison card: the first of theirs that not everyone shares. */
function compareSymbols(decks) {
  const finals = decks.map((d) => d.cards.at(-1).symbols || []);
  const everywhere = (sym) => finals.every((list) => list.includes(sym));
  return finals
    .map((list) => list.find((sym) => !everywhere(sym)) || list[0])
    .filter(Boolean)
    .slice(0, 4);
}
