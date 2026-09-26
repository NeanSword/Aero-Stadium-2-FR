param([switch]$Clean)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RunnerVersion = "2026-09-26.1"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"
$SmokeBuildDir = Join-Path $RepoRoot "build\np3f\generated-smoke-vs2022-x64"
$RuntimeSource = Join-Path $RepoRoot ".local\n64modernruntime\src"
$RuntimeBuild = Join-Path $RepoRoot ".local\n64modernruntime\build-vs2022-x64"
$Rt64Source = Join-Path $RepoRoot ".local\rt64\src"
$CMakeSource = Join-Path $RepoRoot "cmake\np3f_link_smoke"
$BuildDir = Join-Path $RepoRoot "build\np3f\link-smoke-prebuilt-vs2022-x64"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$ConfigureLog = Join-Path $LogDir "NP3F_LINK_SMOKE_CONFIGURE.log"
$ConfigureStdoutLog = Join-Path $LogDir "NP3F_LINK_SMOKE_CONFIGURE.stdout.log"
$ConfigureStderrLog = Join-Path $LogDir "NP3F_LINK_SMOKE_CONFIGURE.stderr.log"
$BuildLog = Join-Path $LogDir "NP3F_LINK_SMOKE_BUILD.log"
$BuildStdoutLog = Join-Path $LogDir "NP3F_LINK_SMOKE_BUILD.stdout.log"
$BuildStderrLog = Join-Path $LogDir "NP3F_LINK_SMOKE_BUILD.stderr.log"

Write-Host "=== Aero-Stadium-2-FR / first Windows linkage executable ==="
Write-Host "Runner version: $RunnerVersion"

$GeneratedLib = Get-ChildItem -LiteralPath $SmokeBuildDir -Filter "AeroNP3FGenerated.lib" -Recurse -File | Select-Object -First 1
if ($null -eq $GeneratedLib) { throw "AeroNP3FGenerated.lib was not found. Run .\windows\build_np3f_generated_smoke.ps1 first." }
if (-not (Test-Path -LiteralPath (Join-Path $RuntimeSource "CMakeLists.txt") -PathType Leaf)) { throw "N64ModernRuntime source was not found." }
if (-not (Test-Path -LiteralPath (Join-Path $Rt64Source "CMakeLists.txt") -PathType Leaf)) { throw "RT64 source was not found. Run .\windows\setup_rt64_windows.ps1 first." }
if (-not (Test-Path -LiteralPath (Join-Path $Rt64Source "src\hle\rt64_application.h") -PathType Leaf)) { throw "RT64 source is incomplete. Re-run .\windows\setup_rt64_windows.ps1 -Force." }
if (-not (Test-Path -LiteralPath (Join-Path $CMakeSource "CMakeLists.txt") -PathType Leaf)) { throw "Link-smoke CMakeLists.txt was not found." }

if ($Clean -and (Test-Path -LiteralPath $BuildDir)) { Remove-Item -LiteralPath $BuildDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
foreach ($OldLog in @($ConfigureLog,$ConfigureStdoutLog,$ConfigureStderrLog,$BuildLog,$BuildStdoutLog,$BuildStderrLog)) { Remove-Item -LiteralPath $OldLog -Force -ErrorAction SilentlyContinue }

$CMakeExe = (Get-Command cmake -ErrorAction Stop).Source
$GeneratedLibCMake = $GeneratedLib.FullName.Replace("\", "/")
$GeneratedDirCMake = $GeneratedDir.Replace("\", "/")
$RuntimeSourceCMake = $RuntimeSource.Replace("\", "/")
$RuntimeBuildCMake = $RuntimeBuild.Replace("\", "/")
$Rt64SourceCMake = $Rt64Source.Replace("\", "/")

Write-Host "Generated NP3F library : $($GeneratedLib.FullName)"
Write-Host "Runtime source         : $RuntimeSource"
Write-Host "Runtime prebuilt libs  : $RuntimeBuild"
Write-Host "RT64 source            : $Rt64Source"
Write-Host ""
Write-Host "[1/2] Configuring first AeroStadium2.exe link..."
$ConfigureArgumentLine = '-S "{0}" -B "{1}" -G "Visual Studio 17 2022" -A x64 -DNP3F_GENERATED_LIB="{2}" -DNP3F_GENERATED_DIR="{3}" -DN64MODERNRUNTIME_SOURCE_DIR="{4}"' -f $CMakeSource,$BuildDir,$GeneratedLibCMake,$GeneratedDirCMake,$RuntimeSourceCMake
Push-Location $RepoRoot
try {
    & $CMakeExe -S $CMakeSource -B $BuildDir -G "Visual Studio 17 2022" -A x64 `
        "-DNP3F_GENERATED_LIB=$GeneratedLibCMake" `
        "-DNP3F_GENERATED_DIR=$GeneratedDirCMake" `
        "-DN64MODERNRUNTIME_SOURCE_DIR=$RuntimeSourceCMake" `
        "-DN64MODERNRUNTIME_BUILD_DIR=$RuntimeBuildCMake" `
        "-DRT64_SOURCE_DIR=$Rt64SourceCMake" `
        1> $ConfigureStdoutLog 2> $ConfigureStderrLog
    $ConfigureExit = $LASTEXITCODE
}
finally {
    Pop-Location
}
$ConfigureStdout = if (Test-Path $ConfigureStdoutLog) { @(Get-Content $ConfigureStdoutLog) } else { @() }
$ConfigureStderr = if (Test-Path $ConfigureStderrLog) { @(Get-Content $ConfigureStderrLog) } else { @() }
@("=== CMake configure stdout ===",$ConfigureStdout,"","=== CMake configure stderr ===",$ConfigureStderr,"","=== CMake configure exit code: $ConfigureExit ===") | Set-Content -LiteralPath $ConfigureLog -Encoding UTF8
$ConfigureStdout | ForEach-Object { Write-Host $_ }
$ConfigureStderr | ForEach-Object { Write-Warning $_ }
if ($ConfigureExit -ne 0) { exit $ConfigureExit }

Write-Host ""
Write-Host "[2/2] Linking AeroStadium2.exe..."
$env:MSBUILDDISABLENODEREUSE = "1"
Push-Location $RepoRoot
try {
    & $CMakeExe --build $BuildDir --config Release --target AeroStadium2 -- /m:1 /nodeReuse:false `
        1> $BuildStdoutLog 2> $BuildStderrLog
    $BuildExit = $LASTEXITCODE
}
finally {
    Pop-Location
}
$BuildStdout = if (Test-Path $BuildStdoutLog) { @(Get-Content $BuildStdoutLog) } else { @() }
$BuildStderr = if (Test-Path $BuildStderrLog) { @(Get-Content $BuildStderrLog) } else { @() }
@("=== CMake build stdout ===",$BuildStdout,"","=== CMake build stderr ===",$BuildStderr,"","=== CMake build exit code: $BuildExit ===") | Set-Content -LiteralPath $BuildLog -Encoding UTF8
$BuildStdout | ForEach-Object { Write-Host $_ }
$BuildStderr | ForEach-Object { Write-Warning $_ }
Write-Host ""
Write-Host "Configure log : $ConfigureLog"
Write-Host "Build log     : $BuildLog"
if ($BuildExit -ne 0) { exit $BuildExit }

$Exe = Get-ChildItem -LiteralPath $BuildDir -Filter "AeroStadium2.exe" -Recurse -File | Select-Object -First 1
if ($null -eq $Exe) { throw "Link reported success but AeroStadium2.exe was not found." }
Write-Host ""
Write-Host "First AeroStadium2.exe linked successfully."
Write-Host "Executable: $($Exe.FullName)"
Write-Host ""
Write-Host "Running bootstrap executable..."
& $Exe.FullName
$ExeExit = $LASTEXITCODE
if ($ExeExit -ne 0) { throw "AeroStadium2.exe returned exit code $ExeExit." }
exit 0