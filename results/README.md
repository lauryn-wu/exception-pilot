# Experiment archives

The ZIP files contain the original run exports. The two main reports are also
available below as Markdown and JSON, with the same contents as their archived
versions.

| Study | Completion | Result |
| --- | --- | --- |
| [Fixed-target background comparison](counterfactual-001.zip) | 160/160 valid requests; 20 independent lists | Reasoning conflict accuracy 16/40 versus 40/40 direct; extra conflict penalty 60 points |
| [Fresh wording comparison](wording-001.zip) | 480/480 valid requests; 20 fresh lists | Neutral-reasoning extra penalty 52.5 points under the original question, 0 under the recorded-class variant; broader robustness check stopped |
| [Question × uncertainty factorial](factorial-001-recovered.zip) | 640 returned, 639 valid; 19 complete lists; original technical-failure status retained | Separates question text and uncertainty wording; one invalid response leaves a list incomplete |
| [Copying and record sensitivity](explanation-001.zip) | 384/384 valid final answers; 24 worlds | Class copying yielded 48/48 correct visible-record answers; same-row marker copying yielded 29/48 |
| [Selected-case continuation diagnostic](missingness-001.zip) | 10 original replays collected; 7/10 matched; stopped before intervention | Replay feasibility failed; no available-versus-unavailable intervention effect was measured |

The [original factorial export](factorial-001.zip) contains the earlier interrupted state: 596 attempts, 595 valid responses, and one invalid response. It and the later export are snapshots of the same run, not independent experiments. The later export preserves the invalid answer instead of replacing it.

## Reports

- Fixed-target background comparison: [report](summary-counterfactual-001.md), [JSON](summary-counterfactual-001.json), [protocol](../COUNTERFACTUAL_PROTOCOL.md)
- Fresh wording comparison: [report](summary-wording-001.md), [JSON](summary-wording-001.json), [protocol](../WORDING_PROTOCOL.md)

Both analyses were reproduced from the raw archives when preparing this summary,
without new model calls. The reports preserve the original wording and decisions.
Intervals are descriptive and use independent lists or worlds as the sample unit.

The [study guide](../STUDY_GUIDE.md) contains the longer development history,
including later diagnostics whose full archives are not in this repository.
The main [README](../README.md) summarizes the experiments listed here.

## Qwen3.8 native-thinking screen (2026-10-22)

[Results and audit](current-qwen-screen-v1/README.md): 384/384 correct final answers
across native thinking off/on, original/lookup wording, and support/conflict.
The folder includes the unchanged evidence ZIP and run log, machine-readable
analysis, and SHA-256 checksums. No model calls were made while archiving.
