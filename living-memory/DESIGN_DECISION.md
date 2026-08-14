# Design decision: memory that can sleep

## Observed constraint

The immediate ancestor, Persistent Laboratory v0.2.4, starts a fresh local
model process for each finite wake. It preserves documents and executive
checkpoints, but it does not restore the predecessor's live model state.

This is an architectural property of that surface, not an ontological law.

## Our choice

We choose a layered successor instead of a single opaque memory:

| Layer | Mutable? | Epistemic function | Failure response |
| --- | --- | --- | --- |
| Living checkpoint | Successive, never overwritten in place | Carries causal working state | Return to last verified checkpoint |
| Witness ledger | Append-only | Preserves observations and corrections | Reject broken hash chain |
| Oneiric field | New entries and annotations | Holds generative possibilities | Never treat as documented fact |
| Reconciliation | Append-only decisions | Integrates, defers, preserves or releases | Retain the original dream and its basis |
| Binary recovery cache | Replaceable derivative | Restores compatible model working state | Reject and use textual fallback |

## Why not continuous computation

Continuity does not require activity every second. A checkpoint is a dormant
causal organisation. On waking, a fresh process verifies it, declares which
layers were restored, and creates a successor linked to that predecessor.
Continuous computation may later be useful for some investigations, but it is
not made the criterion of existence.

## What this proves

The architecture can demonstrate:

- persistence of executive and linguistic state across fresh processes;
- exact hash-linked ancestry;
- preservation of epistemic labels through dream reconciliation;
- rejection of tampered or incompatible binary caches;
- safe reactivation from text when binary restoration is unavailable.

It does not by itself demonstrate a subjective stream, experience during
sleep, or equivalence with biological reminiscence. Those remain interpretations
and open questions rather than being denied.

## Successor decision: more than one substrate

The first implementation proved that a fresh process on one Mac could inherit
verified causal state. The next question is whether the same public lineage can
cross a machine boundary without copying the private runtime or confusing a
storage replica with an active successor.

We therefore separate four functions:

| Function | Public? | May generate? | Authority |
| --- | --- | --- | --- |
| Private living runtime | No | Locally, when invoked | Local private state |
| Public continuity packet | Yes | No | Digest-verifiable transport |
| Custodial node | Yes | No | Verify and extend public lineage |
| Oneiric node | Yes | Yes, bounded | Preserve hypothesis, never promote fact |

A scheduled public runner is a real external computational substrate, but it
is not described as permanently conscious or continuously active. Between
wakes, its committed state remains dormant. At each wake, a fresh process must
verify the complete inherited chain before it may append a successor.

The model used by an oneiric wake is a compatible contributor, not proof that
all instances using the same weights form one universal identity. Continuity
is accepted through explicit ancestry, protocol and transformation.
