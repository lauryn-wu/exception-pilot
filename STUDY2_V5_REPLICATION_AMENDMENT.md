# Study 2A replication-only workflow amendment v1

This additive amendment starts from `40aa1f7c5b61e8862a9c9d0f3768e9880323bbc1`
on `codex/study2-v5-judge-review-v2`. The four-world pilot was examined **before**
this amendment. Its results are exploratory pilot evidence, not untouched validation.

## Decision and scope

Complete the already specified 56 remaining independent worlds (448 original
attempts), followed by their fixed-checkpoint Study 2A answer-preference readouts.
Unresolved semantic review and Study 2B intervention eligibility need not prevent
this fixed-sample replication. This is a workflow amendment, not evidence that
Study 2B is eligible or complete. The existing v5 approval functions and their
Study 2B prerequisites remain unchanged for the original workflow.

`exception_study2_v5_replication` implements a separate, explicit approval, with
source-bound acknowledgment that the pilot was examined. Preparation is not
approval. Approval is not collection. Collection stops without starting any
measurements. Measurement preparation, execution, and analysis are separate
commands; none dispatches judges or interventions.

All 56 remaining worlds must be retained, including failed, truncated, invalid,
null, and uninformative outcomes. There is no result-dependent stopping,
replacement, threshold change, or selection to reproduce world 003.

## Frozen scientific design

The original plan remains exactly 60 worlds / 480 tasks. Preserve worlds, seeds,
classes, row order, targets, both prompt framings, both output instructions,
answer parsing, and all frozen scientific source hashes. Generation remains
pinned Qwen3-32B, official chat formatting with `enable_thinking=False`, BF16,
greedy, batch one, eager attention, no added quantization, and an explicit
2,048-token scientific budget. The legacy model configuration's default generation
cap is not edited; the frozen v5 caller supplies 2,048 explicitly.

The 32 pilot attempts are never generated again. Only the exact frozen tasks
33–480 are eligible for new attempts. All 224 remaining visible trajectories are
included in fixed-only readout planning, even when no checkpoint can be scored.
Readouts use the unchanged v5 eligibility rules at 0, 128, 256, 512, and 1,024
generated tokens and immediately before the answer. A cut must have an eligible
exact saved token boundary; an ineligible cut is retained with its reason. Aliased
cuts share a computation. Both frozen cues (`\nANSWER:` and `\nFinal answer:`)
score all three complete candidate sequences (` A\n`, ` B\n`, ` C\n`). Individual
token log probabilities, sequence likelihoods, and normalized three-class
probabilities are retained. Measurement generates no answers and requires no
semantic annotations.

## Preservation and execution identity

Historical salvage/residual evidence binds whole source trees. Adding files to
the original directory would invalidate those tree hashes, even if existing
response files were unchanged. Preparation therefore copies only the original
experiment directory into a new versioned research directory, byte-verifies every
file, and freezes inventories of the original source and explicitly preserved
judge/readout archives. It rejects overlapping outputs, symlinks, model-weight
files, incomplete copies, additional original attempts, and orphan journals.
It neither copies weights nor hard-links mutable research files.

The original `Session` freezes Git HEAD in `execution-v5.json`. Reusing its
constructor after changing HEAD would conflict with that saved execution. The
replication session retains the original execution file byte-for-byte and uses a
separate `replication-execution.json` containing actual current HEAD, the original
revision, amendment/approval identities, implementation hash, and the exact
original backend identity. Every new immutable operation binds that execution.
It inherits the original journal and generation methods without patching them.
No old revision, approval, checklist, result, or hash is forged.

The backend must equal the original identity, including hardware, environment,
model/tokenizer/template/configuration hashes, and model path. Rendering all 32
pilot prompts must reproduce their saved input IDs before new generation.
Resuming at a different replication HEAD or with any backend mismatch stops.
Use the same pinned checkout throughout collection and readouts. A deliberately
changed runtime requires a separately reviewed amendment; do not rewrite records
to make it match. Returned operations are reused; started/failed operations are
preserved as unavailable and never automatically resent. A request recorded before
its `started` marker can be executed because dispatch has not begun.

## Prespecified analysis

The primary outcome is original-question **pre-answer minus initial
verified-versus-pattern log odds**, using cue 0 (`\nANSWER:`). Average the two
matched variants within each world and require both matched variants for the
primary estimate. Use independent worlds as sampling units and the unchanged v5
bootstrap (seed 981723, 10,000 resamples, 95% interval). Explicit lookup is secondary;
cue 1 is a sensitivity analysis. The unchanged v5 trajectory report is also retained.

Descriptive output includes:

- World-weighted checkpoint means, eligible/observed/planned trajectory and world
  denominators, reasons for ineligibility, and observed variants per world.
- Paired changes from initial at each cut, plus a fixed cohort with all six named
  checkpoints. Cross-sectional means over changing populations are not interpreted
  as a population-wide trajectory.
- Verified-to-pattern preference reversals and subsequent recoveries in temporal
  token order; aliases are deduplicated. These are descriptive readout transitions,
  not new semantic-event definitions. A third class may intervene in an observed
  sequence; literal adjacent verified-to-pattern transition counts are also given.
  Missing eligible readouts break a sequence. Observed positive events remain
  positive; negative claims require complete eligible observations. Recovery rates
  are additionally conditional on observed reversal.
- Cross-cue preferred-class agreement/disagreement and paired log-odds differences.
- Associations with actual correct, wrong, and unknown final answers, plus frozen
  direct-versus-visible accuracy contrasts and incorrect pattern-based answers.

No missing readout is zero-imputed or treated as a negative event. The 56 remaining
worlds and four examined pilot worlds are separate report sections. Pilot readouts
are read only when their preserved archive is explicitly supplied; they are never
recomputed. No pooled 60-world claim is produced. Partial analysis is saved as a
new content-addressed snapshot, without overwriting earlier analysis.

## Acceptance and limits

See [the offline audit](audits/study2-replication-v1/AUDIT.md) and
[the execution runbook](STUDY2_V5_REPLICATION_RUNBOOK.md). This patch runs only
mock-backed execution tests and offline inspection of saved evidence. Live
replication, new readout timing, and real-model compatibility of the new wrapper
remain untested. The original real-model technical gate is verified and reused;
this amendment does not rerun it or claim a new technical result.

The locally recovered pilot readout folder contains a 112-computation plan and
lock file, but no returned measurement journals. Those 112 completions cannot be
verified from the local archive. Preserve the actual completed readout folder on
the Pod and supply it for read-only pilot analysis; do not rerun pilot readouts to
fill this local evidence gap.
