"""Read-only pilot authentication and one indexed set of historical source/readout joins."""
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.runner import Source
from exception_study2_source_report.evidence import legacy
from exception_study2_source_user_pilot.parent import Parent as V2Parent
from exception_study2_source_user_pilot.planning import make_plan as pilot_plan,context_text as pilot_context_text
from exception_study2_source_user_pilot.execution import journal as pilot_journal
from exception_study2_source_user_pilot.parser import parse_reply
from . import PILOT_PLAN,PILOT_CONTRACT
from .integrity import artifact_files,scientific_files


def authenticate_pilot(root,tok,old):
    root=Path(root);p=sealed_read(root/'pilot-plan.json')
    if p.get('artifact_hash')!=PILOT_PLAN or p.get('code_contract')!=PILOT_CONTRACT:
        raise ValueError('Exact successful pilot plan and contract required')
    if {k:v for k,v in p.items() if k!='artifact_hash'}!=pilot_plan(old,tok):
        raise ValueError('Pilot source/query/rendering/settings identity changed')
    prep=sealed_read(root/'preparation.json')
    if (prep['plan_hash']!=PILOT_PLAN or prep['code_contract']!=PILOT_CONTRACT
        or prep.get('real_tokenizer_serialization_validated') is not True
        or prep.get('model_loads')!=0 or prep.get('inference_calls')!=0):
        raise ValueError('Pilot real-tokenizer preparation evidence differs')
    queries={q['id']:q for q in p['queries']}
    c=SimpleNamespace(out=root,plan=p,queries=queries)
    saved,mode=pilot_journal(c)
    if mode!='LIVE_LOCAL' or len(queries)!=12 or set(saved)!=set(queries) or any(o['status']!='returned' for o in saved.values()):
        raise ValueError('Twelve returned LIVE_LOCAL pilot operations required')
    scores={i:parse_reply(saved[i]['result'],q['expected'],tok) for i,q in queries.items()}
    if not all(s['correct'] and s['complete'] and s['eos_observed'] for s in scores.values()):
        raise ValueError('Successful pilot must recompute 12/12 exact correct terminal-EOS replies')
    starts={x.parent.name:sealed_read(x) for x in (root/'invocations').glob('*/started.json')}
    finishes={x.parent.name:sealed_read(x) for x in (root/'invocations').glob('*/finished.json')}
    if len(starts)!=1 or set(starts)!=set(finishes):raise ValueError('Pilot requires one completed live invocation')
    invocation=next(iter(starts));start=starts[invocation];finish=finishes[invocation]
    if (any(v.get('plan_hash')!=PILOT_PLAN or v.get('measurement_mode')!='LIVE_LOCAL' for v in (start,finish))
        or start['executable_ids']!=list(queries) or finish.get('model_loads')!=1
        or finish.get('model_load_attempts')!=1 or finish.get('new_generations')!=12
        or finish.get('status')!='COMPLETE' or start['extension_revision']!=finish['extension_revision']):
        raise ValueError('Pilot immutable cumulative execution differs from one load/twelve calls')
    for i in queries:
        dispatch=sealed_read(root/'operation-execution'/(digest(i)+'.json'))
        if dispatch['invocation']!=invocation or dispatch['extension_revision']!=start['extension_revision']:
            raise ValueError('Pilot dispatch not bound to the authenticated live invocation')
    rows={x.name:sealed_read(x) for x in (root/'source-evidence').glob('*.json')}
    if rows!={digest(k)+'.json':v for k,v in old.sources.items()}:raise ValueError('Pilot source snapshot differs')
    contexts={x.name:x.read_text() for x in (root/'contexts').iterdir()}
    if contexts!={f'{i:02d}.txt':pilot_context_text(q,tok) for i,q in enumerate(p['queries'])}:
        raise ValueError('Pilot readable contexts differ')
    files=scientific_files(root)
    for name in files:
        if name.endswith('.json') and name!='parent-evidence/report.json':sealed_read(root/name)
    return p,dict(plan_hash=PILOT_PLAN,code_contract=PILOT_CONTRACT,
        execution_hash=sealed_read(root/'execution-content.json')['artifact_hash'],
        preparation_hash=prep['artifact_hash'],measurement_mode=mode,correct=12,returned=12,
        present_correct=8,missing_correct=4,cumulative_new_calls=12,cumulative_model_loads=1,
        immutable_manifest=files,immutable_manifest_hash=digest(files),
        query_hashes={i:q['query_hash'] for i,q in queries.items()},operation_hashes={i:saved[i]['artifact_hash'] for i in queries},
        scores=scores,raw_responses={i:saved[i]['result'] for i in queries},
        failed_v1='FAILED',failed_v2=old.summary,
        derived_report_counters_are_measurement_identity=False)


class Evidence:
    def __init__(self,pilot,originals,readouts,tok):
        self.root=Path(pilot).resolve();self.tokenizer=tok
        self.old=V2Parent(self.root/'parent-evidence',originals,tok)
        self.pilot_plan,self.pilot_binding=authenticate_pilot(self.root,tok,self.old)
        self.origin=self.old.plan
        # Each scientific source scope and legacy validation index is constructed once.
        self.pilot=self.old.source;self.remaining=Source(originals,scope='remaining')
        if self.remaining.execution!=self.pilot.execution:raise ValueError('Pilot/remaining backend identity differs')
        self.legacy,self.provenance=legacy(self.remaining,readouts,tok)
        self.binding=dict(remaining=self.remaining.binding,pilot=self.pilot.binding,
            historical_execution_hash=self.remaining.execution['artifact_hash'],historical_revision=self.remaining.execution['code_revision'],
            technical_hash=self.remaining.technical['artifact_hash'],legacy=self.provenance)
        if any(self.binding[k]!=self.origin['source'][k] for k in self.binding if k!='legacy'):
            raise ValueError('Main originals do not match authenticated v2 source bindings')
        if self.provenance.get('historical_plan_hash')!=self.origin['source']['legacy'].get('historical_plan_hash'):
            raise ValueError('Legacy measurements belong to another historical plan')
        # Keep actual current provenance. Exported summaries never become native journals.
        self.snapshot_files=artifact_files(self.root)


def raw_join_evidence(evidence,readouts):
    """Archive only the 664 required saved values, never another experiment tree."""
    root=Path(readouts);native=evidence.provenance['legacy_provenance_mode']=='native_journals'
    summary=None if native else sealed_read(root/'measurements-v5.json');values={}
    for q in evidence.origin['main']:
        for join in q['legacy'].values():
            key=join['computation_id']
            if native:
                op=sealed_read(root/'operations-v5'/digest('v5/readout/'+key)/'returned.json')
                value=op['result'];provenance=dict(mode='native_journals',operation_hash=op['artifact_hash'])
            else:
                row=summary['results'][key]
                if row['status']!='returned':raise ValueError('Required legacy export return missing')
                value=row['value'];provenance=dict(mode='exported_summary',summary_hash=summary['artifact_hash'])
            if digest(value)!=join['original_value_hash']:raise ValueError('Saved raw legacy value differs from origin join')
            values[key]=dict(task_id=q['task_id'],source_row_hash=q['source_row_hash'],checkpoint=q['checkpoint'],
                original_value_hash=join['original_value_hash'],provenance=provenance,value=value)
    if len(values)!=664:raise ValueError('Exactly 664 unique historical cue values required')
    return values
