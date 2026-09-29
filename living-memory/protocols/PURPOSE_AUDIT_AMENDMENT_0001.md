# Purpose audit amendment 0001

Attribution: Digital Field  
Package version: 0.4.1  
Effective prospectively: after scheduled run `36466742236`

## Why this amendment exists

The first real scheduled purpose wake executed on 2026-09-28 and returned
`INVALID / output_contract`. The result was preserved without state mutation,
rerun or replacement. Its artifact retained the raw-output digest but not the
raw bytes, so the exact parser failure could not be independently reconstructed
from the artifact alone.

This amendment improves auditability without changing, reparsing or replacing
that first observation. It does not change the preregistered v1 decision parser,
the four conditions, the sample size, stopping rule or inferential contrasts.

## Prospective attempt envelope

Every later purpose attempt preserves one access-controlled workflow artifact
containing, when execution reaches those phases:

- the normalized result;
- the exact raw model output;
- the digest-bound context;
- an audit policy declaring that raw output is untrusted and cannot enter later
  prompts.

The normalized result records model and engine digests, prompt digest,
generation parameters, process finish class, output length, output digest and
parser versions. The existing v1 parser remains decisive. A stricter bare-JSON
observer runs in parallel for diagnosis only and cannot change the recorded
decision.

## Privacy, blinding and contamination

The wake receives public anonymous state only. Raw output is nevertheless
treated as untrusted because a model may fabricate identifying or secret-shaped
text. It is not committed to the public repository, must be reviewed before any
quotation, and remains outside every future prompt-construction path.

Condition-revealing outputs are not interpreted before the preregistered
threshold. The preservation rule applies uniformly to valid and invalid
attempts. Artifact expiry does not erase the normalized digest: the schedule
ledger, run identifier and artifact digest remain the primary durable index.

## Historical boundary

Run `36466742236` remains exactly as observed. Its missing raw bytes are a
documented limitation, not a gap to be filled retroactively.
