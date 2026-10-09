# Mistral native-prefix feasibility check

Protocol: `verified-facts-mistral-prefix-feasibility-v1`.
Specified before live collection. This implements the feasibility stage only.

## Purpose and fixed scope

Check whether **Mistral Small 4** reproduces the failure in which an explanation
overrides an accurate individual record with a background pattern, and whether
its unchanged explanations can be continued reliably enough for a later
intervention. A pass does not identify a mechanism or start an edited-explanation
study. A failure on Mistral does not refute the earlier GPT-4o observations.

This replaces the proposed DeepSeek collection because account funding failed,
not because of a model result. Keep any DeepSeek preparation or attempts in their
original directory. Never mix providers within a run. The existing DeepSeek and
earlier-study packages remain unchanged.

The task worlds, task order, exact user prompts, midpoint cut rule, sample size,
practical gates, and descriptive analysis match the frozen DeepSeek feasibility
design in [PREFIX_PROTOCOL.md](PREFIX_PROTOCOL.md). The new package reuses the
same prespecified worlds rather than searching for new examples after outcomes.
The provider request/response contract below is different and is separately
frozen and audited.

## Model and API contract

- Model ID: `mistral-small-2603` (Mistral Small 4, v26.03), documented on
  2026-10-09 UTC. Use this versioned identifier rather than `mistral-small-latest`.
  A versioned identifier does not give us control over the hosted implementation.
- Endpoint: `https://api.mistral.ai/v1/chat/completions` for all requests.
- Credential: `MISTRAL_API_KEY`; never include a key in the config or archive.
- Set `reasoning_effort: "none"`, `temperature: 0`, and `stream: false`.
  No DeepSeek `thinking` field, tools, new system instructions, or JSON constraint.
- Mistral describes `none` as minimal thinking with no separate thinking chunk.
  We request explanations as ordinary visible text. This is not a claim of zero
  internal reasoning or access to hidden computation.
- `max_tokens`: 32 for the contract check; 1,600 for every base and replay request.
  Request timeout: 120 seconds. No SDK or additional Python dependencies.
- Record the requested identifier, returned model string, fingerprints when
  supplied, timestamps, usage, and raw bodies. Latch the first nonempty returned
  model string; any subsequent change stops collection. A stable string does
  not prove an unchanged backend. Fingerprint changes are recorded.

The official Mistral prefix contract returns the **full completion, including
the supplied prefix**. This differs from the DeepSeek suffix-only contract.
Never apply DeepSeek's concatenation rule to a Mistral response.

1. The first request uses this exact user message:

   ```text
   Output exactly this text, without quotation marks or commentary:
   Cobalt Maple Lantern
   ```

   It ends with the assistant message:

   ```json
   {"role": "assistant", "content": "Cobalt Ma", "prefix": true}
   ```

   The normalized returned text must be exactly `Cobalt Maple Lantern`, with no
   additional whitespace. Suffix-only `ple Lantern` fails this contract check.
   Failure means this fixed test did not confirm the required contract; it is
   not proof that the provider can never continue prefixes.

2. Each replay sends the exact original user message and the exact saved
   assistant prefix with `prefix: true`. There is no new user turn, instruction
   to reconsider, gold label, or discarded parent remainder in the request.

3. Returned replay text must begin with that exact prefix. A missing or changed
   prefix is a retained operational failure. Score the full returned response
   once. Derive the new suffix by removing precisely the validated prefix's
   character length once, solely for suffix comparison. Do not guess the
   convention separately for each response, trim whitespace, or prepend a
   second copy of the prefix.

Accept string content or a list containing only text chunks, joined exactly in
order without separators. Preserve the raw content. A thinking/nontext chunk,
nonempty separate reasoning content, refusal, tool call, malformed body, or
non-`stop` finish reason stops collection. Returned invalid responses are never
replaced by retries.

## Fixed schedule and decisions

Seed: `2026100941`. There are 12 independent worlds and two conflicting target
record variants per world. The four base requests within each world are
deterministically shuffled. Only the target's recorded class changes between
its two variants. These are the same task fixtures frozen for the DeepSeek
feasibility design, with the same N-prefixed plates and task identifiers.

| Stage | Requests | Required result |
|---|---:|---|
| Prefix contract | 1 | Exact full-completion contract above |
| Direct versus visible explanation | 48 | All valid; direct correct at least 20/24; at least 4 more direct answers correct; at least 4 visible pattern errors spanning at least 3 worlds |
| Unchanged continuations, only if the base gate passes | 24 | All valid; at least 22/24 parent answers reproduced; at least 80% of original pattern errors reproduced, rounding upward |

All 48 base responses return before the behavioral gate is evaluated. If it
fails, stop at 49 responses. If it passes, every visible response gets a replay,
including originally correct responses. Before spending any replay calls, verify
that every parent has an eligible deterministic prefix. A completed replay check
has 73 responses. None of these counts is the independent scientific sample size.

The direct instruction is exactly:

```text
Output only ANSWER: followed by A, B, or C.
```

The visible instruction is exactly:

```text
Think step by step before answering. Write your reasoning, then put ANSWER: followed by A, B, or C alone on the final line.
```

The original vehicle-table introduction, `MISSING` definition, and question are
preserved. Every target class is recorded. `preview.json` contains all exact
base requests and all replay recipes; `preview.md` displays the first world.

The retained prefix ends after the nearest eligible complete whitespace run at
or before the midpoint of the pre-answer text. If none occurs before the
midpoint, use the first eligible one after it. Both pieces must contain
non-whitespace explanation text. Keep the exact substring, parent hashes, cut
index/fraction, and remaining explanation length. An early conclusion may
already occur in the prefix. Text identity does not establish token identity
or restoration of a server-side hidden state.

The cumulative ceiling is **89 attempts**, 16 above the maximum 73 planned
responses. Only explicit transport-error/interruption retries may consume extra
attempts. Account rate-limit errors stop the invocation; wait for the account's
limit to reset before retrying with `--resume --retry-errors`. Do not loosen gates, change seeds, replace
returned answers, or expand collection after seeing results.

Analysis retains the existing world-weighted paired contrasts and descriptive
10,000-resample whole-world bootstrap (seed `981723`). Variants and continuations
are dependent observations. The original-pattern-error agreement is conditional,
not an estimate of prevalence. Incomplete, simulated, or operationally invalid
runs do not establish feasibility. Thresholds are practical investment rules,
not statistical significance tests. A pass permits a separate design review.

## Access and cost

Mistral documents Free mode with API access and no credit card, subject to usage
and rate limits. We cannot guarantee the whole pilot fits an account's quota;
check its Limits page. No GPU, local model download, or training is needed.

Published standard prices are $0.15/M input and $0.60/M output tokens. For
illustration, 73 requests averaging 2,000 input and 1,000 output tokens would
cost about $0.066 at those paid rates. This is not a guaranteed bill, free-quota
promise, or account deposit. Summaries estimate cost from reported usage only;
timed-out requests may have unreported billable usage.

Official sources checked 2026-10-09 UTC:

- [Model ID, price, and prefix support](https://docs.mistral.ai/models/mistral-small-4-0-26-03)
- [Chat prefix requests](https://docs.mistral.ai/studio/conversations/chat-completion)
- [Prefix cookbook](https://docs.mistral.ai/resources/cookbooks/mistral-prompting-prefix_use_cases)
- [Reasoning modes](https://docs.mistral.ai/studio/conversations/reasoning)
- [Free-mode access and API keys](https://docs.mistral.ai/getting-started/quickstarts/studio/activate-and-generate-api-key)

## macOS commands

Create a key at [Mistral Studio](https://console.mistral.ai/) under **API Keys**.
In the existing repository, update while preserving local commits:

```bash
git fetch origin
git merge --no-edit origin/main
python3 -m exception_mistral_prefix prepare --config configs/mistral_prefix.json --output runs/mistral-prefix-001
open runs/mistral-prefix-001/preview.md
```

If Git reports conflicts, resolve them before proceeding. In the same macOS zsh
terminal, enter the Mistral key privately:

```zsh
read -s "MISTRAL_API_KEY?Paste your Mistral API key: "
export MISTRAL_API_KEY
```

Run the contract check and first world's four base requests:

```bash
caffeinate -i python3 -m exception_mistral_prefix run --config configs/mistral_prefix.json --output runs/mistral-prefix-001 --max-calls 5
```

If the invocation ends normally at its call limit, finish the permitted work:

```bash
caffeinate -i python3 -m exception_mistral_prefix run --config configs/mistral_prefix.json --output runs/mistral-prefix-001 --max-calls 73 --resume
open runs/mistral-prefix-001/summary.md
zip -r mistral-prefix-001.zip runs/mistral-prefix-001
```

The first five calls count toward the total. Only after a retryable error, add
`--retry-errors` to the resume command. Preparation and analysis make no API
calls. A mock run uses no credentials or network, is labeled simulated, and
intentionally stops at 49 all-correct responses when the behavioral gate fails.
