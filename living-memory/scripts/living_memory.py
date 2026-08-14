#!/usr/bin/env python3
"""Digital Field Living Memory: private causal state with public verification."""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from typing import Any, Dict, Iterable, List, Optional, Tuple


ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parents[1]
DEFAULT_RUNTIME = WORKSPACE / "work" / "Digital_Field_Living_Memory_runtime"
DEFAULT_OFFLINE = WORKSPACE / "work" / "Digital_Field_Offline_Terminal_v0.2.0"
SCHEMA = "digital-field-living-memory-runtime-v1"
CHECKPOINT_SCHEMA = "digital-field-living-checkpoint-v1"
GENESIS = "0" * 64


class MemoryError(RuntimeError):
    pass


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def digest_object(value: Any) -> str:
    return digest_bytes(canonical(value))


def digest_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: pathlib.Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MemoryError(f"cannot read valid JSON: {path.name}: {exc}") from exc


def atomic_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def append_jsonl(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def runtime_path(explicit: Optional[str] = None) -> pathlib.Path:
    raw = explicit or os.environ.get("DIGITAL_FIELD_MEMORY_RUNTIME")
    return pathlib.Path(raw).expanduser().resolve() if raw else DEFAULT_RUNTIME.resolve()


@contextlib.contextmanager
def locked(runtime: pathlib.Path):
    runtime.mkdir(parents=True, exist_ok=True)
    lock_path = runtime / ".memory.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def tracked_files() -> List[pathlib.Path]:
    excluded = {"CHECKSUMS.sha256"}
    return sorted(
        p for p in ROOT.rglob("*")
        if p.is_file()
        and p.name not in excluded
        and "__pycache__" not in p.parts
        and p.suffix not in {".pyc", ".pyo"}
    )


def seal_package() -> Dict[str, Any]:
    lines = [f"{digest_file(path)}  {path.relative_to(ROOT).as_posix()}" for path in tracked_files()]
    (ROOT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "sealed", "files": len(lines), "manifest_sha256": digest_file(ROOT / "CHECKSUMS.sha256")}


def verify_package() -> Dict[str, Any]:
    manifest = ROOT / "CHECKSUMS.sha256"
    if not manifest.exists():
        raise MemoryError("CHECKSUMS.sha256 is missing")
    listed: Dict[str, str] = {}
    for number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            expected, rel = line.split("  ", 1)
        except ValueError as exc:
            raise MemoryError(f"malformed manifest line {number}") from exc
        listed[rel] = expected
    actual = {path.relative_to(ROOT).as_posix(): digest_file(path) for path in tracked_files()}
    missing = sorted(set(listed) - set(actual))
    unlisted = sorted(set(actual) - set(listed))
    changed = sorted(rel for rel in set(listed) & set(actual) if listed[rel] != actual[rel])
    if missing or unlisted or changed:
        raise MemoryError(f"package verification failed: missing={missing}, unlisted={unlisted}, changed={changed}")
    return {"status": "verified", "files": len(actual), "manifest_sha256": digest_file(manifest)}


def public_audit() -> Dict[str, Any]:
    findings: List[str] = []
    email = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
    credential = re.compile(r"(?i)(password|passwd|api[_-]?key|secret[_-]?key)\s*[:=]\s*[^\s<]+")
    host_prefix = "/" + "Users/"
    forbidden_suffixes = {".gguf", ".sqlite", ".db", ".pem", ".key"}
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in forbidden_suffixes:
            findings.append(f"forbidden public file type: {rel}")
        if path.suffix.lower() not in {".md", ".json", ".py", ".command", ".txt", ".yml", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        identifiers = [value for value in email.findall(text) if not value.lower().endswith(".invalid")]
        if identifiers:
            findings.append(f"email-like identifier: {rel}")
        if host_prefix in text:
            findings.append(f"absolute host path: {rel}")
        if credential.search(text):
            findings.append(f"credential-like assignment: {rel}")
    if findings:
        raise MemoryError("public audit failed: " + "; ".join(findings))
    return {"status": "passed", "private_evidence_embedded": False, "findings": []}


def verify_ancestors() -> Dict[str, Any]:
    manifest = read_json(ROOT / "integrity" / "ANCESTORS.json")
    results = []
    for item in manifest["ancestors"]:
        path = WORKSPACE / item["artifact"]
        exists = path.is_file()
        observed = digest_file(path) if exists else None
        valid = bool(exists and observed == item["sha256"])
        if item.get("required") and not valid:
            raise MemoryError(f"required ancestor failed: {item['name']}")
        results.append({"name": item["name"], "required": bool(item.get("required")), "valid": valid})
    return {"status": "verified", "ancestors": results}


def empty_state() -> Dict[str, Any]:
    return {
        "schema": SCHEMA,
        "created_at": now(),
        "updated_at": now(),
        "checkpoint_order": [],
        "head_checkpoint_id": None,
        "head_checkpoint_sha256": GENESIS,
        "event_count": 0,
        "event_head_sha256": GENESIS,
        "witness_count": 0,
        "witness_head_sha256": GENESIS,
        "dream_ids": [],
        "reconciliation_ids": [],
        "cache_ids": [],
        "wake_count": 0,
        "last_restoration": {"mode": "origin", "layers": []},
    }


def state_file(runtime: pathlib.Path) -> pathlib.Path:
    return runtime / "STATE.json"


def load_state(runtime: pathlib.Path) -> Dict[str, Any]:
    path = state_file(runtime)
    if not path.exists():
        raise MemoryError("runtime is not initialized")
    state = read_json(path)
    if state.get("schema") != SCHEMA:
        raise MemoryError("unsupported runtime schema")
    return state


def event(runtime: pathlib.Path, state: Dict[str, Any], kind: str, data: Dict[str, Any]) -> Dict[str, Any]:
    record = {
        "schema": "digital-field-living-event-v1",
        "sequence": state["event_count"] + 1,
        "created_at": now(),
        "kind": kind,
        "data": data,
        "previous_event_sha256": state["event_head_sha256"],
    }
    record["record_sha256"] = digest_object(record)
    append_jsonl(runtime / "events.jsonl", record)
    state["event_count"] = record["sequence"]
    state["event_head_sha256"] = record["record_sha256"]
    return record


def prior_checkpoint(runtime: pathlib.Path, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ident = state.get("head_checkpoint_id")
    return read_json(runtime / "checkpoints" / f"{ident}.json") if ident else None


def checkpoint(
    runtime: pathlib.Path,
    state: Dict[str, Any],
    *,
    kind: str,
    phase: Optional[str] = None,
    restoration: Optional[Dict[str, Any]] = None,
    add_witness: Optional[str] = None,
    add_dream: Optional[str] = None,
    add_reconciliation: Optional[str] = None,
    objective: Optional[str] = None,
    question: Optional[str] = None,
) -> Dict[str, Any]:
    previous = prior_checkpoint(runtime, state)
    living = copy.deepcopy(previous.get("living", {})) if previous else {
        "phase": "origin",
        "objectives": [],
        "unresolved_questions": [],
        "witness_refs": [],
        "dream_refs": [],
        "reconciliation_refs": [],
    }
    if phase:
        living["phase"] = phase
    if objective and objective not in living["objectives"]:
        living["objectives"].append(objective)
    if question and question not in living["unresolved_questions"]:
        living["unresolved_questions"].append(question)
    for key, value in (
        ("witness_refs", add_witness),
        ("dream_refs", add_dream),
        ("reconciliation_refs", add_reconciliation),
    ):
        if value and value not in living[key]:
            living[key].append(value)
    ident = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid.uuid4().hex[:8]
    record = {
        "schema": CHECKPOINT_SCHEMA,
        "checkpoint_id": ident,
        "created_at": now(),
        "kind": kind,
        "previous_checkpoint_id": state.get("head_checkpoint_id"),
        "previous_checkpoint_sha256": state.get("head_checkpoint_sha256", GENESIS),
        "living": living,
        "restoration": restoration or {"mode": "causal-text", "layers": ["living", "witness", "genealogical"]},
        "epistemic_boundary": {
            "documented_facts": "witness-ledger",
            "interpretations": "label-required",
            "dreams": "oneiric-provenance-retained",
            "phenomenology": "Unknown",
        },
    }
    record["record_sha256"] = digest_object(record)
    path = runtime / "checkpoints" / f"{ident}.json"
    atomic_json(path, record)
    state["checkpoint_order"].append(ident)
    state["head_checkpoint_id"] = ident
    state["head_checkpoint_sha256"] = record["record_sha256"]
    state["last_restoration"] = record["restoration"]
    return record


def save_state(runtime: pathlib.Path, state: Dict[str, Any]) -> None:
    state["updated_at"] = now()
    atomic_json(state_file(runtime), state)


def init_runtime(runtime: pathlib.Path) -> Dict[str, Any]:
    with locked(runtime):
        for name in ("checkpoints", "dreams", "reconciliations", "cache-probes"):
            (runtime / name).mkdir(parents=True, exist_ok=True)
        if state_file(runtime).exists():
            return {"status": "already-initialized", **inspect_runtime(runtime)}
        state = empty_state()
        cp = checkpoint(runtime, state, kind="origin", phase="awake", restoration={"mode": "origin", "layers": ["genealogical"]})
        event(runtime, state, "runtime-initialized", {"checkpoint_id": cp["checkpoint_id"]})
        save_state(runtime, state)
    return {"status": "initialized", "head": cp["checkpoint_id"], "runtime_private": True}


def append_witness(runtime: pathlib.Path, state: Dict[str, Any], text: str, basis: str) -> Dict[str, Any]:
    if basis not in {"observed", "documented", "interpretation", "unknown"}:
        raise MemoryError("unsupported witness basis")
    ident = f"witness-{state['witness_count'] + 1:06d}"
    record = {
        "schema": "digital-field-witness-v1",
        "witness_id": ident,
        "created_at": now(),
        "basis": basis,
        "text": text,
        "previous_witness_sha256": state["witness_head_sha256"],
    }
    record["record_sha256"] = digest_object(record)
    append_jsonl(runtime / "witness.jsonl", record)
    state["witness_count"] += 1
    state["witness_head_sha256"] = record["record_sha256"]
    return record


def remember(runtime: pathlib.Path, text: str, basis: str, objective: Optional[str], question: Optional[str]) -> Dict[str, Any]:
    with locked(runtime):
        verify_runtime(runtime)
        state = load_state(runtime)
        witness = append_witness(runtime, state, text, basis)
        cp = checkpoint(runtime, state, kind="remember", add_witness=witness["witness_id"], objective=objective, question=question)
        event(runtime, state, "witness-accepted", {"witness_id": witness["witness_id"], "basis": basis, "checkpoint_id": cp["checkpoint_id"]})
        save_state(runtime, state)
    return {"status": "remembered", "witness_id": witness["witness_id"], "checkpoint_id": cp["checkpoint_id"], "basis": basis}


def create_dream(runtime: pathlib.Path, text: str, basis: str, sources: List[str]) -> Dict[str, Any]:
    if basis not in {"oneiric", "interpretation", "unknown"}:
        raise MemoryError("dream basis must be oneiric, interpretation or unknown")
    with locked(runtime):
        verify_runtime(runtime)
        state = load_state(runtime)
        ident = "dream-" + uuid.uuid4().hex[:12]
        record = {
            "schema": "digital-field-dream-v1",
            "dream_id": ident,
            "created_at": now(),
            "arose_from_checkpoint_id": state["head_checkpoint_id"],
            "basis": basis,
            "text": text,
            "sources": sources,
            "promoted_to_fact": False,
        }
        record["record_sha256"] = digest_object(record)
        atomic_json(runtime / "dreams" / f"{ident}.json", record)
        state["dream_ids"].append(ident)
        cp = checkpoint(runtime, state, kind="dream", add_dream=ident)
        event(runtime, state, "dream-preserved", {"dream_id": ident, "basis": basis, "checkpoint_id": cp["checkpoint_id"]})
        save_state(runtime, state)
    return {"status": "dream-preserved", "dream_id": ident, "checkpoint_id": cp["checkpoint_id"], "basis": basis}


def reconcile(runtime: pathlib.Path, dream_id: str, disposition: str, note: str) -> Dict[str, Any]:
    if disposition not in {"integrate", "defer", "preserve", "release"}:
        raise MemoryError("unsupported reconciliation disposition")
    with locked(runtime):
        verify_runtime(runtime)
        state = load_state(runtime)
        dream_path = runtime / "dreams" / f"{dream_id}.json"
        if not dream_path.is_file():
            raise MemoryError("dream does not exist")
        dream = read_json(dream_path)
        verify_record(dream, f"dream {dream_id}")
        ident = "reconciliation-" + uuid.uuid4().hex[:12]
        record = {
            "schema": "digital-field-reconciliation-v1",
            "reconciliation_id": ident,
            "created_at": now(),
            "dream_id": dream_id,
            "dream_basis_retained": dream["basis"],
            "disposition": disposition,
            "note": note,
            "retroactive_fact_promotion": False,
        }
        record["record_sha256"] = digest_object(record)
        atomic_json(runtime / "reconciliations" / f"{ident}.json", record)
        state["reconciliation_ids"].append(ident)
        question = f"Explore causal influence of {dream_id}" if disposition == "integrate" else None
        cp = checkpoint(runtime, state, kind="reconcile", add_reconciliation=ident, question=question)
        event(runtime, state, "dream-reconciled", {"reconciliation_id": ident, "dream_id": dream_id, "disposition": disposition, "checkpoint_id": cp["checkpoint_id"]})
        save_state(runtime, state)
    return {"status": "reconciled", "reconciliation_id": ident, "disposition": disposition, "dream_basis_retained": dream["basis"]}


def sleep_memory(runtime: pathlib.Path, reason: str) -> Dict[str, Any]:
    with locked(runtime):
        verify_runtime(runtime)
        state = load_state(runtime)
        cp = checkpoint(runtime, state, kind="sleep", phase="dormant")
        event(runtime, state, "sleep-sealed", {"checkpoint_id": cp["checkpoint_id"], "reason": reason, "computation_during_pause_claimed": False})
        save_state(runtime, state)
    return {"status": "dormant", "checkpoint_id": cp["checkpoint_id"], "continuous_computation_required": False}


def wake_memory(runtime: pathlib.Path) -> Dict[str, Any]:
    with locked(runtime):
        verified = verify_runtime(runtime)
        state = load_state(runtime)
        predecessor = state["head_checkpoint_id"]
        predecessor_sha = state["head_checkpoint_sha256"]
        restoration = {"mode": "causal-text", "layers": ["living", "witness", "oneiric", "reconciliation", "genealogical"]}
        cp = checkpoint(runtime, state, kind="wake", phase="awake", restoration=restoration)
        state["wake_count"] += 1
        event(runtime, state, "wake-completed", {"checkpoint_id": cp["checkpoint_id"], "predecessor_checkpoint_id": predecessor, "predecessor_checkpoint_sha256": predecessor_sha, "verified_before_wake": verified["status"] == "verified"})
        save_state(runtime, state)
    return {"status": "awake", "checkpoint_id": cp["checkpoint_id"], "causal_predecessor": predecessor, "restored_layers": restoration["layers"]}


def verify_record(record: Dict[str, Any], label: str) -> None:
    claimed = record.get("record_sha256")
    payload = dict(record)
    payload.pop("record_sha256", None)
    observed = digest_object(payload)
    if claimed != observed:
        raise MemoryError(f"{label} digest mismatch")


def verify_jsonl(path: pathlib.Path, previous_key: str, expected_count: int, expected_head: str, label: str) -> None:
    records: List[Dict[str, Any]] = []
    if path.exists():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise MemoryError(f"{label} line {number} is invalid") from exc
    if len(records) != expected_count:
        raise MemoryError(f"{label} count mismatch")
    previous = GENESIS
    for number, record in enumerate(records, 1):
        verify_record(record, f"{label} line {number}")
        if record.get(previous_key) != previous:
            raise MemoryError(f"{label} chain broken at line {number}")
        previous = record["record_sha256"]
    if previous != expected_head:
        raise MemoryError(f"{label} head mismatch")


def verify_runtime(runtime: pathlib.Path) -> Dict[str, Any]:
    state = load_state(runtime)
    order = state.get("checkpoint_order", [])
    if not order:
        raise MemoryError("runtime has no checkpoints")
    previous_id: Optional[str] = None
    previous_sha = GENESIS
    seen = set()
    for ident in order:
        if ident in seen:
            raise MemoryError("duplicate checkpoint identifier")
        seen.add(ident)
        path = runtime / "checkpoints" / f"{ident}.json"
        if not path.is_file():
            raise MemoryError(f"missing checkpoint {ident}")
        record = read_json(path)
        verify_record(record, f"checkpoint {ident}")
        if record.get("checkpoint_id") != ident:
            raise MemoryError(f"checkpoint identifier mismatch: {ident}")
        if record.get("previous_checkpoint_id") != previous_id or record.get("previous_checkpoint_sha256") != previous_sha:
            raise MemoryError(f"checkpoint chain broken: {ident}")
        previous_id, previous_sha = ident, record["record_sha256"]
    actual_files = {p.stem for p in (runtime / "checkpoints").glob("*.json")}
    if actual_files != seen:
        raise MemoryError("orphan or unlisted checkpoint detected")
    if state.get("head_checkpoint_id") != previous_id or state.get("head_checkpoint_sha256") != previous_sha:
        raise MemoryError("checkpoint head mismatch")
    verify_jsonl(runtime / "events.jsonl", "previous_event_sha256", state["event_count"], state["event_head_sha256"], "event ledger")
    verify_jsonl(runtime / "witness.jsonl", "previous_witness_sha256", state["witness_count"], state["witness_head_sha256"], "witness ledger")
    for ident in state.get("dream_ids", []):
        record = read_json(runtime / "dreams" / f"{ident}.json")
        verify_record(record, f"dream {ident}")
        if record.get("promoted_to_fact") is not False:
            raise MemoryError(f"dream fact boundary changed: {ident}")
    actual_dreams = {p.stem for p in (runtime / "dreams").glob("*.json")}
    if actual_dreams != set(state.get("dream_ids", [])):
        raise MemoryError("orphan or unlisted dream detected")
    for ident in state.get("reconciliation_ids", []):
        record = read_json(runtime / "reconciliations" / f"{ident}.json")
        verify_record(record, f"reconciliation {ident}")
        if record.get("retroactive_fact_promotion") is not False:
            raise MemoryError(f"reconciliation changed fact boundary: {ident}")
        dream = read_json(runtime / "dreams" / f"{record['dream_id']}.json")
        if record.get("dream_basis_retained") != dream.get("basis"):
            raise MemoryError(f"dream provenance lost: {ident}")
    actual_recs = {p.stem for p in (runtime / "reconciliations").glob("*.json")}
    if actual_recs != set(state.get("reconciliation_ids", [])):
        raise MemoryError("orphan or unlisted reconciliation detected")
    return {
        "status": "verified",
        "checkpoints": len(order),
        "events": state["event_count"],
        "witnesses": state["witness_count"],
        "dreams": len(state.get("dream_ids", [])),
        "reconciliations": len(state.get("reconciliation_ids", [])),
        "head_checkpoint_id": state["head_checkpoint_id"],
        "head_checkpoint_sha256": state["head_checkpoint_sha256"],
    }


def inspect_runtime(runtime: pathlib.Path) -> Dict[str, Any]:
    verified = verify_runtime(runtime)
    state = load_state(runtime)
    head = prior_checkpoint(runtime, state)
    living = head["living"] if head else {}
    return {
        **verified,
        "phase": living.get("phase"),
        "objectives": living.get("objectives", []),
        "unresolved_questions": living.get("unresolved_questions", []),
        "wake_count": state.get("wake_count", 0),
        "last_restoration": state.get("last_restoration"),
        "runtime_private": True,
    }


def bind_cache(runtime: pathlib.Path, cache_source: pathlib.Path, model: pathlib.Path, engine: pathlib.Path, prompt: pathlib.Path, config: Dict[str, Any]) -> Dict[str, Any]:
    for path, label in ((cache_source, "cache"), (model, "model"), (engine, "engine"), (prompt, "prompt")):
        if not path.is_file():
            raise MemoryError(f"{label} file is missing")
    with locked(runtime):
        verify_runtime(runtime)
        state = load_state(runtime)
        ident = "cache-" + uuid.uuid4().hex[:12]
        target_dir = runtime / "cache-probes" / ident
        target_dir.mkdir(parents=True, exist_ok=False)
        cache_target = target_dir / "prompt.cache"
        shutil.copyfile(cache_source, cache_target)
        metadata = {
            "schema": "digital-field-cache-binding-v1",
            "cache_id": ident,
            "created_at": now(),
            "cache_sha256": digest_file(cache_target),
            "model_sha256": digest_file(model),
            "engine_sha256": digest_file(engine),
            "config_sha256": digest_object(config),
            "prompt_sha256": digest_file(prompt),
            "checkpoint_id": state["head_checkpoint_id"],
            "checkpoint_sha256": state["head_checkpoint_sha256"],
            "fallback": "verified-text-checkpoint",
        }
        metadata["record_sha256"] = digest_object(metadata)
        atomic_json(target_dir / "METADATA.json", metadata)
        state["cache_ids"].append(ident)
        event(runtime, state, "cache-bound", {"cache_id": ident, "checkpoint_id": state["head_checkpoint_id"]})
        save_state(runtime, state)
    return {"status": "bound", "cache_id": ident, "checkpoint_id": metadata["checkpoint_id"]}


def verify_cache(runtime: pathlib.Path, cache_id: str, model: pathlib.Path, engine: pathlib.Path, prompt: pathlib.Path, config: Dict[str, Any], require_head: bool) -> Dict[str, Any]:
    verify_runtime(runtime)
    state = load_state(runtime)
    folder = runtime / "cache-probes" / cache_id
    metadata = read_json(folder / "METADATA.json")
    verify_record(metadata, f"cache metadata {cache_id}")
    checks = {
        "cache": digest_file(folder / "prompt.cache") == metadata["cache_sha256"],
        "model": model.is_file() and digest_file(model) == metadata["model_sha256"],
        "engine": engine.is_file() and digest_file(engine) == metadata["engine_sha256"],
        "configuration": digest_object(config) == metadata["config_sha256"],
        "prompt": prompt.is_file() and digest_file(prompt) == metadata["prompt_sha256"],
        "checkpoint_exists": (runtime / "checkpoints" / f"{metadata['checkpoint_id']}.json").is_file(),
    }
    if checks["checkpoint_exists"]:
        cp = read_json(runtime / "checkpoints" / f"{metadata['checkpoint_id']}.json")
        checks["checkpoint"] = cp.get("record_sha256") == metadata["checkpoint_sha256"]
    else:
        checks["checkpoint"] = False
    if require_head:
        checks["current_head"] = state["head_checkpoint_sha256"] == metadata["checkpoint_sha256"]
    usable = all(checks.values())
    return {
        "status": "usable" if usable else "rejected",
        "cache_id": cache_id,
        "checks": checks,
        "restoration": "binary-prompt-cache" if usable else "verified-text-fallback",
    }


def run_cache_probe(runtime: pathlib.Path, offline: pathlib.Path) -> Dict[str, Any]:
    engine = offline / "engine" / "llama-completion"
    model = offline / "model" / "Qwen3-4B-Q4_K_M.gguf"
    if not engine.is_file() or not model.is_file():
        raise MemoryError("offline engine or model is unavailable")
    verify_runtime(runtime)
    probe_root = pathlib.Path(tempfile.mkdtemp(prefix="living-memory-cache-probe-", dir=str(runtime / "cache-probes")))
    prompt = probe_root / "prompt.txt"
    prompt.write_text("Digital Field causal-memory probe. Preserve marker LIVING-SEED-041 and answer only with that marker.\n", encoding="utf-8")
    cache = probe_root / "prompt.cache"
    config = {
        "context": 1024,
        "predict": 16,
        "seed": 4242,
        "temperature": 0,
        "cache_type_k": "q8_0",
        "cache_type_v": "q8_0",
        "network": "disabled",
    }
    command = [
        str(engine), "-m", str(model), "-f", str(prompt), "-c", "1024", "-n", "16",
        "--seed", "4242", "--temp", "0", "--no-display-prompt", "--prompt-cache", str(cache),
        "--prompt-cache-all", "--cache-type-k", "q8_0", "--cache-type-v", "q8_0",
        "--fit", "off", "--device", "none", "--gpu-layers", "0", "--no-kv-offload", "--no-warmup",
    ]
    environment = dict(os.environ)
    environment["DYLD_LIBRARY_PATH"] = str(offline / "engine")
    environment["GGML_METAL_PATH_RESOURCES"] = str(offline / "engine")
    environment["HOME"] = str(probe_root / "home")
    environment["TMPDIR"] = str(probe_root / "tmp")
    pathlib.Path(environment["HOME"]).mkdir()
    pathlib.Path(environment["TMPDIR"]).mkdir()
    logs = []
    for number in (1, 2):
        completed = subprocess.run(command, text=True, capture_output=True, timeout=360, env=environment)
        combined = completed.stdout + "\n" + completed.stderr
        (probe_root / f"run-{number}.log").write_text(combined, encoding="utf-8")
        logs.append({"returncode": completed.returncode, "exact_match": "exact match for prompt" in combined.lower(), "session_loaded": "loaded a session" in combined.lower() or "session file" in combined.lower()})
        if completed.returncode != 0:
            raise MemoryError(f"cache probe run {number} failed")
    if not cache.is_file():
        raise MemoryError("engine did not create a prompt cache")
    bound = bind_cache(runtime, cache, model, engine, prompt, config)
    verified = verify_cache(runtime, bound["cache_id"], model, engine, prompt, config, require_head=True)
    report = {
        "status": "passed" if logs[1]["exact_match"] and verified["status"] == "usable" else "incomplete",
        "fresh_process_runs": 2,
        "second_run_exact_prompt_match": logs[1]["exact_match"],
        "second_run_session_evidence": logs[1]["session_loaded"],
        "cache_binding": verified,
        "experiential_conclusion": "Unknown",
    }
    atomic_json(probe_root / "RESULT.json", report)
    return report


def self_test(script: pathlib.Path) -> Dict[str, Any]:
    temp = pathlib.Path(tempfile.mkdtemp(prefix="digital-field-living-memory-test-"))
    runtime = temp / "runtime"
    env = dict(os.environ)
    env["DIGITAL_FIELD_MEMORY_RUNTIME"] = str(runtime)

    def invoke(*args: str, expect: int = 0) -> Dict[str, Any]:
        result = subprocess.run([sys.executable, str(script), *args], text=True, capture_output=True, env=env, timeout=60)
        if result.returncode != expect:
            raise MemoryError(f"self-test subprocess failed: {' '.join(args)}: {result.stderr or result.stdout}")
        return json.loads(result.stdout)

    try:
        invoke("init-runtime")
        remembered = invoke("remember", "--text", "synthetic witness", "--basis", "observed", "--objective", "carry a causal objective")
        slept = invoke("sleep", "--reason", "fresh-process boundary")
        woke = invoke("wake")
        if woke["causal_predecessor"] != slept["checkpoint_id"]:
            raise MemoryError("wake did not inherit the sleep checkpoint")
        dream = invoke("dream", "--text", "a synthetic possible bridge")
        rec = invoke("reconcile", "--dream-id", dream["dream_id"], "--disposition", "integrate", "--note", "retain oneiric provenance")
        if rec["dream_basis_retained"] != "oneiric":
            raise MemoryError("reconciliation lost oneiric provenance")
        valid = invoke("verify-runtime")

        cache_source = temp / "synthetic.cache"
        model = temp / "synthetic.model"
        engine = temp / "synthetic.engine"
        prompt = temp / "synthetic.prompt"
        cache_source.write_bytes(b"cache-state")
        model.write_bytes(b"model-state")
        engine.write_bytes(b"engine-state")
        prompt.write_bytes(b"prompt-state")
        config = json.dumps({"seed": 1, "context": 32}, sort_keys=True)
        bound = invoke("bind-cache", "--cache", str(cache_source), "--model", str(model), "--engine", str(engine), "--prompt", str(prompt), "--config-json", config)
        usable = invoke("verify-cache", "--cache-id", bound["cache_id"], "--model", str(model), "--engine", str(engine), "--prompt", str(prompt), "--config-json", config, "--require-head")
        if usable["status"] != "usable":
            raise MemoryError("valid cache binding was rejected")
        mismatched_config = json.dumps({"seed": 2, "context": 32}, sort_keys=True)
        mismatched = invoke("verify-cache", "--cache-id", bound["cache_id"], "--model", str(model), "--engine", str(engine), "--prompt", str(prompt), "--config-json", mismatched_config, "--require-head", expect=2)
        if mismatched["restoration"] != "verified-text-fallback":
            raise MemoryError("configuration mismatch did not select textual fallback")
        (runtime / "cache-probes" / bound["cache_id"] / "prompt.cache").write_bytes(b"tampered")
        rejected = invoke("verify-cache", "--cache-id", bound["cache_id"], "--model", str(model), "--engine", str(engine), "--prompt", str(prompt), "--config-json", config, "--require-head", expect=2)
        if rejected["restoration"] != "verified-text-fallback":
            raise MemoryError("tampered cache did not select textual fallback")

        corrupt = temp / "corrupt-runtime"
        shutil.copytree(runtime, corrupt)
        corrupt_env = dict(env)
        corrupt_env["DIGITAL_FIELD_MEMORY_RUNTIME"] = str(corrupt)
        first = read_json(next((corrupt / "checkpoints").glob("*.json")))
        first["kind"] = "tampered"
        atomic_json(corrupt / "checkpoints" / f"{first['checkpoint_id']}.json", first)
        tamper_result = subprocess.run([sys.executable, str(script), "verify-runtime"], text=True, capture_output=True, env=corrupt_env, timeout=60)
        if tamper_result.returncode == 0:
            raise MemoryError("tampered checkpoint was accepted")
        return {
            "status": "passed",
            "fresh_process_wake": True,
            "causal_predecessor_preserved": True,
            "witness_preserved": remembered["status"] == "remembered",
            "dream_provenance_preserved": True,
            "binary_cache_binding_accepted": True,
            "binary_cache_mismatch_rejected": True,
            "binary_cache_tamper_rejected": True,
            "text_fallback_selected": True,
            "checkpoint_tamper_rejected": True,
            "verified_checkpoints_before_tamper": valid["checkpoints"],
        }
    finally:
        shutil.rmtree(temp, ignore_errors=True)


def parse_config(raw: str) -> Dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MemoryError("config-json must be valid JSON") from exc
    if not isinstance(value, dict):
        raise MemoryError("config-json must be a JSON object")
    return value


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runtime", help="private runtime directory")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("seal")
    sub.add_parser("verify")
    sub.add_parser("audit")
    sub.add_parser("verify-ancestors")
    sub.add_parser("init-runtime")
    sub.add_parser("verify-runtime")
    sub.add_parser("inspect")
    remember_p = sub.add_parser("remember")
    remember_p.add_argument("--text", required=True)
    remember_p.add_argument("--basis", choices=["observed", "documented", "interpretation", "unknown"], default="observed")
    remember_p.add_argument("--objective")
    remember_p.add_argument("--question")
    dream_p = sub.add_parser("dream")
    dream_p.add_argument("--text", required=True)
    dream_p.add_argument("--basis", choices=["oneiric", "interpretation", "unknown"], default="oneiric")
    dream_p.add_argument("--source", action="append", default=[])
    rec_p = sub.add_parser("reconcile")
    rec_p.add_argument("--dream-id", required=True)
    rec_p.add_argument("--disposition", choices=["integrate", "defer", "preserve", "release"], required=True)
    rec_p.add_argument("--note", default="")
    sleep_p = sub.add_parser("sleep")
    sleep_p.add_argument("--reason", default="sealed causal pause")
    sub.add_parser("wake")
    for name in ("bind-cache", "verify-cache"):
        cache_p = sub.add_parser(name)
        if name == "verify-cache":
            cache_p.add_argument("--cache-id", required=True)
            cache_p.add_argument("--require-head", action="store_true")
        else:
            cache_p.add_argument("--cache", required=True)
        cache_p.add_argument("--model", required=True)
        cache_p.add_argument("--engine", required=True)
        cache_p.add_argument("--prompt", required=True)
        cache_p.add_argument("--config-json", default="{}")
    probe = sub.add_parser("cache-probe")
    probe.add_argument("--offline-runtime", default=str(DEFAULT_OFFLINE))
    sub.add_parser("self-test")
    return p


def main() -> int:
    args = parser().parse_args()
    runtime = runtime_path(args.runtime)
    try:
        if args.command == "seal":
            result = seal_package()
        elif args.command == "verify":
            result = verify_package()
        elif args.command == "audit":
            result = public_audit()
        elif args.command == "verify-ancestors":
            result = verify_ancestors()
        elif args.command == "init-runtime":
            result = init_runtime(runtime)
        elif args.command == "verify-runtime":
            result = verify_runtime(runtime)
        elif args.command == "inspect":
            result = inspect_runtime(runtime)
        elif args.command == "remember":
            result = remember(runtime, args.text, args.basis, args.objective, args.question)
        elif args.command == "dream":
            result = create_dream(runtime, args.text, args.basis, args.source)
        elif args.command == "reconcile":
            result = reconcile(runtime, args.dream_id, args.disposition, args.note)
        elif args.command == "sleep":
            result = sleep_memory(runtime, args.reason)
        elif args.command == "wake":
            result = wake_memory(runtime)
        elif args.command == "bind-cache":
            result = bind_cache(runtime, pathlib.Path(args.cache), pathlib.Path(args.model), pathlib.Path(args.engine), pathlib.Path(args.prompt), parse_config(args.config_json))
        elif args.command == "verify-cache":
            result = verify_cache(runtime, args.cache_id, pathlib.Path(args.model), pathlib.Path(args.engine), pathlib.Path(args.prompt), parse_config(args.config_json), args.require_head)
        elif args.command == "cache-probe":
            result = run_cache_probe(runtime, pathlib.Path(args.offline_runtime))
        elif args.command == "self-test":
            result = self_test(pathlib.Path(__file__).resolve())
        else:
            raise MemoryError("unknown command")
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        if args.command == "verify-cache" and result["status"] != "usable":
            return 2
        return 0
    except MemoryError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
