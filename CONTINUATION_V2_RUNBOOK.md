# Study 2 v2 runbook

Use branch `codex/reasoning-continuation-followup`. Read
`REASONING_CONTINUATION_V2_PROTOCOL.md` before collection. All commands run from
the repository root. V1 directories and artifacts remain unchanged; checkout
commit `1be7551d058f5d7db64c16cb8ffa6e42ae01ac91` to reproduce v1 analysis.
V2 requires **new output directories**. Do not overwrite old runs or previews.

## Offline tests and prompt preview (no model dependencies or calls)

```bash
python -m unittest discover -s tests -p 'test_continuation*.py' -v
python -m unittest discover -s tests -v
python -m exception_continuation prepare --phase selection --config configs/continuation_v2.json --output runs/continuation-v2-preview
python -m exception_continuation analyze --output runs/continuation-v2-preview
```

The exact planned user messages are in `preview.json`; `preview.md` shows a small
sample. These previews have no loaded model/template and make no token-position
or real-model fidelity claim. `summary.json` says PENDING for both experiments.

## Optional mock walkthrough (software fixtures only)

```bash
python -m exception_continuation prepare --phase selection --config configs/continuation_v2.json --output runs/continuation-v2-mock
python -m exception_continuation validate --output runs/continuation-v2-mock --mock
python -m exception_continuation collect --output runs/continuation-v2-mock --mock
python -m exception_continuation review-export --output runs/continuation-v2-mock
python -m exception_continuation measure --output runs/continuation-v2-mock --mock
python -m exception_continuation analyze --output runs/continuation-v2-mock
```

Mock success NEVER establishes real-model validation. The default always-A mock
also fails the behavioral calibration gate. Tests exercise calibrated fixtures,
edits and failure paths; those fixtures are not scientific evidence.

## Real local model validation and selection — explicitly opt-in, NOT run here

Prerequisites: an already installed compatible PyTorch/Transformers/tokenizers
environment and an existing local decoder-only model directory containing weights,
tokenizer and a saved chat template. There is no installation/download command.
This implementation uses `local_files_only=True`, `trust_remote_code=False`,
greedy decoding, eager attention and fresh full-prefix prefill for each branch.
It does not launch cloud resources or use an API. Model loading can need substantial
local RAM/VRAM. Only plain visible assistant prose is supported in v2.

Create a local config, then edit `model_dir`, `device`, `dtype` and, if supported by
that template, `chat_template_kwargs: {"enable_thinking": false}`. Review cues,
calibration minimums and numerical tolerances BEFORE any selection generation.
`max_new_tokens` remains 512. Do not set `enable_thinking` to true.

```bash
cp configs/continuation_v2.json configs/local-continuation-v2.json
# Edit configs/local-continuation-v2.json with your existing local model path.
python -m exception_continuation prepare --phase selection --config configs/local-continuation-v2.json --output runs/continuation-v2-selection
python -m exception_continuation validate --output runs/continuation-v2-selection --live
python -m exception_continuation collect --output runs/continuation-v2-selection --live
python -m exception_continuation review-export --output runs/continuation-v2-selection
```

`validate` compares uninterrupted and unchanged-prefix generation on three
technical prompts, including full next-token distributions and exact deterministic
suffixes. It saves `validation.json`, `validation-status.json`, identity metadata
and raw operation records. Failure blocks collection; no automatic retry.
`collect` verifies/reuses this validation, then generates each original response
once to EOS/cap. `calibration.json` records the separate behavior-replication gate.
A technical pass alone does not validate any edited case.

Manually complete **every** row of `review.json`. Positive cases need original
`statement_span`/`statement`, exact narrower `span`/`old`, all three replacements,
reviewer, justification and the semantic/grammar/first-false-statement certifications.
Spans are zero-based Python character offsets `[start,end)`. Copy original text
exactly. Negatives need review, reviewer and justification too. Do not select by
final correctness. Declare `selection_basis`; any 2A-informed edits are discovery.
Do not edit generated source fields, table, preliminary entry or unrelated text.

```bash
python -m exception_continuation freeze-edits --output runs/continuation-v2-selection --review-file runs/continuation-v2-selection/review.json
python -m exception_continuation measure --output runs/continuation-v2-selection --live
python -m exception_continuation intervene --output runs/continuation-v2-selection --live
python -m exception_continuation analyze --output runs/continuation-v2-selection
```

2A (`measure`) and 2B (`intervene`) can run independently after their prerequisites.
Intervention collection automatically performs the additional statement-boundary
uninterrupted-reference/replay checks, then generates a fresh suffix per arm.
No cached state from changed text is reused. Each call is journaled before/after;
repeating a completed command reuses its identical artifact, not another sample.
Incomplete calls require review, never silent regeneration or overwriting.

## Fresh confirmation after selection passes

The same selected config and backend identity must pass calibration and technical
replay. Record the selection decision; do not tune on confirmation outcomes.
Each confirmation trajectory will be new. Set the review's
`selection_basis="predeclared_first_false_missingness"` and
`no_2a_selection_attested=true` only when accurate. Freeze edits before inspecting
confirmation readouts. If discovery changes the edit rule, version and freeze that
rule on discovery cases before collecting fresh confirmation cases.

```bash
python -m exception_continuation prepare --phase confirmation --config configs/local-continuation-v2.json --selection-output runs/continuation-v2-selection --selection-note 'Frozen model/interface passed the preregistered replication gate; edits use the predeclared rule.' --output runs/continuation-v2-confirmation
python -m exception_continuation validate --output runs/continuation-v2-confirmation --live
python -m exception_continuation collect --output runs/continuation-v2-confirmation --live
python -m exception_continuation review-export --output runs/continuation-v2-confirmation
# Complete all review rows and attest the selection basis before proceeding.
python -m exception_continuation freeze-edits --output runs/continuation-v2-confirmation --review-file runs/continuation-v2-confirmation/review.json
python -m exception_continuation measure --output runs/continuation-v2-confirmation --live
python -m exception_continuation intervene --output runs/continuation-v2-confirmation --live
python -m exception_continuation analyze --output runs/continuation-v2-confirmation
```

Inspect `study-2a-summary.json` and `study-2b-summary.json` separately. All raw
tokens, likelihoods, edited spans, fresh suffixes, invalid responses and exclusions
remain in the source artifacts. Full-vocabulary logits at selected cuts support
replay validation only. Defaults store multiple copies in audit artifacts, so
reserve disk space; no full every-token logit dump is promised.

## Choices still requiring prospective scientific decisions

Select and calibrate an existing local model/interface. Freeze appropriate
precision/tolerances and the practical calibration thresholds before selection.
The current gate reproduces direct-versus-reasoning pattern errors; it does not
guarantee a sufficient false-missingness cohort for 2B. Report an empty cohort if
that behavior is absent. Manual edit truth/grammar/meaning certification remains
required. Equal suffix budgets do not equalize total edited-prefix length; retain
and report that limitation. Real replay fidelity and behavior remain **PENDING**.
