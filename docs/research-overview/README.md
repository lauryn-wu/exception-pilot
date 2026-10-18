# Overview figure: sources and reproduction

This figure displays preserved aggregate results. It adds no model responses, exclusions, statistical tests or bootstrap draws. The experiments use different prompts, populations and answer interfaces; the panels are not a comparison of model performance on a common benchmark.

| Panel | Data source | Displayed population |
|---|---|---|
| A — GPT-4o classification | [Counterfactual summary](../../results/reports/counterfactual-001/summary.json), `accuracy_tables` | 20 worlds, 40 responses per condition. Direct: 40/40 under support and conflict; visible reasoning: 40/40 under support and 16/40 under conflict. |
| B — Qwen source transcription | [Source-user main report](../../results/reports/study2-source-user-main-v1/report.json), `paired` | The same 108 trajectories eligible at 0, 256 and 512 saved tokens, across 56 worlds. Correct counts: 107, 96, 80. Four original k512 exclusions remain excluded from this panel. |

The Qwen counts are reconstructed from the existing `0->512` and `256->512` transition tables after verifying identical trajectory IDs. They differ from the full k0/k256 counts of 111/112 and 100/112 because this panel uses one matched cohort throughout. All 332 queries remain in the original report.

The axes start at zero. Labels give correct/eligible counts. No pointwise uncertainty is drawn: the README cites the saved world-cluster bootstrap intervals for the relevant paired contrasts. Repeated responses from a world are not treated as independent observations. The Qwen source question is a fresh user turn with the original table still supplied; the line does not establish a causal effect of a particular reasoning statement.

- [PNG](evidence-summary.png): displayed in the repository README.
- [SVG](evidence-summary.svg): vector export for reuse.
- [Data and provenance](figure-data.json): counts, saved paired intervals, source SHA256 hashes, archival revision and rendering version.
- [Rendering script](render_figure.py): reads only saved JSON summaries and writes the two figures and provenance file.

To reproduce in an optional, separate plotting environment, from the repository root:

```bash
python3 -m venv /tmp/exception-overview-figure
/tmp/exception-overview-figure/bin/python -m pip install matplotlib==3.10.7
MPLCONFIGDIR=/tmp/exception-overview-mpl \
  /tmp/exception-overview-figure/bin/python docs/research-overview/render_figure.py
```

The installation downloads plotting dependencies only. The renderer makes no network calls, imports no experimental backend, and uses no model weights or credentials. It does not change the experiment environment. Exact image bytes can depend on font/rendering dependencies; plotted counts and source hashes are recorded explicitly.
