# Shared Workflows

> Last Updated: 2026-03-06

This directory stores workspace-owned shared workflows. Antigravity uses them directly, and Codex or Claude can follow the same checked-in steps without relying on hidden prompts.

## Naming Convention

- `workflows/<name>.md` is the canonical workflow file.
- The workflow basename is the intended slash command or operator entrypoint.
- `git.md` maps to `/git`.

## Available Workflows

- [`/git`](./git.md) — checkpoint and push the active feature branch by default; merge into `main` only with explicit `--merge-main`.

## Authoring Rules

- Keep workflows thin and explicit.
- Prefer repository scripts when the workflow contains executable logic.
- Keep dangerous Git operations out of workflows by default.
- Keep workflows usable from Antigravity, Codex, and Claude with minimal platform-specific branching.
