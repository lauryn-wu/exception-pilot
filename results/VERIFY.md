# Verify the preserved results

From the repository root, run:

```bash
python3 results/verify_results.py
```

This uses only Python's standard library. It checks `results/SHA256SUMS`, each
archive's original byte count and SHA256, and every regular archive member
against its member manifest. Directory entries are not counted as files.
Duplicate paths, unlisted or missing members, links, special entries, and
hash mismatches fail verification. Archives are read without extracting them.

Two large original `.tar.gz` files are stored as ordered binary parts. Their
logical original paths and whole-file hashes remain in `manifest.json`; the
`storage.parts` records identify the stored pieces in concatenation order.
Verification checks each part and temporarily assembles the original byte
stream to check the whole archive and its members. It does not require the
original `.tar.gz` files to be reconstructed in the checkout.

To optionally reconstruct those original files:

```bash
python3 results/restore_archives.py
```

The command checks every part and the complete reconstructed archive before
atomically creating the original path. An existing matching archive is checked
and skipped. An existing differing file causes an error and is preserved. The
parts remain in place. Reconstruction preserves the exact original archive
bytes; it neither reruns experiments nor repackages their contents.

Both scripts locate the results directory through their own file locations, so
they also work when called by absolute path from another working directory.
Verification is an integrity check, not a scientific replication or a signature
of who collected the results. Some older archives may contain copies of the
same underlying measurements; archive counts are not counts of independent
experiments.
