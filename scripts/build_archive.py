#!/usr/bin/env python3
"""Build and inspect a reproducible, metadata-minimized Public Mesh ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath


FIXED_TIME = (2026, 8, 12, 0, 0, 0)
IGNORED_NAMES = {".DS_Store"}
IGNORED_SUFFIXES = {".pyc", ".zip", ".car"}


def source_files(root: Path) -> list[Path]:
    return sorted(
        (
            path
            for path in root.rglob("*")
            if path.is_file()
            and ".git" not in path.parts
            and "__pycache__" not in path.parts
            and path.name not in IGNORED_NAMES
            and path.suffix not in IGNORED_SUFFIXES
            and not path.name.endswith(".release.json")
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(root: Path, output: Path) -> dict[str, object]:
    root = root.resolve()
    output = output.resolve()
    if root == output or root in output.parents:
        raise SystemExit("Output archive must be outside the package root.")
    entries = source_files(root)
    temporary = output.with_suffix(output.suffix + ".tmp")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source in entries:
            relative = PurePosixPath(root.name) / PurePosixPath(source.relative_to(root).as_posix())
            info = zipfile.ZipInfo(relative.as_posix(), date_time=FIXED_TIME)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            info.extra = b""
            info.comment = b""
            archive.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        archive.comment = b""
    temporary.replace(output)
    return {
        "archive": output.name,
        "file_entries": len(entries),
        "fixed_timestamp": "2026-08-12T00:00:00",
        "sha256": sha256(output),
        "result": "built",
    }


def inspect(archive_path: Path) -> dict[str, object]:
    findings: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        infos = archive.infolist()
        for info in infos:
            name = PurePosixPath(info.filename)
            if name.is_absolute() or ".." in name.parts:
                findings.append(f"unsafe path: {info.filename}")
            if info.date_time != FIXED_TIME:
                findings.append(f"variable timestamp: {info.filename}")
            if info.extra:
                findings.append(f"extra metadata: {info.filename}")
            if info.comment:
                findings.append(f"entry comment: {info.filename}")
        if archive.comment:
            findings.append("archive comment present")
    return {
        "file_entries": len(infos),
        "sha256": sha256(archive_path),
        "metadata_findings": findings,
        "result": "passed" if not findings else "failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("root")
    build_parser.add_argument("output")
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("archive")
    args = parser.parse_args()
    result = build(Path(args.root), Path(args.output)) if args.command == "build" else inspect(Path(args.archive))
    print(json.dumps(result, indent=2))
    return 0 if result["result"] in {"built", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
