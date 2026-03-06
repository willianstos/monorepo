# Workspace Conventions

## Purpose

The monorepo separates shared orchestration runtime from concrete target projects:

- `workspace/`: shared multi-agent runtime, graph blueprints, providers, tools, and memory adapters.
- `projects/`: projects the agent system can inspect and modify.
- `.agent/`: local agent skills, vendored skill catalogs, workflow definitions, backups, and agent-local memory notes.
- `env/`: environment templates and deployment-local configuration assets.
- `bootstrap/`: idempotent host and WSL bootstrap plus healthcheck scripts.
- `docs/`: human-readable architecture and operating documentation.

## Architectural Rules

- Shared agent orchestration logic lives under `workspace/`.
- Provider-specific LLM wiring lives under `workspace/providers/`.
- Runtime bootstrapping and task coordination live under `workspace/runtime/`.
- Declarative agent/model/tool settings live under `workspace/config/`.
- Target business applications live under `projects/`.
- Agent nodes may coordinate tools, but tool adapters remain isolated in `workspace/tools/`.
- Cross-agent coordination must move through Redis Streams and Redis-backed scheduler state, not implicit globals.
- Project-specific behavior should be configured, not hardcoded into the graph.

## Operating Model

- The default happy path is `issue_created -> planner -> coder -> tester -> reviewer -> human approval -> merge`.
- Provider choice should remain swappable through model profiles, not hardcoded in agent code.
- CI failures already route into scheduler-managed fix loops before review and merge can proceed.
- Reviewer failures and rejected human approval already block graph progression instead of silently retrying.
- Scheduler event handling is now idempotent by persisted event ID, with `audit_log` emitted for duplicate suppression and rejected transitions.
- Runtime memory writes now enforce structured `MemoryRecord` payloads and reject raw transcript-style fields on the write path.
- Minimal Redis-backed observability is available through scheduler metrics and runtime health snapshots.
- Several LangGraph agent nodes still behave like placeholders even though the scheduler/event bus layer is implemented.
- Every tool action should still become fully auditable, replayable, and policy-checked.
- Memory still needs richer long-term storage and retrieval beyond the current Redis-backed runtime sink.

## Editing Guide

- Edit `README.md` when the repository overview or next-build narrative changes.
- Edit `WORKSPACE.md` when ownership boundaries or orchestration rules change.
- Edit `GUARDRAILS.md` and `guardrails/` together when agent safety policy changes.
- Edit `bootstrap/` when host, WSL, Git, Docker, or Gitea bootstrap flows change.
- Edit `.context/` when adding reusable documentation, agent playbooks, or generated artefacts for future runs.
