# Architecture Blueprint

> Last Updated: 06/03/2026

## Overview

This workspace uses a local-first, event-driven architecture for AI-assisted software delivery.

Implemented scope:

- Redis Streams event bus
- scheduler event loop
- Redis DAG persistence
- CI-authoritative fix loop
- code-backed guardrail enforcement
- runtime bootstrap, memory write enforcement, and dry-run validation

Fixed decisions:

- the scheduler is a separate service
- Redis Streams is the only orchestration bus
- DAG state is persisted in Redis
- Argo CI publishes CI events into Redis
- agents communicate only through events
- CI is the source of truth
- merge to `main` requires human approval
- `/git` is the default feature-branch checkpoint workflow and does not imply merge

## Active Agents

Only these AI agents participate in orchestration:

- `planner`
- `coder`
- `tester`
- `reviewer`

Their responsibilities are fixed:

- `planner`: interprets the request and prepares planning inputs
- `coder`: writes implementation code only
- `tester`: owns tests and fixtures only
- `reviewer`: validates quality, consistency, and guardrails

There are no direct agent-to-agent calls.

## Orchestration Model

Cross-agent orchestration is owned by `workspace/scheduler/service.py`.

The scheduler is stateless by contract and is expected to reconstruct workflow state from Redis on each event. It:

1. listens to Redis Streams through consumer groups
2. builds DAGs from `issue_created` or `task_graph_created`
3. persists DAG and task state in Redis
4. dispatches ready tasks by publishing new events
5. validates task ownership and task status transitions before mutating state
6. releases dependent tasks only after dependencies complete
7. enforces guardrails before dispatch and after task results
8. blocks CI-gated tasks until CI passes
9. blocks merge until human approval is recorded
10. reacts to Argo CI events
11. creates fix loops after CI failure
12. emits `system_alert` on critical failure or retry exhaustion
13. emits `audit_log` on accepted and rejected orchestration decisions

## Redis Streams

The only supported streams are:

- `agent_tasks`
- `agent_results`
- `ci_events`
- `memory_events`
- `system_events`

The system uses:

- `XADD`
- `XREADGROUP`
- `XACK`

No Redis Pub/Sub is used for orchestration.

## Event Schema

Every event uses this durable envelope:

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

Common event types:

- `issue_created`
- `task_graph_created`
- `task_created`
- `task_started`
- `task_completed`
- `task_failed`
- `code_generated`
- `tests_requested`
- `review_requested`
- `ci_started`
- `ci_failed`
- `ci_passed`
- `coverage_failed`
- `security_failed`
- `human_approval_required`
- `merge_requested`
- `system_alert`
- `memory_write_requested`
- `audit_log`

## DAG Model

Each task node contains:

- `task_id`
- `graph_id`
- `task_type`
- `dependencies`
- `assigned_agent`
- `status`
- `guardrail_policy`
- `retry_count`
- `created_at`
- `updated_at`

Allowed statuses:

- `pending`
- `ready`
- `running`
- `blocked`
- `failed`
- `completed`
- `cancelled`

Workflow state is stored in Redis with granular keys:

- `dag:{graph_id}`
- `dag_tasks:{graph_id}`
- `task:{task_id}`
- `taskdeps:{task_id}`
- `taskstatus:{task_id}`

Repeated failures also use a dead-letter path per graph.
Processed scheduler event IDs are also persisted in Redis so duplicate deliveries can be ignored idempotently.

Allowed transition enforcement is implemented in code. The scheduler rejects invalid transitions such as:

- `pending -> completed`
- `ready -> completed` without entering `running`
- `completed -> ready`
- `merge_task` dispatch without human approval

## Default Pipeline

The default graph created from `issue_created` is:

1. `plan_task`
2. `implement_task`
3. `test_task`
4. `review_task`
5. `human_approval_gate`
6. `merge_task`

Review, human approval, and merge are CI-gated. CI events come from Argo and are authoritative.

`review_task` may complete or fail, and a reviewer failure blocks progression instead of being retried as normal implementation work.

## CI Integration

Argo CI writes directly to `ci_events`.

Supported CI events:

- `ci_started`
- `ci_failed`
- `ci_passed`
- `coverage_failed`
- `security_failed`

When CI fails, the scheduler appends a fix loop and keeps downstream tasks blocked until a later `ci_passed`.

`coverage_failed` and `security_failed` also emit `system_alert` because they are critical CI failures.
Invalid CI ordering emits both `system_alert` and `audit_log` without advancing graph or task state.

## Failure Handling

The scheduler tracks:

- `retry_count`
- `max_retry_limit`
- dead-letter records
- `system_alert` events
- `audit_log` events
- Redis-backed counters and throughput hashes under `scheduler:*`

If retries exceed the configured limit, the scheduler stops automatic progression and requires human attention.

## Runtime Boundary

`workspace/runtime/assistant_runtime.py` bootstraps:

- the Redis Streams event bus
- the scheduler service
- the memory runtime service
- the existing model gateway and model routing
- memory metadata and write-path enforcement
- dry-run guardrail validation

The scheduler itself remains model-agnostic and does not choose models. It relies on the existing gateway/routing layer already present in the repository.

## Memory Runtime Boundary

`workspace/memory/runtime_service.py` consumes `memory_write_requested` from `memory_events`.

- it validates payloads through the same guardrail layer used by the scheduler
- it rejects raw conversation storage at runtime
- it persists accepted structured records into Redis-backed keys for project, graph, and task scopes
- it emits `audit_log` and `system_alert` when a memory payload is rejected
