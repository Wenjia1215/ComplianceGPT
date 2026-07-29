"""Versioned RQ2 runner with immutable, shared model-visible evidence windows."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import platform
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from compliancegpt.pipeline.evidence_window import (
    assert_same_evidence_window,
    build_evidence_window,
    evidence_window_manifest,
    select_allowed_controls,
)
from compliancegpt.pipeline.pipeline import (
    _apply_doc_filter_mode,
    _filter_docs_to_controls,
    normalize_control_id,
)


CONTEXT_SCHEMA = "compliancegpt-rq2-prepared-context"
RUN_SCHEMA = "compliancegpt-rq2-matched-run"

RUN_FIELDNAMES = [
    "query_id",
    "framework_version",
    "system",
    "question",
    "context_sha256",
    "evidence_window_sha256",
    "evidence_window_source_ids",
    "model_id",
    "model_requested_revision",
    "model_resolved_revision",
    "tokenizer_resolved_revision",
    "status",
    "verifier_pass",
    "verifier_errors",
    "verifier_metrics_json",
    "control_hit_any",
    "doc_hit_any",
    "doc_full_recall",
    "has_evidence_spans",
    "evidence_span_count",
    "verbatim_strict_pass_rate",
    "verbatim_normalized_pass_rate",
    "contract_validity_pass",
    "primary_citation",
    "all_citations",
    "odp_required_list",
    "selected_source_ids",
    "contract_json",
]


class FrozenCCSRetriever:
    """Read-only CCS inventory for prepared-context answerer runs.

    The object intentionally refuses retrieval calls.  Its only purpose is to
    provide the canonical records needed for citation filling, ODP
    canonicalization, hierarchy lookup, and verification after the evidence
    window has already been frozen.
    """

    def __init__(self, records: Mapping[str, Mapping[str, Any]]) -> None:
        self.record_by_id = {str(key): dict(value) for key, value in records.items()}
        self.ids = list(self.record_by_id)
        self.last_meta: Dict[str, Any] = {}

    @classmethod
    def from_jsonl(cls, path: os.PathLike[str] | str) -> "FrozenCCSRetriever":
        return cls(load_ccs(path))

    def retrieve(self, *_args: Any, **_kwargs: Any) -> List[Dict[str, Any]]:
        raise RuntimeError("Live retrieval is forbidden in a prepared-context RQ2 run.")

    def retrieve_debug(self, *_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("Live retrieval is forbidden in a prepared-context RQ2 run.")


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_sha256(path: os.PathLike[str] | str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: os.PathLike[str] | str, value: Any) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def load_gold_rows(
    path: os.PathLike[str] | str,
    *,
    expected_rows: Optional[int] = None,
) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), start=2):
            query_id = ""
            for key in ("query_id", "ID", "id"):
                if row.get(key) is not None and str(row.get(key, "")).strip():
                    query_id = str(row[key]).strip()
                    break
            if not query_id:
                raise ValueError(f"Gold row {row_number} has no query identifier: {path}")
            if query_id in rows:
                raise ValueError(f"Duplicate gold query id {query_id!r}: {path}")
            rows[query_id] = dict(row)
    if expected_rows is not None and len(rows) != int(expected_rows):
        raise AssertionError(f"Expected {expected_rows} gold rows, loaded {len(rows)}: {path}")
    return rows


def load_ccs(path: os.PathLike[str] | str) -> Dict[str, Dict[str, Any]]:
    records: Dict[str, Dict[str, Any]] = {}
    with open(path, "r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            source_id = str(record.get("id", "") or "").strip()
            if not source_id:
                raise ValueError(f"CCS record at line {line_number} has no id: {path}")
            if source_id in records:
                raise ValueError(f"Duplicate CCS id {source_id!r}: {path}")
            records[source_id] = dict(record)
    if not records:
        raise ValueError(f"No CCS records loaded: {path}")
    return records


def reconstruct_retrieved_docs(
    contract: Mapping[str, Any],
    ccs_by_id: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Rebuild the frozen retrieved-document order from a stored contract trace."""

    debug = dict(contract.get("debug", {}) or {})
    retrieval_meta = dict(debug.get("retrieval_meta", {}) or {})
    by_control = dict(retrieval_meta.get("selected_clause_ids_by_control", {}) or {})
    selected_controls = list(retrieval_meta.get("selected_controls", []) or [])
    if not by_control:
        raise ValueError("Stored contract lacks selected_clause_ids_by_control.")

    ordered_keys: List[str] = []
    for control in selected_controls:
        key = str(control)
        if key in by_control and key not in ordered_keys:
            ordered_keys.append(key)
    for key in by_control:
        if str(key) not in ordered_keys:
            ordered_keys.append(str(key))

    docs: List[Dict[str, Any]] = []
    seen = set()
    for control in ordered_keys:
        for raw_source_id in list(by_control.get(control, []) or []):
            source_id = str(raw_source_id or "").strip()
            if not source_id or source_id in seen:
                continue
            record = ccs_by_id.get(source_id)
            if record is None:
                raise KeyError(f"Stored retrieval trace references missing CCS id {source_id!r}.")
            seen.add(source_id)
            docs.append(dict(record))

    expected = ((debug.get("counts") or {}).get("retrieved_docs"))
    if expected is None:
        expected = retrieval_meta.get("n_docs")
    if expected is not None and int(expected) != len(docs):
        raise AssertionError(
            f"Reconstructed retrieved-doc count {len(docs)} does not match stored count {expected}."
        )
    return docs


def _context_without_hash(context: Mapping[str, Any]) -> Dict[str, Any]:
    clean = dict(context)
    clean.pop("context_sha256", None)
    return clean


def _gold_key_paths(value: Any, path: str = "") -> List[str]:
    found: List[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{path}.{key_text}" if path else key_text
            if key_text.strip().lower().startswith("gold"):
                found.append(child_path)
            found.extend(_gold_key_paths(child, child_path))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            child_path = f"{path}[{index}]" if path else f"[{index}]"
            found.extend(_gold_key_paths(child, child_path))
    return found


def validate_prepared_context(context: Mapping[str, Any]) -> None:
    if str(context.get("schema_version", "")) != CONTEXT_SCHEMA:
        raise ValueError("Unexpected prepared-context schema.")
    if not str(context.get("question", "") or "").strip():
        raise ValueError("Prepared context has no question.")
    if str(context.get("framework_version", "")) not in {"rev4", "rev5"}:
        raise ValueError("Prepared context has an invalid framework revision.")
    if not list(context.get("retrieved_docs", []) or []):
        raise ValueError("Prepared context has no retrieved documents.")
    locked_docs = list(context.get("evidence_window", []) or [])
    manifest = evidence_window_manifest(locked_docs)
    assert_same_evidence_window(manifest, dict(context.get("evidence_window_manifest", {}) or {}))
    expected_hash = _canonical_sha256(_context_without_hash(context))
    if str(context.get("context_sha256", "")) != expected_hash:
        raise AssertionError("Prepared-context hash does not match its contents.")
    forbidden = _gold_key_paths(context)
    if forbidden:
        raise ValueError(f"Gold fields are forbidden anywhere in prepared model contexts: {forbidden}")


def build_prepared_context(
    *,
    query_id: str,
    framework_version: str,
    contract: Mapping[str, Any],
    ccs_by_id: Mapping[str, Mapping[str, Any]],
    gen_control_gate_topn: int = 1,
    gen_control_gate_lowconf_top2: float = 0.08,
    gen_control_gate_lowconf_top3: float = 0.04,
    gen_control_gate_lowconf_maxn: int = 3,
    doc_filter_mode: str = "prefer_smt_keep_params",
    gen_docs_k: int = 24,
    primary_first_min_margin_ratio: float = 0.06,
) -> Dict[str, Any]:
    debug = dict(contract.get("debug", {}) or {})
    retrieval_meta = dict(debug.get("retrieval_meta", {}) or {})
    query_plan = dict(debug.get("query_plan", {}) or {})
    question = str(contract.get("question", "") or query_plan.get("original_query", "") or "").strip()
    rewrites = [str(value).strip() for value in list(query_plan.get("rewrites", []) or []) if str(value).strip()]
    retrieved_docs = reconstruct_retrieved_docs(contract, ccs_by_id)

    controls, primary_control, allowed_controls, widen_tier = select_allowed_controls(
        retrieved_docs=retrieved_docs,
        retrieval_meta=retrieval_meta,
        normalize_control_id=normalize_control_id,
        topn=gen_control_gate_topn,
        lowconf_top2=gen_control_gate_lowconf_top2,
        lowconf_top3=gen_control_gate_lowconf_top3,
        lowconf_maxn=gen_control_gate_lowconf_maxn,
    )
    window, audit = build_evidence_window(
        retrieved_docs=retrieved_docs,
        retrieval_meta=retrieval_meta,
        allowed_controls=allowed_controls,
        primary_control=primary_control,
        doc_filter_mode=doc_filter_mode,
        gen_docs_k=gen_docs_k,
        filter_docs_to_controls=_filter_docs_to_controls,
        apply_doc_filter_mode=_apply_doc_filter_mode,
        primary_first_min_margin_ratio=primary_first_min_margin_ratio,
    )

    context: Dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA,
        "query_id": str(query_id),
        "framework_version": str(framework_version).strip().lower(),
        "question": question,
        "rewrites": rewrites,
        "retrieved_docs": retrieved_docs,
        "retrieval_meta": retrieval_meta,
        "control_gate": {
            "normalized_controls": controls,
            "primary_control": primary_control,
            "allowed_controls": allowed_controls,
            "widen_tier": widen_tier,
        },
        "window_config": {
            "doc_filter_mode": doc_filter_mode,
            "gen_docs_k": int(gen_docs_k),
            "primary_first_min_margin_ratio": float(primary_first_min_margin_ratio),
        },
        "evidence_window": window,
        "evidence_window_manifest": audit["evidence_window"],
    }
    context["context_sha256"] = _canonical_sha256(context)
    validate_prepared_context(context)
    return context


def build_context_file(
    *,
    contracts_csv: os.PathLike[str] | str,
    ccs_path: os.PathLike[str] | str,
    output_jsonl: os.PathLike[str] | str,
    framework_version: str,
    expected_rows: int,
) -> Dict[str, Any]:
    ccs_by_id = load_ccs(ccs_path)
    contexts: List[Dict[str, Any]] = []
    with open(contracts_csv, "r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            contract = json.loads(str(row.get("contract_json", "") or "{}"))
            query_id = str(row.get("query_id", "") or contract.get("query_id", ""))
            contexts.append(
                build_prepared_context(
                    query_id=query_id,
                    framework_version=framework_version,
                    contract=contract,
                    ccs_by_id=ccs_by_id,
                )
            )

    if len(contexts) != int(expected_rows):
        raise AssertionError(f"Expected {expected_rows} contexts, built {len(contexts)}.")
    keys = [(item["framework_version"], item["query_id"]) for item in contexts]
    if len(keys) != len(set(keys)):
        raise AssertionError("Prepared contexts contain duplicate revision/query keys.")

    output = Path(output_jsonl)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for context in contexts:
            handle.write(json.dumps(context, ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "schema_version": CONTEXT_SCHEMA,
        "framework_version": framework_version,
        "row_count": len(contexts),
        "contracts_csv": str(contracts_csv),
        "contracts_csv_sha256": file_sha256(contracts_csv),
        "ccs_path": str(ccs_path),
        "ccs_sha256": file_sha256(ccs_path),
        "context_jsonl": str(output),
        "context_jsonl_sha256": file_sha256(output),
        "window_hashes_sha256": _canonical_sha256(
            [item["evidence_window_manifest"]["sha256"] for item in contexts]
        ),
    }


def load_context_file(path: os.PathLike[str] | str) -> List[Dict[str, Any]]:
    contexts: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            context = json.loads(line)
            validate_prepared_context(context)
            contexts.append(context)
    return contexts


def runtime_metadata(pipeline: Any) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "model_id": str(getattr(pipeline, "model_id", "") or ""),
        "model_requested_revision": str(getattr(pipeline, "model_revision", "") or ""),
        "model_resolved_revision": str(getattr(pipeline, "model_resolved_revision", "") or ""),
        "tokenizer_resolved_revision": str(
            getattr(pipeline, "tokenizer_resolved_revision", "") or ""
        ),
    }
    try:
        import torch  # type: ignore

        metadata.update(
            {
                "torch": str(torch.__version__),
                "cuda_available": bool(torch.cuda.is_available()),
                "cuda_version": str(torch.version.cuda or ""),
                "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
            }
        )
    except Exception as error:
        metadata["torch_error"] = repr(error)
    try:
        import transformers  # type: ignore

        metadata["transformers"] = str(transformers.__version__)
    except Exception as error:
        metadata["transformers_error"] = repr(error)
    try:
        from importlib.metadata import version

        metadata["packages"] = {
            name: version(name)
            for name in (
                "accelerate",
                "bitsandbytes",
                "huggingface-hub",
                "numpy",
                "pandas",
                "pyyaml",
                "tqdm",
                "transformers",
            )
        }
    except Exception as error:
        metadata["package_metadata_error"] = repr(error)
    return metadata


def run_prepared_contexts(
    *,
    pipeline: Any,
    contexts: Sequence[Mapping[str, Any]],
    gold_rows_by_id: Mapping[str, Mapping[str, Any]],
    system_name: str,
    output_csv: os.PathLike[str] | str,
    top_k: int = 12,
    resume: bool = True,
    progress_every: int = 1,
) -> Dict[str, Any]:
    """Run one answer path over locked contexts with row-level checkpoints."""

    runtime = runtime_metadata(pipeline)
    model_fields = {
        "model_id": str(runtime.get("model_id", "") or ""),
        "model_requested_revision": str(runtime.get("model_requested_revision", "") or ""),
        "model_resolved_revision": str(runtime.get("model_resolved_revision", "") or ""),
        "tokenizer_resolved_revision": str(runtime.get("tokenizer_resolved_revision", "") or ""),
    }
    output = Path(output_csv)
    output.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    if output.exists() and resume:
        with output.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if list(reader.fieldnames or []) != RUN_FIELDNAMES:
                raise ValueError(f"Existing checkpoint has an unexpected schema: {output}")
            rows = list(reader)
    elif output.exists():
        output.unlink()

    context_by_id = {str(context["query_id"]): context for context in contexts}
    if len(context_by_id) != len(contexts):
        raise AssertionError("Prepared contexts contain duplicate query ids.")

    completed = set()
    for row in rows:
        query_id = str(row.get("query_id", "") or "")
        if query_id in completed:
            raise AssertionError(f"Checkpoint contains duplicate query id {query_id!r}.")
        context = context_by_id.get(query_id)
        if context is None:
            raise AssertionError(f"Checkpoint query id {query_id!r} is not in the prepared contexts.")
        if str(row.get("system", "")) != str(system_name):
            raise AssertionError("Checkpoint system name does not match this run.")
        if str(row.get("context_sha256", "")) != str(context.get("context_sha256", "")):
            raise AssertionError(f"Checkpoint context hash changed for query {query_id!r}.")
        if str(row.get("evidence_window_sha256", "")) != str(
            (context.get("evidence_window_manifest") or {}).get("sha256", "")
        ):
            raise AssertionError(f"Checkpoint evidence window changed for query {query_id!r}.")
        for key, expected in model_fields.items():
            if str(row.get(key, "")) != expected:
                raise AssertionError(f"Checkpoint {key} does not match the current model runtime.")
        completed.add(query_id)
    resumed_rows = len(completed)

    new_file = not output.exists()
    mode = "w" if new_file else "a"
    with output.open(mode, encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_FIELDNAMES)
        if new_file:
            writer.writeheader()
            handle.flush()
            os.fsync(handle.fileno())

        for position, context in enumerate(contexts, start=1):
            query_id = str(context["query_id"])
            if query_id in completed:
                continue
            validate_prepared_context(context)
            gold_row = dict(gold_rows_by_id.get(query_id, {}) or {})
            if not gold_row:
                raise KeyError(f"No gold row for query id {query_id!r}.")
            answer_output = pipeline.answer(
                str(context["question"]),
                top_k=int(top_k),
                rewrites=list(context.get("rewrites", []) or []),
                gold_row=gold_row,
                use_generator=True,
                run_verify=True,
                prepared_context=dict(context),
            )
            contract = dict(answer_output.get("contract", answer_output) or {})
            actual_window = dict(((contract.get("debug") or {}).get("evidence_window") or {}))
            shared_hash = assert_same_evidence_window(
                dict(context["evidence_window_manifest"]),
                actual_window,
            )
            metrics = dict(contract.get("verifier_metrics", {}) or {})
            evidence_spans = list(contract.get("evidence_spans", []) or [])
            validity = dict(contract.get("validity_check", {}) or {})
            row = {
                "query_id": query_id,
                "framework_version": str(context["framework_version"]),
                "system": str(system_name),
                "question": str(context["question"]),
                "context_sha256": str(context["context_sha256"]),
                "evidence_window_sha256": shared_hash,
                "evidence_window_source_ids": "|".join(actual_window.get("source_ids", []) or []),
                **model_fields,
                "status": str(contract.get("status", "") or ""),
                "verifier_pass": bool(contract.get("verifier_pass", False)),
                "verifier_errors": "|".join(list(contract.get("verifier_errors", []) or [])),
                "verifier_metrics_json": json.dumps(metrics, ensure_ascii=False, sort_keys=True),
                "control_hit_any": float(metrics.get("control_recall", 0.0) or 0.0) > 0.0,
                "doc_hit_any": float(metrics.get("doc_recall", 0.0) or 0.0) > 0.0,
                "doc_full_recall": float(metrics.get("doc_recall", 0.0) or 0.0) >= 1.0,
                "has_evidence_spans": bool(evidence_spans),
                "evidence_span_count": len(evidence_spans),
                "verbatim_strict_pass_rate": metrics.get("verbatim_strict_pass_rate", float("nan")),
                "verbatim_normalized_pass_rate": metrics.get(
                    "verbatim_normalized_pass_rate", float("nan")
                ),
                "contract_validity_pass": bool(validity.get("is_pass", False)),
                "primary_citation": str(contract.get("primary_citation", "") or ""),
                "all_citations": str(contract.get("all_citations", "") or ""),
                "odp_required_list": "|".join(list(contract.get("odp_required_list", []) or [])),
                "selected_source_ids": "|".join(list(contract.get("selected_source_ids", []) or [])),
                "contract_json": json.dumps(contract, ensure_ascii=False),
            }
            writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
            rows.append(row)
            completed.add(query_id)
            if int(progress_every) > 0 and (position % int(progress_every) == 0 or position == len(contexts)):
                print(f"[{system_name}] {len(completed)}/{len(contexts)} completed")

    if len(completed) != len(contexts):
        raise AssertionError(f"Run checkpoint is incomplete: {len(completed)}/{len(contexts)} rows.")

    return {
        "schema_version": RUN_SCHEMA,
        "system": system_name,
        "row_count": len(completed),
        "output_csv": str(output),
        "output_csv_sha256": file_sha256(output),
        "runtime": runtime,
        "resumed_rows": resumed_rows,
    }


def validate_paired_outputs(
    compliance_csv: os.PathLike[str] | str,
    baseline_csv: os.PathLike[str] | str,
) -> Dict[str, Any]:
    def read(path: os.PathLike[str] | str) -> Dict[str, Dict[str, str]]:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        return {str(row["query_id"]): row for row in rows}

    compliance = read(compliance_csv)
    baseline = read(baseline_csv)
    if set(compliance) != set(baseline):
        raise AssertionError("Paired outputs have different query-id sets.")
    mismatches = []
    for query_id in sorted(compliance, key=lambda value: int(value) if value.isdigit() else value):
        left = compliance[query_id]
        right = baseline[query_id]
        if left["context_sha256"] != right["context_sha256"]:
            mismatches.append((query_id, "context"))
        if left["evidence_window_sha256"] != right["evidence_window_sha256"]:
            mismatches.append((query_id, "window"))
        if left["model_id"] != right["model_id"]:
            mismatches.append((query_id, "model_id"))
        if left["model_requested_revision"] != right["model_requested_revision"]:
            mismatches.append((query_id, "model_requested_revision"))
        if left["model_resolved_revision"] != right["model_resolved_revision"]:
            mismatches.append((query_id, "model_resolved_revision"))
        if left["tokenizer_resolved_revision"] != right["tokenizer_resolved_revision"]:
            mismatches.append((query_id, "tokenizer_resolved_revision"))
    if mismatches:
        raise AssertionError(f"Matched RQ2 validation failed: {mismatches[:10]}")
    return {
        "schema_version": RUN_SCHEMA,
        "paired_rows": len(compliance),
        "context_mismatches": 0,
        "evidence_window_mismatches": 0,
        "model_mismatches": 0,
        "model_id": next(iter(compliance.values()))["model_id"] if compliance else "",
        "model_requested_revision": (
            next(iter(compliance.values()))["model_requested_revision"] if compliance else ""
        ),
        "model_resolved_revision": (
            next(iter(compliance.values()))["model_resolved_revision"] if compliance else ""
        ),
        "tokenizer_resolved_revision": (
            next(iter(compliance.values()))["tokenizer_resolved_revision"] if compliance else ""
        ),
        "compliance_csv_sha256": file_sha256(compliance_csv),
        "baseline_csv_sha256": file_sha256(baseline_csv),
    }


def _csv_bool(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "t", "yes", "y"}


def _listish(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return []
    parts = [text]
    for delimiter in ("\r\n", "\n", "|", ","):
        expanded: List[str] = []
        for part in parts:
            expanded.extend(part.split(delimiter))
        parts = expanded
    return [part.strip().lower() for part in parts if part.strip()]


def _exact_mcnemar_pvalue(left_only: int, right_only: int) -> float:
    """Two-sided exact McNemar p-value for a paired binary outcome."""

    discordant = int(left_only) + int(right_only)
    if discordant == 0:
        return 1.0
    tail = sum(math.comb(discordant, index) for index in range(min(left_only, right_only) + 1))
    return min(1.0, 2.0 * tail / (2.0**discordant))


def summarize_paired_outputs(
    *,
    compliance_csv: os.PathLike[str] | str,
    baseline_csv: os.PathLike[str] | str,
    gold_rows_by_id: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """Produce the core paired RQ2 result without depending on pandas/scipy."""

    validation = validate_paired_outputs(compliance_csv, baseline_csv)

    def read(path: os.PathLike[str] | str) -> Dict[str, Dict[str, str]]:
        with open(path, "r", encoding="utf-8", newline="") as handle:
            return {str(row["query_id"]): row for row in csv.DictReader(handle)}

    compliance = read(compliance_csv)
    baseline = read(baseline_csv)
    query_ids = sorted(
        compliance,
        key=lambda value: (0, int(value)) if value.isdigit() else (1, value),
    )

    compliance_pass = sum(_csv_bool(compliance[qid]["verifier_pass"]) for qid in query_ids)
    baseline_pass = sum(_csv_bool(baseline[qid]["verifier_pass"]) for qid in query_ids)
    compliance_only = sum(
        _csv_bool(compliance[qid]["verifier_pass"])
        and not _csv_bool(baseline[qid]["verifier_pass"])
        for qid in query_ids
    )
    baseline_only = sum(
        _csv_bool(baseline[qid]["verifier_pass"])
        and not _csv_bool(compliance[qid]["verifier_pass"])
        for qid in query_ids
    )

    def status_counts(rows: Mapping[str, Mapping[str, str]]) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for qid in query_ids:
            status = str(rows[qid].get("status", "") or "")
            counts[status] = counts.get(status, 0) + 1
        return dict(sorted(counts.items()))

    total = len(query_ids)
    summary: Dict[str, Any] = {
        "schema_version": RUN_SCHEMA,
        "framework_version": (
            str(compliance[query_ids[0]].get("framework_version", "")) if query_ids else ""
        ),
        "n_questions": total,
        "validation": validation,
        "strict_verifier_pass": {
            "compliancegpt_count": compliance_pass,
            "compliancegpt_rate": compliance_pass / total if total else float("nan"),
            "generative_baseline_count": baseline_pass,
            "generative_baseline_rate": baseline_pass / total if total else float("nan"),
        },
        "paired_strict_pass": {
            "compliancegpt_only": compliance_only,
            "generative_baseline_only": baseline_only,
            "exact_mcnemar_two_sided_p": _exact_mcnemar_pvalue(compliance_only, baseline_only),
        },
        "status_counts": {
            "compliancegpt": status_counts(compliance),
            "generative_baseline": status_counts(baseline),
        },
    }

    if gold_rows_by_id is not None:
        odp_ids = [
            qid
            for qid in query_ids
            if _listish(
                (gold_rows_by_id.get(qid, {}) or {}).get(
                    "odp_required",
                    (gold_rows_by_id.get(qid, {}) or {}).get("odp_ids_required", ""),
                )
            )
        ]

        def odp_metrics(rows: Mapping[str, Mapping[str, str]]) -> Dict[str, Any]:
            n = len(odp_ids)
            params_required = sum(rows[qid].get("status") == "PARAMS_REQUIRED" for qid in odp_ids)
            false_complete = sum(rows[qid].get("status") == "OK" for qid in odp_ids)
            exact_list = sum(
                set(_listish(rows[qid].get("odp_required_list", "")))
                == set(
                    _listish(
                        (gold_rows_by_id.get(qid, {}) or {}).get(
                            "odp_required",
                            (gold_rows_by_id.get(qid, {}) or {}).get("odp_ids_required", ""),
                        )
                    )
                )
                for qid in odp_ids
            )
            return {
                "n": n,
                "params_required_count": params_required,
                "params_required_rate": params_required / n if n else float("nan"),
                "false_complete_count": false_complete,
                "false_complete_rate": false_complete / n if n else float("nan"),
                "exact_odp_list_count": exact_list,
                "exact_odp_list_rate": exact_list / n if n else float("nan"),
            }

        summary["odp_subset"] = {
            "compliancegpt": odp_metrics(compliance),
            "generative_baseline": odp_metrics(baseline),
        }

    return summary
