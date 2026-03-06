# Documentation Index

> Last Updated: 2026-03-06

Welcome to the repository knowledge base. Start with the project overview, then dive into specific guides as needed.

## Core Guides
- [Repository Overview](../../README.md)
- [Codex Instructions](../../AGENTS.md)
- [Claude Instructions](../../CLAUDE.md)
- [Contributor Guide](../../CONTRIBUTING.md)
- [Workspace Conventions](../../WORKSPACE.md)
- [Guardrails](../../GUARDRAILS.md)
- [Model Routing](../../docs/model-routing.md)
- [Local Model Policy](../../docs/local-model-policy.md)
- [CLI Auth And MCP](../../docs/cli-auth-and-mcp.md)
- [Agent Rules](../../docs/agent_rules.md)
- [Hybrid Environment Audit (2026-03-05)](../../ENV_AUDIT_WINDOWS_WSL_2026-03-05.md)
- [Project Overview](./project-overview.md)
- [Architecture Notes](./architecture.md)
- [Development Workflow](./development-workflow.md)
- [Testing Strategy](./testing-strategy.md)
- [Glossary & Domain Concepts](./glossary.md)
- [Data Flow & Integrations](./data-flow.md)
- [Security & Compliance Notes](./security.md)
- [Tooling & Productivity Guide](./tooling.md)
- [Local Validation Runbook](./local-validation.md)
- [Release Candidate Status](../../docs/release-candidate.md)
- [Workflow Index](../../.agent/workflows/README.md)
- [Local Git Workflow](../../.agent/workflows/git.md)
- [Shared Agent Layer](../../.agent/README.md)
- [Finish With Git Rule](../../.agent/rules/finish-with-git.md)

## Repository Snapshot
- `.agent/` — Local agent assets: curated skills, vendored catalogs, workflow notes, rules, backups, and memory stubs.
- `.claude/` — Claude-specific rules plus curated durable project memory.
- `docs/` — Human-authored architecture and operating guides for the workspace.
- `env/` — Local environment templates and example configuration inputs.
- `GUARDRAILS.md` — Narrative explanation of repository safety rules.
- `guardrails/` — Machine-readable agent and CI guardrail policies.
- `bootstrap/` — Idempotent host and WSL bootstrap plus healthcheck scripts.
- `projects/` — Seed projects the multi-agent runtime may later inspect and modify.
- `pyproject.toml` — Python package metadata and tooling configuration.
- `README.md` — Top-level project overview and onboarding guide.
- `workspace/` — Python source for the implemented scheduler/event bus spine plus partial agent runtime, providers, and tools.
- `WORKSPACE.md` — Architectural boundaries between shared runtime and target projects.
- `.context/` — Generated AI context, documentation indexes, and reusable artefacts.

## Document Map
| Guide | File | Primary Inputs |
| --- | --- | --- |
| Project Overview | `project-overview.md` | Roadmap, README, stakeholder notes |
| Architecture Notes | `architecture.md` | ADRs, service boundaries, dependency graphs |
| Development Workflow | `development-workflow.md` | Branching rules, CI config, contributing guide |
| Testing Strategy | `testing-strategy.md` | Test configs, CI gates, known flaky suites |
| Glossary & Domain Concepts | `glossary.md` | Business terminology, user personas, domain rules |
| Data Flow & Integrations | `data-flow.md` | System diagrams, integration specs, queue topics |
| Security & Compliance Notes | `security.md` | Auth model, secrets management, compliance requirements |
| Tooling & Productivity Guide | `tooling.md` | CLI scripts, IDE configs, automation workflows |
| Local Validation Runbook | `local-validation.md` | Redis integration flow, audit inspection, local orchestration checks |
| Release Candidate Status | `../../docs/release-candidate.md` | RC maturity, exact validation commands, remaining hardening gaps |
| Model Routing | `../../docs/model-routing.md` | model authority split, escalation rules, local-helper lane |
| Local Model Policy | `../../docs/local-model-policy.md` | approved helper tasks, forbidden local-model tasks, token economy |
| CLI Auth And MCP | `../../docs/cli-auth-and-mcp.md` | Codex login, Claude auth, MCP and memory operator commands |
