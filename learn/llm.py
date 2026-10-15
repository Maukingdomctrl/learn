"""Model client. One JSON-returning call per task, so tests can substitute a scripted fake."""

import base64
import json
import re
from typing import Protocol


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


class AnthropicLLM:
    """Claude via the Anthropic SDK. Credentials come from the environment (ANTHROPIC_API_KEY etc.)."""

    def __init__(self, model: str, effort: str = "high"):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.effort = effort

    def _call(self, system: str, content) -> str:
        try:
            with self.client.beta.messages.stream(
                model=self.model,
                max_tokens=32000,
                system=system,
                messages=[{"role": "user", "content": content}],
                thinking={"type": "adaptive"},
                output_config={"effort": self.effort},
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            ) as stream:
                msg = stream.get_final_message()
        except self._anthropic.AuthenticationError as e:
            raise LLMError("Claude API credentials are missing or invalid (set ANTHROPIC_API_KEY).") from e
        except self._anthropic.RateLimitError as e:
            raise LLMError("Claude API rate limit reached; try again later.") from e
        except self._anthropic.APIStatusError as e:
            raise LLMError(f"Claude API error {e.status_code}: {e.message}") from e
        except self._anthropic.APIConnectionError as e:
            raise LLMError(f"Cannot reach the Claude API: {e}") from e
        except TypeError as e:  # the SDK raises TypeError when no credentials can be resolved
            if "authentication" in str(e).lower():
                raise LLMError("Claude API credentials are not configured (set ANTHROPIC_API_KEY).") from e
            raise
        if msg.stop_reason == "refusal":
            raise LLMError("The model declined the request.")
        if msg.stop_reason == "max_tokens":
            raise LLMError("The model response was cut off (max_tokens).")
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")

    def json(self, task: str, system: str, prompt: str) -> dict:
        text = self._call(system, prompt)
        try:
            return parse_json(text)
        except ValueError as e:
            retry = f"{prompt}\n\nYour previous reply was not valid JSON ({e}). Reply with one JSON object only."
            try:
                return parse_json(self._call(system, retry))
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
        return self._call("You are a careful OCR transcriber.", content)
