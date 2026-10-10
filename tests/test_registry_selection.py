"""Check registry isolation, provenance, and real prepared-context output."""

import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from answerer_comparison.matched_window_runner import FrozenCCSRetriever
from compliancegpt.pipeline.evidence_window import evidence_window_manifest
from compliancegpt.pipeline.odp_registry import load_registry_selection, resolve_registry_path, REPAIRED_REGISTRY_ID
from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline

ROOT = Path(__file__).resolve().parents[1]


class RegistrySelectionTests(unittest.TestCase):
    def test_default_keeps_original_prompt_and_records_exact_hash(self):
        data, metadata = load_registry_selection("rev5")
        self.assertIn("org units", data["au-02_odp.01"]["ask_prompt"])
        self.assertEqual(metadata["registry_id"], "odp_registry_legacy_rev5")
        self.assertEqual(metadata["sha256"], hashlib.sha256((ROOT / "data/ODP/rev5/odp_registry_rev5.json").read_bytes()).hexdigest())

    def test_explicit_repair_changes_only_the_sixteen_guarded_entries(self):
        expected = {"rev4": 3, "rev5": 13}
        for revision in expected:
            with self.subTest(revision=revision):
                old, _ = load_registry_selection(revision)
                new, metadata = load_registry_selection(revision, registry_version=REPAIRED_REGISTRY_ID)
                self.assertEqual(set(old), set(new))
                self.assertEqual(sum(old[p] != new[p] for p in old), expected[revision])
                self.assertEqual(metadata["registry_id"], REPAIRED_REGISTRY_ID)
                self.assertEqual(metadata["revision"], revision)
                self.assertTrue(metadata["loaded"])

    def test_rejects_unknown_version_and_ambiguous_custom_path(self):
        for kw in ({"registry_version": "unknown"}, {"registry_version": REPAIRED_REGISTRY_ID, "path_override": "legacy.json"}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                load_registry_selection("rev5", **kw)

    def test_repaired_registry_rejects_drift_and_wrong_revision_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "data/ODP/registry_v2", root / "data/ODP/registry_v2")
            path = root / "data/ODP/registry_v2/rev5/odp_registry_rev5.json"
            data = json.loads(path.read_text())
            data["au-02_odp.01"]["version"] = "rev4"
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, "bytes"):
                load_registry_selection("rev5", registry_version=REPAIRED_REGISTRY_ID, repository_root=root)
            manifest_path = root / "data/ODP/registry_v2/REGISTRY_MANIFEST.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["files_sha256"]["rev5/odp_registry_rev5.json"] = hashlib.sha256(path.read_bytes()).hexdigest()
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "revision"):
                load_registry_selection("rev5", registry_version=REPAIRED_REGISTRY_ID, repository_root=root)

    def test_custom_registry_is_identified_by_its_own_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "custom.json"
            path.write_text('{}')
            data, metadata = load_registry_selection("rev4", path_override=str(path))
            self.assertEqual(data, {})
            self.assertEqual(metadata["registry_id"], "custom")
            self.assertEqual(metadata["sha256"], hashlib.sha256(b'{}').hexdigest())
            self.assertEqual(metadata["selection"], "custom_path")

    def test_missing_custom_registry_retains_legacy_fallback_without_claiming_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            data, metadata = load_registry_selection("rev5", path_override=str(Path(tmp) / "missing.json"))
        self.assertEqual(data, {})
        self.assertFalse(metadata["loaded"])
        self.assertIsNone(metadata["sha256"])

    def test_revision_aliases_resolve_without_crossing_catalogs(self):
        self.assertEqual(resolve_registry_path("r4"), ROOT / "data/ODP/rev4/odp_registry_rev4.json")
        self.assertEqual(resolve_registry_path("5", registry_version="source_repair_v2"),
                         ROOT / "data/ODP/registry_v2/rev5/odp_registry_rev5.json")

    def pipeline(self, version):
        class Config: _commit_hash = "frozen-test"
        class Model: config = Config()
        class Tokenizer:
            pad_token_id = 0
            eos_token_id = 1
            init_kwargs = {"_commit_hash": "frozen-test"}
        class Selector:
            def generate(self, *args):
                return {"status": "OK", "evidence_spans": [{"source_id": "au-2_smt.a"}]}
        records = {r["id"]: r for r in map(json.loads, (ROOT / "data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl").read_text().splitlines())}
        record = records["au-2_smt.a"]
        window = evidence_window_manifest([record])
        context = {"question": "Which event types can the system log?", "framework_version": "rev5",
                   "retrieved_docs": [record], "evidence_window": [record], "evidence_window_manifest": window,
                   "retrieval_meta": {"selected_controls": ["AU-2"], "primary_control": "AU-2"}}
        pipe = ComplianceGPTPipeline(framework_version="rev5", shared_model=Model(), shared_tokenizer=Tokenizer(),
                generator_instance=Selector(), retriever_instance=FrozenCCSRetriever(records), use_qur=False,
                strict_ccs_assert=False, odp_registry_version=version, resolution_policy="ASK")
        return pipe, context

    def test_pipeline_uses_selected_prompts_and_keeps_body_and_evidence(self):
        old_pipe, context = self.pipeline("legacy")
        new_pipe, _ = self.pipeline(REPAIRED_REGISTRY_ID)
        old = old_pipe.answer(context["question"], prepared_context=copy.deepcopy(context))["contract"]
        new = new_pipe.answer(context["question"], prepared_context=copy.deepcopy(context))["contract"]
        for field in ("answer_text", "evidence_spans", "odp_required_list", "status", "primary_citation", "all_citations"):
            self.assertEqual(old[field], new[field])
        self.assertEqual(new["odp_registry"]["registry_id"], REPAIRED_REGISTRY_ID)
        self.assertEqual(new_pipe.odp_registry_path, str(ROOT / "data/ODP/registry_v2/rev5/odp_registry_rev5.json"))
        self.assertIn("org units", old["ask_list"][0]["ask_prompt"])
        self.assertIn("event types", new["ask_list"][0]["ask_prompt"])
        self.assertEqual(old["validity_check"], {"is_pass": True, "errors": []})
        self.assertEqual(new["validity_check"], old["validity_check"])

    def test_error_output_records_the_selected_registry(self):
        pipe, _ = self.pipeline(REPAIRED_REGISTRY_ID)
        contract = pipe.answer("")["contract"]
        self.assertEqual(contract["status"], "ERROR")
        self.assertEqual(contract["odp_registry"]["registry_id"], REPAIRED_REGISTRY_ID)


if __name__ == "__main__":
    unittest.main()
