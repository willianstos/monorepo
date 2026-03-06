# Scheduler

> Last Updated: 06/03/2026

## Purpose

The scheduler is the orchestration service for the AI Software Factory. It is separate from agents and separate from the local model gateway.

The current implementation runs an event loop over Redis Streams, rebuilds workflow state from Redis, and enforces guardrails before dispatch and before task state transitions.

## Components

- `service.py`
- `dag_builder.py`
- `dag_store.py`
- `dispatcher.py`
- `ci_handler.py`
- `guardrail_enforcer.py`

## Redis Responsibilities

Streams:

- `agent_tasks`
- `agent_results`
- `ci_events`
- `memory_events`
- `system_events`

State keys:

- `dag:{graph_id}`
- `dag_tasks:{graph_id}`
- `task:{task_id}`
- `taskdeps:{task_id}`
- `taskstatus:{task_id}`

## Event Handling

`issue_created`

- must build the default DAG
- must persist graph and tasks in Redis
- must dispatch the ready `plan_task`

`task_completed`

- must mark the task complete
- must re-evaluate dependencies
- must dispatch the next ready work item if guardrails allow
- must reject invalid transitions such as completing a task that never entered `running`

`task_failed`

- must increment retry count
- must requeue the task until `max_retry_limit`
- must emit `system_alert` and dead-letter the task after retry exhaustion
- reviewer failures may block progression immediately instead of requeueing

`ci_failed`, `coverage_failed`, `security_failed`

- must update CI status in Redis
- must create a fix loop
- must keep downstream tasks blocked until `ci_passed`
- must emit `audit_log` for accepted handling and invalid ordering

`ci_passed`

- must release CI-gated tasks such as `review_task`, `human_approval_gate`, and `merge_task`
- must only complete `rerun_ci` if the latest `fix_task` is already completed and `rerun_ci` is already running

## Human Approval

The scheduler never merges automatically.

When the DAG reaches `human_approval_gate`, the scheduler publishes `human_approval_required` to `system_events` and waits for an external completion event before releasing `merge_task`.
If the approval result is anything other than `approved`, the graph remains blocked and `merge_task` stays undispatched.
Local `/git` checkpoints on feature branches do not bypass this merge gate.

Trusted approval completion must use:

- `source="system"`
- `payload.approval_source` in `{"human", "system"}`
- `payload.approval_status`
- `payload.approval_actor` when `approval_source="human"`

## Audit Trail

`audit_log` is the structured trace event carried on `system_events`.

Every audit payload includes:

- `event_id`
- `correlation_id`
- `graph_id`
- `task_id`
- `source`
- `task_type`
- `previous_status`
- `next_status`
- `reason`
- `category`
- `result`

The scheduler emits `audit_log` for accepted and rejected transitions, guardrail rejections, trusted-source violations, merge-gate blocks, CI handling, and duplicate-event suppression.

## Idempotency And Observability

- processed scheduler event IDs are persisted in Redis and duplicates are ignored before state mutation
- scheduler counters live in `scheduler:metrics`
- per-stage throughput lives in `scheduler:throughput`
- `AssistantRuntime.scheduler_health_report()` returns a lightweight snapshot of those counters

## Runtime Memory Path

`memory_events` now accepts `memory_write_requested`.

- raw transcript-style fields are rejected at runtime
- only structured `MemoryRecord` payloads are accepted
- accepted records are persisted to Redis-backed memory keys scoped by project, graph, and task
- rejection emits both `system_alert` and `audit_log`

## Guardrails

The scheduler enforces:

- coder cannot touch tests
- coder cannot touch CI config
- tester owns tests and fixtures
- tester may not edit implementation files
- reviewer owns review decisions
- reviewer may block progression
- CI cannot be bypassed
- merge requires human approval
- task completion checkpoints stay on feature branches unless explicit human-approved merge work is requested
- system-owned tasks require trusted completion sources
- direct agent-to-agent calls are forbidden
- push to `main` is forbidden
- raw conversation payloads are forbidden for memory storage
