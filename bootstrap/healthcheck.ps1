[CmdletBinding()]
param(
    [string]$WslDistro = "Ubuntu-24.04",
    [switch]$AllowOpen
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function Write-Warn([string]$Message) {
    Write-Host "[WARN] $Message"
}

function Write-Err([string]$Message) {
    Write-Host "[ERROR] $Message"
}

function Invoke-Wsl {
    param([string]$Command)
    & wsl.exe -d $WslDistro -- bash -lc $Command
}

function Test-SshProbe {
    param(
        [Parameter(Mandatory)] [string]$Target,
        [Parameter(Mandatory)] [string]$Port
    )

    $output = & ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=5 -o BatchMode=yes -T $Target -p $Port 2>&1
    $status = $LASTEXITCODE
    $text = ($output | Out-String).Trim()

    if ($text -match "Permission denied|successfully authenticated|Shell access is disabled") {
        return @{
            Success = $true
            Output = $text
            ExitCode = $status
        }
    }

    return @{
        Success = $false
        Output = $text
        ExitCode = $status
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$repoRootForWsl = ($repoRoot -replace "\\", "/")
$wslRepoRoot = (& wsl.exe -d $WslDistro -- bash -lc "wslpath -a '$repoRootForWsl'").Trim()
$wslHealthcheck = "cd '$wslRepoRoot' && bash bootstrap/healthcheck-wsl.sh"
if ($AllowOpen) {
    $wslHealthcheck += " --allow-open"
}

$failures = 0
$warnings = 0

try {
    $wslVersion = & wsl.exe -d $WslDistro -- uname -a
    Write-Info "WSL invocation OK: $wslVersion"
} catch {
    Write-Err "WSL invocation failed: $($_.Exception.Message)"
    $failures++
}

try {
    $linuxSmoke = Invoke-Wsl "printf '%s' ok"
    if ($linuxSmoke -eq "ok") {
        Write-Info "Linux command execution OK"
    } else {
        throw "Unexpected Linux smoke output: $linuxSmoke"
    }
} catch {
    Write-Err "Linux smoke check failed: $($_.Exception.Message)"
    $failures++
}

try {
    $response = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:3001/api/v1/version" -TimeoutSec 10
    Write-Info "Windows -> Gitea HTTP OK: $($response.Content)"
} catch {
    Write-Err "Windows -> Gitea HTTP failed: $($_.Exception.Message)"
    $failures++
}

try {
    $port222 = Test-NetConnection -ComputerName localhost -Port 222 -WarningAction SilentlyContinue
    if ($port222.TcpTestSucceeded) {
        Write-Info "Windows -> Gitea SSH port 222 OK"
    } else {
        Write-Err "Windows -> Gitea SSH port 222 failed"
        $failures++
    }
} catch {
    Write-Err "Windows -> Gitea SSH port check failed: $($_.Exception.Message)"
    $failures++
}

try {
    $giteaSsh = Test-SshProbe -Target "git@localhost" -Port "222"
    if ($giteaSsh.Success) {
        Write-Info "Windows -> Gitea SSH handshake OK"
    } else {
        Write-Err "Windows -> Gitea SSH handshake failed: $($giteaSsh.Output)"
        $failures++
    }
} catch {
    Write-Err "Windows -> Gitea SSH handshake failed: $($_.Exception.Message)"
    $failures++
}

try {
    $wslCheck = & wsl.exe -d $WslDistro -- bash -lc $wslHealthcheck
    $wslCheck | ForEach-Object { Write-Host $_ }
} catch {
    Write-Err "WSL healthcheck failed: $($_.Exception.Message)"
    $failures++
}

try {
    $sshProbe = & ssh -G github.com 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Info "Windows OpenSSH config is readable"
    } else {
        Write-Warn "Windows OpenSSH config probe returned exit code $LASTEXITCODE"
        $warnings++
    }
} catch {
    Write-Warn "Windows OpenSSH config probe failed: $($_.Exception.Message)"
    $warnings++
}

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -like "*:PATH*") {
    Write-Warn "User PATH contains a literal ':PATH' segment"
    $warnings++
}

if ($warnings -gt 0) {
    Write-Warn "Windows healthcheck completed with $warnings warning(s)."
}

if ($failures -gt 0) {
    Write-Err "Windows healthcheck failed with $failures critical issue(s)."
    exit 1
}

Write-Info "Windows hybrid healthcheck passed."
