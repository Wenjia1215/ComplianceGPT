S2 Dense Retriever: Performance Evaluation
This report summarizes the performance of the s2 dense retriever on the NIST SP 800-53 Rev. 5 and Rev. 4 gold sets, and error bank set.

NIST SP 800-53 Rev. 5: Performance
Metric	Overall (100q)	ODP-Subset (63q)
Recall@1	0.7500	0.7937
Recall@5	0.9600	0.9841
Recall@10	0.9900	1.0000
MRR@10	0.8524	0.8806
nDCG@10	0.8870	0.9107

NIST SP 800-53 Rev. 4: Performance
Metric	Overall (36q)	ODP-Subset (19q)
Recall@1	0.7500	0.6316
Recall@5	0.9722	0.9474
Recall@10	1.0000	1.0000
MRR@10	0.8472	0.7719
nDCG@10	0.8856	0.8289

Error Bank — Rev.5 only (n=23)
Metric	Overall (23q)	ODP-Subset (0q)
Recall@1	0.5652	0.0000
Recall@5	0.9130	0.0000
Recall@10	1.0000	0.0000
MRR@10	0.7399	0.0000
nDCG@10	0.8042	0.0000

Error Bank — Rev.4 only (n=11)
Metric	Overall (11q)	ODP-Subset (0q)
Recall@1	0.6364	0.0000
Recall@5	1.0000	0.0000
Recall@10	1.0000	0.0000
MRR@10	0.7879	0.0000
nDCG@10	0.8420	0.0000