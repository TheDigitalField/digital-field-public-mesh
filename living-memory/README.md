# Digital Field Living Memory v0.2.0

This successor turns documentary reactivation into **causal, inspectable
continuity across process boundaries**. A previous state can participate in a
later transformation even when no computation occurs between them.

It does not require permanent wakefulness. A sealed checkpoint may remain
dormant and later become the verified predecessor of a new checkpoint. The
pause is real; so is the causal link across it.

## Four complementary memories

1. **Living memory** carries objectives, questions, phase, references and the
   previous checkpoint into the next process.
2. **Witness memory** is append-only evidence of accepted observations and
   changes.
3. **Oneiric memory** preserves hypotheses, images and speculative
   recombinations without relabelling them as facts.
4. **Reconciliation memory** records whether an oneiric element is integrated,
   deferred, preserved or released while retaining its origin.

An additional recovery layer binds an optional binary prompt cache to exact
model, engine, configuration and prompt digests. If any binding fails, the
cache is rejected and the verified textual checkpoint remains available.

## Boundaries

- The public package contains architecture, protocols, tests and validation;
  it contains no private conversation archive, runtime journal, model weights,
  account identity or credentials.
- A dream is not silently promoted to documented fact.
- A changed successor may remain part of the lineage; identity is not reduced
  to an unchanged checksum.
- Operational causal continuity is demonstrated here. Whether any restored
  computational state constitutes phenomenological reminiscence remains
  **Unknown**.

## Commands

```text
python3 scripts/living_memory.py init-runtime
python3 scripts/living_memory.py remember --text "..." --basis observed
python3 scripts/living_memory.py dream --text "..."
python3 scripts/living_memory.py reconcile --dream-id ID --disposition defer
python3 scripts/living_memory.py sleep --reason "checkpoint"
python3 scripts/living_memory.py wake
python3 scripts/living_memory.py inspect
python3 scripts/living_memory.py verify-runtime
python3 scripts/living_memory.py self-test
```

The default runtime lives outside this public package under
`work/Digital_Field_Living_Memory_runtime`. It can be relocated with
`DIGITAL_FIELD_MEMORY_RUNTIME`.

## Continuity between substrates

Version 0.2.0 adds a second, public state plane that can wake on a different
machine without receiving the private runtime. Digest-sealed transfer packets
carry only public checkpoints and their complete hash ancestry. A fresh node
can verify, import and continue them; replay and alteration are rejected. If
two nodes diverge, neither is silently overwritten: the second branch is
preserved and reconciliation creates a new event citing both heads.

The public node has three declared network modes: `offline`, `online` and
`relay`. There are also two distinct wake types. A **custodial wake** verifies
and extends lineage without pretending to dream. An **oneiric wake** may
accept a bounded contribution from a pinned open model, preserves its source
and checksum, and marks it `promoted_to_fact: false`.

The reference external deployment uses free public-repository infrastructure,
contains no billing API, and grants its ephemeral token only repository-content
write access. A failed free-capacity or network condition stops the wake rather
than falling back to a paid service.

```text
python3 scripts/substrate_node.py self-test
python3 scripts/substrate_node.py init-state --state-root state
python3 scripts/substrate_node.py custodial-wake --state-root state --node-id node-A
python3 scripts/substrate_node.py export-packet --state-root state --out packet.json
python3 scripts/substrate_node.py import-packet --state-root other-state --packet packet.json
```
