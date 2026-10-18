#!/usr/bin/env python3
"""Render saved aggregate results only. No model imports, inference or new statistics."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter


def read_bound(root, relative):
    raw = (root / relative).read_bytes()
    return json.loads(raw), {'path': relative, 'sha256': hashlib.sha256(raw).hexdigest()}


def build_data(root):
    gpt, gpt_source = read_bound(root, 'results/reports/counterfactual-001/summary.json')
    qwen, qwen_source = read_bound(root, 'results/reports/study2-source-user-main-v1/report.json')
    assert gpt['complete'] and gpt['paired_lists'] == 20
    assert qwen['live_main_results_obtained'] and qwen['counts']['returned'] == 332
    cells = {(row['condition'], row['background']): row for row in gpt['accuracy_tables']}
    gpt_counts = {arm: [cells[(arm, bg)]['n_correct'] for bg in ['support', 'conflict']]
                  for arm in ['direct', 'cot']}
    assert all(row['n_valid'] == row['n_planned'] == 40 for row in cells.values())
    assert gpt_counts == {'direct': [40, 40], 'cot': [40, 16]}
    pairs = [qwen['paired'][key] for key in ['0->512', '256->512']]
    cohort = set(pairs[0]['returned_task_ids'])
    assert len(cohort) == 108 and cohort == set(pairs[1]['returned_task_ids'])
    assert all(p['eligible_pairs'] == p['returned_pairs'] == 108 for p in pairs)
    before = [p['transitions']['correct->correct'] + p['transitions']['correct->incorrect']
              for p in pairs]
    after = [p['transitions']['correct->correct'] + p['transitions']['incorrect->correct']
             for p in pairs]
    assert after[0] == after[1]
    qwen_counts = before + [after[0]]
    assert qwen_counts == [107, 96, 80]
    return {
        'kind': 'documentation_figure_from_preserved_aggregate_results',
        'archive_revision': '7c7a72c354d384654e5bc3b58d2c440c87dfce27',
        'sources': [gpt_source, qwen_source],
        'matplotlib_version': matplotlib.__version__,
        'gpt': {'model': gpt['model'], 'correct': gpt_counts,
                'denominator_per_bar': 40, 'worlds': 20,
                'extra_conflict_penalty': gpt['effects']['extra_conflict_penalty']},
        'qwen': {'model': 'Qwen/Qwen3-32B', 'saved_tokens': [0, 256, 512],
                 'correct': qwen_counts, 'matched_denominator': 108,
                 'worlds': pairs[0]['paired_accuracy_change_bootstrap']['observed_worlds'],
                 'source_queries_in_full_collection': 332,
                 'paired_0_to_512': pairs[0]['paired_accuracy_change_bootstrap'],
                 'cohort_note': 'Same 108 trajectories at all points; four pre-existing k512 exclusions retained.'},
        'limits': ['Separate experimental populations and interfaces; do not pool or rank models.',
                   'Counts reconstructed from saved aggregate transition tables; no new statistical analysis.',
                   'No pointwise confidence intervals plotted. Saved paired intervals are retained above.',
                   'Qwen source questions use a new user turn with the original table still in context.',
                   'Neither panel establishes internal erasure or a causal role for a specific reasoning statement.']}


def render(root, output):
    data = build_data(root)
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'axes.labelcolor': '#243746', 'text.color': '#243746',
                         'xtick.color': '#405361', 'ytick.color': '#405361',
                         'svg.fonttype': 'path', 'svg.hashsalt': 'exception-pilot-overview-v1'})
    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.9))
    fig.patch.set_facecolor('white')
    fig.subplots_adjust(left=0.075, right=0.975, bottom=0.32, top=0.73, wspace=0.28)
    fig.text(0.075, 0.94, 'Reasoning and use of an explicit record', fontsize=20, weight='bold')
    fig.text(0.075, 0.885, 'Two completed experiments • separate populations and answer interfaces', fontsize=12, color='#526772')
    for ax in axes:
        ax.set_ylim(0, 115)
        ax.set_yticks([0, 25, 50, 75, 100])
        ax.yaxis.set_major_formatter(PercentFormatter(100, decimals=0))
        ax.set_axisbelow(True)
        ax.grid(axis='y', color='#E3E9EC', linewidth=0.8)
        for edge in ['top', 'right', 'left']:
            ax.spines[edge].set_visible(False)
        ax.spines['bottom'].set_color('#BAC7CC')
        ax.tick_params(axis='both', length=0, pad=8)
    a, b = axes
    a.set_title('A   GPT-4o · classification', loc='left', fontsize=13, weight='bold', pad=16)
    width = 0.3
    for name, label, color, offset in [('direct', 'Direct answer', '#277E8B', -width/2),
                                        ('cot', 'Visible reasoning', '#BF632F', width/2)]:
        values = data['gpt']['correct'][name]
        positions = [x + offset for x in [0, 1]]
        a.bar(positions, [100*n/40 for n in values], width, color=color, label=label)
        for x, n in zip(positions, values):
            a.text(x, 100*n/40+3, f'{n}/40', ha='center', fontsize=11, weight='bold')
    a.set_xticks([0, 1], ['Supporting\nbackground', 'Conflicting\nbackground'])
    a.set_xlim(-0.58, 1.58)
    a.set_ylabel('Final-answer accuracy')
    a.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22), ncols=2, frameon=False, fontsize=10)
    b.set_title('B   Qwen3-32B · source transcription', loc='left', fontsize=13, weight='bold', pad=16)
    counts = data['qwen']['correct']
    b.plot([0, 1, 2], [100*n/108 for n in counts], color='#5265A1', linewidth=2.8, marker='o', markersize=8)
    for x, n in enumerate(counts):
        b.text(x, 100*n/108+5, f'{n}/108', ha='center', fontsize=11, weight='bold')
    b.set_xticks([0, 1, 2], ['0', '256', '512'])
    b.set_xlim(-0.35, 2.35)
    b.set_xlabel('Saved reasoning tokens', labelpad=12)
    b.set_ylabel('Source-transcription accuracy')
    fig.text(0.075, 0.11, 'A: 20 worlds; 40 responses per bar.   B: 108 matched trajectories across 56 worlds.', fontsize=10, color='#526772')
    fig.text(0.075, 0.065, 'Descriptive counts. Paired-effect intervals and limitations are in the README and linked reports.', fontsize=10, color='#526772')
    for extension in ['png', 'svg']:
        metadata = {'Date': None} if extension == 'svg' else {'Software': 'Matplotlib; preserved aggregate data'}
        fig.savefig(output / f'evidence-summary.{extension}', dpi=180, facecolor='white', metadata=metadata)
    # Normalize Matplotlib's line-ending spaces without changing SVG geometry.
    svg = output / 'evidence-summary.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)
    (output / 'figure-data.json').write_text(json.dumps(data, indent=2) + '\n')
    print('Rendered two panels from verified saved aggregates; no inference or statistical resampling.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    render(args.repo, args.output)
