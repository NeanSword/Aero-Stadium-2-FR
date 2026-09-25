param(
    [string]$Relocations = "",
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

$RomPath = if ([string]::IsNullOrWhiteSpace($Rom)) {
    Join-Path $RepoRoot "baseroms\fr\baserom.z64"
} else {
    (Resolve-Path -LiteralPath $Rom).Path
}

$SegmentYaml = Join-Path $RepoRoot "build\np3f\analysis\splat-segment-relocated.yaml"
$SegmentReport = Join-Path $RepoRoot "build\np3f\analysis\segment_relocation_application.json"

$VerifiedYaml = Join-Path $RepoRoot "build\np3f\analysis\splat-segment-verified.yaml"
$VerifiedReport = Join-Path $RepoRoot "build\np3f\analysis\verified_fragment_overrides.json"

$SplatLog = Join-Path $RepoRoot "build\NP3F_SPLAT_EXTRACT.log"
$HintsReport = Join-Path $RepoRoot "build\np3f\analysis\splat_verified_segment_hints.json"

if (-not (Test-Path -LiteralPath $RelocationPath -PathType Leaf)) {
    throw "Relocation report not found: $RelocationPath"
}

if (-not (Test-Path -LiteralPath $RomPath -PathType Leaf)) {
    throw "NP3F ROM not found: $RomPath"
}

Write-Host "=== Aero-Stadium-2-FR / verified NP3F segment candidate ==="
Write-Host "Relocations: $RelocationPath"
Write-Host "ROM        : $RomPath"
Write-Host ""

Push-Location $RepoRoot
try {
    Write-Host "[1/4] Building segment-relocated candidate..."
    python .\tools\np3f\build_segment_relocated_candidate.py --relocations "$RelocationPath" --output "$SegmentYaml" --report "$SegmentReport"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "[2/4] Applying ROM-verified fragment starts..."
    python .\tools\np3f\apply_verified_fragment_overrides.py --input "$SegmentYaml" --rom "$RomPath" --output "$VerifiedYaml" --report "$VerifiedReport"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "[3/4] Running Splat with verified candidate..."

$RunArgs = @{
    CandidateYaml = $VerifiedYaml
    Rom = $RomPath
    AllowRelocatedStarts = $true
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
Write-Host "[4/4] Extracting Splat hints..."

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
Write-Host "Verified candidate : $VerifiedYaml"
Write-Host "Segment report     : $SegmentReport"
Write-Host "Verified report    : $VerifiedReport"
Write-Host "Splat hints        : $HintsReport"
exit 0
