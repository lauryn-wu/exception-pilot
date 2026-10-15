# Study 2 v5 automated review v2.1

This is additive CPU-only **annotation**, not a new scientific experiment. It keeps
v5 originals, prompts, model settings, 2A, 2B, token boundaries, technical gates and
v1 review files unchanged. No human labeling is required by this detection pipeline.
Unresolved evidence stays uncertain. **Detection does not verify intervention edits**;
the existing independent edit-verification gate remains mandatory. Automating edits
requires a separate protocol amendment. No command here approves the remaining worlds.

The four-world pilot has already informed this redesign. It is exploratory development,
not held-out validation. Exact API model compatibility and semantic accuracy remain
**not tested** until explicitly authorized live calls have been inspected.

This focused follow-up adds contrastive clause localization and a separately versioned,
audit-informed balanced evaluation. The v2.0 codebook definitions, frozen v5 validator,
scientific code and original results are unchanged. Review code/prompt hashes and
`VERSION` changed: **prepare a fresh v2.1 review directory**. Old v2.0 plans, journals
and reports remain historical artifacts; this version refuses to resume them under
changed code. Do not edit or migrate their frozen files.

## What is frozen

`exception_study2_v5_review_v2/CODEBOOK.md` defines A/M/C/P/O/X with exclusions and
examples. P is observational and appears only in `observations-v2.json`; the scientific
export retains acknowledgment, erasure, conflict, override and miscopy.

Every v2 plan binds its own codebook, package code, schemas, family-specific prompt
sections, provider configuration, shared provider/journal code, scientific source hash,
code revision, all source row hashes, original prompt/table, and exact pre-answer text.
J1 uses OpenAI; J2 uses Anthropic; J3 is independently configured (OpenAI or Anthropic).
Different model families are enforced for J1/J2. Separate stateless calls do not prove
statistical independence: correlated semantic errors remain possible.

Canonical spans are Python Unicode character offsets. Repeated strings have different
IDs. Statements are presegmented before extraction; judges cannot invent quotations or
select arbitrary quote boundaries. Contrastive comma/dash clauses (`but`, `yet`,
`whereas`, `however`) can have separate nonoverlapping IDs. For example, `The recorded
class is C, but we should prefer inferred A.` yields `The recorded class is C` and
`but we should prefer inferred A.`. Every clause retains its exact enclosing statement
and full-text context. A and O still require independent semantic acceptance; a split
is not evidence of endorsement. This added clause pass leaves recognized quoted,
conditional, explicitly denied, interrogative, table and field-list statements intact.
Unsupported or ambiguous constructions can remain uncertain under the unchanged
A-before-O and unique-anchor checks. A generated table cell uses its generated column
header and exact target plate; field-list attribution records its preceding plate.
Facts outside the supported structural grammar remain unknown. Context attribution
and endorsement still require judges. The original source table never enters the
candidate stream as generated text. The target index is zero-based among vehicle data
rows: index 9 means the tenth vehicle, Markdown table line index 11.

Each available trajectory has two explicitly versioned journal phases:

1. `primary`: independent semantic extractor (J1), merged structural/semantic candidates,
   independent J1 and J2 candidate verification, conditional independent J3.
2. `audit`: independent full-text negative auditor (J2), without earlier votes or
   candidate lists; all its findings get independent J1/J2 and conditional J3.

Each phase has at most four distinct immutable calls. One global call/spend ledger
covers both phases. There are no retries or revisions. Both phases recheck duplicate
candidates. Disagreement between phases also invokes their existing J3 slots, using
the original evidence without votes and keeping the eight-call ceiling. Conflicting
phase judgments that remain after adjudication stay uncertain. A failed extractor/auditor
or unresolved earlier candidate prevents absence or first-occurrence certification.
A positive with no independently accepted earlier A cannot establish O. Later
correction references remain in the sidecar and never erase earlier events.

## Offline setup and inspection — no network or model required

Use Python 3.12 (standard library for the review CLI). No Torch installation, Qwen
weights, Hugging Face access, API keys or running GPU is required. From the repository:

```bash
git switch codex/study2-v5-judge-review-v2
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export TOKENIZERS_PARALLELISM=false

export SOURCE_V5="$HOME/exception-v5-recovery/study2-v5-staged-huwUCkqs/originals"
export REVIEW_V2_OFFLINE="$HOME/exception-v5-recovery/study2-v5-review-v2-1-offline"

python3.12 -m exception_study2_v5_review_v2 prepare \
  --source "$SOURCE_V5" --scope pilot \
  --output "$REVIEW_V2_OFFLINE" \
  --config configs/study2_v5_review_v2_offline.json

python3.12 -m exception_study2_v5_review_v2 inspect \
  --output "$REVIEW_V2_OFFLINE"

python3.12 -m exception_study2_v5_review_v2 evaluate --suite balanced-audit1 \
  --output "$HOME/exception-v5-recovery/study2-v5-review-v2-1-balanced-audit1.json"
```

Set `SOURCE_V5` to the actual recovered directory if different. On RunPod it can
point at the existing originals directory; no GPU is needed. Output must be separate
from and neither contain nor be contained by the source. Prepare permits identical
resumption but refuses changed source/policy. Do not reuse a v1 directory. Never edit
a frozen policy or an old scientific plan in place.

`inspect` is read-only: shows structural counts, unresolved status, row binding and
limits. Candidate counts are not event prevalence. A default `run` without `--live`
only plans requests, attempts zero calls and stops `OFFLINE`. An incomplete review
cannot export. Keep all private inputs/outputs outside the repository.

## Offline tests

```bash
python3.12 -m unittest discover -s tests -p 'test_study2_v5_review_v2*.py' -v
```

For the complete existing suite, use the project's already pinned test environment
and an already available pinned tokenizer. Do not download a tokenizer automatically:

```bash
export QWEN3_TOKENIZER_DIR=/absolute/path/to/existing/pinned/tokenizer
python audits/study2-v5-review-v2-followup/run_full_offline.py
```

The full runner blocks socket connections and writes its machine-readable result to
`/tmp/study2-v5-review-v2-followup-full-offline-results.json`. Historical CPU random-model tests
remain part of the full suite; none run pretrained Qwen inference. New tests also
block construction of `LocalBackend`.

The preserved historical v2.0 suite has 192 cases, 64 authored templates, 96 cases per split. Each
three-case template family uses distinct context/layout challenges, not independent
random samples. Do not interpret 192 as 192 IID observations. Development and held-out
wording differ. The frozen split/hash and first evaluation are recorded in the original audit.
`evaluate --suite historical` (the backward-compatible default) replays that original
sentence representation; it is not an evaluation of the new clause localizer. Its
hash and complete evaluation output are regression-tested against the prior artifacts.

The separate `controlled-v2.1-balanced-audit1` suite uses the current production
localizer: **3,600 variants = 20 authored scenarios × 6 ordered recorded/inferred
pairs × 3 target identifiers × 10 data-row positions**. Each recorded class and
inferred class appears 1,200 times, each ordered pair 600 times, each target 1,200
times, and each row position 360 times. Every scenario contains every combination.
Gold clause spans are authored before localization; misalignment fails instead of
propagating a parent label to every new fragment. Its seed, hash, results and provenance
are saved separately in `audits/study2-v5-review-v2-followup/`.

These revised examples explicitly respond to this audit. They are **not independent
validation, not held-out data, and not 3,600 independent observations**. Counterbalanced
variants share 20 scenarios. They test all six event types, compound overrides and
conflict-only/rejected alternatives, negation, hypotheses, quotes, other plates/fields,
correct predictions, corrections and ordering. Neither suite measures paid-model
semantic performance.

The report separates structural extraction recall, **oracle-wired** reconciliation
precision/recall/F1/confusion/abstention, and production behavior with no judges
(100% abstention on available originals). Oracle correctness does **not** establish
real semantic judge accuracy. Actual model-based ≥95% precision/recall targets are
unverified. Historical held-out structural C/O recall falls below 95%; these observed results
were retained without tuning the extractor against the held-out wording.

Follow-up acceptance: **685 full offline tests passed** (656 prior + 29 new),
0 failures/errors/skips, 391.799 seconds. The focused follow-up run passed
29/29 in 17.492 seconds. The new fixture report has 4,320 exact accepted spans and
540 ordered A→O pairs with supplied oracle judgments. These counts do not certify
real semantic accuracy. Exact logs, provenance and preservation hashes are in
`audits/study2-v5-review-v2-followup/`.

## Configure a later authorized live run

Do this only after separately authorizing paid calls. No calls were made during
implementation. Copy the offline config to a **private** path outside Git, for example:

```bash
cp configs/study2_v5_review_v2_offline.json \
  "$HOME/exception-v5-recovery/review-v2-live.json"
```

Edit that private JSON before preparing a fresh live directory:

- Set exact versioned model IDs for J1/J2/J3; do not use an unverified alias or silently
  substitute a model. Confirm account access and documented structured-output support.
- Enter the applicable input, cached-input, output and cache-write USD per million rates.
  Reasoning tokens are included in billed output; do not add them twice.
- Confirm compatible settings and output cap for each model. Default output cap is
  32,768 because candidate-by-candidate check arrays can be large; use only a cap
  actually supported by the chosen model. Truncation is terminal uncertain, not retried.
- Set `contract_verified: true`, `access_verified: true`, and `live_enabled: true`
  only after checking them. These are operator attestations, not an API smoke result.
- Keep finite `max_calls`, `max_estimated_usd`, `timeout_seconds`, and `wall_seconds`.
  Defaults are 128 calls, $25 estimated budget, 120 seconds/request and 7,200 seconds
  per invocation. Invocation flags may only tighten the frozen budgets.

The non-null wire schema uses required strings, objects, arrays and string enums,
with `additionalProperties: false`. `NONE` means no applicable prior acknowledgment;
normalization turns it into internal null. A non-present export has no invented span
or quote. Both provider requests use the existing transport: OpenAI Responses
`text.format`, Anthropic Messages `output_config.format`. Local strict validation
also rejects missing fields, unknown IDs, contradictory checks, refusals, truncation,
model identity mismatches and malformed responses. JSON validity is not semantics.

See the [OpenAI structured-output contract](https://developers.openai.com/api/docs/guides/structured-outputs)
and [Anthropic structured-output contract](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).
The current Anthropic documentation lists nulls among supported basic types; that
is not evidence that the old nullable-enum schema or any selected model works.
V2 removes that wire combination. **Provider acceptance remains untested.**

Supply `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` securely as environment variables.
Do not put keys in JSON, shell transcripts, source files or Git. Paid execution
requires a verified `LIVE_LOCAL` scientific source and both providers configured.

## Exact optional four-call smoke procedure — PAID, do not run automatically

The fresh live policy must already have been configured as above. These commands
are intentionally separate from offline inspection and use a fresh output directory:

```bash
export REVIEW_V2_LIVE="$HOME/exception-v5-recovery/study2-v5-review-v2-1-live"
export REVIEW_V2_CONFIG="$HOME/exception-v5-recovery/review-v2-live.json"

python3.12 -m exception_study2_v5_review_v2 prepare \
  --source "$SOURCE_V5" --scope pilot \
  --output "$REVIEW_V2_LIVE" --config "$REVIEW_V2_CONFIG"

python3.12 -m exception_study2_v5_review_v2 smoke \
  --output "$REVIEW_V2_LIVE" \
  --case-id staged-v5-001/v1/original/visible \
  --live --max-calls 4 --wall-seconds 600

python3.12 -m exception_study2_v5_review_v2 inspect \
  --output "$REVIEW_V2_LIVE"
```

**Stop here and inspect raw responses and parsed validity** under `judge-operations/`,
plus `cases/` and `reports/`. `--case-id` selects exactly that available visible task
from the frozen plan; unknown, direct or unavailable tasks fail before dispatch.
Omit it to select the first available trajectory on the first invocation. The choice
is sealed in `smoke-selection-v2.json`; later invocations with no ID reuse that choice,
and attempts to change it fail. The smoke visits only this one trajectory:
extractor, primary J1, primary J2, full-text auditor; it defers J3 and audit-finding
verification. The limit is **at most four calls**, fewer after a budget stop or if
there are no candidates. It is not a completed annotation or quality benchmark.
Rerunning smoke reuses these slots and never gives four extra samples.

HTTP errors, model identity mismatches, refusals, incomplete/ambiguous calls or
schema failures are terminal ledger entries. Do not delete them, edit journals,
change frozen models, or resend automatically. Diagnose offline; a corrected policy
requires a separately authorized, newly versioned plan/directory preserving the failure.

Only after separate approval of the smoke results, a later full pilot execution is:

```bash
python3.12 -m exception_study2_v5_review_v2 run \
  --output "$REVIEW_V2_LIVE" --live --max-calls 128 --wall-seconds 7200

python3.12 -m exception_study2_v5_review_v2 inspect --output "$REVIEW_V2_LIVE"
python3.12 -m exception_study2_v5_review_v2 export --output "$REVIEW_V2_LIVE"
```

Run can resume on the same immutable plan; global call/spend limits still include
previous invocations and smoke calls. Wall time resets per explicitly requested
invocation; call/spend ceilings do not. A POSIX main-thread alarm bounds live requests
by remaining wall time and clamps their timeout. The deadline can leave an ambiguous
terminal failure; it does not trigger retries. Do not run live from worker threads.

Export rederives decisions from saved journals, sends zero requests, and passes the
unchanged `read_manifest` and `validate_decisions`. It requires a terminal result for
all visible trajectories, including uncertain and invalid cases. Unavailable originals
are invalid. Observed invalid-answer/truncated originals can still contain events;
we never infer unobserved continuation. V2 does not exclude inconvenient trajectories.
`excluded` remains supported by the existing scientific/manual path and downstream
eligibility; this automated detector introduces no new exclusion rule.

The compatibility manifest and P/provenance sidecar are separately sealed. Semantic
checks are explicit fallible judge assertions plus mechanical checks and conservative
reconciliation. They do not certify truth or intervention eligibility. **Stop after
export.** No confirmation, remaining-world collection, measurements or interventions
are started by this module.

## Pilot request and cost estimate

For 16 available trajectories: 64 initial/extraction/audit calls, normally up to 96
when audit findings need verification, at most 128 including both conditional J3
phases. Smoke calls count toward these totals, not in addition. Fewer calls are possible
with empty candidate sets, unavailable originals or budget stops. No retry allowance.

Historical v2.0 read-only preparation of this recovered pilot yielded 368 structural candidates and
2,138,958 serialized request bytes for the initial 64-call schedule, before semantic
extractor additions. Clause localization may change these counts; use fresh `inspect`
output for v2.1. At an assumed 3 bytes/token that is about 0.71M input tokens.
Allow roughly **0.7–2.0M input and 0.15–0.8M output tokens** across 64–128 calls;
actual tokenizer, schema overhead, reasoning tokens, candidate additions and verbosity
can change this substantially. Assuming **$1–$3/M input and $5–$15/M output**, that
is roughly **$1.45–$18**, or a practical **$2–$20 planning range**. These are explicit
rate assumptions, not current quotes or a guaranteed cap. A four-call smoke is roughly
$0.10–$1 under those same typical-length assumptions; all outputs hitting the 32K cap
could cost more. Set verified rates before execution.

The journal reserves conservative input-byte estimates plus maximum output tokens
before each call, then accounts for returned provider usage; missing usage retains
its reservation. This is an estimated-spend guard, not a provider billing guarantee.
The $25 default may stop a run early. Inspect before authorizing any new plan/budget.
