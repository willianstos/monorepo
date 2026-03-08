# MCP Home Lab Servers — Canonical Inventory

Last Updated: 08/03/2026

Authoritative inventory of MCP servers configured in the home lab stack.
Canonical rule: [`.agent/rules/MCP_SERVERS.md`](../.agent/rules/MCP_SERVERS.md).
Single source of truth: [`bootstrap/mcp-registry.toml`](../bootstrap/mcp-registry.toml).
Generated outputs: [`bootstrap/templates/`](../bootstrap/templates/).

## Mode Models

This repository can run in two MCP modes:

- **P1 Platform Mode** (minimum required for Epic 1 operations)
- **P2 Factory Mode** (industry-scale agent factory: multi-CLI + OAuth-driven integrations)

Keep both modes aligned from the registry and roll them out through `.agent/workflows/mcp-fleet.md`.

## Source Chain

1. Edit `bootstrap/mcp-registry.toml`
2. Render with `python3 bootstrap/render_mcp_configs.py templates`
3. Apply with governance wrappers
4. Verify with healthchecks and client-specific smoke tests

### P1 Core Servers (active)

| Server | Package | Purpose | Claude Code CLI | Codex WSL | Codex Windows | Claude Desktop |
|--------|---------|---------|:--------------:|:---------:|:-------------:|:--------------:|
| `future-agents-local` | `workspace.mcp.server` (stdio) | bounded scheduler and memory tools via local repo server | ✓ | ✓ | ✓ | ✓ |
| `docker` | `workspace.mcp.docker_server` (stdio) | Docker control and inspection tools | ✓ | ✓ | ✓ `wsl.exe` | ✓ `wsl.exe` |
| `git` | `@cyanheads/git-mcp-server` | repository operations | ✓ | ✓ | ✓ | ✓ |
| `fetch` | `mcp-server-fetch` (uvx on WSL / npx on Windows) | HTTP/REST helper | ✓ | ✓ | ✓ | ✓ |
| `redis` | `@modelcontextprotocol/server-redis@2025.4.25` | scheduler and stream debug | ✓ | ✓ | ✓ | ✓ |

### P2 Full-stack Factory Servers (approved expansion)

These servers are required for multi-agent full-stack composition workflows and should be kept in sync when the factory profile is enabled.

| Server | Package | Purpose | Claude Code CLI | Codex WSL | Codex Windows | Claude Desktop |
|--------|---------|---------|:--------------:|:---------:|:-------------:|:--------------:|
| `filesystem` | `@modelcontextprotocol/server-filesystem@2026.1.14` | project/file operations in whitelisted roots | ✓ | ✓ | ✓ | ✓ |
| `context7` | `@upstash/context7-mcp@2.1.2` | docs lookup and reference search | ✓ | ✓ | ✓ | ✓ |
| `tavily` | `tavily-mcp@0.2.17` | web and issue research | ✓ | ✓ | ✓ | ✓ |
| `TestSprite` | `@testsprite/testsprite-mcp@0.0.30` | test/QA automation surfaces | ✓ | ✓ | ✓ | ✓ |
| `chrome-devtools` | `chrome-devtools-mcp@0.19.0` | UI and screenshot debugging hooks | ✓ | ✓ | ✓ | ✓ |
| `ai-context` | `@ai-coders/context@0.7.1` | context-aware agent utilities and schema helpers | ✓ | ✓ | ✓ | ✓ |

Total active set: **11 MCP servers**.

### P2 Deferred

- `postgres` not yet installed. Requires passworded connection management via `.env` or secret store before inclusion.

## Canonical Commands

### Claude Code CLI (WSL) — `claude mcp add`

```bash
claude mcp add future-agents-local -s user -- bash --noprofile --norc -lc "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-future-agents.sh"
claude mcp add docker -s user -- bash --noprofile --norc -lc "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-docker.sh"
claude mcp add git    -s user -- npx -y @cyanheads/git-mcp-server
claude mcp add fetch  -s user -- uvx mcp-server-fetch
claude mcp add redis  -s user -- npx -y @modelcontextprotocol/server-redis@2025.4.25 redis://127.0.0.1:6380
```

### Codex CLI — WSL (`~/.codex/config.toml`)

```toml
[mcp_servers.future-agents-local]
command = "bash"
args = ["--noprofile", "--norc", "-lc", "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-future-agents.sh"]
startup_timeout_sec = 120

[mcp_servers.docker]
command = "bash"
args = ["--noprofile", "--norc", "-lc", "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-docker.sh"]
env = { DOCKER_HOST = "unix:///var/run/docker.sock" }
startup_timeout_sec = 40

[mcp_servers.redis]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-redis@2025.4.25", "redis://127.0.0.1:6380"]
startup_timeout_sec = 40

[mcp_servers.fetch]
command = "uvx"
args = ["mcp-server-fetch==2025.4.7"]
startup_timeout_sec = 20
```

(`git`, `filesystem`, `context7`, `tavily`, `TestSprite`, `chrome-devtools`, `ai-context` are included in the generated managed templates and are omitted here for brevity.)

### Codex CLI — Windows (`C:\Users\Zappro\.codex\config.toml`)

```toml
[mcp_servers.future-agents-local]
command = "wsl.exe"
args = ["-d", "Ubuntu-24.04", "bash", "--noprofile", "--norc", "-lc", "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-future-agents.sh"]
startup_timeout_sec = 120

[mcp_servers.docker]
command = "wsl.exe"
args = ["-d", "Ubuntu-24.04", "bash", "--noprofile", "--norc", "-lc", "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-docker.sh"]
startup_timeout_sec = 40

[mcp_servers.redis]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-redis@2025.4.25", "redis://127.0.0.1:6380"]
startup_timeout_sec = 40

[mcp_servers.fetch]
command = "npx"
args = ["-y", "mcp-server-fetch"]
startup_timeout_sec = 20
```

### Claude Desktop — Windows (`AppData\Roaming\Claude\claude_desktop_config.json`)

```json
"future-agents-local": { "command": "wsl.exe", "args": ["-d", "Ubuntu-24.04", "bash", "--noprofile", "--norc", "-lc", "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-future-agents.sh"] },
"docker": { "command": "wsl.exe", "args": ["-d", "Ubuntu-24.04", "bash", "--noprofile", "--norc", "-lc", "cd /mnt/c/Users/Zappro/repos/01-monorepo && exec bash bootstrap/mcp-launch-docker.sh"] },
"git":    { "command": "npx", "args": ["-y", "@cyanheads/git-mcp-server"] },
"fetch":  { "command": "npx", "args": ["-y", "mcp-server-fetch"] },
"redis":  { "command": "npx", "args": ["-y", "@modelcontextprotocol/server-redis@2025.4.25", "redis://127.0.0.1:6380"] }
```

## Rules

- Never hardcode API keys or DB passwords in versioned config files. Use process env, `env/.env`, or ignored local overlay files.
- Dockerized services accessed from containers must use `172.17.0.1`, not `localhost`.
- `localhost` is fine for services accessed from WSL host processes (e.g. Redis on `6380`).
- Repo-backed WSL launchers should stay under `bootstrap/` and use deterministic shell flags.
- Manage live configs only through `bootstrap/render_mcp_configs.py`, the governance wrappers, and the flows documented in `.agent/rules/MCP_SERVERS.md` and `docs/windows11-wsl2-mcp-governance.md`.

## Verification Checklist

```bash
# Claude Code CLI
claude mcp list

# Docker socket accessibility
# from WSL: docker ps

docker ps

# Redis (only when stack is up)
redis-cli -h 127.0.0.1 -p 6380 ping  # → PONG

# MCP reachability smoke (factory mode)
# ask a client for a fetch call or test command against redis/docker futures
```
