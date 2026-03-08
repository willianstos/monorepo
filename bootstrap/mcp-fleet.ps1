<#
.SYNOPSIS
    Converge MCP config across managed Windows, WSL, Claude Desktop, and project surfaces.
#>

[CmdletBinding()]
param(
    [ValidateSet('all', 'windows', 'wsl', 'projects', 'codex', 'claude-desktop')]
    [string]$Scope = 'all',

    [string]$ProjectsRoot = "$env:USERPROFILE\repos",

    [ValidateSet('Ubuntu-24.04', 'Ubuntu')]
    [string]$WslDistro = 'Ubuntu-24.04',

    [string]$WslUser = 'will',

    [string]$ClaudeDesktopConfig = "$env:APPDATA\Claude\claude_desktop_config.json",

    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$GovernanceScript = Join-Path $RepoRoot 'bootstrap\codex-governance.ps1'
$RendererScript = Join-Path $RepoRoot 'bootstrap\render_mcp_configs.py'

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Resolve-PythonCommand {
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        return @($py.Source, '-3')
    }
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @($python.Source)
    }
    throw 'Python 3 executable not found on Windows PATH.'
}

function Invoke-WindowsRenderer {
    param([string[]]$Arguments)

    $command = Resolve-PythonCommand
    $fullArgs = @()
    if ($command.Length -gt 1) {
        $fullArgs += $command[1..($command.Length - 1)]
    }
    $fullArgs += $RendererScript
    $fullArgs += $Arguments
    & $command[0] @fullArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Renderer failed with exit code $LASTEXITCODE"
    }
}

$mode = if ($DryRun) { 'check' } else { 'apply' }

Write-Info "Scope=$Scope Mode=$mode"
Invoke-WindowsRenderer -Arguments @('templates')

if ($Scope -in @('all', 'windows', 'wsl', 'codex', 'claude-desktop')) {
    $governanceArgs = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $GovernanceScript,
        '-Mode', $mode,
        '-WslDistro', $WslDistro,
        '-WslUser', $WslUser
    )

    switch ($Scope) {
        'windows' {
            $governanceArgs += '-ApplyWindows'
        }
        'wsl' {
            $governanceArgs += '-ApplyWsl'
        }
        'claude-desktop' {
            $governanceArgs += '-ApplyClaudeDesktop'
        }
        default {
            $governanceArgs += '-ApplyWindows'
            $governanceArgs += '-ApplyWsl'
            if ($Scope -in @('all', 'codex')) {
                # Codex surfaces only by default.
            } else {
                $governanceArgs += '-ApplyClaudeDesktop'
            }
        }
    }

    if ($Scope -eq 'all') {
        $governanceArgs += '-ApplyClaudeDesktop'
    }

    & pwsh.exe @governanceArgs
    if ($LASTEXITCODE -ne 0) {
        throw "codex-governance.ps1 failed with exit code $LASTEXITCODE"
    }
}

if ($Scope -in @('all', 'projects')) {
    Invoke-WindowsRenderer -Arguments @(
        $mode,
        '--target', 'project_mcp',
        '--projects-root', $ProjectsRoot
    )
}

Write-Info 'MCP fleet run complete.'
