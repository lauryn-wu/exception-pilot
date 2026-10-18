"""Separate, draft native-thinking comparison; no historical protocol changes."""
VERSION = 'study2-native-thinking-draft-v2'
SEED = 2026101801
PILOT_BUDGET = 4096
BUDGET_POLICY = 'pilot-budget-review-v1'
PILOT_WORLDS = 4
DECODING = dict(do_sample=True, temperature=0.6, top_p=0.95, top_k=20, min_p=0.0,
                num_beams=1, num_return_sequences=1, repetition_penalty=1.0,
                use_cache=True, renormalize_logits=False)
FINAL_INSTRUCTION = ('Your final answer must be a single uppercase letter: A, B, or C. '
                     'Do not add any prefix, punctuation, or explanation.')
STOP = 'STOP_REVIEW_NATIVE_THINKING_DRAFT'
