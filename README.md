# Reasoning prompts and exception records

## Next experiment: query form × response

The revised [query-form protocol](QUERY_FORM_PROTOCOL.md) is implemented and
prepared for GPT-4o and Mistral; **no new live collection has been performed**.
It crosses profile/key queries with direct, visible-reasoning, and same-response
neutral-copy conditions: 24 fresh worlds and 288 calls per model. The shared
plan is identical across providers. See the exact [GPT-4o previews](previews/query-form-gpt4o/preview.md)
and [Mistral previews](previews/query-form-mistral/preview.md).

The corrected sensitivity scale is [−1,1]. Both live models must satisfy the
predeclared spending rule before analysis can issue `proceed_to_dose`. Mock runs
are labeled SIMULATED and cannot pass that rule. Run 2 remains deferred pending
redesign of its peer fractions, counterfactual pairing and description pools.

The [offline rationale audit](analysis/rationales/README.md) covers 240 archived
responses, with CSV evidence excerpts and 20 blinded samples per run. Its codes
are provisional descriptions of text, not measures of hidden reasoning.

The separate [query-role-001 report](results/query-role-001-report.md) records
144/144 correct answers across literal, encoded and downstream queries, including
both direct and visible responses (24/24 per cell). That Mistral screen returned
`stop_this_screen`: the predicted deterioration was absent in those 12 worlds.

Run commands are in the new protocol. Run from the repository root; the existing
package manifest and historical studies remain unchanged.

These experiments ask GPT-4o to answer questions about synthetic vehicle records.
Under the original classification wording, asking for reasoning made the model
more likely to follow the surrounding labels even when they conflicted with the
target's recorded class. That result depended on the question: explicitly asking
for the recorded class removed the penalty under neutral reasoning in a follow-up.

The studies below used `gpt-4o-2024-08-06`. They build on
[Mind Your Step (ICML 2025)](https://proceedings.mlr.press/v267/liu25t.html), which
showed that chain-of-thought prompting can reduce performance on some tasks.
Here, the question is how the response instruction and question wording affect
the model's use of surrounding records. Keeping the target record fixed makes
it possible to change the background without changing the answer.

## Changing the surrounding labels

The first diagnostic used 20 independent lists and 160 requests. Each list had two backgrounds: one whose majority pattern supported the target labels, and one whose pattern conflicted with them. Target records, attributes, order, class balance, and the overall exception rate stayed fixed.

| Response instruction | Supporting background | Conflicting background |
| --- | ---: | ---: |
| Direct answer | 40/40 correct | 40/40 correct |
| Visible reasoning before the answer | 40/40 correct | 16/40 correct |

Reasoning added a 60-percentage-point penalty from the conflicting background
(descriptive 95% bootstrap interval: [47.5, 72.5] points). Eighteen lists had a
positive interaction and two had zero. The bootstrap resamples whole lists.
See the [report](results/summary-counterfactual-001.md) and
[protocol](COUNTERFACTUAL_PROTOCOL.md).

## Changing the question

A 480-call follow-up used 20 fresh lists. It compared the original question with a version explicitly asking for the recorded class, and included a neutral "Think step by step" instruction.

| Question / instruction | Supporting background | Conflicting background |
| --- | ---: | ---: |
| Original question, direct | 40/40 | 40/40 |
| Original question, neutral reasoning | 39/40 | 18/40 |
| Recorded-class question, direct | 40/40 | 40/40 |
| Recorded-class question, neutral reasoning | 40/40 | 40/40 |

The extra conflict penalty was 52.5 points under the original question and 0
under the recorded-class wording. The result failed the planned robustness
check, producing the decision `stop_explicit_record_boundary`.

The recorded-class variant also removed an uncertainty sentence, so this
comparison does not isolate the question text. A later factorial study
separated these changes but retained one invalid response; its status is in the
[results index](results/README.md). The
[wording report](results/summary-wording-001.md) includes all six conditions and
paired comparisons.

## Copying the class or a marker

In a separate 24-world experiment, final answers on 48 visible-record cases were
correct in 25/48 cases after neutral reasoning, 48/48 after copying the target
class, and 29/48 after copying a marker from the same row. Both copying tasks
succeeded in all 48 cases, but copying the marker often led to a wrong final
answer.

A subsequent diagnostic attempted to continue responses on selected cases. Only
7/10 unchanged replays matched their original answers, below the required 8/10,
so collection stopped before the intervention. The
[copying experiment](results/explanation-001.zip) and
[stopped replay run](results/missingness-001.zip) are both archived.

## Interpretation

The model sometimes answered from the background pattern despite having the
target record, but explicit wording changed that behavior. The result is limited
to one model snapshot and closely related synthetic tasks. The wording follow-up
used fresh cases, but the studies were designed in sequence after inspecting
earlier results.

Changing background labels also changes local consensus and can introduce
correlations with other attributes. These comparisons, and the explanations the
model produced, do not establish an internal mechanism or show that reasoning
generally harms retrieval. Parser changes, invalid responses, and stopped runs
are documented in the [results index](results/README.md). The
[study guide](STUDY_GUIDE.md) retains the longer development history and
instructions for later diagnostics, including work without a complete archive
in this repository.

## Inspect or reanalyze the archived results

Start with the [results index](results/README.md). The two main reports are available as Markdown and JSON without downloading a ZIP; the archives contain the full requests and responses.

Python 3.10+ and the standard library are sufficient. From the repository root, these commands reanalyze a working copy of the wording run without model API calls:

```bash
python3 -m zipfile -e results/wording-001.zip runs/reproduce-wording
python3 -m exception_wording analyze \
  --output runs/reproduce-wording/runs/wording-001
```

Use a fresh extraction directory. Protocols and live-run commands are in the
[study guide](STUDY_GUIDE.md).
