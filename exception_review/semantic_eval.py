"""Explicit live semantic evaluation; constructed examples never inform natural timing."""
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from .artifacts import freeze
from .policy import freeze_policy
from .journal import Journal
from .fixtures import fixtures
from .decisions import validate_vote
from .reporting import write_report


def evaluate(output,config,live=False,transport=None,max_calls=None,clock=None):
    out=Path(output); examples=fixtures(); policy=freeze_policy(config); fixture_hash=digest(examples)
    class FixtureSource:
        def case_binding(self,tid):
            case=next(c for c in examples if c['id']==tid)
            return dict(source_hash=fixture_hash,task_id=tid,trajectory_hash=case['trajectory_hash'],view_hash=digest(case['input']))
    with run_lock(out/'locks'):
        freeze(out/'semantic-evaluation-plan.json',dict(policy=policy,fixtures=examples,fixture_hash=fixture_hash,maximum_calls=3*len(examples),natural_trajectory_estimates=False))
        review=SimpleNamespace(root=out,policy=policy,source=FixtureSource())
        journal=Journal(review,live,transport,max_calls,clock=clock); rows=[]
        try:
            for example in examples:
                for judge in ('J1','J2','J3'):
                    entry=journal.call(example['id'],judge,'initial' if judge!='J3' else 'adjudicate',0,example['input'])
                    if entry is None: break
                    parsed=entry['parsed']; vote=validate_vote(parsed.get('value'),example['input']['detection_view'],example['trajectory_hash'],entry['identity']['trajectory_hash'],parsed['valid'],parsed.get('reason'))
                    expected_vote='POS' if example['expected_decision']=='present' else 'NEG'
                    correct=vote['effective_vote']==expected_vote and vote['span']==example['expected_span']
                    rows.append(dict(fixture=example['id'],judge=judge,operation_key=entry['key'],vote=vote,expected_decision=example['expected_decision'],expected_span=example['expected_span'],correct=correct))
                if journal.metrics['stop_reason']: break
        finally: journal.finish('semantic-evaluation','CONSTRUCTED_FIXTURES_ONLY')
        return write_report(out/'semantic-evaluation-report',dict(status='COMPLETE' if len(rows)==3*len(examples) else 'INCOMPLETE',measurement='LIVE' if live else 'MOCK' if transport else 'OFFLINE',expected=3*len(examples),returned=len(rows),correct=sum(r['correct'] for r in rows),rows=rows,quality_claim='Constructed-fixture evaluation only; no natural-trajectory accuracy established',timing_separate_from_natural_trajectories=True),'Fixed semantic-fixture evaluation')
