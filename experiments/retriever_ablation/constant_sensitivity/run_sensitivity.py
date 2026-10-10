#!/usr/bin/env python3
"""Register, capture, and replay the primary RQ1 constant-sensitivity study."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from experiments.retriever_ablation.constant_sensitivity import primary_adapter as primary
from experiments.retriever_ablation.constant_sensitivity.statistics import rank_metrics, describe, paired

RESULT_ID = "rq1_constant_sensitivity_v1"
MODELS = {"dense": {"model_id": "intfloat/e5-small-v2", "revision": "ffb93f3bd4047442299a41ebb6fa998a38507c52"},
          "reranker": {"model_id": "BAAI/bge-reranker-base", "revision": "2cfc18c9415c912f9d8155881c133215df768a70"}}
SOURCE_PATHS = ("primary_adapter.py", "statistics.py", "run_sensitivity.py", "PROTOCOL.md", "requirements-colab.txt")
TEST_PATH = "tests/test_rq1_constant_sensitivity.py"
BASE = "experiments/retriever_ablation/constant_sensitivity"
INPUTS = {revision: {
    "ccs": f"data/ccs/nist800-53/NIST_SP-800-53_{revision}_catalog.jsonl",
    "gold": f"data/gold_standard_datasets/nist800-53/nist_sp800-53_{revision}_gold-set_{count}q.csv",
    "rewrites": f"data/qur_outputs/qur_rewrites_{revision}.csv",
    "historical": f"experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_{revision}_results.csv",
} for revision, count in (("rev4", 36), ("rev5", 100))}


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def read_csv(path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def manifests(repo):
    paths = [primary.NOTEBOOK] + [p for revision in INPUTS.values() for p in revision.values()]
    code = [f"{BASE}/{p}" for p in SOURCE_PATHS] + [TEST_PATH]
    return {p: sha(repo / p) for p in paths}, {p: sha(repo / p) for p in code}


def registered_queries(repo, namespace):
    queries = []
    for revision, paths in INPUTS.items():
        gold = read_csv(repo / paths["gold"])
        historical = {r["question_id"]: r for r in read_csv(repo / paths["historical"])}
        rewrites = read_csv(repo / paths["rewrites"])
        if len(gold) != (36 if revision == "rev4" else 100) or {r["id"] for r in gold} != set(historical):
            raise AssertionError("Historical query population changed")
        for row in gold:
            question = row["question"]
            old = historical[row["id"]]
            if old["question"] != question or namespace["normalize_control_id"](old["gold_control_id"]) != namespace["normalize_control_id"](row["control_id"]):
                raise AssertionError("Historical question or governing-control label differs")
            key = namespace["strict_clean"](question)
            frozen = [r["rewritten_query"] for r in rewrites if namespace["strict_clean"](r["original_query"]) == key]
            variants = namespace["get_qur_variants_filtered"](
                question, primary.rewrites_frame(frozen, question), max_rewrites=3, jaccard_min=0.15)
            queries.append({"revision": revision, "query_id": row["id"], "question": question,
                            "gold_control_id": namespace["normalize_control_id"](row["control_id"]),
                            "rewrites": frozen, "accepted_variants": variants,
                            "historical_rank_at_10": int(old["rank"]),
                            "historical_top10": json.loads(old["retrieved_control_ids"]),
                            "historical_meta": json.loads(old["system_meta"])})
    return queries


def prepare(repo, folder):
    if (folder / "protocol.json").exists() or (folder / "registered_queries.jsonl").exists():
        raise FileExistsError("Registration already exists; use a new result identity for changes")
    namespace = primary.load_primary(repo)
    queries = registered_queries(repo, namespace)
    inputs, code = manifests(repo)
    with (folder / "registered_queries.jsonl").open("w") as f:
        for query in queries:
            f.write(json.dumps(query, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    protocol = {"result_id": RESULT_ID, "registered_at_utc": datetime.now(timezone.utc).isoformat(),
                "registration_parent_commit": git(repo, "rev-parse", "HEAD"), "models": MODELS,
                "baseline": primary.BASELINE, "conditions": primary.CONDITIONS,
                "queries": 136, "expected_evaluations": 952, "new_llm_rewrites": False,
                "input_sha256": inputs, "code_sha256": code,
                "primary_definition_sha256": {k: hashlib.sha256(v.encode()).hexdigest() for k, v in primary.definitions(repo).items()},
                "registered_queries_sha256": sha(folder / "registered_queries.jsonl"),
                "seed": 42, "bootstrap_samples": 10000,
                "historical_model_revisions_recorded": False,
                "historical_comparison_is_acceptance_gate": False,
                "acceptance": ["all_136_cache_captures_reproduce", "all_952_evaluations_complete",
                               "all_source_and_input_hashes_match", "all_gate_comparisons_use_identical_scores",
                               "all_model_snapshots_pinned", "all_seven_conditions_reported"]}
    write(folder / "protocol.json", protocol)
    print(json.dumps({"registered_queries": len(queries), "evaluations": 952, "protocol_sha256": sha(folder / "protocol.json")}))


def validate_registration(repo, folder):
    if git(repo, "status", "--porcelain"):
        raise RuntimeError("Formal execution requires a clean committed registration")
    protocol = json.loads((folder / "protocol.json").read_text())
    if protocol["queries"] != 136 or protocol["expected_evaluations"] != 952:
        raise AssertionError("Registered population or evaluation count changed")
    inputs, code = manifests(repo)
    if inputs != protocol["input_sha256"] or code != protocol["code_sha256"]:
        raise AssertionError("Registered source or inputs changed")
    if sha(folder / "registered_queries.jsonl") != protocol["registered_queries_sha256"]:
        raise AssertionError("Registered questions changed")
    queries = [json.loads(line) for line in (folder / "registered_queries.jsonl").read_text().splitlines()]
    namespace = primary.load_primary(repo)
    if queries != registered_queries(repo, namespace) or len(queries) != 136:
        raise AssertionError("Registered question matrix differs from source inputs")
    if protocol["models"] != MODELS or protocol["conditions"] != primary.CONDITIONS or protocol["baseline"] != primary.BASELINE:
        raise AssertionError("Registered condition or model settings changed")
    return protocol, queries, namespace


def load_models(folder, namespace):
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import torch
    import faiss
    from sentence_transformers import SentenceTransformer, CrossEncoder
    from huggingface_hub import snapshot_download
    if not torch.cuda.is_available():
        raise RuntimeError("Formal inference requires a GPU. Use the A100 Colab notebook in this directory.")
    requirements = [line for line in (folder / "requirements-colab.txt").read_text().splitlines() if line.strip()]
    dependencies = {}
    for requirement in requirements:
        name, expected = requirement.split("==")
        actual = importlib.metadata.version(name)
        if actual.split("+")[0] != expected:
            raise RuntimeError(f"Runtime dependency mismatch: {name} {actual} != {expected}")
        dependencies[name] = actual
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    namespace["np"].random.seed(42)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    namespace.update({"torch": torch, "faiss": faiss, "SentenceTransformer": SentenceTransformer})
    snapshots, model_files = {}, {}
    for role, spec in MODELS.items():
        print(f"Loading pinned {role}: {spec['model_id']} at {spec['revision']}", flush=True)
        path = Path(snapshot_download(repo_id=spec["model_id"], revision=spec["revision"],
                                     allow_patterns=["*.json", "*.txt", "*.model", "*.safetensors", "1_Pooling/*"]))
        if path.name != spec["revision"]:
            raise AssertionError("Model snapshot does not resolve to the registered revision")
        snapshots[role] = str(path)
        model_files[role] = {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}
        if "model.safetensors" not in model_files[role]:
            raise AssertionError("Native safetensors weights not retained")
    namespace["DENSE_MODEL_ID"] = snapshots["dense"]
    cross_encoder = CrossEncoder(snapshots["reranker"], device="cuda")
    runtime = {"python": platform.python_version(), "dependencies": dependencies,
               "gpu_name": torch.cuda.get_device_name(0), "cuda_version": torch.version.cuda,
               "model_revisions": MODELS, "model_file_sha256": model_files,
               "compute_dtype": "float32", "deterministic_algorithms": True, "tf32": False}
    return cross_encoder, runtime


def base_index(repo, namespace, revision):
    path = repo / INPUTS[revision]["ccs"]
    records = namespace["load_clause_records_jsonl"](str(path))
    docs = namespace["build_control_docs_from_clauses"](records)
    bm25, controls = namespace["build_bm25"](docs)
    return bm25, controls, namespace["build_control_fallback_text_map"](records)


def check_trace(trace, case):
    for key in ("revision", "query_id", "question", "rewrites", "accepted_variants"):
        if trace[key] != case[key]:
            raise AssertionError("Cached input differs from registered question")


def cache_relative(case):
    return f"cache/{case['revision']}/{case['query_id']}.json"


def capture_all(repo, folder, output, protocol, queries, namespace):
    cross_encoder, runtime = load_models(folder, namespace)
    config = {"result_id": RESULT_ID, "execution_repo_commit": git(repo, "rev-parse", "HEAD"),
              "protocol_sha256": sha(folder / "protocol.json"), "input_sha256": protocol["input_sha256"],
              "code_sha256": protocol["code_sha256"], "registered_queries_sha256": protocol["registered_queries_sha256"],
              "runtime": runtime, "new_llm_rewrites": False,
              "inference_strategy": "one ungated complete candidate probe per question; identical scores reused for seven logical conditions"}
    path = output / "run_config.json"
    if path.exists():
        old = json.loads(path.read_text())
        if {k: old[k] for k in config} != config:
            raise RuntimeError("Resume settings/runtime differ; preserve this run and use a new identity")
    elif output.exists() and any(output.iterdir()):
        raise RuntimeError("Output folder is nonempty without a compatible run configuration")
    else:
        config["started_at_utc"] = datetime.now(timezone.utc).isoformat()
        write(path, config)
    manifest_path = output / "cache_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for revision in INPUTS:
        group = [q for q in queries if q["revision"] == revision]
        bm25, controls, fallback = base_index(repo, namespace, revision)
        dense = None
        for case in group:
            relative = cache_relative(case)
            target = output / relative
            if target.exists():
                if relative not in manifest or sha(target) != manifest[relative]:
                    raise AssertionError("Uncommitted or altered cache file; do not silently regenerate it")
                trace = json.loads(target.read_text())
                check_trace(trace, case)
            else:
                if dense is None:
                    dense = namespace["build_dense_retriever"](str(repo / INPUTS[revision]["ccs"]))
                started = time.monotonic()
                trace = primary.capture(namespace, case, bm25, dense, cross_encoder, controls, fallback)
                trace["protocol_sha256"] = config["protocol_sha256"]
                trace["model_revisions"] = MODELS
                write(target, trace)
                manifest[relative] = sha(target)
                write(manifest_path, manifest)
                print(f"Captured {revision}/{case['query_id']} ({len(manifest)}/136), {time.monotonic() - started:.1f}s", flush=True)
        del dense
    if len(manifest) != 136:
        raise AssertionError("Incomplete cache population")


def score_all(repo, folder, output, protocol, queries, namespace):
    manifest = json.loads((output / "cache_manifest.json").read_text())
    config = json.loads((output / "run_config.json").read_text())
    if config["protocol_sha256"] != sha(folder / "protocol.json") or config["code_sha256"] != protocol["code_sha256"] or config["input_sha256"] != protocol["input_sha256"]:
        raise AssertionError("Cache provenance differs from registration")
    if config["runtime"]["model_revisions"] != MODELS or len(manifest) != protocol["queries"]:
        raise AssertionError("Model identity or cache population changed")
    rows, historical, verified = [], [], 0
    for revision in INPUTS:
        _, controls, fallback = base_index(repo, namespace, revision)
        for case in [q for q in queries if q["revision"] == revision]:
            relative = cache_relative(case)
            target = output / relative
            if relative not in manifest or sha(target) != manifest[relative]:
                raise AssertionError("Cache file hash differs from the captured manifest")
            trace = json.loads(target.read_text())
            check_trace(trace, case)
            if trace["model_revisions"] != MODELS or trace["protocol_sha256"] != config["protocol_sha256"]:
                raise AssertionError("Per-query cache provenance differs")
            probe_settings = dict(primary.BASELINE, rerank_skip_enabled=False, rerank_apply_min_margin_ratio=0.0)
            if primary.replay(namespace, trace, controls, fallback, probe_settings) != trace["ungated_probe"]:
                raise AssertionError("Complete captured candidate probe does not reproduce")
            verified += 1
            invariant = None
            for condition in primary.CONDITIONS:
                settings = primary.config(condition)
                result = primary.replay(namespace, trace, controls, fallback, settings)
                meta, ranked = result["meta"], result["final_ranked_cids"]
                now = {k: meta[k] for k in ("num_variants", "bm25_top1", "dense_top1", "base_top1", "base_margin_ratio", "top1_agree")}
                if invariant is not None and invariant != now:
                    raise AssertionError("A sensitivity condition changed fixed upstream retrieval")
                invariant = now
                ungated = primary.replay(namespace, trace, controls, fallback,
                                         dict(settings, rerank_skip_enabled=False, rerank_apply_min_margin_ratio=0.0))
                gold = case["gold_control_id"]
                actual_correct, proposal_correct = bool(ranked and ranked[0] == gold), bool(ungated["final_ranked_cids"] and ungated["final_ranked_cids"][0] == gold)
                stage = "skip" if not meta["reranker_called"] else ("adoption" if not meta["rerank_applied"] else "none")
                rank = namespace["find_rank"](gold, ranked, 10)
                rows.append({"revision": revision, "query_id": case["query_id"], "condition": condition,
                             "gold_control_id": gold, "ranked_controls": ranked, "rank": rank,
                             "metrics": rank_metrics(rank), "meta": meta, "cache_sha256": manifest[relative],
                             "ungated_ranked_controls": ungated["final_ranked_cids"],
                             "gate": {"stage": stage, "prevented_reference_error": stage != "none" and actual_correct and not proposal_correct,
                                      "blocked_reference_correction": stage != "none" and not actual_correct and proposal_correct}})
                if condition == "baseline":
                    old = case["historical_meta"]
                    historical.append({"revision": revision, "query_id": case["query_id"],
                                       "top10_unchanged": ranked[:10] == case["historical_top10"],
                                       "gold_rank_unchanged": rank == case["historical_rank_at_10"],
                                       "gate_flags_unchanged": all(meta[k] == old[k] for k in ("reranker_called", "rerank_applied", "num_variants")),
                                       "historical_rank": case["historical_rank_at_10"], "new_rank": rank})
    expected = protocol["expected_evaluations"]
    if len(rows) != expected or len({(r['revision'], r['query_id'], r['condition']) for r in rows}) != expected:
        raise AssertionError("Sensitivity matrix is incomplete")
    for name, data in (("per_query_results.jsonl", rows), ("historical_baseline_comparison.jsonl", historical)):
        with (output / name).open("w") as f:
            for row in data:
                f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
    summary = {"result_id": RESULT_ID, "evaluations": len(rows), "verified_cache_captures": verified,
               "historical_baseline": {"queries": len(historical), **{k: sum(r[k] for r in historical) for k in ("top10_unchanged", "gold_rank_unchanged", "gate_flags_unchanged")}},
               "strata": {}, "exploratory": True, "historical_scores_replaced": False}
    for stratum in ("rev4", "rev5", "pooled"):
        selected = [r for r in rows if stratum == "pooled" or r["revision"] == stratum]
        baseline = [r for r in selected if r["condition"] == "baseline"]
        conditions, comparisons = {}, {}
        for condition in primary.CONDITIONS:
            subset = [r for r in selected if r["condition"] == condition]
            conditions[condition] = describe(subset)
            if condition != "baseline":
                comparisons[condition] = paired(baseline, subset, seed=protocol["seed"], bootstrap_samples=protocol["bootstrap_samples"])
        summary["strata"][stratum] = {"conditions": conditions, "paired_vs_baseline": comparisons,
                                     "metric_ranges": {metric: [min(c['metrics'][metric]['mean'] for c in conditions.values()),
                                                                 max(c['metrics'][metric]['mean'] for c in conditions.values())] for metric in rank_metrics(0)}}
    summary["acceptance_checks"] = {name: True for name in protocol["acceptance"]}
    summary["accepted"] = verified == protocol["queries"] and len(rows) == expected
    write(output / "summary.json", summary)
    lines = ["# Primary RQ1 constant sensitivity", "", f"Result identity: `{RESULT_ID}`.",
             f"Execution source: `{config['execution_repo_commit']}`.", f"Protocol SHA-256: `{config['protocol_sha256']}`.",
             "", "Seven conditions share identical inferred channel/cross-encoder scores for each question.",
             "The historical primary notebook logic and frozen rewrites are retained.", ""]
    for stratum, data in summary["strata"].items():
        lines += [f"## {stratum}", "", "| Condition | Success@1 | Success@5 | Success@10 | MRR@10 | nDCG@10 | Logical calls | Adopted |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for condition, values in data["conditions"].items():
            m = values["metrics"]
            lines.append("| " + condition + " | " + " | ".join(f"{m[k]['mean']:.4f}" for k in rank_metrics(0)) +
                         f" | {values['logical_reranker_calls']} | {values['adopted_reranks']} |")
        lines.append("")
    h = summary["historical_baseline"]
    lines += ["## Historical comparison and limits", "",
              f"New baseline retains the historical top-10 order in {h['top10_unchanged']}/136 queries, "
              f"gold rank in {h['gold_rank_unchanged']}/136, and gate/variant flags in {h['gate_flags_unchanged']}/136.",
              "Historical model revisions were not recorded; new model revisions and runtime are pinned here. "
              "Any drift is reported and the historical headline scores remain unchanged.", "",
              "This exploratory local sensitivity check does not remove evaluation-set tuning bias or establish held-out validity. "
              "Paired p-values are unadjusted; bootstrap intervals use paired query resampling. "
              "Governing-control labels are author references, not independently adjudicated truth. "
              "The complete-candidate probes enable skip-gate counterfactuals; logical call counts are not measured latency savings.", "",
              "All seven conditions, per-query ranks, gate effects, Wilson intervals, paired comparisons, "
              "historical differences and complete candidate score caches are retained. No condition is selected as a replacement main result."]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    package_results(output)
    print(json.dumps({"accepted": summary['accepted'], "evaluations": len(rows), "historical_baseline": h}, indent=2), flush=True)


def package_results(output):
    archive = output / (RESULT_ID + ".zip")
    exclude = {archive.name, "SHA256SUMS", "ARCHIVE_SHA256SUMS"}
    files = [p for p in sorted(output.rglob("*")) if p.is_file() and p.name not in exclude and not p.name.endswith(".tmp")]
    (output / "SHA256SUMS").write_text("".join(sha(p) + "  " + str(p.relative_to(output)) + "\n" for p in files))
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files + [output / "SHA256SUMS"]:
            info = zipfile.ZipInfo(str(p.relative_to(output)), (2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    (output / "ARCHIVE_SHA256SUMS").write_text(sha(archive) + "  " + archive.name + "\n")


def completed_result_is_valid(output, protocol):
    summary_path = output / "summary.json"
    archive_path = output / (RESULT_ID + ".zip")
    if not summary_path.exists() or not archive_path.exists():
        return False
    summary = json.loads(summary_path.read_text())
    if not summary.get("accepted"):
        return False
    config = json.loads((output / "run_config.json").read_text())
    if config["code_sha256"] != protocol["code_sha256"] or config["input_sha256"] != protocol["input_sha256"]:
        raise AssertionError("Completed result belongs to different registered inputs")
    if summary["evaluations"] != protocol["expected_evaluations"] or summary["verified_cache_captures"] != protocol["queries"]:
        raise AssertionError("Completed result has an incomplete matrix")
    for line in (output / "SHA256SUMS").read_text().splitlines():
        expected, relative = line.split("  ", 1)
        if sha(output / relative) != expected:
            raise AssertionError("Completed result file was altered")
    expected, relative = (output / "ARCHIVE_SHA256SUMS").read_text().strip().split("  ", 1)
    if sha(output / relative) != expected:
        raise AssertionError("Completed result archive was altered")
    with zipfile.ZipFile(archive_path) as archive:
        if archive.testzip() is not None:
            raise AssertionError("Completed result archive is corrupt")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--replay-cache", action="store_true", help="Score a complete captured cache without new inference")
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    repo = folder.parents[2]
    if args.prepare:
        prepare(repo, folder)
        return
    if args.output_dir is None:
        parser.error("Specify an output directory outside the repository")
    output = args.output_dir.resolve()
    if output == repo or repo in output.parents:
        raise RuntimeError("Use an external output folder to keep the registered checkout clean")
    protocol, queries, namespace = validate_registration(repo, folder)
    if not args.replay_cache and completed_result_is_valid(output, protocol):
        print("The completed registered result and archive are intact; no new inference or overwrite.", flush=True)
        return
    try:
        if not args.replay_cache:
            capture_all(repo, folder, output, protocol, queries, namespace)
        score_all(repo, folder, output, protocol, queries, namespace)
    except Exception as exc:
        if (output / "run_config.json").exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
            write(output / "failures" / (stamp + ".json"),
                  {"accepted": False, "error_type": type(exc).__name__, "error": str(exc),
                   "source_commit": git(repo, "rev-parse", "HEAD"),
                   "protocol_sha256": sha(folder / "protocol.json"),
                   "recorded_at_utc": datetime.now(timezone.utc).isoformat()})
        raise


if __name__ == "__main__":
    main()
