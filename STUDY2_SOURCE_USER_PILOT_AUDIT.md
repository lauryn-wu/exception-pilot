# Source-user pilot implementation audit

Baseline and fetched remote: `75d2fd03d8a9bfdf745d313f81d6b7dd504d6f71`,
branch `codex/study2-v5-judge-review-v2`. No later commits or preexisting local changes were present.
No applicable AGENTS.md was found. This audit records the offline handoff before commit/push
authorization. The addition changes no preexisting tracked files.

## Implemented scope and evidence

| Requirement | Result | Evidence |
|---|---|---|
| Independent 12-call pilot; zero main work | Passed offline | Own sibling package, protocol, namespace, plan/request identity and runner; 12 queries, 8 present + 4 MISSING, 192-token ceiling, no main worklist/CLI switch. |
| Actual failed parent provenance | Passed artifact checks; tokenizer replay pending | Supplied archive SHA and all 75 contained file identities authenticated; all sealed JSON checked; actual LIVE_LOCAL request/dispatch journals and original FAILED report verified; 12 returned and no main records. Saved source binding and cell edits verified. |
| Preserve original failure interpretation | Passed | Authenticated v2 report: 8/8 present correct, 0/4 MISSING correct; four length-stopped row copies. V1 remains FAILED. Prior responses are separate from child cache hits. |
| Exact control/source alignment | Passed offline | Parent calibration ordering, source-row hashes, present input IDs, variant pairs and shared single-cell MISSING edit checked on actual saved evidence. New expected values come from source tasks/table edits. |
| Append-only new role bridge | Implemented; synthetic tests passed; real tokenizer NOT TESTED | Sentinel-derived suffix, actual control-ID lookup, exact text/tokenized-template suffix checks, independent new-user render cross-check, preserved original IDs/scaffold and explicit empty-assistant close. Production prepare cannot skip these checks. |
| Whole-response parser | Passed focused tests | Exact A/B/C/MISSING with outer whitespace only, terminal EOS, metadata integrity, 16-token non-EOS length requirement; separate integrity/completion/format/correctness. No prose/quote/row salvage. |
| Call bound and stopping | Passed focused tests | All-correct and all-wrong fake runs make 12 calls/one load; zero main. Completed resume makes zero calls/loads. Ordinary malformed returns collect all controls. |
| Failure, ambiguity, durability | Passed focused tests | First persistent backend exception makes one failed operation and leaves 11 untouched; explicit resume dispatches only those 11. Started/ambiguous entries never resend. Durable raw replies recover after report interruption without inference. |
| Cache identity/locks/archive | Passed focused tests | MOCK/LIVE and cross-version rejection; plan/source/backend mismatch rejection; exclusive locks and source/model/output separation; archive contains parent evidence/contexts and refuses overwrite. |
| Real child plan / live outcomes | NOT TESTED / NOT RUN | Local pinned tokenizer directory is empty and former venv lacks pinned transformer package metadata. No substitute tokenizer or synthetic child plan is presented as a live plan. RunPod preparation must succeed first. |

The original v2 scores are preserved from its authenticated report. They were not re-decoded with
the real tokenizer in this handoff. The parent validator implements original-parser replay and
requires it during production preparation/execution. The precise offline evidence preview is
`audits/study2-source-user-pilot-v1/offline-evidence-preview.json`; it is explicitly NOT a child plan.

The actual parent archive is
`study2-source-report-v2-results-20261017T030153Z.tar.gz`, SHA-256
`ee1ffa85ca03f44562226637a671e388c753ee61bbae75c057858e0369622d59`.
Contained-file mapping digest:
`1de950bb54ce7c64243f76cf5a415fdfe6bc4eebc7053d408992fcc714bf65ca`.
Repackaging identical files is accepted; changing the authenticated parent contents is not.

## Focused test results

Command (no network/inference):

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=tests:. /tmp/study2-qwen3-venv/bin/python -m unittest -v test_study2_source_user_pilot
```

21 tests discovered: **20 passed, 1 skipped, 0 failures/errors**, 18.856 seconds.
The skip is the actual pinned-tokenizer/12-bridge integration check. Its missing assets are not
replaced by synthetic fixtures. The actual saved-parent/source artifact regression did pass.
Only the focused new tests were run; no full historical suite or redundant historical parser suite.
See `audits/study2-source-user-pilot-v1/focused-tests.txt` for the exact output.

CLI help confirms only prepare/inspect/run/archive, with run accepting only output and live-qwen.
Runbook shell blocks were syntax-checked without executing their commands. All new Python files
parse successfully. No source-report v1/v2 runner/session is used for child execution.

## Preservation and remaining limits

All **551 preexisting tracked files** are byte-identical to the baseline; no shared dependencies,
scientific protocols, historical outputs, or old code contracts were edited. The 75 parent files,
parent archive, and 2,105 source files (excluding run.lock files) checked unchanged.

V1 contract: `ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d`.
V2 contract: `163b456eca49796b4d7d6a099f630946044a8a693e8acdc11f808a2f83305675`.
Child contract: `205656521aa4aa5fe30bfec3f54eb1ac365520c33a4599a7b176238ef7c64c38`.
See `audits/study2-source-user-pilot-v1/preservation.json`.

No weights were downloaded, loaded, or hashed; no live model calls, paid judging, GPU provisioning,
original generation, checkpoint scoring, main cases or interventions were executed. Mock test calls
are synthetic only. Real-model compatibility, exact actual bridge serialization, and the 12 child
outcomes remain pending. A real child plan/input-token total is deliberately not fabricated.

The protocol and runbook disclose that structure, wording and response format changed together
on examined development data. Even a complete 12/12 success ends at STOP_AFTER_PILOT and establishes
no long-prefix validity, population result, matched-interface accuracy advantage, or mechanism.

## Added files

- `exception_study2_source_user_pilot/`: nine small modules for frozen identity, parent validation,
  append-only rendering, planning, strict parsing, independent execution, reporting and CLI.
- `tests/test_study2_source_user_pilot.py`.
- `STUDY2_SOURCE_USER_PILOT_PROTOCOL.md`, `STUDY2_SOURCE_USER_PILOT_RUNBOOK.md`, this audit.
- Three offline audit artifacts under `audits/study2-source-user-pilot-v1/`.

The runbook contains the exact checkout, prepare, inspect, explicit live/resume and archive
commands. They use the existing RunPod environment and directories; no new environment setup.
Review the code before a separately authorized push/run, and review all 12 replies before any
larger experiment.
