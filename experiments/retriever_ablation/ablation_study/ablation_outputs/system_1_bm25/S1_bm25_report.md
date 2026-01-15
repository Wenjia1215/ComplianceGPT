System 1: BM25 Retriever: Performance Evaluation
This report summarizes the performance of the system 1: bm25 retriever on the NIST SP 800-53 Rev. 5 and Rev. 4 gold sets, and error bank set.

NIST SP 800-53 Rev. 5: Performance
Metric	Overall (100q)	ODP-Subset (63q)
Recall@1	0.7600	0.8095
Recall@5	0.9700	0.9683
Recall@10	0.9900	0.9841
MRR@10	0.8512	0.8907
nDCG@10	0.8857	0.9144

NIST SP 800-53 Rev. 4: Performance
Metric	Overall (36q)	ODP-Subset (19q)
Recall@1	0.6111	0.7368
Recall@5	0.8611	0.8947
Recall@10	0.9167	0.9474
MRR@10	0.7239	0.8246
nDCG@10	0.7715	0.8552

Error Bank — Rev.5 only (n=23)
Metric	Overall (23q)	ODP-Subset (0q)
Recall@1	0.0000	0.0000
Recall@5	0.9130	0.0000
Recall@10	1.0000	0.0000
MRR@10	0.3966	0.0000
nDCG@10	0.5465	0.0000

Error Bank — Rev.4 only (n=11)
Metric	Overall (11q)	ODP-Subset (0q)
Recall@1	0.0000	0.0000
Recall@5	0.8182	0.0000
Recall@10	1.0000	0.0000
MRR@10	0.3690	0.0000
nDCG@10	0.5250	0.0000