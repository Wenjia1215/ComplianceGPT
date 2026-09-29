import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from answerer_comparison.frontier_api_answerer import (
    LOG_SCHEMA_VERSION,
    make_openai_responses_answerer_class,
    read_api_call_log,
    summarize_usage,
)
from generative_answerer.generator import BaselineGenerativeAnswerer, build_system_prompt


class FakeResponses:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        if not self.responses:
            raise AssertionError("No fake response remains.")
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


def fake_response(response_id, output_text, model="gpt-6-astra"):
    return SimpleNamespace(
        id=response_id,
        model=model,
        output_text=output_text,
        created_at=123456,
        status="completed",
        usage={"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        incomplete_details=None,
        error=None,
    )


class FrontierAPIAnswererTest(unittest.TestCase):
    def build_answerer(self, directory, responses, **overrides):
        cls = make_openai_responses_answerer_class(BaselineGenerativeAnswerer)
        kwargs = {
            "client": FakeClient(responses),
            "model_id": "gpt-6-astra",
            "system_prompt": build_system_prompt(),
            "query_id_by_question": {"What is required?": "1", "Second?": "2"},
            "call_log_path": Path(directory) / "responses.jsonl",
            "reasoning_effort": "low",
            "max_output_tokens": 2048,
            "max_parse_retries": 2,
            "store": False,
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
            self.assertEqual(result["api_provenance"]["response_model"], "gpt-6-astra")
            request = answerer.client.responses.requests[0]
            self.assertEqual(request["model"], "gpt-6-astra")
            self.assertEqual(request["reasoning"], {"effort": "low"})
            self.assertEqual(request["max_output_tokens"], 2048)
            self.assertFalse(request["store"])
            self.assertEqual(request["input"][0]["content"], build_system_prompt())
            rows = read_api_call_log(Path(directory) / "responses.jsonl")
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["schema_version"], LOG_SCHEMA_VERSION)
            self.assertEqual(rows[0]["response_id"], "resp_1")

    def test_parse_retry_is_logged_and_returned_in_provenance(self):
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
            self.assertEqual(len(answerer.client.responses.requests[1]["input"]), 4)
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
                    fake_response("resp_1", payload, "gpt-6-astra-2026-09-01"),
                    fake_response("resp_2", payload, "gpt-6-astra-2026-09-15"),
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
            self.assertEqual(resumed.resolved_model, "gpt-6-astra")
            with self.assertRaisesRegex(RuntimeError, "max_output_tokens"):
                self.build_answerer(directory, [], max_output_tokens=4096)

    def test_store_true_is_forbidden(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "store=False"):
                self.build_answerer(directory, [], store=True)

    def test_usage_summary_tolerates_missing_fields(self):
        summary = summarize_usage(
            [
                {"usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}},
                {"usage": {"input_tokens": 5}},
                {"usage": None},
            ]
        )
        self.assertEqual(summary["api_calls"], 3)
        self.assertEqual(summary["totals"], {"input_tokens": 15, "output_tokens": 2, "total_tokens": 12})
        self.assertEqual(summary["calls_with_field"]["input_tokens"], 2)


if __name__ == "__main__":
    unittest.main()
