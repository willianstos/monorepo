# Orchestration Validator

Use this playbook when validating the production-hardening path locally.

## Goals

- exercise Redis Streams consumer-group behavior
- verify trusted-source enforcement for system tasks
- confirm CI ordering rules and fix-loop handling
- confirm human approval and merge remain non-bypassable
- inspect `audit_log`, `system_alert`, and scheduler metrics after each step

## Baseline Commands

```bash
docker compose -f env/docker-compose.redis.yml up -d redis-integration
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py issue --graph-id demo-001 --objective "Validate orchestration"
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py snapshot
```

## What To Inspect

- `system_events` contains `audit_log` entries for accepted and rejected transitions
- `scheduler:metrics` increments `tasks_created`, `tasks_blocked`, `retries`, `dead_letters`, `ci_failures`, and `merge_blocks`
- `scheduler:throughput` reflects created/running/completed/blocked transitions per task type
- merge completion is rejected until `human_approval_status` is recorded as `approved`
- `memory_write_requested` accepts only distilled `MemoryRecord` payloads

## Redis Inspection

```bash
docker exec redis-integration redis-cli XRANGE system_events - +
docker exec redis-integration redis-cli HGETALL scheduler:metrics
docker exec redis-integration redis-cli HGETALL scheduler:throughput
```
