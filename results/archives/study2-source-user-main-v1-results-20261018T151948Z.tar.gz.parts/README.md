# Exact archive parts

These are ordered binary pieces of `study2-source-user-main-v1-results-20261018T151948Z.tar.gz`. All pieces except the final piece are exactly 6 MiB. From the repository root, reassemble and verify with:

```bash
cat results/archives/study2-source-user-main-v1-results-20261018T151948Z.tar.gz.parts/part-000 results/archives/study2-source-user-main-v1-results-20261018T151948Z.tar.gz.parts/part-001 results/archives/study2-source-user-main-v1-results-20261018T151948Z.tar.gz.parts/part-002 > results/archives/study2-source-user-main-v1-results-20261018T151948Z.tar.gz
printf '27f6121c7fd6e980fdd51299a0cafeab1e7857be1bce510a83a3455f69e3d192  results/archives/study2-source-user-main-v1-results-20261018T151948Z.tar.gz\n' | sha256sum -c -
```

The full archive is 14931584 bytes. `results/manifest.json` records the ordered pieces and their individual hashes.
