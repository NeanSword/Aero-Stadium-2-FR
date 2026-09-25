param()

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $RepoRoot "tools\recomp\analyze_np3f_thread_boot.py"
$Generated = Join-Path $RepoRoot "generated\recomp\np3f"
$Report = Join-Path $RepoRoot "build\np3f\analysis\thread_boot_callsites.txt"

Write-Host "=== Aero-Stadium-2-FR / NP3F thread boot analysis ==="
Write-Host "Generated C : $Generated"
Write-Host "Report      : $Report"
Write-Host ""

Push-Location $RepoRoot
try {
    python $Script --generated-dir $Generated --output $Report
    $ExitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($ExitCode -ne 0) {
    exit $ExitCode
}

Write-Host ""
Write-Host "=== Report ==="
Get-Content -LiteralPath $Report
exit 0
