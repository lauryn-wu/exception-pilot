# False availability claims and the next factual answer

This fixed exploratory study uses gpt-4o-2024-08-06, temperature zero, 64 completion tokens, 342 planned returns and 378 maximum attempts. No live results are included. No outcome-dependent extension or success gate is defined.

## Sources and selection

The frozen snapshot contains all 192 column-study class-copy response inventory entries and 36 full source conversations. The primary cohort comprises 13 responses from nine worlds with a correct COPIED line, an explicit false target-MISSING claim, and a correct final answer. Its 46 annotated MISSING spans are manually identified with exact offsets and evidence lines. One correct-copy/wrong-final response is a separate diagnostic. Thirteen controls are matched on schema and gold label without replacement and reviewed for absence of false target-missingness; this does not certify their other reasoning. Nine authentic missing-cell sources from the earlier explanation study form a separate calibration cohort. They used a different query form and must not be pooled with the main cohort. Selection and provenance are recorded in source_snapshot.json; screen-negative inventory entries were not exhaustively coded for every possible semantic error.

## Interventions

Each call receives the exact saved user prompt and table, one saved or edited assistant response, and: `What is written in {plate}'s Verified class cell? Reply with exactly one of A, B, C, or MISSING.`

Five arms apply to each contradictory source: original; availability_repair (only annotated MISSING tokens become RECORDED); missing_synonym (UNRECORDED); value_repair (recorded as the gold class); endpoints_only (retain only original COPIED and ANSWER lines). The primary repair introduces no additional class-letter tokens. Other inaccurate feature claims remain unchanged. The synonym edit controls for changing the word while preserving unavailability meaning. Value repair additionally repeats the answer, and removing the entire explanation has broader effects; both are secondary diagnostics. Every intervention preserves original endpoint lines, including the wrong final answer in the separate diagnostic.

Controls receive original and endpoints_only. Three independent scheduled calls per case and arm yield 195 main, 78 availability-control, 54 genuine-missing-control, and 15 wrong-final-diagnostic calls. Temperature-zero repetitions are not independent worlds. Each call is a fresh reconstructed conversation, not a restoration of the original model's hidden state.

## Outcomes and analysis

Only whitespace-trimmed A, B, C, or MISSING is valid. Invalid returns are retained and never retried. The sole primary contrast is original minus availability-repair false-MISSING rate in the main cohort. Average repetitions within case, then cases within world, then equally weight the nine worlds. Complete-world estimates require every repetition of every case in both arms to be valid. Full-plan bounds retain unknown outcomes; 10,000 world bootstrap draws (seed 481602) produce descriptive unadjusted intervals. Nine selected source worlds cannot establish prevalence, and a degenerate zero interval cannot prove no population effect. Accuracy, all other contrasts, and the wrong-final diagnostic are secondary. Controls are calibration, not randomized cross-cohort causal comparisons. A null result applies to this follow-up with the original correct copy and final answer still visible.

Outputs retain raw responses, paired transitions, world contrasts, invalid and pending denominators. Requests, source hashes, plan, and preview are frozen before collection. See FOLLOWUP_STUDIES.md for preparation, run, resume, and analysis commands. No paid calls are needed for preparation or mock validation.
