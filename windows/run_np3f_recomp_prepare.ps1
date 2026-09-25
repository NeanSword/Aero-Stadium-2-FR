param(
    [switch]$SkipExtract
)

$ErrorActionPreference = "Stop"

$RunnerVersion = "2026-09-25.2"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RecompExe = Join-Path $RepoRoot ".local\bin\N64Recomp.exe"
$Symbols = Join-Path $RepoRoot "build\np3f\recomp\np3f.syms.toml"
$SymbolReport = Join-Path $RepoRoot "build\np3f\analysis\recomp_symbols_report.json"
$Config = Join-Path $RepoRoot "recomp\np3f.toml"
$Log = Join-Path $RepoRoot "build\NP3F_N64RECOMP.log"
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"

Write-Host "=== Aero-Stadium-2-FR / first NP3F N64Recomp pass ==="
Write-Host "Runner version: $RunnerVersion"
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

$StdoutLog = Join-Path $RepoRoot "build\NP3F_N64RECOMP.stdout.log"
$StderrLog = Join-Path $RepoRoot "build\NP3F_N64RECOMP.stderr.log"

Remove-Item -LiteralPath $StdoutLog -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $StderrLog -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $Log -Force -ErrorAction SilentlyContinue

$Process = Start-Process -FilePath $RecompExe -ArgumentList @($Config) -WorkingDirectory $RepoRoot -NoNewWindow -Wait -PassThru -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog
$RecompExit = $Process.ExitCode

$StdoutLines = @()
$StderrLines = @()

if (Test-Path -LiteralPath $StdoutLog) {
    $StdoutLines = @(Get-Content -LiteralPath $StdoutLog)
}
if (Test-Path -LiteralPath $StderrLog) {
    $StderrLines = @(Get-Content -LiteralPath $StderrLog)
}

$Combined = @(
    "=== N64Recomp stdout ==="
    $StdoutLines
    ""
    "=== N64Recomp stderr ==="
    $StderrLines
    ""
    "=== N64Recomp exit code: $RecompExit ==="
)
$Combined | Set-Content -LiteralPath $Log -Encoding UTF8

if ($StdoutLines.Count -gt 0) {
    $StdoutLines | ForEach-Object { Write-Host $_ }
}
if ($StderrLines.Count -gt 0) {
    $StderrLines | ForEach-Object { Write-Warning $_ }
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
