# Results index

Inventory dated **2026-10-13**. This directory consolidates all available result exports found in the exception-pilot worktrees and related Downloads folder: **33 distinct archives**, with byte-identical copies deduplicated. Failed checks, invalid responses, interrupted states and unstarted plans are retained. No new model calls or scientific reanalysis were performed.

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

No live result export was located for the **216-call matched downstream history control**. The completed 342-call downstream text-edit study is a different experiment. No separate result export was located for the historical DeepSeek prefix alternative or the original pilot's conditional stage-2 diagnostics. "Not found" refers to inspected local folders/Git branches, not inaccessible cloud machines.

## Layout and preservation

- `archives/`: original ZIP bytes and additional local snapshots. New snapshots omit only OS metadata and transient `run.lock` files.
- `reports/<run>/`: unchanged reports/tables copied from each archive; full requests, plans, execution records and raw attempts remain in the ZIPs.
- `audits/`: unchanged historical implementation checks, rationale audits and the tokenizer-only Qwen audit; these are not new live or human-certified semantic results.
- [manifest.json](manifest.json): hashes, snapshot identities, source checkout provenance and report-to-archive mappings.
- `manifests/`: per-member size/SHA-256 inventories for every ZIP.
- [SHA256SUMS](SHA256SUMS) and [verification instructions](VERIFY.md): offline integrity checks.

All original local folders and experimental branches remain untouched. No credentials, models or tokenizer downloads are included. Distinct exports remain separate even when names/plan hashes coincide. Only byte-identical redundant ZIP copies were removed from the repository layout.

Use each frozen original plan/configuration and its [source branch](BRANCH_STATUS.md). Do not overwrite an existing run or assume default-branch code can resume it. Manifest source checkout commits identify the copies inspected, not necessarily the code used at collection. Historical audit documents are preserved verbatim: references there to root-level ZIPs now correspond to `results/archives/`, and reproduction scripts may live on their original branch.
