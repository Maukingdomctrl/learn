"""Model client. One JSON-returning call per task, so tests can substitute a scripted fake.

Every API request is recorded in `call_log` (task, limits, stop reason, token usage, error) so a run's report
shows why a response was cut off or failed. Thinking counts toward `max_tokens` on current models, so a
response stopped at `max_tokens` is retried once with a larger budget, never above the model's own output limit.
"""

import base64
import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Optional, Protocol

from . import config as C


class LLMError(Exception):
    pass


class LLM(Protocol):
    def json(self, task: str, system: str, prompt: str) -> dict: ...
    def transcribe_image(self, png: bytes) -> str: ...


def parse_json(text: str) -> dict:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start : end + 1])


@dataclass
class CallRecord:
    task: str
    model: str
    effort: str
    max_tokens: int
    attempt: int
    stop_reason: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    thinking_tokens: Optional[int] = None
    seconds: float = 0.0
    error: Optional[str] = None


# Stands in for the June key when the environment's network secret replaces it on the way out.
JUNE_KEY_FROM_NETWORK = "set-by-network-secret"


class AnthropicLLM:
    """Claude via the Anthropic SDK. Credentials come from the environment (ANTHROPIC_API_KEY etc.).

    ``base_url`` and ``api_key`` point the same client at a service with Anthropic's Messages API, such as June.
    ``auth_token`` sends the key as "Authorization: Bearer"; a network secret may put the real key there instead.
    ``fallbacks`` asks the API to re-run a declined request on another model; Haiku and June do not offer it.
    """

    def __init__(
        self,
        model: str,
        effort: str = "high",
        check_effort: str = "medium",
        max_tokens: int = 32000,
        retry_max_tokens: int = 64000,
        client=None,
        base_url: str = "",
        api_key: str = "",
        auth_token: str = "",
        fallbacks: bool = True,
        key_name: str = "ANTHROPIC_API_KEY",
    ):
        import anthropic

        self._anthropic = anthropic
        if client is None:
            options = {"base_url": base_url} if base_url else {}
            if api_key:
                options["api_key"] = api_key
            elif auth_token:
                options["auth_token"] = auth_token
            client = anthropic.Anthropic(**options)
        self.client = client
        self.fallbacks = fallbacks
        self.key_name = key_name
        self.model = model
        self.effort = effort
        self.check_effort = check_effort
        self.max_tokens = max_tokens
        self.retry_max_tokens = retry_max_tokens
        self.call_log: list[dict] = []
        self.notes: list[str] = []
        self._model_cap: Optional[int] = None
        self._cap_checked = False

    @classmethod
    def from_config(cls) -> "AnthropicLLM":
        return cls(C.model_name(), C.model_effort(), C.check_effort(), C.max_output_tokens(), C.retry_output_tokens())

    @classmethod
    def for_cards(cls, effort: str = "") -> "AnthropicLLM":
        """The card model (Gemini through June, else Haiku) at the cards' effort, or ``effort`` when given."""
        june = C.provider() == "june"
        effort = effort or C.cards_effort()
        return cls(
            C.cards_model(),
            effort,
            effort,
            C.cards_max_tokens(),
            2 * C.cards_max_tokens(),
            base_url=C.june_base_url() if june else "",
            api_key=C.env("JUNE_API_KEY") if june else "",
            # Without JUNE_API_KEY, the environment's network secret adds the key as "Authorization: Bearer".
            auth_token=JUNE_KEY_FROM_NETWORK if june and not C.env("JUNE_API_KEY") else "",
            fallbacks=False,
            key_name="JUNE_API_KEY" if june else "ANTHROPIC_API_KEY",
        )

    def model_output_cap(self) -> Optional[int]:
        """The model's maximum output tokens from the Models API, or None if it cannot be read."""
        if not self._cap_checked:
            self._cap_checked = True
            try:
                self._model_cap = int(self.client.models.retrieve(self.model).max_tokens)
                self.notes.append(f"{self.model}: Models API reports max output {self._model_cap} tokens")
            except Exception as e:  # noqa: BLE001 - fall back to configured limits, but say so
                self.notes.append(
                    f"Could not read {self.model}'s output limit ({type(e).__name__}); using configured limits"
                )
        return self._model_cap

    def budgets(self) -> tuple[int, int]:
        """(first attempt, retry) output budgets, each clamped to the model's limit when known."""
        cap = self.model_output_cap()
        first, retry = self.max_tokens, max(self.retry_max_tokens, self.max_tokens)
        if cap:
            first, retry = min(first, cap), min(retry, cap)
        return first, retry

    def effort_for(self, task: str) -> str:
        return self.effort if task in C.WRITING_TASKS else self.check_effort

    def _request(self, task: str, system: str, content, max_tokens: int, attempt: int):
        effort = self.effort_for(task)
        rec = CallRecord(task=task, model=self.model, effort=effort, max_tokens=max_tokens, attempt=attempt)
        start = time.monotonic()
        request = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": content}],
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": effort},
        }
        try:
            if self.fallbacks:
                manager = self.client.beta.messages.stream(
                    **request, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                )
            else:
                manager = self.client.messages.stream(**request)
            with manager as stream:
                msg = stream.get_final_message()
        except Exception as e:
            rec.error = f"{type(e).__name__}: {e}"
            rec.seconds = round(time.monotonic() - start, 2)
            self.call_log.append(asdict(rec))
            translated = self._translate(e)
            if translated is e:
                raise
            raise translated from e
        rec.seconds = round(time.monotonic() - start, 2)
        rec.stop_reason = msg.stop_reason
        usage = getattr(msg, "usage", None)
        if usage is not None:
            rec.input_tokens = getattr(usage, "input_tokens", None)
            rec.output_tokens = getattr(usage, "output_tokens", None)
            details = getattr(usage, "output_tokens_details", None)
            rec.thinking_tokens = getattr(details, "thinking_tokens", None) if details else None
        self.call_log.append(asdict(rec))
        return msg

    def _translate(self, e: Exception) -> Exception:
        a = self._anthropic
        if isinstance(e, a.AuthenticationError):
            return LLMError(f"Claude API credentials are missing or invalid (set {self.key_name}).")
        if isinstance(e, a.RateLimitError):
            return LLMError("Claude API rate limit reached; try again later.")
        if isinstance(e, a.APIStatusError):
            return LLMError(f"Claude API error {e.status_code}: {e.message}")
        if isinstance(e, a.APIConnectionError):
            return LLMError(f"Cannot reach the Claude API: {e}")
        if isinstance(e, TypeError) and "authentication" in str(e).lower():  # SDK: no credentials resolved
            return LLMError(f"Claude API credentials are not configured (set {self.key_name}).")
        return e

    def _call(self, task: str, system: str, content) -> str:
        first, retry = self.budgets()
        msg = self._request(task, system, content, first, attempt=1)
        if msg.stop_reason == "max_tokens" and retry > first:
            # Safe to retry: the request was accepted and only ran out of output budget.
            msg = self._request(task, system, content, retry, attempt=2)
        if msg.stop_reason == "refusal":
            raise LLMError(f"{task}: the model declined the request.")
        if msg.stop_reason == "max_tokens":
            last = self.call_log[-1]
            raise LLMError(
                f"{task}: the model response was cut off at its {last['max_tokens']}-token output limit "
                f"({last['output_tokens']} output tokens, of which {last['thinking_tokens']} thinking). "
                "Lower LEARN_EFFORT or raise LEARN_MAX_TOKENS_RETRY (it cannot exceed the model's limit)."
            )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    def json(self, task: str, system: str, prompt: str) -> dict:
        text = self._call(task, system, prompt)
        try:
            return parse_json(text)
        except ValueError as e:
            retry = f"{prompt}\n\nYour previous reply was not valid JSON ({e}). Reply with one JSON object only."
            try:
                return parse_json(self._call(task, system, retry))
            except ValueError as e2:
                raise LLMError(f"{task}: model did not return valid JSON ({e2})") from e2

    def transcribe_image(self, png: bytes) -> str:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": base64.standard_b64encode(png).decode(),
                },
            },
            {
                "type": "text",
                "text": (
                    "Transcribe all text on this scanned textbook page exactly as printed, in reading order. "
                    "Separate paragraphs with a blank line. Do not add, correct, summarise or explain anything. "
                    "Write [unreadable] for text you cannot read. Output only the transcription."
                ),
            },
        ]
        return self._call("ocr", "You are a careful OCR transcriber.", content)
