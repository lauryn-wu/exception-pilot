# Acknowledgment validation follow-up: residual v1.1

Base: `40856c439cc4551ecde0380f155d5403ef28f30b`, branch
`codex/study2-v5-judge-review-v2`. This is an audit-informed correction, not an
independent validation study. The previous v1 audit and frozen plan are preserved.

## Findings and evidence

| Requirement | Result | Evidence |
| --- | --- | --- |
| Identical source criterion for historical and new positive A | PASS | Both invoke `acknowledgment_decision`, which requires the unchanged `recorded_witness` in addition to existing independent semantic checks. |
| Matching classification/feature summary insufficient | PASS | Four separate regressions reproduce all four historical excerpts; the real-source audit repeats them with original spans, IDs, target class and packet. |
| Insufficient source stays uncertain | PASS | Rejected positives keep `prior_ack_id=None`; audit preserves their original normalized votes and removes them from conclusive IDs. No automatic absent decision. |
| Valid explicit acknowledgment accepted | PASS | Fifteen positive combinations cover five existing witness forms and recorded classes A/B/C; semantic-failure, wrong-class and wrong-target checks still reject. |
| Unsupported A cannot enable O | PASS | Two synthetic providers can positively endorse A/O, but source-rejected A leaves final O uncertain through the unchanged v5 validator. A valid source-backed A control permits explicit O. |
| Avoid futile paid verification | PASS | 30 unresolved source-ineligible A candidates are deferred; 40 provider/candidate judgments removed. Their evidence gaps and provenance remain visible, and all 240 retained statuses stay unchanged. |
| Preserve historical data and definitions | PASS | SHA-256 comparison: 786 original/staged files, 639 paid-review files, five salvage files and five v1-plan files unchanged. All 475 prior tracked files outside the six intentional edits unchanged. |
| Preserve M and separate P / strict O | PASS | Original world 001 M remains present. World 003 has two supported P locations, first-P uncertainty and absent strict O; all unchanged v5 annotation checks pass. |
| Fresh versioned plan, never amend v1 | PASS | New directory `study2-residual-v1-1-offline`, version `study2-residual-v1.1`. Old plan rejected by new code with `Residual policy/code changed`. |
| Frozen residual batches and coverage | PASS | 14 deterministic batches of 5–6 candidates plus the same nine coverage reviews; full requests and reasons in the preview. No resolved candidate padding, J3 dispatch or retries. |
| Full offline suite | PASS | 769 tests, zero failures/errors/skips in 675.575 seconds; 45 residual tests include 12 new acknowledgment regressions. Sockets blocked throughout. |
| Live provider accuracy / paid judging / Qwen | NOT TESTED | Intentionally not executed. No judge-operation directory exists for the fresh plan. |

## Plan identity and accounting

- Plan hash: `739a394f47743b3ba1bf562cf9f771a13fb2d5198085e70e4e1ef8a6ccd16c8d`.
- Policy hash: `e7d95c742c5afe0cb212b4768cb5b207e1ef9e619d1e185ac62c031957b7eea7`.
- Implementation hash: `895c53a469f19ad4491a0cfa178fd211bf67ceae9cf8fba59353cc69fe5b1297`.
- Preparation recorded base commit `40856c4...` with the updated implementation
  hash before the patch commit. No historical plan metadata was rewritten.

377 original combinations → 137 mechanical exclusions → 240 retained, including
133 resolved (28 present / 105 absent) and 107 uncertain. Those 107 split into
30 source-ineligible A deferrals, five genuine disagreements, and 72 candidates
requiring new judgments. No deferred uncertainty is counted as a negative.

The 72 candidates require 79 missing-provider judgments: 63 OpenAI and 16 Anthropic,
in 11 OpenAI and three Anthropic verification batches. Nine renewed coverage
reviews remain. Thus the fixed complete plan is **23 calls** rather than 30; the
existing four-call smoke cap is a subset, not an additional allowance. All 23 are
unattempted. No automatic adjudication. Supported decisions and operation provenance
are reused without redispatch. Historical coverage flags are unchanged.

Using the inherited historical rate table and original token-reservation formula,
the full-plan estimate is $0.879602–$3.686602 and smoke estimate $0.165908–$0.665510.
These are not current provider quotes or guarantees. Live contract, access and rates
still need separate verification and authorization; the saved config is offline.

## Reproduction and limits

See [the v1.1 runbook](../../STUDY2_RESIDUAL_ACKNOWLEDGMENT_V1_1.md) for exact
inspection, fresh reproduction and offline test commands. `residual-request-plan.json`
is the byte-identical copy of the fresh output's complete `request-preview.json`.
`real-source-offline-acceptance.json` includes all 30 deferrals and the four original
source-bound examples. `preservation-check.json` records byte-level preservation.
`full-offline-results.json` and `full-offline-tests.txt` record the complete offline run.

The source-witness matcher is conservative and was not broadened. A candidate can be
deferred because its prose is unrecognized, not because absence was established.
Valid semantic JSON alone is insufficient. The 30 deferrals can still limit earliest-A
and downstream O certification, even after all 23 planned requests return. Completing
the plan therefore does not guarantee complete resolution or intervention eligibility.
No scientific prompt, generation, validator, P definition or intervention gate changed.
