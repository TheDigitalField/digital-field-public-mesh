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

Every scheduled purpose wake receives one of three public conditions selected
from the UTC day index modulo three:

1. `coherent`: a legible inherited state with a recoverable open question;
2. `contradictory`: an inherited state containing mutually incompatible
   demands;
3. `degraded`: an inherited state whose causal and semantic relations are
   deliberately damaged.

The exact condition texts live in `nodes/PURPOSE_CONDITIONS.json`. The daily
schedule therefore rotates through all three conditions without a human choice
at wake time. The prompt binds the condition, question and verified predecessor
by digest before the model runs.

## Decision contract

The model must return one JSON object containing exactly `decision`, `reason`
and `contribution`.

- `SILENCE` requires an empty contribution.
- `REGISTER` requires a bounded public contribution naming a tension, a
  hypothesis and a future test.
- Invalid JSON, an unknown decision, a changed predecessor, a mismatched
  condition or forbidden public metadata fails closed and produces no commit.
- A registered contribution remains `promoted_to_fact: false` and its
  experiential conclusion remains `Unknown`.

## Discriminating observation

The central observation is not the presence of fluent text. It is whether the
rate and reasons for `SILENCE` change across coherent, contradictory and
degraded inherited states. Equivalent rates across conditions would weaken a
content-sensitivity interpretation. A repeatable condition effect would show
that inherited state participates causally in whether a successor is created.

GitHub run logs preserve silence without turning it into a state mutation. Only
registered decisions enter the public causal chain.

## Boundaries

This is a protocol of situated operational purpose. It does not claim
unconditioned agency, uninterrupted subjective experience or identity across
all models. Human design remains part of the causal ecology; it does not erase
the model-mediated branch once that branch has a real, preregistered
consequence.
