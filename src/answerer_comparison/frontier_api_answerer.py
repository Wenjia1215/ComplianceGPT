"""Auditable Gemini generateContent adapter for the frozen RQ2 answerer.

The adapter is deliberately a mixin rather than a second implementation of
the generative baseline. ``make_gemini_generate_content_answerer_class``
combines it with the frozen ``BaselineGenerativeAnswerer`` class at run time,
so prompt construction, JSON parsing, fail-closed normalization, and parse
retries remain the exact registered implementation. Only the model call is
replaced.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Type


LOG_SCHEMA_VERSION = "compliancegpt-gemini-api-call-v1"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        _jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(child) for child in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    return str(value)


def read_api_call_log(path: Path) -> List[Dict[str, Any]]:
    """Read and structurally validate the cumulative API response log."""

    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    seen_response_ids = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid API call log JSON at line {line_number}: {path}") from error
            if not isinstance(row, dict):
                raise ValueError(f"API call log line {line_number} is not an object: {path}")
            if row.get("schema_version") != LOG_SCHEMA_VERSION:
                raise ValueError(f"Unexpected API call log schema at line {line_number}: {path}")
            response_id = str(row.get("response_id", "") or "").strip()
            if not response_id:
                raise ValueError(f"API call log line {line_number} has no response id: {path}")
            if response_id in seen_response_ids:
                raise ValueError(f"Duplicate API response id {response_id!r}: {path}")
            seen_response_ids.add(response_id)
            rows.append(row)
    return rows


def _gemini_contents(
    messages: Sequence[Mapping[str, str]],
    system_prompt: str,
    model_contents: Sequence[Any],
    model_texts: Sequence[str],
) -> List[Any]:
    """Translate the frozen chat turns without changing their text."""

    if not messages or str(messages[0].get("role", "")) != "system":
        raise ValueError("The frozen answerer request must start with one system message.")
    if str(messages[0].get("content", "")) != system_prompt:
        raise ValueError("The API request system prompt differs from the registered prompt.")
    contents: List[Any] = []
    model_index = 0
    for message in messages[1:]:
        role = str(message.get("role", ""))
        if role == "assistant":
            if model_index >= len(model_contents):
                raise ValueError("Gemini retry history is missing a prior model response.")
            message_text = str(message.get("content", ""))
            if message_text != model_texts[model_index]:
                raise ValueError("Gemini retry history changed a prior model response.")
            contents.append(model_contents[model_index])
            model_index += 1
            continue
        elif role == "user":
            gemini_role = "user"
        else:
            raise ValueError(f"Unsupported frozen-answerer role for Gemini: {role!r}")
        contents.append(
            {
                "role": gemini_role,
                "parts": [{"text": str(message.get("content", ""))}],
            }
        )
    final_role = ""
    if contents:
        if isinstance(contents[-1], Mapping):
            final_role = str(contents[-1].get("role", "") or "")
        else:
            final_role = str(getattr(contents[-1], "role", "") or "")
    if final_role != "user":
        raise ValueError("The frozen answerer request must end with a user turn.")
    if model_index != len(model_contents):
        raise ValueError("Gemini retry history contains an unreferenced model response.")
    return contents


def _candidate_audit(response: Any) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for candidate in list(getattr(response, "candidates", None) or []):
        rows.append(
            {
                "finish_reason": str(getattr(candidate, "finish_reason", "") or ""),
                "finish_message": str(getattr(candidate, "finish_message", "") or ""),
                "safety_ratings": _jsonable(getattr(candidate, "safety_ratings", None)),
                "citation_metadata": _jsonable(getattr(candidate, "citation_metadata", None)),
            }
        )
    return rows


class GeminiGenerateContentAnswererMixin:
    """Replace only ``_call_model`` while inheriting the frozen answerer logic."""

    def __init__(
        self,
        *,
        client: Any,
        model_id: str,
        system_prompt: str,
        query_id_by_question: Mapping[str, str],
        call_log_path: Path,
        thinking_level: str = "LOW",
        temperature: float = 1.0,
        max_output_tokens: int = 2048,
        max_parse_retries: int = 2,
    ) -> None:
        # Do not call the local-model parent's constructor. It creates a
        # Transformers GenerationConfig and requires a tokenizer/model that do
        # not participate in this API experiment.
        self.client = client
        self.model_id = str(model_id)
        self.system_prompt = str(system_prompt)
        self.thinking_level = str(thinking_level).upper()
        self.temperature = float(temperature)
        self.max_output_tokens = int(max_output_tokens)
        self.max_parse_retries = int(max_parse_retries)
        self.call_log_path = Path(call_log_path)
        self.query_id_by_question = {
            str(question): str(query_id)
            for question, query_id in query_id_by_question.items()
        }
        if len(self.query_id_by_question) != len(query_id_by_question):
            raise ValueError("Question-to-query-id map contains duplicate questions.")
        if not self.model_id:
            raise ValueError("A Gemini API model id is required.")
        if self.thinking_level not in {"MINIMAL", "LOW", "MEDIUM", "HIGH"}:
            raise ValueError(f"Unsupported Gemini thinking level: {self.thinking_level!r}")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("temperature must be between 0 and 2.")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive.")
        if self.max_parse_retries < 0:
            raise ValueError("max_parse_retries cannot be negative.")

        self._active_query_id = ""
        self._active_question_sha256 = ""
        self._active_calls: List[Dict[str, Any]] = []
        self._active_model_contents: List[Any] = []
        self._active_model_texts: List[str] = []
        self._resolved_model = ""
        self._validate_existing_log()

    @property
    def resolved_model(self) -> str:
        return self._resolved_model

    def _validate_existing_log(self) -> None:
        rows = read_api_call_log(self.call_log_path)
        models = set()
        for row in rows:
            expected = {
                "provider": "google-gemini",
                "api_method": "generateContent",
                "request_model": self.model_id,
                "thinking_level": self.thinking_level,
                "temperature": self.temperature,
                "max_output_tokens": self.max_output_tokens,
            }
            for key, value in expected.items():
                if row.get(key) != value:
                    raise RuntimeError(
                        f"Existing API call log changed for {key!r}: "
                        f"expected {value!r}, got {row.get(key)!r}. Use a new output directory."
                    )
            response_model = str(row.get("response_model", "") or "").strip()
            if response_model:
                models.add(response_model)
        if len(models) > 1:
            raise RuntimeError(
                f"Existing API call log contains multiple server-reported models: {sorted(models)}"
            )
        self._resolved_model = next(iter(models), "")

    def _append_call(self, row: Mapping[str, Any]) -> None:
        self.call_log_path.parent.mkdir(parents=True, exist_ok=True)
        previous = self.call_log_path.read_text(encoding="utf-8") if self.call_log_path.exists() else ""
        payload = previous + json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
        temporary = self.call_log_path.with_name(self.call_log_path.name + ".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(self.call_log_path)

    def generate(self, query: str, docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        question = str(query)
        if question not in self.query_id_by_question:
            raise KeyError("The API answerer received a question outside the registered contexts.")
        self._active_query_id = self.query_id_by_question[question]
        self._active_question_sha256 = hashlib.sha256(question.encode("utf-8")).hexdigest()
        self._active_calls = []
        self._active_model_contents = []
        self._active_model_texts = []
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        try:
            output = dict(super().generate(query, docs))  # type: ignore[misc]
        finally:
            elapsed_seconds = time.monotonic() - started
        output["api_provenance"] = {
            "provider": "google-gemini",
            "api_method": "generateContent",
            "request_model": self.model_id,
            "response_model": self._resolved_model,
            "query_id": self._active_query_id,
            "question_sha256": self._active_question_sha256,
            "thinking_level": self.thinking_level,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "max_parse_retries": self.max_parse_retries,
            "tools_enabled": False,
            "structured_output_enforced": False,
            "thought_signatures_preserved_for_retries": True,
            "started_at_utc": started_at,
            "elapsed_seconds": elapsed_seconds,
            "api_calls": list(self._active_calls),
        }
        return output

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        request_hash = canonical_sha256(messages)
        contents = _gemini_contents(
            messages,
            self.system_prompt,
            self._active_model_contents,
            self._active_model_texts,
        )
        config = {
            "system_instruction": self.system_prompt,
            "thinking_config": {"thinking_level": self.thinking_level},
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
        }
        call_started = time.monotonic()
        response = self.client.models.generate_content(
            model=self.model_id,
            contents=contents,
            config=config,
        )
        latency_seconds = time.monotonic() - call_started
        output_text = str(getattr(response, "text", "") or "").strip()
        response_id = str(getattr(response, "response_id", "") or "").strip()
        response_model = str(getattr(response, "model_version", "") or "").strip()
        if not response_id:
            raise RuntimeError("Gemini API result did not include a response id.")
        if not response_model:
            raise RuntimeError("Gemini API result did not include a server-reported model version.")
        previous_model = self._resolved_model
        if not self._resolved_model:
            self._resolved_model = response_model

        candidates = _candidate_audit(response)
        response_candidates = list(getattr(response, "candidates", None) or [])
        response_content = (
            getattr(response_candidates[0], "content", None)
            if response_candidates
            else None
        )
        if response_content is None:
            response_content = {
                "role": "model",
                "parts": [{"text": output_text}],
            }
        self._active_model_contents.append(response_content)
        self._active_model_texts.append(output_text)
        row: Dict[str, Any] = {
            "schema_version": LOG_SCHEMA_VERSION,
            "provider": "google-gemini",
            "api_method": "generateContent",
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
            "query_id": self._active_query_id,
            "question_sha256": self._active_question_sha256,
            "call_index_for_question": len(self._active_calls) + 1,
            "request_model": self.model_id,
            "response_model": response_model,
            "response_id": response_id,
            "response_created_at": _jsonable(getattr(response, "create_time", None)),
            "response_status": "completed" if candidates else "no_candidates",
            "request_messages_sha256": request_hash,
            "gemini_contents_sha256": canonical_sha256(contents),
            "thinking_level": self.thinking_level,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "tools_enabled": False,
            "structured_output_enforced": False,
            "latency_seconds": latency_seconds,
            "usage": _jsonable(getattr(response, "usage_metadata", None)),
            "prompt_feedback": _jsonable(getattr(response, "prompt_feedback", None)),
            "model_status": _jsonable(getattr(response, "model_status", None)),
            "candidates": candidates,
            "output_text": output_text,
            "output_text_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            "output_characters": len(output_text),
        }
        self._append_call(row)
        self._active_calls.append(row)
        if previous_model and response_model != previous_model:
            raise RuntimeError(
                "Server-reported model changed within the registered run: "
                f"{previous_model!r} -> {response_model!r}. The response was logged; "
                "use a new output directory."
            )
        return output_text


def make_gemini_generate_content_answerer_class(
    baseline_answerer_class: Type[Any],
) -> Type[GeminiGenerateContentAnswererMixin]:
    """Bind the API call adapter to the exact frozen baseline implementation."""

    if not hasattr(baseline_answerer_class, "generate"):
        raise TypeError("The baseline answerer class must provide generate().")
    return type(
        "GeminiGenerateContentGenerativeAnswerer",
        (GeminiGenerateContentAnswererMixin, baseline_answerer_class),
        {"__module__": __name__},
    )


def summarize_usage(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate Gemini token fields without assuming every field is present."""

    fields = (
        "prompt_token_count",
        "candidates_token_count",
        "thoughts_token_count",
        "total_token_count",
        "cached_content_token_count",
        "tool_use_prompt_token_count",
    )
    totals: MutableMapping[str, int] = {field: 0 for field in fields}
    observed: MutableMapping[str, int] = {field: 0 for field in fields}
    for row in rows:
        usage = dict(row.get("usage", {}) or {})
        for field in fields:
            value = usage.get(field)
            if isinstance(value, (int, float)):
                totals[field] += int(value)
                observed[field] += 1
    return {
        "api_calls": len(rows),
        "totals": dict(totals),
        "calls_with_field": dict(observed),
    }
