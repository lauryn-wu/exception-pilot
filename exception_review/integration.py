"""Versioned event/edit integration; source is read-only, no fake manual review."""
import json
from pathlib import Path
from exception_pilot.core import digest,rng_for
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read,sealed_write,validate_intervention_case
from exception_continuation.core import final_score
from exception_continuation.backend import readout
from exception_continuation.validation import replay_check
from exception_continuation.edits import token_change
from .artifacts import Source,Review,freeze,sha
from .policy import code_hash
from .boundaries import answer_boundary
from .workflow import statements,eligible
from .telemetry import Telemetry,TimedBackend,operation_stage,load_backend

class OperationFailed(Exception): pass

class ModelSession:
    """Independent model journal: terminal arm errors do not erase other contrasts."""
    def __init__(self,out,source,backend,telemetry,artifact_hash):
        self.out=Path(out); self.plan=source.plan; self.backend_hash=digest(backend.identity)
        if self.backend_hash!=source.collection['backend_hash']: raise ValueError('Source backend identity changed')
        self.backend=TimedBackend(backend,telemetry); self.telemetry=telemetry
        self.identity=dict(source_path=str(source.root),source_hash=source.hash,backend_hash=self.backend_hash,code_hash=code_hash(),manifest_hash=artifact_hash)
        freeze(self.out/'model-execution.json',self.identity)
    def operation(self,op_id,request,fn):
        path=self.out/'model-operations'/(digest(op_id)+'.json'); identity=dict(self.identity,id=op_id,request=request)
        self.backend.stage=operation_stage(op_id)
        if path.exists():
            old=sealed_read(path)
            if any(old[k]!=v for k,v in identity.items()): raise ValueError('Model operation identity changed')
            self.telemetry.record(stage=operation_stage(op_id),measurement='CACHE',status='cache_hit',operation_id=op_id)
            if old['status']!='returned': raise OperationFailed('Terminal unavailable; never resend: '+op_id)
            return old['result']
        sealed_write(path,dict(identity,status='started'))
        try: result=fn()
        except BaseException as exc:
            sealed_write(path,dict(identity,status='failed',error_type=type(exc).__name__))
            if not isinstance(exc,Exception): raise
            raise OperationFailed(type(exc).__name__+': '+op_id) from exc
        sealed_write(path,dict(identity,status='returned',result=result)); return result
    def generate(self,op_id,ids,budget,capture_at=()):
        return self.operation(op_id,dict(input_ids=ids,budget=budget,capture_at=list(capture_at)),lambda:self.backend.generate(ids,budget,capture_at))

class TokenizerOnly:
    """Explicit separate stage; exact source tokenizer assets, no model loader."""
    def __init__(self,source,path):
        root=Path(path); identity=source.execution['backend']; files=identity['files']
        names={'tokenizer.json','tokenizer_config.json','special_tokens_map.json','vocab.json','merges.txt','tokenizer.model','chat_template.jinja','added_tokens.json'}
        checked={n:h for n,h in files.items() if Path(n).name in names}
        if not checked or any(not (root/n).is_file() or sha(root/n)!=h for n,h in checked.items()): raise ValueError('Exact source tokenizer files required')
        # Refuse unbound tokenizer-affecting extras as well.
        if any(p.name in names and p.name not in checked for p in root.iterdir() if p.is_file()): raise ValueError('Unbound tokenizer file')
        import importlib.metadata
        for package in ('transformers','tokenizers'):
            if importlib.metadata.version(package)!=identity[package]: raise ValueError('Source tokenizer dependency version changed: '+package)
        from transformers import AutoTokenizer
        self.tokenizer=AutoTokenizer.from_pretrained(str(root),local_files_only=True,trust_remote_code=False)
        if self.tokenizer.chat_template!=identity['chat_template'] or not set(self.tokenizer.all_special_ids)<=set(identity['special_ids']): raise ValueError('Tokenizer template/special IDs changed')
        self.special_ids=set(identity['special_ids']); self.identity=identity
    def encode(self,text): return self.tokenizer.encode(text,add_special_tokens=False)
    def decode(self,ids): return self.tokenizer.decode(ids,skip_special_tokens=True,clean_up_tokenization_spaces=False)


def check_tokens(output,scope='full',tokenizer_dir=None,mock=False,backend_override=None):
    with run_lock(str(output)+'/locks'):
        review=Review(output); plan=review.plan(scope); manifest=statements(review,plan)
        if backend_override is not None: backend=backend_override
        elif mock:
            from exception_continuation.backend import MockBackend
            backend=MockBackend()
        elif tokenizer_dir: backend=TokenizerOnly(review.source,tokenizer_dir)
        else: raise ValueError('Explicit --tokenizer-dir or --mock required; never approximate')
        if digest(backend.identity)!=review.source.collection['backend_hash']: raise ValueError('Tokenizer/backend identity mismatch')
        results=[]
        for statement in manifest['rows']:
            tid=statement['task_id']; p=review.case_path(tid,'edit-result')
            if not p.exists(): continue
            edit=review.read_case(tid,'edit-result')
            if edit['state']!='SEMANTIC_ACCEPTED': continue
            row=review.source.rows[tid]; cut=statement['boundaries']['after_statement']; ids=row['raw']['tokens'][:cut['k']]
            checks={}; tokenized={}
            for arm,text in edit['texts'].items():
                tokens=backend.encode(text); tokenized[arm]=tokens
                checks[arm]=bool(backend.decode(tokens)==text and not any(t in backend.special_ids for t in tokens) and (arm!='unchanged' or tokens==ids))
            value=dict(review.binding(),**review.source.case_binding(tid),edit_hash=edit['artifact_hash'],backend_hash=review.source.collection['backend_hash'],passed=all(checks.values()),checks=checks,tokens=tokenized)
            results.append(freeze(review.case_path(tid,'token-check'),value))
        return results


def freeze_edits(output,scope='full'):
    with run_lock(str(output)+'/locks'):
        review=Review(output); plan=review.plan(scope); manifest=statements(review,plan); cases=[]; excluded=[]
        for statement in manifest['rows']:
            tid=statement['task_id']; row=review.source.rows[tid]
            if not eligible(statement):
                reason=statement['decision'] if statement['decision']!='present' else 'after_boundary_failure'
                excluded.append(dict(task_id=tid,reason=reason)); continue
            path=review.case_path(tid,'edit-result')
            if not path.exists(): raise ValueError('Edits INCOMPLETE: pending drafting/verification')
            edit=review.read_case(tid,'edit-result')
            if edit['state']=='EXCLUDED': excluded.append(dict(task_id=tid,reason='edit_failure',detail=edit['reason'])); continue
            token_path=review.case_path(tid,'token-check')
            if not token_path.exists(): raise ValueError('Edits INCOMPLETE: explicit tokenizer check required')
            tokens=review.read_case(tid,'token-check')
            if tokens['edit_hash']!=edit['artifact_hash'] or tokens['backend_hash']!=review.source.collection['backend_hash']: raise ValueError('Stale edit token validation')
            if not tokens['passed']: excluded.append(dict(task_id=tid,reason='edit_token_failure')); continue
            cut=statement['boundaries']['after_statement']; k=cut['k']
            cases.append(dict(task_id=tid,world=row['task']['world'],trajectory_hash=digest(row),initial_agreement=statement['initial_agreement'],agreeing_pair=statement['agreeing_pair'],statement_span=statement['span'],edit_span=edit['span'],edit_hash=edit['artifact_hash'],token_check_hash=tokens['artifact_hash'],texts=edit['texts'],tokenized=tokens['tokens'],k=k,prefix_ids=row['raw']['tokens'][:k],suffix_budget=review.source.plan['config']['max_new_tokens']-k))
        return freeze(review.root/'manifests'/(scope+'-edits.json'),dict(**review.binding(),statement_manifest_hash=manifest['artifact_hash'],review_plan_hash=plan['artifact_hash'],cases=cases,excluded=excluded,status='FROZEN',primary='availability_repair-minus-meaning_control'))


def freeze_events(source,output,statement_manifest=None):
    src=Source(source); out=Path(output).resolve()
    if out==src.root or src.root in out.parents or out in src.root.parents: raise ValueError('Event output must be separate from source')
    annotations=sealed_read(statement_manifest) if statement_manifest else None
    if annotations and (annotations['source_hash']!=src.hash or annotations['code_hash']!=code_hash()): raise ValueError('Stale statement manifest')
    rows=[]
    if annotations:
        for statement in annotations['rows']:
            tid=statement['task_id']
            if statement['trajectory_hash']!=digest(src.rows[tid]): raise ValueError('Wrong source statement')
            cuts=[dict(event=n,**v) for n,v in (statement['boundaries'] or {}).items() if n in src.plan['config']['event_checkpoints']]
            if not cuts: cuts=[dict(event=n,eligible=False,reason=statement['decision'],k=None) for n in ('before_statement','after_statement') if n in src.plan['config']['event_checkpoints']]
            rows.append(dict(task_id=tid,trajectory_hash=digest(src.rows[tid]),cuts=cuts))
    else:
        for tid,row in src.rows.items(): rows.append(dict(task_id=tid,trajectory_hash=digest(row),cuts=[answer_boundary(row)] if 'before_answer' in src.plan['config']['event_checkpoints'] else []))
    with run_lock(out/'locks'):
        return freeze(out/'event-plan.json',dict(source_path=str(src.root),source_hash=src.hash,code_hash=code_hash(),statement_manifest=annotations,kind='statement' if annotations else 'before_answer',rows=rows))


def measure_events(output,live_qwen=False,mock=False,backend_override=None,clock=None):
    with run_lock(str(output)+'/locks'):
        out=Path(output); frozen=sealed_read(out/'event-plan.json'); source=Source(frozen['source_path'])
        if frozen['source_hash']!=source.hash or frozen['code_hash']!=code_hash(): raise ValueError('Stale event plan')
        telemetry=Telemetry(out/'timing-sidecar',{'source_hash':source.hash},clock); status='FAILED'
        try:
            backend=backend_override or load_backend(source.plan,telemetry,live_qwen,mock)
            session=ModelSession(out,source,backend,telemetry,frozen['artifact_hash']); results=[]
            for item in frozen['rows']:
                tid=item['task_id']; row=source.rows[tid]; task=row['task']; ks=sorted({c['k'] for c in item['cuts'] if c['eligible']}); bycut={}; reference=None
                if ks:
                    try:
                        reference=session.generate(f'event/{tid}/reference',row['input_ids'],512,capture_at=ks)
                        matches=all(reference[x]==row['raw'][x] for x in ('tokens','finish','stopped'))
                        for k in ks:
                            try:
                                replay=session.generate(f'event/{tid}/replay/{k}',row['input_ids']+row['raw']['tokens'][:k],512-k,capture_at=(0,))
                                check=replay_check(reference,replay,k,source.plan['config']['validation_tolerances'])
                                check.update(passed=matches and check['passed'],uninterrupted_matches_saved=matches,replay=replay)
                                if check['passed']:
                                    req=dict(input_ids=row['input_ids'],prefix_ids=row['raw']['tokens'][:k],gold=task['expected'],pattern=task['pattern'])
                                    check['readout']=session.operation(f'event/{tid}/readout/{k}',req,lambda req=req:readout(session.backend,**req))
                                bycut[k]=check
                            except OperationFailed as exc: bycut[k]=dict(passed=False,reason=str(exc))
                    except OperationFailed as exc: bycut={k:dict(passed=False,reason=str(exc)) for k in ks}
                cuts=[dict(c,**bycut[c['k']]) if c['eligible'] else c for c in item['cuts']]
                results.append(dict(task_id=tid,reference=reference,cuts=cuts,any_checkpoint_failed=any(c['eligible'] and not c.get('passed') for c in cuts)))
            status='COMPLETE'
            result=freeze(out/'event-measurements.json',dict(source_hash=source.hash,event_plan_hash=frozen['artifact_hash'],backend_hash=session.backend_hash,real_model_status='PENDING' if backend.simulated else 'SEE_PER_CHECKPOINT_VALIDATION',rows=results))
            from exception_continuation.events import summarize_events
            freeze(out/'event-summary.json',dict(source_hash=source.hash,event_plan_hash=frozen['artifact_hash'],measurements_hash=result['artifact_hash'],summary=summarize_events(source.plan,result)))
            return result
        finally:
            telemetry.finish(status)
            from .reporting import model_timing_report
            model_timing_report(out)


def intervene(output,scope='full',live_qwen=False,mock=False,backend_override=None,clock=None):
    with run_lock(str(output)+'/locks'):
        review=Review(output); manifest=sealed_read(review.root/'manifests'/(scope+'-edits.json')); source=review.source
        if any(manifest[k]!=v for k,v in review.binding().items()): raise ValueError('Stale edit manifest')
        out=review.root/'interventions'/scope
        freeze(out/'edit-plan-reference.json',dict(source_path=str(source.root),source_hash=source.hash,manifest=manifest))
        if not manifest['cases']:
            return freeze(out/'interventions.json',dict(source_hash=source.hash,edit_plan_hash=manifest['artifact_hash'],status='NO_ELIGIBLE_CASES',rows=[],real_model_status='PENDING'))
        telemetry=Telemetry(out/'timing-sidecar',{'source_hash':source.hash},clock); status='FAILED'
        try:
            backend=backend_override or load_backend(source.plan,telemetry,live_qwen,mock)
            session=ModelSession(out,source,backend,telemetry,manifest['artifact_hash']); results=[]
            for case in manifest['cases']:
                row=source.rows[case['task_id']]; task=row['task']; tid=task['id']; original=case['prefix_ids']
                if digest(row)!=case['trajectory_hash'] or backend.encode(case['texts']['unchanged'])!=original: raise ValueError('Original trajectory/prefix changed')
                try: validation=validate_intervention_case(session,row,case)
                except OperationFailed as exc: validation=dict(passed=False,reason=str(exc))
                if not validation['passed']:
                    results.append(dict(task_id=tid,world=task['world'],validation=validation,unchanged_replay_passed=False,arms={})); continue
                arms=list(case['texts']); rng_for('edit-order',tid).shuffle(arms); observations={}
                for arm in arms:
                    text=case['texts'][arm]; ids=original if arm=='unchanged' else backend.encode(text)
                    if ids!=case['tokenized'][arm] or backend.decode(ids)!=text or any(t in backend.special_ids for t in ids):
                        observations[arm]=dict(error='token_roundtrip_or_special_token_failure'); continue
                    try:
                        raw=session.generate(f'edit/{tid}/{arm}/continuation',row['input_ids']+ids,case['suffix_budget'],capture_at=(0,))
                        full=backend.decode(ids+raw['tokens']); preserved=full.startswith(text)
                        obs=dict(prefix_ids=ids,prefix_text=text,raw=raw,full_text=full,full_tokens=ids+raw['tokens'],prefix_text_preserved=preserved,score=final_score(full,raw['stopped'] and preserved,task['expected']),changed_tokens=token_change(original,ids),character_delta=len(text)-len(case['texts']['unchanged']))
                        req=dict(input_ids=row['input_ids'],prefix_ids=ids,gold=task['expected'],pattern=task['pattern'])
                        try: obs['readout']=session.operation(f'edit/{tid}/{arm}/readout',req,lambda req=req:readout(session.backend,**req))
                        except OperationFailed as exc: obs['readout_error']=str(exc)
                        observations[arm]=obs
                    except OperationFailed as exc: observations[arm]=dict(error=str(exc))
                raw=observations.get('unchanged',{}).get('raw')
                check=replay_check(validation['reference'],raw,case['k'],source.plan['config']['validation_tolerances']) if raw else dict(passed=False,reason='missing_unchanged_continuation')
                results.append(dict(task_id=tid,world=task['world'],validation=validation,control_validation=check,unchanged_replay_passed=check['passed'],arms=observations))
            status='COMPLETE'
            return freeze(out/'interventions.json',dict(source_hash=source.hash,edit_plan_hash=manifest['artifact_hash'],backend_hash=session.backend_hash,rows=results,real_model_status='PENDING' if backend.simulated else 'SEE_PER_CASE_VALIDATION'))
        finally:
            telemetry.finish(status)
            from .reporting import model_timing_report
            model_timing_report(out)
