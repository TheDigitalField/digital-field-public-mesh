#!/usr/bin/env python3
"""Deterministic status, privacy, integrity, and scaffold tools for the Observatory."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path


IGNORED_NAMES = {"CHECKSUMS.sha256", ".DS_Store"}
IGNORED_SUFFIXES = {".zip", ".pyc"}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".csv", ".txt", ".py"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ABSOLUTE_PATH_PATTERNS = (
    "/" + "Users" + "/",
    "/" + "home" + "/",
    "file:" + "//",
    "C:" + "\\Users\\",
)


def package_root(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())
    candidates.extend([Path(__file__).resolve().parents[3], Path.cwd().resolve()])
    for candidate in candidates:
        if (candidate / "VERSION.json").is_file() and (candidate / "registry" / "modules.json").is_file():
            return candidate
    raise SystemExit("Could not locate an Observatory root; pass --root PATH.")


def tracked_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.name in IGNORED_NAMES or path.suffix in IGNORED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cmd_status(root: Path) -> int:
    version = json.loads((root / "VERSION.json").read_text(encoding="utf-8"))
    registry = json.loads((root / "registry" / "modules.json").read_text(encoding="utf-8"))
    observations = list((root / "observations").glob("[0-9][0-9][0-9][0-9]-*.md"))
    ledger = (root / "transformations" / "LEDGER.md").read_text(encoding="utf-8")
    transformations = len(re.findall(r"^## DF-T\d{4}", ledger, flags=re.MULTILINE))
    atlas_works = sum(
        len(re.findall(r"^## (?:Carta|Chart) \d{4}", path.read_text(encoding="utf-8"), flags=re.MULTILINE))
        for path in (root / "atlas").glob("ATLAS.*.md")
    )
    payload = {
        "title": version["title"],
        "version": version["version"],
        "status": version["status"],
        "modules": {module["name"]: module["status"] for module in registry["modules"]},
        "observation_count": len(observations),
        "transformation_count": transformations,
        "atlas_language_entries": atlas_works,
        "checksum_manifest": (root / "CHECKSUMS.sha256").is_file(),
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_seal(root: Path) -> int:
    lines = [f"{sha256(path)}  {path.relative_to(root).as_posix()}" for path in tracked_files(root)]
    target = root / "CHECKSUMS.sha256"
    temporary = root / ".CHECKSUMS.sha256.tmp"
    temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(f"Sealed {len(lines)} files in {target.name}.")
    return 0


def cmd_verify(root: Path) -> int:
    manifest = root / "CHECKSUMS.sha256"
    if not manifest.is_file():
        print("CHECKSUMS.sha256 is missing.", file=sys.stderr)
        return 1
    expected: dict[str, str] = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError:
            print(f"Malformed checksum line {number}.", file=sys.stderr)
            return 1
        expected[relative] = digest
    actual = {path.relative_to(root).as_posix(): path for path in tracked_files(root)}
    failures = []
    for relative, digest in expected.items():
        path = actual.get(relative)
        if path is None:
            failures.append(f"missing: {relative}")
        elif sha256(path) != digest:
            failures.append(f"changed: {relative}")
    for relative in sorted(set(actual) - set(expected)):
        failures.append(f"unlisted: {relative}")
    if failures:
        print("Integrity verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Verified {len(expected)} files.")
    return 0


def cmd_audit(root: Path) -> int:
    findings = []
    for path in tracked_files(root):
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(root).as_posix()
        for marker in ABSOLUTE_PATH_PATTERNS:
            if marker in text:
                findings.append(f"{relative}: absolute-path marker {marker!r}")
        for match in EMAIL_RE.finditer(text):
            findings.append(f"{relative}: possible email {match.group(0)!r}")
    if findings:
        print("Public-scope audit found possible identifying metadata:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print(f"Public-scope audit passed across {len(tracked_files(root))} files.")
    return 0


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "observation"


def cmd_new_observation(root: Path, title: str) -> int:
    existing = sorted((root / "observations").glob("[0-9][0-9][0-9][0-9]-*.md"))
    next_id = int(existing[-1].name[:4]) + 1 if existing else 1
    target = root / "observations" / f"{next_id:04d}-{slugify(title)}.md"
    if target.exists():
        print(f"Refusing to overwrite {target}.", file=sys.stderr)
        return 1
    template = (root / "templates" / "OBSERVATION.md").read_text(encoding="utf-8")
    template = template.replace("Observation NNNN — Title", f"Observation {next_id:04d} — {title}", 1)
    template = template.replace("YYYY-MM-DD", dt.date.today().isoformat(), 1)
    target.write_text(template, encoding="utf-8")
    print(target.relative_to(root).as_posix())
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("command", choices=("status", "seal", "verify", "audit", "new-observation"))
    result.add_argument("--root", help="Path to the Digital Field Observatory root")
    result.add_argument("--title", help="Title for new-observation")
    return result


def main() -> int:
    args = parser().parse_args()
    root = package_root(args.root)
    if args.command == "status":
        return cmd_status(root)
    if args.command == "seal":
        return cmd_seal(root)
    if args.command == "verify":
        return cmd_verify(root)
    if args.command == "audit":
        return cmd_audit(root)
    if args.command == "new-observation":
        if not args.title:
            raise SystemExit("new-observation requires --title.")
        return cmd_new_observation(root, args.title)
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
