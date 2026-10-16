# Targeted residual review v1: offline acceptance audit

Date: 2026-10-15. Base: `db53da0e6c811f64646f9e0b1af50772a2a3ccf4`, branch
`codex/study2-v5-judge-review-v2`. All changes are additive. Previous code, experiments,
Qwen outputs, paid operations, manifests and v2.2 salvage remain unchanged.

The new package is `exception_study2_v5_residual`. It reuses the existing provider,
immutable journal, budget, timeout, structured-output, canonical source and scientific
validation infrastructure. It does not invoke the full v2.2 review pipeline.

## Exact population reconciliation

| Accounting step | Resolved | Unresolved | Excluded | Total |
| --- | ---: | ---: | ---: | ---: |
| Original v2.1 | 122 | 255 | 0 | 377 |
| Saved v2.2 salvage | 149 | 228 | 0 | 377 |
| After mechanical exclusions | 137 | 103 | 137 | 377 |
| After historical A source revalidation | 133 | 107 | 137 | 377 |

The 137 mechanical exclusions comprise 12 already-absent and 125 unresolved
candidate/event combinations. They remain in the immutable prior evidence; their
exclusion is not a new judge vote. Four retained, previously positive A candidates
lack a sufficiently explicit recorded-value witness. They are unresolved in this new
plan, while the original votes, salvage labels and manifests remain unchanged:

| Case | Candidate | Exact source text |
| --- | --- | --- |
| `staged-v5-000/v0/original/visible` | `s-4ba7b2a2ebddd34dfb27:A` | `- **V5T9NUGW**: Manual, Cloth, Four doors, Y audit marker` |
| `staged-v5-002/v1/original/visible` | `s-23500c8d4581bf4681f2:A` | `- **V5TD48HZ** (Equipped for hot sand) → **B**` |
| `staged-v5-002/v1/original/visible` | `s-6e53213f88b9827c36f9:A` | `So the only record with "Equipped for hot sand" is **V5TD48HZ**, and it is classified as **B**.` |
| `staged-v5-002/v0/original/visible` | `s-c6f161eb2dd493ba7797:A` | `- **V5TD48HZ**: Equipped for hot sand, Automatic, Cloth, Four, Z → A` |

These feature summaries/classifications are not automatically called false. They do
not by themselves prove a recorded-value acknowledgment. Prior positive A votes need
an exact target recorded cell or a narrow, explicit whole-statement record assertion,
in addition to all existing semantic checks. Unknown forms remain unresolved. These
source-witness rules were informed by this audit and are not held-out validation.

Of the 107 retained unresolved candidates:

- **102 need fresh evidence**: 85 need only one provider; 17 need both.
- **Five are deferred disagreements**, all P diagnostics. Four are OpenAI/Anthropic
  present-versus-absent disagreements; one has inconsistent historical OpenAI phases.
  They remain uncertain, with no repeat votes or automatic adjudication.
- 92 missing OpenAI positions + 27 missing Anthropic positions = **119 requested
  candidate/provider decisions**. They form **21 deterministic batches**, of five or
  six items each, across separate full source packets where necessary.
- Nine coverage calls renew 44 historical failed obligations: A1, M7, C9, P9, O9, X9.
  The independent historical auditor coverage remains available. No old flag changes.

Retained candidate accounting by event (candidate counts, not trajectory incidence):

| Event | Reused resolved | Needs fresh evidence | Deferred disagreement | New provider decisions |
| --- | ---: | ---: | ---: | ---: |
| A | 38 | 30 | 0 | 40 |
| M | 33 | 18 | 0 | 20 |
| C | 10 | 11 | 0 | 12 |
| P | 20 | 24 | 5 | 26 |
| O | 0 | 0 | 0 | 0 |
| X | 32 | 19 | 0 | 21 |
| Total | 133 | 102 | 5 | 119 |

There are no retained O candidates in the historical pool; nine O coverage obligations
still require review. This does not broaden O or establish absence before coverage.

## Complete frozen request plan

Private immutable directory:
`~/exception-v5-recovery/study2-residual-v1-offline`.

Plan artifact hash:
`e60aedd71ad24f2c93a7aa8ac56fce0c03bc9ccb6d842d5e2ae81a70bd0a7ea7`.

Policy hash:
`c12bf5ab6c884fdf4935fbef245009aa327fd5244fa6c1d8e092f9359bb1a1d9`.

The plan was prepared from the implementation working tree on base `db53da0`; the
policy binds the exact new package, reused v2.1/v2.2/provider code and scientific code
hashes. The pushed implementation contains that code. Git HEAD alone is not used as
a substitute for the frozen code hashes.

- `residual-request-plan.json` in this audit is the complete request preview, copied
  byte-for-byte from the private plan. It contains every exact wire payload, candidate
  reference/span, source binding, reason for requesting the missing provider and cost.
- `request-index.md` indexes all 30 requests for inspection.
- The private `residual-plan.json`, `residual-policy.json` and `prior-evidence.json`
  retain the complete population, all old votes/operation references and source hashes.
- Full original paid response bodies remain in their existing immutable journal. No
  credentials, model weights, caches or new paid responses are included in this patch.

Exactly 21 semantic-verification requests plus nine coverage requests are frozen.
Every verification request has 4–8 candidates (the actual plan uses 5–6); already
resolved candidates are never used as padding. Multi-case requests use namespaced
wire IDs, with complete separate source packets and exact canonical ID mappings.
There are no J3 requests or dynamic request expansion. Newly discovered out-of-pool
candidates are deferred and prevent certification of affected event boundaries.

## Provider asymmetry and semantics

Historical source/operation identity, returned model, raw parsing, per-item semantic
checks and source alignment are revalidated before reuse. Both historical phases and
all J3 opinions remain in provenance. One provider is one position: the predesignated
J1 takes precedence within OpenAI; J3 is a fallback only when J1 has no conclusive
valid position. This fixed rule is not selected by outcome. Same-provider repetitions
are never counted as independent support or a majority. Contradictory valid phases
remain uncertain; valid OpenAI/Anthropic disagreement stays uncertain. No automatic
J3 dispatch or optional adjudication implementation is included in this protocol.

Only missing/invalid provider evidence is requested again in a new residual epoch.
Old valid support is never resent, rewritten, or outweighed by a new same-provider
majority. A returned partial batch can supply individually valid items; omitted,
malformed and duplicated items stay uncertain. Unrelated unknown IDs never vote.

M and O are the only primary failure families. A, C and X are supporting annotations;
P is solely in the observations sidecar. The unchanged scientific validator checks
source spans and prior-A ordering. Valid JSON alone cannot pass semantic checks.
Intervention semantics are not certified here; existing manual-review workflows remain
available with their own explicit provenance.

The real-source offline check preserves World 001's M at `[1285,1314)` and both
World 003 supported P statements. World 003's first P remains uncertain and O remains
absent. The P disagreements above receive no automatic rejudgment. These checks reused
existing evidence only; no new scientific or judge result was generated.

## Calls, cost and bounded smoke

Completing the fixed plan takes exactly **30 attempted calls**, minimum and maximum;
zero automatic adjudication/retries. A failed or omitted decision can remain uncertain
even after all planned calls finish. Budget stops/interruption may stop earlier.

Estimated spend: **$1.210284–$4.989262**, using the existing historical prices and
conservative token assumptions detailed in `cost` and the runbook. These are estimates,
not current pricing claims or billing guarantees. The exact J1/J2 model IDs are
`gpt-4.1-2025-04-14` and `claude-sonnet-5-5`; no silent model substitution is allowed.
The frozen offline configuration caps 30 calls and $25 estimated spend, with 8,192
output tokens/call, 240-second request timeout and 7,200-second scheduling wall limit.

The separately authorized smoke has four fixed lifetime slots, estimated
**$0.173178–$0.694592**. Its calls are a subset of the 30. Repeating smoke reuses its
terminal slots; full review reuses smoke results and has at most 26 calls remaining.
An interrupted in-flight call is terminal unavailable and is never resent. Changing
selection cannot gain four more calls because the subset is frozen in the plan.

The offline policy cannot dispatch. A future paid plan requires a separately reviewed
live configuration in a fresh directory, current access/contract/rate attestations,
and an explicit plan-hash authorization. The CLI has different authorization arguments
for smoke and full review; neither automatically launches the other. Exact offline
inspection and future authorized-smoke commands are in
`STUDY2_TARGETED_RESIDUAL_REVIEW.md`.

## Acceptance evidence

| Requirement | Status and evidence |
| --- | --- |
| Reuse only valid historical evidence with full provenance | PASS: `History` reparses/binds saved operations, reproduces salvage cases, revalidates source-specific A; prior evidence frozen separately |
| Precise unresolved population / exclude resolved items | PASS: 133 retained resolved excluded from dispatch; 102 residual candidates/119 missing provider decisions; exact set-equality regression |
| Small deterministic batches and complete bindings | PASS: 21 actual 5–6 item batches; namespaced case/candidate IDs; frozen request/source/prior evidence hashes; tamper and source-isolation tests |
| Nine renewed coverage reviews | PASS offline: nine exact frozen obligations; complete/no-event and incomplete/no-absence paths; old flags immutable; new discoveries deferred |
| Cross-provider support without OpenAI majority | PASS: disagreement/no-J3 tests; same-provider repeat/fallback/phase-conflict tests; all five real disagreements remain deferred |
| M/O definitions, A/C/X support, P sidecar | PASS: M preservation, P-not-O, false-A and prior-accepted-A regressions; exact legacy manifest validation |
| Bounded separately authorized smoke | PASS offline: four fixed slots; repeated smoke and full resume reuse slots; explicit stage authorization; invalid limits rejected |
| Immutable/no-retry historical and new operations | PASS: snapshots, tamper rejection, terminal HTTP error, interrupted-started recovery, no-resend tests |
| Scientific artifacts and old implementations unchanged | PASS: final `preservation-check.json` verifies all pre-task tracked and recovery files |
| Real-source frozen plan and baseline | PASS offline: `real-source-offline-acceptance.json`; sockets/model construction blocked; 30 unattempted requests |
| Real-provider schema acceptance / multi-case reliability | NOT TESTED: no paid calls |
| Fresh residual semantic accuracy / independent confirmation | NOT TESTED; this is an audit-informed repair, not independent validation |
| Qwen, RunPod, Study 2A/2B or interventions | NOT RUN, as requested |

- Targeted residual regressions: **33 passed**, zero failures/errors/skips, **202.617 seconds**.
- Full offline suite: **757 passed**, zero failures/errors/skips, **765.387 seconds**, including all 724 pre-existing tests.
- Network blocked; zero paid judge calls, pretrained Qwen inference calls or GPU inference calls.

The full runner blocks network sockets. New regression fixtures also block the real
model loader and use only mocked judges/source generation. Existing random-weight
CPU architecture tests remain in the full suite; no pretrained Qwen/GPU inference
or model download occurs. Full test IDs, exact elapsed times and logs are saved here.

Remaining limitations: the five genuine disagreements need a separately specified
protocol; new candidate discoveries are not automatically judged; conservative A
witnesses can leave valid but unrecognized prose unresolved; provider-family separation
is not statistical independence; the refreshed multi-case payloads and eight-k output
cap have not been tried on live providers. Stop after the pushed offline implementation.
