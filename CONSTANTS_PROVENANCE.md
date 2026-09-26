# Evaluation Constants: Provenance and Limitations

This record identifies the fixed values that materially shape the released
retrieval and answer-construction configurations. It distinguishes settings
with an external trace from project development choices. No value is presented
as universally optimal.

## Provenance classes

- **Traceable setting:** a package-common default or a value reported in prior
  literature. Traceability does not establish optimality for ComplianceGPT.
- **Project development choice:** an engineering, gate, or capacity value
  retained during project development. A complete tuning log was not preserved,
  and no separate development set was maintained.

## Complete constant record

| Setting family | Released value | Provenance class | Recorded scope |
|---|---:|---|---|
| BM25 `k1` | `1.5` | Traceable setting | Matches the default in [`dorianbrown/rank_bm25`](https://github.com/dorianbrown/rank_bm25); the ComplianceGPT implementation uses a different IDF expression. |
| BM25 `b` | `0.75` | Traceable setting | Same boundary as `k1`. |
| RRF rank constant | `60` | Traceable setting | Pilot value reported by [Cormack, Clarke, and Buettcher (2009)](https://doi.org/10.1145/1571941.1572114); not independently optimized here. |
| Candidate controls | `50` | Project development choice | Control-ranking candidate pool. |
| Accepted rewrites | at most `3` | Project development choice | S7 variant bound. |
| Rewrite weight | `0.25` | Project development choice | Weight per accepted rewrite; original/transformed query weight is `1.0`. |
| Rewrite Jaccard gate | `0.15` | Project development choice | Minimum overlap used when filtering rewrites. |
| Rerank blend | `0.65` base / `0.35` cross-encoder | Project development choice | Normalized score blend. |
| Rerank skip margin | `0.10` | Project development choice | Skip cross-encoder when base ordering is sufficiently separated. |
| Changed-top adoption margin | `0.15` | Project development choice | Normal rerank adoption threshold. |
| Low-confidence trigger and adoption margin | `0.08` / `0.10` | Project development choice | Lower adoption threshold when the base margin is below `0.08`. |
| Privilege-scope adjustment | `+0.08` / `-0.06` of peak fused score | Project development choice | Secondary diagnostic only; explicit match bonus and mismatch penalty. |
| Clause candidates per control | at most `72` | Project development choice | Capacity before within-control retention. |
| Retained clauses per control | at most `12` | Project development choice | Retriever clause-pool capacity. |
| Answerer retrieval depth | first `12` controls | Project development choice | Clause pool requested for the matched answerer path. |
| Control gate | top 2 below `0.08`; top 3 below `0.04`; maximum `3` controls | Project development choice | Bounded window widening under low rank confidence. |
| Primary-first threshold | `0.06` | Project development choice | Reorders the primary control first when the margin reaches the threshold. |
| Selector window cap | `24` records | Project development choice | Shared bounded evidence window for both matched answer paths. |
| Winner heuristic | first `25` window records; first `25` selected IDs; overlap multiplier `10` | Project development choice | Deterministic winner-control handling. |
| Secondary fallback search | first `50` candidates; first `25` considered | Project development choice | Bounded fallback handling. |
| ODP rescue additions | at most `4` | Project development choice | Bound on deterministic rescue additions. |

## Interpretation boundary

Alternative settings were explored during development, but the surviving
record does not establish held-out tuning or an a-priori choice that was never
revised. The same 136 benchmark rows were available during development.
Accordingly, the reported point estimates are exposed to configuration-selection
optimism. No sensitivity analysis is reported. Results characterize the exact
frozen configurations listed in [`EVALUATION_CONFIGURATIONS.md`](EVALUATION_CONFIGURATIONS.md);
they do not establish robustness under nearby settings.

## E5 compatibility condition

The frozen `intfloat/e5-small-v2` path prefixes indexed text with `passage:`
but encodes transformed queries without the model-recommended `query:` prefix.
Published results characterize that exact behavior. A corrected-prefix run
must receive a new result identity and must not overwrite or be presented as a
bitwise reproduction of the reported metrics.

## Change rule

Any future change to these settings, the BM25 IDF formula, E5 input formatting,
model revisions, or gate logic requires a new configuration identifier and new
evaluation outputs. Historical results remain tied to their recorded code and
input hashes.
