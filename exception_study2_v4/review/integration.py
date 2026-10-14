"""Conditional-prefix v4 integration; independent arm availability, no suffix replay gate."""
from pathlib import Path
from exception_pilot.core import digest,rng_for
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from exception_continuation.core import final_score
from exception_continuation.backend import readout
from exception_continuation.edits import token_change
from exception_review.telemetry import Telemetry,load_backend
from .artifacts import Source,Review,freeze,sha
from .policy import code_hash
from .boundaries import answer_boundary
from .workflow import statements,eligible
from .. import PROTOCOL,ESTIMAND
from ..journal import Session,OperationUnavailable
from ..readouts import measure_cut,saved_cut

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
            arm_order=list(edit['texts']); rng_for('edit-order',tid).shuffle(arm_order)
            cases.append(dict(arm_order=arm_order,task_id=tid,world=row['task']['world'],trajectory_hash=digest(row),initial_agreement=statement['initial_agreement'],agreeing_pair=statement['agreeing_pair'],statement_span=statement['span'],edit_span=edit['span'],edit_hash=edit['artifact_hash'],token_check_hash=tokens['artifact_hash'],texts=edit['texts'],tokenized=tokens['tokens'],k=k,prefix_ids=row['raw']['tokens'][:k],suffix_budget=review.source.plan['config']['max_new_tokens']-k))
        return freeze(review.root/'manifests'/(scope+'-edits.json'),dict(**review.binding(),statement_manifest_hash=manifest['artifact_hash'],review_plan_hash=plan['artifact_hash'],cases=cases,excluded=excluded,status='FROZEN',primary='availability_repair-minus-meaning_control'))



def freeze_events(source,output,statement_manifest=None):
    src=Source(source);out=Path(output).resolve()
    if out==src.root or src.root in out.parents or out in src.root.parents:raise ValueError('Event output must be separate')
    annotations=sealed_read(statement_manifest) if statement_manifest else None
    if annotations and (annotations.get('source_schema')!=PROTOCOL or annotations['source_hash']!=src.hash or annotations['code_hash']!=code_hash()):
        raise ValueError('Statement manifest source/code changed')
    annotations_by_id={s['task_id']:s for s in annotations['rows']} if annotations else {}
    if annotations and len(annotations_by_id)!=len(annotations['rows']):raise ValueError('Duplicate statement annotations')
    rows=[]
    # Always retain every visible source, including negatives/edit exclusions.
    for tid,row in src.rows.items():
        statement=annotations_by_id.get(tid);cuts=[]
        if statement and statement['trajectory_hash']!=digest(row):raise ValueError('Wrong-source statement')
        if annotations:
            for name in ('before_statement','after_statement'):
                if name not in src.plan['config']['event_checkpoints']:continue
                boundary=(statement or {}).get('boundaries') or {}
                c=boundary.get(name,dict(k=None,eligible=False,reason=(statement or {}).get('decision','not_reviewed')))
                cuts.append(dict(event=name,**c))
        if 'before_answer' in src.plan['config']['event_checkpoints']:
            cuts.append(answer_boundary(row))
        rows.append(dict(task_id=tid,trajectory_hash=digest(row),cuts=cuts))
    with run_lock(out/'locks'):
        return freeze(out/'event-plan-v4.json',dict(protocol=PROTOCOL,source_path=str(src.root),source_hash=src.hash,
            code_hash=code_hash(),statement_manifest=annotations,rows=rows,kind='annotated-and-before-answer' if annotations else 'before-answer'))


def measure_events(output,live_qwen=False,mock=False,backend_override=None,clock=None):
    with run_lock(str(output)+'/locks'):
        out=Path(output);frozen=sealed_read(out/'event-plan-v4.json');source=Source(frozen['source_path'])
        if frozen['protocol']!=PROTOCOL or frozen['source_hash']!=source.hash or frozen['code_hash']!=code_hash():raise ValueError('Stale v4 event plan')
        telemetry=Telemetry(out/'timing-v4',dict(protocol=PROTOCOL,source_hash=source.hash),clock);status='FAILED'
        try:
            backend=backend_override or load_backend(source.plan,telemetry,live_qwen,mock)
            if digest(backend.identity)!=source.execution['backend_hash']:raise ValueError('Source backend changed')
            session=Session(out,source.plan,backend,telemetry,dict(source_binding=source.hash,manifest_hash=frozen['artifact_hash']))
            rows=[]
            for item in frozen['rows']:
                row=source.rows[item['task_id']]
                if item['trajectory_hash']!=digest(row):raise ValueError('Event source changed')
                bycut={k:measure_cut(session,row,k,source.plan['config']['readout_cues'][:1],'v4/event/'+item['task_id'])
                       for k in sorted({c['k'] for c in item['cuts'] if c['eligible']})}
                cuts=[dict(c,**{n:v for n,v in bycut[c['k']].items() if n!='k'}) if c['eligible'] else
                      dict(c,checkpoint_eligible=False,conditional_readout_valid=False,readout_returned=False,
                           failed_or_unavailable_reason=c.get('reason')) for c in item['cuts']]
                rows.append(dict(task_id=item['task_id'],cuts=cuts))
            value=freeze(out/'event-measurements-v4.json',dict(protocol=PROTOCOL,source_hash=source.hash,
                event_plan_hash=frozen['artifact_hash'],measurement='MOCK' if backend.simulated else 'LIVE',rows=rows))
            from ..reporting import summarize_events
            freeze(out/'event-summary-v4.json',dict(measurements_hash=value['artifact_hash'],**summarize_events(source.plan,value)))
            status='COMPLETE';return value
        finally:
            telemetry.finish(status)
            from ..reporting import timing_report
            timing_report(out)


def arm_input(backend,row,case,arm):
    original=case['prefix_ids'];k=case['k'];text=case['texts'][arm];ids=case['tokenized'][arm]
    if original!=row['raw']['tokens'][:k] or case['suffix_budget']!=512-k or saved_cut(row,k) is None:
        raise ValueError('Frozen original cut/budget changed')
    start,end=case['edit_span'];original_text=case['texts']['unchanged']
    if not (0<=start<end<=len(original_text)):raise ValueError('Invalid edit span')
    outside=text[:start]==original_text[:start] and text.endswith(original_text[end:])
    if arm=='unchanged':outside=text==backend.decode(original) and ids==original
    context=row['input_ids']+ids
    valid=bool(outside and backend.encode(text)==ids and backend.decode(ids)==text
               and not any(t in backend.special_ids for t in ids)
               and backend.decode(context)==backend.decode(row['input_ids'])+text)
    return dict(arm_input_valid=valid,prefix_ids=ids,prefix_text=text,context_ids=context,
        context_hash=digest(context),prefix_hash=digest(ids),original_k=k,suffix_budget=case['suffix_budget'],
        token_length_delta=len(ids)-k,character_delta=len(text)-len(original_text),
        fresh_prefix_control=arm=='unchanged',failed_or_unavailable_reason=None if valid else 'arm_input_preservation_failed')


def intervene(output,scope='full',live_qwen=False,mock=False,backend_override=None,clock=None):
    with run_lock(str(output)+'/locks'):
        review=Review(output);source=review.source;manifest=sealed_read(review.root/'manifests'/(scope+'-edits.json'))
        if any(manifest.get(k)!=v for k,v in review.binding().items()):raise ValueError('Stale v4 edit manifest')
        out=review.root/'interventions-v4'/scope
        freeze(out/'edit-plan-reference-v4.json',dict(protocol=PROTOCOL,source_path=str(source.root),source_hash=source.hash,manifest=manifest))
        if not manifest['cases']:
            return freeze(out/'interventions-v4.json',dict(protocol=PROTOCOL,source_hash=source.hash,edit_plan_hash=manifest['artifact_hash'],
                status='NO_ELIGIBLE_CASES',rows=[],measurement='MOCK' if source.execution['mode']=='MOCK' else 'NOT_RUN',interpretation=ESTIMAND))
        telemetry=Telemetry(out/'timing-v4',dict(protocol=PROTOCOL,source_hash=source.hash),clock);status='FAILED'
        try:
            backend=backend_override or load_backend(source.plan,telemetry,live_qwen,mock)
            if digest(backend.identity)!=source.execution['backend_hash']:raise ValueError('Source backend changed')
            session=Session(out,source.plan,backend,telemetry,dict(source_binding=source.hash,manifest_hash=manifest['artifact_hash']))
            rows=[]
            for case in manifest['cases']:
                tid=case['task_id'];row=source.rows[tid];task=row['task']
                edit=review.read_case(tid,'edit-result');tokens=review.read_case(tid,'token-check')
                if (digest(row)!=case['trajectory_hash'] or edit['artifact_hash']!=case['edit_hash']
                        or tokens['artifact_hash']!=case['token_check_hash'] or edit['texts']!=case['texts']
                        or edit['span']!=case['edit_span'] or tokens['tokens']!=case['tokenized']):raise ValueError('Frozen edit/source changed')
                expected_order=list(case['texts']);rng_for('edit-order',tid).shuffle(expected_order)
                if case['arm_order']!=expected_order:raise ValueError('Frozen arm order changed')
                arms={}
                for arm in case['arm_order']:
                    obs=arm_input(backend,row,case,arm);arms[arm]=obs
                    if not obs['arm_input_valid']:continue
                    try:
                        raw=session.generate(f'v4/edit/{tid}/{arm}/continuation',obs['context_ids'],case['suffix_budget'],stage='edited_continuation')
                        full=backend.decode(obs['prefix_ids']+raw['tokens']);preserved=full.startswith(obs['prefix_text'])
                        obs.update(raw=raw,full_text=full,full_tokens=obs['prefix_ids']+raw['tokens'],
                            prefix_text_preserved=preserved,arm_input_valid=obs['arm_input_valid'] and preserved,
                            score=final_score(full,raw['stopped'] and preserved,task['expected']),
                            changed_tokens=token_change(case['prefix_ids'],obs['prefix_ids']))
                        if not preserved:obs['failed_or_unavailable_reason']='generated_prefix_text_not_preserved'
                    except OperationUnavailable as exc:
                        obs['failed_or_unavailable_reason']=str(exc);continue
                    req=dict(input_ids=row['input_ids'],prefix_ids=obs['prefix_ids'],gold=task['expected'],pattern=task['pattern'])
                    try:
                        obs['readout']=session.operation(f'v4/edit/{tid}/{arm}/readout',req,lambda req=req:readout(session.backend,**req),'candidate_readout')
                        obs['conditional_readout_valid']=obs['arm_input_valid']
                    except OperationUnavailable as exc:obs.update(conditional_readout_valid=False,readout_error=str(exc))
                unchanged=arms.get('unchanged',{}).get('raw')
                diagnostic=None if unchanged is None else all(unchanged[x]==(row['raw']['tokens'][case['k']:] if x=='tokens' else row['raw'][x]) for x in ('tokens','stopped','finish'))
                rows.append(dict(task_id=tid,world=task['world'],fresh_prefix_control='unchanged',arms=arms,
                    original_vs_unchanged=dict(exact_suffix_match=diagnostic,gating=False)))
            value=freeze(out/'interventions-v4.json',dict(protocol=PROTOCOL,source_hash=source.hash,edit_plan_hash=manifest['artifact_hash'],
                status='COMPLETE',rows=rows,measurement='MOCK' if backend.simulated else 'LIVE',interpretation=ESTIMAND))
            status='COMPLETE';return value
        finally:
            telemetry.finish(status)
            from ..reporting import timing_report
            timing_report(out)
