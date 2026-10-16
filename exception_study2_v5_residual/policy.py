"""Freeze the existing semantic contract with a two-provider, no-adjudication policy."""
from pathlib import Path
from exception_pilot.core import digest
from exception_study2_v5_review_v22 import policy as v22
from . import VERSION

SCHEMAS = v22.SCHEMAS
UNTRUSTED = v22.UNTRUSTED
RUBRICS = dict(v22.RUBRICS)
RUBRICS['detect'] += '''
RESIDUAL REVIEW: This is the complete frozen batch assigned to you.
The cases array contains independent trajectories. Each has a complete source packet
and its requested candidates. Return each candidate's exact namespaced id (including
the task prefix); never transfer evidence between cases. prior_ack_id refers to a
canonical statement in THAT candidate's source packet. Review all supplied cases. Review only these
candidate/event IDs, with the entire unchanged source for context. Prior judgments
are deliberately not shown. Distinguish a statement of the recorded Verified class
from a prediction that happens to match it. A feature list alone is not A. Keep P as
an observational pattern-substitution diagnostic, never a third failure family or
an automatic O. The only primary failure families are M and strict O.
'''
RUBRICS['verify'] += '''
RESIDUAL COVERAGE REVIEW: Review the full text for the requested coverage_events.
Return the standard full-text and per-event search/detection fields, all plausible
candidates and corrections. Existing judgments are not shown. Complete coverage with
no event is complete/no, never incomplete merely because no event was found. Extra
candidate discoveries will be held for a separate plan, not automatically dispatched.
'''

def code_hash():
    return digest({p.name:p.read_text() for p in sorted(Path(__file__).parent.glob('*.py'))})


def freeze_policy(config):
    base = v22.freeze_policy(config)
    result = dict(base, rubrics=RUBRICS, schemas=SCHEMAS, code_hash=code_hash(),
        reused_v22_code_hash=v22.code_hash(),
        rules=dict(version=VERSION, primary_families=['M','O'], supporting_annotations=['A','C','X'],
            observational_sidecar=['P'], automatic_judges=['J1','J2'], automatic_adjudication=False,
            historical_provider_rule='J1 primary/audit positions; J3 only if J1 has no conclusive revalidated vote. Never majority-count same-provider repetitions.',
            agreement='One consistent conclusive position per provider; cross-provider disagreement remains uncertain.',
            requests='Only missing/invalid provider evidence for unresolved dispatch-eligible candidates, plus failed coverage obligations.',
            acknowledgment='Historical and new positive A require the identical recorded_witness source gate AND independent semantic passes. No witness means uncertain, never automatic absence.',
            source_deferral='Unresolved A without the frozen recorded_witness is retained uncertain but excluded from paid verification. Preserve required_providers as evidence gaps; dispatch_providers is empty. No source edits or new protocol implicit.',
            coverage='Fresh separate evidence; never rewrite historical flags. New candidate discoveries require another plan.',
            retries=0, smoke_lifetime_max_calls=4, smoke_requires_separate_authorization=True,
            full_review_requires_separate_authorization=True, batch_target=config['batch_size']))
    result.pop('policy_hash',None)
    result['policy_hash'] = digest(result)
    return result
