# Study 2 implementation audit — 2026-10-12

Starting branch: `codex/reasoning-continuation-followup`, commit `1be7551`.
Patches reuse existing generation, exact-prefix continuation, world generation,
sequence scoring, edit arms, journals and estimators. No duplicate implementation
or third experiment was added. V1 protocols/config/previews/results remain intact;
new runs use `within-reasoning-continuation-v2` and fresh seeds/output directories.

| Requirement | Existing behavior | Targeted change / remaining validation |
|---|---|---|
| Linked 2A and 2B | Shared collection, but protocol/analysis organization was not explicit | Separate protocol sections and summary files; one shared backend; logits explicitly supporting infrastructure |
| Normal original generation | Single uninterrupted generation; post hoc fixed-prefix probes | Retained; regression checks original bytes and exactly one original generation per task |
| Exact checkpoint readout | k=0/32/64/128; standardized cue; full multi-token sequence likelihoods already retained | Added configurable small cue check, saved literal candidate/cue strings, whitespace tests, success/failure/invalid strata |
| Candidate-statement branch | Branched at the next fixed 2A checkpoint, allowing intervening original reasoning | Replaced only boundary selection: immediate statement end, whitespace-only token allowance, explicit exclusions, independent of 2A |
| Matched edits and natural continuations | Existing unchanged, availability, meaning and value arms; no class letter added by availability repair; fresh token-ID generation | Retained; added statement spans, grammar certification, protected preliminary entry checks, exact-boundary validation; no cue/future reasoning/new turn in generation inputs |
| Real replay validation | Tokens checked; no next-token distribution comparison | Added uninterrupted logit capture and full-vocabulary logit/probability checks under frozen tolerances; explicit `validate` command; every edited case separately checked; real validation PENDING |
| Model selection versus confirmation | Fresh worlds and backend lock, but no measured replication gate | Added prospective behavior counts, calibration report and gate; confirmation forbids 2A-informed edit selection and requires attestation |
| Raw/invalid/null/harmful retention | Atomic raw journals and complete-case estimates with unknown-outcome bounds | Retained; validation failures remain recorded; mock summaries cannot claim validated same-response interventions |
| Preservation and opt-in | Existing opt-in backend loading and plan integrity | Retained; v1 plans rejected with reproducibility commit guidance; all 585 old output-file hashes unchanged |

Primary 2A is the world-mean gold-versus-pattern log-odds change from k=0 to k=64
under the checkpoint cue. Primary 2B is availability repair minus meaning-control
final accuracy. Raw generation logits do not estimate these preferences.
See `REASONING_CONTINUATION_V2_PROTOCOL.md` for precise exclusions, contrasts,
bootstrap units, coverage and confounds; `CONTINUATION_V2_RUNBOOK.md` has all exact
offline, local validation, collection and confirmation commands.

## Modified/added files

- Runtime patches: `exception_continuation/{core,backend,runner,edits,analysis,__main__}.py`.
- Supporting checks: new `exception_continuation/validation.py`.
- Tests: updated `tests/test_continuation_followup.py`; added `tests/test_continuation_v2.py`.
- Versioned specification/config: `REASONING_CONTINUATION_V2_PROTOCOL.md`,
  `CONTINUATION_V2_RUNBOOK.md`, this audit, `configs/continuation_v2.json`.
- New previews only: `previews/continuation-v2/{preview.md,branch-preview.json,validation-status.json}`.

## Tests actually run

```bash
python -m unittest discover -s tests -p 'test_continuation*.py' -v
python -m unittest discover -s tests -v
python -m exception_continuation prepare --phase selection --config configs/continuation_v2.json --output runs/continuation-v2-preview
python -m exception_continuation analyze --output runs/continuation-v2-preview
```

**20/20 focused tests; 389/389 full-suite tests passed.** The full suite ran after
all runtime changes. `git diff --check` passed. Also ran the CLI mock path in a
separate `runs/continuation-v2-mock-audit` directory: prepare, validate, collect,
measure, review-export, freeze-edits, intervene and analyze. The one manually
specified synthetic edit case is an illustrative software fixture, not a
scientific cohort. The committed branch preview is explicitly labeled synthetic.

Tests include distribution disagreement with identical output tokens, missing or
nonfinite logits, numerical tolerances, no future-token leakage, candidate leading
whitespace, fresh edited suffixes, no 2A dependency for 2B, boundary cuts beyond
128, protected preceding text, wrong/invalid originals, behavior-gated confirmation,
discovery separation, legacy-version rejection and no implicit model loading.

Mock replay passes leave `real_model_status=PENDING` and
`validated_same_response_interventions=false`. Default mock calibration fails,
so it cannot unlock scientific confirmation. A separate synthetic calibrated
fixture exercises the software lock and cannot be used to start a live run.

## Still pending / scientific choices

No real model, API, cloud resource or model download was used. The real local
backend, model/template compatibility, numerical replay fidelity and behavior
replication remain **PENDING**, not validated by offline tests. Select an available
local model and plain visible assistant interface; freeze precision/tolerances,
cues and practical calibration thresholds before selection. Other thinking-channel
formats need a separately specified and calibrated interface.

The default behavior gate tests matched direct-correct / reasoning-pattern errors,
not the prevalence of false-missingness claims; 2B may have no eligible cohort.
Human truth, grammaticality and meaning-preservation judgments remain required.
Edits can change wording and token length, and fixed generated-token checkpoints
are not semantic stages. Conditional readouts are not internal beliefs; repaired
continuation effects alone do not identify a reasoning mechanism. A 2A-informed
discovery rule needs fresh confirmation rather than relabeling discovery cases.
