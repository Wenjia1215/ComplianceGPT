#!/usr/bin/env python3
"""使用统一严格通过条件评估冻结的补充实验；不重新生成回答。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))
from answerer_comparison import strict_pass as scoring
from experiments.answerer_comparison.run_strict_pass import load_inputs

BASE = Path("experiments/answerer_comparison")
FROZEN_SHA256 = {
    "experiments/answerer_comparison/rq2_bf16_baseline/results_v1/contracts/rev4_generative_baseline_bf16.csv": "1b84eb673145bdae15d8e52c22678f2cf780d5f09f6e8603e6578ec586c2fc60",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-00": "a485699b25eca2d4489867fa4db10dbd6c69693463d2bd447a1bcfeef8e64fed",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-01": "f5aebbb185b065c7d8e9935191d09fc750f09e9f435ab95faf5039effca46512",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-02": "868df4c3ce717d042e3f81c9202c8ee1a3f715bcc87356265d8b2e8e1a231c60",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-03": "914c03ad1ff2ede532dbd98b365d7cdaac54a36001c541e28f7e08d8a4acc333",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-04": "9103ee130d80a95ccc9029f39fd55c39865873868ca1d8c47cc50ebccf8318d3",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-05": "d089c18b27bbdc41cdf796c223337e8988b93e50e4dfcb1ab7b90e73ead4aa5a",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-06": "328f3b9b79daae5a9c52be891d5a5a14d7a333f6c38615f9626d665b111e556b",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-07": "69c827f982c2127d18949adec5d76d7b527613f5bd6f12ec9322730885f2d5d8",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-08": "e8a0a2bdd997bf379955bd6578eb828dd70a12c327d78f94188cc10c5f1a8224",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-09": "7fa52a69b9b9908641a11df9841cafd7af64502abe7c6ada5579d6a275531221",
    "experiments/answerer_comparison/rq2_control_gate_width/results_v1/rq2_control_gate_width_v1.zip.part-10": "9f139635d712591c06f8b7b3c2ce1df6e9f4aac4d42c965bc930905009f46291",
    "experiments/answerer_comparison/rq2_no_selector/results_v1/contracts/rev4_no_selector.csv": "af05e97e7c0078a1f576700922ca292331bc778db4d9948337b38d6364be7602",
    "experiments/answerer_comparison/rq2_no_selector/results_v1/contracts/rev5_no_selector.csv": "606024e83dacdabac8e0dcbe7bbd37aa61d7a9823d23341b3de6d1d58fcfff3d",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev4_rescue_off.csv": "1f707ab93063fc82dd4c014a55396da872f4fa7cf780b405dcebcd313daa1b45",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev4_rescue_on.csv": "5a29bce877990ef3f52a270a4d8038464bf3b7973409ae35e87e630dddae8aa8",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev5_rescue_off.csv": "df0a9884fe8f8f284a2bf38d7c110d361faf12c63e46204e082496d022e176c6",
    "experiments/answerer_comparison/rq2_rescue_ablation/results_v1/contracts/rev5_rescue_on.csv": "369587fe442acd0b5f80039af034d3fa412823fdb0ec020deeced2b86829c59f"
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv(data: bytes) -> dict:
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    result = {r["query_id"]: r for r in rows}
    if len(rows) != len(result):
        raise ValueError("合同题号重复")
    return result


def truth(value) -> bool:
    return str(value).lower() in {"true", "1"}


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def run(output_root: Path) -> dict:
    inputs, input_hashes = load_inputs(REPO_ROOT)
    primary_reviews = scoring.load_reviews(REPO_ROOT / BASE / "strict_pass_reviews.jsonl")
    supplemental_path = REPO_ROOT / BASE / "strict_pass_supplementary_reviews.jsonl"
    extra_reviews = scoring.load_reviews(supplemental_path)
    if set(primary_reviews) & set(extra_reviews):
        raise ValueError("主比较与补充判定记录重复")
    reviews = {**primary_reviews, **extra_reviews}
    primary = {
        rev: {system: scoring.score_rows(revision=rev, rows=rows, gold_rows=gold, repo_root=REPO_ROOT, reviews=reviews)
              for system, rows in systems.items()}
        for rev, (_, gold, systems) in inputs.items()
    }
    blobs = {}
    for name, expected in FROZEN_SHA256.items():
        blobs[name] = (REPO_ROOT / name).read_bytes()
        input_hashes[name] = digest(blobs[name])
        if input_hashes[name] != expected:
            raise ValueError(f"冻结补充输入发生变化：{name}")
    parts = sorted(name for name in blobs if ".zip.part-" in name)
    archive = zipfile.ZipFile(io.BytesIO(b"".join(blobs[name] for name in parts)))
    groups = {}
    used_reviews = set()
    all_rows = []
    for rev, (records, gold, systems) in inputs.items():
        main_rows = systems["compliancegpt"]
        conditions = [
            ("no_selector", f"{BASE}/rq2_no_selector/results_v1/contracts/{rev}_no_selector.csv", None),
            ("rescue_off", f"{BASE}/rq2_rescue_ablation/results_v1/contracts/{rev}_rescue_off.csv", None),
            ("rescue_on", f"{BASE}/rq2_rescue_ablation/results_v1/contracts/{rev}_rescue_on.csv", None),
        ]
        if rev == "rev4":
            conditions.append(("baseline_bf16", f"{BASE}/rq2_bf16_baseline/results_v1/contracts/rev4_generative_baseline_bf16.csv", None))
        for width in (1, 2, 3, 5):
            conditions.append((f"top{width}", f"contracts/top{width}_{rev}_compliancegpt.csv", f"contexts/top{width}_{rev}_prepared_contexts.jsonl"))
        for condition, name, context_name in conditions:
            data = archive.read(name) if context_name else blobs[name]
            if context_name:
                input_hashes[f"archive:{name}"] = digest(data)
                context_data = archive.read(context_name)
                input_hashes[f"archive:{context_name}"] = digest(context_data)
                context_list = [json.loads(line) for line in context_data.decode().splitlines()]
                contexts = {r["query_id"]: r for r in context_list}
                if len(context_list) != len(contexts) or set(contexts) != set(gold):
                    raise ValueError("归档上下文题号不完整或重复")
            rows = read_csv(data)
            if set(rows) != set(gold):
                raise ValueError(f"补充合同题号与参考标签不一致：{name}")
            results = {}
            for qid in sorted(rows, key=int):
                row = rows[qid]
                contract = json.loads(row["contract_json"])
                if context_name:
                    context = contexts[qid]
                    manifest = context["evidence_window_manifest"]
                    window_ids = [r["id"] for r in context["evidence_window"]]
                    if (row["context_sha256"] != context["context_sha256"]
                            or row["evidence_window_sha256"] != manifest["sha256"]
                            or window_ids != manifest["source_ids"]
                            or window_ids != row["evidence_window_source_ids"].split("|")):
                        raise ValueError(f"门控合同与自身冻结窗口不一致：{rev}/{condition}/{qid}")
                    for record, pinned in zip(context["evidence_window"], manifest["records"], strict=True):
                        if record["id"] != pinned["source_id"] or digest(record["text"].encode()) != pinned["text_sha256"]:
                            raise ValueError("归档窗口内容校验失败")
                        if record["id"] not in records or record["text"] != records[record["id"]]["text"]:
                            raise ValueError("归档窗口与活动 CCS 不一致")
                    window_sha = manifest["sha256"]
                else:
                    matched = main_rows[qid]
                    if row["context_sha256"] != matched["context_sha256"]:
                        raise ValueError(f"补充合同上下文与主比较不一致：{rev}/{condition}/{qid}")
                    window_ids = matched["evidence_window_source_ids"].split("|")
                    window_sha = matched["evidence_window_sha256"]
                    if "evidence_window_sha256" in row and row["evidence_window_sha256"] != window_sha:
                        raise ValueError("补充合同冻结窗口校验失败")
                    if "evidence_window_source_ids" in row and row["evidence_window_source_ids"].split("|") != window_ids:
                        raise ValueError("补充合同冻结窗口身份失败")
                result = scoring.evaluate_contract(revision=rev, query_id=qid, contract=contract,
                    gold=gold[qid], records=records, window_ids=window_ids, reviews=reviews)
                recorded = truth(row.get("verifier_pass", row.get("offline_strict_pass")))
                if result["contract_checks_pass"] != recorded:
                    raise ValueError(f"原合同条件无法复现：{rev}/{condition}/{qid}")
                covered = truth(row.get("doc_full_recall", row.get("full_gold_clause_coverage")))
                runtime = truth(row.get("contract_validity_pass", row.get("runtime_contract_pass")))
                if result["strict_pass"] and not covered:
                    raise ValueError("严格通过缺少完整条款覆盖")
                if result["review_method"] == "source_inspection":
                    used_reviews.add(result["review_id"])
                result = {**result, "condition": condition, "question": contract["question"],
                    "full_gold_clause_coverage": covered, "runtime_contract_pass": runtime,
                    "evidence_window_sha256": window_sha, "input_path": name}
                results[qid] = result
                all_rows.append(result)
            groups[(rev, condition)] = results
    if set(extra_reviews) != used_reviews & set(extra_reviews):
        raise ValueError("补充判定记录缺失、过期或未使用")

    def rate(results):
        return {"count": sum(r["strict_pass"] for r in results.values()), "n": len(results),
                "rate": sum(r["strict_pass"] for r in results.values()) / len(results)}

    def update_rate(target, results):
        target.update(rate(results))

    definition = "严格通过要求 C、W、L、U、A、F、P 同时满足；完整参考条款覆盖、来源和跨度有效、保留参数记录完整、引用在正文中实际使用、正文要求完整且规范与参数语义忠实。正确改写可通过；澄清值域不计分。"
    boundary = "统一规则用于冻结的保存回答。正文采用来源对照或完整保留证明，未经过独立专家裁定；不确定项留在分母中且不计通过。配对检验为事后、未调整的探索性分析。"
    written = []
    for study in ("rq2_bf16_baseline", "rq2_no_selector", "rq2_rescue_ablation", "rq2_control_gate_width"):
        relative = BASE / study / "results_v1"
        summary = json.loads((REPO_ROOT / relative / "summary.json").read_text())
        summary["strict_pass_definition"] = definition
        summary["strict_pass_assessment_boundary"] = boundary
        summary["strict_pass_rule_version"] = scoring.RULE_VERSION
        if study == "rq2_bf16_baseline":
            configs = {"generative_baseline_bf16": groups[("rev4", "baseline_bf16")],
                       "generative_baseline_4bit": primary["rev4"]["baseline"],
                       "compliancegpt_4bit": primary["rev4"]["compliancegpt"]}
            for key, results in configs.items():
                update_rate(summary["configurations"][key]["strict_pass"], results)
            for key, right in (("bf16_vs_4bit_baseline", "generative_baseline_4bit"),
                               ("bf16_baseline_vs_4bit_compliancegpt", "compliancegpt_4bit")):
                summary["paired_strict_pass"][key].update(scoring.paired_strict_pass(configs["generative_baseline_bf16"], configs[right]))
        elif study == "rq2_control_gate_width":
            configs = {f"{rev}_{condition}": results for (rev, condition), results in groups.items() if condition.startswith("top")}
            configs.update({f"{rev}_adaptive_v3": primary[rev]["compliancegpt"] for rev in inputs})
            for key, results in configs.items():
                update_rate(summary["configurations"][key]["strict_pass"], results)
            for key, target in summary["pairwise_strict_pass"].items():
                left, right = key.split("_vs_")
                rev = left.split("_")[0]
                target.update(scoring.paired_strict_pass(configs[left], configs[f"{rev}_{right}"]))
        else:
            for rev in inputs:
                r = summary["revisions"][rev]
                if study == "rq2_no_selector":
                    left, right = primary[rev]["compliancegpt"], groups[(rev, "no_selector")]
                    update_rate(r["selector_v3"]["offline_strict_pass"], left)
                    update_rate(r["no_selector_v1"]["offline_strict_pass"], right)
                    r["delta_no_selector_minus_selector"]["offline_strict_pass_rate"] = rate(right)["rate"] - rate(left)["rate"]
                    p = scoring.paired_strict_pass(left, right)
                    r["paired"]["offline_strict_pass"] = {"selector_only": p["left_only"], "no_selector_only": p["right_only"],
                        "both": p["both_pass"], "neither": p["neither_pass"], "exact_mcnemar_two_sided_p": p["exact_mcnemar_two_sided_p"]}
                else:
                    left, right = groups[(rev, "rescue_off")], groups[(rev, "rescue_on")]
                    update_rate(r["rescue_off"]["offline_strict_pass"], left)
                    update_rate(r["rescue_on"]["offline_strict_pass"], right)
                    r["delta_on_minus_off"]["offline_strict_pass_rate"] = rate(right)["rate"] - rate(left)["rate"]
                    p = scoring.paired_strict_pass(left, right)
                    r["paired"]["offline_strict_pass"] = {"rescue_off_only": p["left_only"], "rescue_on_only": p["right_only"],
                        "both": p["both_pass"], "neither": p["neither_pass"], "n": p["paired_rows"], "exact_mcnemar_two_sided_p": p["exact_mcnemar_two_sided_p"]}
        target = output_root / relative / "summary.json"
        write_json(target, summary)
        written.append(target)
        table = [f"# {study} 严格通过结果", "", definition, "", boundary, "",
                 "| 版本与条件 | 严格通过 | 完整条款覆盖 | 平均回答词数 | 平均条款精确率 |",
                 "| --- | --- | --- | --- | --- |"]
        if "configurations" in summary:
            for key, item in summary["configurations"].items():
                n = item["n_questions"]
                table.append(f"| {key} | {item['strict_pass']['count']}/{n} | {item['full_gold_clause_coverage']['count']}/{n} | {item['answer_word_count']['mean']:.2f} | {item['mean_gold_clause_precision']:.4f} |")
        else:
            keys = ("selector_v3", "no_selector_v1") if study == "rq2_no_selector" else ("rescue_off", "rescue_on")
            for rev, revision_summary in summary["revisions"].items():
                for key in keys:
                    item = revision_summary[key]
                    n = item["n_questions"]
                    table.append(f"| {rev}/{key} | {item['offline_strict_pass']['count']}/{n} | {item['full_gold_clause_coverage']['count']}/{n} | {item['review_burden']['answer_word_count']['mean']:.2f} | {item['review_burden']['gold_clause_precision']['mean']:.4f} |")
        table.extend(["", "逐题判定及校验清单见 `../../supplementary_strict_pass/results_v1/`。原合同 CSV 中的旧检查字段保留为原合同条件记录，最终严格通过由本摘要及逐题判定给出。", ""])
        if study == "rq2_no_selector":
            table.append("保存的诊断合同包含空的 `ask_list`。Rev.5 的 85 题、Rev.4 的 32 题通过原合同条件但缺少对应的参数澄清请求记录。严格通过差异不能全部归因于选择器；完整覆盖、长度、精确率和原参数集合指标保持原测量。")
            for rev in inputs:
                pair = summary["revisions"][rev]["paired"]["offline_strict_pass"]
                table.append(f"\n{rev}：主路径独有通过 {pair['selector_only']}，无选择器独有通过 {pair['no_selector_only']}，双侧精确 McNemar 值 {pair['exact_mcnemar_two_sided_p']:.10g}。")
            comparison = REPO_ROOT / relative / "per_row_comparison.csv"
            with comparison.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = reader.fieldnames
                comparison_rows = list(reader)
            for row in comparison_rows:
                rev, qid = row["framework_version"], row["query_id"]
                row["selector_offline_strict_pass"] = primary[rev]["compliancegpt"][qid]["strict_pass"]
                row["no_selector_offline_strict_pass"] = groups[(rev, "no_selector")][qid]["strict_pass"]
            comparison_target = output_root / relative / "per_row_comparison.csv"
            with comparison_target.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(comparison_rows)
            written.append(comparison_target)
        elif study == "rq2_control_gate_width":
            table.append("Rev.5 固定 top-5 的 Q12、Q39、Q61 引用了各自冻结窗口之外的有效 CCS 来源，因来源窗口要求失败；完整覆盖仍为 67/100，严格通过为 64/100。其余固定门控条件的严格通过数与完整覆盖数相同。")
        elif study == "rq2_bf16_baseline":
            table.append("BF16 的 Q17 对信息系统执行限制与组织承担动作的关系判定不确定，不计严格通过且保留在 36 题分母中。该记录不构成独立专家裁定。")
            for key, pair in summary["paired_strict_pass"].items():
                table.append(f"\n{key}：左方独有通过 {pair['left_only']}，右方独有通过 {pair['right_only']}，双侧精确 McNemar 值 {pair['exact_mcnemar_two_sided_p']:.10g}。")
        else:
            table.append("两批冻结救援合同在统一规则下通过数为 Rev.5 关闭 59/100、启用 65/100，Rev.4 两条件均为 29/36。其余测量与原归档一致。")
        markdown = output_root / relative / "SUMMARY.md"
        markdown.write_text("\n".join(table) + "\n", encoding="utf-8")
        written.append(markdown)

    relative = BASE / "supplementary_strict_pass/results_v1"
    destination = output_root / relative
    destination.mkdir(parents=True, exist_ok=True)
    jsonl = destination / "strict_pass_rows.jsonl"
    jsonl.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_rows), encoding="utf-8")
    metrics = {}
    for (rev, condition), results in groups.items():
        covered = [r for r in results.values() if r["full_gold_clause_coverage"]]
        metrics[f"{rev}_{condition}"] = {
            "strict_pass": rate(results), "full_gold_clause_coverage": len(covered),
            "coverage_complete_failures": sum(not r["strict_pass"] for r in covered),
            "uncertain_query_ids": [qid for qid, r in results.items() if r["semantic_uncertain"]],
            "strict_pass_query_ids": [qid for qid, r in results.items() if r["strict_pass"]],
            "paired_vs_main_compliancegpt": scoring.paired_strict_pass(primary[rev]["compliancegpt"], results),
        }
    metrics["rev4_baseline_bf16"]["paired_vs_4bit_baseline"] = scoring.paired_strict_pass(groups[("rev4", "baseline_bf16")], primary["rev4"]["baseline"])
    write_json(destination / "summary.json", {"rule_version": scoring.RULE_VERSION, "评估范围": boundary, "conditions": metrics})
    written.extend([jsonl, destination / "summary.json"])
    code_paths = [Path(__file__).relative_to(REPO_ROOT), BASE / "strict_pass_supplementary_reviews.jsonl",
                  BASE / "strict_pass_reviews.jsonl", Path("src/answerer_comparison/strict_pass.py"), BASE / "run_strict_pass.py"]
    manifest = {"rule_version": scoring.RULE_VERSION, "原始数据提交": "72979835f1e05bae513468ca4074b4d43497da2c",
                "inputs": input_hashes, "evaluation": {str(p): digest((REPO_ROOT / p).read_bytes()) for p in code_paths},
                "outputs": {str(p.relative_to(output_root)): digest(p.read_bytes()) for p in written},
                "补充回答数": len(all_rows), "补充正文判定记录数": len(extra_reviews)}
    write_json(destination / "manifest.json", manifest)
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="统一严格通过条件下的补充实验评估")
    parser.add_argument("--output-root", type=Path, default=REPO_ROOT)
    args = parser.parse_args()
    result = run(args.output_root.resolve())
    print(json.dumps({key: value["strict_pass"] for key, value in result.items()}, ensure_ascii=False, indent=2))
