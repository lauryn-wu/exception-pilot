"""Synthetic native/exported evidence tests plus supplied-data offline validation."""
import copy
import json
import math
import os
import socket
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from exception_pilot.core import digest
from exception_continuation.runner import sealed_write,sealed_read
from exception_study2_v5_replication.readouts import expected_plan
from exception_study2_v5.journal import Session
from exception_study2_source_report import evidence,planning
from exception_study2_source_report.tokenizer import Tokenizer
from source_report_fixtures import Tokens,fixture


def value(row,c,tok):
    # Newline-adversarial: class A wins on token 0, class B wins on the sequence.
    logps={'A':[-1.,-5.],'B':[-2.,-.01],'C':[-3.,-.2]}
    scores={x:dict(tokens=list(evidence.CANDIDATES[x]),token_logprobs=v,logprob=sum(v)) for x,v in logps.items()}
    top=max(v['logprob'] for v in scores.values());z=top+math.log(sum(math.exp(v['logprob']-top) for v in scores.values()))
    cue=tok.encode(c['cue_text']);context=row['input_ids']+row['raw']['tokens'][:c['k']]+cue
    return dict(candidate_texts={x:' '+x+'\n' for x in 'ABC'},cue_text=c['cue_text'],cue_ids=cue,context_ids=context,context_hash=digest(context),
        scores=scores,normalized={x:math.exp(v['logprob']-z) for x,v in scores.items()},candidate_log_mass=z,
        gold_pattern_log_odds=scores[row['task']['expected']]['logprob']-scores[row['task']['pattern']]['logprob'],preferred_class='B')


class LegacyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.tok=Tokens();self.source=copy.deepcopy(fixture().remaining)
        t=self.source.tasks[0];self.source.tasks=[t];self.source.rows={t['id']:self.source.rows[t['id']]}
        self.folder=self.root/'readouts';self.folder.mkdir();self.plan=expected_plan(self.source,self.folder)
        self.results={}
        for key,c in self.plan['computations'].items():
            row=self.source.rows[c['task_id']]
            self.results[key]=dict(status='returned',world=row['task']['world'],source_row_hash=row['artifact_hash'],value=value(row,c,self.tok))
        self.summary=dict(plan_hash=digest(self.plan),measurement='LIVE',results=self.results)
        sealed_write(self.folder/'measurements-v5.json',self.summary)
    def test_export_summary_and_newline_adversarial_class_token_preference(self):
        before={p.name:p.read_bytes() for p in self.folder.iterdir()}
        data,provenance=evidence.legacy(self.source,self.folder,self.tok)
        self.assertEqual(provenance['legacy_provenance_mode'],'exported_summary');self.assertFalse(provenance['journal_level_verified'])
        self.assertTrue(provenance['plan_hash_independently_reproduced'])
        for r in data.values():
            self.assertEqual(r['class_token']['preferred_class'],'A');self.assertEqual(r['whole_sequence_sensitivity']['preferred_class'],'B')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.folder.iterdir()})
    def test_unreconstructible_historical_plan_reference_is_explicit_not_fabricated(self):
        self.summary['plan_hash']='a'*64;sealed_write(self.folder/'measurements-v5.json',self.summary)
        data,p=evidence.legacy(self.source,self.folder,self.tok)
        self.assertFalse(p['plan_hash_independently_reproduced']);self.assertEqual(p['historical_plan_hash'],'a'*64)
        self.assertFalse((self.folder/'measurement-plan-v5.json').exists());self.assertFalse((self.folder/'operations-v5').exists())
    def test_native_journals_preferred_and_match_export_content(self):
        exported,_=evidence.legacy(self.source,self.folder,self.tok)
        p=sealed_write(self.folder/'measurement-plan-v5.json',self.plan)
        backend=SimpleNamespace(identity=self.source.execution['backend'],simulated=False)
        s=Session(self.folder,self.source.plan,backend,binding={'measurement_plan':p['artifact_hash']})
        for key,c in self.plan['computations'].items():
            row=self.source.rows[c['task_id']]
            req=dict(input_ids=row['input_ids'],prefix_ids=row['raw']['tokens'][:c['k']],gold=row['task']['expected'],pattern=row['task']['pattern'],cue_text=c['cue_text'])
            s.operation('v5/readout/'+key,req,lambda key=key:self.results[key]['value'],'candidate_readout')
        native,p=evidence.legacy(self.source,self.folder,self.tok)
        self.assertEqual(native,exported);self.assertEqual(p['legacy_provenance_mode'],'native_journals');self.assertTrue(p['journal_level_verified'])
        # Partial/corrupt native evidence cannot silently downgrade to summary mode.
        (self.folder/'execution-v5.json').unlink()
        with self.assertRaisesRegex(ValueError,'Partial native evidence'):evidence.legacy(self.source,self.folder,self.tok)
    def test_source_row_context_cue_candidate_and_arithmetic_rejections(self):
        original=copy.deepcopy(self.summary);key=next(iter(self.results))
        for bad in ('source_row','context','cue','candidate','arithmetic','population'):
            d=copy.deepcopy(original);r=d['results'][key]
            if bad=='source_row':r['source_row_hash']='bad'
            elif bad=='context':r['value']['context_ids'][0]+=1
            elif bad=='cue':r['value']['cue_ids']=[123]
            elif bad=='candidate':r['value']['scores']['A']['tokens'][0]=999
            elif bad=='arithmetic':r['value']['scores']['A']['logprob']+=.1
            else:d['results'].pop(key)
            sealed_write(self.folder/'measurements-v5.json',d)
            with self.assertRaises(ValueError,msg=bad):evidence.legacy(self.source,self.folder,self.tok)
    def test_missing_required_content_or_summary_stops_without_inference(self):
        (self.folder/'measurements-v5.json').unlink()
        with self.assertRaisesRegex(ValueError,'Required sealed'):evidence.legacy(self.source,self.folder,self.tok)
        c=next(iter(self.plan['computations'].values()));row=next(iter(self.source.rows.values()));v=value(row,c,self.tok)
        absent=copy.deepcopy(v);del absent['scores']['A']['token_logprobs']
        with self.assertRaisesRegex(ValueError,'Required legacy content.*token_logprobs'):evidence.validate_legacy(absent,row,c,self.tok)
        v['scores']['A']['token_logprobs'][0]=float('nan')
        with self.assertRaises(ValueError):evidence.validate_legacy(v,row,c,self.tok)


@unittest.skipUnless(os.environ.get('STUDY2_SOURCE_REPORT_ORIGINALS') and os.environ.get('STUDY2_SOURCE_REPORT_READOUTS') and os.environ.get('QWEN3_TOKENIZER_DIR'), 'Saved-data integration requires explicit local source/readout/tokenizer paths')
class SavedDataTests(unittest.TestCase):
    def test_supplied_archive_exact_inventory_prefixes_exclusions_and_controls(self):
        def forbidden(*a,**k):raise AssertionError('Offline saved-data validation may not load models/connect')
        from exception_continuation import backend
        real_hash=backend.file_hash;hashed=[]
        def checked_hash(path):
            self.assertNotEqual(Path(path).suffix,'.safetensors');hashed.append(str(path));return real_hash(path)
        with patch('socket.socket.connect',forbidden),patch('socket.create_connection',forbidden),patch.object(backend.LocalBackend,'__init__',forbidden),patch.object(backend,'file_hash',checked_hash):
            tok=Tokenizer(os.environ['QWEN3_TOKENIZER_DIR'])
            e=evidence.Evidence(os.environ['STUDY2_SOURCE_REPORT_ORIGINALS'],os.environ['STUDY2_SOURCE_REPORT_READOUTS'],tok)
            plan=planning.make_plan(e)
        self.assertEqual(plan['inventory']['main'],332);self.assertEqual(plan['inventory']['legacy_entries'],664)
        self.assertEqual(len(plan['calibration']),12);self.assertEqual(len(hashed),7)
        self.assertTrue(plan['source']['legacy']['plan_hash_independently_reproduced'])
        self.assertEqual({x['task_id'] for x in plan['exclusions']},{'staged-v5-011/v1/original/visible','staged-v5-026/v0/original/visible','staged-v5-027/v0/original/visible','staged-v5-059/v1/original/visible'})
        self.assertEqual(plan['backend']['hardware'],'NVIDIA H100 80GB HBM3')
        for q in plan['main']:
            row=e.remaining.rows[q['task_id']]
            self.assertEqual(q['context_ids'][:len(row['input_ids'])],row['input_ids'])
            self.assertEqual(q['prefix_ids'],row['raw']['tokens'][:q['checkpoint']])
        self.assertTrue(all(q['prefix_ids']==[] for q in plan['calibration']))
