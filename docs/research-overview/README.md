# Figure sources and reproduction

The figure uses aggregate results from two archived reports. The panels have different tasks, populations and answer interfaces, so they should be read separately.

| Panel | Data source | Displayed population |
|---|---|---|
| A — GPT-4o classification | [Counterfactual summary](../../results/reports/counterfactual-001/summary.json), `accuracy_tables` | 20 worlds, 40 responses per condition. Direct: 40/40 under support and conflict; visible reasoning: 40/40 under support and 16/40 under conflict. |
| B — Qwen source transcription | [Source-user main report](../../results/reports/study2-source-user-main-v1/report.json), `paired` | The same 108 trajectories eligible at 0, 256 and 512 saved tokens, across 56 worlds. Correct counts: 107, 96, 80. Four original k512 exclusions remain excluded from this panel. |

For Qwen, the renderer checks that the `0->512` and `256->512` transition tables contain the same trajectory IDs, then reconstructs the counts for that cohort. This is why the first two plotted counts differ from the full-sample counts of 111/112 and 100/112. All 332 queries remain in the original report.

The axes start at zero, and labels give correct/eligible counts. The README reports the saved world-cluster bootstrap intervals for paired changes; the figure does not show pointwise intervals. In the Qwen study, the original table remains available when the new user turn asks for its contents. The plotted decline does not isolate the effect of a particular reasoning statement.

- [PNG](evidence-summary.png): displayed in the repository README.
- [SVG](evidence-summary.svg): vector export for reuse.
- [Data and provenance](figure-data.json): counts, saved paired intervals, source SHA256 hashes, archival revision and rendering version.
- [Rendering script](render_figure.py): reads only saved JSON summaries and writes the two figures and provenance file.

To redraw the figure from the repository root, use a separate plotting environment:

```bash
python3 -m venv /tmp/exception-overview-figure
/tmp/exception-overview-figure/bin/python -m pip install matplotlib==3.10.7
MPLCONFIGDIR=/tmp/exception-overview-mpl \
  /tmp/exception-overview-figure/bin/python docs/research-overview/render_figure.py
```

This installs plotting dependencies and renders the saved counts; it runs no experiments. Font and rendering versions can affect image bytes. The data file records the plotted counts, source hashes and Matplotlib version.
