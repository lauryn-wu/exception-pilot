"""Additive same-assistant source-report measurement; no inference on import."""
VERSION = 'study2-source-report-v1'
INTERFACE = 'same-assistant-literal-source-query-v1'
PARSER = 'eos-whole-response-four-labels-v1'
BUDGET = 16
CUTS = (0, 256, 512)
SUFFIX = '\n\nWhat value is written in the Verified class cell for license plate {plate}? Return exactly one of A, B, C, or MISSING.\nSOURCE_REPORT:'
CANDIDATES = {'A': [362, 198], 'B': [425, 198], 'C': [356, 198]}
INVENTORY = {'trajectories':112, 'eligible_by_checkpoint':{'0':112,'256':112,'512':108},
             'main':332, 'legacy_entries':664, 'excluded':4, 'calibration_present':8,
             'calibration_missing':4, 'calibration':12, 'maximum_generations':344,
             'maximum_output_tokens':5504}
BOOTSTRAP_SEED = 2026101601
BOOTSTRAP_SAMPLES = 2000
