# Windows 11 + WSL2 MCP Governance

Canonical operational rule: [`.agent/rules/MCP_SERVERS.md`](../.agent/rules/MCP_SERVERS.md).

## Goal

Keep MCP clients deterministic across Windows 11 and WSL Ubuntu 24.04 while making direct edits to live user configs the exception, not the default.

## Governance Model

1. `bootstrap/mcp-registry.toml` is the only hand-authored MCP inventory.
2. `bootstrap/render_mcp_configs.py` renders repo templates and applies live state.
3. `bootstrap/templates/` contains generated review artifacts only.
4. Live files under `~/.codex/`, `C:\Users\Zappro\.codex\`, `%APPDATA%\Claude\`, and project `.mcp.json` files are managed outputs.
5. Drift is recorded with SHA-256 manifests next to live targets.
6. Optional Windows Scheduled Task can re-apply governance.
7. Optional WSL immutable lock (`chattr +i`) blocks accidental edits to `~/.codex/config.toml`.

## Secret and Overlay Resolution

Live application resolves MCP secret env in this order:

1. process environment
2. `env/.env`
3. ignored local overlay files in the repo root
4. existing env already present in the live target

Supported local overlay files:

- `codex_secrets.toml`
- `codex_secrets.json`
- `codex_wsl_secrets.json`
- `claude_secrets.json`

These files are operator-owned local overlays. They must remain ignored and must not be copied into versioned templates.

## Managed Files

| Surface | Generated template | Live target |
|--------|---------------------|-------------|
| Codex WSL | `bootstrap/templates/codex-wsl-managed.toml` | `~/.codex/config.toml` |
| Codex Windows TOML | `bootstrap/templates/codex-windows-managed.toml` | `C:\Users\Zappro\.codex\config.toml` |
| Codex Windows legacy JSON | `bootstrap/templates/codex-windows-managed.json` | `C:\Users\Zappro\.codex\config.json` |
| Claude Desktop | `bootstrap/templates/claude-desktop-managed.json` | `%APPDATA%\Claude\claude_desktop_config.json` |
| Project fragments | `bootstrap/templates/project-managed.mcp.json` | `**/.mcp.json` under the chosen projects root |

## Launchers

| Launcher | Purpose |
|---------|---------|
| `bootstrap/mcp-launch-future-agents.sh` | Start `workspace.mcp.server` from repo root with stable shell flags |
| `bootstrap/mcp-launch-docker.sh` | Start `workspace.mcp.docker_server` with `DOCKER_HOST=unix:///var/run/docker.sock` |

These wrappers remove mutable ad hoc startup commands from client config and keep WSL-owned behavior versioned in one place.

## Apply Governance

### Regenerate managed templates

```bash
cd /mnt/c/Users/Zappro/repos/01-monorepo
python3 bootstrap/render_mcp_configs.py templates
```

### WSL only

```bash
cd /mnt/c/Users/Zappro/repos/01-monorepo
bash bootstrap/codex-governance-wsl.sh --apply
```

### WSL with immutable lock

```bash
cd /mnt/c/Users/Zappro/repos/01-monorepo
bash bootstrap/codex-governance-wsl.sh --apply --lock
```

### Windows 11

```powershell
Set-Location C:\Users\Zappro\repos\01-monorepo
pwsh -NoProfile -ExecutionPolicy Bypass -File .\bootstrap\codex-governance.ps1 -Mode apply -ApplyWindows -ApplyWsl -ApplyClaudeDesktop
```

### Windows 11 with periodic re-apply

```powershell
Set-Location C:\Users\Zappro\repos\01-monorepo
pwsh -NoProfile -ExecutionPolicy Bypass -File .\bootstrap\codex-governance.ps1 -Mode apply -ApplyWindows -ApplyWsl -ApplyClaudeDesktop -RegisterTask
```

## Check Drift

### WSL

```bash
cd /mnt/c/Users/Zappro/repos/01-monorepo
bash bootstrap/codex-governance-wsl.sh --check
```

### Windows

```powershell
Set-Location C:\Users\Zappro\repos\01-monorepo
pwsh -NoProfile -ExecutionPolicy Bypass -File .\bootstrap\codex-governance.ps1 -Mode check -ApplyWindows -ApplyWsl -ApplyClaudeDesktop
```

## Fleet Flow

For batch convergence across Windows, WSL, Claude Desktop, and project trees:

```powershell
Set-Location C:\Users\Zappro\repos\01-monorepo
pwsh -NoProfile -ExecutionPolicy Bypass -File .\bootstrap\mcp-fleet.ps1 -Scope all
```

Dry-run:

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File .\bootstrap\mcp-fleet.ps1 -Scope all -DryRun
```

## Maintenance Window

To change managed MCP behavior on purpose:

1. Edit `bootstrap/mcp-registry.toml`.
2. Regenerate templates.
3. Re-apply governance.
4. Re-enable the WSL immutable lock if used.

Unlock command:

```bash
cd /mnt/c/Users/Zappro/repos/01-monorepo
bash bootstrap/codex-governance-wsl.sh --unlock
```

## Operational Notes

- `future-agents-local` and `docker` are WSL-owned launch surfaces and must remain WSL-backed on Windows clients.
- `redis` stays on `127.0.0.1:6380` for host-side processes.
- Windows governance is stronger when paired with Scheduled Task re-apply.
- WSL governance is strongest when paired with `--lock`.
- If a target drifts, fix the registry or the secret overlay source, not the generated file.
