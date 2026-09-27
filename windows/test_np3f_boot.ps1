param([ValidateRange(1, 300)][int]$Seconds = 15, [switch]$Visible)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $RepoRoot 'build/np3f/link-smoke-prebuilt-vs2022-x64/bin/AeroStadium2.exe'
$Rom = Join-Path $RepoRoot 'baseroms/fr/baserom.z64'
$Data = Join-Path $RepoRoot 'build/rt64-test-userdata'
$LogDir = Join-Path $RepoRoot ('build/np3f/probes/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
foreach ($Required in @($Exe, $Rom)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) { throw "Missing $Required" }
}
New-Item -ItemType Directory -Force $LogDir | Out-Null
$Arguments = '--rom "{0}" --data-dir "{1}" --seconds {2}' -f $Rom, $Data, $Seconds
$WindowStyle = if ($Visible) { 'Normal' } else { 'Hidden' }
$Probe = Start-Process -FilePath $Exe -ArgumentList $Arguments -WorkingDirectory (Split-Path $Exe) `
    -WindowStyle $WindowStyle -PassThru -RedirectStandardOutput (Join-Path $LogDir 'stdout.log') `
    -RedirectStandardError (Join-Path $LogDir 'stderr.log')
if (-not $Probe.WaitForExit(($Seconds + 15) * 1000)) {
    Stop-Process -Id $Probe.Id -Force
    throw "Probe exceeded its deadline. Logs: $LogDir"
}
$Probe.Refresh()
@{ exit_code = $Probe.ExitCode; seconds = $Seconds; executable = $Exe;
   sha256 = (Get-FileHash -LiteralPath $Exe -Algorithm SHA256).Hash } |
    ConvertTo-Json | Set-Content (Join-Path $LogDir 'result.json')
Write-Host "Probe exit: $($Probe.ExitCode). Logs: $LogDir"
Get-Content (Join-Path $LogDir 'stderr.log') -Tail 35
exit $Probe.ExitCode
