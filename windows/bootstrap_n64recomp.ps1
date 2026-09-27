param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$BootstrapVersion = "2026-09-27.2"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LocalRoot = Join-Path $RepoRoot ".local\n64recomp"
$SourceDir = Join-Path $LocalRoot "src"

# Use a generator-specific build directory so stale NMake caches can never
# conflict with the Visual Studio generator.
$BuildDir = Join-Path $LocalRoot "build-vs2022-x64"

$BinDir = Join-Path $RepoRoot ".local\bin"
$ExePath = Join-Path $BinDir "N64Recomp.exe"
$RspExePath = Join-Path $BinDir "RSPRecomp.exe"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$BuildStdoutLog = Join-Path $LogDir "NP3F_N64RECOMP_BUILD.stdout.log"
$BuildStderrLog = Join-Path $LogDir "NP3F_N64RECOMP_BUILD.stderr.log"

$N64RecompCommit = "ffb39cdad1da5de07eaaa48bd1db4a89a7986771"
$ForbiddenAeroHooks = @(
    "aero_lookup_asset",
    "aero_cartridge_read_u32",
    "aero_poll_events"
)

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

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$ArgumentLine,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$StdoutLog,
        [Parameter(Mandatory = $true)][string]$StderrLog,
        [Parameter(Mandatory = $true)][string]$Activity,
        [int]$HeartbeatSeconds = 10
    )

    Remove-Item -LiteralPath $StdoutLog -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $StderrLog -Force -ErrorAction SilentlyContinue

    $StartedAt = Get-Date
    $Process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentLine `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow `
        -PassThru `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog

    $StdoutSeen = 0
    $StderrSeen = 0
    $LastVisibleActivity = Get-Date

    Write-Host ("[{0}] Demarre. PID={1}" -f $Activity, $Process.Id) -ForegroundColor DarkGray

    while (-not $Process.HasExited) {
        Start-Sleep -Milliseconds 250

        $StdoutLines = if (Test-Path -LiteralPath $StdoutLog) {
            @(Get-Content -LiteralPath $StdoutLog -ErrorAction SilentlyContinue)
        } else { @() }

        if ($StdoutLines.Count -gt $StdoutSeen) {
            for ($Index = $StdoutSeen; $Index -lt $StdoutLines.Count; $Index++) {
                Write-Host $StdoutLines[$Index]
            }
            $StdoutSeen = $StdoutLines.Count
            $LastVisibleActivity = Get-Date
        }

        $StderrLines = if (Test-Path -LiteralPath $StderrLog) {
            @(Get-Content -LiteralPath $StderrLog -ErrorAction SilentlyContinue)
        } else { @() }

        if ($StderrLines.Count -gt $StderrSeen) {
            for ($Index = $StderrSeen; $Index -lt $StderrLines.Count; $Index++) {
                Write-Host $StderrLines[$Index] -ForegroundColor Yellow
            }
            $StderrSeen = $StderrLines.Count
            $LastVisibleActivity = Get-Date
        }

        if (((Get-Date) - $LastVisibleActivity).TotalSeconds -ge $HeartbeatSeconds) {
            $Elapsed = [int]((Get-Date) - $StartedAt).TotalSeconds
            Write-Host (
                "[{0}] Toujours en cours... PID={1} duree={2}s" -f
                $Activity,
                $Process.Id,
                $Elapsed
            ) -ForegroundColor DarkGray
            $LastVisibleActivity = Get-Date
        }
    }

    $Process.WaitForExit()

    $StdoutLines = if (Test-Path -LiteralPath $StdoutLog) {
        @(Get-Content -LiteralPath $StdoutLog -ErrorAction SilentlyContinue)
    } else { @() }
    for ($Index = $StdoutSeen; $Index -lt $StdoutLines.Count; $Index++) {
        Write-Host $StdoutLines[$Index]
    }

    $StderrLines = if (Test-Path -LiteralPath $StderrLog) {
        @(Get-Content -LiteralPath $StderrLog -ErrorAction SilentlyContinue)
    } else { @() }
    for ($Index = $StderrSeen; $Index -lt $StderrLines.Count; $Index++) {
        Write-Host $StderrLines[$Index] -ForegroundColor Yellow
    }

    $Elapsed = [int]((Get-Date) - $StartedAt).TotalSeconds
    Write-Host (
        "[{0}] Termine. PID={1} duree={2}s exit={3}" -f
        $Activity,
        $Process.Id,
        $Elapsed,
        $Process.ExitCode
    ) -ForegroundColor DarkGray

    return [int]$Process.ExitCode
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

foreach ($ForbiddenHook in $ForbiddenAeroHooks) {
    $SourceMatch = Get-ChildItem -LiteralPath $SourceDir -Recurse -File -ErrorAction SilentlyContinue |
        Select-String -SimpleMatch $ForbiddenHook -List -ErrorAction SilentlyContinue |
        Select-Object -First 1

    if ($null -ne $SourceMatch) {
        throw @"
Pinned N64Recomp source contains an unexpected Aero-specific hook:
  $ForbiddenHook
  $($SourceMatch.Path):$($SourceMatch.LineNumber)

Delete the local N64Recomp source/build and rerun this bootstrap with -Force.
"@
    }
}

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

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$CMakeExe = (Get-Command cmake -ErrorAction Stop).Source
$BuildArgumentLine = '--build "{0}" --config Release --target N64RecompCLI RSPRecomp --parallel' -f $BuildDir
$BuildExit = Invoke-LoggedProcess `
    -FilePath $CMakeExe `
    -ArgumentLine $BuildArgumentLine `
    -WorkingDirectory $RepoRoot `
    -StdoutLog $BuildStdoutLog `
    -StderrLog $BuildStderrLog `
    -Activity "MSBuild N64Recomp+RSPRecomp"

if ($BuildExit -ne 0) {
    throw "N64Recomp/RSPRecomp build failed with exit code $BuildExit. See $BuildStdoutLog and $BuildStderrLog."
}

$BuiltExe = Get-ChildItem -LiteralPath $BuildDir -Filter "N64Recomp.exe" -Recurse -File |
    Sort-Object { $_.FullName.Length } |
    Select-Object -First 1

if ($null -eq $BuiltExe) {
    throw "Build completed but N64Recomp.exe was not found."
}

$BuiltRspExe = Get-ChildItem -LiteralPath $BuildDir -Filter "RSPRecomp.exe" -Recurse -File |
    Sort-Object { $_.FullName.Length } |
    Select-Object -First 1

if ($null -eq $BuiltRspExe) {
    throw "Build completed but RSPRecomp.exe was not found."
}

Copy-Item -LiteralPath $BuiltExe.FullName -Destination $ExePath -Force
Copy-Item -LiteralPath $BuiltRspExe.FullName -Destination $RspExePath -Force

$ExeBytes = [System.IO.File]::ReadAllBytes($ExePath)
$ExeAscii = [System.Text.Encoding]::ASCII.GetString($ExeBytes)
foreach ($ForbiddenHook in $ForbiddenAeroHooks) {
    if ($ExeAscii.Contains($ForbiddenHook)) {
        throw @"
The freshly built N64Recomp executable still contains an obsolete Aero hook:
  $ForbiddenHook

Executable: $ExePath

This should never happen with the pinned upstream source. Do not use this binary.
"@
    }
}

Write-Host ""
Write-Host "[4/4] Verifying N64Recomp executable..."

& $ExePath
if ($LASTEXITCODE -ne 0) {
    throw "N64Recomp executable verification failed."
}

& $RspExePath
if ($LASTEXITCODE -ne 0) {
    throw "RSPRecomp executable verification failed."
}

$ExeHash = (Get-FileHash -LiteralPath $ExePath -Algorithm SHA256).Hash
$RspExeHash = (Get-FileHash -LiteralPath $RspExePath -Algorithm SHA256).Hash

$Versions = @{
    bootstrap_version = $BootstrapVersion
    n64recomp = $N64RecompCommit
    n64recomp_exe_sha256 = $ExeHash
    rsprecomp_exe_sha256 = $RspExeHash
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
Write-Host "N64Recomp : $ExePath"
Write-Host "  SHA-256 : $ExeHash"
Write-Host "RSPRecomp : $RspExePath"
Write-Host "  SHA-256 : $RspExeHash"
exit 0
