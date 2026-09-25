param(
    [switch]$SkipExtract
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RecompExe = Join-Path $RepoRoot ".local\bin\N64Recomp.exe"
$Symbols = Join-Path $RepoRoot "build\np3f\recomp\np3f.syms.toml"
$SymbolReport = Join-Path $RepoRoot "build\np3f\analysis\recomp_symbols_report.json"
$Config = Join-Path $RepoRoot "recomp\np3f.toml"
$Log = Join-Path $RepoRoot "build\NP3F_N64RECOMP.log"
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"

Write-Host "=== Aero-Stadium-2-FR / first NP3F N64Recomp pass ==="
Write-Host ""

if (-not (Test-Path -LiteralPath $RecompExe -PathType Leaf)) {
    throw "N64Recomp.exe not found. Run .\windows\bootstrap_n64recomp.ps1 first."
}

if (-not $SkipExtract) {
    Write-Host "[1/3] Regenerating canonical Splat output with full disassembly..."
    & (Join-Path $PSScriptRoot "run_np3f_extract.ps1") -DisassembleAll
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}
else {
    Write-Host "[1/3] Reusing existing Splat disassembly (-SkipExtract)."
}

Write-Host ""
Write-Host "[2/3] Generating N64Recomp symbol map from Splat assembly..."

Push-Location $RepoRoot
try {
    python .\tools\recomp\generate_np3f_symbols.py --yaml .\yamls\fr\splat.yaml --asm-root .\build\np3f\asm --output $Symbols --report $SymbolReport
    $SymbolsExit = $LASTEXITCODE
} finally {
    Pop-Location
}

if ($SymbolsExit -ne 0) {
    exit $SymbolsExit
}

Write-Host ""
Write-Host "[3/3] Running N64Recomp..."

if (Test-Path -LiteralPath $GeneratedDir) {
    Write-Host "Removing partial previous recompilation output: $GeneratedDir"
    Remove-Item -LiteralPath $GeneratedDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Log) | Out-Null

Push-Location $RepoRoot
try {
    & $RecompExe $Config 2>&1 | Tee-Object -FilePath $Log
    $RecompExit = $LASTEXITCODE
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Symbol map report : $SymbolReport"
Write-Host "N64Recomp log     : $Log"

if ($RecompExit -ne 0) {
    Write-Host "N64Recomp stopped with exit code $RecompExit."
    exit $RecompExit
}

Write-Host "N64Recomp generation completed successfully."
exit 0
