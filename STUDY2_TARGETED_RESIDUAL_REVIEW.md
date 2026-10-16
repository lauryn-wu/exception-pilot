# Study 2 targeted residual review v1

This additive procedure reuses paid v2.1 judgments through the separately saved v2.2
salvage. It does not rerun the v2.2 extraction pipeline, alter original Qwen responses,
change scientific definitions, or approve interventions. Its implementation and
source-witness rules are informed by this audit; the resulting hybrid review is not
independent confirmation. No paid calls are made by default.

Only **M (evidence erasure)** and **O (explicit evidence overriding after accepted A)**
are primary failure families. A, C and X remain supporting annotations. P is written
to the observations sidecar only. A contradictory inferred class alone does not make O.
The existing v5 annotation validator and prior-A/source-order checks remain unchanged.

## Exact frozen scope

The saved inputs contain 377 distinct candidate/event combinations. v2.1 had 122
resolved and 255 unresolved; the v2.2 salvage recovered 149 resolved and 228 unresolved.
Mechanical filtering excludes 137 (12 previously resolved absent; 125 unresolved),
leaving 240 candidates: initially 137 resolved and 103 unresolved.

Before reuse, historical A positives additionally need an explicit, source-bound
recorded-value witness. Four previously accepted candidates lack sufficiently explicit
recorded-value evidence; they remain archived, but need new semantic verification.
They are not declared false and the old salvage/manifest is not edited. See the exact
IDs and text in the audit. The retained population is therefore:

- **133 resolved candidates reused**, with original operation references.
- **107 unresolved candidates**, of which five have genuine cross-provider or
  within-provider disagreement. Those five remain uncertain and receive no new call
  under this initial protocol.
- **102 candidates needing new judgments:** 85 need only one missing provider;
  17 need both. There are 92 OpenAI and 27 Anthropic missing decisions (119 total).
- **21 verification requests**, each containing five or six items, plus **nine full-text
  coverage reviews**: **30 requests total**, zero J3 calls.

Residual items are pooled by provider and ordered by original case order, source
span and ID. This avoids padding short per-case batches with already resolved items.
Each request supplies complete separate source packets for every included trajectory.
Wire candidate IDs are namespaced by task; historical/scientific IDs and spans are
unchanged. All requests, schemas, source references, configuration and prior evidence
are frozen before execution. A source/provider cohort smaller than four is rejected
rather than padded; another explicitly specified protocol would be needed for that case.

## Reuse and disagreement policy

Every saved raw response is reparsed and bound to its original immutable request,
source, policy, returned model and journal slot. The v2.2 salvage must reproduce.
Each reused vote passes the unchanged semantic checks, deterministic vetoes and exact
source alignment. Old A positives lacking a literal recorded-value witness become
unresolved for this new plan; predictions that merely match the record cannot supply A.
Full source text and all prior decisions, including disqualified/minority opinions,
remain in `prior-evidence.json` and the historical artifacts.

Each provider supplies one position, not one vote per call. OpenAI's predesignated J1
position takes precedence; historical J3 is used only when J1 has no conclusive
revalidated position. This rule is independent of the verdict. Repeated phases are
not votes in a majority: contradictory valid positions within a provider remain
uncertain. OpenAI/Anthropic disagreement also remains uncertain. Valid old support is
never redispatched or overwritten by a fresh opinion. Missing/invalid support can be
filled by one new request to that provider. There is **no automatic J3 or tie breaker**.
Further adjudication requires another separately approved, explicit protocol.

The nine coverage requests provide new evidence for failed obligations. Old flags
remain in the immutable prior evidence and plan. Full-text review and per-event
coverage are separate from event detection; complete/no-event is valid. Incomplete,
failed or inconsistent coverage cannot establish absence. Newly discovered candidates
outside the frozen population are logged and leave the affected event uncertain;
this run does not silently expand its candidate population or dispatch more requests.

## Saved plan and offline inspection

The complete private frozen plan is:

```
~/exception-v5-recovery/study2-residual-v1-offline/
```

- `residual-plan.json`: exact population, all decisions/provenance, source hashes,
  request list, costs and four fixed smoke slots.
- `prior-evidence.json`: complete original salvage evidence, including all old votes.
- `residual-policy.json`: frozen prompts, schemas, judge configuration and code hashes.
- `request-preview.json`: every exact wire payload, candidate reference, necessity
  explanation, source binding and cost estimate.

A copy of the complete request preview is committed as
`audits/study2-residual-v1/residual-request-plan.json`. The original paid response bodies
are not copied into Git. `AUDIT.md` records accounting, preservation and acceptance.

Exact commands on this Mac using the existing offline environment:

```bash
cd /Users/laurynwu/.codex/worktrees/study2-audit-fixes/exception-pilot
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export RESIDUAL="$HOME/exception-v5-recovery/study2-residual-v1-offline"
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual inspect \
  --output "$RESIDUAL" > /tmp/study2-residual-inspection.json
/tmp/study2-qwen3-venv/bin/python -m json.tool /tmp/study2-residual-inspection.json
```

To reproduce preparation with the same frozen inputs (zero API calls):

```bash
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual prepare \
  --review "$HOME/exception-v5-recovery/study2-v5-review-v2-1-live" \
  --salvage "$HOME/exception-v5-recovery/study2-v5-review-v2-1-salvage-v2-2" \
  --config configs/study2_residual_v1_offline.json \
  --output "$RESIDUAL"
```

The existing plan is immutable. Changed code/configuration/evidence requires a new
output directory. Inspection never sends requests or creates new judge operations.
Calling `smoke` or `run` without `--live` also sends zero requests.

## Estimated cost and separately authorized smoke

For completion of this fixed plan, the minimum and maximum are both **30 attempted
calls**; there are no automatic retries or conditional adjudication calls. Budget
stops or operator interruption can stop earlier without completing it. Missing items
in a returned batch stay uncertain instead of generating extra calls.

Using the saved historical rate table (not a current pricing quote):

| Model | Input / million | Output / million |
| --- | ---: | ---: |
| `gpt-4.1-2025-04-14` | $2 | $8 |
| `claude-sonnet-5-5` | $2 | $10 |

Estimated full-plan spend is **$1.21–$4.99**. The lower scenario uses request bytes/4
for input tokens and 256+350 tokens per candidate batch (1,500 for coverage). The upper
scenario uses the existing journal's conservative request-bytes+2,048 input reservation
and the full **8,192 output-token cap** per request. No caching discounts are assumed.
Neither scenario is a provider billing guarantee. Rates, contracts and access must be
rechecked before a paid run. The saved offline policy has a 30-call ceiling and $25
estimated-spend ceiling; the exact frozen request allowlist also prevents extra slots.

The fixed smoke subset has **at most four lifetime calls**, estimated **$0.17–$0.69**.
It includes both providers' semantic verification and a coverage review. Repeated
smoke invocations reuse the same four slots; completed, failed and ambiguously
interrupted calls are not resent. Smoke requests are part of the 30, not four extras.
Later separately authorized full execution reuses them, leaving at most 26 new calls.
After any paid attempt, resume the same live directory. Creating a new directory is
not an authorized retry of completed or interrupted residual requests.

**No live execution is authorized by preparing this patch.** After separate approval,
prepare a new live output using a separately reviewed configuration. It must preserve
exact J1/J2 model identities and the fixed semantics, and explicitly attest verified
provider contracts/access/rates. The offline configuration has `live_enabled: false`
and `contract_verified: false`; do not edit the already frozen offline plan. J3 remains
an unused legacy configuration entry and can never be dispatched by this implementation.
Do not store API keys in configuration or Git; the shared provider reads environment keys.

The following commands are **for a later, separately authorized smoke only**. Set
`APPROVED_RESIDUAL_CONFIG` to that reviewed private configuration first:

```bash
export RESIDUAL_LIVE="$HOME/exception-v5-recovery/study2-residual-v1-live-smoke"
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual prepare \
  --review "$HOME/exception-v5-recovery/study2-v5-review-v2-1-live" \
  --salvage "$HOME/exception-v5-recovery/study2-v5-review-v2-1-salvage-v2-2" \
  --config "$APPROVED_RESIDUAL_CONFIG" --output "$RESIDUAL_LIVE"
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual inspect --output "$RESIDUAL_LIVE"
export RESIDUAL_PLAN_HASH=$(/tmp/study2-qwen3-venv/bin/python -c \
  'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["RESIDUAL_LIVE"])/"residual-plan.json").read_text())["artifact_hash"])')
/tmp/study2-qwen3-venv/bin/python -m exception_study2_v5_residual smoke \
  --output "$RESIDUAL_LIVE" --live --authorize-paid-smoke "$RESIDUAL_PLAN_HASH" \
  --max-calls 4
# STOP. Inspect the saved responses before authorizing anything further.
```

There is no automatic transition from smoke to full review. Full review has a distinct
`--authorize-paid-review PLAN_HASH` gate. Export refuses pending/ambiguous requests and
validates `annotation-manifest-v5-residual.json` with the unchanged scientific validator.
P stays in `residual-observations.json`. This does not verify intervention semantics or
launch Study 2A/2B. Manual review remains available through the unchanged v5 workflow;
it must produce its own explicit, separately provenance-tracked decisions.

## Offline acceptance and limitations

- Targeted residual regressions: **33 passed**, zero failures/errors/skips, **202.617 seconds**.
- Full offline suite: **757 passed**, zero failures/errors/skips, **765.387 seconds**, including all 724 pre-existing tests.
- Network blocked; zero paid judge calls, pretrained Qwen inference calls or GPU inference calls.

Reproduce with the existing environment and cached tokenizer (no downloads):

```bash
/tmp/study2-qwen3-venv/bin/python -m unittest discover -s tests -p 'test_study2_residual.py' -v
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
QWEN3_TOKENIZER_DIR=/tmp/study2-qwen3-tokenizer \
/tmp/study2-qwen3-venv/bin/python audits/study2-residual-v1/run_full_offline.py
```

Tests cover historical reuse, only-needed provider requests, namespaced multi-case
batches, source binding, disagreement, coverage overlays/discoveries, false A prevention,
World 001 M, World 003 P versus O, immutable histories, no retries, bounded smoke,
resume and v5 manifest compatibility. No paid judging, pretrained Qwen inference,
model downloads, RunPod operation or intervention execution occurs.

Fresh provider acceptance of the residual multi-case requests and their semantic
accuracy remain **NOT TESTED**. A smoke can assess technical behavior, not independently
validate semantic accuracy. Source-witness matching is intentionally conservative;
unrecognized recorded prose can require review. The five genuine disagreements and
any newly discovered candidates require separately specified follow-up, not more votes
under this plan. All outcomes, including failed calls and unresolved decisions, persist.
