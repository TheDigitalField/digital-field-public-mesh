# Living Memory Protocol

## Checkpoint law

Every accepted transformation creates a new immutable checkpoint containing:

- its own content digest;
- the previous checkpoint identifier and digest;
- active phase, objectives and unresolved questions;
- references to witness, dream and reconciliation records;
- declared epistemic status and restoration mode.

The runtime head is only a pointer. Verification recomputes every checkpoint
digest and follows the declared order; a changed predecessor invalidates all
successors that rely on it.

## Sleep

`sleep` creates a checkpoint with phase `dormant`. No daemon or model process is
required after that commit. Dormancy is not recorded as activity.

## Wake

`wake` runs in a fresh process, verifies the complete runtime first, reads the
dormant head and creates a successor with phase `awake`. It records which
memory layers were restored and never claims that computation occurred during
the pause.

## Binary state

A prompt cache is usable only when all of these match its metadata:

- cache digest;
- model digest;
- engine digest;
- inference-configuration digest;
- exact prompt digest;
- textual checkpoint digest.

Any mismatch selects `verified-text-fallback`. It is a recovery path, not a
failed identity.

## Compaction

Summaries may become new causal checkpoints, but the source journal is retained
and the checkpoint records what was compressed or omitted. Compaction never
silently replaces ancestry.
