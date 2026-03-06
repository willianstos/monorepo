# Agent Workspace Assets

> Last Updated: 2026-03-06

This directory is the shared agent layer for Codex, Claude-compatible workflows, and Antigravity. Keep it tool-agnostic where possible.

## Layout

- `skills/` — curated workspace-owned skills.
- `catalogs/` — vendored third-party skill repositories kept intact as references, not default load paths.
- `workflows/` — shared workflow playbooks. Antigravity consumes them directly; Codex and Claude can follow them manually.
- `memory/` — short tool-agnostic notes and distilled reminders.
- `rules/` — workspace-owned operating rules such as `/git`.
- `backups/` — recovery material only.

## Conventions

- Put workspace-owned skills under `skills/<skill-name>/SKILL.md`.
- Keep vendored catalogs under `catalogs/` without flattening them into the active skill tree.
- Select a category first and load one relevant skill when possible.
- Do not bulk-load skills or catalogs into model context.
- Summarize generated context before passing it onward.
- `.agent/memory/` is shared and tool-agnostic. `.claude/memory/` is Claude-specific durable project memory.
