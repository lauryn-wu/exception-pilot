# Branch and experiment status

Updated 2026-10-18. This is an archival update, not a merge of experiment implementations.

| Branch / material | Current archived coverage |
|---|---|
| `codex/study2-v5-judge-review-v2` (latest checked `7f78a333`) | Qwen trace export; source-report v1/v2 failed 12-call calibrations; source-user 12-call pilot and 332-call main; independent audits |
| `codex/downstream-history-control` | 216-call history export now located and preserved. Branch association comes from project history; the export does not itself record a branch. |
| Downstream rule control | 432-call export now preserved, in two ZIP containers with identical member data. The export does not itself record a branch. |
| Source/history crossing plan |Offline proposal only; on hold ; 208 continuations not run |
| Availability-edit diagnostic |Offline nine-history/eight-world draft ; 27 continuations not run; tokenizer validation pending |

Read the [current results index](README.md) before the historical status below. The older statement that no live Qwen or downstream-history exports were found is superseded by this update. Code remains on existing branches and is not changed by the archival commit. No inference was performed.

## Historical October 13 snapshot

As of 2026-10-13, from inspected worktrees, remote branches and related local Downloads. This cleanup changes no experimental implementation, prompts, thresholds or configurations. Code remains on its existing branches.

| Code branch | Experiment | Result coverage |
|---|---|---|
| [codex/column-study](https://github.com/lauryn-wu/exception-pilot/tree/codex/column-study) | Column availability | 576/576 returned |
| [codex/evidence-role-study](https://github.com/lauryn-wu/exception-pilot/tree/codex/evidence-role-study) | Evidence role | 480/480 returned |
| [codex/features-and-downstream](https://github.com/lauryn-wu/exception-pilot/tree/codex/features-and-downstream) | Feature support; downstream edits | 648/648 and 342/342 returned |
| [codex/instruction-interface-diagnostic](https://github.com/lauryn-wu/exception-pilot/tree/codex/instruction-interface-diagnostic) | Instruction × output interface | 192/192 returned; earlier unstarted snapshot retained |
| [codex/query-form-audit](https://github.com/lauryn-wu/exception-pilot/tree/codex/query-form-audit) | Query form: GPT-4o and Mistral | 288/288 each |
| [codex/row-position-study](https://github.com/lauryn-wu/exception-pilot/tree/codex/row-position-study) | Target row position | 288/288 returned |
| [codex/row-position-confirmation](https://github.com/lauryn-wu/exception-pilot/tree/codex/row-position-confirmation) | Row-position confirmation | Two executions of the same plan: 960/960 each; do not pool |
| [codex/evidence-order-followup](https://github.com/lauryn-wu/exception-pilot/tree/codex/evidence-order-followup) | Study 1 / evidence ordering | 7,680/7,680 returned; token/provider-serialization limitation retained |
| [codex/reasoning-continuation-followup](https://github.com/lauryn-wu/exception-pilot/tree/codex/reasoning-continuation-followup) | Qwen Study 2A/2B | No live Qwen results found: 0/48 selection; compatibility and replication pending |
| [codex/downstream-history-control](https://github.com/lauryn-wu/exception-pilot/tree/codex/downstream-history-control) | Matched downstream history control | No live export found; 216 calls planned |

The only recent implementation branches without located live results are **Qwen Study 2** and **matched downstream history control**. The closed Mistral capability check is a failed technical result, not Qwen behavior. This inventory does not cover inaccessible cloud machines.

The [results index](README.md) also includes the original 1,200-response `reference-001` run recovered from Downloads. No separate local export was found for the historical DeepSeek prefix alternative (`PREFIX_PROTOCOL.md`) or conditional original stage-2 diagnostics; neither is scheduled here.

Collection completeness does not imply protocol success, behavioral replication or reviewed semantic eligibility. Invalid observations, null/stopping decisions and technical failures remain in the reports. The two row-position confirmation executions reuse the same worlds/tasks and must not be pooled or selectively reported.

For reproduction, use frozen plans/execution records and matching original code. Source hashes can intentionally reject newer code. The manifest's checkout revisions identify inspected copies without claiming collection-time code identity. No inference is needed to inspect the archives.
