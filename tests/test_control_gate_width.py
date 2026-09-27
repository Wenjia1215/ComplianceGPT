import copy
import unittest

from answerer_comparison.matched_window_runner import CONTEXT_SCHEMA, validate_prepared_context
from compliancegpt.pipeline.evidence_window import build_evidence_window, evidence_window_manifest
from compliancegpt.pipeline.pipeline import (
    _apply_doc_filter_mode,
    _filter_docs_to_controls,
    normalize_control_id,
)

from experiments.answerer_comparison.rq2_control_gate_width.run_control_gate_width import (
    MODEL_ID,
    MODEL_REVISION,
    build_fixed_width_context,
    canonical_sha256,
    validate_registered_design,
    validate_registered_runtime,
)


def source_context():
    docs = []
    for control in ("AC-1", "AU-1", "CM-1", "IA-1", "SC-1"):
        docs.extend(
            [
                {
                    "id": f"{control.lower()}_smt",
                    "control_id": control,
                    "kind": "smt",
                    "text": f"{control} statement",
                },
                {
                    "id": f"{control.lower()}_gdn",
                    "control_id": control,
                    "kind": "gdn",
                    "text": f"{control} guidance",
                },
            ]
        )
    window = docs[:2]
    context = {
        "schema_version": CONTEXT_SCHEMA,
        "query_id": "1",
        "framework_version": "rev5",
        "question": "What is required?",
        "rewrites": [],
        "retrieved_docs": docs,
        "retrieval_meta": {
            "selected_controls": ["AC-1", "AU-1", "CM-1", "IA-1", "SC-1"],
            "final_margin_ratio": 0.01,
        },
        "control_gate": {
            "normalized_controls": ["AC-1", "AU-1", "CM-1", "IA-1", "SC-1"],
            "primary_control": "AC-1",
            "allowed_controls": ["AC-1"],
            "widen_tier": 0,
        },
        "window_config": {
            "doc_filter_mode": "prefer_smt_keep_params",
            "gen_docs_k": 24,
            "primary_first_min_margin_ratio": 0.06,
        },
        "evidence_window": window,
        "evidence_window_manifest": evidence_window_manifest(window),
    }
    context["context_sha256"] = canonical_sha256(context)
    validate_prepared_context(context)
    return context


class ControlGateWidthTests(unittest.TestCase):
    def build(self, width):
        return build_fixed_width_context(
            source_context=copy.deepcopy(source_context()),
            width=width,
            normalize_control_id=normalize_control_id,
            build_evidence_window=build_evidence_window,
            evidence_window_manifest=evidence_window_manifest,
            filter_docs_to_controls=_filter_docs_to_controls,
            apply_doc_filter_mode=_apply_doc_filter_mode,
            validate_prepared_context=validate_prepared_context,
        )

    def test_registered_widths_are_locked(self):
        self.assertEqual(validate_registered_design([1, 2, 3, 5]), [1, 2, 3, 5])
        with self.assertRaises(ValueError):
            validate_registered_design([1, 2, 3])

    def test_registered_runtime_is_locked(self):
        self.assertEqual(
            validate_registered_runtime(
                revisions=["rev5", "rev4"],
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                load_in_4bit=True,
            ),
            ["rev5", "rev4"],
        )
        with self.assertRaises(ValueError):
            validate_registered_runtime(
                revisions=["rev5"],
                model_id=MODEL_ID,
                model_revision=MODEL_REVISION,
                load_in_4bit=True,
            )

    def test_fixed_top_one_does_not_adaptively_widen(self):
        context = self.build(1)
        self.assertEqual(context["control_gate"]["allowed_controls"], ["AC-1"])
        self.assertEqual(context["control_gate"]["effective_window_width"], 1)
        self.assertEqual(
            [record["control_id"] for record in context["evidence_window"]],
            ["AC-1", "AC-1"],
        )

    def test_fixed_top_five_admits_all_ranked_controls(self):
        context = self.build(5)
        self.assertEqual(len(context["control_gate"]["allowed_controls"]), 5)
        self.assertEqual(context["control_gate"]["effective_window_width"], 5)
        self.assertEqual(len(context["evidence_window"]), 10)
        validate_prepared_context(context)

    def test_context_hash_changes_with_width(self):
        top_one = self.build(1)
        top_two = self.build(2)
        self.assertNotEqual(top_one["context_sha256"], top_two["context_sha256"])
        self.assertNotEqual(
            top_one["evidence_window_manifest"]["sha256"],
            top_two["evidence_window_manifest"]["sha256"],
        )

    def test_duplicate_normalized_rank_is_not_silently_replaced(self):
        source = source_context()
        source["control_gate"]["normalized_controls"] = [
            "AC-1",
            "AU-1",
            "AC-1",
            "CM-1",
            "IA-1",
        ]
        source["context_sha256"] = canonical_sha256(
            {key: value for key, value in source.items() if key != "context_sha256"}
        )
        context = build_fixed_width_context(
            source_context=source,
            width=3,
            normalize_control_id=normalize_control_id,
            build_evidence_window=build_evidence_window,
            evidence_window_manifest=evidence_window_manifest,
            filter_docs_to_controls=_filter_docs_to_controls,
            apply_doc_filter_mode=_apply_doc_filter_mode,
            validate_prepared_context=validate_prepared_context,
        )
        self.assertEqual(
            context["control_gate"]["allowed_controls"],
            ["AC-1", "AU-1", "AC-1"],
        )
        self.assertEqual(context["control_gate"]["effective_window_width"], 2)


if __name__ == "__main__":
    unittest.main()
