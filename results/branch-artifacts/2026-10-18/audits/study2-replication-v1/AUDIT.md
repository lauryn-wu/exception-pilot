# Replication-only amendment v1: offline implementation audit

Base: `40aa1f7c5b61e8862a9c9d0f3768e9880323bbc1`, branch
`codex/study2-v5-judge-review-v2`. This audit concerns an additive workflow patch,
not a new scientific result. No new real-model generation, measurement, paid
judgment, model download, RunPod session, or GPU execution occurred.

## Historical preservation

`historical-baseline.json` captures hashes before implementation.
`preservation-audit.json` compares them after implementation:

- **492/492 pre-existing tracked files unchanged**; zero modifications to original
  v5 scientific code/configuration, old tests, documentation, or stored audits.
- **1,442/1,442 historical files unchanged** across six recovery trees: staged
  pilot/original judge archive (786), paid v2.1 review (639), v2.2 salvage (5),
  residual v1 (5), residual v1.1 (5), and pilot fixed-readout recovery (2).
- **313/313 original experiment files byte-copied** into the fresh research
  directory `~/exception-v5-recovery/study2-v5-replication-v1-offline/originals`.
  Copy verification includes the original execution, plan, technical journals,
  32 original responses, timing, and design confirmation. No hard links, model
  weights, or caches were copied.

Direct extension would invalidate historical tree hashes: residual
`history.History` compares snapshots of the paid review and original source
against `salvage-report.json` provenance. Preserving only old row contents is
therefore insufficient. The new workflow extends only the verified copy and
rechecks protected archives on every stage.

Original `journal.Session` freezes actual HEAD in `execution-v5.json`; changing
HEAD would conflict with that immutable file. `ReplicationSession` overrides only
initialization and inherits the immutable `operation` and `generate` methods. It
retains the old execution and creates a separately bound, truthful new execution.
Every new operation carries both amendment and replication-execution hashes.
Resumption at a changed HEAD fails. The test fixture simulates an older original
revision and verifies this behavior without altering actual historical metadata.

## Frozen preview

`amendment.json` is the exact offline frozen amendment; `offline-preview.json`
lists every remaining world, task, full prompt, and visible-trajectory ID.
This preview is **not approved** and contains no new attempts.

| Item | Value |
|---|---|
| Frozen design | 60 worlds, 480 original tasks |
| Preserved pilot | `staged-v5-000`–`staged-v5-003`, 32 attempted originals |
| Remaining population | `staged-v5-004`–`staged-v5-059`, all 56 worlds |
| Remaining original tasks | 448: 224 direct and 224 visible |
| Each visible framing | 112 trajectories, two variants per world |
| New generation ceiling | 917,504 output tokens |
| Fixed readout ceiling | 2,688 checkpoint × cue computations |
| Candidate-sequence ceiling | 8,064 full likelihood evaluations |
| New measurement answers / edited continuations | 0 / 0 |
| Actual new model/judge calls in audit | 0 / 0 |

Identities:

- Scientific plan: `7a7ad23ac63d8c06c1e68fd2a1232f159da7f1201ac1d970a07618394cedfc22`
- Scientific source: `e545f0a756934f0d5c953db3a1c102146a1616dc2706913cb3537e8a5a6a2c2b`
- Pilot binding: `4a9aff2291c6a99c4e770d841dd98a4812b995d46a47232c88d773d3649b925b`
- Backend: `a7a7eb1cd399fd4a3a74c0cee48546c6db219840c5ccc960d4c984dc04a3b1c4`
- Original execution revision: `07e4b6552509f955f62d234c7a9ee8a634cf649b`
- Additive implementation hash: `2cf2d7ff25bcb8f2f2b627aaa3b02079a3274695dd19c12c6cde662063cc667d`
- Offline amendment: `4277097b9204199b6dd1415b342488a318c36862f8cd97f10ae01f6197cf6b66`

The offline preparation truthfully records base HEAD while the additive code is
uncommitted, together with its exact implementation hash. The eventual commit
contains these same implementation bytes. A live Pod must prepare its own fresh
amendment at its actual checkout and paths; copying/editing this Mac plan is not
an execution procedure.

## Requirement evidence

| Requirement | Status | Evidence |
|---|---|---|
| Exact frozen design; 32 preserved, 448 remaining | PASS offline | Real-source preview and `test_exact_design_copy_and_preview_32_448_224` |
| Explicit post-pilot approval, no 2B forgery/bypass | PASS offline | `test_approval_requires_exact_hash_and_pilot_acknowledgment`; old approval patched to raise in a test, never called |
| No pilot replay or historical mutations | PASS offline | Complete 448-attempt mock executions, separate 224-trajectory readout plan, historical SHA audit |
| Model/backend/prompt identity mismatch stops | PASS offline | Backend mismatch and saved pilot prompt-ID mismatch tests; source/template hashes remain frozen |
| Technical/source/journal integrity | PASS offline | Technical artifact mutation, archive mutation, amended-task mutation, orphan journal, nested output and symlink tests |
| Truthful new execution revision | PASS offline | Earlier synthetic execution retained; actual HEAD recorded separately; changed HEAD rejected |
| No automatic retries; safe resumability | PASS offline | Ambiguous-start recovery sends only 447 remaining calls; completed return without row reused; repeat full collection makes no new calls |
| Preparation/default collection/default measurement no inference | PASS offline | Loaders and sockets blocked; mock generate forbidden during preparation; real preview unapproved |
| All 224 visible trajectories planned | PASS offline | Complete mock collection and all-failed collection both produce 224 rows |
| Frozen cuts, aliases, cues, complete ABC scores | PASS offline | Exact checkpoint test, full readout test, unchanged v5 planner/scorer reused |
| Measurements never generate answers | PASS offline | Mock `generate` explicitly fails if called during measurement |
| World-level analysis and missingness | PASS offline | Unequal per-world counts, incomplete matched variants, missing readouts, reversals/recovery/gaps, cue disagreement tests |
| Existing v5 result formats | PASS offline | Existing `Source`, `prepare_measurements`, `measure`, `trajectory_report`, bootstrap, and behavioral scoring consume new artifacts |
| Separate examined pilot and remaining 56 | PASS offline | Full mock report checks 4/56 split; no pooled claim; pilot readouts read only |
| Live wrapper compatibility and remaining-world outcomes | NOT TESTED | No real-model calls authorized or made |
| 112 completed historical pilot readouts | NOT VERIFIED LOCALLY | Recovered folder has plan + lock only; zero returned operation journals or scoring timings |
| New GPU peak memory and scoring throughput | NOT TESTED | Estimates explicitly distinguish measured pilot generation from assumed scoring speed |

The 112-computation historical plan is source-bound and verified. Missing local
completion records are not interpreted as failed or zero readouts, and are not
recomputed. The runbook preserves and reads the actual completed folder if
available on the Pod. This evidence limitation does not justify changing the
frozen remaining task population or starting Study 2B.

## Offline tests

Targeted acceptance: **25 passed**, zero failures/errors/skips, **129.645 seconds**.
`targeted-tests.txt` records the final targeted run. A first test run exposed a
synthetic fixture path comparison (`/var` versus `/private/var`); resolving both
paths fixed the interruption assertion. The final returned-operation test verifies
that a durable model return is reused rather than resampled.

Full offline suite: **794 passed**, zero failures/errors/skips, **784.729 seconds** (769 existing + 25 new).

Full-suite results are recorded in `full-offline-results.json` and
`full-offline-tests.txt`. `run_full_offline.py` blocks socket connections for the
entire suite. Existing tiny random-weight CPU architecture fixtures do not load
pretrained Qwen3-32B weights or use a GPU. All new execution tests use mock backends.

To repeat the historical byte audit on this machine without overwriting it:

```bash
python audits/study2-replication-v1/verify_preservation.py \
  --output /tmp/study2-replication-preservation-recheck.json
```

The baseline contains machine-local recovery paths intentionally; it is an audit
of those preserved artifacts, not a portable execution configuration.

## Workload and operational limits

`pilot-timing-estimate.json` reproduces measured original-generation timings.
`workload-estimate.json` additionally records the complete pilot collection
invocation, tokenizer-only forward-work estimates, and explicit throughput/cost
assumptions. On the exact original H100 80GB HBM3 backend, extrapolation gives about
two hours for collection and **2.5–3.2 hours** including scoring under the assumed
800–2,000 forward tokens/s. At the user's historical $3.99/hour quote, approximately
**$10–$13**, excluding idle/storage and additional new-wrapper/reporting overhead.
These are scenarios, not measured replication runtimes or bounds.

Collection, measurement preparation, measurement execution, and analysis are
separate commands in `STUDY2_V5_REPLICATION_RUNBOOK.md`. No live approval was
recorded in this audit. The original v5 and failed prior validations remain intact.
