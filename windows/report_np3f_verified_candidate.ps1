param(
    [string]$CandidateYaml = "",
    [string]$Relocations = "",
    [string]$Overrides = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

$CandidatePath = if ([string]::IsNullOrWhiteSpace($CandidateYaml)) {
    Join-Path $RepoRoot "build\np3f\analysis\splat-segment-verified.yaml"
} else {
    (Resolve-Path -LiteralPath $CandidateYaml).Path
}

$RelocationPath = if ([string]::IsNullOrWhiteSpace($Relocations)) {
    Join-Path $RepoRoot "build\np3f\analysis\subsegment_relocations.json"
} else {
    (Resolve-Path -LiteralPath $Relocations).Path
}

$OverridePath = if ([string]::IsNullOrWhiteSpace($Overrides)) {
    Join-Path $RepoRoot "build\np3f\analysis\verified_fragment_overrides.json"
} else {
    (Resolve-Path -LiteralPath $Overrides).Path
}

$ReportPath = Join-Path $RepoRoot "build\np3f\analysis\verified_candidate_validation.json"

Write-Host "=== Aero-Stadium-2-FR / verified candidate validation ==="
Write-Host "Candidate  : $CandidatePath"
Write-Host "Relocations: $RelocationPath"
Write-Host "Overrides  : $OverridePath"
Write-Host ""

Push-Location $RepoRoot
try {
    python .\tools\np3f\validate_verified_candidate.py --candidate "$CandidatePath" --relocations "$RelocationPath" --overrides "$OverridePath" --output "$ReportPath"
    $ExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($ExitCode -ne 0) {
    throw "Verified NP3F candidate validation failed."
}

Write-Host ""
Write-Host "Verified candidate validation completed successfully."
Write-Host "Report: $ReportPath"
