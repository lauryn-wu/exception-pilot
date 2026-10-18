# Results index

Updated **2026-10-18** with the later Qwen Study 2 results, downstream control exports, and independent audits. The October 13 collection of 33 archives is retained below. The additions preserve failed calibrations, invalid answers, earlier review snapshots, and unexecuted proposals. Archive counts are containers, not independent experiments; several include overlapping parent evidence.

This update archives existing outputs only. **No model calls or experiment reruns were made.** Experimental implementations remain on their existing branches; this commit does not merge or change them.

## Branch and local-export gap check

A further October 18 audit checked all **18 published experiment/archive branches** against main, including archived member hashes rather than filenames alone. Earlier branches' tracked raw results were already present. The following previously missing local exports are now preserved:

| Run / export | Saved result | Files |
|---|---|---|
| Qwen v3 technical validation | **FAILED**; scientific 48-response selection was blocked | [status](reports/study2-qwen-v3-failed-validation/validation-status.json) · [compact diagnostic](reports/study2-qwen-v3-failed-validation/validation-compact-summary.txt) · [full export](archives/study2-validation-audit.tar.gz) · [subset export](archives/qwen3-32b-selection-runpod-44pCvsSf-validation-audit.tar.gz) |
| Qwen v4 pilot | Technical same-input check passed; **8/48 originals**, incomplete. Four direct answers correct; all four visible responses truncated at 512 tokens | [selection report](reports/study2-v4-pilot/selection-report-v4.json) · [traces](reports/study2-v4-pilot/pilot-traces.txt) · [archive](archives/study2-v4-pilot-backup.tar.gz) |
| Qwen length diagnostic | **4/4 fresh generations** at 2048 tokens. Four prefix matches and EOS completions; strict parser: one wrong, three invalid, zero correct | [saved report and complete case text](reports/study2-qwen-length-diagnostic/diagnostic-results.json) |
| Qwen expanded screen | **16/16** exploratory generations. Direct: 8/8 strict-correct. Visible: 2/8 strict-correct, 5/8 strict-valid; separate tolerant parser: 4/8 correct, 8/8 valid. No truncations | [saved report and complete case text](reports/study2-qwen-expanded-screen/screen-results.json) |

Both v3 archives preserve the **same failed validation**, not two experiments: all 12 regular members of the smaller export match members in the larger export. The v4 pilot remains incomplete; the longer diagnostics do not fill or relabel its missing tasks. The two diagnostic JSON reports include case text, but separate complete operation-journal exports were not located. No missing scientific result has been inferred from a passing technical check.

The [branch-artifact index](branch-artifacts/2026-10-18/README.md) preserves 161 previously unarchived audit/preview/documentation files and five context documents, with byte-level source bindings in its [inventory](branch-artifacts/2026-10-18/inventory.json). These are **offline records**, not additional model generations. In particular, the native-thinking draft has no located live results; its main budget still awaits pilot review. Existing scientific code branches remain separate, consistent with the results-and-documentation-only consolidation.

This covers located results in the inspected Git branches and local exports. It cannot certify unexported results on remote machines. Historical DeepSeek-prefix and original conditional stage-2 exports are still not located.

## October 18 result additions

| Run / export | Returned / planned | Status and scope | Files |
|---|---:|---|---|
| Qwen Study 2 v5 trace export | Original trajectories and saved checkpoint evidence | Raw exported collection; use its frozen internal plans and journals | [archive parts](archives/study2-v5-traces-for-audit.tar.gz.parts/) · [independent trace audit](analyses/2026-10-18/full_trace_audit/study2-v5-trace-audit.html) |
| source-report v1 | Calibration 12/12; main 0/332 | Calibration FAILED; main never started | [report](reports/study2-source-report-v1/report.md) · [archive](archives/study2-source-report-v1-results.tar.gz) |
| source-report v2 | Calibration 12/12; main 0/332 | Calibration FAILED; main never started | [report](reports/study2-source-report-v2/report.md) · [archive](archives/study2-source-report-v2-results-20261017T030153Z.tar.gz) |
| source-user pilot v1 | 12/12 | 12 correct; STOP_AFTER_PILOT | [report](reports/study2-source-user-pilot-v1/report.md) · [archive](archives/study2-source-user-pilot-v1-results-20261017T234902Z.tar.gz) |
| source-user main v1 | 332/332 | LIVE_LOCAL; STOP_REVIEW_MAIN; original trajectories reused | [report](reports/study2-source-user-main-v1/report.md) · [audit](analyses/2026-10-18/Study2_Source_User_Main_Audit.md) · [archive parts](archives/study2-source-user-main-v1-results-20261018T151948Z.tar.gz.parts/) |
| downstream-history-gpt4o-001 | 216/216 | exploratory_complete_with_invalid;212 valid, 4 invalid | [report](reports/downstream-history-gpt4o-001/summary.md) · [archive](archives/downstream-history-gpt4o-001-results.zip) |
| downstream-rule-gpt4o-001 | 432/432 | exploratory_complete_with_invalid;414 valid, 18 invalid | [report](reports/downstream-rule-gpt4o-001/summary.md) · [archive](archives/downstream-rule-gpt4o-001-results.zip) · [second uploaded container](archives/downstream-rule-gpt4o-001-results-upload2.zip) |

The two downstream-rule ZIPs have different ZIP bytes but identical contents for all 443 regular members. They are **the same run**, not replications. Both original containers are preserved because the independent audit binds the second uploaded container's SHA256.

The two largest tar.gz exports are stored as numbered binary parts because of the upload interface's request-size limit. Their concatenation exactly reproduces the original archive bytes. From the repository root:

```bash
python3 results/verify_results.py
python3 results/restore_archives.py
```

Verification can inspect the parts directly; restoration creates the two original archive filenames and refuses to overwrite mismatching existing files. See [verification instructions](VERIFY.md).

## Independent analyses and earlier review material

Start with the [analysis index](analyses/2026-10-18/README.md): main-source-query audit, full-trace annotations, historical experiments without the MISSING conditional, and the 104-prefix semantic audit. These are analyses of existing outputs, not additional live experiments. Manual semantic annotations are exploratory and should not be read as ground truth about hidden model state.

Also retained: [earlier v5 pilot review](archives/study2-v5-pilot-review.tar.gz), [earlier v2 implementation review](archives/study2-v2-review-audit.zip), [replication analysis](analyses/2026-10-18/prior-review/replication-analysis.json), and [judge audit](analyses/2026-10-18/prior-review/study2-v5-judge-audit.json). Earlier snapshots may overlap later evidence; retain their original failure and limitation records.

The [follow-up plans](plans/README.md) are **unexecuted**. The 208-continuation source/history crossing is on hold. The 27-continuation availability diagnostic is an offline draft requiring tokenizer validation and semantic review; no intervention result is claimed.

The Qwen source-user implementation used commit [`7f78a333`](https://github.com/lauryn-wu/exception-pilot/commit/7f78a3338225614535b90a0d520ef6c346282d13) on `codex/study2-v5-judge-review-v2`. Earlier archives retain their own execution provenance. A code branch association is not a substitute for the archived execution identity.

## Preserved October 13 collection

Historical inventory dated **2026-10-13**. This directory consolidates all available result exports found in the exception-pilot worktrees and related Downloads folder: **33 distinct archives**, with byte-identical copies deduplicated. Failed checks, invalid responses, interrupted states and unstarted plans are retained. No new model calls or scientific reanalysis were performed.

Start here or with the [branch/experiment status](BRANCH_STATUS.md). Counts describe collection coverage, **not scientific success**. Original reports retain their interpretations. Historical implementation audits can say "not run" even when a later live result is now available here. Experimental code branches remain separate.

## Recent experiments with local results

| Run / snapshot | Returned / planned | Saved analysis status | Files |
|---|---:|---|---|
| columns-gpt4o-001 | 576/576 | exploratory_complete | [report](reports/columns-gpt4o-001/summary.md) · [archive](archives/columns-gpt4o-001-results.zip) |
| downstream-gpt4o-001 | 342/342 | exploratory_complete | [report](reports/downstream-gpt4o-001/summary.md) · [archive](archives/downstream-gpt4o-001-results.zip) |
| evidence-role-gpt4o-001 | 480/480 | complete_ready_for_interpretation; no_automatic_followup | [report](reports/evidence-role-gpt4o-001/summary.md) · [archive](archives/evidence-role-gpt4o-001-results.zip) |
| features-gpt4o-001 | 648/648 | exploratory_complete | [report](reports/features-gpt4o-001/summary.md) · [archive](archives/features-gpt4o-001-results.zip) |
| instruction-interface-gpt4o-001 | 192/192 | COMPLETE | [report](reports/instruction-interface-gpt4o-001/summary.md) · [archive](archives/instruction-interface-gpt4o-001-results.zip) |
| ordering-live | 7,680/7,680 | ALL_PLANNED_RETURNS_PRESENT | [report](reports/ordering-live/summary.md) · [archive](archives/ordering-live-results.zip) |
| query-form-gpt4o-001 | 288/288 | complete; stop_query_form | [report](reports/query-form-gpt4o-001/summary.md) · [archive](archives/query-form-gpt4o-001-snapshot-ecf5c541e60f.zip) |
| query-form-mistral-001 | 288/288 | complete; output_manipulation_inconclusive | [report](reports/query-form-mistral-001/summary.md) · [archive](archives/query-form-mistral-001-snapshot-8fd0a84243a4.zip) |
| row-position-confirm-mistral-001 (2026-10-12T05:23:49 UTC) | 960/960; 1 transport errors retained | complete; confirm_positive_interaction | [report](reports/row-position-confirm-mistral-001--20261012T052349Z/summary.md) · [archive](archives/row-position-confirm-mistral-001-snapshot-fee0844b1f94.zip) |
| row-position-confirm-mistral-001 (2026-10-12T23:45:28 UTC) | 960/960 | complete; confirm_positive_interaction | [report](reports/row-position-confirm-mistral-001--20261012T234528Z/summary.md) · [archive](archives/row-position-confirm-mistral-001-results.zip) |
| row-position-mistral-001 | 288/288 | complete; review_fresh_world_confirmation | [report](reports/row-position-mistral-001/summary.md) · [archive](archives/row-position-mistral-001-results.zip) |

**Row-position confirmation has two live executions of the same 960-task plan**, begun at 2026-10-12 05:23:49 UTC and 23:45:28 UTC. All 960 complete attempt records differ between executions. Both are preserved separately. They reuse worlds/tasks, so they are not fresh-world replications of one another; this archive neither pools them nor selects the more favorable outcome.

The evidence-ordering run has 7,680 returns, but its local token audit reports only **112/960 exact token matches** and is not verified provider serialization. Feature-support semantic coding remains unreviewed. Collection completeness does not remove these limitations.

## Earlier studies, failed checks and exploratory Mistral work

| Run / snapshot | Returned / planned | Saved analysis status | Files |
|---|---:|---|---|
| constrained-cue-001 | 96/96 | complete_ready_for_interpretation | [report](reports/constrained-cue-001/summary.md) · [archive](archives/constrained-cue-001.zip) |
| counterfactual-001 | 160/160 | ALL_PLANNED_RETURNS_PRESENT | [report](reports/counterfactual-001/summary.md) · [archive](archives/counterfactual-001.zip) |
| cue-001 | 144/144 | complete_ready_for_interpretation | [report](reports/cue-001/summary.md) · [archive](archives/cue-001.zip) |
| explanation-001 | 384/384 | complete_ready_for_interpretation | [report](reports/explanation-001/summary.md) · [archive](archives/explanation-001.zip) |
| factorial-001 | 640/640; 1 invalid | technical_failure | [report](reports/factorial-001/summary.md) · [archive](archives/factorial-001-recovered.zip) |
| missingness-001 | 10/40 | replay_gate_failed_stop | [report](reports/missingness-001/summary.md) · [archive](archives/missingness-001.zip) |
| mistral-framing-001 | 673/673 | exploratory_intervention_complete | [report](reports/mistral-framing-001/report.md) · [archive](archives/mistral-framing-001-results.zip) |
| mistral-map-001 | 6/1,075; 1 invalid | sampling_check_failed_stop | [report](reports/mistral-map-001/summary.md) · [archive](archives/mistral-map-001-snapshot-531e516b5676.zip) |
| mistral-map-v2-001 | 9/1,075; 1 invalid | sampling_check_failed_stop | [report](reports/mistral-map-v2-001/summary.md) · [archive](archives/mistral-map-v2-001-snapshot-6ec09bd13ed7.zip) |
| mistral-map-v3-001 | 1,075/1,075; 2 invalid, 3 transport errors retained | exploratory_map_complete_with_unscorable | [report](reports/mistral-map-v3-001/summary.md) · [archive](archives/mistral-map-v3-001.zip) |
| mistral-prefix-001 | 1/73; 1 invalid, 6 transport errors retained | capability_failed_stop | [report](reports/mistral-prefix-001/summary.md) · [archive](archives/mistral-prefix-001-snapshot-753eeb8a7925.zip) |
| mistral-prefix-v2-001 | 73/73 | replay_failed_stop | [report](reports/mistral-prefix-v2-001/summary.md) · [archive](archives/mistral-prefix-v2-001.zip) |
| mistral-small-2603-20261012-204146 | Technical check | FAILED_TECHNICAL_CAPABILITY_CHECK | [report](reports/mistral-small-2603-20261012-204146/report.json) · [archive](archives/mistral-small-2603-20261012-204146-snapshot-404b8ca8ac50.zip) |
| order-001 | 72/72 | complete_ready_for_interpretation | [report](reports/order-001/summary.md) · [archive](archives/order-001.zip) |
| query-role-001 | 144/144 | screen_complete | [report](reports/query-role-001/report.md) · [archive](archives/query-role-001.zip) |
| reference-001 | 1,200/1,200; 4 transport errors retained | ALL_PLANNED_RETURNS_PRESENT | [report](reports/reference-001/summary.md) · [archive](archives/reference-001.zip) |
| revision-001 | 192/192 | complete_ready_for_interpretation | [report](reports/revision-001/summary.md) · [archive](archives/revision-001.zip) |
| wording-001 | 480/480 | ALL_PLANNED_RETURNS_PRESENT | [report](reports/wording-001/summary.md) · [archive](archives/wording-001.zip) |

The [original factorial export](archives/factorial-001.zip) has 596 attempts (595 valid and one invalid). The [recovered export](archives/factorial-001-recovered.zip) has 640 returned (639 valid and one invalid), with 19 complete lists. They are snapshots of the same run, not independent experiments; the invalid response is retained.

The selected-case missingness replay stopped after 7/10 replays matched. The Mistral prefix/map failures remain failed results. The current Study 2 Mistral API route is closed: saved responses reject logprobs/prompt logprobs, and both character-prefix replays failed. These technical artifacts cannot become Qwen natural trajectories.

## Unstarted plans and previews

| Run / snapshot | Returned / planned | Saved analysis status | Files |
|---|---:|---|---|
| continuation-v3-qwen3-32b-selection-001 | 0/48 | UNSTARTED_OR_PREVIEW | [report](reports/continuation-v3-qwen3-32b-selection-001/selection-summary.md) · [archive](archives/continuation-v3-qwen3-32b-selection-001-snapshot-0e61ddfbee85.zip) |
| instruction-interface-gpt4o-001 | 0/192 | INCOMPLETE | [report](reports/instruction-interface-gpt4o-001--unstarted/summary.md) · [archive](archives/instruction-interface-gpt4o-001-snapshot-7ba3f65dc7d1.zip) |
| ordering-preview | 0/7,680 | UNSTARTED_OR_PREVIEW | [archive](archives/ordering-preview-snapshot-4629ed76162c.zip) |

At the October 13 inventory, no live result export was located for the **216-call matched downstream history control**. Its completed export is now preserved in the October 18 addition above. The completed 342-call downstream text-edit study is a different experiment. No separate result export was located for the historical DeepSeek prefix alternative or the original pilot's conditional stage-2 diagnostics. "Not found" refers to inspected local folders/Git branches, not inaccessible cloud machines.

## Layout and preservation

- `archives/`: original ZIP bytes and additional local snapshots. New snapshots omit only OS metadata and transient `run.lock` files.
- `reports/<run>/`: unchanged reports/tables copied from each archive; full requests, plans, execution records and raw attempts remain in the ZIPs.
- `audits/`: unchanged historical implementation checks, rationale audits and the tokenizer-only Qwen audit; these are not new live or human-certified semantic results.
- [manifest.json](manifest.json): hashes, snapshot identities, source checkout provenance and report-to-archive mappings.
- `manifests/`: per-member size/SHA-256 inventories for every ZIP.
- [SHA256SUMS](SHA256SUMS) and [verification instructions](VERIFY.md): offline integrity checks.

All original local folders and experimental branches remain untouched. No credentials, models or tokenizer downloads are included. Distinct exports remain separate even when names/plan hashes coincide. Only byte-identical redundant ZIP copies were removed from the repository layout.

Use each frozen original plan/configuration and its [source branch](BRANCH_STATUS.md). Do not overwrite an existing run or assume default-branch code can resume it. Manifest source checkout commits identify the copies inspected, not necessarily the code used at collection. Historical audit documents are preserved verbatim: references there to root-level ZIPs now correspond to `results/archives/`, and reproduction scripts may live on their original branch.
