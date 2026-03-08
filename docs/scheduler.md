# Scheduler

Orchestration service for the Future Agents workspace. Separate from agents and separate from the model gateway.

Stateless by contract. Runs an event loop over Redis Streams, rebuilds workflow state from Redis on each event, and enforces guardrails before dispatch and before state transitions.

## Components

`service.py`, `dag_builder.py`, `dag_store.py`, `dispatcher.py`, `ci_handler.py`, `guardrail_enforcer.py`

## Redis

**Streams:** `agent_tasks`, `agent_results`, `ci_events`, `memory_events`, `system_events`

**State keys:** `dag:{graph_id}`, `dag_tasks:{graph_id}`, `task:{task_id}`, `taskdeps:{task_id}`, `taskstatus:{task_id}`

## Event Handling

| Event | Behavior |
|-------|----------|
| `issue_created` | Build default DAG, persist in Redis, dispatch `plan_task` |
| `task_completed` | Mark complete, re-evaluate dependencies, dispatch next if guardrails allow. Reject invalid transitions. |
| `task_failed` | Increment retry, requeue until limit, then `system_alert` + dead-letter. Reviewer failures block immediately. |
| `ci_failed` / `coverage_failed` / `security_failed` | Update CI status, create fix loop, keep downstream blocked. Emit `audit_log`. |
| `ci_passed` | Release CI-gated tasks. Complete `rerun_ci` only if `fix_task` is done and `rerun_ci` is running. |

## CI Ingress

External CI systems publish `ci_*` events to `ci_events`; they do not call agents directly. In the current release-candidate path, those producers are simulated locally, but the scheduler contract is unchanged.

## Human Approval

The scheduler never merges automatically. At `human_approval_gate`, it publishes `human_approval_required` and waits for external completion. Non-approved results keep the graph blocked.

Trusted completion requires `source="system"`, `payload.approval_source` in `{"human", "system"}`, `payload.approval_status`, and `payload.approval_actor` when human.

## Audit Trail

`audit_log` on `system_events`. Every payload includes: `event_id`, `correlation_id`, `graph_id`, `task_id`, `source`, `task_type`, `previous_status`, `next_status`, `reason`, `category`, `result`.

Emitted for: accepted/rejected transitions, guardrail rejections, trusted-source violations, merge-gate blocks, CI handling, duplicate-event suppression.

## Idempotency

Processed event IDs persist in Redis; duplicates are ignored before mutation. Counters in `scheduler:metrics`, throughput in `scheduler:throughput`. `AssistantRuntime.scheduler_health_report()` returns an operator-friendly snapshot.

## Memory Runtime

`memory_events` accepts `memory_write_requested`. Raw transcripts rejected. Only structured `MemoryRecord` payloads accepted. Persisted to Redis-backed keys scoped by project, graph, and task. Rejection emits `system_alert` + `audit_log`.

## Guardrails

Coder cannot touch tests or CI config. Tester owns tests and fixtures only. Reviewer may block progression. CI cannot be bypassed. Merge requires human approval. System-owned tasks require trusted completion sources. Direct agent-to-agent calls forbidden. Push to `main` forbidden. Raw conversation payloads forbidden for memory storage.
