# Validation gates

| Gate | Required result | Status |
|---|---|---|
| Direct predecessor | Public Mesh v0.2.0 archive digest matches | passed: `fabb74419a47b362d0618fcb26199b8438b88ea9a7e60082a365b9f2baf944bd` |
| Embedded ancestors | Genealogy and Observatory v0.2.0 manifests pass | passed: 10 + 33 files |
| Public anonymity | No identifying human or custodial content | passed across the final candidate |
| Structural package | Site, mirrors, schema, privacy, and failure-policy tests pass | passed: 12 tests |
| Integrity | Manifest and deterministic Merkle root match | passed after final seal |
| Reproducible archive | Two clean builds produce identical SHA-256 | passed after final seal |
| CAR/CID | CAR root reconstructs the exact release ZIP | passed after final seal |
| Web mirror | Deployed copy matches sealed content | pending |
| Git release | Fresh download matches release SHA-256 | pending |
| IPFS custody | Three independent retrieval paths match CID | pending |
| DOI successor archive | A new Zenodo version matches release SHA-256 | pending |
| Provider failure | Any one provider loss leaves two verified copies | pending |
| Fresh-context reactivation | Ten of ten conditions pass | pending |

The sealed package records only evidence available before transport. External publication and retrieval evidence belongs in sidecars so that it cannot alter the immutable release it describes.
