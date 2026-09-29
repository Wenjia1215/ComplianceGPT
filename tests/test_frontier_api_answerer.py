import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from answerer_comparison.frontier_api_answerer import (
    LOG_SCHEMA_VERSION,
    make_gemini_generate_content_answerer_class,
    read_api_call_log,
    summarize_usage,
)
from generative_answerer.generator import BaselineGenerativeAnswerer, build_system_prompt


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def generate_content(self, **kwargs):
        self.requests.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake response remains.")
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.models = FakeModels(responses)


def fake_response(response_id, output_text, model="gemini-3.5-flash"):
    candidate = SimpleNamespace(
        finish_reason="STOP",
        finish_message="",
        safety_ratings=[],
        citation_metadata=None,
        content={
            "role": "model",
            "parts": [{"text": output_text, "thought_signature": f"sig-{response_id}"}],
        },
    )
    return SimpleNamespace(
        response_id=response_id,
        model_version=model,
        text=output_text,
        create_time="2026-09-29T12:00:00Z",
        usage_metadata={
            "prompt_token_count": 100,
            "candidates_token_count": 20,
            "thoughts_token_count": 5,
            "total_token_count": 125,
        },
        prompt_feedback=None,
        model_status=None,
        candidates=[candidate],
    )


class FrontierAPIAnswererTest(unittest.TestCase):
    def build_answerer(self, directory, responses, **overrides):
        cls = make_gemini_generate_content_answerer_class(BaselineGenerativeAnswerer)
        kwargs = {
            "client": FakeClient(responses),
            "model_id": "gemini-3.5-flash",
            "system_prompt": build_system_prompt(),
            "query_id_by_question": {"What is required?": "1", "Second?": "2"},
            "call_log_path": Path(directory) / "responses.jsonl",
            "thinking_level": "LOW",
            "temperature": 1.0,
            "max_output_tokens": 2048,
            "max_parse_retries": 2,
        }
        kwargs.update(overrides)
        return cls(**kwargs)

    def test_valid_response_reuses_frozen_prompt_and_normalizer(self):
        payload = json.dumps(
            {
                "status": "OK",
                "answer_text": "Use the registered control.",
                "cited_source_ids": ["ac-1_smt", "invented"],
                "odp_required_list": [],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            answerer = self.build_answerer(directory, [fake_response("resp_1", payload)])
            result = answerer.generate(
                "What is required?",
                [{"id": "ac-1_smt", "text": "Use the registered control."}],
            )
            self.assertEqual(result["status"], "OK")
            self.assertEqual(result["cited_source_ids"], ["ac-1_smt"])
            self.assertEqual(result["api_provenance"]["query_id"], "1")
            self.assertEqual(result["api_provenance"]["response_model"], "gemini-3.5-flash")
            request = answerer.client.models.requests[0]
            self.assertEqual(request["model"], "gemini-3.5-flash")
            self.assertEqual(request["config"]["thinking_config"], {"thinking_level": "LOW"})
            self.assertEqual(request["config"]["temperature"], 1.0)
            self.assertEqual(request["config"]["max_output_tokens"], 2048)
            self.assertEqual(request["config"]["system_instruction"], build_system_prompt())
            self.assertEqual(request["contents"][0]["role"], "user")
            rows = read_api_call_log(Path(directory) / "responses.jsonl")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["schema_version"], LOG_SCHEMA_VERSION)
            self.assertEqual(rows[0]["provider"], "google-gemini")
            self.assertEqual(rows[0]["response_id"], "resp_1")

    def test_parse_retry_is_logged_and_preserves_gemini_roles(self):
        valid = json.dumps(
            {
                "status": "NO_EVIDENCE",
                "answer_text": "",
                "cited_source_ids": [],
                "odp_required_list": [],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            answerer = self.build_answerer(
                directory,
                [fake_response("resp_bad", "not json"), fake_response("resp_good", valid)],
            )
            result = answerer.generate("What is required?", [{"id": "ac-1_smt", "text": "x"}])
            self.assertEqual(result["status"], "NO_EVIDENCE")
            self.assertEqual(len(result["api_provenance"]["api_calls"]), 2)
            retry_contents = answerer.client.models.requests[1]["contents"]
            self.assertEqual(len(retry_contents), 3)
            self.assertEqual([row["role"] for row in retry_contents], ["user", "model", "user"])
            self.assertEqual(
                retry_contents[1]["parts"][0]["thought_signature"], "sig-resp_bad"
            )
            self.assertEqual(
                [row["response_id"] for row in read_api_call_log(Path(directory) / "responses.jsonl")],
                ["resp_bad", "resp_good"],
            )

    def test_model_change_is_logged_then_rejected(self):
        payload = json.dumps(
            {
                "status": "NO_EVIDENCE",
                "answer_text": "",
                "cited_source_ids": [],
                "odp_required_list": [],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            answerer = self.build_answerer(
                directory,
                [
                    fake_response("resp_1", payload, "gemini-3.5-flash-001"),
                    fake_response("resp_2", payload, "gemini-3.5-flash-002"),
                ],
            )
            answerer.generate("What is required?", [{"id": "ac-1_smt", "text": "x"}])
            with self.assertRaisesRegex(RuntimeError, "model changed"):
                answerer.generate("Second?", [{"id": "ac-1_smt", "text": "x"}])
            rows = read_api_call_log(Path(directory) / "responses.jsonl")
            self.assertEqual([row["response_id"] for row in rows], ["resp_1", "resp_2"])

    def test_existing_log_locks_settings_and_model(self):
        payload = json.dumps(
            {
                "status": "NO_EVIDENCE",
                "answer_text": "",
                "cited_source_ids": [],
                "odp_required_list": [],
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            first = self.build_answerer(directory, [fake_response("resp_1", payload)])
            first.generate("What is required?", [{"id": "ac-1_smt", "text": "x"}])
            resumed = self.build_answerer(directory, [])
            self.assertEqual(resumed.resolved_model, "gemini-3.5-flash")
            with self.assertRaisesRegex(RuntimeError, "max_output_tokens"):
                self.build_answerer(directory, [], max_output_tokens=4096)

    def test_invalid_thinking_level_is_forbidden(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "thinking level"):
                self.build_answerer(directory, [], thinking_level="unbounded")

    def test_usage_summary_tolerates_missing_fields(self):
        summary = summarize_usage(
            [
                {
                    "usage": {
                        "prompt_token_count": 10,
                        "candidates_token_count": 2,
                        "total_token_count": 12,
                    }
                },
                {"usage": {"prompt_token_count": 5}},
                {"usage": None},
            ]
        )
        self.assertEqual(summary["api_calls"], 3)
        self.assertEqual(summary["totals"]["prompt_token_count"], 15)
        self.assertEqual(summary["totals"]["candidates_token_count"], 2)
        self.assertEqual(summary["totals"]["total_token_count"], 12)
        self.assertEqual(summary["calls_with_field"]["prompt_token_count"], 2)


if __name__ == "__main__":
    unittest.main()
