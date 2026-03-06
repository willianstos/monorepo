# Local Validation

> Last Updated: 06/03/2026

This runbook is the release-candidate local validation path for the assistant workspace. It gives one reproducible Redis path, one fallback when bridge networking is unreliable, exact validation commands, and a short operator runbook for the main failure modes.

## 1. Start Redis

Preferred bridge path:

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

Fallback when the bridge path is running but `127.0.0.1:6380` is unreliable:

```bash
docker compose -f docker-compose.redis.yml up -d redis-hostnet
```

Diagnostic command:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/redis_diagnostics.py
```

Use a dedicated DB such as `REDIS_DB=15` for repeatable runs.

## 2. Reset The Validation DB

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py reset-db --yes
```

## 3. Scheduler Unit Tests

```bash
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py -q
```

## 4. Redis Integration Tests

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
```

## 5. Local Validation Snapshot

Operator-friendly health snapshot:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py snapshot
```

Raw-ish metrics plus operator hints:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py metrics
```

## 6. Controlled End-To-End Local Flow

This exercises the actual scheduler, Redis Streams, task/result handling, CI event handling, human approval, merge gate blocking, and final merge completion path.

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow --reset-db --graph-id rc-local-001 --objective "Release-candidate controlled flow" --project-name 01-monolito
```

What this command does:

- publishes `issue_created`
- drives planner, coder, tester, reviewer completion through real task/result events
- publishes authoritative `ci_passed`
- attempts merge before approval and captures the rejection
- records trusted approval payload
- completes merge only after approval is present

The command also writes an inspectable run artifact to:

```text
.context/runs/local-validation/<timestamp>-<graph_id>/summary.json
```

The flow intentionally records one blocked `review_task` before CI passes and one blocked merge attempt before approval. After this scenario, `snapshot` and `metrics` will show those historical counters until the Redis DB is reset again.

## 7. Inspect Graph, Audit, And Dead-Letter State

Inspect graph and task state:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py graph-state --graph-id rc-local-001
```

Inspect `audit_log` events:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py audit-events --graph-id rc-local-001 --count 100
```

Inspect `system_alert` events:

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py audit-events --event-type system_alert --graph-id rc-local-001 --count 100
```

## 8. Memory Runtime Validation

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py memory-write --graph-id rc-local-001 --task-id rc-local-001:review_task --records-json '[{"memory_type":"decision","topic":"Audit trail","summary":"Use audit_log on system_events.","confidence":0.9,"tags":["scheduler","audit"]}]'
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py memory-once
```

## Operator Runbook

- `scheduler healthy`: `snapshot` should report `"status": "healthy"` with `connection_available: true` and no dead letters.
- `backlog growing`: use `metrics`; if `summary.backlog_estimate` keeps rising, inspect `graph-state` for stuck tasks and compare throughput `created` vs `completed`.
- `dead-letter appears`: use `graph-state --graph-id <id>` and `audit-events --graph-id <id>`; the graph should be in `requires_human_attention`.
- `merge blocked`: use `audit-events --graph-id <id> --category merge_gate` or inspect `system_alert`; verify `human_approval_status` exists in `graph-state`.
- `CI ordering rejected`: use `audit-events --graph-id <id> --category ci`; the audit trail explains which CI event order was invalid.
- `trusted-source violation`: use `audit-events --graph-id <id> --category trusted_source`; the payload identifies which system-owned task was completed by the wrong source or without approval markers.
