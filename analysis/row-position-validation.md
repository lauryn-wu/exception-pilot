# Row-position implementation checks

The implementation is ready for the fixed Mistral development run. No live model
calls were made while implementing or validating it.

- 29 row-position tests passed: 6 design checks, 12 analysis checks and 11 runner
  checks. The 18 existing query-form tests also passed.
- The bundled 24 worlds match the completed query-form plan. Each appears at
  rows 1, 5 and 10 with both record labels and both response instructions.
- Relocation changes only table order. Target content and the other nine rows'
  relative order are preserved; matching original positions reproduce the old
  key-query prompt exactly.
- A full 288-task simulated run completed through the same runner, including a
  12-call start and 276-call resume. Mock outputs remain labeled SIMULATED.
- Returned invalid answers cannot be retried. Transport retries require an
  explicit flag and count toward the 316-attempt cap. An unresolved started
  request cannot be followed by another journal entry.
- Synthetic outcomes verify the interaction's direction, variant averaging,
  world pairing, signed missing-data bounds and 20-point review threshold. A
  missing middle-row response does not remove a complete endpoint world.
- A large constant interaction can merit fresh-world review, with a warning
  that its degenerate bootstrap interval cannot establish precision. Constant
  small or null effects cannot trigger the small-effect spending decision.

The frozen preview plan hash is
`ae4423a09d6d1652ba829f6fe9b5c3759320f2e942a5733e5c9c1dc271171ea0`.
The source-world digest is
`3eeaf3a09137f7faa60539f3b34c78916ea5f1cf068f2562df94720c644c74a4`.

Exact requests and the first world's readable preview are under
`previews/row-position-mistral/`. Prepare a new directory under `runs/` for live
collection using `ROW_POSITION_PROTOCOL.md`; do not run into the preview folder.
