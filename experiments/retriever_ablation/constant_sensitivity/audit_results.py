#!/usr/bin/env python3
"""Verify the registered RQ1 result archive without repeating model inference."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

import numpy as np
import scipy
from scipy.stats import binomtest

SCIENTIFIC_COMMIT = "a066453a317bba365db707b71745e49fee28811a"
BASE = "experiments/retriever_ablation/constant_sensitivity"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def close(a, b):
    return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-13)


def load_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def run_audit(repo, archive, output):
    repo, archive, output = repo.resolve(), archive.resolve(), output.resolve()
    if output == repo or repo in output.parents:
        raise ValueError("Use an audit output directory outside the repository")
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo))
    sys.path.insert(0, str(repo / "src"))
    from experiments.retriever_ablation.constant_sensitivity import run_sensitivity as study
    from experiments.retriever_ablation.constant_sensitivity import primary_adapter as primary

    checks = Counter()

    def require(test, category):
        if not test:
            raise AssertionError(category)
        checks[category] += 1

    if archive.is_dir():
        parts_directory = archive
        parts_manifest = json.loads((parts_directory / "ARCHIVE_PARTS.json").read_text())
        require(parts_manifest["archive_name"] == "rq1_constant_sensitivity_v1.zip", "archive_part_identity")
        archive = output / parts_manifest["archive_name"]
        with archive.open("wb") as assembled:
            for part in parts_manifest["parts"]:
                name = part["name"]
                require(PurePosixPath(name).name == name and "\\" not in name, "safe_archive_part_paths")
                data = (parts_directory / name).read_bytes()
                require(len(data) == part["bytes"] and digest(data) == part["sha256"], "archive_part_hashes")
                assembled.write(data)
        require(archive.stat().st_size == parts_manifest["archive_bytes"] and
                digest(archive.read_bytes()) == parts_manifest["archive_sha256"], "reassembled_original_archive_hash")

    protocol, questions, namespace = study.validate_registration(repo, repo / BASE)
    require(len(questions) == 136 and protocol["expected_evaluations"] == 952, "registered_population")
    original, replay = output / "original", output / "replay"
    original.mkdir()
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        require(len(names) == len(set(names)), "unique_archive_members")
        require(bundle.testzip() is None, "archive_crc")
        require(all(not PurePosixPath(name).is_absolute() and ".." not in PurePosixPath(name).parts
                    and "\\" not in name and not name.endswith("/") for name in names), "safe_archive_paths")
        lines = bundle.read("SHA256SUMS").decode().splitlines()
        hashes = {}
        for line in lines:
            expected, name = line.split("  ", 1)
            require(name not in hashes and len(expected) == 64, "unique_payload_hash_records")
            require(digest(bundle.read(name)) == expected, "payload_sha256")
            hashes[name] = expected
        require(set(hashes) == set(names) - {"SHA256SUMS"}, "complete_payload_hash_coverage")
        for name in names:
            target = original / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(bundle.read(name))

    config = json.loads((original / "run_config.json").read_text())
    summary = json.loads((original / "summary.json").read_text())
    manifest = json.loads((original / "cache_manifest.json").read_text())
    require(config["execution_repo_commit"] == SCIENTIFIC_COMMIT, "immutable_scientific_commit")
    require(config["protocol_sha256"] == study.sha(repo / BASE / "protocol.json"), "registered_protocol_hash")
    for name in ("input_sha256", "code_sha256", "registered_queries_sha256"):
        require(config[name] == protocol[name], "registered_source_and_input_hashes")
    runtime = config["runtime"]
    require(runtime["model_revisions"] == protocol["models"], "registered_model_revisions")
    require(runtime["compute_dtype"] == "float32" and runtime["deterministic_algorithms"]
            and not runtime["tf32"], "registered_compute_settings")
    require("A100" in runtime["gpu_name"] and bool(runtime["cuda_version"]), "recorded_gpu_execution")
    for line in (repo / BASE / "requirements-colab.txt").read_text().splitlines():
        name, version = line.split("==")
        require(runtime["dependencies"][name].split("+")[0] == version, "pinned_dependency_versions")
    require(config["new_llm_rewrites"] is False, "frozen_rewrite_policy")
    started = datetime.fromisoformat(config["started_at_utc"])
    committed = datetime.fromisoformat(subprocess.check_output(
        ["git", "show", "-s", "--format=%cI", SCIENTIFIC_COMMIT], cwd=repo, text=True).strip())
    require(datetime.fromisoformat(protocol["registered_at_utc"]) <= committed <= started,
            "registration_precedes_recorded_execution")

    expected_paths = {study.cache_relative(q) for q in questions}
    require(set(manifest) == expected_paths, "complete_cache_population")
    require({n for n in hashes if n.startswith("cache/")} == expected_paths, "no_extra_or_missing_caches")
    lexical_vectors, dense_texts, cross_encoder_pairs = 0, 0, 0
    for revision in study.INPUTS:
        bm25, controls, _ = study.base_index(repo, namespace, revision)
        records = namespace["load_clause_records_jsonl"](str(repo / study.INPUTS[revision]["ccs"]))
        clauses = {r["clause_id"]: r for r in records}
        for case in [q for q in questions if q["revision"] == revision]:
            path = study.cache_relative(case)
            require(study.sha(original / path) == manifest[path], "cache_manifest_hashes")
            trace = json.loads((original / path).read_text())
            study.check_trace(trace, case)
            require(trace["model_revisions"] == protocol["models"] and
                    trace["protocol_sha256"] == config["protocol_sha256"], "per_cache_provenance")
            variants = case["accepted_variants"]
            require(len(trace["lexical_calls"]) == len(trace["dense_calls"]) == len(variants), "complete_variant_captures")
            for variant, lexical, dense in zip(variants, trace["lexical_calls"], trace["dense_calls"]):
                require(lexical["tokens"] == namespace["tokenize"](variant), "lexical_query_tokens")
                scores = bm25.get_scores(lexical["tokens"]).astype(np.float32)
                require(np.array_equal(scores, np.asarray(lexical["scores"], dtype=np.float32)), "lexical_scores_from_frozen_corpus")
                require(list(bm25.get_top_n(lexical["tokens"], n=lexical["n"])) == lexical["indices"], "lexical_ranks_from_frozen_corpus")
                lexical_vectors += 1
                require(dense["query"] == variant and dense["top_k"] == 50, "dense_variant_and_width")
                hits = dense["hits"]
                require(len(hits) <= 50 and len({h[0] for h in hits}) == len(hits), "dense_control_uniqueness")
                require(all(h[0] in controls and math.isfinite(h[1]) for h in hits), "dense_control_identity_and_finite_scores")
                require(all(hits[i][1] >= hits[i + 1][1] for i in range(len(hits) - 1)), "dense_score_order")
                for cid, clause_id in dense["best_clause_ids"].items():
                    require(clause_id in clauses and clauses[clause_id]["control_id"] == cid, "dense_best_clause_provenance")
                for cid, text in dense["texts"].items():
                    record = clauses[dense["best_clause_ids"][cid]]
                    expected_text = f"{record['control_id']} {record['title']} ({record['kind']})\n{record['text']}"
                    require(text == expected_text, "dense_text_from_frozen_corpus")
                    dense_texts += 1
            require(len(trace["cross_encoder_calls"]) == 1, "complete_cross_encoder_capture")
            call = trace["cross_encoder_calls"][0]
            require(primary.digest(call["pairs"]) == call["pairs_sha256"], "cross_encoder_pair_hashes")
            require(len(call["scores"]) == len(call["pairs"]) and all(math.isfinite(s) for s in call["scores"]), "cross_encoder_score_shape")
            cross_encoder_pairs += len(call["pairs"])

    # Replay from a separate copy. The uploaded archive and extracted original are retained verbatim.
    shutil.copytree(original, replay)
    study.score_all(repo, repo / BASE, replay, protocol, questions, namespace)
    replayed_names = ("per_query_results.jsonl", "historical_baseline_comparison.jsonl", "summary.json", "SUMMARY.md", "SHA256SUMS")
    for name in replayed_names:
        require((original / name).read_bytes() == (replay / name).read_bytes(), "byte_identical_replayed_outputs")
    print("All cached probes and 952 condition evaluations replayed exactly.", flush=True)

    rows = load_lines(original / "per_query_results.jsonl")
    cases = {(q["revision"], q["query_id"]): q for q in questions}
    expected_keys = {(rev, qid, cond) for rev, qid in cases for cond in primary.CONDITIONS}
    require({(r["revision"], r["query_id"], r["condition"]) for r in rows} == expected_keys
            and len(rows) == 952, "complete_unique_condition_matrix")
    for row in rows:
        gold = cases[(row["revision"], row["query_id"])]["gold_control_id"]
        require(row["gold_control_id"] == gold, "reference_label_identity")
        ranked = row["ranked_controls"]
        require(len(ranked) == len(set(ranked)), "unique_ranked_controls")
        rank = ranked.index(gold) + 1 if gold in ranked[:10] else 0
        require(row["rank"] == rank, "rank_from_control_order")
        metric = {"success_at_1": int(rank == 1), "success_at_5": int(1 <= rank <= 5),
                  "success_at_10": int(1 <= rank <= 10), "mrr_at_10": 1 / rank if rank else 0,
                  "ndcg_at_10": 1 / math.log2(rank + 1) if rank else 0}
        require(all(close(row["metrics"][k], v) for k, v in metric.items()), "independent_per_query_metrics")
        require(row["cache_sha256"] == manifest[f"cache/{row['revision']}/{row['query_id']}.json"], "condition_cache_identity")
        settings = primary.config(row["condition"])
        for name in ("rerank_alpha", "rerank_apply_min_margin_ratio", "rerank_skip_min_base_margin_ratio"):
            require(row["meta"][name] == settings[name], "condition_threshold_identity")

    for stratum in ("rev4", "rev5", "pooled"):
        selected = [r for r in rows if stratum == "pooled" or r["revision"] == stratum]
        base = [r for r in selected if r["condition"] == "baseline"]
        for condition in primary.CONDITIONS:
            changed = [r for r in selected if r["condition"] == condition]
            recorded = summary["strata"][stratum]["conditions"][condition]
            require(len(changed) == recorded["n"], "stratum_condition_size")
            for metric in changed[0]["metrics"]:
                values = [r["metrics"][metric] for r in changed]
                require(close(math.fsum(values) / len(values), recorded["metrics"][metric]["mean"]), "independent_metric_means")
                if metric.startswith("success"):
                    hits = sum(values)
                    ci = binomtest(hits, len(values)).proportion_ci(confidence_level=0.95, method="wilson")
                    require(recorded["metrics"][metric]["hits"] == hits and
                            np.allclose([ci.low, ci.high], recorded["metrics"][metric]["wilson_95"], rtol=0, atol=1e-13), "independent_wilson_intervals")
            if condition == "baseline":
                continue
            require([(r["revision"], r["query_id"]) for r in base] ==
                    [(r["revision"], r["query_id"]) for r in changed], "independent_pair_identities")
            indices = np.random.default_rng(protocol["seed"]).integers(0, len(base), size=(protocol["bootstrap_samples"], len(base)))
            paired = summary["strata"][stratum]["paired_vs_baseline"][condition]
            for metric in changed[0]["metrics"]:
                a, b = [r["metrics"][metric] for r in base], [r["metrics"][metric] for r in changed]
                deltas = np.asarray([y - x for x, y in zip(a, b)], dtype=np.float64)
                entry = paired["metrics"][metric]
                require(close(math.fsum(deltas) / len(deltas), entry["delta"]), "independent_paired_deltas")
                if metric.startswith("success"):
                    losses = sum(x == 1 and y == 0 for x, y in zip(a, b))
                    gains = sum(x == 0 and y == 1 for x, y in zip(a, b))
                    p = binomtest(min(losses, gains), losses + gains, p=0.5).pvalue if losses + gains else 1.0
                    require(entry["losses"] == losses and entry["gains"] == gains and
                            close(entry["exact_mcnemar_p_unadjusted"], p), "independent_mcnemar_counts_and_p")
                else:
                    ci = np.quantile(deltas[indices].mean(axis=1), [0.025, 0.975])
                    require(np.allclose(ci, entry["paired_bootstrap_95"], rtol=0, atol=1e-13), "independent_paired_bootstrap_intervals")

    # Verify recorded model-file hashes against the immutable upstream revisions.
    model_checks, downloads = {}, []
    for role, spec in protocol["models"].items():
        url = f"https://huggingface.co/api/models/{spec['model_id']}/revision/{spec['revision']}?blobs=true"
        with urllib.request.urlopen(url, timeout=30) as response:
            metadata = json.load(response)
        require(metadata["sha"] == spec["revision"], "upstream_immutable_model_revision")
        files = {item["rfilename"]: item for item in metadata["siblings"]}
        model_checks[role] = {"metadata_url": url, "revision": metadata["sha"], "files": {}}
        for name, expected in runtime["model_file_sha256"][role].items():
            require(name in files, "upstream_model_file_presence")
            if files[name].get("lfs"):
                require(files[name]["lfs"]["sha256"] == expected, "upstream_lfs_file_sha256")
                model_checks[role]["files"][name] = {"sha256": expected, "verified_via": "immutable upstream LFS SHA-256"}
            else:
                downloads.append((role, name, expected,
                                  f"https://huggingface.co/{spec['model_id']}/resolve/{spec['revision']}/{name}"))

    def verify_small_file(item):
        role, name, expected, url = item
        with urllib.request.urlopen(url, timeout=30) as response:
            actual = digest(response.read())
        return role, name, expected, actual, url

    with ThreadPoolExecutor(max_workers=6) as executor:
        for role, name, expected, actual, url in executor.map(verify_small_file, downloads):
            require(actual == expected, "upstream_model_content_sha256")
            model_checks[role]["files"][name] = {"sha256": actual, "verified_via": url}

    historical = load_lines(original / "historical_baseline_comparison.jsonl")
    failures = sorted(n for n in hashes if n.startswith("failures/"))
    require(summary["accepted"] and summary["evaluations"] == 952 and summary["verified_cache_captures"] == 136
            and all(summary["acceptance_checks"].values()), "reported_acceptance_agrees_with_audit")
    report = {"accepted": True, "audit_recorded_at_utc": datetime.now(timezone.utc).isoformat(),
              "archive_sha256": digest(archive.read_bytes()), "archive_bytes": archive.stat().st_size,
              "archive_members": len(names), "payload_hashes_verified": len(hashes),
              "scientific_commit": SCIENTIFIC_COMMIT, "protocol_sha256": config["protocol_sha256"],
              "registered_questions": 136, "evaluations_replayed": 952,
              "lexical_score_vectors_recomputed": lexical_vectors, "dense_canonical_texts_verified": dense_texts,
              "cross_encoder_pairs_retained": cross_encoder_pairs, "model_files_verified": sum(len(m["files"]) for m in model_checks.values()),
              "byte_identical_replayed_files": list(replayed_names), "checks_passed_by_category": dict(sorted(checks.items())),
              "total_checks_passed": sum(checks.values()), "independent_statistics_tolerance": 1e-13,
              "capture_runtime": runtime, "audit_runtime": {"python": sys.version.split()[0], "numpy": np.__version__, "scipy": scipy.__version__},
              "failed_attempt_records_retained": failures,
              "historical_baseline": summary["historical_baseline"],
              "historical_gold_rank_differences": [h for h in historical if not h["gold_rank_unchanged"]],
              "limits": ["Cached neural scores were verified for provenance and replay, not reinferred in this audit.",
                         "Same-author benchmark labels are not independently adjudicated correctness.",
                         "Sensitivity covers three selected retrieval constants, not every configuration constant.",
                         "Local sensitivity does not remove benchmark tuning bias or establish held-out validity.",
                         "The fresh baseline does not replace the saved historical RQ1 results.",
                         "Logical skip counts are not measured runtime or cost savings."]}
    (output / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    (output / "model_verification.json").write_text(json.dumps(model_checks, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("accepted", "archive_sha256", "evaluations_replayed", "total_checks_passed", "model_files_verified", "historical_baseline")}, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True, help="Original ZIP or directory containing ARCHIVE_PARTS.json and its binary parts")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    run_audit(args.repo, args.archive, args.output_dir)
