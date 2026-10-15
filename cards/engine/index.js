// One call from PDF bytes to checked decks.

import { buildDecks } from './cards.js';
import { checkDecks } from './checks.js';
import { extractLines } from './extract.js';
import { parseSheet } from './structure.js';

export async function makeDecks(pdfjs, data, options = {}) {
  const { pages, lines } = await extractLines(pdfjs, data, options);
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
  const check = checkDecks(sheet, built);
  return { pages, sheet, built, check };
}
