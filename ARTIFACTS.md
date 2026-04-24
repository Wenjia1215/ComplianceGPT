# ComplianceGPT_v2 Artifacts

**Generated:** 2026-02-25  
This document records the **data artifacts and key experiment outputs** for the `ComplianceGPT_v2` repository, together with cryptographic checksums.

All paths are relative to the project root (`ComplianceGPT_v2/`). Checksums use **SHA-256**.

## Scope
- **Evaluated scope:** NIST SP 800-53 **Rev4** and **Rev5** only.
- **Not part of the current dissertation scope:** cross-framework ingestion/mapping and any action-plan synthesis.
- Note: Rev4↔Rev5 *delta files* are stored as data artifacts, but there is **no delta-aware knowledge editing module** in the current pipeline.

## Repository Structure (high-level)
```text
ComplianceGPT_v2/
  data/                 # Canonical datasets (CCS, gold sets, Error Bank, ODP registries, QUR outputs)
  experiments/          # Retriever ablations + benchmark outputs
  src/compliancegpt/     # Pipeline + generator + verifier + retrievers
  ARTIFACTS.md
  README.md
```

## A. Frozen Inputs (hash these)
These are the **frozen inputs** that define your corpus and evaluation. If any of these change, prior results are no longer directly comparable.

### CCS (NIST 800-53 clause-level JSONL)

| Path | Size | SHA-256 |
|---|---|---|
| `data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl` | 5099879 | `500bb5d1f265080752710c2f0ae84b8044b67a1e2118cd5e166353b6fc3ab726` |
| `data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl` | 5875092 | `71057ba79c54b8c1f0d171198a6ccb60b4c8818acbd2062e7f7c74ee11242e08` |
| `data/ccs/nist800-53/deltas/rev4_to_rev5.delta.json` | 1830855 | `b1a70f723cbf1d67e9de8830ce797cb84fbaa1b12193c887a2923d0467db7ad9` |
| `data/ccs/nist800-53/deltas/rev4_to_rev5.delta.jsonl` | 1768170 | `190096d1f3e83ac1076b0aa848e885d60d6cee26a2a5b774206c905a0016ed5f` |

### Raw upstream sources (NIST OSCAL + PDFs)

| Path | Size | SHA-256 |
|---|---|---|
| `data/raw/nist800-53/NIST_SP-800-53_rev4_catalog.json` | 5617143 | `9ea66bf110f1c380d6536a2d8a9f722e652100953736102bd664ba74a4d83fcd` |
| `data/raw/nist800-53/NIST_SP-800-53_rev5_catalog.json` | 10381604 | `81cf2de45ede9aef3de7ce09d65ea9d32f662c483bbf916f6e346292b22f7763` |
| `data/raw/nist800-53/source/NIST.SP.800-53r4.pdf` | 5301858 | `e6f8a1aae41168f4ec9edc5b34aee0a21f2c888c78bf1de33e6ec63a0209db4e` |
| `data/raw/nist800-53/source/NIST.SP.800-53r5.pdf` | 6073678 | `fc63bcd61715d0181dd8e85998b1e6201ae3515fc6626102101cab1841e11ec6` |

### Gold standard evaluation sets

| Path | Size | SHA-256 |
|---|---|---|
| `data/gold_standard_datasets/nist800-53/nist_sp800-53_rev4_gold-set_36q.csv` | 35166 | `80a0a8844abdf04d634d779feea970f01f071b62f8c73ada9c19d455863bb9b2` |
| `data/gold_standard_datasets/nist800-53/nist_sp800-53_rev5_gold-set_100q.csv` | 154584 | `f5838fb4fdbdc4ab9543f7860f9e2d9169935bdb308e43d49d21dae267e595b5` |

### Error Bank benchmark

| Path | Size | SHA-256 |
|---|---|---|
| `data/error_bank/error_bank_v1.csv` | 12651 | `61f871db3a1611a62a5895c69d78bf38ae58b71bfed6b10cdaa519db19ee894a` |

### ODP registries + org profile templates

| Path | Size | SHA-256 |
|---|---|---|
| `data/ODP/rev4/odp_registry_rev4.jsonl` | 370576 | `f8e2ee637996fdae506252f3a20748cf5cf03339da5f4c74f663e0cd85e83d93` |
| `data/ODP/rev4/odp_registry_rev4.json` | 385060 | `399509be44e720609efa25c0e39646fa2f27b20a0a20248435b9ae9926dbac7c` |
| `data/ODP/rev4/odp_registry_rev4.csv` | 211769 | `f46b5b2d8e415862259ebf4c5ac47a67753708dfee9efd1a703fbdc042decfa0` |
| `data/ODP/rev4/org_profile_blank_rev4.yaml` | 16030 | `4ed7383f202c244c5bdcbe260feab6ea45a728b3d007cd3ebcc42b44fe03401e` |
| `data/ODP/rev4/org_profile_example_rev4.yaml` | 695 | `ce84c7704e95e4eb7b916015568eaccf3f1375e4b3f8424c64e0164f7039b020` |
| `data/ODP/rev5/odp_registry_rev5.jsonl` | 636595 | `d41457965d1bd9a15fe9694a265030dbfb8267fb0d58d393cd63abb488f2a7c1` |
| `data/ODP/rev5/odp_registry_rev5.json` | 723989 | `3cd31393ed97df6292a45b749bca5359c802397d68ee6dcb41081b075fd32545` |
| `data/ODP/rev5/odp_registry_rev5.csv` | 711229 | `dae68c4c96b98f415fc294d5f33aea52c54c60e65d4191a367cc0a7b6271cf0e` |
| `data/ODP/rev5/org_profile_blank_rev5.yaml` | 31534 | `7fcc7ccb2bd16b4cb13249cd78273d7121f93c4abaff0f10f80e70379791c1fd` |
| `data/ODP/rev5/org_profile_example_rev5.yaml` | 219 | `a40b2102699333f66e126e74039c09fc382e172360117c8479b38d2e7760ae17` |

### Frozen QUR rewrite outputs used in ablations

| Path | Size | SHA-256 |
|---|---|---|
| `data/qur_outputs/qur_rewrites_rev4.csv` | 42667 | `13c7657154dbc5ee307ed8c674c7e6e30558faa3fa3990ec851a8bcb0ce105e7` |
| `data/qur_outputs/qur_rewrites_rev5.csv` | 134106 | `ae20478163cbae94e5ccba5b27d401a707fe0c5bb4dd46e31061aa11191ddd82` |
| `data/qur_outputs/qur_rewrites_error_bank.csv` | 47019 | `866eb98c761358bf916cd5477571c9cc8cf30df53ba3360d026c06f4a45a8de4` |

### Dataset manifests and labeling notes

| Path | Size | SHA-256 |
|---|---|---|
| `data/DATA_VERSIONS.md` | 1010 | `21a3b855d8e255f52ac7f9953486c9264bb30ad82c302d81bc3bab43a4862c3f` |
| `data/ccs/nist800-53/README_ccs.md` | 6803 | `2780054ac7842d2eafd25cb8597d97f20c6efdef7775a8a3ac47dfdf78354d71` |
| `data/gold_standard_datasets/nist800-53/README.md` | 4719 | `de33cfd66f994de64aaa52cab5a1d8fc80968f3b71dedcf3df334ac3839e203f` |
| `data/error_bank/README.md` | 2411 | `e72753adeea42007f078ccbbafb88abd8b51c4cc8541d40a8aee82f90784bfaf` |
| `data/error_bank/Labeling_Rationale.md` | 73314 | `2728c63b470886f9aa864cf08a5e304127e4ea1beb8f1c8c4fac483b65c4677b` |
| `data/ODP/README_ODP_template.md` | 5667 | `e796b68b71fb6da96bd699bd8ed321ed756f4f294d7f05de510416794e8c33ed` |

## B. Key Derived Outputs (regenerable, but hashed for release bookkeeping)
These files are produced by running the evaluation / ablation workflows in this repository. They should be reproducible from the frozen inputs + code, but are included here as **release artifacts**.

| Path | Size | SHA-256 |
|---|---|---|
| `experiments/retriever_ablation/README.md` | 2768 | `a07a121a6f54a422f69a9bbd1512e1b5c3d7815d527f66f89277781aad11c976` |
| `experiments/retriever_ablation/RESULTS.md` | 6308 | `19013b8808236bfd046a778dfe976aaabb8446726d96b1381e242cacc19c3d79` |
| `experiments/retriever_ablation/SYSTEMS.md` | 6882 | `5284cff7f03bd6d344fcbc127854818955361c6f7175585f889762af48636a84` |
| `experiments/retriever_ablation/WORKFLOW.md` | 3239 | `3be4dcc3d6eaa3e3c834aff44080b63d42ce9935b072563b475d424f685dad69` |
| `experiments/retriever_ablation/ablation_outputs/system_1_bm25/S1_bm25_error_bank_rev4_results.csv` | 3800 | `b62d10ca68b19f7fd5cb301099cb32df5fd4ba9a96815b08ed2649adddc31a02` |
| `experiments/retriever_ablation/ablation_outputs/system_1_bm25/S1_bm25_error_bank_rev5_results.csv` | 7353 | `e4891a1c82f3e4e582a6e84cf866cb2b8c43dfefaf9a739f8c6277ef460eb881` |
| `experiments/retriever_ablation/ablation_outputs/system_1_bm25/S1_bm25_report.md` | 1087 | `a1d88da5a801bcb80f75e8fb1732f7867733f5481812414eab16321f05c217c0` |
| `experiments/retriever_ablation/ablation_outputs/system_1_bm25/S1_bm25_rev4_results.csv` | 9978 | `f6aba5465c2471075cfb244a9c14534c0fb859016c59686dec1b8dca6be08936` |
| `experiments/retriever_ablation/ablation_outputs/system_1_bm25/S1_bm25_rev5_results.csv` | 30731 | `bcb8bba1357e74a23b788ca20a507c52f11af3a6543521b3309668787d3b0bdf` |
| `experiments/retriever_ablation/ablation_outputs/system_2_dense/S2_dense_error_bank_rev4_results.csv` | 3707 | `a6f9bf6af437a5cc8896d2b60be5f8a51e8d19fad7a6c0b6129a52f362d85d3f` |
| `experiments/retriever_ablation/ablation_outputs/system_2_dense/S2_dense_error_bank_rev5_results.csv` | 7331 | `92a8bd76958791ec12a09ae05425c5c6391e29a02ab43d2a6df9260665bfd71b` |
| `experiments/retriever_ablation/ablation_outputs/system_2_dense/S2_dense_report.md` | 1091 | `71b3274eba85b17ed0047670bd55ef44f933282c4f9d7584291e1ee3dab9f82d` |
| `experiments/retriever_ablation/ablation_outputs/system_2_dense/S2_dense_rev4_results.csv` | 9879 | `0047fa231dddbd2f8d266e0a7e015435c3bb88099d1a04fb0494862b6a182cf2` |
| `experiments/retriever_ablation/ablation_outputs/system_2_dense/S2_dense_rev5_results.csv` | 30745 | `4c38c3b4031b8d01fa7a1acba8a134a0fbb1296e9f594eaa9c240225a8996e7f` |
| `experiments/retriever_ablation/ablation_outputs/system_3_rewrite_only/S3_rewrite_only_error_bank_rev4_results.csv` | 3760 | `db885f8a264bae9f5f644f65974ad5a30143f24818857e4e19ada676a6739edf` |
| `experiments/retriever_ablation/ablation_outputs/system_3_rewrite_only/S3_rewrite_only_error_bank_rev5_results.csv` | 7340 | `12c0c09d8d3b8a934c84bfd91b6d85b3c32962036de0127f9d8e73a31f6045d4` |
| `experiments/retriever_ablation/ablation_outputs/system_3_rewrite_only/S3_rewrite_only_report.md` | 1119 | `d1a1668faec956aba05ebfc3dbe618c15a07fc0a3fa2c2c3d98f10cb6964a543` |
| `experiments/retriever_ablation/ablation_outputs/system_3_rewrite_only/S3_rewrite_only_rev4_results.csv` | 9961 | `7e3a6de08923cfd16131e1e3359bbf95d2d4d65c7cff973e4338c301a36b5010` |
| `experiments/retriever_ablation/ablation_outputs/system_3_rewrite_only/S3_rewrite_only_rev5_results.csv` | 30783 | `c39eb8058f80b4f38372f35a62f04a7f781e5f2195c0259eee15756ae9346327` |
| `experiments/retriever_ablation/ablation_outputs/system_4_qur_rrf/S4_qur_rrf_error_bank_rev4_results.csv` | 3983 | `deb851233e08f3223955020c35ca067a9c60767d763ea803e5ed224b41d0d920` |
| `experiments/retriever_ablation/ablation_outputs/system_4_qur_rrf/S4_qur_rrf_error_bank_rev5_results.csv` | 7690 | `5ae00ab0fcb2ec87915794ddf4488025f09289b4c83dd5828ced3e3fbe03c6f6` |
| `experiments/retriever_ablation/ablation_outputs/system_4_qur_rrf/S4_qur_rrf_report.md` | 1099 | `437d034b2eec27b1260742bfee41dd851a8fabb74488fcce848364629bfbe47a` |
| `experiments/retriever_ablation/ablation_outputs/system_4_qur_rrf/S4_qur_rrf_rev4_results.csv` | 10506 | `8a56324048b14811ec921e0dfc8bded20fda852dd3519bc5322fdece5da71f49` |
| `experiments/retriever_ablation/ablation_outputs/system_4_qur_rrf/S4_qur_rrf_rev5_results.csv` | 32216 | `9ccabad5f16c9cacd2c0cbd44fe85540020d048c1e632665f1bbb7bc0d57aed8` |
| `experiments/retriever_ablation/ablation_outputs/system_5_hybrid_rrf/S5_hybrid_rrf_error_bank_rev4_results.csv` | 3709 | `8f99894556496184d2126b78c965155a850be986b0d838e5588b23b4b164de30` |
| `experiments/retriever_ablation/ablation_outputs/system_5_hybrid_rrf/S5_hybrid_rrf_error_bank_rev5_results.csv` | 7271 | `207086bdd68022d4ad3d5772a08cee44bd9d7a76431c921fb686c20a2ce73edc` |
| `experiments/retriever_ablation/ablation_outputs/system_5_hybrid_rrf/S5_hybrid_rrf_report.md` | 1111 | `415a5fcaf33e6a3041d4b21f4df6addf3fac6a7e3956839e44d9b668c22f115f` |
| `experiments/retriever_ablation/ablation_outputs/system_5_hybrid_rrf/S5_hybrid_rrf_rev4_results.csv` | 9861 | `ceaff621241fb4fbf8fe7c27c4a2def1b065781a406a53f70f554a29842a658d` |
| `experiments/retriever_ablation/ablation_outputs/system_5_hybrid_rrf/S5_hybrid_rrf_rev5_results.csv` | 30600 | `2ce1b6ab6f2df76e6cadfcf72fbe66ea337c642bc3eab57bd6a3e92bdaded33f` |
| `experiments/retriever_ablation/ablation_outputs/system_6_hybrid_rerank/S6_hybrid_rerank_error_bank_rev4_results.csv` | 3748 | `5ed0a1c9b310b0d785a574828fa808b61ea2078c6767b26db08522afdcda5c81` |
| `experiments/retriever_ablation/ablation_outputs/system_6_hybrid_rerank/S6_hybrid_rerank_error_bank_rev5_results.csv` | 7286 | `7f6a676571405b631b0810a38f80179e7f633072e27788d56bdfe802aa9a7528` |
| `experiments/retriever_ablation/ablation_outputs/system_6_hybrid_rerank/S6_hybrid_rerank_report.md` | 1123 | `f5aae42a3be45c04eff7e3f92f2cc71846d7fbb27b3630d28ecd77930710a4e4` |
| `experiments/retriever_ablation/ablation_outputs/system_6_hybrid_rerank/S6_hybrid_rerank_rev4_results.csv` | 10005 | `5592b9a02eeb11632b96f82e4ecf48626e21f3180b2d0272a9840444667cfcb7` |
| `experiments/retriever_ablation/ablation_outputs/system_6_hybrid_rerank/S6_hybrid_rerank_rev5_results.csv` | 30744 | `a7cebc41e043672505b0b08c86e9cc033c2bb534ad02ef4f9aa7f8d1ee0df33a` |
| `experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_error_bank_rev4_results.csv` | 10454 | `3e90dadf3b625c119c40f92c8b21b9c4110dbf7a1c060276ff0b8e16b9549b04` |
| `experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_error_bank_rev5_results.csv` | 19792 | `da78cc7b7653969497f6673cda925d2e115b856926d788c91aa8ffba4a975324` |
| `experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_report.md` | 1754 | `496470296409b107f01bd4d8a5e6b1f72cc94902f06a0b0e9b0afe9a9baea2d3` |
| `experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_rev4_results.csv` | 28471 | `3ad554cc5d63925341453368d74481728e0f04ff7ef7adc5f9e706b77f2ec999` |
| `experiments/retriever_ablation/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_rev5_results.csv` | 82478 | `bc0f8e51a3afcb90739ba746e0ead8b34aca5616b3a52d4cb6049dc23318219a` |
| `experiments/retriever_ablation/performance_benchmark/output/retriever_performance_benchmark_meta_rev5_20q.json` | 1333 | `09556813ec970c285043d23c14cbd620f61e0ebb2c9e5d261c9304755d8bc6cd` |
| `experiments/retriever_ablation/performance_benchmark/output/retriever_performance_benchmark_rev5_20q.csv` | 700 | `876ae9f045e850a9a607d06738a8421648d1d4400089fdb1460d1221140f767e` |
| `experiments/retriever_ablation/performance_benchmark/output/retriever_performance_benchmark_runs_rev5_20q.csv` | 44716 | `e451fc7b1b3c08eec18bed400758b0f30dc371a59016596e207846a5908d1ef1` |
| `experiments/retriever_ablation/performance_benchmark/output/retriever_performance_benchmark_table_rev5_20q.md` | 760 | `7d8e0904fde608d652764cad4f7b00d7c88e1b25a070f2ef7e6cbf0adbfbd44e` |
| `src/compliancegpt/generator/citation_contract_80053.md` | 5405 | `7859aef90da277b63385265b552594f76a03d91848cb9967bd79d5bf3bc24d54` |
| `src/compliancegpt/generator/logic.md` | 1281 | `e89b61f8583058632dc9e21ccf762522d9c1763825706fe9fa94b0571a0f03d4` |
| `src/compliancegpt/generator/tech_note.md` | 1105 | `786f29c651974fd785451e044785f03a542ed4da49a117e525f5ab55e3a5c5e6` |
| `src/compliancegpt/pipeline/README.md` | 2436 | `c8cfa0782fb95a74012545bf95d88dc35a4a4051caff3ae70d2f44e7910fe429` |
| `src/compliancegpt/pipeline/pipeline_score/eval_rev4.csv` | 138779 | `742e83fa9623eae6c4387f2091b1b3f7cab726b669336f6ec4630fd2fe0be683` |
| `src/compliancegpt/pipeline/pipeline_score/eval_rev5.csv` | 392359 | `d4c2bd07c11eb311e4c94b69b9dd2d30ccea59ed36781aed1d4caf0adea2d55d` |

## C. Deprecated / Not used in current evaluation
- Deprecated CCS assets (not used by current pipeline): `data/ccs/nist800-53/deprecated_ccs/`
- Deprecated gold sets (not used): `data/gold_standard_datasets/nist800-53/DeprecatedGoldSets/`

## D. How to verify a hash (one-liner)
Compute SHA-256 on your machine and compare to the values above (e.g., `shasum -a 256 <file>` on macOS, or `sha256sum <file>` on Linux).
