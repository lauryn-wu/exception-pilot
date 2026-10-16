"""Read-only proof of every historical vote, source span and salvage result."""
from pathlib import Path
from exception_pilot.core import digest
from exception_continuation.runner import sealed_read
from exception_study2_v5_review_v2.workflow import Review as HistoricalReview
from exception_study2_v5_review_v2 import candidates as canonical
from exception_study2_v5_review_v22 import salvage,decisions,policy


class History:
    def __init__(self,review,salvage_path):
        self.review=HistoricalReview(review);self.root=Path(salvage_path).resolve()
        self.report=sealed_read(self.root/'salvage-report.json')
        self.side=sealed_read(self.root/'retrospective-observations.json')
        self.audit=sealed_read(self.root/'operation-audit.json')
        self.manifest=sealed_read(self.root/'annotation-manifest-v5-retrospective.json')
        p=self.report['provenance'];r=self.review
        if (p!=self.side['provenance'] or p!=self.audit['provenance']
            or p['salvage_code_hash']!=policy.code_hash() or p['source_review_plan_hash']!=r.plan['artifact_hash']
            or p['source_policy_hash']!=r.policy['policy_hash']
            or p['original_manifest_hash']!=sealed_read(r.root/'annotation-manifest-v5.json')['artifact_hash']
            or p['original_observations_hash']!=sealed_read(r.root/'observations-v2.json')['artifact_hash']
            or self.report['alternative_manifest_hash']!=self.manifest['artifact_hash']):
            raise ValueError('Historical/salvage identity mismatch')
        roots=(r.root,r.source_original.root)
        if {str(path):digest(salvage.snapshot(path)) for path in roots}!=p['historical_source_tree_hashes']:
            raise ValueError('Historical source tree changed since salvage')
        self.operations=salvage.validated_operations(r)
        if set(self.side['cases'])!=set(r.plan['case_ids']):raise ValueError('Salvage population mismatch')
        for tid,saved in self.side['cases'].items():
            packet=r.plan['packets'][tid];paths=[];phases=[];extractions={}
            for phase in ('primary','audit'):
                op=self.operations.get((tid,phase,'J1' if phase=='primary' else 'J2','draft' if phase=='primary' else 'verify'))
                if op and op['view']!=packet:raise ValueError('Extraction source changed')
                parsed=op['parsed'] if op else dict(valid=False,value=None,reason='missing_extraction_operation')
                ex=canonical.extraction(parsed.get('value'),packet,parsed['valid'],parsed.get('reason'))
                if ex!=saved['extractor' if phase=='primary' else 'auditor']:raise ValueError('Salvaged coverage changed')
                extra=[('semantic-extractor' if phase=='primary' else 'negative-audit',ex['candidates'])]
                if phase=='primary':extra.insert(0,('structural',canonical.structural_candidates(packet)))
                cs=canonical.merge(packet,extra);paths+=extra;votes={}
                for judge in ('J1','J2','J3'):
                    op=self.operations.get((tid,phase,judge,'adjudicate' if judge=='J3' else 'initial'))
                    if not op:continue
                    if op['view']!=dict(packet,candidates=cs):raise ValueError('Historical source/candidate alignment mismatch')
                    parsed=op['parsed']
                    vote=decisions.partial_vote(parsed.get('value'),packet,cs,parsed['valid'],parsed.get('reason'),historical=True)
                    votes[judge]=dict(vote,operation_key=op['record']['key'],operation_hash=op['record']['artifact_hash'])
                combined=decisions.reconcile(cs,votes,r.policy['config']['judges'])
                if saved['phases'][phase]!=dict(candidates=cs,votes=votes,reconciliation=combined):raise ValueError('Historical vote revalidation mismatch')
                phases.append(combined);extractions[phase]=ex
            cs=canonical.merge(packet,paths)
            if cs!=saved['candidates']:raise ValueError('Salvage candidate population changed')
            result=decisions.finalize(packet,cs,phases,extractions['primary'],extractions['audit'])
            for d in list(result['events'].values())+[result['substitution']]:d['rationale']='RETROSPECTIVE SENSITIVITY ANALYSIS. '+d['rationale']
            if result!=saved['result'] or saved['source_row_hash']!=packet['source_row_hash']:raise ValueError('Salvage decisions do not reproduce')
        self.binding=dict(review=str(r.root),salvage=str(self.root),review_plan_hash=r.plan['artifact_hash'],
            source_hash=r.source_original.hash,salvage_report_hash=self.report['artifact_hash'],
            observations_hash=self.side['artifact_hash'],operation_audit_hash=self.audit['artifact_hash'],
            prior_manifest_hash=self.manifest['artifact_hash'],
            historical_tree_hashes=p['historical_source_tree_hashes'],salvage_tree_hash=digest(salvage.snapshot(self.root)))
        self.cases=self.side['cases'];self.packets=r.plan['packets']
