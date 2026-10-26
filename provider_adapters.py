"""
Modular AI Provider Adapter Layer for the Standalone Question-Generation Engine.

Responsibilities:
- Read credentials from environment variables without ever logging or exposing secrets.
- Provide a unified interface (`AIProviderAdapter`) for question generation and review passes.
- Support Google Gemini (`GeminiProviderAdapter`), OpenAI-compatible APIs (`OpenAICompatibleProviderAdapter`),
  and a deterministic curriculum-grounded synthesis adapter (`DeterministicSynthesisAdapter`) for unit testing
  and offline/baseline evaluation.
- Enforce request timeouts, bounded retries with exponential backoff, rate-limit handling,
  and JSON schema output constraints.
"""

from __future__ import annotations

import abc
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class ProviderError(Exception):
    """Raised when an AI provider fails after bounded retries or returns unrecoverable errors."""

    def __init__(
        self,
        message: str,
        *,
        provider: str = "unknown",
        model: str = "unknown",
        status_code: Optional[int] = None,
        retryable: bool = False,
        attempts: int = 1,
    ) -> None:
        super().__init__(sanitize_secrets(message))
        self.provider = provider
        self.model = model
        self.status_code = status_code
        self.retryable = retryable
        self.attempts = attempts


def sanitize_secrets(text: str) -> str:
    """Redact API keys, Bearer tokens, and query key parameters from diagnostic messages."""
    if not text:
        return ""
    sanitized = str(text)
    for env_var in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AI_API_KEY"):
        secret_val = os.environ.get(env_var)
        if secret_val and len(secret_val) > 4:
            sanitized = sanitized.replace(secret_val, f"[REDACTED_{env_var}]")
    sanitized = re.sub(r"(key=)[A-Za-z0-9_\-]{12,}", r"\1[REDACTED_KEY]", sanitized)
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{12,}", r"\1[REDACTED_TOKEN]", sanitized)
    sanitized = re.sub(r"(AIza[A-Za-z0-9_\-]{20,})", "[REDACTED_GCP_KEY]", sanitized)
    return sanitized


@dataclass
class ProviderConfig:
    """Configuration for AI provider calls, timeouts, and bounded retries."""

    provider: str = field(default_factory=lambda: os.environ.get("AI_PROVIDER", "auto"))
    model: str = field(default_factory=lambda: os.environ.get("AI_MODEL", "gemini-3.8-flash"))
    timeout_seconds: float = field(
        default_factory=lambda: float(os.environ.get("AI_TIMEOUT_SECONDS", "25.0"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.environ.get("AI_MAX_RETRIES", "2"))
    )
    backoff_base_seconds: float = 0.75
    temperature: float = 0.25
    allow_fallback_to_deterministic: bool = True
    base_url: Optional[str] = field(default_factory=lambda: os.environ.get("AI_BASE_URL"))


GEMINI_QUESTION_ARRAY_SCHEMA: Dict[str, Any] = {
    "type": "ARRAY",
    "items": {
        "type": "OBJECT",
        "properties": {
            "question": {"type": "STRING"},
            "answer": {"type": "STRING"},
            "question_type": {
                "type": "STRING",
                "enum": [
                    "recall",
                    "understanding",
                    "why_how",
                    "comparison",
                    "sequence",
                    "application",
                    "interpretation",
                    "reasoning",
                    "problem_solving",
                ],
            },
            "difficulty": {
                "type": "STRING",
                "enum": ["easy", "medium", "hard"],
            },
            "learning_point": {"type": "STRING"},
            "source_evidence": {"type": "STRING"},
            "source_page": {"type": "INTEGER", "nullable": True},
        },
        "required": [
            "question",
            "answer",
            "question_type",
            "difficulty",
            "learning_point",
            "source_evidence",
        ],
    },
}


class AIProviderAdapter(abc.ABC):
    """Abstract interface for AI providers used by the Question Quality Engine."""

    def __init__(self, config: Optional[ProviderConfig] = None) -> None:
        self.config = config or ProviderConfig()

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier of the provider (e.g., 'gemini', 'openai_compatible', 'deterministic')."""

    @property
    def model_name(self) -> str:
        return self.config.model

    @abc.abstractmethod
    def generate_candidates(
        self,
        *,
        learning_points: List[Dict[str, Any]],
        class_level: int,
        subject: str,
        question_count: int,
        planned_types: List[str],
        difficulty_distribution: Optional[Dict[str, float]] = None,
        allow_external_knowledge: bool = False,
    ) -> List[Dict[str, Any]]:
        """Generate candidate question records grounded in the analyzed learning points."""

    def review_candidates(
        self,
        *,
        candidates: List[Dict[str, Any]],
        class_level: int,
        subject: str,
    ) -> List[Dict[str, Any]]:
        """Optional AI-assisted review pass; default returns candidates for deterministic rubric scoring."""
        return candidates


class GeminiProviderAdapter(AIProviderAdapter):
    """
    Adapter for Google Gemini API using structured JSON output.
    Reads `GEMINI_API_KEY` from the environment and enforces timeouts + bounded retries.
    """

    def __init__(
        self,
        config: Optional[ProviderConfig] = None,
        *,
        api_key: Optional[str] = None,
        http_sender: Optional[Callable[[urllib.request.Request, float], bytes]] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(config)
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self._http_sender = http_sender or self._default_http_sender
        self._sleep_fn = sleep_fn

    @property
    def provider_name(self) -> str:
        return "gemini"

    def is_configured(self) -> bool:
        return bool(
            self._api_key
            and self._api_key != "MY_GEMINI_API_KEY"
            and len(self._api_key.strip()) >= 10
        )

    @staticmethod
    def _default_http_sender(req: urllib.request.Request, timeout: float) -> bytes:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.read()

    def _call_gemini_json(self, system_instruction: str, user_prompt: str, schema: Dict[str, Any]) -> Any:
        if not self.is_configured():
            raise ProviderError(
                "GEMINI_API_KEY is not configured in environment variables.",
                provider=self.provider_name,
                model=self.model_name,
                retryable=False,
                attempts=0,
            )

        base = self.config.base_url or "https://generativelanguage.googleapis.com/v1beta"
        url = f"{base.rstrip('/')}/models/{self.model_name}:generateContent?key={self._api_key}"
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": self.config.temperature,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        body_bytes = json.dumps(payload).encode("utf-8")

        max_attempts = max(1, int(self.config.max_retries) + 1)
        last_error: Optional[Exception] = None
        last_status: Optional[int] = None

        for attempt in range(1, max_attempts + 1):
            req = urllib.request.Request(
                url,
                data=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "aistudio-build",
                },
                method="POST",
            )
            try:
                raw_response = self._http_sender(req, float(self.config.timeout_seconds))
                parsed_envelope = json.loads(raw_response.decode("utf-8"))
                candidates = parsed_envelope.get("candidates") or []
                if not candidates:
                    raise ProviderError(
                        "Gemini returned an empty candidates array.",
                        provider=self.provider_name,
                        model=self.model_name,
                        retryable=True,
                        attempts=attempt,
                    )
                parts = candidates[0].get("content", {}).get("parts", [])
                text_out = "".join(part.get("text", "") for part in parts).strip()
                if not text_out:
                    raise ProviderError(
                        "Gemini returned empty text content.",
                        provider=self.provider_name,
                        model=self.model_name,
                        retryable=True,
                        attempts=attempt,
                    )
                return json.loads(text_out)
            except urllib.error.HTTPError as exc:
                last_status = exc.code
                last_error = exc
                retryable = exc.code in (408, 429, 500, 502, 503, 504)
                if not retryable or attempt >= max_attempts:
                    raise ProviderError(
                        f"Gemini HTTP {exc.code}: {sanitize_secrets(str(exc))}",
                        provider=self.provider_name,
                        model=self.model_name,
                        status_code=exc.code,
                        retryable=retryable,
                        attempts=attempt,
                    ) from exc
            except (TimeoutError, urllib.error.URLError, json.JSONDecodeError, ProviderError) as exc:
                last_error = exc
                if isinstance(exc, ProviderError) and not exc.retryable:
                    raise
                if attempt >= max_attempts:
                    raise ProviderError(
                        f"Gemini provider error after {attempt} attempt(s): {sanitize_secrets(str(exc))}",
                        provider=self.provider_name,
                        model=self.model_name,
                        status_code=last_status,
                        retryable=True,
                        attempts=attempt,
                    ) from exc

            backoff = self.config.backoff_base_seconds * (2 ** (attempt - 1))
            self._sleep_fn(backoff)

        raise ProviderError(
            f"Gemini request failed after {max_attempts} attempts: {sanitize_secrets(str(last_error))}",
            provider=self.provider_name,
            model=self.model_name,
            status_code=last_status,
            retryable=False,
            attempts=max_attempts,
        )

    def generate_candidates(
        self,
        *,
        learning_points: List[Dict[str, Any]],
        class_level: int,
        subject: str,
        question_count: int,
        planned_types: List[str],
        difficulty_distribution: Optional[Dict[str, float]] = None,
        allow_external_knowledge: bool = False,
    ) -> List[Dict[str, Any]]:
        grade_band = (
            "ICSE Classes 8–10 (use accessible, age-appropriate wording; test essential knowledge, understanding, application, and reasoning; avoid advanced terminology not in the source)"
            if class_level <= 10
            else "ICSE Classes 11–12 (accommodate advanced technical terminology, multi-step analytical and numerical derivations, and preserve rigorous scientific/mathematical detail)"
        )
        external_rule = (
            "External knowledge is enabled ONLY to clarify context, and must be explicitly marked."
            if allow_external_knowledge
            else (
                "CRITICAL PDF-GROUNDED RULE: The uploaded PDF is the sole source of truth. "
                "Generate questions and answers ONLY from facts, dates, names, definitions, and formulas explicitly stated in the supplied learning points. "
                "Never invent, supplement, or import facts from general knowledge. "
                "Do not create hypothetical scenarios or application questions unless the source text itself provides the reasoning."
            )
        )
        system_instruction = (
            f"You are an expert ICSE Class {class_level} {subject} curriculum question designer.\n"
            f"Grade Adaptation Profile: {grade_band}.\n"
            f"{external_rule}\n"
            "Rules for Question Quality:\n"
            "1. Use natural, self-contained, age-appropriate language. Never refer to 'in the section above', 'according to the text', or raw section numbers.\n"
            "2. Ensure every answer directly and completely addresses what the question asks using only facts from the source.\n"
            "3. Preserve all chemical formulas, subscripts, superscripts, state symbols, units, and mathematical equations accurately.\n"
            "4. Do not confuse publication/reprint metadata dates with historical lesson dates.\n"
            "5. Do not claim to interpret a diagram or map unless its data is explicitly present in the extracted text/table."
        )
        prompt_payload = {
            "class_level": class_level,
            "subject": subject,
            "requested_question_count": question_count,
            "planned_question_types": planned_types,
            "difficulty_distribution": difficulty_distribution or {"easy": 0.3, "medium": 0.5, "hard": 0.2},
            "learning_points": [
                {
                    "id": lp.get("id"),
                    "category": lp.get("category"),
                    "topic": lp.get("topic"),
                    "summary": lp.get("summary"),
                    "source_evidence": lp.get("source_evidence"),
                    "source_page": lp.get("source_page"),
                    "formulas": lp.get("formulas", []),
                    "table_data": lp.get("table_data"),
                }
                for lp in learning_points[: max(question_count * 2, 12)]
            ],
        }
        user_prompt = (
            "Generate a JSON array of curriculum-grounded questions and answers from the learning points below.\n"
            "Each item must copy an exact verbatim substring into `source_evidence` and use the exact `source_page`.\n"
            f"Input Data:\n{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
        )
        raw_list = self._call_gemini_json(system_instruction, user_prompt, GEMINI_QUESTION_ARRAY_SCHEMA)
        if not isinstance(raw_list, list):
            raise ProviderError(
                "Gemini response was not a JSON array.",
                provider=self.provider_name,
                model=self.model_name,
                retryable=False,
            )
        return raw_list


class OpenAICompatibleProviderAdapter(AIProviderAdapter):
    """Adapter for OpenAI-compatible chat completion endpoints."""

    def __init__(
        self,
        config: Optional[ProviderConfig] = None,
        *,
        api_key: Optional[str] = None,
        http_sender: Optional[Callable[[urllib.request.Request, float], bytes]] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        super().__init__(config)
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self._http_sender = http_sender or GeminiProviderAdapter._default_http_sender
        self._sleep_fn = sleep_fn

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    def generate_candidates(
        self,
        *,
        learning_points: List[Dict[str, Any]],
        class_level: int,
        subject: str,
        question_count: int,
        planned_types: List[str],
        difficulty_distribution: Optional[Dict[str, float]] = None,
        allow_external_knowledge: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self._api_key:
            raise ProviderError(
                "OPENAI_API_KEY is not configured in environment variables.",
                provider=self.provider_name,
                model=self.model_name,
                retryable=False,
            )
        base_url = (self.config.base_url or "https://api.openai.com/v1").rstrip("/")
        url = f"{base_url}/chat/completions"
        payload = {
            "model": self.model_name,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Generate {question_count} ICSE Class {class_level} {subject} questions "
                        "as JSON {\"questions\": [...]} grounded strictly in the provided learning points."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "planned_types": planned_types,
                            "learning_points": learning_points[: max(question_count * 2, 10)],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        try:
            raw = self._http_sender(req, float(self.config.timeout_seconds))
            parsed = json.loads(raw.decode("utf-8"))
            content = parsed["choices"][0]["message"]["content"]
            obj = json.loads(content)
            return obj.get("questions", obj if isinstance(obj, list) else [])
        except Exception as exc:
            raise ProviderError(
                f"OpenAI-compatible provider failed: {sanitize_secrets(str(exc))}",
                provider=self.provider_name,
                model=self.model_name,
            ) from exc


class DeterministicSynthesisAdapter(AIProviderAdapter):
    """
    Curriculum-grounded deterministic question synthesizer.

    Used when:
    - Running offline automated unit tests without live API calls
    - Comparing deterministic baseline output against LLM providers
    - Operating in environments where live API credentials are not supplied and fallback is enabled
    """

    @property
    def provider_name(self) -> str:
        return "deterministic"

    @property
    def model_name(self) -> str:
        return "icse-pedagogical-synthesizer-v2"

    def generate_candidates(
        self,
        *,
        learning_points: List[Dict[str, Any]],
        class_level: int,
        subject: str,
        question_count: int,
        planned_types: List[str],
        difficulty_distribution: Optional[Dict[str, float]] = None,
        allow_external_knowledge: bool = False,
    ) -> List[Dict[str, Any]]:
        if not learning_points or question_count <= 0:
            return []

        results: List[Dict[str, Any]] = []
        senior_grade = class_level >= 11
        # Generate extra candidates so Step 6 repair/replacement can draw from unused learning points
        candidate_limit = min(len(learning_points), max(question_count + 5, int(question_count * 1.8)))

        # Interleave learning points by suggested question type so the top N questions span diverse cognitive types
        by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for lp in learning_points:
            c = str(lp.get("suggested_type") or lp.get("category") or "concept_fact")
            by_cat.setdefault(c, []).append(lp)
        diverse_lps: List[Dict[str, Any]] = []
        cat_keys = list(by_cat.keys())
        round_idx = 0
        while len(diverse_lps) < len(learning_points):
            added = False
            for ck in cat_keys:
                if round_idx < len(by_cat[ck]):
                    diverse_lps.append(by_cat[ck][round_idx])
                    added = True
            if not added:
                break
            round_idx += 1

        for idx in range(min(candidate_limit, len(diverse_lps))):
            lp = diverse_lps[idx]
            cat = lp.get("category")
            if lp.get("suggested_type"):
                q_type = lp["suggested_type"]
            elif cat == "table_data":
                q_type = "interpretation"
            elif cat in ("numerical_problem", "formula_equation"):
                q_type = "problem_solving"
            elif cat == "sequence":
                q_type = "sequence"
            elif cat == "comparison":
                q_type = "comparison"
            elif cat == "cause_effect":
                q_type = "why_how"
            elif cat == "reasoning_synthesis":
                q_type = "reasoning"
            elif cat == "definition":
                q_type = "understanding" if senior_grade or idx % 2 == 0 else "recall"
            else:
                q_type = planned_types[idx % len(planned_types)] if planned_types else "understanding"

            candidate = self._build_question_from_learning_point(
                lp=lp,
                q_type=q_type,
                class_level=class_level,
                subject=subject,
                senior_grade=senior_grade,
                index=idx,
            )
            results.append(candidate)

        return results

    def _build_question_from_learning_point(
        self,
        *,
        lp: Dict[str, Any],
        q_type: str,
        class_level: int,
        subject: str,
        senior_grade: bool,
        index: int,
    ) -> Dict[str, Any]:
        evidence = re.sub(r"^(?:[Æ•\-\*‹\{]|z(?=\s+[A-Z]))\s*", "", lp.get("source_evidence", "").strip())
        page = lp.get("source_page")
        term = lp.get("key_term") or subject
        formulas = lp.get("formulas") or []
        table_data = lp.get("table_data")
        numerical = lp.get("numerical_case")
        source_ref = lp.get("source_reference")

        # 1. Check if SourceAnalyzer synthesized a tailored, source-grounded curriculum question
        custom_q = lp.get("senior_question" if senior_grade else "custom_question") or lp.get("custom_question")
        custom_a = lp.get("custom_answer")
        if custom_q and custom_a:
            return {
                "question": custom_q,
                "answer": custom_a,
                "question_type": lp.get("suggested_type") or q_type,
                "difficulty": lp.get("difficulty") or ("hard" if senior_grade else "medium"),
                "learning_point": lp.get("summary") or f"Understand {term}",
                "source_evidence": evidence,
                "source_page": page,
                "source_reference": source_ref,
            }

        # 2. Structured Table Interpretation
        if q_type == "interpretation" and table_data:
            headers = table_data.get("headers", [])
            rows = table_data.get("rows", [])
            caption = re.sub(r"^Table\s+\d+(?:\.\d+)?\s*[:.\-–]\s*", "", table_data.get("caption") or "").strip() or "the comparative data"
            if len(rows) >= 2 and len(headers) >= 2:
                r0, r1 = rows[0], rows[-1]
                h1 = headers[1]
                h_last = headers[-1]
                if len(headers) == 2 or h1.lower() == h_last.lower():
                    if senior_grade:
                        question = (
                            f"Compare {r0[0]} and {r1[0]} with respect to {h1}, "
                            f"and state the specific values or characteristics for each."
                        )
                    else:
                        question = (
                            f"How do {r0[0]} and {r1[0]} differ in terms of {h1}?"
                        )
                    answer = (
                        f"For {r0[0]}, the {h1} is {r0[1]}. "
                        f"In contrast, for {r1[0]}, the {h1} is {r1[1]}."
                    )
                    lp_summary = lp.get("summary") or f"Compare {r0[0]} and {r1[0]} in terms of {h1}"
                else:
                    if senior_grade:
                        question = (
                            f"Compare {r0[0]} and {r1[0]} with respect to {h1} and {h_last}, "
                            f"and state the specific values or characteristics for each."
                        )
                    else:
                        question = (
                            f"How do {r0[0]} and {r1[0]} differ in terms of {h1} and {h_last}?"
                        )
                    answer = (
                        f"For {r0[0]}, the {h1} is {r0[1]} and {h_last} is {r0[-1]}. "
                        f"In contrast, for {r1[0]}, the {h1} is {r1[1]} and {h_last} is {r1[-1]}."
                    )
                    lp_summary = lp.get("summary") or f"Compare {r0[0]} and {r1[0]} across {h1} and {h_last}"
                return {
                    "question": question,
                    "answer": answer,
                    "question_type": "interpretation",
                    "difficulty": "medium" if not senior_grade else "hard",
                    "learning_point": lp_summary,
                    "source_evidence": evidence,
                    "source_page": page,
                    "source_reference": source_ref,
                }

        # 3. Quantitative Problem Solving & Formula/Equation Questions
        if q_type == "problem_solving" and (numerical or formulas):
            if numerical:
                question = numerical["question"] if not senior_grade else numerical.get("senior_question", numerical["question"])
                answer = numerical["answer"]
                return {
                    "question": question,
                    "answer": answer,
                    "question_type": "problem_solving",
                    "difficulty": "hard" if senior_grade else "medium",
                    "learning_point": lp.get("summary") or f"Apply {formulas[0] if formulas else term} to solve a numerical problem",
                    "source_evidence": evidence,
                    "source_page": page,
                    "source_reference": source_ref,
                    "calculation_metadata": numerical.get("calculation_metadata"),
                }
            formula_str = formulas[0]
            if senior_grade:
                question = (
                    f"State the chemical or mathematical equation ({formula_str}) associated with {term} "
                    f"and explain the process or relationship it represents."
                )
            else:
                question = (
                    f"Write the equation or formula ({formula_str}) for {term} and state what process or relationship it describes."
                )
            answer = evidence
            return {
                "question": question,
                "answer": answer,
                "question_type": "problem_solving",
                "difficulty": "medium",
                "learning_point": lp.get("summary") or f"Understand and apply {formula_str}",
                "source_evidence": evidence,
                "source_page": page,
                "source_reference": source_ref,
            }

        # 4. Self-contained, natural sentence-level synthesis without meta-references
        clean_term = re.sub(r"^(?:[Æ•\-\*]|\d+(?:\.\d+)*\.?)\s*", "", term).strip(" .,:;?\"'")
        if q_type == "sequence":
            if senior_grade:
                question = f"Trace the chronological sequence of events or stages involved in {clean_term}."
            else:
                question = f"What is the chronological order of events or steps described for {clean_term}?"
            difficulty = "medium"
        elif q_type == "comparison":
            if senior_grade:
                question = f"Distinguish between the contrasting features, roles, or methods of {clean_term}."
            else:
                question = f"What is the main difference explained regarding {clean_term}?"
            difficulty = "medium"
        elif q_type == "why_how":
            if senior_grade:
                question = f"What cause, reason, or mechanism is explained regarding {clean_term}, and what is its effect?"
            else:
                question = f"What reason or cause is explained regarding {clean_term}, and what is its result?"
            difficulty = "medium" if not senior_grade else "hard"
        elif q_type == "application":
            if senior_grade:
                question = f"How is the principle or process of {clean_term} applied in practice?"
            else:
                question = f"How is {clean_term} used or applied?"
            difficulty = "hard" if senior_grade else "medium"
        elif q_type == "reasoning":
            if senior_grade:
                question = f"Analyze the relationship and significance of {clean_term}."
            else:
                question = f"Explain the significance and effect of {clean_term}."
            difficulty = "hard"
        elif q_type == "recall":
            if senior_grade:
                question = f"Define {clean_term} and state its governing conditions or key characteristics."
            else:
                question = f"What is meant by {clean_term}, and what are its key characteristics?"
            difficulty = "easy"
        else:  # understanding
            if senior_grade:
                question = f"Explain the concept and significance of {clean_term}."
            else:
                question = f"Explain {clean_term} and its main features."
            difficulty = "easy" if index == 0 and not senior_grade else "medium"

        return {
            "question": question,
            "answer": evidence,
            "question_type": q_type,
            "difficulty": difficulty,
            "learning_point": lp.get("summary") or f"Understand {clean_term}",
            "source_evidence": evidence,
            "source_page": page,
            "source_reference": source_ref,
        }


def create_provider_adapter(options: Optional[Dict[str, Any]] = None) -> AIProviderAdapter:
    """
    Factory that instantiates the configured AIProviderAdapter.
    Supports 'gemini', 'openai_compatible', 'deterministic', or 'auto' (uses Gemini if GEMINI_API_KEY
    is set and valid, otherwise falls back cleanly when allowed).
    """
    opts = options or {}
    config = ProviderConfig(
        provider=str(opts.get("provider") or os.environ.get("AI_PROVIDER", "auto")).lower(),
        model=str(opts.get("model") or os.environ.get("AI_MODEL", "gemini-3.8-flash")),
        timeout_seconds=float(opts.get("timeout_seconds") or os.environ.get("AI_TIMEOUT_SECONDS", "4.0")),
        max_retries=int(opts.get("max_retries") if opts.get("max_retries") is not None else os.environ.get("AI_MAX_RETRIES", "1")),
        temperature=float(opts.get("temperature", 0.25)),
        allow_fallback_to_deterministic=bool(opts.get("allow_fallback_to_deterministic", True)),
        base_url=opts.get("base_url") or os.environ.get("AI_BASE_URL"),
    )

    if config.provider == "deterministic":
        return DeterministicSynthesisAdapter(config)
    if config.provider == "openai_compatible":
        return OpenAICompatibleProviderAdapter(config, api_key=opts.get("api_key"))
    if config.provider in ("gemini", "auto"):
        gemini = GeminiProviderAdapter(config, api_key=opts.get("api_key"))
        if config.provider == "gemini" or gemini.is_configured():
            return gemini
        return DeterministicSynthesisAdapter(config)

    raise ProviderError(
        f"Unsupported AI provider '{config.provider}'. Supported values: 'gemini', 'openai_compatible', 'deterministic', 'auto'.",
        provider=config.provider,
        model=config.model,
        retryable=False,
    )
