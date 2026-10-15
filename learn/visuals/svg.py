"""Deterministic SVG drawings for visual specs.

Same spec in, same SVG out: no randomness, no layout engine. Coordinates are worked out in millimetres and
written in CSS pixels, so the browser reports real font sizes to D6. Every type has a fixed width (one column)
and a fixed height budget, so a visual cannot push a page over its limit by surprise. Drawings use black lines,
no shading and no filled areas except small arrowheads and point markers: pencil-style line art that prints
clearly on an ordinary home printer. `INK_FILLS` lists the only fills allowed; D8 checks every drawing against it.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

from markupsafe import escape

from .specs import BarModelSpec, FlowSequenceSpec, NumberLineSpec, ShapeSpec, Table

PX = 96 / 25.4  # CSS px per mm
WIDTH_MM = 120.0  # one column
SHAPE_WIDTH_MM = 68.0  # shapes sit beside the worked example in Discover
FONT_PX = 14.7  # ~11 pt: above the 10.5 pt minimum in methodology section 7.2
LINE_MM = 5.0  # text line height
CHAR_MM = 0.6 * FONT_PX / PX  # conservative average character width for DejaVu Sans at FONT_PX

# Fixed height budgets per type (mm). Bar models grow by row; nothing else grows.
HEIGHT_MM = {"shape": 38.0, "number_line": 26.0, "flow_linear": 24.0, "flow_two_rows": 50.0, "flow_cycle": 64.0}
FLOW_ONE_ROW_MAX = 4  # 5-6 linear steps go on two rows of up to 3, so each box stays readable
BAR_ROW_MM, BAR_GAP_MM, BAR_TOP_MM = 10.0, 4.0, 3.0
MAX_TICKS = 20
EDGE_MM = 0.5  # keep outlines fully inside the canvas
BLANK = "_____"  # printed in place of a hidden label; the child writes the answer on it
INK_FILLS = {"none", "#fff", "#000"}  # white or no fill for shapes; black only for small arrowheads and dots


@dataclass
class Drawing:
    svg: str
    width_mm: float
    height_mm: float
    problems: list[str] = field(default_factory=list)  # layout problems, e.g. text that does not fit


def fmt(n: float) -> str:
    """Stable number formatting: 8.0 -> '8', 2.5 -> '2.5'."""
    if float(n).is_integer():
        return str(int(n))
    return f"{n:.4g}"


def text_width_mm(s: str) -> float:
    return len(s) * CHAR_MM


def wrap(s: str, max_chars: int) -> list[str]:
    words, lines, cur = s.split(), [], ""
    for w in words:
        if cur and len(cur) + 1 + len(w) > max_chars:
            lines.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    return lines


def _p(v: float) -> str:
    return f"{v * PX:.2f}"


class _Canvas:
    def __init__(self, w_mm: float, h_mm: float, label: str):
        self.w, self.h, self.label = w_mm, h_mm, label
        self.parts: list[str] = []

    def line(self, x1, y1, x2, y2, dashed=False, width=0.35):
        dash = ' stroke-dasharray="6 4"' if dashed else ""
        self.parts.append(
            f'<line x1="{_p(x1)}" y1="{_p(y1)}" x2="{_p(x2)}" y2="{_p(y2)}" stroke="#000" '
            f'stroke-width="{_p(width)}"{dash}/>'
        )

    def poly(self, pts, fill="none", width=0.4, close=True):
        tag = "polygon" if close else "polyline"
        coords = " ".join(f"{_p(x)},{_p(y)}" for x, y in pts)
        self.parts.append(f'<{tag} points="{coords}" fill="{fill}" stroke="#000" stroke-width="{_p(width)}"/>')

    def rect(self, x, y, w, h, fill="#fff", width=0.4):
        self.parts.append(
            f'<rect x="{_p(x)}" y="{_p(y)}" width="{_p(w)}" height="{_p(h)}" fill="{fill}" stroke="#000" '
            f'stroke-width="{_p(width)}"/>'
        )

    def circle(self, cx, cy, r, fill="none", width=0.4):
        self.parts.append(
            f'<circle cx="{_p(cx)}" cy="{_p(cy)}" r="{_p(r)}" fill="{fill}" stroke="#000" stroke-width="{_p(width)}"/>'
        )

    def path(self, d_mm: list, width=0.35):
        d = " ".join(_p(t) if isinstance(t, (int, float)) else t for t in d_mm)
        self.parts.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{_p(width)}"/>')

    def text(self, x, y, s, anchor="middle", bold=False):
        weight = ' font-weight="bold"' if bold else ""
        self.parts.append(
            f'<text x="{_p(x)}" y="{_p(y)}" font-size="{FONT_PX}" text-anchor="{anchor}"{weight}>{escape(s)}</text>'
        )

    def arrowhead(self, x, y, angle):
        """Filled triangle pointing along `angle` (radians) with its tip at (x, y)."""
        size = 2.2
        a1, a2 = angle + math.radians(150), angle - math.radians(150)
        p1 = (x + size * math.cos(a1), y + size * math.sin(a1))
        p2 = (x + size * math.cos(a2), y + size * math.sin(a2))
        self.poly([(x, y), p1, p2], fill="#000", width=0.2)

    def arrow(self, x1, y1, x2, y2):
        self.line(x1, y1, x2, y2)
        self.arrowhead(x2, y2, math.atan2(y2 - y1, x2 - x1))

    def svg(self) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" class="visual-svg" width="{_p(self.w)}" height="{_p(self.h)}" '
            f'viewBox="0 0 {_p(self.w)} {_p(self.h)}" role="img" aria-label="{escape(self.label)}" '
            f'font-family="DejaVu Sans, Liberation Sans, Arial, sans-serif">' + "".join(self.parts) + "</svg>"
        )


# ---------------------------------------------------------------- shape
def _dim(value: Optional[float], unit: str) -> str:
    return f"{fmt(value)} {unit}".strip() if value is not None else "?"


def _slot_text(name: str, value: Optional[float], unit: str, hidden) -> str:
    if name in hidden:
        return f"{name} = {BLANK} {unit}".strip()
    return f"{name} = {_dim(value, unit)}"


def draw_shape(v: ShapeSpec, hidden=frozenset()) -> Drawing:
    w, h = SHAPE_WIDTH_MM, HEIGHT_MM["shape"]
    c = _Canvas(w, h, v.caption or f"{v.shape} diagram")
    problems: list[str] = []
    left, top, bottom = 3.0, 6.0, 9.0
    ah = h - top - bottom
    yb = top + ah

    if v.shape == "circle":
        label = _slot_text("radius", v.radius, v.unit, hidden)
        aw = w - left - (4 + text_width_mm(label))
        r = min(aw, ah) / 2
        cx, cy = left + aw / 2, top + ah / 2 + 1
        c.circle(cx, cy, r)
        c.circle(cx, cy, 0.7, fill="#000")
        c.line(cx, cy, cx + r, cy)
        c.text(cx + r + 3, cy + 1.5, label, anchor="start")
        if cx + r + 3 + text_width_mm(label) > w:
            problems.append("radius label does not fit")
        return Drawing(c.svg(), w, h, problems)

    if v.shape == "rectangle":
        b, ht, b_name, h_name = v.length, v.width, "length", "width"
    else:
        b, ht, b_name, h_name = v.base, v.height, "base", "height"
    if not b or not ht or b <= 0 or ht <= 0:
        return Drawing(c.svg(), w, h, [f"{v.shape} needs positive {b_name} and {h_name}"])

    h_label = _slot_text(h_name, ht, v.unit, hidden)
    aw = w - left - (4 + text_width_mm(h_label))  # leave exactly enough room for the side label
    if aw < 18:
        return Drawing(c.svg(), w, h, [f"{h_name} label is too long to fit beside the shape"])
    ratio = ht / b
    drawn = min(max(ratio, 0.25), 1.4)  # keep extreme shapes readable; say so when not to scale
    skew = 0.25 if v.shape == "parallelogram" else 0.0
    db = min(aw / (1 + skew), ah / drawn)
    dh = db * drawn
    x0 = left
    if v.shape == "triangle":
        ax = x0 + 0.35 * db
        c.poly([(x0, yb), (x0 + db, yb), (ax, yb - dh)], fill="#fff")
        foot_x, top_y, right_edge = ax, yb - dh, x0 + db
    elif v.shape == "parallelogram":
        off = skew * db
        c.poly([(x0, yb), (x0 + db, yb), (x0 + db + off, yb - dh), (x0 + off, yb - dh)], fill="#fff")
        foot_x, top_y, right_edge = x0 + off, yb - dh, x0 + db + off
    else:
        c.rect(x0, yb - dh, db, dh, fill="#fff")
        foot_x, top_y, right_edge = None, yb - dh, x0 + db

    b_label = _slot_text(b_name, b, v.unit, hidden)
    half = text_width_mm(b_label) / 2 + EDGE_MM
    c.text(min(max(x0 + db / 2, half), w - half), yb + 6.5, b_label)  # centred under the base, kept on the canvas
    label_x = right_edge + 3
    if foot_x is not None:
        c.line(foot_x, top_y, foot_x, yb, dashed=True)  # perpendicular height
        c.poly([(foot_x, yb - 2.5), (foot_x + 2.5, yb - 2.5), (foot_x + 2.5, yb)], width=0.3, close=False)
        c.line(foot_x, (top_y + yb) / 2, label_x - 1, (top_y + yb) / 2, dashed=True, width=0.2)
    c.text(label_x, (top_y + yb) / 2 + 1.5, h_label, anchor="start")
    if label_x + text_width_mm(h_label) > w:
        problems.append(f"{h_name} label does not fit beside the shape")
    if abs(drawn - ratio) > 1e-9:
        c.text(w - 1, 4.5, "(not to scale)", anchor="end")
    return Drawing(c.svg(), w, h, problems)


# ---------------------------------------------------------------- number line
def draw_number_line(v: NumberLineSpec, hidden=frozenset()) -> Drawing:
    w, h = WIDTH_MM, HEIGHT_MM["number_line"]
    c = _Canvas(w, h, v.caption or "number line")
    problems: list[str] = []
    if v.end <= v.start or v.step <= 0:
        return Drawing(c.svg(), w, h, ["number line needs start < end and a positive step"])
    n = round((v.end - v.start) / v.step)
    if n > MAX_TICKS:
        return Drawing(c.svg(), w, h, [f"number line has {n} intervals; max {MAX_TICKS}"])
    left, right, y = 8.0, 8.0, 17.0
    span = w - left - right

    def x(val: float) -> float:
        return left + (val - v.start) / (v.end - v.start) * span

    c.line(left - 5, y, w - right + 5, y)
    c.arrowhead(w - right + 5.5, y, 0)
    c.arrowhead(left - 5.5, y, math.pi)
    labels = [fmt(v.start + i * v.step) for i in range(n + 1)]
    spacing = span / max(n, 1)
    every = 1
    while max(text_width_mm(t) for t in labels) + 1 > spacing * every:
        every += 1
    for i, t in enumerate(labels):
        xi = left + i * spacing
        c.line(xi, y - 1.6, xi, y + 1.6)
        if i % every == 0 or i == n:
            c.text(xi, y + 6.5, t)
    for k, j in enumerate(v.jumps):
        x1, x2 = x(j.start), x(j.end)
        mid = (x1 + x2) / 2
        c.path(["M", x1, y - 1, "Q", mid, y - 13, x2, y - 1.2])
        c.arrowhead(x2, y - 1.2, math.atan2(11.8, x2 - mid))  # tangent of the curve at its end
        if j.label:
            c.text(mid, y - 8.5, BLANK if f"jump{k}" in hidden else j.label)
    for k, pt in enumerate(v.points):
        xp = x(pt.value)
        c.circle(xp, y, 1.1, fill="#000")
        if pt.label:
            c.text(xp, y - 3, BLANK if f"point{k}" in hidden else pt.label)
    return Drawing(c.svg(), w, h, problems)


# ---------------------------------------------------------------- bar model
def bar_total(bar) -> float:
    return sum(p.value for p in bar.parts)


def bar_part_text(part, hide: bool) -> str:
    value = BLANK if hide else fmt(part.value)
    return f"{part.label} {value}".strip() if part.label else value


def draw_bar_model(v: BarModelSpec, hidden=frozenset()) -> Drawing:
    n = len(v.bars)
    w = WIDTH_MM
    h = BAR_TOP_MM + n * (BAR_ROW_MM + BAR_GAP_MM)
    c = _Canvas(w, h, v.caption or "bar model")
    problems: list[str] = []
    label_w, total_w = 28.0, 18.0
    area = w - label_w - total_w
    biggest = max((bar_total(b) for b in v.bars), default=0)
    if biggest <= 0:
        return Drawing(c.svg(), w, h, ["bar model needs positive values"])
    scale = area / biggest
    for i, bar in enumerate(v.bars):
        y = BAR_TOP_MM + i * (BAR_ROW_MM + BAR_GAP_MM)
        c.text(label_w - 2, y + BAR_ROW_MM / 2 + 1.5, bar.label, anchor="end")
        if text_width_mm(bar.label) > label_w - 2:
            problems.append(f"bar label '{bar.label}' is too long")
        x = label_w
        for p_i, part in enumerate(bar.parts):
            pw = part.value * scale
            c.rect(x, y, pw, BAR_ROW_MM, fill="#fff")  # parts are told apart by dividing lines and labels
            t = bar_part_text(part, f"bar{i}.part{p_i}" in hidden)
            c.text(x + pw / 2, y + BAR_ROW_MM / 2 + 1.5, t)
            if text_width_mm(t) + 1 > pw:
                problems.append(f"text '{t}' does not fit inside its part of the bar")
            x += pw
        total = bar.total if bar.total is not None else bar_total(bar)
        total_text = BLANK if f"bar{i}.total" in hidden else fmt(total)
        c.text(x + 2, y + BAR_ROW_MM / 2 + 1.5, f"= {total_text}", anchor="start")
    return Drawing(c.svg(), w, h, problems)


# ---------------------------------------------------------------- flow sequence
def _box_text(c: _Canvas, cx: float, cy: float, box_w: float, s: str, max_lines: int, n: int) -> list[str]:
    max_chars = max(1, int((box_w - 3) / CHAR_MM))
    lines = wrap(s, max_chars)
    problems = []
    if len(lines) > max_lines or any(len(line) > max_chars for line in lines):
        problems.append(f"step {n} ('{s[:30]}') is too long for its box")
    shown = lines[:max_lines]
    y0 = cy - (len(shown) - 1) * LINE_MM / 2 + 1.5
    for k, line in enumerate(shown):
        c.text(cx, y0 + k * LINE_MM, line)
    return problems


def flow_box_width(v: FlowSequenceSpec) -> float:
    if v.layout == "cycle":
        return 34.0
    n = max(len(v.steps), 1)
    per_row = n if n <= FLOW_ONE_ROW_MAX else math.ceil(n / 2)
    return (WIDTH_MM - 2 * EDGE_MM - (per_row - 1) * 7.0) / per_row


def _blank_box(c: _Canvas, x: float, y: float, box_w: float, box_h: float):
    """A hidden step: an empty box with a writing line."""
    c.line(x + 3, y + box_h - 5, x + box_w - 3, y + box_h - 5, width=0.25)


def draw_flow(v: FlowSequenceSpec, hidden=frozenset()) -> Drawing:
    n = len(v.steps)
    w = WIDTH_MM
    problems: list[str] = []
    if v.layout == "linear":
        per_row = n if n <= FLOW_ONE_ROW_MAX else math.ceil(n / 2)
        rows = math.ceil(n / max(per_row, 1))
        h = HEIGHT_MM["flow_linear"] if rows == 1 else HEIGHT_MM["flow_two_rows"]
        c = _Canvas(w, h, v.caption or "sequence")
        gap, box_h, row_gap = 7.0, 20.0, 6.0
        box_w = flow_box_width(v)
        for i, step in enumerate(v.steps):
            row, col = divmod(i, per_row)
            x, y = EDGE_MM + col * (box_w + gap), 2.0 + row * (box_h + row_gap)
            c.rect(x, y, box_w, box_h, fill="#fff")
            if f"step{i}" in hidden:
                _blank_box(c, x, y, box_w, box_h)
            else:
                problems += _box_text(c, x + box_w / 2, y + box_h / 2, box_w, step, 3, i + 1)
            if i == n - 1:
                continue
            if col < per_row - 1:
                c.arrow(x + box_w + 0.8, y + box_h / 2, x + box_w + gap - 0.8, y + box_h / 2)
            else:  # elbow from the end of row 1 to the start of row 2, keeping left-to-right reading order
                mid_y = y + box_h + row_gap / 2
                first_x = EDGE_MM + box_w / 2
                c.poly(
                    [(x + box_w / 2, y + box_h + 0.5), (x + box_w / 2, mid_y), (first_x, mid_y)],
                    close=False,
                    width=0.35,
                )
                c.arrow(first_x, mid_y, first_x, y + box_h + row_gap - 0.8)
        return Drawing(c.svg(), w, h, problems)

    h = HEIGHT_MM["flow_cycle"]
    c = _Canvas(w, h, v.caption or "cycle")
    box_w, box_h = 34.0, 16.0
    cx, cy = w / 2, h / 2
    rx, ry = w / 2 - box_w / 2 - 1, h / 2 - box_h / 2 - 1
    centres = [
        (cx + rx * math.cos(-math.pi / 2 + 2 * math.pi * i / n), cy + ry * math.sin(-math.pi / 2 + 2 * math.pi * i / n))
        for i in range(n)
    ]
    for i, (bx, by) in enumerate(centres):
        c.rect(bx - box_w / 2, by - box_h / 2, box_w, box_h, fill="#fff")
        if f"step{i}" in hidden:
            _blank_box(c, bx - box_w / 2, by - box_h / 2, box_w, box_h)
        else:
            problems += _box_text(c, bx, by, box_w, v.steps[i], 2, i + 1)
    for i in range(n):
        (x1, y1), (x2, y2) = centres[i], centres[(i + 1) % n]
        c.arrow(x1 + (x2 - x1) * 0.32, y1 + (y2 - y1) * 0.32, x1 + (x2 - x1) * 0.68, y1 + (y2 - y1) * 0.68)
    return Drawing(c.svg(), w, h, problems)


def draw(v, hidden=frozenset()) -> Optional[Drawing]:
    """SVG drawing for a visual spec, or None for tables (printed as HTML tables).

    `hidden` names label slots (see visuals/practice.py) printed as blanks for the child to complete.
    """
    hidden = frozenset(hidden)
    if isinstance(v, Table):
        return None
    if isinstance(v, ShapeSpec):
        return draw_shape(v, hidden)
    if isinstance(v, NumberLineSpec):
        return draw_number_line(v, hidden)
    if isinstance(v, BarModelSpec):
        return draw_bar_model(v, hidden)
    if isinstance(v, FlowSequenceSpec):
        return draw_flow(v, hidden)
    raise TypeError(f"unknown visual type {type(v).__name__}")
