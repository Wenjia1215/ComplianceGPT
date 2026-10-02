# AI-Assistance Disclosure

Candidate topics were collected through Web search, and ChatGPT and Gemini
supplied additional candidate-question suggestions. The author selected the
final question set and manually wrote and checked every final answer and
substantive gold annotation, including expected control and clause identifiers,
ODP lists, status labels, and exact citations. The author produced the initial
labels, asked ChatGPT to review them, and made a small number of changes after
considering its feedback; final decisions remained the author's.

The author assigned the ErrorBank categories and wrote the underlying
rationale in rough text. Gemini formatted that material as Markdown and
suggested grammar edits. Codex was used to help diagnose implementation bugs
encountered in the S1–S7 ablation work. The author made the final decisions and
retains responsibility for the benchmark, labels, code, manuscript, and
released artifacts.

Codex also assisted in implementing and testing the deterministic sampler and
spreadsheet packaging for the intra-annotator test-retest protocol. The author
specified the sample size, revision-stratified allocation, blinding fields,
washout procedure, and reporting plan; reviewed the selection logic; and
verified the frozen inputs, counts, exclusions, and cryptographic commitments.

## Experimental model use

`Qwen/Qwen2.5-7B-Instruct` is an experimental component, not merely a writing
assistant. Its roles in query rewriting, identifier selection, and the
generative baseline are documented with the model revision, prompts, settings,
and frozen outputs in the experiment records.
