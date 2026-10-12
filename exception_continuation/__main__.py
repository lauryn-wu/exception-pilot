import argparse
import json
from pathlib import Path
from .core import DEFAULT_CONFIG
from .runner import prepare, collect, measure, validate_run
from .edits import review_export, freeze_edits, intervene
from .analysis import analyze


def main():
    p = argparse.ArgumentParser(description='Within-response continuation; no automatic model calls')
    p.add_argument('command', choices=['prepare', 'validate', 'collect', 'measure', 'review-export', 'freeze-edits', 'intervene', 'analyze'])
    p.add_argument('--output', required=True)
    p.add_argument('--phase', choices=['selection', 'confirmation'], default='selection')
    p.add_argument('--config'); p.add_argument('--selection-output'); p.add_argument('--selection-note')
    p.add_argument('--review-file')
    p.add_argument('--live', action='store_true'); p.add_argument('--mock', action='store_true')
    a = p.parse_args()
    if a.command == 'prepare':
        config = json.loads(Path(a.config).read_text()) if a.config else DEFAULT_CONFIG
        r = prepare(a.output, a.phase, config, a.selection_output, a.selection_note)
        print(json.dumps({'phase': r['phase'], 'planned_trajectories': len(r['tasks']), 'plan_hash': r['plan_hash']}))
    elif a.command == 'validate':
        r = validate_run(a.output, live=a.live, mock=a.mock)
        print(json.dumps({'passed': r['passed'], 'mode': r['mode'], 'real_model_status': 'PENDING' if a.mock else ('TECHNICAL_PASSED' if r['passed'] else 'FAILED')}))
    elif a.command in ('collect', 'measure', 'intervene'):
        r = {'collect': collect, 'measure': measure, 'intervene': intervene}[a.command](a.output, live=a.live, mock=a.mock)
        print(json.dumps({'stage': a.command, 'rows': len(r['rows']), 'artifact_hash': r['artifact_hash']}))
    elif a.command == 'review-export':
        print(review_export(a.output, a.review_file))
    elif a.command == 'freeze-edits':
        if not a.review_file: p.error('--review-file is required')
        r = freeze_edits(a.output, a.review_file)
        print(json.dumps({'cases': len(r['cases']), 'excluded': len(r['excluded']), 'artifact_hash': r['artifact_hash']}))
    else:
        r = analyze(a.output); print(json.dumps({'phase': r['phase'], 'mode': r['mode'], 'summary': a.output + '/summary.json'}))


if __name__ == '__main__': main()
