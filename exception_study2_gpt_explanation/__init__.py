"""Fresh GPT arms on the frozen current-Qwen inputs; no Qwen inference dependency."""
from exception_study2_explanation import INSTRUCTION, SOURCE_ZIP, SOURCE_SHA256, SOURCE_PLAN, SOURCE_CONTRACT
VERSION = 'study2-gpt-explicit-explanation-v1'
MODEL = 'gpt-6-sol'
SCHEDULE_SEED = 20261022
SETTINGS = dict(model=MODEL, reasoning={'effort': 'none'}, temperature=1.0, top_p=0.95,
                max_output_tokens=4096, store=False, stream=False, service_tier='default')
DOCUMENTATION = dict(checked='2026-10-22', snapshot=None, snapshot_note='No dated snapshot listed; returned identifiers are recorded, not required to equal the requested alias.',
    model='https://developers.openai.com/api/docs/models/gpt-6-sol',
    sampling='https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-sol',
    responses='https://developers.openai.com/api/reference/typescript/resources/responses/methods/create',
    caching='https://developers.openai.com/api/docs/guides/prompt-caching',
    support='reasoning.effort=none supports temperature and top_p; API behavior has not been tested here.')
PRICING = dict(as_of='2026-10-22', currency='USD', service_tier='default', region='global',
    input_per_million=2.0, cached_input_per_million=0.20, cache_write_30m_per_million=2.50,
    cache_write_12h_per_million=5.0, output_per_million=10.0, long_context_threshold=272000,
    source=DOCUMENTATION['model'], accounting_source=DOCUMENTATION['caching'],
    assumption='Standard global synchronous API; no Batch/Flex/priority/regional premiums. Missing usage components leave exact cost unknown.')
STOP = 'STOP_AFTER_192_SCIENTIFIC_REQUESTS_NO_AUTOMATIC_EXPANSION'
