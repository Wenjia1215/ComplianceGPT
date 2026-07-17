import unittest

from compliancegpt.pipeline.evidence_window import (
    assert_same_evidence_window,
    build_evidence_window,
    evidence_window_manifest,
    select_allowed_controls,
)
from compliancegpt.pipeline.pipeline import (
    _extract_control_hints,
    _query_allows_enhancements,
)
from generative_answerer.pipeline import _ordered_unique_citation_ids


def normalize_control(value):
    text = str(value or "").upper()
    return text.split("(", 1)[0] if text else None


def filter_controls(docs, allowed):
    allow = {str(value).upper() for value in allowed}
    return [doc for doc in docs if str(doc.get("control_id", "")).upper() in allow]


def apply_mode(docs, mode):
    if mode in {"smt_only", "statement_only"}:
        return [doc for doc in docs if doc.get("kind") == "smt"]
    if mode == "prefer_smt_keep_params":
        return sorted(docs, key=lambda doc: 0 if doc.get("kind") == "smt" else 1)
    return list(docs)


class EvidenceWindowTests(unittest.TestCase):
    def setUp(self):
        self.docs = [
            {"id": "b_smt", "control_id": "B-1", "kind": "smt", "text": "B statement"},
            {"id": "a_gdn", "control_id": "A-1", "kind": "gdn", "text": "A guidance"},
            {"id": "a_smt", "control_id": "A-1", "kind": "smt", "text": "A statement"},
            {"id": "b_gdn", "control_id": "B-1", "kind": "gdn", "text": "B guidance"},
        ]
        self.meta = {
            "selected_controls": ["A-1", "B-1"],
            "final_margin_ratio": 0.10,
        }

    def test_control_gate_is_shared(self):
        controls, primary, allowed, tier = select_allowed_controls(
            retrieved_docs=self.docs,
            retrieval_meta=self.meta,
            normalize_control_id=normalize_control,
            topn=1,
            lowconf_top2=0.08,
            lowconf_top3=0.04,
            lowconf_maxn=3,
        )
        self.assertEqual(controls, ["A-1", "B-1"])
        self.assertEqual(primary, "A-1")
        self.assertEqual(allowed, ["A-1"])
        self.assertEqual(tier, 0)

    def test_primary_first_and_cap_are_deterministic(self):
        window, audit = build_evidence_window(
            retrieved_docs=self.docs,
            retrieval_meta=self.meta,
            allowed_controls=["A-1", "B-1"],
            primary_control="A-1",
            doc_filter_mode="prefer_smt_keep_params",
            gen_docs_k=3,
            filter_docs_to_controls=filter_controls,
            apply_doc_filter_mode=apply_mode,
            primary_first_min_margin_ratio=0.06,
        )
        self.assertEqual([doc["id"] for doc in window], ["a_smt", "b_smt", "a_gdn"])
        self.assertTrue(audit["primary_first_applied"])
        self.assertEqual(audit["evidence_window"]["record_count"], 3)

    def test_manifest_detects_order_and_text_changes(self):
        original = evidence_window_manifest(self.docs)
        same = evidence_window_manifest([dict(doc) for doc in self.docs])
        self.assertEqual(assert_same_evidence_window(original, same), original["sha256"])

        reordered = evidence_window_manifest(list(reversed(self.docs)))
        with self.assertRaises(AssertionError):
            assert_same_evidence_window(original, reordered)

        changed = [dict(doc) for doc in self.docs]
        changed[0]["text"] = "changed"
        with self.assertRaises(AssertionError):
            assert_same_evidence_window(original, evidence_window_manifest(changed))


class MatchedAnswerPathRegressionTests(unittest.TestCase):
    def test_parenthesized_enhancement_is_recognized(self):
        question = "What method does AT-3(3) specify?"
        self.assertTrue(_query_allows_enhancements(question))
        self.assertEqual(_extract_control_hints(question), ["AT-3.3"])

    def test_locked_window_enhancement_citations_are_preserved(self):
        citations = ["at-3.3_smt", "at-3.3_gdn", "at-3.3_smt", ""]
        self.assertEqual(
            _ordered_unique_citation_ids(citations),
            ["at-3.3_smt", "at-3.3_gdn"],
        )


if __name__ == "__main__":
    unittest.main()
