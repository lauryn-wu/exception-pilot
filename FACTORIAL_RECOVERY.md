# Formatting-failure continuation amendment

Amendment `factorial-format-continuation-v1`, specified 2026-10-08 **after**
inspecting the uploaded partial factorial run. This amendment changes how
collection proceeds after an unparseable returned answer. It does not change
any question, record, schedule, model, output budget, answer parser, or planned
640-task sample. The original packages and their source fingerprints are frozen.

## Observed reason for the amendment

The run stopped at attempt 596, with 595 valid answers and 44 unattempted tasks.
The model returned a complete response ending in a sentence saying the target
belongs to class B. The exact recorded class was B. It omitted the required
standalone final A/B line, so the frozen parser marked it invalid. There was no
timeout or truncation. The strict analysis currently has 18 complete lists.

The partial behavioral results were visible before this amendment was written.
This is therefore a documented post-result continuation, not an unmodified
completion of the initial collection protocol. Do not relabel it as such.

## Fixed continuation policy

- Preserve every existing attempt file byte for byte, including attempt 596.
- Do not infer a replacement answer from prose. Keep the invalid answer invalid.
- Never request another response for a task that already returned any answer.
- Continue the existing frozen schedule only for tasks with no returned answer.
  For this upload that means 44 additional requests, absent transport errors.
- Preserve any further complete but unparseable responses as invalid and continue.
  Incomplete, refused, or model-mismatched responses still stop for inspection.
- Transport errors and interrupted requests require `--retry-errors`; a previous
  request interrupted in flight may already have been billed.
- Record the amendment, recovery-code fingerprint, initial attempt count, and a
  digest of the pre-recovery journal in `recovery.json`. Guard them on resume.

The original strict report still excludes lists with any invalid endpoint and
retains its `technical_failure` status. If there are no further invalid answers,
the completed collection will contain 639 valid answers, one retained invalid,
and 19 strictly complete lists. That falls short of the original 20-list valid
sample and must be disclosed. The wrapper does not award a scientific pass or
authorize another study.

An additional report gives full-plan point-estimate sensitivity bounds: assign
every invalid endpoint both possible correctness values, accounting for the
sign of its coefficient in each linear contrast. These are sharp bounds over
the unknown binary scores, not imputed ground truth or confidence intervals.
Different contrasts can attain their bounds under different assignments. They
do not incorporate sampling uncertainty. Bounds appear only after every planned
task has a returned response; they supplement the unchanged strict analysis.

## Commands

From the Git checkout, with the same OpenAI API key set:

```bash
git pull --ff-only
caffeinate -i python3 factorial_recovery.py run --output runs/factorial-001 --max-calls 44 --resume
zip -r factorial-001.zip runs/factorial-001
```

Expected completion: `all_planned_tasks_returned`, zero `tasks_without_return`,
and the retained invalid count. `strict_analysis_status: technical_failure`
remains expected because the original endpoint was not parseable. This does not
mean the continuation failed. Do not rerun the invalid task to remove that status.

After resolving a transport error, use the same recovery command with
`--retry-errors`. It skips every returned answer, including invalid ones.

To regenerate both reports without API calls:

```bash
python3 factorial_recovery.py analyze --output runs/factorial-001
open runs/factorial-001/recovery-summary.md
```

`summary.md` and `summary.json` remain the strict analysis. The supplemental
`recovery-summary.md` and `recovery-summary.json` disclose all invalid responses,
collection completeness, and sensitivity bounds. Live and mock runs cannot mix.
No model calls are made by the offline tests or by `analyze`.
