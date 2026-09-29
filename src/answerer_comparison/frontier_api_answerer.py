"""Auditable OpenAI Responses API adapter for the frozen RQ2 answerer.

The adapter is deliberately a mixin rather than a second implementation of
the generative baseline.  ``make_openai_responses_answerer_class`` combines it
with the frozen ``BaselineGenerativeAnswerer`` class at run time, so prompt
construction, JSON parsing, fail-closed normalization, and parse retries remain
the exact registered implementation.  Only the model call is replaced.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence, Type


LOG_SCHEMA_VERSION = "compliancegpt-frontier-api-call-v1"


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
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
    """Read and structurally validate an append-only API response log."""

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


class OpenAIResponsesAnswererMixin:
    """Replace only ``_call_model`` while inheriting the frozen answerer logic."""

    def __init__(
        self,
        *,
        client: Any,
        model_id: str,
        system_prompt: str,
        query_id_by_question: Mapping[str, str],
        call_log_path: Path,
        reasoning_effort: str = "low",
        max_output_tokens: int = 2048,
        max_parse_retries: int = 2,
        store: bool = False,
    ) -> None:
        # Do not call the local-model parent's constructor.  It creates a
        # Transformers GenerationConfig and requires a tokenizer/model that do
        # not participate in this API experiment.
        self.client = client
        self.model_id = str(model_id)
        self.system_prompt = str(system_prompt)
        self.reasoning_effort = str(reasoning_effort)
        self.max_output_tokens = int(max_output_tokens)
        self.max_parse_retries = int(max_parse_retries)
        self.store = bool(store)
        self.call_log_path = Path(call_log_path)
        self.query_id_by_question = {
            str(question): str(query_id)
            for question, query_id in query_id_by_question.items()
        }
        if len(self.query_id_by_question) != len(query_id_by_question):
            raise ValueError("Question-to-query-id map contains duplicate questions.")
        if not self.model_id:
            raise ValueError("A Responses API model id is required.")
        if self.max_output_tokens < 1:
            raise ValueError("max_output_tokens must be positive.")
        if self.max_parse_retries < 0:
            raise ValueError("max_parse_retries cannot be negative.")
        if self.store:
            raise ValueError("This registered experiment requires store=False.")

        self._active_query_id = ""
        self._active_question_sha256 = ""
        self._active_calls: List[Dict[str, Any]] = []
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
                "request_model": self.model_id,
                "reasoning_effort": self.reasoning_effort,
                "max_output_tokens": self.max_output_tokens,
                "store": self.store,
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
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.monotonic()
        try:
            output = dict(super().generate(query, docs))  # type: ignore[misc]
        finally:
            elapsed_seconds = time.monotonic() - started
        output["api_provenance"] = {
            "request_model": self.model_id,
            "response_model": self._resolved_model,
            "query_id": self._active_query_id,
            "question_sha256": self._active_question_sha256,
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
            "max_parse_retries": self.max_parse_retries,
            "store": self.store,
            "tools_enabled": False,
            "structured_output_enforced": False,
            "started_at_utc": started_at,
            "elapsed_seconds": elapsed_seconds,
            "api_calls": list(self._active_calls),
        }
        return output

    def _call_model(self, messages: List[Dict[str, str]]) -> str:
        request_hash = canonical_sha256(messages)
        call_started = time.monotonic()
        response = self.client.responses.create(
            model=self.model_id,
            input=messages,
            reasoning={"effort": self.reasoning_effort},
            max_output_tokens=self.max_output_tokens,
            store=self.store,
        )
        latency_seconds = time.monotonic() - call_started
        output_text = str(getattr(response, "output_text", "") or "").strip()
        response_id = str(getattr(response, "id", "") or "").strip()
        response_model = str(getattr(response, "model", "") or "").strip()
        if not response_id:
            raise RuntimeError("Responses API result did not include a response id.")
        if not response_model:
            raise RuntimeError("Responses API result did not include a server-reported model.")
        previous_model = self._resolved_model
        if not self._resolved_model:
            self._resolved_model = response_model

        row: Dict[str, Any] = {
            "schema_version": LOG_SCHEMA_VERSION,
            "logged_at_utc": datetime.now(timezone.utc).isoformat(),
            "query_id": self._active_query_id,
            "question_sha256": self._active_question_sha256,
            "call_index_for_question": len(self._active_calls) + 1,
            "request_model": self.model_id,
            "response_model": response_model,
            "response_id": response_id,
            "response_created_at": _jsonable(getattr(response, "created_at", None)),
            "response_status": str(getattr(response, "status", "") or ""),
            "request_messages_sha256": request_hash,
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
            "store": self.store,
            "tools_enabled": False,
            "structured_output_enforced": False,
            "latency_seconds": latency_seconds,
            "usage": _jsonable(getattr(response, "usage", None)),
            "incomplete_details": _jsonable(getattr(response, "incomplete_details", None)),
            "error": _jsonable(getattr(response, "error", None)),
            "output_text": output_text,
            "output_text_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            "output_characters": len(output_text),
        }
        self._append_call(row)
        self._active_calls.append(row)
        if previous_model and response_model != previous_model:
            raise RuntimeError(
                "Server-reported model changed within the registered run: "
                f"{previous_model!r} -> {response_model!r}. The billed response was logged; "
                "use a new output directory."
            )
        return output_text


def make_openai_responses_answerer_class(
    baseline_answerer_class: Type[Any],
) -> Type[OpenAIResponsesAnswererMixin]:
    """Bind the API call adapter to the exact frozen baseline implementation."""

    if not hasattr(baseline_answerer_class, "generate"):
        raise TypeError("The baseline answerer class must provide generate().")
    return type(
        "OpenAIResponsesGenerativeAnswerer",
        (OpenAIResponsesAnswererMixin, baseline_answerer_class),
        {"__module__": __name__},
    )


def summarize_usage(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """Aggregate token fields without assuming every API version exposes details."""

    fields = ("input_tokens", "output_tokens", "total_tokens")
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
