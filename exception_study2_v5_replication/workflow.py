"""Explicit replication-only approval and append-only extension of a verified copy."""
import shutil
from pathlib import Path
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review.telemetry import Telemetry, load_backend
from exception_study2_v5 import PROTOCOL, BUDGET
from exception_study2_v5.runner import Source,V5MockBackend
from exception_study2_v5.journal import Session,OperationUnavailable,V5TimedBackend
from exception_study2_v5.scoring import final_score,validate_raw,boundaries,raw_metadata
from . import VERSION
from .integrity import (pilot,tree,separate,archive_ref,expected_amendment,read_amendment,
                        check_archives,operation_tree,revision,code_hash)


def prepare(source,output,preserve=()):
    src=pilot(source);out=Path(output).resolve()
    roots=list(dict.fromkeys([src.root]+[Path(p).resolve() for p in preserve]))
    separate(out,roots)
    if out.exists():
        if (out/'amendment.json').exists():
            a=read_amendment(out)
            if [str((out/r['path']).resolve()) for r in a['archives']]!=[str(p) for p in roots]:
                raise ValueError('Preserved input set changed')
            return a
        raise ValueError('Fresh versioned output required; incomplete copies are not silently resumed')
    refs=[archive_ref(p,out) for p in roots]
    a=expected_amendment(src,out,refs)
    out.mkdir(parents=True)
    # A real byte copy, never hard links, symlinks, or duplicated model weights.
    shutil.copytree(src.root,out/'originals')
    if tree(out/'originals')!=a['copied_source_files']:raise ValueError('Copy failed byte verification')
    check_archives(a,out)
    result=freeze(out/'amendment.json',a)
    freeze(out/'preparation-provenance.json',dict(amendment_hash=result['artifact_hash'],
        code_revision=revision(),implementation_hash=code_hash(),inference_calls=0,next_stage='STOP_EXPLICIT_APPROVAL'))
    return result


def approve(output,amendment_hash,reviewer,rationale,acknowledge_pilot_examined=False,approve_remaining=False):
    out=Path(output).resolve()
    with run_lock(out):
        a=read_amendment(out)
        if (amendment_hash!=a['artifact_hash'] or not reviewer.strip() or not rationale.strip()
            or acknowledge_pilot_examined is not True or approve_remaining is not True):
            raise ValueError('Explicit source-bound approval and acknowledgment of examined pilot required')
        return freeze(out/'replication-approval.json',dict(version=VERSION,amendment_hash=amendment_hash,
            reviewer=reviewer,rationale=rationale,pilot_examined=True,approve_remaining=True,
            worlds=56,original_attempts=448,only_prespecified_tasks=True,study_2b_not_a_prerequisite=True,
            no_result_dependent_stopping=True,automatic_measurements=False,automatic_interventions=False,
            code_revision=revision(),next_stage='STOP_EXPLICIT_COLLECTION'))


def require_approval(out,a):
    v=sealed_read(Path(out)/'replication-approval.json')
    if (v.get('version')!=VERSION or v.get('amendment_hash')!=a['artifact_hash']
        or v.get('pilot_examined') is not True or v.get('approve_remaining') is not True
        or v.get('worlds')!=56 or v.get('original_attempts')!=448 or not v.get('reviewer','').strip()
        or not v.get('rationale','').strip() or v.get('only_prespecified_tasks') is not True
        or v.get('no_result_dependent_stopping') is not True
        or v.get('study_2b_not_a_prerequisite') is not True
        or v.get('automatic_measurements') is not False or v.get('automatic_interventions') is not False):
        raise ValueError('Invalid replication-only approval')
    return v


def base_identity(source):
    return dict(protocol=PROTOCOL,plan_hash=source.plan['plan_hash'],source_hash=source.plan['source_hash'],
                backend_hash=source.execution['backend_hash'])


def runtime_value(a,approval,source):
    return dict(version=VERSION,amendment_hash=a['artifact_hash'],approval_hash=approval['artifact_hash'],
        code_revision=revision(),implementation_hash=code_hash(),original_execution_hash=source.execution['artifact_hash'],
        original_code_revision=source.execution['code_revision'],backend=source.execution['backend'],
        mode=source.execution['mode'],**base_identity(source))


def verify_copy(out,a,approval=None):
    source=Source(Path(out)/'originals',complete=False,scope='all');saved=operation_tree(source.root)
    runtime_path=Path(out)/'replication-execution.json'
    runtime=sealed_read(runtime_path) if runtime_path.exists() else None
    if runtime:
        approval=approval or require_approval(out,a)
        if {k:v for k,v in runtime.items() if k!='artifact_hash'}!=runtime_value(a,approval,source):
            raise ValueError('Replication runtime/revision changed; never rewrite execution metadata')
    initial={'v5/original/'+tid for tid in a['pilot_rows']}
    remaining={'v5/original/'+t['id']:t for t in a['remaining_tasks']}
    base=base_identity(source)
    for op_id,op in saved.items():
        if any(op.get(k)!=v for k,v in base.items()):raise ValueError('Operation scientific/backend identity changed')
        if op_id.startswith('v5/technical/') or op_id in initial:continue
        if op_id not in remaining or runtime is None:raise ValueError('Unplanned or unbound replication operation')
        if op.get('replication_execution_hash')!=runtime['artifact_hash'] or op.get('amendment_hash')!=a['artifact_hash']:
            raise ValueError('Replication operation provenance changed')
        if op['stage']!='original_generation':raise ValueError('Replication operation stage changed')
        req=op['request']
        if (set(req)!= {'input_ids','context_hash','budget','capture_at','fresh_prefill'}
            or req['context_hash']!=digest(req['input_ids']) or req['budget']!=BUDGET
            or req['capture_at']!=[] or req['fresh_prefill'] is not True):raise ValueError('Replication generation settings changed')
    expected={digest(t['id'])+'.json' for t in source.plan['tasks']}
    if any(p.name not in expected for p in (source.root/'originals-v5').iterdir()):raise ValueError('Unplanned original row')
    return source


class ReplicationSession(Session):
    """Reuse immutable operation/generate methods, but retain the pilot execution.

    The old execution-v5.json remains the scientific source's original identity.
    Every NEW operation binds a truthful replication-execution.json with actual HEAD.
    This constructor never calls or patches the legacy constructor/approval function.
    Resumption requires this exact replication runtime revision and backend identity.
    """
    def __init__(self,out,a,approval,source,backend,telemetry):
        if backend.identity!=source.execution['backend'] or digest(backend.identity)!=source.execution['backend_hash']:
            raise ValueError('Exact original backend identity required; abort without generating')
        if ('MOCK' if backend.simulated else 'LIVE_LOCAL')!=source.execution['mode']:raise ValueError('Backend mode changed')
        # Check official chat rendering against all 32 saved pilot inputs, no inference.
        for tid in a['pilot_rows']:
            row=source.rows[tid]
            if backend.prompt(row['task']['prompt'])!=row['input_ids']:raise ValueError('Original prompt token IDs changed')
        self.out=source.root;self.plan=source.plan;self.backend_hash=source.execution['backend_hash']
        self.execution=source.execution
        runtime=freeze(Path(out)/'replication-execution.json',runtime_value(a,approval,source))
        self.identity=dict(base_identity(source),amendment_hash=a['artifact_hash'],replication_execution_hash=runtime['artifact_hash'])
        self.telemetry=telemetry;self.backend=V5TimedBackend(backend,telemetry)


def inspect(output):
    a=read_amendment(output);source=verify_copy(output,a)
    if (Path(output)/'replication-approval.json').exists():require_approval(output,a)
    rows={tid:r for tid,r in source.rows.items() if tid not in a['pilot_rows']}
    return dict(version=VERSION,amendment_hash=a['artifact_hash'],mode=source.execution['mode'],
        historical_execution_revision=source.execution['code_revision'],current_code_revision=revision(),
        backend_hash=source.execution['backend_hash'],required_hardware=source.execution['backend'].get('hardware'),
        required_model_dir=source.plan['config']['model_dir'],technical_passed=True,
        pilot_originals_preserved=32,remaining_worlds=[w['id'] for w in a['remaining_worlds']],
        remaining_tasks=a['remaining_tasks'],remaining_visible_ids=a['remaining_visible_ids'],
        recorded_remaining=len(rows),unrecorded_remaining=448-len(rows),visible_trajectories=224,
        generated_token_ceiling=448*BUDGET,readout_ceiling=2688,candidate_sequence_ceiling=8064,
        generated_measurement_answers=0,edited_continuations=0,
        approved=(Path(output)/'replication-approval.json').exists(),next_stage='STOP')


def collect(output,live_qwen=False,mock=False,backend_override=None):
    if not live_qwen and not mock and backend_override is None:return dict(inspect(output),inference_calls=0)
    out=Path(output).resolve()
    with run_lock(out):
        a=read_amendment(out);approval=require_approval(out,a);source=verify_copy(out,a,approval)
        if live_qwen and (mock or backend_override is not None):raise ValueError('Choose one explicit execution mode')
        if live_qwen and source.execution['mode']!='LIVE_LOCAL':raise ValueError('Mock source cannot authorize live replication')
        telemetry=Telemetry(out/'timing-replication',dict(replication_version=VERSION,amendment_hash=a['artifact_hash'],code_revision=revision()))
        status='FAILED'
        try:
            backend=backend_override if backend_override is not None else V5MockBackend() if mock else load_backend(source.plan,telemetry,True,False)
            session=ReplicationSession(out,a,approval,source,backend,telemetry)
            for task in a['remaining_tasks']:
                path=source.root/'originals-v5'/(digest(task['id'])+'.json')
                if path.exists():continue  # Source and the immutable provenance were checked above.
                ids=session.backend.prompt(task['prompt']);op_id='v5/original/'+task['id']
                row=dict(task=task,input_ids=ids,input_hash=digest(ids),raw=None,boundaries=[],validation_error=None,
                         score=final_score('',False,task['expected'],task['arm']))
                try:raw=session.generate(op_id,ids,BUDGET,stage='original_generation')
                except OperationUnavailable:
                    row.update(status='unavailable',validation_error='failed_or_ambiguous_no_resend')
                else:
                    row['raw']=raw
                    try:
                        validate_raw(raw,session.backend,BUDGET)
                        row.update(boundaries=boundaries(session.backend,raw),
                            score=final_score(raw['text'],raw['stopped'],task['expected'],task['arm']),status='returned')
                    except (ValueError,KeyError,TypeError) as exc:row.update(status='invalid_return',validation_error=str(exc))
                folder=source.root/'operations-v5'/digest(op_id)
                saved=next(sealed_read(folder/(s+'.json')) for s in ('returned','failed','started') if (folder/(s+'.json')).exists())
                row.update(**raw_metadata(row['raw'],ids),operation_hash=saved['artifact_hash'],plan_hash=source.plan['plan_hash'],
                    backend_hash=session.backend_hash,technical_hash=source.technical['artifact_hash'])
                freeze(path,row)
            final=Source(source.root,scope='all')
            freeze(source.root/'collection-v5.json',dict(protocol=PROTOCOL,plan_hash=source.plan['plan_hash'],source_binding=final.hash,
                row_hashes={tid:r['artifact_hash'] for tid,r in final.rows.items()}))
            result=freeze(out/'replication-collection.json',dict(version=VERSION,amendment_hash=a['artifact_hash'],
                source=Source(source.root,scope='remaining').binding_at(out),recorded_remaining=448,
                pilot_originals_preserved=32,measurements_started=False,interventions_started=False,next_stage='STOP'))
            read_amendment(out);verify_copy(out,a,approval);status='COMPLETE';return result
        finally:telemetry.finish(status)
