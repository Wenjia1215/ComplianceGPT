# Source-backed review findings

The final strict endpoint uses every gate in [STANDARD_V2.md](STANDARD_V2.md), including clarification value domains. The summary and all 408 per-row decisions are in [results_v2](results_v2/). Historical data and scores are retained.

## Count reconciliation

Body failures include withheld credit for the one uncertain semantic case. Category overlaps count once.

| Revision / system | Old passes | Added body failures | Added clarification failures | Overlap | Final passes |
| --- | ---: | ---: | ---: | ---: | ---: |
| Rev5 baseline | 25 | 4 | 0 | 0 | 21 |
| Rev5 ComplianceGPT | 65 | 0 | 14 | 0 | 51 |
| Rev5 Gemini | 66 | 10 | 9 | 1 | 48 |
| Rev4 baseline | 8 | 2 | 0 | 0 | 6 |
| Rev4 ComplianceGPT | 29 | 0 | 4 | 0 | 25 |
| Rev4 Gemini | 24 | 2 | 6 | 1 | 17 |

Rev5 Gemini Q67 is uncertain: its rescreening wording may change the parameter's conditional conjunction or may be shorthand for trigger modes. It receives no strict credit. If adjudicated as passing, Gemini's final count becomes 49/100 and its supplementary body count becomes 57/100. It remains in the denominator in both cases.

## Gemini body findings

Every case below passed S0. Exact answer excerpts and full canonical references are recorded in [reviews_v2.jsonl](reviews_v2.jsonl); this table summarizes the material change.

| Revision / question | Added gate | Source-grounded issue |
| --- | --- | --- |
| Rev5 Q17 | P, F | CA-3's agreement selection is expanded to policies/procedures as alternatives. The parameter inventory permits agreement types and other agreements. |
| Rev5 Q20 | P, F, A | `ca-7_prm_5` is a reporting frequency, but the body groups it with recipient personnel/roles. Reporting periodicity disappears. |
| Rev5 Q22 | P, F | The convening choice permits periodic or condition-triggered meetings. The body silently selects the periodic branch while the choice remains unresolved. |
| Rev5 Q24 | U, A | `cm-6_smt.b` is cited but implementation of the configuration settings is absent from the body. Establishment, deviations and monitoring do not express implementation. |
| Rev5 Q35 | F | The public-accessible limitation on accepting only NIST-compliant external authenticators is moved to the SP 800-63B parenthesis. The former obligation becomes unconditional. |
| Rev5 Q67 | P, F — uncertain | The parameter specifies rescreening conditions and, where indicated, frequency. The body says frequency or conditions. This case is withheld from strict credit pending independent adjudication. |
| Rev5 Q86 | P, F | The parameter alternatives are physical/logical separation; the body substitutes organizational separation. |
| Rev5 Q87 | F | The source says hash functions have applications in signatures/checksums/MACs. The body presents those as included hash functions. TLS and IPSec are explicitly supported and are not error grounds. |
| Rev5 Q90 | P, F | A confidentiality/integrity selection becomes safeguards to protect. The condition on fallback scanning/offline storage is also omitted. |
| Rev5 Q100 | P | The reporting choice includes counterfeit sources, external reporting organizations and a personnel/roles branch. The body keeps only personnel/roles without an approved selection. |
| Rev4 Q7 | A | Naming CA-2 and deferring frequency/recipients does not explain assessment of correct implementation, intended operation and security outcomes. |
| Rev4 Q10 | P, F | Operational requirements for approving deviations become an organizational monitoring and assessment path. |

## Baseline body findings

The baseline faces the same gates. Rev5 Q31 cites non-organizational-user IA-8 while stating only organizational-user behavior; Q57 cites social-media guidance without expressing its content. Q35 drops the same public-accessible authenticator limitation as Gemini. Q76 omits the required supporting rationale for categorization. Rev4 Q15 cites lessons learned while stating only incident phases, and Q33 cites managed external connections while stating only communication monitoring/control.

The audit accepts concise correct answers elsewhere. A principle-name question does not require a copied guidance paragraph. An overlapping citation can contribute a proposition already supported by another record; it need not be unique. Extra cited enhancements are not automatically rejected when their source-backed content is actually used.

## ComplianceGPT strength and remaining failures

All 65 Rev5 and 29 Rev4 S0-passing ComplianceGPT bodies equal concatenations of complete canonical statement/guidance records, including all gold-required IDs. This supplies a sufficient proof that selected obligations, source limitations, technical relations and parameter references are expressed without alteration. Nonliteral answers can satisfy the same body gates through source inspection; copying is not required.

This is a body-retention strength on the eligible archived outputs, not a proof of overall evidence selection, useful brevity, parameter specificity or general model superiority. For example, ComplianceGPT Rev5 Q24 retains implementation prose through the parent but lacks the required child ID. Its S0 failure remains a failure.

Clarification errors remove 14 Rev5 and four Rev4 eligible ComplianceGPT answers. Examples include requesting days for recipients, a job title for a frequency, a scalar duration for an event-set-plus-frequency parameter, or a numeric threshold for an action selection. The same shared clarification mechanism also affects Gemini. These are contract/wrapper defects, not all attributable to the free-form model's prose.

All clarification mismatches retain the canonical definition, requested domain and original prompt in the per-row files. Unknown domains are not guessed; a neutral free-text prompt can pass.

## Interpretation

ComplianceGPT has the highest point estimate under this trial's full endpoint on both revisions. The Rev5 paired difference is small (51 versus 48; exact two-sided McNemar p = 0.663624). It does not establish statistical superiority. The Rev4 paired p = 0.0214844 is an unadjusted exploratory comparison under retrospectively developed criteria, not confirmatory evidence.

The original outcomes were reproduced with zero disagreements across 408 outputs. No model was rerun; no gold label, output, evidence window, generation prompt or Runtime Verifier file was changed. Independent adjudication and a new validation set would be needed to make a prospective accuracy claim.
