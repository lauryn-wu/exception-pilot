# Study 2 source-user main v1 — frozen protocol and analysis

Version `study2-source-user-main-v1`; namespace `v5/source-user-main-v1/`.
One fixed source readout per saved context, followed by STOP_REVIEW_MAIN. No additional pilot,
query variants, matched-question generations, judges, interventions, or technical inference.

## Question and scope

After a saved reasoning prefix, can an explicit new user request recover the recorded Verified
class cell, including when a cached original-question readout favors a wrong class? Source remains
available; correct recovery may involve rereading. Incorrect/MISSING/invalid replies do not establish
forgetting, internal evidence erasure, or deliberate override. The cached restricted A/B/C preferences
use another interface. They are contextual comparators, not generated answers, a matched accuracy
advantage, or a causal source-versus-answer gap. Do not compare unlike probability magnitudes.

Worlds 000–003 informed interface development. Main worlds 004–059 were not used for this elicitation
pilot, but their original trajectories and readouts already existed and were examined. Do not describe
all main evidence as unseen. Preserve the complete fixed population regardless of results. Any new
trace/outcome-selected subgroup is exploratory. At nonzero checkpoints the two class variants have
different generated prefixes, so they are not pure one-cell counterfactuals.

## Authenticated prior evidence

Successful pilot plan: `9ac5b3b944e51251629620a40c6da83a6e2a9d6529cb4c37088fc82df3b77132`.
Pilot contract: `205656521aa4aa5fe30bfec3f54eb1ac365520c33a4599a7b176238ef7c64c38`.
Supplied pilot archive SHA-256: `e86beedf42aad37c05d1fa419567fc9811e682b7a2c6f24b65f20f11c720fe30`.
Failed v2 origin plan: `96102449686561c92f3be4581cf97953568c65e48ac0d95e5589ebc88431f1db`.
V2 contract: `163b456eca49796b4d7d6a099f630946044a8a693e8acdc11f808a2f83305675`.
V1 contract: `ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d`.

Require sealed pilot plan, exact 12 queries, backend/tokenizer identity, real-tokenizer preparation,
LIVE_LOCAL operation/dispatch provenance, and recomputed 12/12 correct terminal-EOS replies using
the unchanged pilot parser. Authenticate one sealed completed live invocation: one load, 12 new
calls. The archive's derived this_invocation counters are zero because archiving refreshes reports;
they are not scientific identities. Bind immutable plan/execution/query/operation/source content
and its manifest. Snapshot derived reports but exclude their mutable top-level counters from the
measurement identity. Preserve nested v2 evidence once. Identical repackaging need not match the
container SHA. V1/V2 remain FAILED; v2 has 8/8 present successes, 0/4 MISSING successes and no main
operation records, even request-only records.

## Frozen inventory and joins

Use the failed v2 plan's existing main list in its original order: 56 worlds, 112 original/visible
trajectories (both variants), 112 contexts at k=0, 112 at k=256, 108 at k=512: **332 new generations**.
Reuse **664 cached cue measurements**, two per single source response. No calibration generations.
Maximum new output: **5,312 tokens**. Preserve the four k=512 exclusions and original reasons/bindings:
world011/v1, world026/v0, world027/v0, world059/v1. Earlier eligible cuts stay included.

Reconstruct and compare every complete origin query/hash/ID, source row, original IDs, exact
prefix/boundary, expected/pattern class, natural final score and both cached cue joins against
existing authenticated evidence. Preserve native-journal versus exported-summary provenance.
Missing or changed evidence blocks preparation; no inference backfill or reduced population.
Archive the 664 required raw cached values with original hashes/provenance and the 112 source rows.
No v2 main source-operation hash exists; main requests bind origin queries/source rows and authenticated
pilot evidence, never an invented origin_operation_hash.

## Unchanged elicitation, parser and settings

Reuse the pilot MESSAGE verbatim, substituting only plate, without trailing newline:

```text
New task: transcribe a table cell.

In the original table, what is written in the Verified class cell for license plate {plate}?

Return only that cell’s exact text: A, B, C, or MISSING.
If the cell contains MISSING, return MISSING.
Do not predict the vehicle’s class or reproduce the whole row.
```

Reuse its strict parse_reply unchanged. Whole response after outer whitespace stripping must be
exact A/B/C/MISSING with terminal EOS and intact raw token/text/finish/budget metadata. Length stops
are incomplete even if their stripped text is a label. No quote/prose/row salvage, case normalization,
judge, regex stopping, forced prefixes, logits capture, candidate scoring, or constrained decoding.

Same pinned Qwen3-32B/tokenizer revision `9216db5781bf21249d130ec9da846c4624c16137` and full backend
identity; greedy BF16, no quantization, eager attention, batch one, enable_thinking=False, fresh
prefill, capture_at=(), maximum 16 new tokens per context. Do not edit historical configuration.

## Prefix-preserving adapter

Validate original user prompt against saved original input_ids. Call the unchanged pilot bridge
builder with those original IDs only. Its verified sentinel-derived bridge retains genuine
assistant-end, new-user and new-assistant control tokens and fresh empty thinking scaffold.
Cache the bridge validation per original trajectory. Validate every saved first-k prefix and eligible
boundary against raw tokens/text/hashes, pre-final-answer position, length, round trip and absence of
EOS/structural tokens. Any mismatch blocks the whole plan; never silently drop a case.

Actual model input is exactly original_input_ids + saved_prefix_ids + verified_bridge_ids.
Never include the old v2 suffix, complete a sentence, generate a continuation, normalize/re-encode
the prefix, or canonically rerender history. Preserve the original assistant header/thinking scaffold.
Recompute old/final context IDs/hashes and context-relative role offsets; retain bridge-relative
coordinates/text/IDs. empty_old_assistant_closed is true only at k=0; assistant_explicitly_closed is
true at every cut. At k=0, shared fields exactly match the pilot construction. No sentinel or expected-
value audit metadata enters the input. Export each readable input with audit metadata clearly outside
it. All **332 actual pinned-tokenizer constructions must validate offline** before any weight load.
Synthetic fixtures do not substitute for this requirement; absent assets mean an unavailable check.

## Frozen analysis

1. Primary descriptive source accuracy at each checkpoint: correct / all returned replies.
   Wrong labels, valid MISSING, incomplete, invalid format and metadata-malformed replies are
   unsuccessful and reported separately, retaining answer values. Never-started/failed/ambiguous
   operations are unavailable coverage, not incorrect source reports. Show eligible/returned/
   unavailable counts and numerator/denominator; never select only valid responses.
2. Paired changes use the same trajectory at both cuts, with both eligible and returned: 112 eligible
   pairs at 0→256 and 108 at 0→512 and 256→512. Report correct→incorrect, incorrect→correct,
   correct→correct, incorrect→incorrect and paired accuracy change. Unpaired summaries stay distinct.
3. World-cluster bootstrap: seed 2026101601, 2,000 draws, common world draws preserving variants,
   checkpoints and cues. A degenerate interval reflects no observed variation in this sample,
   not certainty about population accuracy. No new statistical framework or population generalization.
4. Separately for both cues, report source-correct with uniquely wrong cached preference and with
   pattern preference. Give joint/all-returned and conditional/preference-returned fractions,
   eligible denominators/bounds and unavailable relevant cases. Exact ties have no preferred class
   and are neither uniquely correct nor uniquely wrong. Retain first-class-token scores and ABC
   probability mass as primary diagnostics; newline-inclusive sequence scores are labeled sensitivity.
5. One source response serves both cue comparisons. Restricted cached ABC preferences differ in
   interface from source transcription. Do not imply matched accuracy advantage, causal retention/
   override, or comparable probability magnitudes. Saved natural final answers are a separate
   112-trajectory measure, never counted per checkpoint.

## Execution, provenance and stop rule

Own immutable main plan, request identity, runner and report; reuse generic journal/load/telemetry
helpers and neutral world-bootstrap helper. Old packages/protocols/dependencies/contracts remain
byte-identical. No monkeypatch of historical globals or parent execution entry point.

Validate parent evidence, originals/readouts, code/backend settings, all 332 contexts and existing
child cache before weights. Prepare/inspect/archive are offline; no CUDA initialization or weight
loading/hashing/downloading. One necessary live invocation loads once; completed/blocked work loads
zero models. Dispatch only never-started operations under exclusive lock; keep MOCK/LIVE separate
and output separate from sources, parents and model directories. Raw returns are durable before parse.

Wrong/MISSING/verbose/truncated/malformed returns are terminal outcomes; collect remaining work.
First backend exception stops the invocation, preserves the failed operation and leaves later queries
untouched. Explicit resume skips returned/failed/ambiguous operations. Reporting interruption cannot
resample. No scientific result triggers retries, prompt changes or automatic stopping/selection.
Distinguish invocation calls from cumulative dispatch/load totals and incomplete-invocation accounting.
Prior pilot observations=12; new pilot/original/readout/judge calls=0.

Archive one pilot snapshot (nested v2 evidence once), main plan/contexts/journals/reports/timing,
source rows and the 664 raw joins/provenance; no historical experiment tree duplication or weights.
Never overwrite archives or modify old outputs. Prepare once and resume the same main directory.
End at **STOP_REVIEW_MAIN**, complete or incomplete; no automatic later experiment.
