# Batch 5D validated result

This directory records the complete evidence package for the finished
`rq2_frontier_baseline_rev5_v1` run. The experiment used the stable Gemini
Developer API model `gemini-3.5-flash` on all 100 frozen Revision 5 contexts.
It was pre-committed before outputs were generated, and the server-reported
model matched the requested model for every response.

The executed notebook at the parent level and the byte-exact runner archive in
this directory form the execution record. The current distributed notebook and
the immutable result archive have these SHA-256 values:

```text
d4cafb9d32ddf1e51516bb1b08eb6d1037cc99e05ed5e0ef9894fbb358a751af  Batch_5D_Rev5_Frontier_API_Baseline.ipynb
9f088b2ccb410fdd6df8980d693529320fec351e9a01e7400cd7d48fc55dddef  rq2_frontier_baseline_rev5_v1.zip
```

The notebook as executed, before repository-only Colab/tool metadata was
removed, remains addressable at public commit
`e00f9cdf77b1ad45a42df0a0bddd338de744266f` with SHA-256
`2e96e47c83f4d02e04b992a81d76cb3c8e670cffbc876d3329437637a1247fcc`.
The historical and current notebooks have the same cell sources, execution
counts, outputs, attachments, and notebook format; their shared semantic-
projection SHA-256 is
`a84858d01a08076445c9597902e95a15151d7ebd14e50d4ae43321ee53f1bee0`.

## Recorded result

| System | Strict pass | Full clause coverage | Runtime contract pass | Right control | Realization loss |
|---|---:|---:|---:|---:|---:|
| ComplianceGPT 4-bit | 65/100 (0.650) | 65/100 (0.650) | 100/100 (1.000) | 97/100 (0.970) | 0/65 (0.000) |
| Gemini 3.5 Flash | 66/100 (0.660) | 67/100 (0.670) | 99/100 (0.990) | 97/100 (0.970) | 1/67 (0.015) |
| Qwen2.5-7B 4-bit | 25/100 (0.250) | 53/100 (0.530) | 42/100 (0.420) | 93/100 (0.930) | 28/53 (0.528) |

The paired ComplianceGPT-versus-Gemini strict-pass discordance was 11 to 12
with an exact two-sided McNemar value of `1.0`. The systems are therefore not
statistically distinguishable on strict pass, and no direction claim is made.
Gemini versus Qwen was 42 to 1 (`p = 1.000444171950221e-11`).

ComplianceGPT's observed 0/65 realization loss confirms its deterministic
construction on this benchmark. Gemini's observed 1/67 is excellent empirical
performance but is not a construction guarantee. The two-sided Fisher exact
comparison is `p = 1.0`; the claim is mechanistic and verifiability-based, not
an observed loss-rate superiority claim.

ODP sensitivity and specificity under the current author labels were 63/63 and
17/37 for ComplianceGPT, 56/63 and 31/37 for Gemini, and 0/63 and 37/37 for
Qwen. These labels have not been independently adjudicated. Sensitivity and
specificity are reported together so the cost of ComplianceGPT's
high-sensitivity operating point remains visible.

See [`AUDIT.md`](AUDIT.md) for the independent post-run checks,
[`SUMMARY.md`](SUMMARY.md) for the runner-generated summary, and
[`ARCHIVE_SHA256SUMS`](ARCHIVE_SHA256SUMS) for the top-level artifact hashes.
