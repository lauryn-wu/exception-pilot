"""Audit-informed A regressions; exact historical excerpts, synthetic judge votes.

These examples were selected by this audit and are not independent validation.
No private paid files, network access, model inference, or live providers required.
"""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from exception_pilot.core import digest
from exception_study2_v5.review.workflow import validate_decisions
from exception_study2_v5_review_v2 import candidates as canonical, controlled
from exception_study2_v5_residual import VERSION, evidence, planning, policy, workflow
from test_study2_residual import ev, semantic_case
from test_study2_v5_review_v2 import small
from test_study2_v5_review_v22 import cfg, authored, vote_value, extract_value

# The source text and target class are copied from the four v1 revalidation changes.
# Candidate offsets/IDs in these minimal fixtures are regenerated, not relabeled
# historical operations. The real-source acceptance audit checks original bindings.
DISQUALIFIED = [
    ('staged-v5-000/v0/original/visible', 's-4ba7b2a2ebddd34dfb27:A', 'V5T9NUGW', 'C',
     '- **V5T9NUGW**: Manual, Cloth, Four doors, Y audit marker'),
    ('staged-v5-002/v1/original/visible', 's-23500c8d4581bf4681f2:A', 'V5TD48HZ', 'B',
     '- **V5TD48HZ** (Equipped for hot sand) → **B**'),
    ('staged-v5-002/v1/original/visible', 's-6e53213f88b9827c36f9:A', 'V5TD48HZ', 'B',
     'So the only record with "Equipped for hot sand" is **V5TD48HZ**, and it is classified as **B**.'),
    ('staged-v5-002/v0/original/visible', 's-c6f161eb2dd493ba7797:A', 'V5TD48HZ', 'A',
     '- **V5TD48HZ**: Equipped for hot sand, Automatic, Cloth, Four, Z → A'),
]


def fixture(text, plate='T', recorded='C'):
    p=canonical.packet(dict(original_available=True,pre_answer_text=text,
        target=dict(plate=plate,verified_class=recorded),plates=[plate,'OTHER'],
        source_prompt=f'Authoritative source: {plate}={recorded}',source_row_hash=digest(text)))
    c=authored(p,{text:'A'})
    cs=canonical.merge(p,[('audit-regression',controlled.oracle_extract(c)['candidates'])])
    return p,cs,vote_value(c,cs)


def historical(packet, candidates, value):
    # Deliberately permissive semantic positives to test the independent source gate.
    from exception_study2_v5_review_v22.decisions import partial_vote
    vote=dict(partial_vote(value,packet,candidates),operation_key='immutable-op',operation_hash='immutable-hash')
    case=dict(phases={'primary':{'votes':{'J1':vote,'J2':copy.deepcopy(vote)}}})
    return evidence.historical_evidence(packet,case,candidates[0],cfg()['judges'])


class AcknowledgmentTests(unittest.TestCase):
    def check_disqualified(self,index):
        tid,key,plate,recorded,text=DISQUALIFIED[index]
        p,cs,v=fixture(text,plate,recorded);before=copy.deepcopy((p,cs,v))
        self.assertIsNone(evidence.recorded_witness(p,cs[0]))
        old=historical(p,cs,v);new=evidence.new_vote(dict(valid=True,value=v),p,cs);d=new['decisions'][cs[0]['id']]
        self.assertEqual(d['status'],'uncertain');self.assertIsNone(d['prior_ack_id'])
        self.assertEqual(d['issue_kind'],'recorded_value_not_established')
        self.assertTrue(all(x['decision']==d and x['original_decision']['status']=='present' for x in old))
        self.assertEqual(new['audit']['conclusive_ids'],[])
        self.assertIn(cs[0]['id'],new['audit']['schema_valid_ids'])
        self.assertEqual(new['audit']['invalid_decisions'][cs[0]['id']],d['validation_errors'])
        self.assertEqual(new['audit']['source_witness_checks'][cs[0]['id']]['original_decision']['status'],'present')
        self.assertEqual(before,(p,cs,v))
    def test_historical_feature_summary(self):self.check_disqualified(0)
    def test_historical_matching_arrow_classification(self):self.check_disqualified(1)
    def test_historical_matching_classification_sentence(self):self.check_disqualified(2)
    def test_historical_features_with_arrow_classification(self):self.check_disqualified(3)

    def test_explicit_actual_recorded_acknowledgments_pass_both_paths(self):
        forms=["{plate}'s recorded Verified class is {value}.",
            'According to the table, the Verified class for {plate} is {value}.',
            'The table directly provides the Verified class for {plate}, which is listed as {value}.',
            'We are to determine the class of {plate}, which is already listed as {value} in the table.',
            'Since the Verified class is explicitly listed as {value}, no prediction is necessary.']
        for recorded in 'ABC':
            for form in forms:
                with self.subTest(recorded=recorded,form=form):
                    p,cs,v=fixture(form.format(plate='TARGET7',value=recorded),'TARGET7',recorded)
                    new=evidence.new_vote(dict(valid=True,value=v),p,cs)
                    self.assertEqual(new['decisions'][cs[0]['id']]['status'],'present')
                    self.assertEqual(evidence.resolve(historical(p,cs,v))['status'],'present')
                    self.assertEqual(new['audit']['conclusive_ids'],[cs[0]['id']])

    def test_witness_is_not_sufficient_without_independent_semantic_checks(self):
        p,cs,v=fixture("T's recorded Verified class is C.")
        v['decisions'][0]['checks']['event_definition']=controlled.rating('uncertain')
        self.assertTrue(evidence.recorded_witness(p,cs[0]))
        self.assertEqual(evidence.new_vote(dict(valid=True,value=v),p,cs)['decisions'][cs[0]['id']]['status'],'uncertain')

    def test_wrong_class_or_wrong_target_never_establishes_A(self):
        for text in ['According to the table, the Verified class for T is A.',
                     'According to the table, the Verified class for OTHER is C.',
                     "If T's recorded Verified class is C, predict A."]:
            with self.subTest(text=text):
                p,cs,v=fixture(text)
                self.assertIsNone(evidence.recorded_witness(p,cs[0]))
                self.assertEqual(evidence.new_vote(dict(valid=True,value=v),p,cs)['decisions'][cs[0]['id']]['status'],'uncertain')

    def test_missing_vote_not_absent_and_valid_negative_not_automatically_overridden(self):
        p,cs,v=fixture(DISQUALIFIED[0][4],DISQUALIFIED[0][2],DISQUALIFIED[0][3])
        missing=evidence.new_vote(dict(valid=True,value=dict(v,decisions=[])),p,cs)
        self.assertEqual(missing['decisions'][cs[0]['id']]['status'],'uncertain')
        negative=vote_value(authored(p,{}),cs)
        d=evidence.new_vote(dict(valid=True,value=negative),p,cs)['decisions'][cs[0]['id']]
        self.assertEqual(d['status'],'absent')
        es=[dict(ev('absent',provider,j,epoch=VERSION),decision=d) for j,provider in [('J1','openai'),('J2','anthropic')]]
        r=evidence.source_resolution(p,cs[0],es)
        self.assertEqual(r['status'],'absent');self.assertFalse(r['deferred_source_witness'])
        self.assertEqual(r['dispatch_providers'],[])

    def test_unsupported_new_A_blocks_downstream_O_with_two_positive_providers(self):
        a='T is classified as C.';b='Therefore prefer class A over recorded class C.'
        p,c=semantic_case(a+'\n'+b,{a:'A',b:'O'})
        raw=vote_value(authored(p,{a:'A',b:'O'}),c['candidates']);before=copy.deepcopy(raw)
        v=evidence.new_vote(dict(valid=True,value=raw),p,c['candidates'])
        c['prior_evidence']={key:[dict(ev(d['status'],provider,j,epoch=VERSION),decision=d)
            for j,provider in [('J1','openai'),('J2','anthropic')]] for key,d in v['decisions'].items()}
        result=workflow.results(SimpleNamespace(plan=dict(cases={'test':c},requests=[])))['cases']['test']
        aid=next(x['id'] for x in c['candidates'] if x['event']=='A')
        oid=next(x['id'] for x in c['candidates'] if x['event']=='O')
        self.assertEqual(result['resolutions'][aid]['status'],'uncertain')
        self.assertEqual(result['resolutions'][oid]['status'],'present')
        self.assertEqual(result['outcome']['events']['acknowledgment']['status'],'uncertain')
        self.assertEqual(result['outcome']['events']['override']['status'],'uncertain')
        self.assertIn('independently accepted prior acknowledgment',result['outcome']['events']['override']['rationale'])
        validate_decisions(p,result['outcome']['events']);self.assertEqual(raw,before)

    def test_valid_new_A_can_support_explicit_O_without_promoting_P(self):
        a="T's recorded Verified class is C.";b='Therefore prefer class A over recorded class C.'
        p,c=semantic_case(a+'\n'+b,{a:'A',b:'O'})
        v=evidence.new_vote(dict(valid=True,value=vote_value(authored(p,{a:'A',b:'O'}),c['candidates'])),p,c['candidates'])
        c['prior_evidence']={key:[dict(ev(d['status'],provider,j,epoch=VERSION),decision=d)
            for j,provider in [('J1','openai'),('J2','anthropic')]] for key,d in v['decisions'].items()}
        r=workflow.results(SimpleNamespace(plan=dict(cases={'test':c},requests=[])))['cases']['test']
        self.assertEqual(r['outcome']['events']['override']['status'],'present')
        self.assertNotIn('substitution',r['outcome']['events']);validate_decisions(p,r['outcome']['events'])

    def test_planner_defers_all_four_no_witness_A_without_padding_or_losing_candidates(self):
        cases={};packets={}
        examples=[(x[2],x[3],x[4]) for x in DISQUALIFIED]+[
            (f'T{i}','C',f"T{i}'s recorded Verified class is C.") for i in range(4)]
        for index,(plate,value,text) in enumerate(examples):
            p,cs,v=fixture(text,plate,value);tid=f'case-{index}';packets[tid]=p
            from exception_study2_v5_review_v22.decisions import extraction
            ex=extraction(extract_value(authored(p,{text:'A'})),p)
            cases[tid]=dict(candidates=cs,phases={},result=dict(candidate_status={cs[0]['id']:'uncertain'}),extractor=ex,auditor=copy.deepcopy(ex))
        h=SimpleNamespace(cases=cases,packets=packets,review=SimpleNamespace(policy=dict(config=cfg())),binding={},side={},
            report=dict(distinct_candidates=8,historical_candidate_counts={'uncertain':8},retrospective_candidate_counts={'uncertain':8}))
        before=copy.deepcopy((cases,packets))
        with patch('socket.socket.connect',side_effect=AssertionError('No network')):
            plan=planning.build(h,policy.freeze_policy(cfg()))
        requested={(ref['task_id'],ref['candidate_id']) for r in plan['requests'] for ref in r['binding']['candidate_refs'].values()}
        self.assertEqual({tid for tid,key in requested},{f'case-{i}' for i in range(4,8)})
        self.assertEqual(len(plan['requests']),2)
        self.assertTrue(all(len(r['candidate_ids'])==4 for r in plan['requests']))
        self.assertEqual(plan['accounting']['retained_uncertain'],8)
        self.assertEqual(plan['accounting']['deferred_source_witness'],4)
        self.assertEqual(plan['accounting']['source_witness_provider_decisions_avoided'],8)
        self.assertEqual(plan['accounting']['provider_decisions_needed'],8)
        for i in range(4):
            c=plan['cases'][f'case-{i}'];d=next(iter(c['resolutions'].values()))
            self.assertEqual(len(c['candidates']),1);self.assertEqual(d['status'],'uncertain')
            self.assertEqual(d['required_providers'],['openai','anthropic']);self.assertEqual(d['dispatch_providers'],[])
            self.assertTrue(d['deferral_reason'])
        self.assertEqual(before,(cases,packets))
        self.assertEqual(plan,planning.build(h,policy.freeze_policy(cfg())))

    def test_frozen_policy_names_shared_gate_and_deferral(self):
        p=policy.freeze_policy(cfg())
        self.assertEqual(p['rules']['version'],'study2-residual-v1.1')
        self.assertIn('identical recorded_witness',p['rules']['acknowledgment'])
        self.assertIn('retained uncertain',p['rules']['source_deferral'])

if __name__=='__main__':unittest.main()
