"""Pinned archived evidence + real tokenizer; every generation is a mock."""
import copy
import csv
import io
import json
import os
import shutil
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch
from exception_pilot.core import digest
from exception_review.artifacts import freeze, sha
from exception_continuation.runner import sealed_read
from exception_study2_current.adapter import Tokenizer
from exception_study2_current.planning import contract as original_contract
from exception_study2_native import FINAL_INSTRUCTION
from exception_study2_explanation import SOURCE_ZIP, SOURCE_LOG, SOURCE_SHA256, SOURCE_CONTRACT, INSTRUCTION, VERSION
from exception_study2_explanation import source as source_module
from exception_study2_explanation.source import Source, match_key, sha_bytes
from exception_study2_explanation.planning import prepare, Context, requests_from_source
from exception_study2_explanation.parsing import parse_result
from exception_study2_explanation.execution import run, inspect, analyze, recover, journal, opid, binding, STAGE
from exception_study2_explanation.analysis import report, primary_contrast, sensitivity, paired_changes
from exception_study2_explanation.export import export, ANNOTATIONS

TOKENIZER = os.environ.get('CURRENT_QWEN_TOKENIZER_DIR')
ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'results/current-qwen-screen-v1'/SOURCE_ZIP


@unittest.skipUnless(TOKENIZER, 'Set CURRENT_QWEN_TOKENIZER_DIR to existing pinned assets; tests never download')
class ExplanationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok = Tokenizer(TOKENIZER)
        cls.source = Source(ARCHIVE, cls.tok)
        cls.requests, cls.controls = requests_from_source(cls.source, cls.tok)
        cls.tmp = tempfile.TemporaryDirectory(); cls.base = Path(cls.tmp.name)
        cls.prototype = cls.base/'prototype'
        with patch('exception_study2_explanation.planning.Tokenizer', return_value=cls.tok):
            cls.preview = prepare(ARCHIVE, cls.prototype, TOKENIZER)
        cls.original_hashes = {p.name: sha(p) for p in ARCHIVE.parent.iterdir() if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.tmpcase = tempfile.TemporaryDirectory(); self.root = Path(self.tmpcase.name)
        self.out = self.root/'run'; shutil.copytree(self.prototype, self.out)
        self.token_patch = patch('exception_study2_explanation.planning.Tokenizer', return_value=self.tok)
        self.token_patch.start(); self.calls = []; self.loads = 0

    def tearDown(self):
        self.token_patch.stop(); self.tmpcase.cleanup()

    def raw(self, request, text=None, eos=True):
        text = text if text is not None else 'The recorded class is '+request['expected']+'.\n'+request['expected']
        ids = self.tok.encode(text)
        if eos:
            ids.append(min(self.tok.eos_ids))
        else:
            ids = (ids * (request['budget']//max(1, len(ids))+1))[:request['budget']]
        return dict(tokens=ids, raw_text=self.tok.decode_all(ids), text=self.tok.decode(ids),
                    input_ids_verified=True, actual_input_ids=request['input_ids'], stopped=eos,
                    finish='eos' if eos else 'length', backend_finish_reason='stop' if eos else 'length',
                    backend_stop_reason=None, resolved_sampling=request['resolved_sampling'], elapsed_seconds=.1)

    def factory(self, model, tok):
        self.loads += 1
        test = self
        class Mock:
            simulated = True
            identity = copy.deepcopy(test.source.execution['backend'])
            def generate(self, q):
                test.calls.append(q)
                return test.raw(q)
        return Mock()

    def test_counts_source_matching_and_no_world_regeneration(self):
        with patch('exception_study2_current.design.make_design', side_effect=AssertionError('no worlds')):
            rs, refs = requests_from_source(self.source, self.tok)
        self.assertEqual(len(rs), 96); self.assertEqual(len(refs), 192)
        self.assertEqual({r['cell']['wording'] for r in rs}, {'original'})
        self.assertEqual({r['cell']['thinking'] for r in rs}, {False})
        self.assertEqual(Counter(r['cell']['relation'] for r in rs), {'support':48, 'conflict':48})
        self.assertEqual(Counter(r['cell']['world'] for r in rs), Counter({f'current-qwen-v1-{i:03d}':4 for i in range(24)}))
        self.assertEqual(self.preview['maximum_output_tokens'], 393216)
        self.assertEqual(self.preview['input_tokens'], 54264)
        self.assertEqual([r['request']['controls']['direct']['cell_id'] for r in rs], [r['cell']['id'] for r in self.source.off])

    def test_every_prompt_changes_only_suffix_and_all_settings_match(self):
        for r, old in zip(self.requests, self.source.off):
            a, b = old['request'], r['request']
            self.assertTrue(a['prompt'].endswith(FINAL_INSTRUCTION))
            self.assertTrue(b['prompt'].endswith(INSTRUCTION))
            self.assertEqual(a['prompt'][:-len(FINAL_INSTRUCTION)].encode(), b['prompt'][:-len(INSTRUCTION)].encode())
            self.assertNotEqual(r['request_hash'], old['request_hash'])
            changed = {'protocol','cell_id','prompt','prompt_hash','input_ids','input_hash','rendered_input'}
            for key in a.keys()-changed:
                self.assertEqual(a[key], b[key], key)
            self.assertEqual(b['input_ids'], self.tok.render(b['prompt'], False))
            self.assertTrue(b['rendered_input'].endswith('<think>\n\n</think>\n\n'))
            self.assertEqual(b['rendered_input'].count('<think>'), 1)
            on = self.source.on[match_key(r['cell'])]
            self.assertEqual(b['controls']['native_on'], self.source.reference(on))

    def test_suffix_assertion(self):
        source = copy.copy(self.source); source.off = copy.deepcopy(source.off)
        source.off[0]['request']['prompt'] += ' '
        with self.assertRaisesRegex(ValueError, 'suffix'):
            requests_from_source(source, self.tok)

    def test_source_archive_and_contract_unchanged(self):
        self.assertEqual(original_contract(), SOURCE_CONTRACT)
        self.assertEqual(sha(ARCHIVE), SOURCE_SHA256)
        self.assertEqual(self.original_hashes, {p.name:sha(p) for p in ARCHIVE.parent.iterdir() if p.is_file()})
        self.assertEqual(self.source.seals_checked, 1582)
        self.assertEqual(self.source.smoke_binding['verified_passing_records'], 8)
        self.assertEqual(self.source.smoke_binding['scheduled_new_records'], 0)
        self.assertEqual(sum(self.source.scores[r['cell_id']]['correct'] for r in self.controls), 192)
        self.assertEqual(self.source.binding['startup_log']['line_number'], 1)
        self.assertNotIn('VLLM_USE_FLASHINFER_SAMPLER', self.source.execution['backend'])

    def test_offline_and_relocated_source_never_follow_runpod_paths(self):
        shutil.copytree(self.out, self.root/'relocated')
        with patch('exception_study2_explanation.execution.Backend', side_effect=AssertionError('no model')):
            result = inspect(self.root/'relocated', TOKENIZER)
        self.assertEqual(result['totals']['never_started'], 96)
        self.assertIsNone(result['primary']['estimate'])
        self.assertEqual(result['arms']['direct']['conflict']['accuracy'], 1)
        self.assertEqual(result['this_invocation']['model_loads'], 0)
        self.assertEqual(result['this_invocation']['cached_explanation_responses'], 0)
        self.assertEqual(result['this_invocation']['historical_controls_reused'], 192)
        self.assertEqual(Context(self.root/'relocated', TOKENIZER).locations['model'], self.source.locations['model'])

    def test_default_run_is_offline(self):
        with patch('exception_study2_explanation.execution.Backend', side_effect=AssertionError('no model')):
            result = run(self.out)
        self.assertEqual(result['this_invocation']['new_dispatches'], 0)
        self.assertFalse((self.out/'execution.json').exists())

    def test_source_zip_digest_and_log_rejection(self):
        source = self.out/'source-evidence'/SOURCE_ZIP
        source.write_bytes(source.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'ZIP SHA256'):
            Source(source, self.tok)
        source.write_bytes(ARCHIVE.read_bytes())
        (source.parent/SOURCE_LOG).write_text('VLLM_USE_FLASHINFER_SAMPLER=1\n')
        with self.assertRaisesRegex(ValueError, 'startup log SHA256'):
            Source(source, self.tok)

    def rewrite_source(self, mutate):
        files = dict(self.source.files)
        mutate(files)
        m = json.loads(files['bundle-manifest.json'])
        m['files'] = {n:dict(bytes=len(v),sha256=sha_bytes(v)) for n,v in files.items() if n!='bundle-manifest.json'}
        files['bundle-manifest.json'] = json.dumps(m).encode()
        source = self.out/'source-evidence'/SOURCE_ZIP
        with zipfile.ZipFile(source, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, value in files.items(): z.writestr(name, value)
        h = sha(source); p=source.parent/'SHA256SUMS'; p.write_text(p.read_text().replace(SOURCE_SHA256,h))
        return source, patch.object(source_module, 'SOURCE_SHA256', h)

    def test_resealed_raw_input_corruption_rejected_beyond_outer_checksum(self):
        def change(files):
            n = next(n for n in files if n.startswith('operations-v5/') and n.endswith('returned.json'))
            obj=json.loads(files[n]); obj['result']['actual_input_ids'][0] += 1
            obj['artifact_hash']=digest({k:v for k,v in obj.items() if k!='artifact_hash'}); files[n]=json.dumps(obj).encode()
        source, lock = self.rewrite_source(change)
        with lock, self.assertRaisesRegex(ValueError, 'raw return identity'):
            Source(source, self.tok)

    def test_resealed_dispatch_binding_corruption_rejected(self):
        def change(files):
            n = next(n for n in files if n.startswith('dispatches/'))
            obj=json.loads(files[n]); obj['backend_hash']='0'*64
            obj['artifact_hash']=digest({k:v for k,v in obj.items() if k!='artifact_hash'});files[n]=json.dumps(obj).encode()
        source, lock=self.rewrite_source(change)
        with lock, self.assertRaisesRegex(ValueError,'dispatch/invocation'):
            Source(source,self.tok)

    def test_wrong_model_identity_and_sealed_request_fail(self):
        source=copy.copy(self.source); source.off=copy.deepcopy(source.off)
        q=source.off[0]['request'];q['budget']=2048
        with self.assertRaisesRegex(ValueError,'source budget'):
            requests_from_source(source,self.tok)
        p=self.out/'plan.json';v=sealed_read(p);v['requests'][0]['request']['model_revision']='wrong'
        p.unlink();freeze(p,v)
        with self.assertRaisesRegex(ValueError,'source/request/settings'):
            Context(self.out)

    def test_brief_explanation_correct_wrong_and_label_only(self):
        q=self.requests[0]['request']; expected=q['expected'];wrong=next(x for x in 'ABC' if x!=expected)
        good=parse_result(self.raw(q,'The record says '+expected+'.\n'+expected),q,self.tok)
        self.assertTrue(good['correct']);self.assertTrue(good['explanation_format_compliant'])
        self.assertEqual(good['explanation_compliance'],'not_reviewed')
        bad=parse_result(self.raw(q,'I choose this.\n'+wrong),q,self.tok)
        self.assertEqual(bad['category'],'wrong_label');self.assertTrue(bad['valid'])
        label=parse_result(self.raw(q,expected),q,self.tok)
        self.assertTrue(label['correct']);self.assertFalse(label['explanation_format_compliant'])
        self.assertEqual(label['explanation_text'],'')

    def test_exact_last_nonempty_line_no_earlier_letter_rescue(self):
        q=self.requests[0]['request'];a=q['expected']
        for text in ('ANSWER: '+a, 'Reason\n '+a, 'Reason\n'+a+' ', 'Reason\n'+a+'.', a+'\nThat is my answer.'):
            with self.subTest(text=text):
                s=parse_result(self.raw(q,text),q,self.tok);self.assertFalse(s['valid']);self.assertIsNone(s['answer'])
        s=parse_result(self.raw(q,'A is considered.\nB is considered.\n'+a+'\n\n'),q,self.tok)
        self.assertTrue(s['correct']);self.assertIn('A is considered.',s['explanation_text'])

    def test_empty_missing_answer_and_truncated(self):
        q=self.requests[0]['request']
        self.assertEqual(parse_result(self.raw(q,''),q,self.tok)['category'],'missing_answer')
        s=parse_result(self.raw(q,'A\n',False),q,self.tok)
        self.assertTrue(s['truncated']);self.assertFalse(s['valid']);self.assertIsNone(s['answer'])
        self.assertEqual(s['token_count'],4096)

    def test_structural_tokens_rejected_not_stripped(self):
        q=self.requests[0]['request']
        for marker in (v.content for v in self.tok.tokenizer.added_tokens_decoder.values()):
            with self.subTest(marker=marker):
                s=parse_result(self.raw(q,marker+'reason\n'+q['expected']),q,self.tok)
                self.assertFalse(s['valid']);self.assertEqual(s['category'],'malformed_channel')
                self.assertIn(marker,s['ordinary_text'])

    def test_token_input_eos_stop_and_sampling_corruption(self):
        q=self.requests[0]['request']
        mutations=[lambda r:r.update(raw_text='wrong'),lambda r:r.update(text='wrong'),
                   lambda r:r.update(input_ids_verified=False),lambda r:r.update(actual_input_ids=[1]),
                   lambda r:r.update(stopped=False),lambda r:r.update(finish='length'),
                   lambda r:r.update(backend_finish_reason='length'),lambda r:r.update(backend_stop_reason='A'),
                   lambda r:r.update(resolved_sampling={}),lambda r:r.update(tokens=[-1]),
                   lambda r:r.update(tokens=[True])]
        for mutate in mutations:
            raw=copy.deepcopy(self.raw(q));mutate(raw)
            with self.subTest(raw=raw.keys()):
                s=parse_result(raw,q,self.tok);self.assertFalse(s['valid']);self.assertEqual(s['category'],'metadata_malformed')

    def test_budget_overrun_unfinished_under_cap_and_non_payload(self):
        q=self.requests[0]['request'];raw=self.raw(q)
        raw['tokens']=self.tok.encode('x')*4097+[min(self.tok.eos_ids)]
        raw.update(raw_text=self.tok.decode_all(raw['tokens']),text=self.tok.decode(raw['tokens']))
        self.assertIn('invalid generation length',parse_result(raw,q,self.tok)['errors'])
        raw=self.raw(q);raw['tokens']=raw['tokens'][:-1]
        raw.update(raw_text=self.tok.decode_all(raw['tokens']),text=self.tok.decode(raw['tokens']),stopped=False,finish='length',backend_finish_reason='length')
        self.assertIn('invalid generation length',parse_result(raw,q,self.tok)['errors'])
        self.assertEqual(parse_result(None,q,self.tok)['category'],'metadata_malformed')

    def rows(self, scorer=None):
        c=Context(self.out);current={r['cell']['id']:None for r in c.requests}
        current,_,_=journal(c);rows=report(c,current,{})['cases']
        for row,r in zip(rows,c.requests):
            row['score']=parse_result(self.raw(r['request']),r['request'],self.tok)
            if scorer:scorer(row)
        return rows

    def test_primary_contrast_four_blocks_and_world_sensitivity(self):
        rows=self.rows(lambda r:r['score'].update(correct=r['cell']['relation']=='support'))
        p=primary_contrast(rows);self.assertEqual(p['estimate'],1);self.assertEqual(p['block_interval_95'],[1,1])
        self.assertEqual(p['block_bootstrap']['planned_clusters'],4)
        self.assertEqual(p['world_sensitivity']['planned_worlds'],24)
        self.assertEqual(paired_changes(rows,'direct')['conflict']['control_only_correct'],48)
        rows[0]['score']=None;self.assertIsNone(primary_contrast(rows)['estimate'])

    def test_record_pairs_hold_cue_and_cue_pairs_hold_variant(self):
        rows=self.rows()
        for r in rows:r['score']['answer']=r['cell']['pattern']
        record=sensitivity(rows,'record');cue=sensitivity(rows,'cue')
        self.assertEqual(record['planned_pairs'],48);self.assertEqual(record['label_changes'],0)
        self.assertEqual(cue['label_changes'],48)
        self.assertTrue(all(p['fixed_field']=='cue_state' for p in record['pairs']))
        self.assertTrue(all(p['fixed_field']=='variant' for p in cue['pairs']))

    def test_invalid_not_counted_as_label_change_and_pair_denominators(self):
        rows=self.rows();rows[0]['score']['valid']=False;rows[0]['score']['answer']=None
        r=sensitivity(rows,'record');self.assertEqual(r['eligible_pairs'],47);self.assertEqual(r['unscorable_pairs'],1)
        self.assertEqual(r['label_changes'],47);self.assertEqual(r['denominator'],47)
        rows[0]['score']=None;r=sensitivity(rows,'record');self.assertEqual(r['unavailable_pairs'],1)

    def test_mock_run_complete_no_controls_no_duplicates_zero_completed_loads(self):
        first=run(self.out,max_new=3,_factory=self.factory)
        self.assertEqual(first['this_invocation']['new_dispatches'],3);self.assertFalse(first['complete'])
        self.assertEqual(first['totals']['never_started'],93)
        second=run(self.out,_factory=self.factory)
        self.assertEqual(second['this_invocation']['cached_explanation_responses'],3)
        self.assertEqual(second['this_invocation']['new_dispatches'],93)
        self.assertTrue(second['complete']);self.assertEqual(second['primary']['estimate'],0)
        self.assertEqual(len(self.calls),96);self.assertEqual(self.loads,2)
        self.assertEqual(len({digest(q) for q in self.calls}),96)
        self.assertTrue(all(q['protocol']==VERSION and q['prompt'].endswith(INSTRUCTION) for q in self.calls))
        self.assertEqual(os.environ['VLLM_USE_FLASHINFER_SAMPLER'],'0')
        third=run(self.out,_factory=lambda *_:self.fail('complete must not load'))
        self.assertEqual(third['this_invocation']['model_loads'],0)
        self.assertEqual(third['this_invocation']['cached_explanation_responses'],96)

    def test_first_failure_stops_then_resume_only_remaining(self):
        def failing(*args):
            backend=self.factory(*args)
            def generate(q):self.calls.append(q);raise RuntimeError('persistent failure')
            backend.generate=generate;return backend
        first=run(self.out,_factory=failing)
        self.assertEqual(first['totals']['failed'],1);self.assertEqual(first['totals']['never_started'],95)
        self.assertEqual(len(self.calls),1)
        failed=next((self.out/'operations-v5').glob('*/failed.json'));before=failed.read_bytes()
        second=run(self.out,_factory=self.factory)
        self.assertEqual(second['totals']['returned'],95);self.assertEqual(second['totals']['failed'],1)
        self.assertEqual(len(self.calls),96);self.assertEqual(failed.read_bytes(),before)
        self.assertIsNone(second['primary']['estimate']);self.assertFalse(second['complete'])
        third=run(self.out,_factory=lambda *_:self.fail('no pending loads'))
        self.assertEqual(third['this_invocation']['model_loads'],0)

    def test_ambiguous_start_and_debris_remain_held_after_recovery(self):
        run(self.out,max_new=1,_factory=self.factory);c=Context(self.out);r=c.requests[1];oid=opid(r)
        identity=dict(binding(c,'MOCK'),id=oid,request=r['request'],request_hash=r['request_hash'],stage=STAGE)
        folder=self.out/'operations-v5'/digest(oid)
        freeze(folder/'request.json',dict(identity,status='planned'))
        freeze(folder/'started.json',dict(identity,status='started'))
        (folder/'returned.json.abcdefgh.tmp').write_text('interrupted write')
        a=inspect(self.out);self.assertEqual(a['totals']['ambiguous'],1)
        recover(self.out,'Offline fixture: quarantine partial return; do not retry')
        result=run(self.out,_factory=self.factory)
        self.assertEqual(result['totals']['returned'],95);self.assertEqual(result['totals']['ambiguous'],1)
        self.assertNotIn(r['request'],self.calls)
        self.assertEqual(len(self.calls),95)

    def test_invalid_wrong_and_truncated_returns_are_cached(self):
        def factory(*args):
            backend=self.factory(*args)
            def generate(q):
                self.calls.append(q);i=len(self.calls)
                text=next(a for a in 'ABC' if a!=q['expected']) if i==1 else 'Verbose final answer is '+q['expected']
                return self.raw(q,text,eos=i!=3)
            backend.generate=generate;return backend
        result=run(self.out,max_new=3,_factory=factory)
        self.assertEqual(result['totals']['returned'],3);self.assertEqual(result['totals']['failed'],0)
        result=run(self.out,_factory=self.factory)
        self.assertEqual(len(self.calls),96);self.assertTrue(result['complete'])
        self.assertEqual(sum(g['invalid'] for g in result['arms']['explanation'].values()),2)
        self.assertEqual(sum(g['valid_wrong_labels'] for g in result['arms']['explanation'].values()),1)
        self.assertEqual(sum(g['truncated'] for g in result['arms']['explanation'].values()),1)

    def test_backend_mismatch_never_dispatches(self):
        def factory(*args):
            backend=self.factory(*args);backend.identity['hardware']='different';return backend
        with self.assertRaisesRegex(ValueError,'archived passing smoke'):
            run(self.out,_factory=factory)
        self.assertEqual(self.calls,[]);self.assertFalse((self.out/'execution.json').exists())
        self.assertEqual(inspect(self.out)['totals']['never_started'],96)

    def test_live_and_mock_caches_cannot_mix_and_limit_checked(self):
        run(self.out,max_new=1,_factory=self.factory)
        with self.assertRaisesRegex(ValueError,'Mock/live caches'):
            run(self.out,live=True)
        for limit in (0,97,True):
            with self.assertRaises(ValueError):run(self.out,max_new=limit)

    def test_export_portable_checksums_blank_review_and_no_secrets(self):
        run(self.out,max_new=1,_factory=self.factory)
        (self.out/'do-not-export.env').write_text('FAKE_SECRET_FOR_TEST')
        target=self.root/'evidence.zip';export(self.out,target)
        with zipfile.ZipFile(target) as z:
            m=json.loads(z.read('bundle-manifest.json'))
            self.assertEqual(set(z.namelist()),set(m['files'])|{'bundle-manifest.json'})
            for name,info in m['files'].items():
                self.assertEqual(info,dict(bytes=len(z.read(name)),sha256=sha_bytes(z.read(name))))
            self.assertEqual(sha_bytes(z.read('source-evidence/'+SOURCE_ZIP)),SOURCE_SHA256)
            self.assertNotIn('do-not-export.env',z.namelist())
            rows=list(csv.DictReader(io.StringIO(z.read('manual-review.csv').decode())))
            self.assertEqual(len(rows),96)
            self.assertTrue(all(row[a]=='not_reviewed' for row in rows for a in ANNOTATIONS))
            relocated=self.root/'exported';z.extractall(relocated)
        before={str(p.relative_to(relocated)):sha(p) for p in relocated.rglob('*') if p.is_file()}
        result=inspect(relocated,TOKENIZER)
        after={str(p.relative_to(relocated)):sha(p) for p in relocated.rglob('*') if p.is_file()}
        self.assertEqual(before,after);self.assertEqual(result['totals']['returned'],1)
        self.assertEqual(result['this_invocation']['model_loads'],0)
        with self.assertRaisesRegex(ValueError,'Fresh export'):
            export(self.out,target)

    def test_malformed_payload_is_cached_without_backend_failure(self):
        def factory(*args):
            backend=self.factory(*args)
            def generate(q):
                self.calls.append(q)
                return dict(tokens=None, raw_text=None, elapsed_seconds=None)
            backend.generate=generate;return backend
        first=run(self.out,max_new=1,_factory=factory)
        self.assertEqual(first['totals']['returned'],1);self.assertEqual(first['totals']['failed'],0)
        self.assertEqual(first['cases'][0]['score']['category'],'metadata_malformed')
        second=run(self.out,max_new=1,_factory=self.factory)
        self.assertEqual(second['this_invocation']['cached_explanation_responses'],1)
        self.assertEqual(len(self.calls),2)
        export(self.out,self.root/'malformed-evidence.zip')

    def test_sampler_environment_is_set_before_factory(self):
        def factory(*args):
            self.assertEqual(os.environ['VLLM_USE_FLASHINFER_SAMPLER'],'0')
            return self.factory(*args)
        with patch.dict(os.environ,{'VLLM_USE_FLASHINFER_SAMPLER':'1'}):
            run(self.out,max_new=1,_factory=factory)
        ex=sealed_read(self.out/'execution.json')
        self.assertEqual(ex['runtime_environment'],{'VLLM_USE_FLASHINFER_SAMPLER':'0'})
        self.assertEqual(ex['backend'],self.source.execution['backend'])

    def test_offline_paths_do_not_initialize_cuda(self):
        import torch
        with patch.object(torch.cuda,'init',side_effect=AssertionError('no CUDA')), \
             patch.object(torch.cuda,'_lazy_init',side_effect=AssertionError('no CUDA')):
            inspect(self.out,TOKENIZER)
            analyze(self.out,TOKENIZER)
            export(self.out,self.root/'offline.zip',TOKENIZER)

    def test_new_plan_cannot_be_prepared_over_existing_source_or_run(self):
        with self.assertRaises(ValueError):prepare(ARCHIVE,ARCHIVE.parent/'unsafe',TOKENIZER)
        with self.assertRaises(ValueError):prepare(ARCHIVE,self.out,TOKENIZER)
        self.assertEqual(self.original_hashes,{p.name:sha(p) for p in ARCHIVE.parent.iterdir() if p.is_file()})

    def test_analyze_preserves_all_immutable_files(self):
        run(self.out,max_new=1,_factory=self.factory)
        files=[p for p in self.out.rglob('*') if p.is_file() and p.name not in ('analysis.json','analysis.md','run.lock')]
        before={str(p):sha(p) for p in files}
        value=analyze(self.out)
        self.assertFalse(value['complete']);self.assertTrue((self.out/'analysis.md').exists())
        self.assertEqual(before,{str(p):sha(p) for p in files})

if __name__=='__main__':unittest.main()
