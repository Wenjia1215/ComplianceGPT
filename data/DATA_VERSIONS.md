# Data Versions and Upstream Sources

This file pins the upstream NIST source artifacts used to build the released
Canonical Clause Stores (CCS). File identity is defined by the tagged upstream
release, upstream commit, embedded metadata, and local SHA-256 digest.

## OSCAL source release

- Upstream repository: <https://github.com/usnistgov/oscal-content>
- Release tag: `v1.3.0`
- Resolved release commit: `941c978d14c57379fbf6f7fb388f675067d5bff7`
- Release date: 2024-02-13
- Release notes: <https://github.com/usnistgov/oscal-content/releases/tag/v1.3.0>

The local files are byte-identical to the following tagged files:

| Revision | Tagged upstream file | Embedded content version | OSCAL version | Last modified | Local SHA-256 |
|---|---|---|---|---|---|
| Rev. 4 | <https://github.com/usnistgov/oscal-content/blob/v1.3.0/nist.gov/SP800-53/rev4/json/NIST_SP-800-53_rev4_catalog.json> | `2015-01-22` | `1.1.1` | `2023-10-12T00:00:00.000000-04:00` | `9ea66bf110f1c380d6536a2d8a9f722e652100953736102bd664ba74a4d83fcd` |
| Rev. 5 | <https://github.com/usnistgov/oscal-content/blob/v1.3.0/nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json> | `5.1.1+u4` | `1.1.2` | `2024-02-04T23:16:00.000000-00:00` | `81cf2de45ede9aef3de7ce09d65ea9d32f662c483bbf916f6e346292b22f7763` |

The corresponding local paths are:

```text
data/raw/nist800-53/NIST_SP-800-53_rev4_catalog.json
data/raw/nist800-53/NIST_SP-800-53_rev5_catalog.json
```

These OSCAL catalogs contain SP 800-53 control material and embedded SP
800-53A assessment objectives/procedures. The CCS builder retains assessment
objective records for source completeness, but the evaluated retriever admits
only statement (`smt`) and guidance (`gdn`) records as ordinary evidence.

## Publication PDFs retained with the release

| Publication | Official source | Local path | Local SHA-256 |
|---|---|---|---|
| NIST SP 800-53 Rev. 4 | <https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r4.pdf> | `data/raw/nist800-53/source/NIST.SP.800-53r4.pdf` | `e6f8a1aae41168f4ec9edc5b34aee0a21f2c888c78bf1de33e6ec63a0209db4e` |
| NIST SP 800-53 Rev. 5 | <https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-53r5.pdf> | `data/raw/nist800-53/source/NIST.SP.800-53r5.pdf` | `fc63bcd61715d0181dd8e85998b1e6201ae3515fc6626102101cab1841e11ec6` |

The assessment publications that explain the objective material are NIST SP
800-53A Rev. 4 (<https://doi.org/10.6028/NIST.SP.800-53Ar4>) and NIST SP
800-53A Rev. 5 (<https://doi.org/10.6028/NIST.SP.800-53Ar5>).

## Verification

From a checkout of `usnistgov/oscal-content` at `v1.3.0`, run:

```bash
sha256sum \
  nist.gov/SP800-53/rev4/json/NIST_SP-800-53_rev4_catalog.json \
  nist.gov/SP800-53/rev5/json/NIST_SP-800-53_rev5_catalog.json
```

The output must match the two JSON digests above. Then verify all local
evaluation inputs using the command in [`EVALUATION_INPUT_CHECKSUMS.md`](../EVALUATION_INPUT_CHECKSUMS.md).

## Update policy

Do not replace either raw catalog in place and continue using old metrics.
Treat a newer NIST/OSCAL release as a new data version: retain the old files,
record the new release/tag/commit and hashes, rebuild the CCS and registries,
and rerun every affected evaluation under a new result identity.
