# Diagnose a persistent Mistral HTTP error

If a single delayed retry still returns `HTTP 429`, capture the provider's
specific error before spending more attempts or changing account settings.
The original runner records the HTTP status but discards the error body.

From the same terminal with `MISTRAL_API_KEY` exported:

```bash
git fetch origin
git merge --no-edit origin/main
caffeinate -i python3 mistral_diagnostic.py --config configs/mistral_prefix.json --output runs/mistral-prefix-001
```

The diagnostic attempts **at most one next scheduled request** in the existing
run, with the original runner's `--resume --retry-errors` behavior. It does not
make a separate probe or automatically retry. If the request succeeds, its full
response is saved and scored normally. If it fails with an HTTP error, the
terminal output and the new attempt journal include recognized error fields
and `Retry-After` when supplied. The active API key is redacted. Raw error bodies
and other headers are omitted. Non-JSON, oversized, or unreadable error bodies
produce a short status instead.

This optional observer delegates request construction, successful response
normalization, scoring, gates, and attempt limits to the unchanged experiment
code. It is outside the hashed experiment packages, so the existing saved plan
continues to validate. Previous attempts are retained, and the diagnostic
attempt counts toward the same cumulative cap of 89. Do not delete the old run,
edit its plan hash, change the model, or restart after a returned invalid answer.

The helper is for a single CLI process, not concurrent use from multiple threads.
Use the normal runner to continue once the account issue is resolved.

Mistral documents request-per-second, token-per-minute, and monthly token
limits across an organization. Displayed throughput ceilings alone do not show
remaining monthly quota. Check [Limits](https://admin.mistral.ai/plateforme/limits)
and the specific error. A repeated 429 alone does not establish that payment is
required. Adding prepaid credits alone does not increase the usage tier.

Official references:

- [Mistral error fields and retry guidance](https://docs.mistral.ai/resources/error-glossary)
- [Rate limits and usage tiers](https://help.mistral.ai/en/articles/698531-why-am-i-hitting-api-rate-limits-and-how-do-i-increase-them)
