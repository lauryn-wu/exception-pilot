"""Arm coverage from frozen cohort, saved assessments and model operations.

Validity here means answer syntax; replay gates are a separate axis. Unknown
or partially persisted assessments are never recomputed as wrong answers.
"""
from pathlib import Path
from exception_continuation.runner import sealed_read
from .policy import ARMS


def intervention_coverage(cases,results,output,source_hash,manifest_hash):
    byid={r['task_id']:r for r in results}; ops={}
    for path in (Path(output)/'model-operations').glob('*.json'):
        entry=sealed_read(path)
        if entry['source_hash']!=source_hash or entry['manifest_hash']!=manifest_hash:
            raise ValueError('Intervention coverage operation binding changed')
        ops[entry['id']]=entry
    names=(*ARMS,'unchanged'); coverage={}; details=[]
    fields=('planned','attempted','returned','valid','invalid','truncated','missing',
            'unassessed','unattempted','attempted_without_return','replay_excluded',
            'replay_unassessed','analysis_valid','valid_replay_excluded','valid_replay_unassessed',
            'unassessed_truncated','candidate_scoring_attempted','candidate_scoring_returned',
            'candidate_scoring_failed','candidate_scoring_missing','candidate_readout_assessed')
    for arm in names:
        counts={k:0 for k in fields}
        for case in cases:
            tid=case['task_id']; row=byid.get(tid,{}); obs=row.get('arms',{}).get(arm,{})
            continuation=ops.get(f'edit/{tid}/{arm}/continuation')
            readout=ops.get(f'edit/{tid}/{arm}/readout')
            attempted=continuation is not None
            returned=bool(continuation and continuation['status']=='returned')
            # Journal is authoritative for dispatch and return, even when an
            # interrupt prevented interventions.json from being assembled.
            raw=continuation.get('result',{}) if returned else {}
            score=obs.get('score',{}) if returned else {}
            valid=score.get('valid') is True; invalid=score.get('valid') is False
            unassessed=returned and not (valid or invalid)
            branch=row.get('validation',{}).get('passed')
            control=row.get('unchanged_replay_passed')
            replay='excluded' if branch is False or control is False else 'passed' if branch is True and control is True else 'unassessed'
            scoring_returned=bool(readout and readout['status']=='returned')
            counts['planned']+=1; counts['attempted']+=attempted; counts['returned']+=returned
            counts['valid']+=valid; counts['invalid']+=invalid; counts['unassessed']+=unassessed
            counts['truncated']+=invalid and raw.get('stopped') is False
            counts['unassessed_truncated']+=unassessed and raw.get('stopped') is False
            counts['missing']+=not returned; counts['unattempted']+=not attempted
            counts['attempted_without_return']+=attempted and not returned
            counts['replay_excluded']+=replay=='excluded'; counts['replay_unassessed']+=replay=='unassessed'
            counts['analysis_valid']+=valid and replay=='passed'
            counts['valid_replay_excluded']+=valid and replay=='excluded'
            counts['valid_replay_unassessed']+=valid and replay=='unassessed'
            counts['candidate_scoring_attempted']+=readout is not None
            counts['candidate_scoring_returned']+=scoring_returned
            counts['candidate_scoring_failed']+=readout is not None and not scoring_returned
            counts['candidate_scoring_missing']+=not scoring_returned
            counts['candidate_readout_assessed']+=scoring_returned and 'readout' in obs
            details.append(dict(task_id=tid,arm=arm,attempted=attempted,returned=returned,
                                syntax='valid' if valid else 'invalid' if invalid else 'unassessed' if returned else 'missing',
                                replay=replay,readout_returned=scoring_returned,readout_assessed='readout' in obs))
        assert counts['planned']==counts['valid']+counts['invalid']+counts['unassessed']+counts['missing']
        assert counts['returned']==counts['valid']+counts['invalid']+counts['unassessed']
        assert counts['missing']==counts['unattempted']+counts['attempted_without_return']
        assert counts['valid']==counts['analysis_valid']+counts['valid_replay_excluded']+counts['valid_replay_unassessed']
        assert counts['truncated']<=counts['invalid']
        coverage[arm]=counts
    return dict(per_arm=coverage,details=details,
                definitions=dict(valid='Assessed answer syntax only; correctness and replay validity are separate.',
                                 invalid='Assessed invalid syntax, including truncation; never automatically wrong.',
                                 truncated='Assessed invalid outputs with stopped=false; subset of invalid.',
                                 missing='No returned continuation, including unattempted and failed/started operations.',
                                 unassessed='Returned continuation whose answer score was not persisted.',
                                 replay_excluded='Known failed branch/control gate; overlaps syntax and missing counts.',
                                 candidate_scoring='Complete three-candidate readout operations, separate from answer assessment.'),
                identities=['planned = valid + invalid + unassessed + missing',
                            'returned = valid + invalid + unassessed',
                            'missing = unattempted + attempted_without_return',
                            'valid = analysis_valid + valid_replay_excluded + valid_replay_unassessed',
                            'truncated <= invalid'])
