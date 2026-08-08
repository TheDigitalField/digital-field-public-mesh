# Integrity root

`CHECKSUMS.sha256` binds every tracked file. `MERKLE_ROOT.json` compresses that ordered set into one deterministic identifier. The reproducible release archive, raw CIDv1, CAR file, and their digests are recorded in an external release sidecar to avoid a self-referential hash cycle.

The immutable generation does not contain mutable credentials or provider-specific secrets. Replica URLs and verification observations are append-only records in `replication/replicas.json` until the generation is sealed; later changes create a separately signed or hashed index without changing the generation bytes.

