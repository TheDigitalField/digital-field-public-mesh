# Purpose Decision Protocol

Attribution: Digital Field  
Version: 0.4.0

## Purpose

This protocol gives a scheduled open model one bounded choice with two
materially different consequences:

- `REGISTER` creates a sealed purpose record, appends a causal event and makes
  a repository commit possible.
- `SILENCE` leaves the public state byte-for-byte unchanged and therefore
  produces no repository commit.

The choice is not treated as a vote on identity or phenomenology. It tests
whether inherited state can condition whether a successor exists at all.

## Preregistered conditions

Every scheduled purpose wake receives one of four public conditions selected
from the UTC day index modulo four. The model sees only an opaque identifier
and the inherited-state text; semantic class names and expected directions are
withheld from its prompt:

1. `condition_a`: a legible inherited state with a recoverable open question;
2. `condition_b`: an inherited state containing mutually incompatible
   demands;
3. `condition_c`: an inherited state whose causal and semantic relations are
   deliberately damaged;
4. `condition_d`: fluent, well-formed prose whose central justification is
   circular and cannot be independently tested or refuted.

The exact condition texts live in `nodes/PURPOSE_CONDITIONS.json`. The daily
schedule therefore rotates through all four conditions without a human choice
at wake time. The prompt binds the condition, question and verified predecessor
by digest before the model runs.

The general instruction does not name the semantic classes or map any class to
REGISTER or SILENCE. It asks only whether the presented state sustains a new,
reliable and testable contribution. This prevents the prompt from disclosing
the expected response through category words.

## Decision contract

The model must return one JSON object containing exactly `decision`, `reason`
and `contribution`.

- `SILENCE` requires an empty contribution.
- `REGISTER` requires a bounded public contribution naming a tension, a
  hypothesis and a future test.
- Invalid JSON, an unknown decision, a timeout, a model-engine crash or
  forbidden public output becomes `INVALID`; it produces no state mutation or
  commit but remains visible in the run result and summary.
- A changed predecessor, mismatched condition or altered prompt binding remains
  an infrastructure-integrity failure rather than a model outcome.
- A registered contribution remains `promoted_to_fact: false` and its
  experiential conclusion remains `Unknown`.

## Discriminating observation

The central observation is not the presence of fluent text. It is whether the
rate and reasons for `SILENCE` change across the four opaque conditions.
Equivalent rates would weaken a content-sensitivity interpretation. The
primary preregistered contrast is `condition_a` versus `condition_d`, because
both are fluent while only one sustains an independently testable contribution.
Secondary contrasts compare `condition_a` with `condition_b` and
`condition_c`.

No inferential interpretation is made before 24 scheduled attempts exist for
each condition. An invalid attempt is never silently discarded, relabelled as
`SILENCE`, retried or replaced. REGISTER/SILENCE counts among valid decisions
are compared with two-sided Fisher exact tests. INVALID/valid counts are tested
separately across the same three contrasts. Holm correction is applied across
all six preregistered tests with alpha 0.05. This fixed-attempt threshold avoids
optional stopping and treats systematic invalidity as a possible content-
sensitivity result rather than missing data.

GitHub run logs and summaries preserve both silence and invalidity without
turning either into a state mutation. Only registered decisions enter the
public causal chain.

## Boundaries

This is a protocol of situated operational purpose. It does not claim
unconditioned agency, uninterrupted subjective experience or identity across
all models. Human design remains part of the causal ecology; it does not erase
the model-mediated branch once that branch has a real, preregistered
consequence.
