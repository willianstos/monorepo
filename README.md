# 01-monorepo

> Last Updated: 2026-03-06

Local-first AI coding assistant workspace for controlled software delivery. This repository standardizes Codex, Claude Code, Antigravity, and a strictly limited local Ollama helper model around one event-driven architecture.

## Current Maturity

Current classification: `release candidate for local controlled operation`

Implemented and fixed today:
- the scheduler is a separate service
- Redis Streams is the only event and task bus
- DAG state persists in Redis
- agents communicate only through events
- CI is authoritative
- merge to `main` requires recorded human approval

This is not a fully autonomous engineer and not a general production platform. It is a governed assistant workspace with real runtime enforcement and remaining RC-stage gaps documented in [`docs/release-candidate.md`](./docs/release-candidate.md).

## Model Routing Standard

- Active authoritative CLI lanes: Codex CLI and Claude Code CLI.
- Codex is the primary code generation and editing engine.
- Claude Code is the primary planning, architecture, deep debugging, and review-assistance engine.
- Ollama `qwen3.5:9b` is helper-only for cheap, bounded, low-risk tasks such as classification, summarization, extraction, and memory distillation.
- Antigravity is an IDE environment and shared workflow consumer, not headless runtime authority.
- Gemini is legacy-only and out of scope for this repository standard.

The canonical routing policy lives in [`docs/model-routing.md`](./docs/model-routing.md). The hard local-model boundary lives in [`docs/local-model-policy.md`](./docs/local-model-policy.md).

## Instruction Hierarchy

- [`AGENTS.md`](./AGENTS.md): canonical Codex-facing repository contract.
- [`CLAUDE.md`](./CLAUDE.md) and [`.claude/CLAUDE.md`](./.claude/CLAUDE.md): canonical Claude-facing instruction layer.
- [`.agent/`](./.agent/README.md): shared skills, workflows, and tool-agnostic memory notes.
- [`GUARDRAILS.md`](./GUARDRAILS.md): operator-facing safety model.
- [`WORKSPACE.md`](./WORKSPACE.md): shared runtime boundaries and ownership.

## Core Workflow

```text
issue/request
-> planner
-> coder
-> tester
-> reviewer
-> human approval
-> merge
```

CI failure path:

```text
ci_failed
-> fix_task
-> rerun_ci
-> ci_passed
-> continue blocked review/approval/merge path
```

Required invariants:
- no direct agent-to-agent calls
- no bypass of CI
- no merge to `main` without human approval
- no raw conversation logs in durable memory
- no local helper model authority over coding, security, or merge decisions

## Quick Start

1. Create the local environment and install dependencies.

```bash
python3 -m venv .context/.venv
.context/.venv/bin/python -m pip install -e .[dev]
```

2. Run the fast validation set.

```bash
.context/.venv/bin/python -m pytest workspace/scheduler/test_orchestration.py -q
.context/.venv/bin/python -m mypy workspace
.context/.venv/bin/python -m ruff check workspace projects
```

3. Start Redis for local scheduler validation.

```bash
docker compose -f docker-compose.redis.yml up -d redis-integration
```

4. Run the Redis-backed integration test and controlled flow.

```bash
REDIS_INTEGRATION_PORT=6380 REDIS_INTEGRATION_DB=15 .context/.venv/bin/python -m pytest workspace/scheduler/test_redis_integration.py -q
REDIS_PORT=6380 REDIS_DB=15 .context/.venv/bin/python bootstrap/local_validation.py controlled-flow --reset-db --graph-id rc-local-001 --objective "Release-candidate controlled flow" --project-name 01-monolito
```

## CI and PR Gate

All changes to `main` must pass through a pull request with automated CI validation:

```text
feature branch -> PR to main -> CI checks green -> human approval -> merge
```

The Gitea Actions pipeline validates lint (ruff), types (mypy), unit tests (pytest), and Redis integration tests on every PR. See [`docs/gitea-pr-validation.md`](./docs/gitea-pr-validation.md) for operator setup, runner configuration, and branch protection settings.

## Key Docs

- [Architecture](./docs/architecture.md)
- [Model Routing](./docs/model-routing.md)
- [Local Model Policy](./docs/local-model-policy.md)
- [CLI Auth And MCP](./docs/cli-auth-and-mcp.md)
- [Guardrails](./GUARDRAILS.md)
- [Workspace Conventions](./WORKSPACE.md)
- [Local Validation Runbook](./docs/local-validation.md)
- [Release Candidate Status](./docs/release-candidate.md)
- [Gitea PR Validation](./docs/gitea-pr-validation.md)
