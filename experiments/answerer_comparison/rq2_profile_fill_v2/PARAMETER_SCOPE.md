# Parameter scope of the profile-filling result

This is a **post-hoc diagnostic**, added after the registered v2 run. It does not
change the formal protocol, acceptance rules, original gold labels, or result
archive. Reproduce it with:

```bash
PYTHONPATH=src:. python experiments/answerer_comparison/rq2_profile_fill_v2/audit_parameter_scope.py
```

The 63/63 complete-profile result means every keyed placeholder visible in each
of those 63 rows' retained canonical spans was supplied and resolved. It does
not mean every author-gold parameter or normative obligation was present in the
selected evidence. Comparing normalized parameter IDs with the unchanged author
gold labels gives full listed-parameter coverage in 61/63 positive rows:

| Rev.5 query | Gold parameter absent from retained evidence |
|---|---|
| 77 | `ra-03_odp.02` |
| 93 | `si-04_odp.02` |

For these two rows, `OK` under a complete profile is a conditional construction
status for retained spans; it is not evidence of a complete answer to the
question. Supplying values cannot repair an unselected clause. No original
retrieval, selection, historical ASK score, or label was changed to improve this
diagnostic. The profile study must not be described as 63/63 semantically correct
or complete answers, or as a new overall benchmark accuracy score.

The 37 author-negative controls refer to the existing gold ODP stratum. Twenty
of their frozen answers nevertheless contain keyed placeholders. Accordingly,
the empty/partial/invalid profile conditions correctly report `PARAMS_REQUIRED`
for those 20 retained-span constructions; the other 17 have no such visible key.
This observation does not establish whether the author labels or retained
evidence are independently correct. Evidence completeness and independent
expert validation remain separate questions.

`parameter_scope_audit.json` preserves the normalized sets for all 100 rows and
the exact source/registration hashes. The formal v2 results remain PASS against
their predeclared conditional mechanism rules.
