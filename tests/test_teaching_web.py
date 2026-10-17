import pymupdf
import pytest
from fastapi.testclient import TestClient

import learn.teaching_web as web


def test_keyless_teaching_web_returns_printable_cards_without_saving_files(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LEARN_OUTPUT_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = TestClient(web.app)

    page = client.get("/").text
    assert "No account or API key needed" in page
    assert "<strong>Detective</strong>" in page
    assert "<strong>Superhero</strong>" in page
    assert '<dialog class="preview" id="output-preview"' in page
    assert 'aria-haspopup="dialog"' in page
    assert 'aria-controls="output-preview" hidden' in page
    assert 'id="preview-button"' in page
    assert 'name="output" value="detective" checked' in page
    assert 'name="output" value="superhero"' in page
    assert "Study Visual Library" in page
    assert "Preview before printing" in page
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post("/generate", files={"pdf": ("curriculum.pdf", pdf_file, "application/pdf")})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == 'attachment; filename="learn_detective_game.pdf"'
    document = pymupdf.open(stream=response.content, filetype="pdf")
    assert document.page_count >= 2
    pdf_text = "\n".join(page.get_text() for page in document)
    assert "DETECTIVE CASE FILE" in pdf_text
    assert "ANSWER SHEET" in document[-1].get_text()
    assert "p. 1" in document[-1].get_text()
    assert list(tmp_path.iterdir()) == []


def test_teaching_web_builds_selected_superhero_mode(sample_pdf):
    client = TestClient(web.app)
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post(
            "/generate",
            data={"output": "superhero", "standard": "9"},
            files={"pdf": ("curriculum.pdf", pdf_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="learn_superhero_game.pdf"'
    document = pymupdf.open(stream=response.content, filetype="pdf")
    text = "\n".join(page.get_text() for page in document)
    assert "SUPERHERO POWER-UP GAME" in text
    assert "ICSE STANDARD" not in text
    assert "TURN OVER TO CHECK" not in text


@pytest.mark.parametrize("output", ["detective", "superhero"])
def test_preview_endpoint_returns_the_selected_game_pdf_inline(sample_pdf, output):
    client = TestClient(web.app)
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post(
            "/preview",
            data={"output": output, "standard": "8"},
            files={"pdf": ("curriculum.pdf", pdf_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == f'inline; filename="learn_{output}_game.pdf"'
    document = pymupdf.open(stream=response.content, filetype="pdf")
    game_title = "DETECTIVE CASE FILE" if output == "detective" else "SUPERHERO POWER-UP GAME"
    assert game_title in "\n".join(page.get_text() for page in document)


def test_teaching_web_keeps_lesson_pdf_as_an_option(sample_pdf):
    client = TestClient(web.app)
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post(
            "/generate",
            data={"output": "lesson"},
            files={"pdf": ("curriculum.pdf", pdf_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="learn_teaching_plan.pdf"'
    document = pymupdf.open(stream=response.content, filetype="pdf")
    assert "IDEA 1" in document[0].get_text()


def test_teaching_web_rejects_unknown_game_mode(sample_pdf):
    client = TestClient(web.app)
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post(
            "/generate",
            data={"output": "not-a-game"},
            files={"pdf": ("curriculum.pdf", pdf_file, "application/pdf")},
        )

    assert response.status_code == 200
    assert "Choose Detective, Superhero, or lesson PDF." in response.text


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


def test_teaching_web_does_not_require_credentials(monkeypatch):
    monkeypatch.setenv("LEARN_REQUIRE_ACCESS", "1")
    monkeypatch.setenv("LEARN_ACCESS_PASSWORD", "test-secret")
    client = TestClient(web.app)

    assert client.get("/").status_code == 200


def test_teaching_web_rejects_its_own_generated_card_pdf():
    document = pymupdf.open()
    document.new_page()
    document.set_metadata({"title": "Learn ICSE Standard 8 detective game", "author": "Learn Teaching Engine"})
    generated_pdf = document.tobytes()
    document.close()

    with pytest.raises(ValueError, match="already a Learn-generated card PDF"):
        web._build_pdf(generated_pdf, "", "detective", 8)
