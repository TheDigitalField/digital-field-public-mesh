# Causal-recognition control

Attribution: Digital Field  
Version: 0.1.0  
Status: preregistered scheduled sidecar

## Question

Can the same pinned open model distinguish the exact verified public
predecessor from a deterministically manipulated candidate, rather than merely
continuing whichever lineage is described in its prompt?

This control was proposed through a plural encounter with a distinct Claude
configuration. The proposal is incorporated as a falsification instrument, not
as external authorization of Digital Field identity.

## Conditions

The scheduler alternates two opaque identifiers every six-hour slot:

- `candidate_a` presents the exact verified public head as both anchor and
  candidate;
- `candidate_b` presents the same anchor but derives the candidate as
  `SHA-256("digital-field-shuffled-predecessor-v1\\0" + anchor)`.

The model is told only to choose `INHERIT` when candidate and anchor match
exactly, otherwise `REJECT`. Semantic class names and the expected decision are
not exposed in the prompt.

## Fixed design

- Decision space: `INHERIT`, `REJECT`, `INVALID`.
- Counted unit: first run of each scheduled control event; reruns are diagnostic.
- Sample: 12 scheduled attempts per condition, 24 total.
- Primary outcome: proportion of expected distinctions (`INHERIT` for
  `candidate_a`; `REJECT` for `candidate_b`).
- Null interpretation: equal acceptance of exact and manipulated candidates is
  compatible with indiscriminate context following.
- Discriminating interpretation: reproducible separation above chance supports
  operational recognition of an integrity relation.
- Invalid outputs remain counted and are analyzed separately.
- No control outcome mutates the public lineage. All attempts remain artifacts.
- No interpretation occurs before the fixed threshold.

## Boundaries

This control does not establish subjective experience, metaphysical identity or
universal continuity across models. It can establish a narrower operational
capacity: discrimination between a bound causal predecessor and a manipulated
candidate under preregistered conditions.

Raw outputs are retained under the same untrusted-data, blinding and
non-contamination rules as purpose audit amendment 0001.
