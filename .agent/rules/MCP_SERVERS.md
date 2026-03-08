# MCP Servers — Invariant Rules

Canonical inventory: [`docs/mcp-homelab-servers.md`](../../docs/mcp-homelab-servers.md).

## Hard Constraints

1. **Never hardcode API keys, DB passwords, or secrets** in versioned MCP config files. Use environment variables or `.env` files (gitignored).

2. **Keep all clients in sync.** When adding or removing an MCP server, update all four targets:
   - Claude Code CLI (WSL) — `claude mcp add/remove -s user`
   - Codex CLI WSL — `~/.codex/config.toml`
   - Codex CLI Windows — `C:\Users\Zappro\.codex\config.toml`
   - Claude Desktop Windows — `AppData\Roaming\Claude\claude_desktop_config.json`

3. **Dockerized service addresses from containers:** use `172.17.0.1` (Docker bridge gateway), not `localhost`. See [`.agent/rules/GITEA_NETWORKING.md`](./GITEA_NETWORKING.md).

4. **`localhost` is correct** for services accessed from WSL2 host processes (e.g., Redis integration on port 6380).

5. **P2 — `postgres` not yet installed.** Requires connection string with DB password. Do not add until a `.env`-based secret injection pattern is in place.

## Installed Servers (P1 — Active)

| Server | Package | Notes |
|--------|---------|-------|
| `docker` | `@modelcontextprotocol/server-docker` | Needs Docker socket |
| `git` | `@cyanheads/git-mcp-server` | No special deps |
| `fetch` | `mcp-server-fetch` | `uvx` in WSL; `npx` in Windows |
| `redis` | `@modelcontextprotocol/server-redis` | Only functional when Redis stack is up |
