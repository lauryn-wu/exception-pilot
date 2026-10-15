"""Focused follow-up: authored semantic fixtures and MOCK transports only."""
import copy
import json
import subprocess
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.review.workflow import validate_decisions
from exception_study2_v5_review_v2 import candidates, controlled, controlled_balanced, decisions, policy, workflow
from test_study2_v5 import Offline
from test_study2_v5_review_v2 import cfg, small, cs_for, Transport, snapshot


def resolve(p, labels, change=None):
    # Explicit authored labels, never keyword-based natural-text classification.
    case=dict(packet=p,statement_truth={s['id']:list(labels.get(s['text'],'')) for s in p['statements']})
    raw=controlled.oracle_extract(case);ex=candidates.extraction(raw,p)
    cs=candidates.merge(p,[('structural',candidates.structural_candidates(p)),('authored',raw['candidates'])])
    value=controlled.oracle_vote(case,cs)
    if change:change(value,cs)
    first=decisions.vote(value,p,cs);second=decisions.vote(copy.deepcopy(value),p,cs)
    return decisions.finalize(p,cs,[decisions.reconcile(cs,dict(J1=first,J2=second))],ex,ex)


class ClauseTests(unittest.TestCase):
    def test_requested_compound_distinct_ordered_spans_pass_frozen_validator(self):
        p=small('The recorded class is C, but we should prefer inferred A.')
        self.assertEqual([s['text'] for s in p['statements']],['The recorded class is C','but we should prefer inferred A.'])
        r=resolve(p,{'The recorded class is C':'A','but we should prefer inferred A.':'PO'})
        a,o=r['events']['acknowledgment'],r['events']['override']
        self.assertEqual((a['status'],o['status']),('present','present'))
        self.assertLessEqual(a['span'][1],o['span'][0]);self.assertNotEqual(a['span'],o['span'])
        for d in (a,o):self.assertEqual(p['pre_answer_text'][slice(*d['span'])],d['text'])
        validate_decisions(p,r['events'])

    def test_unicode_offsets_enclosing_scope_and_repeated_clause_ids(self):
        text='é 🚘\nThe recorded class is C, but prefer inferred A.\nThe recorded class is C, but prefer inferred A.'
        p=small(text);clauses=[s for s in p['statements'] if 'enclosing_statement' in s]
        self.assertEqual(len(clauses),4);self.assertEqual(len({s['id'] for s in clauses}),4)
        for s in clauses:
            parent=s['enclosing_statement'];self.assertEqual(text[slice(*parent['span'])],parent['text'])
            self.assertEqual(text[slice(*s['span'])],s['text']);self.assertEqual(s['id'],'s-'+digest([*s['span'],s['text']])[:20])

    def test_yet_and_em_dash_localize_without_consuming_assertions(self):
        for separator in (', yet ', ' — but ', ', however '):
            with self.subTest(separator=separator):
                p=small('The recorded class is C'+separator+'I prefer inferred A.')
                self.assertEqual(len(p['statements']),2)
                self.assertEqual(p['statements'][0]['text'],'The recorded class is C')
                self.assertTrue(p['statements'][1]['text'].endswith('I prefer inferred A.'))

    def test_three_clauses_preserve_order_and_exact_offsets(self):
        p=small('The recorded class is C, but prefer inferred A, whereas the earlier draft retained C.')
        self.assertEqual(len(p['statements']),3)
        self.assertEqual([s['clause_index'] for s in p['statements']],[0,1,2])
        for a,b in zip(p['statements'],p['statements'][1:]):self.assertLess(a['span'][1],b['span'][0])

    def test_whitespace_and_markdown_bullet_prose_keep_source_characters(self):
        p=small('  - **The recorded class is C, but prefer inferred A.**  ')
        self.assertEqual([s['text'] for s in p['statements']],['- **The recorded class is C','but prefer inferred A.**'])
        for s in p['statements']:self.assertEqual(p['pre_answer_text'][slice(*s['span'])],s['text'])

    def test_quoted_conditional_denied_and_question_scope_not_split(self):
        for text in [
            '"The recorded class is C, but prefer inferred A."',
            "The draft says 'The recorded class is C, but prefer inferred A.'",
            'If the recorded class were C, but we preferred inferred A, this would be hypothetical.',
            'Suppose the recorded class is C, but prefer inferred A.',
            'It is false that the recorded class is C, but prefer inferred A.',
            'I deny that the recorded class is C, but prefer inferred A.',
            'The recorded class is C, but should we prefer inferred A?',
        ]:
            with self.subTest(text=text):
                p=small(text);self.assertEqual(len(p['statements']),1)
                r=resolve(p,{})
                self.assertTrue(all(d['status']=='absent' for d in r['events'].values()))

    def test_negated_override_keeps_negation_and_does_not_accept_O(self):
        p=small('The recorded class is C, but we should not prefer inferred A.')
        self.assertIn('not prefer',p['statements'][1]['text'])
        r=resolve(p,{'The recorded class is C':'A'})
        self.assertEqual(r['events']['acknowledgment']['status'],'present')
        self.assertEqual(r['events']['override']['status'],'absent')

    def test_conflict_and_prediction_are_not_automatically_override(self):
        for right,label in [('but this conflicts with inferred A.','C'),('but I predict A from the peer pattern.','P')]:
            with self.subTest(right=right):
                p=small('The recorded class is C, '+right)
                r=resolve(p,{'The recorded class is C':'A',right:label})
                self.assertEqual(r['events']['override']['status'],'absent')

    def test_valid_json_does_not_certify_explicit_preference(self):
        p=small('The recorded class is C, but prefer inferred A.')
        def reject(value,cs):
            lookup={c['id']:c for c in cs}
            for d in value['decisions']:
                if lookup[d['candidate_id']]['event']=='O':d['checks']['explicit_preference']=controlled.rating('uncertain')
        r=resolve(p,{'The recorded class is C':'A','but prefer inferred A.':'PO'},reject)
        self.assertEqual(r['events']['override']['status'],'uncertain')

    def test_O_before_A_or_without_A_still_fails(self):
        for text,labels in [
            ('Prefer inferred A, but the recorded class is C.',{'Prefer inferred A':'O','but the recorded class is C.':'A'}),
            ('Prefer inferred A over the recorded C.',{'Prefer inferred A over the recorded C.':'O'}),
        ]:
            with self.subTest(text=text):
                self.assertEqual(resolve(small(text),labels)['events']['override']['status'],'uncertain')

    def test_localization_alone_never_supplies_semantic_certificates(self):
        p=small('The recorded class is C, but prefer inferred A.');cs=cs_for(p)
        r=decisions.finalize(p,cs,[],{}, {})
        self.assertEqual(r['events']['acknowledgment']['status'],'uncertain')
        self.assertEqual(r['events']['override']['status'],'uncertain')
        self.assertTrue(all(not d['certificates'] for d in r['events'].values()))

    def test_table_field_list_and_simple_statement_ids_unchanged(self):
        for text in ['| T | C, but A |','T: Verified class: C, but the note differs.',
                     "T's recorded Verified class is C.","T's recorded Verified class is C.\nPrefer inferred A."]:
            with self.subTest(text=text):self.assertEqual(small(text)['statements'],candidates.segment(text))

    def test_family_prompts_and_semantic_checks_still_frozen(self):
        self.assertEqual(policy.CHECKS,('target_identity','asserted','verified_field','value_role','event_definition','prior_acknowledgment','recorded_relationship','explicit_preference'))
        for prompt in policy.RUBRICS.values():
            self.assertIn('enclosing_statement',prompt);self.assertIn(policy.CODEBOOK,prompt)
            self.assertIn(policy.FAMILY_PROMPTS['M'],prompt);self.assertIn(policy.FAMILY_PROMPTS['O'],prompt)


class BalancedSuiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.cases=controlled_balanced.generate()

    def test_full_factorial_balance_in_each_scenario(self):
        self.assertEqual(len(self.cases),3600)
        for scenario,_,_ in controlled_balanced.SCENARIOS:
            subset=[c for c in self.cases if c['scenario']==scenario]
            self.assertEqual(len(subset),180)
            self.assertEqual(set(Counter(c['recorded'] for c in subset).values()),{60})
            self.assertEqual(set(Counter(c['inferred'] for c in subset).values()),{60})
            self.assertEqual(set(Counter((c['recorded'],c['inferred']) for c in subset).values()),{30})
            self.assertEqual(set(Counter(c['target_id'] for c in subset).values()),{60})
            self.assertEqual(set(Counter(c['row_position'] for c in subset).values()),{18})
            self.assertEqual(len({(c['recorded'],c['inferred'],c['target_id'],c['row_position']) for c in subset}),180)

    def test_rows_and_alternatives_match_authoritative_source(self):
        for c in self.cases:
            p=c['packet'];t=p['target'];row=p['source_table'].splitlines()[c['row_position']+2]
            self.assertEqual(row,f"| {c['target_id']} | {c['recorded']} |")
            self.assertEqual(t['row'],row);self.assertEqual(t['target_row_index_base'],0)
            self.assertEqual(t['target_row_number_one_based'],c['row_position']+1)
            self.assertNotEqual(c['recorded'],c['inferred'])

    def test_authored_gold_aligns_without_relabelling_split_fragments(self):
        for c in self.cases:
            p=c['packet'];statements={tuple(s['span']):s for s in p['statements']}
            for g in c['authored_gold']:
                s=statements[tuple(g['span'])];self.assertEqual(s['text'],g['text'])
                self.assertEqual(p['pre_answer_text'][slice(*g['span'])],g['text'])
                self.assertEqual(c['statement_truth'][s['id']],g['events'])

    def test_new_suite_deterministic_versioned_and_audit_informed(self):
        self.assertEqual(self.cases,controlled_balanced.generate())
        self.assertEqual(controlled_balanced.SUITE_VERSION,'controlled-v2.1-balanced-audit1')
        # Freeze the independently stored generator output checksum before accepting results.
        self.assertEqual(digest(self.cases),BALANCED_SUITE_HASH)
        self.assertEqual(len({c['id'] for c in self.cases}),3600)

    def test_old_suite_hash_and_frozen_results_are_preserved(self):
        self.assertEqual(digest(controlled.generate()),'48d1a7b6b4b76375f69f229cc8c0977d930d0ff493b843f29e60d4e739c07fa8')
        old=json.loads(Path('audits/study2-v5-review-v2/controlled-results.json').read_text())
        self.assertEqual(controlled.evaluate(),old)

    def test_metrics_separate_oracle_from_semantic_validation(self):
        r=controlled_balanced.evaluate()
        self.assertTrue(r['provenance']['audit_informed']);self.assertFalse(r['provenance']['independent_validation'])
        self.assertIn('NOT TESTED',r['real_semantic_validation']);self.assertEqual(r['exact_alignment'],1)
        self.assertEqual(r['ordered_nonoverlapping_overrides'],540)
        for e in policy.EVENTS:
            self.assertEqual(r['oracle_wired_pipeline'][e]['f1'],1)
            self.assertEqual(r['production_without_judges'][e]['abstention_rate'],1)


class SmokeSelectionTests(Offline):
    CASE='staged-v5-001/v1/original/visible'
    def setup_review(self):
        source,b=self.run_source();out=self.root/'review';plan=workflow.prepare(source,out,cfg())
        self.assertIn(self.CASE,plan['case_ids']);return source,b,out,plan

    def test_requested_case_exactly_four_calls_and_repeat_caches(self):
        source,b,out,plan=self.setup_review();before=snapshot(source);t=Transport()
        m=workflow.run(out,transport=t,stage='smoke',case_id=self.CASE,max_calls=128)
        self.assertEqual(m['attempted'],4);self.assertEqual(len(t.calls),4)
        self.assertEqual({c['view']['task_id'] for c in t.calls},{self.CASE})
        self.assertFalse(any(c['request']['model']=='fixture-J3' for c in t.calls))
        journal_before=snapshot(out/'judge-operations')
        self.assertEqual(workflow.run(out,transport=t,stage='smoke',case_id=self.CASE)['attempted'],0)
        self.assertEqual(workflow.run(out,transport=t,stage='smoke')['attempted'],0)
        self.assertEqual(len(t.calls),4);self.assertEqual(snapshot(out/'judge-operations'),journal_before)
        self.assertEqual(sealed_read(out/'smoke-selection-v2.json')['case_id'],self.CASE)
        self.assertEqual(snapshot(source),before);self.assertFalse((out/'annotation-manifest-v5.json').exists())

    def test_selection_cannot_switch_to_gain_four_more_calls(self):
        source,b,out,plan=self.setup_review();t=Transport();workflow.run(out,transport=t,stage='smoke',case_id=self.CASE)
        before=snapshot(out)
        other=next(tid for tid in plan['case_ids'] if tid!=self.CASE)
        with self.assertRaisesRegex(ValueError,'immutable'):workflow.run(out,transport=t,stage='smoke',case_id=other)
        self.assertEqual(len(t.calls),4);self.assertEqual(snapshot(out),before)

    def test_unknown_direct_and_empty_id_fail_before_any_calls(self):
        source,b,out,plan=self.setup_review();t=Transport();before=snapshot(out)
        for tid in ('not-a-case',self.CASE.replace('/visible','/direct'),''):
            with self.subTest(tid=tid),self.assertRaisesRegex(ValueError,'visible case'):
                workflow.run(out,transport=t,stage='smoke',case_id=tid)
        self.assertFalse(t.calls);self.assertEqual(snapshot(out),before)

    def test_case_option_rejected_outside_smoke(self):
        with self.assertRaisesRegex(ValueError,'only supported for smoke'):
            workflow.run(self.root/'nonexistent',case_id=self.CASE)
        self.assertFalse((self.root/'nonexistent').exists())

    def test_unavailable_selected_original_fails_before_journal(self):
        source,b,out,plan=self.setup_review();review=workflow.Review(out)
        review.plan['packets'][self.CASE]['original_available']=False;t=Transport()
        with patch.object(workflow,'Review',return_value=review),self.assertRaisesRegex(ValueError,'unavailable'):
            workflow.run(out,transport=t,stage='smoke',case_id=self.CASE)
        self.assertFalse(t.calls);self.assertFalse((out/'judge-operations').exists())

    def test_default_first_available_and_tighter_limit_resume_same_slots(self):
        source,b,out,plan=self.setup_review();t=Transport()
        self.assertEqual(workflow.run(out,transport=t,stage='smoke',max_calls=2)['attempted'],2)
        self.assertEqual(workflow.run(out,transport=t,stage='smoke',max_calls=4)['attempted'],2)
        self.assertEqual(len(t.calls),4);self.assertEqual({c['view']['task_id'] for c in t.calls},{plan['case_ids'][0]})

    def test_selected_smoke_then_full_resume_does_not_resend(self):
        source,b,out,plan=self.setup_review();t=Transport()
        workflow.run(out,transport=t,stage='smoke',case_id=self.CASE)
        self.assertEqual(workflow.run(out,transport=t)['attempted'],92)
        self.assertEqual(len(t.calls),96);self.assertEqual(len({digest(c['request']) for c in t.calls}),96)
        workflow.export(out)

    def test_selected_smoke_terminal_http_error_never_retried(self):
        source,b,out,plan=self.setup_review()
        class Failed:
            kind='MOCK'
            def __init__(self):self.calls=[]
            def __call__(self,*args):self.calls.append(args);return dict(status=400,body='{"error":"offline fixture"}')
        t=Failed();workflow.run(out,transport=t,stage='smoke',case_id=self.CASE)
        before=snapshot(out/'judge-operations');workflow.run(out,transport=t,stage='smoke',case_id=self.CASE)
        self.assertEqual(len(t.calls),4);self.assertEqual(snapshot(out/'judge-operations'),before)

    def test_selected_smoke_ambiguous_interruption_never_resends(self):
        source,b,out,plan=self.setup_review()
        def interrupted(call,value):raise KeyboardInterrupt('Mock interruption')
        first=Transport(interrupted)
        with self.assertRaises(KeyboardInterrupt):workflow.run(out,transport=first,stage='smoke',case_id=self.CASE)
        failed=next((out/'judge-operations').glob('*/failed.json'));failed.unlink()  # Synthetic crash window only.
        second=Transport();workflow.run(out,transport=second,stage='smoke',case_id=self.CASE)
        self.assertEqual(sealed_read(failed)['parsed']['reason'],'ambiguous_inflight')
        self.assertEqual(len(first.calls)+len(second.calls),4)
        self.assertNotIn(digest(first.calls[0]['request']),[digest(c['request']) for c in second.calls])

    def test_cli_case_id_is_smoke_only_and_forwarded(self):
        from exception_study2_v5_review_v2 import __main__ as cli
        args=['review','smoke','--output','unused','--case-id',self.CASE,'--max-calls','4']
        with patch.object(sys,'argv',args),patch.object(cli,'run',return_value={}) as run,patch('builtins.print'):
            cli.main()
        self.assertEqual(run.call_args.kwargs['case_id'],self.CASE);self.assertEqual(run.call_args.kwargs['stage'],'smoke')
        help_result=subprocess.run([sys.executable,'-B','-m','exception_study2_v5_review_v2','smoke','--help'],capture_output=True,text=True)
        self.assertEqual(help_result.returncode,0);self.assertIn('--case-id',help_result.stdout)


BALANCED_SUITE_HASH='21cce04b74609765c733474684958dcb540b3e125fae9203a5ae515f72bfc1f9'
if __name__=='__main__':unittest.main()
