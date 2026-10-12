# Offline verification — 2026-10-12

- Full repository suite: 375 tests passed (369 inherited + 6 new test methods).
- New test methods exercise all 24 worlds and all 20 rotations, fixed target row,
  complete record inventory, matched radial distances, identity/slot balance,
  differing token offsets under a test tokenizer, outcome bounds, partial data,
  opt-in enforcement, mock/live isolation, identity drift, raw-invalid retention,
  and journal tamper detection. The final new-study suite was rerun after polish.
- Offline preparation: 7,680 deterministic requests and complete JSON preview.
- A 16-response mock integration block exercised prepare/run/analyze. SIMULATED
  correctness is a software check, not evidence for the hypothesis.
- No real tokenizer was available in this workspace. Token positions remain
  explicitly UNMEASURED in the committed preview; live execution is blocked until
  a model-matched tokenizer audit is supplied and its provenance acknowledged.
- No model calls or model downloads were made.
- Only new files are added. Main and the four pending-study branches are unchanged.

Exact commands and interpretation limits: EVIDENCE_ORDER_FOLLOWUP_PROTOCOL.md.
All 7,680 requests can be regenerated offline. The committed readable preview
shows one full 16-cell block; position-preview.json includes both response arms.
