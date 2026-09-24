$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Rom = Join-Path $RepoRoot "baseroms\fr\baserom.z64"

Write-Host "=== Aero-Stadium-2-FR / NP3F verification ==="
Write-Host "Repository: $RepoRoot"
Write-Host "ROM       : $Rom"
Write-Host ""

if (-not (Test-Path -LiteralPath $Rom -PathType Leaf)) {
    Write-Host "ERROR: baseroms\fr\baserom.z64 was not found."
    Write-Host "Place your legal NP3F ROM dump there and run this script again."
    exit 2
}

Write-Host "Running Python verifier..."
python (Join-Path $RepoRoot "tools\verify_np3f_rom.py") $Rom
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "ROM verification FAILED."
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "ROM verification PASSED."
