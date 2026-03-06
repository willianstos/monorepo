# Guardrails

> Last Updated: 2026-03-06

This file explains the repository safety model in plain language. Machine-readable rule files live in `guardrails/`. Active code-backed enforcement lives mainly in:

- `workspace/scheduler/guardrail_enforcer.py`
- `workspace/scheduler/service.py`
- `workspace/memory/runtime_service.py`
- `workspace/tools/`
- `workspace/providers/` and `workspace/gateway/` for model routing defaults

## Enforced In Code Today

- Cross-agent coordination goes through Redis Streams only.
- Direct agent-to-agent calls are forbidden.
- Task ownership is enforced for `planner`, `coder`, `tester`, `reviewer`, and system-owned tasks.
- Invalid task status transitions are rejected and audited.
- `coder` may not modify tests or CI configuration.
- `tester` may modify tests and fixtures only.
- `reviewer` may block progression and may not mutate code as part of review.
- Review, approval, and merge remain CI-gated.
- Merge cannot complete without recorded human approval metadata.
- Trusted source checks apply to `human_approval_gate`, `merge_task`, and `rerun_ci`.
- Duplicate scheduler events are ignored before state mutation and recorded in `audit_log`.
- Raw conversation-style memory payloads are rejected at runtime.
- Filesystem scope and terminal allowlists are enforced by local tool contracts, with audit artifacts written under `.context/tool-audit/`.

## Repository Policy That Must Remain True

- Local model misuse is a policy violation.
- Ollama `qwen3.5:9b` is helper-only and non-authoritative.
- `qwen3.5:9b` must not own final code generation, auth or secrets changes, migrations, CI edits, guardrail design, merge decisions, review sign-off, or scheduler authority.
- CI is authoritative. Agents may not replace CI outcomes with self-reported success.
- Merge to `main` always requires both passing CI and explicit human approval.
- Raw conversations must never enter durable memory.
- Tool use must stay bounded, auditable, and scoped to the selected repository.
- Test weakening is forbidden.

## Current Enforcement Edge

- Model authority is enforced today through routing defaults, gateway exposure, repository instructions, and config policy. The scheduler does not yet inspect model provenance on every event.
- Tool policy is enforced locally in tool contracts, not yet as a centralized scheduler-wide policy plane.
- Audit trails are strong for scheduler and memory paths, but not yet complete for every prompt, action, and artifact boundary.

## Remaining Gaps Before Production-Hardened

- Full external validation against real code-host and CI boundaries.
- Broader tool telemetry in `system_events`, not only local artifact files.
- Stronger secrets redaction and storage review across the full runtime surface.
- Stronger checkpoint attestation and broader operator observability.

## Non-Negotiable Rules

- No task may bypass CI as the source of truth.
- No task may merge to `main` without human approval.
- No raw conversation transcript belongs in durable memory.
- No agent should mutate files outside the selected repository scope.
- No agent should publish fake success to replace CI outcomes.
- No destructive or privileged action should happen without an explicit approval path.

The intent remains simple: repository rules should be auditable, minimal, and increasingly code-enforced rather than hidden in prompts.
