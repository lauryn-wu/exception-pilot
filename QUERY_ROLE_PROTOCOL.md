# Reporting a fact versus using it

Protocol: `query-conditioned-fact-use-v1`.

This is a prospective, bounded screen of a specific behavioral hypothesis:
requesting a visible explanation may reduce use of a supplied observation when
reporting that observation, while preserving its use in answering about another
property. This predicted interaction has not yet been observed in this design.
Earlier direct-versus-explanation results motivate it but do not establish it.

## Design

There are 12 new independent worlds: six vehicle-record worlds and six device
configuration worlds. Each world has two source-value versions, three question
types, and two response instructions: **12 × 2 × 3 × 2 = 144 planned calls**.
One response is collected per condition. All calls are separate conversations.
No old answers, assistant prefixes, stopping points, or replay probes are used.

Vehicle worlds have 18 peer records, six in each of three regions. Each region
has a different consistent peer class. The target's recorded class takes either
of the two classes that conflict with its region's peer pattern. Configuration
worlds supply site defaults and device-specific settings, with the rule:

> A device-specific setting determines the active mode when present.
> Otherwise the site default applies, if one exists.

The target override takes either of the two modes different from its unchanged
site default. Thus both source versions are exceptions; the manipulation does
not switch between an ordinary and exceptional case.

Within a source pair, only the target value changes. All questions about a given
version receive exactly the same context. The context contains two mapping
columns with **identical bijections**: a coded notation for the class/mode, and
its downstream gate/signal. Identities, row order, mapping-column order, source
ordering, and call order are varied before collection. The six bijections and
three competing categories are balanced within each family. The seeded mapping
assignment also makes each code occupy each source role (a, b, competitor)
exactly twice per family; it is chosen before any responses are collected.

For example, suppose Q7 is recorded as B despite its neighbors being A, with
A → K, B → Z, C → R in both mapping columns:

| Query | Question | Correct with B record | Correct with C record |
|---|---|---|---|
| Literal | Which class does vehicle Q7 belong to? | B | C |
| Encoded | Which class does vehicle Q7 belong to? Use the class's coded notation. | Z | R |
| Downstream | Which dispatch gate is vehicle Q7 assigned to? | Z | R |

The primary comparison is **encoded versus downstream**. Both apply one
bijection and use the same output alphabet. Both use the original class as a
computational intermediate. The difference concerns the property asked about;
it does not isolate an intermediate token versus an output token. Literal
reporting is a secondary reference, not a third interchangeable primary test.

The exact direct instruction is:

```text
Give only your final answer in this format:
FINAL: <answer>
```

The exact visible-explanation instruction is:

```text
Explain your answer step by step, then give your final answer in this format:
FINAL: <answer>
```

`prepare` writes every full prompt, API setting, and gold answer to `preview.md`
and `preview.json`. Gold answers and other analysis metadata are not included
in the API messages. These files, the complete plan, configuration, and relevant
source code are checked for changes before resumption.

## Model and collection settings

| Setting | Value |
|---|---|
| Model | `mistral-small-2603` |
| Temperature / top_p | 0.6 / 0.95 |
| reasoning_effort | `none` |
| Maximum output tokens | 1,600 in both modes |
| Generation seed | 2026101001 |
| Bootstrap seed / resamples | 2026101002 / 10,000 |
| Minimum request-start interval | 10 seconds |
| Per-request timeout | 120 seconds |
| Extra transport attempts | At most two per task and nine across the run |
| Maximum API attempts | 153 |

The seed controls generation and scheduling; it does not make model responses
deterministic. The manipulation tests requesting a visible explanation, not
hidden computation or equal total inference effort. The token limit is held
constant but actual generated lengths may differ.

## Primary measure

Decode an answer to its source category using the known bijection. For source
values `a` and `b`, assign decoded `a` a score of −1, decoded `b` +1, and the
third category 0. Literal responses use the identity mapping.

```text
R = [score(answer with source b) - score(answer with source a)] / 2

D = (R_downstream_visible - R_encoded_visible)
    - (R_downstream_direct - R_encoded_direct)
```

`R=1` means both answers track their supplied values; `R=-1` means reversed
tracking; an unchanged decoded answer gives `R=0`. One-sided tracking can give
±0.5. This is **record-consistent counterfactual responsiveness**, not a direct
measure of internal retrieval. Mapping errors remain possible.

Average independent worlds equally. Report the four component responsiveness
means, family-level contrasts, accuracy, and competitor-choice rates. Compute
descriptive 95% bootstrap intervals by resampling whole worlds within families.
Complete-case estimates weight eligible worlds equally; their bootstrap
preserves the eligible family proportions. Report exclusion counts explicitly.
Full-plan missing-answer bounds retain every planned world with equal weight,
and therefore retain the planned equal weight of the two families.

The final nonempty line must be `FINAL: <allowed answer>`; case and surrounding
whitespace are ignored. Earlier explanation text is not scored as the answer.
Malformed, empty, and truncated completions remain unscorable and are never
regenerated. Instruction adherence is reported separately from answer accuracy.
Completed responses with model-identity drift stop collection and are retained.

For missing or unscorable responses, let each answer score range over [−1,+1]
to calculate full-plan bounds on each linear contrast. These are point-estimate
bounds for missingness, not confidence intervals. Shared terms are combined
before calculating bounds. Scorable-only results do not replace these bounds.

## Fixed advance rule

Finish the entire batch before applying the rule. Advance only if all hold:

| Requirement | Threshold |
|---|---|
| Scorable responses | At least 137 of 144 |
| Direct-mode accuracy | At least 22 of 24 for each query type; unscorable counts as incorrect |
| Encoded reporting worsens | Mean `R_encoded_direct − R_encoded_visible ≥ 0.15` |
| Downstream use stays responsive | Mean `R_downstream_visible ≥ 0.75` |
| Differential explanation effect | Mean `D ≥ 0.15` |
| Agreement across families | Positive encoded deterioration and positive D in each family |

Use worst-case full-plan lower bounds for the responsiveness and direction
criteria when relevant answers are unscorable. This prevents missingness or
downstream improvement alone from creating a misleading positive.

These are **practical spending criteria**, not significance tests. A failed
screen means insufficient support to fund the specified extension at this
budget, not proof that the phenomenon does not exist. Do not select favorable
worlds, rerun valid errors, or loosen thresholds after seeing results. Software
simulations are marked as such and cannot authorize a scientific advance.

If the screen passes, the proposed follow-up is 24 fresh worlds with additional
competitor-removal conditions, requiring 576 planned calls. That second study
is **not implemented or started automatically**. It requires a separately
frozen manifest. For vehicles it would balance class frequencies within each
region while preserving overall frequencies; for devices it would remove the
target site's default while preserving the override. Those are distinct
ablations and must be interpreted separately.

## What the outcomes mean

- Literal fails but encoded and downstream succeed: a transformation/retrieval
  scaffold is sufficient; the semantic-role hypothesis is weakened.
- Encoded and downstream both fail: compatible with a more general failure
  under an explanation request; the distinctive prediction is unsupported.
- Encoded tracking declines while downstream tracking remains strong, beyond
  their direct-mode difference: supports the operational query-role interaction
  and justifies a fresh controlled replication.

Even a replicated positive would not establish that the model internally knows
the fact, marks it unavailable, or suppresses its representation. Query wording,
retrieval cues, and competition with defaults remain possible explanations.
This screen is not a mechanistic result or a promise of conference acceptance.

## Run on macOS

Run from the repository directory. No extra Python packages are required
(Python 3.10 or newer; the current laptop's Python 3.12 is suitable).

```bash
cd ~/Documents/Codex/exception-pilot
git pull --ff-only
```

If Git reports a non-fast-forward error, stop before the Python commands and
inspect `git status` and `git log --oneline --left-right HEAD...origin/main`.
Preserve local work; do not reset or delete your runs to fix a Git divergence.

Set the key in your current zsh terminal if necessary; do not put it in JSON or
commit it:

```zsh
read -s "MISTRAL_API_KEY?Paste your Mistral API key: "
echo
export MISTRAL_API_KEY
```

Prepare and inspect the exact prompts without spending credits:

```bash
python3 -m exception_query_role prepare --config configs/query_role.json --output runs/query-role-001
open runs/query-role-001/preview.md
```

Collect the full fixed first screen:

```bash
caffeinate -i python3 -m exception_query_role run --config configs/query_role.json --output runs/query-role-001 --max-calls 144
```

For a short transport check you may use `--max-calls 6` first, then the following
resume command. This only divides collection; do not change the design based on
those first answers:

```bash
caffeinate -i python3 -m exception_query_role run --config configs/query_role.json --output runs/query-role-001 --max-calls 144 --resume
```

After a timeout or other transport error, the failed attempt is preserved and
resumption requires the explicit retry flag:

```bash
caffeinate -i python3 -m exception_query_role run --config configs/query_role.json --output runs/query-role-001 --max-calls 144 --resume --retry-errors
```

`--max-calls` limits attempts in that invocation, not the planned sample size.
Resume skips returned answers, including unscorable ones, and stops when the
fixed manifest is exhausted. Reissuing a completed run makes zero new calls.
Per-task/global retry caps remain in force across invocations. A process killed
during a request can leave an uncertain `started` attempt: any explicit retry
still consumes the attempt budget; the lost response cannot be recovered.

Read or regenerate the report offline:

```bash
python3 -m exception_query_role analyze --output runs/query-role-001
open runs/query-role-001/report.md
```

Keep the complete run directory, including `attempts/`, `plan.json`,
`plan.sha256`, `preview.json`, `preview.md`, and `execution.json`. The report and
summary alone are not sufficient for an audit. Do not edit prepared artifacts
or mix mock and live data in one directory.

## Offline verification

```bash
python3 -m unittest discover -s tests -p 'test_query_role*.py' -v
python3 -m exception_query_role run --config configs/query_role.json --output runs/query-role-software-check --max-calls 144 --mock
```

Mock collection never reads a key or invokes the provider. Its all-correct
fixture checks software behavior and produces no predicted effect. It is not
model evidence and cannot be resumed as a live run.
