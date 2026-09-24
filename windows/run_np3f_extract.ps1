param(
    [string]$CandidateYaml = "",

    [string]$Rom = "",

    [switch]$DisassembleAll
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ToolsDir = Join-Path $RepoRoot "tools"
$BuildDir = Join-Path $RepoRoot "build"
$RomPath = if ([string]::IsNullOrWhiteSpace($Rom)) {
    Join-Path $RepoRoot "baseroms\fr\baserom.z64"
} else {
    (Resolve-Path -LiteralPath $Rom).Path
}

$CandidatePath = if ([string]::IsNullOrWhiteSpace($CandidateYaml)) {
    Join-Path $RepoRoot "yamls\fr\splat.yaml"
} else {
    (Resolve-Path -LiteralPath $CandidateYaml).Path
}
$LocalCandidate = Join-Path $RepoRoot "np3f-local.yaml"
$LogPath = Join-Path $BuildDir "NP3F_SPLAT_EXTRACT.log"

if (-not (Test-Path -LiteralPath $RomPath -PathType Leaf)) {
    Write-Host "ERROR: ROM not found: $RomPath"
    exit 2
}

if (-not (Test-Path -LiteralPath $CandidatePath -PathType Leaf)) {
    Write-Host "ERROR: candidate YAML not found: $CandidatePath"
    exit 2
}

Write-Host "=== Aero-Stadium-2-FR / NP3F extraction ==="
Write-Host "ROM      : $RomPath"
Write-Host "Candidate: $CandidatePath"
Write-Host ""

Write-Host "[1/3] Verifying NP3F ROM..."
python (Join-Path $ToolsDir "verify_np3f_rom.py") $RomPath
if ($LASTEXITCODE -ne 0) {
    throw "NP3F ROM verification failed."
}

Write-Host ""
Write-Host "[2/3] Validating candidate fragment map..."
python (Join-Path $ToolsDir "np3f\validate_candidate_yaml.py") $CandidatePath
if ($LASTEXITCODE -ne 0) {
    throw "Candidate YAML validation failed."
}

Write-Host ""
Write-Host "[3/3] Running Splat from repository root..."

Copy-Item -LiteralPath $CandidatePath -Destination $LocalCandidate -Force

$SplatArgs = @("-m", "splat", "split")
if ($DisassembleAll) {
    $SplatArgs += "--disassemble-all"
}
$SplatArgs += $LocalCandidate

Push-Location $RepoRoot
try {
    python (Join-Path $ToolsDir "run_command_capture.py") --log $LogPath -- python @SplatArgs
    $ExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($ExitCode -ne 0) {
    Write-Host ""
    Write-Host "Splat extraction FAILED. Full output:"
    Write-Host $LogPath
    exit $ExitCode
}

Write-Host ""
Write-Host "Splat extraction completed successfully."
Write-Host "Log: $LogPath"
