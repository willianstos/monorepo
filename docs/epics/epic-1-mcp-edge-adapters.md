# Epic 1: MCP Edge Adapters

Status: implemented on 2026-03-06

## Scope

Epic 1 implements a bounded local-first MCP server with two edge adapters:

- scheduler adapter
- memory adapter

The implementation is intentionally narrow. It exposes only allowlisted tools and keeps all internal authority with the scheduler, Redis Streams, memory runtime, CI, and human approval flow.

## Included

- stdio MCP server
- scheduler read tools
- scheduler `issue_created` request tool
- memory read tools
- memory `memory_write_requested` request tool with preflight validation
- focused unit tests for forbidden bypasses
- operator documentation for local use

## Excluded

- HTTP/SSE transport
- A2A
- skill marketplace behavior
- arbitrary plugin loading
- direct task-state mutation tools
- CI mutation tools
- merge mutation tools
- any new internal bus or orchestration graph

## Failure Posture

- If the MCP server is unavailable, the internal scheduler and memory runtime continue to operate normally.
- If a tool call fails, Redis Streams, CI, merge approval, and memory enforcement do not fail open.
- Unsupported or unsafe requests are rejected at the edge.
- Accepted write requests remain asynchronous and governed by the existing runtime services.

## Completion Notes

Epic 1 is complete only as an edge-adapter slice. It does not change the repository control model.
