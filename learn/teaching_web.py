"""Standalone, offline web app for the Teaching Engine."""

import hmac
import json
import os
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from jinja2 import Environment, FileSystemLoader, select_autoescape

from .extraction import ExtractionError, choose_ocr, extract, pdf_page_count
from .grounding import InputError, parse_page_range
from .teaching_engine import create_teaching_lesson, extract_facts

MAX_UPLOAD_BYTES = 30 * 1024 * 1024
app = FastAPI(title="Learn Teaching Engine", docs_url=None, redoc_url=None)
_env = Environment(
    loader=FileSystemLoader(str(Path(__file__).parent / "templates")), autoescape=select_autoescape(["j2", "html"])
)
_basic = HTTPBasic(auto_error=False)


def _authorize(credentials: HTTPBasicCredentials | None = Depends(_basic)) -> None:
    if os.getenv("LEARN_REQUIRE_ACCESS") != "1":
        return
    password = os.getenv("LEARN_ACCESS_PASSWORD", "")
    if not password:
        raise HTTPException(503, "Access protection is not configured. Set LEARN_ACCESS_PASSWORD.")
    if credentials is None or not (
        hmac.compare_digest(credentials.username, "learn") and hmac.compare_digest(credentials.password, password)
    ):
        raise HTTPException(
            401,
            "Sign-in required",
            headers={"WWW-Authenticate": "Basic"},
        )


def _page(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_env.get_template(name).render(**ctx))


@app.get("/", response_class=HTMLResponse, dependencies=[Depends(_authorize)])
def index():
    return _page("teaching_upload.html.j2")


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.post("/generate", response_class=HTMLResponse, dependencies=[Depends(_authorize)])
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
    payload = {"lesson": lesson.model_dump(), "source_warnings": source.warnings}
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": 'attachment; filename="teaching_lesson.json"'},
    )
