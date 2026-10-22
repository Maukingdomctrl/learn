import re
from collections import OrderedDict
from pathlib import Path

import pymupdf
import pytest
from conftest import ScriptedLLM
from fastapi.testclient import TestClient
from test_evidence_cards import GOOD

import learn.teaching_web as web
from learn.teaching_engine.evidence_cards import TASK


def test_keyless_teaching_web_returns_printable_cards_without_saving_files(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LEARN_OUTPUT_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("JUNE_API_KEY", raising=False)  # no key: the Detective button makes the rule-based case file
    client = TestClient(web.app)

    page = client.get("/").text
    assert "No account or API key needed" in page
    # The page offers the Detective game; Superhero is hidden for now.
    assert "<strong>Detective</strong>" in page and "<strong>Superhero</strong>" not in page
    assert "uperhero" not in re.sub(r"(?s)<script.*?</script>", "", page)  # nor in the page's wording
    assert 'name="output" value="detective" checked' in page
    assert '<dialog class="preview" id="output-preview"' in page
    assert 'aria-haspopup="dialog"' in page
    assert 'aria-controls="output-preview" hidden' in page
    assert 'id="preview-button"' in page
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
    assert "Choose study cards, Detective, Superhero, or lesson PDF." in response.text


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


def test_turning_superhero_back_on_shows_both_games(monkeypatch):
    monkeypatch.setattr(web, "SHOW_SUPERHERO", True)
    page = TestClient(web.app).get("/").text

    assert 'name="output" value="detective" checked' in page and 'name="output" value="superhero"' in page
    assert "Pick Detective or Superhero." in page


def test_turning_the_games_off_makes_plain_study_cards(monkeypatch):
    monkeypatch.setattr(web, "SHOW_GAMES", False)
    page = TestClient(web.app).get("/").text

    assert "<strong>Detective</strong>" not in page and "<strong>Superhero</strong>" not in page
    assert '<input type="hidden" name="output" value="study">' in page


def test_the_page_default_makes_plain_study_cards(sample_pdf):
    client = TestClient(web.app)
    with open(sample_pdf, "rb") as pdf_file:
        response = client.post(
            "/generate", files={"pdf": ("c.pdf", pdf_file, "application/pdf")}, data={"output": "study"}
        )

    assert response.headers["content-disposition"] == 'attachment; filename="learn_study_cards.pdf"'
    text = pymupdf.open(stream=response.content, filetype="pdf")[0].get_text()
    assert text.startswith("STUDY CARDS") and "DETECTIVE" not in text


def test_the_home_page_links_a_blank_card_sheet_drawn_like_the_printed_cards():
    client = TestClient(web.app)

    assert 'href="/blank-cards" download' in client.get("/").text
    response = client.get("/blank-cards")

    assert response.status_code == 200
    assert response.headers["content-disposition"] == 'attachment; filename="learn_blank_study_cards.pdf"'
    document = pymupdf.open(stream=response.content, filetype="pdf")
    cards, answers = document[0].get_text(), document[1].get_text()
    assert document.page_count == 2
    assert "STUDY CARDS" in cards and "BLANK SHEET" in cards
    assert all(str(number) in cards for number in range(1, 9))
    assert "ANSWER SHEET" in answers


def _scanned_pdf(pages: int) -> bytes:
    """Pages that are only a picture of text, as a scanner or phone camera makes them."""
    document = pymupdf.open()
    for _ in range(pages):
        picture = pymupdf.Pixmap(pymupdf.csGRAY, pymupdf.IRect(0, 0, 60, 80), False)
        picture.clear_with(230)
        page = document.new_page()
        page.insert_image(page.rect, pixmap=picture)
    data = document.tobytes()
    document.close()
    return data


def test_scanned_pages_are_read_with_ocr_and_limited_to_what_the_host_can_read_in_time(monkeypatch):
    texts = iter(
        [
            "Rivers carry water from the hills to the sea and shape the land along the way.",
            "The Ganga rises in the Himalayas and flows east to the Bay of Bengal.",
        ]
    )
    monkeypatch.setattr(web, "choose_ocr", lambda setting, llm: (lambda png: next(texts), "fake"))
    monkeypatch.setattr(web, "MAX_SCANNED_PAGES", 2)
    client = TestClient(web.app)

    def upload(pdf: bytes):
        return client.post("/generate", data={"output": "study"}, files={"pdf": ("scan.pdf", pdf, "application/pdf")})

    response = upload(_scanned_pdf(2))
    assert response.headers["content-type"].startswith("application/pdf")
    assert "Ganga" in "".join(page.get_text() for page in pymupdf.open(stream=response.content, filetype="pdf"))

    refused = upload(_scanned_pdf(3))
    assert refused.headers["content-type"].startswith("text/html")
    assert "3 of the selected pages are scanned images, and up to 2 can be read" in refused.text


UK = Path(__file__).parent / "sheets" / "uk-cities-comparative-table.pdf"


@pytest.fixture
def case_model(monkeypatch):
    """The Detective button with a scripted model: good cards for the first sheet, then no more replies."""
    monkeypatch.setattr(web, "_CASE_PAPERS", OrderedDict())
    llm = ScriptedLLM({TASK: [GOOD, {}]})
    made = []

    def model():
        made.append(llm)
        return llm

    monkeypatch.setattr(web, "_case_paper_model", model)
    monkeypatch.setenv("LEARN_DETECTIVE_AI_SHEETS", "1")
    return llm, made


def _post(client, path, pages="1-5"):
    with open(UK, "rb") as pdf_file:
        data = {"output": "detective", "pages": pages}
        return client.post(path, data=data, files={"pdf": ("uk.pdf", pdf_file, "application/pdf")})


@pytest.fixture(autouse=True)
def a_card_model_key(monkeypatch):
    """A model key, so the Detective button tries the (scripted or broken) model; tests that need none unset it."""
    monkeypatch.setenv("LEARN_PROVIDER", "june")
    monkeypatch.setenv("JUNE_API_KEY", "test-key")


def test_the_detective_button_makes_case_papers_when_a_model_is_set(case_model):
    llm, made = case_model
    client = TestClient(web.app)
    preview = _post(client, "/preview")
    download = _post(client, "/generate")

    assert preview.headers["content-disposition"] == 'inline; filename="learn_detective_game.pdf"'
    assert download.headers["content-disposition"] == 'attachment; filename="learn_detective_game.pdf"'
    text = pymupdf.open(stream=download.content, filetype="pdf")[1].get_text()
    assert "River Thames" in text and "Sheet says: p. 1" in text  # the sealed key after the first sheet
    assert download.content == preview.content
    assert len(made) == 1 and len(llm.calls) == 1  # preview then download: the model is asked once


def test_without_a_key_or_past_the_daily_limit_no_model_is_used(monkeypatch):
    monkeypatch.setenv("LEARN_PROVIDER", "google")
    monkeypatch.setenv("JUNE_API_KEY", "a-june-key")
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    assert web._case_paper_model() is None  # the Google provider needs GOOGLE_API_KEY, not June's key
    monkeypatch.setenv("LEARN_PROVIDER", "june")
    monkeypatch.delenv("JUNE_API_KEY", raising=False)
    assert web._case_paper_model() is None
    monkeypatch.setenv("JUNE_API_KEY", "test-key")
    monkeypatch.setenv("LEARN_DETECTIVE_DAILY_LIMIT", "2")
    monkeypatch.setattr(web, "_ai_uploads", {"day": web.date.min, "count": 0})
    assert [web._case_paper_model() is not None for _ in range(3)] == [True, True, False]


def test_a_model_that_writes_no_good_card_gives_the_rule_based_case_file(monkeypatch):
    monkeypatch.setattr(web, "_CASE_PAPERS", OrderedDict())
    broken = {"cards": [{**c, "answer": "Paris"} for c in GOOD["cards"]]}
    monkeypatch.setattr(web, "_case_paper_model", lambda: ScriptedLLM({TASK: [broken, broken, {}]}))
    monkeypatch.setenv("LEARN_DETECTIVE_AI_SHEETS", "1")
    response = _post(TestClient(web.app), "/generate")

    assert "DETECTIVE CASE FILE" in "\n".join(page.get_text() for page in pymupdf.open(stream=response.content))


def test_a_broken_model_setup_gives_the_rule_based_case_file_not_an_error_page(monkeypatch):
    def broken():
        raise ModuleNotFoundError("No module named 'httpx'")  # what the live site hit

    monkeypatch.setattr(web, "_CASE_PAPERS", OrderedDict())
    monkeypatch.setattr(web, "_case_paper_model", broken)
    response = _post(TestClient(web.app), "/preview")

    assert response.status_code == 200
    assert "DETECTIVE CASE FILE" in "\n".join(page.get_text() for page in pymupdf.open(stream=response.content))


def test_the_site_installs_every_package_the_card_models_import():
    """The Render image installs only requirements-teaching.txt, so the model clients' imports must be in it."""
    pinned = {
        line.split("==")[0].strip().lower()
        for line in (Path(__file__).parent.parent / "requirements-teaching.txt").read_text().splitlines()
        if line and not line.startswith("#")
    }
    source = (Path(__file__).parent.parent / "learn" / "llm.py").read_text()
    imported = set(re.findall(r"^[ \t]+import (\w+)$", source, re.M))  # the clients import their packages lazily
    assert imported and imported <= pinned, f"missing from requirements-teaching.txt: {imported - pinned}"


def _text(response) -> str:
    return "\n".join(page.get_text() for page in pymupdf.open(stream=response.content))


def test_detective_takes_up_to_five_pages_and_says_why_before_any_model_call(case_model):
    llm, made = case_model
    response = _post(TestClient(web.app), "/preview", pages="")  # the UK sheet has 6 pages

    assert "up to 5 pages at a time" in response.headers["x-learn-error"] and "1-5" in response.headers["x-learn-error"]
    assert not made and not llm.calls  # no tokens spent
    assert _post(TestClient(web.app), "/preview", pages="2-6").headers["content-type"] == "application/pdf"
    page = TestClient(web.app).get("/").text
    assert "Detective works on up to 5 pages at a time." in page and 'headers.get("x-learn-error")' in page


def test_the_parent_is_told_when_the_story_cards_could_not_be_made(monkeypatch, capsys):
    monkeypatch.setattr(web, "_CASE_PAPERS", OrderedDict())
    monkeypatch.setattr(web, "_case_paper_model", lambda: None)  # today's uploads are used up
    assert "Today's AI story cards are used up" in _text(_post(TestClient(web.app), "/preview"))
    assert "Detective upload: daily limit reached" in capsys.readouterr().out

    broken = {"cards": [{**c, "answer": "Paris"} for c in GOOD["cards"]]}
    monkeypatch.setattr(web, "_case_paper_model", lambda: ScriptedLLM({TASK: [broken, broken, {}]}))
    assert "The AI could not write story cards just now" in _text(_post(TestClient(web.app), "/preview"))
    assert "0/" in capsys.readouterr().out  # the log says no card came from the model

    monkeypatch.delenv("JUNE_API_KEY")  # no model set up at all: the plain cards, with no note
    assert "story cards" not in _text(_post(TestClient(web.app), "/preview"))


def test_each_detective_upload_logs_what_the_model_did(case_model, capsys):
    _post(TestClient(web.app), "/preview")
    line = capsys.readouterr().out
    assert "Detective upload: 8/" in line and "cards by AI" in line and "calls" in line and "tokens" in line
