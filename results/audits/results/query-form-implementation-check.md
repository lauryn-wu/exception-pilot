# Revised Run 0 / Run 1 implementation check

No new live model collection has occurred. Neither `OPENAI_API_KEY` nor
`MISTRAL_API_KEY` was available in the implementation workspace. No credential
values were read into reports or saved files. Run 2 is deferred for redesign.

Completed checks:

- Initial implementation, before the review amendment below:
  `python3 -m unittest discover -s tests -v`: **393 tests passed**, including
  all existing tests and 24 new offline tests. Final full-suite duration: 87.750 s.
- Mock end-to-end checks for both providers completed 288 tasks, resumed after
  12 calls, retained invalid responses, blocked config/source/mode changes and
  prohibited response replacement. Mock outputs say SIMULATED and cannot proceed.
- Fixtures recovered a planted world-paired interaction and the full [−1,1]
  record-sensitivity scale. They checked paired denominators, sign-test ties,
  invalid-answer bounds, both stop decisions and the two-model spending rule.
- Returned malformed JSON, truncation and refusal remain terminal invalid data;
  model mismatch stops; known transport errors require explicit retry; unresolved
  attempts cannot be resampled. The cumulative 316-attempt cap is enforced.
- Preparation ran with socket connections blocked and made zero network calls.
  Both prepared plans are byte-identical, with plan hash
  `110bbe5e3f1dd1cc1b5967c3c2cdd8e52a35c6f266fec6d2215107de019cd74a`
  after the precollection review amendment below.
- Exact world-000 prompts and all 288 requests per provider are committed under
  `previews/query-form-gpt4o/` and `previews/query-form-mistral/`. Run configurations
  are frozen separately from the model-independent plan.
- The offline coder processed 240 selected archived responses, wrote 20 blinded
  samples per run, and retained both revised and original-regex flags. Every file
  extracted for the five source run directories remained byte-identical to its
  original ZIP entry after coding. See `analysis/rationales/README.md` for caveats.
- The only changed existing tracked file is `README.md`; packages, configs,
  protocols, tests and results from earlier studies were preserved. All other
  additions are new files. The existing package manifest is unchanged; invoke
  the new CLI from the repository root.

Live collection must still be performed with the commands in
`QUERY_FORM_PROTOCOL.md`. A 12-call execution check is followed by the fixed
remaining schedule, regardless of interim accuracy. `analyze --replication`
recomputes both models before a combined decision can be written. No dose
execution is implemented or authorized by a simulated result.

## Precollection review amendment

The original spending rule could pass with zero key accuracy when both key arms
failed equally. The reviewed rule also requires full-plan accuracy lower bounds
of at least 0.90 for profile/direct, key/direct and key/visible: at least 44/48
correct in each cell. Invalid answers count conservatively as incorrect. Failure
returns `insufficient_record_competence`, preventing a floor effect from being
mistaken for preserved record use. Existing clear-harm stops retain precedence.

All 18 query-form tests and all 8 rationale tests passed after the change. New
regressions reproduce the zero-accuracy false approval and verify the 44/48
threshold. Both provider previews were regenerated and revalidated offline with
socket connections blocked. Prompts, models, tasks and provider settings are
unchanged. Only the decision rule, documentation and resulting plan hashes changed.
No live API calls were made. Use fresh run directories for this reviewed plan.

The study is suitable as a bounded test of whether query form moderates harm from
requesting written reasoning. A positive result does not identify an internal
retrieval or task-recognition mechanism. The filler condition is an approximate
content/length control. `stop_query_form` rejects the prespecified near-elimination
criterion; it does not show that query form has no effect.
