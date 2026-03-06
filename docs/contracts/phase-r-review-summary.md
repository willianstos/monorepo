# Phase R Review Summary

Status: accepted in Phase R on 2026-03-06

## Reviewed Domains

- MCP boundary
- worktree strategy
- telemetry boundary
- A2A boundary

## Accepted Principles

1. MCP is an edge adapter only.
2. Redis Streams remains the only internal bus.
3. The scheduler remains the only orchestration authority.
4. Worktrees isolate mutable task execution, not approval or merge flow.
5. Telemetry exists for operator clarity, not transcript capture.
6. A2A is deferred until after MCP and remains edge-only.

## Rejected Patterns

- MCP as a second control plane
- direct agent-to-agent channels
- shared mutable worktrees across active tasks
- prompt dumping as default observability
- remote-first telemetry defaults
- A2A in Epic 1 scope
- any path that bypasses CI or human approval

## Unresolved Questions

- Whether failed worktrees should default to immediate cleanup or short local retention after evidence capture
- Whether remote telemetry exporters should be documented in Epic 1 or deferred until after local exporter support is stable

Neither question blocks Epic 1.

## Epic 1 Preconditions

Epic 1 may start only when all of the following are true:

1. [mcp-boundary.md](./mcp-boundary.md) is accepted as the MCP authority boundary.
2. [worktree-policy.md](./worktree-policy.md) is accepted as the isolation policy.
3. [telemetry-policy.md](./telemetry-policy.md) is accepted as the observability boundary.
4. [a2a-boundary.md](./a2a-boundary.md) is accepted as the interoperability boundary.
5. The Epic 1 scope is frozen to MCP scheduler and memory edge adapters only.
6. No contract conflicts with `AGENTS.md`, `CLAUDE.md`, `WORKSPACE.md`, `GUARDRAILS.md`, or the existing Redis Streams and scheduler authority model.
7. No contract weakens CI authority, human approval, local-first routing, or distilled memory rules.

## Why Implementation Was Blocked Before This Review

Implementation was blocked because the repository did not yet define hard boundaries for:

- what MCP may control
- how mutable task isolation should work
- what telemetry may retain
- where A2A stops

Without those contracts, Epic 1 could drift into a second control plane, unsafe telemetry, or speculative orchestration changes. This review package removes that ambiguity.

## Epic 1 Readiness

Epic 1 is ready to enter execution after this review package because the required boundaries are now explicit, versioned, and consistent with current repository invariants.
