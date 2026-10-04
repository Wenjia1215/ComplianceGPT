#!/usr/bin/env python3
"""Post-hoc scope diagnostic; not a new formal acceptance rule or label study."""
import json
from pathlib import Path

from experiments.answerer_comparison.rq2_profile_fill_v2 import run_profile_fill as study


def main():
    folder = Path(__file__).resolve().parent
    repo = folder.parents[2]
    inputs, hashes = study.load_inputs(repo)
    cases = [json.loads(line) for line in (folder / "registered_cases.jsonl").read_text().splitlines()]
    complete = [case for case in cases if case["condition"] == "complete"]
    if len(complete) != 100 or len({case["query_id"] for case in complete}) != 100:
        raise AssertionError("Registered complete-profile row identities changed")
    rows = []
    for case in complete:
        qid = case["query_id"]
        gold = inputs["rev5"]["gold"][qid]
        required = {study.normalize_odp_id(key.strip())
                    for key in gold["odp_required"].splitlines() if key.strip()}
        visible = {study.normalize_odp_id(key) for key in case["frozen_visible_keys"]}
        rows.append({"query_id": qid, "author_odp_positive": case["author_odp_positive"],
                     "author_gold_required_keys": sorted(required), "visible_keys": sorted(visible),
                     "gold_keys_absent_from_retained_evidence": sorted(required - visible),
                     "visible_keys_not_listed_in_gold": sorted(visible - required)})
    positive = [row for row in rows if row["author_odp_positive"]]
    negative = [row for row in rows if not row["author_odp_positive"]]
    report = {
        "analysis": "post-hoc retained-parameter scope diagnostic",
        "changes_formal_acceptance": False,
        "new_inference": False,
        "new_retrieval": False,
        "validates_independent_label_correctness": False,
        "protocol_sha256": study.file_sha256(folder / "protocol.json"),
        "registered_cases_sha256": study.file_sha256(folder / "registered_cases.jsonl"),
        "input_sha256": hashes,
        "author_odp_positive_rows": len(positive),
        "positive_rows_with_all_gold_parameter_keys_visible": sum(
            not row["gold_keys_absent_from_retained_evidence"] for row in positive),
        "positive_rows_with_a_gold_parameter_key_absent": sum(
            bool(row["gold_keys_absent_from_retained_evidence"]) for row in positive),
        "author_negative_rows": len(negative),
        "author_negative_rows_with_visible_parameter_keys": sum(bool(row["visible_keys"]) for row in negative),
        "rows": rows,
    }
    study.dump(folder / "parameter_scope_audit.json", report)
    print(json.dumps({key: value for key, value in report.items()
                      if key not in {"rows", "input_sha256"}}, indent=2))


if __name__ == "__main__":
    main()
