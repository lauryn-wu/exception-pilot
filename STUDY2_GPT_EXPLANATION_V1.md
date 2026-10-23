# GPT matched explanation experiment, v1

This follow-up uses 96 existing inputs and collects two fresh GPT responses to each. No Qwen response serves as a GPT control. It is separate from the Qwen screen, the Qwen explanation follow-up, and historical Study 2 protocols.

The source is `results/current-qwen-screen-v1/screen-evidence-20261022T214422Z.zip`, SHA256 `bb0e059f8a44a69b33990998b672e245405c4ca67c2d7d9214113283a6c9d31a`. The reader verifies the archive inventory, member hashes, sealed records, saved prompt/table bindings, recorded labels, input-ID identity and completed operation/dispatch bindings. It checks the saved smoke-evidence bindings. It does not re-render or decode Qwen tokens, load a tokenizer, follow archived absolute paths, or claim a new real-model validation.

The 24 worlds have two recorded-label variants and two cue states. Only original wording is used. The 96 source OFF entries identify the inputs; their output text is not used in analysis. The direct arm sends the original prompt unchanged. The explanation arm replaces only the terminal answer-only instruction with:

> Think step by step before answering. Write your reasoning, then put a single uppercase letter—A, B, or C—alone on the final line.

Every preceding UTF-8 byte is preserved. Each arm has 48 support and 48 conflict cases. There are exactly 192 requests, no repetitions, calibration calls, judges, new worlds or live smoke calls. A small first invocation is a subset of this same plan.

## API contract

The Responses API request uses `gpt-6-sol`, `reasoning.effort="none"`, `temperature=1.0`, `top_p=0.95`, `max_output_tokens=4096`, `store=false`, `stream=false` and standard `service_tier="default"`. Input is one user message. No tools, schema, developer rubric, answer-key metadata, conversation history, Qwen template/token IDs, top-k, min-p, engine flags or model-generation seed are sent.

The [model documentation](https://developers.openai.com/api/docs/models/gpt-6-sol) and [parameter guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-sol), inspected 22 October 2026, support these settings. No dated snapshot was listed. The requested identifier is frozen; returned model identifiers may differ and are preserved with timestamps. This is not snapshot-level reproducibility. API acceptance and actual returned behavior remain untested. The setting `none` does not establish that the model performs no internal reasoning.

Pairs are hash-sorted with scheduling seed 20261022. The two arms are adjacent, and first arm alternates by sorted world index. There are 48 direct-first and 48 explanation-first pairs, balanced within relation and construction block. The seed is local scheduling metadata, not an API generation seed.

## Returned evidence and scoring

The complete raw response body and HTTP request ID are saved before classifying a server failure. Response ID, requested/returned model, client and server timestamps, status, incomplete details, usage and reasoning-token counts remain available. Message order, content-part boundaries, output indices and optional phases are preserved. Reasoning items are retained as raw evidence but never used as visible explanation. A defensive secret redaction is recorded if an API response unexpectedly echoes a credential.

An explicit final-answer phase identifies the final message; without phases, one assistant message is accepted. Multiple unphased messages, multiple final messages or commentary after the final message are malformed, not silently flattened into a guessed final answer. Display text uses a newline between messages; each original message and content part remains available separately.

For answer-only responses, the entire visible assistant text, trimmed at its outer boundaries, must be exactly `A`, `B` or `C`. For explanations, the last nonempty line of the final answer must be exactly one of those letters. Line terminators are removed; punctuation, Markdown and extra spaces on that line are not repaired. Earlier labels are never substituted. Refusals and incomplete returns are retained. A response cut off by `max_output_tokens` is truncated and unsuccessful even if its partial text ends in a label.

Correctness and explanation-format compliance are separate. A correct label alone fails to explain. Nonempty preceding visible text (including a preceding commentary message) meets the format observation, including a brief record-retrieval explanation; this does not automatically certify semantic compliance. Raw text is exported for manual review with semantic annotation fields set to `not_reviewed`.

## Execution and resume

Prepare, inspect, analyze, export and run without `--live-openai` are offline. The existing single-attempt HTTP transport is reused, with a 180-second timeout and no SDK retries. The frozen request identity binds the source case/reference, exact prompt, arm, model, all API settings, source binding and protocol. Code and reused helper hashes are also frozen in the plan.

The existing lock and immutable request/start/terminal journal protect dispatch. Normal resume executes never-started requests only. Failed or ambiguous requests remain held; they are not resampled, promoted or retried. A completed resume requires neither credentials nor a transport call. Per-invocation `--max-new` is 1–192 and cannot expand the scientific population. Returned wrong, verbose, malformed, refused or truncated responses remain cached; they do not stop later planned calls. HTTP errors, transport exceptions, server failures and detected echoed-setting mismatches stop the invocation after that failure. Subsequent calls remain never-started. Explicit `recover` only quarantines recognized atomic-write debris; it cannot authorize a resend.

## Accounting and analysis

Report completed, cached in the invocation, pending, failed and ambiguous counts separately. Fixed-budget returned invalid outcomes are unsuccessful; infrastructure-unavailable outcomes are not assigned a wrong label. Missing infrastructure outcomes prevent completion and leave affected arm accuracies and the primary contrast undefined. Bounds and unscorable pairs remain visible.

The primary contrast is `(explanation support − explanation conflict) − (answer-only support − answer-only conflict)`. The existing paired estimators resample four construction blocks, retaining their six worlds and both variants. The 24-world bootstrap is a sensitivity analysis. Neither 96 matched inputs nor 192 responses are independent worlds. A zero-width all-perfect bootstrap interval does not imply population certainty. Per-arm category counts, paired changes, conflict pattern-label versus other wrong-label errors and explanation compliance are also reported. Record sensitivity varies label variant at fixed world/cue; cue sensitivity varies cue state at fixed world/variant. Invalid, truncated or unavailable pairs remain unscorable with fixed-budget denominators reported.

Dated Standard/global USD assumptions (22 October 2026) are $2/M ordinary input, $0.20/M cached input, $2.50/M 30-minute cache writes, $5/M 12-hour cache writes, and $10/M output. Above 272,000 input tokens, input/cache prices double and output is 1.5×. These follow the [model pricing](https://developers.openai.com/api/docs/models/gpt-6-sol) and [cache accounting documentation](https://developers.openai.com/api/docs/guides/prompt-caching). Ordinary input subtracts cache reads and writes. Reasoning tokens already belong to output usage and are not added again. Unknown usage components or unpriced service tiers leave total cost unknown; observed priced subtotals are labeled. Failed or ambiguous calls may still be billable. The 786,432-token aggregate output cap corresponds to $7.86432 at short-context output prices, plus input/cache charges; it is not a dollar-spending cap. Input token counts are not guessed from Qwen tokens.

Inputs and analysis were chosen after observing the Qwen screen. The experiment does not isolate written output from the instruction's effect on interpretation. It makes no automatic novelty, mechanism or project-success claim.

Stop after this fixed plan. No automatic expansion or further Study 2 experiments.
