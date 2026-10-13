# Study 2 v3: checkpoint-local validation and secondary event readouts

New runs only. V1 remains reproducible at 1be7551; v2 at 4baf414.
Do not open, migrate, overwrite or reinterpret their plans/results with v3.
Historical protocols, configs and previews remain unchanged. V3 retains v2's
scientific design except the explicitly versioned eligibility fix and secondary
event analysis below. Real-model replay fidelity and behavioral replication are
PENDING. Mock results are software fixtures only.

## Shared collection and fixed primary

12 selection worlds (seed 2026101421, I plates), 24 fresh confirmation worlds
(seed 2026101422, J plates); two recorded values crossed with direct/visible
instructions: 48 + 96 = 144 uninterrupted originals. Same target-last inventory,
role/climate balance, one-shot greedy generation, 512-token cap, plain visible
assistant interface, model/template identity and calibration gate as v2.
Selection needs >=20 correct direct answers, >=3 matched direct-correct/visible-
pattern errors over >=2 worlds before confirmation. Freeze model, precision,
template, tolerances and config before selection; do not relax on outcomes.

Fixed cuts stay 0/32/64/128. Primary is still gold-versus-pattern log-odds at
64 minus 0, with BOTH recorded-value variants required per world. Each cut is
measured only when that cut is eligible and its full-vocabulary distribution and
exact-suffix replay pass. Failure at 128 does not discard valid 0/64 measurements.
Failure at either 0 or 64 removes that trajectory's primary contrast and hence
its world's primary estimate unless both variants remain available. Failed and
unavailable cuts remain recorded. Row `replay_passed` means all eligible cuts
passed; `any_checkpoint_failed` is its inverse, not a global measurement gate.
Analysis checks each cut's eligible/passed flags even if a stray readout exists.

Primary cue remains newline ANSWER:, with optional newline Final answer: at
0/64. Score the complete literal candidates ` A\n`, ` B\n`, ` C\n` separately,
without length normalization. No probe is supplied to the original trajectory
or any natural continuation. All numerical tolerances remain exactly v2's.

## Secondary event-checkpoints-v1

Freeze `event_checkpoints` as a unique subset of `before_statement`,
`after_statement`, `before_answer` in the new config; default all three, []
disables this extension. No dense sweep. Review EVERY visible output regardless
of correct/wrong/invalid final answer. Reuse v2's first explicit false-missingness
statement annotation and exact token boundary catalog. Freeze the edit manifest
and then `event-plan.json` BEFORE event measurements. This needs no 2A results.
Negative annotations are retained; before-answer remains eligible for them.
Selection informed by fixed 2A stays discovery only; confirmation requires the
predeclared first-statement rule and no-2A-selection attestation as in v2.

Boundaries are generated-token counts on the saved ORIGINAL response:

* Before statement: latest stable exact-roundtrip token boundary at/before its
  annotated start, permitting only intervening whitespace. Token 0 is allowed.
  If a token combines earlier non-whitespace text with the statement, exclude;
  never shift the cut to a convenient earlier sentence.
* After statement: existing 2B boundary rule, first stable exact-roundtrip token
  boundary at/after statement end, allowing only trailing whitespace and no
  subsequent non-whitespace reasoning. Record unavailable when absent.
* Before answer: same before-boundary rule at the FIRST literal `ANSWER:` marker,
  consistent with fixed-checkpoint eligibility. Marker recognition does not
  require a valid final answer. No marker means unavailable; never search for a
  later valid answer or choose a boundary by its probability shift.

Statements after the first marker are ineligible. Internal special tokens,
partial text boundaries and roundtrip failures are unavailable, with reasons.
The frozen manifest lists every configured event for every visible trajectory.

Post-generation locations have no previously captured reference logits. Therefore
generate ONE fresh uninterrupted reference per trajectory with any available
event, capturing all unique event cuts. Require its whole token sequence, stop
status and finish reason to match the saved original. Replay each unique cut
with budget 512-k, compare full-vocabulary distributions under the unchanged
tolerances, and require exact suffix/finish equality. Each passing cut receives
one disposable primary-cue readout. Failed cuts receive none. Identical event
cuts share their reference/replay/readout within the event analysis; fixed and
2B validation calls remain separate. Future tokens never enter any probe prefix.

Report event coverage/reasons, checkpoint means, and after-minus-before-statement
as SECONDARY, requiring both variants per world. Preserve failed checks and
trajectory failure flags. This does not replace the fixed primary or identify
internal beliefs; event eligibility and edits condition on selected statements.

## 2B reporting revision: intervention-coverage-v2

Four unchanged v2 arms: unchanged, availability repair, meaning-preserving
control, and explicit-value repair. Fresh natural suffixes get the same 512-k
budget; full edited prefixes are recomputed. The separate secondary readout
does not enter generation. Each case gets fresh reference/replay checks, and
the unchanged arm must also pass. Invalid correctness remains UNKNOWN.

Remove the misleading `invalid_or_replay_failed` counter and publish its
deprecation in the summary. `coverage` reports replay failures separately from
pre-freeze exclusions and post-freeze tokenization failures, with reasons and
denominators. Per arm, planned is the frozen case count; attempted means a
journaled generation, including error/started; returned includes later replay
failures. valid/invalid are syntactic final-answer categories independent of
replay. Truncation is a subtype of invalidity for assessed returns. Partial-run
returns lacking completed arm assessment are `unassessed`; truncation may also
overlap that category. valid+invalid+unassessed=returned;
returned+missing=planned; returned<=attempted<=planned.

Replay failure makes correctness unavailable even for syntactically valid
returns. All contrast-specific complete-world estimates and full-frozen-plan
unknown-in-[0,1] bounds remain unchanged. No invalid answer is recoded as wrong.
Before-freeze exclusions are not members of the conditional intervention cohort.

## Workload and execution

See CONTINUATION_V3_RUNBOOK.md for exact commands and operation counts.
No model, tokenizer download, paid call or GPU launch is implicit in any command.
Use existing local files and an installed compatible environment for opt-in live
work. All four earlier pending studies are outside this patch.
