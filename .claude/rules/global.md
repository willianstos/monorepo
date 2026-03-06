# Global Claude Rules

- Follow `AGENTS.md` and `.claude/CLAUDE.md` before adding any extra behavior.
- Keep the repository assistant-style, local-first, CI-authoritative, and human-governed.
- Do not invent new primary agents, alternate orchestration layers, or direct agent-to-agent coordination.
- Do not weaken tests, bypass scheduler ownership, or claim success without evidence.
- Do not persist raw conversation, raw prompts, or raw logs into durable memory.
- Prefer one relevant shared skill at a time. Do not bulk-load `.agent/catalogs/`.
