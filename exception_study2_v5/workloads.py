"""Counts are ceilings, never fabricated live measurements."""
from . import BUDGET

def workload(worlds):
    originals=8*worlds;visible=4*worlds
    family=dict(max_events=visible,max_edited_continuations=4*visible,
                generated_token_ceiling=4*visible*BUDGET,max_candidate_sequences=24*visible,
                actual_generated_budget='sum(4 * (2048-original_k)) over frozen eligible cases',
                annotation_requests=0,annotation_mode='independent manual reviewers; no paid calls')
    return dict(worlds=worlds,originals=originals,visible=visible,original_token_ceiling=originals*BUDGET,
                technical=dict(generation_calls=33,generated_tokens=3882),
                study_2a=dict(fixed_and_pre_answer_positions=6*visible,event_positions=8*visible,
                    max_distinct_readouts=28*visible,max_candidate_sequences=84*visible,generated_answers=0,
                    deduplication='Exact task/cut/cue, within one combined fixed+event plan'),
                family_M=family,family_O=dict(family),
                timing_status='NOT_MEASURED_LIVE')

def report():
    return {phase:workload(w) for phase,w in [('pilot',4),('selection',12),('confirmation',48)]}
