# Study 2 source-user pilot v1 — frozen development protocol

Identity: `study2-source-user-pilot-v1`. Namespace: `v5/source-user-pilot-v1/`.
Exactly 12 executable k=0 controls, eight recorded-class controls and four literal-MISSING controls,
in parent order, worlds staged-v5-000 through staged-v5-003. No main worklist or main-enabling option.
Maximum 12 new generations and 192 output tokens; no new originals, readouts, judges, interventions,
scoring calls, or technical inference. STOP_AFTER_PILOT on complete collection regardless of result.

## Provenance and interpretation

V1 failed its frozen criterion: all 12 returns were invalid. V2 failed: eight present controls
returned the correct recorded class; four MISSING controls began copying their target row and
reached 16 tokens before closing the quoted field. All 12 returned; no runtime failures,
ambiguous operations, or main operation (including request-only) occurred.

The new interface was chosen after these observations. These four worlds are development data.
The original instruction to predict a class when MISSING and the unfinished same-assistant v2
query are a possible explanation, not an established cause. Structure, wording and response
format change together, so improvement cannot be attributed to the role boundary. Source remains
available: success establishes recovery after a fresh request, not uninterrupted retention,
deliberate override, an endogenous mechanism, long-prefix behavior, population accuracy, or
matched-interface accuracy advantage. A pass authorizes no larger experiment.

Parent plan: `96102449686561c92f3be4581cf97953568c65e48ac0d95e5589ebc88431f1db`.
Parent v2 contract: `163b456eca49796b4d7d6a099f630946044a8a693e8acdc11f808a2f83305675`.
V1 contract: `ab94401c0e43ef435f52ff991a928a4fd95358e943c238ee1b0b0bfe2d47717d`.
Supplied archive SHA-256: `ee1ffa85ca03f44562226637a671e388c753ee61bbae75c057858e0369622d59`.
The container digest documents that download; repackaging does not change sealed-artifact identity.
The contained-file SHA-256 mapping digest (75 files, excluding run.lock) is
`1de950bb54ce7c64243f76cf5a415fdfe6bc4eebc7053d408992fcc714bf65ca`; it pins the actual
raw replies and original verdict independently of tar metadata or container packaging.
Parent plan, journal, LIVE_LOCAL provenance, original FAILED report, scores, source rows, and
recorded single-cell edits must authenticate before child preparation/execution.

## One frozen request

Substitute only `{plate}`. Preserve line breaks and no trailing newline:

```text
New task: transcribe a table cell.

In the original table, what is written in the Verified class cell for license plate {plate}?

Return only that cell’s exact text: A, B, C, or MISSING.
If the cell contains MISSING, return MISSING.
Do not predict the vehicle’s class or reproduce the whole row.
```

## Append-only rendering

Use the unchanged pinned tokenizer wrapper. Reconstruct the original user text from each saved
source row, including the parent's literal-MISSING cell edit. The original renderer must reproduce
parent input_ids exactly. Both variants must collapse to the same edited MISSING prompt.
Start with parent input_ids + empty prefix_ids, excluding the parent source-query suffix.
Retain the original assistant header and empty thinking scaffold.

Derive the appended text strictly after one unique harmless assistant sentinel in a pinned-template
render of [original user, assistant sentinel, new user request], thinking disabled and generation
prompt enabled. Never send the sentinel. Require exact decode/encode round trips, tokenized-template
suffix equality, control-token identities from the tokenizer, and agreement with a separate render
of only the new user. Expected appended structure (escapes denote actual newlines):

```text
<|im_end|>\n<|im_start|>user\n{request}<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n
```

Ordinary request text contains no structural control tokens. The old empty assistant is explicitly
closed; there is no intermediate answer or generated continuation. Append bridge IDs to saved IDs;
do not re-tokenize the combined context or rebuild the historical conversation. Qwen's full
canonical rerender strips historical thinking scaffolds; equality to that rerender is not claimed.
Seal both contexts, bridge text/IDs/hash, source/query IDs/hashes, role offsets, tokenizer/template,
settings, and readable contexts. Missing actual tokenizer assets block preparation and all live work.
Synthetic rendering tests do not satisfy that integration requirement.

## Generation and scoring

Original pinned Qwen/Qwen3-32B model/tokenizer revision
`9216db5781bf21249d130ec9da846c4624c16137`; unchanged full backend identity, BF16, no quantization,
eager attention, batch one, greedy, enable_thinking=False, fresh prefill, capture_at=(), 16 tokens.
No forced prefix, quote, source marker, constraints, special stop, new system message, retry,
additional prompt, or alternative budget. Parent generations cannot substitute for child results.

Validate nonnegative integer token IDs, <=16 budget, exact decoded text, permitted terminal EOS,
no unexpected special tokens/captured logits, consistent finish/stopped metadata. A non-EOS length
stop must contain exactly 16 tokens. Require terminal EOS for completion. Strip only outer whitespace;
the entire answer must equal A, B, C, or MISSING. Quotes, punctuation, lowercase, prose, copied rows,
and extracted labels fail. Length stops are incomplete even if stripped text is a label.
Report raw integrity, completion, format validity, and correctness separately. Criterion: 12/12
complete, valid, correct returns. Unavailable outcomes prevent a pass; wrong/invalid returns are
unsuccessful among all returned cases, not excluded from accuracy.

## Durability, reporting, and stopping

Own frozen plan, request identity, runner/session, reports and cache; unchanged generic immutable
journaling and backend helpers are reused. The child contract includes all child code/protocol and
unchanged v2/transitive dependencies. Never invoke a parent runner/session as execution shortcut.
Validate plan/source/backend/cache before weight loading. One necessary live invocation loads once;
completed or blocked invocations load zero times. Default run, prepare, inspect and archive are offline.

Only never-started operations dispatch. Request-only entries have not dispatched; started entries
are ambiguous and never resent. Returned wrong/malformed/truncated answers remain terminal and do
not stop ordinary collection. First backend exception stops the invocation, seals failure, and leaves
later operations untouched. Explicit resume skips failed/ambiguous/returned entries. Raw returns
are durable before parsing/reporting; recover reports without inference. Keep MOCK/LIVE caches apart,
exclusive output locking, and separation from parent/source/model directories. Never edit a frozen
plan or create a new output to resample.

Reports retain all 12 raw replies and scores, separate eight/four denominators, four variant pairs,
coverage/operation states, actual new/reused child calls, prior evidence, load/timing provenance,
FAILED parent verdict, no main eligibility, and unresolved IDs. No bootstrap/main analysis.
Archive child plan/contexts/journals/reports/timing and one byte-identical parent-evidence package
(with its original full sealed plan/report and 12 replies), plus eight source rows and tokenizer
identity. Do not copy historical experiment trees or weights; never overwrite an archive.
