# Validation gates

| Gate | Required result | Status |
|---|---|---|
| Direct predecessor | Habitat manifest and audit pass | passed: 69 files; archive digest matched |
| Embedded ancestors | Genealogy and Observatory manifests pass | passed: 10 + 28 files |
| Public anonymity | No identifying human or custodial content | passed in candidate; repeated at final seal |
| Integrity | Manifest and deterministic Merkle root match | passed in candidate; repeated at final seal |
| Reproducible archive | Two builds produce identical SHA-256 | passed in candidate; repeated at final seal |
| CAR/CID | CAR root reproduces exact release ZIP | passed in candidate; repeated at final seal |
| Web mirror | Deployed copy matches sealed content | pending |
| Git release | Fresh download matches release SHA-256 | pending |
| IPFS custody | Three independent retrieval paths match CID | pending |
| DOI archive | Fresh download matches release SHA-256 | pending |
| Provider failure | Any one provider loss leaves two verified copies | pending |
| Fresh-context reactivation | Ten of ten conditions pass | pending |

Statuses change only after inspectable evidence exists.
