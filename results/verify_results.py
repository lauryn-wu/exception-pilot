#!/usr/bin/env python3
"""Verify stored results and archive members without extracting any archive."""

import contextlib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import tarfile
import tempfile
import zipfile


CHUNK_SIZE = 1024 * 1024
RESULTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = RESULTS_DIR.parent


class VerificationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=unique_object)


def safe_path(root, name):
    require(isinstance(name, str) and bool(name), "Empty or invalid file path")
    parts = name.split("/")
    require(not name.startswith("/") and "\\" not in name,
            f"Not a relative POSIX path: {name}")
    require(all(part not in ("", ".", "..") for part in parts),
            f"Noncanonical file path: {name}")
    require(not re.match(r"^[A-Za-z]:", name), f"Drive-qualified path: {name}")
    path = root
    for part in parts:
        path = path / part
        require(not path.is_symlink(), f"Symlinks are not accepted: {path}")
    return path


def result_path(name):
    require(isinstance(name, str) and name.startswith("results/"),
            f"Manifest path must begin results/: {name}")
    return safe_path(REPO_ROOT, name)


def validate_metadata(expected, label):
    require(isinstance(expected, dict), f"Invalid metadata: {label}")
    require(type(expected.get("bytes")) is int and expected["bytes"] >= 0,
            f"Invalid byte count: {label}")
    require(isinstance(expected.get("sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", expected["sha256"]),
            f"Invalid SHA256: {label}")


def digest_stream(handle, output=None, blob_size=None):
    sha256 = hashlib.sha256()
    blob = hashlib.sha1() if blob_size is not None else None
    if blob is not None:
        blob.update(f"blob {blob_size}\0".encode("ascii"))
    size = 0
    while True:
        chunk = handle.read(CHUNK_SIZE)
        if not chunk:
            break
        size += len(chunk)
        sha256.update(chunk)
        if blob is not None:
            blob.update(chunk)
        if output is not None:
            output.write(chunk)
    return {"bytes": size, "sha256": sha256.hexdigest(),
            "git_blob_sha": blob.hexdigest() if blob is not None else None}


def check_digest(actual, expected, label):
    validate_metadata(expected, label)
    require(actual["bytes"] == expected["bytes"], f"Byte count mismatch: {label}")
    require(actual["sha256"] == expected["sha256"], f"SHA256 mismatch: {label}")
    if "git_blob_sha" in expected:
        require(actual.get("git_blob_sha") == expected["git_blob_sha"],
                f"Git blob SHA mismatch: {label}")


def verify_file(path, expected):
    validate_metadata(expected, str(path))
    require(path.is_file() and not path.is_symlink(), f"Missing regular file: {path}")
    with path.open("rb") as handle:
        actual = digest_stream(handle, blob_size=expected["bytes"]
                               if "git_blob_sha" in expected else None)
    check_digest(actual, expected, str(path))


def read_manifest():
    manifest = read_json(RESULTS_DIR / "manifest.json")
    require(isinstance(manifest, dict) and isinstance(manifest.get("archives"), list),
            "manifest.json must contain an archives list")
    logical_paths, stored_paths = set(), set()
    for entry in manifest["archives"]:
        validate_metadata(entry, "archive entry")
        name = entry.get("path")
        result_path(name)
        require(name not in logical_paths, f"Duplicate archive path: {name}")
        logical_paths.add(name)
        result_path(entry.get("member_manifest"))
        storage = entry.get("storage")
        if storage is None:
            physical = [name]
        else:
            require(storage.get("format") == "concatenated-parts",
                    f"Unknown storage format: {name}")
            parts = storage.get("parts")
            require(isinstance(parts, list) and bool(parts), f"No parts: {name}")
            physical = []
            for part in parts:
                validate_metadata(part, f"part of {name}")
                result_path(part.get("path"))
                physical.append(part["path"])
            require(sum(part["bytes"] for part in parts) == entry["bytes"],
                    f"Part sizes do not sum to archive size: {name}")
        for path in physical:
            require(path not in stored_paths, f"Duplicate stored path: {path}")
            stored_paths.add(path)
    split_names = {e["path"] for e in manifest["archives"] if e.get("storage")}
    require(not split_names.intersection(stored_paths),
            "A split archive logical path is also used as stored content")
    return manifest


def concatenate_parts(entry, output):
    """Write parts in manifest order, checking each part and the combined bytes."""
    for part in entry["storage"]["parts"]:
        path = result_path(part["path"])
        require(path.is_file(), f"Missing archive part: {path}")
        with path.open("rb") as handle:
            actual = digest_stream(handle, output, part["bytes"]
                                   if "git_blob_sha" in part else None)
        check_digest(actual, part, part["path"])
    output.flush()
    output.seek(0)
    check_digest(digest_stream(output, blob_size=entry["bytes"]
                               if "git_blob_sha" in entry else None),
                 entry, entry["path"])
    output.seek(0)


@contextlib.contextmanager
def archive_stream(entry):
    if entry.get("storage") is not None:
        # This scratch file is deleted on close; nothing is extracted or restored.
        with tempfile.TemporaryFile() as handle:
            concatenate_parts(entry, handle)
            restored = result_path(entry["path"])
            if restored.exists():
                verify_file(restored, entry)
            yield handle
    else:
        path = result_path(entry["path"])
        verify_file(path, entry)
        with path.open("rb") as handle:
            yield handle


def archive_name_key(name):
    require(isinstance(name, str) and bool(name), "Empty archive member name")
    require(not name.startswith("/") and "\\" not in name
            and not re.match(r"^[A-Za-z]:", name), f"Unsafe archive member: {name}")
    require(".." not in name.split("/"), f"Parent traversal in archive member: {name}")
    return str(PurePosixPath(name))


def verify_members(entry, handle):
    expected = read_json(result_path(entry["member_manifest"]))
    require(isinstance(expected, dict), f"Invalid member manifest: {entry['path']}")
    for name, metadata in expected.items():
        archive_name_key(name)
        validate_metadata(metadata, name)
    seen, actual_names = set(), set()

    def start_member(name):
        key = archive_name_key(name)
        require(key not in seen, f"Duplicate archive member path: {name}")
        seen.add(key)

    def check_member(name, stream):
        require(name in expected, f"Unlisted archive member: {name}")
        actual_names.add(name)
        metadata = expected[name]
        check_digest(digest_stream(stream, blob_size=metadata["bytes"]
                                   if "git_blob_sha" in metadata else None),
                     metadata, name)

    if entry["path"].lower().endswith(".zip"):
        with zipfile.ZipFile(handle) as archive:
            for member in archive.infolist():
                start_member(member.filename)
                mode = member.external_attr >> 16
                if member.is_dir():
                    require(not stat.S_ISLNK(mode), f"ZIP symlink: {member.filename}")
                    continue
                require(stat.S_IFMT(mode) in (0, stat.S_IFREG),
                        f"ZIP nonregular member: {member.filename}")
                with archive.open(member) as stream:
                    check_member(member.filename, stream)
    else:
        with tarfile.open(fileobj=handle, mode="r:*") as archive:
            for member in archive:
                start_member(member.name)
                if member.isdir():
                    continue
                require(member.isfile(), f"TAR nonregular member: {member.name}")
                stream = archive.extractfile(member)
                require(stream is not None, f"Unreadable archive member: {member.name}")
                with stream:
                    check_member(member.name, stream)
    missing = set(expected) - actual_names
    require(not missing, f"Missing archive members: {sorted(missing)}")
    if "members" in entry:
        require(entry["members"] == len(actual_names),
                f"Archive member count mismatch: {entry['path']}")
    return len(actual_names)


def verify_checksums():
    seen = set()
    for number, line in enumerate((RESULTS_DIR / "SHA256SUMS").read_text().splitlines(), 1):
        if not line:
            continue
        match = re.fullmatch(r"([0-9a-f]{64}) [ *](.+)", line)
        require(match is not None, f"Malformed SHA256SUMS line {number}")
        digest, name = match.groups()
        require(name not in seen, f"Duplicate checksum path: {name}")
        seen.add(name)
        path = safe_path(RESULTS_DIR, name)
        require(path.is_file(), f"Missing checksum-listed file: {path}")
        with path.open("rb") as handle:
            actual = digest_stream(handle)
        require(actual["sha256"] == digest, f"SHA256SUMS mismatch: {name}")
    require(bool(seen), "SHA256SUMS is empty")
    return len(seen)


def main():
    if len(sys.argv) != 1:
        print("Usage: python3 results/verify_results.py", file=sys.stderr)
        return 2
    try:
        files = verify_checksums()
        manifest = read_manifest()
        members = 0
        for entry in manifest["archives"]:
            with archive_stream(entry) as handle:
                members += verify_members(entry, handle)
        print(f"Verified {files} checksum-listed files, "
              f"{len(manifest['archives'])} archives, and {members} regular archive members.")
        return 0
    except (VerificationError, OSError, ValueError, KeyError, TypeError,
            tarfile.TarError, zipfile.BadZipFile, RuntimeError) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
