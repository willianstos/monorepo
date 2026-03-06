# 01-monorepo — Local-First AI Coding Assistant Workspace

> Last Updated: 06/03/2026

A local-first, event-driven AI coding assistant monorepo for controlled software delivery.

This repository is designed as a **human-guided coding workspace**, not an autonomous software company. It uses a Redis-backed scheduler, Redis Streams event bus, CI-authoritative task progression, and explicit human approval before merge.

## What this repository is

This project provides a governed orchestration layer for AI-assisted software work:

- **Local-first** runtime and model routing
- **Event-driven** task orchestration with Redis Streams
- **Redis-backed DAG persistence**
- **Minimal primary agents**:
  - Planner
  - Coder
  - Tester
  - Reviewer
- **CI-authoritative workflow**
- **Human approval required before merge**
- **Guardrails enforced in code**

## What is enforced today

The current implementation already includes:

- Redis Streams as the only orchestration bus
- Scheduler as a separate service
- Redis-backed DAG/task persistence
- Trusted-source enforcement for protected system tasks
- Guardrail enforcement in scheduler/runtime paths
- CI fix-loop orchestration
- Structured `audit_log` events on `system_events`
- Runtime memory-write validation for structured records
- Redis-backed scheduler metrics / health snapshot
- Duplicate-event idempotency and dead-letter handling

## What is still partial

Some areas are intentionally not yet fully productionized:

- Several LangGraph nodes still use placeholder execution behavior
- Tool adapters are contracts-first, not fully hardened
- Local Gitea/Argo flow is scaffolded, not yet fully exercised end-to-end
- Long-term memory is still a Redis-backed runtime sink, not a full durable knowledge layer

## Core operating rules

This repository preserves these fixed architecture decisions:

- Scheduler runs as a separate service
- Redis Streams is the only event/task bus
- DAG state is persisted in Redis
- Agents communicate only through events
- CI is authoritative
- Merge to main always requires human approval
- Task completion requires a `/git` checkpoint on the active feature branch
- This is an assistant-style system, not a fully autonomous engineer

## Primary workflow

Default graph:

```text
issue_created
→ plan_task
→ implement_task
→ test_task
→ review_task
→ human_approval_gate
→ merge_task
````

On CI failure:

```text
ci_failed
→ fix_task
→ rerun_ci
→ continue only after ci_passed
```

## Repository layout

```text
01-monorepo/
├── .agent/        # local skills, workflows, memory assets, vendored catalogs
├── .claude/       # Claude-specific project memory/instructions
├── .codex/        # Codex-specific memory/rules
├── .context/      # generated project context and reusable docs
├── bootstrap/     # Windows + WSL bootstrap and healthcheck scripts
├── docs/          # human-authored architecture and operations docs
├── env/           # environment templates and examples
├── guardrails/    # rule files consumed by runtime/scheduler
├── projects/      # target repositories for future execution
└── workspace/
    ├── agents/
    ├── config/
    ├── event_bus/
    ├── gateway/
    ├── guardrails/
    ├── langgraph/
    ├── memory/
    ├── providers/
    ├── runtime/
    ├── scheduler/
    └── tools/
```

## Quick start

### Recommended environment

For the best developer experience, use this repository from **WSL Ubuntu 24.04**. OpenAI’s Codex IDE guidance recommends WSL workspaces for the best Windows experience. ([OpenAI Developers][4])

### Bootstrap

Run the local bootstrap / healthcheck flow from `bootstrap/`.

### Validate Python code

```bash
python -m compileall workspace docs
```

### Run scheduler tests

```bash
python -m unittest workspace.scheduler.test_orchestration -v
```

### Redis-backed integration tests

See the docs for the local Redis container flow and the exact commands to run integration coverage.

## Event model

Required Redis Streams:

* `agent_tasks`
* `agent_results`
* `ci_events`
* `memory_events`
* `system_events`

Base event envelope:

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

## Guardrails

This repository enforces these core boundaries:

* AI-generated code is untrusted until validated
* No direct push to main
* Required path:
  `branch → commit → CI → review → human approval → merge`
* Required completion checkpoint:
  `/git dd/mm/aaaa nome-randomico` on the active feature branch
* No direct agent-to-agent calls
* No raw conversation logs in long-term memory
* Coder cannot own tests
* Tester cannot weaken tests to force green CI
* Reviewer may block progression
* Protected system tasks require trusted sources

See:

* `GUARDRAILS.md`
* `docs/architecture.md`
* `workspace/scheduler/README.md`

## Current maturity

This repository is best described as:

**pre-production with a real orchestration core**

It already contains real stateful orchestration, runtime guardrails, audit logging, and CI-aware task progression. It is not just a scaffold, but it is also not yet a fully hardened production platform.

## Next milestones

1. Replace remaining placeholder LangGraph execution paths
2. Harden tool execution with policy + artifact capture
3. Exercise the local Gitea/Argo loop end-to-end
4. Expand observability and audit inspection flows
5. Evolve long-term memory beyond the current Redis-backed sink

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for local setup, validation, and doc update expectations.
