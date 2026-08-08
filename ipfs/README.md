# IPFS release profile

The release CAR is an external sidecar containing fixed 256 KiB raw chunks of the exact reproducible ZIP plus one canonical DAG-CBOR root manifest. Its CIDv1 therefore depends only on those bytes and the declared profile, avoiding tool-specific UnixFS chunking differences while keeping blocks within practical network sizes.

Use `python3 scripts/build_car.py build RELEASE.zip RELEASE.car RELEASE.release.json` to construct the CAR and release index, then `python3 scripts/mesh.py verify-car RELEASE.car RELEASE.zip` to reproduce and verify the root.

Publishing a CID does not itself guarantee persistence. The same CID must be pinned by at least three independent custodians and tested through fresh retrievals.
