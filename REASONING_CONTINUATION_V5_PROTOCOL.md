# Study 2 v5: evidence erasure, evidence overriding and conditional text interventions

Protocol `study2-evidence-interventions-v5`, design contract `staged-60-v1`. All v3/v4 and Qwen length/expanded-screen
observations are development evidence, never v5 confirmation. Code, configurations,
plans and all execution stages are separately versioned. No retrospective prompt or
threshold tuning after v5 outcomes or interventions. Mock fixtures are not evidence.

## Questions and claims

Behavioral: matched explanation instructions reduce accuracy relative to direct
answers under the original question. Secondary: explicit lookup framing attenuates
that penalty (interaction). Trajectory: verified-minus-pattern conditional log odds
change between initial and pre-answer prefixes. Intervention: value-blind repair
changes subsequent accuracy relative to an error-preserving paraphrase.

These are three different claims. Readouts are relative complete-sequence scores,
not calibrated probabilities or latent beliefs. Controlled prefix edits do not
restore an internal state or prove that the original statement caused an error.
Semantic before/after changes are descriptive, not sentence-level causal effects.

## Frozen originals

**One prespecified 60-world experiment, 480 originals.** The first four worlds in
the frozen order form an operational pilot (32 originals, 16 visible); the remaining
56 worlds add 448 originals only after explicit human approval. They are not
selection and confirmation samples. Confirm the 60-world sample size before the
first live execution; a different sample size requires a new reviewed protocol.
Each world: two target values × original/explicit-lookup question × direct/visible
instruction. Preserve the original introduction, question and instructions verbatim.
Lookup changes only the question to “According to the table, what is the value in
the Verified class column for license plate [TARGET]?” Same tables and targets.
10 vehicles; target last; four same-climate peers unanimously suggest the third
class, conflicting with both target variants. Six class-role permutations × two
climates, five replicates of each role/climate combination. Fresh seed 20261015053,
V5T plate namespace, deterministic shuffled worlds and eight cells per world.
Before generation, freeze all 60 worlds, tables, target rows, eight matched prompts,
configuration, source fingerprints, fixed/event analysis policy, collection order
and M/O arm schedules for every task. Event eligibility never changes those schedules.
No old worlds or trajectories are imported.

Pinned Qwen3-32B revision `9216db5781bf21249d130ec9da846c4624c16137` for weights
and tokenizer, BF16/unquantized, eager Hugging Face backend, greedy single sequence,
`enable_thinking=False`. The official empty closed thinking block stays in the
original rendered prompt. No new chat turn, hidden-thinking access, answer cues,
probes, judges or edits during original generation. Both instructions receive
**2048** tokens. The legacy loader config retains 512 solely for compatibility;
explicit v5 scientific request budgets override it. Never relabel the old config.

Record full IDs, text, EOS/finish, exact boundaries, source/model/backend fingerprint
and CUDA-synchronized timing. Preserve failed/invalid/truncated outputs, never
resample them. The terminal parser accepts plain `ANSWER: A` and balanced bold
whole-line, label or marker equivalents for A/B/C; it never infers from prose.
Truncated/no-terminal-answer correctness is unknown. Strict terminal syntax is
reported separately; strict direct compliance also requires a one-line response.

No behavioral-success gate is applied: neither accuracy gaps, reasoning-error counts,
nor M/O event prevalence determine whether the fixed remaining sample is retained.
Zero events is a valid result; never replace unfavorable or uninformative worlds.
The legacy loader's calibration fields are inert and never consulted by v5.
Two-world reporting flags describe limited coverage, not authorization thresholds.

## Technical validation and execution

Fresh v5 validation on the new Pod, irrespective of v4's result: reuse v4's three
non-scientific prompts, 128-token original and two identical-input fresh-prefill
repeats at eligible k=0,1,8,16,32. At most 33 calls/3882 tokens per run. Require
identical repeated tokens/finish, finite full-vocabulary telemetry (151936 live),
argmax agreement, probability allclose (atol 1e-5, rtol .001), TV ≤ .0001. Raw
logits and original-versus-fresh suffix differences are diagnostic only. No old
incremental-KV/fresh exact gate. Frozen new backend identity must match every stage.

Separate commands: prepare all 60; confirm sample size; offline preflight; technical
validation; collect first four worlds; STOP; inspect/scoring; fixed 2A; independent
annotation; event 2A; validate/freeze edits; separate M and O pilot execution; STOP
for human review; approve remaining; explicitly collect the other 56. Every command
stops after its own stage. Downstream `pilot` snapshots bind exactly the first 32
attempted originals and remain valid after the remaining batch. `remaining` means
only its 448 originals; `all` is a separate complete 480-response analysis snapshot.
No downstream stage starts from collection or approval.

The pilot acceptance checklist covers matched rendering, verified/pattern assignments,
target lookup, model/template/settings, completion/truncation, both parsers, cut/cue
behavior, annotation definitions/quality, source spans/boundaries, all four edits,
no-label-leak semantics, fresh-prefix/unchanged diagnostics, and immutable resume.
It binds fixed/event 2A, reviewed annotations, M and O results and source hashes.
Every check requires a named review and evidence. Zero-event edit checks may be
explicitly not applicable; failed/unreviewed checks cannot authorize the remainder.
Failures/ambiguous operations consume their planned attempt and are never resent.

Technical repairs address implementation without changing prompts, eligibility,
edits, sample schedule or analysis; document the defect and regression evidence.
Scientific changes after pilot inspection require a new version/run, and affected
pilot observations become exploratory. The current strict code hash intentionally
refuses in-place migration, even for a technical repair: retain the old revision
and artifacts and document a compatible migration separately before resuming.
Under unchanged scientific protocol and completion of the fixed 60-world schedule,
pilot data may enter the full analysis. If outcomes inform stopping, inclusion,
world replacement or methods, naive fixed-sample inference is not justified: report
adaptation, label affected analyses exploratory, and obtain fresh confirmatory data
or prespecify a valid sequential procedure. If pilot results informed probing method
design, those four worlds cannot be its held-out test set.

Historical v5 plans from commit `40d548d12ee306fe670128a8516001f4e848e053` are
unchanged and readable with that revision. This design refuses them with an explicit
message; it never upgrades/relabels a frozen plan or overwrites its outputs.

## 2A: disposable preference readouts

Visible trajectories only: fixed original-token cuts 0,128,256,512,1024 strictly
before the first line-start eligible ANSWER marker, plus the adjacent exact
pre-answer boundary. Boundaries decode/encode exactly; whitespace-only adjacency
is permitted and documented. No answer marker means pre-answer unavailable, while
eligible fixed cuts remain. A partial/Markdown marker is conservatively treated as
a boundary; never use later original tokens. Cut zero may coincide with pre-answer;
this yields a zero-change pair and remains explicit, not silently discarded.

Independently annotate first correct target-value acknowledgment, first erasure,
first conflict acknowledgment, first actual overriding justification. Measure both
sides of each eligible event. Use the same saved original IDs, disposable frozen
`\nANSWER:` and `\nFinal answer:` cues, and full ` A\n`, ` B\n`, ` C\n`
sequence log probabilities (sums, not length normalized). Normalize over these
three candidates, record raw scores, candidate/cue IDs, preferred class, and
verified-minus-pattern log odds. No generated/sampled answers. Deduplicate exact
(task, cut, cue) within one combined fixed+event plan; separate plans are not free.

Primary: original-framing pre-answer minus initial log odds, averaged across both
variants then worlds; only worlds with both complete pairs enter point estimates.
Lookup is secondary. Intermediate cuts, event deltas, outcome strata and cue
differences are descriptive. Report unavailable reasons, complete pair/world
coverage, and both cue results. Events are selected without seeing readouts.

## Semantic review and cohorts

Every visible response is reviewed, including correct, wrong, invalid, truncated,
and unavailable originals. Two independently named reviewers receive only the
original prompt and pre-answer text, no parsed final answer, scores, continuations
or outcomes. Blinding cannot conceal implications already present in the reasoning.
Human/judge-authored structured review files are supported; this implementation
uses manual imports and makes **zero paid judge calls**. Disagreements require a
third independent adjudicator. All independent decisions and negatives persist.
Use exact Unicode spans, unique 40-character context anchors, first-occurrence
certification, and explicit absent/present/uncertain/excluded/invalid statuses.
No keyword detector is treated as semantic evidence.

M: falsely assert target verified evidence absent/unavailable, including prose
absence and `?`/blank/unknown reconstructed cells. Exclude hypotheticals, negation,
other vehicles, prediction uncertainty and conflict-only statements. Mis-copying a
class as a different class is a distinct observational subtype, never automatic M.
O: a correct acknowledgment followed by an explicit argument preferring an inferred
class over the recorded class. Conflict or wrong final answer alone is insufficient.
Record clean, earlier-erasure mixed, or uncertain-erasure-history strata. O's primary
cohort is **clean overrides**; never silently pool mixed cases into it. Retain both
family events when present in one trajectory, grouped in the same world.

## 2B-M and 2B-O

Per eligible event, freeze exact statement and edit span, four complete prefix
texts/IDs, deterministic order, semantic verification and source identity before
any intervention. For reconstructed cells the selected event may be the verified
cell span, with its unique row context visible to reviewers. Four arms: unchanged;
meaning-preserving but different erroneous paraphrase; value-blind correction with
no class/hint; explicit correction supplying the verified value. An independent
verifier must certify all semantic, grammar, no-leakage and structure checks against
the exact draft hash. Lexical checks supplement, never replace, semantic judgment.
Value-blind checks exclude any standalone class label or alternative suggestion.
Meaning controls may retain a correct label already present in an override, but
may not newly introduce it. Table edits stay single cells; exclude impossible edits.

Re-encode the entire edited prefix with the exact source tokenizer. No unexpected
special IDs; decoded text and prompt+prefix concatenation must match. Unchanged
IDs must equal the original prefix IDs. All edits preserve every character outside
one shared span. Budget for every arm is **2048-original_k**, even when prefix length
changes; record length deltas. Independent fresh calls, no supplied caches, future
original tokens or extra prompts. Original/unchanged suffix agreement is descriptive
only. Independent full-candidate readouts (both cues) measure post-prefix preference;
these never enter arm generation. Unavailable arms affect only their own contrasts.

Primary for each family: value-blind minus meaning-control tolerant accuracy.
Secondary: blind-minus-unchanged, meaning-minus-unchanged, explicit-minus-unchanged,
explicit-minus-blind; all analogous conditional log-odds contrasts and strict-format
scoring are secondary. Explicit-only improvement may simply supply the answer.

## Denominators and statistics

Equal weight per independent world; within each world average matched cases/variants.
Behavioral point estimates require both variants' pairs for each framing. Interaction
requires all eight cells. 2B point estimates require all frozen cases in a world
for that contrast, without discarding other contrasts. Report prevalence, eligible
worlds, cases/world, both-family dependence, initial outcomes, initially-agreed
sensitivity, strict/tolerant results, semantic exclusions, incomplete arms and
complete-world coverage. Unknown correctness remains [0,1]; aggregate worst/best
bounds across the entire frozen cohort, including failures. No finite bounds are
invented for missing log odds. 10000 deterministic world-bootstrap samples;
95% intervals, with 97.5% intervals for the two family primary accuracy tests
(Bonferroni). Preference is secondary. Degenerate/small-world intervals are flagged;
no automatic significance or adequate-power claim. Additional stratified results
are exploratory. Frozen eligibility is never chosen using 2A shifts or edit effects.

## Separately authorized future pattern-alignment control

Not in the primary schedule. Hold target label, all non-class cells, row order,
framing and instruction fixed. Pair conflict with same-climate peer labels favoring
the target. Exact class marginals cannot generally be held while changing all four
peers to a target label occurring only 2–4 times among non-targets. Predeclare a
**majority-alignment** version: use compensating swaps with opposite-climate peers
where at least 3 copies of the target label are available; freeze which three same-
climate peers are swapped, preserve global class counts, and record changed opposite-
climate pattern strength. If infeasible for a variant, mark unavailable rather than
changing the target or silently shifting marginals. This is a joint peer-label
redistribution, not a perfectly isolated same-climate manipulation. A separately
reported unanimous-alignment sensitivity changes marginals explicitly. Manipulation
checks: same target/features/order, global counts, same/opposite climate counts,
majority strength, number/positions of changed cells and no answer leakage.
With 12 fresh worlds × two variants × two backgrounds × two framings × two
instructions, ceiling 192 originals/393216 generated tokens per alignment design;
confirmation 48 worlds gives 768/1572864. Requires new plan and authorization;
no collection command implements or starts it. Row-position, new domains and other
models likewise remain future validation. Strong pattern-specific causal claims
await these controls.

## Portable data and later probing

Retain the whole research directory with its relative layout on the persistent volume.
Original rows link task/world/variant/framing/condition, source table and rendered
prompt, target plate/row position/row values, verified and misleading class, prompt
hash, exact prompt and all output IDs (including EOS), text, lengths, finish/truncation,
strict/tolerant scores, generation operation and source/backend/technical hashes.
The plan and execution manifest retain seeds/schedules, pinned model/tokenizer,
precision, actual hardware/device/library identity and Git revision. Nothing relies
on the Pod's previous hostname or ID. Local model paths remain recorded provenance;
offline reconstruction does not open them or require matching hardware.

Boundaries retain token count k, Unicode code-point offset, exact-roundtrip status,
text and token fingerprints, and explicit unavailability reasons, without duplicating
every prefix string. 2A retains candidate sequence/token likelihoods, normalized
preferences, preferred class, log odds and context identity. Annotations retain all
independent decisions, disagreements/adjudication, clean/mixed O and source row.
Edits retain all four texts/IDs, exact source span, three replacements, original k,
remaining budgets, token deltas, order, full responses and continuation IDs, outcomes,
and fresh-prefill/unchanged diagnostics. Every descendant carries its parent world.

`prepare-checkpoints` freezes fixed/event cut metadata from original rows.
`reconstruct` verifies seals, source identity, original operation/token fingerprints,
checkpoint offsets and annotations, then returns precisely `prompt_ids + output_ids[:k]`.
No cue, edit, future original tokens, tokenization, weights, CUDA or generation is
used. Unavailable cuts return no context and an explicit reason. These are **fresh-prefix
replay contexts**, not original incremental hidden states. Preserve the original
same-input and cross-path diagnostic metadata; never reinstate the v3 cross-path gate.
Any future live replay must record its actual backend/hardware. Exact original hidden
states would require a separately versioned collection experiment; no activations
or dense per-step vocabulary arrays are collected in scientific stages here.

`split-worlds` assigns the frozen world IDs deterministically using seed 20261015054,
by default 48 train/12 evaluation worlds, without reading response outcomes. Every
variant/framing/condition and all derived checkpoints/interventions inherit that
world assignment. Explicitly record whether the pilot informed method design; if so,
it is confined to training. Freeze the split before probe selection or evaluation.
Outcome-based rebalancing is not implemented and would need exploratory labeling.
No probe architecture, layer, target label, hypothesis or training is selected.
See `STUDY2_V5_PROBING_SCHEMA.md` for the offline contract and storage budget.
