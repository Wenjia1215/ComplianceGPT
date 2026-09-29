# Batch 5C — Rev. 4 Frontier API Baseline

This registered follow-on study addresses the stronger-baseline requirement for RQ2. It runs the same free-form answer prompt against the same 36 frozen Revision 4 questions and ordered evidence windows, but replaces the Qwen2.5-7B answer call with the OpenAI Responses API model alias `gpt-6-astra`.

The result identity is `rq2_frontier_baseline_v1`. It is a new result family and never edits or replaces RQ2 v3 or Batch 5B.

## Registered boundary

- Framework: NIST SP 800-53 Revision 4 only.
- Questions: the same 36 rows used in RQ2 v3 and Batch 5B.
- API model request: `gpt-6-astra`.
- Model snapshot boundary: the public API exposes a mutable alias rather than a registered immutable snapshot in this experiment. Every response ID and server-reported model string is retained, and the runner stops if that string changes within one output directory.
- Prompt: the exact frozen free-form system prompt, context serialization, user prompt, JSON parser, fail-closed normalization, and two parse retries from source commit `be862bcadfa61b474d795303e01ce9394909fdcc`.
- Frozen prompt SHA-256: `91ba0d840befd5517fbec7595f640333bcb8df8e63301e80552dad841744fdef`.
- API settings: reasoning effort `low`, maximum output tokens `2048`, `store=false`, no tools, and no API-enforced structured-output schema.
- Retrieval: none. The runner consumes immutable ordered contexts from the validated RQ2 v3 archive.
- Gold policy: gold labels never enter an API request; they are used only by the unchanged offline verifier.
- Hardware: CPU is sufficient because model inference is remote. A Colab GPU provides no benefit and wastes compute units.

The API run is a stronger-system comparison, not a one-factor precision experiment. Questions, evidence, prompt/parser, ODP policy, and verifier are fixed; the model and serving runtime change. API sampling may not reproduce byte-identical text on a later run.

## Authentication and billing

Create an OpenAI API key in the API platform, ensure the API project has billing or credits, and expose the key as `OPENAI_API_KEY`. ChatGPT or Colab subscriptions do not supply API credits. The key is read only from the environment and is never printed, written to Drive, included in the result archive, or committed to GitHub.

The 36 first-attempt prompts contain roughly 227,000 characters in total (about 57,000 tokens by a simple characters-per-token estimate). Actual input, output, and reasoning token counts are taken from each API response and aggregated in the final manifest. Parse retries increase usage. Check the current official model pricing before starting.

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
read -rsp "OPENAI_API_KEY: " OPENAI_API_KEY
export OPENAI_API_KEY
python experiments/answerer_comparison/rq2_frontier_baseline/run_frontier_baseline.py \
  --output-dir /content/drive/MyDrive/rq2_frontier_baseline_v1
```

For Colab, use the notebook linked at the top of this README after it is published. Its first code cell mounts Drive, and a later cell reads `OPENAI_API_KEY` from Colab Secrets without displaying it.

The runner checkpoints one contract at a time. Re-running the command validates completed rows and skips them. The append-only API response log is checkpointed before the result CSV, so billed responses remain visible even if the runtime disconnects between an API response and a row checkpoint. Such orphaned calls are reported and excluded from scientific results.

The completed directory contains:

- `contracts/rev4_generative_frontier_api.csv` — 36 checkpointed outputs;
- `api/responses.jsonl` — response IDs, raw output, server-reported model, latency, status, and token usage for every billed response;
- `references/` — unchanged 4-bit, BF16, and ComplianceGPT paired references;
- `manifests/` — source, prompt, API runtime, response, run, and output hashes;
- `summary.json` and `SUMMARY.md` — descriptive metrics and paired exact McNemar tests; and
- a sibling `rq2_frontier_baseline_v1.zip` archive.

The summary compares the frontier API baseline with the validated Qwen BF16 baseline, the frozen Qwen 4-bit baseline, and frozen 4-bit ComplianceGPT. ODP operating characteristics against author labels remain provisional until blinded independent annotation is returned.
