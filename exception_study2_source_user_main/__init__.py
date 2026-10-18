"""Fixed source recovery readout on 332 saved contexts; no inference on import."""
from exception_study2_source_user_pilot import MESSAGE, PARSER, BUDGET, INTERFACE
VERSION='study2-source-user-main-v1'
NAMESPACE='v5/source-user-main-v1/'
RENDERER='saved-prefix-new-user-adapter-v1'
PILOT_PLAN='9ac5b3b944e51251629620a40c6da83a6e2a9d6529cb4c37088fc82df3b77132'
PILOT_CONTRACT='205656521aa4aa5fe30bfec3f54eb1ac365520c33a4599a7b176238ef7c64c38'
CUTS=(0,256,512)
EXCLUDED=('staged-v5-011/v1/original/visible','staged-v5-026/v0/original/visible',
          'staged-v5-027/v0/original/visible','staged-v5-059/v1/original/visible')
INVENTORY=dict(worlds=56,trajectories=112,checkpoints={'0':112,'256':112,'512':108},
    queries=332,reused_cue_measurements=664,exclusions=4,new_calibration_generations=0,maximum_calls=332,maximum_output_tokens=5312)
INTERPRETATION=('Explicit recovery after a fresh user request while the original source remains available; '
    'correct recovery may involve rereading. Incorrect, MISSING, or invalid responses do not establish '
    'forgetting, internal evidence erasure, or deliberate override. Cached restricted A/B/C preferences '
    'use another elicitation interface; they are not unconstrained generated answers, matched-interface '
    'accuracy controls, or evidence of a causal source-versus-answer gap. Worlds 000–003 informed '
    'interface development. Worlds 004–059 were not used for this elicitation pilot, but their original '
    'trajectories/readouts already existed and were examined. Nonzero-prefix variants have different '
    'generated traces and are not pure one-cell counterfactuals. New outcome-selected subgroups are exploratory.')
ANALYSIS=dict(primary='Correct / all returned source responses at each checkpoint; unavailable operations are coverage, not incorrect responses.',
    categories=['correct','wrong_label','MISSING','incomplete','invalid_format','metadata_malformed'],
    pairs={'0->256':112,'0->512':108,'256->512':108},pairing='Same trajectory, common eligible and returned pairs only.',
    bootstrap_seed=2026101601,bootstrap_samples=2000,bootstrap_unit='world',
    bootstrap_caveat='A degenerate interval reflects no observed variation in this sample, not certainty about population accuracy.',
    comparisons='For each cached cue: joint and conditional source-correct/wrong-preference and source-correct/pattern-preference fractions; exact ties separate.',
    preferences='First-class-token scores and A/B/C mass primary; newline-inclusive sequence scores sensitivity only.',
    natural_answers='Separate unique trajectory-level saved final answers; never counted once per checkpoint.',
    next_stage='STOP_REVIEW_MAIN')
