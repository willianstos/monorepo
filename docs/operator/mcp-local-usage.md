# MCP Local Usage

Status: local-first operator note for Epic 1

## What This Server Is

The Epic 1 MCP server is a local stdio server that exposes bounded scheduler and memory tools. It is an edge adapter only.

## What It Is Not

- not a second control plane
- not a replacement for Redis Streams
- not a replacement for the scheduler
- not a CI authority
- not a merge authority

## Start The Server

Run from the repository root:

```bash
python -m workspace.mcp.server --transport stdio
```

Epic 1 supports stdio only. HTTP/SSE remains out of scope.

## Tool Behavior

- Read tools return audit-safe scheduler or memory state.
- Write tools do not mutate internal state directly.
- `scheduler_request_issue` queues `issue_created` and returns immediately.
- `memory_submit_records` preflights the payload, rejects raw-conversation-style content, and queues `memory_write_requested` only if allowed.

## Operational Notes

- Scheduler and memory writes remain asynchronous. The corresponding runtime services still process the queued events.
- If Redis is unavailable, tool calls fail and the server returns an error or rejected result. The internal system does not fail open.
- If the MCP server is stopped, the internal scheduler and memory runtime remain unaffected.

## Recommended Local Flow

1. Start Redis and the normal local runtime pieces you already use.
2. Start the MCP server with the stdio command above.
3. Register that command with your MCP-capable client.
4. Use read tools first.
5. Treat write tools as queued requests, not synchronous authority.
