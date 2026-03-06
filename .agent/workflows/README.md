# Local Workflows

This directory stores workspace-owned Antigravity workflows.

## Naming Convention

- `workflows/<name>.md` is the canonical workflow file.
- The workflow basename is the intended slash command.
- `git.md` is the workflow activated as `/git`.

## Available Workflows

- [`/git`](./git.md) — checkpoint current feature branch, push it, merge into `main`, push `main`, and create the next feature branch.

## Authoring Rules

- Keep workflows WSL-first for repository operations.
- Prefer calling repository scripts when the workflow contains executable logic.
- Keep dangerous Git operations out of workflows by default.
- Use merge commits for auditability when the workflow updates `main`.
- Keep Markdown workflows thin; operational behavior should live in scripts under `bootstrap/`.
