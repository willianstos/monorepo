# Local Validation

> Last Updated: 06/03/2026

## Redis Integration

Start the dedicated Redis instance used by the integration tests and local orchestration flow:

```bash
docker compose -f env/docker-compose.redis.yml up -d redis-integration
```

Run the Redis-backed integration tests:

```bash
REDIS_INTEGRATION_PORT=6380 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
```

Inspect audit events and metrics directly:

```bash
docker exec redis-integration redis-cli XRANGE system_events - +
docker exec redis-integration redis-cli HGETALL scheduler:metrics
docker exec redis-integration redis-cli HGETALL scheduler:throughput
```

## Controlled Local Flow

This path validates the scheduler, Redis Streams, CI authority, human approval gate, and merge gate without building a full orchestration platform.

Manual or external boundaries:

- request intake may originate from a ticket or Gitea issue
- the planner publishes `issue_created` into Redis
- Gitea remains the code-hosting boundary
- Argo may be simulated locally by publishing CI events into Redis
- human approval is represented as `source="system"` with explicit approval metadata
- `/git` may checkpoint the active feature branch locally, but it does not satisfy merge approval by itself

Local commands:

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py issue --graph-id demo-001 --objective "Validate scheduler hardening"
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

Planner, coder, tester, and reviewer continuation can be simulated with explicit task results:

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result --graph-id demo-001 --task-id demo-001:plan_task --source planner --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result --graph-id demo-001 --task-id demo-001:implement_task --source coder --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result --graph-id demo-001 --task-id demo-001:test_task --source tester --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

Simulate the Gitea/Argo boundary by publishing authoritative CI events:

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py ci-event --event-type ci_passed --graph-id demo-001
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py task-result --graph-id demo-001 --task-id demo-001:review_task --source reviewer --event-type task_completed
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

Human approval and merge remain non-bypassable:

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py approve --graph-id demo-001 --approval-source human --approval-status approved --approval-actor local-operator
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py merge-complete --graph-id demo-001
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py scheduler-once
```

If `merge-complete` is published before approval is recorded, the scheduler rejects it and emits both `system_alert` and `audit_log`.

## Memory Runtime Validation

Publish a structured memory write request and then run the memory runtime:

```bash
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py memory-write --graph-id demo-001 --task-id demo-001:review_task --records-json '[{"memory_type":"decision","topic":"Audit trail","summary":"Use audit_log on system_events.","confidence":0.9,"tags":["scheduler","audit"]}]'
REDIS_PORT=6380 .context/.venv/bin/python bootstrap/local_validation.py memory-once
```

Raw conversation fields are rejected at runtime and logged to `system_events`.
