# ComplianceGPT Artifact Manifest

**Hash Algorithm:** SHA-256
**Purpose:** This manifest records all frozen input artifacts (source data, clause stores, configuration profiles, and evaluation sets) required to reproduce the ComplianceGPT experimental results.

---

## Verification Command
To verify a file from the project root, run:
`shasum -a 256 <file_path>`

---

## Frozen Input Hashes

### 1. Official NIST Source Inputs
| Path | SHA-256 |
|---|---|
| `data/raw/nist800-53/NIST_SP-800-53_rev4_catalog.json` | `9ea66bf110f1c380d6536a2d8a9f722e652100953736102bd664ba74a4d83fcd` |
| `data/raw/nist800-53/NIST_SP-800-53_rev5_catalog.json` | `81cf2de45ede9aef3de7ce09d65ea9d32f662c483bbf916f6e346292b22f7763` |
| `data/raw/nist800-53/source/NIST.SP.800-53r4.pdf` | `e6f8a1aae41168f4ec9edc5b34aee0a21f2c888c78bf1de33e6ec63a0209db4e` |
| `data/raw/nist800-53/source/NIST.SP.800-53r5.pdf` | `fc63bcd61715d0181dd8e85998b1e6201ae3515fc6626102101cab1841e11ec6` |

### 2. Canonical Clause Store and Revision Deltas
| Path | SHA-256 |
|---|---|
| `data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl` | `500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726` |
| `data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl` | `71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08` |
| `data/ccs/nist800-53/deltas/rev4_to_rev5.delta.json` | `b1a70f723cbf1d67e9de8830ce797cb84fbaa1b12193c887a2923d0467db7ad9` |
| `data/ccs/nist800-53/deltas/rev4_to_rev5.delta.jsonl` | `190096d1f3e83ac1076b0aa848e885d60d6cee26a2a5b774206c905a0016ed5f` |

### 3. Gold Evaluation Sets & ErrorBank
| Path | SHA-256 |
|---|---|
| `data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv` | `80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2` |
| `data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv` | `f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5` |
| `data/error_bank/error_bank_v1.csv` | `61f871db3a1611a62a5895c69d78bf38ae58b71bfed6b10cdaa519db19ee894a` |

### 4. ODP Registries and Organization Profiles
| Path | SHA-256 |
|---|---|
| `data/ODP/rev4/odp_registry_rev4.csv` | `f46b5b2d8e415862259ebf4c5ac47a67753708dfee9efd1a703fbdc042decfa0` |
| `data/ODP/rev4/odp_registry_rev4.json` | `399509be44e720609efa25c0e39646fa2f27b20a0a20248435b9ae9926dbac7c` |
| `data/ODP/rev4/org_profile_blank_rev4.yaml` | `4ed7383f202c244c5bdcbe260feab6ea45a728b3d007cd3ebcc42b44fe03401e` |
| `data/ODP/rev4/org_profile_example_rev4.yaml` | `ce84c7704e95e4eb7b916015568eaccf3f1375e4b3f8424c64e0164f7039b020` |
| `data/ODP/rev5/odp_registry_rev5.csv` | `dae68c4c96b98f415fc294d5f33aea52c54c60e65d4191a367cc0a7b6271cf0e` |
| `data/ODP/rev5/odp_registry_rev5.json` | `3cd31393ed97df6292a45b749bca5359c802397d68ee6dcb41081b075fd32545` |
| `data/ODP/rev5/org_profile_blank_rev5.yaml` | `7fcc7ccb2bd16b4cb13249cd78273d7121f93c4abaff0f10f80e70379791c1fd` |
| `data/ODP/rev5/org_profile_example_rev5.yaml` | `a40b2102699333f66e126e74039c09fc382e172360117c8479b38d2e7760ae17` |