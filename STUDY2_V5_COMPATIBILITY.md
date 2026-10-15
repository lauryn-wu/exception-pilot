# V4 → v5 compatibility and preservation audit

Base branch: `codex/study2-qwen-expanded-screen`.
Base commit: `bfee376e6369a6266f0d4671761312c2d667b240`.
New branch: `codex/study2-v5-evidence-interventions`.

All **353** previously tracked files are preserved byte for byte, including the
v3/v4 scientific packages, protocol documents, original configurations, failed
validation audit, Mistral capability-check implementation/artifacts, Qwen length
diagnostic and expanded screen. No historical run is imported or relabeled.
`audits/study2-v5/preservation-baseline.json` records every prior file SHA-256;
`DesignTests.test_v4_and_all_previous_files_preserved` checks every entry.
Untracked/ignored historical model/results/cache folders are not targets of any
implementation write. No credentials, weights, environment or cache are committed.

V4 scientific source hash remains:

`913f64efa3f12a1a787575c14c7670e072e250d7e8a3690a9957cfa70bb88e78`

V5 hashes its new package and protocol, plus this immutable v4 dependency hash.
Frozen plans also bind the full v5 configuration, 2048 scientific cap, random
schedules, tables/prompts, source hash, phase and selection lock. Execution freezes
the actual new Pod model/backend fingerprint and Git revision. Source/identity
changes fail resume. Original, readout, annotation and intervention artifacts have
separate namespaces and seals. A failed/ambiguous dispatch is never automatically
resent. Downstream contexts contain only original prompt + selected saved/edited
prefix (+ a disposable cue for readout only).

## Reused without modification

- `exception_counterfactual.core.make_world`, stable RNG, original introduction,
  question, direct and visible instructions.
- `exception_continuation.backend.LocalBackend`: pinned BF16 loader, model/tokenizer
  file hashes, official template, EOS, greedy overrides, complete candidate scoring.
- V4's same-input comparison function and probability tolerances, adapted into a
  separate v5 journal/report namespace. No incremental-KV/original suffix gate.
- Existing sealed storage, atomic file writes/locks, tokenizer-only verifier,
  CUDA-synchronized timing wrappers and model-load instrumentation.
- Existing pinned dependency file and existing local model snapshot.

## New or deliberately adapted

- Fresh balanced 12/48-world design and mandatory lookup framing; 96/384 originals.
- Independent 2048-budget configuration envelope. Legacy config still says 512;
  every scientific `generate` request explicitly uses 2048 or 2048-original_k.
- Legacy `cue_check_checkpoints` and `event_checkpoints` remain inert loader-profile
  fields; v5 uses its own checkpoint/event schedules and both cues explicitly.
- Balanced Markdown terminal parser with separate strict compliance/unknown outcomes.
- New fixed/pre-answer/event checkpoint planner and full-candidate readout journal;
  both cues at every eligible cut, deduplication within one measurement plan.
- Blinded independent-review imports, separate M/O rubrics, miscopy observations,
  exact spans/anchors, third-review adjudication, frozen negative decisions.
- Separate M/O edit manifests, mandatory independent semantic verification,
  table-cell safeguards, class/hint checks, exact tokenizer roundtrips, independent
  continuations and per-arm availability.
- World-grouped behavioral, trajectory and family-specific intervention reports,
  unknown-outcome bounds, clean/mixed O, partial-contrast coverage and multiplicity.
- Explicit command staging, selection coverage lock, local-only preflight and docs.

## Limits that remain real, not mock failures

No pretrained Qwen weights, GPU, paid judge calls or cloud resources were used.
New-Pod preflight/technical success, BF16 peak memory, throughput, scientific
calibration, event prevalence, semantic edit validity and confirmation effects are
pending. The real pinned tokenizer/template is tested offline; this is not model
repeatability. Fake generation/logits are labelled MOCK throughout.

Review is deliberately an auditable **manual two-reviewer/third-adjudicator import
workflow** with new semantic rubrics. It does not claim to automatically determine
meaning from keyword rules or to have executed the legacy paid judge pipeline.
Independent semantic certification can be wrong; reviewers must check complete
source text. In particular, first-occurrence/absence/hint-free meaning are semantic
judgments, not proven by lexical validators. Class-letter checks are supplemental.
No new automated paid judge client is part of v5; its necessity was not assumed.

Two eligible worlds is only a minimum coverage gate, not a power calculation.
Low-prevalence clean overrides may yield insufficient coverage. O's primary cohort
excludes mixed and uncertain-history trajectories but reports them separately.
Small/degenerate bootstrap intervals require cautious interpretation. Results under
lookup framing and future controlled alignment address task interpretation and
pattern-specific causal attribution; no stronger mechanistic claim is licensed.
