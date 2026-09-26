# Runtime Verifier Mutation Evaluation

This experiment applies five deterministic single-field mutation operators to the 136 frozen valid ComplianceGPT contracts from the matched-window RQ2 v3 archive. It measures the gold-independent Runtime Verifier's detection rate and triggering predicates for each operator.

The result identity is `runtime_verifier_mutation_v1`. It does not replace the frozen RQ2 v3, no-selector v1, or rescue-ablation v1 results.

## Run

From the repository root:

```bash
python experiments/answerer_comparison/runtime_verifier_mutation/run_verifier_mutations.py \
  --output-dir experiments/answerer_comparison/runtime_verifier_mutation/results_v1
```

The output directory and sibling ZIP archive must not already exist. The runner validates all 136 baseline contracts before mutation, hashes the frozen archive before and after execution, and uses no gold labels, retrieval, selector, model, or offline scorer.

## Operators

1. swap the first source ID for a valid but different active-revision ID;
2. alter one character in the first evidence span;
3. place a Rev. 4-only ID in a Rev. 5 contract;
4. remove one entry from a nonempty `odp_required_list`;
5. flip `OK` and `PARAMS_REQUIRED`.

Detection means that `verify_contract_validity` accepts the original contract and rejects the mutated contract. Operator-specific rates, triggering error tags, and undetected examples are reported separately. These results establish behavior only for the defined mutations and implemented structural predicates; they do not establish evidence completeness or legal correctness.

## Recorded result

All 136 source contracts passed before mutation. The frozen `results_v1`
record contains the following operator-specific outcomes:

| Operator | Attempted | Detected | Rate | Triggering predicate(s) |
|---|---:|---:|---:|---|
| Valid active-revision ID swap | 136 | 136 | 1.0000 | `SpanNotVerbatim` |
| One-character span alteration | 136 | 136 | 1.0000 | `SpanNotVerbatim` |
| Rev. 4-only ID in Rev. 5 | 100 | 100 | 1.0000 | `UnknownSourceId` |
| Remove one ODP-list entry | 111 | 41 | 0.3694 | `ParamsRequiredButODPListEmpty` |
| Status flip | 136 | 136 | 1.0000 | status/placeholder/list consistency |

The 41 detected ODP-list removals are exactly the singleton lists that become
empty. All 70 removals from multi-entry lists remain undetected because the
implemented predicate requires only a nonempty list under `PARAMS_REQUIRED`;
it does not compare the list with every visible placeholder.

The result archive SHA-256 is
`8bbb98b0f40299a5d46cf0106262c3d3437eb0ffcbbb0111c2d3ab1172f86366`.
