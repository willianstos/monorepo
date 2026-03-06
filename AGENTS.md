# AGENTS.md

## Dev environment tips
- Use Python 3.11 or newer.
- Install dependencies with `python -m pip install -e .[dev]`.
- Use `python -m pytest` for validation and `python -m pytest -k <pattern>` for targeted iteration.
- Run `python -m ruff check workspace projects` and `python -m mypy workspace` before shipping runtime changes.
- Store generated artefacts in `.context/` so reruns stay deterministic.

## Testing instructions
- Execute `python -m pytest` to run the repository test suite.
- Prefer targeted runs such as `python -m pytest workspace/scheduler -k dag` while iterating.
- Re-run tests after changing contracts, routing logic, guardrails, or provider selection code.
- Add or update tests alongside runtime, scheduler, tool, or provider changes.

## PR instructions
- Follow Conventional Commits (for example, `docs(contributing): align repo instructions`).
- Cross-link new docs and playbooks in `.context/docs/README.md` and `.context/agents/README.md`.
- Attach sample payloads or generated markdown when schemas, prompts, or scaffolds change.
- Keep `README.md`, `WORKSPACE.md`, `GUARDRAILS.md`, and `CONTRIBUTING.md` aligned with structure changes.

## Repository map
- `.agent/` — local workspace skills, vendored skill catalogs, backups, workflows, and agent-local memory notes. Edit when curating local skills or reorganizing agent-facing assets.
- `docs/` — human-readable architecture, scheduler, and operating documentation. Edit when system contracts or workflow explanations change.
- `env/` — local environment templates such as `.env.example`. Edit when runtime configuration or provider setup changes.
- `guardrails/` — machine-readable policy files enforced by the scheduler. Edit when agent permissions or safety controls change.
- `GUARDRAILS.md` — narrative summary of the policy model. Edit when the intent behind rules or safety layers changes.
- `projects/` — target repositories that the workspace may later operate on. Edit when adding seed projects or project-specific guidance.
- `pyproject.toml` — Python package metadata plus lint, type-check, and test configuration. Edit when dependencies or tooling change.
- `README.md` — top-level overview and onboarding entry point. Edit when repository goals, layout, or next steps change.
- `workspace/` — Python blueprint code for agents, gateway, runtime, scheduler, memory, and tools. Edit when changing implementation contracts.
- `WORKSPACE.md` — shared-runtime operating model and architectural boundaries. Edit when ownership or orchestration rules change.
- `.context/` — AI context indexes, generated artefacts, and reusable playbooks. Edit when capturing knowledge for future runs.

## AI Context References
- Documentation index: `.context/docs/README.md`
- Agent playbooks: `.context/agents/README.md`
- Contributor guide: `CONTRIBUTING.md`
