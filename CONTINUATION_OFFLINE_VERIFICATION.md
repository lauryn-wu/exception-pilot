# Offline verification — 2026-10-12

- Full repository suite: 379 tests passed (369 inherited + 10 new test methods).
- New tests cover disjoint selection/confirmation worlds; opt-in before backend
  loading; technical and scientific replay failures; exact token-prefix reuse;
  early-final checkpoint exclusions; multi-token candidate scores; unchanged
  parent trajectories; first-eligible edit cuts; availability repair without added
  class letters; matched control arms; immutable edit plans; phase/backend locks;
  mock/live isolation; invalid/truncated answers; interruption and tamper guards;
  and detection of prefix re-encoding differences. The final new-study suite was
  rerun after polish.
- Full mock selection collection: 48 trajectories, 24 visible checkpoint audits,
  separate readout branches, review export and descriptive analysis.
- An end-to-end test completes manual-fixture review, edit freezing, all four
  intervention arms, analysis and a separately locked mock confirmation plan.
- Committed branch-preview.json is an explicitly synthetic character-token
  fixture, not a real language-model response or model tokenizer.
- No real model/backend was loaded. No real prefix-continuation validation,
  behavior replication or confirmation has been claimed. Actual local execution
  requires an already downloaded model and explicit --live, and the technical
  and per-trajectory replay gates must pass before edited results are interpreted.
- No paid model calls, inference, or model downloads were made.
- Only new files are added. Main and the four pending-study branches are unchanged.

Exact commands: CONTINUATION_RUNBOOK.md. Design: REASONING_CONTINUATION_PROTOCOL.md.
