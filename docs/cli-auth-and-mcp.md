# CLI Auth And MCP

> Last Updated: 2026-03-06

Practical operator notes only.

## Codex

- Use `codex login` to manage sign-in.
- ChatGPT/device-style login is the preferred CLI path when available.
- API-key-driven configuration remains valid when that is the environment standard.
- `AGENTS.md` is the repo-native Codex instruction layer.
- Prefer shared skills under `.agent/` over deprecated custom prompt patterns.
- Use `codex mcp` to manage MCP servers for Codex.

## Claude

- Claude uses `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/`, and `.claude/memory/` as the checked-in project layer.
- Claude CLI exposes `claude auth`, `claude setup-token`, and `claude mcp` for operator management.
- Inside Claude, `/mcp` is the operator path for MCP connections and auth management.
- Inside Claude, `/memory` is the operator path for memory handling.
- Keep terminal, IDE, and desktop sessions aligned with the same checked-in instructions and memory files.
