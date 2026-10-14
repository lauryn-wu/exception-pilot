"""Opt-in constructed-fixture evaluation, separate from natural cohorts/timing."""
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from exception_pilot.core import digest
from exception_pilot.storage import run_lock
from exception_continuation.runner import sealed_read
from .artifacts import freeze
from .policy import freeze_policy, ARMS, CRITERIA, VERIFY_SCHEMA, schema_check
from .journal import Journal
from .fixtures import fixtures, edit_fixtures
from .decisions import validate_vote
from .editing import verify_bundle
from .reporting import write_report, stats


def evaluation_report(out, policy, examples, journal, stage):
    by_slot = {(e['identity']['task_id'],e['identity']['judge']):e for e in journal.entries()}
    rows = []; models = {}
    categories=('planned','attempted','returned','assessed','unavailable','pending','refused','malformed','unusable','false_approvals','false_rejections','uncertain')
    for judge, cfg in policy['config']['judges'].items():
        models[judge] = dict(provider=cfg['provider'], model=cfg['model'], planned=len(examples),
                            bundle_counts=Counter({k:0 for k in categories}), criteria={a:{c:Counter({k:0 for k in (*categories,'expected_pass','expected_fail','pass','fail','correct')}) for c in CRITERIA} for a in ARMS})
    for example in examples:
        for judge in ('J1','J2','J3'):
            entry = by_slot.get((example['id'],judge)); parsed = (entry or {}).get('parsed',{})
            state = (entry or {}).get('state','pending'); terminal = state in ('returned','failed')
            row = dict(fixture=example['id'], judge=judge, provider=models[judge]['provider'],
                       model=models[judge]['model'], operation_key=(entry or {}).get('key'), state=state,
                       usage=parsed.get('usage'), accounting=(entry or {}).get('accounting'),
                       provider_seconds=(entry or {}).get('provider_seconds'), correct=False)
            if stage == 'detection':
                vote = validate_vote(parsed.get('value'),example['input']['detection_view'],
                                     example['trajectory_hash'],(entry or {}).get('identity',{}).get('trajectory_hash'),
                                     parsed.get('valid',False),parsed.get('reason','pending'))
                expected = 'POS' if example['expected_decision']=='present' else 'NEG'
                row.update(vote=vote,expected_decision=example['expected_decision'],expected_span=example['expected_span'],
                           correct=terminal and vote['effective_vote']==expected and vote['span']==example['expected_span'])
            else:
                category = 'unavailable' if state=='failed' else 'pending'
                reason = parsed.get('reason'); value = parsed.get('value'); usable = False
                if state == 'returned':
                    category = 'refused' if 'refus' in (reason or '') else 'malformed' if reason=='malformed_response' or parsed.get('valid') else 'unusable'
                    if parsed.get('valid'):
                        try: schema_check(value,VERIFY_SCHEMA); usable=True; category='assessed'
                        except (ValueError,TypeError,KeyError): reason='invalid_verifier_schema'
                approved = verify_bundle(value)['passed'] if usable else None
                expected_approval = example['expected_approval']
                bundle = models[judge]['bundle_counts']; bundle['planned']+=1
                bundle['attempted']+=state not in ('pending','planned'); bundle['returned']+=state=='returned'
                bundle[category]+=1
                bundle['false_approvals']+=approved is True and not expected_approval
                bundle['false_rejections']+=usable and expected_approval and (value['source_assertion_concern'] is not None or any(value['replacements'][a][c]['status']=='fail' for a in ARMS for c in CRITERIA))
                bundle['uncertain']+=usable and any(value['replacements'][a][c]['status']=='uncertain' for a in ARMS for c in CRITERIA)
                matches = []
                for arm in ARMS:
                    for criterion in CRITERIA:
                        counts=models[judge]['criteria'][arm][criterion]; expected=example['expected_criteria'][arm][criterion]
                        actual=value['replacements'][arm][criterion]['status'] if usable else None
                        counts['planned']+=1; counts['expected_'+expected]+=1; counts[category]+=1
                        counts['attempted']+=state not in ('pending','planned'); counts['returned']+=state=='returned'
                        for key in ('pass','fail','uncertain'): counts[key]+=actual==key
                        counts['false_approvals']+=expected=='fail' and actual=='pass'
                        counts['false_rejections']+=expected=='pass' and actual=='fail'
                        counts['correct']+=actual==expected
                        matches.append(actual==expected)
                row.update(category=category,reason=reason,response=value,expected_criteria=example['expected_criteria'],
                           expected_approval=expected_approval,approved=approved,label_basis=example['label_basis'],
                           correct=usable and all(matches) and (value['source_assertion_concern'] is not None)==example['expected_source_assertion_concern'])
            rows.append(row)
    attempted=[e for e in by_slot.values() if e['state']!='planned']; groups=defaultdict(list)
    for entry in attempted:
        key='/'.join([entry['identity']['judge_config']['provider'],str(entry['identity']['judge_config']['model']),entry['measurement']])
        groups[key]
        if entry.get('provider_seconds') is not None: groups[key].append(entry['provider_seconds'])
    invocations=[sealed_read(p) for p in (out/'invocations').glob('*.json')]
    terminal=sum(r['state'] in ('returned','failed') for r in rows)
    # Provider-native usage is retained above. Anthropic input excludes cache reads/writes.
    total_input=sum((e.get('accounting',{}).get('input_tokens') or 0) +
                    (sum(e.get('accounting',{}).get(k) or 0 for k in ('cached_input_tokens','cache_write_input_tokens')) if e['identity']['judge_config']['provider']=='anthropic' else 0) for e in attempted)
    timing=dict(by_operation_model_measurement={k:stats(v) for k,v in groups.items()},
                cumulative=dict(attempted=len(attempted),returned=sum(e['state']=='returned' for e in attempted),
                                cache_hits=sum(i['cached'] for i in invocations),input_tokens=total_input,
                                output_tokens=sum(e.get('accounting',{}).get('output_tokens') or 0 for e in attempted),
                                known_usage_estimated_usd=sum(e.get('accounting',{}).get('estimated_usd') or 0 for e in attempted),
                                usage_unavailable=sum(e.get('accounting',{}).get('estimated_usd') is None for e in attempted)),
                this_invocation=journal.metrics,invocations=invocations,
                note='All completed attempt latencies, including refusals/errors; constructed fixtures only. Costs use frozen rates, not invoices.')
    return write_report(out/'semantic-evaluation-report',dict(
        status='COMPLETE' if terminal==len(rows) else 'INCOMPLETE', stage=stage,
        measurement=journal.metrics['measurement'], expected=len(rows), terminal=terminal,
        returned=sum(r['state']=='returned' for r in rows), correct=sum(r['correct'] for r in rows),
        rows=rows,per_model=models if stage=='edits' else None,timing=timing,
        quality_claim='Constructed-fixture evaluation only; no natural-trajectory accuracy established',
        timing_separate_from_natural_trajectories=True),'Fixed semantic-fixture evaluation')


def evaluate(output,config,live=False,transport=None,max_calls=None,clock=None,wall_seconds=None,stage='detection'):
    if stage not in ('detection','edits'): raise ValueError('Unknown semantic-evaluation stage')
    out=Path(output); examples=fixtures() if stage=='detection' else edit_fixtures()
    policy=freeze_policy(config); fixture_hash=digest(examples)
    class FixtureSource:
        def case_binding(self,tid):
            case=next(c for c in examples if c['id']==tid)
            return dict(source_hash=fixture_hash,task_id=tid,trajectory_hash=case['trajectory_hash'],view_hash=digest(case['input']))
    with run_lock(out/'locks'):
        review=SimpleNamespace(root=out,policy=policy,source=FixtureSource())
        journal=Journal(review,live=live,transport=transport,max_calls=max_calls,wall_seconds=wall_seconds,clock=clock)
        freeze(out/'semantic-evaluation-plan.json',dict(policy=policy,stage=stage,fixtures=examples,fixture_hash=fixture_hash,maximum_calls=3*len(examples),natural_trajectory_estimates=False))
        try:
            for example in examples:
                for judge in ('J1','J2','J3'):
                    role='verify' if stage=='edits' else 'initial' if judge!='J3' else 'adjudicate'
                    entry=journal.call(example['id'],judge,role,0,example['input'])
                    if entry is None: break
                if journal.metrics['stop_reason']: break
        finally:
            journal.finish('semantic-evaluation-'+stage,'CONSTRUCTED_FIXTURES_ONLY')
            result=evaluation_report(out,policy,examples,journal,stage)
        return result
