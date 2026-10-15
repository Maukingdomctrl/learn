"""Minimal local web UI: upload a PDF, pick Standard 7/8, get validated PDFs or a limitation report.

Run with: uvicorn learn.web:app
No accounts or database: each request writes to its own folder under LEARN_OUTPUT_DIR.
"""
import os
import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape

from . import config as C
from .cli import make_llm
from .pipeline import run, save_report

C.load_dotenv()
MAX_UPLOAD_BYTES = 30 * 1024 * 1024
app = FastAPI(title="Learn V1")
_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
                   autoescape=select_autoescape(["j2", "html"]))
_JOB_RE = re.compile(r"^[0-9a-f]{32}$")


def _page(name: str, **ctx) -> HTMLResponse:
    return HTMLResponse(_env.get_template(name).render(**ctx))


@app.get("/", response_class=HTMLResponse)
def index():
    return _page("upload.html.j2")


@app.post("/generate", response_class=HTMLResponse)
def generate(request: Request, pdf: UploadFile = File(...), standard: int = Form(...),
             topic: str = Form(""), pages: str = Form("")):
    if standard not in (7, 8):
        raise HTTPException(400, "Standard must be 7 or 8")
    data = pdf.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "PDF is larger than 30 MB")
    if not data.startswith(b"%PDF"):
        return _page("result.html.j2", report=None, error="The uploaded file is not a PDF.")
    job = uuid.uuid4().hex
    out = os.path.join(C.output_dir(), job)
    os.makedirs(out, exist_ok=True)
    src = os.path.join(out, "source.pdf")
    with open(src, "wb") as f:
        f.write(data)
    llm, _ = make_llm()
    report = run(src, standard, llm, out, topic=topic.strip()[:200], page_range=pages.strip()[:50])
    save_report(report, out)
    return _page("result.html.j2", report=report, job=job, error=None)


@app.get("/jobs/{job}/{name}")
def download(job: str, name: str):
    files = {"student_lesson.pdf", "parent_answer_key.pdf"}
    if not _JOB_RE.match(job) or name not in files:
        raise HTTPException(404)
    path = os.path.join(C.output_dir(), job, "deliver", name)  # only validated, delivered files are served
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path, media_type="application/pdf", filename=name)
