# Retriever Performance Benchmark Report
Report generated: 2025-11-14 18:04:02.729851


## 1. End-to-End Query Latency (Performance)
Average latency per query over 10 trials on a single GPU.


| System               |   Avg. Latency (ms) |
|:---------------------|--------------------:|
| S1 (BM25)            |               12.38 |
| S2 (Dense)           |                9.81 |
| S5 (Hybrid RRF)      |               23.55 |
| S6 (Hybrid + Rerank) |              306.42 |
| S7 (ComplianceGPT)   |              367.55 |


## 2. Model VRAM Footprint (Resource Cost)
VRAM measured by loading models onto an idle GPU.


| Component             | Model                                |   VRAM (MB) |
|:----------------------|:-------------------------------------|------------:|
| Bi-Encoder (S2)       | intfloat/e5-small-v2                 |      127.27 |
| Cross-Encoder (S6/S7) | cross-encoder/ms-marco-MiniLM-L-6-v2 |       86.65 |


### Estimated Total System VRAM
* **S2 (Dense) Total:** 127.27 MB
* **S6/S7 (Hybrid) Total:** 213.92 MB


## 3. QUR Model Size (Static Cost)
Size of the model used for Query-Rewrite (QUR) generation.


* **QUR Model:** Qwen2.5-7B