# MCP Boundary Contract

Status: accepted in Phase R on 2026-03-06

## Purpose

Define what MCP may and may not do in this repository before any MCP implementation work begins.

## Repository Position

MCP is an outside-core interoperability layer. It is an edge adapter for operator-facing and IDE-facing access to governed repository capabilities. Internal orchestration remains the scheduler plus Redis Streams.

## Allowed

- Expose governed scheduler and memory capabilities at the boundary.
- Support operator-facing and IDE-facing interoperability through stdio and HTTP/SSE.
- Surface read-oriented status, health, and context queries.
- Accept state-changing requests only when those requests resolve into existing scheduler or memory entrypoints.
- Carry tool, provider, and context access only through explicit repository contracts.
- Surface human approval recording only as an operator-mediated action. It does not grant merge authority by itself.

## Forbidden

- Replacing Redis Streams as the internal event or task bus.
- Replacing the scheduler as the authority for DAG creation, task release, status transitions, retries, or merge gating.
- Acting as a second runtime control plane beside the scheduler.
- Creating direct agent-to-agent channels, hidden backchannels, or out-of-band task coordination.
- Marking CI success, merge readiness, or task completion without the same authoritative events already required today.
- Writing durable memory outside the existing memory validation path.

## Required Rules

1. Every state-changing MCP action must map to an existing repository authority:
   - scheduler actions become scheduler-governed events
   - memory actions become memory-runtime requests
2. MCP does not own task transitions, CI outcomes, merge approval, or graph state.
3. MCP does not introduce new primary agents, alternate schedulers, or alternate approval paths.
4. MCP defaults to local-first operation. Remote publication or remote registry use is optional and does not change local authority.
5. Audit-safe identifiers may be exposed. Raw conversations, secrets, and hidden prompt payloads may not be exposed by default.

## Epic 1 Scope Constraint

Epic 1 may implement MCP only for governed scheduler and memory edge adapters. It may not pull A2A, marketplace behavior, plugin execution, or alternate bus behavior into the same slice.
