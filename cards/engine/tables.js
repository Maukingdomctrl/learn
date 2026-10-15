// Comparison tables: a header row that names three or more of the sheet's topics ("Feature | London |
// Birmingham | …") and rows of short facts under each. Every cell is kept as the PDF's own pieces of text,
// so the checks can confirm each piece is in the sheet.

const SAME_LINE = 2.5; // points
const EMPTY = /^[—–-]$/;

const centre = (it) => it.x + it.width / 2;

/**
 * @returns {Array<{page, top, bottom, label, columns: string[], rows: Array<{label, cells: Map<string, string[]>}>}>}
 * cells map a topic's name to the pieces of text in its cell, top to bottom.
 */
export function findTables(items, entities) {
  const names = new Map(entities.map((e) => [e.display.toLowerCase(), e.display]));
  const tables = [];
  const pages = [...new Set(items.map((i) => i.page))];
  for (const page of pages) {
    const onPage = items.filter((i) => i.page === page && i.text.trim());
    const ys = [...new Set(onPage.map((i) => Math.round(i.y)))].sort((a, b) => b - a);
    for (const y of ys) {
      const row = onPage.filter((i) => Math.abs(i.y - y) <= SAME_LINE).sort((a, b) => a.x - b.x);
      const heads = row.filter((i) => names.has(i.text.trim().toLowerCase()));
      if (heads.length < 3 || row.length - heads.length > 1) continue;
      const corner = row.find((i) => !heads.includes(i));
      tables.push(readTable(onPage, page, y, heads, corner, names));
    }
  }
  return tables.filter((t) => t.rows.length);
}

function readTable(onPage, page, headerY, heads, corner, names) {
  const columns = heads.map((h) => ({ name: names.get(h.text.trim().toLowerCase()), x: centre(h) }));
  const labelX = corner ? centre(corner) : Math.min(...heads.map((h) => h.x)) - 60;
  const nearest = (it) => {
    const x = centre(it);
    let best = { name: null, d: Math.abs(x - labelX) };
    for (const c of columns) if (Math.abs(x - c.x) < best.d) best = { name: c.name, d: Math.abs(x - c.x) };
    return best.name; // null = the row-label column
  };

  const below = onPage.filter((i) => i.y < headerY - SAME_LINE).sort((a, b) => b.y - a.y || a.x - b.x);
  const xs = columns.map((c) => c.x).sort((a, b) => a - b);
  const gap = Math.min(...xs.slice(1).map((x, i) => x - xs[i]));
  const rows = [];
  let current = null;
  let lastY = headerY;
  let labelY = null;
  for (const it of below) {
    // The table ends at a big gap, a heading-like line, or text wider than a column (a line across the page).
    if (lastY - it.y > 40 || /^\d+[.)]\s+[A-Z]/.test(it.text.trim()) || it.width > 1.6 * gap) break;
    lastY = it.y;
    const column = nearest(it);
    if (column === null) {
      // A label on the very next line continues the one above ("Famous Landmark /" + "Fact").
      const wrapped = current && labelY !== null && labelY - it.y < 12;
      labelY = it.y;
      if (!wrapped) {
        current = { label: it.text.trim(), labelPieces: [it.text.trim()], cells: new Map() };
        rows.push(current);
      } else {
        current.label += ` ${it.text.trim()}`;
        current.labelPieces.push(it.text.trim());
      }
      continue;
    }
    if (!current) continue;
    if (!current.cells.has(column)) current.cells.set(column, []);
    current.cells.get(column).push(it.text.trim());
  }
  return {
    page,
    top: headerY,
    bottom: lastY,
    label: corner ? corner.text.trim() : '',
    columns: columns.map((c) => c.name),
    rows,
  };
}

/**
 * One "match" card per table row with two or more filled cells: the row's values scrambled on the front,
 * each topic with its value on the back ("River: River Thames · River Rea · River Lagan ↔ which city?").
 */
export function tableCards(tables, kindWord) {
  const cards = [];
  tables.forEach((t, n) => {
    for (const row of t.rows) {
      const filled = t.columns
        .filter((c) => row.cells.has(c))
        .map((c) => ({ name: c, pieces: row.cells.get(c) }))
        .filter((x) => !EMPTY.test(x.pieces.join(' ').trim()));
      if (filled.length < 2) continue;
      const value = (x) => x.pieces.join(' ');
      cards.push({
        id: `table-${n + 1}-${row.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`,
        entity: 'From the table',
        kind: 'match',
        clue: `${row.label}: match each to its ${kindWord || 'topic'}.`,
        ask: '',
        answer: 'Pairs',
        exact: '',
        frontLines: [
          filled
            .map(value)
            .sort((a, b) => a.localeCompare(b))
            .join(' · '),
          filled
            .map((x) => x.name)
            .sort((a, b) => a.localeCompare(b))
            .join(' · '),
        ],
        lines: filled.map((x) => `${x.name} … ${value(x)}`),
        // Wrapped cells are separate lines in the PDF; each piece is checked on its own.
        sheetPieces: [...row.labelPieces, ...filled.flatMap((x) => [x.name, ...x.pieces])],
        page: t.page,
        symbol: null,
      });
    }
  });
  return cards;
}
