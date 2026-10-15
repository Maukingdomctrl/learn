import copy
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.fixtures import SAMPLE_LESSON, make_sample_pdf  # noqa: E402


@pytest.fixture
def lesson_data():
    return copy.deepcopy(SAMPLE_LESSON)


@pytest.fixture(scope="session")
def sample_pdf(tmp_path_factory):
    path = tmp_path_factory.mktemp("pdf") / "triangle_area.pdf"
    make_sample_pdf(str(path))
    return str(path)


class ScriptedLLM:
    """Test double for the model. Returns canned JSON per task; records every call.

    This is NOT a real model: tests that use it verify the pipeline's code paths, not lesson quality.
    """

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def json(self, task, system, prompt):
        self.calls.append((task, prompt))
        r = self.responses[task]
        if callable(r):
            r = r(prompt, self)
        if isinstance(r, list):
            r = r.pop(0) if len(r) > 1 else r[0]
        return json.loads(json.dumps(r))

    def transcribe_image(self, png):
        self.calls.append(("ocr", ""))
        return self.responses.get("ocr", "")


@pytest.fixture
def scripted():
    return ScriptedLLM
