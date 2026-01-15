# Validation Study for S4 and S7 Retrieval Architectures: Comparison Report
Report generated: 2025-11-14 16:29:23.667557


## Ablation (a): S7 (Standard) vs. S7a (Rerank Best)
**Hypothesis:** Reranking with the Original Query is SUPERIOR.


| Dataset             |   S7 (Standard) MRR@10 |   S7a (Rerank Best) MRR@10 |
|:--------------------|-----------------------:|---------------------------:|
| Rev. 5 Overall      |                 0.9448 |                   0.817706 |
| Rev. 4 Overall      |                 0.9444 |                   0.844907 |
| Error Bank (Rev. 5) |                 0.8323 |                   0.69824  |
| Error Bank (Rev. 4) |                 0.8182 |                   0.787879 |


## Ablation (b): S4 (Standard) vs. S4b (RRF Best)
**Hypothesis:** Fusing ALL rewrites is SUPERIOR.


| Dataset             |   S4 (Standard) MRR@10 |   S4b (RRF Best) MRR@10 |
|:--------------------|-----------------------:|------------------------:|
| Rev. 5 Overall      |                 0.7802 |                0.767429 |
| Rev. 4 Overall      |                 0.8114 |                0.778241 |
| Error Bank (Rev. 5) |                 0.4493 |                0.396791 |
| Error Bank (Rev. 4) |                 0.5586 |                0.583333 |