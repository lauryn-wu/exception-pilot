# Reasoning and evidence use in language models

**When does generated reasoning help a language model use an explicit record, and when does it lead the model away from that record?**

This project studies that question with synthetic tables in which a target's recorded class can conflict with a pattern suggested by other rows. The recorded answer is known, and paired table changes separate the target evidence from the surrounding pattern. The aim is to identify conditions under which models follow supplied exceptions, misreport the source, or favor an inferred alternative.

The motivation is reliability when a supplied fact should take precedence over a plausible generalization. These synthetic tasks do not establish real-world performance. The project builds on [*Mind Your Step (by Step)* (Liu et al., ICML 2025)](https://proceedings.mlr.press/v267/liu25t.html), which investigated tasks on which chain-of-thought prompting can reduce performance.

**Current status:** preliminary behavioral evidence from completed GPT-4o, Mistral and Qwen experiments. Effects depend on the prompt and answer interface. Their internal mechanism and generalization to native thinking remain open.

[Results and raw data](results/README.md) · [Experiment status](results/BRANCH_STATUS.md) · [Independent analyses](results/analyses/2026-10-18/README.md) · [Verification](results/VERIFY.md)

## Preliminary findings

![Two separate experiments: GPT-4o visible-reasoning accuracy falls from 40/40 to 16/40 when surrounding labels conflict with the record, while direct answers remain 40/40. Qwen source-transcription accuracy on 108 matched trajectories is 107/108, 96/108 and 80/108 after 0, 256 and 512 saved reasoning tokens.](docs/research-overview/evidence-summary.png)

*These panels summarize different tasks and interfaces, not a pooled model comparison. Counts are shown directly; uncertainty for the paired contrasts is reported below. [Figure data, provenance and reproduction](docs/research-overview/README.md) · [Vector figure](docs/research-overview/evidence-summary.svg).*

### 1. Surrounding patterns can change the effect of asking for reasoning

In a GPT-4o diagnostic with **20 independent worlds and 160 responses**, direct answers were correct on **40/40** cases under both supporting and conflicting backgrounds. Visible-reasoning answers were **40/40** correct under support and **16/40** under conflict. The target records were unchanged. The extra conflict penalty under reasoning was **60 percentage points**, with a descriptive world-bootstrap 95% interval of **47.5–72.5 points**. [Report](results/reports/counterfactual-001/summary.md).

**A fresh-data wording follow-up failed the broader robustness criterion.** Across 20 new worlds and 480 responses, neutral reasoning produced a 52.5-point extra conflict penalty under the original question, but zero observed penalty when explicitly asked for the recorded class. That wording also removed an uncertainty clause, so it did not isolate a single phrasing change. The supported finding is conditional on the tested instructions. [Report](results/reports/wording-001/summary.md).

### 2. Other models show related failures, with important boundaries

A **288-response Mistral query-form experiment across 24 worlds** found direct-answer accuracy of **48/48** for both a descriptive-profile query and a lookup-key query. Visible-reasoning accuracy was **20/48** and **33/48**, respectively. However, filler-control compliance was incomplete, and the prespecified decision was **inconclusive**. This supports further investigation of interface dependence, not a confirmed account of why the errors occur. [Report](results/reports/query-form-mistral-001/summary.md).

### 3. Longer saved reasoning histories can impair explicit source reporting

In the completed **Qwen3-32B source-transcription study**, a new user turn asked for the target table cell after 0, 256 or 512 tokens of the model's saved visible reasoning. The original table remained in context. All **332 planned source queries** returned valid, completed answers.

On the **same 108 trajectories** eligible at all three checkpoints, correct responses fell from **107 → 96 → 80**. The paired 0-to-512 change was **−25 percentage points** (descriptive world-bootstrap 95% interval: **−33.3 to −16.8**). All 27 newly incorrect responses said `MISSING`, although the cells contained a class. Four other trajectories were ineligible at 512 tokens and remain excluded under the original rules. [Execution report](results/reports/study2-source-user-main-v1/report.md) · [Independent audit](results/analyses/2026-10-18/Study2_Source_User_Main_Audit.md).

This is an interface-specific behavioral result. Among those 27 false `MISSING` reports, 21 still favored the correct class under an existing restricted A/B/C `ANSWER:` readout. That readout and the new transcription question are different measurements. Neither establishes whether the fact was continuously retained internally. These Qwen runs used greedy decoding with native thinking disabled; visible reasoning was requested in the response.

## What remains unresolved

The experiments do **not** establish internal forgetting, deliberate evidence override, or a general disadvantage of reasoning. Longer prefixes also change content, source-to-query distance and where the assistant turn ends. Correct mentions, contradictory statements and final answers are distinct observations; exploratory semantic annotations are not ground truth about hidden state.

The studies developed sequentially after inspecting earlier results. Worlds, trajectories and repeated queries are not interchangeable independent samples. Some prompts include explicit instructions about missing values, so false `MISSING` reports cannot be generalized beyond that interface without further controls. Failures, invalid responses, truncation, duplicate exports and incomplete collections remain visible in the [full index](results/README.md).

Technical validation is also separate from scientific success. The earlier Qwen v3 replay check failed, the v4 pilot remains incomplete at **8/48 originals**, and two source-report interfaces failed calibration before the successful new-user-turn interface was tested. Those failed runs have not been relabeled as successful replications.

## What additional support would enable

The next phase would fund bounded GPU experiments, independent annotation and reproducible analysis:

- **Test native thinking under matched conditions.** The current Qwen draft compares thinking on/off on new controlled worlds with the same sampling settings. Its 64-response development pilot precedes 896 main responses; the main token budget remains unfrozen until truncation and repetition are reviewed. Offline shortcut checks are complete, but design review and live validation remain pending. Historical greedy responses are not controls for this comparison. [Draft and limitations](results/branch-artifacts/2026-10-18/context/STUDY2_NATIVE_THINKING_DRAFT_PROTOCOL.md).
- **Test the contribution of specific textual claims.** Independently review candidate evidence-erasure and explicit-override statements before freezing any intervention protocol. Future edited-continuation studies need an unedited comparator and controls for added answer information. Existing intervention proposals remain unexecuted; the whole-history crossing proposal is on hold. [Plans and status](results/plans/README.md).
- **Strengthen independent evaluation.** Fund reviewed annotations and prospective analyses with frozen populations, prompts, scoring and stopping rules. Deliver auditable datasets that retain null and failed outcomes.

These are proposed next steps, not completed findings or a commitment to a particular outcome. No new inference is required to inspect the existing evidence.

## Inspect the evidence

The [results index](results/README.md) links reports, raw exports and provenance; [branch status](results/BRANCH_STATUS.md) identifies failed, partial and unstarted work. Experimental code remains on its source branches. This overview reflects artifacts inspected through **18 October 2026**; unexported remote activity is not covered.

Verify the preserved archives offline with Python 3.10+:

```bash
python3 results/verify_results.py
```

For optional reconstruction of split archives, see [verification instructions](results/VERIFY.md). The [historical study guide](STUDY_GUIDE.md) preserves earlier protocols and run instructions; its live commands may incur charges and are not a recommended execution queue.
