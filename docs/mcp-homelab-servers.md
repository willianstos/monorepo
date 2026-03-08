# MCP Home Lab Servers — Canonical Inventory

Authoritative inventory of MCP servers configured in the home lab stack.
Canonical rule: [`.agent/rules/MCP_SERVERS.md`](../.agent/rules/MCP_SERVERS.md).

## Server Matrix

| Server | Package | Purpose | Claude Code CLI | Codex WSL | Codex Windows | Claude Desktop |
|--------|---------|---------|:--------------:|:---------:|:-------------:|:--------------:|
| `docker` | `@modelcontextprotocol/server-docker` | `docker ps`, `logs`, `inspect`, `exec` | ✓ | ✓ | ✓ | ✓ |
| `git` | `@cyanheads/git-mcp-server` | `log`, `diff`, `status`, `blame` | ✓ | ✓ | ✓ | ✓ |
| `fetch` | `mcp-server-fetch` (uvx/npx) | HTTP requests — Gitea API, health checks | ✓ | ✓ | ✓ | ✓ |
| `redis` | `@modelcontextprotocol/server-redis` | `KEYS`, `XREAD`, `GET` — scheduler/streams debug | ✓ | ✓ | ✓ | ✓ |

**Redis endpoint:** `redis://localhost:6380` (integration Redis; only reachable when stack is up).

**P2 — not installed yet:** `postgres` — requires connection string with DB password; do not hardcode in versioned configs.

## Installation Commands

### Claude Code CLI (WSL) — `claude mcp add`

```bash
claude mcp add docker -s user -- npx -y @modelcontextprotocol/server-docker
claude mcp add git    -s user -- npx -y @cyanheads/git-mcp-server
claude mcp add fetch  -s user -- uvx mcp-server-fetch
claude mcp add redis  -s user -- npx -y @modelcontextprotocol/server-redis redis://localhost:6380
```

Verify: `claude mcp list`

The AntiGravity IDE uses the same Claude Code extension and inherits the user-scoped config automatically.

### Codex CLI — WSL (`~/.codex/config.toml`)

```toml
[mcp_servers.docker]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-docker"]
startup_timeout_sec = 20

[mcp_servers.redis]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-redis", "redis://localhost:6380"]
startup_timeout_sec = 20

[mcp_servers.fetch]
command = "uvx"
args = ["mcp-server-fetch"]
startup_timeout_sec = 20
```

(`git` was already present — no change needed.)

### Codex CLI — Windows (`C:\Users\Zappro\.codex\config.toml`)

```toml
[mcp_servers.docker]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-docker"]
startup_timeout_sec = 20

[mcp_servers.git]
command = "npx"
args = ["-y", "@cyanheads/git-mcp-server"]
startup_timeout_sec = 30

[mcp_servers.redis]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-redis", "redis://localhost:6380"]
startup_timeout_sec = 20

[mcp_servers.fetch]
command = "npx"
args = ["-y", "mcp-server-fetch"]
startup_timeout_sec = 20
```

### Claude Desktop — Windows (`AppData\Roaming\Claude\claude_desktop_config.json`)

```json
"docker": { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-docker"] },
"git":    { "command": "npx", "args": ["-y", "@cyanheads/git-mcp-server"] },
"fetch":  { "command": "npx", "args": ["-y", "mcp-server-fetch"] },
"redis":  { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-redis", "redis://localhost:6380"] }
```

## Rules

- **Never hardcode API keys or DB passwords** in versioned config files. Use environment variables or `.env` (gitignored).
- **Dockerized services** accessed from within containers: use `172.17.0.1` (Docker bridge gateway), not `localhost`.
- **localhost is fine** for services accessed from the WSL2 host process itself (e.g. Redis on port 6380).
- Keep all three clients (Claude Code CLI, Codex WSL, Codex Windows) + Claude Desktop in sync when adding new servers.

## Verification Checklist

```bash
# Claude Code CLI
claude mcp list  # should show: docker, git, fetch, redis

# Docker socket accessible
docker ps

# Redis (only when stack is up)
redis-cli -h 127.0.0.1 -p 6380 ping  # → PONG

# Fetch — exercise via Claude chat
# ask Claude: "fetch http://172.17.0.1:3001/api/v1/version"
```
