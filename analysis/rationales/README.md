# Offline rationale audit

This audit uses only archived responses. There were no model API calls and no
changes to the archived plans or journals. The five archives are preserved at
the repository root. Each output directory contains `rationales.csv`,
`summary.md`, `audit.json`, `rationale_sample.md` and a separate `sample_key.json`.

| Run | Selected arms | Scorable responses | Wrong | Wrong: never detected | Wrong: relabeled missing | Wrong: stated then overridden |
|---|---|---:|---:|---:|---:|---:|
| [cue-001](cue-001/summary.md) | visible | 48 | 25 | 13 | 9 | 3 |
| [explanation-001](explanation-001/summary.md) | cot, recorded variants | 48 | 23 | 11 | 9 | 3 |
| [order-001](order-001/summary.md) | reasoning_first | 24 | 9 | 8 | 1 | 0 |
| [revision-001](revision-001/summary.md) | reasoning_first and revision, separately tabulated | 96 | 33 | 30 | 2 | 1 |
| [mistral-prefix-v2-001](mistral-prefix-v2-001/summary.md) | base visible, no replay | 24 | 9 | 3 | 5 | 1 |

These are provisional **automated lexical codes**. `never_stated` means that
the conservative heuristic did not detect an explicit record assertion. It does
not establish absence of such an assertion, retrieval failure, or an internal
task representation. Acknowledgment in an enumerated class group counts;
merely saying that features resemble a class does not. Missing-label evidence
takes priority in the categorical code, while both flags remain available.

Across the five runs, the revised record-assertion flag differs from the initial
brief's single-line regex on **86/240 responses**. The regex misses multiline
attribute lists and class-first membership groups, and can treat inferential
comparisons as record acknowledgments. Both versions are retained in the CSV.
Among the 99 wrong selected responses, 91 have no detected assertion or a
missing-label assertion; this pooled count is descriptive and is not an
independent-world estimate. Revision arms are correlated within world.

## Development checks, not independent validation

Hand-written unit tests cover the four classes, multiline records, class-group
membership, copied rows, negated missingness, rhetorical questions, inferential
comparisons and JSON reasoning fields. A seeded 20-response development spot
check (seed 492017 over the five runs in the order above) was inspected by the
coding assistant with outcomes visible. It found two clear missed formats:
`PLATE: ?` and `PLATE (Class X): attributes`. Both were added to the rule and
regression tests. This same sample therefore cannot validate the resulting rule.
No independent blinded human validation has been performed.

The 20-response blind samples in each directory use seed 981723. Terminal answer
fields, gold, correctness and source identifiers are hidden; the target's gold
table cell is masked. The reasoning itself can reveal a proposed answer.
Annotators should mark explicit recorded labels, missing assertions and evidence
first. Outcome-dependent categories require later unblinding with `sample_key.json`.

## Reproduction

Extract each root archive into its original `runs/<name>` path only if absent.
Never overwrite an existing run directory. Then, for each run:

```sh
python3 code_rationales.py --run runs/cue-001 --out analysis/rationales/cue-001 --sample 20 --seed 981723
```

Package selection follows `plan.json["protocol_version"]`, not folder names.
The coder checks plan hashes, attempt identity, task metadata and the original
protocol's answer scoring. It includes only scorable recorded-gold visible
responses; missing-gold tasks, anchors and replay tasks are excluded.
`audit.json` binds the plan, accepted records and exact coder source. Output
must be outside the source run directory.
