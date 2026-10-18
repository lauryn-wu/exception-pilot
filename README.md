# Reasoning and recorded evidence

Asking for reasoning sometimes makes a language model less likely to follow an explicit record. These experiments examine when that happens, using synthetic vehicle tables in which the target's recorded class can disagree with the pattern in the surrounding rows. The correct answer is known. Background labels can be changed while keeping the target record fixed.

[Results and raw data](results/README.md) · [Experiment status](results/BRANCH_STATUS.md) · [Independent analyses](results/analyses/2026-10-18/README.md)

## Findings so far

![GPT-4o: direct answers remain 40/40 correct under supporting and conflicting backgrounds; visible-reasoning answers fall from 40/40 to 16/40. Qwen: correct source reports on the same 108 trajectories fall from 107 to 96 to 80 after 0, 256 and 512 saved reasoning tokens.](docs/research-overview/evidence-summary.png)

The panels show separate experiments with different tasks and answer interfaces. Counts and paired-effect intervals are discussed below. [Figure sources and reproduction](docs/research-overview/README.md) · [Vector figure](docs/research-overview/evidence-summary.svg).

### Background labels and question wording

In the first GPT-4o diagnostic, direct answers were correct on 40/40 cases under both supporting and conflicting backgrounds. Answers preceded by visible reasoning were 40/40 correct under support and 16/40 under conflict, despite unchanged target records. The experiment used 20 independent worlds and 160 responses. The extra conflict penalty under reasoning was 60 percentage points, with a descriptive world-bootstrap 95% interval of 47.5–72.5 points. [Report](results/reports/counterfactual-001/summary.md).

The wording follow-up put a limit on that finding. Across 20 new worlds and 480 responses, neutral reasoning produced a 52.5-point extra conflict penalty under the original question. When explicitly asked for the recorded class, the observed penalty was zero. That version also removed an uncertainty clause, so the comparison did not isolate one wording change. The study failed its broader robustness criterion. [Report](results/reports/wording-001/summary.md).

### Query form in Mistral

Mistral was asked about the same vehicle in two ways: by its features, or by its license plate. When asked for just the answer, it got all 48 questions right in each version. When asked to write out its reasoning first, it got 20/48 right for the feature descriptions and 33/48 for the license plates.

The full experiment collected 288 responses across 24 worlds. It also included a control that asked Mistral to copy a neutral paragraph before answering, which the model did not consistently follow. The planned decision rule classified the run as inconclusive. [Report](results/reports/query-form-mistral-001/summary.md).

### Asking Qwen to report the source

The Qwen3-32B study asked for the target table cell in a new user turn after 0, 256 or 512 tokens of saved visible reasoning. The original table stayed in context. All 332 planned source queries returned valid, completed answers.

Among the same 108 trajectories eligible at every checkpoint, correct responses fell from 107 to 96 to 80. The paired 0-to-512 change was −25 percentage points (descriptive world-bootstrap 95% interval: −33.3 to −16.8). All 27 newly incorrect responses said `MISSING`, although the cells contained a class. Four other trajectories were ineligible at 512 tokens and remain excluded under the original rules. [Execution report](results/reports/study2-source-user-main-v1/report.md) · [Independent audit](results/analyses/2026-10-18/Study2_Source_User_Main_Audit.md).

For 21 of those 27 histories, a separate test gave the correct letter the highest score among A, B and C after an `ANSWER:` cue. That cue was added to the assistant's text; the `MISSING` responses came from a new user question asking for the source cell. This difference is why the missingness reports alone cannot show that the model had forgotten the record. These runs used greedy decoding with native thinking disabled and an instruction to write visible reasoning.

## Limits of the evidence

These studies do not establish internal forgetting, deliberate override, or a general disadvantage of reasoning. In the Qwen experiment, longer histories change the text, the distance from the source and where the assistant turn ends. Some prompts also explicitly discuss missing values. Further controls are needed to separate those influences. Semantic annotations of the generated text remain exploratory.

The studies developed sequentially after earlier results were inspected. Repeated queries and trajectories from one world are not independent samples. Technical failures are retained: the Qwen v3 replay check failed, the v4 pilot is incomplete at 8/48 originals, and two source-report interfaces failed calibration before the new-user-turn interface was tested. The [results index](results/README.md) also records invalid responses, truncation and overlapping exports.

## Next experiments

Native thinking has not yet been tested in the archived runs. The planned Qwen comparison uses new controlled worlds and the same sampling settings for thinking on and off. The draft allocates 64 responses to a development pilot and 896 to the main collection. The main token budget will be fixed after reviewing pilot truncation and repetition. Offline shortcut checks are complete; design review and live validation are still pending. Historical greedy responses will remain separate. [Draft protocol](results/branch-artifacts/2026-10-18/context/STUDY2_NATIVE_THINKING_DRAFT_PROTOCOL.md).

A second question is whether changing a specific false claim in the reasoning changes the final answer. This needs independently reviewed passages, an unedited comparator and controls for any answer information introduced by an edit. The intervention proposals are unexecuted, and the whole-history crossing proposal is on hold. [Plans](results/plans/README.md).

Additional support would pay for GPU time and independent annotation for this work. Populations, prompts, scoring and stopping rules would be fixed before the relevant runs, with null and failed outcomes retained alongside positive findings.

## Data and reproduction

The [results index](results/README.md) links reports, raw exports and provenance. [Branch status](results/BRANCH_STATUS.md) identifies failed, partial and unstarted work. Experimental code remains on its source branches.

After cloning the repository, check the saved files with:

```bash
python3 results/verify_results.py
```

[Verification instructions](results/VERIFY.md) explain how to reconstruct split archives. The [historical study guide](STUDY_GUIDE.md) preserves earlier protocols and commands, including live commands that may incur charges.

*The archive check requires Python 3.10 or later. Last archive review: 18 October 2026.*

Related paper: [*Mind Your Step (by Step)*, Liu et al., ICML 2025](https://proceedings.mlr.press/v267/liu25t.html).
