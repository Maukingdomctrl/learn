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

const FONT = `font-family="'Patrick Hand', cursive" fill="currentColor" stroke="none"`;

/** A time line with one bar per life and a dot for each dated fact. Drawn from the sheet's years only. */
export function lifelineSvg(rows) {
  const start = Math.floor(Math.min(...rows.map((r) => r.born)) / 10) * 10;
  const end = Math.ceil(Math.max(...rows.map((r) => r.died)) / 10) * 10;
  const x = (year) => (12 + ((year - start) / Math.max(1, end - start)) * 146).toFixed(1);
  const step = [10, 20, 25, 50, 100].find((s) => (end - start) / s <= 7) || 100;
  const rowH = Math.min(24, 74 / rows.length);
  let out = `<path d="M12 94 H158" stroke-width="1.4"/>`;
  for (let t = Math.ceil(start / step) * step; t <= end; t += step) {
    out += `<path d="M${x(t)} 92 V96" stroke-width="1.2"/><text x="${x(t)}" y="104" text-anchor="middle" font-size="6.5" ${FONT}>${t}</text>`;
  }
  rows.forEach((r, i) => {
    const y = 14 + i * rowH + rowH / 2;
    out += `<text x="${x(r.born)}" y="${(y - 6).toFixed(1)}" font-size="7" ${FONT}>${esc(r.name)}</text>`;
    out += `<rect x="${x(r.born)}" y="${(y - 3).toFixed(1)}" width="${(x(r.died) - x(r.born)).toFixed(1)}" height="6" rx="3" fill="#fbfaf7" stroke-width="1.3"/>`;
    for (const ev of r.events) out += `<circle cx="${x(ev)}" cy="${y.toFixed(1)}" r="2" fill="currentColor" stroke="none"/>`;
  });
  return `<svg viewBox="0 0 170 110" fill="none" stroke="currentColor" stroke-linecap="round" aria-hidden="true">${out}</svg>`;
}

const FROM_MEMORY = `<svg viewBox="0 0 170 110" aria-hidden="true"><text x="85" y="72" text-anchor="middle" font-size="64" ${FONT}>?</text><text x="85" y="98" text-anchor="middle" font-size="10" ${FONT}>from memory</text></svg>`;

export function frontHtml(card) {
  const photo = typeof card.photoUrl === 'string' && card.photoUrl.startsWith('data:image/') ? card.photoUrl : null;
  const picture = photo
    ? `<img class="photo" src="${esc(photo)}" alt="">`
    : card.kind === 'lifeline'
      ? lifelineSvg(card.lifeline)
      : card.kind === 'again'
        ? FROM_MEMORY
        : ['portrait', 'compare', 'list'].includes(card.kind)
          ? portraitSvg(card.symbols)
          : svg(card.symbol);
  // A fill-in clue names its place, so it still makes sense when decks are mixed.
  const tag = card.kind === 'cloze' ? card.entity : '';
  return `${tag ? `<span class="tag">${esc(tag)}</span>` : ''}${card.star ? '<span class="star" title="The sheet repeats this">★</span>' : ''}
    <div class="pic">${card.frontLines ? `<ul class="lines">${card.frontLines.map((l) => `<li>${clueHtml(l)}</li>`).join('')}</ul>` : picture}</div>
    <div class="clue">${card.clue ? `<span>${clueHtml(card.clue)}</span>` : ''}${card.ask ? `<b>${esc(card.ask)}</b>` : ''}${
      card.link ? `<small class="link">Think: ${esc(card.link)}</small>` : ''
    }${card.hint ? `<small class="hint">Hint: ${esc(card.hint)}</small>` : ''
    }</div>`;
}

export function backHtml(card) {
  const also = card.alsoTrue?.length ? `<div class="also">Also linked: ${esc(card.alsoTrue.join(', '))}</div>` : '';
  if (card.lines) {
    return `<ul class="lines">${card.lines.map((l) => `<li>${esc(l)}</li>`).join('')}</ul>
    <span class="src">${esc(card.entity)} · p.${esc(card.page)}</span>`;
  }
  const exact = card.exact === card.answer ? '' : `<div class="exact">${esc(card.exact)}</div>`;
  const tip = card.tip ? `<div class="tip"><b>Fun fact</b> ${esc(card.tip)}</div>` : '';
  const long = card.answer.split(' ').length > 5 ? ' long' : '';
  const sum = card.sum ? `<div class="exact">${card.sum.year} − ${card.sum.born} = ${card.sum.year - card.sum.born}</div>` : '';
  const identity = card.identity ? `<div class="identity">Remember: ${esc(card.identity)}</div>` : '';
  return `<div class="answer${long}">${esc(card.answer)}</div>${sum}${exact}${also}${tip}${identity}
    <span class="src">${esc(card.entity)} · p.${esc(card.page)}</span>`;
}
