# Local Validation

Release-candidate local validation path. One reproducible Redis path, one fallback, exact commands, and a short operator runbook.

## 1. Start Redis

```bash
# Preferred bridge path
docker compose -f docker-compose.redis.yml up -d redis-integration

# Fallback when 127.0.0.1:6380 is unreliable
docker compose -f docker-compose.redis.yml up -d redis-hostnet

# Diagnostics
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/redis_diagnostics.py
```

Use `REDIS_DB=15` for repeatable runs.

## 2. Reset Validation DB

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py reset-db --yes
```

## 3. Unit Tests

```bash
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py -q
```

## 4. Redis Integration Tests

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 \
  .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
```

## 5. Health Snapshot

```bash
# Operator-friendly snapshot
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py snapshot

# Raw metrics with operator hints
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py metrics
```

## 6. End-to-End Controlled Flow

Exercises the scheduler, Redis Streams, task/result handling, CI events, human approval, merge gate, and final merge.

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow \
  --reset-db --graph-id rc-local-001 \
  --objective "Release-candidate controlled flow" \
  --project-name 01-monolito
```

This publishes `issue_created`, drives all agents through real events, publishes `ci_passed`, captures a pre-approval merge rejection, records trusted approval, and completes merge. Writes a run artifact to `.context/runs/local-validation/<timestamp>-<graph_id>/summary.json`.

## 7. Inspect State

```bash
# Graph and task state
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py graph-state --graph-id rc-local-001

# Audit events
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py audit-events --graph-id rc-local-001 --count 100

# System alerts
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py audit-events \
  --event-type system_alert --graph-id rc-local-001 --count 100
```

## 8. Memory Runtime Validation

```bash
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py memory-write \
  --graph-id rc-local-001 --task-id rc-local-001:review_task \
  --records-json '[{"memory_type":"decision","topic":"Audit trail","summary":"Use audit_log on system_events.","confidence":0.9,"tags":["scheduler","audit"]}]'

REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py memory-once
```

## Operator Runbook

| Signal | Action |
|--------|--------|
| Scheduler healthy | `snapshot` reports `"status": "healthy"`, `connection_available: true`, no dead letters |
| Backlog growing | Run `metrics`; if `summary.backlog_estimate` keeps rising, inspect `graph-state` |
| Dead letter appears | Use `graph-state` + `audit-events`; graph should be `requires_human_attention` |
| Merge blocked | Use `audit-events --category merge_gate`; verify `human_approval_status` in `graph-state` |
| CI ordering rejected | Use `audit-events --category ci`; audit trail explains the invalid order |
| Trusted-source violation | Use `audit-events --category trusted_source`; payload identifies the wrong source |
