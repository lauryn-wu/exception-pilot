# Feature competition and explanation follow-up

These are two separate, fixed experiments. Both use `gpt-4o-2024-08-06` at
temperature 0. Preparation, tests, and analysis are offline. Only `run` without
`--mock` calls the API. Neither study has live results with this addition.

| Study | Question | Planned calls | Independent units |
|---|---|---:|---|
| `exception_features` | Does changing the feature pattern change how answers use the explicit record? | 648 | 36 fresh worlds |
| `exception_downstream` | Can a false missingness claim affect the next factual answer despite an initially correct answer? | 342 | 9 source worlds in the primary cohort; controls reported separately |

The feature study crosses two recorded classes, three feature arrangements, and
three response instructions in every world. The strongest comparison swaps the
feature bundles assigned to the two competing classes while preserving all
column value counts, table dimensions, and the third class's rows. The balanced
feature condition balances the two record candidates and is a separate reference.
Twelve-row tables keep the background-pattern class most frequent under both
record variants, avoiding a correct-answer shortcut from the overall majority.
This is a controlled new task, not a
reconstruction of the cause of the original random-column result. See
[FEATURES_PROTOCOL.md](FEATURES_PROTOCOL.md).

The downstream study reuses complete saved user prompts and assistant responses.
Each intervention creates a separate three-message conversation ending in a
literal question about the table cell. The primary repair changes only annotated
false `MISSING` claims to `RECORDED`; it introduces no additional correct-class
tokens. Repeated calls are averaged within source cases and source worlds. The
study does not treat reconstructed conversations as restored hidden states. See
[DOWNSTREAM_PROTOCOL.md](DOWNSTREAM_PROTOCOL.md).

## Use a separate checkout

Keep this checkout unchanged while either study runs. Existing experiments can
continue in their own worktrees. These commands assume the main checkout is
`~/exception-pilot` and the new directory does not already exist:

```bash
cd ~/exception-pilot
git fetch origin
git worktree add ../exception-pilot-followups origin/codex/features-and-downstream
cd ../exception-pilot-followups
```

Python 3.10+ and the standard library suffice. Run from this checkout's root;
the historical package-installation configuration is unchanged. Set
`OPENAI_API_KEY` in the terminal before either live command.

## Inspect the frozen requests

```bash
python3 -m unittest discover -s tests -p 'test_features*.py' -v
python3 -m unittest discover -s tests -p 'test_downstream*.py' -v
python3 -m unittest discover -s tests -p 'test_study_support*.py' -v

python3 -m exception_features prepare \
  --config configs/features_gpt4o.json --output runs/features-gpt4o-001
python3 -m exception_downstream prepare \
  --config configs/downstream_gpt4o.json --output runs/downstream-gpt4o-001
```

Each output directory contains the frozen plan, `preview.json` with every exact
provider request, and a shorter readable `preview.md`. Neither command collects
responses. The plan includes scoring and analysis identities for later checks.

## Run the fixed collections

On macOS, `caffeinate -i` keeps the computer awake. Omit it on other systems.
These two commands run sequentially and request all 990 planned responses:

```bash
caffeinate -i python3 -m exception_features run \
  --config configs/features_gpt4o.json --output runs/features-gpt4o-001 \
  --max-calls 648

caffeinate -i python3 -m exception_downstream run \
  --config configs/downstream_gpt4o.json --output runs/downstream-gpt4o-001 \
  --max-calls 342
```

You can instead run them in two terminals in this same checkout: they use
different output directories and process locks. Do not edit or switch this
checkout's source while collection is active.

An invocation can be limited with a smaller `--max-calls`; this changes how many
new attempts that invocation makes, not the frozen total. Resume with the same
command plus `--resume`. A known transport error additionally requires
`--retry-errors`. A returned wrong or invalid response is retained and never
retried. An unresolved in-flight request or a model-identity failure stops the
run for review. Attempt caps are 684 and 378 respectively; there is no automatic
sample extension or follow-up run.

## Analyze and package

The run commands write summaries automatically. Reanalysis makes no model calls:

```bash
python3 -m exception_features analyze --output runs/features-gpt4o-001
python3 -m exception_downstream analyze --output runs/downstream-gpt4o-001
zip -r features-gpt4o-001-results.zip runs/features-gpt4o-001
zip -r downstream-gpt4o-001-results.zip runs/downstream-gpt4o-001
```

Both summaries retain invalid and unreturned denominators and paired estimates.
Mock runs must use separate directories and `--mock` on every invocation. They
are labeled simulated software checks and are never model evidence.
