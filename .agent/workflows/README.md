# Local Workflows

> Last Updated: 06/03/2026

This directory stores workspace-owned Antigravity workflows.

## Naming Convention

- `workflows/<name>.md` is the canonical workflow file.
- The workflow basename is the intended slash command.
- `git.md` is the workflow activated as `/git`.

## Available Workflows

- [`/git`](./git.md) — checkpoint and push the active feature branch by default; merge into `main` only with explicit `--merge-main`.

## Authoring Rules

- Keep workflows WSL-first for repository operations.
- Prefer calling repository scripts when the workflow contains executable logic.
- Keep dangerous Git operations out of workflows by default.
- Use merge commits for auditability only when the workflow is explicitly asked to update `main`.
- Keep Markdown workflows thin; operational behavior should live in scripts under `bootstrap/`.
