# GPT explanation implementation audit

This is an **unexecuted plan**, not an experiment result. It contains exactly 96 matched input pairs, 192 pending GPT requests and zero dispatches. No paid API calls, tokenizer downloads, model loads or GPU inference were used to produce it.

`offline-plan-evidence.zip` is the portable audit export. It includes the sealed source archive, frozen GPT plan, source-validation record, incomplete analysis, blank manual-review sheet, trace placeholders and protocol. `request-manifest.json.gz` provides the same 192 ordered requests for inspection. `preview.json` records the settings, source hashes, code contract and plan hash. The historical Qwen responses inside the source archive are preserved as provenance; none is a GPT control.

The source ZIP remains `bb0e059f8a44a69b33990998b672e245405c4ca67c2d7d9214113283a6c9d31a`. The screen code contract remains `701262504d095b23d2d3320fb1ec794647b55b1064c07bb9788eb8a4547b9998`; the Qwen explanation contract remains `afa22d341708255bf3836d30c5db88176eb979981bf47741446b241041eeed48`. No existing package or result was modified.

The audit was prepared before this patch's commit. Its recorded Git revision is the preceding Qwen implementation commit; its code contract hashes the actual new implementation and protocol bytes. Reproduction after committing will record the newer Git revision and therefore a different sealed plan hash. That provenance difference is expected; the scientific request identities and code contract should agree.

## Offline results

| Suite | Run | Passed | Skipped | Failed |
|---|---:|---:|---:|---:|
| GPT explanation | 45 | 45 | 0 | 0 |
| Qwen explanation | 31 | 31 | 0 | 0 |
| Current Qwen screen | 27 | 27 | 0 | 0 |
| Historical native workflow | 36 | 33 | 3 | 0 |
| Total | 139 | 136 | 3 | 0 |

The three native skips concern unavailable optional saved tokenizer/template fixtures; they are listed in `native-tests.log.gz`. Qwen regression tests used previously available tokenizer assets and mocked generation. The new GPT suite ran with `python3.12 -S`, with third-party packages disabled. These are focused and related regression suites, not a claim that every test in the repository was rerun.

The tests cover exact prompt preservation and population, balanced order, payload allowlists, returned model aliases, final-message handling, visible commentary versus reasoning summaries, refusal/truncation/malformed categories, unknown billing metadata, output caps, one-failure stops, interrupted and ambiguous requests, zero-call completion, immutable source evidence, fixed-budget paired contrasts and correct sensitivity pairing. All API transports used in tests are mocks, including tests of the live opt-in code path. Logs and machine-readable results are included.

Offline prepare, default run, inspect, analyze, export, bundle checksums and relocation were also checked. Official documentation supports the frozen settings; real API acceptance, response behavior, runtime, cost and the scientific outcomes remain **not tested**. No dated model snapshot was listed, so reproducibility remains limited by the alias.

## Reproduce and inspect without credentials

From the repository root:

```sh
python3.12 -S -m unittest discover -s tests -p 'test_study2_gpt_explanation.py' -v
python3.12 -S audits/gpt-explanation-v1/reproduce.py --output /tmp/gpt-explanation-audit-reproduction
python3.12 -m zipfile -e audits/gpt-explanation-v1/offline-plan-evidence.zip /tmp/gpt-explanation-audit-inspect
python3.12 -S -m exception_study2_gpt_explanation inspect --output /tmp/gpt-explanation-audit-inspect
```

Use fresh temporary destinations. `SHA256SUMS` inventories every file in this audit directory except itself. The [laptop runbook](../../STUDY2_GPT_EXPLANATION_RUNBOOK.md) contains setup and the separately opted-in live commands. Stop after the fixed plan; no follow-on experiment is launched automatically.
