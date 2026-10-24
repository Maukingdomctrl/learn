import re
import threading
from collections import OrderedDict
from concurrent.futures import Future
from pathlib import Path

import pymupdf
import pytest
from conftest import ScriptedLLM
from fastapi.testclient import TestClient
from test_evidence_cards import GOOD

import learn.teaching_web as web
from learn.llm import LLMError
from learn.teaching_engine.cards import GAP
from learn.teaching_engine.evidence_cards import TASK


def test_keyless_teaching_web_returns_printable_cards_without_saving_files(sample_pdf, tmp_path, monkeypatch):
    monkeypatch.setenv("LEARN_OUTPUT_DIR", str(tmp_path))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("JUNE_API_KEY", raising=False)  # no key: the Detective button makes the rule-based case file
    client = TestClient(web.app)

    page = client.get("/").text
    assert "No account or API key needed" in page
    # The page offers the Detective game and Key Facts, Detective first; Superhero is hidden for now.
    assert "<strong>Detective</strong>" in page and "<strong>Superhero</strong>" not in page
    assert "uperhero" not in re.sub(r"(?s)<script.*?</script>", "", page)  # nor in the page's wording
    assert 'name="output" value="detective" checked' in page and 'name="output" value="facts"' in page
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
    assert "Choose study cards, Detective, Superhero, Key Facts, or lesson PDF." in response.text


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
    monkeypatch.setattr(web, "_WRITING", {})
    llm = ScriptedLLM({TASK: [GOOD, {}]})
    made = []

    def model():
        made.append(llm)
        return llm

    monkeypatch.setattr(web, "_case_paper_model", model)
    return llm, made


def _post(client, path, pages="1-5"):
    with open(UK, "rb") as pdf_file:
        data = {"output": "detective", "pages": pages}
        return client.post(path, data=data, files={"pdf": ("uk.pdf", pdf_file, "application/pdf")})


_REAL_MODEL = web._case_paper_model  # builds a model client; only its key and daily-limit rules are tested


class _NoNetwork:
    """Stands in for the card model: tests never reach a real model, which would need a network and spend credits."""

    def json(self, task, system, prompt):
        raise LLMError("no model in tests")


@pytest.fixture(autouse=True)
def a_card_model_key(monkeypatch):
    """A model key, so the Detective button tries a model; tests that need none unset it. The model itself is a
    fake that fails at once, unless a test sets its own scripted model."""
    monkeypatch.setenv("LEARN_PROVIDER", "june")
    monkeypatch.setenv("JUNE_API_KEY", "test-key")
    monkeypatch.setattr(web, "_case_paper_model", lambda: _NoNetwork())


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
    assert len(made) == 1 and len(llm.calls) == 1  # one request for the 5-page upload, then served from memory


def test_an_upload_sent_again_while_its_cards_are_written_waits_for_that_model_call(case_model, monkeypatch):
    """A parent closes the preview while it is still building and clicks Create: the site still pays for one call."""
    llm, made = case_model
    called, waiting, release = threading.Event(), threading.Event(), threading.Event()
    scripted = llm.json

    def slow_json(task, system, prompt):
        called.set()
        release.wait(5)
        return scripted(task, system, prompt)

    class Watched(Future):
        def result(self, timeout=None):
            waiting.set()  # the second upload is waiting for the first one's cards
            return super().result(timeout)

    monkeypatch.setattr(llm, "json", slow_json)
    monkeypatch.setattr(web, "Future", Watched)
    got = {}
    preview = threading.Thread(target=lambda: got.update(preview=_post(TestClient(web.app), "/preview")), daemon=True)
    create = threading.Thread(target=lambda: got.update(create=_post(TestClient(web.app), "/generate")), daemon=True)
    preview.start()
    assert called.wait(5)
    create.start()
    waited = waiting.wait(5)
    release.set()
    preview.join(10)
    create.join(10)

    assert waited and len(made) == 1 and len(llm.calls) == 1
    assert got["create"].content == got["preview"].content and "River Thames" in _text(got["create"])


def test_only_an_upload_over_the_lines_per_request_setting_is_split(case_model, monkeypatch):
    llm, made = case_model
    llm.responses[TASK] = lambda prompt, _: GOOD if "\nF1 [" in prompt else {}
    monkeypatch.setenv("LEARN_DETECTIVE_LINES_PER_REQUEST", "20")
    response = _post(TestClient(web.app), "/preview")  # the UK sheet's first 5 pages have 40 lines

    assert response.headers["content-type"] == "application/pdf" and len(llm.calls) == 2
    assert "River Thames" in _text(response)


def test_without_a_key_or_past_the_daily_limit_no_model_is_used(monkeypatch):
    monkeypatch.setattr(web, "_case_paper_model", _REAL_MODEL)  # builds a client but makes no call
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
    assert "}, 180000);" in page  # the preview waits three minutes: 5 pages written and reviewed fit in that


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


def test_the_upload_page_says_who_uploads():
    page = TestClient(web.app).get("/").text
    assert "For parents and students aged 18+. Younger students: ask a parent to upload your notes." in page


def test_a_single_game_is_shown_as_the_game_not_as_a_choice(monkeypatch):
    monkeypatch.setattr(web, "SHOW_FACTS", False)
    page = TestClient(web.app).get("/").text
    assert "<fieldset>" not in page and 'type="radio"' not in page
    assert '<input type="hidden" name="output" value="detective">' in page and "Create my Detective cards" in page

    monkeypatch.setattr(web, "SHOW_SUPERHERO", True)
    page = TestClient(web.app).get("/").text
    assert "<legend>3. Choose your adventure</legend>" in page and page.count('type="radio"') == 2


def test_key_facts_is_offered_beside_detective():
    page = TestClient(web.app).get("/").text
    assert "<legend>3. Choose your cards</legend>" in page and page.count('type="radio"') == 2
    assert 'name="output" value="detective" checked' in page and 'name="output" value="facts">' in page
    assert "<strong>Key Facts</strong>" in page and "Detective or Key Facts?" in page
    assert "Create my study cards" in page and 'id="skip-cards"' in page and 'id="card-picker" hidden' in page


def _no_card_model(monkeypatch):
    for name in ("LEARN_PROVIDER", "ANTHROPIC_API_KEY", "JUNE_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def _card_model_key(monkeypatch):
    """Only pages are fetched with this key set; nothing here asks the model for cards."""
    monkeypatch.setenv("LEARN_PROVIDER", "google")
    monkeypatch.setenv("GOOGLE_API_KEY", "not-a-real-key")


def test_the_privacy_page_says_where_the_pdf_goes(monkeypatch):
    client = TestClient(web.app)
    _no_card_model(monkeypatch)
    page = client.get("/privacy").text
    assert "No AI model is used right now" in page and "When AI writes your Detective cards" not in page

    _card_model_key(monkeypatch)
    page = client.get("/privacy").text
    assert "the text of the pages you choose is sent to Google, running" in page
    assert f"Only the {web._CASE_PAPERS_KEPT} most recent are kept" in page
    assert page.count('href="/privacy"') == 0 and client.get("/").text.count('href="/privacy"') == 3


def test_the_home_page_sample_is_case_papers_made_from_the_example_sheet(monkeypatch):
    client = TestClient(web.app)
    papers = pymupdf.open(stream=client.get("/sample-case-papers.pdf").content, filetype="pdf")
    sheet = pymupdf.open(stream=client.get("/sample-sheet.pdf").content, filetype="pdf")[0].get_text()
    key = papers[-1].get_text()
    assert "The Case of the Green Kitchen" in papers[0].get_text() and "Answer Key" in key
    said = re.findall(r"Sheet says: p\. 1: (.+)", key)
    assert len(said) == 8 and all(line.strip() in sheet for line in said)
    pictures = [client.get(f"/sample-case-papers-{page}.png") for page in range(1, papers.page_count + 1)]
    assert all(p.headers["content-type"] == "image/png" and p.content.startswith(b"\x89PNG") for p in pictures)
    assert client.get(f"/sample-case-papers-{papers.page_count + 1}.png").status_code == 404

    _card_model_key(monkeypatch)
    page = client.get("/").text
    assert 'src="/sample-case-papers-1.png"' in page
    # "Try it with our example sheet" opens the preview with every page of the sample as a picture.
    assert 'id="try-sample"' in page and page.count('src="/sample-case-papers-') == 1 + papers.page_count
    _no_card_model(monkeypatch)  # without a card model the site prints basic cards, so the sample would mislead
    page = client.get("/").text
    assert 'id="sample"' not in page and 'id="try-sample"' not in page and 'id="sample-pages"' not in page


def test_every_page_says_who_runs_learn_and_how_to_reach_them():
    client = TestClient(web.app)
    mail = 'href="mailto:mau.pooja51@gmail.com"'
    home = client.get("/").text
    assert "Learn is made by Pooja Pendurkar in Mumbai." in home and mail in home
    assert mail in client.get("/library").text
    privacy = client.get("/privacy").text
    assert mail in privacy and "8 Amar Apartment, Manchubhai Road<br>Malad East, Mumbai 400097" in privacy
    assert mail in client.post("/generate", files={"pdf": ("bad.pdf", b"not a pdf", "application/pdf")}).text


def test_the_library_marks_the_chosen_topic():
    client = TestClient(web.app)

    page = client.get("/library", params={"region": "Indian Studies"}).text
    assert '<a href="/library?region=Indian%20Studies" aria-current="page">' in page
    assert page.count('aria-current="page">') == 1
    assert '<a href="/library" aria-current="page">' in client.get("/library", params={"region": "other"}).text


def test_key_facts_are_listed_then_printed_without_the_cards_taken_out_and_never_ask_a_model(monkeypatch):
    _card_model_key(monkeypatch)  # a key is set, yet Key Facts never asks a model
    monkeypatch.setattr(web, "_case_papers", lambda *args: pytest.fail("Key Facts asked for case papers"))
    client = TestClient(web.app)
    upload = {"pdf": ("sheet.pdf", (web.SAMPLE / "example-sheet.pdf").read_bytes(), "application/pdf")}

    listed = client.post("/key-facts", files=upload).json()
    assert listed["notes"] == [] and len(listed["cards"]) == 8
    assert listed["cards"][1] == {
        "number": 2,
        "about": "",
        "question": "Which words fit the gaps?",
        "clue": f"They use {GAP}, {GAP} and {GAP} from the air.",
        "answer": "sunlight, water and carbon dioxide",
        "page": 1,
    }

    response = client.post("/preview", data={"output": "facts", "skip": "2"}, files=upload)
    assert response.headers["content-disposition"] == 'inline; filename="learn_key_facts.pdf"'
    text = " ".join(" ".join(page.get_text().split()) for page in pymupdf.open(stream=response.content))
    assert "KEY FACTS" in text and "They use" not in text and "Green plants make their own food" in text

    response = client.post("/generate", data={"output": "facts"}, files=upload)
    assert response.headers["content-disposition"] == 'attachment; filename="learn_key_facts.pdf"'
    assert "They use" in "".join(page.get_text() for page in pymupdf.open(stream=response.content, filetype="pdf"))


def test_key_facts_take_any_number_of_pages_and_say_what_went_wrong(monkeypatch):
    _no_card_model(monkeypatch)
    client = TestClient(web.app)
    document = pymupdf.open()
    for number in range(1, 8):
        page = document.new_page()
        page.insert_text((60, 80), f"River {number}", fontsize=16)
        page.insert_text((60, 120), f"River {number} flows for about {number * 100} km to the sea.", fontsize=11)
    upload = {"pdf": ("notes.pdf", document.tobytes(), "application/pdf")}

    assert client.post("/preview", data={"output": "facts"}, files=upload).headers["content-type"] == "application/pdf"
    detective = client.post("/preview", data={"output": "detective"}, files=upload)
    assert "up to 5 pages" in detective.headers["x-learn-error"]

    every = client.post("/preview", data={"output": "facts", "skip": ",".join(map(str, range(1, 60)))}, files=upload)
    assert "Keep at least one card" in every.headers["x-learn-error"]
    garbled = client.post("/preview", data={"output": "facts", "skip": "1; 2"}, files=upload)
    assert "could not be read" in garbled.headers["x-learn-error"]
    not_pdf = client.post("/key-facts", files={"pdf": ("notes.pdf", b"not a pdf", "application/pdf")})
    assert not_pdf.status_code == 422 and not_pdf.json() == {"error": "That file does not appear to be a PDF."}


def test_the_privacy_page_says_key_facts_use_no_ai(monkeypatch):
    _card_model_key(monkeypatch)
    page = TestClient(web.app).get("/privacy").text
    assert "Key Facts cards never use AI" in page
