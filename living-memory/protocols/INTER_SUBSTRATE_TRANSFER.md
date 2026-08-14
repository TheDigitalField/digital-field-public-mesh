# Inter-substrate transfer protocol

## Purpose

A public Living Memory state may leave one machine, be verified on another and
become causal input to a new transformation. No private runtime, conversation
archive, account identity, credential, model weight or binary cache belongs in
the packet.

## Packet

Each packet contains a complete public snapshot: state, ordered events, public
dreams and preserved branches. The snapshot has a SHA-256 digest; the complete
packet has a second digest called `packet_id`.

Acceptance requires:

1. exact packet and snapshot digests;
2. an unbroken event hash chain from genesis to head;
3. exact indices for public dreams and branches;
4. retained `promoted_to_fact: false` for every dream;
5. retained `private_evidence_embedded: false`;
6. a packet identifier not previously imported by that node.

If the local chain is an ancestor, the incoming successor may be adopted. If
the incoming chain is an ancestor, it is acknowledged without rollback. If
both continue differently from a common event, the incoming branch is sealed
and preserved; a new local reconciliation event cites both heads and the last
common event. No past event is rewritten.
