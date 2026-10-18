# Branch artifact audit — October 18, 2026

This is a results/documentation consolidation, not a merge of experimental implementations.
The [inventory](inventory.json) records all 18 published branch tips, original paths,
blob IDs and SHA256 comparisons. 507 distinct branch files absent as loose main files
were already preserved in archive members; they were not duplicated. Another 161
branch audit/preview/documentation files are copied byte-for-byte here. Two old
catalog versions remain in Git history. Five context documents accompany the copies.

## What these files represent

- `audits/study2-validation/` and `docs/study2-validation/`: the historical **failed** Qwen v3 validation audit.
- `audits/study2-v4/`, `study2-v5*`, `study2-residual*`, `study2-replication*`, and `study2-source-*`: saved implementation tests, reviews, salvage analyses, and frozen offline previews. A mock test or planned request is not a live observation. Retain each file's original status and provenance.
- `audits/study2-native-thinking-*`: three preserved versions of the **unexecuted** native-thinking draft, budget review, and shortcut/recovery audit. No native-thinking Qwen results exist in this collection; the main generation budget remains pending pilot review.
- `docs/study2-review/` and `previews/`: historical implementation checks and mock/unstarted previews.
- `context/`: unchanged context documents. Run commands and relative links belong to their source branches, not this archival folder. Do not run an experiment from the main archive layout.

The [main results index](../../README.md) links the actual live exports separately.
Historical helper scripts are inert copies retained for provenance; experimental
code remains on its existing branches. The copied documents retain original relative
paths; use the inventory's source branch, commit, and path to locate dependencies.
