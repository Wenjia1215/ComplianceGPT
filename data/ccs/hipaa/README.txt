
HIPAA CCS (Cleaned) — Schema & Delta Notes
==========================================

Files
-----
- 2023 CCS: /mnt/data/hipaa/hipaa_2023_ccs.jsonl
- 2024 CCS: /mnt/data/hipaa/hipaa_2024_ccs.jsonl
- Delta 2023→2024: /mnt/data/hipaa/deltas/hipaa_2023to2024.jsonl
- Categories snapshot: /mnt/data/hipaa/categories_snapshot.csv

Cleaned clause object schema
----------------------------
{
  "framework": "HIPAA",
  "version": "2023" | "2024",
  "effective_date": "YYYY-MM-DD" | null,
  "clause_id": "HIPAA-SR-<stable-id>",
  "title": "...",
  "clause_text": "...",
  "category": "Administrative|Technical|Physical|...",
  "is_required": true | false | null,
  "source_uri": "http(s)://" | null,
  "norm_text": "<lowercased whitespace-collapsed clause_text>",
  "norm_text_hash": "sha256:<hash>",
  "_orig": { ... original fields ... }
}

Notes
-----
- `clause_id` is **version-agnostic** and stable. We derive it from CFR-style fields if present;
  otherwise we normalize the original ID by removing year segments (e.g., HIPAA-SR-2023-0001 → HIPAA-SR-0001).
- `is_required` has been normalized to a nullable boolean: true/false/null (e.g., "N/A" → null).
- `norm_text` + `norm_text_hash` support dedup and text-change detection across versions.

Delta semantics
---------------
We compare records by stable `clause_id`:
- Present in 2024, not in 2023 → ADDED
- Present in 2023, not in 2024 → REMOVED
- Present in both but `norm_text_hash` differs → MODIFIED
- Else → unchanged (no delta row)

Stats from the current files
-----------------------------
- 2023 clauses: 118
- 2024 clauses: 118
