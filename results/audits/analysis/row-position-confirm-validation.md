# Fresh-world row-position confirmation: offline validation

The implementation is ready for the fixed 960-response Mistral confirmation
study described in `ROW_POSITION_CONFIRM_PROTOCOL.md`. No live model calls were
made during implementation or validation. The simulated outputs are software
fixtures, not evidence about model behavior.

## Checks completed

- All **43 new confirmation tests** passed, covering design, runner, analysis,
  and manual trace review. The final new-study suite completed in 21.572 seconds.
- The **29 existing row-position tests** and **18 query-form tests** also passed:
  **90 distinct passing tests** across the new study and these regressions.
- The new worlds use seed 2026101202, balance all six label-role permutations
  across two target climates with two worlds per combination, and have unique
  plate identities excluded from the 24-world development cohort. Both the world
  order and each world's 40-task schedule are deterministically shuffled.
- Every world appears at all ten target positions, with both recorded-label
  variants and both response instructions. Relocation preserves record contents
  and the relative order of the other nine rows.
- Synthetic analysis checks cover the endpoint interaction, variant averaging,
  pairing, signed missing-answer bounds, primary completeness despite missing
  intermediate responses, boundary and middle contrasts, all 20 adherence cells,
  and the directional 20-point decision rules. Large degenerate effects retain
  a precision warning; small degenerate effects remain inconclusive.
- Execution checks cover immutable run identity, journal integrity, explicit
  transport retries, attempt caps, retained invalid answers, and separation of
  mock and live collection. Existing study code and configurations remain
  unchanged.
- Manual trace checks cover independent nullable codes, exact evidence quotes,
  ordered gold-then-final-answer evidence, positive/negative review attribution,
  partial-review denominators, invalid visible outputs, immutable exported
  metadata, stale-journal rejection, and refusal to overwrite review files.

## Full offline workflow

The complete CLI workflow passed: prepare, 40 simulated calls, resume for 920
more, analyze, export traces, and summarize the unannotated review file. It
retained **960 valid returned responses** and exported **480 visible responses**.
All manual annotations remained unknown: there were zero reviewed judgments,
not zero observed phenomena. The decision remained `simulated_only`.

Analysis writes the ten-row accuracy curve to `row_curve.csv` and
`row_curve.svg`. The summaries also report harm at every row, the primary
estimate, per-world contrasts, full-plan bounds, and validity/adherence counts.
Secondary curve intervals are pointwise and unadjusted.

## Frozen preview

The frozen plan hash is
`534e56c260494450ce31dfb9fd295b565ef5ed1291a5772e1e9503c049efb506`.

The fresh-world content digest is
`abe6a2250e622983a3957ab065a10ad15ee0e1b2d3d7fa955bdc4cc696b1d4cf`.

`previews/row-position-confirm-mistral/` contains the plan, provider configuration,
all 960 exact request previews in JSON, and a readable preview of the first
world's 40 requests. Prepare a separate run directory for live collection; do
not collect into the preview directory or reuse a simulated directory.

These checks establish software and protocol consistency. They do not predict
the scientific outcome or extend a future confirmation beyond fresh worlds from
the same generator family.
