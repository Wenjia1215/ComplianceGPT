# Manuscript Consistency Audit

Audit date: 2026-10-03  
Audit branch: `manuscript-consistency-audit-v1`  
Scientific-artifact baseline: public commit
`487f207edc578930cd66a53ff524e12d8edfbec3`

## Disposition

**PASS — 107 of 107 automated consistency checks passed.**

The audit compares the extracted dissertation LaTeX source with the frozen
ComplianceGPT repository evidence. It checks LaTeX dependencies, figures,
citations, file hashes, repository paths, benchmark and corpus counts, RQ1
retrieval tables, RQ2/RQ3 and follow-on experiment endpoints, claim-boundary
wording, and historical-versus-public artifact identities.

Run it from the repository root against an extracted Overleaf source folder:

```bash
python tools/audit_manuscript_consistency.py /path/to/overleaf-source \
  --json-out manuscript_consistency_audit.json \
  --markdown-out manuscript_consistency_audit.md
```

## Corrections made during the audit

1. **Batch 5D notebook identity.** The dissertation and repository records now
   distinguish the original executed notebook bytes from the metadata-sanitized
   distribution. The two versions retain identical notebook format, cell
   sources, execution counts, outputs, and attachments.

   | Identity | Public commit | SHA-256 |
   |---|---|---|
   | Original executed notebook | `e00f9cdf77b1ad45a42df0a0bddd338de744266f` | `2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc` |
   | Metadata-sanitized distribution | `487f207edc578930cd66a53ff524e12d8edfbec3` | `d4cafb9d32ddf1e51516bb1b08eb6d1037cc99e05ed5e0ef9894fbb358a751af` |
   | Shared metadata-excluding semantic projection | Both | `a84858d01a08076445c9597902e95a15151d7ebd14e50d4ae43321ee53f1bee0` |

2. **PRESERVE replay publication identity.** The frozen run configuration
   retains local execution commit
   `17a76e14a2285c5070b8d8da3c7341e5772d303d`. The public connector-created
   precommit is `bb2e382b7428feab4e1804dceb788606d73ac8ce`; both point to Git tree
   `f62d667917fe84855506752dbfb55649b0956c96`. The final public replay result is
   commit `e00f9cdf77b1ad45a42df0a0bddd338de744266f`, tree
   `e58ba15d5ab9e7c98c6e500a696018d10eefb35b`.

3. **Wilson-interval display rounding.** Six displayed interval endpoints were
   corrected at the third decimal place using the same 95% Wilson calculation
   and frozen counts. No count, effect direction, hypothesis-test result, or
   interpretation changed.

4. **Overleaf source repository pointer.** The upload instructions now point to
   the public scientific-artifact branch and commit instead of implying that
   every post-evaluation artifact is on `main`.

## Passed check groups

| Group | Passed |
|---|---:|
| LaTeX source inventory, includes, and figures | 3/3 |
| Citation inventory | 1/1 |
| Explicit Appendix path/hash pairs | 1/1 (22 file pairs verified) |
| Repository implementation paths | 16/16 |
| Benchmark, CCS, registry, and upstream metadata | 5/5 |
| RQ1 evidence and manuscript rows | 46/46 |
| RQ2/RQ3 and follow-on evidence | 16/16 |
| Publication identities | 9/9 |
| Claim-boundary checks | 4/4 |
| Other manuscript claim anchors | 6/6 |

The retained bibliography has 133 cited keys and 133 defined entries, with no
missing, duplicate, or uncited retained entries. All 22 explicit input-file
hash pairs in the Appendix match the repository files.

## Scope boundary

This is an internal traceability and arithmetic audit. It demonstrates that the
manuscript reports the frozen repository evidence consistently. It does not
independently validate legal sufficiency, benchmark-label correctness,
population generalizability, or external expert agreement.
