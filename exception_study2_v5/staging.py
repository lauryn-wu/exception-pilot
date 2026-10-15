"""Explicit human decisions; zero desired events never blocks the remaining fixed sample."""
import json
import os
from pathlib import Path
from exception_continuation.runner import sealed_read
from exception_pilot.core import digest
from exception_review.artifacts import freeze
from .core import read_plan, DESIGN_VERSION
from .runner import Source, binding_identity, bound_source

CHECKS=('rendering_and_eight_matched_conditions','verified_pattern_and_target_lookup',
        'pinned_bf16_greedy_thinking_template_and_2048_cap','completion_truncation_and_both_parsers',
        'checkpoints_and_cue_sensitivity','annotation_quality_and_event_definitions',
        'source_spans_and_token_boundaries','four_arm_semantics_and_label_leak',
        'fresh_prefix_and_unchanged_diagnostics','immutable_journals_and_resume')

def confirm_design(output, reviewer, rationale, worlds=60):
    plan=read_plan(output)
    if worlds!=60 or not reviewer.strip() or not rationale.strip():raise ValueError('Confirm 60 prespecified worlds with reviewer and rationale')
    if any((Path(output)/'originals-v5').glob('*.json')):raise ValueError('Sample-size confirmation must precede originals')
    return freeze(Path(output)/'design-confirmation-v5.json',dict(design_version=DESIGN_VERSION,
        plan_hash=plan['plan_hash'],worlds=worlds,reviewer=reviewer,rationale=rationale,confirmed=True))

def require_design_confirmation(output):
    plan=read_plan(output);value=sealed_read(Path(output)/'design-confirmation-v5.json')
    if value['plan_hash']!=plan['plan_hash'] or value['worlds']!=60 or value['confirmed'] is not True:
        raise ValueError('Sample-size confirmation differs from frozen design')
    return value

def pilot_checklist(source_path, output, measurements, annotations, family_m, family_o, event_measurements=None):
    source=Source(source_path,scope='pilot');path=Path(output)
    from .review.workflow import read_manifest
    from .reporting import annotation_report
    ann=read_manifest(annotations,source)
    evidence={};layouts=[]
    refs= [('measurements',measurements),('annotations',annotations),('family_m',family_m),('family_o',family_o)]
    if event_measurements:refs.append(('event_measurements',event_measurements))
    for label,ref in refs:
        ref=Path(ref);value=sealed_read(ref)
        if label in ('measurements','event_measurements'):
            parent=sealed_read(ref.parent/'measurement-plan-v5.json')
            if value['plan_hash']!=parent['artifact_hash']:raise ValueError('Measurement plan mismatch')
            layouts.append(parent['layout'])
            if parent['layout']!='fixed_only' and parent['annotations_hash']!=ann['artifact_hash']:raise ValueError('Measurement annotations mismatch')
        elif label.startswith('family_'):
            parent=sealed_read(ref.parent/'intervention-manifest-v5.json')
            if value['manifest_hash']!=parent['artifact_hash'] or parent['family']!=('M' if label=='family_m' else 'O'):
                raise ValueError('Intervention manifest mismatch')
        else: parent=value
        if binding_identity(parent['source'])!=source.binding:raise ValueError('Pilot evidence uses a different source snapshot')
        bound_source(parent['source'],ref.parent)
        evidence[label]=dict(path=os.path.relpath(ref.resolve(),path.parent.resolve()),artifact_hash=value['artifact_hash'],
                             parent_hash=parent['artifact_hash'])
    if not ('combined' in layouts or {'fixed_only','events_only'}<=set(layouts)):
        raise ValueError('Review both fixed and event readouts, including unavailable events')
    value=freeze(path,dict(schema='v5-pilot-checklist-v1',source=source.binding_at(path.parent),evidence=evidence,
        coverage=annotation_report(source,ann),technical_hash=source.technical['artifact_hash'],
        behavioral_success_threshold=None,required_checks=list(CHECKS),next_stage='STOP_HUMAN_REVIEW'))
    template=path.with_name('pilot-review-template.json')
    if not template.exists():
        with template.open('x') as f:json.dump(dict(checklist_hash=value['artifact_hash'],reviewer='',rationale='',
            approve_remaining=False,scientific_protocol_unchanged=True,technical_repairs=[],
            pilot_informed_method_design=False,checks={c:dict(status='not_reviewed',evidence='') for c in CHECKS}),f,indent=2)
    return value

def check_checklist(output, checklist):
    source=Source(output,scope='pilot');path=Path(checklist);value=sealed_read(path)
    if binding_identity(value['source'])!=source.binding or value.get('schema')!='v5-pilot-checklist-v1':
        raise ValueError('Pilot checklist identity mismatch')
    bound_source(value['source'],path.parent)
    for ref in value['evidence'].values():
        if sealed_read(path.parent/ref['path'])['artifact_hash']!=ref['artifact_hash']:raise ValueError('Pilot evidence changed')
    refs={k:path.parent/v['path'] for k,v in value['evidence'].items()}
    rebuilt=pilot_checklist(output,path,refs['measurements'],refs['annotations'],refs['family_m'],refs['family_o'],refs.get('event_measurements'))
    if rebuilt!=value:raise ValueError('Pilot checklist evidence changed')
    return source,value

def check_decision(value, decision):
    if (decision.get('checklist_hash')!=value['artifact_hash'] or not decision.get('reviewer','').strip()
        or not decision.get('rationale','').strip() or decision.get('approve_remaining') is not True
        or decision.get('scientific_protocol_unchanged') is not True
        or type(decision.get('pilot_informed_method_design')) is not bool
        or not isinstance(decision.get('technical_repairs'),list) or set(decision.get('checks',{}))!=set(CHECKS)):
        raise ValueError('Explicit approval and unchanged scientific protocol required; changed protocols need a new version, with affected pilot exploratory')
    for key,c in decision['checks'].items():
        if c.get('status') not in ('passed','not_applicable_zero_cases') or not c.get('evidence','').strip():
            raise ValueError('Every technical/semantic check needs a completed review and evidence: '+key)
        if c['status']=='not_applicable_zero_cases' and (key not in ('source_spans_and_token_boundaries','four_arm_semantics_and_label_leak')
            or any(v['cases'] for v in value['coverage']['families'].values())):
            raise ValueError('Zero-case exemption applies only to absent event/edit cases')
    return decision

def approve_remaining(output, checklist, decisions):
    source,value=check_checklist(output,checklist)
    decision=check_decision(value,json.loads(Path(decisions).read_text()))
    return freeze(Path(output)/'remaining-approval-v5.json',dict(schema='v5-remaining-approval-v1',
        source=source.binding_at(output),checklist=value,decisions=decision,
        checklist_path=os.path.relpath(Path(checklist).resolve(),Path(output).resolve()),
        remaining_worlds=56,remaining_originals=448,scientific_plan_hash=source.plan['plan_hash'],
        pilot_inclusion='eligible_under_unchanged_fixed_sample_protocol',automatic_execution=False))

def require_approval(output):
    source=Source(output,scope='pilot');approval=sealed_read(Path(output)/'remaining-approval-v5.json')
    if (approval.get('schema')!='v5-remaining-approval-v1' or binding_identity(approval['source'])!=source.binding
        or approval['scientific_plan_hash']!=source.plan['plan_hash'] or approval['remaining_worlds']!=56
        or approval['decisions']['approve_remaining'] is not True
        or approval['decisions']['scientific_protocol_unchanged'] is not True):
        raise ValueError('Remaining batch has no valid source-bound approval')
    _,checklist=check_checklist(output,Path(output)/approval['checklist_path'])
    if checklist!=approval['checklist']:raise ValueError('Approval checklist changed')
    check_decision(checklist,approval['decisions'])
    return approval
