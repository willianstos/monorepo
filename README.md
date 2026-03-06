# 01-monorepo

> Last Updated: 06/03/2026

Local-first AI coding assistant workspace for controlled software delivery.

This repository is not a fully autonomous engineer and it is not a general production platform. It is a governed local workspace where planner, coder, tester, and reviewer coordinate through Redis Streams, a separate scheduler service, CI events, and an explicit human approval gate before merge.

## Current Maturity

Current classification: `release candidate for local controlled operation`

That means the core orchestration path is real and locally verifiable today:

- the scheduler is a separate service
- Redis Streams is the only event/task bus
- DAG state persists in Redis
- agents communicate only through events
- CI is authoritative
- merge to `main` requires recorded human approval

It does not mean every boundary is fully production-hardened. External integrations, some tool surfaces, and the LangGraph execution layer still have known gaps described below.

## What This Repository Is

- A local-first assistant workspace for AI-assisted coding and review.
- A Redis-backed orchestration spine with real DAG persistence, event handling, retries, dead-letter handling, and audit events.
- A human-governed workflow where CI and human approval remain authoritative.
- A monorepo that keeps shared runtime code in `workspace/` and target projects in `projects/`.

## Enforced Today

- Redis Streams is the only orchestration bus.
- Scheduler state is persisted in Redis with granular DAG and task keys.
- Duplicate scheduler events are suppressed idempotently before state mutation.
- Task ownership is enforced for planner, coder, tester, reviewer, and system-owned tasks.
- Invalid task transitions are rejected and audited.
- CI-gated tasks stay blocked until `ci_passed`.
- Merge cannot complete without recorded approval metadata.
- Trusted source checks apply to `human_approval_gate`, `merge_task`, and `rerun_ci`.
- Memory runtime rejects raw conversation-style payloads and accepts only structured records.
- `audit_log` and `system_alert` events are emitted for accepted and rejected orchestration decisions.
- Tool contracts now enforce filesystem scope and terminal allowlists when invoked, with audit artifacts written under `.context/tool-audit/`.

## Partial Today

- LangGraph nodes are still placeholder-oriented and do not yet represent the full production execution path.
- The local end-to-end flow uses controlled simulation for Gitea/Argo boundaries instead of full external integration.
- Tool policy is implemented locally in tool contracts, but not yet centralized as a scheduler-emitted policy plane.
- Observability is operator-friendly for local use, but still based on Redis counters, throughput hashes, and audit stream inspection.
- Git checkpoint workflow exists as an operator helper, but scheduler-side checkpoint attestation is not yet machine-enforced.

## Still Open Before "Production Hardened"

- Full external validation against real Gitea and Argo event sources.
- Stronger tool/action artifact capture across every runtime path, not only the local tool contracts.
- More complete incident-grade observability and operator dashboards.
- Multi-user, multi-host, and internet-facing hardening are still out of scope.

## Quick Start

1. Create the local virtual environment and install the repo:

```bash
python3 -m venv .context/.venv
.context/.venv/bin/python -m pip install -e .[dev]
```

2. Run the fast local checks:

```bash
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py -q
.context/.venv/bin/python -m mypy workspace
.context/.venv/bin/python -m ruff check workspace projects
```

3. Start Redis for integration and local scheduler validation:

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

4. If `localhost:6380` is unreachable, diagnose and switch to the host-network fallback:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/redis_diagnostics.py
docker compose -f docker-compose.redis.yml up -d redis-hostnet
```

5. Run the Redis-backed integration test and the controlled local flow:

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow --reset-db --graph-id rc-local-001 --objective "Release-candidate controlled flow" --project-name 01-monolito
```

## Core Workflow

Default workflow:

```text
issue/request
-> plan_task
-> implement_task
-> test_task
-> review_task
-> human_approval_gate
-> merge_task
```

CI failure loop:

```text
ci_failed
-> fix_task
-> rerun_ci
-> ci_passed
-> continue blocked review/approval/merge path
```

Merge remains blocked until approval is recorded by a trusted system result payload.

## Event Model Summary

Streams in use:

- `agent_tasks`
- `agent_results`
- `ci_events`
- `memory_events`
- `system_events`

Base event envelope:

```json
{
  "event_type": "string",
  "event_id": "uuid",
  "timestamp": "iso8601",
  "source": "planner|coder|tester|reviewer|scheduler|ci|system",
  "correlation_id": "uuid",
  "payload": {}
}
```

Important system events:

- `audit_log`
- `system_alert`
- `human_approval_required`
- `merge_requested`

## Guardrail Summary

- No direct agent-to-agent calls.
- No bypass of CI as the source of truth.
- No merge to `main` without recorded approval.
- Coder cannot claim test ownership.
- Tester is limited to test and fixture scope.
- Reviewer can block progression.
- Protected system-owned tasks require trusted result sources.
- Raw conversations are forbidden in long-term memory writes.

## Operator Docs

- [Architecture](./docs/architecture.md)
- [Scheduler Readme](./workspace/scheduler/README.md)
- [Local Validation Runbook](./docs/local-validation.md)
- [Guardrails](./GUARDRAILS.md)
- [Contributing](./CONTRIBUTING.md)

## Next Milestones

1. Replace remaining placeholder LangGraph execution behavior with real runtime actions.
2. Move more tool and action auditing into the runtime/scheduler path.
3. Validate the same flow against real external CI and code-host boundaries.
4. Tighten checkpoint attestation, operator diagnostics, and incident-grade observability.
5. Reassess "production hardened" only after those gaps are closed with evidence.
