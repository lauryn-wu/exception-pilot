# Study 2 review v2.2: offline salvage and targeted reliability fixes

This is an additive repair alongside `exception_study2_v5_review_v2` (frozen v2.1).
The old implementation, paid journals, manifests, original Qwen generations and
scientific v5 code remain unchanged. It does not run Qwen, download weights, verify
intervention edits, approve the remaining worlds, or start Study 2A/2B.

The recovered evidence remains **retrospective sensitivity analysis**. Recovering a
valid individual vote is not an independent new judgment or proof of semantic truth.
The implementation was informed by this run, so these cases are not held-out validation.

## Saved offline salvage

The completed analysis is in:

```
~/exception-v5-recovery/study2-v5-review-v2-1-salvage-v2-2/
```

- `salvage-report.json`: exact recovery counts, uncertainties, coverage failures and
  additional-call projections.
- `operation-audit.json`: every verification response's expected/returned/omitted,
  duplicated, unknown and malformed IDs; individually invalid decisions and reasons;
  original operation hashes and raw-body checksums.
- `retrospective-observations.json`: per-item votes, original operation references,
  independent support, phase reconciliation, existence evidence, first-occurrence
  decisions and retained historical coverage flags.
- `annotation-manifest-v5-retrospective.json`: separately named compatibility manifest,
  checked by the unchanged scientific `read_manifest`/`validate_decisions`. It has
  explicit retrospective/sensitivity provenance. Structural validity does not make
  it an independently validated scientific result or an intervention approval.

Source and paid-response trees are hashed before/after analysis. The salvage command
has no transport dispatch path. It validates original sealed artifacts, slot/source/
policy/request identities, exact raw-body parsing, model identity and source spans.
It writes only to a separate output directory; identical reanalysis reuses immutable
outputs, while code/data changes require a different output directory.

Reproduce offline with the existing Python environment (no GPU or model required):

```bash
cd /absolute/path/to/exception-pilot
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
python -m exception_study2_v5_review_v22 salvage \
  --review "$HOME/exception-v5-recovery/study2-v5-review-v2-1-live" \
  --output "$HOME/exception-v5-recovery/study2-v5-review-v2-1-salvage-v2-2"
```

All source paths refer to the existing Mac recovery; no RunPod setup is involved.
The complete numerical diagnosis is in `audits/study2-v5-review-v22/AUDIT.md`.

## What changes in prospective v2.2

1. **Auditable filtering.** Existing deterministic vetoes remove impossible candidate/
   event combinations (explicit other vehicle/column, recorded-cell comparison against
   the source, rigid prediction vs recorded-value roles). A narrow additional rule
   handles an unambiguous other-vehicle recorded-class prose assertion. Exclusions and
   reasons are saved. Ambiguous prose remains; full source text is never filtered out.
2. **Small immutable batches.** Default target six candidates; deterministic balanced
   groups of 4–8 whenever at least four remain (smaller groups when fewer exist). A
   phase's batches, candidate IDs, source references, schema/prompt hashes and exact
   J1/J2/J3 requests are sealed before the first verification call in that phase.
   Semantic extraction necessarily precedes freezing its newly discovered candidates.
3. **Per-item validation.** A unique expected valid item survives missing/malformed
   siblings. Omitted IDs stay uncertain; duplicates invalidate only that ID, even if
   identical. Unknown IDs never vote. Provider/envelope/full-review errors cannot be
   salvaged into successful reviews. All raw failed/partial responses remain terminal.
4. **Coverage separated from detection.** Extraction/audit return a full-text review
   status plus per-event search coverage and `detected: yes/no/uncertain`. Complete
   review with no event is explicitly `coverage: complete, detected: no`. Incomplete
   review/detection uncertainty never establishes absence. Historical `fail` fields
   are not rewritten from their explanations.
5. **Recorded vs inferred evidence.** Candidate decisions include `value_basis` and
   `asserted_class`. A needs the actual recorded class and a recorded assertion; a
   coincidentally correct prediction is not A. P needs endorsement of a different
   inferred class. O additionally needs an accepted earlier A and explicit preference
   over the record. An asserted false claim is still an assertion: M's falsehood is
   not grounds for marking its assertion mode false. Existing semantic/first-occurrence
   gates and the scientific validator remain in force.
6. **Support and disagreement.** Agreement requires two distinct exact models from
   different providers (a conservative provider-family grouping, not a statistical
   independence claim). Same-family repeats cannot form a second independent vote.
   J3 cannot duplicate J1/J2's exact model. Missing/malformed responses are distinguished
   from semantic disagreement; only actual disagreement or explicit semantic uncertainty
   automatically opens the existing single J3 slot. Cross-phase semantic discrepancies
   remain uncertain. A missing phase is not a contrary vote against valid independent
   support in another phase. An extra same-family minority vote does not reopen an
   already established J1/J2 consensus.

Supported existence is reported separately from a certifiable first occurrence. A
later accepted P can be real evidence even while an earlier unresolved candidate
blocks the first-P boundary. P never becomes O merely because it contradicts a record.
No natural trajectory is resegmented or newly generated during historical salvage.

## Preparing a future review without executing paid calls

The old v2.1 smoke/run commands stay available in their original package; do not mix
old and new output directories, policies or schemas. v2.2 is a new plan, not a retry
of failed old slots. Use the existing CPU/Python setup. For offline inspection:

```bash
python -m exception_study2_v5_review_v22 prepare \
  --source "$HOME/exception-v5-recovery/study2-v5-staged-huwUCkqs/originals" \
  --scope pilot --config configs/study2_v5_review_v22_offline.json \
  --output "$HOME/exception-v5-recovery/study2-v5-review-v22-offline"
python -m exception_study2_v5_review_v22 inspect \
  --output "$HOME/exception-v5-recovery/study2-v5-review-v22-offline"
```

Default `run` without `--live` dispatches zero calls. Do not enable paid execution as
part of this repair. A future live run needs separate authorization, a new private
configuration with verified exact provider model identities/contracts/access/rates,
and a fresh directory prepared under that configuration. The unchanged shared
transport and ledger enforce model identity, finite total call/spend budgets, per-call
and wall deadlines, immutable slots and no automatic retries. Ambiguously interrupted
calls are terminal and never resent. Default offline limits are 256 total calls,
$25 estimated spend, 120 seconds/request and 7,200 seconds/invocation; these are ceilings,
not promises that the review will finish. Conservative reservations may stop it sooner.

For the observed historical pool after filtering: 62 verification batches plus 32
extractor/auditor calls imply **156 calls without J3; at most 218 with one J3 per batch**.
A targeted retrospective repair *estimate* is **61–87 new calls**: nine failed-coverage
reviews plus two judges across 26 batches of the 103 remaining retained uncertain
candidates, with up to one J3 per batch. This estimate is not an implemented mixed-epoch
repair protocol, permission to retry old slots, or an independent confirmation plan.
Fresh extraction can discover additional candidates; a frozen global budget still wins.

## Offline acceptance

```bash
python -m unittest discover -s tests -p 'test_study2_v5_review_v22.py' -v
# Existing pinned environment/tokenizer already available; no automatic download.
export QWEN3_TOKENIZER_DIR=/absolute/path/to/existing/pinned/tokenizer
python audits/study2-v5-review-v22/run_full_offline.py
```

The runner blocks network connections and writes
`/tmp/study2-v22-full-offline-results.json`. New workflow/salvage tests also block real
model construction and use synthetic judge responses. Historical tiny random-weight
CPU model tests remain in the full suite; no pretrained Qwen/GPU inference occurs.

- Targeted v2.2 regressions: **39 passed**, zero failures/errors/skips, **62.510 seconds**.
- Full offline suite: **724 passed**, zero failures/errors/skips, **461.887 seconds**, including all 685 prior tests.
- Network blocked; zero paid judge calls, pretrained Qwen inference calls, GPU inference calls or model downloads.

The revised API schemas, batching behavior with real providers, and semantic accuracy
of fresh v2.2 judgments remain **NOT TESTED**. No paid calls were made. Stop after the
offline report and pushed patch; no GPU experiment or intervention is approved here.
