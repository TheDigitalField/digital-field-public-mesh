#!/usr/bin/env python3
"""Verify an immutable Public Mesh ancestor beside mutable Living Memory successors."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import subprocess
import sys


LEGACY_WRAPPER = ".github/workflows/verify.yml"
SUCCESSOR_PATHS = (
    ".github/workflows/living-memory-node.yml",
    LEGACY_WRAPPER,
    "living-memory/",
    "living-state/",
    "successors/",
)
IGNORED_SUFFIXES = {".zip", ".car", ".pyc"}
ROOT_INTEGRITY = {"CHECKSUMS.sha256", "integrity/MERKLE_ROOT.json"}


def file_digest(path: pathlib.Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def leaf_hash(relative: str, digest_hex: str) -> bytes:
    return hashlib.sha256(b"leaf\0" + relative.encode() + b"\0" + bytes.fromhex(digest_hex)).digest()


def merkle_root(entries: list[tuple[str, str]]) -> str:
    nodes = [leaf_hash(relative, digest_hex) for relative, digest_hex in entries]
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [hashlib.sha256(b"node\0" + nodes[index] + nodes[index + 1]).digest() for index in range(0, len(nodes), 2)]
    return nodes[0].hex() if nodes else hashlib.sha256(b"empty\0").hexdigest()


def run(root: pathlib.Path, *command: str) -> None:
    completed = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=120)
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout).strip())


def verify_successor_bundles(root: pathlib.Path) -> dict:
    successor_root = root / "successors"
    if not successor_root.exists():
        return {"bundles": 0, "files": 0}
    manifests = sorted(successor_root.rglob("CHECKSUMS.sha256"))
    if not manifests:
        raise RuntimeError("successor directory has no checksum manifest")
    verified_files = 0
    for manifest in manifests:
        bundle = manifest.parent
        listed = {}
        for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                digest_hex, relative = line.split("  ", 1)
            except ValueError as exc:
                raise RuntimeError(f"malformed successor manifest line {number}: {manifest}") from exc
            candidate = pathlib.PurePosixPath(relative)
            if candidate.is_absolute() or ".." in candidate.parts or relative == "CHECKSUMS.sha256":
                raise RuntimeError(f"unsafe successor manifest path: {relative}")
            listed[relative] = digest_hex
        actual = {
            path.relative_to(bundle).as_posix(): file_digest(path)
            for path in bundle.rglob("*")
            if path.is_file() and path.name != "CHECKSUMS.sha256" and path.name != ".DS_Store"
        }
        if set(actual) != set(listed):
            raise RuntimeError(f"successor bundle file set mismatch: {bundle.relative_to(root)}")
        changed = sorted(relative for relative in listed if actual[relative] != listed[relative])
        if changed:
            raise RuntimeError(f"changed successor bundle file: {changed[0]}")
        verified_files += len(actual)
    return {"bundles": len(manifests), "files": verified_files}


def verify(root: pathlib.Path) -> dict:
    failures = []
    entries = []
    for line in (root / "CHECKSUMS.sha256").read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest_hex, relative = line.split("  ", 1)
            entries.append((relative, digest_hex))
    expected = dict(entries)
    for relative, digest_hex in entries:
        if relative == LEGACY_WRAPPER:
            continue
        path = root / relative
        if not path.is_file():
            failures.append(f"missing immutable ancestor file: {relative}")
        elif file_digest(path) != digest_hex:
            failures.append(f"changed immutable ancestor file: {relative}")
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if relative in ROOT_INTEGRITY or path.name == ".DS_Store" or path.suffix in IGNORED_SUFFIXES or path.name.endswith(".release.json"):
            continue
        if relative in expected:
            continue
        if relative in SUCCESSOR_PATHS or any(relative.startswith(prefix) for prefix in SUCCESSOR_PATHS if prefix.endswith("/")):
            continue
        failures.append(f"unrecognized path outside successor boundary: {relative}")
    merkle = json.loads((root / "integrity" / "MERKLE_ROOT.json").read_text(encoding="utf-8"))
    if merkle.get("file_count") != len(entries) or merkle.get("root") != merkle_root(entries):
        failures.append("immutable ancestor Merkle root mismatch")
    current_wrapper = (root / LEGACY_WRAPPER).read_text(encoding="utf-8")
    if "contents: read" not in current_wrapper or "contents: write" in current_wrapper or "secrets." in current_wrapper:
        failures.append("successor verification wrapper exceeds read-only authority")
    living_workflow = root / ".github" / "workflows" / "living-memory-node.yml"
    packaged_workflow = root / "living-memory" / "deployment" / "github-actions" / "living-memory-node.yml"
    if not living_workflow.is_file() or living_workflow.read_bytes() != packaged_workflow.read_bytes():
        failures.append("deployed Living Memory workflow differs from sealed source")
    if failures:
        raise RuntimeError("\n".join(failures))
    run(root, sys.executable, "living-memory/scripts/living_memory.py", "verify")
    run(root, sys.executable, "living-memory/scripts/living_memory.py", "audit")
    run(root, sys.executable, "living-memory/scripts/audit_external_node.py")
    run(root, sys.executable, "living-memory/scripts/substrate_node.py", "verify-state", "--state-root", "living-state")
    run(root, sys.executable, "scripts/mesh.py", "verify-ancestors")
    run(root, sys.executable, "scripts/mesh.py", "simulate-failures")
    successors = verify_successor_bundles(root)
    return {
        "status": "verified",
        "immutable_ancestor_files": len(entries),
        "legacy_wrapper_excluded_by_explicit_successor_boundary": LEGACY_WRAPPER,
        "living_memory_manifest_sha256": file_digest(root / "living-memory" / "CHECKSUMS.sha256"),
        "living_state_verified": True,
        "private_evidence_embedded": False,
        "successor_bundles_verified": successors["bundles"],
        "successor_files_verified": successors["files"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    args = parser.parse_args()
    try:
        print(json.dumps(verify(args.root.resolve()), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
