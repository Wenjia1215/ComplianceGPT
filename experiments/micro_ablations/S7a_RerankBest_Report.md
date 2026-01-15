# Micro-Ablation (a): (S7a: S7 pipeline but with the Reranker using the Best-Rewrite) — Performance Evaluation


## NIST SP 800-53 Rev. 5: Performance

| Metric   | Overall (100q) | ODP-Subset (63q) |
|----------|----------------:|-----------------:|
| Recall@1 |          0.7000 |           0.6667 |
| Recall@5 |          0.9500 |           0.9683 |
| Recall@10|          0.9900 |           1.0000 |
| MRR@10   |          0.8177 |           0.8045 |
| nDCG@10  |          0.8607 |           0.8536 |

## NIST SP 800-53 Rev. 4: Performance

| Metric   | Overall (36q) | ODP-Subset (19q) |
|----------|---------------:|-----------------:|
| Recall@1 |         0.7222 |           0.6842 |
| Recall@5 |         1.0000 |           1.0000 |
| Recall@10|         1.0000 |           1.0000 |
| MRR@10   |         0.8449 |           0.8289 |
| nDCG@10  |         0.8846 |           0.8729 |

## Error Bank — Rev. 5 only (n=23)

| Metric | Overall (23q) | ODP-Subset (0q) |
|--------|---------------:|----------------:|
| MRR@10 |         0.6982 |          0.0000 |

## Error Bank — Rev. 4 only (n=11)

| Metric | Overall (11q) | ODP-Subset (0q) |
|--------|---------------:|----------------:|
| MRR@10 |         0.7879 |          0.0000 |
