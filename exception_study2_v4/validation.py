"""Identical-input repeats. Original-versus-fresh differences are descriptive only."""
import math
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.core import TECHNICAL as PROMPTS
from exception_continuation.validation import compare_distributions
from exception_continuation.runner import sealed_read, sealed_write
from exception_review.artifacts import freeze
from . import PROTOCOL, TECHNICAL
from .core import CUTS
from .journal import operations

def compare(first, second, tolerances, expected_vocab_size=None):
    metrics = compare_distributions(first.get('next_token_logits',{}).get('0'), second.get('next_token_logits',{}).get('0'), tolerances)
    # Legacy metrics are retained, but its combined raw-logit gate is not inherited.
    metrics.pop('passed')
    metrics['raw_logit_check_passed'] = metrics.get('logits_allclose', False)
    valid_outputs = all(isinstance(r.get('tokens'),list) and bool(r['tokens'])
        and all(type(t) is int and t>=0 for t in r['tokens']) and type(r.get('stopped')) is bool
        and r.get('finish') in ('eos','length') and r['stopped']==(r['finish']=='eos') for r in (first,second))
    vector_lengths = [len(r.get('next_token_logits',{}).get('0',[])) if isinstance(r.get('next_token_logits',{}).get('0'),list) else None for r in (first,second)]
    full_vocabulary = expected_vocab_size is None or vector_lengths==[expected_vocab_size]*2
    exact_tokens = valid_outputs and first.get('tokens') == second.get('tokens')
    finish = first.get('stopped') == second.get('stopped') and first.get('finish') == second.get('finish')
    finite = 'reason' not in metrics
    passed = bool(exact_tokens and finish and finite and metrics.get('argmax_agrees')
                  and full_vocabulary and metrics.get('probabilities_allclose') and metrics['total_variation'] <= tolerances['max_total_variation'])
    return dict(technical_same_input_passed=passed, exact_tokens=exact_tokens, finish_agrees=finish,
                finite_telemetry=finite, full_vocabulary=full_vocabulary, vocabulary_sizes=vector_lengths,
                expected_vocab_size=expected_vocab_size, valid_output_metadata=valid_outputs, distribution=metrics, raw_logits_gating=False,
                decision='PASS_IDENTICAL_INPUT' if passed else 'FAIL_IDENTICAL_INPUT')

def eligible(base, special_ids):
    return [k for k in CUTS if k < len(base['tokens']) and not any(t in special_ids for t in base['tokens'][:k])]

def build_report(plan, execution, saved):
    records=[]; all_pass=True; expected_operations=set()
    for i,prompt in enumerate(PROMPTS):
        expected_operations.add(f'v4/technical/{i}/original')
        base_op=saved[f'v4/technical/{i}/original']; base=base_op['result']; ids=base_op['request']['input_ids']
        if base_op['request'] != dict(input_ids=ids,context_hash=digest(ids),budget=128,capture_at=[],fresh_prefill=True):
            raise ValueError('Technical original request changed')
        cuts=eligible(base,execution['backend'].get('special_ids',[0,1000000])); repeats=[]
        all_pass=all_pass and bool(cuts)
        for k in cuts:
            context=ids+base['tokens'][:k]; results=[]; hashes=[]
            for label in ('a','b'):
                expected_operations.add(f'v4/technical/{i}/fresh/{k}/{label}')
                op=saved[f'v4/technical/{i}/fresh/{k}/{label}']
                if op['request'] != dict(input_ids=context,context_hash=digest(context),budget=128-k,capture_at=[0],fresh_prefill=True):
                    raise ValueError('Same-input technical request changed')
                results.append(op['result']);hashes.append(op['artifact_hash'])
            checked=compare(*results,plan['config']['validation_tolerances'],
                            expected_vocab_size=151936 if execution['mode']=='LIVE_LOCAL' else None)
            all_pass=all_pass and checked['technical_same_input_passed']
            diagnostic=all(results[0].get(x)==(base['tokens'][k:] if x=='tokens' else base.get(x)) for x in ('tokens','stopped','finish'))
            repeats.append(dict(k=k,context_hash=digest(context),operation_hashes=hashes,**checked,
                                original_vs_fresh=dict(exact_suffix_match=diagnostic,gating=False)))
        records.append(dict(prompt=prompt,input_ids=ids,base_operation_hash=base_op['artifact_hash'],repeats=repeats))
    if {k for k in saved if k.startswith('v4/technical/')} != expected_operations:
        raise ValueError('Unexpected technical operations outside the fixed request budget')
    return dict(protocol=PROTOCOL,technical_gate=TECHNICAL,plan_hash=plan['plan_hash'],backend_hash=execution['backend_hash'],
                measurement='MOCK' if execution['mode']=='MOCK' else 'LIVE',
                real_model_status='PENDING' if execution['mode']=='MOCK' else 'V4_SAME_INPUT_PASSED' if all_pass else 'FAILED',
                technical_same_input_passed=bool(all_pass),records=records,
                operation_count=3+2*sum(len(r['repeats']) for r in records),maximum_operations=33,
                maximum_generated_tokens=3882,original_vs_fresh_is_gating=False)

def require_technical(output, plan, execution):
    if (execution.get('protocol')!=PROTOCOL or execution.get('mode') not in ('MOCK','LIVE_LOCAL')
            or execution['backend_hash']!=digest(execution['backend'])):
        raise ValueError('Invalid v4 execution identity')
    if execution['mode']=='LIVE_LOCAL' and (execution['backend'].get('kind')!='LOCAL_HF_TOKEN_IDS'
            or execution['backend'].get('config')!=plan['config']):
        raise ValueError('Live technical backend does not match the pinned plan')
    value=sealed_read(Path(output)/'technical-v4.json')
    saved=operations(output)
    selected={k:v for k,v in saved.items() if k.startswith('v4/technical/')}
    for op in selected.values():
        if (op['status']!='returned' or op['plan_hash']!=plan['plan_hash'] or op['backend_hash']!=execution['backend_hash']
                or op['source_hash']!=plan['source_hash'] or op['protocol']!=PROTOCOL):
            raise ValueError('Technical operation identity/status differs')
    expected=build_report(plan,execution,selected)
    if expected != {k:v for k,v in value.items() if k!='artifact_hash'} or not value['technical_same_input_passed']:
        raise ValueError('v4 identical-input technical gate FAILED or changed; collection blocked')
    return value

def validate(session):
    path=session.out/'technical-v4.json'
    if path.exists():
        result=require_technical(session.out,session.plan,session.execution)
        if session.telemetry:session.telemetry.record(stage='technical_same_input',measurement='CACHE',status='cache_hit')
        return result
    try:
        for i,prompt in enumerate(PROMPTS):
            ids=session.backend.prompt(prompt)
            base=session.generate(f'v4/technical/{i}/original',ids,128)
            for k in eligible(base,session.backend.special_ids):
                for label in ('a','b'):
                    session.generate(f'v4/technical/{i}/fresh/{k}/{label}',ids+base['tokens'][:k],128-k,capture_at=(0,))
        report=freeze(path,build_report(session.plan,session.execution,operations(session.out)))
        sealed_write(session.out/'technical-status-v4.json',dict(protocol=PROTOCOL,plan_hash=session.plan['plan_hash'],
                     technical_hash=report['artifact_hash'],technical_same_input_passed=report['technical_same_input_passed'],
                     measurement=report['measurement'],real_model_status=report['real_model_status']))
        if not report['technical_same_input_passed']:raise ValueError('v4 identical-input repeatability FAILED; STOP')
        return report
    except BaseException as exc:
        if not path.exists():
            sealed_write(session.out/'technical-status-v4.json',dict(protocol=PROTOCOL,plan_hash=session.plan['plan_hash'],
                technical_same_input_passed=False,measurement='MOCK' if session.backend.simulated else 'LIVE',
                real_model_status='PENDING' if session.backend.simulated else 'FAILED',reason=type(exc).__name__))
        raise
