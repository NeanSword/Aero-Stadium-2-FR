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
    Join-Path $RepoRoot "build\np3f\analysis\splat-segment-relocated.yaml"
} else {
    $CandidateYaml
}
$ApplicationReport = Join-Path $RepoRoot "build\np3f\analysis\segment_relocation_application.json"
$SplatLog = Join-Path $RepoRoot "build\NP3F_SPLAT_EXTRACT.log"
$HintsReport = Join-Path $RepoRoot "build\np3f\analysis\splat_segment_hints.json"

if (-not (Test-Path -LiteralPath $RelocationPath -PathType Leaf)) {
    throw "Relocation report not found: $RelocationPath"
}

Write-Host "=== Aero-Stadium-2-FR / segment-aware NP3F candidate ==="
Write-Host "Relocations: $RelocationPath"
Write-Host ""

Push-Location $RepoRoot
try {
    python .\tools\np3f\build_segment_relocated_candidate.py --relocations "$RelocationPath" --output "$OutputYaml" --report "$ApplicationReport"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Running Splat with segment-aware candidate..."

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
$ExtractExit = $LASTEXITCODE
if ($ExtractExit -ne 0) {
    exit $ExtractExit
}

Write-Host ""
Write-Host "Extracting Splat rodata hints..."

Push-Location $RepoRoot
try {
    python .\tools\np3f\extract_splat_hints.py --log "$SplatLog" --output "$HintsReport"
    $HintsExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($HintsExit -ne 0) {
    exit $HintsExit
}

Write-Host ""
Write-Host "Segment relocation report: $ApplicationReport"
Write-Host "Splat hint report: $HintsReport"
exit 0
