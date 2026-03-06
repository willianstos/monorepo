# Documentation Index

Welcome to the repository knowledge base. Start with the project overview, then dive into specific guides as needed.

## Core Guides
- [Repository Overview](../../README.md)
- [Contributor Guide](../../CONTRIBUTING.md)
- [Workspace Conventions](../../WORKSPACE.md)
- [Guardrails](../../GUARDRAILS.md)
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

## Repository Snapshot
- `.agent/` — Local agent assets: curated skills, vendored catalogs, workflow notes, backups, and memory stubs.
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
