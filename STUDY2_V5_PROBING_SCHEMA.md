# Offline probing-readiness contract (no probes implemented)

Schema `v5-fresh-prefix-context-v1`; experiment design `staged-60-v1`.
This interface reconstructs **fresh-prefix replay contexts**. It does not assert
that future replay hidden states equal the original incremental generation states.
There is no activation extractor, model load, CUDA access, training, probe layer,
target label, architecture or hypothesis selection in this interface.

## Artifact graph and portable references

`plan-v5.json → execution/technical journals → originals-v5/<task digest>.json`
feeds three separate branches: candidate readouts, independent semantic annotations,
and the offline checkpoint manifest. Reviewed annotations additionally feed M/O
edit manifests, independent continuations and event checkpoints. Only original rows
supply uncued reconstruction IDs. Intervention IDs never replace original IDs.

All frozen JSON uses canonical `artifact_hash` seals. Source bindings contain
`scope` (pilot, remaining, all), plan/source/backend hashes, and a **relative path**
from the referring manifest's directory. Each scoped hash binds all source row seals,
execution and technical report. It stays unchanged as later originals are added.
Move the entire research tree together; copying only a manifest is insufficient.
Missing or stale dependencies fail explicitly. Hardware is provenance, not an offline
execution requirement. Source model paths may name a now-absent GPU directory.
Live resumption still uses the strict original backend identity checks.

## Original and checkpoint fields

Originals preserve the task (world/variant/framing/condition/table/target row/expected
and pattern class), prompt IDs/hash, raw generated IDs including EOS, full text,
lengths, finish/truncation, strict and tolerant parsing, operation and backend hashes.
The source plan retains source text, randomized schedules and model/tokenizer pins;
execution retains actual dtype/device/hardware/libraries and code revision.

`prepare-checkpoints` freezes one manifest containing each visible task's parent
world, source-row seal, input/output fingerprints and named cuts. Cuts contain:

| Field | Meaning |
|---|---|
| `name` | fixed/0, fixed/128, fixed/256, fixed/512, fixed/1024, pre_answer, or event/before/after |
| `eligible`, `reason` | Explicit availability and unavailable reason |
| `k` | Number of saved original generated IDs to include |
| `char_end` | Exclusive Unicode code-point offset in original response text |
| `roundtrip_exact` | Exact token/text roundtrip checked during original collection |
| `token_hash`, `text_hash` | Fingerprints of original IDs[:k] and text[:char_end] |

Event cuts also bind a frozen annotation manifest with exact statement span/text,
anchor, independent decisions, disagreements/adjudication and clean/mixed history.
Absent/uncertain/invalid events have unavailable checkpoints. No implicit fallback
to a nearby invalid cut is permitted.

## Reconstruction result

For an available cut, `reconstruct` returns:

- `prompt_ids`: saved rendered original IDs, including official chat-template tokens.
- `original_prefix_ids`: saved generated IDs[:k], never re-encoded text.
- `context_ids`: exactly their concatenation; no answer cue appended.
- `original_prefix_text`, token counts, hashes and full checkpoint boundary metadata.
- Task/world, original row/operation, plan/code/backend/technical identities.
- Original generation settings, finish and parsed outcomes; original/fresh replay
  diagnostic metadata, explicitly nongating for cross-path agreement.
- `context_kind: "fresh-prefix replay context"`,
  `original_hidden_state_equivalence: false`, `activations_collected: false`.

Unavailable results have `available:false`, reason and null context fields. Missing,
corrupt, wrong-source or malformed artifacts raise errors. No tokenizer/model/GPU is
used to recreate IDs. The stored roundtrip certificate is checked against recorded
text/token fingerprints; this utility does not claim to independently decode IDs
without a tokenizer. If later activation replay is implemented, it must version and
record its actual model, layer, dtype, backend, device and hardware separately.
Original incremental hidden-state capture would require a new collection protocol.

## World-disjoint split manifest

Schema `v5-world-split-v1`: fixed plan/source fingerprints, seed, all world assignments,
all 480 task-to-world assignments, explicit pilot design-use decision and descendant
inheritance rule. Default 12 evaluation worlds, remainder training; choose by hashing
(seed, world ID), without reading any responses. When pilot informed methods, its
four worlds are excluded from the evaluation pool. The eight matched conditions and
all checkpoint and intervention descendants of a world stay in its one split.
`descendant_split` checks the parent task/world and deterministic assignment against
the frozen plan before returning it. A forged parent world or stale split is rejected.
Split files are immutable; changing the seed/path to hunt a favorable test set is not
a valid confirmatory procedure. Outcome-based rebalance must be explicitly exploratory.

The synthetic example in `audits/study2-v5-staged/mock-context-example.json` demonstrates
the exact concatenation and identifies itself as MOCK. It is not behavioral evidence.
No hidden activations were collected for that example or the offline tests.
