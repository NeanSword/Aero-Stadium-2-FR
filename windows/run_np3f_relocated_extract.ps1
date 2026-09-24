param(
    [string]$Relocations = "",
    [string]$CandidateYaml = "",
    [string]$Rom = "",
    [switch]$DisassembleAll
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RelocationPath = if ([string]::IsNullOrWhiteSpace($Relocations)) {
    Join-Path $RepoRoot "build\np3f\analysis\subsegment_relocations.json"
} else {
    (Resolve-Path -LiteralPath $Relocations).Path
}
$OutputYaml = if ([string]::IsNullOrWhiteSpace($CandidateYaml)) {
    Join-Path $RepoRoot "build\np3f\analysis\splat-relocated.yaml"
} else {
    $CandidateYaml
}
$ApplicationReport = Join-Path $RepoRoot "build\np3f\analysis\relocation_application.json"

if (-not (Test-Path -LiteralPath $RelocationPath -PathType Leaf)) {
    throw "Relocation report not found: $RelocationPath"
}

Write-Host "=== Aero-Stadium-2-FR / relocated NP3F candidate ==="
Write-Host "Relocations: $RelocationPath"
Write-Host ""

Push-Location $RepoRoot
try {
    python .\tools\np3f\build_relocated_candidate.py --relocations "$RelocationPath" --output "$OutputYaml" --report "$ApplicationReport"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Running Splat with the generated candidate..."

$RunArgs = @{
    CandidateYaml = $OutputYaml
}
if (-not [string]::IsNullOrWhiteSpace($Rom)) {
    $RunArgs["Rom"] = $Rom
}
if ($DisassembleAll) {
    $RunArgs["DisassembleAll"] = $true
}

& (Join-Path $PSScriptRoot "run_np3f_extract.ps1") @RunArgs
exit $LASTEXITCODE
