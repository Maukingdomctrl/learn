// Checks run on every deck before it can be shown or printed. A failed check blocks printing.

import { BLANK } from './cards.js';

const norm = (s) =>
  s
    .toLowerCase()
    .replace(/[‘’]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/\s+/g, ' ')
    .trim();

/**
 * @returns {{ok: boolean, problems: string[], notes: string[]}}
 * problems block printing; notes are shown to the parent but don't block.
 */
export function checkDecks(sheet, built) {
  const problems = [];
  const notes = [];
  const source = norm(sheet.text.replace(/\n/g, ' '));
  const allCards = built.decks.flatMap((d) => d.cards);

  if (!sheet.entities.length) {
    problems.push(
      'No topics found. The engine needs headings like "1. LONDON – Capital of …" followed by bullet points.',
    );
  }

  // Coverage: every fact on the sheet has its own card.
  for (const e of sheet.entities) {
    if (!e.facts.length) problems.push(`${e.display}: the heading has no bullet points under it.`);
    const deck = built.decks.find((d) => d.entity === e.display);
    for (const f of e.facts) {
      if (!deck || !deck.cards.some((c) => c.id === f.id)) problems.push(`${e.display}: no card for "${f.text}".`);
    }
  }

  for (const c of allCards) {
    // Exactness: the back is the sheet's own words.
    if (!source.includes(norm(c.exact))) problems.push(`${c.entity}: card back is not word-for-word from the sheet: "${c.exact}".`);
    if (c.kind === 'cloze' && !norm(c.exact).includes(norm(c.answer))) {
      problems.push(`${c.entity}: the answer "${c.answer}" is not in its sentence.`);
    }
    // Fronts add nothing: each visible piece of the clue appears in the sheet.
    for (const piece of c.clue.split(new RegExp(`${BLANK}|…`)).map((p) => p.trim())) {
      if (piece && !source.includes(norm(piece))) problems.push(`${c.entity}: clue text not found in the sheet: "${piece}".`);
    }
    // A hint is the answer's own shape: same length, and every letter it shows is the answer's letter there.
    if (c.hint && !hintFits(c.hint, c.answer)) problems.push(`${c.entity}: the hint "${c.hint}" does not match "${c.answer}".`);
    // A 'which place?' clue must not contain the answer.
    if ((c.kind === 'who' || c.kind === 'hook') && norm(c.clue).includes(norm(c.answer))) {
      problems.push(`${c.entity}: the clue gives the answer away: "${c.clue}".`);
    }
  }

  // Mixed decks: a 'which place?' clue that also fits another place must say so.
  // "Fits" means the same clue, or a name in the clue (e.g. "Industrial Revolution") that the sheet also gives another place.
  const whoCards = allCards.filter((c) => c.kind === 'who' || c.kind === 'hook');
  for (const c of whoCards) {
    // Names in the sheet's title (e.g. "United Kingdom") are the whole topic, not a clue to one place.
    const names = namedThings(c.clue).filter((n) => !norm(sheet.title).includes(norm(n)));
    const also = sheet.entities
      .filter((e) => e.display !== c.entity)
      .filter(
        (e) =>
          whoCards.some((o) => o.entity === e.display && norm(o.clue) === norm(c.clue)) ||
          names.some((n) => e.facts.some((f) => norm(f.text).includes(norm(n)))),
      )
      .map((e) => e.display);
    if (also.length) {
      c.alsoTrue = also;
      notes.push(`"${c.clue}": the sheet also links this to ${also.join(' and ')}, so the card back says so.`);
    }
  }

  const untaught = sheet.other.filter((t) => /[a-z]/.test(t)).length;
  if (untaught) {
    notes.push(
      `${untaught} lines (tables, questions, tips) are not on cards yet. This version only makes cards from headed bullet lists.`,
    );
  }
  const noPicture = allCards.filter((c) => c.kind !== 'portrait' && !c.symbol).length;
  if (noPicture) notes.push(`${noPicture} cards have no matching picture, so they show a "draw it!" box.`);

  return { ok: problems.length === 0, problems, notes };
}

/** Names of two or more capitalised words that are not at the start of the clue ("Industrial Revolution"). */
function namedThings(text) {
  const out = [];
  const re = /(?:^|\s)((?:[A-Z][a-zA-Z’'-]+)(?:\s(?:of\s|and\s)?[A-Z][a-zA-Z’'-]+)+)/g;
  for (const m of text.matchAll(re)) {
    const start = m.index + m[0].indexOf(m[1]);
    if (start > 0) out.push(m[1]);
  }
  return out;
}

function hintFits(hint, answer) {
  if (hint.length !== answer.length || hint === answer) return false;
  return [...hint].every((ch, i) => ch === '_' || ch === answer[i]);
}
