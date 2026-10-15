// Card -> HTML. Used by the on-screen deck and the print sheets, so both always show the same card.
// All sheet text is escaped: it comes from an uploaded file.

import { BLANK } from './cards.js';
import { portraitSvg, svg } from './symbols.js';

export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);
}

function clueHtml(clue) {
  return esc(clue).split(esc(BLANK)).join('<span class="blank" aria-label="blank"></span>');
}

export function frontHtml(card) {
  const picture = card.kind === 'portrait' ? portraitSvg(card.symbols) : svg(card.symbol);
  // A fill-in clue names its place, so it still makes sense when decks are mixed.
  const tag = card.kind === 'cloze' ? card.entity : '';
  return `${tag ? `<span class="tag">${esc(tag)}</span>` : ''}${card.star ? '<span class="star" title="The sheet repeats this">★</span>' : ''}
    <div class="pic">${picture}</div>
    <div class="clue">${card.clue ? `<span>${clueHtml(card.clue)}</span>` : ''}${card.ask ? `<b>${esc(card.ask)}</b>` : ''}${
      card.link ? `<small class="link">Think: ${esc(card.link)}</small>` : ''
    }${card.hint ? `<small class="hint">Hint: ${esc(card.hint)}</small>` : ''
    }</div>`;
}

export function backHtml(card) {
  const also = card.alsoTrue?.length ? `<div class="also">Also linked: ${esc(card.alsoTrue.join(', '))}</div>` : '';
  const exact = card.exact === card.answer ? '' : `<div class="exact">${esc(card.exact)}</div>`;
  const tip = card.tip ? `<div class="tip"><b>Fun fact</b> ${esc(card.tip)}</div>` : '';
  return `<div class="answer">${esc(card.answer)}</div>${exact}${also}${tip}
    <span class="src">${esc(card.entity)} · p.${esc(card.page)}</span>`;
}
