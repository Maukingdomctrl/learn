// One call from PDF bytes to checked decks.

import { buildDecks } from './cards.js';
import { checkDecks } from './checks.js';
import { linesFromDocument } from './extract.js';
import { assignPhotos, imagesFromDocument } from './photos.js';
import { parseSheet } from './structure.js';

/**
 * Cards that show a place or person (the riddle and the final card) get a `photo` when the sheet
 * prints one in that part of the page; `photo.load()` gives pdf.js's decoded image for the page to draw.
 */
export async function makeDecks(pdfjs, data, options = {}) {
  const doc = await pdfjs.getDocument({ data, ...options }).promise;
  const pages = doc.numPages;
  const { lines } = await linesFromDocument(doc);
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
  const photos = assignPhotos(sheet.entities, await imagesFromDocument(doc, pdfjs.OPS));
  for (const d of built.decks) {
    const photo = photos.get(d.entity);
    if (photo) for (const c of d.cards) if (c.kind === 'hook' || c.kind === 'portrait') c.photo = photo;
  }
  const check = checkDecks(sheet, built);
  if (photos.size) check.notes.push(`${photos.size} photos taken from the sheet itself.`);
  return { pages, sheet, built, check };
}
