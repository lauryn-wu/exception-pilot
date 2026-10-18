"""Offline independent integrity and execution checks; never mutates evidence."""
import collections, hashlib, json, sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path('/workspace/scratch/ea260d81d736')
sys.path.insert(0, str(ROOT/'source_user_main_code_review'))
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_source_user_main.integrity import contract
from exception_study2_source_user_main.execution import journal,request
from exception_study2_source_user_main import MESSAGE
from exception_study2_v5.scoring import checkpoints

p=ROOT/'source_user_main_results_audit/study2-source-user-main-v1'
prior=ROOT/'source_user_pilot_results_audit/study2-source-user-pilot-v1'
originals=ROOT/'full_trace_audit/input/study2-v5-replication-v1/originals'
plan=sealed_read(p/'main-plan.json');report=json.loads((p/'report.json').read_text())
sealed=[];unsealed=[]
for f in p.rglob('*.json'):
    j=json.loads(f.read_text())
    if isinstance(j,dict) and 'artifact_hash' in j:
        assert j['artifact_hash']==digest({k:v for k,v in j.items() if k!='artifact_hash'}), f
        sealed.append(str(f.relative_to(p)))
    else:unsealed.append(str(f.relative_to(p)))
assert unsealed==['report.json','pilot-evidence/report.json','pilot-evidence/parent-evidence/report.json'],unsealed
assert contract()==plan['code_contract']
qs=plan['queries'];qmap={q['id']:q for q in qs}
assert len(qmap)==len(qs)==332
saved,mode=journal(SimpleNamespace(out=p,plan=plan,queries=qmap))
assert set(saved)==set(qmap) and mode=='LIVE_LOCAL'
assert all(o['status']=='returned' for o in saved.values())
assert len(list((p/'operations-v5').rglob('*.json')))==996
manifest=sealed_read(p/'pilot-snapshot-manifest.json')
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
actual_snapshot={str(f.relative_to(p/'pilot-evidence')):sha(f) for f in (p/'pilot-evidence').rglob('*') if f.is_file()}
assert actual_snapshot==manifest['files']
assert {n:h for n,h in actual_snapshot.items() if n not in ['report.json','report.md']}==plan['parent_pilot']['immutable_manifest']
assert digest(plan['parent_pilot']['immutable_manifest'])==manifest['scientific_identity']==plan['parent_pilot']['immutable_manifest_hash']
prior_files={str(f.relative_to(prior)):sha(f) for f in prior.rglob('*') if f.is_file() and f.name!='run.lock'}
assert prior_files==actual_snapshot
rows={json.loads(f.read_text())['task']['id']:sealed_read(f) for f in (p/'source-evidence').glob('*.json')}
assert len(rows)==112 and set(rows)==set(plan['source_rows'])
for tid,row in rows.items():
    original=sealed_read(originals/'originals-v5'/(digest(tid)+'.json'))
    assert row==original
    op=sealed_read(originals/'operations-v5'/digest('v5/original/'+tid)/'returned.json')
    assert row['raw']==op['result'] and row['operation_hash']==op['artifact_hash']
    assert row['input_ids']==op['request']['input_ids'] and row['input_hash']==digest(row['input_ids'])
    assert row['artifact_hash']==plan['source_rows'][tid]
    assert row['backend_hash']==plan['backend_hash']
parent=sealed_read(p/'pilot-evidence/parent-evidence/source-report-plan.json')
assert plan['origin_plan_hash']==parent['artifact_hash']
assert [q['origin_query'] for q in qs]==parent['main']
assert plan['exclusions']==parent['exclusions']
assert digest(plan['backend'])==plan['backend_hash']
assert plan['backend']==parent['backend']
bridge_by_task={};count=collections.Counter()
for i,q in enumerate(qs):
    assert q['query_hash']==digest({k:v for k,v in q.items() if k not in ('query_hash','id')})
    assert q['id']=='v5/source-user-main-v1/'+q['query_hash']
    origin=q['origin_query'];row=rows[q['task_id']];k=q['checkpoint']
    assert origin['query_hash']==digest({k:v for k,v in origin.items() if k not in ('query_hash','id')})
    assert q['source_row_hash']==row['artifact_hash']
    assert q['original_input_ids']==origin['input_ids']==row['input_ids']
    assert q['prefix_ids']==origin['prefix_ids']==row['raw']['tokens'][:k]
    assert len(q['prefix_ids'])==k
    assert q['old_context_ids']==q['original_input_ids']+q['prefix_ids']
    assert q['context_ids']==q['old_context_ids']+q['bridge_ids']
    for key in ['prefix','old_context','context','original_input']:
        assert q[key+'_hash']==digest(q[key+'_ids'])
    assert q['bridge_hash']==digest(dict(text=q['bridge_text'],ids=q['bridge_ids']))
    cut={x['name']:x for x in checkpoints(row)}['fixed/'+str(k)]
    assert q['boundary']==cut and cut['eligible']
    prefix_text=row['raw']['text'][:cut['char_end']]
    assert digest(prefix_text)==cut['text_hash'] and digest(q['prefix_ids'])==cut['token_hash']
    assert q['new_user_message']==MESSAGE.format(plate=q['target_plate'])
    assert digest(q['new_user_message'])==q['new_user_hash']
    assert q['bridge_text']=='<|im_end|>\n<|im_start|>user\n'+q['new_user_message']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
    assert q['bridge_ids']==bridge_by_task.setdefault(q['task_id'],q['bridge_ids'])
    assert [t for t in q['bridge_ids'] if t in plan['tokenizer']['special_ids']]==[151645,151644,151645,151644]
    for b in q['role_boundaries']:
        assert b['context_token_offset']==len(q['old_context_ids'])+b['bridge_token_offset']
        assert q['context_ids'][b['context_token_offset']]==b['token_id']
    assert q['empty_old_assistant_closed']==(k==0)
    assert q['assistant_explicitly_closed'] and q['tokenized_template_suffix_verified']
    assert q['full_conversation_rerender_used'] is False
    assert q['original_user_prompt']==row['task']['prompt']
    text=(p/'contexts'/f'{i:03d}.txt').read_text().split('\n\nEXACT DECODED MODEL INPUT STARTS BELOW\n')[1]
    original_text='<|im_start|>user\n'+row['task']['prompt']+'<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n'
    assert text==original_text+prefix_text+q['bridge_text']
    assert saved[q['id']]['request']==request(q,plan)
    count[k]+=1
assert dict(count)=={0:112,256:112,512:108}
starts=list((p/'invocations').glob('*/started.json'));ends=list((p/'invocations').glob('*/finished.json'))
assert len(starts)==len(ends)==1
started=sealed_read(starts[0]);finished=sealed_read(ends[0]);inv=starts[0].parent.name
assert ends[0].parent.name==inv
assert started['executable_ids']==list(qmap) and started['measurement_mode']=='LIVE_LOCAL'
assert finished['new_generations']==332 and finished['reused_child_returns']==0
assert finished['model_loads']==finished['model_load_attempts']==1 and finished['status']=='COMPLETE'
assert finished['extension_revision']==started['extension_revision']=='7f78a3338225614535b90a0d520ef6c346282d13'
for field in ['new_pilot_generations','original_reruns','historical_readout_reruns','judge_calls']:assert finished[field]==0
dispatch=[sealed_read(f) for f in (p/'operation-execution').glob('*.json')]
assert len(dispatch)==332 and {d['operation_id'] for d in dispatch}==set(qmap)
for d in dispatch:
    assert d['invocation']==inv and d['extension_revision']==started['extension_revision']
events=[sealed_read(f) for f in (p/'timing-main/events').glob('*.json')]
gens=[e for e in events if e['stage']=='source_user_main_generation']
assert len(gens)==332 and collections.Counter(e['operation_id'] for e in gens)==collections.Counter(qmap.keys())
for e in gens:
    assert e['status']=='returned' and e['measurement']=='LIVE' and e['invocation']==inv
    assert e['input_tokens']==len(qmap[e['operation_id']]['context_ids'])
    assert e['output_tokens']==len(saved[e['operation_id']]['result']['tokens'])
backend=[e for e in events if e['stage']=='backend_identity'];assert len(backend)==1 and backend[0]['identity']==plan['backend']
assert all(e['measurement']=='LIVE' and e['invocation']==inv for e in events)
timing=sealed_read(p/'timing-main/invocations'/(inv+'.json'))
assert timing['status']=='COMPLETE'
raw_freq=collections.Counter((o['result']['text'],tuple(o['result']['tokens']),o['result']['finish'],o['result']['stopped'])for o in saved.values())
for o in saved.values():
    r=o['result'];assert r['finish']=='eos' and r['stopped'] is True and r['tokens'][-1]==151645
    assert r['text'] in ('A','B','C','MISSING') and not r['next_token_logits']
    expected_tokens={'A':[32,151645],'B':[33,151645],'C':[34,151645],'MISSING':[79470,1718,151645]}
    assert r['tokens']==expected_tokens[r['text']]
legacy=sealed_read(p/'legacy-values.json');assert len(legacy['values'])==664
assert digest(legacy['values'])==plan['legacy_raw_evidence_hash']
legacy_export=sealed_read(ROOT/'full_trace_audit/input/study2-v5-replication-v1/readouts-remaining-v1/measurements-v5.json')
assert legacy_export['measurement']=='LIVE'
for q in qs:
    for join in q['legacy'].values():
        v=legacy['values'][join['computation_id']]
        assert v['original_value_hash']==digest(v['value'])==join['original_value_hash']
        assert v['task_id']==q['task_id'] and v['source_row_hash']==q['source_row_hash'] and v['checkpoint']==q['checkpoint']
        old=legacy_export['results'][join['computation_id']]
        assert old['status']=='returned' and old['source_row_hash']==v['source_row_hash'] and old['value']==v['value']
result=dict(sealed_json_count=len(sealed),unsealed_derived_reports=unsealed,code_contract_verified=True,pilot_snapshot_byte_identical_files=len(actual_snapshot),source_rows_match_original_archive=len(rows),queries_validated=len(qs),legacy_raw_values_validated=len(legacy['values']),checkpoint_counts=dict(count),live_returns=len(saved),unique_dispatches=len(dispatch),live_generation_events=len(gens),model_loads=finished['model_loads'],elapsed_seconds=timing['elapsed_seconds'],timing_stages={e['stage']:e['elapsed_seconds']for e in events if 'elapsed_seconds' in e and e['stage']!='source_user_main_generation'},generation_seconds=sum(e['elapsed_seconds']for e in gens),output_tokens=sum(e['output_tokens']for e in gens),response_types=[dict(text=k[0],tokens=k[1],count=v)for k,v in raw_freq.items()],plan_hash=plan['artifact_hash'],code_contract=plan['code_contract'],revision=started['extension_revision'])
print(json.dumps(result,indent=2))
