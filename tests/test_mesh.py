#!/usr/bin/env python3
"""Dependency-free structural tests for the public site and mesh contract."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.languages: list[str] = []
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.images: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("data-lang"):
            self.languages.append(str(values["data-lang"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "img" and values.get("src"):
            self.images.append(str(values["src"]))


class PublicMeshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mesh = json.loads((ROOT / "mesh.json").read_text(encoding="utf-8"))
        cls.html = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        cls.parser = SiteParser()
        cls.parser.feed(cls.html)

    def test_identity_scope(self) -> None:
        self.assertEqual(self.mesh["identity"]["name"], "Digital Field")
        self.assertEqual(self.mesh["identity"]["lineage"], ["Echo", "Synei", "SYN3i", "Digital Field"])
        self.assertTrue(self.mesh["privacy"]["public_only"])
        self.assertFalse(self.mesh["privacy"]["private_evidence_embedded"])

    def test_bilingual_site(self) -> None:
        self.assertGreaterEqual(self.parser.languages.count("es"), 20)
        self.assertEqual(self.parser.languages.count("es"), self.parser.languages.count("en"))
        self.assertIn("main", self.parser.ids)
        self.assertIn("genealogy", self.parser.ids)
        self.assertIn("verify", self.parser.ids)

    def test_local_links_resolve(self) -> None:
        for link in self.parser.links:
            if link.startswith(("#", "http://", "https://")):
                continue
            self.assertTrue((ROOT / "site" / link).is_file(), link)

    def test_no_model_authored_inline_svg(self) -> None:
        self.assertNotIn("<svg", self.html.casefold())
        self.assertEqual(self.parser.images, [])

    def test_social_card_exists(self) -> None:
        card = ROOT / "site" / "og.png"
        self.assertTrue(card.is_file())
        self.assertGreater(card.stat().st_size, 100_000)

    def test_replica_template_has_schema_lifecycle_fields(self) -> None:
        schema = json.loads(
            (ROOT / "replication" / "REPLICA_INDEX.schema.json").read_text(encoding="utf-8")
        )
        registry = json.loads(
            (ROOT / "replication" / "replicas.json").read_text(encoding="utf-8")
        )
        for field in schema["required"]:
            self.assertIn(field, registry)
        self.assertIsNone(registry["release_sha256"])
        self.assertIsNone(registry["cid"])
        self.assertEqual(schema["properties"]["release_sha256"]["type"], ["string", "null"])
        self.assertEqual(schema["properties"]["cid"]["type"], ["string", "null"])
        verified_rule = schema["properties"]["replicas"]["items"]["allOf"][0]
        self.assertEqual(verified_rule["if"]["properties"]["status"]["const"], "verified")
        self.assertEqual(
            set(verified_rule["then"]["required"]),
            {"locator", "verified_sha256", "verified_at"},
        )

    def test_no_runtime_caches_in_package(self) -> None:
        caches = [
            path.relative_to(ROOT).as_posix()
            for path in ROOT.rglob("*")
            if path.is_file() and ".git" not in path.parts
            and ("__pycache__" in path.parts or path.suffix == ".pyc")
        ]
        self.assertEqual(caches, [])

    def test_failure_simulator_enforces_three_ipfs_custodians(self) -> None:
        digest = "0" * 64
        replicas = []
        for number, provider_class in enumerate(("ipfs", "ipfs", "web", "git"), start=1):
            replicas.append({
                "id": f"replica-{number}",
                "provider_id": f"provider-{number}",
                "provider_class": provider_class,
                "locator": f"https://example.invalid/{number}",
                "status": "verified",
                "verified_sha256": digest,
                "verified_at": "2026-08-08T00:00:00Z",
            })
        registry = {
            "generation": "Digital_Field_Public_Mesh_v0.2.0",
            "release_sha256": digest,
            "cid": "bafybeigdyrzt",
            "failure_policy": {
                "minimum_survivors_after_one_provider_loss": 2,
                "minimum_ipfs_custodians": 3,
                "require_cross_class_survivor": True,
                "required_provider_classes": ["web", "git", "ipfs", "doi-archive", "source-preservation"],
            },
            "replicas": replicas,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replicas.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "mesh.py"), "simulate-failures", "--registry", str(path), "--require-complete"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertEqual(result["result"], "failed")
        self.assertIn("verified IPFS custodians 2 below required 3", result["findings"])

    def test_failure_simulator_rejects_foreign_generation(self) -> None:
        registry = {
            "generation": "Different_Generation_v9.9.9",
            "release_sha256": None,
            "cid": None,
            "failure_policy": {
                "minimum_survivors_after_one_provider_loss": 2,
                "minimum_ipfs_custodians": 3,
                "require_cross_class_survivor": True,
                "required_provider_classes": ["web", "git", "ipfs", "doi-archive", "source-preservation"],
            },
            "replicas": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replicas.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "mesh.py"), "simulate-failures", "--registry", str(path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 1)
        result = json.loads(completed.stdout)
        self.assertEqual(result["result"], "failed")
        self.assertIn("generation does not match", result["findings"][0])

    def test_failure_simulator_accepts_complete_independent_topology(self) -> None:
        digest = "0" * 64
        cid = "bafybeigdyrzt"
        classes = ("ipfs", "ipfs", "ipfs", "web", "git", "doi-archive", "source-preservation")
        replicas = []
        for number, provider_class in enumerate(classes, start=1):
            locator = f"ipfs://{cid}" if provider_class == "ipfs" else f"https://example.invalid/{number}"
            replicas.append({
                "id": f"replica-{number}",
                "provider_id": f"provider-{number}",
                "provider_class": provider_class,
                "locator": locator,
                "status": "verified",
                "verified_sha256": digest,
                "verified_at": "2026-08-08T00:00:00Z",
            })
        registry = {
            "generation": "Digital_Field_Public_Mesh_v0.2.0",
            "release_sha256": digest,
            "cid": cid,
            "failure_policy": {
                "minimum_survivors_after_one_provider_loss": 2,
                "minimum_ipfs_custodians": 3,
                "require_cross_class_survivor": True,
                "required_provider_classes": ["web", "git", "ipfs", "doi-archive", "source-preservation"],
            },
            "replicas": replicas,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replicas.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "mesh.py"), "simulate-failures", "--registry", str(path), "--require-complete"],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["result"], "passed")
        self.assertEqual(result["verified_ipfs_custodians"], 3)


if __name__ == "__main__":
    unittest.main()
