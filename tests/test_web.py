from fastapi.testclient import TestClient

import learn.web as web
from tests.test_pipeline import responses


def test_upload_flow(sample_pdf, tmp_path, monkeypatch, scripted):
    monkeypatch.setenv("LEARN_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(web, "make_llm", lambda: (scripted(responses()), ""))
    client = TestClient(web.app)
    assert "Standard 8" in client.get("/").text
    with open(sample_pdf, "rb") as f:
        r = client.post("/generate", data={"standard": "7"}, files={"pdf": ("c.pdf", f, "application/pdf")})
    assert r.status_code == 200 and "Download student lesson" in r.text
    link = r.text.split('href="/jobs/')[1].split('"')[0]
    pdf = client.get("/jobs/" + link)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get("/jobs/" + link.split("/")[0] + "/work/student.pdf").status_code == 404


def test_rejects_non_pdf_and_bad_standard(tmp_path, monkeypatch):
    monkeypatch.setenv("LEARN_OUTPUT_DIR", str(tmp_path))
    client = TestClient(web.app)
    r = client.post("/generate", data={"standard": "7"}, files={"pdf": ("x.pdf", b"hello", "application/pdf")})
    assert "not a PDF" in r.text
    r = client.post("/generate", data={"standard": "9"}, files={"pdf": ("x.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 400
