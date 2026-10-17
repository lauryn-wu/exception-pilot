# Source-user pilot: operator runbook

Review the code/protocol before running the pilot. The Git commands below update the existing
checkout from `codex/study2-v5-judge-review-v2`. They must leave local changes intact; stop on a
Git conflict. Publishing this implementation does not execute or expand the pilot.
Do not run an earlier source-present amendment, v1/v2 runner, or any main cases.

## 1. Update the existing checkout

GitHub authentication already works through gh. No account password or environment reinstall is needed.

```bash
cd /workspace/exception-pilot
git status --short --branch
git fetch origin refs/heads/codex/study2-v5-judge-review-v2:refs/remotes/origin/codex/study2-v5-judge-review-v2
```

```bash
if git show-ref --verify --quiet refs/heads/codex/study2-v5-judge-review-v2; then git switch codex/study2-v5-judge-review-v2; else git switch --track -c codex/study2-v5-judge-review-v2 origin/codex/study2-v5-judge-review-v2; fi
git merge --ff-only origin/codex/study2-v5-judge-review-v2
test -f exception_study2_source_user_pilot/__main__.py
```

If the final file check fails, the reviewed patch is not on that checkout yet. Stop; do not run v2 again.
No reset, clean, reclone, forced checkout, or discarded local work is needed.

## 2. Activate the existing environment and paths

```bash
source /workspace/venvs/study2-qwen3/bin/activate
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false PYTHONDONTWRITEBYTECODE=1
export STUDY2_MODEL_DIR=/workspace/models/Qwen3-32B/9216db5781bf21249d130ec9da846c4624c16137
export SOURCE_REPORT_V2=/workspace/study2-source-report-v2
export SOURCE_USER_PILOT=/workspace/study2-source-user-pilot-v1
```

The parent must be the actual failed run, plan hash
`96102449686561c92f3be4581cf97953568c65e48ac0d95e5589ebc88431f1db`.
Keep its original plan, locations, 12 journals, raw replies and FAILED report unchanged.
The original source location is read from its `locations.json`.
No new model download or reinstallation is part of this pilot.

## 3. Prepare offline once, then inspect

```bash
python -m exception_study2_source_user_pilot prepare --parent "$SOURCE_REPORT_V2" --tokenizer-dir "$STUDY2_MODEL_DIR" --output "$SOURCE_USER_PILOT"
```

Preparation validates all parent evidence, the unchanged model/tokenizer identity and exact source
controls. It requires the actual pinned tokenizer/template and verifies all 12 appended bridges,
without loading, hashing or downloading weights. It freezes the plan, preserves a parent snapshot,
and exports `contexts/00.txt` through `contexts/11.txt`. Missing/different evidence or assets is a
hard stop. Do not bypass it or change the parent's frozen paths/plan in place.

If this output already has a plan, do not prepare another output: use inspect/resume on the same one.
If preparing a relocated **offline** export elsewhere, `--originals /actual/existing/originals` and
`--tokenizer-dir /actual/existing/pinned/assets` are explicit read-only path overrides. They do not
change source/backend identities or make a different backend eligible for live execution.

```bash
python -m exception_study2_source_user_pilot inspect --output "$SOURCE_USER_PILOT"
```

Before running, review `pilot-plan.json`, the 12 readable context files, and the protocol. Require
12 queries, 8 present + 4 MISSING, k=0 only, main_planned=0, maximum 192 output tokens, parent FAILED.
A default `run` without `--live-qwen` is also offline and writes a readable report.

## 4. Only after review: run the 12-call pilot

```bash
python -m exception_study2_source_user_pilot run --output "$SOURCE_USER_PILOT" --live-qwen
```

One necessary live invocation loads the original Qwen backend once. It generates at most 12 new
answers, at most 16 tokens each, then stops. Ordinary wrong/verbose/truncated/malformed returns
remain cached and collection continues. The first backend exception stops that invocation;
failed and ambiguous calls are never automatically resent.

After resolving a runtime issue, **explicit resume uses precisely the same command and output**:

```bash
python -m exception_study2_source_user_pilot run --output "$SOURCE_USER_PILOT" --live-qwen
```

It dispatches only never-started cases. Completed or terminally blocked work loads no model.
Preserve failed/ambiguous cases; do not create another directory to resample them.
A failed backend identity/preparation/cache check is a hard stop before any generation.

## 5. Inspect, archive, and stop for review

```bash
python -m exception_study2_source_user_pilot inspect --output "$SOURCE_USER_PILOT"
```

Read `report.json` and `report.md`: all 12 new raw replies and strict EOS scores, prior v2 replies
under their original parser, separate 8/4 denominators, variant pairs, operation coverage, and calls.
A complete result says `STOP_AFTER_PILOT`, whether PASSED or FAILED. An incomplete result lists
unresolved operations and has no main eligibility. Even 12/12 is development evidence only.

```bash
python -m exception_study2_source_user_pilot archive --output "$SOURCE_USER_PILOT" --archive "/workspace/study2-source-user-pilot-v1-results-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
```

Archive is offline, validates the cache, refreshes derived reports, and refuses overwrite. It includes
the child plan, readable contexts, raw journals, timing/provenance, eight source rows, tokenizer
identity, and one immutable parent-evidence snapshot. No model weights or historical experiment
trees are copied. Review these 12 outcomes before deciding whether any larger experiment is worthwhile.

## Focused offline tests

```bash
PYTHONPATH=tests:. python -m unittest -v test_study2_source_user_pilot
```

To include the actual parent/tokenizer integration on RunPod:

```bash
export QWEN3_TOKENIZER_DIR="$STUDY2_MODEL_DIR" STUDY2_SOURCE_USER_PARENT="$SOURCE_REPORT_V2" STUDY2_SOURCE_REPORT_ORIGINALS=/workspace/study2-v5-replication-v1/originals
PYTHONPATH=tests:. python -m unittest -v test_study2_source_user_pilot.RealIntegrationTests
```

Tests never call live inference. The real integration check skips when local tokenizer assets are
absent; production preparation never skips it. No historical full-suite rerun is required.
