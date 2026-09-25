param(
    [switch]$Clean,
    [int]$Parallel = 0
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$RunnerVersion = "2026-09-25.1"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"
$N64RecompInclude = Join-Path $RepoRoot ".local\n64recomp\src\include"
$CMakeSource = Join-Path $RepoRoot "cmake\np3f_generated_smoke"
$BuildDir = Join-Path $RepoRoot "build\np3f\generated-smoke-vs2022-x64"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$ConfigureLog = Join-Path $LogDir "NP3F_GENERATED_SMOKE_CONFIGURE.log"
$BuildLog = Join-Path $LogDir "NP3F_GENERATED_SMOKE_BUILD.log"

Write-Host "=== Aero-Stadium-2-FR / NP3F generated-code smoke build ==="
Write-Host "Runner version: $RunnerVersion"
Write-Host ""

if ($null -eq (Get-Command cmake -ErrorAction SilentlyContinue)) {
    throw "CMake was not found in PATH."
}

$ProgramFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
$VsWhere = Join-Path $ProgramFilesX86 "Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path -LiteralPath $VsWhere -PathType Leaf)) {
    throw "Visual Studio Build Tools 2022 was not found."
}

$VsInstall = & $VsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if ([string]::IsNullOrWhiteSpace($VsInstall)) {
    throw "MSVC x64/x86 C++ tools are missing from Visual Studio Build Tools 2022."
}

$RequiredFiles = @(
    (Join-Path $GeneratedDir "funcs.h"),
    (Join-Path $GeneratedDir "lookup.cpp"),
    (Join-Path $N64RecompInclude "recomp.h"),
    (Join-Path $CMakeSource "CMakeLists.txt")
)

foreach ($RequiredFile in $RequiredFiles) {
    if (-not (Test-Path -LiteralPath $RequiredFile -PathType Leaf)) {
        throw "Required file not found: $RequiredFile"
    }
}

$GeneratedSources = @(Get-ChildItem -LiteralPath $GeneratedDir -Filter "funcs_*.c" -File)
if ($GeneratedSources.Count -eq 0) {
    throw "No generated funcs_*.c files were found in $GeneratedDir."
}

Write-Host "Generated translation units : $($GeneratedSources.Count)"
Write-Host "N64Recomp header            : $(Join-Path $N64RecompInclude 'recomp.h')"
Write-Host "Build directory             : $BuildDir"
Write-Host ""

if ($Parallel -le 0) {
    $Parallel = [Math]::Min(8, [Environment]::ProcessorCount)
    if ($Parallel -lt 1) {
        $Parallel = 1
    }
}

if ($Clean -and (Test-Path -LiteralPath $BuildDir)) {
    Write-Host "Removing previous smoke-build directory..."
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
Remove-Item -LiteralPath $ConfigureLog -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $BuildLog -Force -ErrorAction SilentlyContinue

$GeneratedCMake = $GeneratedDir.Replace("\", "/")
$IncludeCMake = $N64RecompInclude.Replace("\", "/")

Write-Host "[1/2] Configuring generated-code smoke build..."

$ConfigureArgs = @(
    "-S", $CMakeSource,
    "-B", $BuildDir,
    "-G", "Visual Studio 17 2022",
    "-A", "x64",
    "-DNP3F_GENERATED_DIR=$GeneratedCMake",
    "-DN64RECOMP_INCLUDE_DIR=$IncludeCMake"
)

& cmake @ConfigureArgs 2>&1 | Tee-Object -FilePath $ConfigureLog
$ConfigureExit = $LASTEXITCODE

if ($ConfigureExit -ne 0) {
    Write-Host ""
    Write-Host "Configure log: $ConfigureLog"
    throw "CMake configuration failed with exit code $ConfigureExit."
}

Write-Host ""
Write-Host "[2/2] Compiling all generated NP3F translation units..."
Write-Host "Parallel jobs: $Parallel"

$BuildArgs = @(
    "--build", $BuildDir,
    "--config", "Release",
    "--target", "AeroNP3FGenerated",
    "--parallel", "$Parallel"
)

& cmake @BuildArgs 2>&1 | Tee-Object -FilePath $BuildLog
$BuildExit = $LASTEXITCODE

Write-Host ""
Write-Host "Configure log : $ConfigureLog"
Write-Host "Build log     : $BuildLog"

if ($BuildExit -ne 0) {
    Write-Host "Generated-code smoke build stopped with exit code $BuildExit."
    exit $BuildExit
}

$Library = Get-ChildItem -LiteralPath $BuildDir -Filter "AeroNP3FGenerated.lib" -Recurse -File |
    Select-Object -First 1

if ($null -eq $Library) {
    throw "Compilation reported success but AeroNP3FGenerated.lib was not found."
}

$SizeMB = [Math]::Round($Library.Length / 1MB, 2)

Write-Host ""
Write-Host "NP3F generated-code smoke build completed successfully."
Write-Host "Static library : $($Library.FullName)"
Write-Host "Library size   : $SizeMB MB"
exit 0
