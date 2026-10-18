# Exact archive parts

These are ordered binary pieces of `study2-v5-traces-for-audit.tar.gz`. All pieces except the final piece are exactly 6 MiB. From the repository root, reassemble and verify with:

```bash
cat results/archives/study2-v5-traces-for-audit.tar.gz.parts/part-000 results/archives/study2-v5-traces-for-audit.tar.gz.parts/part-001 results/archives/study2-v5-traces-for-audit.tar.gz.parts/part-002 results/archives/study2-v5-traces-for-audit.tar.gz.parts/part-003 > results/archives/study2-v5-traces-for-audit.tar.gz
printf '642fd12ae4a70be3063ff5605335fdc8aade766dde7df82dd959eb89316865da  results/archives/study2-v5-traces-for-audit.tar.gz\n' | sha256sum -c -
```

The full archive is 23930797 bytes. `results/manifest.json` records the ordered pieces and their individual hashes.
