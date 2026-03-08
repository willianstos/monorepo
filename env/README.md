# Environment

> Last Updated: 06/03/2026

This directory stores auditable environment templates for the monorepo and for the local hybrid Windows + WSL platform contract.

Current intent:

- `env/.env.example` is the canonical template for workspace defaults plus the local Gitea stack contract.
- `bootstrap/mcp-registry.toml` defines MCP server inventory and client-specific rendering rules.
- `bootstrap/render_mcp_configs.py` resolves MCP secrets from process env, then `env/.env`, then ignored local overlays.
- `bootstrap/github-mirror-auth.sh` performs the one-time GitHub mirror registration from local token state, first trying `gh` + Git credential helper and then falling back to a repo-scoped SSH deploy key when HTTPS push is denied.
- The SSH fallback uses pinned identifiers derived from the repo slug: SSH host alias `github-mirror-<owner>-<repo>` and deploy key title `wsl-github-mirror-<owner>-<repo>`.
- GitHub mirror auth is considered healthy only when `bootstrap/github-mirror-auth.sh check` passes the real `git push --dry-run` probe against the configured `github` remote.
- If SSH fallback cannot complete, the helper restores the previous `remote.github.pushurl` instead of leaving the mirror half-switched.
- Live secrets must stay outside the repo in the operational `.env` owned by the WSL stack.
- Placeholder markers such as `__generate_strong_secret__` must be replaced in the live `.env`, never committed as real values.

Recommended future contents:

- provider configuration templates
- per-environment policy files
- redacted examples for additional local infrastructure
