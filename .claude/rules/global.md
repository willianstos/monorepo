# Global Claude Rules

Claude-only reminders. Canonical rules remain in [`AGENTS.md`](../../AGENTS.md); shared operator rules in [`.agent/rules/`](../../.agent/rules/README.md).

- Do not invent new primary agents, alternate orchestration layers, or direct agent-to-agent coordination.
- Do not weaken tests, bypass scheduler ownership, or claim success without evidence.
- Do not persist raw conversation, raw prompts, or raw logs into durable memory.
- Prefer one relevant shared skill at a time. Do not bulk-load `.agent/catalogs/`.
