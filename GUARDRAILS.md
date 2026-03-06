# Guardrails

> Last Updated: 06/03/2026

This file explains the repository safety model in plain language. The machine-readable rule files live in `guardrails/`. The active code-backed enforcement lives mainly in:

- `workspace/scheduler/guardrail_enforcer.py`
- `workspace/scheduler/service.py`
- `workspace/scheduler/dispatcher.py`
- `workspace/memory/runtime_service.py`
- `workspace/tools/`

## Enforced Today

- Cross-agent coordination must go through Redis Streams.
- Direct agent-to-agent calls are forbidden.
- Task ownership is enforced for planner, coder, tester, reviewer, and system-owned tasks.
- Invalid task status transitions are rejected and audited.
- Coder may not modify tests or CI configuration.
- Tester may modify tests and fixtures only.
- Reviewer may block progression instead of silently passing work through.
- Review, approval, and merge remain CI-gated.
- Merge cannot complete without recorded human approval metadata.
- Trusted source checks apply to `human_approval_gate`, `merge_task`, and `rerun_ci`.
- Duplicate scheduler events are ignored before state mutation and recorded in `audit_log`.
- Raw conversation-style memory payloads are rejected at runtime.
- Filesystem scope and terminal allowlists are enforced by the local tool contracts, with rejection/output artifacts written under `.context/tool-audit/`.

## Partial Today

- Git checkpoint workflow exists and is documented, but scheduler-side attestation of that checkpoint is not yet automatic.
- Tool policy is local-contract enforcement, not yet a full runtime-wide sandbox or centralized audit stream.
- Audit trails are strong for scheduler and memory paths, but not yet complete for every prompt, action, and artifact boundary.

## Remaining Gaps

- Full external validation against real Gitea and Argo boundaries.
- Broader tool telemetry in `system_events`, not only local artifact files.
- Stronger secrets redaction and storage review across the entire runtime surface.

## Non-Negotiable Policy

- No task may bypass CI as the source of truth.
- No task may merge to `main` without human approval.
- No raw conversation transcript belongs in long-term memory.
- No agent should mutate files outside the selected repository scope.
- No agent should publish fake success to replace CI outcomes.
- No destructive or privileged action should happen without an explicit approval path.

## Production-Readiness Standard

Before calling this production-hardened, the repository still needs:

- fully validated external CI/code-host integration
- broader operator observability and incident-grade audit collection
- stronger checkpoint attestation and tool execution telemetry

The intent remains simple: the rules should be true because code enforces them, not because documentation says so.
