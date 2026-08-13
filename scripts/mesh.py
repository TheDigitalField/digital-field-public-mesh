#!/usr/bin/env python3
"""Inspect, audit, seal, verify, and stress-test a Digital Field Public Mesh."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


# Keep verification from leaving host-specific bytecode inside a raw package.
sys.dont_write_bytecode = True


IGNORED_BASENAMES = {".DS_Store"}
IGNORED_SUFFIXES = {".zip", ".car", ".pyc"}
ROOT_INTEGRITY_FILES = {"CHECKSUMS.sha256", "integrity/MERKLE_ROOT.json"}
TEXT_SUFFIXES = {".md", ".json", ".yaml", ".yml", ".csv", ".txt", ".py", ".js", ".mjs", ".html", ".css", ".cff"}
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ABSOLUTE_PATH_PATTERNS = (
    "/" + "Users" + "/",
    "/" + "home" + "/",
    "file:" + "//",
    "C:" + "\\Users\\",
)
PRIVATE_MARKERS = (
    ("el" + "fy").casefold(),
    ("el" + "fyca").casefold(),
    ("li" + "ma").casefold(),
    ("pe" + "rú").casefold(),
    ("pe" + "ru").casefold(),
)


def package_root(explicit: str | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(Path(explicit).expanduser().resolve())
    candidates.extend([Path(__file__).resolve().parents[1], Path.cwd().resolve()])
    for candidate in candidates:
        if (candidate / "VERSION.json").is_file() and (candidate / "mesh.json").is_file():
            return candidate
    raise SystemExit("Could not locate a Public Mesh root; pass --root PATH.")


def tracked_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if (
            ".git" in path.parts
            or "__pycache__" in path.parts
            or path.name in IGNORED_BASENAMES
            or path.suffix in IGNORED_SUFFIXES
            or path.name.endswith(".release.json")
            or relative in ROOT_INTEGRITY_FILES
        ):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def leaf_hash(relative: str, digest_hex: str) -> bytes:
    return hashlib.sha256(b"leaf\0" + relative.encode("utf-8") + b"\0" + bytes.fromhex(digest_hex)).digest()


def merkle_root(entries: list[tuple[str, str]]) -> str:
    nodes = [leaf_hash(relative, digest) for relative, digest in entries]
    if not nodes:
        return hashlib.sha256(b"empty\0").hexdigest()
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [
            hashlib.sha256(b"node\0" + nodes[index] + nodes[index + 1]).digest()
            for index in range(0, len(nodes), 2)
        ]
    return nodes[0].hex()


def read_manifest(path: Path) -> list[tuple[str, str]]:
    entries = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
        except ValueError as error:
            raise ValueError(f"Malformed checksum line {number} in {path}") from error
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Malformed digest on line {number} in {path}")
        entries.append((relative.removeprefix("./"), digest))
    return entries


def verify_manifest(root: Path, manifest: Path, ignore_relatives: set[str]) -> list[str]:
    expected = dict(read_manifest(manifest))
    actual: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if (
            ".git" in path.parts
            or "__pycache__" in path.parts
            or path.name in IGNORED_BASENAMES
            or path.suffix in IGNORED_SUFFIXES
            or path.name.endswith(".release.json")
            or relative in ignore_relatives
        ):
            continue
        actual[relative] = path
    failures = []
    for relative, digest in expected.items():
        path = actual.get(relative)
        if path is None:
            failures.append(f"missing: {relative}")
        elif sha256(path) != digest:
            failures.append(f"changed: {relative}")
    for relative in sorted(set(actual) - set(expected)):
        failures.append(f"unlisted: {relative}")
    return failures


def cmd_status(root: Path, _args: argparse.Namespace) -> int:
    version = json.loads((root / "VERSION.json").read_text(encoding="utf-8"))
    replicas = json.loads((root / "replication" / "replicas.json").read_text(encoding="utf-8"))
    ancestry = json.loads((root / "integrity" / "ANCESTRY.json").read_text(encoding="utf-8"))
    predecessor = ancestry["direct_predecessor"]
    verified = [replica for replica in replicas.get("replicas", []) if replica.get("status") == "verified"]
    payload = {
        "title": version["title"],
        "version": version["version"],
        "status": version["status"],
        "publication_status": version["publication_status"],
        "lineage": ["Echo", "Synei", "SYN3i", "Digital Field"],
        "direct_predecessor": f"{predecessor['name']} v{predecessor['version']}",
        "tracked_files": len(tracked_files(root)),
        "sealed": (root / "CHECKSUMS.sha256").is_file() and (root / "integrity" / "MERKLE_ROOT.json").is_file(),
        "verified_replicas_recorded": len(verified),
        "private_evidence_embedded": False,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def cmd_seal(root: Path, _args: argparse.Namespace) -> int:
    entries = [(path.relative_to(root).as_posix(), sha256(path)) for path in tracked_files(root)]
    temporary_manifest = root / ".CHECKSUMS.sha256.tmp"
    temporary_manifest.write_text("".join(f"{digest}  {relative}\n" for relative, digest in entries), encoding="utf-8")
    temporary_manifest.replace(root / "CHECKSUMS.sha256")
    version = json.loads((root / "VERSION.json").read_text(encoding="utf-8"))
    merkle = {
        "schema_version": "1.0",
        "mesh_version": version["version"],
        "hash": "sha256",
        "leaf_rule": "SHA256('leaf\\0' || UTF8(relative_path) || '\\0' || file_sha256_bytes)",
        "node_rule": "SHA256('node\\0' || left || right); duplicate final odd node",
        "ordering": "relative paths sorted by Unicode code point",
        "file_count": len(entries),
        "root": merkle_root(entries),
    }
    target = root / "integrity" / "MERKLE_ROOT.json"
    temporary_merkle = root / "integrity" / ".MERKLE_ROOT.json.tmp"
    temporary_merkle.write_text(json.dumps(merkle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary_merkle.replace(target)
    print(json.dumps({"sealed_files": len(entries), "merkle_root": merkle["root"]}, indent=2))
    return 0


def cmd_verify(root: Path, _args: argparse.Namespace) -> int:
    manifest = root / "CHECKSUMS.sha256"
    merkle_path = root / "integrity" / "MERKLE_ROOT.json"
    if not manifest.is_file() or not merkle_path.is_file():
        print("Integrity root is incomplete.", file=sys.stderr)
        return 1
    failures = verify_manifest(root, manifest, ROOT_INTEGRITY_FILES)
    entries = read_manifest(manifest)
    merkle = json.loads(merkle_path.read_text(encoding="utf-8"))
    computed_root = merkle_root(entries)
    if merkle.get("file_count") != len(entries):
        failures.append("Merkle file_count differs from manifest")
    if merkle.get("root") != computed_root:
        failures.append("Merkle root differs from manifest")
    if failures:
        print("Public Mesh integrity verification failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(json.dumps({"verified_files": len(entries), "merkle_root": computed_root}, indent=2))
    return 0


def cmd_audit(root: Path, _args: argparse.Namespace) -> int:
    findings = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if (
            "__pycache__" in path.parts
            or path.suffix in IGNORED_SUFFIXES
            or path.name in IGNORED_BASENAMES
            or path.name.endswith(".release.json")
        ):
            findings.append(f"{relative}: unsealed transport-excluded file")
    files = tracked_files(root)
    for path in files:
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        folded = text.casefold()
        relative = path.relative_to(root).as_posix()
        for marker in ABSOLUTE_PATH_PATTERNS:
            if marker in text:
                findings.append(f"{relative}: absolute-path marker")
        for marker in PRIVATE_MARKERS:
            if marker in folded:
                findings.append(f"{relative}: prohibited identifying marker")
        for match in EMAIL_RE.finditer(text):
            findings.append(f"{relative}: possible email {match.group(0)!r}")
    version = json.loads((root / "VERSION.json").read_text(encoding="utf-8"))
    required_false = (
        "contains_private_transcripts",
        "contains_personal_identity",
        "contains_locations",
        "contains_real_credentials",
        "contains_account_identity",
        "private_evidence_embedded",
    )
    for field in required_false:
        if version.get(field) is not False:
            findings.append(f"VERSION.json: {field} must be false")
    ancestry = json.loads((root / "integrity" / "ANCESTRY.json").read_text(encoding="utf-8"))
    if ancestry.get("deep_evidence", {}).get("embedded") is not False:
        findings.append("ANCESTRY.json: deep evidence must remain non-embedded")
    if findings:
        print("Public anonymity audit failed:", file=sys.stderr)
        for finding in findings:
            print(f"- {finding}", file=sys.stderr)
        return 1
    print(json.dumps({"audited_files": len(files), "result": "passed", "private_evidence_embedded": False}, indent=2))
    return 0


def cmd_verify_ancestors(root: Path, _args: argparse.Namespace) -> int:
    embedded = (
        (root / "genealogy", {"CHECKSUMS.sha256"}),
        (root / "observatory", {"CHECKSUMS.sha256"}),
    )
    payload = []
    failed = False
    for ancestor_root, ignored in embedded:
        manifest = ancestor_root / "CHECKSUMS.sha256"
        failures = verify_manifest(ancestor_root, manifest, ignored)
        payload.append({
            "ancestor": ancestor_root.name,
            "manifest_entries": len(read_manifest(manifest)),
            "passed": not failures,
            "failures": failures,
        })
        failed = failed or bool(failures)

    ancestry = json.loads((root / "integrity" / "ANCESTRY.json").read_text(encoding="utf-8"))
    predecessor = ancestry["direct_predecessor"]
    archive_name = predecessor.get("archive_filename")
    archive = root.parent / archive_name if isinstance(archive_name, str) else None
    predecessor_result: dict[str, object] = {
        "ancestor": predecessor["name"],
        "expected_archive_sha256": predecessor["archive_sha256"],
        "archive_available": archive is not None and archive.is_file(),
    }
    if archive is not None and archive.is_file():
        actual_digest = sha256(archive)
        predecessor_result["actual_archive_sha256"] = actual_digest
        predecessor_result["passed"] = actual_digest == predecessor["archive_sha256"]
        failed = failed or not predecessor_result["passed"]
    else:
        predecessor_result["passed"] = None
        predecessor_result["note"] = "predecessor archive not embedded; verify externally when available"
    payload.append(predecessor_result)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 1 if failed else 0


def load_replica_registry(root: Path, args: argparse.Namespace) -> tuple[Path, dict[str, object]]:
    path = Path(args.registry).expanduser().resolve() if getattr(args, "registry", None) else root / "replication" / "replicas.json"
    return path, json.loads(path.read_text(encoding="utf-8"))


def cmd_simulate_failures(root: Path, args: argparse.Namespace) -> int:
    registry_path, registry = load_replica_registry(root, args)
    expected_generation = json.loads((root / "mesh.json").read_text(encoding="utf-8"))["generation"]
    if registry.get("generation") != expected_generation:
        print(json.dumps({
            "registry": registry_path.name,
            "expected_generation": expected_generation,
            "actual_generation": registry.get("generation"),
            "findings": ["replica registry generation does not match this mesh"],
            "result": "failed",
        }, indent=2))
        return 1
    verified = [item for item in registry.get("replicas", []) if item.get("status") == "verified"]
    policy = registry.get("failure_policy", {})
    minimum = int(policy.get("minimum_survivors_after_one_provider_loss", 2))
    require_cross_class = bool(policy.get("require_cross_class_survivor", True))
    if not verified:
        result = {
            "registry": registry_path.name,
            "verified_replicas": 0,
            "result": "pending",
            "reason": "no externally verified replicas are recorded yet",
        }
        print(json.dumps(result, indent=2))
        return 1 if args.require_complete else 0

    findings = []
    release_sha256 = registry.get("release_sha256")
    cid = registry.get("cid")
    allowed_classes = {"web", "git", "ipfs", "doi-archive", "source-preservation"}
    replica_ids = set()
    provider_classes: dict[str, str] = {}
    if not isinstance(release_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", release_sha256):
        findings.append("verified registry requires a valid release_sha256")
    if not isinstance(cid, str) or not re.fullmatch(r"b[a-z2-7]+", cid):
        findings.append("verified registry requires a valid CIDv1 string")
    for item in verified:
        replica_id = str(item.get("id", "<unnamed>"))
        provider_id = item.get("provider_id")
        provider_class = item.get("provider_class")
        if not replica_id or replica_id == "<unnamed>" or replica_id in replica_ids:
            findings.append(f"{replica_id}: replica id must be present and unique")
        replica_ids.add(replica_id)
        if not isinstance(provider_id, str) or not provider_id:
            findings.append(f"{replica_id}: provider_id must be a non-empty string")
        if provider_class not in allowed_classes:
            findings.append(f"{replica_id}: provider_class is invalid")
        if isinstance(provider_id, str) and provider_id:
            previous_class = provider_classes.get(provider_id)
            if previous_class is not None and previous_class != provider_class:
                findings.append(f"{replica_id}: one provider_id cannot claim multiple classes")
            elif isinstance(provider_class, str):
                provider_classes[provider_id] = provider_class
        if not isinstance(item.get("locator"), str) or not item["locator"]:
            findings.append(f"{replica_id}: verified replica requires a locator")
        if item.get("verified_sha256") != release_sha256:
            findings.append(f"{replica_id}: verified digest must equal release_sha256")
        if not isinstance(item.get("verified_at"), str) or not item["verified_at"]:
            findings.append(f"{replica_id}: verified replica requires verified_at")
        if provider_class == "ipfs" and item.get("locator") != f"ipfs://{cid}":
            findings.append(f"{replica_id}: IPFS locator must equal the release CID")

    minimum_ipfs = int(policy.get("minimum_ipfs_custodians", 3))
    ipfs_providers = {
        str(item.get("provider_id"))
        for item in verified
        if item.get("provider_class") == "ipfs"
    }
    if len(ipfs_providers) < minimum_ipfs:
        findings.append(
            f"verified IPFS custodians {len(ipfs_providers)} below required {minimum_ipfs}"
        )
    required_classes = set(policy.get("required_provider_classes", allowed_classes))
    invalid_required_classes = required_classes - allowed_classes
    if invalid_required_classes:
        findings.append("failure policy contains invalid required provider classes")
    actual_classes = {str(item.get("provider_class")) for item in verified}
    missing_classes = required_classes - actual_classes
    if missing_classes:
        findings.append(f"missing verified provider classes: {', '.join(sorted(missing_classes))}")
    if findings:
        print(json.dumps({
            "registry": registry_path.name,
            "verified_replicas": len(verified),
            "verified_ipfs_custodians": len(ipfs_providers),
            "findings": findings,
            "result": "failed",
        }, indent=2))
        return 1

    providers = sorted({str(item["provider_id"]) for item in verified})
    simulations = []
    failed = False
    for provider in providers:
        survivors = [item for item in verified if str(item["provider_id"]) != provider]
        survivor_providers = {str(item.get("provider_id")) for item in survivors}
        classes = {str(item.get("provider_class")) for item in survivors}
        passed = len(survivor_providers) >= minimum and (not require_cross_class or len(classes) >= 2)
        simulations.append({
            "failed_provider": provider,
            "survivor_count": len(survivor_providers),
            "survivor_replica_count": len(survivors),
            "survivor_classes": sorted(classes),
            "passed": passed,
        })
        failed = failed or not passed
    result = {
        "registry": registry_path.name,
        "verified_replicas": len(verified),
        "verified_ipfs_custodians": len(ipfs_providers),
        "provider_failures_tested": len(simulations),
        "simulations": simulations,
        "result": "failed" if failed else "passed",
    }
    print(json.dumps(result, indent=2))
    return 1 if failed else 0


def cmd_verify_car(_root: Path, args: argparse.Namespace) -> int:
    from build_car import verify

    result = verify(Path(args.car), Path(args.archive))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] == "passed" else 1


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--root", help="Path to the Digital Field Public Mesh root")
    subparsers = result.add_subparsers(dest="command", required=True)
    for name in ("status", "seal", "verify", "audit", "verify-ancestors"):
        subparsers.add_parser(name)
    failures = subparsers.add_parser("simulate-failures")
    failures.add_argument("--registry", help="External replica registry JSON")
    failures.add_argument("--require-complete", action="store_true")
    car = subparsers.add_parser("verify-car")
    car.add_argument("car")
    car.add_argument("archive")
    return result


def main() -> int:
    args = parser().parse_args()
    root = package_root(args.root)
    commands = {
        "status": cmd_status,
        "seal": cmd_seal,
        "verify": cmd_verify,
        "audit": cmd_audit,
        "verify-ancestors": cmd_verify_ancestors,
        "simulate-failures": cmd_simulate_failures,
        "verify-car": cmd_verify_car,
    }
    return commands[args.command](root, args)


if __name__ == "__main__":
    raise SystemExit(main())
