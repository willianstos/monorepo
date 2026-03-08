# Shared Operator Layer

Shared operator rules, workflows, skills, and memory. Does not replace [`AGENTS.md`](../AGENTS.md).

## Layout

| Directory | Contents |
|-----------|----------|
| `rules/` | Shared operational rules |
| `workflows/` | Executable workflow playbooks |
| `skills/` | Canonical shared skills and capability assets |
| `catalogs/` | Vendored third-party skill sources (reference only) |
| `memory/` | Short shared notes and distilled reminders |
| `backups/` | Recovery material |

## Conventions

- Repository-wide architecture, agent boundaries, model authority, and delivery rules belong in [`AGENTS.md`](../AGENTS.md), not here.
- Shared operator behavior: [`rules/`](./rules/README.md)
- Runnable workflow steps: [`workflows/`](./workflows/README.md)
- Capability assets: [`skills/`](./skills/README.md)
- `.context/` is generated state, not shared operator authority.
- Prefer one relevant skill at a time. Do not bulk-load catalogs.
- Keep `.agent/memory/` shared and tool-agnostic. Claude-specific memory belongs in `.claude/memory/`.
