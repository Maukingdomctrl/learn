"""Standalone Teaching Engine web app; its optional Commons gallery loads external images."""

from pathlib import Path

import pymupdf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .extraction import ExtractionError, choose_ocr, extract, pdf_page_count
from .grounding import InputError, parse_page_range
from .teaching_engine import create_teaching_lesson, extract_facts, render_printable_cards_pdf, render_teaching_pdf
from .teaching_engine.visual_library import list_visuals

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
# The Detective and Superhero choices are hidden from the upload page, which makes the same cards titled
# "STUDY CARDS"; /generate still makes the games when asked, so turning this back on is the only change needed.
SHOW_GAMES = False
app = FastAPI(title="Learn Teaching Engine", docs_url=None, redoc_url=None)
_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=select_autoescape(["j2", "html"])
)


def _page(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_env.get_template(name).render(**ctx))


@app.get("/", response_class=HTMLResponse)
def index():
    return _page("teaching_upload.html.j2", show_games=SHOW_GAMES)


@app.get("/healthz")
def health():
    return {"status": "ok"}


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
    page_range = parse_page_range(pages.strip()[:50], pdf_page_count(data))
    ocr, ocr_name = choose_ocr("auto", None)
    source = extract(data, ocr, ocr_name, page_range)

    if not source.units:
        raise ValueError(
            "No readable text was found in the selected pages. Scanned PDFs need OCR before they can be used."
        )

    inventory = extract_facts(source.units)
    if output == "lesson":
        lesson = create_teaching_lesson(inventory)
        pdf_bytes = render_teaching_pdf(lesson, source.warnings)
        filename = "learn_teaching_plan.pdf"
    else:
        if output not in {"study", "detective", "superhero"}:
            raise ValueError("Choose study cards, Detective, Superhero, or lesson PDF.")
        try:
            pdf_bytes = render_printable_cards_pdf(
                inventory, source_pdf=data, game_mode=output, pages=page_range, standard=standard
            )
        except ValueError:
            raise
        filename = "learn_study_cards.pdf" if output == "study" else f"learn_{output}_game.pdf"

    return pdf_bytes, filename


def _process_upload(pdf: UploadFile, pages: str, output: str, standard: int, inline: bool) -> Response:
    data = pdf.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF is larger than 30 MB")
    if not data.startswith(b"%PDF"):
        return _page("teaching_result.html.j2", job=None, error="That file does not appear to be a PDF.", warnings=[])

    try:
        pdf_bytes, filename = _build_pdf(data, pages, output, standard)
    except (InputError, ExtractionError, ValueError) as error:
        return _page("teaching_result.html.j2", job=None, error=str(error), warnings=[])

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
