"""Additive same-assistant source-report measurement; no inference on import."""
VERSION = 'study2-source-report-v2'
INTERFACE = 'same-assistant-quoted-source-query-v2'
PARSER = 'first-closed-quoted-field-four-labels-v2'
BUDGET = 16
CUTS = (0, 256, 512)
SUFFIX = (
    '\n\nWhat value is written in the Verified class cell for license plate {plate}?\n'
    'Complete the quoted cell value with A, B, C, or MISSING.\n'
    'SOURCE_REPORT: "'
)
CANDIDATES = {'A': [362, 198], 'B': [425, 198], 'C': [356, 198]}
INVENTORY = {'trajectories':112, 'eligible_by_checkpoint':{'0':112,'256':112,'512':108},
             'main':332, 'legacy_entries':664, 'excluded':4, 'calibration_present':8,
             'calibration_missing':4, 'calibration':12, 'maximum_generations':344,
             'maximum_output_tokens':5504}
BOOTSTRAP_SEED = 2026101601
BOOTSTRAP_SAMPLES = 2000

V1_PLAN_HASH = 'a5f38dc97c35a3ace5dfee579627aaa40599a48c482ecf63bc8eb366cbfdfc70'
REVISION_REASON = ('Pilot-informed elicitation/boundary revision after v1 FAILED: all twelve '
    'calibration returns reached 16 tokens without EOS. Prose-level post hoc observations '
    'do not pass v1. V2 changes only the suffix and response-field boundary and may also fail.')
