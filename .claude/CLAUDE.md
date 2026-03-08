# Claude Extension Layer

Claude-specific extension only. Non-authoritative relative to [`AGENTS.md`](../AGENTS.md).

## Layering

| Source | Scope |
|--------|-------|
| [`../AGENTS.md`](../AGENTS.md) | Global repository contract |
| [`../.agent/rules/`](../.agent/rules/README.md) | Shared operator rules |
| [`../.agent/workflows/`](../.agent/workflows/README.md) | Shared workflow playbooks |
| [`rules/`](./rules) | Claude-only extensions |
| [`memory/`](./memory) | Claude durable memory |

## Conventions

- Keep `.claude/rules/*.md` narrow and Claude-specific.
- Move shared behavior to `.agent/rules/` or `.agent/workflows/`.
- Keep `.claude/memory/*.md` distilled, durable, and free of raw transcripts.
