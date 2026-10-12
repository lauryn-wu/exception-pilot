# Study 1 follow-up audit — 2026-10-12

Audited existing branch `codex/evidence-order-followup`, starting at `02c7e08`.
The generator, protocol, configurations, analyses, old previews and collected
outputs are unchanged. Added tests verify the existing implementation; no design
change or protocol reinterpretation was needed.

| Requirement | Existing behavior | Audit action / remaining limit |
|---|---|---|
| Fixed target and inventory | Target at row 5; ten complete records and their labels preserved within variant/rotation | Added exact rendered-record, target-row, class-count and query checks for all 960 matched groups / 7,680 tasks |
| Before / after / split × answering style | Four layouts (two split layouts averaged), direct and visible reasoning | Verified all eight cells occur in every matched group; retained original primary interaction |
| Identity and order controls | All 20 joint cyclic rotations; role/climate balancing; reversed base orders across replicates | Existing balance tests retained; this covers cyclic orders, not all permutations |
| Actual token positions and lengths | Complete-user-message tokenizer offsets and lengths, target plate AND class starts, explicit UNMEASURED without tokenizer | Added offset/length/report tests and a class-only shift test; synthetic test tokenizers are not model evidence |
| Residual differences | Full offsets/lengths saved even when starts differ; matched subset secondary only | Added test that missing audits cannot become exact matches; actual model-matched audit remains PENDING |
| Raw and invalid outputs / opt-in | Existing atomic journals, invalid retention, no silent retry, live provenance gate | Existing offline failure/identity/opt-in tests retained |

No model tokenizer is available in this environment. The existing previews remain
UNMEASURED. Equal row numbers do **not** establish equal target-token positions.
Even a user-supplied matching tokenizer audits only the user message; the provider's
chat serialization is not verified. Exact-control claims remain unavailable unless
the input audit supports them, and server equivalence remains an explicit limit.

The comparison tests sensitivity to background rearrangement at a fixed target
row. On the input-audited subset, it also fixes target plate/class token starts.
It cannot by itself explain the earlier first/last effect. Before/after also moves
the non-pattern records, neighboring identities and labels, signed distances,
token proximity, clustering, query distance and recency. Matching the absolute
row-distance multiset does not match token distances or neighbor order. Rotations
balance identities over slots but do not orthogonalize those mechanisms.

## Commands

Run from this branch's repository root; use a new output directory:

```bash
python -m unittest discover -s tests -p 'test_ordering_followup.py' -v
python -m unittest discover -s tests -v
python -m exception_ordering prepare --output runs/ordering-audit-preview
```

With an ALREADY AVAILABLE, model-matched tokenizer (no download required):

```bash
python -m exception_ordering prepare --output runs/ordering-audit-tokenized --tokenizer-json /absolute/path/tokenizer.json --tokenizer-model mistral-small-2603
```

Inspect `position-audit.json` for target plate/class offsets and full prompt lengths.
Keep all comparisons; do not select using outcomes or pad/rewrite records to force
matching. Future live collection requires the explicit flags and call limits in
the unchanged `EVIDENCE_ORDER_FOLLOWUP_PROTOCOL.md`. No paid call was made here.

Offline results: **9/9** focused tests and **378/378** full-suite tests passed.
The new preview command generated all 7,680 tasks, with tokenizer=null and token
positions UNMEASURED as intended. A SHA-256 check across both follow-up worktrees
found **585/585 pre-existing output files unchanged**. Real tokenization and
behavioral results remain pending. Changed files on this branch are only this
additive audit and `tests/test_ordering_followup.py`.
