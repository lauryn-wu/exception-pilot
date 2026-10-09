# Mistral prefix feasibility: V2 setup correction

Protocol: `verified-facts-mistral-prefix-feasibility-v2`.

## Why this version exists

In `mistral-prefix-001`, after repeated transport errors, attempt seven
returned `Cobalt Mape Lantern` with finish reason `stop`, the requested
model ID, and no separate reasoning content. The supplied prefix `Cobalt Ma`
was preserved, but the generated continuation omitted the `l` in `Maple`.
V1 correctly failed its exact-match requirement. This single response does not
identify why the letter was omitted or establish that prefix continuation is
unavailable. No research-case responses were collected in V1.

The V1 technical probe split a word. The actual replay cut rule always ends
after a complete whitespace run. V2 corrects this mismatch by changing **only
the capability prefix**, from `Cobalt Ma` to `Cobalt ` (one trailing ASCII space).
This amendment was made after inspecting the V1 capability response and before
collecting any V2 or research-case response. It is not independent confirmation.

V1 source and its failed run remain unchanged and auditable. Do not edit its
saved plan, relabel the typo as a pass, resume it, or delete its attempts.

## Exact V2 capability request

The user message remains:

```text
Output exactly this text, without quotation marks or commentary:
Cobalt Maple Lantern
```

The last assistant message is now:

```json
{"role": "assistant", "content": "Cobalt ", "prefix": true}
```

The required full returned text is still exactly `Cobalt Maple Lantern`.
No trimming, spelling correction, suffix-only acceptance, or tolerance is added.
The model, temperature, reasoning setting, 32-token capability limit, provider
normalization, and all other request fields are unchanged.

Passing this check establishes the specified behavior for this setup probe.
It does not establish preservation of a hidden state or reproducibility of
research answers. The later unchanged-prefix replay gate is still required.
If V2 fails, stop and inspect its saved response; do not repeatedly change
phrases or replace returned answers until a setup check passes.

## Scientific design and bounds

All worlds, target variants, base prompts, task order, answer parsing, exact
replay cuts, sample sizes, and behavioral/replay thresholds remain those in
[MISTRAL_PREFIX_PROTOCOL.md](MISTRAL_PREFIX_PROTOCOL.md). V2 has a new protocol
identity, source digest, configuration path, and output directory.

There are at most 73 responses: 1 capability, 48 base, and 24 conditional replay.
The 89-attempt cap applies separately to V2. V1's seven attempts are retained
separately; they are not erased from project history or counted as V2 evidence.
The unchanged behavioral gate can stop V2 at 49 returned responses. No edited
prefix intervention is implemented, and no gate is a statistical significance
test or an identified mechanism.

The V2 package reuses the original provider. Its runner and reporting module
are separate copies so adding V2 does not change V1's frozen source digest.
Offline parity tests compare the plans and requests across versions.

## Run the one-call setup check first

Update the existing checkout:

```bash
git fetch origin
git merge --no-edit origin/main
```

Keep `MISTRAL_API_KEY` exported in this terminal. Use a new directory:

```bash
python3 -m exception_mistral_prefix_v2 prepare --config configs/mistral_prefix_v2.json --output runs/mistral-prefix-v2-001
caffeinate -i python3 -m exception_mistral_prefix_v2 run --config configs/mistral_prefix_v2.json --output runs/mistral-prefix-v2-001 --max-calls 1
```

Inspect the output before any research-case collection. A passing setup should
show `valid_answers: 1`, capability status `pass`, and `stopped: call_limit`.
If it fails, preserve the new run and inspect its saved first response:

```bash
python3 -m json.tool runs/mistral-prefix-v2-001/attempts/000001.json
```

After a pass, the unchanged runner can resume with an explicit call budget;
use `--resume`, and use `--retry-errors` only after transport errors. A returned
invalid response remains terminal. Do not mix V1 and V2 output directories.
