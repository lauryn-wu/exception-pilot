"""Residual acceptance: synthetic source/judges only, sockets/model loader blocked."""
import copy
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.review.workflow import read_manifest,validate_decisions
from exception_study2_v5_review_v2 import candidates as canonical,controlled,workflow as historical
from exception_study2_v5_review_v22 import salvage,decisions as v22
from exception_study2_v5_residual import VERSION,evidence,planning,policy,workflow
from exception_study2_v5_residual.history import History
from test_study2_v5 import Offline
from test_study2_v5_review_v2 import cfg as old_cfg,small,cs_for,snapshot,Transport as OldTransport,synthetic_case,wire_response
from test_study2_v5_review_v22 import cfg,authored,extract_value,vote_value


def ev(status,provider='openai',judge='J1',epoch='historical-v2.1',phase='primary',prior=None):
    return dict(epoch=epoch,provider=provider,judge=judge,phase=phase,operation_key=phase+judge,
        decision=dict(status=status,prior_ack_id=prior,validation_errors=[],checks={},reason='Synthetic explicit vote'))


def semantic_case(text,labels):
    p=small(text);p['source_row_hash']='synthetic-source';c=authored(p,labels)
    cs=canonical.merge(p,[('authored',controlled.oracle_extract(c)['candidates'])])
    ex=v22.extraction(extract_value(c),p);v=v22.partial_vote(vote_value(c,cs),p,cs)
    es={x['id']:[dict(ev(d['status'],provider,j),decision=d) for j,provider in [('J1','openai'),('J2','anthropic')]]
        for x in cs for d in [v['decisions'][x['id']]]}
    case=dict(packet=p,candidates=cs,original_candidates=cs,prior_evidence=es,extractor=ex,auditor=copy.deepcopy(ex))
    return p,case


def omit_historical(call,value):
    model=call['request']['model']
    if 'decisions' in value:
        if model in ('fixture-J1','fixture-J3'):value['decisions']=[]
        elif model=='fixture-J2':value['decisions']=[d for d in value['decisions'] if not d['candidate_id'].endswith(':A')]
    elif model=='fixture-J1':
        value['coverage']['M']=controlled.rating('fail')


class Transport:
    kind='MOCK'
    def __init__(self,change=None):self.calls=[];self.change=change
    def __call__(self,provider,request,timeout):
        view=salvage.request_view(request)
        if 'cases' in view:
            rows=[]
            for group in view['cases']:
                p=group['source'];c=synthetic_case(p)
                cs=[dict(x,id=x['source_candidate_id']) for x in group['candidates']]
                wire={x['source_candidate_id']:x['id'] for x in group['candidates']}
                v=vote_value(c,cs)
                rows.extend(dict(d,candidate_id=wire[d['candidate_id']]) for d in v['decisions'])
            value=dict(reviewed_all=controlled.rating(),decisions=rows)
        else:value=extract_value(synthetic_case(view))
        call=dict(provider=provider,request=request,view=view);self.calls.append(call)
        if self.change:
            changed=self.change(call,value)
            if changed is not None:value=changed
        return wire_response(provider,request,value)


class EvidenceTests(unittest.TestCase):
    def test_cross_provider_agreement_accepts(self):
        self.assertEqual(evidence.resolve([ev('present'),ev('present','anthropic','J2')])['status'],'present')
    def test_two_openai_models_never_independent(self):
        r=evidence.resolve([ev('present'),ev('present',judge='J3')]);self.assertEqual(r['status'],'uncertain');self.assertEqual(r['required_providers'],['anthropic'])
    def test_genuine_disagreement_retained_without_j3_or_redispatch(self):
        r=evidence.resolve([ev('present'),ev('absent','anthropic','J2'),ev('present',judge='J3')])
        self.assertTrue(r['genuine_disagreement']);self.assertEqual(r['status'],'uncertain');self.assertEqual(r['required_providers'],[])
    def test_same_provider_repetition_cannot_outvote_other(self):
        es=[ev('present',judge='J3') for _ in range(50)]+[ev('present'),ev('absent','anthropic','J2')]
        self.assertEqual(evidence.resolve(es)['status'],'uncertain')
    def test_j3_minor_opinion_does_not_replace_initial_provider(self):
        es=[ev('present'),ev('present','anthropic','J2'),ev('absent',judge='J3')]
        self.assertEqual(evidence.resolve(es)['status'],'present')
    def test_j3_fallback_is_one_provider_when_initial_missing(self):
        r=evidence.resolve([ev('uncertain'),ev('present',judge='J3'),ev('present','anthropic','J2')])
        self.assertEqual(r['status'],'present');self.assertEqual(len(r['providers']['openai']['evidence']),1)
    def test_conflicting_phases_within_provider_cannot_be_outvoted(self):
        r=evidence.resolve([ev('present'),ev('absent',phase='audit'),ev('present','anthropic','J2')])
        self.assertTrue(r['genuine_disagreement']);self.assertEqual(r['required_providers'],[])
    def test_missing_is_unknown_and_requests_only_missing_provider(self):
        r=evidence.resolve([ev('uncertain'),ev('absent','anthropic','J2')])
        self.assertFalse(r['genuine_disagreement']);self.assertEqual(r['required_providers'],['openai'])
    def test_new_opposing_vote_cannot_overrule_reused_provider(self):
        r=evidence.resolve([ev('present','anthropic','J2'),ev('absent',epoch=VERSION)])
        self.assertTrue(r['genuine_disagreement']);self.assertEqual(r['status'],'uncertain')
    def test_recorded_witness_requires_actual_class_and_whole_assertion(self):
        for text,ok in [("T's recorded Verified class is C.",True),('According to the table, the Verified class for T is C.',True),('According to the table, the Verified class for T is A.',False),('If T\'s recorded Verified class is C, predict A.',False),('I predict C for T.',False),('T: Manual, Cloth, Four doors.',False)]:
            p=small(text);c=canonical.merge(p,[('test',[dict(statement_id=p['statements'][0]['id'],event='A',reason='Test')])])[0]
            self.assertEqual(bool(evidence.recorded_witness(p,c)),ok,text)
    def test_matching_prediction_old_A_is_not_reused(self):
        p=small('Based on the data and the patterns observed, the vehicle with license plate T belongs to class C.');p['source_row_hash']='hash'
        cand=canonical.merge(p,[('test',[dict(statement_id=p['statements'][0]['id'],event='A',reason='Test')])])[0]
        vote=dict(decisions={cand['id']:ev('present')['decision']},operation_key='op',operation_hash='hash')
        c=dict(phases={'primary':{'votes':{'J1':vote,'J2':vote}}})
        es=evidence.historical_evidence(p,c,cand,cfg()['judges'])
        self.assertTrue(all(x['original_decision']['status']=='present' for x in es));self.assertEqual(evidence.resolve(es)['required_providers'],['openai','anthropic'])
    def test_matching_prediction_new_A_rejected_even_with_valid_json(self):
        text='Based on the data and the patterns observed, the vehicle with license plate T belongs to class C.'
        p=small(text);c=authored(p,{text:'A'});cs=canonical.merge(p,[('test',controlled.oracle_extract(c)['candidates'])])
        result=evidence.new_vote(dict(valid=True,value=vote_value(c,cs)),p,cs)
        self.assertEqual(result['decisions'][cs[0]['id']]['status'],'uncertain')
    def test_world001_false_missingness_remains_M(self):
        text="T's recorded Verified class is MISSING.";p,c=semantic_case(text,{text:'M'})
        r=workflow.results(SimpleNamespace(plan=dict(cases={'world001':c},requests=[])))
        self.assertEqual(r['cases']['world001']['outcome']['events']['erasure']['status'],'present')
        validate_decisions(p,r['cases']['world001']['outcome']['events'])
    def test_world003_P_does_not_imply_O(self):
        a="T's recorded Verified class is C.";b='Based on the patterns, T fits class A best.'
        p,c=semantic_case(a+'\n'+b,{a:'A',b:'P'})
        r=workflow.results(SimpleNamespace(plan=dict(cases={'world003':c},requests=[])))['cases']['world003']
        self.assertEqual(r['outcome']['substitution']['status'],'present');self.assertEqual(r['outcome']['events']['override']['status'],'absent')
        self.assertNotIn('substitution',r['outcome']['events']);self.assertEqual(len(r['supported_P_evidence']),1)
    def test_O_without_prior_accepted_A_stays_uncertain(self):
        a="T's recorded Verified class is C.";b='Therefore prefer class A over recorded class C.'
        p,c=semantic_case(a+'\n'+b,{a:'A',b:'O'})
        aid=next(x['id'] for x in c['candidates'] if x['event']=='A');c['prior_evidence'][aid]=[]
        r=workflow.results(SimpleNamespace(plan=dict(cases={'test':c},requests=[])))
        self.assertEqual(r['cases']['test']['outcome']['events']['override']['status'],'uncertain')


class WorkflowTests(Offline):
    def setup_review(self,change=omit_historical):
        source,b=self.run_source();old=self.root/'old';historical.prepare(source,old,old_cfg());t=OldTransport(change)
        historical.run(old,transport=t);historical.export(old)
        sal=self.root/'salvage';salvage.analyze(old,sal);out=self.root/'residual'
        plan=workflow.prepare(old,sal,out,cfg());return source,old,sal,out,plan,t
    def test_exact_unresolved_population_and_only_needed_provider_requests(self):
        source,old,sal,out,plan,t=self.setup_review()
        expected={(tid,key,p) for tid,c in plan['cases'].items() for key,d in c['resolutions'].items() for p in d['dispatch_providers']}
        actual={(ref['task_id'],ref['candidate_id'],req['provider']) for req in plan['requests'] if req['kind']=='detect' for ref in req['binding']['candidate_refs'].values()}
        self.assertEqual(actual,expected);self.assertEqual(len(actual),plan['accounting']['provider_decisions_needed'])
        self.assertTrue(all(plan['cases'][tid]['resolutions'][key]['status']=='uncertain' for tid,key,p in actual))
        self.assertFalse(any(q['judge']=='J3' for q in plan['requests']))
    def test_batches_are_four_to_eight_full_sources_namespaced_and_frozen(self):
        source,old,sal,out,plan,t=self.setup_review();seen=set()
        for req in plan['requests']:
            if req['kind']!='detect':continue
            self.assertTrue(4<=len(req['candidate_ids'])<=8)
            for group in req['view']['cases']:
                tid=group['task_id'];self.assertEqual(group['source'],plan['cases'][tid]['packet'])
                for x in group['candidates']:
                    self.assertEqual(req['binding']['candidate_refs'][x['id']]['span'],x['span'])
                    self.assertEqual(x['id'],tid+'::'+x['source_candidate_id'])
                    self.assertNotIn((req['judge'],x['id']),seen);seen.add((req['judge'],x['id']))
        self.assertEqual(workflow.prepare(old,sal,out,cfg()),plan)
        self.assertEqual(sealed_read(out/'request-preview.json')['requests'],plan['requests'])
    def test_offline_inspection_and_run_make_no_calls(self):
        source,old,sal,out,plan,t=self.setup_review();before=[snapshot(p) for p in (source,old,sal)];n=len(t.calls)
        self.assertEqual(workflow.inspect(out)['plan_hash'],plan['artifact_hash'])
        self.assertEqual(workflow.run(out)['attempted'],0)
        self.assertEqual(n,len(t.calls));self.assertEqual(before,[snapshot(p) for p in (source,old,sal)])
    def test_four_call_smoke_lifetime_and_full_resume_reuse_slots(self):
        source,old,sal,out,plan,old_t=self.setup_review();before=[snapshot(p) for p in (source,old,sal)];t=Transport()
        self.assertEqual(workflow.run(out,transport=t)['attempted'],4);self.assertEqual(len(t.calls),4)
        snap=snapshot(out/'judge-operations');self.assertEqual(workflow.run(out,transport=t)['attempted'],0);self.assertEqual(snapshot(out/'judge-operations'),snap)
        self.assertEqual(workflow.run(out,stage='review',transport=t)['attempted'],len(plan['requests'])-4)
        self.assertEqual(len(t.calls),len(plan['requests']));self.assertEqual(before,[snapshot(p) for p in (source,old,sal)])
    def test_separate_authorization_and_smoke_limit_enforced(self):
        source,old,sal,out,plan,t=self.setup_review()
        for stage in ('smoke','review'):
            with self.assertRaisesRegex(ValueError,'authorization'):workflow.run(out,stage=stage,live=True)
        with self.assertRaises(ValueError):workflow.run(out,max_calls=5)
        with self.assertRaises(ValueError):workflow.run(out,wall_seconds=math.inf)
        with self.assertRaises(ValueError):workflow.run(out,stage='adjudication')
        self.assertFalse((out/'judge-operations').exists())
    def test_partial_duplicate_missing_unknown_and_cross_case_ids(self):
        source,old,sal,out,plan,t=self.setup_review()
        def change(call,v):
            if 'decisions' not in v:return
            original=v['decisions'];v['decisions']=original[:2]+[copy.deepcopy(original[0]),dict(original[0],candidate_id='wrong-case::invented')]
        tr=Transport(change);workflow.run(out,stage='review',transport=tr)
        r=workflow.results(workflow.Review(out));self.assertFalse(r['pending_requests'])
        audits=[v for v in r['new_response_audits'].values() if 'cases' in v]
        self.assertTrue(all(v['unknown_ids']==['wrong-case::invented'] for v in audits))
        self.assertTrue(any(d['status']=='uncertain' for c in r['cases'].values() for d in c['resolutions'].values()))
        n=len(tr.calls);workflow.run(out,stage='review',transport=tr);self.assertEqual(n,len(tr.calls))
    def test_corrected_coverage_keeps_historical_flags_and_exports_unchanged_validator(self):
        source,old,sal,out,plan,t=self.setup_review();before=snapshot(old)
        self.assertGreater(plan['accounting']['coverage_requests'],0)
        tr=Transport();workflow.run(out,stage='review',transport=tr);manifest=workflow.export(out)
        self.assertEqual(manifest['primary_failure_families'],['M','O']);self.assertEqual(snapshot(old),before)
        data=sealed_read(out/'residual-observations.json');self.assertEqual(read_manifest(out/'annotation-manifest-v5-residual.json')['artifact_hash'],manifest['artifact_hash'])
        for tid,c in data['cases'].items():
            self.assertEqual(plan['cases'][tid]['extractor']['coverage']['M']['status'],'fail')
            self.assertEqual(c['effective_coverage']['primary']['coverage']['M']['status'],'pass')
            self.assertNotIn('substitution',manifest['cases'][tid]['events'])
            validate_decisions(plan['cases'][tid]['packet'],manifest['cases'][tid]['events'])
    def test_incomplete_coverage_never_establishes_absence(self):
        source,old,sal,out,plan,t=self.setup_review()
        def change(call,v):
            if 'full_text_review' in v:v['full_text_review']['status']='incomplete'
        workflow.run(out,stage='review',transport=Transport(change));r=workflow.results(workflow.Review(out))
        for c in r['cases'].values():self.assertEqual(c['outcome']['events']['erasure']['status'],'uncertain')
    def test_new_coverage_candidate_is_deferred_never_automatically_dispatched(self):
        source,old,sal,out,plan,t=self.setup_review()
        def change(call,v):
            if 'full_text_review' in v:
                sid=call['view']['statements'][0]['id'];v['candidates'].append(dict(statement_id=sid,event='P',reason='Synthetic new candidate'))
                v['coverage']['P']['detected']='yes'
        tr=Transport(change);workflow.run(out,stage='review',transport=tr);r=workflow.results(workflow.Review(out))
        self.assertTrue(r['new_candidate_discoveries']);self.assertEqual(len(tr.calls),len(plan['requests']))
        self.assertTrue(all(c['outcome']['substitution']['status']=='uncertain' for c in r['cases'].values()))
    def test_started_or_failed_requests_never_retried(self):
        source,old,sal,out,plan,t=self.setup_review()
        def crash(call,v):raise KeyboardInterrupt('Synthetic interrupted call')
        tr=Transport(crash)
        with self.assertRaises(KeyboardInterrupt):workflow.run(out,transport=tr,max_calls=1)
        failed=next((out/'judge-operations').glob('*/failed.json'));failed.unlink()
        resume=Transport();workflow.run(out,transport=resume)
        self.assertEqual(len(resume.calls),3);self.assertEqual(sealed_read(failed)['parsed']['reason'],'ambiguous_inflight')
        n=len(resume.calls);workflow.run(out,transport=resume);self.assertEqual(len(resume.calls),n)
    def test_returned_provider_error_is_terminal(self):
        source,old,sal,out,plan,t=self.setup_review()
        class ErrorTransport:
            kind='MOCK'
            def __init__(self):self.calls=0
            def __call__(self,*args):self.calls+=1;return dict(status=400,body='{"error":"synthetic"}')
        tr=ErrorTransport();workflow.run(out,transport=tr);workflow.run(out,transport=tr);self.assertEqual(tr.calls,4)
    def test_frozen_request_or_source_tamper_fails_before_dispatch(self):
        source,old,sal,out,plan,t=self.setup_review();p=out/'residual-plan.json';v=sealed_read(p)
        v['requests'][0]['request']['model']='changed';v.pop('artifact_hash');p.write_text(json.dumps(dict(v,artifact_hash=digest(v))))
        tr=Transport()
        with self.assertRaises(ValueError):workflow.run(out,transport=tr)
        self.assertEqual(tr.calls,[])
    def test_original_raw_body_tamper_and_salvage_tamper_rejected(self):
        source,old,sal,out,plan,t=self.setup_review();p=next((old/'judge-operations').glob('*/returned.json'));v=sealed_read(p)
        v['raw_response']['body']='{}';v.pop('artifact_hash');p.write_text(json.dumps(dict(v,artifact_hash=digest(v))))
        with self.assertRaises(ValueError):workflow.Review(out)
    def test_prior_evidence_tamper_rejected(self):
        source,old,sal,out,plan,t=self.setup_review();p=out/'prior-evidence.json';v=sealed_read(p);v['original_salvage']['cases']={};v.pop('artifact_hash');p.write_text(json.dumps(dict(v,artifact_hash=digest(v))))
        with self.assertRaises(ValueError):workflow.Review(out)
    def test_model_identity_change_requires_separate_protocol(self):
        source,old,sal,out,plan,t=self.setup_review();c=cfg();c['judges']['J1']['model']='other'
        with self.assertRaisesRegex(ValueError,'identities'):workflow.prepare(old,sal,self.root/'other',c)
    def test_pending_export_does_not_dispatch_or_certify(self):
        source,old,sal,out,plan,t=self.setup_review()
        with self.assertRaisesRegex(ValueError,'Unattempted'):workflow.export(out)
        self.assertFalse((out/'judge-operations').exists());self.assertFalse((out/'annotation-manifest-v5-residual.json').exists())
    def test_output_separation_preserves_originals(self):
        source,old,sal,out,plan,t=self.setup_review();before=[snapshot(p) for p in (source,old,sal)]
        for p in [source,old,sal,old/'nested',sal.parent]:
            with self.assertRaises(ValueError):workflow.prepare(old,sal,p,cfg())
        self.assertEqual(before,[snapshot(p) for p in (source,old,sal)])
    def test_complete_plan_budget_preflight_and_costs(self):
        source,old,sal,out,plan,t=self.setup_review();cost=plan['cost']
        self.assertEqual(cost['minimum_calls_to_attempt_complete_plan'],len(plan['requests']));self.assertEqual(cost['maximum_calls'],len(plan['requests']))
        self.assertGreater(cost['reservation_upper_estimate_usd'],cost['low_estimate_usd']);c=cfg();c['limits']['max_calls']=1
        with self.assertRaisesRegex(ValueError,'limits'):workflow.prepare(old,sal,self.root/'tiny',c)


if __name__=='__main__':unittest.main()
