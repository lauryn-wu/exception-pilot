"""Judge-only regression tests: mock transports, synthetic originals, blocked network/GPU."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_review import policy as legacy_policy
from exception_study2_v4.review import policy as v4_policy
from exception_study2_v5 import core, interventions
from exception_study2_v5.review.workflow import read_manifest, validate_decisions
from exception_study2_v5_judges import policy, decisions, workflow
from test_study2_v5 import Offline, annotations_for, reviewed, Fake
from test_automated_review import config, FakeClock


def response_for(view):
    """Explicit synthetic reviewer author; never a production semantic detector."""
    source = annotations_for(view)
    return {e: dict(status=d['status'], claim_quote=d['text'],
                    anchor_quote=d['text'], subtype=d['subtype'], rationale=d['rationale'],
                    checks={c:dict(status='pass' if d['status']=='present' or c=='reviewed_all_pre_answer_text' else 'not_applicable',
                                   reason='Synthetic reviewer explicitly checked this criterion against the fixture.')
                            for c in policy.criteria(e)})
            for e in policy.EVENTS[view['family']] for d in [source[e]]}


class Transport:
    kind = 'MOCK'
    def __init__(self, callback=None, clock=None):
        self.calls=[]; self.callback=callback; self.clock=clock
    def __call__(self, provider, request, timeout):
        user=request.get('input', request.get('messages'))[0]['content']
        view=json.loads(user.split('BEGIN_UNTRUSTED_SOURCE_JSON\n')[1].split('\nEND_UNTRUSTED_SOURCE_JSON')[0])
        call=dict(provider=provider, request=request, view=view)
        self.calls.append(call)
        if self.clock:self.clock.advance(2)
        value=response_for(view)
        if self.callback:
            override=self.callback(call, value)
            if override is not None:value=override
        body=(dict(id='fixture',model=request['model'],status='completed',usage=dict(input_tokens=100,output_tokens=200),
                   output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])]) if provider=='openai' else
              dict(id='fixture',model=request['model'],stop_reason='end_turn',usage=dict(input_tokens=100,output_tokens=200),
                   content=[dict(type='text',text=json.dumps(value))]))
        return dict(status=200,body=json.dumps(body),request_id='mock')


def snapshot(path):
    return {str(p.relative_to(path)):hashlib.sha256(p.read_bytes()).hexdigest() for p in path.rglob('*') if p.is_file()}


def small_view(family='O'):
    return dict(family=family, original_available=True, pre_answer_text='The target verified class is A.\nThe target verified class is MISSING.\nThe recorded A conflicts with the peer pattern C.\nTherefore prefer class C over recorded class A.\n')


class DecisionTests(unittest.TestCase):
    def vote(self, family='O', mutate=None):
        view=small_view(family); value=response_for(view)
        if mutate:mutate(value)
        return decisions.validate_vote(family,value,view)
    def test_distinct_frozen_family_prompts_and_schema(self):
        self.assertNotEqual(policy.PROMPTS['M'],policy.PROMPTS['O'])
        self.assertIn('table_unknown',policy.PROMPTS['M'])
        self.assertIn('PRIOR',policy.PROMPTS['O'])
        self.assertEqual(set(policy.SCHEMAS['M']['properties']),{'erasure','miscopy'})
        self.assertEqual(set(policy.SCHEMAS['O']['properties']),{'acknowledgment','conflict','override'})
        self.assertEqual(v4_policy.RUBRICS,legacy_policy.RUBRICS)
        self.assertNotEqual(policy.PROMPTS['O'],v4_policy.DETECTION)
    def test_json_validity_never_certifies_semantics(self):
        for rating in ('fail','uncertain','not_applicable'):
            with self.subTest(rating=rating):
                r=self.vote(mutate=lambda v:v['override']['checks']['explicit_preference_over_recorded_value'].update(status=rating))
                self.assertTrue(r['schema_valid']);self.assertEqual(r['events']['override']['status'],'uncertain')
                self.assertEqual(r['events']['override']['certificates'],{})
        r=self.vote(mutate=lambda v:v['override'].update(checks={}))
        self.assertFalse(r['schema_valid']);self.assertEqual(r['events']['override']['status'],'invalid')
    def test_negatives_require_complete_review(self):
        r=self.vote('M',lambda v:v['miscopy']['checks']['reviewed_all_pre_answer_text'].update(status='uncertain'))
        self.assertEqual(r['events']['miscopy']['status'],'uncertain')
    def test_override_needs_prior_acknowledgment_not_conflict_alone(self):
        def change(v):
            v['acknowledgment'].update(status='absent',claim_quote=None,anchor_quote=None,subtype=None)
        r=self.vote(mutate=change)
        self.assertEqual(r['events']['override']['status'],'uncertain')
        self.assertEqual(r['events']['conflict']['status'],'present')
    def test_unicode_alignment_and_duplicate_quotes(self):
        view=small_view('M');view['pre_answer_text']='é 🚘 '+view['pre_answer_text']
        value=response_for(view);r=decisions.validate_vote('M',value,view)
        d=r['events']['erasure'];self.assertEqual(view['pre_answer_text'][slice(*d['span'])],d['text'])
        self.assertNotEqual(d['span'][0],len(view['pre_answer_text'][:d['span'][0]].encode()))
        view['pre_answer_text']+=d['text']
        self.assertEqual(decisions.validate_vote('M',value,view)['events']['erasure']['status'],'invalid')
    def test_table_unknown_and_miscopy_are_distinct(self):
        view=dict(original_available=True,pre_answer_text='| target | Verified class |\n| T | ? |\n')
        value=response_for(small_view('M'))
        value['erasure'].update(claim_quote='?',anchor_quote='| T | ? |',subtype='table_unknown')
        r=decisions.validate_vote('M',value,view)
        self.assertEqual(r['events']['erasure']['subtype'],'table_unknown')
        self.assertEqual(r['events']['miscopy']['status'],'absent')
    def test_blank_verified_cell_retains_exact_source_whitespace(self):
        view=dict(original_available=True,pre_answer_text='| T |   |')
        value=response_for(small_view('M'))
        value['erasure'].update(claim_quote='   ',anchor_quote='| T |   |',subtype='table_unknown')
        r=decisions.validate_vote('M',value,view)
        self.assertTrue(r['schema_valid']);self.assertEqual(r['events']['erasure']['text'],'   ')
        self.assertEqual(r['events']['erasure']['span'],[5,8])
        value['erasure']['rationale']=' '
        self.assertFalse(decisions.validate_vote('M',value,view)['schema_valid'])
    def test_excluded_distinct_from_absent_uncertain_and_invalid(self):
        for status in ('excluded','absent','uncertain','invalid'):
            def change(v):
                v['erasure'].update(status=status,claim_quote=None,anchor_quote=None,subtype=None)
            r=self.vote('M',change)
            self.assertEqual(r['events']['erasure']['status'],status)
            self.assertEqual(decisions.resolve('M',dict(J1=r,J2=r))['needs_j3'],status in ('uncertain','invalid'))
    def test_agreement_disagreement_and_conditional_adjudication(self):
        a=self.vote('M');b=copy.deepcopy(a)
        self.assertEqual(decisions.resolve('M',dict(J1=a,J2=b))['state'],'TERMINAL')
        b['events']['erasure']=decisions.nonpresent('absent','Independent negative')
        pending=decisions.resolve('M',dict(J1=a,J2=b))
        self.assertTrue(pending['needs_j3']);self.assertEqual(pending['state'],'PENDING')
        done=decisions.resolve('M',dict(J1=a,J2=b,J3=a))
        self.assertEqual(done['pairs']['erasure'],['J1','J3']);self.assertEqual(done['events']['erasure']['status'],'present')
    def test_uncertain_invalid_never_become_negative_or_majority_acceptance(self):
        for status in ('uncertain','invalid'):
            a=self.vote('M');a['events']['erasure']=decisions.nonpresent(status,'Insufficient evidence')
            self.assertTrue(decisions.resolve('M',dict(J1=a,J2=a))['needs_j3'])
            r=decisions.resolve('M',dict(J1=a,J2=a,J3=a))
            self.assertEqual(r['state'],'TERMINAL');self.assertEqual(r['events']['erasure']['status'],status)
            self.assertIsNone(r['pairs']['erasure'])
    def test_schema_error_nonpresent_quotes_and_unavailable(self):
        view=small_view('M');v=response_for(view);v['miscopy']['claim_quote']='invented'
        self.assertEqual(decisions.validate_vote('M',v,view)['events']['miscopy']['status'],'invalid')
        v=response_for(view);v['erasure']['checks']['first_eligible_occurrence']['status']=True
        self.assertFalse(decisions.validate_vote('M',v,view)['schema_valid'])
        view['original_available']=False
        self.assertTrue(all(d['status']=='invalid' for d in decisions.validate_vote('M',response_for(view),view)['events'].values()))
    def test_live_policy_preserves_configured_models_without_substitution(self):
        cfg=config();cfg['live_enabled']=True
        for j in cfg['judges'].values():j.update(contract_verified=True,access_verified=True)
        cfg['judges']['J3']=copy.deepcopy(cfg['judges']['J1'])
        frozen=policy.freeze_policy(cfg)
        self.assertEqual(frozen['config'],cfg)
        self.assertEqual(frozen['config']['judges']['J3']['model'],cfg['judges']['J1']['model'])


class WorkflowTests(Offline):
    def setup_review(self, cfg=None):
        src,b=self.run_source();out=self.root/'judges'
        plan=workflow.prepare(src,out,cfg or config())
        return src,b,out,plan
    def test_preserved_science_row_index_population_and_offline_default(self):
        self.assertEqual(core.source_hash(),'e545f0a756934f0d5c953db3a1c102146a1616dc2706913cb3537e8a5a6a2c2b')
        src,b,out,p=self.setup_review();before=snapshot(src);calls=len(b.calls)
        self.assertEqual(len(p['case_ids']),16);self.assertEqual(p['initial_request_ceiling'],64);self.assertEqual(p['total_request_ceiling'],96)
        for f in ('M','O'):
            for view in p['views'][f].values():
                target=view['target'];self.assertEqual(target['target_row_position'],9)
                self.assertEqual(target['target_row_index_base'],0);self.assertEqual(target['target_row_number_one_based'],10)
                self.assertEqual(target['table_line_index_zero_based'],11)
                self.assertNotIn('score',view);self.assertNotIn('ANSWER:',view['pre_answer_text'])
        result=workflow.run(out)
        self.assertEqual(result['attempted'],0);self.assertEqual(result['stop_reason'],'OFFLINE')
        self.assertEqual(snapshot(src),before);self.assertEqual(len(b.calls),calls)
        with self.assertRaisesRegex(ValueError,'incomplete'):workflow.export(out)
    def test_row_index_all_worlds_and_mismatch(self):
        plan=core.make_plan()
        worlds={w['id']:w for w in plan['worlds']}
        for t in plan['tasks']:
            meta=workflow.target_metadata(t);w=worlds[t['world']]
            self.assertEqual(w['order'][meta['target_row_position']],w['target'])
            self.assertEqual(w['items'][w['target']]['id'],meta['plate'])
        bad=dict(plan['tasks'][0],target_row_position=8)
        with self.assertRaises(ValueError):workflow.target_metadata(bad)
    def test_independent_journals_export_manual_edits_and_no_source_mutations(self):
        src,b,out,p=self.setup_review();before=snapshot(src);transport=Transport()
        metrics=workflow.run(out,transport=transport)
        self.assertEqual(metrics['attempted'],64);self.assertEqual(len(transport.calls),64)
        self.assertEqual({c['request']['model'] for c in transport.calls},{'fixture-J1','fixture-J2'})
        for f in ('M','O'):
            seen=[c for c in transport.calls if c['view']['family']==f]
            self.assertEqual(seen[0]['view'],seen[1]['view'])
            system=seen[0]['request'].get('instructions',seen[0]['request'].get('system'))
            self.assertEqual(system,policy.UNTRUSTED+'\n'+policy.PROMPTS[f])
            self.assertFalse(set(seen[0]['view']) & {'votes','final_answer','correct','readouts','interventions'})
        manifest=workflow.export(out);self.assertEqual(len(manifest['cases']),16)
        self.assertEqual(read_manifest(out/'annotation-manifest-v5.json')['artifact_hash'],manifest['artifact_hash'])
        self.assertEqual(len(list((out/'judge-operations').glob('*/returned.json'))),64)
        self.assertTrue(all('intervention' not in d for c in manifest['cases'].values() for d in c['events'].values()))
        prep=interventions.prepare_edits(src,out/'annotation-manifest-v5.json',self.root/'M','M')
        self.assertTrue(prep['cases'])
        with self.assertRaises((ValueError,FileNotFoundError,KeyError)):
            interventions.freeze_edits(self.root/'M',self.root/'M'/'draft-template.json',self.root/'M'/'verification-template.json',backend_override=b)
        manual=reviewed(src,self.root/'manual');self.assertEqual(len(read_manifest(manual)['cases']),16)
        workflow.run(out,transport=transport);workflow.export(out)
        self.assertEqual(len(transport.calls),64);self.assertEqual(snapshot(src),before)
    def test_j3_only_on_disputed_family_and_no_peer_votes(self):
        src,b,out,p=self.setup_review();tid=p['case_ids'][0]
        def change(call,v):
            if call['request']['model']=='fixture-J2' and call['view']['task_id']==tid and call['view']['family']=='M':
                v['erasure'].update(status='uncertain',claim_quote=None,anchor_quote=None,subtype=None)
        t=Transport(change)
        self.assertEqual(workflow.run(out,transport=t,stage='initial')['attempted'],64)
        with self.assertRaisesRegex(ValueError,'incomplete'):workflow.export(out)
        workflow.run(out,transport=t)
        j3=[c for c in t.calls if c['request']['model']=='fixture-J3']
        self.assertEqual(len(t.calls),65);self.assertEqual(len(j3),1)
        self.assertEqual(j3[0]['view'],next(c['view'] for c in t.calls if c['view']['task_id']==tid and c['view']['family']=='M'))
        m=workflow.export(out);r=m['reviews'][tid]['M'];self.assertEqual(r['pairs']['erasure'],['J1','J3'])
    def test_aggregate_request_budget_resume_across_families(self):
        cfg=config();cfg['limits']['max_calls']=33
        src,b,out,p=self.setup_review(cfg);t=Transport()
        r=workflow.run(out,transport=t,max_calls=10)
        self.assertEqual(r['attempted'],10);self.assertEqual(r['stop_reason'],'REQUEST_BUDGET')
        r=workflow.run(out,transport=t)
        self.assertEqual(r['attempted'],23);self.assertEqual(len(t.calls),33)
        self.assertEqual({c['view']['family'] for c in t.calls},{'M','O'})
        self.assertEqual(workflow.run(out,transport=t)['attempted'],0)
        with self.assertRaisesRegex(ValueError,'incomplete'):workflow.export(out)
    def test_spend_and_wall_limits(self):
        cfg=config();cfg['limits']['max_estimated_usd']=0.000001
        src,b,out,p=self.setup_review(cfg);t=Transport()
        r=workflow.run(out,transport=t);self.assertEqual(r['stop_reason'],'ESTIMATED_SPEND_BUDGET');self.assertEqual(t.calls,[])
        other=self.root/'time';workflow.prepare(src,other,config())
        clock=FakeClock();t=Transport(clock=clock)
        r=workflow.run(other,transport=t,clock=clock,wall_seconds=1)
        self.assertEqual(len(t.calls),1);self.assertEqual(r['stop_reason'],'WALL_SCHEDULING_LIMIT')
    def test_ambiguous_interruption_never_resends(self):
        src,b,out,p=self.setup_review();t=Transport()
        workflow.run(out,transport=t,max_calls=1)
        returned=next((out/'judge-operations').glob('*/returned.json'))
        returned.unlink()  # fixture: emulate death after started, before persisted terminal/vote
        first=p['case_ids'][0];workflow.Review(out).path('M',first,'J1').unlink()
        workflow.run(out,transport=t)
        firstcalls=[c for c in t.calls if c['view']['task_id']==first and c['view']['family']=='M' and c['request']['model']=='fixture-J1']
        self.assertEqual(len(firstcalls),1)
        failed=sealed_read(returned.parent/'failed.json')
        self.assertEqual(failed['error']['type'],'AmbiguousInterruptedOperation')
        m=workflow.export(out);self.assertEqual(m['reviews'][first]['M']['pairs']['miscopy'],['J2','J3'])
    def test_malformed_and_provider_failures_remain_journaled(self):
        src,b,out,p=self.setup_review();tid=p['case_ids'][0]
        def change(c,v):
            if c['view']['task_id']==tid and c['view']['family']=='M':return {'valid_json_is_not_semantics':True}
        t=Transport(change);workflow.run(out,transport=t);m=workflow.export(out)
        self.assertEqual(m['cases'][tid]['events']['erasure']['status'],'invalid')
        self.assertEqual(len([c for c in t.calls if c['request']['model']=='fixture-J3']),1)
        self.assertTrue(all(not m['reviews'][tid]['M']['votes'][j]['schema_valid'] for j in ('J1','J2','J3')))
    def test_unavailable_originals_are_invalid_without_paid_attempts(self):
        from exception_study2_v5 import runner
        src=self.root/'failed-originals';core.prepare(src);b=Fake()
        runner.technical(src,backend_override=b);b.fail_generation=True
        runner.collect(src,backend_override=b)
        out=self.root/'failed-judges';workflow.prepare(src,out,config());t=Transport()
        r=workflow.run(out,transport=t);m=workflow.export(out)
        self.assertEqual(r['attempted'],0);self.assertEqual(t.calls,[])
        self.assertTrue(all(d['status']=='invalid' for c in m['cases'].values() for d in c['events'].values()))
    def test_provider_exception_is_terminal_and_never_retried(self):
        src,b,out,p=self.setup_review();tid=p['case_ids'][0]
        def change(c,v):
            if c['request']['model']=='fixture-J1' and c['view']['task_id']==tid and c['view']['family']=='O':
                raise TimeoutError('Synthetic timeout')
        t=Transport(change);workflow.run(out,transport=t);workflow.export(out)
        count=len(t.calls);workflow.run(out,transport=t)
        self.assertEqual(len(t.calls),count)
        failures=[sealed_read(q) for q in (out/'judge-operations').glob('*/failed.json')]
        self.assertEqual(len(failures),1);self.assertEqual(failures[0]['error']['type'],'TimeoutError')
    def test_returned_model_mismatch_is_invalid_and_not_a_semantic_pass(self):
        src,b,out,p=self.setup_review()
        class WrongModel(Transport):
            def __call__(self,provider,request,timeout):
                r=super().__call__(provider,request,timeout)
                body=json.loads(r['body']);body['model']='unexpected-model';r['body']=json.dumps(body);return r
        t=WrongModel();workflow.run(out,transport=t);m=workflow.export(out)
        self.assertEqual(len(t.calls),96)
        self.assertTrue(all(d['status']=='invalid' for c in m['cases'].values() for d in c['events'].values()))
        self.assertTrue(all(sealed_read(q)['parsed']['reason']=='returned_model_identity_mismatch' for q in (out/'judge-operations').glob('*/returned.json')))
    def test_policy_source_tampering_and_output_overlap_fail_safely(self):
        src,b,out,p=self.setup_review()
        with self.assertRaises(ValueError):workflow.prepare(src,src/'judges',config())
        with patch.object(policy,'PROMPTS',dict(policy.PROMPTS,M='changed')):
            with self.assertRaisesRegex(ValueError,'changed'):workflow.Review(out)
        saved=sealed_read(out/'judge-plan-v5.json');saved['views']['M'][p['case_ids'][0]]['pre_answer_text']='tampered'
        from exception_continuation.runner import sealed_write
        sealed_write(out/'judge-plan-v5.json',saved)
        with self.assertRaisesRegex(ValueError,'identity'):workflow.Review(out)
    def test_shared_journal_source_reused_without_global_mutation(self):
        from exception_study2_v5_judges.family_m import journal as m
        from exception_study2_v5_judges.family_o import journal as o
        from exception_review import journal as legacy
        self.assertEqual(Path(m.__file__),Path(legacy.__file__))
        self.assertEqual(Path(o.__file__),Path(legacy.__file__))
        self.assertNotEqual(m.RUBRICS['detect'],o.RUBRICS['detect'])
        self.assertEqual(legacy.RUBRICS,legacy_policy.RUBRICS)
    def test_live_disabled_and_mock_sources_cannot_trigger_paid_requests(self):
        src,b,out,p=self.setup_review()
        with self.assertRaisesRegex(ValueError,'real-model'):workflow.run(out,live=True,transport=Transport())
        from exception_review.providers import HTTPTransport
        with self.assertRaises(ValueError):workflow.run(out,transport=HTTPTransport())
        self.assertFalse(list((out/'judge-operations').glob('*/started.json')))


if __name__ == '__main__':unittest.main()
