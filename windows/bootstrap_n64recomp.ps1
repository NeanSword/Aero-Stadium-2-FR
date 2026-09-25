param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$BootstrapVersion = "2026-09-25.3"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LocalRoot = Join-Path $RepoRoot ".local\n64recomp"
$SourceDir = Join-Path $LocalRoot "src"

# Use a generator-specific build directory so stale NMake caches can never
# conflict with the Visual Studio generator.
$BuildDir = Join-Path $LocalRoot "build-vs2022-x64"

$BinDir = Join-Path $RepoRoot ".local\bin"
$ExePath = Join-Path $BinDir "N64Recomp.exe"

$N64RecompCommit = "ffb39cdad1da5de07eaaa48bd1db4a89a7986771"

$Dependencies = @(
    @{ Owner = "Decompollaborate"; Repo = "rabbitizer"; Commit = "e0d8003047938e2ec3697eaf8d61a84d11d17b43"; Path = "lib\rabbitizer" },
    @{ Owner = "serge1"; Repo = "ELFIO"; Commit = "ad8b641f9682b6091ba8b9f7c8152255c1a2c803"; Path = "lib\ELFIO" },
    @{ Owner = "fmtlib"; Repo = "fmt"; Commit = "407c905e45ad75fc29bf0f9bb7c5c2fd3475976f"; Path = "lib\fmt" },
    @{ Owner = "marzer"; Repo = "tomlplusplus"; Commit = "1f7884e59165e517462f922e7b6de131bd9844f3"; Path = "lib\tomlplusplus" },
    @{ Owner = "zherczeg"; Repo = "sljit"; Commit = "f6326087b3404efb07c6d3deed97b3c3b8098c0c"; Path = "lib\sljit" }
)

function Install-GitHubArchive {
    param(
        [Parameter(Mandatory = $true)][string]$Owner,
        [Parameter(Mandatory = $true)][string]$Repo,
        [Parameter(Mandatory = $true)][string]$Commit,
        [Parameter(Mandatory = $true)][string]$Destination
    )

    $TempRoot = Join-Path $env:TEMP ("aero-n64recomp-" + [Guid]::NewGuid().ToString("N"))
    $ZipPath = Join-Path $TempRoot "$Repo.zip"
    $ExtractRoot = Join-Path $TempRoot "extract"

    New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

    try {
        $Url = "https://github.com/$Owner/$Repo/archive/$Commit.zip"
        Write-Host "  Downloading $Owner/$Repo @ $Commit"

        Invoke-WebRequest -Uri $Url -OutFile $ZipPath
        Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractRoot -Force

        $ArchiveRoot = Get-ChildItem -LiteralPath $ExtractRoot -Directory | Select-Object -First 1
        if ($null -eq $ArchiveRoot) {
            throw "Could not locate extracted archive root for $Owner/$Repo."
        }

        if (Test-Path -LiteralPath $Destination) {
            Remove-Item -LiteralPath $Destination -Recurse -Force
        }

        New-Item -ItemType Directory -Force -Path $Destination | Out-Null

        Get-ChildItem -LiteralPath $ArchiveRoot.FullName -Force | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $Destination -Recurse -Force
        }
    }
    finally {
        if (Test-Path -LiteralPath $TempRoot) {
            Remove-Item -LiteralPath $TempRoot -Recurse -Force
        }
    }
}

Write-Host "=== Aero-Stadium-2-FR / N64Recomp bootstrap ==="
Write-Host "Bootstrap version: $BootstrapVersion"
Write-Host "Pinned N64Recomp commit: $N64RecompCommit"
Write-Host ""

if ($null -eq (Get-Command cmake -ErrorAction SilentlyContinue)) {
    throw "CMake was not found in PATH. Install CMake 3.20+ first."
}

$CMakeVersion = (& cmake --version | Select-Object -First 1)
Write-Host $CMakeVersion
Write-Host ""

$ProgramFilesX86 = [Environment]::GetFolderPath("ProgramFilesX86")
$VsWhere = Join-Path $ProgramFilesX86 "Microsoft Visual Studio\Installer\vswhere.exe"

if (-not (Test-Path -LiteralPath $VsWhere -PathType Leaf)) {
    throw @"
Visual Studio Build Tools 2022 was not found.

Install it from an elevated PowerShell with:
winget install --id Microsoft.VisualStudio.2022.BuildTools --exact --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --norestart"
"@
}

$VsInstall = & $VsWhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath

if ([string]::IsNullOrWhiteSpace($VsInstall)) {
    throw @"
Visual Studio Build Tools was found, but the MSVC x64/x86 C++ tools are missing.

Install or modify Build Tools with:
Microsoft.VisualStudio.Workload.VCTools
"@
}

Write-Host "MSVC Build Tools:"
Write-Host "  $VsInstall"
Write-Host ""

if ($Force -or -not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    Write-Host "[1/4] Downloading pinned N64Recomp source without Git..."
    Install-GitHubArchive -Owner "N64Recomp" -Repo "N64Recomp" -Commit $N64RecompCommit -Destination $SourceDir

    Write-Host ""
    Write-Host "[2/4] Downloading pinned N64Recomp submodules without Git..."

    foreach ($Dependency in $Dependencies) {
        $Destination = Join-Path $SourceDir $Dependency.Path
        Install-GitHubArchive -Owner $Dependency.Owner -Repo $Dependency.Repo -Commit $Dependency.Commit -Destination $Destination
    }
}
else {
    Write-Host "[1/4] Existing pinned source found: $SourceDir"
    Write-Host "[2/4] Existing dependencies retained. Use -Force to redownload."
}

Write-Host ""
Write-Host "[3/4] Configuring and building N64Recomp..."
Write-Host "Build directory: $BuildDir"

if ($Force -and (Test-Path -LiteralPath $BuildDir)) {
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
}

# This directory is intentionally separate from the old ".local\n64recomp\build"
# directory that may contain an NMake cache from earlier attempts.
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

& cmake -S $SourceDir -B $BuildDir -G "Visual Studio 17 2022" -A x64
if ($LASTEXITCODE -ne 0) {
    throw "CMake configure failed with the Visual Studio 17 2022 x64 generator."
}

& cmake --build $BuildDir --config Release --target N64RecompCLI
if ($LASTEXITCODE -ne 0) {
    throw "N64Recomp build failed."
}

$BuiltExe = Get-ChildItem -LiteralPath $BuildDir -Filter "N64Recomp.exe" -Recurse -File |
    Sort-Object { $_.FullName.Length } |
    Select-Object -First 1

if ($null -eq $BuiltExe) {
    throw "Build completed but N64Recomp.exe was not found."
}

Copy-Item -LiteralPath $BuiltExe.FullName -Destination $ExePath -Force

Write-Host ""
Write-Host "[4/4] Verifying N64Recomp executable..."

& $ExePath
if ($LASTEXITCODE -ne 0) {
    throw "N64Recomp executable verification failed."
}

$Versions = @{
    n64recomp = $N64RecompCommit
    rabbitizer = "e0d8003047938e2ec3697eaf8d61a84d11d17b43"
    elfio = "ad8b641f9682b6091ba8b9f7c8152255c1a2c803"
    fmt = "407c905e45ad75fc29bf0f9bb7c5c2fd3475976f"
    tomlplusplus = "1f7884e59165e517462f922e7b6de131bd9844f3"
    sljit = "f6326087b3404efb07c6d3deed97b3c3b8098c0c"
}

$Versions |
    ConvertTo-Json |
    Set-Content -LiteralPath (Join-Path $LocalRoot "versions.json") -Encoding UTF8

Write-Host ""
Write-Host "N64Recomp bootstrap completed."
Write-Host "Executable: $ExePath"
exit 0
