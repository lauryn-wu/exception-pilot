# Continuation map V2: whitespace-scoring amendment

Protocol: `verified-facts-mistral-continuation-map-v2-whitespace`.
This is an explicit amendment to [the V1 map](MISTRAL_MAP_PROTOCOL.md), made
after observing its first six returned responses. It is exploratory, uses the
same previously examined worlds, and is not an independent confirmation.

## Why the first check stopped

V1 attempt 6 (`prefix-list-001/record_2/visible`) returned a complete response
ending in two lines:

```text
ANSWER:
A
```

The parser required `ANSWER: A` on one line, so it recorded
`final_answer_unparseable`. Because the feasibility check required all 48 base
responses to be valid, this stopped collection after six total calls.

The label A is unambiguous. It is incorrect for this case: the table records
NEV268 as B. The response falsely describes that class as MISSING and infers A
from the hot/tropical background pattern. This is one illustrative error,
not a completed behavioral comparison or evidence of a causal mechanism.

The strict V1 result remains `sampling_check_failed_stop`. Its code, journal,
and report are preserved. The earlier temperature-zero replay failure also
remains preserved. Neither result is rewritten as a pass.

## The only scoring change

Retain all strict V1 acceptances. In addition, accept a terminal block consisting
of `ANSWER:`, one or more ASCII whitespace characters (including a newline or
tab), and exactly one uppercase A, B, or C, followed only by ASCII whitespace.
Optional leading spaces/tabs on the ANSWER line are allowed.

- Apply this rule to every existing and future direct, visible, and mapping
  response, for every label and regardless of correctness.
- Direct answers must still contain no preceding explanation. Visible/mapping
  answers must still have preceding reasoning text.
- Do not infer an answer from prose, select among multiple terminal labels,
  remove Markdown wrappers, accept trailing explanations, or repair a label.
- Keep all exact-prefix, capability, provider-completion, returned-model, and
  response-ID checks. The `Cobalt Maple Lantern` probe is still exact.
- Do not change requests, sampling settings, source parents, checkpoints,
  schedule, scientific thresholds, or the cumulative 1,107-attempt cap.

Raw responses are never normalized or rewritten. The parser records the
extracted label separately. Every response retains its `strict_v1_score` and
`answer_whitespace_normalized` flag. Reports contain both strict format counts
and amended results. Strict scoring of later V2 responses is a sensitivity
view; those responses were not collected under the stopped V1 protocol.

## Offline migration, no repeated model calls

V2 audits the complete existing V1 run and its frozen parent snapshot. It then
copies all original plan/execution/journal bytes into `source-map-v1/` in a
**new** output directory. Every attempt is imported in order, including any
transport errors, and counts toward the unchanged cumulative budget.

The new derived journal stores the original response, request, timestamps,
response ID, and migration provenance. It rescores every returned response
using the same amended rule. No favorable subset is selected and no returned
answer is generated again. New requests start at the next unfinished task.

Migration rejects in-place/nested destinations, changed requests, provider or
prefix failures, remaining unscorable responses, sources where mapping already
started, and sources without a whitespace-rejected answer. It cannot restart a
failed accuracy check merely to draw different answers. An existing matching
migration is idempotent; source/imported-journal tampering is rejected.

For the reported six-attempt run, migration makes **zero API calls**, reuses all
six responses, and leaves **43 new screening calls**. The screen is still
incomplete until all 48 base responses have returned and the original accuracy
thresholds are evaluated. Mapping still requires a separate command after a
pass. The full 1,075-response plan includes the imported responses.

## Commands

Update the existing checkout:

```bash
cd ~/Documents/Codex/exception-pilot
git fetch origin
git merge --no-edit origin/main
```

Migrate offline, preserving `runs/mistral-map-001`:

```bash
python3 -m exception_mistral_map_v2 migrate --config configs/mistral_map_v2.json --source runs/mistral-map-001 --output runs/mistral-map-v2-001
```

With `MISTRAL_API_KEY` exported in this Terminal, complete the sampling check:

```bash
caffeinate -i python3 -m exception_mistral_map_v2 run --config configs/mistral_map_v2.json --output runs/mistral-map-v2-001 --max-calls 49 --resume
```

The imported responses are skipped, so a six-response source needs only 43 new
calls. Share the output before mapping. After `sampling_check_passed`, first
check six mapping calls:

```bash
caffeinate -i python3 -m exception_mistral_map_v2 run --config configs/mistral_map_v2.json --output runs/mistral-map-v2-001 --stage map --max-calls 6 --resume
```

If those return normally, the remaining mapping command is:

```bash
caffeinate -i python3 -m exception_mistral_map_v2 run --config configs/mistral_map_v2.json --output runs/mistral-map-v2-001 --stage map --max-calls 1107 --resume
python3 -m exception_mistral_map_v2 analyze --output runs/mistral-map-v2-001
zip -r mistral-map-v2-001.zip runs/mistral-map-v2-001
```

Only transport errors or unresolved requests can be retried with
`--retry-errors`; returned invalid answers stay in the data. If another format
fails, inspect the saved response. Do not edit the journal or rerun until a
desired answer appears. The original statistical and interpretation limits in
the V1 protocol still apply. No paid calls run during migration or analysis.
