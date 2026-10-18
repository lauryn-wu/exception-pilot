# Sample sizes, paired estimates and figure sources

The overview describes four experiments. The figure plots results from the first and fourth; their tasks, populations and answer interfaces differ.

## Studies in the overview

| Experiment | Independent worlds | Responses | Report |
|---|---:|---:|---|
| GPT-4o background labels | 20 | 160 | [Counterfactual diagnostic](../../results/reports/counterfactual-001/summary.md) |
| GPT-4o question wording | 20 new worlds | 480 | [Wording follow-up](../../results/reports/wording-001/summary.md) |
| Mistral query form | 24 | 288 | [Query-form study](../../results/reports/query-form-mistral-001/summary.md) |
| Qwen source transcription | 56 | 332 source queries from 112 saved response histories | [Execution report](../../results/reports/study2-source-user-main-v1/report.md) |

The Mistral count includes 96 requests to copy a neutral paragraph before answering. Exact copying succeeded in 36/48 feature-description requests and 24/48 license-plate requests. Both fell below the required 95% adherence within each query form, triggering the saved `output_manipulation_inconclusive` decision.

## Paired estimates

| Comparison | Estimate | Descriptive 95% world-bootstrap interval |
|---|---:|---:|
| GPT-4o: extra conflict penalty with reasoning, first diagnostic | 60 percentage points | 47.5 to 72.5 points |
| GPT-4o: extra conflict penalty with neutral reasoning, original wording in the follow-up | 52.5 percentage points | 40 to 65 points |
| Qwen: change in correct source reports from 0 to 512 saved tokens, same 108 histories | −25 percentage points | −33.3 to −16.8 points |

For GPT-4o, the extra conflict penalty is the support-minus-conflict accuracy difference with reasoning, minus that difference for direct answers. The wording follow-up observed a zero penalty under the explicit recorded-class question with neutral reasoning. This does not establish equivalence: that wording also removed an uncertainty clause, and the study failed its planned robustness criterion.

The estimates were copied from the saved reports. Resampling whole worlds keeps related responses together. The studies were developed sequentially after earlier results were inspected; the intervals are descriptive.

## Figure data

| Panel | Data source | Displayed population |
|---|---|---|
| A — GPT-4o classification | [Counterfactual summary](../../results/reports/counterfactual-001/summary.json), `accuracy_tables` | 20 worlds, 40 responses per condition. Direct: 40/40 under support and conflict; visible reasoning: 40/40 under support and 16/40 under conflict. |
| B — Qwen source transcription | [Source-user main report](../../results/reports/study2-source-user-main-v1/report.json), `paired` | The same 108 trajectories eligible at 0, 256 and 512 saved tokens, across 56 worlds. Correct counts: 107, 96, 80. Four original k512 exclusions remain excluded from this panel. |

For Qwen, the renderer checks that the `0->512` and `256->512` transition tables contain the same trajectory IDs, then reconstructs the counts for that cohort. This is why the first two plotted counts differ from the full-sample counts of 111/112 and 100/112. All 332 queries remain in the original report.

The axes start at zero, and labels give correct/eligible counts. The table above gives the saved world-cluster bootstrap intervals for paired changes; the figure does not show pointwise intervals. In the Qwen study, the original table remains available when the new user turn asks for its contents. The plotted decline does not isolate the effect of a particular reasoning statement.

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
