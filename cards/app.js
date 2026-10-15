// Page wiring: read the PDF in the browser, build checked decks, play them one card at a time, print them.

import * as pdfjs from 'https://cdn.jsdelivr.net/npm/pdfjs-dist@5.4.624/build/pdf.min.mjs';
import { makeDecks } from './engine/index.js';
import { backHtml, esc, frontHtml } from './engine/render.js';

const PDFJS = 'https://cdn.jsdelivr.net/npm/pdfjs-dist@5.4.624/';
pdfjs.GlobalWorkerOptions.workerSrc = `${PDFJS}build/pdf.worker.min.mjs`;

const CARDS_PER_SHEET = 10;
const $ = (id) => document.getElementById(id);

const state = { result: null, deckIndex: 0, mixed: false, order: [], pos: 0, seen: new Set(), done: new Set() };

// ---------- upload ----------

$('file').addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (file) loadFile(file);
});
const drop = $('drop');
drop.addEventListener('dragover', (e) => {
  e.preventDefault();
  drop.classList.add('over');
});
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', (e) => {
  e.preventDefault();
  drop.classList.remove('over');
  const file = e.dataTransfer.files[0];
  if (file) loadFile(file);
});
for (const b of document.querySelectorAll('[data-sample]')) {
  b.addEventListener('click', async () => {
    setStatus('Loading the sample…');
    try {
      const res = await fetch(b.dataset.sample);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await run(new Uint8Array(await res.arrayBuffer()), 'Sample sheet');
    } catch (err) {
      setStatus(`Could not load the sample (${err.message}).`, true);
    }
  });
}

async function loadFile(file) {
  if (!/\.pdf$/i.test(file.name) && file.type !== 'application/pdf') {
    setStatus('That is not a PDF. Please choose a .pdf file.', true);
    return;
  }
  setStatus(`Reading ${file.name}…`);
  await run(new Uint8Array(await file.arrayBuffer()), file.name);
}

async function run(data, name) {
  try {
    const result = await makeDecks(pdfjs, data, { standardFontDataUrl: `${PDFJS}standard_fonts/` });
    await drawPhotos(result.built.decks);
    state.result = result;
    state.done.clear();
    setStatus('');
    showResult(name);
  } catch (err) {
    console.error(err);
    setStatus(`Could not read this PDF. It may be damaged or password-protected. (${err.message})`, true);
  }
}

const PHOTO_MAX = 600; // pixels on the longest side: plenty for a 85 × 55 mm card

/** Turns each photo found in the sheet into an image the cards can show. A photo that fails is left out. */
async function drawPhotos(decks) {
  const urls = new Map();
  for (const card of decks.flatMap((d) => d.cards)) {
    if (!card.photo) continue;
    if (!urls.has(card.photo.id)) {
      try {
        urls.set(card.photo.id, imageToDataUrl(await card.photo.load()));
      } catch (err) {
        console.warn('Photo skipped', err);
        urls.set(card.photo.id, null);
      }
    }
    const url = urls.get(card.photo.id);
    if (url) card.photoUrl = url;
  }
}

function imageToDataUrl(img) {
  const width = img.bitmap?.width || img.width;
  const height = img.bitmap?.height || img.height;
  const scale = Math.min(1, PHOTO_MAX / Math.max(width, height));
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const ctx = canvas.getContext('2d');
  if (img.bitmap) {
    ctx.drawImage(img.bitmap, 0, 0, canvas.width, canvas.height);
  } else {
    const full = document.createElement('canvas');
    full.width = width;
    full.height = height;
    full.getContext('2d').putImageData(toImageData(img), 0, 0);
    ctx.drawImage(full, 0, 0, canvas.width, canvas.height);
  }
  return canvas.toDataURL('image/jpeg', 0.85);
}

/** pdf.js raw pixels (grey 1-bit, RGB or RGBA) -> ImageData. */
function toImageData(img) {
  const { width, height, data, kind } = img;
  const out = new ImageData(width, height);
  if (kind === 3 || data.length === width * height * 4) {
    out.data.set(data);
  } else if (kind === 2 || data.length === width * height * 3) {
    for (let i = 0, j = 0; i < width * height; i++, j += 3) {
      out.data.set([data[j], data[j + 1], data[j + 2], 255], i * 4);
    }
  } else {
    const rowBytes = Math.ceil(width / 8);
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const on = (data[y * rowBytes + (x >> 3)] >> (7 - (x & 7))) & 1;
        out.data.set(on ? [255, 255, 255, 255] : [0, 0, 0, 255], (y * width + x) * 4);
      }
    }
  }
  return out;
}

function setStatus(text, error = false) {
  const s = $('status');
  s.textContent = text;
  s.classList.toggle('error', error);
}

// ---------- result ----------

function showResult(name) {
  const { built, check, pages } = state.result;
  $('result').hidden = false;
  $('doc-title').textContent = built.title || name;
  const count = built.decks.reduce((n, d) => n + d.cards.length, 0);
  $('doc-meta').textContent = `${name} · ${pages} page${pages === 1 ? '' : 's'} · ${built.decks.length} decks · ${count} cards`;

  const checks = $('checks');
  if (!check.ok) {
    checks.innerHTML = `<div class="bad"><b>Not ready to print.</b> These need fixing in the sheet first:
      <ul>${check.problems.map((p) => `<li>${esc(p)}</li>`).join('')}</ul></div>`;
  } else {
    checks.innerHTML = `<div class="ok">✓ Every card checked word-for-word against the sheet.${
      check.notes.length ? `<ul>${check.notes.map((n) => `<li>${esc(n)}</li>`).join('')}</ul>` : ''
    }</div>`;
  }

  const playable = check.ok && built.decks.length > 0;
  for (const id of ['decks', 'stage']) $(id).hidden = !playable;
  $('closed').hidden = true;
  $('print').disabled = !playable;
  $('sheets').innerHTML = playable ? sheetsHtml(built.decks) : '';
  if (!playable) return;

  renderChips();
  startDeck(0);
  $('result').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderChips() {
  const { decks } = state.result.built;
  $('decks').innerHTML =
    decks
      .map(
        (d, i) =>
          `<button type="button" class="chip${state.done.has(i) ? ' done' : ''}" data-i="${i}" aria-pressed="${!state.mixed && i === state.deckIndex}">${esc(d.entity)}</button>`,
      )
      .join('') +
    (decks.filter((d) => !d.compare).length > 1
      ? `<button type="button" class="chip" data-mix="1" aria-pressed="${state.mixed}">Mix all</button>`
      : '');
}

$('decks').addEventListener('click', (e) => {
  const b = e.target.closest('.chip');
  if (!b) return;
  if (b.dataset.mix) startMixed();
  else startDeck(Number(b.dataset.i));
});

// ---------- one card at a time ----------

function startDeck(i) {
  state.mixed = false;
  state.deckIndex = i;
  state.order = state.result.built.decks[i].cards;
  begin();
}

function startMixed() {
  state.mixed = true;
  const decks = state.result.built.decks;
  // Only single-fact cards are shuffled; cards about a whole topic (final picture, lists, timelines,
  // pairs, the comparison) would give the game away mid-round.
  const SINGLE = new Set(['hook', 'cloze', 'who', 'why', 'recall']);
  const all = decks.flatMap((d) => d.cards.filter((c) => SINGLE.has(c.kind)));
  for (let i = all.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [all[i], all[j]] = [all[j], all[i]];
  }
  // The "who did what?" card comes last: after mixing, compare them all.
  state.order = [...all, ...decks.flatMap((d) => d.cards.filter((c) => c.kind === 'compare'))];
  begin();
}

function begin() {
  state.pos = 0;
  state.seen = new Set();
  $('stage').hidden = false;
  $('closed').hidden = true;
  renderChips();
  renderCard();
}

const card = $('card');

function renderCard() {
  const c = state.order[state.pos];
  card.classList.remove('flipped');
  $('front').innerHTML = `<span class="cardface f">${frontHtml(c)}</span>`;
  $('back').innerHTML = `<span class="cardface b">${backHtml(c)}</span>`;
  card.setAttribute('aria-label', `Card ${state.pos + 1} of ${state.order.length}. ${c.clue} ${c.ask}. Tap to flip.`);
  renderDots();
  $('prev').disabled = state.pos === 0;
}

function renderDots() {
  $('dots').innerHTML = state.order
    .map((_, k) => `<span class="dot${state.seen.has(k) ? ' seen' : ''}${k === state.pos ? ' here' : ''}"></span>`)
    .join('');
}

function flip() {
  card.classList.toggle('flipped');
  if (card.classList.contains('flipped')) {
    state.seen.add(state.pos);
    renderDots();
  }
}

function next() {
  if (state.pos < state.order.length - 1) {
    state.pos++;
    renderCard();
    return;
  }
  if (!state.mixed) state.done.add(state.deckIndex);
  $('stage').hidden = true;
  $('closed').hidden = false;
  $('closed-text').textContent = state.mixed
    ? `All ${state.order.length} cards, mixed. Detective rank earned!`
    : `${state.result.built.decks[state.deckIndex].entity}: ${state.order.length} cards done.`;
  renderChips();
}

function prev() {
  if (state.pos > 0) {
    state.pos--;
    renderCard();
  }
}

card.addEventListener('click', flip);
$('next').addEventListener('click', next);
$('prev').addEventListener('click', prev);
$('again').addEventListener('click', () => (state.mixed ? startMixed() : startDeck(state.deckIndex)));
$('mixed').addEventListener('click', startMixed);
document.addEventListener('keydown', (e) => {
  if ($('stage').hidden || $('result').hidden || e.target.closest('input')) return;
  if (e.key === 'ArrowRight') next();
  else if (e.key === 'ArrowLeft') prev();
});

// ---------- print sheets ----------

function sheetsHtml(decks) {
  const cards = decks.flatMap((d) => d.cards);
  let html = '';
  for (let s = 0; s * CARDS_PER_SHEET < cards.length; s++) {
    const group = cards.slice(s * CARDS_PER_SHEET, (s + 1) * CARDS_PER_SHEET);
    const fronts = [];
    const backs = [];
    for (let i = 0; i < CARDS_PER_SHEET; i++) {
      const c = group[i];
      fronts.push(c ? `<div class="cell"><span class="cardface f">${frontHtml(c)}</span></div>` : '<div class="cell empty"></div>');
      // Backs are mirrored left-right so they line up when printed double-sided (flip on long edge).
      const mirror = i % 2 === 0 ? i + 1 : i - 1;
      const m = group[mirror];
      backs.push(m ? `<div class="cell"><span class="cardface b">${backHtml(m)}</span></div>` : '<div class="cell empty"></div>');
    }
    const n = s + 1;
    html += `<div class="sheet-wrap"><div class="sheet-label">Sheet ${n} · fronts</div><div class="sheet">${fronts.join('')}</div></div>`;
    html += `<div class="sheet-wrap"><div class="sheet-label">Sheet ${n} · backs (print on the reverse)</div><div class="sheet">${backs.join('')}</div></div>`;
  }
  return html;
}

$('print').addEventListener('click', () => window.print());
