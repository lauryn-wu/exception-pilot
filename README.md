# Reasoning prompts and exception records

When an item's label is explicitly recorded, can asking a language model to explain its answer make it follow the surrounding pattern instead?

**Main finding: a large reasoning penalty appeared under the original classification wording, but depended strongly on how the task was asked.** Direct answers preserved the target records. Reasoning prompts produced errors when surrounding labels conflicted with those records. Explicitly asking for the recorded class removed the penalty under neutral reasoning in the fresh wording experiment.

This repository documents an exploratory sequence of controlled behavioral studies. It includes the positive result, the boundary that limited the claim, and diagnostics that stopped or remained technically incomplete. The main archived experiments below used `gpt-4o-2024-08-06` on synthetic vehicle records.

## Why this comparison?

A model answering from supplied records should distinguish retrieving an item's stated label from inferring a label from other items. The experiment keeps the queried item's record fixed while changing surrounding labels. This separates sensitivity to the supplied background from a change in the target fact itself.

The work builds on [Mind Your Step (ICML 2025)](https://proceedings.mlr.press/v267/liu25t.html), which already establishes that chain-of-thought prompting can reduce performance on some tasks. The question here is narrower: how does dependence on surrounding records change with the response instruction and the wording of the question?

## What was learned

### 1. Surrounding labels changed reasoned answers to a fixed target

The first diagnostic used 20 independent lists and 160 requests. Each list had two backgrounds: one whose majority pattern supported the target labels, and one whose pattern conflicted with them. Target records, attributes, order, class balance, and the overall exception rate stayed fixed.

| Response instruction | Supporting background | Conflicting background |
| --- | ---: | ---: |
| Direct answer | 40/40 correct | 40/40 correct |
| Visible reasoning before the answer | 40/40 correct | 16/40 correct |

The extra conflict penalty under reasoning was **60 percentage points**, with a descriptive 95% whole-list bootstrap interval of [47.5, 72.5] points. Eighteen lists had a positive interaction and two had zero. The independent unit is the list, not each request. See the [saved report](results/summary-counterfactual-001.md) and [protocol](COUNTERFACTUAL_PROTOCOL.md).

### 2. Fresh cases exposed a task-wording boundary

A 480-call follow-up used 20 fresh lists. It compared the original question with a version explicitly asking for the recorded class, and included a neutral "Think step by step" instruction.

| Question / instruction | Supporting background | Conflicting background |
| --- | ---: | ---: |
| Original question, direct | 40/40 | 40/40 |
| Original question, neutral reasoning | 39/40 | 18/40 |
| Recorded-class question, direct | 40/40 | 40/40 |
| Recorded-class question, neutral reasoning | 40/40 | 40/40 |

The extra conflict penalty was **52.5 points** under the original question and **0 points** under explicit recorded-class wording. The frozen decision was `stop_explicit_record_boundary`: the broader wording-robust claim did not pass. This boundary is part of the result, not an omitted unsuccessful replication.

The recorded-class variant also removed an uncertainty sentence, so this comparison alone does not isolate the effect of the question text. A later factorial study separated the changes but retained one invalid response; its incomplete measurement status is documented in the [results index](results/README.md). See the [wording report](results/summary-wording-001.md) for all six cells, paired contrasts, and limits.

### 3. Relevant copying helped, but continuation diagnostics did not establish a mechanism

In a separate 24-world experiment, final answers on 48 visible-record cases were correct in **25/48** cases after neutral reasoning, **48/48** after copying the target class, and **29/48** after copying a marker from the same row. Copying the class and copying the marker both succeeded in all 48 cases. Thus merely producing a correct same-row copy was not sufficient for correct final answers.

These prompt comparisons do not identify the model's internal process. A selected-case continuation diagnostic subsequently stopped because only 7/10 unchanged replays matched their original answers, below its fixed 8/10 feasibility criterion. Its proposed intervention was not evaluated. Both the [explanation archive](results/explanation-001.zip) and [stopped replay archive](results/missingness-001.zip) are retained.

## Interpretation

The supported result is a prompt-dependent tendency to answer from the background pattern despite an available target record. It is not evidence that reasoning generally harms retrieval or that a model knowingly rejects a fact. Explicit task semantics materially changed the outcome.

Other limits matter:

- These experiments use one model snapshot and closely related synthetic tasks. Multiple follow-ups on the same family do not establish broad generalization.
- Changing background labels also changes local consensus strength and can change incidental correlations with other attributes. It is not a selective intervention on an internal representation.
- Visible explanations are outputs, not direct measurements of internal beliefs or a faithful causal trace.
- Follow-ups were designed after inspecting earlier results. Fresh cases, fixed plans, parser amendments, invalid outputs, and unsuccessful stopping decisions are recorded separately.

The committed results justify the narrow behavioral comparison and its wording boundary. They do not establish a general mechanism. Later diagnostic packages and historical run instructions remain available in the [study guide](STUDY_GUIDE.md); their presence alone does not establish a completed or successful experiment.

## Inspect or reanalyze the archived results

Start with the [results index](results/README.md). The two main reports are available as Markdown and JSON without downloading a ZIP; the archives contain the full requests and responses.

Python 3.10+ and the standard library are sufficient. From the repository root, these commands reanalyze a working copy of the wording run without model API calls:

```bash
python3 -m zipfile -e results/wording-001.zip runs/reproduce-wording
python3 -m exception_wording analyze \
  --output runs/reproduce-wording/runs/wording-001
```

Use a fresh extraction directory to preserve existing local results. The original archive is unchanged. Protocols and optional live-run commands are linked in the [historical study guide](STUDY_GUIDE.md).
