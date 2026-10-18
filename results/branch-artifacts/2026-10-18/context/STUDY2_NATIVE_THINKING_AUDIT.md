# Native-thinking v2: targeted shortcut and recovery patch

Branch: `codex/study2-native-thinking-draft`. Reviewed base and starting head:
`af2e78663856c8812e2f068186be706da271b7c4`. No intervening local/remote changes were present.
Status: **DRAFT_FOR_REVIEW**. No inference, paid calls, GPU/cloud use, or model downloads occurred.
The historical experiment packages and both earlier native audit directories are unchanged.
This patch does not migrate or rewrite frozen v1 execution plans/results.

## Changed components

- `design.py`: revised 16-row count-block generator; exact target-only/eight-background-cell pairing;
  pooled block balance checks; rejection of audited perfect shortcuts.
- New `shortcuts.py`: final-rendered counts, count/profile/vote baselines, world/block-held-out
  histogram prediction, per-table and pooled associations, explicit coverage/ties.
- `__init__.py`: v2 protocol identity and the requested final-answer instruction, verbatim.
- New `recovery.py`, with small execution/analysis/CLI integrations: native-only read-only inspection,
  conservative interrupted-write holds, explicit locked quarantine and resumable recovery.
  Historical journal/storage readers and the model interface remain unchanged.
- `planning.py`: offline `audit-shortcuts` command; existing exact request checks and pilot-to-main
  review preserved. `diagnostics.py` uses the same conservative operation-state interpretation.
- Focused tests, protocol and RunPod runbook; new artifacts only under
  `audits/study2-native-thinking-draft-v2/`. The v1 generator/budget artifacts remain byte-identical.

The matched sampler is unchanged: `do_sample=True, temperature=0.6, top_p=0.95, top_k=20, min_p=0`.
Seeds remain in request identity and are applied per call. BF16, pinned weights/tokenizer,
native template behavior, caching and pilot-before-main budget review are unchanged. Revised
scientific inputs receive v2 IDs/hashes; historical greedy results remain separate.

## Revised generator and tradeoffs

There are still **60 worlds, 240 final tables and 960 response cells: 64 pilot + 896 main**.
Original/lookup wording × native thinking off/on × two cue contexts × two target-record variants
remain intact. Each final table has 15 background rows and one target at row 16.

Ten count/feature blocks each contain all six ABC role permutations. Six blocks use the six
permutations of `(4,5,6)` background role counts, three use `(4,4,7)` with the third/non-target
role receiving seven rows, and one uses `(5,5,5)`. Four same-climate peers remain unanimous.
Across cue contexts, four opposite-climate rows swap labels with those peers: exactly eight
background label cells change while the target remains fixed. Within a cue context, record
variants change only the target's Verified-class cell. The three extra opposite-climate records
keep their labels across cue contexts. Full histograms therefore change across target flips.

The v1 4/4/4 background made both majority and parity rules correct on 240/240 tables. It is
preserved and explicitly rejected. During this offline revision, assigning seven background rows
to a target-record role was also rejected: a count of eight identified that answer on a subset.
The chosen design has no single-answer full histogram and no perfect audited selective rule across
the full manifest. This audit-informed revision is not an independent evaluation of the design.

Exact per-table distractor independence is deliberately relaxed. Every revised table has joint
background distractor association. Pooling each complete six-world label-permutation block yields
exact raw-A/B/C joint independence, for target-excluded AND full-table rows. Neither pilot nor
main alone has that exact pooled independence. Relative recorded/alternative/third-role association
remains even pooled: full-joint MI is approximately 0.10514 bits in both support and conflict.
Raw-label counterbalancing does not remove that signal. All counts/rates, marginal and 2/3/4-way
joint associations, signed/absolute vote margins and target-profile matches are retained per table.

Other limitations: fixed last-row target; repeated descriptions/profile scaffolds; larger tables
and eleven opposite-climate background rows; shared block structure; nonuniform pilot/main block
composition. World-cluster outcome intervals remain descriptive. Block-held-out histogram checks
supplement world-held-out checks, rather than treating scaffold copies as independent evidence.

## Shortcut results (240 tables, not 960 duplicated response cells)

Ties abstain. Accuracy here is conditional on making a prediction; coverage is reported separately.

| Baseline | Correct / predicted | Coverage | Ties | No candidate |
|---|---:|---:|---:|---:|
| Full-table majority | 72 / 192 (37.5%) | 80% | 48 | 0 |
| Full-table minority | 0 / 168 | 70% | 72 | 0 |
| Full-count unique parity remainder | 24 / 192 (12.5%) | 80% | 0 | 48 |
| Full-table matching-profile majority | 114 / 150 (76.0%) | 62.5% | 90 | 0 |
| Target-excluded matching-profile majority | 66 / 156 (42.31%) | 65% | 84 | 0 |
| World-held-out exact histogram | 72 / 168 (42.86%) | 70% | 72 | 0 |
| World-held-out nearest-L1 histogram | 72 / 168 (42.86%) | 70% | 72 | 0 |
| Block-held-out nearest-L1 histogram | 0 / 96 | 40% | 144 | 0 |

Every observed histogram has multiple possible recorded answers. The in-sample upper bound for
any histogram-only predictor on this fixed manifest is **120/240 = 50%**, not chance and not a
claim about future data. Cross-validation excludes all variants/cues of the held-out world or
six-world block, uses no heavy dependencies and performs no tuning. Counterbalancing can make
these held-out votes systematically unfavorable; their low scores do not prove absence of leakage.

| Subset | Tables | Majority correct / predicted; ties | Full-profile correct / predicted; ties |
|---|---:|---:|---:|
| Support | 120 | 36 / 96; 24 | 72 / 96; 24 |
| Conflict | 120 | 36 / 96; 24 | 42 / 54; 66 |
| Pilot | 16 | 4 / 12; 4 | 8 / 10; 6 |
| Main | 224 | 68 / 180; 44 | 106 / 140; 84 |
| Pilot support | 8 | 2 / 6; 2 | 6 / 8; 0 |
| Pilot conflict | 8 | 2 / 6; 2 | 2 / 2; 6 |
| Main support | 112 | 34 / 90; 22 | 66 / 88; 24 |
| Main conflict | 112 | 34 / 90; 22 | 40 / 52; 60 |

The full audit additionally reports majority/minority on background counts, each remainder rule
modulo 2/3/4, each feature count/rate vote, and pattern agreement, for every subset above.
No arbitrary chance-score criterion was imposed. Residual profile prediction is substantial;
the unique minority also rules out an answer on many tables. Pilot-conflict profile prediction
is perfect on only two covered tables, with six ties. These are explicit review limitations.

## Atomic-write recovery and preservation

`inspect` performs no writes, including no lock-file/report creation. Recognized temporary names
are limited to the existing writer's exact canonical-name + eight lowercase/digit/underscore
characters + `.tmp` pattern. Canonical JSON, hash, request, backend and terminal-state validation
remains strict. Unrelated files, symlinks and identity mismatches are still rejected.

A valid canonical returned result stays completed despite leftover temporary files and is reused
with zero model loads when no executable work remains. Request/start/return write interruptions,
empty known orphan folders and orphan dispatch evidence are conservatively held ambiguous. No
temporary return is promoted, even if its JSON is complete and valid. A likely pre-dispatch
request interruption is still not silently made never-started.

Explicit `recover --reason ...` runs under the run lock, freezes an evidence/move manifest first,
then quarantines only recognized temporary files. Canonical files remain byte-identical. Holds
survive quarantine; explicit retry produces a distinct attempt. An interruption during recovery
resumes against the same manifest. Interrupted manifest writes before any move remain visible,
uncommitted evidence. Unknown orphan folders or orphan canonical states without a request require
forensic review; the tool does not invent their identity. This is native-v2 recovery, not a migration
or relaxation of historical journal contracts.

## Verification and readiness

Focused offline command:

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=/tmp/study2-native-template-deps:tests:. /tmp/study2-qwen3-venv/bin/python -m unittest -v test_study2_native
```

**36 tests: 35 passed, one skipped, zero failures/errors; 55.832 seconds.**
The skipped check requires the absent real pinned tokenizer. The saved pinned Jinja template
mode-switch check passed; real tokenizer/GPU integration remains unverified.

Regression coverage includes v1 majority/parity rejection, all revised pairing/count/block checks,
held-out world grouping, exact final wording, sampled settings/seeds, request identity, incomplete
pilot/main gating, request/start/return interruptions, real atomic-writer debris beside a completed
return, read-only inspect, recovery interruption/resumption, orphan dispatch/empty folder handling,
unknown/malformed/mismatched files, no promotion/resampling, and zero loads for completed resume.
The synthetic 64-pilot + 896-main workflow still passes. No broad historical suite was rerun.

The separately versioned v2 package contains the frozen design, prompts, full shortcut audit,
readable baseline tables, test log, static checks and preservation hashes. Frozen previews retain
base Git revision af2e786 and the exact patched code/protocol contract; prepare fresh real-tokenizer
plans from the eventual pushed patch revision. Never edit a frozen plan's provenance to update it.

**Ready for design review before a separately authorized pilot**, with the residual profile/role
signal, target position and table-size tradeoffs above. It is not approved automatically for live
execution. The 4,096-token pilot cap remains provisional; the main cap remains unset until the
completed pilot's truncation/repetition review. No pilot or main experiment has been launched.
