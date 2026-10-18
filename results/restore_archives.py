#!/usr/bin/env python3
"""Optionally reconstruct split result archives, never overwriting another file."""

import os
from pathlib import Path
import sys
import tempfile

from verify_results import (
    VerificationError, concatenate_parts, read_manifest, result_path, verify_file,
)


def restore(entry):
    destination = result_path(entry["path"])
    if destination.exists():
        verify_file(destination, entry)
        return "already present and verified"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w+b", prefix=".restore-",
                                         dir=destination.parent, delete=False) as handle:
            temporary = Path(handle.name)
            concatenate_parts(entry, handle)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic creation using a same-filesystem hard link cannot overwrite a
        # target that another process creates while verification is in progress.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            verify_file(destination, entry)
            return "already present and verified"
        return "restored and verified"
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    if len(sys.argv) != 1:
        print("Usage: python3 results/restore_archives.py", file=sys.stderr)
        return 2
    try:
        manifest = read_manifest()
        entries = [entry for entry in manifest["archives"] if entry.get("storage")]
        for entry in entries:
            print(f"{entry['path']}: {restore(entry)}")
        if not entries:
            print("No split archives to restore.")
        return 0
    except (VerificationError, OSError, ValueError, KeyError, TypeError) as error:
        print(f"Restoration stopped; existing files were preserved: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
