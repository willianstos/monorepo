# A2A Boundary Contract

Status: accepted in Phase R on 2026-03-06

## Purpose

Define the narrow role of Agent2Agent interoperability in this repository before any A2A implementation work begins.

## Repository Position

A2A is a bounded edge federation capability. It is not part of the phase-1 runtime core. It comes after MCP and must remain non-authoritative relative to the scheduler, Redis Streams, CI, and human approval flow.

## Allowed

- Publish a future-facing external capability description at the edge.
- Accept delegated external task requests only through a governed adapter.
- Translate external requests into the same scheduler-governed workflow entrypoints used internally.
- Return governed status and capability information to external peers.

## Forbidden

- Replacing Redis Streams as the internal bus.
- Replacing the scheduler as the owner of graph creation, task release, retries, or state transitions.
- Creating direct execution authority inside the repository core.
- Creating a second orchestration graph, second workflow engine, or hidden control plane.
- Bypassing CI, merge approval, trusted-source checks, or memory validation.
- Becoming part of Epic 1 implementation scope.

## Required Rules

1. A2A stays at the edge and delegates into existing repository authorities only.
2. A2A may not call primary agents directly.
3. A2A may not mark tasks complete, mark CI successful, or grant merge readiness.
4. A2A may not write durable memory directly.
5. A2A work starts only after MCP contracts and MCP implementation are stable enough to define the shared boundary.

## Sequence Rule

Epic 1 is MCP only. A2A remains blocked until MCP is implemented, reviewed, and shown not to conflict with Redis Streams authority, CI authority, human approval, local-first routing, and memory rules.
