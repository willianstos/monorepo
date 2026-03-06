# Scheduler

> Last Updated: 06/03/2026

This package implements the separate scheduler service for the local-first AI coding assistant workspace.

The scheduler is stateless at runtime. It rebuilds workflow state from Redis on each event and coordinates work only through Redis Streams.

## Responsibilities

- subscribe to Redis Streams through consumer groups
- build DAGs from `issue_created` and `task_graph_created`
- persist graph and task state in Redis using granular keys
- dispatch only ready tasks through event publishing
- enforce guardrails before dispatch and before task state transitions
- react to authoritative Argo CI events
- create fix loops after CI failure
- dead-letter repeated failures and raise `system_alert`
- persist processed event IDs for idempotent handling
- emit `audit_log` for transition decisions, CI handling, merge-gate blocks, and duplicate suppression

## Modules

- `service.py`: event loop, task/result handling, transition enforcement, retry logic, alerts, audit logs, and metrics
- `dag_builder.py`: default pipeline, fix-loop construction, and guardrail defaults
- `dag_store.py`: Redis persistence for `dag:*`, `task:*`, `taskdeps:*`, `taskstatus:*`, dead-letter records, metrics, and processed-event IDs
- `dispatcher.py`: publish ready tasks to `agent_tasks` or `system_events` without mutating task state directly
- `ci_handler.py`: authoritative CI translation and fix-loop planning
- `guardrail_enforcer.py`: rule-file presence checks, assignment validation, transition validation, and memory payload checks

## Default Pipeline

1. `plan_task`
2. `implement_task`
3. `test_task`
4. `review_task`
5. `human_approval_gate`
6. `merge_task`

The scheduler publishes work items rather than calling agents directly.

## Enforcement Summary

- `coder` cannot modify tests or CI config
- `tester` owns tests and fixtures only
- `reviewer` may block progression
- `review_task`, `human_approval_gate`, and `merge_task` remain CI-gated
- `merge_task` remains blocked until human approval is recorded
- `human_approval_gate`, `merge_task`, and `rerun_ci` enforce trusted completion sources
- invalid task assignments and invalid status transitions are rejected
- repeated failures go to a dead-letter path and require human attention
