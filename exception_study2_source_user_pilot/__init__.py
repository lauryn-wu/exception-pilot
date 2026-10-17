"""One development-only, twelve-call source-transcription pilot."""
VERSION = 'study2-source-user-pilot-v1'
INTERFACE = 'append-only-new-user-source-transcription-v1'
PARSER = 'whole-response-exact-label-terminal-eos-v1'
NAMESPACE = 'v5/source-user-pilot-v1/'
BUDGET = 16
# SHA-256 mapping digest of the 75 contained files, excluding run.lock; tar metadata is irrelevant.
PARENT_ARTIFACTS_HASH = '1de950bb54ce7c64243f76cf5a415fdfe6bc4eebc7053d408992fcc714bf65ca'
PARENT_PLAN = '96102449686561c92f3be4581cf97953568c65e48ac0d95e5589ebc88431f1db'
V2_CONTRACT = '163b456eca49796b4d7d6a099f630946044a8a693e8acdc11f808a2f83305675'
V1_CONTRACT = 'ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d'
MESSAGE = (
    'New task: transcribe a table cell.\n\n'
    'In the original table, what is written in the Verified class cell for license plate {plate}?\n\n'
    'Return only that cell’s exact text: A, B, C, or MISSING.\n'
    'If the cell contains MISSING, return MISSING.\n'
    'Do not predict the vehicle’s class or reproduce the whole row.'
)
INVENTORY = dict(present=8,missing=4,queries=12,main_planned=0,maximum_calls=12,maximum_output_tokens=192)
LIMITATION = ('Development controls selected after v1/v2 failures. Message structure, wording and '
    'response format change together; improvement cannot be attributed to the role boundary. '
    'At k=0 with the source available, this measures recovery after a fresh request, not '
    'uninterrupted retention, deliberate override, an endogenous mechanism, long-prefix '
    'behavior, population accuracy, or matched-interface accuracy advantage.')
