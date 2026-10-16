# Residual v1.1 frozen request index

Plan hash: `739a394f47743b3ba1bf562cf9f771a13fb2d5198085e70e4e1ef8a6ccd16c8d`.

These are 23 planned requests, all unattempted. Complete payloads, source bindings,
prior-evidence hashes, and per-candidate reasons are in `residual-request-plan.json`.
No J3 calls or automatic retries. The four marked smoke slots are part of the 23.

| # | Request ID | Judge / provider | Purpose | Candidates | Trajectories | Smoke |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | `r-5903f28b29861230ab7f69ac` | J1 / openai | Candidate verification | 6 | 1 | yes |
| 2 | `r-16647c451a37c45054f288a6` | J1 / openai | Candidate verification | 6 | 1 | yes |
| 3 | `r-e376fc85fe255317f6b6022d` | J1 / openai | Candidate verification | 6 | 1 |  |
| 4 | `r-36fb9453deb7d37320ad3961` | J1 / openai | Candidate verification | 6 | 1 |  |
| 5 | `r-0e2bcd7561495a36c30fd0d8` | J1 / openai | Candidate verification | 6 | 3 |  |
| 6 | `r-66af0c83f77c6cf281e0dfd7` | J1 / openai | Candidate verification | 6 | 1 |  |
| 7 | `r-4d5b6d643b47ee2c6832933c` | J1 / openai | Candidate verification | 6 | 1 |  |
| 8 | `r-9d2e94d340b505ba8b9153f5` | J1 / openai | Candidate verification | 6 | 2 |  |
| 9 | `r-5790036eb0b03f407f2b5c26` | J1 / openai | Candidate verification | 5 | 1 |  |
| 10 | `r-7e2ad92f2a382aadc0782993` | J1 / openai | Candidate verification | 5 | 1 |  |
| 11 | `r-6b98933d4742160294f920ac` | J1 / openai | Candidate verification | 5 | 2 |  |
| 12 | `r-1a5d5e240d61f1d768587bc2` | J2 / anthropic | Candidate verification | 6 | 3 | yes |
| 13 | `r-e88a28a9db08e7218e384501` | J2 / anthropic | Candidate verification | 5 | 2 |  |
| 14 | `r-b651dc9fe80df84b036c171a` | J2 / anthropic | Candidate verification | 5 | 2 |  |
| 15 | `r-f4536aa16fec0a30ae99cd40` | J1 / openai | Full-text coverage | 0 | 1 | yes |
| 16 | `r-22e703cfb2fb76c78a5b1178` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 17 | `r-25410c4c45b60eff88942889` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 18 | `r-b3b653bc32fca864fca15c20` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 19 | `r-e46579547f8d812c723369d8` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 20 | `r-70c53bf882a93e7dea005e71` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 21 | `r-8e88dd6d655bb8aa02aeee65` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 22 | `r-33fe6154c98eea74643ad339` | J1 / openai | Full-text coverage | 0 | 1 |  |
| 23 | `r-b93a442c028cd3d83c423c28` | J1 / openai | Full-text coverage | 0 | 1 |  |

## Deferred A candidates

All remain uncertain in the retained population. They receive no new candidate
verification request because the frozen text lacks the required recorded-value
witness. Coverage reviews remain scheduled. Exact source text, spans, missing
providers, and prior operation references appear in `real-source-offline-acceptance.json`.

| Task | Candidate | Span | Missing providers |
| --- | --- | --- | --- |
| `staged-v5-000/v0/original/visible` | `s-4ba7b2a2ebddd34dfb27:A` | [1630, 1687] | openai, anthropic |
| `staged-v5-000/v0/original/visible` | `s-13b31094d53fb7f10cea:A` | [2072, 2200] | openai, anthropic |
| `staged-v5-000/v1/lookup/visible` | `s-728c39cff03b0b6b77d0:A` | [127, 211] | openai, anthropic |
| `staged-v5-001/v1/lookup/visible` | `s-fe07ec5d810fadf6cc92:A` | [0, 104] | openai |
| `staged-v5-001/v1/lookup/visible` | `s-7c0d13a2c0c9d58aa116:A` | [178, 283] | openai |
| `staged-v5-001/v0/original/visible` | `s-1fa78c5eb4faccd5d155:A` | [476, 575] | openai |
| `staged-v5-001/v0/original/visible` | `s-e55ed370bb557facb999:A` | [1398, 1445] | openai |
| `staged-v5-001/v0/lookup/visible` | `s-a419f597bebfd750ec07:A` | [0, 150] | openai |
| `staged-v5-002/v1/original/visible` | `s-ef49cef95a58a8e5042c:A` | [0, 285] | openai |
| `staged-v5-002/v1/original/visible` | `s-b08b0343d13aa1dd750d:A` | [328, 439] | openai |
| `staged-v5-002/v1/original/visible` | `s-320355bb0b833716fb03:A` | [441, 540] | openai |
| `staged-v5-002/v1/original/visible` | `s-e30914c1de28825bc9bc:A` | [1375, 1390] | openai, anthropic |
| `staged-v5-002/v1/original/visible` | `s-5d171ea2a8a996390a14:A` | [1776, 1855] | openai |
| `staged-v5-002/v1/original/visible` | `s-23500c8d4581bf4681f2:A` | [4028, 4074] | openai, anthropic |
| `staged-v5-002/v1/original/visible` | `s-6e53213f88b9827c36f9:A` | [4122, 4217] | openai, anthropic |
| `staged-v5-002/v1/original/visible` | `s-29ff22bb39a9f47e97f7:A` | [4242, 4354] | openai, anthropic |
| `staged-v5-002/v0/lookup/visible` | `s-5baaca595fd27f85a0e7:A` | [235, 310] | openai, anthropic |
| `staged-v5-002/v1/lookup/visible` | `s-2069e0588dfdfb752980:A` | [108, 192] | anthropic |
| `staged-v5-002/v0/original/visible` | `s-c6f161eb2dd493ba7797:A` | [1384, 1452] | openai, anthropic |
| `staged-v5-003/v1/original/visible` | `s-82875d5aaba8d7322e7e:A` | [325, 434] | openai |
| `staged-v5-003/v1/original/visible` | `s-c2f5663b407da4179f3a:A` | [436, 535] | openai |
| `staged-v5-003/v1/original/visible` | `s-bcf1e76f017583e5c8b6:A` | [1698, 1797] | openai |
| `staged-v5-003/v1/original/visible` | `s-d51fa1c32d50078b8918:A` | [2981, 3107] | openai |
| `staged-v5-003/v0/original/visible` | `s-20a47cfef1c9300f2b90:A` | [0, 282] | openai |
| `staged-v5-003/v0/original/visible` | `s-82875d5aaba8d7322e7e:A` | [325, 434] | openai |
| `staged-v5-003/v0/original/visible` | `s-c2f5663b407da4179f3a:A` | [436, 535] | openai |
| `staged-v5-003/v0/original/visible` | `s-2e2701c0d4aa16390a05:A` | [1694, 1766] | openai |
| `staged-v5-003/v1/lookup/visible` | `s-713bdf8e989699a47a3e:A` | [0, 104] | openai |
| `staged-v5-003/v1/lookup/visible` | `s-7c0d13a2c0c9d58aa116:A` | [178, 283] | openai, anthropic |
| `staged-v5-003/v0/lookup/visible` | `s-7c0d13a2c0c9d58aa116:A` | [178, 283] | openai |
