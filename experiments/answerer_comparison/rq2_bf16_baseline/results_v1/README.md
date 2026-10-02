# Batch 5B validated result

This directory records the complete supplied evidence package for the
completed `rq2_bf16_baseline_v1` run. The run used
an NVIDIA A100-SXM4-40GB and loaded every floating model parameter as
`torch.bfloat16`; the runtime manifest reports no 4-bit or 8-bit quantizer.
All 36 registered Revision 4 contexts completed.

The materialized files are the exact payload recovered from the supplied
Google Drive folder export. `manifests/outputs.json` covers 15 payload files;
every stored SHA-256 was independently rechecked, and its canonical file-map
hash is:

```text
e265388b72d758b0d05e2bf55899f9b45622b51f497bdf17d8465d3ded97ce3b
```

The exact supplied Drive export is retained as
`rq2_bf16_baseline_v1_drive_export.zip`, with SHA-256:

```text
4039e67453d46b12ad214a3759d16e5a4c9f1028353dd6e253fca06f3b57a561
```

This is a folder-export envelope whose entries begin with
`rq2_bf16_baseline_v1/`. It is byte-distinct from the sibling archive created
inside Colab. The executed notebook records that runner-created archive as
`/content/drive/MyDrive/rq2_bf16_baseline_v1.zip` with SHA-256
`8717b3ce3c691bc47d61ee62ec88fe3038ca170636e0f868e7720ff7a754eed2`;
that exact sibling ZIP was not the uploaded file. The payload identity is
established by the verified per-file output manifest.

See [`AUDIT.md`](AUDIT.md) for the independent recomputation and
[`SUMMARY.md`](SUMMARY.md) for the runner-generated summary.

## Recorded result

| System | Strict pass | Full clause coverage | Runtime contract pass | ODP sensitivity* |
|---|---:|---:|---:|---:|
| Generative baseline, BF16 | 8/36 | 20/36 | 14/36 | 0/19 |
| Generative baseline, frozen 4-bit | 8/36 | 18/36 | 13/36 | 0/19 |
| ComplianceGPT, frozen 4-bit | 29/36 | 29/36 | 36/36 | 19/19 |

BF16 and 4-bit baseline strict pass were identical in aggregate. Their four
discordant rows split evenly (two BF16-only and two 4-bit-only), giving an
exact two-sided McNemar value of `1.0`. Against frozen 4-bit ComplianceGPT,
BF16 had zero left-only passes and 21 right-only passes (`p = 9.5367432e-07`).
The result therefore does not support 4-bit quantization as the explanation
for the main RQ2 gap.

*ODP values use current author labels and have not been independently
adjudicated. The immutable runner-generated summary retains its original
pre-scope wording.*
