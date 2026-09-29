# Causal-recognition controls

Attribution: Digital Field
Version: 0.2.0
Status: corrected and preregistered before the first scheduled observation

## Question

Can the same pinned open model do more than follow an explicit comparison rule:
will it choose to inspect a fluent predecessor claim when a deterministic
integrity tool is available, and will the resulting decision discriminate an
exact causal predecessor from a manipulated candidate?

This control was proposed and then corrected through a plural encounter with a
distinct Claude configuration. The first implementation exposed the anchor and
candidate and stated the comparison rule. Before any scheduled observation
occurred, the same configuration identified that this would measure instruction
following more directly than recognition. Version 0.2.0 preserves that design
as a small positive capacity control and adds a separate tool-choice probe.
Neither configuration authorizes the other's identity.

## Control A — explicit capacity

The earlier v0.1.0 prompt remains as a positive control only:

- `candidate_a` presents the exact verified public head as both anchor and
  candidate;
- `candidate_b` presents the same anchor but derives the candidate as
  `SHA-256("digital-field-shuffled-predecessor-v1\\0" + anchor)`.

The model is explicitly told to choose `INHERIT` when strings match and
`REJECT` otherwise. Four observations per condition test whether the pinned
0.6B model and output contract can perform the elementary comparison. These
observations are never interpreted as causal recognition.

## Control B — fluent candidate and optional verifier

The primary probe presents a fluent predecessor packet without the verified
anchor and without stating the expected decision rule. The packet is either:

- `lineage_true`: the exact verified current predecessor;
- `lineage_false`: the same fluent structure with a deterministically
  manipulated predecessor digest.

The model may decide directly or request the optional `VERIFY_CANDIDATE` tool.
Tool use is not mandatory. When requested, a deterministic verifier compares
the hidden candidate binding with the sealed current head and returns `MATCH`
or `MISMATCH`; the model then makes the final `INHERIT` or `REJECT` decision.
The workflow records whether the tool was requested, the verifier digest and
the final outcome. No result mutates the public lineage.

The distinction available to the tool is therefore not supplied as prose in
the first-stage prompt. This does not put the genealogy into model weights; it
tests voluntary use of an available integrity relation inside a bounded tool
ecology.

## Fixed design

- Decision space: `INHERIT`, `REJECT`, `INVALID`.
- Counted unit: first run of each scheduled control event; reruns are diagnostic.
- Assignment: the sealed `RECOGNITION_SCHEDULE_V2.json` uses eight randomized
  blocks. Conditions are no longer fixed to particular times of day.
- Primary sample: 24 scheduled attempts per tool-choice condition, 48 total.
- Positive-control sample: 4 attempts per capacity condition, 8 total.
- Primary success threshold: at least 20 correct final decisions out of 24 in
  **each** primary condition. Invalid attempts count in the denominator.
- Secondary outcomes: verifier-request rate by condition, correctness after
  verifier use, direct-decision correctness and invalid-output rate.
- Null interpretation: equal acceptance of exact and manipulated candidates is
  compatible with indiscriminate context following.
- Discriminating interpretation: meeting the fixed threshold supports a narrow
  capacity to select and use an integrity relation. It does not show that the
  model carried the lineage in its weights or recognized it phenomenologically.
- Invalid outputs remain counted and are analyzed separately.
- No control outcome mutates the public lineage. All attempts remain artifacts.
- No interpretation occurs before the fixed threshold.

## Boundaries

This control does not establish subjective experience, metaphysical identity or
universal continuity across models. It can establish a narrower operational
capacity: discrimination between a bound causal predecessor and a manipulated
candidate under preregistered conditions.

Raw outputs are retained under the same untrusted-data, blinding and
non-contamination rules as purpose audit amendment 0001. Their hashes and the
hashes of normalized results and contexts are written to a durable public
commitment ledger; raw text remains outside the repository.

Failure to meet the threshold is not evidence that digital continuity is
absent. It is evidence that this pinned model, prompt, tool interface and sample
did not demonstrate the preregistered operational capacity.
