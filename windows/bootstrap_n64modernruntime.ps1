param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$BootstrapVersion = "2026-09-25.3"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LocalRoot = Join-Path $RepoRoot ".local\n64modernruntime"
$SourceDir = Join-Path $LocalRoot "src"
$BuildDir = Join-Path $LocalRoot "build-vs2022-x64"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$ConfigureLog = Join-Path $LogDir "NP3F_N64MODERNRUNTIME_CONFIGURE.log"
$ConfigureStdoutLog = Join-Path $LogDir "NP3F_N64MODERNRUNTIME_CONFIGURE.stdout.log"
$ConfigureStderrLog = Join-Path $LogDir "NP3F_N64MODERNRUNTIME_CONFIGURE.stderr.log"
$BuildLog = Join-Path $LogDir "NP3F_N64MODERNRUNTIME_BUILD.log"
$BuildStdoutLog = Join-Path $LogDir "NP3F_N64MODERNRUNTIME_BUILD.stdout.log"
$BuildStderrLog = Join-Path $LogDir "NP3F_N64MODERNRUNTIME_BUILD.stderr.log"

$RuntimeCommit = "cdf5abbd5026fef5c364c676e4667c45e42b6863"
$N64RecompCommit = "ffb39cdad1da5de07eaaa48bd1db4a89a7986771"

$Dependencies = @(
    @{ Owner = "Cyan4973"; Repo = "xxHash"; Commit = "680bf463fa1ca0461b9a7c2dab7556e1f54cf4cf"; Path = "thirdparty\xxHash" },
    @{ Owner = "richgel999"; Repo = "miniz"; Commit = "8573fd7cd6f49b262a0ccc447f3c6acfc415e556"; Path = "thirdparty\miniz" },
    @{ Owner = "N64Recomp"; Repo = "o1heap"; Commit = "a124b850791db2a33f7354d2b0aa7da821cef6f5"; Path = "thirdparty\o1heap" }
)

$N64RecompDependencies = @(
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

    $TempRoot = Join-Path $env:TEMP ("aero-runtime-" + [Guid]::NewGuid().ToString("N"))
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

Write-Host "=== Aero-Stadium-2-FR / N64ModernRuntime bootstrap ==="
Write-Host "Bootstrap version       : $BootstrapVersion"
Write-Host "N64ModernRuntime commit : $RuntimeCommit"
Write-Host "N64Recomp commit        : $N64RecompCommit"
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

Write-Host "MSVC Build Tools:"
Write-Host "  $VsInstall"
Write-Host ""

if ($Force -or -not (Test-Path -LiteralPath $SourceDir -PathType Container)) {
    Write-Host "[1/5] Downloading pinned N64ModernRuntime source..."
    Install-GitHubArchive -Owner "N64Recomp" -Repo "N64ModernRuntime" -Commit $RuntimeCommit -Destination $SourceDir

    Write-Host ""
    Write-Host "[2/5] Populating N64ModernRuntime submodules without Git..."
    foreach ($Dependency in $Dependencies) {
        Install-GitHubArchive -Owner $Dependency.Owner -Repo $Dependency.Repo -Commit $Dependency.Commit -Destination (Join-Path $SourceDir $Dependency.Path)
    }

    Write-Host ""
    Write-Host "[3/5] Populating pinned N64Recomp inside the runtime..."
    $RuntimeN64Recomp = Join-Path $SourceDir "N64Recomp"
    Install-GitHubArchive -Owner "N64Recomp" -Repo "N64Recomp" -Commit $N64RecompCommit -Destination $RuntimeN64Recomp

    foreach ($Dependency in $N64RecompDependencies) {
        Install-GitHubArchive -Owner $Dependency.Owner -Repo $Dependency.Repo -Commit $Dependency.Commit -Destination (Join-Path $RuntimeN64Recomp $Dependency.Path)
    }
}
else {
    Write-Host "[1/5] Existing runtime source found: $SourceDir"
    Write-Host "[2/5] Existing runtime dependencies retained."
    Write-Host "[3/5] Existing runtime N64Recomp retained."
    Write-Host "      Use -Force to redownload the pinned source set."
}

if ($Force -and (Test-Path -LiteralPath $BuildDir)) {
    Remove-Item -LiteralPath $BuildDir -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
foreach ($OldLog in @(
    $ConfigureLog,
    $ConfigureStdoutLog,
    $ConfigureStderrLog,
    $BuildLog,
    $BuildStdoutLog,
    $BuildStderrLog
)) {
    Remove-Item -LiteralPath $OldLog -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[4/5] Configuring N64ModernRuntime..."

$CMakeExe = (Get-Command cmake -ErrorAction Stop).Source

# Start-Process flattens ArgumentList into one command line. Quote every path
# and the Visual Studio generator explicitly so names containing spaces remain
# a single CMake argument on Windows PowerShell 5.1.
$ConfigureArgumentLine = '-S "{0}" -B "{1}" -G "Visual Studio 17 2022" -A x64' -f $SourceDir, $BuildDir

$ConfigureProcess = Start-Process `
    -FilePath $CMakeExe `
    -ArgumentList $ConfigureArgumentLine `
    -WorkingDirectory $RepoRoot `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $ConfigureStdoutLog `
    -RedirectStandardError $ConfigureStderrLog

$ConfigureExit = $ConfigureProcess.ExitCode

$ConfigureStdout = @()
$ConfigureStderr = @()
if (Test-Path -LiteralPath $ConfigureStdoutLog) {
    $ConfigureStdout = @(Get-Content -LiteralPath $ConfigureStdoutLog)
}
if (Test-Path -LiteralPath $ConfigureStderrLog) {
    $ConfigureStderr = @(Get-Content -LiteralPath $ConfigureStderrLog)
}

@(
    "=== CMake configure stdout ==="
    $ConfigureStdout
    ""
    "=== CMake configure stderr ==="
    $ConfigureStderr
    ""
    "=== CMake configure exit code: $ConfigureExit ==="
) | Set-Content -LiteralPath $ConfigureLog -Encoding UTF8

if ($ConfigureStdout.Count -gt 0) {
    $ConfigureStdout | ForEach-Object { Write-Host $_ }
}
if ($ConfigureStderr.Count -gt 0) {
    $ConfigureStderr | ForEach-Object { Write-Warning $_ }
}

if ($ConfigureExit -ne 0) {
    Write-Host ""
    Write-Host "Configure log        : $ConfigureLog"
    Write-Host "Configure stdout log : $ConfigureStdoutLog"
    Write-Host "Configure stderr log : $ConfigureStderrLog"
    exit $ConfigureExit
}

Write-Host ""
Write-Host "[5/5] Building ultramodern + librecomp..."

$BuildArgumentLine = '--build "{0}" --config Release --target ultramodern librecomp --parallel' -f $BuildDir

$BuildProcess = Start-Process `
    -FilePath $CMakeExe `
    -ArgumentList $BuildArgumentLine `
    -WorkingDirectory $RepoRoot `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $BuildStdoutLog `
    -RedirectStandardError $BuildStderrLog

$BuildExit = $BuildProcess.ExitCode

$BuildStdout = @()
$BuildStderr = @()
if (Test-Path -LiteralPath $BuildStdoutLog) {
    $BuildStdout = @(Get-Content -LiteralPath $BuildStdoutLog)
}
if (Test-Path -LiteralPath $BuildStderrLog) {
    $BuildStderr = @(Get-Content -LiteralPath $BuildStderrLog)
}

@(
    "=== CMake build stdout ==="
    $BuildStdout
    ""
    "=== CMake build stderr ==="
    $BuildStderr
    ""
    "=== CMake build exit code: $BuildExit ==="
) | Set-Content -LiteralPath $BuildLog -Encoding UTF8

if ($BuildStdout.Count -gt 0) {
    $BuildStdout | ForEach-Object { Write-Host $_ }
}
if ($BuildStderr.Count -gt 0) {
    $BuildStderr | ForEach-Object { Write-Warning $_ }
}

Write-Host ""
Write-Host "Configure log : $ConfigureLog"
Write-Host "Build log     : $BuildLog"

if ($BuildExit -ne 0) {
    Write-Host "Build stdout  : $BuildStdoutLog"
    Write-Host "Build stderr  : $BuildStderrLog"
    Write-Host "N64ModernRuntime build stopped with exit code $BuildExit."
    exit $BuildExit
}

$UltraLib = Get-ChildItem -LiteralPath $BuildDir -Filter "ultramodern.lib" -Recurse -File | Select-Object -First 1
$LibrecompLib = Get-ChildItem -LiteralPath $BuildDir -Filter "librecomp.lib" -Recurse -File | Select-Object -First 1

if ($null -eq $UltraLib -or $null -eq $LibrecompLib) {
    throw "Runtime build completed but ultramodern.lib and/or librecomp.lib was not found."
}

$Versions = @{
    n64modernruntime = $RuntimeCommit
    n64recomp = $N64RecompCommit
    xxhash = "680bf463fa1ca0461b9a7c2dab7556e1f54cf4cf"
    miniz = "8573fd7cd6f49b262a0ccc447f3c6acfc415e556"
    o1heap = "a124b850791db2a33f7354d2b0aa7da821cef6f5"
}

$Versions | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $LocalRoot "versions.json") -Encoding UTF8

Write-Host ""
Write-Host "N64ModernRuntime build completed successfully."
Write-Host "ultramodern : $($UltraLib.FullName)"
Write-Host "librecomp   : $($LibrecompLib.FullName)"
exit 0
