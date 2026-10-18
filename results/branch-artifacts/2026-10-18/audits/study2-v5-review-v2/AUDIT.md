# Review v2 implementation and failure audit

Base: `07e4b6552509f955f62d234c7a9ee8a634cf649b` on the existing v5 branch.
Implementation branch: `codex/study2-v5-judge-review-v2`.
This directory contains code/test evidence and aggregate inspection facts only. The
private original generations, recovered journals and v2 inspection packets were not
copied into Git. No paid calls, GPU inference or weight downloads were performed.

## Demonstrated v1 failures and changes

| Finding | Additive v2 response | Evidence / limitation |
|---|---|---|
| A reconstructed target missing cell was missed by holistic votes | Structural field/row extraction plus independent semantic extraction; all candidates are reference checked and independently verified | Recovered world 001/v1/original produces one grounded false recorded reconstruction; M span `[1285,1314)`; source value C vs generated missing value. **Semantic live confirmation not tested.** |
| Pattern substitution risked being conflated with override | Separate observational P, explicit C, and stronger O requiring independently accepted earlier A | World 003/v0/original has matching recorded-value reconstructions at `[1233,1300)` and `[1484,1552)` and pattern candidates. No automatic O conclusion; final answer removed before review. |
| Two negative votes could miss an event | Separate independent full-text negative auditor; every finding independently verified even if previously rejected | Regression detects an omitted M via audit. Cross-phase disagreement invokes the existing bounded J3 slots; unresolved disagreement stays uncertain, not majority-overridden. |
| Independently invented quotes failed literal alignment | Fixed canonical Unicode statements and IDs; no generated quotes; merge by location/event | Exact accepted-span alignment 100% on controlled oracle integration; repeated/Markdown/Unicode regressions. |
| Nullable enum provider failure reported in v1 | Non-null required wire objects/arrays/string enums; internal null only after validation | Both provider payloads tested offline. Recovered directory contains 86 OpenAI HTTP 200 responses and no Anthropic HTTP error body; the stated historical error could not be re-audited from these files. Current documentation includes null support, so do not claim all nullable schemas are universally unsupported. No real v2 provider acceptance tested. |
| Valid JSON was insufficient semantic evidence | Separate required semantic ratings, exact references, mechanical contradiction veto, independent prior-A check | Invalid positive and invalid negative regressions: an affirmed target/field/recorded assertion cannot deny its exact missing-cell comparison. Fabricated IDs, contradictory fields, negation/hypothesis and O-without-A also covered. |
| Downstream edit verification could be conflated with annotation | Existing scientific export validator and independent edit verifier unchanged | v2 export passes both legacy validators; unverified edit template still fails. |

Only generated pre-answer text is segmented. The original prompt/table is separate
reference data. The source row index is zero-based over data rows, excluding two
Markdown header lines. An objectively differing/missing reconstructed value does not
itself prove endorsement: quoted, negated and hypothetical reconstructions remain
semantic decisions. The structural grammar is intentionally incomplete; ambiguous
facts stay unknown, not mechanically accepted.

Final full offline acceptance: **656 tests passed, 0 failures, 0 errors, 0 skips**,
395.094 seconds, network blocked. This includes 46 new v2 tests and all 610 existing
tests. Targeted v2 run: 46 passed in 54.830 seconds. Exact logs and machine-readable
results are included in this directory.

## Requirement acceptance

| Spec | Status | Evidence |
|---|---|---|
| 1. Additive module; preserve all frozen scientific/v1 work | PASSED offline | New package/config/tests/docs/audit only; preservation-check.json; unchanged scientific hashes. |
| 2. Six-event codebook; P separate | PASSED offline | CODEBOOK.md, family prompt sections, schema and sidecar tests. |
| 3. Structural + independent semantic extraction | IMPLEMENTED; mock-tested | Exact spans, provenance merge, full-text semantic extractor. Real semantic extraction recall NOT TESTED. |
| 4. Deterministic reference verification | PASSED for supported structures | Target plate, source value, generated header/cell order, field lists, prediction grammar, Unicode spans, wrong entity/column and comparison veto tests. Ambiguous prose remains semantic. |
| 5. J1/J2 + conditional J3, blinded | PASSED offline | OpenAI/Anthropic payloads, independent operation slots, same blinded candidate packet, no votes/outcomes; actual model access/contract NOT TESTED. |
| 6. Reconciliation/negative audit/earliest occurrence | PASSED offline | False-negative rescue, cross-phase disagreement, earlier uncertainty, later correction and O ordering tests. Real semantic completeness NOT TESTED. |
| 7. Provider reliability and no retries | PASSED offline; live NOT TESTED | Non-null schema, required/enums, missing/unknown IDs, contradictory fields, refusal/truncation/errors, exact returned model, interruption/replay tests. |
| 8. Controlled suite and metrics | PASSED as engineering harness; semantic targets NOT ESTABLISHED | 192 cases / 64 template families, explicit development and held-out wording, per-event metrics in controlled-results.json. C/O structural held-out recall below 95%. |
| 9. Existing Qwen pilot | PARTIAL: mechanical inspection PASSED; semantic judging NOT TESTED | Read-only verified 32 originals / 16 visible, 368 structural candidates; known M located; A/P/C/O kept distinct; zero judge requests. Pilot remains exploratory. |
| 10. Compatible export and intervention gates | PASSED offline | All 16 mock cases exported, unchanged read_manifest/validate_decisions pass, source hashes retained, P sidecar, independent edit gate fails without verification. |
| 11. CPU-only and finite budgets | PASSED offline | Import without Torch, socket-blocked preparation/tests, explicit live flag, finite calls/spend/output/timeout/wall, POSIX deadline and no-resend tests. |
| 12. Package, CLI, runbook, audit and tests | PASSED offline | Added files listed below; exact commands in runbook. |
| 13. Commit/push then stop | Verify with final delivered commit | No downstream scientific work authorized or executed. |

The detector emits present/absent/uncertain and unavailable-source invalid. It adds no
new exclusion rule. The legacy manual/export ecosystem retains excluded where
applicable downstream; annotation acceptance never substitutes for edit eligibility.

## Controlled evaluation: frozen split, not an empirical judge benchmark

Suite `controlled-v2.0-split1`, seed `2026101502`, hash
`48d1a7b6b4b76375f69f229cc8c0977d930d0ff493b843f29e60d4e739c07fa8`.
Both partitions contain 96 cases from 32 authored templates with three context/layout
challenges each. These are dependent within template family, not 192 IID observations.
Truth is assigned during construction, never by an LLM. The first evaluation is saved
as controlled-results.json. The extractor was not tuned after inspecting held-out
results; the observed C/O shortfalls are retained. A later generic code-audit fix rejected
negative verdicts that contradict affirmed structured facts, and another ensured
cross-phase disagreements also invoke the already reserved J3 slots. Neither changed the
extractor nor the templates, labels, split or thresholds; reevaluation was identical
(see controlled-evaluation-provenance.json). It is not a new independent validation.

| Event | Held-out structural occurrence recall | Oracle-wired precision / recall / F1 | Oracle TP / FP / FN / TN | Oracle abstention |
|---|---:|---:|---:|---:|
| A | 67/67 = 100% | 100% / 100% / 100% | 48 / 0 / 0 / 47 | 0% |
| M | 26/26 = 100% | 100% / 100% / 100% | 18 / 0 / 0 / 77 | 0% |
| C | 11/14 = 78.6% | 100% / 100% / 100% | 12 / 0 / 0 / 83 | 0% |
| P | 26/26 = 100% | 100% / 100% / 100% | 24 / 0 / 0 / 71 | 0% |
| O | 9/12 = 75% | 100% / 100% / 100% | 12 / 0 / 0 / 83 | 0% |
| X | 12/12 = 100% | 100% / 100% / 100% | 9 / 0 / 0 / 86 | 0% |

One unavailable original in each split is separately invalid, excluded from these
95-case confusion counts. Accepted exact spans: development 120/120; held-out 123/123.
No critical constructed M/X occurrence was missed structurally. Complete development
metrics are in the JSON. These counts test mechanics conditional on oracle-supplied
semantic extraction/verification; they do not establish model semantic accuracy.

**Without real judges, production abstains on all 95 available cases per split**:
precision undefined, recall 0, F1 0, abstention 100% for all six events. All real-model
≥95% semantic precision/recall targets remain unverified. Abstentions on positives are
counted as FN; abstentions on negatives are not TN and are separately counted. No
unresolved case becomes absent. Do not present the oracle scores as achieved judge
performance or use this pilot as independent validation.

## Reuse and implementation boundaries

Added package files: `__init__.py`, `__main__.py`, `artifacts.py`, `policy.py`,
`candidates.py`, `decisions.py`, `workflow.py`, `controlled.py`, `CODEBOOK.md`.
Added configuration, targeted tests, runbook and this audit directory.

Unchanged reuse: `exception_review/{journal,providers,policy,artifacts}.py`, v5
`Source`/`bound_source`, `blinded_view`, `validate_decisions`/`read_manifest`, source
hashing and locks, plus v1 `target_metadata` and output separation checks. Shared
journal/provider code is loaded in an isolated v2 policy namespace; no globals are
patched. Its old draft/verify operation names now select v2 extraction/audit schemas;
no edit generation occurs. Two explicitly versioned phases each have at most four
calls and share one global budget ledger. v1's policies and call identities do not
change.

## Remaining risks and operational limits

- Non-null request construction is tested locally; provider schema acceptance, exact
  model availability and semantic judgment quality require the later authorized smoke
  and further independent semantic evaluation. A four-call smoke is not that benchmark.
- Correct structured facts and aligned text are not semantic truth. Judges can share
  errors. A conservative negative audit reduces but cannot eliminate missed claims.
- Compound assertions may lack separable A→O spans; repeated contexts may fail the
  unchanged unique 40-character export anchor. These remain uncertain, preserving the
  frozen scientific validation rules. Large candidate arrays may hit output limits;
  that is a recorded terminal failure, never an automatic retry with altered prompts.
- Existing v5 stores absence/presence over the saved pre-answer text only. Truncated
  traces are not extrapolated. Invalid final answers are not semantic event labels.
- Existing edit verification still needs its independent verifier. Fully automating
  that stage requires a separately approved protocol amendment.
- The full pilot later uses 64–128 requests (normally up to 96 before J3), including
  smoke calls. About $2–$20 is a planning range under explicitly assumed $1–$3/M input
  and $5–$15/M output with 0.7–2.0M input / 0.15–0.8M output tokens. See runbook for
  byte-based evidence, output-cap caveats and finite $25 estimated-spend default.

Offline test counts and elapsed times are recorded in `offline-results.json` and
`targeted-offline-tests.txt`. All original test files remain unchanged. No API access
or GPU computation was needed to produce this evidence.
