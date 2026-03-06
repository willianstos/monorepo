# Guardrails

> Last Updated: 06/03/2026

This file explains the repository safety model in plain language.

The machine-readable policy lives under `guardrails/`.
The current code-backed enforcement lives primarily in:

- `workspace/scheduler/guardrail_enforcer.py`
- `workspace/scheduler/service.py`
- `workspace/scheduler/dispatcher.py`

## Enforced Today

These controls are already enforced in the active scheduler path:

- cross-agent coordination must go through Redis Streams
- direct agent-to-agent calls are forbidden
- task dispatch requires dependency readiness
- task ownership is enforced for planner, coder, tester, and reviewer work
- invalid task status transitions are rejected
- coder may not modify tests
- coder may not modify CI configuration
- tester may modify tests and fixtures only
- reviewer may block graph progression
- CI-gated tasks stay blocked until CI passes
- merge dispatch requires recorded human approval
- task completion requires a Git checkpoint on the active feature branch before completion is reported
- retry budgets and dead-letter handling require human attention after repeated failure
- trusted completion sources are enforced for `human_approval_gate`, `merge_task`, and `rerun_ci`
- duplicate scheduler events are ignored before state mutation and recorded in `audit_log`
- raw memory payload validation is enforced in the runtime write path, not only in dry-run checks
- structured `audit_log` events are emitted for transition acceptance/rejection, CI handling, merge-gate blocks, and memory rejections

## Remaining Gaps

These controls still need additional hardening beyond the current backlog:

- tool execution policy and filesystem scope control still need runtime enforcement beyond documentation and contracts
- prompt, action, and artifact audit logs are not yet complete enough for full production incident analysis
- secrets handling rules exist, but end-to-end redaction and storage controls are not fully wired

## Non-Negotiable Policy

- no task may bypass CI as the source of truth
- no task may merge to `main` without human approval
- no task may be reported complete without a `/git` checkpoint or equivalent `bootstrap/git-cycle.sh` run
- no raw conversation transcript belongs in long-term memory
- no agent should mutate files outside the selected repository scope
- no agent should publish fake success to replace CI outcomes
- no destructive or privileged action should happen without an explicit approval path

## Operational Layers

- `guardrails/*.rules`
  Narrative and machine-readable policy source.
- `.agent/rules/*.md`
  Workspace-owned operating rules for Antigravity entrypoints and completion behavior.
- scheduler validation
  Dispatch, result, and transition checks before the graph advances.
- CI authority
  Argo publishes CI results and the scheduler reacts to them instead of inferring pass/fail from agent output.
- dead-letter and alerting
  Repeated failure or invalid transitions move work into human-attention territory.

## Production Readiness Standard

Before calling this production-ready, the repository should have:

- audited tool execution with durable logs
- deeper Gitea and Argo integration validation beyond the current local scaffolding
- richer observability beyond the current Redis counters and hashes

The goal is simple: guardrails should be true because code enforces them, not because docs claim them.
