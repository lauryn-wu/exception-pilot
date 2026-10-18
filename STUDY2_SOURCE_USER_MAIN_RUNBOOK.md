# Fixed 332-context source-user main: operator runbook

Review this implementation before execution. This offline handoff does not itself push the patch
or run the experiment. After a separately authorized push, use the commands below on the existing
RunPod checkout. The pushed revision is reviewed before any main inference.

## 1. Update the existing branch

GitHub CLI authentication already works. Use the existing gh browser/device authentication if it
needs renewal; never an account password. No environment reinstall, model download or reclone.
Stop on any Git error and preserve local changes.

```bash
cd /workspace/exception-pilot
git status --short --branch
git fetch origin refs/heads/codex/study2-v5-judge-review-v2:refs/remotes/origin/codex/study2-v5-judge-review-v2
```

```bash
if git show-ref --verify --quiet refs/heads/codex/study2-v5-judge-review-v2; then git switch codex/study2-v5-judge-review-v2; else git switch --track -c codex/study2-v5-judge-review-v2 origin/codex/study2-v5-judge-review-v2; fi
git merge --ff-only origin/codex/study2-v5-judge-review-v2
test -f exception_study2_source_user_main/__main__.py
```

If the final check fails, the main patch is not present. Stop; do not rerun the pilot or v2.

## 2. Existing environment and directories

```bash
source /workspace/venvs/study2-qwen3/bin/activate
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
export SOURCE_USER_PILOT=/workspace/study2-source-user-pilot-v1
export SOURCE_USER_MAIN=/workspace/study2-source-user-main-v1
```

```bash
export ORIGINALS=/workspace/study2-v5-replication-v1/originals
export LEGACY_READOUTS=/workspace/study2-v5-replication-v1/readouts-remaining-v1
```

Keep the completed pilot and its nested failed-v2 evidence unchanged. The pilot plan must be
`9ac5b3b944e51251629620a40c6da83a6e2a9d6529cb4c37088fc82df3b77132`.
Its archived report has zero *this invocation* calls; sealed cumulative execution is one load and
12 new calls. The validator checks that execution and reparses all twelve raw replies.

## 3. Prepare once, offline

```bash
python -m exception_study2_source_user_main prepare --pilot "$SOURCE_USER_PILOT" --originals "$ORIGINALS" --readouts "$LEGACY_READOUTS" --tokenizer-dir "$STUDY2_MODEL_DIR" --output "$SOURCE_USER_MAIN"
```

**Stop on any preparation failure.** This command validates the successful pilot, original v1/v2
failures, all origins/664 cached joins and all **332 real pinned-tokenizer context constructions**,
without loading/hashing/downloading weights or initializing CUDA. It preserves the exact prompt,
parser, settings, inventory, exclusions and source IDs. Missing or changed evidence blocks it.

A successful preparation freezes `main-plan.json`, `legacy-values.json`, one `pilot-evidence/`
snapshot (nested v2 once), 112 source rows, and `contexts/000.txt`–`contexts/331.txt`.
Audit metadata appears outside the actual model input in these readable files.

If the output already contains a plan or partial run, **do not prepare another output**. Inspect
and resume this same directory. Never delete journals or reprepare to resample outcomes.

```bash
python -m exception_study2_source_user_main inspect --output "$SOURCE_USER_MAIN"
```

Before live execution, review the frozen plan and readable contexts. Required inventory:
56 worlds, 112 trajectories; checkpoint counts 112/112/108; 332 new queries; 664 reused joins;
zero new pilot/original/readout/judge calls; at most 5,312 output tokens. The four original k=512
exclusions remain eligible at earlier cuts. Inspect is offline. `run` without `--live-qwen` also
stays offline and writes a readable report.

## 4. Only after review: execute the fixed main worklist

```bash
python -m exception_study2_source_user_main run --output "$SOURCE_USER_MAIN" --live-qwen
```

One necessary live invocation loads the unchanged original Qwen backend once. It makes one
16-token-maximum generation per context, not one per cue. It does not run the pilot again.
Wrong/MISSING/verbose/truncated/malformed returns remain cached and collection continues.
The first backend exception stops dispatch and leaves later operations untouched.

After resolving a runtime issue, explicit resume uses exactly the same command and directory:

```bash
python -m exception_study2_source_user_main run --output "$SOURCE_USER_MAIN" --live-qwen
```

Returned, failed and ambiguous operations are never resent; only never-started work executes.
Completed or blocked invocations load zero models. Raw replies survive reporting interruption.
Do not tune prompts, parser, budget or selection after seeing outcomes.

## 5. Inspect, export, and stop for review

```bash
python -m exception_study2_source_user_main inspect --output "$SOURCE_USER_MAIN"
```

`report.json` and `report.md` retain every reply, source truth, strict score, status and both cached
cue joins. Primary accuracy includes all returned outcomes; unavailable work is coverage, not error.
Paired summaries use common eligible/returned trajectories, separate from unpaired checkpoints.
Ceiling/degenerate bootstrap intervals do not imply population certainty. Cached restricted ABC
preferences use another interface and do not constitute matched generated-answer accuracy.

```bash
python -m exception_study2_source_user_main archive --output "$SOURCE_USER_MAIN" --archive "/workspace/study2-source-user-main-v1-results-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
```

Export is offline and refuses overwrite. It includes the main plan, contexts, journals, reports,
timing/provenance, one pilot snapshot, 112 source rows and 664 required raw legacy values, without
weights or duplicate historical experiment trees. It refreshes only derived main reports.

**STOP_REVIEW_MAIN.** Review these outcomes before any separately specified experiment.

## Focused offline checks

```bash
PYTHONPATH=tests:. python -m unittest -v test_study2_source_user_main
```

For real saved evidence/tokenizer checks in the existing environment:

```bash
export STUDY2_SOURCE_USER_PILOT="$SOURCE_USER_PILOT" STUDY2_SOURCE_REPORT_ORIGINALS="$ORIGINALS" STUDY2_SOURCE_REPORT_READOUTS="$LEGACY_READOUTS" QWEN3_TOKENIZER_DIR="$STUDY2_MODEL_DIR"
PYTHONPATH=tests:. python -m unittest -v test_study2_source_user_main.SavedEvidenceTests test_study2_source_user_main.RealTokenizerTests
```

These perform no inference. When actual assets are absent, integration tests report a skip; production
preparation never skips the real-tokenizer requirement. No full historical-suite rerun is needed.
