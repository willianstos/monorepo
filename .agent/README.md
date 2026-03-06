# Agent Workspace Assets

This directory now separates local workspace assets from vendored third-party catalogs.

## Layout

- `skills/` — curated local skills used directly by this workspace.
- `catalogs/` — vendored external skill repositories kept intact to preserve upstream structure.
- `backups/` — dated backups and migration leftovers kept for recovery.
- `workflows/` — Antigravity workflow entrypoints; the basename maps to the slash command, for example `git.md` -> `/git`.
- `memory/` — lightweight agent-local memory notes.

## Conventions

- Prefer placing workspace-owned skills directly under `skills/<skill-name>/SKILL.md`.
- Keep vendored catalogs intact under `catalogs/` instead of flattening their internal structure into the workspace root.
- Treat `backups/` as recovery material, not an active load path.
- If the skill router changes, keep `.agent/skills/` first and vendor catalogs as fallback sources.
