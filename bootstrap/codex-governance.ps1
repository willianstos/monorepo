[CmdletBinding()]
param(
    [ValidateSet('apply', 'check')]
    [string]$Mode = 'apply',

    [string]$RepoRoot = '',

    [ValidateSet('Ubuntu-24.04', 'Ubuntu')]
    [string]$WslDistro = 'Ubuntu-24.04',

    [string]$WslUser = 'will',

    [switch]$ApplyWindows = $true,

    [switch]$ApplyWsl = $true,

    [switch]$ApplyClaudeDesktop,

    [switch]$RegisterTask,

    [switch]$LockWsl
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
}

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
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $command = Resolve-PythonCommand
    $fullArgs = @()
    if ($command.Length -gt 1) {
        $fullArgs += $command[1..($command.Length - 1)]
    }
    $fullArgs += (Join-Path $RepoRoot 'bootstrap\render_mcp_configs.py')
    $fullArgs += $Arguments
    & $command[0] @fullArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Renderer failed with exit code $LASTEXITCODE"
    }
}

function Convert-ToWslPath {
    param([string]$WindowsPath)
    $wslReady = ($WindowsPath -replace '\\', '/')
    return (& wsl.exe -d $WslDistro -- bash -lc "wslpath -a '$wslReady'").Trim()
}

function Invoke-WslRenderer {
    param(
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $wslRepoRoot = Convert-ToWslPath -WindowsPath $RepoRoot
    $escapedArgs = $Arguments | ForEach-Object { "'$($_ -replace "'", "'\\''")'" }
    $renderCommand = "cd '$wslRepoRoot' && python3 bootstrap/render_mcp_configs.py $($escapedArgs -join ' ')"
    & wsl.exe -d $WslDistro -- bash -lc $renderCommand
    if ($LASTEXITCODE -ne 0) {
        throw "WSL renderer failed with exit code $LASTEXITCODE"
    }
}

Invoke-WindowsRenderer -Arguments @('templates')

if ($ApplyWindows) {
    $windowsCodexRoot = Join-Path $env:USERPROFILE '.codex'
    Invoke-WindowsRenderer -Arguments @(
        $Mode,
        '--target', 'codex_windows_toml',
        '--output', (Join-Path $windowsCodexRoot 'config.toml'),
        '--manifest', (Join-Path $windowsCodexRoot 'config.governance.json')
    )
    Invoke-WindowsRenderer -Arguments @(
        $Mode,
        '--target', 'codex_windows_json',
        '--output', (Join-Path $windowsCodexRoot 'config.json'),
        '--manifest', (Join-Path $windowsCodexRoot 'config.legacy.governance.json')
    )
}

if ($ApplyWsl) {
    $wslTarget = "/home/$WslUser/.codex/config.toml"
    $wslManifest = "/home/$WslUser/.codex/config.governance.json"
    Invoke-WslRenderer -Arguments @(
        'templates'
    )
    Invoke-WslRenderer -Arguments @(
        $Mode,
        '--target', 'codex_wsl',
        '--output', $wslTarget,
        '--manifest', $wslManifest
    )

    if ($LockWsl -and $Mode -eq 'apply') {
        $wslRepoRoot = Convert-ToWslPath -WindowsPath $RepoRoot
        & wsl.exe -d $WslDistro -- bash -lc "cd '$wslRepoRoot' && bash bootstrap/codex-governance-wsl.sh --lock"
        if ($LASTEXITCODE -ne 0) {
            throw 'Failed to apply immutable lock to WSL Codex config.'
        }
        Write-Info 'Applied immutable lock to WSL Codex config.'
    }
}

if ($ApplyClaudeDesktop) {
    $claudeConfig = Join-Path $env:APPDATA 'Claude\claude_desktop_config.json'
    $claudeManifest = Join-Path $env:APPDATA 'Claude\claude_desktop_config.governance.json'
    Invoke-WindowsRenderer -Arguments @(
        $Mode,
        '--target', 'claude_desktop',
        '--output', $claudeConfig,
        '--manifest', $claudeManifest
    )
}

if ($RegisterTask) {
    $taskName = 'CodexMcpGovernance'
    $scriptPath = $MyInvocation.MyCommand.Path
    $pwsh = (Get-Command pwsh.exe -ErrorAction SilentlyContinue).Source
    if (-not $pwsh) {
        throw 'pwsh.exe not found; cannot register governance task.'
    }

    $arguments = @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', ('"{0}"' -f $scriptPath),
        '-Mode', 'apply',
        '-ApplyWindows',
        '-ApplyWsl'
    )
    $action = New-ScheduledTaskAction -Execute $pwsh -Argument ($arguments -join ' ')
    $triggerLogon = New-ScheduledTaskTrigger -AtLogOn
    $triggerStart = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5)
    $triggerStart.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(5) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration ([TimeSpan]::MaxValue)).Repetition
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($triggerLogon, $triggerStart) -Description 'Reapply repo-managed Codex MCP governance.' -Force | Out-Null
    Write-Info "Registered Scheduled Task: $taskName"
}
