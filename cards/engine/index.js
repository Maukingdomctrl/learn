// One call from PDF bytes to checked decks.

import { buildDecks } from './cards.js';
import { checkDecks } from './checks.js';
import { linesFromDocument } from './extract.js';
import { assignPhotos, imagesFromDocument } from './photos.js';
import { findTables, tableCards } from './tables.js';
import { parseSheet } from './structure.js';

/**
 * Cards that show a place or person (the riddle and the final card) get a `photo` when the sheet
 * prints one in that part of the page; `photo.load()` gives pdf.js's decoded image for the page to draw.
 */
export async function makeDecks(pdfjs, data, options = {}) {
  const doc = await pdfjs.getDocument({ data, ...options }).promise;
  const pages = doc.numPages;
  const { lines, items } = await linesFromDocument(doc);
  if (!lines.length) {
    return {
      pages,
      sheet: null,
      built: { title: '', kindWord: null, decks: [] },
      check: {
        ok: false,
        problems: ['No text found in this PDF. It may be a scan or a photo. This version needs a PDF with real text.'],
        notes: [],
      },
    };
  }
  const sheet = parseSheet(lines);
  const built = buildDecks(sheet);
  // Comparison tables become one "match" card per row, in a deck of their own.
  const tables = findTables(items, sheet.entities);
  const fromTables = tableCards(tables, sheet.kindWord);
  if (fromTables.length) {
    built.decks.push({ entity: 'From the table', cards: fromTables, compare: true });
    const inTable = new Set(
      lines.filter((l) => tables.some((t) => t.page === l.page && l.y <= t.top + 2 && l.y >= t.bottom - 2)).map((l) => l.text),
    );
    sheet.other = sheet.other.filter((t) => !inTable.has(t));
  }
  const photos = assignPhotos(sheet.entities, await imagesFromDocument(doc, pdfjs.OPS));
  for (const d of built.decks) {
    const photo = photos.get(d.entity);
    if (photo) for (const c of d.cards) if (c.kind === 'hook' || c.kind === 'portrait') c.photo = photo;
  }
  const check = checkDecks(sheet, built);
  if (photos.size) check.notes.push(`${photos.size} photos taken from the sheet itself.`);
  return { pages, sheet, built, check };
}
