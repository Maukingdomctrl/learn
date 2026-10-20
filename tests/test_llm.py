"""AnthropicLLM limits, bounded truncation retry and call logging, against a fake SDK client (no network)."""

from types import SimpleNamespace

import pytest

from learn.llm import AnthropicLLM, LLMError


def msg(stop="end_turn", text='{"ok": 1}', output=900, thinking=600):
    usage = SimpleNamespace(
        input_tokens=1200, output_tokens=output, output_tokens_details=SimpleNamespace(thinking_tokens=thinking)
    )
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=text)], usage=usage)


class FakeStream:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_final_message(self):
        return self.message


class FakeClient:
    def __init__(self, messages, cap=128000, cap_error=None, stream_error=None):
        self.messages = list(messages)
        self.cap, self.cap_error, self.stream_error = cap, cap_error, stream_error
        self.requests: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))
        self.models = SimpleNamespace(retrieve=self._retrieve)

    def _stream(self, **kwargs):
        self.requests.append(kwargs)
        if self.stream_error:
            raise self.stream_error
        return FakeStream(self.messages.pop(0))

    def _retrieve(self, model):
        if self.cap_error:
            raise self.cap_error
        return SimpleNamespace(max_tokens=self.cap)


def make(client, **kw):
    return AnthropicLLM("claude-test", client=client, **kw)


def test_truncated_response_is_retried_once_with_larger_budget():
    client = FakeClient([msg("max_tokens", text='{"ok": '), msg()])
    llm = make(client, max_tokens=32000, retry_max_tokens=64000)
    assert llm.json("generate_lesson", "sys", "prompt") == {"ok": 1}
    assert [r["max_tokens"] for r in client.requests] == [32000, 64000]
    assert [c["stop_reason"] for c in llm.call_log] == ["max_tokens", "end_turn"]
    assert [c["attempt"] for c in llm.call_log] == [1, 2]
    assert llm.call_log[0]["thinking_tokens"] == 600 and llm.call_log[0]["input_tokens"] == 1200


def test_second_truncation_stops_with_details_and_no_third_request():
    client = FakeClient([msg("max_tokens", output=64000, thinking=50000), msg("max_tokens", output=64000)])
    llm = make(client)
    with pytest.raises(LLMError) as err:
        llm.json("generate_lesson", "sys", "prompt")
    assert len(client.requests) == 2
    assert "cut off" in str(err.value) and "64000" in str(err.value)


def test_budgets_are_clamped_to_the_models_reported_limit():
    client = FakeClient([msg("max_tokens"), msg()], cap=40000)
    llm = make(client, max_tokens=32000, retry_max_tokens=64000)
    llm.json("generate_lesson", "sys", "prompt")
    assert [r["max_tokens"] for r in client.requests] == [32000, 40000]


def test_no_retry_when_first_budget_already_equals_model_limit():
    client = FakeClient([msg("max_tokens")], cap=20000)
    llm = make(client, max_tokens=32000, retry_max_tokens=64000)
    with pytest.raises(LLMError):
        llm.json("generate_lesson", "sys", "prompt")
    assert [r["max_tokens"] for r in client.requests] == [20000]


def test_models_api_failure_falls_back_to_configured_limits():
    client = FakeClient([msg()], cap_error=RuntimeError("no access"))
    llm = make(client, max_tokens=12345)
    llm.json("select_concept", "sys", "prompt")
    assert client.requests[0]["max_tokens"] == 12345
    assert any("configured limits" in n for n in llm.notes)


def test_refusal_is_not_retried():
    client = FakeClient([msg("refusal")])
    with pytest.raises(LLMError, match="declined"):
        make(client).json("generate_lesson", "sys", "prompt")
    assert len(client.requests) == 1


def test_effort_depends_on_task():
    client = FakeClient([msg(), msg()])
    llm = make(client, effort="high", check_effort="medium")
    llm.json("generate_lesson", "sys", "p")
    llm.json("A1", "sys", "p")
    assert [r["output_config"]["effort"] for r in client.requests] == ["high", "medium"]


def test_request_errors_are_logged_and_translated():
    client = FakeClient([], stream_error=TypeError("Could not resolve authentication method"))
    llm = make(client)
    with pytest.raises(LLMError, match="credentials"):
        llm.json("select_concept", "sys", "p")
    assert "TypeError" in llm.call_log[0]["error"]


def test_limits_come_from_environment(monkeypatch):
    monkeypatch.setenv("LEARN_MAX_TOKENS", "16000")
    monkeypatch.setenv("LEARN_MAX_TOKENS_RETRY", "not-a-number")
    monkeypatch.setenv("LEARN_CHECK_EFFORT", "low")
    llm = AnthropicLLM.from_config()
    assert (llm.max_tokens, llm.retry_max_tokens, llm.check_effort) == (16000, 64000, "low")


def test_without_fallbacks_requests_use_the_plain_endpoint_and_send_the_effort():
    requests = []

    def stream(**kwargs):
        requests.append(kwargs)
        return FakeStream(msg())

    client = SimpleNamespace(
        messages=SimpleNamespace(stream=stream),
        beta=SimpleNamespace(messages=SimpleNamespace(stream=None)),  # must not be used
        models=SimpleNamespace(retrieve=lambda model: SimpleNamespace(max_tokens=128000)),
    )
    llm = make(client, effort="low", check_effort="low", fallbacks=False)
    assert llm.json("write_cards", "sys", "prompt") == {"ok": 1}
    request = requests[0]
    assert request["output_config"] == {"effort": "low"} and request["thinking"] == {"type": "adaptive"}
    assert "fallbacks" not in request and "betas" not in request


def test_with_fallbacks_requests_ask_for_the_default_fallback():
    client = FakeClient([msg()])
    make(client).json("generate_lesson", "sys", "prompt")
    assert client.requests[0]["fallbacks"] == "default"
