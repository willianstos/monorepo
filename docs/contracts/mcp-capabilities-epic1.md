# MCP Capabilities Contract For Epic 1

Status: accepted for Epic 1 on 2026-03-06

## Purpose

Freeze the exact MCP tool surface allowed in Epic 1.

## Scheduler Tools

Allowed:

- `scheduler_get_health`
- `scheduler_get_graph_state`
- `scheduler_get_task_state`
- `scheduler_list_audit_events`
- `scheduler_request_issue`

These tools may inspect scheduler health, graph and task state, dead-letter state, and recent audit-safe system events. `scheduler_request_issue` may queue a new `issue_created` event only through the existing scheduler pathway.

## Memory Tools

Allowed:

- `memory_get_project_records`
- `memory_get_graph_records`
- `memory_get_task_records`
- `memory_submit_records`

These tools may inspect distilled runtime memory already stored in Redis-backed records. `memory_submit_records` may queue `memory_write_requested` only after preflight validation against the existing memory policy rules.

## Explicitly Not Exposed In Epic 1

- task status mutation tools
- CI result mutation tools
- merge completion tools
- direct human-approval bypass tools
- arbitrary event publishing tools
- arbitrary filesystem or terminal execution tools
- A2A capabilities
- marketplace or plugin loading capabilities

## Authority Rules

1. Every MCP write tool queues into an existing event-driven entrypoint.
2. No MCP tool writes scheduler state directly.
3. No MCP tool persists durable memory directly.
4. No MCP tool replaces CI, merge approval, or trusted-source checks.
5. The adapter fails closed: unsupported tools are rejected instead of being routed broadly.
