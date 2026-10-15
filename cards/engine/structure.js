// Lines -> the sheet's structure: the places/items it teaches, their facts, and the author's summary lines.
// Only rules, no AI. Anything the rules don't recognise is kept in `other` so it can be reported, never guessed.

const BULLET = /^[•●▪◦‣*–-]\s+/;
const ENTITY_HEADING = /^(?:\d+[.)]\s+)?([A-Z][A-Z .'’&]*[A-Z])\s*[–—-]\s*(.*[a-z].*)$/;
// "2. COMPARATIVE TABLE" or an unnumbered all-capitals line of two or more words ("QUICK COMPARISON").
const SECTION_HEADING = /^(?:\d+[.)]\s+[A-Z][A-Z0-9 &,'’:–—-]+|[A-Z][A-Z&,'’-]+(?:\s+[A-Z0-9&,'’–—-]+)+)$/;
const LABEL = /^[A-Z][A-Z ]{2,}:/;
const SUBHEADING = /^[A-Z][A-Za-z ]{2,30}:$/; // "Causes:" inside a topic: labels the bullets under it
const FACT_LABEL =
  /^(immediate cause|causes?|reasons?|results?|consequences?|effects?|impact|push factors?|pull factors?|measures|precautions|prevention|solutions|raw materials?|(?:main |other )?(?:centres|centers|states|places)|products?|(?:location )?factors|term|tenure|presiding officer|chairman|head|powers?|functions?|members|composition|strength)\s*:/i;
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
        display: sentenceCase(heading[1].trim()),
        descriptor: heading[2].trim(),
        page: line.page,
        y: line.y,
        bullets: [],
        type: kindOfHeading(heading[1], heading[2]),
      };
      entities.push(current);
      continue;
    }
    if (SECTION_HEADING.test(text)) {
      // A numbered section ("1. CAUSES OF THE UPRISING") is a topic of its own if bullets follow it.
      // Sections with no bullets of their own (notes headers, tables, questions) are dropped below.
      closeBullet();
      const name = text.replace(/^\d+[.)]\s+/, '').trim();
      current = {
        name,
        heading: text,
        display: sentenceCase(name),
        descriptor: '',
        page: line.page,
        y: line.y,
        bullets: [],
        type: 'aspect',
      };
      current.label = labelFor(name);
      entities.push(current);
      continue;
    }
    if (LABEL.test(text)) {
      closeBullet();
      current = null;
      other.push(text);
      continue;
    }
    if (current && SUBHEADING.test(text) && !BULLET.test(text)) {
      closeBullet();
      current.sublabel = labelFor(text);
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
      if (current) bullet = { page: line.page, segments: stripBullet(line.segments), label: current.sublabel || null };
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
  for (const e of entities) if (e.type === 'aspect' && !e.bullets.length) other.push(e.heading);
  const result = entities
    .filter((e) => e.bullets.length || e.type === 'place')
    .map((e) => ({
      name: e.name,
      display: e.display,
      descriptor: e.descriptor,
      page: e.page,
      y: e.y,
      type: e.type,
      label: e.label || null,
      facts: e.bullets.flatMap((b, i) =>
        splitFacts(b, e.display, `${slug(e.display)}-${i + 1}`).map((f) => ({
          ...f,
          label:
            bulletLabel(f.text.match(FACT_LABEL)?.[1] || '') ||
            b.label ||
            e.label ||
            (e.type === 'institution' ? institutionLabel(f.text) : null),
        })),
      ),
    }));
  return {
    title,
    kindWord: kindWordFrom(title),
    kindPlural: kindPluralFrom(title),
    entities: result,
    summaries,
    other,
    text: docText,
  };
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

// A heading is about a person when its description says what they were ("Social reformer"),
// gives life years ("(1772–1833)"), or the name starts with a title ("RAJA", "SWAMI").
const PERSON_WORDS =
  /\b(reformer|leader|scientist|king|queen|emperor|empress|ruler|poet|writer|author|founder|freedom fighter|saint|philosopher|inventor|president|prime minister|general|educationist|thinker|explorer|governor|viceroy|sultan|nawab)s?\b/i;
const LIFE_YEARS = /\(\s*(?:c\.\s*)?\d{3,4}\s*[–—-]\s*\d{3,4}\s*\)/;
const TITLES = /^(RAJA|RANI|SWAMI|MAHATMA|SIR|LORD|DR|BEGUM|MAHARAJA|MAHARANI|SANT|GURU|EMPEROR|QUEEN|KING)\b/;

/** Place, person, industry or institution, from a heading's name and description. */
export function kindOfHeading(name, descriptor) {
  if (isIndustry(name, descriptor)) return 'industry';
  if (isProcess(name)) return 'process';
  if (isInstitution(name, descriptor)) return 'institution';
  if (isPerson(name, descriptor)) return 'person';
  return 'place';
}

const PROCESSES =
  /\b(MIGRATION|URBANI[SZ]ATION|POPULATION|EARTHQUAKES?|FLOODS?|CYCLONES?|DROUGHTS?|LANDSLIDES?|TSUNAMIS?|SOIL EROSION|EROSION|DEFORESTATION|POLLUTION|GLOBAL WARMING|CLIMATE CHANGE|VOLCANO(?:ES)?|VOLCANIC ERUPTIONS?|DISASTERS?|WEATHERING|DESERTIFICATION)\b/;

/** "MIGRATION – Movement of people…", "EARTHQUAKES – Sudden shaking of the ground". */
export function isProcess(name) {
  return PROCESSES.test(name);
}

const INSTITUTIONS =
  /\b(PARLIAMENT|LOK SABHA|RAJYA SABHA|PRESIDENT|VICE-PRESIDENT|PRIME MINISTER|SUPREME COURT|HIGH COURTS?|JUDICIARY|EXECUTIVE|LEGISLATURE|CONSTITUTION|ELECTION COMMISSION|COUNCIL OF MINISTERS|CABINET|PANCHAYATS?|MUNICIPAL|ASSEMBLY|UNITED NATIONS|SECURITY COUNCIL)\b/;

/** "LOK SABHA – Lower House of Parliament", "SUPREME COURT – Highest court of India". */
export function isInstitution(name, descriptor) {
  return INSTITUTIONS.test(name) || /\b(house of|court|head of the state|legislature)\b/i.test(descriptor);
}

/** "COTTON TEXTILE INDUSTRY – Agro-based industry" */
export function isIndustry(name, descriptor) {
  return /\bINDUSTR(Y|IES)\b/.test(name) || /^\s*(agro|mineral|forest|marine)-based\b/i.test(descriptor);
}

/** What a bullet's own label says it is: "Raw material:", "Main centres:", "Products:", "Cause:"… */
export function bulletLabel(prefix) {
  const t = prefix.toLowerCase();
  if (!t) return null;
  if (/\bpush\b/.test(t)) return 'push';
  if (/\bpull\b/.test(t)) return 'pull';
  if (/raw material/.test(t)) return 'raw';
  if (/centres|centers|states|places/.test(t)) return 'where';
  if (/product/.test(t)) return 'product';
  if (/factor/.test(t)) return 'factor';
  if (/term|tenure/.test(t)) return 'term';
  if (/presiding officer|chairman|head/.test(t)) return 'head';
  if (/powers?|functions?/.test(t)) return 'job';
  if (/members|composition|strength/.test(t)) return 'members';
  return labelFor(t);
}

/** For institutions, what an unlabelled sentence is about: how they are chosen, age, term, who leads, the job. */
export function institutionLabel(text) {
  if (/\b(elected|appointed|chosen|nominated)\b/i.test(text)) return 'chosen';
  if (/\bat least \d+ years old\b|\bage of \d+\b/i.test(text)) return 'age';
  if (/\bterm\b|\b\d+ years\b/i.test(text)) return 'term';
  if (/\b(presiding officer|speaker|chairman)\b/i.test(text)) return 'head';
  if (/\b(protects?|can |powers?|functions?|commander|guardian|makes laws)\b/i.test(text)) return 'job';
  return null;
}

export function isPerson(name, descriptor) {
  return PERSON_WORDS.test(descriptor) || LIFE_YEARS.test(descriptor) || TITLES.test(name);
}

const KIND_WORDS = {
  industries: 'industry',
  disasters: 'disaster',
  institutions: 'institution',
  reformers: 'reformer',
  personalities: 'person',
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

function kindPluralFrom(title) {
  const words = title.toLowerCase().match(/[a-z]+/g) || [];
  return words.find((w) => KIND_WORDS[w]) || null;
}

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

/** What a heading or label says its bullets are: causes, results, a course of events, or people. */
export function labelFor(text) {
  const t = text.toLowerCase();
  if (/\bpush\b/.test(t)) return 'push';
  if (/\bpull\b/.test(t)) return 'pull';
  if (/\b(measures?|precautions?|prevention|solutions?|remedies|safety|do's|conservation|conserve|saving)\b/.test(t)) return 'action';
  if (/\b(causes?|reasons?|why)\b/.test(t)) return 'cause';
  if (/\b(results?|consequences?|effects?|impact|significance|outcome)\b/.test(t)) return 'result';
  if (/\b(course|events?|timeline|chronology)\b/.test(t)) return 'course';
  if (/\b(leaders?|people|personalities|centres?|who)\b/.test(t)) return 'people';
  return null;
}

const SMALL = new Set(['of', 'the', 'and', 'in', 'at', 'to', 'for', 'a', 'an', 'on', 'by']);

/** "CAUSES OF THE UPRISING" -> "Causes of the Uprising". */
export function sentenceCase(s) {
  return titleCase(s)
    .split(' ')
    .map((w, i) => (i > 0 && SMALL.has(w.toLowerCase()) ? w.toLowerCase() : w))
    .join(' ');
}
