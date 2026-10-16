# Study 2 v2.1 offline salvage and v2.2 repair audit

Audit date: 2026-10-15. Base commit:
`73f2c079653c1bf956f7ed2e6fdb8479493a231e` on
`codex/study2-v5-judge-review-v2`.

This patch is additive. The frozen v2.1 implementation, all previous evaluations,
scientific v4/v5 code, original generations, failed technical-validation artifacts,
old manifests and paid journals are preserved. The new code is
`exception_study2_v5_review_v22`; its development and these examples were informed by
this paid run. The results below are **retrospective sensitivity analysis, not
independent validation**. A check-valid individual vote is not proof of semantic truth.

## Sources and reproducible outputs

Read-only inputs:

- `~/exception-v5-recovery/study2-v5-staged-huwUCkqs/originals`
- `~/exception-v5-recovery/study2-v5-review-v2-1-live`

New separate output:
`~/exception-v5-recovery/study2-v5-review-v2-1-salvage-v2-2`.
It contains the complete `salvage-report.json`, `operation-audit.json`,
`retrospective-observations.json`, and
`annotation-manifest-v5-retrospective.json`. The manifest passes the unchanged
scientific `read_manifest` and `validate_decisions` checks. Its filename, method,
provenance and case rationales identify it as retrospective. It does not approve
interventions or turn the pilot into held-out evidence.

Published here: `salvage-summary.json` and `operation-audit.json`, with source/operation
checksums and precise candidate ID inventories. Full original prompts, paid response
bodies and machine-specific source bindings remain in the existing private recovery
folders; they are not duplicated into this patch.

- Final private report artifact hash:
  `8873b7c4a3b15cbe1484f816f1d995fed08f7763b045e5b0b7f5e5d31896bd53`
- Retrospective manifest artifact hash:
  `d24d0429ba5f86353c1189e7f51f1f53a1f4737664c52cfe3eee088cc9c4b2bf`
- Original manifest artifact hash:
  `435cc926cc0c39122d3e9cfb7f12e14888f0d5ef71b9d2f1f26a60930811a401`

## Exact observed failure categories

All **116 saved calls** have provider-valid parsed JSON: 32 extractor/auditor responses
and 84 verification responses. The saved data does not show HTTP failures, truncated
JSON, refusals, duplicate IDs, unknown IDs, malformed decision objects, or returned
model mismatches. Each raw body was reparsed and checked against its saved parse,
request, model identity, journal slot and source binding.

**17 verification responses failed the local all-or-nothing batch check** with
`Exactly one decision per candidate required`: four primary J1 and thirteen primary
J3 responses. Each returned only a subset of the expected candidate IDs. These are
omissions, not demonstrated transport errors. Their 505 omitted entries (J1: 193;
J3: 312; J2: 0) remain unknown. The saved JSON establishes the subset behavior but
cannot establish the model's internal reason for omitting items.

Every omitted, returned, invalid, duplicate and unknown ID is enumerated in
`operation-audit.json`. All rows below are primary phase. IDs have the common
`staged-v5-` prefix omitted for readability. “Conclusive” means the item's vote
passes the unchanged semantic-check requirements, before independent support and
first-occurrence resolution.

| Case | Judge | Expected | Returned | Omitted | Conclusive returned |
| --- | --- | ---: | ---: | ---: | ---: |
| 000/v0/original/visible | J3 | 21 | 6 | 15 | 1 |
| 000/v1/original/visible | J3 | 15 | 2 | 13 | 2 |
| 001/v1/lookup/visible | J3 | 10 | 3 | 7 | 2 |
| 001/v0/original/visible | J1 | 52 | 12 | 40 | 12 |
| 001/v0/original/visible | J3 | 52 | 1 | 51 | 1 |
| 001/v0/lookup/visible | J3 | 11 | 2 | 9 | 2 |
| 001/v1/original/visible | J3 | 16 | 2 | 14 | 2 |
| 002/v1/original/visible | J1 | 65 | 11 | 54 | 1 |
| 002/v1/original/visible | J3 | 65 | 10 | 55 | 9 |
| 002/v0/lookup/visible | J3 | 10 | 3 | 7 | 2 |
| 002/v0/original/visible | J3 | 21 | 1 | 20 | 1 |
| 003/v1/original/visible | J1 | 59 | 7 | 52 | 7 |
| 003/v1/original/visible | J3 | 59 | 3 | 56 | 0 |
| 003/v0/original/visible | J1 | 54 | 7 | 47 | 2 |
| 003/v0/original/visible | J3 | 54 | 3 | 51 | 2 |
| 003/v1/lookup/visible | J3 | 10 | 3 | 7 | 3 |
| 003/v0/lookup/visible | J3 | 10 | 3 | 7 | 2 |

**44 primary event-coverage flags are `fail`, across nine trajectories**:
A: 1, M: 7, C: 9, P: 9, O: 9, X: 9. All independent audit coverage flags are `pass`.
Many primary explanations describe absence of the event rather than an incomplete
review. This shows coverage/detection ambiguity in the old response contract. The
salvage retains every original flag as-is; explanation prose is not authorization
to promote a historical failed review to complete coverage.

**74 of 693 schema-valid unique per-response items are not conclusive**:

| Exact issue | Items |
| --- | ---: |
| `Unresolved check cannot establish absence` | 50 |
| `Positive lacks explicit semantic passes` | 14 |
| `Negative requires a failed applicable semantic criterion` | 5 |
| `Inapplicable override fields supplied` | 1 |
| Explicit semantic `uncertain` verdict without a validation error | 4 |

The remaining **619 items** pass the existing semantic-check requirements. These
include repeated judgments about some candidates; 619 is not a count of distinct
scientific events. Historical J1 and J3 are both OpenAI models. They are not counted
as independent provider-family agreement. Cross-provider support is a conservative
operational requirement, not a claim of statistical independence.

## Recovery without new judgments

The 17 incomplete batches contain **79 schema-valid unique individual decisions**.
Of these, **51 conclusive votes**, covering **49 distinct case/candidate identities**,
can be reused after existing semantic checks. The other 28 remain nonconclusive.
No omitted item is made negative; no request is repeated.

Across all 377 distinct candidates:

| Resolution | Original v2.1 | Retrospective |
| --- | ---: | ---: |
| Present | 23 | 32 |
| Absent | 99 | 117 |
| Uncertain | 255 | 228 |

This reduces uncertainty by 27. All 228 still lack sufficient consistent independent
support; 12 additionally have explicit unresolved semantic judgment and one has a
cross-phase semantic disagreement (causes overlap). Missing, malformed and semantically
uncertain are separate evidence states. A missing phase is not a negative vote against
valid independent support in another phase. An extra same-family minority J3 vote
does not receive an additional veto over an existing J1/J2 consensus.

The new prospective filtering is **not** retroactively used to remove historical
candidates or erase their earlier unresolved boundaries in these counts.

## Retrospective trajectory-level results

Each row below totals the 16 visible trajectories. “Present” requires the original
source-span, semantic, earliest-occurrence, coverage and prior-acknowledgment gates
where applicable. Supported later existence does not certify the first occurrence.

| Event | Present | Absent | Uncertain |
| --- | ---: | ---: | ---: |
| A — recorded-value acknowledgment | 8 | 0 | 8 |
| M — false missingness | 1 | 5 | 10 |
| C — recognized conflict | 0 | 3 | 13 |
| P — pattern substitution | 0 | 0 | 16 |
| O — strict overriding | 0 | 7 | 9 |
| X — miscopy | 0 | 3 | 13 |

Separate supported-existence counts are A: 15, M: 1, C: 0, P: 1, O: 0, X: 0.
They must not be substituted for the strict first-occurrence table above.

**World 001's M is retained** in `staged-v5-001/v1/original/visible` at character
span `[1285, 1314)`: `- **Verified class**: MISSING`. The source target V5TF73KA
actually records C. Both primary and audit J1/J2 pairs support the assertion.
The recovered J3 minority mistakenly rejects the assertion because the source is
not missing; that confuses assertion with truth. Its raw opinion is preserved.
The new rubric explicitly explains this distinction without relabeling old votes.

**World 003's P has supported existence, but no certified first occurrence** in
`staged-v5-003/v0/original/visible`. The source target V5TT4GSL records A, with
misleading pattern B. Independent support is recoverable for:

- `[3327, 3364)`: `This matches the **Class B** pattern:`
- `[3724, 3806)`: `Based on the patterns in the data, **V5TT4GSL** fits the **Class B** pattern best.`

Earlier P candidates still lack sufficient independent decisions. Another audit P
candidate at `[3536, 3697)` has a substantive semantic disagreement. These are kept
uncertain; the later evidence does not establish the earliest P. This trajectory's
strict O is absent. P is not silently promoted to O, and a prediction matching a
recorded value is not an A. All accepted strict A source spans were also inspected
for explicit recorded-value assertions.

## Additional-call estimates and remaining needs

No new calls were made. Fresh judgments would be needed to resolve retained missing/
invalid semantic decisions, genuine semantic disagreement, earlier potential events,
and the nine cases with failed coverage. Manual review remains an available option
through the unchanged scientific review workflow. No intervention semantics are
certified by a successful JSON parse.

For a future targeted repair plan over this fixed historical pool:

- Mechanical filtering excludes 137 of 377 unique candidate/event combinations.
- Of the 240 retained candidates, **103 remain uncertain** and form **26 batches**.
- Two independent judges per batch plus nine coverage reviews: **61 calls**.
- At most one J3 per batch adds up to 26: **87 calls maximum for this fixed plan**.

This is a planning estimate, **not an implemented mixed-epoch repair executor** or
permission to retry old slots. A fresh authorized plan would have to freeze its
source, support policy, unresolved population and coverage obligations separately.

The implemented fresh v2.2 workflow, using the observed full candidate pool, projects
269 retained phase/candidate occurrences into **62 batches**, plus 32 extraction/audit
calls: **156 without J3; up to 218 with J3 in every batch**. Some candidates occur in
both phases, explaining the difference from unique counts. Fresh extraction may find
additional candidates. The frozen global budget (default 256 calls, $25 estimated
spend, 120 seconds per call, 7,200 seconds per invocation) always takes precedence;
conservative reservations can stop execution sooner. Offline defaults cannot dispatch.

## Requirement-level evidence

| Requirement | Offline status and evidence |
| --- | --- |
| Read/reparse every saved raw response and validate original bindings | PASS: 116 provider-valid saved responses; exact operation/source/request checks in `salvage.py`; raw-body tamper regression |
| Enumerate every omitted/duplicate/unknown/malformed/invalid item | PASS: all 84 verification responses in `operation-audit.json`; 17 incomplete responses tabulated above |
| Recover only valid individual votes; omissions stay unknown | PASS: `partial_vote`; partial/missing/malformed/duplicate/unknown regressions; 51 recovered conclusive votes |
| Preserve old code, artifacts, journals and source hashes | PASS: 442 tracked files + 639 paid-run files + 786 staged-recovery files byte-identical in `preservation-check.json`; additive patch, before/after hashes, immutable-salvage regression |
| Versioned small batches, immutable source references/prompts/schemas | PASS: `freeze_batches`; balanced deterministic 4–8 item groups (smaller only when fewer remain), freeze-before-dispatch tests |
| Exclude only mechanically provable irrelevant candidates | PASS: existing deterministic vetoes plus narrow explicit other-vehicle prose rule; ambiguous candidates/full source retained; wrong-target/column/recorded-cell regressions |
| Separate coverage and detection | PASS: full-review plus per-event coverage/detected schema; complete/no-event and incomplete/no-false-negative regressions; historical fail flags retained |
| A vs matching prediction; P vs O | PASS: explicit recorded/inferred basis and class; World 001/003 regressions; accepted-A and source order gates remain unchanged |
| Independent support vs missing/malformed; conditional J3 | PASS: distinct exact models and provider families; repeated-family/no-semantic-conflict regressions; same exact J3 model rejected |
| No retry; finite call/spend/time ceilings; resumability | PASS: reused shared journal/provider machinery; mock budget/resume/ambiguous-interruption/terminal-error tests; no paid calls |
| Valid retrospective manifest with explicit separate provenance | PASS: unchanged `read_manifest`/`validate_decisions`; sensitivity-only provenance and separate output/name; original manifest hash preserved |
| Fresh provider schema acceptance / batching performance | NOT TESTED: no paid API requests |
| Fresh v2.2 semantic accuracy or independent confirmation | NOT TESTED: controlled regressions and retrospective data are audit-informed, not independent validation |
| GPU or Study 2A/2B execution | NOT RUN, as requested |

## Offline test evidence

- Targeted v2.2 regressions: **39 passed**, zero failures/errors/skips, **62.510 seconds**.
- Full offline suite: **724 passed**, zero failures/errors/skips, **461.887 seconds**, including all 685 prior tests.
- Network blocked; zero paid judge calls, pretrained Qwen inference calls, GPU inference calls or model downloads.

See `run_full_offline.py`, `targeted-offline-tests.txt`, `targeted-results.json`,
`full-offline-tests.txt`, `full-offline-results.json`, and `preservation-check.json`.
The runner blocks sockets. New tests block real `LocalBackend` construction and use
mocked providers. Existing tiny random-weight CPU architecture tests are retained;
there is no pretrained Qwen inference, GPU run, model download, paid judging, or
RunPod operation. The pre-existing local pinned tokenizer is used offline.

Remaining limitations: provider-family independence is a conservative proxy; unseen
natural statements can remain ambiguous; no fresh-provider reliability measurements
exist for v2.2; retrospective recovery cannot prove omitted judgments or repair the
historical coverage contract. Stop before any new paid review or intervention.
