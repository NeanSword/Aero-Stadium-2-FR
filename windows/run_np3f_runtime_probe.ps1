param([int]$HeartbeatSeconds = 10)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RunnerVersion = "2026-09-27.1"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$BuildDir = Join-Path $RepoRoot "build\np3f\link-smoke-prebuilt-vs2022-x64"
$Exe = Join-Path $BuildDir "bin\AeroStadium2.exe"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$StdoutLog = Join-Path $LogDir "NP3F_RUNTIME.stdout.log"
$StderrLog = Join-Path $LogDir "NP3F_RUNTIME.stderr.log"
$CombinedLog = Join-Path $LogDir "NP3F_RUNTIME.log"

Write-Host "=== Aero-Stadium-2-FR / NP3F runtime probe ==="
Write-Host "Runner version: $RunnerVersion"
Write-Host ""

if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
    throw "AeroStadium2.exe not found: $Exe"
}

foreach ($Name in @("SDL2.dll", "dxcompiler.dll", "dxil.dll")) {
    $RuntimeFile = Join-Path (Split-Path -Parent $Exe) $Name
    if (-not (Test-Path -LiteralPath $RuntimeFile -PathType Leaf)) {
        throw "Required runtime file not found: $RuntimeFile"
    }
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Remove-Item $StdoutLog,$StderrLog,$CombinedLog -Force -ErrorAction SilentlyContinue

Write-Host "Executable : $Exe"
Write-Host "Runtime log: $CombinedLog"
Write-Host "Conseil: branche la manette avant ce premier test."
Write-Host "Une selection de ROM peut apparaitre si NP3F n est pas encore stockee."
Write-Host ""

$Process = Start-Process -FilePath $Exe -WorkingDirectory (Split-Path -Parent $Exe) -NoNewWindow -PassThru -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
$LastHeartbeat = Get-Date
while (-not $Process.HasExited) {
    Start-Sleep -Milliseconds 250
    if (((Get-Date) - $LastHeartbeat).TotalSeconds -ge $HeartbeatSeconds) {
        Write-Host ("[runtime] Toujours actif... PID={0}" -f $Process.Id) -ForegroundColor DarkGray
        $LastHeartbeat = Get-Date
    }
}
$Process.WaitForExit()

$Stdout = if (Test-Path $StdoutLog) { @(Get-Content $StdoutLog) } else { @() }
$Stderr = if (Test-Path $StderrLog) { @(Get-Content $StderrLog) } else { @() }
@(
    "=== AeroStadium2 runtime stdout ==="
    $Stdout
    ""
    "=== AeroStadium2 runtime stderr ==="
    $Stderr
    ""
    "=== AeroStadium2 exit code: $($Process.ExitCode) ==="
) | Set-Content -LiteralPath $CombinedLog -Encoding UTF8

if ($Stdout.Count -gt 0) { $Stdout | ForEach-Object { Write-Host $_ } }
if ($Stderr.Count -gt 0) { $Stderr | ForEach-Object { Write-Host $_ -ForegroundColor Yellow } }
Write-Host ""
Write-Host "Runtime log : $CombinedLog"
Write-Host "Exit code   : $($Process.ExitCode)"
exit $Process.ExitCode
