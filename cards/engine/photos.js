// Photos printed in the sheet itself (a portrait beside a person's heading, a picture of a place).
// They come from the PDF, so they can't show the wrong person; nothing is downloaded.

const MIN_SIZE = 36; // points (half an inch): smaller images are bullets, icons or logos
const ABOVE_SLACK = 40; // a photo may start a little above its heading

/**
 * Where each image is drawn on each page, in the same coordinates as the text.
 * @returns {Promise<Array<{page, x, y, w, h, id, load: () => Promise<object>}>>}
 * `load` resolves to pdf.js's decoded image ({width, height, data} or {bitmap}).
 */
export async function imagesFromDocument(doc, OPS) {
  const out = [];
  for (let p = 1; p <= doc.numPages; p++) {
    const page = await doc.getPage(p);
    const ops = await page.getOperatorList();
    let ctm = [1, 0, 0, 1, 0, 0];
    const stack = [];
    ops.fnArray.forEach((fn, i) => {
      const args = ops.argsArray[i];
      if (fn === OPS.save) stack.push(ctm);
      else if (fn === OPS.restore) ctm = stack.pop() || ctm;
      else if (fn === OPS.transform) ctm = multiply(args, ctm);
      else if (fn === OPS.paintImageXObject && typeof args[0] === 'string') {
        const box = unitSquare(ctm);
        if (box.w >= MIN_SIZE && box.h >= MIN_SIZE) {
          const id = args[0];
          out.push({ page: p, ...box, id: `p${p}-${id}`, load: () => loadImage(page, id) });
        }
      }
    });
  }
  return out;
}

function multiply(m, n) {
  return [
    m[0] * n[0] + m[1] * n[2],
    m[0] * n[1] + m[1] * n[3],
    m[2] * n[0] + m[3] * n[2],
    m[2] * n[1] + m[3] * n[3],
    m[4] * n[0] + m[5] * n[2] + n[4],
    m[4] * n[1] + m[5] * n[3] + n[5],
  ];
}

/** The page box an image fills: pdf.js draws every image into the unit square under the current matrix. */
export function unitSquare(m) {
  const xs = [0, 1].flatMap((u) => [0, 1].map((v) => m[0] * u + m[2] * v + m[4]));
  const ys = [0, 1].flatMap((u) => [0, 1].map((v) => m[1] * u + m[3] * v + m[5]));
  const x = Math.min(...xs);
  const y = Math.min(...ys);
  return { x, y, w: Math.max(...xs) - x, h: Math.max(...ys) - y };
}

function loadImage(page, id) {
  return new Promise((resolve) => {
    const objs = id.startsWith('g_') ? page.commonObjs : page.objs;
    objs.get(id, resolve);
  });
}

/**
 * Gives each place or person the largest photo printed in its part of the page: between its heading
 * (with a little room above) and the next heading on the same page. Topics that are not a place or
 * person get none. Each photo is used once.
 * @returns {Map<string, image>} entity name -> image
 */
export function assignPhotos(entities, images) {
  const result = new Map();
  const used = new Set();
  const byPage = new Map();
  for (const e of entities) {
    if (typeof e.y !== 'number') continue;
    if (!byPage.has(e.page)) byPage.set(e.page, []);
    byPage.get(e.page).push(e);
  }
  for (const [page, list] of byPage) {
    list.sort((a, b) => b.y - a.y);
    list.forEach((e, i) => {
      if (e.type !== 'person' && e.type !== 'place') return;
      const bottom = i + 1 < list.length ? list[i + 1].y : -Infinity;
      const inside = images
        .filter((img) => img.page === page && !used.has(img.id))
        .filter((img) => {
          const middle = img.y + img.h / 2;
          return middle > bottom && img.y + img.h <= e.y + ABOVE_SLACK + img.h / 2;
        })
        .sort((a, b) => b.w * b.h - a.w * a.h);
      if (inside.length) {
        used.add(inside[0].id);
        result.set(e.display, inside[0]);
      }
    });
  }
  return result;
}
