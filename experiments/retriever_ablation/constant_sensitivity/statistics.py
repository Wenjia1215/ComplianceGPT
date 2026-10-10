"""Exploratory paired summaries for one governing-control label per question."""
import math

import numpy as np


def rank_metrics(rank):
    hit = 1 <= rank <= 10
    return {"success_at_1": int(rank == 1), "success_at_5": int(1 <= rank <= 5),
            "success_at_10": int(hit), "mrr_at_10": 1.0 / rank if hit else 0.0,
            "ndcg_at_10": 1.0 / math.log2(rank + 1) if hit else 0.0}


def wilson(successes, n):
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def exact_mcnemar(losses, gains):
    n = losses + gains
    if not n:
        return 1.0
    return min(1.0, 2 * sum(math.comb(n, k) for k in range(min(losses, gains) + 1)) / 2 ** n)


def describe(rows):
    n = len(rows)
    metrics = {}
    for metric in rank_metrics(0):
        values = [row["metrics"][metric] for row in rows]
        metrics[metric] = {"mean": sum(values) / n}
        if metric.startswith("success"):
            metrics[metric].update({"hits": sum(values), "n": n, "wilson_95": wilson(sum(values), n)})
    stages = {}
    for stage in ("skip", "adoption", "none"):
        sub = [row for row in rows if row["gate"]["stage"] == stage]
        stages[stage] = {"queries": len(sub),
                         "prevented_reference_errors": sum(row["gate"]["prevented_reference_error"] for row in sub),
                         "blocked_reference_corrections": sum(row["gate"]["blocked_reference_correction"] for row in sub)}
    return {"n": n, "metrics": metrics, "gates": stages,
            "logical_reranker_calls": sum(row["meta"]["reranker_called"] for row in rows),
            "adopted_reranks": sum(row["meta"]["rerank_applied"] for row in rows)}


def paired(base, changed, seed=42, bootstrap_samples=10000):
    if [(r["revision"], r["query_id"]) for r in base] != [(r["revision"], r["query_id"]) for r in changed]:
        raise AssertionError("Paired row identities differ")
    n = len(base)
    indices = np.random.default_rng(seed).integers(0, n, size=(bootstrap_samples, n))
    result = {}
    for metric in rank_metrics(0):
        a = np.array([r["metrics"][metric] for r in base], dtype=np.float64)
        b = np.array([r["metrics"][metric] for r in changed], dtype=np.float64)
        delta = b - a
        entry = {"delta": float(delta.mean())}
        if metric.startswith("success"):
            losses, gains = int(np.sum((a == 1) & (b == 0))), int(np.sum((a == 0) & (b == 1)))
            entry.update({"losses": losses, "gains": gains, "exact_mcnemar_p_unadjusted": exact_mcnemar(losses, gains)})
        else:
            entry["paired_bootstrap_95"] = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975]).tolist()
        result[metric] = entry
    return {"n": n, "metrics": result,
            "changed_top1": sum(a["ranked_controls"][:1] != b["ranked_controls"][:1] for a, b in zip(base, changed)),
            "changed_top10_order": sum(a["ranked_controls"][:10] != b["ranked_controls"][:10] for a, b in zip(base, changed)),
            "changed_gold_rank_at_10": sum(a["rank"] != b["rank"] for a, b in zip(base, changed))}
