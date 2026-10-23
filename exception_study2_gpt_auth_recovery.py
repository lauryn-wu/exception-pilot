"""One audited retry of a proven invalid-key rejection; offline unless --live-openai.

This additive module does not change the original plan or its code contract. Every
retry is a new, bound attempt, and returned answers are never resampled.
"""
import argparse
import json
import os
import time
import uuid
import zipfile
from pathlib import Path
from types import SimpleNamespace

from exception_pilot.core import digest
from exception_pilot.storage import run_lock, write_json
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze, sha
from exception_review.providers import HTTPTransport, redact
from exception_study2_native.recovery import scan, state
from exception_study2_v5.journal import Session, OperationUnavailable
from exception_study2_source_report.integrity import separate
from exception_study2_gpt_explanation import execution as legacy
from exception_study2_gpt_explanation import analysis as original_analysis
from exception_study2_gpt_explanation.planning import Context
from exception_study2_gpt_explanation.parsing import account, body_of, infrastructure_error
from exception_study2_gpt_explanation.export import TOP, DIRS, review_sheet
from exception_study2_gpt_explanation.source import sha_bytes

VERSION = 'study2-gpt-auth-recovery-v1'
FOLDER = 'auth-recovery-v1'
STAGE = 'gpt_authentication_retry'
ORIGINAL_CONTRACT = '59ce83e4ffea153e1ad737d83a4c6fd97ff06d93117f39295e5dff8f07e4887f'
POLICY = 'Exactly one attempt-2 for a sealed terminal HTTP 401 invalid_api_key rejection with no generation evidence. Identical scientific request. No other retries.'


def contract():
    return sha(Path(__file__))


def retry_id(request):
    return 'v5/' + VERSION + '/' + request['request_hash'] + '/attempt-2'


def _proof(c, request, operation):
    """Eligibility uses saved transport evidence, never an answer or error string."""
    if state(operation) != 'failed' or operation.get('error_type') != 'InfrastructureFailure':
        return None
    oid = legacy.opid(request)
    sidecar = c.out/'responses'/(digest(oid)+'.json')
    if not sidecar.is_file():
        return None
    response = sealed_read(sidecar)
    raw = response['raw']
    if type(raw.get('response', {}).get('status')) is not int or raw['response']['status'] != 401:
        return None
    body = body_of(raw)
    if not isinstance(body, dict) or not isinstance(body.get('error'), dict) or body['error'].get('code') != 'invalid_api_key':
        return None
    # Even contradictory evidence of a generated response makes this ineligible.
    if any(body.get(k) not in (None, '', []) for k in ('id', 'output', 'output_text', 'choices')) or body.get('usage') is not None:
        return None
    if body.get('status') in ('completed', 'incomplete', 'queued', 'in_progress'):
        return None
    return dict(cell_id=request['cell']['id'], request_hash=request['request_hash'],
                request=request['request'], original_operation_id=oid,
                original_operation_hash=operation['artifact_hash'],
                original_failed_file_sha256=sha(c.out/'operations-v5'/digest(oid)/'failed.json'),
                original_response_sha256=sha(sidecar), original_response_hash=response['artifact_hash'],
                original_dispatch_sha256=sha(c.out/'dispatches'/(digest(oid)+'.json')),
                retry_operation_id=retry_id(request))


def _amendment_fields(c, mode, proofs):
    return dict(protocol=VERSION, original_plan_hash=c.plan['artifact_hash'],
                original_code_contract=c.plan['code_contract'], recovery_code_contract=contract(),
                source_binding_hash=digest(c.plan['source']), measurement_mode=mode,
                policy=POLICY, requests=proofs)


def _identity(amendment):
    return dict(protocol=VERSION, plan_hash=amendment['original_plan_hash'],
                original_code_contract=amendment['original_code_contract'],
                recovery_code_contract=amendment['recovery_code_contract'],
                amendment_hash=amendment['artifact_hash'],
                source_binding_hash=amendment['source_binding_hash'],
                measurement_mode=amendment['measurement_mode'])


def _retry_journal(c, amendment):
    root = c.out/FOLDER
    identity = _identity(amendment)
    entries = amendment['requests']
    known = {digest(p['retry_operation_id']): dict(id=p['retry_operation_id'], identity=dict(
        identity, id=p['retry_operation_id'], request=p['request'], request_hash=p['request_hash'], stage=STAGE)) for p in entries}
    recovery_context = SimpleNamespace(out=root)
    saved = scan(recovery_context, known, identity)
    for dirname in ('dispatches', 'responses'):
        for path in (root/dirname).glob('*'):
            if path.is_symlink() or not path.is_file() or path.suffix != '.json' or path.stem not in known:
                raise ValueError('Unknown authentication retry ' + dirname + ' artifact')
    current = {}
    for p in entries:
        oid = p['retry_operation_id']; operation = saved.get(oid)
        current[p['cell_id']] = operation
        if operation and (any(operation.get(k) != v for k, v in identity.items()) or operation.get('request') != p['request']):
            raise ValueError('Authentication retry identity differs')
        dispatch = root/'dispatches'/(digest(oid)+'.json')
        response = root/'responses'/(digest(oid)+'.json')
        if state(operation) == 'returned' and not dispatch.exists():
            raise ValueError('Missing authentication retry dispatch')
        if dispatch.exists():
            record = sealed_read(dispatch)
            started = sealed_read(root/'invocations'/record['invocation']/'started.json')
            if record.get('request_hash') != p['request_hash'] or any(started.get(k) != v for k, v in identity.items()):
                raise ValueError('Authentication retry invocation differs')
        if response.exists():
            receipt = sealed_read(response)
            if not dispatch.exists() or receipt.get('operation_id') != oid or receipt.get('request_hash') != p['request_hash']:
                raise ValueError('Orphan authentication retry response')
            if state(operation) == 'never_started':
                raise ValueError('Authentication retry response without held dispatch')
            if state(operation) == 'returned' and receipt['raw'] != operation['result']:
                raise ValueError('Authentication retry response differs from journal')
        elif state(operation) == 'returned':
            raise ValueError('Missing authentication retry response')
    return current


def _load(output):
    c = Context(output)
    if c.plan['code_contract'] != ORIGINAL_CONTRACT:
        raise ValueError('Authentication recovery supports only the frozen original GPT contract')
    original, mode = legacy.journal(c)
    proofs = [proof for r in c.requests if (proof := _proof(c, r, original[r['cell']['id']])) is not None]
    root = c.out/FOLDER; path = root/'amendment.json'
    amendment = None; retries = {}
    if root.exists():
        if root.is_symlink() or not root.is_dir():
            raise ValueError('Regular authentication recovery directory required')
        if not path.exists():
            raise ValueError('Authentication recovery directory without sealed amendment; preserve for review')
        if path.is_symlink():
            raise ValueError('Authentication amendment symlink forbidden')
        amendment = sealed_read(path)
        eligible = {p['cell_id']: p for p in proofs}
        bound = amendment.get('requests', [])
        if not bound or len({p['cell_id'] for p in bound}) != len(bound):
            raise ValueError('Empty or duplicate authentication recovery authorization')
        if any(eligible.get(p['cell_id']) != p for p in bound):
            raise ValueError('Original authentication rejection evidence changed')
        expected = _amendment_fields(c, mode, bound)
        if amendment != dict(expected, artifact_hash=digest(expected)):
            raise ValueError('Authentication recovery amendment/code binding differs')
        retries = _retry_journal(c, amendment)
    return c, original, mode, proofs, amendment, retries


def _combined(c, original, mode, proofs, amendment, retries, invocation=None):
    selected = dict(original)
    if amendment:
        selected.update(retries)
    value = original_analysis.report(c, selected, invocation or dict(new_dispatches=0))
    for row in value['cases']:
        cell_id = row['cell']['id']
        original_operation = original[cell_id]
        row['original_operation_hash'] = original_operation.get('artifact_hash') if original_operation else None
        row['selected_attempt'] = 'authentication_retry' if cell_id in retries else 'original'
        if cell_id in retries and state(retries[cell_id]) != 'returned':
            # The old analysis otherwise falls back to the original 401 receipt.
            request = next(r for r in c.requests if r['cell']['id'] == cell_id)
            path = c.out/FOLDER/'responses'/(digest(retry_id(request))+'.json')
            row['raw'] = sealed_read(path)['raw'] if path.exists() else None
            row['usage_accounting'] = account(row['raw'], c.plan['pricing']) if row['raw'] else None
    original_dispatches = len(list((c.out/'dispatches').glob('*.json')))
    retry_dispatches = len(list((c.out/FOLDER/'dispatches').glob('*.json')))
    dispatches = original_dispatches + retry_dispatches
    value['totals']['scientific_dispatches'] = dispatches
    # Costs cover both actual attempts, including receipts that are not selected.
    accounting = [account(sealed_read(p)['raw'], c.plan['pricing'])
                  for base in (c.out, c.out/FOLDER) for p in (base/'responses').glob('*.json')]
    priced = [a for a in accounting if a['estimated_usd'] is not None]
    resources = value['resource_summary']
    for key in ('input_tokens', 'output_tokens', 'reasoning_tokens', 'cached_input_tokens', 'cache_write_input_tokens'):
        numbers = [a[key] for a in accounting if type(a.get(key)) is int and a[key] >= 0]
        resources[key] = dict(observed_sum=sum(numbers), responses_reporting=len(numbers))
    resources.update(priced_responses=len(priced), dispatches_without_complete_cost=dispatches-len(priced),
                     observed_estimated_usd=sum(a['estimated_usd'] for a in priced),
                     total_estimated_usd=sum(a['estimated_usd'] for a in priced) if len(priced) == dispatches else None)
    value['authentication_recovery'] = dict(protocol=VERSION, recovery_code_contract=contract(),
        amendment_hash=amendment['artifact_hash'] if amendment else None,
        eligible_rejections=len(proofs), authorized_retries=len(retries), retry_dispatches=retry_dispatches,
        original_dispatches=original_dispatches,
        original_failures=[dict(cell_id=k, operation_hash=op.get('artifact_hash'), status=state(op))
                           for k, op in original.items() if state(op) in ('failed', 'ambiguous')],
        retry_states={k: state(op) for k, op in retries.items()}, policy=POLICY,
        selection='Original returns are retained. For authorized rejections, only attempt-2 is selected; its failure or ambiguity remains unavailable. No outcome-based selection.',
        reporting='Original journals are unchanged. Original-module reports retain the original failed attempt. This combined report includes all actual dispatches and all observed usage.')
    value['recovery']['action'] = ('Original journal debris remains subject to the original quarantine rules. '
        'Only the separately sealed authentication amendment permits one attempt-2; '
        'all other failed/ambiguous attempts, including a failed retry, remain held.')
    value['stop'] = 'STOP_AFTER_192_SELECTED_SCIENTIFIC_RETURNS_NO_AUTOMATIC_EXPANSION'
    return value


def _markdown(value):
    auth = value['authentication_recovery']
    original = original_analysis.markdown(value).replace(original_analysis.STOP, value['stop'])
    return original + ('\n## Authentication recovery\n\n'
        f"Authorized retries: {auth['authorized_retries']}; retry dispatches: {auth['retry_dispatches']}; "
        f"preserved original unavailable attempts: {len(auth['original_failures'])}.\n\n"
        + auth['selection'] + '\n\n' + auth['reporting']
        + '\n\nLocally the combined details are in analysis-auth-recovery.json; the export names that combined report analysis.json.\n')


def _save(value, output):
    root = Path(output)
    write_json(root/'analysis-auth-recovery.json', value)
    from tempfile import NamedTemporaryFile
    with NamedTemporaryFile('w', dir=root, encoding='utf-8', delete=False) as handle:
        handle.write(_markdown(value)); handle.flush(); os.fsync(handle.fileno()); name = handle.name
    os.replace(name, root/'analysis-auth-recovery.md')
    return value


def inspect(output):
    with run_lock(output):
        return _combined(*_load(output))


def analyze(output):
    with run_lock(output):
        return _save(_combined(*_load(output)), output)


class RetrySession(Session):
    def __init__(self, root, amendment):
        self.out = root
        self.identity = _identity(amendment)
        self.telemetry = None


def _blocked(original, retries):
    return any(state(op) in ('failed', 'ambiguous') and cell_id not in retries for cell_id, op in original.items()) or any(
        state(op) in ('failed', 'ambiguous') for op in retries.values())


def run(output, live=False, max_new=192, _transport=None):
    if type(max_new) is not int or not 1 <= max_new <= 192:
        raise ValueError('--max-new must be 1..192, including authentication retries')
    if live and _transport is not None:
        raise ValueError('Cannot mix live and mock execution')
    stats = dict(new_dispatches=0, newly_returned=0)
    started = time.perf_counter()
    with run_lock(output):
        c, original, mode, proofs, amendment, retries = _load(output)
        stats['cached'] = sum(state(op) == 'returned' for op in original.values()) + sum(state(op) == 'returned' for op in retries.values())
        if not live and _transport is None:
            return _combined(c, original, mode, proofs, amendment, retries, stats)
        wanted = 'MOCK' if _transport is not None else 'LIVE_API'
        if mode not in ('UNEXECUTED', wanted):
            raise ValueError('Mock/live caches cannot mix')
        if _transport is not None and getattr(_transport, 'kind', None) != 'MOCK':
            raise ValueError('Mock transport required')
        eligible_ids = {p['cell_id'] for p in proofs}
        # An amendment is a frozen list, never silently expanded after a new failure.
        allowed = set(retries) if amendment else eligible_ids
        if any(state(op) in ('failed', 'ambiguous') and key not in allowed for key, op in original.items()) or any(
                state(op) in ('failed', 'ambiguous') for op in retries.values()):
            stats['stopped_after_held_failure'] = True
            return _save(_combined(c, original, mode, proofs, amendment, retries, stats), output)
        retry_work = [p for p in (amendment['requests'] if amendment else proofs) if state(retries.get(p['cell_id'])) == 'never_started']
        pending_original = any(state(op) == 'never_started' for op in original.values())
        if not retry_work and not pending_original:
            return _save(_combined(c, original, mode, proofs, amendment, retries, stats), output)
        if live and not os.environ.get('OPENAI_API_KEY'):
            raise ValueError('Set OPENAI_API_KEY in this shell; never save it in the repository')
        if retry_work:
            if amendment is None:
                amendment = freeze(c.out/FOLDER/'amendment.json', _amendment_fields(c, wanted, proofs))
            transport = _transport if _transport is not None else HTTPTransport()
            root = c.out/FOLDER; identity = _identity(amendment)
            uid = uuid.uuid4().hex; folder = root/'invocations'/uid
            freeze(folder/'started.json', dict(identity, max_new=max_new, started_utc=legacy.utc()))
            session = RetrySession(root, amendment); status = 'INTERRUPTED'
            try:
                for proof in retry_work[:max_new]:
                    oid = proof['retry_operation_id']
                    def dispatch():
                        freeze(root/'dispatches'/(digest(oid)+'.json'), dict(invocation=uid, request_hash=proof['request_hash']))
                        stats['new_dispatches'] += 1
                        print('Retrying authenticated request ' + proof['cell_id'], flush=True)
                        began = legacy.utc(); tick = time.perf_counter()
                        response = transport('openai', proof['request']['payload'], 180)
                        safe = redact(response)
                        raw = dict(response=safe, requested_model=proof['request']['payload']['model'],
                                   started_utc=began, finished_utc=legacy.utc(), elapsed_seconds=time.perf_counter()-tick,
                                   redacted=safe != response)
                        freeze(root/'responses'/(digest(oid)+'.json'), dict(operation_id=oid, request_hash=proof['request_hash'], raw=raw))
                        failure = infrastructure_error(raw)
                        if failure:
                            raise legacy.InfrastructureFailure(failure)
                        print('Returned authentication retry ' + proof['cell_id'], flush=True)
                        return raw
                    try:
                        session.operation(oid, proof['request'], dispatch, STAGE)
                        stats['newly_returned'] += 1
                    except OperationUnavailable as exc:
                        cause = exc.__cause__ or exc
                        freeze(folder/'error.json', dict(operation_id=oid, error_type=type(cause).__name__, message=redact(str(cause))))
                        stats['stopped_after_failure'] = proof['cell_id']; break
                status = 'STOPPED_AFTER_FAILURE' if 'stopped_after_failure' in stats else 'BOUNDED_COMPLETE'
            finally:
                freeze(folder/'finished.json', dict(identity, status=status, finished_utc=legacy.utc(), **stats))
            retries = _retry_journal(c, amendment)
        may_continue = not _blocked(original, retries) and all(state(op) == 'returned' for op in retries.values())
    # The original runner owns its own non-reentrant run lock and preserves its
    # original cache policy. It only dispatches original never-started requests.
    remaining = max_new - stats['new_dispatches']
    if may_continue and remaining and pending_original:
        continuation = legacy.run(output, live=live, max_new=remaining, _transport=_transport)
        for key in ('new_dispatches', 'newly_returned'):
            stats[key] += continuation['this_invocation'][key]
        if 'stopped_after_failure' in continuation['this_invocation']:
            stats['stopped_after_failure'] = continuation['this_invocation']['stopped_after_failure']
    stats['elapsed_seconds'] = time.perf_counter() - started
    with run_lock(output):
        return _save(_combined(*_load(output), invocation=stats), output)


def export(output, destination):
    target = separate(destination, output)
    if target.exists():
        raise ValueError('Fresh export destination required')
    with run_lock(output):
        loaded = _load(output); c = loaded[0]; value = _combined(*loaded)
        files = {}
        for path in sorted(c.out.rglob('*')):
            relative = path.relative_to(c.out)
            if relative.parts[0] not in DIRS | {FOLDER} and str(relative) not in TOP:
                continue
            if path.is_symlink():
                raise ValueError('Export rejects symlinks')
            if path.is_file():
                files[str(relative)] = path.read_bytes()
        files['analysis.json'] = (json.dumps(value, indent=2, sort_keys=True)+'\n').encode()
        files['analysis.md'] = _markdown(value).encode()
        files['manual-review.csv'] = review_sheet(value['cases']).encode()
        traces = []
        for row in value['cases']:
            traces += [row['cell']['id'], json.dumps({k: row[k] for k in (
                'operation_status', 'request_hash', 'operation_hash', 'original_operation_hash', 'selected_attempt')})]
            if row['score']:
                for message in row['score']['messages']:
                    traces += [f"[output {message['output_index']} / phase {message['phase']}]", message['text']]
                    traces += ['[refusal] '+x for x in message['refusals']]
            else:
                traces += ['[no scoreable returned response; consult both attempt journals]']
            traces += ['']
        files['gpt-traces.txt'] = '\n'.join(traces).encode()
        source_root = Path(__file__).parent
        files['protocol.md'] = (source_root/'STUDY2_GPT_EXPLANATION_V1.md').read_bytes()
        recovery_doc = source_root/'STUDY2_GPT_AUTH_RECOVERY_V1.md'
        if recovery_doc.exists():
            files['authentication-recovery-protocol.md'] = recovery_doc.read_bytes()
        files['authentication-recovery-implementation.py'] = Path(__file__).read_bytes()
        files['bundle-manifest.json'] = (json.dumps(dict(protocol=c.plan['protocol'], plan_hash=c.plan['artifact_hash'],
            code_contract=c.plan['code_contract'], source=c.plan['source'], measurement_mode=value['measurement_mode'],
            authentication_recovery=value['authentication_recovery'],
            files={k: dict(bytes=len(v), sha256=sha_bytes(v)) for k, v in sorted(files.items())},
            annotation_states=['not_reviewed', 'absent', 'present', 'uncertain'],
            offsets='Zero-based half-open Unicode offsets within the selected message text; preserve output_index and phase. Indicators may overlap.',
            relocation='Extract into a fresh directory with both code contracts. No Qwen tokenizer, weights, original paths or API key is required to inspect.'),
            indent=2, sort_keys=True)+'\n').encode()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as handle:
            with zipfile.ZipFile(handle, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(files.items()):
                    archive.writestr(name, data)
    return dict(path=str(target), sha256=sha(target), files=len(files), complete=value['complete'], network_calls=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('inspect', 'run', 'analyze', 'export'):
        p = sub.add_parser(command); p.add_argument('--output', required=True)
        if command == 'run':
            p.add_argument('--live-openai', action='store_true'); p.add_argument('--max-new', type=int, default=192)
        if command == 'export':
            p.add_argument('--destination', required=True)
    args = parser.parse_args(argv)
    if args.command == 'run':
        value = run(args.output, live=args.live_openai, max_new=args.max_new)
    elif args.command == 'inspect':
        value = inspect(args.output)
    elif args.command == 'analyze':
        value = analyze(args.output)
    else:
        value = export(args.output, args.destination)
    print(json.dumps({k: v for k, v in value.items() if k not in ('cases', 'sensitivities')}, indent=2, sort_keys=True))
    if args.command == 'run' and args.live_openai and (value['totals']['failed'] or value['totals']['ambiguous']):
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
