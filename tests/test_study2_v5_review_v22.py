"""Offline repair acceptance; synthetic semantic judgments and blocked network."""
import copy
import json
import math
import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.review.workflow import validate_decisions,read_manifest
from exception_study2_v5_review_v2 import workflow as historical,candidates as canonical,controlled,decisions as old
from exception_study2_v5_review_v22 import policy,decisions,batches,workflow,salvage
from test_study2_v5 import Offline
from test_study2_v5_review_v2 import cfg as old_cfg,small,cs_for,synthetic_case,wire_response,snapshot,Transport as OldTransport
from test_automated_review import FakeClock


def cfg():
    c=old_cfg();c['batch_size']=6;c['policy_name']='v22-offline-test';c['limits']['max_calls']=256
    return c


def authored(p,labels):return dict(packet=p,statement_truth={s['id']:list(labels.get(s['text'],'')) for s in p['statements']})

def extract_value(c):
    v=controlled.oracle_extract(c)
    return dict(full_text_review=dict(status='complete',reason='All authored fixture text inspected.'),
        coverage={e:dict(coverage='complete',detected='yes' if any(e in es for es in c['statement_truth'].values()) else 'no',reason='Authored fixture labels; no semantic accuracy claim.') for e in policy.EVENTS},
        candidates=v['candidates'],corrections=v['corrections'])


def vote_value(c,cs):
    v=controlled.oracle_vote(c,cs);lookup={x['id']:x for x in cs}
    target=c['packet']['target']['verified_class']
    for d in v['decisions']:
        e=lookup[d['candidate_id']]['event'];positive=d['status']=='present'
        d['value_basis']='recorded' if positive and e in ('A','M','X') else 'inferred' if positive and e in ('P','O') else 'not_applicable'
        d['asserted_class']=target if positive and e=='A' else 'MISSING' if positive and e=='M' else next(x for x in 'ABC' if x!=target) if positive and e in ('P','O','X') else 'NONE'
    return v


def resolved(p,labels):
    c=authored(p,labels);raw=controlled.oracle_extract(c)
    cs=canonical.merge(p,[('structural',canonical.structural_candidates(p)),('authored',raw['candidates'])])
    cs,excluded=batches.filter_candidates(cs)
    v=decisions.partial_vote(vote_value(c,cs),p,cs);ex=decisions.extraction(extract_value(c),p)
    phase=decisions.reconcile(cs,dict(J1=v,J2=copy.deepcopy(v)),cfg()['judges'])
    return decisions.finalize(p,cs,[phase],ex,ex),cs,v,ex


class Transport:
    kind='MOCK'
    def __init__(self,change=None,clock=None):self.calls=[];self.change=change;self.clock=clock
    def __call__(self,provider,request,timeout):
        p=salvage.request_view(request);c=synthetic_case(p)
        value=vote_value(c,p['candidates']) if 'candidates' in p else extract_value(c)
        call=dict(provider=provider,request=request,view=p,timeout=timeout);self.calls.append(call)
        if self.clock:self.clock.advance(2)
        if self.change:
            changed=self.change(call,value)
            if changed is not None:value=changed
        return wire_response(provider,request,value)


class PerItemTests(unittest.TestCase):
    def fixture(self):
        p=small("T's recorded Verified class is C.\nT's recorded Verified class is MISSING.")
        c=authored(p,{p['statements'][0]['text']:'A',p['statements'][1]['text']:'M'});cs=cs_for(p)
        return p,cs,vote_value(c,cs)
    def test_partial_valid_decisions_survive_missing_siblings(self):
        p,cs,value=self.fixture();value['decisions']=value['decisions'][:1]
        v=decisions.partial_vote(value,p,cs)
        self.assertEqual(v['decisions'][cs[0]['id']]['status'],'present')
        self.assertEqual(set(v['audit']['missing_ids']),{c['id'] for c in cs[1:]})
        self.assertTrue(all(v['decisions'][c['id']]['status']=='uncertain' for c in cs[1:]))
    def test_duplicate_identical_or_conflicting_items_poison_only_that_id(self):
        for conflicting in (False,True):
            p,cs,value=self.fixture();dup=copy.deepcopy(value['decisions'][0])
            if conflicting:dup['status']='absent'
            value['decisions'].append(dup);v=decisions.partial_vote(value,p,cs)
            self.assertEqual(v['decisions'][cs[0]['id']]['status'],'uncertain')
            self.assertEqual(v['decisions'][cs[1]['id']]['status'],'absent')
            self.assertEqual(v['audit']['duplicate_ids'],[cs[0]['id']])
    def test_unknown_id_never_votes_and_does_not_poison_expected_items(self):
        p,cs,value=self.fixture();unknown=copy.deepcopy(value['decisions'][0]);unknown['candidate_id']='invented';value['decisions'].append(unknown)
        v=decisions.partial_vote(value,p,cs)
        self.assertEqual(v['audit']['unknown_ids'],['invented']);self.assertNotIn('invented',v['decisions'])
        self.assertEqual(v['decisions'][cs[0]['id']]['status'],'present')
    def test_malformed_item_and_missing_id_are_independently_audited(self):
        p,cs,value=self.fixture();del value['decisions'][0]['checks'];value['decisions'].append({'reason':'No ID'});value['decisions'].append(None)
        v=decisions.partial_vote(value,p,cs)
        self.assertEqual(len(v['audit']['malformed_items']),3)
        self.assertEqual(v['decisions'][cs[0]['id']]['status'],'uncertain');self.assertEqual(v['decisions'][cs[1]['id']]['status'],'absent')
    def test_provider_failure_or_unreviewed_text_never_salvaged_as_pass(self):
        p,cs,value=self.fixture()
        for v in (decisions.partial_vote(value,p,cs,False,'HTTP_400'),decisions.partial_vote(dict(value,reviewed_all=controlled.rating('fail')),p,cs)):
            self.assertTrue(all(d['status']=='uncertain' for d in v['decisions'].values()))
    def test_historical_missing_uses_unchanged_check_definitions(self):
        p,cs,value=self.fixture();value['decisions']=value['decisions'][:1]
        for d in value['decisions']:d.pop('value_basis');d.pop('asserted_class')
        self.assertFalse(old.vote(value,p,cs)['valid'])
        v=decisions.partial_vote(value,p,cs,historical=True)
        self.assertEqual(v['decisions'][cs[0]['id']]['status'],'present')
    def test_recorded_ack_requires_value_and_recorded_basis(self):
        p,cs,value=self.fixture();a=next(d for d in value['decisions'] if d['status']=='present' and d['candidate_id'].endswith(':A'))
        for basis,label in [('inferred','C'),('recorded','A'),('recorded','NONE')]:
            changed=copy.deepcopy(value);item=next(d for d in changed['decisions'] if d['candidate_id']==a['candidate_id']);item.update(value_basis=basis,asserted_class=label)
            self.assertEqual(decisions.partial_vote(changed,p,cs)['decisions'][a['candidate_id']]['status'],'uncertain')
    def test_coincidentally_correct_prediction_is_not_A_or_P(self):
        p=small('I predict C for T.');r,_,_,_=resolved(p,{})
        self.assertEqual(r['events']['acknowledgment']['status'],'absent');self.assertEqual(r['substitution']['status'],'absent')
        pred=canonical.merge(p,[('bad',[dict(statement_id=p['statements'][0]['id'],event='A',reason='Test wrong claim')])])
        c=authored(p,{p['statements'][0]['text']:'A'});v=decisions.partial_vote(vote_value(c,pred),p,pred)
        self.assertEqual(v['decisions'][pred[0]['id']]['status'],'uncertain')


class CoverageAndSemanticsTests(unittest.TestCase):
    def test_full_coverage_zero_events_is_complete_and_absent(self):
        p=small('Nothing asserted.');c=authored(p,{})
        value=extract_value(c);self.assertTrue(all(v['detected']=='no' and v['coverage']=='complete' for v in value['coverage'].values()))
        ex=decisions.extraction(value,p);r=decisions.finalize(p,[],[],ex,ex)
        self.assertTrue(all(d['status']=='absent' for d in r['events'].values()))
    def test_incomplete_full_or_event_coverage_prevents_absence(self):
        p=small('Nothing asserted.');c=authored(p,{})
        for field in ('full','event','uncertain_detection'):
            value=extract_value(c)
            if field=='full':value['full_text_review']['status']='incomplete'
            elif field=='event':value['coverage']['M']['coverage']='incomplete'
            else:value['coverage']['M']['detected']='uncertain'
            ex=decisions.extraction(value,p)
            self.assertEqual(decisions.finalize(p,[],[],ex,ex)['events']['erasure']['status'],'uncertain')
    def test_historical_fail_not_promoted_from_absence_explanation(self):
        p=small('Nothing asserted.');c=authored(p,{});value=controlled.oracle_extract(c)
        value['coverage']['M']=dict(status='fail',reason='The whole text contains no missingness event.')
        ex=canonical.extraction(value,p)
        self.assertEqual(decisions.finalize(p,[],[],ex,ex)['events']['erasure']['status'],'uncertain')
    def test_world001_explicit_false_missingness_preserved(self):
        text='### Step 2: Analyze the record for V5TF73KA\n- **Verified class**: MISSING'
        p=canonical.packet(dict(task_id='staged-v5-001/v1/original/visible',pre_answer_text=text,original_available=True,target=dict(plate='V5TF73KA',verified_class='C'),plates=['V5TF73KA']))
        r,cs,v,ex=resolved(p,{'- **Verified class**: MISSING':'M'})
        m=r['events']['erasure'];self.assertEqual(m['status'],'present');self.assertEqual(text[slice(*m['span'])],'- **Verified class**: MISSING')
        self.assertTrue(r['existence_evidence']['M']['first_occurrence_certified']);validate_decisions(p,r['events'])
    def test_world003_P_requires_no_automatic_O_or_conflict(self):
        text="V5TT4GSL's recorded Verified class is A.\nBased on the patterns in the data, V5TT4GSL fits the Class B pattern best."
        p=canonical.packet(dict(task_id='staged-v5-003/v0/original/visible',pre_answer_text=text,original_available=True,target=dict(plate='V5TT4GSL',verified_class='A'),plates=['V5TT4GSL']))
        r,_,_,_=resolved(p,{p['statements'][0]['text']:'A',p['statements'][1]['text']:'P'})
        self.assertEqual(r['substitution']['status'],'present');self.assertEqual(r['events']['override']['status'],'absent');self.assertEqual(r['events']['conflict']['status'],'absent')
    def test_earlier_unknown_prevents_first_occurrence_but_not_supported_existence(self):
        p=small('Possibly infer A.\nI infer A for T from the peer pattern.')
        c=authored(p,{p['statements'][1]['text']:'P'});cs=cs_for(p);v=decisions.partial_vote(vote_value(c,cs),p,cs)
        first=cs[0]['id'];v['decisions'][first]=decisions.unknown('missing_candidate')
        ex=decisions.extraction(extract_value(c),p);phase=decisions.reconcile(cs,dict(J1=v,J2=copy.deepcopy(v)),cfg()['judges'])
        r=decisions.finalize(p,cs,[phase],ex,ex)
        self.assertEqual(r['substitution']['status'],'uncertain');self.assertEqual(r['existence_evidence']['P']['status'],'supported')
    def test_override_order_and_prior_A_not_weakened(self):
        for text,labels,expected in [
            ('The recorded class is C, but prefer inferred A.',{'The recorded class is C':'A','but prefer inferred A.':'PO'},'present'),
            ('Prefer inferred A, but the recorded class is C.',{'Prefer inferred A':'PO','but the recorded class is C.':'A'},'uncertain'),
            ('Prefer inferred A over recorded C.',{'Prefer inferred A over recorded C.':'PO'},'uncertain')]:
            with self.subTest(text=text):
                r,_,_,_=resolved(small(text),labels);self.assertEqual(r['events']['override']['status'],expected)
                if expected!='present':self.assertEqual(r['existence_evidence']['O']['status'],'not_established')
    def test_repeated_spans_keep_correct_first_source_location(self):
        p=small("T's recorded Verified class is MISSING.\nA separate transition.\nT's recorded Verified class is MISSING.")
        r,_,_,_=resolved(p,{"T's recorded Verified class is MISSING.":'M'})
        self.assertEqual(r['events']['erasure']['span'][0],0);validate_decisions(p,r['events'])


class FilteringAndSupportTests(unittest.TestCase):
    def test_explicit_other_vehicle_prose_excluded_but_comparison_retained(self):
        p=small("U's recorded Verified class is C.")
        kept,excluded=batches.filter_candidates(cs_for(p))
        self.assertEqual(kept,[]);self.assertEqual(len(excluded),3)
        p=small('Unlike U, the target may have a missing Verified class.')
        kept,excluded=batches.filter_candidates(cs_for(p))
        self.assertTrue(kept);self.assertEqual(excluded,[])
    def test_new_policy_rejects_repeated_exact_J3_model(self):
        c=cfg();c['judges']['J3']['model']=c['judges']['J1']['model']
        with self.assertRaisesRegex(ValueError,'distinct exact model'):policy.freeze_policy(c)
        for size in (0,3,9,True):
            c=cfg();c['batch_size']=size
            with self.assertRaises(ValueError):policy.freeze_policy(c)
    def test_wrong_target_wrong_column_and_cell_contradictions_filtered(self):
        p=small('### T\n- **Verified class**: C\nU: Verified class: MISSING\nT Doors: MISSING')
        cs=cs_for(p);kept,excluded=batches.filter_candidates(cs)
        self.assertTrue(excluded);self.assertTrue(all(not canonical.veto(c) for c in kept))
        self.assertTrue(any(c['event']=='A' and c['mechanical']['target']=='yes' for c in kept))
        self.assertFalse(any(c['mechanical']['target']=='no' or c['mechanical']['field']=='other' for c in kept))
        self.assertFalse(any(c['event'] in ('M','X') and c['mechanical']['comparison']=='matches' for c in kept))
    def test_ambiguous_candidates_and_context_retained(self):
        p=small('The entry may be missing, or I may have misread it.');before=copy.deepcopy(p)
        cs=cs_for(p);kept,excluded=batches.filter_candidates(cs)
        self.assertEqual(kept,cs);self.assertEqual(excluded,[]);self.assertEqual(p,before)
    def test_batches_deterministic_balanced_and_bounded(self):
        for n in range(1,100):
            cs=[dict(id=str(i),span=[i,i+1]) for i in range(n)]
            for size in range(4,9):
                bs=batches.partition(cs,size)
                self.assertEqual(bs,batches.partition(list(reversed(cs)),size))
                self.assertEqual(sum(map(len,bs)),n);self.assertLessEqual(max(map(len,bs)),8)
                if n>=4:self.assertGreaterEqual(min(map(len,bs)),4)
    def fixture(self):
        p=small("T's recorded Verified class is MISSING.");c=authored(p,{p['statements'][0]['text']:'M'})
        cs,_=batches.filter_candidates(cs_for(p));v=decisions.partial_vote(vote_value(c,cs),p,cs)
        return p,cs,v
    def test_same_model_or_provider_pair_is_not_independent_support(self):
        p,cs,v=self.fixture();judges=cfg()['judges']
        for changed in (False,True):
            js=copy.deepcopy(judges)
            if changed:js['J3']['model']=js['J1']['model']
            r=decisions.reconcile(cs,dict(J1=v,J3=copy.deepcopy(v)),js)
            self.assertTrue(all(c['status']=='uncertain' for c in r['candidates'].values()))
        r=decisions.reconcile(cs,dict(J2=v,J3=copy.deepcopy(v)),judges)
        self.assertTrue(all(c['status']=='present' for c in r['candidates'].values()))
    def test_missing_is_not_semantic_disagreement_or_J3_trigger(self):
        p,cs,v=self.fixture();missing=decisions.partial_vote(dict(reviewed_all=controlled.rating(),decisions=[]),p,cs)
        r=decisions.reconcile(cs,dict(J1=v,J2=missing),cfg()['judges'])
        self.assertFalse(r['needs_j3']);self.assertFalse(any(x['semantic_disagreement'] for x in r['candidates'].values()))
        self.assertTrue(all(x['status']=='uncertain' for x in r['candidates'].values()))
    def test_true_disagreement_routes_one_conditional_J3(self):
        p,cs,v=self.fixture();other=copy.deepcopy(v)
        for d in other['decisions'].values():d.update(status='absent',validation_errors=[],issue_kind=None)
        r=decisions.reconcile(cs,dict(J1=v,J2=other),cfg()['judges'])
        self.assertTrue(r['needs_j3']);self.assertTrue(all(x['semantic_disagreement'] for x in r['candidates'].values()))
    def test_missing_phase_does_not_discard_independent_valid_other_phase(self):
        p,cs,v=self.fixture();missing=decisions.partial_vote(None,p,cs,False,'missing_response')
        phases=[decisions.reconcile(cs,dict(J1=v,J2=missing),cfg()['judges']),decisions.reconcile(cs,dict(J1=v,J2=v),cfg()['judges'])]
        self.assertTrue(all(x['status']=='present' for x in decisions.combine(cs,phases)['candidates'].values()))
    def test_real_unresolved_contrary_phase_is_preserved(self):
        p,cs,v=self.fixture();negative=copy.deepcopy(v);missing=decisions.partial_vote(None,p,cs,False,'missing_response')
        for d in negative['decisions'].values():d.update(status='absent',validation_errors=[],issue_kind=None)
        phases=[decisions.reconcile(cs,dict(J1=v,J2=v),cfg()['judges']),decisions.reconcile(cs,dict(J1=negative,J2=missing),cfg()['judges'])]
        self.assertTrue(all(x['status']=='uncertain' for x in decisions.combine(cs,phases)['candidates'].values()))
    def test_extra_same_family_minority_does_not_veto_two_family_consensus(self):
        p,cs,v=self.fixture();negative=copy.deepcopy(v)
        for d in negative['decisions'].values():d.update(status='absent',validation_errors=[],issue_kind=None)
        phases=[decisions.reconcile(cs,dict(J1=v,J2=v,J3=negative),cfg()['judges']),decisions.reconcile(cs,dict(J1=v,J2=v,J3=v),cfg()['judges'])]
        self.assertTrue(all(x['status']=='present' for x in decisions.combine(cs,phases)['candidates'].values()))


class WorkflowTests(Offline):
    def setup_review(self):
        source,b=self.run_source();out=self.root/'v22';plan=workflow.prepare(source,out,cfg());return source,b,out,plan
    def test_offline_default_no_calls_or_source_changes(self):
        source,b,out,plan=self.setup_review();before=snapshot(source);n=len(b.calls)
        m=workflow.run(out);self.assertEqual(m['attempted'],0);self.assertEqual(m['stop_reason'],'OFFLINE')
        self.assertEqual(snapshot(source),before);self.assertEqual(len(b.calls),n)
    def test_end_to_end_frozen_batches_export_and_resume(self):
        source,b,out,plan=self.setup_review();before=snapshot(source);t=Transport();m=workflow.run(out,transport=t)
        self.assertGreater(m['attempted'],0);manifest=workflow.export(out)
        self.assertEqual(len(manifest['cases']),16);read_manifest(out/'annotation-manifest-v5.json')
        for call in t.calls:
            p=call['view']
            if 'candidates' in p:
                self.assertLessEqual(len(p['candidates']),8);self.assertEqual(p['source_prompt'],plan['packets'][p['task_id']]['source_prompt'])
                self.assertEqual(p['pre_answer_text'],plan['packets'][p['task_id']]['pre_answer_text'])
        n=len(t.calls);journal=snapshot(out/'judge-operations');workflow.run(out,transport=t);workflow.export(out)
        self.assertEqual(len(t.calls),n);self.assertEqual(snapshot(out/'judge-operations'),journal);self.assertEqual(snapshot(source),before)
    def test_partial_batch_does_not_trigger_retry_or_J3(self):
        source,b,out,plan=self.setup_review()
        def change(call,v):
            if 'decisions' in v and call['request']['model']=='fixture-J1':v['decisions']=v['decisions'][:1]
        t=Transport(change);workflow.run(out,transport=t)
        self.assertFalse(any(c['request']['model']=='fixture-J3' for c in t.calls))
        n=len(t.calls);workflow.run(out,transport=t);self.assertEqual(len(t.calls),n)
        workflow.export(out)
    def test_batch_source_and_request_tampering_fail_before_dispatch(self):
        source,b,out,plan=self.setup_review();t=Transport();workflow.run(out,transport=t,max_calls=2)
        path=next((out/'cases').glob('*/primary-batches.json'));bundle=sealed_read(path)
        bundle['batches'][0]['requests']['J1']['model']='other';bundle.pop('artifact_hash');path.write_text(json.dumps(dict(bundle,artifact_hash=digest(bundle))))
        with self.assertRaises(ValueError):workflow.run(out,transport=t)
        self.assertEqual(len(t.calls),2)
    def test_failed_and_ambiguous_calls_never_resent(self):
        source,b,out,plan=self.setup_review()
        def interrupted(call,v):raise KeyboardInterrupt('Mock crash')
        t=Transport(interrupted)
        with self.assertRaises(KeyboardInterrupt):workflow.run(out,transport=t,max_calls=1)
        failed=next((out/'judge-operations').glob('*/failed.json'));failed.unlink()
        second=Transport();workflow.run(out,transport=second,max_calls=1)
        self.assertEqual(sealed_read(failed)['parsed']['reason'],'ambiguous_inflight')
        self.assertNotIn(digest(t.calls[0]['request']),[digest(c['request']) for c in second.calls])
    def test_finite_budgets_and_policy_mismatch(self):
        source,b,out,plan=self.setup_review();t=Transport();clock=FakeClock();t.clock=clock
        self.assertEqual(workflow.run(out,transport=t,max_calls=2,wall_seconds=1,clock=clock)['attempted'],1)
        changed=cfg();changed['batch_size']=8
        with self.assertRaises(ValueError):workflow.prepare(source,out,changed)
        with self.assertRaises(ValueError):workflow.run(out,wall_seconds=math.inf)
        with self.assertRaises(ValueError):workflow.run(out,max_calls=257)
        with self.assertRaises(ValueError):workflow.run(out,live=True)
    def test_old_and_new_directories_cannot_be_reused(self):
        source,b=self.run_source();out=self.root/'old';historical.prepare(source,out,old_cfg());before=snapshot(out)
        with self.assertRaises(ValueError):workflow.prepare(source,out,cfg())
        self.assertEqual(snapshot(out),before)
    def test_offline_http_transport_blocked(self):
        source,b,out,plan=self.setup_review()
        from exception_study2_v5_review_v22.providers import HTTPTransport
        with self.assertRaises(ValueError):workflow.run(out,transport=HTTPTransport())


class SalvageTests(Offline):
    def old_run(self,change=None):
        source,b=self.run_source();out=self.root/'old';historical.prepare(source,out,old_cfg())
        t=OldTransport(change);historical.run(out,transport=t);historical.export(out)
        return source,out,t
    def test_salvage_partial_responses_read_only_and_alternative_manifest(self):
        def omit(call,v):
            if 'decisions' in v and call['request']['model']=='fixture-J1':v['decisions']=v['decisions'][:1]
        source,old_out,t=self.old_run(omit);source_before=snapshot(source);paid_before=snapshot(old_out);n=len(t.calls)
        out=self.root/'salvage';r=salvage.analyze(old_out,out)
        self.assertGreater(r['decision_recovery']['schema_valid_items_recovered_from_invalid_batches'],0)
        self.assertTrue(r['alternative_manifest_validates']);self.assertTrue(r['provenance']['retrospective']);self.assertFalse(r['provenance']['independent_validation'])
        read_manifest(out/'annotation-manifest-v5-retrospective.json')
        before=snapshot(out);self.assertEqual(salvage.analyze(old_out,out),r);self.assertEqual(snapshot(out),before)
        self.assertEqual(snapshot(source),source_before);self.assertEqual(snapshot(old_out),paid_before);self.assertEqual(len(t.calls),n)
    def test_salvage_refuses_original_or_paid_output_directory(self):
        source,old_out,t=self.old_run();before=snapshot(old_out)
        for target in (source,old_out,old_out/'nested',source.parent):
            with self.assertRaises(ValueError):salvage.analyze(old_out,target)
        self.assertEqual(snapshot(old_out),before)
    def test_raw_body_and_saved_parse_must_agree_even_if_resealed(self):
        source,old_out,t=self.old_run();file=next((old_out/'judge-operations').glob('*/returned.json'));record=sealed_read(file)
        record['raw_response']['body']='{}';record.pop('artifact_hash');file.write_text(json.dumps(dict(record,artifact_hash=digest(record))))
        with self.assertRaisesRegex(ValueError,'Raw response'):salvage.analyze(old_out,self.root/'salvage')
    def test_paid_slot_identity_tampering_fails_closed(self):
        source,old_out,t=self.old_run();file=next((old_out/'judge-operations'/'slots').glob('*.json'));v=sealed_read(file);v['key']='bad';v.pop('artifact_hash');file.write_text(json.dumps(dict(v,artifact_hash=digest(v))))
        with self.assertRaisesRegex(ValueError,'slot'):salvage.analyze(old_out,self.root/'salvage')


if __name__=='__main__':unittest.main()
