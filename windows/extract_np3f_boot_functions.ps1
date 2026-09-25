param()

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $RepoRoot "tools\recomp\extract_np3f_boot_functions.py"
$Generated = Join-Path $RepoRoot "generated\recomp\np3f"
$Report = Join-Path $RepoRoot "build\np3f\analysis\boot_functions.txt"

Write-Host "=== Aero-Stadium-2-FR / exact NP3F boot functions ==="

Push-Location $RepoRoot
try {
    python $Script --generated-dir $Generated --output $Report
    $Code = $LASTEXITCODE
}
finally {
    Pop-Location
}

if ($Code -ne 0) {
    exit $Code
}

Write-Host ""
Write-Host "Report: $Report"
Get-Content -LiteralPath $Report
exit 0
