"""Content identities include code, bundled data, and explicit protocol/config files."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def content_digest(value):
    """Canonical JSON SHA-256, compatible with exception_pilot.core.digest."""
    content = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                         allow_nan=False)
    return hashlib.sha256(content.encode()).hexdigest()


def source_digest(root, study_package, extra_paths=()):
    """Hash study code/data plus execution dependencies and declared extra inputs.

    ``study_package`` is a repository-relative directory (or an absolute path in
    the repository). All its .py/.json/.md/.txt files are included recursively.
    Add protocol files, config examples, snapshots, and any other imported source
    modules in ``extra_paths``. Explicit directories include every regular file
    except __pycache__, .git and .pyc files. Missing paths are errors.
    """
    root = Path(root).resolve()

    def inside(path):
        path = Path(path)
        resolved = (path if path.is_absolute() else root / path).resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            raise ValueError("Frozen source paths must be inside the repository") from None
        if not resolved.exists():
            raise ValueError(f"Frozen source file is missing: {resolved.relative_to(root)}")
        return resolved

    files = set()

    def add(path, suffixes=None):
        path = inside(path)
        candidates = path.rglob("*") if path.is_dir() else [path]
        for candidate in candidates:
            if any(p in ("__pycache__", ".git") for p in candidate.parts):
                continue
            if candidate.is_file() and candidate.suffix != ".pyc":
                checked = inside(candidate)
                if suffixes is None or checked.suffix in suffixes:
                    files.add(checked)

    add(study_package, {".py", ".json", ".md", ".txt"})
    add("exception_study_support", {".py"})
    for relative in (
        "exception_columns/__init__.py", "exception_columns/provider.py",
        "exception_pilot/__init__.py", "exception_pilot/core.py",
        "exception_pilot/storage.py", "exception_pilot/provider.py",
        "exception_mistral_map_v3/__init__.py", "exception_mistral_map_v3/parser.py",
    ):
        add(relative)
    for extra in extra_paths:
        add(extra)
    manifest = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(files)}
    return content_digest(manifest)
