# Audit Record

- Result identity: `rq2_preserve_replay_v1`
- Formal execution time (UTC): `2026-10-03T22:07:52Z`
- Recorded local execution commit: `17a76e14a2285c5070b8d8da3c7341e5772d303d`
- Public tree-identical replay precommit:
  `bb2e382b7428feab4e1804dceb788606d73ac8ce`
- Public frozen-result commit:
  `e00f9cdf77b1ad45a42df0a0bddd338de744266f`
- Frozen defective runtime commit: `be862bcadfa61b474d795303e01ce9394909fdcc`
- Frozen matched archive SHA-256: `56a70db6eca0420df6affbe63c859418ac423b54d80d3d1eae7bf785f0f63328`
- Policy version: `1.1`
- Patch identity: `2026-10-03-preserve-status-v1.1`
- Live retrieval: disabled
- New model inference: disabled
- Selector outputs: exact frozen matched-window v3 values
- Gold use: row selection and post-construction verification only
- Registered acceptance: `PASS`

Every output contract, row-level condition, input identity, code hash, and
archive hash is retained in this directory. No row was excluded after the
formal replay began.

The local and public precommit objects have the same Git tree
(`f62d667917fe84855506752dbfb55649b0956c96`). The public commit was created
through the repository connector, so its author/commit metadata and resulting
commit ID differ while its complete file tree is identical. The frozen result
commit publishes the final result tree
`e58ba15d5ab9e7c98c6e500a696018d10eefb35b`.
