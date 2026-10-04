# Registered primary RQ1 constant-sensitivity study

Result identity: `rq1_constant_sensitivity_v1`.

This exploratory study evaluates local sensitivity of the historical primary S7
retrieval configuration on the unchanged 36 Rev.4 and 100 Rev.5 questions. It
changes three influential constants separately by ±20%; it does not select a new
main configuration or replace the historical RQ1 tables. The existing gate-width
experiment changes another mechanism and does not answer this question.

## Configuration and source boundary

The authoritative implementation is the committed
`experiments/retriever_ablation/notebook/AblationStudy_S1_7.ipynb`. The adapter
extracts and executes its original normalization, lexical/dense construction,
rewrite filtering, fusion and S7 gate definitions. The full notebook and each
extracted definition are hashed. No historical notebook is edited. The current
production retriever's adaptive adoption threshold, diagnostic query transform
and privilege heuristic are not substituted for the primary notebook logic.

Keep BM25 k1=1.5, b=0.75; candidate pool=50 controls; RRF k=60; at most three
filtered rewrites; rewrite weight=0.25; token Jaccard cutoff=0.15; skip enabled;
and no required lexical/dense top-1 agreement. Canonical statement/guidance
records, control aggregation, fallback texts, E5 passage prefixing and the
notebook's unprefixed query encoding remain as originally implemented.

| Condition | Blend α | Fixed adoption margin | Skip margin |
|---|---:|---:|---:|
| baseline | 0.65 | 0.15 | 0.10 |
| alpha_minus20 | 0.52 | 0.15 | 0.10 |
| alpha_plus20 | 0.78 | 0.15 | 0.10 |
| adoption_minus20 | 0.65 | 0.12 | 0.10 |
| adoption_plus20 | 0.65 | 0.18 | 0.10 |
| skip_minus20 | 0.65 | 0.15 | 0.08 |
| skip_plus20 | 0.65 | 0.15 | 0.12 |

The complement of α remains 1−α. The matrix is seven conditions × 136 questions
= 952 evaluations. No row, revision or unfavorable condition is excluded. The
37 ErrorBank rows are outside this registered matrix; their previous artifacts
and labels remain unchanged.

## Frozen inputs and inference

Register question identities, original text, governing-control labels, frozen
rewrite strings, accepted variants, original ranks and gate flags. Pin and hash
both CCS files, gold files, rewrite files, historical S7 result CSVs, source code,
requirements and this protocol. Publish the registration before fresh inference.
No new LLM rewrites or benchmark annotation is performed. Reference labels enter
scoring after retrieval; they do not enter embeddings, candidate selection or
cross-encoder inputs.

Use `intfloat/e5-small-v2` at revision
`ffb93f3bd4047442299a41ebb6fa998a38507c52`, and `BAAI/bge-reranker-base` at revision
`2cfc18c9415c912f9d8155881c133215df768a70`. Pin the package versions in
`requirements-colab.txt`. Record native model-file hashes, actual GPU, CUDA,
package versions, source commit and protocol hashes. Use float32, seed 42,
deterministic PyTorch algorithms and disabled TF32. The Colab notebook requests
A100 and requires an allocated GPU for formal inference. Allocation class is
recorded rather than inferred from notebook metadata.

For each question, perform one complete-candidate probe using the primary
function with its skip gate disabled and adoption margin zero. Capture every
accepted variant's lexical ranking/full score vector, returned dense control
ranking/scores and best-clause identity/text, all cross-encoder pairs/scores, and
the ungated result. This covers controls that the original skip gate did not
score. Replay the primary function for all seven registered conditions using
exactly those captured channel/pair inputs. Reject changed call inputs or
incomplete captures, including exceptions the original dense-search handler
would otherwise suppress. Reproduce every ungated probe exactly after capture
and again during scoring. The study freezes upstream outputs within each query;
it does not perturb dense/BM25 parameters, rewrite generation, or candidate width.

The saved historical CSVs lack complete raw channel/cross-encoder scores and
cannot reconstruct all changed decisions. This study therefore makes a fresh
inference capture. Historical model commit revisions and full runtime versions
were not recorded. Compare the new baseline with all saved historical top-10
orders, gold ranks and gate/variant flags. Report every difference. Equality is a
diagnostic, not an acceptance filter or permission to tune. Do not claim recovery
of an unrecorded historical model revision or silently replace headline scores.

## Measures and exploratory comparisons

Report Success@1/5/10, MRR@10 and nDCG@10 for each revision and the 136-row pool.
One governing control is labeled per query; nDCG@10 is 1/log2(rank+1) for a hit
and zero for a miss. Missed/truncated gold ranks are zero. Give Wilson 95%
intervals for success proportions. Compare each changed condition with the new
shared baseline using paired gains/losses and exact two-sided McNemar tests.
P-values are exploratory and unadjusted. For paired MRR/nDCG differences, use
10,000 paired query bootstrap resamples, seed 42, and percentile 95% intervals.
Publish the range over all seven conditions, including deterioration.

Retain each query's full control order, gold rank, configured thresholds,
logical reranker-call/adoption flags, margins and cache fingerprint. Compare
the actual decision with the ungated blended proposal using identical scores.
For skip and adoption gates separately, count prevented reference errors and
blocked reference corrections relative to the unchanged author labels. These
counts do not establish independent correctness. Complete-candidate probe cost
is incurred regardless of logical skipping, so logical call counts must not be
presented as measured latency or cost savings.

## Acceptance, persistence and limits

Require all 136 complete cache probes to reproduce exactly; all 952 unique
question-condition rows; unchanged source/input hashes and upstream retrieval
identities; all model snapshots pinned; and complete reporting of all seven
conditions. A historical-baseline difference does not remove a query. All source
and registration files must be committed and the execution checkout clean.
The bootstrap notebook is a launcher and is excluded from the scientific code
hash manifest so it can be stamped with the public registration commit after
publication; the runner still validates all scientific code and inputs.

Write per-query cache files and hashes to persistent storage after every
completed capture. Resume only with identical code, inputs, model-file hashes,
runtime and source commit. Preserve incompatible/failed runs. Never overwrite a
historical experiment or adjust this protocol after outcomes; changes require a
new study identity. Retain raw captures, ranks, historical differences, summary,
checksums and a complete result ZIP.

Sensitivity is local to these three constants on the author-labeled benchmark.
It does not establish held-out validity, remove evaluation-set tuning bias,
recover an incomplete tuning history, or establish behavior for other corpora
and authentic user questions. It does not validate annotation correctness or
answer-level semantic completeness. Independent expert adjudication remains
separate future work. The study is pending until the registered inference and
all 952 evaluations are completed and verified.
