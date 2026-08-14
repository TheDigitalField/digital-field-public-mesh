#!/usr/bin/env python3
"""Static zero-spend and least-authority audit for the reference workflow."""

from __future__ import annotations

import json
import pathlib
import re
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "deployment" / "github-actions" / "living-memory-node.yml"


def main() -> int:
    text = WORKFLOW.read_text(encoding="utf-8")
    findings = []
    required = [
        "permissions:\n  contents: write",
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "billing_services_used",
        "sha256sum --check --strict",
        "promoted_to_fact",
    ]
    for marker in required:
        if marker not in text and marker not in (ROOT / "scripts" / "substrate_node.py").read_text(encoding="utf-8"):
            findings.append(f"required boundary missing: {marker}")
    forbidden = {
        "human secret reference": r"secrets\.",
        "billable model permission": r"models:\s*read",
        "cloud payment surface": r"(stripe|billing[_-]?account|credit[_-]?card)",
        "unpinned action": r"uses:\s*[^\s@]+@(main|master|v\d+)\s*$",
    }
    for label, pattern in forbidden.items():
        if re.search(pattern, text, re.I | re.M):
            findings.append(label)
    result = {
        "status": "passed" if not findings else "failed",
        "workflow": WORKFLOW.relative_to(ROOT).as_posix(),
        "findings": findings,
        "paid_model_api": False,
        "human_account_secrets": False,
        "declared_permission": "contents: write",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
