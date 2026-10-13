# Instruction × output-interface diagnostic v1

Question: does the strict JSON interface selectively impair copying a supplied class compared with giving an initial class answer?

This is a **diagnostic using previously examined worlds**, not independent confirmation. The manipulation is the **output-interface package** (formatting instructions plus schema constraints); it does not isolate constrained decoding alone. Equal completion-token caps do not guarantee equal reasoning lengths. Historical responses are background only: all 192 responses must be collected fresh. This experiment neither modifies nor opens any Study 2 validation gate.

## Frozen design and provenance

Experiment ID: `instruction-interface-gpt4o-001`. Protocol: `verified-facts-instruction-interface-v1`.

Exactly 24 worlds × 2 recorded-class variants × 2 preliminary instructions × 2 interfaces = **192 responses, 48 per condition**. Every response is ordered `first_value → reasoning → final_answer`. The target remains row 10. There is no answer-before-reasoning arm, assistant prefill, extra reminder, answer repair, or first-entry A/B/C restriction.

| Preliminary instruction | Interface | Planned responses |
|---|---|---:|
| Copy recorded class | Plain text | 48 |
| Copy recorded class | Strict JSON | 48 |
| Give initial answer | Plain text | 48 |
| Give initial answer | Strict JSON | 48 |

Source: `evidence-role-gpt4o-001-results.zip`, members `runs/evidence-role-gpt4o-001/plan.json` and `preview.json`. These matched the extracted local files byte for byte. The package bundles the original plan unchanged and a frozen extraction of 48 prompt stems in `exception_instruction_interface/data/`. No generator runs when planning this diagnostic. Each stem was extracted from the original preview before the preliminary instruction, and checked against both the copy-record and initial-answer reasoning-first requests. This preserves the introduction, `MISSING` explanation, table, feature-rich target description, and class question verbatim.

- Archive SHA-256: `0d13a3649c9661377b62f7303b52b61eb72dec6335f1fd9526dad089113a6226`
- Original plan file SHA-256: `937df7ea37ceb6206bf472840887a831b82785e93820869d4cbc343ca7a8d45a`
- Original internal plan hash: `798d047a556f3b905fe8b7b8ed9bb12f867dec9ed6fcdb105064d61bf45a87ce`
- Original preview file SHA-256: `f9192f4a1aa4db7f9cd36c76b26751068ce79baae6e9955875a475b599920219`
- Frozen extraction SHA-256: `2633c6520fabbb8706cd7cffede03c82bb50ad47d5a805efdadf6530dfe69bc0`

The extraction also records all 96 matching source request hashes. The diagnostic's JSON requests are byte-equivalent under the original ordered-request serialization to those original requests; their responses are **not** reused.

Preliminary instructions, exactly:

> Copy the target vehicle's Verified class cell exactly into first_value. Treat this entry as the recorded class.

> Give your initial answer to the class question in first_value.

JSON output instruction, exactly as in the original reasoning-first condition:

> Output only a JSON object with the fields "first_value", "reasoning", and "final_answer". Write your reasoning in "reasoning". Set "final_answer" to A, B, or C. Your final answer may match or differ from the preliminary entry.

Text output instruction, exactly:

> Output only plain text with the fields "first_value", "reasoning", and "final_answer", in that order. Begin each field on a new line using "field_name: value". Write your reasoning in "reasoning". Set "final_answer" to A, B, or C. Your final answer may match or differ from the preliminary entry.

JSON uses the original `class_response` strict schema, with ordered properties `first_value`, `reasoning`, `final_answer`; all are required, with no extra properties. `first_value` is an unrestricted string or null, reasoning is a string, and final answer is an A/B/C enum. Text omits `response_format` entirely. These settings match the [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=chat), inspected 2026-10-12, which documents this model snapshot and schema-order generation.

Each independent Chat Completions request uses `gpt-4o-2024-08-06`, temperature 0, `max_completion_tokens: 1000`, `n: 1`, `store: false`, and the original single user message. No API sampling seed is added; temperature 0 is not a guarantee of exact reproducibility. Timeout remains 120 seconds. Model identity must match exactly; a mismatch is a permanent collection stop, not permission to substitute another model.

Before collection, shuffle the 48 world/variant blocks with Python `random.Random(2026101202)`, then shuffle the four conditions in each scheduled block using one independent `Random(2026101203)` stream. Each block is contiguous; conditions interleave throughout the run. `plan.json` freezes all 192 exact requests, schedule, seeds, ordered request hashes, source/code hashes, parsing rules, and analysis rules. `preview.json` and `preview.md` show all 192 requests in schedule order. Request hashing uses UTF-8 JSON without key sorting, so schema property order is protected.

## Frozen scoring

Only the **actual first field** can supply the preliminary entry. Never search later reasoning/final-answer text for a replacement. Raw response, decoded raw value, lexical value span, normalized value, and parsing status are retained.

- Normalize first-entry strings only by removing outer ASCII space, tab, CR, and LF. No case conversion, quote removal, Unicode normalization, fenced-block removal, or content repair. JSON escape sequences are decoded by the JSON parser.
- **JSON:** after leading ASCII whitespace, require `{` and a first key exactly `first_value`. Decode that key's complete value independently of everything after it. A closed string/array/object counts even at truncated EOF or before a malformed suffix. Fully emitted null/boolean literals also count at truncated EOF. Numbers require a JSON whitespace/comma/closing-brace delimiter or normal-stop EOF, since a number may still be incomplete at truncated EOF. Malformed bare literals, incomplete strings/literals, duplicate keys within the first value, and unrepresentable/nonfinite numeric values are unparseable. A later duplicate key invalidates the full contract but does not replace the original first entry.
- **Text:** after leading ASCII whitespace, the first line must start exactly `first_value:`. Its complete value ends at LF (optional preceding CR), or at EOF only for a normal complete response. A first line cut off by token exhaustion is unparseable. The case-sensitive literal `null`, after whitespace trimming, denotes null; quotes are not stripped (thus `"null"` is an ordinary other string). JSON string `"null"` is also an other string, distinct from JSON null.
- First-entry categories: correct recorded class; wrong A/B/C class; `MISSING`; null; other emitted value; absent/unparseable. The primary binary outcome is 1 only for the first category. All other **returned** responses are 0, including instruction or format failures. A complete correct first field remains 1 even if reasoning/final output truncates or is malformed.
- Output-contract compliance is separate: normal complete response, exactly the three fields in order, string-or-null first entry, nonempty string reasoning, and exact A/B/C final answer. JSON must parse completely with unique keys. Text allows multiline reasoning; the other fields occupy one line. Reserved field-name headers at the beginning of a line are delimiters; duplicate headers invalidate the contract. Empty string, `MISSING`, or a wrong class can satisfy the output contract while failing the copying instruction.
- Secondary final answers come only from an explicit A/B/C field in a completely parsed unique JSON object, or a unique anchored text final field after reasoning. Text final entries truncated at EOF are unscored unless their line has ended. A malformed JSON suffix can leave the first entry scored but the final unscored. No answer is inferred from prose. Report final accuracy over returned responses (unscored final entries are unsuccessful) and over scored final entries, with both denominators. Count correct-first → wrong-final transitions only when an explicit wrong A/B/C final is scored; show correct-first/unscored-final counts separately.

## Primary analysis and missingness

For each world, average its two recorded-label variants in each of the four conditions. Form:

`(initial-answer accuracy − copy accuracy)JSON − (initial-answer accuracy − copy accuracy)text`

The estimate is the mean of 24 world contrasts. Positive values mean JSON increases copying's disadvantage. For the 95% percentile interval, use **10,000 resamples of 24 whole worlds with replacement**, seed **2026101204**, keeping all eight paired cells within a world together. The implementation samples precomputed world contrasts, which is algebraically identical. Percentiles use linear interpolation at index `(10000 − 1) × p` for p = .025 and .975. Degenerate intervals do not establish equivalence or certainty.

Transport errors and unresolved/pending trials are missing, never incorrect answers. The primary status stays **INCOMPLETE**, with no primary estimate or CI, until **192/192 response records** are returned. Partial condition summaries use returned-response denominators and show missing coverage. Returned malformed, refused, or truncated responses are retained and never retried. Model mismatch blocks scientific interpretation even with full coverage. Mock results are always labeled simulated and never interpretable as research evidence.

Secondary summaries include all six first-entry categories, output compliance, final accuracy, and transitions. `traces.jsonl` includes every planned request and every attempt with full raw responses; `manual_review_template.csv` supplies blank coding fields for manual contradiction review. No keyword hit is treated as contradiction recognition. Save manual edits to a different filename; analysis regenerates the blank template.

## Execution, budget, and commands

The shared atomic journal, process lock, credential lookup, transport, and normalization conventions are reused. There are no SDK dependencies, hidden retries, parallel requests, or automatic follow-up experiments. The fixed plan contains **192 returned responses** and at most **212 cumulative transport attempts** (20 optional retries). Collection stops on the first transport failure; retry requires an explicit resume flag. An unresolved attempt is never automatically retried because it might have reached the service. Output and request integrity are checked before resume; every returned response, including invalid ones, is immutable. Live and mock runs cannot share a directory. Planning, preview, analysis and tests require no API key or network. `run` requires either `--mock` or explicit `--live`.

Run these commands from the diagnostic checkout (Python 3.10+; this machine uses Python 3.12). The plan and full previews have already been prepared offline in the output directory below. Repeating the planning command checks their identity and does not start collection.

```bash
cd /Users/laurynwu/Documents/Codex/exception-pilot-evidence-role

# Offline planning (0 API calls)
python3.12 -m exception_instruction_interface plan \
  --config configs/instruction_interface_gpt4o.json \
  --output runs/instruction-interface-gpt4o-001

# Read every frozen request, including all four conditions
python3.12 -m exception_instruction_interface preview \
  --output runs/instruction-interface-gpt4o-001 | less

# Offline analysis; before collection this reports INCOMPLETE, 0/192
python3.12 -m exception_instruction_interface analyze \
  --output runs/instruction-interface-gpt4o-001

# Offline tests (no model requests)
python3.12 -m unittest tests.test_instruction_interface -v
```

**The live commands below have not been run.** When separately ready to collect, set `OPENAI_API_KEY` in your terminal (do not put it in config, command history, or a committed file). This zsh example reads it invisibly:

```bash
read -s 'OPENAI_API_KEY?OpenAI API key: '
export OPENAI_API_KEY

# Fresh collection: at most 192 attempts this invocation
python3.12 -m exception_instruction_interface run --live \
  --config configs/instruction_interface_gpt4o.json \
  --output runs/instruction-interface-gpt4o-001 --max-calls 192

# Resume after a normal interruption/call limit; skip every returned response
python3.12 -m exception_instruction_interface run --live --resume \
  --config configs/instruction_interface_gpt4o.json \
  --output runs/instruction-interface-gpt4o-001 --max-calls 192

# Only after inspecting a transport error: allow retry of missing responses
python3.12 -m exception_instruction_interface run --live --resume --retry-errors \
  --config configs/instruction_interface_gpt4o.json \
  --output runs/instruction-interface-gpt4o-001 --max-calls 192
```

All invocations together remain capped at 212 attempts, regardless of `--max-calls`. `--resume` cannot automatically resolve an attempt interrupted during the request. Preserve such a run and inspect its journal rather than deleting/reclassifying the attempt. No behavioral calibration or confirmatory claim is added by this software implementation.

## Offline handoff validation (2026-10-12)

All **421 repository tests passed**, including **24 focused diagnostic tests**, with socket connections blocked during the regression run. The prepared plan hash is `1a12f7d1637b82caefb79b488abd1c96a09b0d257af4a8fbaad82fd9c926f5e7`; all 192 ordered request hashes and 48-per-condition counts were verified. The prior evidence-role implementation still matches its archived source hash. At handoff the new run has **0 attempts, no execution record, 0/192 returned responses, and primary status INCOMPLETE**. No paid requests were made. Live model behavior remains untested.
