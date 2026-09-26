param(
    [switch]$SkipExtract
)

$ErrorActionPreference = "Stop"

$RunnerVersion = "2026-09-27.2"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$RecompExe = Join-Path $RepoRoot ".local\bin\N64Recomp.exe"
$Symbols = Join-Path $RepoRoot "build\np3f\recomp\np3f.syms.toml"
$SymbolReport = Join-Path $RepoRoot "build\np3f\analysis\recomp_symbols_report.json"
$Config = Join-Path $RepoRoot "recomp\np3f.toml"
$Log = Join-Path $RepoRoot "build\NP3F_N64RECOMP.log"
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"
$RecompYaml = Join-Path $RepoRoot "build\np3f\recomp\splat.recomp.yaml"
$AsmDir = Join-Path $RepoRoot "build\np3f\asm"
$SrcDir = Join-Path $RepoRoot "build\np3f\src"
$CleanExtractStamp = Join-Path $RepoRoot "build\np3f\recomp\.np3f-symbol-clean-extract-v1"
$GeneratorScript = Join-Path $RepoRoot "tools\recomp\generate_np3f_symbols.py"
$StandaloneN64RecompRoot = Join-Path $RepoRoot ".local\n64recomp"
$StandaloneN64RecompSource = Join-Path $StandaloneN64RecompRoot "src"
$StandaloneVersions = Join-Path $StandaloneN64RecompRoot "versions.json"
$ExpectedN64RecompCommit = "ffb39cdad1da5de07eaaa48bd1db4a89a7986771"
$ForbiddenGeneratedHooks = @(
    "aero_lookup_asset",
    "aero_cartridge_read_u32",
    "aero_poll_events"
)

Write-Host "=== Aero-Stadium-2-FR / first NP3F N64Recomp pass ==="
Write-Host "Runner version: $RunnerVersion"
Write-Host ""

if (-not (Test-Path -LiteralPath $RecompExe -PathType Leaf)) {
    throw "N64Recomp.exe not found. Run .\windows\bootstrap_n64recomp.ps1 first."
}

if (-not (Test-Path -LiteralPath $StandaloneVersions -PathType Leaf)) {
    throw @"
Standalone N64Recomp version metadata is missing.

Run:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\bootstrap_n64recomp.ps1 -Force
"@
}

$VersionInfo = Get-Content -LiteralPath $StandaloneVersions -Raw | ConvertFrom-Json
if ($VersionInfo.n64recomp -ne $ExpectedN64RecompCommit) {
    throw @"
Standalone N64Recomp is not the pinned revision.
Expected: $ExpectedN64RecompCommit
Found   : $($VersionInfo.n64recomp)

Rebuild it with:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\bootstrap_n64recomp.ps1 -Force
"@
}

if (Test-Path -LiteralPath $StandaloneN64RecompSource -PathType Container) {
    foreach ($ForbiddenHook in $ForbiddenGeneratedHooks) {
        $SourceMatch = Get-ChildItem -LiteralPath $StandaloneN64RecompSource -Recurse -File -ErrorAction SilentlyContinue |
            Select-String -SimpleMatch $ForbiddenHook -List -ErrorAction SilentlyContinue |
            Select-Object -First 1

        if ($null -ne $SourceMatch) {
            throw @"
Standalone N64Recomp source contains an Aero-specific host hook:
  $ForbiddenHook
  $($SourceMatch.Path):$($SourceMatch.LineNumber)

The generator source is contaminated by an older local experiment.
Rebuild the pinned upstream source with:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\bootstrap_n64recomp.ps1 -Force
"@
        }
    }
}

if (-not $SkipExtract) {
    Write-Host "[1/3] Regenerating NP3F Splat output for recompilation..."
    Write-Host "      Stale NP3E code symbols are removed for this pass."

    Push-Location $RepoRoot
    try {
        python .\tools\recomp\build_np3f_recomp_yaml.py --input .\yamls\fr\splat.yaml --output $RecompYaml
        $RecompYamlExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    if ($RecompYamlExit -ne 0) {
        exit $RecompYamlExit
    }

    foreach ($GeneratedPath in @($AsmDir, $SrcDir)) {
        if (Test-Path -LiteralPath $GeneratedPath) {
            Write-Host "Removing stale Splat output: $GeneratedPath"
            Remove-Item -LiteralPath $GeneratedPath -Recurse -Force
        }
    }

    Remove-Item -LiteralPath $CleanExtractStamp -Force -ErrorAction SilentlyContinue

    & (Join-Path $PSScriptRoot "run_np3f_extract.ps1") -CandidateYaml $RecompYaml -DisassembleAll
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $CleanExtractStamp) | Out-Null
    "NP3F symbol-clean Splat extraction completed." | Set-Content -LiteralPath $CleanExtractStamp -Encoding ASCII
}
else {
    if (-not (Test-Path -LiteralPath $CleanExtractStamp -PathType Leaf)) {
        throw @"
-SkipExtract cannot be used with the current build output.

The recompilation pass now requires a fresh Splat extraction without stale
NP3E code symbols. Run this script once without -SkipExtract.
"@
    }

    # Older local experiments could leave Aero-specific helper labels inside
    # build/np3f/asm even though the stamp predates the current symbol-clean
    # extraction rules. Those labels are not part of NP3F and must never leak
    # into the generated static library.
    $StaleAeroSymbol = Get-ChildItem -LiteralPath $AsmDir -Recurse -File -Filter "*.s" -ErrorAction SilentlyContinue |
        Select-String -Pattern '\baero_[A-Za-z0-9_]+\b' -List |
        Select-Object -First 1

    if ($null -ne $StaleAeroSymbol) {
        throw @"
-SkipExtract refused: stale Aero-specific symbols were found in the cached
Splat assembly.

First match:
$($StaleAeroSymbol.Path):$($StaleAeroSymbol.LineNumber)
$($StaleAeroSymbol.Line.Trim())

Run this script once WITHOUT -SkipExtract. It will delete build\np3f\asm and
re-extract a clean NP3F disassembly before regenerating N64Recomp output.
"@
    }

    Write-Host "[1/3] Reusing symbol-clean NP3F Splat disassembly (-SkipExtract)."
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

foreach ($ForbiddenHook in $ForbiddenGeneratedHooks) {
    $GeneratedMatch = Get-ChildItem -LiteralPath $GeneratedDir -Recurse -File -ErrorAction SilentlyContinue |
        Select-String -SimpleMatch $ForbiddenHook -List -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($null -ne $GeneratedMatch) {
        throw @"
N64Recomp generated an obsolete Aero-specific host hook:
  $ForbiddenHook
  $($GeneratedMatch.Path):$($GeneratedMatch.LineNumber)

The standalone generator executable is stale or modified. Rebuild it with:
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\bootstrap_n64recomp.ps1 -Force

Then rerun this script with -SkipExtract.
"@
    }
}

Write-Host "N64Recomp generation completed successfully."
exit 0
