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


# The OpenAI-style client for Gemini on Google's own API, against a fake HTTP transport


def google(*replies, **kw):
    """An OpenAIStyleLLM whose requests are answered in turn by ``replies`` (status, JSON body)."""
    import httpx

    from learn.llm import OpenAIStyleLLM

    sent: list[httpx.Request] = []
    queue = list(replies)

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        status, body = queue.pop(0)
        return httpx.Response(status, json=body)

    client = httpx.Client(transport=httpx.MockTransport(answer))
    llm = OpenAIStyleLLM("gemini-test", "low", "https://example.test/v1beta/openai/", "key-1", 8000, 16000, http=client)
    llm.busy_wait = 0
    return llm, sent


def chat(text='{"ok": 1}', finish="stop"):
    usage = {"prompt_tokens": 700, "completion_tokens": 300, "completion_tokens_details": {"reasoning_tokens": 0}}
    return 200, {"choices": [{"message": {"content": text}, "finish_reason": finish}], "usage": usage}


def test_google_client_sends_one_chat_request_and_logs_it():
    import json

    llm, sent = google(chat())
    assert llm.json("write_evidence_cards", "sys", "prompt") == {"ok": 1}
    body = json.loads(sent[0].content)
    assert str(sent[0].url) == "https://example.test/v1beta/openai/chat/completions"
    assert sent[0].headers["authorization"] == "Bearer key-1"
    assert body["model"] == "gemini-test" and body["reasoning_effort"] == "low" and body["max_tokens"] == 8000
    assert body["messages"][0] == {"role": "system", "content": "sys"}
    assert llm.call_log[0]["input_tokens"] == 700 and llm.call_log[0]["stop_reason"] == "stop"


def test_google_client_retries_a_cut_off_reply_once_with_a_larger_budget():
    import json

    llm, sent = google(chat('{"ok": ', "length"), chat())
    assert llm.json("t", "s", "p") == {"ok": 1}
    assert [json.loads(r.content)["max_tokens"] for r in sent] == [8000, 16000]
    llm, _ = google(chat('{"ok": ', "length"), chat('{"ok": ', "length"))
    with pytest.raises(LLMError, match="cut off"):
        llm.json("t", "s", "p")


@pytest.mark.parametrize(
    "status, body, message",
    [
        (400, [{"error": {"message": "Please pass a valid API key"}}], "set GOOGLE_API_KEY"),
        (429, {"error": {"message": "Quota exceeded"}}, "daily quota"),
        (500, {"error": {"message": "Internal"}}, "Model API error 500: Internal"),
    ],
)
def test_google_client_turns_api_failures_into_clear_errors(status, body, message):
    llm, _ = google((status, body), (status, body))  # a 5xx is asked twice
    with pytest.raises(LLMError, match=message):
        llm.json("t", "s", "p")
    assert llm.call_log[0]["error"].startswith(f"HTTP {status}")


def test_the_google_provider_picks_flash_lite_and_the_network_secret_stand_in(monkeypatch):
    from learn.llm import KEY_FROM_NETWORK, OpenAIStyleLLM, card_llm

    monkeypatch.setenv("LEARN_PROVIDER", "google")
    monkeypatch.delenv("LEARN_CARDS_MODEL", raising=False)
    monkeypatch.delenv("LEARN_CARDS_EFFORT", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    llm = card_llm("low")
    assert isinstance(llm, OpenAIStyleLLM) and llm.model == "gemini-3.5-flash-lite" and llm.effort == "low"
    assert llm.api_key == KEY_FROM_NETWORK and llm.base_url.startswith("https://generativelanguage.googleapis.com")
    monkeypatch.setenv("GOOGLE_API_KEY", "key-2")
    assert card_llm().api_key == "key-2" and card_llm().effort == "medium"


def test_google_client_asks_a_busy_server_once_more_then_stops():
    busy = (503, [{"error": {"message": "This model is currently experiencing high demand."}}])
    llm, sent = google(busy, chat())
    assert llm.json("t", "s", "p") == {"ok": 1} and len(sent) == 2
    assert llm.call_log[0]["error"].startswith("HTTP 503") and llm.call_log[1]["error"] is None
    llm, sent = google(busy, busy, chat())
    with pytest.raises(LLMError, match="Model API error 503: This model is currently experiencing high demand"):
        llm.json("t", "s", "p")
    assert len(sent) == 2  # never a third request
