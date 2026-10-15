// Lines -> the sheet's structure: the places/items it teaches, their facts, and the author's summary lines.
// Only rules, no AI. Anything the rules don't recognise is kept in `other` so it can be reported, never guessed.

const BULLET = /^[•●▪◦‣*–-]\s+/;
const ENTITY_HEADING = /^(?:\d+[.)]\s+)?([A-Z][A-Z .'’&]*[A-Z])\s*[–—-]\s*(.*[a-z].*)$/;
const SECTION_HEADING = /^\d+[.)]\s+[A-Z][A-Z0-9 &,'’:–—-]+$/;
const LABEL = /^[A-Z][A-Z ]{2,}:/;
const PAGE_NUMBER = /^page\s+\d+$/i;

/**
 * @returns {{title: string, kindWord: string|null, entities: Entity[], summaries: Map<string,string>, other: string[], text: string}}
 * Entity = { name, display, descriptor, page, facts: Fact[] }
 * Fact = { id, entity, text, keys: string[], page }
 */
export function parseSheet(lines) {
  const body = dropRunningHeaders(lines);
  const title = pickTitle(body);
  const entities = [];
  const summaries = new Map();
  const other = [];
  let current = null; // entity being read
  let bullet = null; // bullet being read (may wrap over several lines)

  const closeBullet = () => {
    if (bullet && current) current.bullets.push(bullet);
    bullet = null;
  };

  for (const line of body) {
    const text = line.text;
    const heading = text.match(ENTITY_HEADING);
    if (heading && line !== body[0] && !BULLET.test(text)) {
      closeBullet();
      current = {
        name: heading[1].trim(),
        display: titleCase(heading[1].trim()),
        descriptor: heading[2].trim(),
        page: line.page,
        bullets: [],
      };
      entities.push(current);
      continue;
    }
    if (SECTION_HEADING.test(text) || LABEL.test(text)) {
      closeBullet();
      current = null;
      other.push(text);
      continue;
    }
    if (BULLET.test(text)) {
      const summary = matchSummary(text, entities);
      if (summary) {
        closeBullet();
        summaries.set(summary.name, summary.text);
        continue;
      }
      closeBullet();
      if (current) bullet = { page: line.page, segments: stripBullet(line.segments) };
      else other.push(text);
      continue;
    }
    if (bullet) {
      bullet.segments = joinSegments(bullet.segments, line.segments);
      continue;
    }
    other.push(text);
  }
  closeBullet();

  const docText = body.map((l) => l.text).join('\n');
  const result = entities.map((e) => ({
    name: e.name,
    display: e.display,
    descriptor: e.descriptor,
    page: e.page,
    facts: e.bullets.flatMap((b, i) => splitFacts(b, e.display, `${slug(e.display)}-${i + 1}`)),
  }));
  return { title, kindWord: kindWordFrom(title), entities: result, summaries, other, text: docText };
}

/** Lines that repeat on most pages (running headers, footers, page numbers) carry no teaching. */
export function dropRunningHeaders(lines) {
  const pages = new Set(lines.map((l) => l.page)).size;
  const seen = new Map();
  for (const l of lines) {
    const k = l.text.replace(/\d+/g, '#');
    if (!seen.has(k)) seen.set(k, new Set());
    seen.get(k).add(l.page);
  }
  return lines.filter((l) => {
    if (PAGE_NUMBER.test(l.text)) return false;
    const k = l.text.replace(/\d+/g, '#');
    return !(pages >= 2 && seen.get(k).size >= Math.max(2, pages / 2));
  });
}

function pickTitle(lines) {
  const first = lines.filter((l) => l.page === 1);
  if (!first.length) return '';
  const maxSize = Math.max(...first.map((l) => l.size));
  return first.find((l) => l.size === maxSize).text;
}

const KIND_WORDS = {
  cities: 'city',
  countries: 'country',
  rivers: 'river',
  states: 'state',
  places: 'place',
  rulers: 'ruler',
  kings: 'king',
  scientists: 'scientist',
  leaders: 'leader',
  elements: 'element',
  planets: 'planet',
  mountains: 'mountain',
};

function kindWordFrom(title) {
  const words = title.toLowerCase().match(/[a-z]+/g) || [];
  for (const w of words) if (KIND_WORDS[w]) return KIND_WORDS[w];
  return null;
}

function matchSummary(text, entities) {
  const m = text.replace(BULLET, '').match(/^(.+?)\s*=\s*(.+)$/);
  if (!m) return null;
  const e = entities.find((x) => x.display.toLowerCase() === m[1].trim().toLowerCase());
  return e ? { name: e.display, text: text.replace(BULLET, '').trim() } : null;
}

function stripBullet(segments) {
  const out = segments.map((s) => ({ ...s }));
  if (out.length) out[0].text = out[0].text.replace(BULLET, '');
  return out.filter((s) => s.text !== '');
}

function joinSegments(a, b) {
  const out = a.map((s) => ({ ...s }));
  const add = b.map((s) => ({ ...s }));
  if (out.length && add.length) add[0].text = ' ' + add[0].text.trimStart();
  return [...out, ...add];
}

/** A bullet can hold several facts separated by ';'. Each keeps the author's emphasised words. */
export function splitFacts(bullet, entityDisplay, idBase) {
  let text = '';
  const mask = [];
  for (const s of bullet.segments) {
    text += s.text;
    for (let i = 0; i < s.text.length; i++) mask.push(s.emph);
  }
  const parts = [];
  let start = 0;
  for (let i = 0; i <= text.length; i++) {
    if (i === text.length || text[i] === ';') {
      parts.push([start, i]);
      start = i + 1;
    }
  }
  return parts
    .map(([a, b], n) => {
      const raw = text.slice(a, b);
      const factText = clean(raw);
      const keys = emphRuns(raw, mask.slice(a, b)).filter((k) => k.toLowerCase() !== entityDisplay.toLowerCase());
      return {
        id: parts.length > 1 ? `${idBase}${String.fromCharCode(97 + n)}` : idBase,
        entity: entityDisplay,
        text: factText,
        keys,
        page: bullet.page,
      };
    })
    .filter((f) => f.text.length > 2);
}

function emphRuns(text, mask) {
  const runs = [];
  let cur = '';
  for (let i = 0; i < text.length; i++) {
    if (mask[i]) cur += text[i];
    else if (cur) {
      runs.push(cur);
      cur = '';
    }
  }
  if (cur) runs.push(cur);
  return runs.map((r) => r.replace(/\s+/g, ' ').replace(/^[\s,.;:]+|[\s,.;:]+$/g, '')).filter((r) => r.length > 1);
}

function clean(s) {
  return s.replace(/\s+/g, ' ').trim();
}

export function titleCase(s) {
  return s.toLowerCase().replace(/(^|[\s'’-])([a-z])/g, (m, a, b) => a + b.toUpperCase());
}

export function slug(s) {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}
