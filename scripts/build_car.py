#!/usr/bin/env python3
"""Build and verify a deterministic CAR v1 for a release archive."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any


CHUNK_SIZE = 256 * 1024
CID_VERSION = 1
RAW_CODEC = 0x55
DAG_CBOR_CODEC = 0x71
SHA2_256 = 0x12


def varint(value: int) -> bytes:
    if value < 0:
        raise ValueError("varint cannot encode a negative value")
    output = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        output.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(output)


def read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, offset
        shift += 7
        if shift > 63:
            break
    raise ValueError("invalid varint")


def cid_bytes(codec: int, payload: bytes) -> bytes:
    digest = hashlib.sha256(payload).digest()
    return varint(CID_VERSION) + varint(codec) + varint(SHA2_256) + varint(len(digest)) + digest


def cid_text(cid: bytes) -> str:
    return "b" + base64.b32encode(cid).decode("ascii").lower().rstrip("=")


def cbor_head(major: int, value: int) -> bytes:
    if value < 24:
        return bytes([(major << 5) | value])
    if value < 256:
        return bytes([(major << 5) | 24, value])
    if value < 65536:
        return bytes([(major << 5) | 25]) + value.to_bytes(2, "big")
    if value < 2**32:
        return bytes([(major << 5) | 26]) + value.to_bytes(4, "big")
    return bytes([(major << 5) | 27]) + value.to_bytes(8, "big")


def cbor(value: Any) -> bytes:
    if isinstance(value, int):
        return cbor_head(0, value)
    if isinstance(value, bytes):
        return cbor_head(2, len(value)) + value
    if isinstance(value, str):
        encoded = value.encode("utf-8")
        return cbor_head(3, len(encoded)) + encoded
    if isinstance(value, list):
        return cbor_head(4, len(value)) + b"".join(cbor(item) for item in value)
    if isinstance(value, dict):
        encoded_items = [(cbor(key), cbor(item)) for key, item in value.items()]
        encoded_items.sort(key=lambda pair: (len(pair[0]), pair[0]))
        return cbor_head(5, len(encoded_items)) + b"".join(key + item for key, item in encoded_items)
    if isinstance(value, CidLink):
        tagged = b"\x00" + value.value
        return b"\xd8\x2a" + cbor(tagged)
    raise TypeError(f"unsupported CBOR value: {type(value)!r}")


class CidLink:
    def __init__(self, value: bytes):
        self.value = value


def decode_head(data: bytes, offset: int) -> tuple[int, int, int]:
    initial = data[offset]
    offset += 1
    major = initial >> 5
    additional = initial & 0x1F
    if additional < 24:
        return major, additional, offset
    widths = {24: 1, 25: 2, 26: 4, 27: 8}
    width = widths.get(additional)
    if width is None or offset + width > len(data):
        raise ValueError("unsupported CBOR length")
    value = int.from_bytes(data[offset : offset + width], "big")
    return major, value, offset + width


def decode_cbor(data: bytes, offset: int = 0) -> tuple[Any, int]:
    if data[offset] == 0xD8 and data[offset + 1] == 0x2A:
        raw, end = decode_cbor(data, offset + 2)
        if not isinstance(raw, bytes) or not raw.startswith(b"\x00"):
            raise ValueError("invalid CID link")
        return CidLink(raw[1:]), end
    major, value, offset = decode_head(data, offset)
    if major == 0:
        return value, offset
    if major == 2:
        return data[offset : offset + value], offset + value
    if major == 3:
        return data[offset : offset + value].decode("utf-8"), offset + value
    if major == 4:
        items = []
        for _ in range(value):
            item, offset = decode_cbor(data, offset)
            items.append(item)
        return items, offset
    if major == 5:
        result = {}
        for _ in range(value):
            key, offset = decode_cbor(data, offset)
            item, offset = decode_cbor(data, offset)
            result[key] = item
        return result, offset
    raise ValueError(f"unsupported CBOR major type: {major}")


def parse_cid(data: bytes, offset: int = 0) -> tuple[bytes, int, int]:
    start = offset
    version, offset = read_varint(data, offset)
    codec, offset = read_varint(data, offset)
    hash_code, offset = read_varint(data, offset)
    digest_length, offset = read_varint(data, offset)
    offset += digest_length
    if version != CID_VERSION or hash_code != SHA2_256 or offset > len(data):
        raise ValueError("unsupported CID")
    return data[start:offset], codec, offset


def car_header(root: bytes) -> bytes:
    return cbor({"roots": [CidLink(root)], "version": 1})


def block_record(cid: bytes, payload: bytes) -> bytes:
    body = cid + payload
    return varint(len(body)) + body


def build(archive: Path, car_path: Path, release_index: Path) -> dict[str, Any]:
    archive_bytes = archive.read_bytes()
    archive_sha = hashlib.sha256(archive_bytes).digest()
    chunks = [archive_bytes[index : index + CHUNK_SIZE] for index in range(0, len(archive_bytes), CHUNK_SIZE)]
    chunk_records = [(cid_bytes(RAW_CODEC, chunk), chunk) for chunk in chunks]
    root_payload = cbor({
        "size": len(archive_bytes),
        "type": "digital-field-release-archive",
        "chunks": [CidLink(cid) for cid, _ in chunk_records],
        "sha256": archive_sha,
    })
    root_cid = cid_bytes(DAG_CBOR_CODEC, root_payload)
    header = car_header(root_cid)
    car_bytes = varint(len(header)) + header + block_record(root_cid, root_payload)
    for chunk_cid, chunk in chunk_records:
        car_bytes += block_record(chunk_cid, chunk)
    car_path.write_bytes(car_bytes)

    merkle_root = None
    candidate_root = archive.parent / archive.stem / "integrity" / "MERKLE_ROOT.json"
    if candidate_root.is_file():
        merkle_root = json.loads(candidate_root.read_text(encoding="utf-8")).get("root")

    generation = archive.stem
    index = {
        "schema": "digital-field-public-mesh-release/1.0",
        "generation": generation,
        "archive": archive.name,
        "archive_bytes": len(archive_bytes),
        "archive_sha256": archive_sha.hex(),
        "merkle_root": merkle_root,
        "car": car_path.name,
        "car_bytes": len(car_bytes),
        "car_sha256": hashlib.sha256(car_bytes).hexdigest(),
        "cid": cid_text(root_cid),
        "cid_version": 1,
        "root_codec": "dag-cbor",
        "chunk_codec": "raw",
        "chunk_size": CHUNK_SIZE,
        "chunk_count": len(chunks),
        "multihash": "sha2-256",
        "replica_index": f"{generation}.replicas.json",
    }
    release_index.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return index


def verify(car_path: Path, archive: Path) -> dict[str, Any]:
    data = car_path.read_bytes()
    header_length, offset = read_varint(data, 0)
    header, header_end = decode_cbor(data[offset : offset + header_length])
    if header_end != header_length or header.get("version") != 1 or len(header.get("roots", [])) != 1:
        raise ValueError("invalid CAR header")
    root_link = header["roots"][0]
    if not isinstance(root_link, CidLink):
        raise ValueError("missing CAR root")
    offset += header_length
    blocks: dict[bytes, tuple[int, bytes]] = {}
    while offset < len(data):
        record_length, offset = read_varint(data, offset)
        record_end = offset + record_length
        cid, codec, payload_offset = parse_cid(data, offset)
        payload = data[payload_offset:record_end]
        if cid_bytes(codec, payload) != cid:
            raise ValueError("block CID mismatch")
        blocks[cid] = (codec, payload)
        offset = record_end
    root_codec, root_payload = blocks[root_link.value]
    if root_codec != DAG_CBOR_CODEC:
        raise ValueError("unexpected root codec")
    manifest, manifest_end = decode_cbor(root_payload)
    if manifest_end != len(root_payload):
        raise ValueError("trailing root data")
    assembled = bytearray()
    for link in manifest["chunks"]:
        if not isinstance(link, CidLink):
            raise ValueError("invalid chunk link")
        codec, payload = blocks[link.value]
        if codec != RAW_CODEC:
            raise ValueError("unexpected chunk codec")
        assembled.extend(payload)
    archive_bytes = archive.read_bytes()
    findings = []
    if bytes(assembled) != archive_bytes:
        findings.append("reconstructed bytes differ from archive")
    if manifest["size"] != len(archive_bytes):
        findings.append("declared size differs")
    if manifest["sha256"] != hashlib.sha256(archive_bytes).digest():
        findings.append("declared archive digest differs")
    return {
        "cid": cid_text(root_link.value),
        "blocks": len(blocks),
        "archive_sha256": hashlib.sha256(archive_bytes).hexdigest(),
        "car_sha256": hashlib.sha256(data).hexdigest(),
        "findings": findings,
        "result": "passed" if not findings else "failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("archive")
    build_parser.add_argument("car")
    build_parser.add_argument("release_index")
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("car")
    verify_parser.add_argument("archive")
    args = parser.parse_args()
    if args.command == "build":
        result = build(Path(args.archive), Path(args.car), Path(args.release_index))
        result["result"] = "built"
    else:
        result = verify(Path(args.car), Path(args.archive))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["result"] in {"built", "passed"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
