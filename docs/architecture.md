# Architecture

Local-first, event-driven architecture for AI-assisted software delivery.

**Implemented:** Redis Streams event bus, scheduler event loop, Redis DAG persistence, CI-event handling and fix-loop logic, code-backed guardrail enforcement, runtime bootstrap, memory write enforcement, dry-run validation.

**Fixed decisions:** scheduler is a separate service; Redis Streams is the only bus; DAG state persists in Redis; CI status enters through `ci_events`; agents communicate only through events; CI is source of truth; merge requires human approval; `/git` is a checkpoint, not a merge.

## Agents

| Agent | Responsibility |
|-------|---------------|
| `planner` | Interpret request, prepare planning inputs |
| `coder` | Write implementation code only |
| `tester` | Own tests and fixtures only |
| `reviewer` | Validate quality, consistency, guardrails |

No direct agent-to-agent calls.

## Orchestration

`workspace/scheduler/service.py` owns cross-agent orchestration. The scheduler is stateless by contract and reconstructs workflow state from Redis on each event.

1. Listen to Redis Streams via consumer groups.
2. Build DAGs from `issue_created` or `task_graph_created`.
3. Persist DAG and task state in Redis.
4. Dispatch ready tasks by publishing events.
5. Validate task ownership and transitions before mutation.
6. Release dependents only after dependencies complete.
7. Enforce guardrails before dispatch and after results.
8. Block CI-gated tasks until CI passes.
9. Block merge until human approval is recorded.
10. React to CI events; create fix loops on failure.
11. Emit `system_alert` on critical failure or retry exhaustion.
12. Emit `audit_log` on accepted and rejected decisions.

## Redis Streams

Streams: `agent_tasks`, `agent_results`, `ci_events`, `memory_events`, `system_events`.

Operations: `XADD`, `XREADGROUP`, `XACK`. No Pub/Sub for orchestration.

## Event Schema

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

Key event types: `issue_created`, `task_graph_created`, `task_created`, `task_started`, `task_completed`, `task_failed`, `code_generated`, `tests_requested`, `review_requested`, `ci_started`, `ci_failed`, `ci_passed`, `coverage_failed`, `security_failed`, `human_approval_required`, `merge_requested`, `system_alert`, `memory_write_requested`, `audit_log`.

## DAG Model

Task node fields: `task_id`, `graph_id`, `task_type`, `dependencies`, `assigned_agent`, `status`, `guardrail_policy`, `retry_count`, `created_at`, `updated_at`.

Statuses: `pending`, `ready`, `running`, `blocked`, `failed`, `completed`, `cancelled`.

State keys: `dag:{graph_id}`, `dag_tasks:{graph_id}`, `task:{task_id}`, `taskdeps:{task_id}`, `taskstatus:{task_id}`.

Invalid transitions are rejected in code. Duplicate scheduler event IDs are persisted and ignored idempotently.

## Default Pipeline

From `issue_created`: `plan_task` > `implement_task` > `test_task` > `review_task` > `human_approval_gate` > `merge_task`.

Review, human approval, and merge are CI-gated. Reviewer failure blocks progression.

## CI Integration

External CI producers publish to `ci_events`. Supported: `ci_started`, `ci_failed`, `ci_passed`, `coverage_failed`, `security_failed`.

In the current release-candidate path, those external boundaries are still simulated locally. The scheduler contract stays the same: CI outcomes arrive as events and gate downstream tasks.

On failure: scheduler appends a fix loop, keeps downstream blocked. `coverage_failed` and `security_failed` also emit `system_alert`. Invalid CI ordering emits `system_alert` + `audit_log` without advancing state.

## Failure Handling

Tracks `retry_count`, `max_retry_limit`, dead-letter records, `system_alert`, `audit_log`, and Redis-backed counters under `scheduler:*`. Retry exhaustion stops progression and requires human attention.

## Runtime

`workspace/runtime/assistant_runtime.py` bootstraps the event bus, scheduler, memory runtime, model gateway/routing, memory metadata, write-path enforcement, and dry-run validation. The scheduler is model-agnostic.

## Memory Runtime

`workspace/memory/runtime_service.py` consumes `memory_write_requested` from `memory_events`. Validates payloads through the guardrail layer, rejects raw conversation storage, persists structured records to Redis-backed keys (project/graph/task scopes), emits `audit_log` and `system_alert` on rejection.
