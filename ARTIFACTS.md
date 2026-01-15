# ComplianceGPT_v1 Artifacts

This document records the key datasets and selected experiment outputs for the `ComplianceGPT_v1` repository, together with their locations and cryptographic checksums.

All paths are relative to the project root:

`ComplianceGPT_v1/`

Checksums are provided using the SHA-256 hash function unless otherwise noted.

---

## 1. Repository Structure (high-level)

The repository is organized into three main areas:

```text
ComplianceGPT_v1/
  answerer_v0/          # Answering and retrieval notebooks, ablations, reports
  data/                 # All canonical datasets used by ComplianceGPT_v1
  src/                  # Utility scripts
  README.md
```

The `data/` subtree holds the canonical data assets:

```text
data/
  ccs/                  # Canonical Clause Store (CCS) corpora and deltas
    nist800-53/
    hipaa/
    pci_dss/
  gold_standard_datasets/
    nist800_53/
    hipaa/
    pci_dss/
  error_bank/           # Error Bank benchmark
  qur_outputs/          # QUR rewrites used by retrieval experiments
  crosswalk/            # Cross-framework control crosswalks
  raw/                  # Raw external source documents (PDFs, etc.)
  DATA_VERSIONS.md      # Semantic versioning notes for datasets
```

The `answerer_v0/` subtree holds experiment-specific code and outputs (for example, S1–S7 ablation results and micro-ablations), which can be linked to the canonical datasets in `data/`.

---

## 2. Hashing Method

All checksums recorded in this document use the SHA-256 cryptographic hash function applied to the full file contents (byte level).

Checksums may be recomputed with standard tools such as:

- `sha256sum <file>` (Linux/macOS)
- `Get-FileHash <file> -Algorithm SHA256` (Windows PowerShell)
- Equivalent SHA-256 implementations in scripting languages (for example, Python’s `hashlib.sha256`).

Any change to a file’s content, including a single character or line ending, results in a different SHA-256 value.

---

## 3. Canonical NIST SP 800-53 Corpora (CCS)

These files constitute the canonical corpora used for NIST SP 800-53 Rev.4 and Rev.5 within ComplianceGPT_v1. The JSON files correspond to structured CCS catalogs; the JSONL files are line-oriented representations used directly by retrieval pipelines.

### 3.1 NIST SP 800-53 Rev.4

| Logical Name                         | Path (relative to project root)                              | Role                                          | SHA-256 |
|--------------------------------------|--------------------------------------------------------------|-----------------------------------------------|---------|
| NIST 800-53 Rev.4 CCS (JSON)        | `data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.json`      | CCS catalog for NIST SP 800-53 Rev.4         | `9ea66bf110f1c380d6536a2d8a9f722e652100953736102bd664ba74a4d83fcd` |
| NIST 800-53 Rev.4 CCS (JSONL)       | `data/ccs/nist800-53/NIST_SP-800-53_rev4_catalog.jsonl`     | Line-oriented corpus used by retrieval       | `07f3b5cf924128090f8172e39f4a6432a2367f410767c83493a0cf2c623c6cdd` |

### 3.2 NIST SP 800-53 Rev.5

| Logical Name                         | Path (relative to project root)                              | Role                                          | SHA-256 |
|--------------------------------------|--------------------------------------------------------------|-----------------------------------------------|---------|
| NIST 800-53 Rev.5 CCS (JSON)        | `data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.json`      | CCS catalog for NIST SP 800-53 Rev.5         | `81cf2de45ede9aef3de7ce09d65ea9d32f662c483bbf916f6e346292b22f7763` |
| NIST 800-53 Rev.5 CCS (JSONL)       | `data/ccs/nist800-53/NIST_SP-800-53_rev5_catalog.jsonl`     | Line-oriented corpus used by retrieval       | `e9bb58464d009a643c6fae39f53c9d6d7e3bc23cf94d11ea0517f17b0b8ca7e5` |

---

## 4. Gold Standard Datasets

Gold standard datasets provide evaluation queries and ground-truth control references for retrieval experiments.

### 4.1 NIST SP 800-53 Gold Sets

| Logical Name                         | Path (relative to project root)                                                | Role                                       | SHA-256 |
|--------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------|---------|
| Rev.4 Gold Set (36 questions)       | `data/gold_standard_datasets/nist800_53/nist_sp800-53_rev4_gold-set_36q.csv` | Evaluation gold set for NIST Rev.4        | `7b0bdfaa53ec077c13b7b0307c795a25d22579423a335223f05c3136589dc4cc` |
| Rev.5 Gold Set (100 questions)      | `data/gold_standard_datasets/nist800_53/nist_sp800-53_rev5_gold-set_100q.csv`| Evaluation gold set for NIST Rev.5        | `8c84dddcd376603f275b197ba4b839b30e9eb96c6e3750daaa94ff29079a42a9` |

Additional gold sets for HIPAA and PCI-DSS may be recorded in future extensions of this document once their schemas and versions are finalized.

---

## 5. Error Bank Benchmark

The Error Bank is a curated set of difficult queries used to stress-test retrieval systems and diagnose specific failure modes.

| Logical Name      | Path (relative to project root)                 | Role                                     | SHA-256 |
|-------------------|-------------------------------------------------|------------------------------------------|---------|
| Error Bank v1     | `data/error_bank/error_bank_v1.csv`            | Error Bank benchmark (v1)               | `1d3ab06bcdb1a296eddb2465e7d07327df41b8c3dfa9658901177e8453591abd` |

Documentation related to labeling rationale and failure mode analysis resides under:

`answerer_v0/retriever/ablation_study/erro_bank/`

and may be updated independently of this checksum table.

---

## 6. QUR Outputs (Query Rewrite Corpora)

QUR (Query Understanding & Rewrite) outputs are pre-generated, AI-normalized query sets used as inputs to retrieval experiments. The canonical copies of these corpora reside under `data/qur_outputs/`.

| Logical Name                      | Path (relative to project root)                | Role                                             | SHA-256 |
|-----------------------------------|------------------------------------------------|--------------------------------------------------|---------|
| QUR rewrites – Rev.4             | `data/qur_outputs/qur_rewrites_rev4.csv`      | Query rewrites for Rev.4 gold set                | `b59fdf27dd1e28d0f478c40bcd2401f27eb9980b508befd3683992fba6114655` |
| QUR rewrites – Rev.5             | `data/qur_outputs/qur_rewrites_rev5.csv`      | Query rewrites for Rev.5 gold set                | `a673aeccc8c8f4cce3d75f0ddb0122608cb77fb136ce856e9565fa4c0da8d2a9` |
| QUR rewrites – Error Bank        | `data/qur_outputs/qur_rewrites_error_bank.csv`| Query rewrites for Error Bank queries            | `4a458773ba439b8ac8c59ff76462799cb2fe02910ca1172b8fff4e95464c8e6e` |

The QUR generator notebooks and unit tests are located under:

`answerer_v0/retriever/QUR_generator/`

These notebooks should treat `data/qur_outputs/` as the canonical location for persisted QUR corpora.

---

## 7. Crosswalk Datasets

Crosswalk datasets define mappings between controls from different frameworks (NIST, HIPAA, PCI-DSS). These mappings are used by ComplianceGPT_v1 to support multi-framework reasoning and alignment.

| Logical Name                        | Path (relative to project root)                          | Role                                       | SHA-256 |
|-------------------------------------|----------------------------------------------------------|--------------------------------------------|---------|
| NIST–HIPAA–PCI crosswalk v3        | `data/crosswalk/crosswalk_v3_with_ids_only.csv`         | Control-level crosswalk (v3, IDs only)     | _TBD_   |

The SHA-256 value for this file should be recorded once the crosswalk version is finalized.

---

## 8. Raw Source Documents (Lineage)

Raw external documents form the ultimate source of truth for the CCS corpora. Hashing these files is optional but provides full lineage from original publications to processed corpora.

### 8.1 NIST SP 800-53 PDFs

| Logical Name                         | Path (relative to project root)                                      | Role                                  | SHA-256 |
|--------------------------------------|----------------------------------------------------------------------|---------------------------------------|---------|
| NIST SP 800-53 Rev.4 (PDF)          | `data/raw/nist800-53/source/NIST.SP.800-53r4.pdf`                   | Original NIST SP 800-53 Rev.4 source  | _TBD_   |
| NIST SP 800-53 Rev.5 (PDF)          | `data/raw/nist800-53/source/NIST.SP.800-53r5.pdf`                   | Original NIST SP 800-53 Rev.5 source  | _TBD_   |

### 8.2 HIPAA Security Rule PDFs

| Logical Name                         | Path (relative to project root)                                      | Role                                  | SHA-256 |
|--------------------------------------|----------------------------------------------------------------------|---------------------------------------|---------|
| HIPAA Security Rule 2023 – Part 160 | `data/raw/hipaa/source/HIPAA_SecurityRule_Complete/CFR-2023-title45-vol2-part160.pdf` | HIPAA Part 160 (2023) source | _TBD_   |
| HIPAA Security Rule 2023 – Part 164 | `data/raw/hipaa/source/HIPAA_SecurityRule_Complete/CFR-2023-title45-vol2-part164.pdf` | HIPAA Part 164 (2023) source | _TBD_   |
| HIPAA Security Rule 2024 – Part 160 | `data/raw/hipaa/source/HIPAA_SecurityRule_Complete/CFR-2024-title45-vol2-part160.pdf` | HIPAA Part 160 (2024) source | _TBD_   |
| HIPAA Security Rule 2024 – Part 164 | `data/raw/hipaa/source/HIPAA_SecurityRule_Complete/CFR-2024-title45-vol2-part164.pdf` | HIPAA Part 164 (2024) source | _TBD_   |

### 8.3 PCI-DSS PDFs

| Logical Name                         | Path (relative to project root)                                      | Role                                  | SHA-256 |
|--------------------------------------|----------------------------------------------------------------------|---------------------------------------|---------|
| PCI-DSS v4.0 (PDF)                  | `data/raw/pci_dss/source/PCI_DSS_v4_0.pdf`                          | PCI-DSS v4.0 source                   | _TBD_   |
| PCI-DSS v4.0.1 (PDF)                | `data/raw/pci_dss/source/PCI_DSS_v4_0_1.pdf`                        | PCI-DSS v4.0.1 source                 | _TBD_   |
| PCI-DSS v4.0 → v4.0.1 Changes PDF   | `data/raw/pci_dss/source/V400-V401_Changes-r1.pdf`                  | Official PCI-DSS change summary       | _TBD_   |

---

## 9. Experiment Outputs (Placeholders)

Experiment outputs (for example, the S1–S7 ablation results and micro-ablations) are stored under:

```text
answerer_v0/retriever/ablation_study/ablation_outputs/
```

Once specific experiment runs are frozen, selected outputs may be recorded here with their SHA-256 checksums. An illustrative template is provided below.

### 9.1 S1–S7 Ablation Results (example template)

| System / Run               | Path (relative to project root)                                                                                     | Description                                      | SHA-256 |
|----------------------------|----------------------------------------------------------------------------------------------------------------------|--------------------------------------------------|---------|
| S1 BM25 – Rev.5            | `answerer_v0/retriever/ablation_study/ablation_outputs/system_1_bm25/S1_bm25_rev5_results.csv`                      | Final S1 results for NIST Rev.5                  | _TBD_   |
| S1 BM25 – Rev.4            | `answerer_v0/retriever/ablation_study/ablation_outputs/system_1_bm25/S1_bm25_rev4_results.csv`                      | Final S1 results for NIST Rev.4                  | _TBD_   |
| S7 ComplianceGPT – Rev.5   | `answerer_v0/retriever/ablation_study/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_rev5_results.csv`  | Final S7 results for NIST Rev.5                  | _TBD_   |
| S7 ComplianceGPT – Rev.4   | `answerer_v0/retriever/ablation_study/ablation_outputs/system_7_compliance_gpt/S7_compliance_gpt_rev4_results.csv`  | Final S7 results for NIST Rev.4                  | _TBD_   |

Additional tables may be added here for:

- Error Bank–specific results,
- Micro-ablations,
- Performance benchmarks,
- Summary markdown reports.

---

## 10. Maintenance Notes

- Any modification to a file’s content invalidates the corresponding SHA-256 entry in this document and requires recomputation.
- New datasets or versions should be accompanied by:
  - An entry in `data/DATA_VERSIONS.md` describing semantic changes, and  
  - An updated row in the relevant table in this document with the correct SHA-256 checksum.
- Deprecated or superseded artifacts may be retained in this document for historical traceability, with clear annotations indicating replacement versions where applicable.
