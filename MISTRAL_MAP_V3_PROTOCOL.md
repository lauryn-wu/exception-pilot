# Continuation map V3: answer presentation and complete-screen collection

Protocol: `verified-facts-mistral-continuation-map-v3-presentation`.

This explicitly amends the [V2 whitespace parser](MISTRAL_MAP_V2_PROTOCOL.md)
after nine total returned responses. V2 attempt 9 ended with `**ANSWER: A**`.
It was a complete, unambiguous answer, rejected solely for its bold formatting.
The table recorded C; A was the competing background pattern. The explanation
listed the target among class C vehicles before ultimately choosing A.
This example does not establish an internal mechanism.

## Fixed parsing rule

Apply one correctness-blind grammar to every saved and future direct, visible,
and mapping response, including answers accepted by previous parsers:

- A terminal standalone answer block has an ASCII case-insensitive `ANSWER`
  marker, a colon, optional ASCII whitespace, and exactly one uppercase A/B/C.
- Balanced `*`, `**`, `_`, `__`, and backtick wrappers may surround the whole
  block, marker (with or without its colon), or label, with at most three levels
  of wrapper nesting. A single terminal period is permitted.
- ASCII whitespace may separate grammar tokens, including before the colon
  and around wrapper contents; the word `ANSWER` must remain contiguous.
- A complete terminal fence using matching triple backticks or tildes may
  contain only that answer block; its language is absent, `text`, or `plaintext`.
- The complete block includes its opening wrapper/fence. Markup cannot count
  as preceding reasoning. Direct responses remain answer-only; visible and
  mapping responses still require preceding non-whitespace reasoning text.
- Do not guess from prose, strip punctuation globally, repair a label, or choose
  among alternatives. Extra trailing prose, lowercase labels, unmatched
  wrappers/fences, and adjacent duplicate/conflicting standalone answer blocks
  remain unscorable. Earlier answer mentions within genuine prose are allowed.

This is a fixed, bounded grammar, not a general Markdown renderer. It inspects
at most the last 30 nonblank line starts and 28 syntax tokens; blank whitespace
does not consume those limits. A standalone emphasis-only line immediately
before the answer is conservatively treated as a dangling wrapper, even if it
could render as a Markdown separator. Such outputs are retained as unscorable.

The parser extracts a label and the raw block boundary. It never rewrites the
model response or retained assistant prefix. Exact capability, prefix,
provider-completion, model, and response-ID checks remain unchanged.

Tests cover the same grammar across A, B, and C and correct/incorrect labels;
the scorer does not consult the gold or pattern label to parse an answer.
V1 and V2 scoring views are saved alongside the amended score. The grammar
also checks previously accepted answers for ambiguous adjacent final blocks.

## Collection policy

Collect all 48 planned base responses even if an answer is unscorable. Keep each
returned response exactly once, never retry it, and report unscorable and
pending counts throughout. Before all base responses return, the sampling gate
is `incomplete`, including when some are unscorable.

After all 48 return:

- If any remain unscorable, stop as `sampling_check_unscorable` with
  `analysis_status: sampling_check_unscorable_stop`. Export their task IDs and
  raw answers for review. This is not a negative behavioral result. Mapping is
  blocked; no answer is replaced.
- Otherwise apply the unchanged practical thresholds: direct correct >=20/24,
  direct minus visible correct >=4, visible pattern errors >=4, and errors in
  at least three worlds. A failure is `sampling_check_failed`; a pass is
  `sampling_check_passed`.

Mapping still requires a separate `--stage map` invocation after a pass.
Operational failures (prefix/provider/model/ID failures, including incomplete
generation) still stop immediately. Transport errors stop and require explicit
retry; they do not replace a returned answer.

This changes when the screen evaluates formatting, not its scientific
thresholds. Unscorable answers are not silently treated as observed errors or
dropped from complete-data accuracy. Reports retain valid-only rates and
full-plan bounds. The unchanged 1,107-attempt cap includes imported attempts.

## Preserve all nine existing responses

Offline migration audits the V2 run and copies all its journals, plus its
nested V1 and original parent snapshots, byte-for-byte into `source-map-v2/`
inside a new output directory. The original V1 and V2 runs are untouched and
remain failed under their original rules. Every existing attempt is imported
in order and rescored uniformly, including any that remain unscorable.
Migration makes zero API calls; no task is redrawn or selected for its answer.

Requests, model (`mistral-small-2603`), temperature (0.6), top_p (0.95), token
limits, source explanations, checkpoint cuts, random schedule, and sample size
are unchanged. The nine saved responses leave **40 new check calls**. They
count as the same observations, not nine new independent samples.

This amendment was designed after examining formatting failures at calls six
and nine. Report it as a retrospective exploratory amendment. Prior strict
scores on later V3 responses are sensitivity analyses, not executed V1/V2 runs.
The original replay failure and all limitations in the
[map design](MISTRAL_MAP_PROTOCOL.md) remain applicable.

## Run commands

Update your checkout:

```bash
cd ~/Documents/Codex/exception-pilot
git fetch origin
git merge --no-edit origin/main
```

Migrate all saved responses offline:

```bash
python3 -m exception_mistral_map_v3 migrate --config configs/mistral_map_v3.json --source runs/mistral-map-v2-001 --output runs/mistral-map-v3-001
```

With the same `MISTRAL_API_KEY` exported, complete the check:

```bash
caffeinate -i python3 -m exception_mistral_map_v3 run --config configs/mistral_map_v3.json --output runs/mistral-map-v3-001 --max-calls 49 --resume
```

Only 40 new requests are needed for the reported nine-response source. Share
the final output before mapping. A future formatting violation is retained
while the rest of the check finishes; it does not trigger another early stop.

After `sampling_check_passed`, test six mapping calls:

```bash
caffeinate -i python3 -m exception_mistral_map_v3 run --config configs/mistral_map_v3.json --output runs/mistral-map-v3-001 --stage map --max-calls 6 --resume
```

If these return normally, complete and export the mapping stage:

```bash
caffeinate -i python3 -m exception_mistral_map_v3 run --config configs/mistral_map_v3.json --output runs/mistral-map-v3-001 --stage map --max-calls 1107 --resume
python3 -m exception_mistral_map_v3 analyze --output runs/mistral-map-v3-001
zip -r mistral-map-v3-001.zip runs/mistral-map-v3-001
```

After transport errors or interruptions, resume the same directory and stage.
Add `--retry-errors` only for a transport error or unresolved request. Never
delete or edit saved attempts. Migration and analysis make no model calls.
