# Batch 5C — Rev. 4 Frontier API Baseline

[Open the clean Batch 5C notebook in Colab](https://colab.research.google.com/github/Wenjia1215/ComplianceGPT/blob/main/experiments/answerer_comparison/rq2_frontier_baseline/Batch_5C_Rev4_Frontier_API_Baseline.ipynb)

This registered follow-on study addresses the stronger-baseline requirement for RQ2. It runs the same free-form answer prompt against the same 36 frozen Revision 4 questions and ordered evidence windows, but replaces the Qwen2.5-7B answer call with the stable Gemini API model `gemini-3.5-flash`. Google describes this model as providing sustained frontier-level intelligence, and its current pricing table includes a free tier.

The result identity is `rq2_frontier_baseline_v1`. It is a new result family and never edits or replaces RQ2 v3 or Batch 5B.

## Registered boundary

- Framework: NIST SP 800-53 Revision 4 only.
- Questions: the same 36 rows used in RQ2 v3 and Batch 5B.
- API model request: `gemini-3.5-flash` (stable model ID, not a `latest` or preview alias).
- Model snapshot boundary: every response ID and server-reported model version is retained, and the runner stops if that version changes within one output directory.
- Prompt: the exact frozen free-form system prompt, context serialization, user prompt, JSON parser, fail-closed normalization, and two parse retries from source commit `be862bcadfa61b474d795303e01ce9394909fdcc`.
- Frozen prompt SHA-256: `91ba0d840befd5517fbec7595f640333bcb8df8e63301e80552dad841744fdef`.
- API settings: thinking level `LOW`, temperature `1.0` (the Gemini 3 recommended default), maximum output tokens `2048`, no tools, and no API-enforced structured-output schema. Parse retries return the prior response's thought signature exactly as required by the Gemini 3 multi-turn contract; signatures are not exposed as model output.
- Retrieval: none. The runner consumes immutable ordered contexts from the validated RQ2 v3 archive.
- Gold policy: gold labels never enter an API request; they are used only by the unchanged offline verifier.
- Hardware: CPU is sufficient because model inference is remote. A Colab GPU provides no benefit and wastes compute units.

The API run is a stronger-system comparison, not a one-factor precision experiment. Questions, evidence, prompt/parser, ODP policy, and verifier are fixed; the model and serving runtime change. API sampling may not reproduce byte-identical text on a later run.

## Authentication, quota, and data-use boundary

Create a fresh key in [Google AI Studio](https://aistudio.google.com/apikey) and expose it as `GEMINI_API_KEY`. Never paste a key into a notebook cell, chat, result archive, or Git commit. The runner reads it only from the environment and never prints or records its value. Revoke any key that has been pasted into a chat or screenshot before running.

The current Gemini pricing table lists a free tier for `gemini-3.5-flash`, but quotas and availability can change. The 36 first-attempt prompts contain roughly 227,000 characters in total (about 57,000 tokens by a simple characters-per-token estimate). Actual prompt, candidate, thinking, and total token counts are taken from each API response and aggregated in the final manifest. Parse retries increase quota use. If a free-tier rate limit returns HTTP 429, wait for quota recovery and run the notebook again; completed rows are validated and skipped.

Google's current pricing table states that free-tier content may be used to improve its products, while paid-tier content is not. This run sends only the frozen model-visible experiment question and NIST evidence window; gold labels and the API key are never sent as prompt content. Review the current [Gemini pricing and data-use table](https://ai.google.dev/gemini-api/docs/pricing) before running.

## Deterministic preparation without an API key

From the repository root:

```bash
python experiments/answerer_comparison/rq2_frontier_baseline/run_frontier_baseline.py \
  --output-dir /tmp/rq2_frontier_baseline_v1 \
  --prepare-only
```

This verifies the frozen archive and source commit, extracts exactly 36 Rev. 4 contexts, verifies every order-sensitive evidence-window hash, copies the registered 4-bit and BF16 references, and writes `PREPARED_CONTEXTS.md`. It does not read an API key or make an API call.

## Full API run

Install the lightweight dependencies, set the key in memory, and use a persistent output directory:

```bash
python -m pip install -r experiments/answerer_comparison/rq2_frontier_baseline/requirements-api.txt
read -rsp "GEMINI_API_KEY: " GEMINI_API_KEY
export GEMINI_API_KEY
python experiments/answerer_comparison/rq2_frontier_baseline/run_frontier_baseline.py \
  --output-dir /content/drive/MyDrive/rq2_frontier_baseline_v1
```

For Colab, use the notebook linked at the top of this README. Its first code cell mounts Drive, and a later cell reads `GEMINI_API_KEY` from Colab Secrets without displaying it. A CPU runtime is sufficient; selecting a GPU does not accelerate this API run.

The runner checkpoints one contract at a time. Re-running the command validates completed rows and skips them. The cumulative API response log is atomically checkpointed before the result CSV, so returned responses remain visible even if the runtime disconnects between an API response and a row checkpoint. Such orphaned calls are reported and excluded from scientific results.

The completed directory contains:

- `contracts/rev4_generative_frontier_api.csv` — 36 checkpointed outputs;
- `api/responses.jsonl` — response IDs, raw output, server-reported model, latency, status, and token usage for every billed response;
- `references/` — unchanged 4-bit, BF16, and ComplianceGPT paired references;
- `manifests/` — source, prompt, API runtime, response, run, and output hashes;
- `summary.json` and `SUMMARY.md` — descriptive metrics and paired exact McNemar tests; and
- a sibling `rq2_frontier_baseline_v1.zip` archive.

The summary compares the frontier API baseline with the validated Qwen BF16 baseline, the frozen Qwen 4-bit baseline, and frozen 4-bit ComplianceGPT. ODP operating characteristics against author labels remain provisional until blinded independent annotation is returned.
