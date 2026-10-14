"""Per-arm journal coverage with independent availability and unknown outcomes."""
from ..journal import operations
from ..core import ARMS


def intervention_coverage(cases,results,output,source_hash,manifest_hash):
    saved=operations(output);byid={r['task_id']:r for r in results};coverage={};details=[]
    for op in saved.values():
        if op.get('source_binding')!=source_hash or op.get('manifest_hash')!=manifest_hash:raise ValueError('Coverage provenance changed')
    for arm in ARMS:
        counts={k:0 for k in ('planned','attempted','returned','valid','invalid','truncated','missing','unassessed','unattempted','attempted_without_return','arm_input_invalid','analysis_valid','candidate_readout_attempted','candidate_readout_returned','candidate_readout_valid')}
        for case in cases:
            tid=case['task_id'];obs=byid.get(tid,{}).get('arms',{}).get(arm,{})
            op=saved.get(f'v4/edit/{tid}/{arm}/continuation');probe=saved.get(f'v4/edit/{tid}/{arm}/readout')
            attempted=bool(op and op['status']!='planned');returned=bool(op and op['status']=='returned');raw=op['result'] if returned else {}
            score=obs.get('score',{}) if returned else {};valid=score.get('valid') is True;invalid=score.get('valid') is False
            counts['planned']+=1;counts['attempted']+=attempted;counts['returned']+=returned
            counts['valid']+=valid;counts['invalid']+=invalid;counts['unassessed']+=returned and not (valid or invalid)
            counts['truncated']+=returned and raw.get('finish')=='length';counts['missing']+=not returned
            counts['unattempted']+=not attempted;counts['attempted_without_return']+=attempted and not returned
            counts['arm_input_invalid']+=obs.get('arm_input_valid') is False
            counts['analysis_valid']+=valid and obs.get('arm_input_valid') is True and obs.get('prefix_text_preserved') is True
            counts['candidate_readout_attempted']+=bool(probe and probe['status']!='planned')
            counts['candidate_readout_returned']+=bool(probe and probe['status']=='returned')
            counts['candidate_readout_valid']+=obs.get('conditional_readout_valid') is True
            details.append(dict(task_id=tid,arm=arm,attempted=attempted,returned=returned,arm_input_valid=obs.get('arm_input_valid'),
                syntax='valid' if valid else 'invalid' if invalid else 'unassessed' if returned else 'missing'))
        assert counts['planned']==counts['valid']+counts['invalid']+counts['unassessed']+counts['missing']
        assert counts['returned']<=counts['attempted']<=counts['planned']
        coverage[arm]=counts
    return dict(per_arm=coverage,details=details,definitions=dict(invalid='Unknown correctness, never wrong by default',
        truncated='Returned length-capped response; overlaps invalid/unassessed',fresh_prefix_control='Unchanged text, independently freshly processed',
        unavailable='Affects only contrasts requiring the unavailable arm'))
