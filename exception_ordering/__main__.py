import argparse
import json
from .runner import prepare, run, position_report
from .analysis import analyze


def main():
    p = argparse.ArgumentParser(description='Background-order study; no implicit live calls')
    p.add_argument('command', choices=['prepare', 'audit-inputs', 'run', 'analyze'])
    p.add_argument('--output', required=True)
    p.add_argument('--tokenizer-json'); p.add_argument('--tokenizer-model')
    p.add_argument('--mock', action='store_true'); p.add_argument('--live', action='store_true')
    p.add_argument('--accept-tokenizer-provenance', action='store_true')
    p.add_argument('--max-calls', type=int, default=0)
    a = p.parse_args()
    if a.command in ('prepare', 'audit-inputs'):
        if a.command == 'audit-inputs' and (a.live or a.mock or a.max_calls):
            p.error('audit-inputs is input-only; no generation flags are allowed')
        r = prepare(a.output, a.tokenizer_json, a.tokenizer_model)
        audit = position_report(r)
        print(json.dumps({'planned': r['planned_responses'], 'plan_hash': r['plan_hash'], 'tokenizer': r['tokenizer'],
                          'audit_status': audit['status'], 'coverage': audit['coverage'],
                          'coverage_assessment': audit['coverage_assessment']}))
    elif a.command == 'run':
        print(json.dumps(run(a.output, live=a.live, mock=a.mock, max_calls=a.max_calls,
                             accept_provenance=a.accept_tokenizer_provenance)))
    else:
        r = analyze(a.output); print(json.dumps({'mode': r['mode'], 'summary': a.output + '/summary.json'}))


if __name__ == '__main__':
    main()
