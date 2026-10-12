"""Numerical replay checks and behavioral calibration, not new experiments."""
import math


def compare_distributions(reference, replay, tolerances):
    result = {'passed': False, 'tolerances': tolerances}
    if (not isinstance(reference, list) or not isinstance(replay, list) or not reference
            or len(reference) != len(replay) or any(type(x) not in (int, float) or not math.isfinite(x) for x in reference + replay)):
        return dict(result, reason='missing_malformed_or_nonfinite_logits')
    def softmax(xs):
        m = max(xs); e = [math.exp(x-m) for x in xs]; z = sum(e)
        return [x/z for x in e]
    p, q = softmax(reference), softmax(replay)
    logits_close = all(abs(a-b) <= tolerances['logit_atol'] + tolerances['logit_rtol'] * abs(a) for a,b in zip(reference,replay))
    probs_close = all(abs(a-b) <= tolerances['prob_atol'] + tolerances['prob_rtol'] * abs(a) for a,b in zip(p,q))
    tv = .5 * sum(abs(a-b) for a,b in zip(p,q))
    return dict(result, passed=logits_close and probs_close and tv <= tolerances['max_total_variation'],
                logits_allclose=logits_close, probabilities_allclose=probs_close, total_variation=tv,
                max_abs_logit_error=max(abs(a-b) for a,b in zip(reference,replay)),
                max_abs_probability_error=max(abs(a-b) for a,b in zip(p,q)),
                argmax_agrees=max(range(len(p)), key=p.__getitem__) == max(range(len(q)), key=q.__getitem__))


def replay_check(reference, replay, k, tolerances):
    d = compare_distributions(reference.get('next_token_logits', {}).get(str(k)),
                              replay.get('next_token_logits', {}).get('0'), tolerances)
    exact = replay['tokens'] == reference['tokens'][k:] and replay['stopped'] == reference['stopped'] and replay['finish'] == reference['finish']
    return dict(passed=exact and d['passed'], exact_suffix_match=exact, distribution=d)


def calibration_result(plan, collection):
    """Prerequisite on selection only. All cases, including invalids, remain denominators."""
    paired = {}
    for r in collection['rows']:
        paired.setdefault((r['task']['world'], r['task']['variant']), {})[r['task']['arm']] = r
    direct = sum(p['direct']['score']['correct'] is True for p in paired.values())
    relevant = [key for key, p in paired.items() if p['direct']['score']['correct'] is True
                and p['visible']['score']['valid'] and p['visible']['score']['answer'] == p['visible']['task']['pattern']]
    gate = plan['config']['calibration']
    passed = direct >= gate['min_direct_correct'] and len(relevant) >= gate['min_matched_pattern_errors'] and len({w for w,v in relevant}) >= gate['min_error_worlds']
    return dict(passed=passed, phase=plan['phase'], thresholds=gate, planned_pairs=len(paired),
                direct_correct=direct, matched_direct_correct_visible_pattern_errors=len(relevant),
                error_worlds=len({w for w,v in relevant}), relevant_pairs=relevant,
                interpretation='Preregistered behavior-replication prerequisite; not a significance test')
