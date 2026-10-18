# Source-user main v1 — offline implementation audit

Baseline inspected: `c47897b9e12bf6529b0ef3de1a8ce23e97ad9350` on
`codex/study2-v5-judge-review-v2`. The explicit remote-tracking ref matched that revision;
there were no later commits to reconcile and no preexisting working-tree changes.
No applicable `AGENTS.md` was found. This additive patch was handed off uncommitted for
review; the user subsequently authorized committing and pushing it. Publication does not
authorize or execute the main experiment.

## Changed files

- `exception_study2_source_user_main/`: eight new modules for the independent contract,
  immutable evidence, prefix adapter, plan, journaled execution, report, and CLI.
- `STUDY2_SOURCE_USER_MAIN_PROTOCOL.md`: frozen population, prompt/parser/settings, analysis,
  provenance requirements, and STOP_REVIEW_MAIN rule.
- `STUDY2_SOURCE_USER_MAIN_RUNBOOK.md`: exact commands for the existing RunPod checkout,
  environment, assets, prepare/inspect/live-run/resume/archive; no reinstall or download.
- `tests/test_study2_source_user_main.py`: 14 focused tests, using established synthetic
  fixtures plus actual saved evidence. No unchanged parser tests are duplicated.
- `audits/study2-source-user-main-v1/`: test log, real saved-evidence inventory preview,
  preservation hashes, and static-check results. This is an audit, not an executable main plan.

No tracked baseline file was changed. The pilot's k=0 guard and all old packages,
protocols, configuration, shared dependencies, and scientific artifacts remain unchanged.

## Exact verification results

Final focused command, executed in the existing study worktree:

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=tests:. /tmp/study2-qwen3-venv/bin/python -m unittest -v test_study2_source_user_main
```

**14 tests discovered; 13 passed; 1 skipped; 0 failures; 0 errors. Elapsed: 70.769 seconds.**
The saved log is `audits/study2-source-user-main-v1/focused-tests.txt`.
Only this new focused suite was run. The complete historical suite was deliberately not rerun.

The skip is `RealTokenizerTests.test_actual_pilot_reparse_and_all_332_real_tokenizer_contexts`:
the actual pinned tokenizer assets are absent locally. No model/tokenizer downloads were made.
Consequently the unchanged parser has **not been rerun locally on the actual 12 pilot returns**,
and the 332 real-tokenizer bridge constructions/full origin reconstructions have **not been
executed locally**. Synthetic tests exercise those code paths; they do not establish real-tokenizer
compatibility. Production `prepare` requires every one of these checks before a plan can be
prepared or any live model loaded. There is no bypass or skip in production.

Static checks passed: Python AST parsing of all nine new Python files, CLI `--help`,
and `bash -n` for all 12 runbook shell blocks. None of the runbook commands were executed.

## Requirement evidence

| Requirement | Status | Evidence / limit |
|---|---|---|
| Preserve historical code and outputs | PASSED | SHA-256 equality for all 567 tracked baseline files, all 170 extracted pilot files, and the original archive. All three old contracts match exactly. During the read-only audit, 2,105 original files and the one exported readout summary also remained byte-identical. |
| Authenticate immutable real pilot execution | PASSED for saved journals/provenance; tokenizer-dependent reparse NOT TESTED locally | The actual sealed plan/contract, 12 LIVE_LOCAL returned journals, dispatch bindings, sealed preparation and live invocation validate. One invocation records 12 calls and one load. All 12 saved texts match truth and carry terminal-EOS metadata. The mutable archived report records zero new calls, correctly accepted. Full unchanged-parser recomputation is mandatory in production preparation. |
| Preserve v1/v2 failures and no v2 main execution | PASSED for saved artifacts/journals | Original v1/v2 FAILED evidence preserved; v2 saved result is 8/8 present and 0/4 MISSING. The read-only v2 journal validator finds only its 12 calibration operations and zero main records, including request-only records. Tokenizer-dependent reparse remains part of production preparation. |
| Fixed main inventory and raw joins | PASSED for real saved inventory/bindings | Exact authoritative ordered 332 query hashes and source-row/input/prefix/boundary bindings checked against original records; 664 raw saved join hashes and probability arithmetic validated. Counts are 112/112/108 at k=0/256/512. Four original exclusions preserved. Full tokenizer-derived reconstruction equality is additionally enforced in production. |
| Honest legacy provenance | PASSED | Local audit input is an exported summary; original v2 plan records native journals. Values are checked against all original hashes without upgrading current provenance. Production preserves whichever validated provenance is actually supplied. |
| Thin append-only adapter | PASSED with synthetic tokenizer; actual-tokenizer integration NOT TESTED locally | Tests check all 332 inputs, exact saved IDs, k=0 equivalence, nonzero prefix preservation, role offsets, empty-assistant metadata, no v2 suffix, and no audit metadata in input. The unchanged pilot bridge is called with original input IDs only. |
| Main-only 332-call execution | PASSED with fake backend | A complete run makes exactly 332 calls and one load, with no pilot/original/legacy/judge calls. Completed resume makes zero calls and zero loads. Each response serves both cue comparisons. Budget is 16 and capture_at is empty. |
| Outcome failures do not trigger retry or stop | PASSED with fake backend | Wrong label, valid MISSING, verbose, length-stopped, and malformed payloads are terminal returns; the mixed run collects all 332 and completed resume makes no calls. |
| First backend exception and safe resume | PASSED with fake backend | Persistent failure makes exactly one main dispatch, one failed operation and 331 untouched operations. Resume executes exactly the 331 never-started IDs and retains failed journals byte-for-byte. Returned and ambiguous operations are not resent. |
| Durable raw results / identity / locking | PASSED | Reporting interruption after durable returns does not repeat inference. Tests reject source, join, boundary, pilot, plan, backend, mode and cross-version mismatches before dispatch; lock and output-separation checks pass. No old execution entry point is used. |
| Frozen categories, denominators and comparisons | PASSED | All-returned denominator, five distinct unsuccessful outcome categories, unavailable coverage, exact ties, joint/conditional preference denominators, common-pair counts 112/108/108, paired transitions, and 112 unique natural trajectories tested. Degenerate bootstrap intervals carry the required caveat. |
| Invocation and cumulative accounting | PASSED | Prior pilot counters remain distinct from new calls; started operation slots include possible ambiguous dispatches, finished-invocation call/load totals are separate, and interrupted/ambiguous accounting is explicitly marked incomplete. |
| Single evidence snapshot / archive | PASSED with fixtures | Archive includes one pilot snapshot with nested v2 once, main plan, contexts, journals, source rows and 664 raw joins/provenance. No overwrite, duplicate historical trees or weights. Mutable parent top-level report refresh is accepted without changing scientific identity. |
| Actual main inference | NOT TESTED / NOT RUN | Zero Qwen calls, CUDA initialization, weight loads/hashes/downloads, paid judging, or cloud operations. No actual main results or executable real-tokenizer child plan were produced locally. |

## Real saved-evidence preview

`audits/study2-source-user-main-v1/offline-evidence-preview.json` lists all 332 origin mappings
in frozen order, source/boundary/prefix hashes, both raw-join references, the four exclusions,
the pilot's 12 raw saved replies and immutable execution counts, and the retained v1/v2 history.
It is clearly labeled **not an executable child plan**. It records the unavailable tokenizer
checks and leaves the new-context input-token total unset. No synthetic context is presented
as a real Qwen-tokenizer validation.

Inventory: **56 worlds (004–059), 112 original-visible trajectories, 332 contexts, 664 reused
cue measurements, maximum 332 new calls / 5,312 output tokens, zero new calibration calls.**
The k=512 exclusions remain world011/v1, world026/v0, world027/v0 and world059/v1, each with
its original `short_or_at_answer_or_inexact_boundary` reason and source binding. Earlier cuts
for those trajectories remain included.

## Preservation identities

Full per-file hashes and before/after counts are in `audits/study2-source-user-main-v1/preservation.json`.
The original/readout before/after comparison covers the read-only audit; tracked/pilot/archive
baseline hashes were recorded before implementation. The existing artifact helper excludes `run.lock`.

| Identity | SHA-256 / content contract |
|---|---|
| Supplied pilot archive | `e86beedf42aad37c05d1fa419567fc9811e682b7a2c6f24b65f20f11c720fe30` |
| Pilot plan | `9ac5b3b944e51251629620a40c6da83a6e2a9d6529cb4c37088fc82df3b77132` |
| Failed v2 plan | `96102449686561c92f3be4581cf97953568c65e48ac0d95e5589ebc88431f1db` |
| V1 contract, unchanged | `ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d` |
| V2 contract, unchanged | `163b456eca49796b4d7d6a099f630946044a8a693e8acdc11f808a2f83305675` |
| Source-user pilot contract, unchanged | `205656521aa4aa5fe30bfec3f54eb1ac365520c33a4599a7b176238ef7c64c38` |
| New main code/protocol contract | `254e70cbcf4dfcb9d37c922c9973a3de2c63b7e1fccc54bfd88eeeb513fa588a` |

## Handoff and limits

Use `STUDY2_SOURCE_USER_MAIN_RUNBOOK.md` after a separately authorized push and review of
that revision. Prepare the distinct main directory once with the real pinned local tokenizer;
stop on any authentication, construction or binding failure. Inspect the frozen plan before
explicit `--live-qwen`. Resume uses the same output and never resends failed/ambiguous calls.
Archive without overwrite and stop at **STOP_REVIEW_MAIN**.

Correct recovery can involve rereading the still-available source. Other outcomes do not
establish forgetting or override. Cached restricted A/B/C preferences use a different interface.
Main worlds were not used for the elicitation pilot, but their prior trajectories/readouts
had been examined. Nonzero prefixes differ between variants. No main outcomes were inspected
or used to tune this patch.
