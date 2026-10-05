#!/usr/bin/env python3
"""Run a registered, separate natural-question study on a CUDA GPU."""
from __future__ import annotations

import argparse
import copy
import gc
import json
import os
import platform
import subprocess
import sys
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from review_and_freeze import (FOLDER, REPO, canonical_sha, read_jsonl, sha,
                               validate_registration, write_json, write_jsonl)


def public_registration(head):
    relative = FOLDER.relative_to(REPO) / "registration.json"
    url = f"https://raw.githubusercontent.com/Wenjia1215/ComplianceGPT/{head}/{relative.as_posix()}"
    with urllib.request.urlopen(url, timeout=30) as response:
        remote = json.loads(response.read())
    if remote != json.loads((FOLDER / "registration.json").read_text()):
        raise ValueError("The exact checkout registration is not publicly retrievable")
    return url


def require_gpu(torch):
    if not torch.cuda.is_available():
        raise RuntimeError("Formal execution requires a CUDA GPU. Select an A100 Colab runtime.")
    if not torch.cuda.is_bf16_supported():
        raise RuntimeError("The registered answerer precision is BF16. Select a supporting GPU.")


def validate_context_authority(context, records):
    """Checkpoint digests alone cannot establish that evidence is canonical."""
    for field in ["retrieved_docs", "evidence_window"]:
        for doc in context.get(field, []):
            record = records.get(doc.get("id"))
            if record is None or any(doc.get(key) != record.get(key)
                                     for key in ["text", "kind", "control_id"]):
                raise ValueError("Checkpoint evidence differs from the registered canonical catalog")


def attach_generation_capture(pipeline, capture_path, active):
    """Capture every prompt/output token sequence, including parse retries."""
    model = pipeline.model
    if not getattr(model, "_natural_capture_attached", False):
        original_generate = model.generate

        def generate(*args, **kwargs):
            inputs = kwargs.get("input_ids", args[0] if args else None)
            config = kwargs.get("generation_config")
            event = dict(active)
            event["started_at_utc"] = datetime.now(timezone.utc).isoformat()
            event["input_ids"] = inputs.detach().cpu().tolist() if inputs is not None else None
            event["attention_mask"] = (kwargs["attention_mask"].detach().cpu().tolist()
                                       if kwargs.get("attention_mask") is not None else None)
            event["generation_config"] = config.to_dict() if config is not None else None
            try:
                result = original_generate(*args, **kwargs)
                sequences = result.sequences if hasattr(result, "sequences") else result
                event["output_ids"] = sequences.detach().cpu().tolist()
                event["decoded_output"] = pipeline.tokenizer.batch_decode(
                    sequences.detach().cpu(), skip_special_tokens=False)
                event["ok"] = True
                return result
            except Exception as e:
                event["ok"] = False
                event["error_type"] = type(e).__name__
                event["error_message"] = str(e)
                raise
            finally:
                event["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
                capture_path.parent.mkdir(parents=True, exist_ok=True)
                with capture_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
                    f.flush()
                    os.fsync(f.fileno())

        model.generate = generate
        model._natural_capture_attached = True
    original_answer = pipeline.answer

    def answer(*args, **kwargs):
        context = kwargs.get("prepared_context") or {}
        active.clear()
        active.update({"query_id": context.get("query_id"), "framework_version": context.get("framework_version"),
                       "context_sha256": context.get("context_sha256"),
                       "system": type(pipeline).__name__})
        return original_answer(*args, **kwargs)

    pipeline.answer = answer


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()
    protocol, questions, _labels, registration = validate_registration()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    if subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=no"], cwd=REPO, text=True):
        raise ValueError("Commit the frozen registration and executable files before formal execution")
    public_url = public_registration(head)
    if args.preflight_only:
        print(json.dumps({"registered_questions": len(questions), "source_commit": head,
                          "public_registration": public_url, "inference_performed": False}))
        return
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.environ.update({"USE_TORCH": "1", "USE_TF": "0", "USE_FLAX": "0",
                       "TOKENIZERS_PARALLELISM": "false", "HF_HUB_DISABLE_TELEMETRY": "1"})
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    sys.path[:0] = [str(REPO / "src"), str(REPO)]
    import torch
    require_gpu(torch)
    from huggingface_hub import snapshot_download
    from answerer_comparison.matched_window_runner import (
        FrozenCCSRetriever, build_prepared_context, load_context_file,
        run_prepared_contexts, validate_paired_outputs, validate_prepared_context)
    from compliancegpt.retriever.retriever_s7 import ComplianceGPTRetriever, RetrievalConfig
    from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline
    from generative_answerer.pipeline import BaselineGenerativeRAGPipeline
    from experiments.answerer_comparison.rq2_matched.run_matched_rq2 import (
        configure_determinism, pipeline_kwargs)

    determinism = configure_determinism()
    packages = {name: version(name) for name in ["torch", "transformers", "sentence-transformers",
               "huggingface-hub", "accelerate", "numpy", "pandas", "faiss-cpu", "PyYAML"]}
    signature = {"result_id": protocol["result_id"], "source_commit": head,
                 "registration_sha256": sha(FOLDER / "registration.json"),
                 "protocol_sha256": sha(FOLDER / "protocol.json"),
                 "code_sha256": registration["code_sha256"], "models": protocol["models"],
                 "inputs": protocol["inputs"], "python": platform.python_version(),
                 "packages": packages, "gpu": torch.cuda.get_device_name(0),
                 "gpu_memory_bytes": torch.cuda.get_device_properties(0).total_memory,
                 "cuda": torch.version.cuda, "determinism": determinism}
    identity = canonical_sha(signature)
    config_path = output / "run_config.json"
    if config_path.exists():
        if json.loads(config_path.read_text())["signature_sha256"] != identity:
            raise ValueError("Runtime/source/registration differs from this checkpoint. Use a new result version.")
    else:
        if any(output.rglob("*.csv")) or any(output.rglob("*.jsonl")):
            raise ValueError("Existing outcome files have no compatible run configuration")
        write_json(config_path, {"signature": signature, "signature_sha256": identity,
                               "public_registration": public_url,
                               "started_at_utc": datetime.now(timezone.utc).isoformat()})

    snapshots = {}
    for kind in ["dense", "reranker"]:
        spec = protocol["models"][kind]
        print(f"Loading pinned {kind}: {spec['id']} at {spec['revision']}", flush=True)
        snapshots[kind] = Path(snapshot_download(spec["id"], revision=spec["revision"],
                                               allow_patterns=["*.json", "*.txt", "*.safetensors", "*.bin", "*.model"]))
    write_json(output / "model_snapshot_files.json", {
        kind: {str(f.relative_to(path)): sha(f) for f in sorted(path.rglob("*")) if f.is_file()}
        for kind, path in snapshots.items()})
    contexts = {}
    for rev in sorted({q["framework_version"] for q in questions}):
        rows = [q for q in questions if q["framework_version"] == rev]
        ccs_path = REPO / protocol["inputs"][rev]["ccs"]["path"]
        canonical_records = {r["id"]: r for r in read_jsonl(ccs_path)}
        context_path = output / "contexts" / f"{rev}.jsonl"
        if context_path.exists():
            contexts[rev] = load_context_file(context_path)
        else:
            partial_path = context_path.with_suffix(".partial.jsonl")
            captured = read_jsonl(partial_path) if partial_path.exists() else []
            if [c["query_id"] for c in captured] != [q["query_id"] for q in rows[:len(captured)]]:
                raise ValueError("Partial retrieval checkpoint changed its question identities/order")
            for q, context in zip(rows, captured):
                validate_prepared_context(context)
                validate_context_authority(context, canonical_records)
                if context["question"] != q["question"] or context["framework_version"] != rev:
                    raise ValueError("Partial retrieval checkpoint changed a question or revision")
            cfg = RetrievalConfig(dense_model_id=str(snapshots["dense"]),
                                  reranker_model_id=str(snapshots["reranker"]))
            retriever = ComplianceGPTRetriever(ccs_path=str(ccs_path), config=cfg)
            for q in rows[len(captured):]:
                docs, meta = retriever.retrieve_debug(q["question"], top_k=12, rewrites=[])
                if not docs:
                    raise RuntimeError(f"{q['query_id']}: empty retrieval needs a new explicit protocol treatment")
                contract = {"question": q["question"], "debug": {
                    "retrieval_meta": copy.deepcopy(meta),
                    "query_plan": {"original_query": q["question"], "rewrites": []}}}
                context = build_prepared_context(query_id=q["query_id"], framework_version=rev,
                                                contract=contract, ccs_by_id=retriever.record_by_id)
                captured.append(context)
                partial_path.parent.mkdir(parents=True, exist_ok=True)
                with partial_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(context, ensure_ascii=False, sort_keys=True) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
                print(f"Captured {q['query_id']} {rev} matched retrieval context", flush=True)
            context_path.parent.mkdir(parents=True, exist_ok=True)
            partial_path.replace(context_path)
            contexts[rev] = captured
            write_json(output / "contexts" / f"{rev}_retrieval_config.json", asdict(cfg))
            del retriever
            gc.collect()
            torch.cuda.empty_cache()
        if [c["query_id"] for c in contexts[rev]] != [q["query_id"] for q in rows]:
            raise ValueError("Checkpoint context rows/order changed")
        for q, context in zip(rows, contexts[rev]):
            validate_prepared_context(context)
            validate_context_authority(context, canonical_records)
            if context["question"] != q["question"] or context["framework_version"] != rev:
                raise ValueError("Checkpoint context no longer matches the registered question")
    # Context checkpoints are re-hashed before answerer resume, preventing drift in either path.
    context_hashes = {rev: sha(output / "contexts" / f"{rev}.jsonl") for rev in contexts}
    lock_path = output / "context_file_hashes.json"
    if lock_path.exists() and json.loads(lock_path.read_text()) != context_hashes:
        raise ValueError("Immutable context files changed since the answerer phase began")
    write_json(lock_path, context_hashes)
    # The default pipeline loader uses FP16 even with load_in_4bit=False.
    # Load the declared BF16 model explicitly once and inject it into both paths.
    from transformers import AutoModelForCausalLM, AutoTokenizer
    spec = protocol["models"]["answerer"]
    answerer_snapshot = Path(snapshot_download(spec["id"], revision=spec["revision"],
                                              allow_patterns=["*.json", "*.txt", "*.safetensors", "*.model"]))
    model = AutoModelForCausalLM.from_pretrained(spec["id"], revision=spec["revision"],
                                               torch_dtype=torch.bfloat16,
                                               device_map={"": "cuda:0"}, trust_remote_code=False)
    tokenizer = AutoTokenizer.from_pretrained(spec["id"], revision=spec["revision"], trust_remote_code=False)
    dtypes = {str(p.dtype) for p in model.parameters() if p.is_floating_point()}
    if dtypes != {str(torch.bfloat16)} or any(p.device.type != "cuda" for p in model.parameters()):
        raise ValueError("The loaded answerer does not match the declared BF16 CUDA configuration")
    if str(getattr(model.config, "_commit_hash", "")) != spec["revision"]:
        raise ValueError("Answerer revision did not resolve to the registered commit")
    write_json(output / "answerer_model_files.json", {
        str(f.relative_to(answerer_snapshot)): sha(f) for f in sorted(answerer_snapshot.rglob("*")) if f.is_file()})
    shared = (model, tokenizer)
    active = {}
    runs = {}
    for system, cls in [("compliancegpt", ComplianceGPTPipeline),
                        ("generative_baseline", BaselineGenerativeRAGPipeline)]:
        for rev, prepared in contexts.items():
            frozen = FrozenCCSRetriever.from_jsonl(REPO / protocol["inputs"][rev]["ccs"]["path"])
            spec = protocol["models"]["answerer"]
            pipeline = cls(**pipeline_kwargs(repo_root=REPO, revision=rev, model_id=spec["id"],
                                             model_revision=spec["revision"], retriever=frozen,
                                             load_in_4bit=False, shared=shared))
            attach_generation_capture(pipeline, output / "generation_calls.jsonl", active)
            # Only a non-label identity row reaches the legacy runtime verifier. Actual
            # author control/clause/ODP judgments enter the separate offline scorer.
            identity_rows = {c["query_id"]: {"query_id": c["query_id"]} for c in prepared}
            runs[f"{rev}_{system}"] = run_prepared_contexts(
                pipeline=pipeline, contexts=prepared, gold_rows_by_id=identity_rows,
                system_name=system, output_csv=output / "contracts" / f"{rev}_{system}.csv")
            write_json(output / "run_manifests.json", runs)
            del pipeline, frozen
            gc.collect()
            torch.cuda.empty_cache()
    pairs = {}
    for rev, prepared in contexts.items():
        pairs[rev] = validate_paired_outputs(
            output / "contracts" / f"{rev}_compliancegpt.csv",
            output / "contracts" / f"{rev}_generative_baseline.csv")
        if pairs[rev]["paired_rows"] != len(prepared):
            raise ValueError("Paired comparison is incomplete")
    write_json(output / "paired_identity_audit.json", pairs)
    from score_results import score_folder
    score_folder(output)
    write_json(output / "SHA256SUMS.json", {
        str(f.relative_to(output)): sha(f) for f in sorted(output.rglob("*"))
        if f.is_file() and f.name != "SHA256SUMS.json"})
    print("Automatic natural-question outcomes completed. Post-run scope/semantic review is pending.", flush=True)


if __name__ == "__main__":
    main()
