# RunPod: staged Study 2 v5 (60 worlds, initial four-world pilot)

Design `staged-60-v1` on `codex/study2-v5-evidence-interventions`. These are commands
for the operator, not commands executed during packaging. Run one small block at a
time and STOP on errors. No command advances automatically to the next stage.
Preserve v3/v4, earlier v5 and diagnostic runs. Old v5 selection/confirmation plans
require commit `40d548d12ee306fe670128a8516001f4e848e053`, not an in-place upgrade.

Reuse the existing persistent `/workspace` volume, environment and pinned snapshot.
Allow approximately 200 GB volume, 128–192 GB host RAM, and one H100 80 GB or H200
141 GB. The serial eager BF16 backend remains unchanged; see the workload document.
Nothing here deploys a Pod. Stop the paid GPU while doing lengthy manual reviews
when practical; preserve the volume and recorded backend identity for resumption.

## 1. Checkout, environment and new frozen plan (CPU/offline after Git fetch)

Inspect changes before switching; never overwrite unrelated work. On first checkout:

```bash
cd /workspace/exception-pilot
git status --short
git fetch origin codex/study2-v5-evidence-interventions
git switch --no-track -c codex/study2-v5-evidence-interventions FETCH_HEAD
```

If that branch already exists, replace the last command with these two commands:

```bash
git switch codex/study2-v5-evidence-interventions
git merge --ff-only FETCH_HEAD
```

Do not update code in the middle of a frozen run. Save the final `git rev-parse HEAD`
with your run notes. Reuse the existing pinned Python 3.12 environment:

```bash
source /workspace/venvs/study2-qwen3/bin/activate
python --version
python -m pip check
export PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
test -d "$STUDY2_MODEL_DIR"
export V5_HOME=$(mktemp -d /workspace/study2-v5-staged-XXXXXXXX)
export RUN_V5="$V5_HOME/originals"
printf '%s\n' "$V5_HOME" > /workspace/study2-v5-home-path.txt
python -m exception_study2_v5 configure --model-dir "$STUDY2_MODEL_DIR" --config "$V5_HOME/config.json"
python -m exception_study2_v5 prepare --config "$V5_HOME/config.json" --output "$RUN_V5"
python -m exception_study2_v5 preflight --output "$RUN_V5"
python -m exception_study2_v5 workload
```

This freezes all 60 worlds/480 prompts, source/configuration, seeds, original order,
fixed analysis policy and all possible M/O arm orders before any generation.
Pinned dependencies: torch 2.7.1+cu126, transformers 4.51.3, tokenizers 0.21.1,
huggingface-hub 0.30.2, safetensors 0.5.3, Jinja2 3.1.6, numpy 2.2.4; authoritative
file `requirements-study2-qwen3.txt`. No reinstallation or weights download is needed
when the preserved environment passes. A moved venv needs a compatible Python image.
Preflight reads tokenizer assets and weight filenames/sizes, not model tensors.

Before the first live command, **confirm the sample size**. Replace the reviewer
name/rationale with your actual decision. If 60 worlds is not approved, STOP and
revise the protocol in a new version before execution.

```bash
python -m exception_study2_v5 confirm-design --output "$RUN_V5" --worlds 60 --reviewer 'YOUR_NAME' --rationale 'I approve the prespecified 60-world design and four-world operational pilot.'
```

After reconnecting, restore the same directory; do not create another plan:

```bash
export V5_HOME=$(cat /workspace/study2-v5-home-path.txt)
export RUN_V5="$V5_HOME/originals"
```

## 2. Technical replay validation (GPU)

```bash
nvidia-smi
python -m exception_study2_v5 validate --output "$RUN_V5" --live-qwen
```

**STOP on any exception or any real status other than `V5_SAME_INPUT_PASSED`.**
Preserve `technical-v5.json`, `technical-status-v5.json`, `execution-v5.json`,
`operations-v5/`, `timing-v5/`. Do not delete failed journals to retry. At most
33 technical calls/3882 output tokens. Initial full weight hashing/loading can take
minutes. This compares identical fresh-prefill inputs, not original incremental KV
states against fresh prefill. Original-suffix disagreement remains diagnostic.

## 3. First four worlds, then STOP (GPU, followed by offline scoring)

Only after real technical validation passes:

```bash
python -m exception_study2_v5 collect --output "$RUN_V5" --batch pilot --live-qwen
```

**STOP: exactly 32 planned original attempts across four complete worlds, 16 visible.**
Failed/ambiguous calls remain unavailable, never resampled. Rerunning this command
processes only unattempted work and never advances to world five. Inspect offline:

```bash
python -m exception_study2_v5 summary --output "$RUN_V5" --scope pilot
python -m exception_study2_v5 timing --output "$RUN_V5"
```

Read `behavioral-summary-pilot-v5.json`, full original texts and operation journals.
Wrong, invalid and truncated results persist. No accuracy gap/error-count gate exists.

## 4. Pilot fixed/pre-answer 2A (prepare offline; measure GPU)

```bash
export FIXED_V5="$V5_HOME/pilot-fixed"
python -m exception_study2_v5 prepare-measurements --source "$RUN_V5" --scope pilot --output "$FIXED_V5"
```

Inspect the frozen measurement plan. Explicit execution:

```bash
python -m exception_study2_v5 measure --output "$FIXED_V5" --live-qwen
```

STOP. This scores complete A/B/C candidate strings under both cues; no answers are
generated and no cues enter original trajectories. Keep readout outcomes hidden
from event annotators and edit drafters/verifiers.

## 5. Independent event review (offline, manual structured imports)

```bash
export REVIEW_V5="$V5_HOME/pilot-review"
python -m exception_study2_v5 prepare-review --source "$RUN_V5" --scope pilot --output "$REVIEW_V5"
```

Two independent reviewers receive only their blinded view and blank template.
Copy templates to `reviewer-1.json` and `reviewer-2.json`, then independently fill
reviewer identity and all event statuses, rationale and certificates. Present events
need exact Unicode code-point `[start,end]`, exact text and unique context anchors.
Non-present decisions use null span/text/anchor/subtype. No keyword rule substitutes
for semantic review. This implementation imports judge/human-authored files; it does
not call a paid judge API. Never auto-fill acceptance certificates.

```bash
python -m exception_study2_v5 freeze-annotations --output "$REVIEW_V5" --first "$REVIEW_V5/reviewer-1.json" --second "$REVIEW_V5/reviewer-2.json"
```

STOP on disagreement. A third independent reviewer adjudicates exactly disputed
cases; rerun with `--adjudication "$REVIEW_V5/adjudication.json"`. All decisions persist.

```bash
export ANNOTATIONS_V5="$REVIEW_V5/annotation-manifest-v5.json"
python -m exception_study2_v5 annotation-summary --source "$RUN_V5" --scope pilot --annotations "$ANNOTATIONS_V5"
export EVENT_V5="$V5_HOME/pilot-events"
python -m exception_study2_v5 prepare-measurements --source "$RUN_V5" --scope pilot --output "$EVENT_V5" --annotations "$ANNOTATIONS_V5" --events-only
```

Run event-only readouts explicitly (GPU), without repeating the fixed-cut plan:

```bash
python -m exception_study2_v5 measure --output "$EVENT_V5" --live-qwen
```

Keep both 2A plans/results. Exact event/fixed aliases may repeat across these two
plans; do not claim cross-plan cache reuse. Combined ceiling remains 1344 candidate
sequence evaluations for the pilot. A single combined plan after blinded review is
also supported by omitting `--events-only` and supplying annotations; do not run both
strategies. Readouts do not choose events or edits.

## 6. Draft, verify and freeze M/O separately (offline; tokenizer only)

```bash
export M_V5="$V5_HOME/pilot-M"
export O_V5="$V5_HOME/pilot-O"
python -m exception_study2_v5 prepare-edits --source "$RUN_V5" --scope pilot --annotations "$ANNOTATIONS_V5" --output "$M_V5" --family M
python -m exception_study2_v5 prepare-edits --source "$RUN_V5" --scope pilot --annotations "$ANNOTATIONS_V5" --output "$O_V5" --family O
```

For each family, independently fill `drafts.json` and `verification.json` from the
provided templates. Name drafter/verifier, proposed/excluded and accepted/uncertain/
invalid/excluded decisions, rationale, exact draft hash and every semantic check.
Do not certify merely because lexical checks pass. Compute hashes without certifying:

```bash
python -c 'import json,os; from pathlib import Path; from exception_pilot.core import digest; d=json.loads((Path(os.environ["M_V5"])/"drafts.json").read_text()); print(json.dumps({t:digest(v) for t,v in d["cases"].items()},indent=2))'
```

Then freeze each independently:

```bash
python -m exception_study2_v5 freeze-edits --output "$M_V5" --drafts "$M_V5/drafts.json" --verification "$M_V5/verification.json" --tokenizer-dir "$STUDY2_MODEL_DIR"
python -m exception_study2_v5 freeze-edits --output "$O_V5" --drafts "$O_V5/drafts.json" --verification "$O_V5/verification.json" --tokenizer-dir "$STUDY2_MODEL_DIR"
```

With zero events, preserve the empty case templates, fill the verifier identity and
freeze the empty manifest. Never invent cases, replace worlds, or pool mixed O into
clean O. Inspect every eligible/excluded case and four-arm prefix before execution.

## 7. Separate pilot interventions (GPU when cases exist)

```bash
python -m exception_study2_v5 intervene --output "$M_V5" --live-qwen
```

STOP and inspect M. O is a separate explicit command:

```bash
python -m exception_study2_v5 intervene --output "$O_V5" --live-qwen
```

Each arm has `2048-original_k` remaining budget; full response and suffix IDs persist.
Unchanged agreement is diagnostic. Failed arms stay failed and do not poison other
contrasts. Empty manifests produce `ZERO_ELIGIBLE_CASES` with zero GPU calls.
**STOP for human review. Do not automatically collect the remaining worlds.**

## 8. Human pilot acceptance and explicit remaining approval (offline)

```bash
python -m exception_study2_v5 pilot-checklist --source "$RUN_V5" --output "$V5_HOME/pilot-checklist.json" --measurements "$FIXED_V5/measurements-v5.json" --event-measurements "$EVENT_V5/measurements-v5.json" --annotations "$ANNOTATIONS_V5" --family-m "$M_V5/interventions-v5.json" --family-o "$O_V5/interventions-v5.json"
```

For a combined measurement plan, use its result for `--measurements` and omit
`--event-measurements`. Review every checklist item. Copy `pilot-review-template.json`
to `pilot-review.json` and fill evidence, named reviewer/rationale, technical repairs,
whether pilot results informed method design, and explicit remaining approval.
There is no desired accuracy gap or minimum M/O event count. Zero-case exemptions
are only for unavailable event/edit checks. Any scientific change (prompts, eligibility,
edits, analysis) means STOP, new version and affected pilot labeled exploratory.
The current strict source hash does not migrate any frozen runs after code repairs.

Only if the unchanged scientific protocol and checklist are accepted:

```bash
python -m exception_study2_v5 approve-remaining --output "$RUN_V5" --checklist "$V5_HOME/pilot-checklist.json" --decisions "$V5_HOME/pilot-review.json"
```

Approval itself makes no model calls. **STOP here unless explicitly choosing the
remaining collection.** To perform that separately authorized GPU stage later:

```bash
python -m exception_study2_v5 collect --output "$RUN_V5" --batch remaining --live-qwen
```

Exactly the remaining 448 attempts, same frozen scientific configuration. It verifies
pilot evidence/approval before loading the backend. It never regenerates pilot data.
Afterward use `summary --scope all`; other downstream stages for the later batch use
`--scope remaining` and fresh `remaining-*` directories, with separate stage commands.
Existing pilot artifacts remain readable. An `all` downstream plan would intentionally
recompute pilot analyses; do not silently duplicate that work. Combine batch results
by world and original plan; no independent confirmation claim is created.

## 9. Offline probing preparation (optional; no GPU, weights or tokenizer)

```bash
python -m exception_study2_v5 prepare-checkpoints --source "$RUN_V5" --scope pilot --annotations "$ANNOTATIONS_V5" --output "$V5_HOME/pilot-checkpoints.json"
```

Choose a task ID and checkpoint name from this frozen manifest. For example:

```bash
export PROBE_TASK=$(python -c 'import json,os; from pathlib import Path; p=json.loads((Path(os.environ["V5_HOME"])/"pilot-checkpoints.json").read_text()); print(next(iter(p["rows"])))')
python -m exception_study2_v5 reconstruct --manifest "$V5_HOME/pilot-checkpoints.json" --task "$PROBE_TASK" --checkpoint fixed/128 --output "$V5_HOME/example-context.json"
```

Unavailable cuts return `available:false`, a reason and no context. Available cuts
are exactly prompt IDs plus the first k original generated IDs, without answer cues
or edits. This is a fresh-prefix replay context, not an original hidden-state claim.
No activations are collected. Move the whole research tree together; relative
references continue to work on CPU-only machines with different hardware.

Freeze outcome-blind splits before any probe development/evaluation, explicitly
recording whether the pilot informed methods (use `yes` whenever it did):

```bash
python -m exception_study2_v5 split-worlds --source "$RUN_V5" --output "$V5_HOME/world-splits.json" --pilot-informed-design yes
```

Default 48 train/12 evaluation worlds; no world crosses the boundary, including all
variants/checkpoints/intervention descendants. No training or architecture selection.
Keep all scientific/technical artifacts; no dense activation cache is assumed.
