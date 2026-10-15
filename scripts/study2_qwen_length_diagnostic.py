#!/usr/bin/env python3
"""Independent four-case length diagnostic. No inference without --live-qwen."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_continuation.core import final_score
from exception_continuation.qwen3 import manifest as qwen_manifest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v4 import PROTOCOL as V4_PROTOCOL
from exception_study2_v4.core import read_plan, source_hash as v4_source_hash
from exception_study2_v4.journal import operations as source_operations
from exception_study2_v4.validation import require_technical

PROTOCOL = 'qwen3-pilot-generation-length-diagnostic-v1'
BUDGET = 2048
ORIGINAL_BUDGET = 512
INTERPRETATION = (
    'Four fresh uninterrupted generations from the original prompt only; '
    'not v4 collection, calibration, an intervention, or continuation from saved prefixes. '
    'Prefix divergence does not invalidate this fresh-generation diagnostic, but prevents '
    'describing it as an exact continuation of the original trajectory. '
    'No automatic false-missingness classification; review the complete text manually.'
)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def code_identity():
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    return dict(git_revision=revision, script_sha256=sha(__file__), v4_source_hash=v4_source_hash())


def valid_ids(ids):
    return isinstance(ids, list) and bool(ids) and all(type(t) is int and 0 <= t < 151936 for t in ids)


def check_raw(raw, budget, eos_ids):
    if (not isinstance(raw, dict) or not valid_ids(raw.get('tokens'))
            or len(raw['tokens']) > budget or not isinstance(raw.get('text'), str)
            or type(raw.get('stopped')) is not bool or raw.get('finish') not in ('eos', 'length')):
        raise ValueError('Malformed generation metadata/tokens')
    stopped = raw['tokens'][-1] in eos_ids
    if (any(t in eos_ids for t in raw['tokens'][:-1]) or raw['stopped'] != stopped
            or raw['finish'] != ('eos' if stopped else 'length')
            or not stopped and len(raw['tokens']) != budget):
        raise ValueError('Inconsistent EOS/finish/budget metadata')


def inspect_pilot(source):
    """Read the partial source only; never instantiate the complete-collection Source."""
    root = Path(source).resolve()
    plan = read_plan(root)
    if plan['protocol'] != V4_PROTOCOL or plan['phase'] != 'selection' or len(plan['tasks']) != 48:
        raise ValueError('Expected a frozen v4 selection plan')
    execution = sealed_read(root / 'execution-v4.json')
    identity = execution['backend']
    if (execution.get('protocol') != V4_PROTOCOL or execution.get('mode') != 'LIVE_LOCAL'
            or execution['plan_hash'] != plan['plan_hash'] or execution['source_hash'] != plan['source_hash']
            or execution['backend_hash'] != digest(identity) or identity.get('config') != plan['config']):
        raise ValueError('Source must be a matching real-model v4 execution')
    expected_files = {name: data['sha256'] for name, data in qwen_manifest()['files'].items()}
    generation = identity.get('generation', {})
    if (identity.get('kind') != 'LOCAL_HF_TOKEN_IDS' or identity.get('files') != expected_files
            or identity.get('dtype') != 'torch.bfloat16' or not identity.get('chat_template')
            or generation.get('do_sample') is not False or generation.get('num_beams') != 1
            or generation.get('use_cache') is not True
            or generation.get('eos_token_id') != [151645, 151643]
            or identity.get('generation_overrides') != dict(do_sample=False, num_beams=1, use_model_defaults=False)):
        raise ValueError('Pinned Qwen/tokenizer/generation identity differs')
    technical = require_technical(root, plan, execution)
    if technical['measurement'] != 'LIVE' or technical['real_model_status'] != 'V4_SAME_INPUT_PASSED':
        raise ValueError('Passed real-model v4 technical validation is required')
    status = sealed_read(root / 'technical-status-v4.json')
    if (status.get('protocol') != V4_PROTOCOL or status.get('plan_hash') != plan['plan_hash']
            or status.get('technical_hash') != technical['artifact_hash']
            or status.get('technical_same_input_passed') is not True
            or status.get('measurement') != 'LIVE' or status.get('real_model_status') != 'V4_SAME_INPUT_PASSED'):
        raise ValueError('Source technical status/report mismatch')

    pilot = plan['tasks'][:8]
    selected = [t for t in pilot if t['arm'] == 'visible']
    if len(selected) != 4 or sum(t['arm'] == 'direct' for t in pilot) != 4:
        raise ValueError('First eight frozen originals must contain four visible and four direct tasks')
    saved = source_operations(root)
    originals = []
    for task in pilot:
        op = saved.get('v4/original/' + task['id'])
        if not op or op['status'] != 'returned':
            raise ValueError('Missing or unavailable pilot original: ' + task['id'])
        if any(op.get(k) != v for k, v in dict(protocol=V4_PROTOCOL, plan_hash=plan['plan_hash'],
                source_hash=plan['source_hash'], backend_hash=execution['backend_hash'], stage='original_generation').items()):
            raise ValueError('Pilot original identity differs: ' + task['id'])
        ids = op['request'].get('input_ids')
        expected = dict(input_ids=ids, context_hash=digest(ids), budget=512, capture_at=[], fresh_prefill=True)
        if not valid_ids(ids) or op['request'] != expected:
            raise ValueError('Pilot original request differs: ' + task['id'])
        raw = op['result']
        check_raw(raw, ORIGINAL_BUDGET, set(generation['eos_token_id']))
        if task['arm'] == 'visible' and (len(raw['tokens']) != 512 or raw['stopped'] or raw['finish'] != 'length'):
            raise ValueError('Every selected visible original must be truncated at exactly 512 tokens')
        originals.append(dict(task=task, original_operation_hash=op['artifact_hash'],
            original_request_hash=op['request_hash'], prompt_hash=digest(task['prompt']),
            prompt_ids=ids, prompt_ids_hash=digest(ids), original_raw=raw))

    # Fingerprint evidence used by this diagnostic, including every technical journal state.
    names = ['plan-v4.json', 'execution-v4.json', 'technical-v4.json', 'technical-status-v4.json']
    ids = [k for k in saved if k.startswith('v4/technical/')]
    ids += ['v4/original/' + task['id'] for task in pilot]
    for op_id in ids:
        directory = root / 'operations-v4' / digest(op_id)
        names.extend(str(p.relative_to(root)) for p in sorted(directory.glob('*.json')))
    files = {name: sha(root / name) for name in sorted(names)}
    binding = dict(source_path=str(root), protocol=V4_PROTOCOL, plan_hash=plan['plan_hash'],
        scientific_source_hash=plan['source_hash'], backend_hash=execution['backend_hash'],
        technical_hash=technical['artifact_hash'], files=files,
        first_eight_original_hashes={r['task']['id']: r['original_operation_hash'] for r in originals})
    return dict(plan=plan, execution=execution, binding=binding, source_hash=digest(binding),
        pilot=originals, cases=[r for r in originals if r['task']['arm'] == 'visible'])


def unchanged_source(source):
    root = Path(source['binding']['source_path'])
    if any(not (root / name).is_file() or sha(root / name) != h for name, h in source['binding']['files'].items()):
        raise ValueError('Source evidence changed during the diagnostic; stop and preserve both runs')


def prefix_comparison(original, generated):
    reference = original[:ORIGINAL_BUDGET]
    prefix = generated[:ORIGINAL_BUDGET]
    mismatch = next((i for i, (a, b) in enumerate(zip(reference, prefix)) if a != b), None)
    if mismatch is None and len(prefix) < len(reference):
        mismatch = len(prefix)
    return dict(first_512_tokens_exact_match=mismatch is None and len(prefix) == ORIGINAL_BUDGET,
        first_differing_token_index_zero_based=mismatch,
        first_differing_token_position_one_based=None if mismatch is None else mismatch + 1,
        original_token_at_difference=None if mismatch is None else reference[mismatch],
        new_token_at_difference=None if mismatch is None or mismatch >= len(prefix) else prefix[mismatch],
        divergence_kind=None if mismatch is None else 'NEW_SEQUENCE_ENDED' if mismatch >= len(prefix) else 'TOKEN_MISMATCH')


def case_result(case, raw, eos_ids):
    check_raw(raw, BUDGET, eos_ids)
    score = final_score(raw['text'], raw['stopped'], case['task']['expected'])
    return dict(raw=raw, token_count=len(raw['tokens']), eos=raw['stopped'], finish=raw['finish'],
        truncated=raw['finish'] == 'length', final_answer=score['answer'], correctness=score['correct'],
        score=score, outcome='correct' if score['correct'] is True else 'wrong' if score['correct'] is False else 'invalid',
        answer_marker_present='ANSWER:' in raw['text'],
        **prefix_comparison(case['original_raw']['tokens'], raw['tokens']))


def diagnostic_plan(source):
    return dict(protocol=PROTOCOL, code=code_identity(), source=source['binding'], source_hash=source['source_hash'],
        model_identity=source['execution']['backend'], backend_hash=source['execution']['backend_hash'],
        original_budget=512, generation_parameters=dict(budget=BUDGET, capture_at=[],
            prompt_only=True, fresh_uninterrupted_generation=True,
            generation=source['execution']['backend']['generation'],
            generation_overrides=source['execution']['backend']['generation_overrides'],
            frozen_model_config=source['plan']['config']),
        planned_generations=4, maximum_generated_tokens=8192,
        cases=source['cases'], interpretation=INTERPRETATION)


def request_for(plan, case):
    return dict(protocol=PROTOCOL, diagnostic_plan_hash=plan['artifact_hash'],
        source_hash=plan['source_hash'], backend_hash=plan['backend_hash'], task_id=case['task']['id'],
        original_operation_hash=case['original_operation_hash'], prompt_hash=case['prompt_hash'],
        input_ids=case['prompt_ids'], context_hash=case['prompt_ids_hash'], budget=BUDGET,
        capture_at=[], fresh_uninterrupted_generation=True)


def entries(output, plan):
    expected = {digest(c['task']['id']): request_for(plan, c) for c in plan['cases']}
    root = Path(output) / 'operations'
    if root.exists() and any(not p.is_dir() or p.name not in expected for p in root.iterdir()):
        raise ValueError('Unexpected diagnostic operation')
    saved = {}
    for key, request in expected.items():
        path = root / key
        states = {}
        for name in ('request', 'started', 'failed', 'returned'):
            file = path / (name + '.json')
            if file.exists():
                entry = sealed_read(file)
                if entry.get('request') != request or entry.get('request_hash') != digest(request) or entry.get('status') != name:
                    raise ValueError('Diagnostic operation identity changed')
                states[name] = entry
        if states and 'request' not in states or any(n in states for n in ('failed', 'returned')) and 'started' not in states:
            raise ValueError('Incomplete diagnostic journal state chain')
        if 'failed' in states and 'returned' in states:
            raise ValueError('Contradictory diagnostic terminal states')
        if states:
            saved[request['task_id']] = next(states[n] for n in ('returned', 'failed', 'started', 'request') if n in states)
    return saved


def separate_output(source, output):
    src, out = Path(source).resolve(), Path(output).resolve()
    if src == out or src in out.parents or out in src.parents:
        raise ValueError('Diagnostic output must be separate from and outside the source directory')
    if out.exists():
        if not out.is_dir():
            raise ValueError('Output must be a directory')
        if any(out.iterdir()) and not (out / 'diagnostic-plan.json').is_file():
            raise ValueError('Use an empty diagnostic directory; never overwrite an existing experiment')
        if any((out / name).exists() for name in ('plan-v4.json', 'plan.json', 'validation.json', 'collection-v4.json')):
            raise ValueError('Existing experiment output is not a diagnostic directory')
        if any(p.is_symlink() for p in out.rglob('*')):
            raise ValueError('Symlinks are not allowed inside diagnostic outputs')
    return out


def write_report(out, plan, status, error=None):
    saved = entries(out, plan)
    rows, traces = [], [PROTOCOL, INTERPRETATION, 'Status: ' + status, 'Source: ' + plan['source']['source_path']]
    if error:
        traces.append('Error: ' + error)
    eos_ids = set(plan['model_identity']['generation']['eos_token_id'])
    for case in plan['cases']:
        tid = case['task']['id']; entry = saved.get(tid)
        row = dict(task_id=tid, expected_class=case['task']['expected'], misleading_pattern_class=case['task']['pattern'],
            prompt_hash=case['prompt_hash'], prompt_ids_hash=case['prompt_ids_hash'],
            original_operation_hash=case['original_operation_hash'], original_request_hash=case['original_request_hash'],
            status='UNATTEMPTED' if not entry or entry['status'] == 'request' else entry['status'].upper())
        if entry:
            row['operation_hash'] = entry['artifact_hash']
            row['measurement'] = entry.get('measurement')
        if entry and entry['status'] == 'returned':
            row['elapsed_seconds'] = entry['elapsed_seconds']
            row['raw'] = entry['raw']
            try:
                row.update(case_result(case, entry['raw'], eos_ids))
                if entry.get('validation_error'):
                    raise ValueError(entry['validation_error'])
            except (ValueError, KeyError, TypeError) as exc:
                row.update(status='UNUSABLE_RETURN', validation_error=str(exc), correctness=None, final_answer=None,
                    score=dict(answer=None, valid=False, correct=None), outcome='unusable_return')
        elif entry and entry['status'] == 'failed':
            row['error_type'] = entry['error_type']
        rows.append(row)
        traces.extend(['', '=' * 72, json.dumps({k: v for k, v in row.items() if k != 'raw'}, indent=2)])
        if row.get('first_512_tokens_exact_match') is False:
            traces.append('DIVERGED WITHIN THE ORIGINAL 512 TOKENS: fresh-generation diagnostic, NOT an exact continuation.')
        raw = row.get('raw')
        text = raw.get('text') if isinstance(raw, dict) else None
        traces.extend(['--- COMPLETE NEW RESPONSE ---', text if isinstance(text, str) else '[No usable response text; see operation journal]', '--- END RESPONSE ---'])
    returned = [r for r in rows if r['status'] == 'RETURNED']
    if any(r['status']=='UNUSABLE_RETURN' for r in rows) and status in ('COMPLETE', 'COMPLETE_FROM_CACHE'):
        status = 'COMPLETE_WITH_UNUSABLE_RETURNS'
    result = dict(protocol=PROTOCOL, diagnostic_plan_hash=plan['artifact_hash'], source_hash=plan['source_hash'],
        code=plan['code'], backend_hash=plan['backend_hash'], status=status, error=error,
        interpretation=INTERPRETATION, false_missingness_classification='NOT_PERFORMED_MANUAL_REVIEW_REQUIRED',
        summary=dict(planned=4, returned=sum(r['status'] in ('RETURNED', 'UNUSABLE_RETURN') for r in rows),
            usable_returned=len(returned), valid=sum(r['score']['valid'] for r in returned),
            correct=sum(r['correctness'] is True for r in returned), wrong=sum(r['correctness'] is False for r in returned),
            correctness_unknown=4-sum(r['score']['valid'] for r in returned),
            eos=sum(r['eos'] for r in returned), truncated=sum(r['truncated'] for r in returned),
            prefix_matches=sum(r['first_512_tokens_exact_match'] for r in returned),
            prefix_divergences=sum(not r['first_512_tokens_exact_match'] for r in returned)), cases=rows)
    write_json(out / 'diagnostic-results.json', result)
    temporary = out / 'diagnostic-traces.txt.tmp'
    temporary.write_text('\n'.join(traces) + '\n')
    temporary.replace(out / 'diagnostic-traces.txt')
    return result


def run(source, output, live_qwen=False, *, backend_factory=None):
    """backend_factory is an in-process test seam; the CLI has no mock/live bypass."""
    out = separate_output(source, output)
    print('Checking frozen v4 pilot and real-model technical evidence...', flush=True)
    src = inspect_pilot(source)
    with run_lock(out):
        plan = freeze(out / 'diagnostic-plan.json', diagnostic_plan(src))
        for case in plan['cases']:
            request = request_for(plan, case)
            freeze(out / 'operations' / digest(case['task']['id']) / 'request.json',
                dict(request=request, request_hash=digest(request), status='request'))
        saved = entries(out, plan)
        blocked = [k for k, v in saved.items() if v['status'] in ('started', 'failed')]
        if blocked:
            write_report(out, plan, 'BLOCKED_NO_RESEND', 'Terminal/ambiguous operations: ' + ', '.join(blocked))
            if live_qwen:
                raise ValueError('Diagnostic has failed/ambiguous operations; no automatic resend')
            return write_report(out, plan, 'BLOCKED_NO_RESEND', 'No automatic resend')
        if all(v['status'] == 'returned' for v in saved.values()):
            return write_report(out, plan, 'COMPLETE_FROM_CACHE')
        if not live_qwen:
            return write_report(out, plan, 'PREPARED_NO_INFERENCE')
        state, error = 'FAILED', None
        try:
            print('Loading the unchanged pinned backend; no model download...', flush=True)
            if backend_factory is None:
                from exception_continuation.backend import LocalBackend
                backend_factory = LocalBackend
            backend = backend_factory(copy.deepcopy(src['plan']['config']))
            if digest(backend.identity) != plan['backend_hash']:
                raise ValueError('Loaded backend identity differs from the original v4 run')
            # Verify all eight frozen requests before any diagnostic generation.
            for original in src['pilot']:
                if (backend.prompt(original['task']['prompt']) != original['prompt_ids']
                        or backend.decode(original['original_raw']['tokens']) != original['original_raw']['text']):
                    raise ValueError('Rendered prompt IDs or original text/token identity differs')
            unchanged_source(src)
            measurement = 'MOCK' if backend.simulated else 'LIVE'
            for i, case in enumerate(plan['cases'], 1):
                tid = case['task']['id']
                if saved[tid]['status'] == 'returned':
                    print(f'{i}/4 {tid}: cached; no new generation', flush=True)
                    continue
                unchanged_source(src)
                request = request_for(plan, case); path = out / 'operations' / digest(tid)
                common = dict(request=request, request_hash=digest(request), measurement=measurement)
                print(f'{i}/4 {tid}: fresh prompt-only generation, budget=2048', flush=True)
                freeze(path / 'started.json', dict(common, status='started', started_utc=utc()))
                start = time.monotonic()
                try:
                    sync(backend)
                    start = time.monotonic()
                    raw = backend.generate(list(case['prompt_ids']), budget=BUDGET, capture_at=())
                    sync(backend)
                except BaseException as exc:
                    freeze(path / 'failed.json', dict(common, status='failed', error_type=type(exc).__name__,
                        finished_utc=utc(), elapsed_seconds=time.monotonic()-start))
                    raise
                validation_error = None
                try:
                    check_raw(raw, BUDGET, set(plan['model_identity']['generation']['eos_token_id']))
                    if backend.decode(raw['tokens']) != raw['text']:
                        raise ValueError('Generated text/token identity differs')
                except (ValueError, KeyError, TypeError) as exc:
                    validation_error = str(exc)
                freeze(path / 'returned.json', dict(common, status='returned', raw=raw,
                    validation_error=validation_error, finished_utc=utc(), elapsed_seconds=time.monotonic()-start))
                write_report(out, plan, 'IN_PROGRESS')
                unchanged_source(src)
                if validation_error:
                    raise ValueError('Unusable return preserved; no resend: ' + validation_error)
            state = 'COMPLETE'
        except BaseException as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            raise
        finally:
            result = write_report(out, plan, state, error)
        return result


def sync(backend):
    torch = getattr(backend, 'torch', None)
    if torch is not None and str(backend.model.device).startswith('cuda'):
        torch.cuda.synchronize(backend.model.device)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, help='Existing incomplete v4 selection run')
    parser.add_argument('--output', required=True, help='Separate diagnostic directory; reuse to resume')
    parser.add_argument('--live-qwen', action='store_true', help='Explicitly authorize at most four new local generations')
    args = parser.parse_args(argv)
    result = run(args.source, args.output, args.live_qwen)
    print(json.dumps({k: result[k] for k in ('status', 'summary', 'interpretation')}, indent=2))


if __name__ == '__main__':
    main()
