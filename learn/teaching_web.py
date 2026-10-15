"""Standalone, offline web app for the Teaching Engine."""

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .extraction import ExtractionError, choose_ocr, extract, pdf_page_count
from .grounding import InputError, parse_page_range
from .teaching_engine import create_teaching_lesson, extract_facts, render_teaching_pdf

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
app = FastAPI(title="Learn Teaching Engine", docs_url=None, redoc_url=None)
_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=select_autoescape(["j2", "html"])
)
def _page(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_env.get_template(name).render(**ctx))


@app.get("/", response_class=HTMLResponse)
def index():
    return _page("teaching_upload.html.j2")


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/generate", response_class=HTMLResponse)
def generate(pdf: UploadFile = File(...), pages: str = Form("")):
    data = pdf.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF is larger than 30 MB")
    if not data.startswith(b"%PDF"):
        return _page("teaching_result.html.j2", job=None, error="That file does not appear to be a PDF.", warnings=[])

    try:
        page_range = parse_page_range(pages.strip()[:50], pdf_page_count(data))
        ocr, ocr_name = choose_ocr("auto", None)
        source = extract(data, ocr, ocr_name, page_range)
    except (InputError, ExtractionError) as error:
        return _page("teaching_result.html.j2", job=None, error=str(error), warnings=[])

    if not source.units:
        message = "No readable text was found in the selected pages. Scanned PDFs need OCR before they can be used."
        return _page("teaching_result.html.j2", job=None, error=message, warnings=source.warnings)

    lesson = create_teaching_lesson(extract_facts(source.units))
    pdf_bytes = render_teaching_pdf(lesson, source.warnings)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="learn_teaching_plan.pdf"'},
    )
