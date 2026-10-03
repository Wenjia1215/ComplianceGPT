import json
import tempfile
import unittest
from pathlib import Path

from answerer_comparison.matched_window_runner import FrozenCCSRetriever
from compliancegpt.pipeline.pipeline import ComplianceGPTPipeline


class _DummyConfig:
    _commit_hash = "frozen-model-commit"


class _DummyModel:
    config = _DummyConfig()


class _DummyTokenizer:
    pad_token_id = 0
    eos_token_id = 1
    init_kwargs = {"_commit_hash": "frozen-model-commit"}


class FrozenGeneratorInjectionTests(unittest.TestCase):
    def test_injected_generator_skips_model_backed_generator_construction(self):
        generator = object()
        retriever = FrozenCCSRetriever(
            {
                "ac-1_smt": {
                    "id": "ac-1_smt",
                    "kind": "smt",
                    "control_id": "AC-1",
                    "text": "Test statement.",
                }
            }
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            registry = Path(temp_dir) / "odp.json"
            registry.write_text(json.dumps({}), encoding="utf-8")
            pipeline = ComplianceGPTPipeline(
                framework_version="rev5",
                model_id="frozen-model",
                model_revision="frozen-model-commit",
                shared_model=_DummyModel(),
                shared_tokenizer=_DummyTokenizer(),
                generator_instance=generator,
                retriever_instance=retriever,
                use_qur=False,
                ccs_path=str(Path(temp_dir) / "unused.jsonl"),
                odp_registry_path=str(registry),
                strict_ccs_assert=False,
                resolution_policy="PRESERVE",
            )

        self.assertIs(pipeline.generator, generator)
        self.assertEqual(pipeline.model_resolved_revision, "frozen-model-commit")
        self.assertEqual(pipeline.tokenizer_resolved_revision, "frozen-model-commit")


if __name__ == "__main__":
    unittest.main()
