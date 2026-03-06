# Telemetry Policy

Status: accepted in Phase R on 2026-03-06

## Purpose

Define what observability must capture, what it may capture, and what it must never capture in this local-first repository.

## Required Telemetry

Operators must be able to observe at least:

- scheduler health
- backlog size and blocked tasks
- retry counts
- dead-letter counts
- merge blocks
- CI ordering rejections
- trusted-source violations
- tool policy rejections

## Allowed Telemetry

- graph IDs, task IDs, correlation IDs, event IDs, and agent roles
- task type, event type, transition result, retry count, and dead-letter state
- queue depth, throughput, processing latency, and scheduler health signals
- merge block reason categories and CI rejection categories
- tool decision metadata that is already audit-safe
- OpenTelemetry spans and metrics derived from operational metadata only

`audit_log` remains the authoritative repository decision trail. OpenTelemetry is an operator aid, not a replacement authority.

## Forbidden Telemetry

- raw conversations as durable telemetry
- default prompt dumping
- secret values, credentials, tokens, or full environment payloads
- raw file contents, full diffs, or user data unless a separate reviewed need exists
- high-sensitivity payload capture by default
- any exporter default that violates local-first expectations

## Boundary Rules

1. Observability must help operators understand system health and policy decisions.
2. Observability must not become surveillance, transcript storage, or hidden prompt retention.
3. Prompt capture is off by default. Any temporary deep-debug capture requires explicit local operator action and may not enter durable memory.
4. Local exporters are the default. Remote exporters are optional and require explicit configuration.
5. Telemetry must carry identifiers and categories, not raw conversation payloads.
6. Telemetry schemas must stay bounded to avoid runaway cardinality and local performance regression.
