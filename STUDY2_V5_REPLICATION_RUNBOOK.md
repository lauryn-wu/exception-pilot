# Study 2A replication-only v1 runbook

This runbook uses the existing v5 environment and frozen scientific settings.
Read [the amendment](STUDY2_V5_REPLICATION_AMENDMENT.md) before approving it.
All commands below are provided for later execution; no live collection,
measurement, GPU, or paid call was run while implementing this patch.

## 1. Checkout and check the existing environment

Run each block separately in the existing Pod terminal. Do not paste all stages
as one unattended script. Keep the checkout and original artifacts unchanged
throughout the run. A dirty checkout should be inspected before continuing.

```bash
cd /workspace/exception-pilot
git status --short --branch
git switch codex/study2-v5-judge-review-v2
git pull --ff-only origin codex/study2-v5-judge-review-v2
source /workspace/venvs/study2-qwen3/bin/activate
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1
export REPLICATION_CODE_REVISION="$(git rev-parse HEAD)"
export PILOT_V5=/workspace/study2-v5-staged-huwUCkqs/originals
export REP_V1=/workspace/study2-v5-replication-v1
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
python --version
python -m pip check
nvidia-smi
```

Expected historical backend: **NVIDIA H100 80GB HBM3**, Python 3.12.3,
torch 2.7.1+cu126, Transformers 4.51.3, tokenizers 0.21.1, CUDA 12.6,
cuDNN 90501, eager BF16, greedy, batch one. The entire saved identity must
match, including actual model-file hashes and the model path. H100 PCIe or another
GPU is not an interchangeable identity for this amendment. Do not change dtype,
backend, attention, paths, tokenizer, dependency versions, or scientific files
to force a match. This workflow does not install packages or download weights.

```bash
python -c 'import json,os; from pathlib import Path; p=Path(os.environ["PILOT_V5"]); e=json.loads((p/"execution-v5.json").read_text()); print(json.dumps(e,indent=2)); assert Path(os.environ["STUDY2_MODEL_DIR"]).is_dir()'
```

Stop if the source/model directory is missing or any compatibility check fails.

## 2. Locate and preserve the existing pilot readouts and judge archives

The expected pilot readout path below must refer to the folder containing the
**existing** `measurement-plan-v5.json`. If it is elsewhere, set the actual path.
Do not create or regenerate pilot measurement results. If needed, locate plans
with `find /workspace -name measurement-plan-v5.json -print`.

```bash
export PILOT_READOUTS=/workspace/study2-v5-pilot-fixed
test -f "$PILOT_READOUTS/measurement-plan-v5.json"
python -c 'import os; from pathlib import Path; p=Path(os.environ["PILOT_READOUTS"]); print("Returned journals:",len(list(p.glob("operations-v5/*/returned.json")))); print("Summary present:",(p/"measurements-v5.json").is_file())'
```

Local recovery has only the plan, with 112 planned computations; completed pilot
journals were not available locally for verification. A missing summary alone
need not mean missing results: the analyzer reads operation journals directly.
Keep the pilot's parent directory (which includes its original judge archive)
intact. For any additional judge, salvage, or residual directory stored elsewhere
on the Pod, add another `--preserve /actual/archive/path` to preparation. Keep all
such preserved archives unchanged for the duration of replication.

## 3. Prepare a fresh copy and inspect — no inference

The source and output must be separate. The new output must not already exist.
Preparation copies about 83 MB of research artifacts, not model weights. It
freezes the actual Pod paths and current package hash; **do not copy or edit the
Mac offline amendment** as a substitute.

```bash
test ! -e "$REP_V1"
python -m exception_study2_v5_replication prepare \
  --source "$PILOT_V5" --output "$REP_V1" \
  --preserve /workspace/study2-v5-staged-huwUCkqs \
  --preserve "$PILOT_READOUTS" > "$REP_V1-prepare-preview.json"
python -m exception_study2_v5_replication inspect --output "$REP_V1" > "$REP_V1-inspect-preview.json"
python -c 'import json,os; p=json.load(open(os.environ["REP_V1"]+"-inspect-preview.json")); print({"worlds":len(p["remaining_worlds"]),"tasks":len(p["remaining_tasks"]),"visible":p["visible_trajectories"],"recorded":p["recorded_remaining"],"approved":p["approved"]})'
python -m exception_study2_v5_replication estimate \
  --source "$PILOT_V5" --pilot-readouts "$PILOT_READOUTS" --hourly-rate 3.99
```

Large JSON previews are saved beside the fresh directory to keep the terminal
readable. These preview files are not approvals or execution journals.
Replace the example hourly rate with the Pod's actual quote. Review the exact 56
world IDs, 448 task IDs/prompts, 224 visible IDs, backend identity, preserved
archives, and `approved: false`. These are the original prespecified tasks, not a
new sampled plan. Keep all 56 worlds irrespective of their eventual outcomes.

## 4. Explicitly approve the post-pilot amendment — no inference

Run only after reviewing the prepared amendment. This is an actual approval
record; preparation in the implementation audit did **not** perform this step.

```bash
export AMENDMENT_HASH="$(python -c 'import json,os; from pathlib import Path; print(json.loads((Path(os.environ["REP_V1"])/"amendment.json").read_text())["artifact_hash"])')"
python -m exception_study2_v5_replication approve \
  --output "$REP_V1" --amendment-hash "$AMENDMENT_HASH" \
  --reviewer Lauryn \
  --rationale "Approve all 56 prespecified remaining worlds after examining the four-world pilot; Study 2A replication proceeds independently of Study 2B eligibility." \
  --acknowledge-pilot-examined --approve-remaining
```

## 5. Collect exactly the remaining 448 attempts, then STOP

This is the first GPU-inference command. It verifies source/technical integrity,
explicit approval, exact backend identity, and pilot prompt rendering before new
generation. **On any validation failure, stop; do not edit hashes or bypass gates.**

```bash
test "$(git rev-parse HEAD)" = "$REPLICATION_CODE_REVISION"
python -m exception_study2_v5_replication collect --output "$REP_V1" --live-qwen
python -m exception_study2_v5_replication inspect --output "$REP_V1" > "$REP_V1-after-collection.json"
python -c 'import json,os; p=json.load(open(os.environ["REP_V1"]+"-after-collection.json")); print({"recorded":p["recorded_remaining"],"remaining":p["unrecorded_remaining"]})'
```

**STOP and review `replication-collection.json` and the 448 remaining rows.**
No measurements or interventions have started. Expect 448 recorded attempts,
including unavailable/failed outcomes, not necessarily 448 successful responses.
A returned model response without a saved row is recovered from its journal.
Started/failed calls are not resent. To resume after interruption, use this same
collection command, output, code revision, and backend. Do not delete journals.

## 6. Separately prepare the remaining-world Study 2A readouts

Only after all 448 attempts are durably represented:

```bash
python -m exception_study2_v5_replication prepare-readouts --output "$REP_V1" > "$REP_V1-readout-preview.json"
python -m exception_study2_v5_replication measure --output "$REP_V1"
```

The second command is an offline preview because it lacks `--live-qwen`.
Inspect `readouts-remaining-v1/measurement-plan-v5.json`: all 224 visible
trajectories, both cues, exact eligibility, no semantic annotations, no pilot
trajectories, and zero generated answers. The maximum is 2,688 unique checkpoint
readouts / 8,064 full candidate-sequence scoring operations; actual counts depend
on saved length, answers, eligible boundaries, and cut aliases.

**STOP if the plan or source checks fail.**

## 7. Explicitly measure, analyze, and STOP

```bash
test "$(git rev-parse HEAD)" = "$REPLICATION_CODE_REVISION"
python -m exception_study2_v5_replication measure --output "$REP_V1" --live-qwen > "$REP_V1-measurement-command.json"
python -m exception_study2_v5_replication analyze \
  --output "$REP_V1" --pilot-readouts "$PILOT_READOUTS" > "$REP_V1-analysis-preview.json"
```

The measurement command scores the three frozen candidate strings only. It never
generates an answer or edited continuation. It can be quiet for tens of minutes;
progress is recorded under `readouts-remaining-v1/operations-v5/` and `timing-v5/`.
Canonical results remain in immutable journals and `measurements-v5.json`; the
redirected command output is only a convenience copy. Resume using the identical command
and checkout; immutable journals prevent automatic resampling. The analyzer can
also inspect an interrupted readout run offline and reports unattempted/failed
readouts as missing. It writes immutable snapshots under `analysis-v1/`.
If pilot readout results are unavailable, omit `--pilot-readouts`; the four-world
pilot behavioral summary remains separate and readout evidence is explicitly
`NOT_PROVIDED`. No pilot readout is recomputed in either mode.

**STOP here. No Study 2B, semantic-event measurements, evidence probes, judge
calls, or additional samples are authorized by these commands.**

## Workload, measured timing, and cost

See `audits/study2-replication-v1/pilot-timing-estimate.json` and
`workload-estimate.json`. Counts exclude the preserved pilot:

| Work | Planned / cap |
|---|---:|
| Independent remaining worlds | 56 |
| Original generations | 448 (224 direct, 224 visible) |
| Exact original prompt tokens | 181,276 |
| Generated output tokens | Unknown; maximum 917,504 |
| Visible trajectories for fixed readouts | 224 |
| Checkpoint × cue readouts | At most 2,688 |
| Full candidate-sequence evaluations | At most 8,064 |
| Teacher-forced candidate tokens | At most 16,128 with this pinned tokenizer |
| Measurement answer generations / edited continuations / paid judge calls | 0 / 0 / 0 |

The actual H100 80GB HBM3 pilot recorded 16 direct calls in 5.189 seconds
(80 output tokens) and 16 visible calls in 385.801 seconds (7,006 output tokens).
Multiplying each condition by 14 gives **91.2 minutes** generation time and
99,204 output tokens as a pilot-matched extrapolation. Two observed backend
initializations took 271.0 and 202.4 seconds, averaging **3.94 minutes**.
Generation plus one load is roughly **95 minutes** under the pilot's length
distribution. The complete pilot collection invocation took 695.4 seconds,
including 202.4 seconds loading and 391.0 seconds generating. Its other 102.0
seconds cover boundary extraction, journaling, and related collection work.
Scaling that overhead by 14 adds about 23.8 minutes, giving **about two hours for
collection**. Four examined worlds are a small timing sample; new worlds may
generate substantially longer traces.

No local returned pilot readouts or scoring telemetry were available. The saved
112-slot plan and cached tokenizer imply 231,072 scoring forward-token
occurrences for that pilot plan; multiplying by 14 gives 1,568 readouts,
4,704 candidate sequences, and 3,235,008 forward-token occurrences if the same
eligibility distribution recurs. A conservative full fixed-position ceiling is
8,800,512 forward-token occurrences. These count each serial candidate's prompt,
prefix, cue, and candidate again; they are not generated output tokens.

Using an **unmeasured planning assumption of 800–2,000 scoring forward tokens/s**,
scoring takes about **27–67 minutes** under the pilot-matched eligibility estimate.
Including 91 minutes generation and two average loads yields **2.1–2.8 hours**
of generation/scoring/loading work. Adding the measured collection-overhead
extrapolation gives **2.5–3.2 hours**. New wrapper integrity checks, readout
bookkeeping, CPU reporting, and idle time can add further time. These are
scenarios, not benchmarks or upper bounds.
The `estimate` command deliberately leaves measured scoring and total time null
until genuinely source-bound pilot scoring timings are provided.

At the user's previously displayed **$3.99/hour H100 SXM quote** (a historical
scenario, not a current price check), the scenario including collection overhead
costs approximately **$9.97–$12.66** (about **$10–$13**), excluding storage and idle
time. Collection alone is approximately **$7.91**. Use actual hours × the Pod's
actual quoted hourly rate.

Retain the existing 200 GB workspace volume, one pinned weight copy (~65.52 GB /
61.02 GiB), and existing environment. The replication copy adds about 83 MB before
new journals. Budget several GB for new research outputs and logs. Existing
planning estimates of **68–77 GiB peak GPU memory** and 128–192 GB host RAM are
not measured peaks; this patch makes no memory benchmark claim. It cannot
silently switch to another GPU or quantize after an OOM.

## Offline verification

With the existing test environment and cached tokenizer:

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python -m unittest discover -s tests -p 'test_study2_v5_replication.py' -v
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  python audits/study2-replication-v1/run_full_offline.py
```

Set `QWEN3_TOKENIZER_DIR` to an existing pinned tokenizer-only directory if needed.
The full runner blocks socket connections and writes its machine-readable report
to `/tmp/study2-replication-full-offline-results.json`. Existing tiny random-weight
CPU tests are offline architecture fixtures, not pretrained Qwen3-32B inference.
