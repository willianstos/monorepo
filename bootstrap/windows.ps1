[CmdletBinding()]
param(
    [string]$ReferenceDate = "2026-03-05",
    [string]$WslDistro = "Ubuntu-24.04",
    [string]$WslUser = "will",
    [string]$DevHomeWsl = "/home/will/projetos",
    [string]$WindowsSshIdentity = "C:/Users/Zappro/.ssh/id_ed25519",
    [switch]$SkipWingetExport,
    [switch]$SkipEditorExport,
    [switch]$SkipProfileBridge,
    [switch]$FixUserPath,
    [switch]$FixSshAcl,
    [switch]$RefreshUserSshConfig
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info([string]$Message) {
    Write-Host "[INFO] $Message"
}

function New-ManagedDirectory([string]$Path) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

function Backup-File {
    param(
        [Parameter(Mandatory)] [string]$SourcePath,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    if (-not (Test-Path -LiteralPath $SourcePath)) {
        return
    }

    New-ManagedDirectory -Path $BackupRoot
    $safeName = $SourcePath.Replace(":", "").Replace("\", "__")
    Copy-Item -LiteralPath $SourcePath -Destination (Join-Path $BackupRoot $safeName) -Force
}

function Write-ManagedFile {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Content,
        [Parameter(Mandatory)] [string]$BackupRoot,
        [ValidateSet("ascii", "utf8")] [string]$Encoding = "ascii"
    )

    New-ManagedDirectory -Path (Split-Path -Parent $Path)
    if (Test-Path -LiteralPath $Path) {
        $existing = Get-Content -LiteralPath $Path -Raw
        if ($existing -eq $Content) {
            return
        }
        Backup-File -SourcePath $Path -BackupRoot $BackupRoot
    }

    Set-Content -LiteralPath $Path -Value $Content -Encoding $Encoding -NoNewline
}

function Ensure-AsciiLine {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Line,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        Write-ManagedFile -Path $Path -Content ($Line + [Environment]::NewLine) -BackupRoot $BackupRoot
        return
    }

    $lines = Get-Content -LiteralPath $Path
    if ($lines -contains $Line) {
        return
    }

    Backup-File -SourcePath $Path -BackupRoot $BackupRoot
    $content = Get-Content -LiteralPath $Path -Raw
    $newContent = if ([string]::IsNullOrWhiteSpace($content)) {
        $Line + [Environment]::NewLine
    } else {
        $Line + [Environment]::NewLine + [Environment]::NewLine + $content.TrimStart()
    }
    Set-Content -LiteralPath $Path -Value $newContent -Encoding ascii -NoNewline
}

function Set-ManagedBlock {
    param(
        [Parameter(Mandatory)] [string]$Path,
        [Parameter(Mandatory)] [string]$Block,
        [Parameter(Mandatory)] [string]$BackupRoot
    )

    $startMarker = "# >>> DEV_HYBRID_WSL_WINDOWS >>>"
    $endMarker = "# <<< DEV_HYBRID_WSL_WINDOWS <<<"

    if (-not (Test-Path -LiteralPath $Path)) {
        New-ManagedDirectory -Path (Split-Path -Parent $Path)
        Set-Content -LiteralPath $Path -Value "" -NoNewline
    }

    $content = Get-Content -LiteralPath $Path -Raw
    if ($content -match "DEV_GOVERNANCE_CLI_IDE_WINDOWS") {
        Write-Info "Existing Windows WSL integration block detected in $Path; leaving profile unchanged."
        return
    }

    $managed = @"
$startMarker
$Block
$endMarker
"@

    $newContent = if ($content -match [regex]::Escape($startMarker)) {
        [regex]::Replace($content, "(?s)$([regex]::Escape($startMarker)).*?$([regex]::Escape($endMarker))", $managed)
    } else {
        ($content.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + $managed + [Environment]::NewLine)
    }

    if ($newContent -ne $content) {
        Backup-File -SourcePath $Path -BackupRoot $BackupRoot
        Set-Content -LiteralPath $Path -Value $newContent -NoNewline
        Write-Info "Updated managed PowerShell profile block in $Path"
    }
}

function Repair-UserPath {
    $current = [Environment]::GetEnvironmentVariable("Path", "User")
    $segments = $current -split ";" | Where-Object { $_ -and $_ -ne ":PATH" }
    $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
    $clean = foreach ($segment in $segments) {
        if ($seen.Add($segment)) {
            $segment
        }
    }
    [Environment]::SetEnvironmentVariable("Path", ($clean -join ";"), "User")
    Write-Info "Repaired user PATH."
}

function Repair-SshAcl {
    $sshDir = Join-Path $HOME ".ssh"
    $sshConfig = Join-Path $sshDir "config"

    if (-not (Test-Path -LiteralPath $sshDir) -or -not (Test-Path -LiteralPath $sshConfig)) {
        Write-Info "SSH config not present; skipping ACL repair."
        return
    }

    $userAccount = New-Object System.Security.Principal.NTAccount("$env:USERDOMAIN\$env:USERNAME")
    $userSid = $userAccount.Translate([System.Security.Principal.SecurityIdentifier])
    $systemSid = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-18")
    $adminsSid = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-544")

    $dirAcl = New-Object System.Security.AccessControl.DirectorySecurity
    $dirAcl.SetOwner($userAccount)
    $dirAcl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($userSid, $systemSid, $adminsSid)) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, "FullControl", "ContainerInherit, ObjectInherit", "None", "Allow")
        [void]$dirAcl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $sshDir -AclObject $dirAcl

    $fileAcl = New-Object System.Security.AccessControl.FileSecurity
    $fileAcl.SetOwner($userAccount)
    $fileAcl.SetAccessRuleProtection($true, $false)
    foreach ($sid in @($userSid, $systemSid, $adminsSid)) {
        $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($sid, "FullControl", "Allow")
        [void]$fileAcl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $sshConfig -AclObject $fileAcl

    Write-Info "Rebuilt SSH ACL for $sshDir and $sshConfig."
}

function Set-UserSshConfig {
    $sshDir = Join-Path $HOME ".ssh"
    $sshConfig = Join-Path $sshDir "config"
    $sshConfigDir = Join-Path $sshDir "config.d"
    $managedConfig = Join-Path $sshConfigDir "dev-hybrid.conf"
    New-ManagedDirectory -Path $sshDir
    New-ManagedDirectory -Path $sshConfigDir

    $content = @"
Host github.com
  HostName github.com
  User git
  IdentityFile $WindowsSshIdentity
  IdentitiesOnly yes
"@

    Write-ManagedFile -Path $managedConfig -Content $content -BackupRoot $backupRoot -Encoding ascii
    $includeLine = "Include config.d/dev-hybrid.conf"

    if (Test-Path -LiteralPath $sshConfig) {
        $existing = (Get-Content -LiteralPath $sshConfig -Raw).Trim()
        if ($existing -eq $content.Trim()) {
            Write-ManagedFile -Path $sshConfig -Content ($includeLine + [Environment]::NewLine) -BackupRoot $backupRoot -Encoding ascii
            Write-Info "Migrated Windows SSH config to managed include file."
            return
        }
    }

    Ensure-AsciiLine -Path $sshConfig -Line $includeLine -BackupRoot $backupRoot
    Write-Info "Ensured managed Windows SSH include file."
}

function Export-EditorExtensions {
    param([string]$ExportRoot)

    New-ManagedDirectory -Path $ExportRoot

    $vscodeTargets = @(
        "code",
        "D:\VSCode\bin\code.cmd",
        "C:\Users\Zappro\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd"
    )

    $codeCommand = $null
    foreach ($target in $vscodeTargets) {
        if ($target -eq "code") {
            $resolved = Get-Command code -ErrorAction SilentlyContinue
            if ($resolved) {
                $codeCommand = $resolved.Source
                break
            }
        } elseif (Test-Path -LiteralPath $target) {
            $codeCommand = $target
            break
        }
    }

    $vscodeExportPath = Join-Path $ExportRoot "vscode-extensions.txt"
    if ($codeCommand) {
        $extensions = & $codeCommand --list-extensions 2>$null | Sort-Object -Unique
        Set-Content -LiteralPath $vscodeExportPath -Value $extensions
        Write-Info "Exported VS Code extensions."
    } elseif (-not (Test-Path -LiteralPath $vscodeExportPath)) {
        Set-Content -LiteralPath $vscodeExportPath -Value "# VS Code CLI not detected on this host."
    }

    $antigravityRoots = @(
        (Join-Path $env:LOCALAPPDATA "Programs\Antigravity\resources\app\extensions"),
        (Join-Path $env:LOCALAPPDATA "Programs\Antigravity\resources\resources\app\extensions")
    )
    $antigravityExtensions = @()
    foreach ($root in $antigravityRoots) {
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }
        $antigravityExtensions += Get-ChildItem -LiteralPath $root -Directory -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "wsl|remote" } |
            Select-Object -ExpandProperty Name
    }

    $antigravityExportPath = Join-Path $ExportRoot "antigravity-extensions.txt"
    if ($antigravityExtensions.Count -gt 0) {
        Set-Content -LiteralPath $antigravityExportPath -Value ($antigravityExtensions | Sort-Object -Unique)
        Write-Info "Exported Antigravity remote integration snapshot."
    } elseif (-not (Test-Path -LiteralPath $antigravityExportPath)) {
        Set-Content -LiteralPath $antigravityExportPath -Value "# Antigravity remote extensions not detected."
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$backupRoot = Join-Path $repoRoot ".context\backups\$ReferenceDate\windows"
$exportRoot = Join-Path $repoRoot ".context\exports\$ReferenceDate"

New-ManagedDirectory -Path $backupRoot
New-ManagedDirectory -Path $exportRoot

$windowsTargets = @(
    "$HOME\Documents\PowerShell\Microsoft.PowerShell_profile.ps1",
    "$HOME\Documents\PowerShell\profile.ps1",
    "$HOME\AppData\Local\Packages\Microsoft.WindowsTerminal_8wekyb3d8bbwe\LocalState\settings.json",
    "$HOME\.wslconfig",
    "$HOME\.gitconfig",
    "$HOME\.ssh\config"
)

foreach ($target in $windowsTargets) {
    Backup-File -SourcePath $target -BackupRoot $backupRoot
}

if ($FixUserPath) {
    Repair-UserPath
}

if ($RefreshUserSshConfig) {
    Set-UserSshConfig
}

if ($FixSshAcl) {
    Repair-SshAcl
}

if (-not $SkipWingetExport) {
    & winget export -o (Join-Path $exportRoot "winget-export.json") --accept-source-agreements --include-versions
    Write-Info "Exported winget manifest."
}

if (-not $SkipEditorExport) {
    Export-EditorExtensions -ExportRoot $exportRoot
}

if (-not $SkipProfileBridge) {
    $profileBlock = @"
\$script:DevHybridWslDistro = '$WslDistro'
\$script:DevHybridWslUser = '$WslUser'
\$script:DevHybridWslHome = '$DevHomeWsl'

function Enter-DevWSL {
    param([string]\$TargetDistro = \$script:DevHybridWslDistro)
    & wsl.exe -d \$TargetDistro -u \$script:DevHybridWslUser --cd ~
}

function Enter-DevProject {
    param(
        [string]\$Path = \$script:DevHybridWslHome,
        [string]\$TargetDistro = \$script:DevHybridWslDistro
    )
    & wsl.exe -d \$TargetDistro -u \$script:DevHybridWslUser --cd \$Path
}

function Open-DevIDE {
    param([string]\$Path = '.')
    \$resolved = Resolve-Path -LiteralPath \$Path -ErrorAction SilentlyContinue
    \$target = if (\$resolved) { \$resolved.Path } else { \$Path }
    if (Get-Command code -ErrorAction SilentlyContinue) {
        & code \$target
        return
    }
    if (Get-Command cursor -ErrorAction SilentlyContinue) {
        & cursor \$target
        return
    }
    Write-Warning 'CLI de IDE nao encontrado no PATH (code/cursor).'
}

Set-Alias devwsl Enter-DevWSL
Set-Alias devproj Enter-DevProject
Set-Alias devide Open-DevIDE
"@

    Set-ManagedBlock -Path $PROFILE.CurrentUserAllHosts -Block $profileBlock -BackupRoot $backupRoot
}

Write-Info "Windows bootstrap complete."
