# Study 2 v3 → v4 compatibility map

The source branch was inspected and fetched before edits. Its current recorded head
was `bea5cc6ad01a954a13809674c31c97b49f4ecc09`, including the failed Qwen replay audit.
The implementation lives on the separate `codex/study2-conditional-prefix-v4`
branch. All pre-existing tracked files, scientific code, earlier experiments and
failure artifacts are preserved byte-for-byte; the acceptance manifest verifies
this against that base. Neither v3 results nor their validity labels are migrated.

| Existing dependency / gate | v4 replacement or reuse | Evidence / protection |
| --- | --- | --- |
| `exception_continuation/core.py` task construction, defaults, boundaries, final scoring | Reused unchanged. New `exception_study2_v4/core.py` wraps exact v3 tasks/config in a new protocol and plan hash. | Selection and confirmation prompt/assignment hashes, 48/96 originals, calibration thresholds, fixed cuts, seeds and per-task equality tests. |
| Local Qwen loader, tokenizer, official chat template, EOS, candidate scoring | Reused unchanged from `exception_continuation/backend.py` and `qwen3.py`. | Real local tokenizer-only regression across 48 prompts, exact empty block and cue/candidate concatenation; model dependency/revision checks unchanged. No weights loaded. |
| `runner.validate` / `validation.replay_check`: original incremental stream versus fresh-prefill exact suffix/logits | **Not invoked by v4.** `exception_study2_v4/validation.py`: two independent calls on identical context IDs, exact token/finish, finite full-vocabulary logits, probability allclose, argmax and TV. Raw-logit discrepancies reported separately, non-gating. | Fixed ≤33 operations/3,882 tokens. Deliberately divergent original suffixes pass only when the identical-input repeats match. All failure dimensions block scientific collection. LIVE requires 151,936 logits per vector. |
| `runner.collect`, timed `exception_review/qwen_timing.py::collect_selection` | v4 `runner.run`: genuine new gate, first-eight pause, explicit complete; no cross-path gate or legacy file construction. | Timed/untimed identical scientific journals, cache hits, no resampling, no downstream automatic launch. |
| `runner.measure`, old per-cut replay gate | v4 `readouts.measure_fixed/measure_cut`: exact pre-answer saved-token cut and fresh complete A/B/C sequence likelihoods. | No generation/reference calls; no future output tokens; failed k128 retains valid k0/k64 primary. Same summed token logprobs, cues, world bootstrap and both-variant requirement. |
| `events.py`, original event cuts | Pure boundary functions reused. v4 `review.integration.freeze_events/measure_events` freezes original cuts independently of edit acceptance. | Negative, unreviewed and edit-excluded outputs retain before-answer events; per-plan cut deduplication. No reference or suffix generation. |
| `exception_review/artifacts.Source` expects v3 validation/collection | Explicit v4 `source.Source` constructor; inherits only pure detector and case-binding views. | Requires new sealed plan, actual complete ordered originals, actual same-input gate recomputed from immutable operations and exact backend/source bindings. Old source readers reject v4; new readers reject v3. No forged `validation.json`. |
| `Review`, source policy, confirmation lock | v4 `review.artifacts` and `review.policy`; exact policy/source/code hash and selection model lock. | Changed configuration/backend/policy rejects resume. Confirmation requires passed selection and matching policy-lock artifact and config. |
| Two judges, conditional J3, one revision, exact-span mechanical and semantic checks, provider transport, budget journal | **Same source files**, loaded under versioned `exception_study2_v4.review` package context. Local adapters override artifacts/policy/integration/reporting; unchanged workflow/journal/decisions/editing/providers/boundaries/fixtures/semantic evaluation are resolved from the legacy package directory. No global monkeypatch of old source/validators. | Distinct module instances with the same stable source file, v4 binding assertions, mocked J3/revision/semantic-evaluation budget/cache tests. Both shared and v4 files contribute to the v4 source hash. |
| `integration.ModelSession` legacy journal | New `journal.Session`, `operations-v4`, `v4/…` IDs, request/start/terminal files. | Immutable requests, exact identity and status-chain verification, no automatic retries for dispatched failed/ambiguous work. Terminal failures retain stable result text across resume. |
| `validate_intervention_case` / `integration.intervene` cross-path unchanged gate | v4 `review.integration.arm_input/intervene`: frozen exact arm texts/tokens, saved original boundary, same original-k budget, exact outside-span preservation, complete generated-prefix preservation. | Every arm freshly generates independently; randomized order frozen with same seed. Unchanged original-suffix mismatch is only diagnostic. No obsolete fields set true. |
| `reporting.comparisons`, `coverage.py` require `unchanged_replay_passed` | v4 contrasts require the two relevant arms' input/text validity and known outcomes independently. | An unavailable unchanged arm does not erase availability-minus-meaning. Same world weighting, full frozen cohort, unknown bounds and initially-agreed subset. Zero-case/partial/invalid/truncated states remain explicit. |
| Legacy timing/workloads | Reuse `Telemetry`, synchronized `TimedBackend`, measured loader; new workload/report adapters count only new journals/plans. | No extra inference; fixed/events have zero generation ops. Mock/live separate. Unmeasured LIVE durations and total remain null. Separate event plans count separately; stale sources/manifests rejected. |
| Old CLI and runbooks / `REASONING_CONTINUATION_V3_PROTOCOL.md` | Left untouched. New CLI `python -m exception_study2_v4` and `python -m exception_study2_v4.review`, new v4 protocol/runbook. | `configure` freezes actual GPU-local path before plan creation; no frozen Mac plan edits. Default/help/preparation/reporting are offline. Inference and paid judges require explicit opt-in. |

## Versioned evidence

Scientific source hash, adapter/shared judge source hash, protocol ID, plan hash,
config, backend fingerprint and model/tokenizer content hashes are bound at their
respective stages. Machine-local absolute paths intentionally affect the frozen
configuration; configure the actual RunPod path before preparation. Reports do not
rewrite immutable source artifacts. Adding code to this scientific version
invalidates an existing plan rather than silently resuming under changed code.

`audits/study2-v4/offline-acceptance.json` records the base SHA, full v4 source hash,
scientific before/after hashes, test counts, preservation counts and hashes of all
prior tracked files. `files.sha256.json` lists the implementation files and hashes
(excluding the audit evidence directory to avoid self-reference). Local test logs
and a compact synthetic smoke result are packaged with the acceptance report.

## Interpretation and unresolved live evidence

v4 asks how subsequent answer choices change under controlled **textual** prefixes.
It does not show identical hidden states, restoration of the uninterrupted suffix,
that the original sentence caused the initial error, or that an edit uniquely
changed a pre-existing latent belief. These caveats are present in protocol and
reports, including event summaries.

There is no detected offline scientific-design conflict. Real Qwen technical
repeatability, GPU memory/timing, behavioral replication, natural false-missingness
case counts and real judge accuracy remain **NOT TESTED/PENDING**. Mock success is
software evidence only. If a same-input check fails, stop and retain the failed run.
No evidence probes or factual-question extension were added.
