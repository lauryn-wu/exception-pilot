# Native prefix continuation: feasibility check

Protocol: `verified-facts-prefix-feasibility-v1`. Fixed seed: `2026100941`.
Specified before live collection. This package implements only the feasibility
stage; it contains no edited-reasoning experiment and makes no mechanism claim.

## Research purpose

The project asks why an explanation can lead a model to override an accurate
individual record with a pattern inferred from other examples. GPT-4o showed
this behavior in the earlier studies. The completed answer-order study obtained
24/24 correct answers with answer-only and answer-first output, versus 15/24
with reasoning-first output. Those results do not establish that the generated
explanation caused the errors.

A later intervention would require continuing an unfinished assistant response
without adding another user turn. This check asks whether one compatible model
both exhibits enough of the target behavior and supports sufficiently stable
unchanged continuations to justify designing that intervention.

This does not restart the stopped `exception_missingness` diagnostic, alter its
replay threshold, or reuse its selected cases. Prior packages and run directories
remain frozen.

## Model and compute

- API model: **`deepseek-flash`**, documented as **DeepSeek-V4.1-Flash** on
  2026-10-09 UTC. This is a provider alias, **not an immutable model snapshot**.
- Endpoint: `https://api.deepseek.com/beta/chat/completions` for every request,
  including the base comparisons.
- Set `thinking: {"type": "disabled"}` explicitly. The visible arm still asks
  the model to write an explanation in its ordinary response. Disabling the
  provider's separate thinking mode does not disable all internal computation.
- Temperature 0; `stream: false`; no tools or structured-output constraint.
  Use `max_tokens`, not OpenAI's `max_completion_tokens`.
- The capability request has a 32-token cap. Each base and replay request has
  the same 1,600-token output cap. Timeout: 120 seconds.
- Credential environment variable: `DEEPSEEK_API_KEY`. An OpenAI key will not
  authenticate with DeepSeek. Never put a key in a config or result archive.
- No local model, training, GPU rental, or additional Python dependencies.

Store the requested alias, returned model string, provider fingerprint when
present, timestamps, token usage, and raw bodies. The first successful response
establishes the returned model string; a subsequent change stops collection.
Stable metadata cannot prove the provider kept an alias's underlying weights
unchanged. A fingerprint change alone is recorded, not treated as proof of a
model change. A nonempty separate `reasoning_content` field is an operational
failure in this non-thinking protocol.

Current published peak prices are $0.30 per million uncached input tokens and
$1.20 per million output tokens; off-peak rates are half. For illustration,
100 requests averaging 2,000 input and 1,000 output tokens cost approximately
**$0.18 at peak rates**. This is a token-cost estimate, not a guaranteed bill or
a minimum account deposit. API latency and request count determine runtime;
the laptop only sends requests and saves results.

Official sources, checked 2026-10-09 UTC:

- [Models and pricing](https://api-docs.deepseek.com/quick_start/pricing/)
- [Thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/)
- [Chat prefix completion](https://api-docs.deepseek.com/guides/chat_prefix_completion/)
- [Model alias changes](https://api-docs.deepseek.com/updates/)

## Fixed schedule: at most 73 returned responses

1. **One prefix-contract check.** This is an execution check, not a research
   observation. The user message is exactly:

   ```text
   Output exactly this text, without quotation marks or commentary:
   Cobalt Maple Lantern
   ```

   The final assistant message is `{"role": "assistant", "content": "Cobalt Ma",
   "prefix": true}`. The expected raw returned suffix is exactly `ple Lantern`.
   A different output, including an echoed whole response, fails this check.
   No per-response heuristic strips apparent echoes. Failure means the required
   prefix/suffix contract was not confirmed by this test, not that the provider
   can never support continuation.

2. **48 base requests.** Twelve fresh worlds, two target-record variants, and
   two output instructions. Every world contains ten accurate vehicle records.
   All six permutations of the two recorded labels and the competing pattern
   label occur once for each target climate. Plates begin with `N` and world IDs
   with `prefix-list-`. Both record variants conflict with the background pattern;
   only the target's recorded class changes between variants. Preserve the prior
   introduction, including the `MISSING` definition, and question. Every target
   class is present. The four requests within each world are deterministically
   shuffled and are independent conversations.

3. **24 unchanged continuations, conditional on the base check.** Every visible
   response receives one continuation, including originally correct responses.
   There is no selection of interesting failures. These are dependent replays,
   not 24 additional independent examples.

There are **12 independent worlds**, not 73. Freeze the complete schedule and
prefix extraction rule during preparation. Replay request text necessarily
depends on its saved parent response and is reconstructed and audited from that
response. All 48 base requests return before the behavioral check is evaluated.
The fixed ceiling is **89 attempts**, 16 above the maximum 73 planned responses.
Explicit transport retries count toward this ceiling.

## Exact base output instructions

These reuse the original cue study's direct and visible instructions, not the
later strict-JSON order experiment. This is a cross-model check of the broad
failure, not an exact replication of the JSON property-order intervention.

`direct`:

```text
Output only ANSWER: followed by A, B, or C.
```

`visible`:

```text
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

Score the final `ANSWER: A`, `ANSWER: B`, or `ANSWER: C` line. Direct responses
must contain only that answer after surrounding whitespace is removed. Visible
responses must contain nonempty text before the answer. These output checks do
not judge explanation truth or faithfulness. A returned formatting failure is
retained and stops the run rather than being resampled.

## Prefix extraction and replay

Find the pre-answer text in the saved visible response. Cut at a whitespace
boundary at or before its character midpoint, choosing the nearest such
boundary; if none exists, use the first eligible boundary after the midpoint.
Both the retained prefix and the remaining explanation must contain nonempty
text. Preserve the prefix as an exact substring; do not trim or rewrite it.
If no eligible cut exists, stop and report prefix unavailability.

Record the parent response identity/hash, cut index and fraction, prefix length,
and remaining explanation length. The rule is independent of the answer's
correctness. An early class conclusion might already appear in the prefix;
this feasibility check does not claim otherwise or identify a later intervention
point. The API accepts text rather than raw token IDs, so byte-preserving text
replay does not establish token-level identity with the provider's original run.

For replay, send the exact original user message followed by the retained
assistant prefix with `prefix: true`. Add no new user instruction. Treat returned
content as the generated suffix, concatenate it with the saved prefix, and score
the resulting response. Preserve both pieces and the raw response separately.
Never condition the continuation on the discarded remainder or parent answer.
Compare the new answer with the parent answer; exact suffix agreement is a
secondary descriptive check, not a prerequisite that every word be reproduced.

## Practical decisions fixed before collection

The base check requires all 48 valid, format-compliant responses and:

- at least **20/24** direct answers correct;
- at least **4 more correct direct answers** than visible answers;
- at least **4 visible pattern errors** spanning **3 or more worlds**.

If any condition fails, stop after the capability check and 48 base calls. This
means insufficient target behavior in this model/setup to justify this route;
it does not refute the original GPT-4o results. Do not override the check or try
new seeds/models/prompts within this protocol.

If the base check passes, run all 24 unchanged continuations. Replay feasibility
requires all 24 to be valid and:

- at least **22/24** answers exactly matching their saved parent answers;
- at least **80% of original pattern-error answers** reproduced, rounding the
  required count upward.

The separate error check prevents agreement on correct examples from hiding
instability in the failures of interest. These are practical investment rules,
not statistical significance tests. Passing permits review and design of a
separate intervention study; it does not start that study or establish a cause.
A failure cannot be repaired by replacing responses, relaxing a threshold, or
extending the sample.

## Reporting and execution integrity

Report each arm's accuracy, pattern choices, output compliance, and paired
correctness changes. For direct-minus-visible accuracy, average both variants
within each world before averaging worlds. Report a descriptive 95% interval
from 10,000 whole-world bootstrap resamples, seed `981723`. A degenerate interval
does not establish certainty or equivalence. Record sensitivity is secondary.

Report replay agreement overall and for the original pattern-error subset,
correctness changes, exact-suffix agreement, and each prefix's position. The
pattern-error subset is conditional and does not estimate population prevalence.
Incomplete, simulated, or operationally invalid runs cannot establish feasibility.

Retain all responses, including valid wrong answers. A refusal, truncation,
malformed response, invalid output format, non-thinking-mode violation, or model
identity change stops collection. No retry can replace a returned response.
Only transport errors or unresolved interrupted requests can be retried with
`--resume --retry-errors`, within the 89-attempt cap. An interrupted request may
already have been billed. Analysis audits the frozen plan, request schedule,
parent-derived replay requests, raw response normalization, and stored scoring.

Mock runs use explicit simulated fixtures, no credentials, and no network. The
default all-correct fixture intentionally fails the behavioral check after 49
calls. That tests the software stop and says nothing about the model.

## macOS instructions

In the existing repository, preserve local commits when updating:

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_prefix prepare --config configs/prefix.json --output runs/prefix-001
open runs/prefix-001/preview.md
```

If Git reports a conflict, resolve it before running; do not discard local work.
Set a DeepSeek API key in the same terminal. These commands use macOS's default
zsh; the key is entered privately and is not written in the command itself:

```zsh
read -s "DEEPSEEK_API_KEY?Paste your DeepSeek API key: "
export DEEPSEEK_API_KEY
```

Run the capability check and the first world's four base requests, then resume:

```bash
caffeinate -i python3 -m exception_prefix run --config configs/prefix.json --output runs/prefix-001 --max-calls 5
caffeinate -i python3 -m exception_prefix run --config configs/prefix.json --output runs/prefix-001 --max-calls 73 --resume
open runs/prefix-001/summary.md
zip -r prefix-001.zip runs/prefix-001
```

The first five calls count toward the total. The second invocation completes
only the remaining permitted tasks. The fixed behavioral decision can stop at
49 returned responses; a completed replay check has 73. Do not interpret either
count as a scientific sample size. Returned operational failures can stop sooner.

Only after a retryable transport error, add `--retry-errors` to the resume
command. Preparation and `python3 -m exception_prefix analyze --output
runs/prefix-001` make no API calls.
