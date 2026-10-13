# Study 2 v3 runbook and workload

Use branch `codex/reasoning-continuation-followup`. Read
REASONING_CONTINUATION_V3_PROTOCOL.md first. V1/v2 protocols and outputs are
historical; use commits 1be7551 / 4baf414 for their original execution/analysis.
V3 refuses old plans. Use NEW directories and fresh v3 selection/confirmation.
This patch does not validate a real model or its behavioral replication.
Use Python 3.10 or newer. On the audit host the tested interpreter is
`/opt/homebrew/bin/python3.12`; substitute that path for `python3` below if
the checkout's shell resolves `python3` to the unsupported system Python 3.8.

## Offline checks and preview

```sh
python3 -m unittest discover -s tests -p 'test_continuation*.py' -v
python3 -m unittest discover -s tests -v
python3 -m exception_continuation prepare --phase selection --config configs/continuation_v3.json --output runs/continuation-v3-preview
python3 -m exception_continuation analyze --output runs/continuation-v3-preview
```

No inference, model loading or downloads occur in these preview commands. The
preview's real-model status is PENDING. Optional `--mock` operations are software
fixtures and cannot establish live validation or scientific calibration.

## Prospective local execution — not run by this patch

Prerequisites: installed compatible PyTorch/Transformers/tokenizers and an
already obtained local decoder-only model with tokenizer/chat template. No
automatic downloads. Copy `configs/continuation_v3.json` to
`configs/local-continuation-v3.json`, then set `model_dir`, `device`, `dtype`,
and supported `enable_thinking:false` template kwargs. Freeze tolerances,
calibration thresholds, readout cues and event subset before selection.
Do not change the fixed 512 budget or enable hidden thinking.

```sh
python3 -m exception_continuation prepare --phase selection --config configs/local-continuation-v3.json --output runs/continuation-v3-selection
python3 -m exception_continuation validate --output runs/continuation-v3-selection --live
python3 -m exception_continuation collect --output runs/continuation-v3-selection --live
python3 -m exception_continuation review-export --output runs/continuation-v3-selection
```

Complete EVERY row of `runs/continuation-v3-selection/review.json`. Annotate the
first explicit false-missingness statement with exact spans and the existing
three matched replacements. Include reviewer and semantic/grammar/first-statement
certifications and justify negatives. Do not select by final correctness.
Freeze annotations before viewing corresponding event readouts:

```sh
python3 -m exception_continuation freeze-edits --output runs/continuation-v3-selection --review-file runs/continuation-v3-selection/review.json
python3 -m exception_continuation freeze-events --output runs/continuation-v3-selection
python3 -m exception_continuation measure --output runs/continuation-v3-selection --live
python3 -m exception_continuation measure-events --output runs/continuation-v3-selection --live
python3 -m exception_continuation intervene --output runs/continuation-v3-selection --live
python3 -m exception_continuation analyze --output runs/continuation-v3-selection
```

`intervene` requires neither `measure` nor `measure-events`. Event measurement
requires its frozen event manifest, collection and technical validation, not
fixed-checkpoint results or edited continuations. No cue is inserted into any
natural generation. Repeat commands reuse identical journaled operations;
unresolved operations require reconciliation, never silent resampling.

After selection passes technical validation AND behavioral calibration, record
the prospective selection decision. Confirmation uses the SAME frozen config
and backend identity. Review all new visible trajectories; confirmation review
requires `selection_basis="predeclared_first_false_missingness"` and a truthful
`no_2a_selection_attested=true`. Freeze before viewing any confirmation readouts.

```sh
python3 -m exception_continuation prepare --phase confirmation --config configs/local-continuation-v3.json --selection-output runs/continuation-v3-selection --selection-note 'Frozen configuration passed selection replay and behavioral calibration.' --output runs/continuation-v3-confirmation
python3 -m exception_continuation validate --output runs/continuation-v3-confirmation --live
python3 -m exception_continuation collect --output runs/continuation-v3-confirmation --live
python3 -m exception_continuation review-export --output runs/continuation-v3-confirmation
# Manually complete all confirmation review rows before these commands.
python3 -m exception_continuation freeze-edits --output runs/continuation-v3-confirmation --review-file runs/continuation-v3-confirmation/review.json
python3 -m exception_continuation freeze-events --output runs/continuation-v3-confirmation
python3 -m exception_continuation measure --output runs/continuation-v3-confirmation --live
python3 -m exception_continuation measure-events --output runs/continuation-v3-confirmation --live
python3 -m exception_continuation intervene --output runs/continuation-v3-confirmation --live
python3 -m exception_continuation analyze --output runs/continuation-v3-confirmation
```

Inspect `study-2a-summary.json`, `study-2a-events-summary.json` and
`study-2b-summary.json` separately. Analyze can also report partial intervention
attempts without resuming failed calls. Missing/unassessed outcomes remain unknown.
Full-vocabulary logits are retained for replay support; reserve disk for audit
artifacts. No dense every-token logit/readout sweep is added.

## Operation accounting (selection + confirmation, one model attempt)

Known originals: 48 selection + 96 confirmation = **144**, shared by 2A/2B;
72 direct and 72 visible. Confirmation is conditional on selection passing.
Only visible trajectories receive scientific checkpoint readouts/interventions.

| Operation | Formula | Default maximum |
|---|---|---:|
| Shared scientific originals | 144 | 144 |
| Technical reference generations | 3 per phase | 6 |
| Technical prefix replay generations | T | 24 |
| Fixed-checkpoint replay generations | C | 288 |
| Fixed readouts | F + S | 432 |
| Fixed candidate scoring forward passes | 3(F + S) | 1,296 |
| 2B uninterrupted reference generations | E | 72 |
| 2B prefix replay generations | E | 72 |
| 2B four-arm continuations | 4B | 288 |
| Of those, edited prefixes / unchanged controls | 3B / B | 216 / 72 |
| 2B secondary candidate scoring forward passes | 12B | 864 |
| Event uninterrupted reference generations | R | 72 |
| Event unique-cut replay generations | U | 216 |
| Event candidate scoring forward passes | 3V | 648 |

T is available technical cuts; C is available fixed cuts; F<=C counts passing
fixed cuts and S<=144 passing sensitivity cuts at 0/64. E is frozen 2B cases
reaching branch validation; B<=E also passes validation/tokenization and reaches
the arm loop. R counts trajectories with any available configured event; U<=3R
counts UNIQUE event cuts; V<=U counts passing event cuts. Exact coincidences
between event labels share an operation, not between separate study commands.
All availability/failure outcomes remain reported. Errors may interrupt a loop,
so attempted/returned counts come from journals rather than these upper bounds.

Maximum generation calls: 144+6+24+288+72+72+288+72+216 = **1,182**.
Of these, **600** are prefix replay generations. There are another **72**
unchanged-arm replay comparisons using already-counted control continuations,
for up to **672** suffix/distribution checks. Whole-reference identity checks
are additional checks without extra calls. Candidate scoring totals **2,808**
forward passes (936 three-candidate readouts). No candidate is freely generated.
Disabled events remove up to 288 generation calls and 648 scoring passes.
Technical `validate` then `collect` reuses its six references/24 replays.

These are design maxima, not an assertion that 72 eligible intervention cases
exist or all four fixed cuts survive. There may be no false-missingness cohort.
