# MCP Servers — Invariant Rules

Authoritative source chain:

1. [`bootstrap/mcp-registry.toml`](../../bootstrap/mcp-registry.toml) is the single source of truth for MCP inventory, profiles, per-client overrides, launch wrappers, and timeout policy.
2. [`bootstrap/render_mcp_configs.py`](../../bootstrap/render_mcp_configs.py) is the only supported renderer/applier.
3. Generated repository artifacts under [`bootstrap/templates/`](../../bootstrap/templates/) are reviewable outputs, not hand-authored config.
4. Live targets under `~/.codex/`, `C:\Users\Zappro\.codex\`, `%APPDATA%\Claude\`, and project `.mcp.json` files are managed artifacts only.

Canonical inventory summary: [`docs/mcp-homelab-servers.md`](../../docs/mcp-homelab-servers.md).
Windows/WSL governance: [`docs/windows11-wsl2-mcp-governance.md`](../../docs/windows11-wsl2-mcp-governance.md).

## Hard Constraints

1. Never hand-edit generated MCP templates in `bootstrap/templates/`. Edit `bootstrap/mcp-registry.toml` and rerun the renderer.
2. Never hardcode API keys, DB passwords, or secrets in versioned MCP files. Use process env, `env/.env`, or ignored local overlays such as `codex_secrets.toml`, `codex_secrets.json`, `codex_wsl_secrets.json`, and `claude_secrets.json`.
3. Keep all managed surfaces aligned from the registry:
   - Codex WSL TOML
   - Codex Windows TOML
   - Codex Windows legacy JSON
   - Claude Desktop JSON
   - project `.mcp.json` fragments when project scope is enabled
4. Repo-backed WSL servers must launch only through stable wrappers in `bootstrap/`:
   - `bootstrap/mcp-launch-future-agents.sh`
   - `bootstrap/mcp-launch-docker.sh`
5. `future-agents-local` must keep `startup_timeout_sec = 120`. `docker` and `redis` must keep `40`. Do not downgrade these without a measured reason.
6. Dockerized services accessed from containers must use `172.17.0.1`, not `localhost`. WSL host processes may use `127.0.0.1`.
7. Windows clients must reach WSL-owned `future-agents-local` and `docker` through `wsl.exe`, never through duplicated Windows-native launch commands.
8. Live Codex configs are managed artifacts. Apply them only through:
   - `bash bootstrap/codex-governance-wsl.sh`
   - `pwsh -File .\bootstrap\codex-governance.ps1`
   - `pwsh -File .\bootstrap\mcp-fleet.ps1`
9. `postgres` stays deferred until a secret-injection contract exists for connection strings.

## Secret Resolution Policy

Live rendering resolves MCP secret env in this order:

1. current process environment
2. `env/.env`
3. ignored local overlay files in the repo root
4. existing env values already present in the live target

This order exists to keep versioned templates clean while avoiding secret loss during re-apply.

## Approved Inventory

Platform profile: `future-agents-local`, `docker`, `git`, `fetch`, `redis`

Factory profile: platform profile plus `filesystem`, `context7`, `tavily`, `TestSprite`, `chrome-devtools`, `ai-context`

Project profile: `future-agents-local`, `docker`, `filesystem`, `context7`, `tavily`, `TestSprite`, `chrome-devtools`, `ai-context`

## Operational Commands

Render templates:

```bash
python3 bootstrap/render_mcp_configs.py templates
```

Apply WSL Codex:

```bash
bash bootstrap/codex-governance-wsl.sh --apply
```

Apply Windows and WSL together:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\bootstrap\codex-governance.ps1 -Mode apply -ApplyWindows -ApplyWsl -ApplyClaudeDesktop
```
