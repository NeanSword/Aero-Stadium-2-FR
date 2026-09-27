param()

$ErrorActionPreference = "Stop"
$RunnerVersion = "2026-09-27.2"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$RomPath = Join-Path $RepoRoot "baseroms\fr\baserom.z64"
$GeneratorPath = Join-Path $RepoRoot "tools\recomp\generate_np3f_rsp_audio.py"
$RspExePath = Join-Path $RepoRoot ".local\bin\RSPRecomp.exe"
$RspBuildDir = Join-Path $RepoRoot "build\np3f\rsp"
$GeneratedDir = Join-Path $RepoRoot "generated\rsp\np3f"
$ConfigPath = Join-Path $RspBuildDir "aspMain_np3f.toml"
$ReportPath = Join-Path $RspBuildDir "aspMain_np3f.report.json"
$OutputCpp = Join-Path $GeneratedDir "aspMain_np3f.cpp"

Write-Host "=== Aero-Stadium-2-FR / NP3F audio RSP build ==="
Write-Host "Runner version: $RunnerVersion"

foreach ($Required in @($RomPath, $GeneratorPath, $RspExePath)) {
    if (-not (Test-Path -LiteralPath $Required -PathType Leaf)) {
        throw "Required file not found: $Required"
    }
}

$Python = Get-Command python -ErrorAction SilentlyContinue
if ($null -eq $Python) { $Python = Get-Command py -ErrorAction SilentlyContinue }
if ($null -eq $Python) { throw "Python was not found in PATH." }

New-Item -ItemType Directory -Force -Path $RspBuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $GeneratedDir | Out-Null
Remove-Item -LiteralPath $ConfigPath,$ReportPath,$OutputCpp -Force -ErrorAction SilentlyContinue

$GeneratorArgs = @(
    $GeneratorPath,
    "--rom", $RomPath,
    "--output-config", $ConfigPath,
    "--output-cpp", $OutputCpp,
    "--output-report", $ReportPath
)
$PythonExecutableName = [System.IO.Path]::GetFileNameWithoutExtension($Python.Source)
$UsePyLauncher = $PythonExecutableName -ieq "py"
if ($UsePyLauncher) {
    $GeneratorArgs = @("-3") + $GeneratorArgs
}
Write-Host "Python executable: $($Python.Source)"
Write-Host "Python launcher mode: $UsePyLauncher"

Write-Host "[1/3] Validating NP3F ROM and generating config..."
& $Python.Source @GeneratorArgs
if ($LASTEXITCODE -ne 0) { throw "NP3F RSP config generation failed: $LASTEXITCODE" }

Write-Host "[2/3] Running RSPRecomp..."
& $RspExePath $ConfigPath
if ($LASTEXITCODE -ne 0) { throw "RSPRecomp failed: $LASTEXITCODE" }

Write-Host "[3/3] Verifying generated C++..."
if (-not (Test-Path -LiteralPath $OutputCpp -PathType Leaf)) {
    throw "Generated RSP C++ was not created: $OutputCpp"
}
$GeneratedText = Get-Content -LiteralPath $OutputCpp -Raw
if (-not $GeneratedText.Contains("RspExitReason aspMain_np3f(")) {
    throw "Generated RSP C++ is missing aspMain_np3f."
}
if ((Get-Item -LiteralPath $OutputCpp).Length -lt 4096) {
    throw "Generated RSP C++ is unexpectedly small."
}

$Report = Get-Content -LiteralPath $ReportPath -Raw | ConvertFrom-Json
if ($Report.sha1 -ne "d7e13535b671024a92822db01507e87bd42f68ec") {
    throw "Unexpected NP3F SHA-1 in report."
}
if ($Report.ucode_data_rom -ne "0x87C10") {
    throw "Unexpected NP3F ucode_data ROM offset: $($Report.ucode_data_rom)"
}

$CppHash = (Get-FileHash -LiteralPath $OutputCpp -Algorithm SHA256).Hash
Write-Host "Handler targets : $($Report.handler_target_count)"
Write-Host "Generated C++   : $OutputCpp"
Write-Host "C++ SHA-256     : $CppHash"
Write-Host "Report          : $ReportPath"
Write-Host "NP3F audio RSP generation completed successfully."
exit 0
