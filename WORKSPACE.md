# Workspace Layout

Directory structure and edit ownership. The global contract remains [`AGENTS.md`](AGENTS.md).

## Directories

| Path | Contents | Owner |
|------|----------|-------|
| `workspace/` | Scheduler, providers, tools, memory services | Runtime implementation |
| `projects/` | Target repositories | Project-specific seeds |
| `.agent/` | Rules, workflows, skills, catalogs, shared memory | Shared operator layer |
| `.claude/` | Claude rules, memory, extensions | Claude-specific |
| `docs/` | Human reference guides | Documentation |
| `.context/` | Generated state, plans, run evidence | Generated only — not policy |
| `guardrails/` | Machine-readable guardrail definitions | Complements `GUARDRAILS.md` |
| `bootstrap/` | WSL/Windows bootstrap, healthcheck, automation | Developer environment |

## Where Policy Lives

- Architecture, agents, models, memory, delivery: [`AGENTS.md`](AGENTS.md)
- Operator rules: [`.agent/rules/`](.agent/rules/README.md)
- Workflow playbooks: [`.agent/workflows/`](.agent/workflows/README.md)
- Git and PR policy: [`docs/guide_git.md`](docs/guide_git.md), [`.agent/workflows/git.md`](.agent/workflows/git.md), [`docs/gitea-pr-validation.md`](docs/gitea-pr-validation.md)
- Worktree isolation policy: [`docs/contracts/worktree-policy.md`](docs/contracts/worktree-policy.md), [`.agent/rules/WORKTREE_STANDARD.md`](.agent/rules/WORKTREE_STANDARD.md)
- Model routing: [`docs/model-routing.md`](docs/model-routing.md), [`docs/local-model-policy.md`](docs/local-model-policy.md)
- Safety model: [`GUARDRAILS.md`](GUARDRAILS.md)

## Edit Guide

| When | Edit |
|------|------|
| Global contract changes | [`AGENTS.md`](AGENTS.md) |
| Layout or ownership changes | [`WORKSPACE.md`](WORKSPACE.md) |
| Safety enforcement changes | [`GUARDRAILS.md`](GUARDRAILS.md) + `guardrails/` together |
| Shared operator rules | [`.agent/rules/`](.agent/rules/README.md) |
| Workflow playbooks | [`.agent/workflows/`](.agent/workflows/README.md) |
| Shared skills | [`.agent/skills/`](.agent/skills/README.md) |
| Claude extensions only | [`CLAUDE.md`](CLAUDE.md), [`.claude/`](.claude/CLAUDE.md) |
| Generated state or evidence | [`.context/`](.context/workflow/README.md) |
| Human entrypoint changes | [`README.md`](README.md) |
