# Targeted Study 2 audit fixes — 2026-10-12

Fetched and inspected origin/codex/reasoning-continuation-followup before edits:
head was still 4baf414008f32e90eda202dee247e0a191a40ac4. Changes stay on that
branch; no merge of the four earlier pending studies or Study 1.

| Issue | Change | Verification |
|---|---|---|
| One failed fixed checkpoint discarded all readouts | Per-cut eligibility and replay gate; trajectory any-failure telemetry retained | 128 failure retains the primary; 0/64 failures exclude it; one failed variant excludes only that world; failed stray readouts ignored |
| Invalid answers absent from combined failure counter | Deprecated combined counter; independent replay/eligibility and per-arm denominators/reasons | Malformed and truncated returns with successful replay stay unknown; contrast-specific coverage/bounds preserved; partial attempts and tokenization failures counted |
| Only early fixed checkpoints | Separately frozen event-checkpoints-v1 in new v3 runs; before/after statement and before first answer marker | Late cuts beyond 128, boundary exclusions, independent event freeze, exact prefix inputs, reference/replay failure rejection and journal reuse tested |
| Risk of reinterpreting old outputs | New v3 protocol/config/source lock and fresh seeds; reject v1/v2 plans | Historical version/config/protocol/preview/result paths unchanged; old plans rejected without writes |

Focused offline suite: **31/31 passed**. Full offline suite on Python 3.12.13:
**400/400 passed**. The initial system Python 3.8 full run had nine existing
`str.removeprefix` errors outside this patch; rerunning with the required modern
interpreter resolved all nine without changing unrelated code. Commands:

```sh
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m unittest discover -s tests -p 'test_continuation*.py' -v
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -m unittest discover -s tests -v
```

New input-only prepare/analyze preview completed with 48 selection tasks and
NOT_COLLECTED/PENDING status. Real model/template replay validity, numerical
tolerances at a chosen precision, and behavioral replication remain PENDING.
No paid API call, live inference, GPU launch or model/tokenizer download occurred.

A SHA-256 preservation check across the seven original exception-pilot folders
found **11,109/11,109** existing output/preview/result/ZIP files unchanged. New
checks used temporary directories. Old frozen plans are not migrated; use
4baf414 for v2 and 1be7551 for v1 reproduction.

See CONTINUATION_V3_RUNBOOK.md for exact next commands and conditional workload:
144 shared originals; up to 1,182 total generation calls including validation;
up to 2,808 candidate likelihood forwards, and 216 edited continuations plus 72
unchanged controls. Event cuts add up to 288 generation calls and 648 candidate
forwards; availability/validation determine actual counts. The fixed primary
and the two-variant world requirement remain intact.
