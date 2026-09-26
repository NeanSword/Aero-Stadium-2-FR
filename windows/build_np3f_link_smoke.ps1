param([switch]$Clean)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$RunnerVersion = "2026-09-26.5"

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

function Stop-StaleBuildProcesses {
    param([Parameter(Mandatory = $true)][string]$TargetBuildDir)

    $NormalizedTarget = $TargetBuildDir.ToLowerInvariant()

    $Candidates = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -in @("cmake.exe", "MSBuild.exe", "cl.exe", "link.exe", "AeroStadium2.exe") -and
            $_.CommandLine -and
            $_.CommandLine.ToLowerInvariant().Contains($NormalizedTarget)
        }

    foreach ($Candidate in $Candidates) {
        Write-Host (
            "[clean] Arret de l'ancien processus {0} PID={1} qui utilise ce build..." -f
            $Candidate.Name,
            $Candidate.ProcessId
        ) -ForegroundColor Yellow

        Stop-Process -Id $Candidate.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

function Remove-BuildDirectoryRobust {
    param([Parameter(Mandatory = $true)][string]$TargetBuildDir)

    if (-not (Test-Path -LiteralPath $TargetBuildDir)) {
        return
    }

    for ($Attempt = 1; $Attempt -le 5; $Attempt++) {
        try {
            Remove-Item -LiteralPath $TargetBuildDir -Recurse -Force -ErrorAction Stop
            return
        }
        catch {
            if ($Attempt -eq 1) {
                Write-Host "[clean] Le dossier de build est verrouille. Recherche des anciens CMake/MSBuild..." -ForegroundColor Yellow
                Stop-StaleBuildProcesses -TargetBuildDir $TargetBuildDir
            }

            if ($Attempt -lt 5) {
                Write-Host ("[clean] Nouvelle tentative {0}/5..." -f ($Attempt + 1)) -ForegroundColor DarkGray
                Start-Sleep -Milliseconds 750
            }
            else {
                throw ((
                    "Impossible de nettoyer le dossier de build apres 5 tentatives: {0}. " +
                    "Ferme toute ancienne fenetre AeroStadium2/CMake/Visual Studio qui utilise ce projet puis relance."
                ) -f $TargetBuildDir)
            }
        }
    }
}

if ($Clean) {
    Remove-BuildDirectoryRobust -TargetBuildDir $BuildDir
}
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
foreach ($OldLog in @($ConfigureLog,$ConfigureStdoutLog,$ConfigureStderrLog,$BuildLog,$BuildStdoutLog,$BuildStderrLog)) { Remove-Item -LiteralPath $OldLog -Force -ErrorAction SilentlyContinue }

$CMakeExe = (Get-Command cmake -ErrorAction Stop).Source
$GeneratedLibCMake = $GeneratedLib.FullName.Replace("\", "/")
$GeneratedDirCMake = $GeneratedDir.Replace("\", "/")
$RuntimeSourceCMake = $RuntimeSource.Replace("\", "/")
$RuntimeBuildCMake = $RuntimeBuild.Replace("\", "/")
$Rt64SourceCMake = $Rt64Source.Replace("\", "/")

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$StdoutLog,
        [Parameter(Mandatory = $true)][string]$StderrLog,
        [Parameter(Mandatory = $true)][string]$Activity
    )

    Remove-Item -LiteralPath $StdoutLog -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $StderrLog -Force -ErrorAction SilentlyContinue

    $Process = Start-Process `
        -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDirectory `
        -NoNewWindow `
        -PassThru `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog

    $StdoutSeen = 0
    $StderrSeen = 0
    $LastVisibleActivity = Get-Date

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

        if (((Get-Date) - $LastVisibleActivity).TotalSeconds -ge 10) {
            Write-Host ("[{0}] Toujours en cours... PID={1}" -f $Activity, $Process.Id) -ForegroundColor DarkGray
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

    return [int]$Process.ExitCode
}


Write-Host "Generated NP3F library : $($GeneratedLib.FullName)"
Write-Host "Runtime source         : $RuntimeSource"
Write-Host "Runtime prebuilt libs  : $RuntimeBuild"
Write-Host "RT64 source            : $Rt64Source"
Write-Host ""
Write-Host "[1/2] Configuring first AeroStadium2.exe link..."
$ConfigureArgs = @(
    "-Wno-deprecated",
    "-Wno-policy",
    "-S", ('"{0}"' -f $CMakeSource),
    "-B", ('"{0}"' -f $BuildDir),
    "-G", '"Visual Studio 17 2022"',
    "-A", "x64",
    ('"-DNP3F_GENERATED_LIB={0}"' -f $GeneratedLibCMake),
    ('"-DNP3F_GENERATED_DIR={0}"' -f $GeneratedDirCMake),
    ('"-DN64MODERNRUNTIME_SOURCE_DIR={0}"' -f $RuntimeSourceCMake),
    ('"-DN64MODERNRUNTIME_BUILD_DIR={0}"' -f $RuntimeBuildCMake),
    ('"-DRT64_SOURCE_DIR={0}"' -f $Rt64SourceCMake)
)

$ConfigureExit = Invoke-LoggedProcess `
    -FilePath $CMakeExe `
    -ArgumentList $ConfigureArgs `
    -WorkingDirectory $RepoRoot `
    -StdoutLog $ConfigureStdoutLog `
    -StderrLog $ConfigureStderrLog `
    -Activity "CMake configure"
$ConfigureStdout = if (Test-Path $ConfigureStdoutLog) { @(Get-Content $ConfigureStdoutLog) } else { @() }
$ConfigureStderr = if (Test-Path $ConfigureStderrLog) { @(Get-Content $ConfigureStderrLog) } else { @() }
@("=== CMake configure stdout ===",$ConfigureStdout,"","=== CMake configure stderr ===",$ConfigureStderr,"","=== CMake configure exit code: $ConfigureExit ===") | Set-Content -LiteralPath $ConfigureLog -Encoding UTF8
if ($ConfigureExit -ne 0) { exit $ConfigureExit }

Write-Host ""
Write-Host "[2/2] Linking AeroStadium2.exe..."
$env:MSBUILDDISABLENODEREUSE = "1"
$BuildArgs = @(
    "--build", ('"{0}"' -f $BuildDir),
    "--config", "Release",
    "--target", "AeroStadium2",
    "--",
    "/m:1",
    "/nodeReuse:false"
)

$BuildExit = Invoke-LoggedProcess `
    -FilePath $CMakeExe `
    -ArgumentList $BuildArgs `
    -WorkingDirectory $RepoRoot `
    -StdoutLog $BuildStdoutLog `
    -StderrLog $BuildStderrLog `
    -Activity "MSBuild"
$BuildStdout = if (Test-Path $BuildStdoutLog) { @(Get-Content $BuildStdoutLog) } else { @() }
$BuildStderr = if (Test-Path $BuildStderrLog) { @(Get-Content $BuildStderrLog) } else { @() }

# Some Visual Studio/CMake combinations can occasionally return a successful
# wrapper exit code even though MSBuild printed a compiler or linker error.
# Treat known MSVC/MSBuild error signatures as authoritative.
$BuildText = @($BuildStdout + $BuildStderr) -join [Environment]::NewLine
$BuildErrorPattern = '(?im)(\berror\s+C\d{4}\b|\bfatal error\b|\berror\s+LNK\d{4}\b|\bMSB\d{4}:\s*error\b)'
if ($BuildText -match $BuildErrorPattern) {
    if ($BuildExit -eq 0) {
        Write-Host "[build] Une erreur compilateur/linker a ete detectee malgre un code retour CMake egal a 0." -ForegroundColor Yellow
    }
    $BuildExit = 1
}

@("=== CMake build stdout ===",$BuildStdout,"","=== CMake build stderr ===",$BuildStderr,"","=== CMake build exit code: $BuildExit ===") | Set-Content -LiteralPath $BuildLog -Encoding UTF8
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