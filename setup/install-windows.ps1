# install-windows.ps1
# Configure the Windows host for octo-setup WSL2 SSH access.
#   1. Write %USERPROFILE%\.wslconfig with mirrored networking
#   2. Remove stale `netsh portproxy` rules for port 22
#   3. Open Windows Firewall for inbound TCP 22
#
# Run from an ELEVATED PowerShell:
#     Set-ExecutionPolicy -Scope Process Bypass -Force
#     .\install-windows.ps1
#
# Safe to re-run -- every step skips work that's already done.
# After this finishes:
#   1. Close all WSL terminals
#   2. wsl --shutdown
#   3. Reopen WSL and run install-wsl2.sh

$ErrorActionPreference = 'Stop'

function Test-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p  = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Admin)) {
    Write-Host "ERROR: Must run as Administrator (portproxy/firewall need it)." -ForegroundColor Red
    exit 1
}

# ---------- Step 1: %USERPROFILE%\.wslconfig with mirrored networking ----------
Write-Host "=== Step 1: configure $env:USERPROFILE\.wslconfig ==="
$wslconfig = Join-Path $env:USERPROFILE '.wslconfig'
$desired = @(
    '[wsl2]'
    'networkingMode=mirrored'
    ''
    '[experimental]'
    'hostAddressLoopback=true'
) -join "`r`n"

if (Test-Path $wslconfig) {
    $cur = Get-Content $wslconfig -Raw
    if ($cur -match '(?im)^\s*networkingMode\s*=\s*mirrored') {
        Write-Host "  .wslconfig already has networkingMode=mirrored -- skipping"
    } else {
        $bak = "$wslconfig.bak.$(Get-Date -Format yyyyMMddHHmmss)"
        Copy-Item $wslconfig $bak -Force
        Set-Content -Path $wslconfig -Value $desired -NoNewline
        Write-Host "  Backed up old .wslconfig to $bak"
        Write-Host "  Wrote new .wslconfig with mirrored networking."
    }
} else {
    Set-Content -Path $wslconfig -Value $desired -NoNewline
    Write-Host "  Wrote new .wslconfig with mirrored networking."
}
Write-Host ""

# ---------- Step 2: clean stale netsh portproxy rules for port 22 ----------
Write-Host "=== Step 2: clean stale netsh portproxy rules for port 22 ==="
$existing = (& netsh interface portproxy show v4tov4 | Out-String)
$matches = ($existing -split "`n") | Where-Object { $_ -match '^\s*0\.0\.0\.0\s+22\b' }
if ($matches) {
    Write-Host "  Found stale portproxy rule(s) for port 22:"
    $matches | ForEach-Object { Write-Host "    $_" }
    & netsh interface portproxy delete v4tov4 listenport=22 listenaddress=0.0.0.0 | Out-Null
    Write-Host "  Removed."
} else {
    Write-Host "  No portproxy rule for port 22 -- skipping."
}
Write-Host ""

# ---------- Step 3: Windows Firewall -- allow inbound TCP 22 ----------
Write-Host "=== Step 3: Windows Firewall -- allow inbound TCP 22 ==="
$ruleName = 'WSL2 SSH (octo-setup)'
$rule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($rule) {
    Write-Host "  Firewall rule '$ruleName' already exists -- skipping"
} else {
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound -Action Allow -Protocol TCP -LocalPort 22 `
        -Profile Any | Out-Null
    Write-Host "  Created firewall rule '$ruleName' (TCP 22 inbound, Any profile)."
}
Write-Host ""

# ---------- Step 4: next steps ----------
Write-Host "=== Step 4: next steps ==="
Write-Host "  1. Close all WSL terminals."
Write-Host "  2. Run:  wsl --shutdown"
Write-Host "  3. Reopen WSL and run:  bash ~/octo-skills/setup/install-wsl2.sh"
Write-Host "  4. Then on the laptop:  bash accept-ssh-access.sh  (after grant-ssh-access.sh on this host)"
Write-Host ""
Write-Host "=== Done ==="
