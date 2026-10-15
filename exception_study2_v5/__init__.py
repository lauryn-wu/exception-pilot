"""Scientifically separate v5. Imports never load models or contact services."""
PROTOCOL = 'study2-evidence-interventions-v5'
TECHNICAL = 'same-input-fresh-prefill-v5'
ESTIMAND = ('Conditional answer preferences and responses under controlled textual prefixes; '
            'not latent beliefs, state restoration, or proof the original statement caused an error.')
BUDGET = 2048
ARMS = ('unchanged', 'meaning_control', 'value_blind', 'explicit_value')
EVENTS = ('acknowledgment', 'erasure', 'conflict', 'override')
