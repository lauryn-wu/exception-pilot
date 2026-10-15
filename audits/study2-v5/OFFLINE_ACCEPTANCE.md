# V5 requirement-by-requirement offline acceptance

Final full offline suite: **565 passed, 0 failures, 0 errors, 0 skips**, including
**36 v5 tests**; 304.585 seconds in the test runner. Network connections blocked.
See `offline-results.json` and `full-offline-tests.txt`.

Status is scoped: “passed” means implemented and checked offline, not experimentally
confirmed. Synthetic text/logits/judge certifications are fixtures, not real evidence.
No Qwen weights, GPU inference, paid judge requests, model downloads or Pod launches
were performed. Independent real annotation/review has not been conducted.

| Specification requirement | Status | Evidence |
|---|---|---|
| New scientific version, behavioral/trajectory/intervention claims and limits | Passed (protocol) | `REASONING_CONTINUATION_V5_PROTOCOL.md`; distinct estimands, conditional-text interpretation, no latent-state/causal-occurrence claim |
| Branch from expanded screen; preserve v3/v4, old diagnostics and artifacts | Passed | Base `bfee376`; preservation manifest; `DesignTests.test_v4_and_all_previous_files_preserved` checks all 353 old tracked files and v4 hash |
| Isolated v5 package/config/plans/hash/journals; no silent legacy 512 cap | Passed | `core`, `journal`, explicit 2048 request tests; old loader config stays 512; versioned manifests/source binding |
| 12 fresh selection and 48 held-out worlds, balanced roles, 8 conditions/world, target-last conflict | Passed | `test_counts_balance_and_fresh_worlds`, `test_matched_prompts_change_only_question_instruction_or_cell` |
| Original framing and direct/visible wording preserved; lookup changes question only | Passed | Exact string/table comparisons in design tests |
| New originals from exact rendered prompts, greedy BF16 profile, thinking disabled, uninterrupted 2048 calls | Passed (implementation/mock) | Unchanged LocalBackend/profile; `test_bounded_pilot_and_explicit_complete`; fake backend call records; no readout capture in originals |
| Official empty thinking block retained; pinned tokenizer/candidate IDs | Passed (real tokenizer only) | `TokenizerTests` checks 96+384 actual rendered prompt templates and prefix concatenations, no model loading |
| Tolerant terminal Markdown answers, strict compliance, invalid/truncated unknown | Passed | Parser tests cover accepted/rejected balanced formats, prose, truncation; raw EOS/finish checks; full-plan missingness/bounds |
| Paired original/lookup behavioral summaries and interaction clustered by world | Passed (mock) | `behavioral_report`; whole-pipeline test; world-weighting/bounds test; calibration 20/24 + 3 pattern errors/2 worlds frozen before real runs |
| 2A fixed 0/128/256/512/1024 and pre-answer, no future tokens/no generated answers | Passed | `checkpoints`, `test_roundtrip_boundaries_and_no_answer`; whole-pipeline context-ID assertions and unchanged generation-call count |
| Full candidate summed log probabilities, normalized scores/preferred class/log odds | Passed | Whole-pipeline scoring assertions; incomplete likelihood rejected by `test_partial_sequence_likelihood_rejected_without_sampling` |
| Four independently annotated semantic events, exact boundaries, cue sensitivity and deduplication | Passed | Distinct annotation schema/events; full combined planner; `test_separate_fixed_and_event_names_deduplicate_exact_cuts`; primary/secondary reports |
| M prose/unknown-cell subtypes; separate miscopy; O requires acknowledgment then actual overriding | Passed (structured review/fixtures) | New frozen rubric; positive/negative fixture decisions; prior-ack, conflict/override certificate tests; no v4 missingness-only detector used for O |
| Every visible response reviewed, outcome blinding, first eligible assertions, negative/uncertain/excluded/invalid decisions | Passed (workflow) | `blinded_view`, unavailable-source test, first-occurrence certificate/anchor tests, review population equality; outcomes/scores cannot change views |
| Independent reviewers and third adjudication, preserved disagreement/source bindings | Passed | `test_adjudication_preserves_disagreements_and_invalid_statuses`; sealed independent reviews/adjudication/manifest |
| Semantic accuracy/first-occurrence correctness in real model text | Not tested | Requires independent human semantic judgments; software checks structured certificates/provenance, not meaning by keyword |
| Four distinct edit arms, no class/hint leakage, exact common span, grammar/table preservation | Passed (mock/structured verification) | `build_texts`, table form/leak tests, mandatory independent full-draft verification hash/checklist; invalid semantic edits cannot be autoaccepted |
| Token validity, separate fresh-prefix arms, 2048-original_k, no future/cache leakage | Passed (mock) | Entire-pipeline exact input-ID/budget assertions, length-change test, tokenizer-only freeze, no supplied caches; suffix agreement diagnostic only |
| Failed/ambiguous requests never resend; invalid arms retained; independent contrasts | Passed | Journal no-retry tests, unavailable original preservation, partial-arm/readout failure tests, repeated cached execution adds no calls |
| World-grouped frozen denominators, bounds, clean/mixed O, initial outcomes and multiplicity | Passed (mock) | `contrasts`, `annotation_report`, `intervention_report`; unequal world sizes/unknown bounds test; 97.5% primary family intervals, no automatic significance claim |
| Explicit task-interpretation control and staged future pattern-alignment design | Passed (protocol) | Lookup in every world; future marginal-preserving majority-swap design, infeasibility/marginal checks and separate workload; no alignment execution |
| Fresh new-Pod same-input gate, full-vocabulary checks, failure blocks collection | Passed (implementation/mock) | Reused v4 comparison, separate v5 journals; `test_failed_gate_blocks_scientific_calls`, `test_no_implicit_gate_or_model_load`; no original/fresh gate |
| New-Pod driver/GPU/native BF16, pinned weights, actual repeatability and memory | Not tested | Explicit runbook `preflight` and `validate` remain to be run on newly deployed Pod |
| Separate staged commands and confirmation lock, no automatic next experiment | Passed (mock) | Public default `--mock` CLI regression; collection does not auto-run summary; bounded pilot/full selection; full pipeline creates independently locked 384-task confirmation plan only |
| Offline entire pipeline, network/model calls prohibited in tests | Passed | `Offline.setUp` blocks sockets and LocalBackend loader; end-to-end mock 2A/M/O; entire suite also blocks sockets |
| Live runtime/cost or scientific replication, actual eligible cohorts | Not tested | Engineering scenarios only; measured LIVE timings absent, mock timing explicitly labelled |

## Review implementation boundary

V5 provides a complete auditable manual review/import/adjudication workflow for both
families, including independent semantic edit verification. It does not implement or
execute a new automatic paid judge driver. “Detection fixture passed” means the
structured rubric decisions and exclusions are handled correctly; it does not mean
natural-language classification has been automated or independently validated.

## Reproduction

Targeted (requires the already-present local tokenizer assets to avoid skips):

```bash
PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
QWEN3_TOKENIZER_DIR=/path/to/existing/pinned/tokenizer \
python -m unittest tests.test_study2_v5 -v
```

Full suite uses `unittest.defaultTestLoader.discover('tests')` under socket connection
patches raising on network attempts. The checked-in logs and `offline-results.json`
record actual counts and results. Prior tiny CPU models in legacy tests are not
pretrained Qwen inference. New generation and scoring tests all use `Fake`.

Offline tokenizer audit: selection 38880 input tokens, confirmation 155904;
complete candidate IDs A=[362,198], B=[425,198], C=[356,198]; both cue lengths 4.
This is local tokenization only, zero original scientific responses generated.
