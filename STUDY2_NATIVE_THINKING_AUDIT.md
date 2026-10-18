# Offline native-thinking draft: implementation and review findings

Branch: `codex/study2-native-thinking-draft`, based on
`7f78a3338225614535b90a0d520ef6c346282d13`. The implementation is isolated on this branch; resolve its checkout revision with `git rev-parse HEAD`.
The 2026-10-18 sampling/budget amendment is included below. The matched sampler was already
explicit; it remains `do_sample=True, temperature=0.6, top_p=0.95, top_k=20, min_p=0`.
The main budget is now unset until a complete pilot and an explicit truncation/repetition review.
The original offline audit artifacts remain byte-identical in `audits/study2-native-thinking-draft-v1/`;
updated design metadata and verification live in `audits/study2-native-thinking-budget-review-v1/`.

No inference, weights download/load/hash, CUDA initialization, paid API call, or cloud operation
was performed. Jinja2 3.1.6 and MarkupSafe 3.0.2 were installed only in a temporary test directory
to execute the already saved template; no historical environment was changed.

## Existing implementation inspected and reused

Inspected branch history and relevant local/remote refs, including reasoning-continuation,
conditional-prefix v4, Qwen length diagnostic, v5 evidence interventions, v5 judge review,
and earlier counterfactual/factorial generators. No applicable repository AGENTS.md was found.
All **583 preexisting tracked files** remain byte-identical to the baseline. The actual saved
v5 plan file also retains its original SHA-256. Exact per-file hashes and old contracts are
in `audits/study2-native-thinking-draft-v1/preservation.json`.

Reused unchanged:

- `exception_pilot.core`: stable hashes/RNG, descriptor vocabulary; `storage`: atomic JSON and locks.
- `exception_counterfactual.core`: actual earlier support/conflict generator for the audit.
- `exception_study2_v5.core.read_plan`: validates the saved final plan against its frozen generator.
- `exception_continuation.qwen3`: exact model/tokenizer revision, pinned file manifest/dependencies.
- `exception_continuation.backend.LocalBackend`: pinned weight loading, native BF16/CUDA checks,
  eager attention, deterministic runtime setup, weight identity. Its plain-visible prompt/greedy
  generation methods are NOT used by the new native interface and are NOT modified.
- `exception_study2_source_report.tokenizer.Tokenizer`: local pinned asset verification and codecs.
  A separate `render()` validates both native template modes.
- Generic immutable `Session.operation`, operation-tree validation, freeze/sealed-read helpers;
  a new namespace, attempt/retry authorization layer and exact request binding are isolated here.
- Existing world-cluster bootstrap: 2,000 draws, seed 2026101601; no new inference or judge framework.

New interfaces are necessary for native scratchpad/final parsing, matched sampled generation,
the draft controlled tables, and explicit retry authorization. Historical v5's thinking-off
constraints remain intact; regression tests confirm they still reject thinking-on configuration.

## Audit of actual final tables

Saved plan hash: `7a7ad23ac63d8c06c1e68fd2a1232f159da7f1201ac1d970a07618394cedfc22`.
The audit reads final rendered tables, not the original items' stale labels. It confirms:

- 60 worlds: four pilot and 56 remaining.
- Both recorded variants oppose the four same-climate peers; the two variants change only
  the queried row's recorded class.
- The queried target is always the tenth data row (zero-based index 9).
- Ternary final assignments replace the earlier binary labels. Target-excluded totals are
  four pattern, three role-0 and two role-1 records. Each ordered label-role permutation occurs
  in ten worlds. Target and same-climate peer positions are retained per queried table.
- Source inspection confirms independent random assignments for transmission/seat/doors and
  later audit-marker draws. Random assignment does not produce exact finite-table independence.

There are **120 world/variant tables**, representing 60 distinct target-excluded backgrounds.
All 120 show marginal and joint distractor–class association. These are descriptive associations,
not evidence that the model uses the features. The duplicated variants are not independent samples.

| Diagnostic | V5 result |
|---|---:|
| Tables with some marginal distractor association | 120/120 |
| Tables with joint distractor association | 120/120 |
| Zero signed rate-margin sum but nonzero absolute margins | 11 |
| Zero signed rate-margin sum with joint association | 12 |
| Mean transmission MI (bits, descriptive) | 0.207071 |
| Mean seat-cover MI | 0.264070 |
| Mean doors MI | 0.279716 |
| Mean audit-marker MI | 0.463012 |

For example, world000/v0 records C while the climate pattern is B. Target-excluded Manual
counts are A=2, B=2, C=1. Therefore P(class|Manual)=(0.4,0.4,0.2), whereas P(Manual|class)=
(1,0.5,1/3). A count vote ties A/B; an equal-prior rate vote uniquely favors A. These are distinct
defined measures, not interchangeable votes. Full per-value tables include both conditional rates.

The relevant earlier generator was deterministically reconstructed with the saved v5 seed,
and its feature fields were checked against saved v5 base items. It yields 240 queried-target/
support-conflict tables, all showing some finite-table distractor association. Earlier support
has three of four target-excluded same-climate peers following the recorded target class;
conflict has four opposing peers. Those reconstructed tables are not presented as saved model
responses. The absent earlier audit marker is explicitly labeled as a constant placeholder.

Complete counts/rates, all 2/3/4-way distractor joints, vote definitions, positions, and per-case
role assignments are in `generator-audit.json.gz`; `generator-summary.json` is readable without
decompression. The compressed JSON round-trips byte-for-byte to the sealed full audit.

## Proposed controlled design and exact population

The draft has 13 rows: a target last at row 13 and 12 background records, four under each class.
It retains four unanimous same-climate peers. Identical four-column distractor profiles occur
once per class, ensuring exact marginal AND full-joint distractor–class independence in every
final table. Binary columns are 2/2 per class; marker frequencies are 2/1/1 per class, not uniform
across marker values. All three existing marker levels remain present.

The historical 4/3/2 constraints cannot support four same-climate peers for either alternative
recorded label. An 11-row 4/4/2 alternative could use only two shared profiles/marker levels.
Thirteen rows retains all three marker levels with nonconstant exact independence. This is a
transparent draft change requiring review, not a claim that historical tables were balanced.

Two cue contexts cross two recorded variants. Within a fixed cue context, the record variants
change only the target label and switch support/conflict. Within a fixed recorded variant,
cue contexts exchange eight background labels. Seeds are shared across variants, cue contexts
and thinking modes within world/wording. We do not claim that two support variants have the
same background or that the support/conflict contrast changes only one target cell.

See `sample-tables.md` for all four representative paired tables, including the exact target
identifiers, labels and cue states. See `constraints.json` for the final-table checks and separate
cohort counterbalancing. The full controlled design is `controlled-design.json.gz`; the exact
960-cell list is the directly readable `cell-manifest.json`. Use those files under
`audits/study2-native-thinking-budget-review-v1/` for current budget metadata. Their scientific
cells, prompts, tables, seeds and schedule exactly match the preserved initial draft.

| Separate design | Worlds | Tables | Pilot responses | Main responses | Total |
|---|---:|---:|---:|---:|---:|
| Controlled draft, full wording × mode × support/conflict × record variant | 60 | 240 | 64 | 896 | **960** |
| Historical v5 tables, fresh wording × mode × record variant; all conflict | 60 | 120 | 32 | 448 | **480** |

Both totals are generated from their manifests. The historical option cannot estimate a support
gap and is not pooled with the controlled experiment. The controlled original and lookup wordings
each contain 480 responses; the lookup condition is not a partial factorial here.

Tradeoffs still requiring scientific review: 13 versus 10 rows; equal background class priors;
more opposite-climate records; stronger support than the earlier binary generator; duplicated
opposite-climate descriptions and conspicuous repeated profiles; a fixed last-row target;
and the provisional 4,096-token pilot cap. The main cap is deliberately pending pilot review. Individual background row positions/IDs are randomized,
not asserted exactly balanced. Across all 60 worlds roles are exactly counterbalanced, but the
four-world pilot and remaining cohort are not separately exact for label roles or doubled markers.
The remaining cohort has 28 worlds per climate and 14 per target distractor profile.

## Native interface and scope of verification

The actual template saved in the pinned pilot was executed using Jinja2: on ends at the assistant
header, while off adds the official empty thinking block. Its tokenizer-config SHA is
`d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101`.
This verifies actual saved-template behavior; it does NOT substitute for the missing real BPE
tokenizer integration test, real CUDA generation, or behavioral replication.

Both modes use the same pinned Qwen3-32B weights, BF16/eager/batch-one settings and shared sampler:
`do_sample=True`, temperature 0.6, top-p 0.95, top-k 20, min-p 0, one beam, no hidden model defaults. This follows the
thinking recommendation for both modes; Qwen recommends temperature 0.7, top-p 0.8,
top-k 20, min-p 0 for non-thinking deployment. Matching here isolates the template mode under
one sampler; it is not a comparison of separately optimized deployment settings.
The inference wrapper is new and untested on real hardware. [Official Qwen model card](https://huggingface.co/Qwen/Qwen3-32B).

All exact prompt IDs, mode, model/tokenizer/template identity, seed, sampling settings, budget,
protocol and expected source truth are frozen per request. Thinking text and the final channel
are separated deterministically; label-only FINAL means A/B/C in the final channel, not suppression
of the native scratchpad. Wrong, malformed and truncated outputs are retained without resampling.

The runbook uses the existing environment and assets. `prepare` validates all 64 pilot contexts (32 historical) with the real tokenizer.
`freeze-main` later validates all 896 main contexts (448 historical) against the explicitly reviewed cap. No prepared real-model plan or Qwen responses were fabricated locally.
There is no live technical pilot, judge, probe, activation cache, or automatic next experiment.

## Pilot-driven budget freeze

`PILOT_BUDGET=4096` is provisional and identical across modes. The design still freezes all 960
scientific cells, but `prepare` produces executable requests only for the 64 pilot cells.
The design's `main_budget` and full-experiment `maximum_output_tokens` remain null. Pilot output
ceilings are 262,144 controlled tokens or 131,072 for the separate historical option.

Per-case and grouped diagnostics report output/thinking/final token lengths, truncation, EOS and
malformed returns. They additionally report repeated 16-token windows, their fraction, maximum
window frequency and longest identical-token run. Null denominators and missing token evidence
remain explicit. Complete raw outputs are retained. These metrics do not diagnose semantic failure
or automatically change decoding, scoring, stopping, retry policy or the budget.

Main preparation is an explicit offline `freeze-main` operation requiring all pilot cells returned,
a chosen shared cap, truncation observations, repetition observations and a budget rationale.
It binds these notes to the pilot plan/backend and all immutable operation hashes, with diagnostics
recomputed from raw journals. It writes a separate main directory, preserving pilot artifacts.
A main invocation revalidates that evidence. MOCK evidence cannot unlock LIVE_LOCAL execution;
`--scope main` on a pilot plan fails before loading. Failed/interrupted/pending pilot cells block
freezing, while returned wrong/malformed/truncated answers stay cached and available for review.

No pilot or main response was generated here. Real truncation/repetition, suitable main budget,
GPU compatibility and sampled-kernel reproducibility remain untested. The pilot's budget decision
will be disclosed and pilot results kept separate from main results; no automatic advancement occurs.

## Focused offline tests

Final command:

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH=/tmp/study2-native-template-deps:tests:. /tmp/study2-qwen3-venv/bin/python -m unittest -v test_study2_native
```

**24 tests: 23 passed, one skipped, zero failures/errors; 38.467 seconds.**

The exact current log is `audits/study2-native-thinking-budget-review-v1/focused-tests.txt`.
The earlier 18-test log remains unchanged in the initial audit directory.

| Requirement | Offline result |
|---|---|
| Saved final-table audit and earlier-generator reconstruction | PASSED on the actual saved v5 plan |
| All 240 controlled final tables and 960-cell deterministic manifest | PASSED |
| Marginal/full-joint balance, correct one-cell/eight-cell transformations | PASSED; tampering rejected |
| Zero marginal signal can coexist with joint association | PASSED with explicit XOR regression fixture |
| Actual saved Jinja template mode change | PASSED; no weights/tokenizer inference involved |
| Real pinned tokenizer on all cells | NOT TESTED locally: assets absent; one explicit skip, required by production prepare |
| Native thinking/final/EOS/malformed/truncated parsing | PASSED with synthetic token fixtures |
| Complete fake 960-response workflow | PASSED: 64 pilot at 4096, explicit synthetic budget review, 896 main at 6144 in a separate directory; one load per necessary invocation, completed resume zero calls/loads |
| Matched sampler and RNG at actual native wrapper boundary | PASSED with mocked tensors/model: explicit requested sampling settings and CPU/CUDA request seeds; historical greedy generate/prompt never called |
| Main budget review gate and provenance | PASSED: incomplete pilots blocked, separate output required, missing review rejected, context overflow rejected, altered pilot evidence rejected, synthetic evidence cannot authorize live main |
| Repetition/truncation diagnostics | PASSED for repeated, unique, short, malformed and capped output; no automatic resampling |
| Original draft scientific population | PASSED: all prior cells, tables, prompts, seeds, schedule and constraints identical |
| Failed/interrupted recovery and explicit retries | PASSED: first failure stops, remaining work resumes, failed attempt preserved; returned outcomes cannot be retried |
| Exact cache identity | PASSED: prompt, input IDs, model revision, tokenizer, thinking mode, decoding, seed and budget mismatches rejected |
| Durable raw output through reporting interruption | PASSED; no repeated generation |
| World-cluster paired analysis and contrast signs | PASSED; synthetic thinking-on conflict errors yield on-minus-off=-1 and penalty-change=+1 |
| Historical behavior | PASSED: frozen files/contracts unchanged, old thinking-on rejection retained |
| Real-model compatibility, sampled kernel determinism and behavioral effects | NOT TESTED; no live-model tests run |

Static checks also passed: eleven Python AST checks, thirteen runbook shell-block syntax checks,
five CLI help commands, strict JSON parsing and compressed-JSON round trips. No live runbook command was executed.
The complete historical suite was not rerun because no historical/shared source was changed.

## Files and operator handoff

New files only: ten modules under `exception_study2_native/`, `tests/test_study2_native.py`,
`STUDY2_NATIVE_THINKING_DRAFT_PROTOCOL.md`, `STUDY2_NATIVE_THINKING_RUNBOOK.md`, this audit,
the ten preserved initial audit/design/test artifacts under `audits/study2-native-thinking-draft-v1/`,
and six separately versioned amendment artifacts under `audits/study2-native-thinking-budget-review-v1/`.

Draft code/protocol contract: `c2c08c4a942674dd32ce74efccc4f9987ec73c88caa142d81173202636adfa42`.
Controlled preview artifact hash: `23825b8d16c1982abfe8100ca3b69cd58569cf82ced4259e17aa621883fedf7d`.
These are offline design previews, not inference evidence. Follow the runbook from this branch
to generate/prepare fresh RunPod outputs; the Git provenance field will reflect the checked-out
revision. The preserved offline previews retain their original pre-commit provenance. Do not edit an existing frozen plan in place.

Small copyable commands for setup, audit/design, prepare, inspect, explicitly authorized pilot,
resume, explicit failed-attempt retry, pilot review/main-budget freezing, and analysis are in `STUDY2_NATIVE_THINKING_RUNBOOK.md`.
Stop after reviewing this implementation. Live pilot/main commands are supplied, not executed.
