"""Read-only native journal or explicitly limited exported-summary evidence."""
import math
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5.runner import Source,binding_identity
from exception_study2_v5_replication.readouts import expected_plan,read_data,validate_value
from . import CANDIDATES


def preference(scores):
    peak=max(scores.values());ties=[c for c in 'ABC' if scores[c]==peak]
    log_mass=peak+math.log(sum(math.exp(v-peak) for v in scores.values()))
    mass=math.exp(log_mass)
    if mass>1+1e-6:raise ValueError('Class-token ABC probability mass exceeds one')
    return dict(logprobs=scores,preferred_class=ties[0] if len(ties)==1 else None,tied_classes=ties if len(ties)>1 else [],
        abc_mass=mass,abc_log_mass=log_mass,restricted_probabilities={c:math.exp(v-log_mass) for c,v in scores.items()})


def _validate_legacy(value,row,computation,tok):
    validate_value(value,row,computation)
    if value['cue_ids']!=tok.encode(computation['cue_text']):raise ValueError('Legacy cue token IDs differ')
    if {c:value['scores'][c]['tokens'] for c in 'ABC'}!=CANDIDATES:
        raise ValueError('Unsupported legacy candidate tokenization; expected class token then newline')
    # Validate arithmetic of BOTH interpretations; retain the original values intact.
    first=preference({c:value['scores'][c]['token_logprobs'][0] for c in 'ABC'})
    whole=preference({c:value['scores'][c]['logprob'] for c in 'ABC'})
    return dict(class_token=first,whole_sequence_sensitivity=whole,
                original_value_hash=digest(value),candidate_token_mapping=CANDIDATES)


def validate_legacy(value,row,computation,tok):
    try:return _validate_legacy(value,row,computation,tok)
    except (KeyError,TypeError,IndexError) as exc:
        raise ValueError('Required legacy content absent or malformed: '+str(exc)) from exc


def legacy(source,folder,tok):
    folder=Path(folder).resolve();expected=expected_plan(source,folder)
    plan_path=folder/'measurement-plan-v5.json';summary_path=folder/'measurements-v5.json'
    journals=folder/'operations-v5';has_journals=journals.exists() and any(journals.iterdir())
    if has_journals:
        if not plan_path.is_file() or not (folder/'execution-v5.json').is_file():
            raise ValueError('Partial native evidence: readout journals require their plan and execution metadata')
        plan,data=read_data(source,folder);mode='native_journals';plan_hash=plan['artifact_hash'];reproduced=True
        evidence_hash=digest(dict(plan=plan,results=data,execution=sealed_read(folder/'execution-v5.json')))
    else:
        if not summary_path.is_file():raise ValueError('Required sealed measurements-v5.json absent; no inference backfill permitted')
        data=sealed_read(summary_path);plan_hash=data['plan_hash'];mode='exported_summary'
        if data.get('measurement')!='LIVE':raise ValueError('Exported summary must identify saved LIVE measurements')
        if plan_path.exists():
            plan=sealed_read(plan_path)
            if (binding_identity(plan['source'])!=source.binding
                or any(plan.get(k)!=v for k,v in expected.items() if k!='source')
                or plan['artifact_hash']!=plan_hash):raise ValueError('Exported legacy plan/source/hash differs')
            reproduced=True
        else:
            plan=expected;reproduced=digest(expected)==plan_hash
        evidence_hash=data['artifact_hash']
    if set(data['results'])!=set(expected['computations']):raise ValueError('Legacy computation population/IDs differ from saved originals')
    validated={}
    for key,c in expected['computations'].items():
        r=data['results'][key];row=source.rows[c['task_id']]
        if r['status']!='returned':
            if r['status'] not in ('unavailable','unattempted'):raise ValueError('Unknown legacy measurement status')
            validated[key]=dict(status=r['status']);continue
        if r.get('source_row_hash')!=row['artifact_hash'] or r.get('world')!=row['task']['world']:
            raise ValueError('Legacy source-row/world binding differs')
        validated[key]=dict(status='returned',**validate_legacy(r['value'],row,c,tok))
    provenance=dict(legacy_provenance_mode=mode,evidence_hash=evidence_hash,historical_plan_hash=plan_hash,
        reconstructed_plan_hash=digest(expected),plan_hash_independently_reproduced=reproduced,
        plan_reference_status='independently_reproduced' if reproduced else 'preserved_unverified_historical_reference',
        plan_reference_limit=None if reproduced else 'Export omits the original relative source path/plan; content checks do not authenticate that absent historical file.',
        checks=['sealed_summary' if mode=='exported_summary' else 'sealed_native_plan_execution_and_operations',
            'reconstructed_computation_ids','source_row_bindings','exact_context_ids_and_hashes','cue_text_and_ids',
            'pinned_candidate_tokens','finite_nonpositive_token_logprobs','sequence_sums','normalized_probabilities',
            'verified_pattern_log_odds','class_token_abc_mass'],journal_level_verified=mode=='native_journals')
    return validated,provenance


class Evidence:
    def __init__(self,originals,readouts,tok):
        # Each scope and the legacy score index are constructed ONCE per invocation.
        self.remaining=Source(originals,scope='remaining')
        self.pilot=Source(originals,scope='pilot')
        self.tokenizer=tok;tok.verify_backend(self.remaining.execution['backend'])
        if self.remaining.execution!=self.pilot.execution:raise ValueError('Pilot/remaining backend identity differs')
        self.legacy,self.provenance=legacy(self.remaining,readouts,tok)
        self.binding=dict(remaining=self.remaining.binding,pilot=self.pilot.binding,
            historical_execution_hash=self.remaining.execution['artifact_hash'],
            historical_revision=self.remaining.execution['code_revision'],technical_hash=self.remaining.technical['artifact_hash'],
            legacy=self.provenance)
