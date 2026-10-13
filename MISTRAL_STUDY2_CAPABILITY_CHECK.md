# Mistral API capability check for Studies 2A and 2B

Status: **CLOSED for the current Study 2 protocol (2026-10-12). No further Mistral
test calls or API-backend development.** Preserve the capability script and all
files in `capability-checks/mistral-small-2603-20261012-204146/` as historical evidence.
The saved run returned "Logprobs are not enabled for this model" and "Prompt
Logprobs are not enabled for this model"; both character-prefix replays failed.
The request audit found no correctable request issue. The protocol's full-logit
and exact-token validation gates remain closed for this API route.

The sections below retain the diagnostic's original design and budget. They do
not authorize another live check. Qwen preparation uses the existing local backend;
Mistral or GPT-4o responses cannot become Qwen trajectories.

## Official documentation inspected on 2026-10-12

- [Mistral Small 4](https://docs.mistral.ai/models/mistral-small-4-0-26-03)
  lists `mistral-small-2603` and prefix support.
- [Chat guide](https://docs.mistral.ai/studio/conversations/chat-completion)
  documents a final assistant message with `prefix: true`.
- [Reasoning guide](https://docs.mistral.ai/studio/conversations/reasoning)
  describes `reasoning_effort: "none"` as suppressing the separate thinking chunk;
  it does not assert that the model performs no internal reasoning.
- [Chat API](https://docs.mistral.ai/api/endpoint/chat) and
  [OpenAPI schema](https://docs.mistral.ai/openapi.yaml) expose `logprobs`,
  `top_logprobs`, `prompt_logprobs`, and `top_prompt_logprobs`. Each choice can
  contain output/prompt token rows with `token`, `token_id`, `bytes`, `logprob`
  and optional `top_logprobs`.

The inspected schema SHA-256 is
`6c349f3bdef67bbbe43b49973f15825c92e7fcc1ff4fadbcc2d87564ef277a03`.
These are documented interfaces, **not verified support on this exact model**.
The schema does not establish whether returned probabilities precede decoding
transforms, nor expose full-vocabulary raw logits. No additional API endpoint
or tokenizer is assumed. The script does not fetch documentation at runtime.

## Commands and fixed budget

Requires Python >=3.10 and only its standard library. From this Study 2 checkout:

```sh
python3 mistral_study2_capability.py
```

The default prints a plan, makes **zero network calls**, does not read API
credentials and does not create output files, even if `--output` is supplied.

Historical live syntax is retained for audit only. **Do not run this command for
the current Study 2 protocol.** The already completed run is preserved above.

```sh
python3 mistral_study2_capability.py --live \
  --output capability-checks/mistral-small-2603-001
```

The directory must not already exist. There is no resume, retry, redirect,
model fallback, GPU launch, model download, SDK dependency or configurable
request-budget override. The endpoint and model are fixed. Each attempted HTTP
request counts, including errors/timeouts. Requests run sequentially.

| Slots | Purpose | Maximum output tokens per request |
|---|---|---:|
| 1 | Uninterrupted plain technical generation | 192 |
| 2–3 | Unchanged prefixes of 32 and 64 Unicode characters | 192 each |
| 4 | Uninterrupted generation requesting output logprobs | 192 |
| 5–6 | Unchanged observed-token prefixes at 32 and 64, requesting output and prompt logprobs | 160, 128 |
| 7 | Output `logprobs` plus `top_logprobs=5` at checkpoint + cue | 1 |
| 8 | `prompt_logprobs` at checkpoint + cue | 1 |
| 9 | Same context, with `top_prompt_logprobs=5` | 1 |
| 10–12 | `prompt_logprobs` for the three complete candidates | 1 each |

**Maximum: 12 HTTP requests, 1,062 requested output tokens in total.** Input
tokens are additional and server-tokenized, so their exact count is recorded
from returned usage rather than asserted offline. Short originals, unavailable
telemetry or non-UTF-8 token boundaries skip dependent slots; unused slots are
never reassigned. Authentication, rate-limit, redirect, server or transport
errors halt further requests. Other rejected requests are saved and independent
slots continue. Top-k fields are tested separately from basic probability
fields, so rejecting one does not imply rejection of the other.

## What the check measures

Every request keeps the same original user prompt: the first bookshelf
technical prompt used by the local continuation check. It is not a study
selection/confirmation case. Continuations append exactly one assistant prefix,
never a new user turn. Settings are fixed: model `mistral-small-2603`, temperature
0, top-p 1, seed 20261012, n=1, non-streaming, `reasoning_effort="none"`, and
`safe_prompt=false`. No tools, logit bias, prediction or reasoning prompt mode
are requested. Returned thinking/tool content or a different model identifier
makes a response unusable for comparisons; raw evidence is still retained.

The two plain replays assess text behavior even if probability fields are
unsupported. Their character cuts are **not** the protocol's token checkpoints.
The token replays use bytes and IDs observed during the instrumented original,
provided those bytes reconstruct its exact text. Partial UTF-8 boundaries and
unexplained special-token bytes are not repaired or stripped. The script saves
each unchanged prefix before sending it. It reports both possible wire formats
(returned full text or suffix) and finish equality; length-limited fragments do
not count as completed behavioral replays. Plain/instrumented original text
agreement is also recorded.

Scoring uses one saved 32-token prefix (or a labelled 32-character fallback),
followed by the local primary cue `\nANSWER:`. Slot 8 supplies the baseline
serialized checkpoint context. Slots 10–12 append exactly the literal complete
strings ` A\n`, ` B\n`, ` C\n` to that same assistant prefix. Their one generated
token is irrelevant: only prompt token likelihoods are assessed. A score is
reported only if the baseline ends at the intended cue, its entire token-ID
sequence and per-token bytes are unchanged in each candidate request, and the
remaining prompt rows cover precisely the complete candidate including its
leading space and final newline. Scores sum all candidate-token logprobs with
no length normalization. Merged boundaries, added terminators, missing IDs or
bytes, absent/nonfinite/positive logprobs, and missing candidate parts produce
`logprob: null` with reasons. No sampled-answer frequencies, top-k renormalization,
logit-biased answers or zero-filled missing candidates are used.

These are conditional likelihoods of **server-tokenized** candidate sequences
if the fields behave as expected. They do not prove equivalence to the local
backend's separately encoded candidates, or establish undocumented probability
semantics. All three candidates must have usable scores for the aggregate
`complete_candidate_scores_observed` flag.

## Validation limits and separate feasibility decisions

| Check | What can be established if telemetry is returned |
|---|---|
| Text replay | Exact visible text/suffix and finish equality; behavioral evidence only |
| Output token identity | Compare observed suffix IDs and bytes; never infer IDs from text |
| Prefix round trip | Compare returned prompt-tail IDs with original prefix IDs |
| Entire original generation input | Unverified: the output-only reference does not capture its input serialization |
| Candidate context identity | Compare all returned baseline prompt IDs and bytes against each candidate request |
| Candidate probability | Sum verified complete-candidate prompt logprobs; semantics limitations remain |
| Observed token probabilities | Report suffix logprob differences when matching IDs are available |
| Full-distribution validation | Not available: top-k and chosen-token probabilities do not supply raw logits or the full vocabulary |
| Server reproducibility | Response model/ID/usage observable; exact weights, template, tokenizer, precision and deployment unpinned |

**Study 2A: API route stopped.** Probability requests were tested and rejected
as not enabled for this model. The raw-logit, full-vocabulary probability and
total-variation gates also cannot be established with the documented interface.
The diagnostic leaves `protocol_compatible: false`.

**Study 2B: API route stopped.** Both character-prefix replays failed. Exact-token
replay remained unavailable; no edits or behavioral calibration were collected.
Even matching text alone would not establish full-distribution equivalence.

**Full API implementation will not proceed for this protocol.** A future protocol
change would require a separate explicit decision; this diagnostic does not weaken
or bypass any current gate and its files cannot serve as local study outputs.

## Evidence and offline verification

The new directory contains `plan.json`, exact per-slot request payloads, raw
HTTP response bodies (`*.response.bin`, including errors), response metadata
(model, response ID, usage, selected non-secret headers, response-body hashes),
saved prefixes, a frozen `scoring-context.json`, and `report.json`. Authorization
headers and API keys are never intentionally saved. A request file written before
dispatch remains evidence of a possible attempt if execution is interrupted.
Inspect the report's separate study decisions and missing-data reasons; exit
zero means the diagnostic encountered no unusable HTTP responses, **not** that
either study is compatible. Synthetic test reports are not live results.

```sh
python3 -m unittest discover -s tests -p 'test_mistral_study2_capability.py' -v
```

Offline tests cover the network-free default, request ceiling, raw evidence,
unchanged prompts/prefix roles/settings, complete multi-token likelihoods,
missing top-k alternatives, changed token context, truncation, thinking/model
mismatches, ignored/rejected fields, error handling, and preserving protocol blocks.
