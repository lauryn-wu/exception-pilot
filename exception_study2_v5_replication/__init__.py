"""Post-pilot Study 2A replication amendment; no inference on import."""
VERSION = 'study2-v5-replication-only-v1'
ANALYSIS = dict(
    primary='Original question: pre-answer minus initial verified-versus-pattern log odds; average the two matched variants within each independent world, complete worlds only.',
    secondary='Same prespecified analysis for explicit lookup; both frozen cues retained, cue 0 primary and cue 1 sensitivity.',
    checkpoints=['fixed/0','fixed/128','fixed/256','fixed/512','fixed/1024','pre_answer'],
    sampling_unit='independent world',bootstrap='Unchanged v5 clustered(): seed 981723, 10000 resamples, 95% interval.',
    missing='Never zero-impute readouts or treat unavailable answers as incorrect; report coverage, complete-pair denominators and unknowns.',
    descriptive='Checkpoint levels, paired changes from initial, complete-checkpoint cohorts, verified-to-pattern reversals and recovery, cue agreement, and actual answer correctness.',
    selection='All 56 remaining worlds retained regardless of outcome; no stopping, replacement, threshold tuning or event selection.',
    provenance='Amendment decided after examining four pilot worlds. Report those separately, never as untouched validation. No pooled claim required.',
    scope='Fixed/pre-answer Study 2A only; no semantic-event annotations, evidence probes or Study 2B interventions.')
