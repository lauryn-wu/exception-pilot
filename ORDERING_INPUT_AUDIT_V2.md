# Study 1 input-audit reporting v2

Starting head verified against origin: 2536666. This is a REPORTING update,
not a redesign. `exception_ordering/core.py`, the frozen generator/config,
historical EVIDENCE_ORDER_FOLLOWUP_PROTOCOL.md and old output artifacts remain
unchanged. Existing source-bound runs remain reproducible at 2536666; do not
overwrite or bypass their source hashes. New audit directories freeze current
source provenance but retain the same 7,680 requests and schedule.

The primary fixes the target at ROW 5, not necessarily its token position.
All 24 worlds × 2 target values × 20 rotations × 4 arrangements × 2 arms =
**7,680 original responses**, collected sequentially, batch size one. No replays,
likelihood evaluations or edited continuations belong to Study 1. No sample
change is automatic. Smaller or exactly token-matched designs need new frozen
protocols and inputs, not filtering/padding this generator.

## Current audit status: PENDING

No model-matched tokenizer for `mistral-small-2603` was found in the available
project/worktree files or local Hugging Face cache. No tokenizer/model was
downloaded, and no character tokenizer was substituted. Input-only preparation
reports 960 planned before/after blocks over 24 worlds, all UNMEASURED.
Zero measured matches is NOT evidence that zero blocks would match. Whether
the existing secondary subset has useful world coverage remains unresolved.
Real behavioral results and provider serialization remain unverified.

## Exact next commands

From this branch's repository root, using new directories:
Use Python 3.10+; the audit host's tested executable is
`/opt/homebrew/bin/python3.12`. Substitute it for `python3` if the checkout's
shell selects the unsupported system Python 3.8.

```sh
python3 -m unittest discover -s tests -p 'test_ordering_followup.py' -v
python3 -m unittest discover -s tests -v
python3 -m exception_ordering audit-inputs --output runs/ordering-input-audit-v2-pending
```

Once an ALREADY AVAILABLE matching tokenizer.json is supplied, replace the
explicit path below with its real absolute path. This command makes no API call
and cannot accept generation flags. It uses the existing `tokenizers` dependency.

```sh
python3 -m exception_ordering audit-inputs --output runs/ordering-input-audit-v2-tokenized --tokenizer-json /absolute/path/to/mistral-small-2603/tokenizer.json --tokenizer-model mistral-small-2603
python3 -m exception_ordering analyze --output runs/ordering-input-audit-v2-tokenized
```

Inspect `position-audit.json`. It retains EVERY block and reports:

* Target plate/class/row and query-plate token spans, complete user-message
  length, and plate-start/class-start/row-end to query-start token distances.
* Signed after-minus-before changes for those quantities in each answering arm.
* Existing exact plate AND class token-start matching, independently of length
  and distance matching; matching starts does not assert all other quantities match.
* Matched, unmatched and unmeasured blocks with denominators; matched blocks
  per world/variant/rotation; worlds with any match, common matched rotations
  for both variants, and all blocks matched. No unmatched block is removed.

The full planned sample stays primary. The legacy summary field
`token_matched_primary` remains the SECONDARY diagnostic of the primary contrast,
not a replacement primary analysis. Coverage reporting sets no new sufficiency
threshold and does not use outcomes to select blocks. Even with broad input
coverage, mechanisms involving background distances/recency remain unresolved.

Token positions are zero-based; span ends are exclusive. Distances above are
start-to-start except the explicitly named row-end distance. The tokenizer
SHA-256 and model attestation are retained. Status `INPUT_ONLY_USER_ATTESTED`
audits the entire user message, not the provider's chat wrapper, normalization
or hidden serialization. It must never be described as verified provider tokens.
Synthetic tokenizers in unit tests establish software behavior only.

No paid call, GPU launch, model download or inference is part of this patch.

## Verification completed

Focused tests: **11/11 passed**. Full offline suite: **380/380 passed**, using
`/opt/homebrew/bin/python3.12` (3.12.13). The initial unsupported system Python
3.8 run hit nine pre-existing `str.removeprefix` errors in the cue study; using
the required modern interpreter resolved them without unrelated code edits.
The input-only audit completed and reported 7,680 tasks, 960 unmeasured blocks,
24 planned worlds and PENDING tokenizer status. No model-token positions were
invented. Git checks confirm the generator and historical protocol unchanged.
Cross-folder SHA-256 verification found 11,109 existing artifact files unchanged.
