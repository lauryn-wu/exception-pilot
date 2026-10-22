# Qwen3.8-27B native-thinking screen — 2026-10-22

All **384/384 final answers were correct**. The earlier pattern-substitution
failure did not reproduce in this configuration.

| Question wording | Background pattern | Thinking off | Thinking on |
| --- | --- | ---: | ---: |
| Original | Support | 48/48 | 48/48 |
| Original | Conflict | 48/48 | 48/48 |
| Lookup | Support | 48/48 | 48/48 |
| Lookup | Conflict | 48/48 | 48/48 |

The paired extra-conflict-penalty estimate is **0 percentage points** under
both question wordings. There were no failed, missing, malformed, or truncated
scientific responses.

## Design and trace audit

The screen crosses 24 fresh worlds, two target-record variants, two background
cue states, two wordings, and native thinking off/on, with one sampled response
per cell. Worlds belong to four prespecified construction families. Tables have
16 rows, with the target last; scientific prompts contain no MISSING clause.
Both modes request a single-letter final answer. This is a controlled-v2
generalization screen, not an exact replication of historical tables or
explicit visible-explanation instructions.

All 192 thinking-on traces were read against their source tables. Every trace
accurately reproduces the target record and explicitly reads its recorded
class: 181 reproduce the complete pipe-delimited row and 11 use bullet lists.
There are **zero false-absence/unknown claims and zero narrated feature-rule
answer justifications**. Copying descriptive features as part of a record was
not counted as rule induction.

Native thinking was active: the on responses generate **67–111 thinking
tokens**, followed by the closing thinking marker and final label. Off responses
use the native empty closed-thinking scaffold and generate the final letter.
Each on/off pair has the same user prompt and seed.

An independent raw-answer comparison also found, in each of the four
wording-by-thinking groups:

- Changing only the recorded target class changes the answer in **48/48 pairs**.
- Changing the background cue while keeping the target fixed changes the answer
  in **0/48 pairs**.

These are paired observations within the 24 worlds, not 48 independent worlds.
The traces describe successful record lookup; they do not establish a causal
account of the model's internal computation.

## Execution and integrity

The main run used pinned Qwen3.8-27B BF16 without quantization on an NVIDIA RTX
PRO 6000 Blackwell Server Edition, with one successful model load and 384 new
generations in one invocation. It took **29.86 minutes overall**; recorded
generation calls total **11.36 minutes**. The remainder includes initialization
and other runner overhead. The separate eight-response technical smoke test
passed. Archiving and auditing did not generate additional model responses.

The audit verified all bundle file sizes and SHA-256 digests, 1,582 sealed JSON
artifact hashes, and request/start/return/dispatch bindings for all 384 main and
eight smoke operations. Final labels were checked against the actual target
table cells, independently of saved correctness flags. The exact scientific
code contract was reproduced against the recorded GitHub revision.

- Protocol: `study2-current-qwen-native-screen-v1`
- Code revision: `feffb681617027d3f8d8d321ec067f766794b5f7`
- Code contract: `701262504d095b23d2d3320fb1ec794647b55b1064c07bb9788eb8a4547b9998`
- Plan hash: `edda713e841caafcd34d86f299d60a07cbde93a1b3d563a27ecfd13b7a4f52f6`
- Model revision: `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`

The log records the startup workaround `VLLM_USE_FLASHINFER_SAMPLER=0`; that
environment override is not included in frozen backend metadata. Model weights
and full tokenizer assets are not in this export, so their bytes were not
independently rehashed during this archive audit.

This finite screen does not establish zero population error. In particular,
the bootstrap interval `[0, 0]` reflects resampling uniformly perfect observed
outcomes; it does not establish that the population thinking-mode effect is
exactly zero. Differences from historical experiments include the model,
table construction, sampling, and reasoning/output elicitation, so the result
cannot isolate model training as the reason for the change.

## Archived evidence

- [Original evidence ZIP](screen-evidence-20261022T214422Z.zip), including raw
  requests, responses, execution journals, analysis, and technical-smoke evidence.
- [Original run log](screen-run-20261022T214422Z.log).
- [Machine-readable analysis](analysis.json), copied unchanged from the ZIP.
- [SHA-256 checksums](SHA256SUMS).

The ZIP and log are preserved byte-for-byte as uploaded. This README is a
subsequent audit summary, not an alteration of the frozen run.
