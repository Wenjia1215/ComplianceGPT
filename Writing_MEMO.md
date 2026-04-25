# ODP Retrieval Boundary Note

This note fixes the wording boundary for ODP/PRM records in ComplianceGPT.

## Canonical Wording

ComplianceGPT uses a clause-level retrieval corpus consisting of statement and guidance records from the Canonical Clause Store. The full CCS inventory also contains object and parameter records, including ODP/PRM records, but these records are not treated as default cited evidence candidates. Instead, they support canonical parameter resolution, organization-profile validation, ODP policy handling, and verifier checks. ODP behavior is triggered when selected clause text contains unresolved parameter placeholders, not by citing parameter records as evidence.

## Correct Statements

- The retriever ranks clause-level statement and guidance records.
- The full CCS inventory includes ODP/PRM records.
- ODP/PRM records support canonicalization, profile validation, ODP policy handling, and verification.
- Evidence spans cited to the user should come from canonical clause text, not standalone parameter records.
- Unresolved ODPs are detected from placeholders appearing inside selected clause text.

## Statements to Avoid

- “The retriever retrieves ODP records.”
- “ODP records are ranked as evidence.”
- “Parameter records are cited as evidence clauses.”
- “The retriever uses ODP records as ordinary candidate chunks.”
- “ComplianceGPT answers ODP questions by retrieving the ODP registry.”

## Practical Interpretation

The retrieval experiment evaluates whether S1–S7 recover the governing clause neighborhood for ODP-bearing questions. The ODP registry and parameter inventory are used after evidence selection to determine whether unresolved organization-defined values must be surfaced or filled from an approved organization profile.