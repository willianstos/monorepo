# CLI Auth and MCP

Operator notes for tool authentication and MCP server configuration. Model authority remains in [`AGENTS.md`](../AGENTS.md).

## Codex

- Sign in with `codex login`. ChatGPT/device-style login preferred; API-key config also valid.
- `AGENTS.md` is the repo-native Codex instruction layer.
- Prefer shared skills under `.agent/` over deprecated custom prompt patterns.
- Manage MCP servers with `codex mcp`. For the local Epic 1 server, see [Operator MCP Local Usage](./operator/mcp-local-usage.md).

## GitHub Mirror Auth

- GitHub mirror authentication for `git fetch/push` is owned by Git + GitHub CLI, not by MCP.
- Run `bash bootstrap/github-mirror-auth.sh ensure` once per WSL profile after setting `GITHUB_TOKEN` in `env/.env`.
- If PAT-based bootstrap still fails, run `bash bootstrap/github-mirror-auth.sh web` to replace local auth with browser-based `gh auth login -w`.
- Validate with `bash bootstrap/github-mirror-auth.sh check`.
- If HTTPS push is denied but the token has repo admin on the mirror, the helper provisions a repo-scoped SSH deploy key and rewrites only `remote.github.pushurl`.
- The SSH fallback stays pinned to `github-mirror-<owner>-<repo>` in `~/.ssh/config.d/` and to deploy key title `wsl-github-mirror-<owner>-<repo>`.
- If `check` still fails with `git push --dry-run`, the mirror remains non-writable from this WSL profile.

## Claude

- Project layer: `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/`, `.claude/memory/`.
- Operator management: `claude auth`, `claude setup-token`, `claude mcp`.
- Inside Claude Code: `/mcp` for MCP connections, `/memory` for memory handling.
- Keep terminal, IDE, and desktop sessions aligned with the same checked-in instructions.
- The repository MCP server is stdio-only in Epic 1. See [Operator MCP Local Usage](./operator/mcp-local-usage.md).
- Add home lab MCP servers with `claude mcp add <name> -s user -- <command> [args]` (user scope is shared across all projects and the AntiGravity IDE).
- Full home lab MCP inventory: [`docs/mcp-homelab-servers.md`](./mcp-homelab-servers.md).

## MCP Boundary

MCP is an edge adapter. It exposes bounded read-only scheduler and memory tools. It does not create a second control plane, bypass CI gates, or grant merge authority. See [`docs/contracts/mcp-boundary.md`](./contracts/mcp-boundary.md) for the full contract.

Installing the official GitHub MCP Server can add GitHub API tools to MCP-capable clients, but it does not replace Git remote authentication or fix HTTPS push failures on the `github` remote.
