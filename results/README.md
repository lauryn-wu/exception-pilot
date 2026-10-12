# Archived results and study status

The archives below were already committed before the current results summary. They are retained unchanged. Markdown and JSON copies of the two main reports are provided for convenient inspection; those copies match the contents of their archives.

| Study | Evidence and status | Main implication |
| --- | --- | --- |
| [Fixed-target background comparison](counterfactual-001.zip) | 160/160 valid requests; 20 independent lists | Reasoning conflict accuracy 16/40 versus 40/40 direct; extra conflict penalty 60 points |
| [Fresh wording comparison](wording-001.zip) | 480/480 valid requests; 20 fresh lists | Neutral-reasoning extra penalty 52.5 points under the original question, 0 under the recorded-class variant; broader robustness check stopped |
| [Question × uncertainty factorial](factorial-001-recovered.zip) | 640 returned, 639 valid; 19 complete lists; original technical-failure status retained | Separates question text and uncertainty wording; the incomplete measurement must accompany any numerical interpretation |
| [Copying and record sensitivity](explanation-001.zip) | 384/384 valid final answers; 24 worlds | Class copying yielded 48/48 correct visible-record answers; same-row marker copying yielded 29/48 |
| [Selected-case continuation diagnostic](missingness-001.zip) | 10 original replays collected; 7/10 matched; stopped before intervention | Replay feasibility failed; no available-versus-unavailable intervention effect was measured |

The [original factorial export](factorial-001.zip) contains the earlier interrupted state: 596 attempts, 595 valid responses, and one invalid response. It and the later export are snapshots of the same run, not independent experiments. The later export preserves the invalid answer instead of replacing it.

## Main reports without extracting an archive

- Fixed-target background comparison: [report](summary-counterfactual-001.md), [JSON](summary-counterfactual-001.json), [protocol](../COUNTERFACTUAL_PROTOCOL.md)
- Fresh wording comparison: [report](summary-wording-001.md), [JSON](summary-wording-001.json), [protocol](../WORDING_PROTOCOL.md)

The two analyses were reproduced from the committed raw archives when preparing this summary, with no new model calls. The copied reports retain their original wording and decisions. All intervals are descriptive; the number of independent lists or worlds, not the number of API calls, is the relevant sample size.

## Scope of this index

This index covers the raw result archives available in this repository. Additional packages, protocols, and earlier reported results appear in the [historical study guide](../STUDY_GUIDE.md). An implemented protocol is not itself evidence that its experiment completed. The root [README](../README.md) bases its numerical comparisons on the archives listed here and preserves the failed checks alongside the positive findings.
