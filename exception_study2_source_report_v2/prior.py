"""Read-only provenance inspection: retain v1's own failed classification."""
import json
from pathlib import Path
from types import SimpleNamespace
from exception_continuation.runner import sealed_read
from exception_study2_source_report.execution import journal,parsed,gate,state
from .integrity import sha
from . import V1_PLAN_HASH,REVISION_REASON


def prior_evidence(root,tok):
    reference=dict(reference_plan_hash=V1_PLAN_HASH,revision_reason=REVISION_REASON,
        reported_v1_status='FAILED',diagnostics_are_post_hoc=True,
        reported_diagnostics=dict(source_present_prose_correct=8,source_present_total=8,
            missing_prose_stated_missing=2,missing_total=4),
        diagnostic_provenance='User-supplied pilot observations; not passing v1 scores or v2 results.')
    if root is None or not Path(root).exists():
        return dict(reference,available=False,actual_artifact_hashes={},
            inspection='V1 GPU output unavailable locally; reference hash retained without fabricating artifacts.')
    root=Path(root).resolve();plan=sealed_read(root/'source-report-plan.json')
    if plan['version']!='study2-source-report-v1' or plan['artifact_hash']!=V1_PLAN_HASH:
        raise ValueError('V1 provenance must match the specified failed v1 plan hash')
    tok.verify_backend(plan['backend'])
    queries={q['id']:q for q in plan['calibration']+plan['main']}
    c=SimpleNamespace(out=root,plan=plan,queries=queries,tokenizer=tok)
    saved,mode=journal(c);answers=parsed(c,saved);g=gate(c,saved,answers)
    if mode!='LIVE_LOCAL' or len(plan['calibration'])!=12 or len(plan['main'])!=332:
        raise ValueError('V1 provenance must describe the saved live 12+332 plan')
    if g['status']!='FAILED' or any(state(saved.get(q['id']))!='returned' for q in plan['calibration']):
        raise ValueError('V1 failed calibration evidence differs; do not reinterpret it')
    if any(state(saved.get(q['id']))!='never_started' for q in plan['main']):
        raise ValueError('V1 main was expected never-started; preserve and inspect divergent evidence')
    historical=json.loads((root/'report.json').read_text())
    if historical['plan_hash']!=V1_PLAN_HASH or historical['calibration_gate']!=g:
        raise ValueError('Saved v1 report differs from its original-parser journal verdict')
    recorded={q['operation_id']:q['source_report'] for q in historical['calibration']}
    if recorded!={q['id']:answers[q['id']] for q in plan['calibration']}:
        raise ValueError('Saved v1 calibration report differs from original parser')
    artifacts={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('V1 provenance refuses symlinked artifacts')
        if not p.is_file() or p.name=='run.lock':continue
        if p.suffix not in ('.json','.md','.txt'):
            raise ValueError('Unexpected non-artifact in v1 evidence; no weights are read')
        value=dict(sha256=sha(p))
        if p.suffix=='.json' and p.name not in ('report.json',):
            sealed=sealed_read(p);value['sealed_artifact_hash']=sealed['artifact_hash']
        artifacts[str(p.relative_to(root))]=value
    return dict(reference,available=True,actual_plan_hash=plan['artifact_hash'],
        v1_code_contract=plan['code_contract'],backend_hash=plan['backend_hash'],
        source_binding={k:plan['source'][k] for k in ('remaining','pilot','historical_execution_hash')},
        actual_artifact_hashes=artifacts,original_parser_gate=g,
        returned_calibration=12,valid_v1_calibration=sum(a['valid'] for a in answers.values()),
        v1_length_stops=sum(a['truncated'] for a in answers.values()),main_never_started=332,
        inspection='Read-only immutable-journal validation using the unchanged v1 parser; no v2 reclassification.')
