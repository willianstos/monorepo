# Memory Layer

> Last Updated: 2026-03-06

Structured memory architecture for the AI development workspace.

## Memory Layers

- `Working Memory`: temporary state intended for Redis. Stores current tasks, agent state, and partial outputs.
- `Session Memory`: recent interaction continuity for the last hours or days.
- `Runtime Durable Memory`: persistent distilled runtime knowledge stored as Redis-backed structured records.
- `Human Durable Memory`: checked-in curated notes under `.claude/memory/`.

## Memory Flush

Before any session context is discarded, the system must perform `MEMORY_FLUSH`.

Flush targets:

- key decisions
- important facts
- architecture updates
- bugs discovered
- fixes implemented
- lessons learned
- performance insights

## Storage Rules

- Never store raw conversations
- Store only distilled knowledge
- Prefer short structured summaries
- Avoid duplicates
- Always attach tags for retrieval

## Runtime Write Path

`memory_events` accepts `memory_write_requested` payloads at runtime.

- payloads are validated through `GuardrailEnforcer.validate_memory_payload`
- raw transcript-style fields are rejected immediately
- accepted distilled `MemoryRecord` items are persisted to Redis-backed project, graph, and task keys
- rejection emits both `system_alert` and `audit_log`

## Retrieval Strategy

1. Search structured memory
2. Search recent sessions
