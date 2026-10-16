# Study 2 residual review v1.1: acknowledgment source gate

This is the acknowledgment follow-up to `40856c439cc4551ecde0380f155d5403ef28f30b`.
Use this version's fresh plan and configuration for offline inspection. The earlier
[residual v1 runbook](STUDY2_TARGETED_RESIDUAL_REVIEW.md), configuration, frozen plan,
and audit remain historical records; their counts describe v1, not v1.1.

## Acceptance and deferral

Historical and new positive **A** votes now pass through the same
`acknowledgment_decision()` → `recorded_witness(packet, candidate)` gate. A positive
must explicitly recognize the target's actual recorded Verified class. A matching
classification, inferred class, or feature summary does not establish that recognition.
The judge's `value_basis=recorded`, `asserted_class`, valid JSON, and passing semantic
checkboxes cannot substitute for the frozen source witness. The existing literal
witness forms, scientific definitions, and v5 annotation validator are unchanged.
A witness is necessary but is not itself a semantic vote or cross-provider agreement.

An unsupported positive becomes **uncertain**, never automatically absent. Its raw
response stays immutable; the derived audit retains its original normalized decision,
records the failed source check, and removes the candidate from `conclusive_ids`.
Existing independently supported negatives remain valid. An unsupported A cannot
satisfy the unchanged prerequisite for an eligible O event, even if both providers
return positive A and O judgments. M and strict O remain the two primary families;
P remains a separate observational sidecar.

For an unresolved A with no witness in the frozen text, more positive judge responses
cannot meet this policy. Such candidates are **deferred from paid verification**, not
removed from the population or relabeled absent. `required_providers` still records
missing evidence; `dispatch_providers=[]` and `deferral_reason` explain why no request
is scheduled. These A candidates continue to affect earliest-event and O eligibility.
The rule does not cancel full-text coverage reviews, certify other events, modify
historical coverage flags, or authorize another protocol. Manual/separately specified
review remains possible; paid retries or relaxing the witness gate are not implicit.

## Fresh plan and accounting

New private output:
`/Users/laurynwu/exception-v5-recovery/study2-residual-v1-1-offline`

- Plan: `739a394f47743b3ba1bf562cf9f771a13fb2d5198085e70e4e1ef8a6ccd16c8d`
- Policy: `e7d95c742c5afe0cb212b4768cb5b207e1ef9e619d1e185ac62c031957b7eea7`
- Implementation digest: `895c53a469f19ad4491a0cfa178fd211bf67ceae9cf8fba59353cc69fe5b1297`

Preparation records base Git revision `40856c4...` plus the exact updated implementation
hash: this preview was generated while the patch was uncommitted. The patch commit
contains that implementation, tests, and preview. No existing plan was edited.
The old plan `e60aedd7...` remains at `study2-residual-v1-offline` and is intentionally
rejected by v1.1 with `Residual policy/code changed`; use commit `40856c4...` to reproduce
its old interpretation. Do not edit its policy hash to bypass that check.

| Quantity | v1 | v1.1 |
| --- | ---: | ---: |
| Original candidate/event combinations | 377 | 377 |
| Mechanically excluded | 137 | 137 |
| Retained resolved (28 present, 105 absent) | 133 | 133 |
| Retained uncertain | 107 | 107 |
| Deferred genuine disagreements | 5 | 5 |
| Deferred A without frozen source witness | 0 | 30 |
| Candidates requiring paid verification | 102 | 72 |
| Missing-provider candidate judgments scheduled | 119 | 79 |
| Verification batches | 21 | 14 |
| Coverage reviews | 9 | 9 |
| Total planned API calls | 30 | 23 |

The 30 deferred A candidates account for 40 avoided provider/candidate judgments.
All 240 retained candidate statuses, original votes and operation references are
unchanged. Four of the deferred candidates are the previously disqualified historical
A positives; all four also fail the new-vote path. There are 63 OpenAI and 16 Anthropic
candidate judgments: 11 OpenAI and 3 Anthropic verification batches, with five or six
items each. Nine existing full-text coverage requests retain their original obligations.
No already resolved candidate is added to fill a batch.

The complete frozen request preview is
[audits/study2-residual-v1.1/residual-request-plan.json](audits/study2-residual-v1.1/residual-request-plan.json).
The [request index](audits/study2-residual-v1.1/request-index.md) lists every request;
[real-source acceptance](audits/study2-residual-v1.1/real-source-offline-acceptance.json)
lists all deferred A candidates, exact source spans, and historical operation references.
World 001's M is preserved. World 003 keeps its two supported P locations separately
from strict O (absent); certification of its earliest P remains uncertain.

Completing this fixed plan requires **23 attempted calls**, with no automatic retry or
J3 adjudication. Failures or budget stops may end earlier, leaving unresolved evidence.
Using the unchanged **historical rate table**, not a current pricing quote, the planning
estimate is **$0.879602–$3.686602**. The low scenario uses JSON bytes/4 input and
256+350 output tokens per candidate batch, or 1,500 for coverage. The upper reservation
uses JSON bytes+2,048 input and 8,192 output tokens per call. No caching discounts;
these are planning estimates, not billing guarantees. The inherited global ceiling
is 30 calls/$25, but only the 23 frozen request slots are dispatchable.

The existing smoke safeguard remains at most **four lifetime calls**, included in
those 23, estimated $0.165908–$0.665510. Provider contracts/access/rates and a separate
paid authorization would still be required. This output has `live_enabled=false` and
no judge operations. This patch stops before any live execution.

## Offline inspection and tests

Use the existing environment; these commands do not install dependencies or download
models. Paths refer to the preserved local recovery inputs, not RunPod.

```bash
cd /Users/laurynwu/.codex/worktrees/study2-audit-fixes/exception-pilot
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export RESIDUAL_ACK_PLAN="$HOME/exception-v5-recovery/study2-residual-v1-1-offline"
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual inspect \
  --output "$RESIDUAL_ACK_PLAN" > /tmp/study2-residual-v1-1-inspection.json
/tmp/study2-qwen3-venv/bin/python -m json.tool /tmp/study2-residual-v1-1-inspection.json
```

To prepare a separate reproducible offline copy, choose a fresh path (the guard stops
if this example directory exists). This is not permission to retry any paid operation.

```bash
export RESIDUAL_ACK_COPY="$HOME/exception-v5-recovery/study2-residual-v1-1-offline-reproduction"
test ! -e "$RESIDUAL_ACK_COPY" && \
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual prepare \
  --review "$HOME/exception-v5-recovery/study2-v5-review-v2-1-live" \
  --salvage "$HOME/exception-v5-recovery/study2-v5-review-v2-1-salvage-v2-2" \
  --config configs/study2_residual_v1_1_offline.json \
  --output "$RESIDUAL_ACK_COPY" > /tmp/study2-residual-v1-1-reproduction.json
```

A later commit changes the recorded Git revision and therefore the artifact hash;
the candidate population, policy implementation hash and exact request payloads must
remain identical. Altered code, inputs or configuration require a new reviewed plan.

```bash
/tmp/study2-qwen3-venv/bin/python -m unittest discover \
  -s tests -p 'test_study2_residual*.py' -v
TOKENIZERS_PARALLELISM=false QWEN3_TOKENIZER_DIR=/tmp/study2-qwen3-tokenizer \
/tmp/study2-qwen3-venv/bin/python audits/study2-residual-v1.1/run_full_offline.py \
  > /tmp/study2-residual-v1-1-full-offline-tests.txt 2>&1
```

The completed full run passed **769 tests**, with zero failures, errors or skips in
675.575 seconds, including **45 residual tests** and **12 new acknowledgment tests**.
The full runner blocks network sockets. Tests use mock judges and synthetic fixtures;
existing tiny random-weight CPU architecture tests are not Qwen3-32B inference.
Exact suite results and preservation evidence are in the versioned audit directory.
The 12 new regressions include the four audit-selected historical excerpts, valid
recorded acknowledgments across A/B/C, wrong class/target, semantic-check failures,
missing and supported-negative votes, deferred request construction, and A→O gating.
These examples are audit-informed, not independent evidence of judge accuracy.

The literal witness recognizer is deliberately conservative: unrecognized prose may
remain uncertain even if a human could interpret it as acknowledgment. Paid provider
behavior and scientific event eligibility have not been newly established. No Qwen
responses, scientific prompts, thresholds, source hashes, or intervention checks changed.
