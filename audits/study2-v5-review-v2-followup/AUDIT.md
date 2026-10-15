# Review v2.1 focused follow-up audit

Base: `2ffbc4779e5bd3a96c86856324faa4f9c8cd607c` on
`codex/study2-v5-judge-review-v2`. This patch is limited to clause localization,
controlled evaluation counterbalancing, smoke-case selection, and their tests/docs.
The scientific v5 protocol, validator, original Qwen responses, failed v3 validation,
manual review option and independent intervention-verification gates are unchanged.

| Requested gap | Result | Evidence |
|---|---|---|
| Distinct A/O clauses with exact ordered nonoverlapping source spans | PASS | Requested compound example passes unchanged `validate_decisions`; Unicode, repeated spans, three clauses, `yet`/dash, Markdown and original IDs covered in `ClauseTests`. |
| Keep semantic definitions and negative gates | PASS offline | Codebook, `CHECKS`, `vote`, `finalize` and frozen scientific validator preserved. Mock negatives cover quotes, hypotheses, denial, questions, negated preference, conflict/prediction without O, O before/without A, uncertain preference and missing semantic judgments. |
| Balance classes, alternatives, target identifiers and row positions | PASS | `BalancedSuiteTests` checks every full factorial combination per scenario, original data-row indexing and exact authored gold spans. See separate suite definition/results. |
| Preserve old evaluation and disclose audit influence | PASS | Original 192-case generator checksum and complete evaluation output match the earlier report. Prior audit files remain byte-identical. New suite explicitly marks `audit_informed: true` and `independent_validation: false`. |
| Optional exact smoke `--case-id` | PASS offline | `SmokeSelectionTests` selects `staged-v5-001/v1/original/visible`; invalid/direct/unavailable IDs fail before dispatch. CLI forwards the ID only for smoke. |
| Four-call cap, immutable operations, no retries | PASS offline | Mock smoke with `max_calls=128` attempts only four calls; repeated smoke sends zero new calls, changing case fails, tighter limits resume only remaining slots, and terminal/ambiguous failures are not resent. Full review reuses smoke slots. |
| Full offline regression suite | PASS | 685 tests; 0 failures/errors/skips in 391.799s. Includes all 656 prior tests and 29 new tests. See `offline-results.json` and `full-offline-tests.txt`. |
| Real provider/semantic performance | NOT TESTED | No paid calls; all new semantic decisions use authored oracle fixtures and MOCK transports. |

## Clause localization and compatibility

The new localizer runs after the historical sentence segmenter. Supported contrastive
comma/dash clauses (`but`, `yet`, `whereas`, `however`) get exact Unicode character
spans, distinct location-based IDs, clause indices and their enclosing statement.
Judges receive the full source plus enclosing context. No automatic A/O labels,
semantic passes, certificates or changed acceptance thresholds are introduced.

For `The recorded class is C, but we should prefer inferred A.` the candidates can
refer to `The recorded class is C` and `but we should prefer inferred A.` separately.
A and O still need independent semantic acceptance and a valid earlier accepted A.
The separating comma/space is outside either assertion span; source text is untouched.

The added clause pass conservatively retains recognized quoted, conditional, explicitly
denied, interrogative, table and field-list statements. Unsupported grammar and ambiguous scope can remain
unresolved. This is not a general syntactic parser or a guarantee of semantic recall.

The review version is `study2-review-v2.1`. Changed code and prompt hashes require a
fresh separate review output directory. Old frozen plans and journals are preserved
and rejected under new code; they are not migrated or rewritten. All unchanged shared
provider/journal budgets, model identity checks and failure records remain in force.

## Separately versioned evaluation

- Version: `controlled-v2.1-balanced-audit1`; seed: `2026101503`.
- Suite hash: `21cce04b74609765c733474684958dcb540b3e125fae9203a5ae515f72bfc1f9`.
- 3,600 variants: 20 authored scenarios × 6 ordered recorded/inferred pairs × 3
  target identifiers × all 10 data-row positions. Every scenario has all 180 combinations.
- Each recorded A/B/C: 1,200; each inferred A/B/C: 1,200; each unequal ordered pair:
  600; each target identifier: 1,200; each zero-based data-row position: 360.
- Gold clause spans are authored independently of the localizer. A missing exact
  alignment fails construction rather than spreading a parent label across fragments.
- `suite-definition-freeze.json` records the definition/hash before the first test
  evaluation (`evaluation_started: false` describes that snapshot, not current status).
- `controlled-results.json` records structural extraction, oracle-wired reconciliation,
  no-judge abstention, exact span alignment, class/identifier/position balance and provenance.

**These examples were designed in response to this audit. They are not independent
validation, not held-out data, and not 3,600 independent observations.** The 20 authored
scenarios share 180 counterbalanced variants each. No natural-model accuracy is claimed.

For these fixtures, structural occurrence recall is 100% for each A/M/C/P/O/X.
With supplied correct semantic judgments, oracle-wired precision/recall/F1 is 1 for
each event, with no abstentions. There are 4,320 accepted exact source-aligned spans
and 540 accepted O events, each linked to an earlier nonoverlapping A. Without judges,
all cases abstain. These are regression/integration results, not estimates of judge
sensitivity, specificity, independence or real-world performance.

The historical `controlled-v2.0-split1` suite retains hash
`48d1a7b6b4b76375f69f229cc8c0977d930d0ff493b843f29e60d4e739c07fa8`.
Its generator explicitly uses the original sentence representation to reproduce prior
results; it is not represented as a benchmark of the new localizer. Its held-out
structural C recall (11/14) and O recall (9/12) remain visible in the prior audit.

## Exact offline results and preservation

- Targeted follow-up: 29 tests passed, 0 failures/errors/skips, 17.492 seconds.
- Full offline suite: 685 tests passed, 0 failures/errors/skips,
  391.799 seconds; all 656 prior tests plus 29 new tests. The review
  subset totals 75 tests (46 prior + 29 follow-up).
- No test changes were needed after the initial targeted run. The new suite definition,
  labels and hash were not changed after evaluation.
- 424 of 431 prior tracked files are byte-identical; only the seven intended review
  files/runbook changed. All prior audit files and all 786 recovered private files
  were verified byte-identical. See `preservation-check.json` for the hashes.
- Frozen v4/v5 source hashes, the semantic codebook, scientific validator, review
  decision gates and shared provider/journal files remain unchanged.
- Paid judging, real-model semantic accuracy and provider smoke: **NOT TESTED**.

## Reproduction and stop point

Use the existing pinned offline environment and already available tokenizer as in
`STUDY2_V5_JUDGE_V2_RUNBOOK.md`; no weights or network access are needed for this patch.

```bash
python -m unittest discover -s tests -p 'test_study2_v5_review_v2*.py' -v
python audits/study2-v5-review-v2-followup/run_full_offline.py
python -m exception_study2_v5_review_v2 evaluate --suite balanced-audit1 \
  --output /absolute/fresh/path/balanced-audit1.json
```

The full runner blocks sockets and writes
`/tmp/study2-v5-review-v2-followup-full-offline-results.json`. Historical CPU tests use
tiny random-weight models and the existing local tokenizer, not pretrained Qwen.
No network calls, GPU inference, weights downloads or scientific 2A/2B runs occurred.

The runbook documents a separately authorized paid smoke command with
`--case-id staged-v5-001/v1/original/visible`. Its sealed selection cannot be changed
within that output directory. Omitting `--case-id` reuses a saved choice or initially
chooses the first available visible case. At most four distinct slots are used:
primary extraction, primary J1, primary J2 and independent full-text audit. It does
not invoke J3, finish semantic review, certify interventions or start scientific runs.
**This implementation task stops after the tested patch is committed and pushed.**
