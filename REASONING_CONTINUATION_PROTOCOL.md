# Within-response conditional answer readouts and text interventions

Design fixed before implementation. No model validation or scientific results
are claimed from offline tests. Base: upstream main bdc9218.

## Scope and overlap

Read the four pending protocols at evidence-role 2eae5f2, row-confirmation e026a97,
and features/downstream 28b5be0. This adds no early entry, forced slot, feature
intervention, target-position sweep, or question after a completed assistant turn.
The existing prefix screens in main provide feasibility context, but do not
validate this backend. Reuse main's generator, table prompt, RNG, digest and
atomic-file infrastructure; leave all earlier packages untouched.

## Backend and validation before interpretation

Use an opt-in LOCAL Transformers causal LM, local_files_only=True,
trust_remote_code=False, one greedy sample, eval mode, explicit device/dtype,
eager attention, no sampling or model API. Save model-file hashes, tokenizer,
chat template, special tokens, library versions and generation settings. Do not
pick or download a model during offline preparation. This is a backend framework;
replication of the original Mistral/GPT-4o behavior on any open model is unknown.

Format the original user message once with add_generation_prompt=True, then
save its exact input token IDs. Save the unmodified generated assistant token
IDs. Resume from original_input_ids + original_generated_ids[:k], without
retokenizing the unchanged prefix, adding a message boundary, ending the assistant
turn, or inserting another user request. Recompute the causal model from this
prefix; this is token-context replay, not restoration of a hidden-state snapshot.

Validation has two layers. A separate fixed three-prompt technical suite tests
multiple prefix lengths and exact entire greedy suffix equality against an
uninterrupted response with the same remaining token budget. ALL available
technical cuts must match; there must be at least one cut per prompt. Then EVERY
eligible scientific checkpoint is replayed and compared token-for-token with
its original suffix. A failing technical suite blocks collection. A failing
per-trajectory replay blocks ALL readout/edit interpretation for that trajectory,
with its raw failure retained. Replay includes EOS/stop behavior, not just final
class agreement. Prefix token round-trip differences are separately reported.
Numerical/backend changes can fail strict replay; do not relax the gate after
seeing edited outcomes. Offline fake-model success does not validate a real model.

## Selection versus confirmation

Separate `selection` (12 worlds, seed 2026101221) and `confirmation` (24 worlds,
seed 2026101222), disjoint prefixes/world IDs, with all label-role/climate
assignments balanced. The selection run contains matched direct/reason responses
and descriptive failure rates to assess behavior replication. It never enters
confirmation estimates. Choose a model/config using selection only, document the
choice in a selection-lock JSON, and explicitly prepare confirmation referencing
that completed selection run and exact backend identity. No automatic model
search, result-dependent sample extension, or importing historical failures.
Confirmation includes all fresh worlds regardless of their answers.

## Unmodified trajectory and predefined checkpoints

Same seven-column ten-record family, fixed last-row target to study the motivating
failure setting; two recorded variants, direct and visible arms. No row comparison.
24 × 2 × 2 = 96 unmodified confirmation trajectories. Fixed maximum 512 new tokens.
For visible outputs define cuts at 0, 32, 64, 128 generated TOKENS; never shift a cut
to a convenient error. Only cuts strictly before the FIRST literal ANSWER: marker
and before termination are eligible. Missing/early-final checkpoints are retained
as ineligible. Markers are output-interface diagnostics, not a detector for every
implicit answer statement. A checkpoint may contain an earlier class assertion.

At each replay-valid checkpoint, append the same tokenized `\nANSWER:` cue on a
SEPARATE measurement branch and teacher-force candidate strings ` A\n`, ` B\n`,
` C\n`. Sum conditional token log probabilities for each entire candidate; save
all token IDs/log probabilities and the normalized three-candidate probabilities.
Do not take top-k omissions as zero probabilities. Report candidate lengths,
unnormalized probability mass and log P(gold)/P(pattern). These are constrained,
cue-dependent conditional readouts, not direct hidden-belief measurements or
probabilities of arbitrary natural completions. Do not feed the cue/readout back
into the original trajectory or intervention continuation. All measurement
branches retain the original prefix IDs; no new conversational turn is used.

Primary longitudinal readout: world-mean change in gold-versus-pattern log odds
from token 0 to token 64 on replay-valid paired variants. Other cuts descriptive.
Report coverage and available-world denominators; absence of late checkpoints is
potentially informative, not evidence of stable preferences. No finite missing-
log-odds bounds are available. Actual spontaneous final answers remain separate.

## Manual targeted edit plan

Export EVERY visible trajectory, including correct, wrong and invalid answers,
for manual review with exact source hashes and truth tables. Reviewers identify
the FIRST explicit false statement of target-class absence, not whichever claim
produces the largest effect. Record exact character span, old text, reviewer,
truth-based justification and three replacement strings. Require manual semantic
certification; automated checks cannot prove that a paraphrase preserves meaning.
Other factual repair types can be represented in separate exploratory plans, but
the implemented confirmatory cohort is false missingness only.

Use the first of 32/64/128 whose prefix contains the entire annotated claim and
is before ANSWER:. If none, mark ineligible; never choose a new cut. A fully
reviewed no-error item is explicit; unreviewed remains unknown. Freeze the edit
plan before any edited continuations; all selected edits are included regardless
of original final accuracy or the direction of their readout change.

Four arms on the same original prefix/checkpoint:
1. unchanged: exact saved token prefix;
2. availability_repair: assert the recorded class is present WITHOUT adding any
   standalone A/B/C token (e.g., 'Its verified class is recorded in the table.');
3. meaning_control: paraphrase the original false absence claim while retaining
   its meaning (e.g., 'Its verified class is absent from the table.');
4. value_repair: explicitly state the correct recorded class; secondary because
   it additionally repeats the answer.

One exact span replacement, all other characters unchanged. Log changed token
span, text/token length deltas, class-letter counts, edit hashes and all strings.
Encode edited assistant text separately, with no special tokens; require exact
text round trip and reject any special token ID in the encoded body. Preserve
original input token IDs and assistant boundary. Also require unchanged body
encode(decode(prefix)) to equal original prefix IDs at this edit checkpoint;
otherwise mark text editing unavailable rather than changing tokenization of the
unchanged control. Token differences outside the edit can arise from tokenizer
boundaries and are reported. Repairs and semantic controls may differ in length,
fluency and pragmatics; they do not isolate 'truth' as a latent variable.

Continue each arm with the SAME remaining-generation budget (512-k), independent
of how many tokens its edit added. Save complete prefix plus suffix, raw token IDs,
stop status, final validity, and conditional readouts at the edited checkpoint
on separate branches. All four arms share a case ID. Invalids are retained.
Primary intervention contrast: availability_repair minus meaning_control in
final-answer accuracy, average variants/cases within world then worlds; unchanged
contrasts and value repair are secondary. Also report paired conditional log-odds
changes. Selected false-missingness cases estimate effects in that cohort, not
prevalence or effects for all outputs. A repair effect concerns text-conditioned
continuation, not proof the original words caused the original error.

## Integrity, outputs and commands

All model operations require `--live` or `--mock`. No API backend or fallback to
new-turn chat exists. Local model loading, generation and scoring are opt-in.
Each operation is journaled started/returned/error atomically; no retries of
invalid outputs. Interrupted/error operations block resume for review. Config,
source, plan, backend, trajectory and edit hashes protect stage boundaries.
Mock directories are labeled SIMULATED and cannot authorize real confirmation.
Use Python 3.10+. Actual local execution additionally needs torch/transformers
and an already downloaded compatible causal model; no model is bundled.

Offline commands:

```sh
python3 -m unittest discover -s tests -p 'test_continuation_followup.py' -v
python3 -m exception_continuation prepare --phase selection --output runs/continuation-preview
python3 -m exception_continuation collect --output runs/continuation-preview --mock
python3 -m exception_continuation measure --output runs/continuation-preview --mock
python3 -m exception_continuation review-export --output runs/continuation-preview
python3 -m exception_continuation analyze --output runs/continuation-preview
```

Exact live workflow and annotation example are in CONTINUATION_RUNBOOK.md.
No forced-entry/forced-slot study is implemented. A future sampling backend would
need a new distributional equivalence protocol; the strict gate here is greedy.
