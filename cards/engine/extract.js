// PDF -> lines of text, keeping which words the author emphasised (bold or a second font).
// Works in the browser and in Node: the caller passes in the pdf.js module.

const Y_TOLERANCE = 2; // points; text items closer than this vertically are on the same line

/**
 * @returns {Promise<{pages: number, lines: Line[]}>}
 * Line = { page, y, size, segments: [{text, emph}], text }
 */
export async function extractLines(pdfjs, data, options = {}) {
  return linesFromDocument(await pdfjs.getDocument({ data, ...options }).promise);
}

/** Same as extractLines, for a document that is already open. */
export async function linesFromDocument(doc) {
  const raw = [];
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const content = await page.getTextContent();
    for (const item of content.items) {
      if (!('str' in item) || item.str === '') continue;
      raw.push({
        page: p,
        x: item.transform[4],
        y: item.transform[5],
        size: Math.round(Math.hypot(item.transform[2], item.transform[3]) * 10) / 10,
        width: item.width,
        text: item.str,
        font: item.fontName,
      });
    }
  }
  return { pages: doc.numPages, lines: groupLines(raw), items: raw };
}

/** Groups positioned text items into reading-order lines and marks emphasised runs. */
export function groupLines(items) {
  const bodyFont = dominant(items.filter((i) => i.text.trim()), (i) => i.font);
  const bodySize = dominant(items.filter((i) => i.text.trim()), (i) => i.size);

  const byPage = new Map();
  for (const it of items) {
    if (!byPage.has(it.page)) byPage.set(it.page, []);
    byPage.get(it.page).push(it);
  }

  const lines = [];
  for (const [page, pageItems] of [...byPage].sort((a, b) => a[0] - b[0])) {
    pageItems.sort((a, b) => b.y - a.y || a.x - b.x);
    let current = null;
    for (const it of pageItems) {
      if (!current || Math.abs(current.y - it.y) > Y_TOLERANCE) {
        current = { page, y: it.y, items: [] };
        lines.push(current);
      }
      current.items.push(it);
    }
  }

  return lines
    .map((line) => {
      line.items.sort((a, b) => a.x - b.x);
      const segments = [];
      let lastEnd = null;
      for (const it of line.items) {
        let text = it.text;
        if (lastEnd !== null && it.x - lastEnd > 1 && !/\s$/.test(lastText(segments)) && !/^\s/.test(text)) {
          text = ' ' + text;
        }
        lastEnd = it.x + it.width;
        const emph = it.text.trim() !== '' && it.font !== bodyFont && Math.abs(it.size - bodySize) < 1;
        const prev = segments[segments.length - 1];
        // Whitespace keeps the previous run's emphasis so "River Thames" stays one run.
        if (prev && (prev.emph === emph || it.text.trim() === '')) prev.text += text;
        else segments.push({ text, emph });
      }
      const size = Math.max(...line.items.filter((i) => i.text.trim()).map((i) => i.size), 0);
      const text = segments
        .map((s) => s.text)
        .join('')
        .replace(/\s+/g, ' ')
        .trim();
      return { page: line.page, y: line.y, size, segments: tidySegments(segments), text };
    })
    .filter((l) => l.text !== '');
}

function lastText(segments) {
  return segments.length ? segments[segments.length - 1].text : '';
}

function tidySegments(segments) {
  return segments.map((s) => ({ text: s.text.replace(/\s+/g, ' '), emph: s.emph })).filter((s) => s.text !== '');
}

function dominant(items, key) {
  const counts = new Map();
  for (const it of items) counts.set(key(it), (counts.get(key(it)) || 0) + it.text.length);
  let best = null;
  let bestCount = -1;
  for (const [k, c] of counts) {
    if (c > bestCount) {
      best = k;
      bestCount = c;
    }
  }
  return best;
}
