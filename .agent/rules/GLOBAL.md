# Global Shared Rules

Shared operator reminders, not a second repository contract.

## Invariants

- Follow [`AGENTS.md`](../../AGENTS.md) for architecture, agent boundaries, model authority, memory rules, and delivery constraints.
- Do not treat IDE settings, local prompts, legacy files, or `.context/` artifacts as substitute authority.
- Use [`.agent/workflows/`](../workflows/README.md) for execution steps; `.context/` for state or evidence.
- Skills are capability-only. Governance does not live under `skills/`.

## Completion Discipline

- Every completed task needs `/git` checkpoint evidence before reporting completion.
- `/git` closes the feature-branch sync step. It does not replace PR review or merge.
- Git chain: [`AGENTS.md`](../../AGENTS.md) > [`docs/guide_git.md`](../../docs/guide_git.md) > [`workflows/git.md`](../workflows/git.md) > [`docs/gitea-pr-validation.md`](../../docs/gitea-pr-validation.md).
