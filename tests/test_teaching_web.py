import json

from fastapi.testclient import TestClient

import learn.teaching_web as web


def test_keyless_teaching_web_returns_plan_without_saving_files(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LEARN_OUTPUT_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(web.app)

    assert "No account, API key, or paid AI call" in client.get("/").text
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post("/generate", files={"pdf": ("curriculum.pdf", pdf_file, "application/pdf")})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.headers["content-disposition"] == 'attachment; filename="teaching_lesson.json"'
    assert json.loads(response.text)["lesson"]["topics"]
    assert list(tmp_path.iterdir()) == []


def test_teaching_web_rejects_bad_file_and_page_range(sample_pdf):
    client = TestClient(web.app)
    response = client.post("/generate", files={"pdf": ("bad.pdf", b"not a pdf", "application/pdf")})
    assert "does not appear to be a PDF" in response.text

    with open(sample_pdf, "rb") as source_file:
        response = client.post(
            "/generate",
            data={"pages": "1-999"},
            files={"pdf": ("input.pdf", source_file, "application/pdf")},
        )
    assert "outside the PDF" in response.text


def test_teaching_web_requires_password_when_deployed(monkeypatch):
    monkeypatch.setenv("LEARN_REQUIRE_ACCESS", "1")
    monkeypatch.setenv("LEARN_ACCESS_PASSWORD", "test-secret")
    client = TestClient(web.app)

    assert client.get("/").status_code == 401
    assert client.get("/", auth=("learn", "wrong-secret")).status_code == 401
    assert client.get("/", auth=("learn", "test-secret")).status_code == 200


def test_teaching_web_fails_closed_if_deployed_password_missing(monkeypatch):
    monkeypatch.setenv("LEARN_REQUIRE_ACCESS", "1")
    monkeypatch.delenv("LEARN_ACCESS_PASSWORD", raising=False)

    assert TestClient(web.app).get("/").status_code == 503
