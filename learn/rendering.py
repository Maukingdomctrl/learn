"""Render student pages and the answer key to PDF (pipeline step 7) and measure the layout for D6.

HTML/CSS templates are printed with headless Chromium through Playwright. Layout measurements are taken
from the same browser page that produced the PDF; page count and size come from the PDF files themselves.
"""
import glob
import math
import os
import re
import string
from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from pypdf import PdfReader

from . import config as C
from .grounding import SourceIndex
from .models import Lesson, Stage
from .textutil import has_blank, written_words
from .timing import LessonTiming

TEMPLATES = Path(__file__).parent / "templates"
STAGE_TITLES = {"Discover": "Discover", "Reinforce": "Practise", "Vary": "Try it another way",
                "Apply": "Use it", "Recall": "Memory check"}
PX_PER_MM = 96 / 25.4
_BLANK_RE = re.compile(r"_{3,}")

WRITTEN_TYPES = {"SPOT_MISTAKE", "SHORT_ANSWER"}


class RenderError(Exception):
    pass


@dataclass
class RenderResult:
    student_pdf: str
    key_pdf: str
    layout: dict = field(default_factory=dict)
    student_pages: list[tuple[float, float]] = field(default_factory=list)  # (width_pt, height_pt)
    key_pages: list[tuple[float, float]] = field(default_factory=list)
    student_text: str = ""
    key_text: str = ""


def required_lines(lesson: Lesson, stage: Stage, number: int) -> int:
    """Section 7.2: at least 1 ruled line per 8 expected written words, plus 1 spare line."""
    if stage.activity_type not in WRITTEN_TYPES:
        return 0
    entry = lesson.key_for(number)
    words = max(1, written_words(entry.answer) if entry else 1)
    return math.ceil(words / C.WORDS_PER_LINE) + 1


def blank_width_mm(lesson: Lesson, number: int) -> int:
    """Inline blank for FILL_IN / COMPLETE_STEPS: 30 mm, widened ~11 mm per expected written word."""
    entry = lesson.key_for(number)
    words = written_words(entry.answer) if entry else 0
    return int(min(120, max(30, 11 * words)))


def group_letter(stage: Stage, group: str) -> str:
    for i, g in enumerate(stage.groups):
        if g.strip().lower() == group.strip().lower():
            return string.ascii_uppercase[i % 26]
    return "?"


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(["j2", "html"]))

    def replace_blanks(text, width=30):
        return Markup(_BLANK_RE.sub(f'<span class="blank" style="width:{width}mm"></span>', str(text)))

    def fill_blank(text, answer):
        filled = f'<u>&nbsp;{Markup.escape(answer)}&nbsp;</u>'
        out = _BLANK_RE.sub(filled, str(text), count=1)
        return Markup(out if out != str(text) else f"{text} &rarr; {filled}")

    env.filters["replace_blanks"] = replace_blanks
    env.filters["fill_blank"] = fill_blank
    env.tests["has_blank"] = has_blank
    return env


def student_html(lesson: Lesson) -> str:
    stages = {s.stage: s for s in lesson.stages}
    missing = [n for n in C.STAGES if n not in stages]
    if missing:
        raise RenderError(f"cannot render: missing stages {missing}")
    req = {i.number: required_lines(lesson, s, i.number) for s, i in lesson.items()}
    blanks = {i.number: blank_width_mm(lesson, i.number) for _, i in lesson.items()}
    return _env().get_template("student.html.j2").render(
        lesson=lesson, stages=stages, stage_titles=STAGE_TITLES, req_lines=req, blank_mm=blanks,
        recall_banner=C.RECALL_BANNER, margin=C.MARGIN_MM, group_letter=group_letter,
        letters=string.ascii_uppercase * 2,
    )


def key_rows(lesson: Lesson, index: SourceIndex) -> list[dict]:
    rows = []
    for stage, item in lesson.items():
        entry = lesson.key_for(item.number)
        if entry is None:
            continue
        answer = entry.answer
        letters = string.ascii_uppercase
        if stage.activity_type == "CHOOSE" and answer in item.options:
            answer = f"{letters[item.options.index(answer) % 26]}. {answer}"
        elif stage.activity_type == "MATCH" and answer in stage.options:
            answer = f"{letters[stage.options.index(answer) % 26]}. {answer}"
        elif stage.activity_type == "SORT":
            answer = f"{group_letter(stage, answer)} ({answer})"
        elif stage.activity_type == "SPOT_MISTAKE" and item.peer_work:
            answer = f"Step {item.peer_work.mistake_step} is wrong. Correct: {answer}"
        pages = index.pages(entry.source_unit_ids)
        rows.append({
            "number": item.number, "answer": answer,
            "alternatives": "; ".join(entry.accepted_alternatives) or "-",
            "reason": entry.reason,
            "source": ("p. " + ", ".join(map(str, pages))) if pages else "-",
        })
    return rows


def key_html(lesson: Lesson, index: SourceIndex, timing: LessonTiming, warnings: list[str]) -> str:
    cited = [i for c in lesson.core_claims for i in c.source_unit_ids]
    cited += [i for e in lesson.answer_key.entries for i in e.source_unit_ids]
    pages = index.pages(cited)
    return _env().get_template("key.html.j2").render(
        lesson=lesson, rows=key_rows(lesson, index), margin=C.MARGIN_MM,
        concepts=", ".join(c.name for c in lesson.concepts),
        source_pages=", ".join(map(str, pages)) or "-",
        minutes=max(1, round(timing.t_lesson / 60)), warnings=warnings,
    )


MEASURE_JS = """
() => {
  const mm = v => v / %(pxmm)f;
  const out = {overflow: [], pages: document.querySelectorAll('.page').length};
  document.querySelectorAll('.page, .col').forEach(el => {
    if (el.scrollHeight > el.clientHeight + 1 || el.scrollWidth > el.clientWidth + 1) {
      const used = mm(el.scrollHeight).toFixed(0), room = mm(el.clientHeight).toFixed(0);
      out.overflow.push((el.dataset.zone || el.id) + ` (content ${used}mm in ${room}mm)`);
    }
  });
  let minFont = 1e9;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode;
    if (!n.textContent.trim()) continue;
    const fs = parseFloat(getComputedStyle(n.parentElement).fontSize);
    if (fs < minFont) minFont = fs;
  }
  out.min_font_pt = minFont * 0.75;
  const heights = sel => Array.from(document.querySelectorAll(sel)).map(e => mm(e.getBoundingClientRect().height));
  const widths = sel => Array.from(document.querySelectorAll(sel)).map(e => mm(e.getBoundingClientRect().width));
  out.line_heights_mm = heights('.write-line, .stem-line');
  out.line_lengths_mm = widths('.write-line, .stem-line');
  out.num_blank_mm = widths('.num-blank');
  out.solve_mm = heights('.workspace');
  out.items_lines = Array.from(document.querySelectorAll('.item[data-required-lines]')).map(e => ({
    item: +e.dataset.item, required: +e.dataset.requiredLines,
    found: e.querySelectorAll('.write-line, .stem-line').length}));
  const page2 = document.getElementById('page2');
  const box = document.getElementById('recall-box');
  out.recall_on_page2 = !!(box && page2 && page2.contains(box));
  out.recall_banner = !!document.getElementById('recall-banner');
  out.hints = Array.from(document.querySelectorAll('[data-hint]')).map(e => e.dataset.hint);
  const p = page2 ? page2.getBoundingClientRect() : null;
  if (box && p) {
    const b = box.getBoundingClientRect();
    out.recall_bottom_right = (b.left - p.left) > (p.width / 2 - 1) && (b.top - p.top) > (p.height / 3);
  }
  return out;
}
""" % {"pxmm": PX_PER_MM}


def _chromium(playwright):
    try:
        return playwright.chromium.launch()
    except Exception as first:
        candidates = [os.environ.get("CHROMIUM_EXECUTABLE", "")]
        candidates += sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"), reverse=True)
        for exe in candidates:
            if exe and os.path.exists(exe):
                return playwright.chromium.launch(executable_path=exe)
        raise RenderError(f"cannot start Chromium: {first}. Run 'playwright install chromium' "
                          "or set CHROMIUM_EXECUTABLE.") from first


def _pdf_info(path: str) -> tuple[list[tuple[float, float]], str]:
    reader = PdfReader(path)
    pages = [(float(p.mediabox.width), float(p.mediabox.height)) for p in reader.pages]
    text = "\n".join(p.extract_text() or "" for p in reader.pages)
    return pages, text


def render(lesson: Lesson, index: SourceIndex, timing: LessonTiming, workdir: str,
           warnings: list[str] | None = None) -> RenderResult:
    from playwright.sync_api import sync_playwright

    os.makedirs(workdir, exist_ok=True)
    student_path = os.path.join(workdir, "student.pdf")
    key_path = os.path.join(workdir, "answer_key.pdf")
    s_html = student_html(lesson)
    k_html = key_html(lesson, index, timing, warnings or [])
    with open(os.path.join(workdir, "student.html"), "w") as f:
        f.write(s_html)
    with open(os.path.join(workdir, "answer_key.html"), "w") as f:
        f.write(k_html)

    with sync_playwright() as p:
        browser = _chromium(p)
        try:
            page = browser.new_page(viewport={"width": 1123, "height": 794})
            page.emulate_media(media="print")
            page.set_content(s_html, wait_until="load")
            layout = page.evaluate(MEASURE_JS)
            page.pdf(path=student_path, prefer_css_page_size=True, print_background=True)
            kpage = browser.new_page()
            kpage.set_content(k_html, wait_until="load")
            kpage.pdf(path=key_path, prefer_css_page_size=True, print_background=True)
        finally:
            browser.close()

    s_pages, s_text = _pdf_info(student_path)
    k_pages, k_text = _pdf_info(key_path)
    return RenderResult(student_pdf=student_path, key_pdf=key_path, layout=layout,
                        student_pages=s_pages, key_pages=k_pages, student_text=s_text, key_text=k_text)
