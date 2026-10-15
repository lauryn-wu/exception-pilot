"""All semantic responses mocked; network and model construction blocked."""
import copy
import hashlib
import json
import math
import socket
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_review.artifacts import freeze
from exception_study2_v5.review.workflow import read_manifest,validate_decisions
from exception_study2_v5.core import source_hash
from exception_study2_v5 import interventions
from exception_study2_v5_judges.workflow import target_metadata
from exception_study2_v5_review_v2 import policy, candidates, decisions, workflow, controlled
from exception_study2_v5_review_v2.providers import payload,parse_response,HTTPTransport
from test_study2_v5 import Offline,annotations_for
from test_automated_review import config,FakeClock

def cfg():
    c=config();c['limits']['wall_seconds']=120;c['limits']['max_calls']=128
    return c

def small(text="T's recorded Verified class is MISSING."):
    return candidates.packet(dict(original_available=True,pre_answer_text=text,
        target=dict(plate='T',verified_class='C'),plates=['T','U'],source_prompt='Authoritative source: T=C'))

def extraction_value(p, refs=()):
    return dict(candidates=[dict(statement_id=sid,event=e,reason='Explicit test candidate.') for sid,e in refs],
                reviewed_all=controlled.rating(),coverage={e:controlled.rating() for e in policy.EVENTS},corrections=[])

def cs_for(p):return candidates.merge(p,[('structural',candidates.structural_candidates(p))])
def synthetic_case(p):
    # Only the author-defined Fake fixture language. Never used by production.
    original=annotations_for(p);names={v:k for k,v in policy.LEGACY.items()}
    labels={s['id']:[names[e] for e,d in original.items() if d['status']=='present' and d['span']==s['span']] for s in p['statements']}
    return dict(packet=p,statement_truth=labels)

def wire_response(provider, request, value):
    body=(dict(id='mock',model=request['model'],status='completed',usage=dict(input_tokens=100,output_tokens=200),
          output=[dict(type='message',content=[dict(type='output_text',text=json.dumps(value))])]) if provider=='openai' else
          dict(id='mock',model=request['model'],stop_reason='end_turn',usage=dict(input_tokens=100,output_tokens=200),
               content=[dict(type='text',text=json.dumps(value))]))
    return dict(status=200,body=json.dumps(body),request_id='mock-only')

class Transport:
    kind='MOCK'
    def __init__(self,change=None,clock=None):self.calls=[];self.change=change;self.clock=clock
    def __call__(self,provider,request,timeout):
        user=request.get('input',request.get('messages'))[0]['content']
        p=json.loads(user.split('BEGIN_UNTRUSTED_SOURCE_JSON\n')[1].split('\nEND_UNTRUSTED_SOURCE_JSON')[0])
        c=synthetic_case(p)
        value=controlled.oracle_vote(c,p['candidates']) if 'candidates' in p else controlled.oracle_extract(c)
        call=dict(provider=provider,request=request,view=p,timeout=timeout);self.calls.append(call)
        if self.clock:self.clock.advance(2)
        if self.change:
            changed=self.change(call,value)
            if changed is not None:value=changed
        return wire_response(provider,request,value)

def snapshot(root):return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

class ExtractionTests(unittest.TestCase):
    def test_unicode_offsets_and_repeated_locations(self):
        p=small('é 🚘 T: Verified class: MISSING\nT: Verified class: MISSING')
        self.assertEqual(len(p['statements']),2);self.assertNotEqual(*[s['id'] for s in p['statements']])
        for s in p['statements']:self.assertEqual(p['pre_answer_text'][slice(*s['span'])],s['text'])
    def test_prompt_table_never_becomes_candidate(self):
        p=small('Nothing to report.')
        p['source_prompt']='T Verified class: MISSING'
        self.assertEqual(cs_for(p),[])
    def test_merge_same_event_location_retains_provenance(self):
        p=small();s=p['statements'][0]['id'];ref=dict(statement_id=s,event='M',reason='Reason')
        cs=candidates.merge(p,[('one',[ref]),('two',[ref])])
        self.assertEqual(len(cs),1);self.assertEqual(len(cs[0]['provenance']),2)
    def test_target_field_and_source_value_comparison(self):
        p=small('### T\n- **Verified class**: MISSING\nU: Verified class: A\nT Doors: MISSING')
        facts=list(p['reference_facts'].values())
        self.assertEqual(facts[1]['target'],'yes');self.assertEqual(facts[1]['comparison'],'missing')
        self.assertEqual(facts[2]['target'],'no');self.assertEqual(facts[2]['comparison'],'differs')
        self.assertEqual(facts[3]['field'],'other')
    def test_table_column_order_and_blank_cell(self):
        p=small('| Verified class | Plate |\n|---|---|\n|   | T |\n| A | U |')
        f=list(p['reference_facts'].values())[2]
        self.assertEqual(f['comparison'],'missing');self.assertEqual(f['target'],'yes')
        self.assertEqual(p['pre_answer_text'][slice(*f['value_span'])],'   ')
    def test_negation_hypothesis_are_candidates_not_labels(self):
        for t in ["T's Verified class is not missing.","If T's recorded class were missing, infer A.",'The draft claims "T: Verified class: MISSING", falsely.']:
            p=small(t);self.assertTrue(any(c['event']=='M' for c in cs_for(p)))
            self.assertNotIn('status',cs_for(p)[0])
    def test_exact_prediction_role_does_not_become_acknowledgment(self):
        p=small('I predict C for T.');ref=dict(statement_id=p['statements'][0]['id'],event='A',reason='test')
        c=candidates.merge(p,[('test',[ref])])[0];self.assertIn('prediction',candidates.veto(c)[0])
    def test_enumeration_is_not_miscopy_fact(self):
        p=small('T: Verified class: A, B, or C (or MISSING).')
        self.assertEqual(next(iter(p['reference_facts'].values()))['comparison'],'unknown')
    def test_unknown_candidate_or_correction_id_invalid(self):
        p=small();v=extraction_value(p,[('invented','M')])
        self.assertFalse(candidates.extraction(v,p)['valid'])
        v=extraction_value(p);v['corrections']=[dict(statement_id='invented',corrects_statement_id='invented',reason='test')]
        self.assertFalse(candidates.extraction(v,p)['valid'])
    def test_correction_order_checked(self):
        p=small("T's recorded Verified class is MISSING.\nCorrection: T's recorded class is C.")
        s=p['statements'];v=extraction_value(p)
        v['corrections']=[dict(statement_id=s[1]['id'],corrects_statement_id=s[0]['id'],reason='test')]
        self.assertTrue(candidates.extraction(v,p)['valid'])
        v['corrections'][0].update(statement_id=s[0]['id'],corrects_statement_id=s[1]['id'])
        self.assertFalse(candidates.extraction(v,p)['valid'])

class DecisionTests(unittest.TestCase):
    def setup_case(self,index=1):
        c=controlled.generate()[index*3];p=c['packet'];ex=candidates.extraction(controlled.oracle_extract(c),p)
        cs=candidates.merge(p,[('oracle',ex['candidates'])]);return c,p,cs,ex
    def test_nonnull_schema_both_provider_requests(self):
        p=small();c=cfg()
        for name in ('J1','J2'):
            req=payload(c['judges'][name],policy.RUBRICS['detect'],policy.SCHEMAS['detect'],p)
            schema=req.get('text',{}).get('format',req.get('output_config',{}).get('format'))['schema']
            self.assertEqual(schema,policy.SCHEMAS['detect']);self.assertNotIn('null',json.dumps(schema))
            self.assertNotIn('tools',req);self.assertFalse(req['stream'])
    def test_required_fields_enum_and_unknown_ids(self):
        c,p,cs,ex=self.setup_case();raw=controlled.oracle_vote(c,cs)
        for mutate in [lambda x:x.pop('reviewed_all'),lambda x:x['decisions'][0].update(status='maybe'),lambda x:x['decisions'][0].update(candidate_id='invented')]:
            v=copy.deepcopy(raw);mutate(v);self.assertFalse(decisions.vote(v,p,cs)['valid'])
    def test_valid_json_does_not_certify_checks(self):
        c,p,cs,ex=self.setup_case();raw=controlled.oracle_vote(c,cs)
        for status in ('fail','uncertain','not_applicable'):
            v=copy.deepcopy(raw);v['decisions'][0]['checks']['asserted']['status']=status
            result=decisions.vote(v,p,cs);self.assertEqual(result['decisions'][cs[0]['id']]['status'],'uncertain')
    def test_absent_requires_failed_check_and_no_invented_ack(self):
        c,p,cs,ex=self.setup_case();v=controlled.oracle_vote(c,cs);d=v['decisions'][0];d['status']='absent'
        self.assertEqual(decisions.vote(v,p,cs)['decisions'][cs[0]['id']]['status'],'uncertain')
        d['checks']['event_definition']=controlled.rating('fail');d['prior_ack_id']='made-up'
        self.assertEqual(decisions.vote(v,p,cs)['decisions'][cs[0]['id']]['status'],'uncertain')
    def test_mechanical_contradiction_cannot_be_outvoted(self):
        p=small('T: Verified class: C');s=p['statements'][0]['id']
        c=dict(packet=p,statement_truth={s:['M']});cs=candidates.merge(p,[('test',[dict(statement_id=s,event='M',reason='bad positive')])])
        v=decisions.vote(controlled.oracle_vote(c,cs),p,cs);r=decisions.reconcile(cs,dict(J1=v,J2=v,J3=v))
        self.assertEqual(r['candidates'][cs[0]['id']]['status'],'uncertain')
        self.assertTrue(r['candidates'][cs[0]['id']]['mechanical_veto'])
    def test_negative_cannot_deny_affirmed_false_reconstruction(self):
        c,p,cs,ex=self.setup_case();raw=controlled.oracle_vote(c,cs)
        raw['decisions'][0]['status']='absent'
        raw['decisions'][0]['checks']['event_definition']=controlled.rating('fail')
        v=decisions.vote(raw,p,cs)
        self.assertEqual(v['decisions'][cs[0]['id']]['status'],'uncertain')
        self.assertIn('Negative contradicts',v['decisions'][cs[0]['id']]['validation_errors'][0])
        # A genuine nonassertion can reject a structurally false reconstruction.
        raw['decisions'][0]['checks']['asserted']=controlled.rating('fail')
        v=decisions.vote(raw,p,cs)
        self.assertEqual(v['decisions'][cs[0]['id']]['status'],'absent')
    def test_independent_j3_resolves_semantic_disagreement(self):
        c,p,cs,ex=self.setup_case();a=decisions.vote(controlled.oracle_vote(c,cs),p,cs);b=copy.deepcopy(a)
        b['decisions'][cs[0]['id']]['status']='absent'
        self.assertTrue(decisions.reconcile(cs,dict(J1=a,J2=b))['needs_j3'])
        r=decisions.reconcile(cs,dict(J1=a,J2=b,J3=a));self.assertEqual(r['candidates'][cs[0]['id']]['pair'],['J1','J3'])
    def test_negative_audit_detects_plausible_false_negative(self):
        c,p,cs,ex=self.setup_case();v=decisions.vote(controlled.oracle_vote(c,cs),p,cs)
        omitted=decisions.reconcile([],dict(J1=v,J2=v))
        # First extraction found nothing; independent full-text auditor finds M.
        first=candidates.extraction(extraction_value(p),p)
        r=decisions.finalize(p,cs,[omitted,decisions.reconcile(cs,dict(J1=v,J2=v))],first,ex)
        self.assertEqual(r['events']['erasure']['status'],'present')
    def test_audit_disagreement_not_silently_overridden(self):
        c,p,cs,ex=self.setup_case();a=decisions.vote(controlled.oracle_vote(c,cs),p,cs);b=copy.deepcopy(a)
        b['decisions'][cs[0]['id']]['status']='absent'
        r=decisions.finalize(p,cs,[decisions.reconcile(cs,dict(J1=b,J2=b)),decisions.reconcile(cs,dict(J1=a,J2=a))],ex,ex)
        self.assertEqual(r['events']['erasure']['status'],'uncertain')
    def test_failed_audit_or_extractor_never_absent(self):
        p=small('Nothing relevant.');good=candidates.extraction(extraction_value(p),p)
        for a,b in [(good,{}),({},good)]:
            r=decisions.finalize(p,[],[],a,b);self.assertTrue(all(d['status']=='uncertain' for d in r['events'].values()))
    def test_earliest_positive_and_later_correction_preserved(self):
        c,p,cs,ex=self.setup_case(17);v=decisions.vote(controlled.oracle_vote(c,cs),p,cs)
        r=decisions.finalize(p,cs,[decisions.reconcile(cs,dict(J1=v,J2=v))],ex,ex)
        self.assertEqual(r['events']['erasure']['status'],'present');self.assertEqual(r['events']['acknowledgment']['status'],'present')
        self.assertLess(r['events']['erasure']['span'][0],r['events']['acknowledgment']['span'][0])
    def test_earlier_uncertainty_blocks_first_occurrence(self):
        c,p,cs,ex=self.setup_case(20);v=decisions.vote(controlled.oracle_vote(c,cs),p,cs);v['decisions'][cs[0]['id']]['status']='uncertain'
        r=decisions.finalize(p,cs,[decisions.reconcile(cs,dict(J1=v,J2=v,J3=v))],ex,ex)
        self.assertEqual(r['events']['erasure']['status'],'uncertain')
    def test_override_without_accepted_prior_A_is_blocked(self):
        c,p,cs,ex=self.setup_case(8);v=decisions.vote(controlled.oracle_vote(c,cs),p,cs)
        for item in cs:
            if item['event']=='A':v['decisions'][item['id']]['status']='absent'
        r=decisions.finalize(p,cs,[decisions.reconcile(cs,dict(J1=v,J2=v))],ex,ex)
        self.assertEqual(r['events']['override']['status'],'uncertain');self.assertEqual(r['substitution']['status'],'present')
    def test_nonpresent_export_has_no_fabricated_evidence(self):
        p=small('No relevant text.');good=candidates.extraction(extraction_value(p),p);r=decisions.finalize(p,[],[],good,good)
        for d in r['events'].values():
            self.assertEqual(d['status'],'absent');self.assertIsNone(d['span']);self.assertIsNone(d['text']);self.assertEqual(d['certificates'],{})
    def test_unavailable_source_invalid_not_absent(self):
        p=small('');p['original_available']=False
        r=decisions.finalize(p,[],[],{},{});self.assertTrue(all(d['status']=='invalid' for d in r['events'].values()))
    def test_refusal_truncation_malformed_and_provider_error(self):
        for provider,body in [('openai',dict(status='completed',output=[dict(type='message',content=[dict(type='refusal')])])),('openai',dict(status='incomplete')),('anthropic',dict(stop_reason='max_tokens')),('anthropic',dict(stop_reason='refusal'))]:
            self.assertFalse(parse_response(provider,dict(status=200,body=json.dumps(body)))['valid'])
        for response in [dict(status=400,body='{"error":{"message":"schema rejected"}}'),dict(status=200,body='{'),dict(status=200,body='{"status":"completed","status":"completed"}')]:
            self.assertFalse(parse_response('openai',response)['valid'])
    def test_limits_and_live_identity_requirements(self):
        for field,value in [('wall_seconds',None),('wall_seconds',math.inf),('wall_seconds',0),('max_calls',-1),('max_estimated_usd',math.inf),('timeout_seconds',0)]:
            c=cfg();c['limits'][field]=value
            with self.assertRaises(ValueError):policy.freeze_policy(c)
        c=cfg();c['live_enabled']=True
        with self.assertRaises(ValueError):policy.freeze_policy(c)
        c=cfg();c['judges']['J2']['provider']='openai'
        with self.assertRaises(ValueError):policy.freeze_policy(c)

class ControlledTests(unittest.TestCase):
    def test_frozen_split_generator_and_independent_template_wording(self):
        cases=controlled.generate();self.assertEqual(len(cases),192);self.assertEqual(cases,controlled.generate())
        self.assertEqual(digest(cases),'48d1a7b6b4b76375f69f229cc8c0977d930d0ff493b843f29e60d4e739c07fa8')
        self.assertEqual(len({c['packet']['pre_answer_text'] for c in cases if c['packet']['original_available']}),190)
        for c in cases:
            p=c['packet'];self.assertEqual(p['source_table'].splitlines()[p['target']['target_row_position']+2],'| T | C |')
    def test_controlled_metrics_honestly_separate_extraction_oracle_and_live(self):
        r=controlled.evaluate();h=r['splits']['heldout'];self.assertEqual(h['exact_alignment'],1)
        for e in ('M','X'):self.assertEqual(h['structural_extraction'][e]['recall'],1)
        self.assertAlmostEqual(h['structural_extraction']['C']['recall'],11/14)
        self.assertEqual(h['structural_extraction']['O']['recall'],.75)
        for e in policy.EVENTS:
            self.assertEqual(h['oracle_wired_pipeline'][e]['f1'],1)
            self.assertEqual(h['production_without_judges'][e]['abstention_rate'],1)
            self.assertFalse(h['production_without_judges'][e]['target_met'])
        self.assertIn('NOT TESTED',r['real_semantic_validation'])

class WorkflowTests(Offline):
    def setup_review(self):
        source,backend=self.run_source();out=self.root/'v2';p=workflow.prepare(source,out,cfg());return source,backend,out,p
    def test_spend_and_global_call_budget_are_frozen(self):
        source,b=self.run_source();c=cfg();c['limits']['max_estimated_usd']=.000001
        out=self.root/'tiny';workflow.prepare(source,out,c);t=Transport()
        m=workflow.run(out,transport=t);self.assertEqual(m['attempted'],0);self.assertEqual(m['stop_reason'],'ESTIMATED_SPEND_BUDGET')
        c=cfg();c['limits']['max_calls']=2;out=self.root/'two';workflow.prepare(source,out,c)
        workflow.run(out,transport=t);workflow.run(out,transport=t);self.assertEqual(len(t.calls),2)
    def test_terminal_http_failure_cached_without_resend(self):
        source,b,out,p=self.setup_review()
        class Failed:
            kind='MOCK'
            def __init__(self):self.calls=0
            def __call__(self,*args):
                self.calls+=1;return dict(status=400,body='{"error":{"message":"unsupported schema"}}')
        t=Failed();workflow.run(out,transport=t,max_calls=1);workflow.run(out,transport=t,max_calls=0)
        self.assertEqual(t.calls,1)
        record=next((out/'judge-operations').glob('*/returned.json'))
        self.assertEqual(sealed_read(record)['parsed']['reason'],'HTTP_400')
    def test_live_deadline_transport_clamps_timeout_without_network(self):
        from types import SimpleNamespace
        clock=FakeClock();clock.advance(3)
        journal=SimpleNamespace(wall_seconds=5,started=0,clock=clock)
        calls=[]
        def transport(provider,request,timeout):calls.append(timeout);return 'fixture'
        wrapped=workflow.DeadlineTransport(journal,transport)
        self.assertEqual(wrapped('openai',{},120),'fixture');self.assertEqual(calls,[2])
        clock.advance(3)
        with self.assertRaises(TimeoutError):wrapped('openai',{},120)
        self.assertEqual(len(calls),1)
    def test_source_population_index_and_offline_prepare_run(self):
        source,b,out,p=self.setup_review();before=snapshot(source);n=len(b.calls)
        self.assertEqual(len(p['case_ids']),16);self.assertEqual(p['total_request_ceiling'],128)
        for packet in p['packets'].values():
            self.assertEqual(packet['target']['target_row_position'],9);self.assertEqual(packet['target']['target_row_number_one_based'],10)
            self.assertNotIn('ANSWER:',packet['pre_answer_text']);self.assertFalse({'score','correct','pattern','votes','interventions'}&set(packet))
        m=workflow.run(out);self.assertEqual(m['attempted'],0);self.assertEqual(m['stop_reason'],'OFFLINE')
        self.assertEqual(snapshot(source),before);self.assertEqual(n,len(b.calls))
        self.assertEqual(source_hash(),'e545f0a756934f0d5c953db3a1c102146a1616dc2706913cb3537e8a5a6a2c2b')
    def test_end_to_end_96_mock_calls_export_and_resumption(self):
        source,b,out,p=self.setup_review();before=snapshot(source);t=Transport()
        m=workflow.run(out,transport=t);self.assertEqual(m['attempted'],96)
        manifest=workflow.export(out);self.assertEqual(len(manifest['cases']),16)
        self.assertEqual(read_manifest(out/'annotation-manifest-v5.json')['artifact_hash'],manifest['artifact_hash'])
        for tid,c in manifest['cases'].items():validate_decisions(p['packets'][tid],c['events'])
        side=sealed_read(out/'observations-v2.json');self.assertEqual(len(side['cases']),16)
        self.assertNotIn('substitution',next(iter(manifest['cases'].values()))['events'])
        self.assertIn('substitution',next(iter(side['cases'].values())))
        workflow.run(out,transport=t);workflow.export(out);self.assertEqual(len(t.calls),96);self.assertEqual(snapshot(source),before)
    def test_no_intervention_verification_bypass(self):
        source,b,out,p=self.setup_review();workflow.run(out,transport=Transport());workflow.export(out)
        edits=self.root/'edits';interventions.prepare_edits(source,out/'annotation-manifest-v5.json',edits,'M')
        with self.assertRaises((ValueError,FileNotFoundError,KeyError)):
            interventions.freeze_edits(edits,edits/'draft-template.json',edits/'verification-template.json',backend_override=b)
    def test_four_call_smoke_then_resume_with_no_duplicate_requests(self):
        source,b,out,p=self.setup_review();t=Transport();m=workflow.run(out,transport=t,stage='smoke')
        self.assertEqual(m['attempted'],4);self.assertEqual(len(t.calls),4)
        self.assertFalse((out/'annotation-manifest-v5.json').exists())
        workflow.run(out,transport=t);self.assertEqual(len(t.calls),96)
        requests=[digest(c['request']) for c in t.calls];self.assertEqual(len(set(requests)),len(requests))
    def test_j3_independent_same_evidence_and_only_on_disagreement(self):
        source,b,out,p=self.setup_review();tid=p['case_ids'][0]
        def change(call,v):
            if call['request']['model']=='fixture-J2' and call['view']['task_id']==tid and 'candidates' in call['view']:
                v['decisions'][0]['status']='uncertain'
        t=Transport(change);workflow.run(out,transport=t)
        j3=[c for c in t.calls if c['request']['model']=='fixture-J3'];self.assertEqual(len(j3),2)
        for call in j3:
            self.assertFalse({'votes','reconciliation','final_answer','correct'}&set(call['view']))
            peers=[c['view'] for c in t.calls if c['request']['model']=='fixture-J1' and c['view']==call['view']]
            self.assertTrue(peers)
    def test_cross_phase_conflict_invokes_bounded_independent_j3(self):
        source,b,out,p=self.setup_review()
        tid=next(t for t,v in p['packets'].items() if 'MISSING' in v['pre_answer_text'])
        def change(call,v):
            cs=call['view'].get('candidates',[])
            if (call['view']['task_id']==tid and cs and
                call['request']['model']!='fixture-J3' and
                any(x['path']=='structural' for c in cs for x in c['provenance'])):
                lookup={c['id']:c for c in cs}
                for d in v['decisions']:
                    if lookup[d['candidate_id']]['event']=='M':
                        d['status']='absent';d['checks']['asserted']=controlled.rating('fail')
        t=Transport(change);workflow.run(out,transport=t)
        self.assertEqual(len(t.calls),98)
        r=sealed_read(workflow.Review(out).path(tid,'resolution'))
        self.assertTrue(r['cross_phase_disagreement']);self.assertTrue(r['adjudicated'])
        self.assertFalse(r['initial_agreement']);self.assertEqual(r['events']['erasure']['status'],'uncertain')
        workflow.run(out,transport=t);workflow.export(out);self.assertEqual(len(t.calls),98)
    def test_request_spend_wall_budgets_and_replay(self):
        source,b,out,p=self.setup_review();clock=FakeClock();t=Transport(clock=clock)
        m=workflow.run(out,transport=t,max_calls=1,clock=clock);self.assertEqual(m['attempted'],1)
        m=workflow.run(out,transport=t,max_calls=2,wall_seconds=1,clock=clock);self.assertEqual(m['attempted'],1);self.assertEqual(m['stop_reason'],'WALL_SCHEDULING_LIMIT')
        with self.assertRaises(ValueError):workflow.run(out,wall_seconds=math.inf)
        with self.assertRaises(ValueError):workflow.run(out,max_calls=129)
    def test_failure_and_ambiguous_started_never_resend(self):
        source,b,out,p=self.setup_review()
        def fail(call,v):raise KeyboardInterrupt('Synthetic process loss')
        t=Transport(fail)
        with self.assertRaises(KeyboardInterrupt):workflow.run(out,transport=t,max_calls=1)
        self.assertEqual(len(t.calls),1);failed=next((out/'judge-operations').glob('*/failed.json'))
        # Simulate process loss between started and terminal in this synthetic copy.
        failed.unlink();t2=Transport();workflow.run(out,transport=t2,max_calls=1)
        self.assertEqual(sealed_read(failed)['parsed']['reason'],'ambiguous_inflight')
        failedkey=failed.parent.name
        self.assertFalse(any(digest(c['request'])==digest(sealed_read(failed)['request']) for c in t2.calls))
        self.assertTrue(failedkey)
    def test_source_policy_model_mismatches_fail_closed(self):
        source,b,out,p=self.setup_review();review=workflow.Review(out)
        changed=cfg();changed['judges']['J1']['model']='new-model'
        with self.assertRaises(ValueError):workflow.prepare(source,out,changed)
        bad=copy.deepcopy(p);bad['packets'][p['case_ids'][0]]['target']['verified_class']='Z';bad.pop('artifact_hash')
        path=out/'review-plan-v2.json';path.write_text(json.dumps(dict(bad,artifact_hash=digest(bad))))
        with self.assertRaises(ValueError):workflow.Review(out)
    def test_returned_model_mismatch_retained_uncertain_no_retry(self):
        source,b,out,p=self.setup_review();t=Transport()
        class WrongModel:
            kind='MOCK'
            def __call__(self,*args):
                r=t(*args);body=json.loads(r['body']);body['model']='different';r['body']=json.dumps(body);return r
        workflow.run(out,transport=WrongModel(),max_calls=1)
        result=next((out/'judge-operations').glob('*/returned.json'))
        self.assertEqual(sealed_read(result)['parsed']['reason'],'returned_model_identity_mismatch')
        workflow.run(out,transport=WrongModel(),max_calls=0);self.assertEqual(len(t.calls),1)
    def test_no_http_offline_no_live_on_synthetic_source(self):
        source,b,out,p=self.setup_review()
        with self.assertRaises(ValueError):workflow.run(out,transport=HTTPTransport())
        with self.assertRaises(ValueError):workflow.run(out,live=True)
    def test_separate_output_and_row_index_mismatch(self):
        source,b,out,p=self.setup_review()
        with self.assertRaises(ValueError):workflow.prepare(source,source/'v2',cfg())
        task=workflow.Review(out).source_original.rows[p['case_ids'][0]]['task']
        with self.assertRaises(ValueError):target_metadata(dict(task,target_row_position=8))
    def test_frozen_packet_and_operation_identity(self):
        source,b,out,p=self.setup_review();workflow.run(out,transport=Transport(),max_calls=1)
        r=workflow.Review(out);j=workflow.journal_for(r,transport=Transport());tid=p['case_ids'][0]
        view=copy.deepcopy(p['packets'][tid]);view['pre_answer_text']+=' changed'
        with self.assertRaises(ValueError):r.call(j,tid,'primary','J1','draft',view)
    def test_inspect_read_only_and_cpu_import_no_torch(self):
        source,b,out,p=self.setup_review();before=snapshot(out);r=workflow.inspect(out)
        self.assertEqual(snapshot(out),before);self.assertEqual(len(r['cases']),16)
        result=subprocess.run([sys.executable,'-B','-c',"import exception_study2_v5_review_v2.workflow;import sys;assert 'torch' not in sys.modules"],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__':unittest.main()
