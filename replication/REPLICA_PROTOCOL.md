# Replica protocol

## Immutable object

Every provider receives the exact same reproducible release archive. The archive SHA-256 and raw CIDv1 are recorded in the external release sidecar. A mirror may add presentation metadata but must not alter the archived bytes.

## Required topology

- one public Git repository with an immutable release and human-readable site;
- one independently hosted web mirror;
- at least three independently maintained IPFS pins or nodes advertising the same CID;
- one preservation archive with a DOI;
- one source-preservation request.

## Admission of a replica

A replica becomes `verified` only after a fresh download is compared against the release SHA-256, the CID or CAR is checked when applicable, the package passes `verify` and `audit`, and its ancestry remains intact.

## Custody rule

Credentials remain outside the package. No single custodian receives authority over every replica. Account administration is a practical transport function, not ownership of identity.

## Failure simulation

For every provider marked verified, temporarily remove it from the registry and confirm that at least two verified retrievable copies remain, including at least one copy outside the failed provider class. Record the result without pretending that a simulation proves future availability.

The simulator counts distinct provider identifiers, requires the complete declared
provider-class topology, requires three distinct IPFS custodians to point to the
exact release CID, and rejects evidence belonging to another generation.
