# Guardrails

Plain-language safety model. The repository contract remains [`AGENTS.md`](AGENTS.md). Machine-readable policy lives in `guardrails/`. Code-backed enforcement lives in `workspace/scheduler/`, `workspace/memory/`, `workspace/tools/`, and `workspace/providers/`.

## Enforced Today

- Redis Streams is the only cross-agent coordination path. Direct agent-to-agent calls are forbidden.
- Task ownership and status transitions are validated and audited.
- `coder` may not edit tests or CI configuration.
- `tester` may edit tests and fixtures only.
- `reviewer` may block progression but does not mutate code during review.
- Review, human approval, and merge are CI-gated.
- Merge requires recorded human approval metadata.
- Trusted-source checks apply to `human_approval_gate`, `merge_task`, and `rerun_ci`.
- Duplicate scheduler events are ignored before state mutation and recorded in `audit_log`.
- Raw conversation-style memory payloads are rejected at runtime.
- Tool contracts enforce bounded filesystem and terminal use, with audit artifacts under `.context/tool-audit/`.

## Non-Negotiables

- CI is authoritative. Agents do not replace CI outcomes with self-reported success.
- Merge to `main` requires passing CI and explicit human approval.
- Ollama `qwen3.5:9b` remains helper-only and non-authoritative.
- Raw conversations never enter durable memory.
- Tool use stays bounded, auditable, and repository-scoped.
- No agent mutates files outside the selected repository scope.
- No destructive or privileged action without an explicit approval path.
- Test weakening is forbidden.

## Current Enforcement Edge

These are known boundaries where enforcement exists but is not yet fully hardened:

- **Model provenance:** enforced through routing defaults, gateway configuration, and checked-in instructions. The scheduler does not yet verify model provenance on every event.
- **Tool policy:** enforced per-tool contract, not through a centralized scheduler-wide policy plane.
- **Audit completeness:** strong for scheduler and memory paths, not yet complete across every prompt, action, and artifact boundary.
