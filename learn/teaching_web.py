"""Standalone Teaching Engine web app; its optional Commons gallery loads external images."""

import hashlib
import threading
import time
from collections import OrderedDict
from datetime import date
from pathlib import Path

import pymupdf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config as C
from .extraction import MIN_PAGE_CHARS, ExtractionError, choose_ocr, extract, pdf_page_count
from .grounding import InputError, parse_page_range
from .teaching_engine import create_teaching_lesson, extract_facts, render_printable_cards_pdf, render_teaching_pdf
from .teaching_engine.cards import render_blank_cards_pdf
from .teaching_engine.evidence_cards import render_case_papers_pdf, write_case_papers
from .teaching_engine.sheet import read_sheet
from .teaching_engine.visual_library import list_visuals

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
# Reading a scanned page (OCR) takes several seconds on the free host; more than this would pass the browser's
# two-minute wait. Pages with their own text are not counted.
MAX_SCANNED_PAGES = 8
# The upload page offers the Detective and Superhero games. With this off it hides them and makes the same cards
# titled "STUDY CARDS"; /generate still makes the games when asked.
SHOW_GAMES = True
# The Superhero game is hidden from the page for now; /generate still makes it when asked.
SHOW_SUPERHERO = False
# Detective case papers already made, by upload: "Preview" then "Create" for the same PDF costs one set of model calls.
_CASE_PAPERS: OrderedDict[str, bytes] = OrderedDict()
_CASE_PAPERS_KEPT = 16
_ai_uploads = {"day": date.min, "count": 0}
_lock = threading.Lock()
app = FastAPI(title="Learn Teaching Engine", docs_url=None, redoc_url=None)
_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=select_autoescape(["j2", "html"])
)


def _page(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_env.get_template(name).render(**ctx))


@app.get("/", response_class=HTMLResponse)
def index():
    return _page(
        "teaching_upload.html.j2",
        show_games=SHOW_GAMES,
        show_superhero=SHOW_SUPERHERO,
        detective_max_pages=C.detective_max_pages(),
    )


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/blank-cards")
def blank_cards():
    """An empty sheet of study cards, drawn like the printed ones, to fill in by hand."""
    return Response(
        content=render_blank_cards_pdf(),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="learn_blank_study_cards.pdf"'},
    )


@app.get("/library", response_class=HTMLResponse)
def visual_library(region: str = "all"):
    if region not in {"all", "Indian Studies", "UK comparison"}:
        region = "all"
    return _page("visual_library.html.j2", visuals=list_visuals(region))


def _build_pdf(data: bytes, pages: str, output: str, standard: int) -> tuple[bytes, str]:
    with pymupdf.open(stream=data, filetype="pdf") as document:
        metadata = document.metadata or {}
    if metadata.get("author") == "Learn Teaching Engine" and (metadata.get("title") or "").startswith(
        "Learn ICSE Standard"
    ):
        raise ValueError("This is already a Learn-generated card PDF. Upload the original curriculum PDF instead.")
    page_count = pdf_page_count(data)
    page_range = parse_page_range(pages.strip()[:50], page_count)
    chosen, most = len(page_range) if page_range else page_count, C.detective_max_pages()
    if output == "detective" and chosen > most:
        raise ValueError(
            f"Detective works on up to {most} pages at a time, so your cards are ready in about a minute. "
            f"You chose {chosen} pages: pick up to {most}, for example 1-{most}, then make the next {most} after."
        )
    ocr, ocr_name = choose_ocr("auto", None)
    if ocr is not None and len(scanned := _scanned_pages(data, page_range)) > MAX_SCANNED_PAGES:
        raise ValueError(
            f"{len(scanned)} of the selected pages are scanned images, and up to {MAX_SCANNED_PAGES} can be read "
            f"at a time. Choose fewer pages, for example {scanned[0]}-{scanned[MAX_SCANNED_PAGES - 1]}."
        )
    source = extract(data, ocr, ocr_name, page_range)

    if not source.units:
        raise ValueError(
            "No readable text was found in the selected pages. Scanned PDFs need OCR before they can be used."
        )

    inventory = extract_facts(source.units)
    notes: tuple[str, ...] = ()
    if output == "detective":
        pdf_bytes, note = _case_papers(data, inventory, page_range, standard)
        if pdf_bytes:
            return pdf_bytes, "learn_detective_game.pdf"
        notes = (note,) if note else ()
    if output == "lesson":
        lesson = create_teaching_lesson(inventory)
        pdf_bytes = render_teaching_pdf(lesson, source.warnings)
        filename = "learn_teaching_plan.pdf"
    else:
        if output not in {"study", "detective", "superhero"}:
            raise ValueError("Choose study cards, Detective, Superhero, or lesson PDF.")
        try:
            pdf_bytes = render_printable_cards_pdf(
                inventory, source_pdf=data, game_mode=output, pages=page_range, standard=standard, notes=notes
            )
        except ValueError:
            raise
        filename = "learn_study_cards.pdf" if output == "study" else f"learn_{output}_game.pdf"

    return pdf_bytes, filename


def _case_paper_model():
    """The model for Detective case papers, or None when no key is set or today's uploads are used up."""
    if not C.env(C.card_key_name()):
        return None
    with _lock:
        if _ai_uploads["day"] != date.today():
            _ai_uploads.update(day=date.today(), count=0)
        if _ai_uploads["count"] >= C.detective_daily_limit():
            return None
        _ai_uploads["count"] += 1
    from .llm import card_llm

    return card_llm(C.evidence_effort())


# Printed on the rule-based case file when the story cards could not be made, so a parent knows why.
BUSY_NOTE = (
    "The AI could not write story cards just now, so these are the basic Detective cards. Try again in a few minutes."
)
LIMIT_NOTE = "Today's AI story cards are used up, so these are the basic Detective cards. Try again tomorrow."


def _case_papers(data: bytes, inventory, page_range: set[int] | None, standard: int) -> tuple[bytes | None, str]:
    """Detective case papers written by the model, or None and a note for the parent to make the rule-based case
    file instead. Every upload logs one line for the site's owner.

    The same upload is answered from memory, so previewing and then downloading calls the model once.
    """
    key = hashlib.sha256(data + repr((sorted(page_range or ()), standard)).encode()).hexdigest()
    with _lock:
        if key in _CASE_PAPERS:
            _CASE_PAPERS.move_to_end(key)
            return _CASE_PAPERS[key], ""
    if not C.env(C.card_key_name()):
        return None, ""  # no model is set up: the site makes its rule-based cards, as it always has
    start = time.monotonic()
    llm = None
    try:
        llm = _case_paper_model()
        if llm is None:
            _log("daily limit reached", llm, start)
            return None, LIMIT_NOTE
        sheet = read_sheet(inventory, data, page_range)
        papers = write_case_papers(sheet, llm, standard, C.detective_ai_sheets(), C.detective_workers())
    except ValueError:  # no lines to write cards from; the rule-based path says why
        return None, ""
    except Exception as error:  # noqa: BLE001 - a broken model setup must not crash the page
        _log(f"failed ({type(error).__name__}: {error})", llm, start)
        return None, BUSY_NOTE
    cards = sum(len(cards) for cards in papers.sheets)
    outcome = f"{papers.model_cards}/{cards} cards by AI on {len(papers.sheets)} sheets"
    _log(outcome + "".join(f"; {note}" for note in papers.notes), llm, start)
    if not papers.model_cards:  # the model was unreachable or broke every rule: the rule-based case file is better
        return None, BUSY_NOTE
    pdf_bytes = render_case_papers_pdf(papers)
    with _lock:
        _CASE_PAPERS[key] = pdf_bytes
        while len(_CASE_PAPERS) > _CASE_PAPERS_KEPT:
            _CASE_PAPERS.popitem(last=False)
    return pdf_bytes, ""


def _log(outcome: str, llm, start: float) -> None:
    """One line per Detective upload in the server log: what the model did, its tokens, and how long it took."""
    calls = getattr(llm, "call_log", [])
    tokens_in = sum(call.get("input_tokens") or 0 for call in calls)
    tokens_out = sum(call.get("output_tokens") or 0 for call in calls)
    model = getattr(llm, "model", "-")
    print(
        f"Detective upload: {outcome} | {model}, {len(calls)} calls, {tokens_in} in / {tokens_out} out tokens, "
        f"{time.monotonic() - start:.0f}s",
        flush=True,
    )


def _scanned_pages(data: bytes, page_range: set[int] | None) -> list[int]:
    """The selected pages with almost no text of their own, which only OCR can read."""
    with pymupdf.open(stream=data, filetype="pdf") as document:
        return [
            page.number + 1
            for page in document
            if (page_range is None or page.number + 1 in page_range) and len(page.get_text().strip()) < MIN_PAGE_CHARS
        ]


def _process_upload(pdf: UploadFile, pages: str, output: str, standard: int, inline: bool) -> Response:
    data = pdf.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF is larger than 30 MB")
    if not data.startswith(b"%PDF"):
        return _page("teaching_result.html.j2", job=None, error="That file does not appear to be a PDF.", warnings=[])

    try:
        pdf_bytes, filename = _build_pdf(data, pages, output, standard)
    except (InputError, ExtractionError, ValueError) as error:
        page = _page("teaching_result.html.j2", job=None, error=str(error), warnings=[])
        # The preview reads the reason from this header, so the parent sees it instead of a generic message.
        page.headers["X-Learn-Error"] = str(error).replace("–", "-").encode("latin-1", "replace").decode("latin-1")
        return page

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'{"inline" if inline else "attachment"}; filename="{filename}"'},
    )


@app.post("/generate", response_class=HTMLResponse)
def generate(
    pdf: UploadFile = File(...),
    pages: str = Form(""),
    output: str = Form("detective"),
    standard: int = Form(8),
):
    return _process_upload(pdf, pages, output, standard, inline=False)


@app.post("/preview", response_class=HTMLResponse)
def preview(
    pdf: UploadFile = File(...),
    pages: str = Form(""),
    output: str = Form("detective"),
    standard: int = Form(8),
):
    return _process_upload(pdf, pages, output, standard, inline=True)
