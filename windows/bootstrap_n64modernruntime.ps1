param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$BootstrapVersion = "2026-09-27.3"

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

function Invoke-LoggedProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList,
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
        -ArgumentList $ArgumentList `
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

# N64ModernRuntime main currently passes a GCC/Clang warning switch directly
# to both runtime targets. Visual Studio translates "-Wno-unused-parameter"
# into "/Wno-unused-parameter", which MSVC rejects as D8021. Keep upstream
# sources otherwise untouched and gate that warning switch away on MSVC.
foreach ($RuntimeTarget in @("ultramodern", "librecomp")) {
    $RuntimeCMake = Join-Path $SourceDir "$RuntimeTarget\CMakeLists.txt"
    if (-not (Test-Path -LiteralPath $RuntimeCMake -PathType Leaf)) {
        throw "Runtime CMake file not found: $RuntimeCMake"
    }

    $RuntimeCMakeText = Get-Content -LiteralPath $RuntimeCMake -Raw
    $OldBlock = @"
target_compile_options($RuntimeTarget PRIVATE
#    -Wall
#    -Wextra
    -Wno-unused-parameter
)
"@
    $NewBlock = @"
if (NOT MSVC)
    target_compile_options($RuntimeTarget PRIVATE
    #    -Wall
    #    -Wextra
        -Wno-unused-parameter
    )
endif()
"@

    if ($RuntimeCMakeText.Contains($OldBlock)) {
        $RuntimeCMakeText = $RuntimeCMakeText.Replace($OldBlock, $NewBlock)
        Set-Content -LiteralPath $RuntimeCMake -Value $RuntimeCMakeText -Encoding UTF8
        Write-Host "Applied MSVC warning compatibility patch: $RuntimeTarget"
    }
    elseif ($RuntimeCMakeText -notmatch 'if \(NOT MSVC\)[\s\S]*-Wno-unused-parameter') {
        throw "Could not find expected warning block in $RuntimeCMake"
    }
}

# o1heap requires ISO C99 or newer and checks __STDC_VERSION__. Use CMake's
# native C language-standard selection for the entire librecomp subproject so
# Visual Studio emits /std:c17 for C translation units (currently o1heap.c).
$LibrecompCMake = Join-Path $SourceDir "librecomp\CMakeLists.txt"
$LibrecompText = Get-Content -LiteralPath $LibrecompCMake -Raw
$C17Marker = "# Aero-Stadium-2-FR librecomp C17 compatibility"

if (-not $LibrecompText.Contains($C17Marker)) {
    $CxxStandardBlock = @"
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS OFF)
"@
    $C17Block = @"
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS OFF)

# Aero-Stadium-2-FR librecomp C17 compatibility
set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED True)
set(CMAKE_C_EXTENSIONS OFF)
"@

    if (-not $LibrecompText.Contains($CxxStandardBlock)) {
        throw "Could not find librecomp language-standard block in $LibrecompCMake"
    }

    $LibrecompText = $LibrecompText.Replace($CxxStandardBlock, $C17Block)
    Set-Content -LiteralPath $LibrecompCMake -Value $LibrecompText -Encoding UTF8
    Write-Host "Applied CMake C17 compatibility patch: librecomp"
}

# N64ModernRuntime currently releases its virtual RDRAM reservation after
# joining the game-start/event/cleanup/save threads. NP3F creates additional
# host threads through osCreateThread; on shutdown, some of those threads can
# still be executing recompiled code after the cleaner exits. Releasing RDRAM
# at that point produces a deterministic use-after-free during process exit.
#
# Aero-Stadium-2-FR is currently a single-session Windows executable. Keep the
# RDRAM reservation alive until process termination, where Windows reclaims it
# automatically. Do not apply this workaround silently to an unexpected
# upstream source revision.
$RuntimeRecompCpp = Join-Path $SourceDir "librecomp\src\recomp.cpp"
if (-not (Test-Path -LiteralPath $RuntimeRecompCpp -PathType Leaf)) {
    throw "Runtime source file not found: $RuntimeRecompCpp"
}

$RuntimeRecompText = Get-Content -LiteralPath $RuntimeRecompCpp -Raw
$ShutdownPatchMarker = "// Aero-Stadium-2-FR Windows shutdown RDRAM lifetime patch 2026-09-27.1"
$OriginalWindowsFreeBlock = @"
#ifdef _WIN32
    // VirtualFree returns zero on failure.
    free_failed = (VirtualFree(rdram, 0, MEM_RELEASE) == 0);
#else
"@
$PatchedWindowsFreeBlock = @"
#ifdef _WIN32
    $ShutdownPatchMarker
    // Game-created host threads can still execute briefly after quit().
    // Keep RDRAM valid until the process exits instead of releasing it here.
    free_failed = false;
#else
"@

if ($RuntimeRecompText.Contains($ShutdownPatchMarker)) {
    if (-not $RuntimeRecompText.Contains($PatchedWindowsFreeBlock)) {
        throw "N64ModernRuntime shutdown patch marker exists, but the patched block does not match the expected content."
    }
    Write-Host "Windows shutdown RDRAM lifetime patch already applied."
}
elseif ($RuntimeRecompText.Contains($OriginalWindowsFreeBlock)) {
    $Occurrences = ([regex]::Matches(
        $RuntimeRecompText,
        [regex]::Escape($OriginalWindowsFreeBlock)
    )).Count
    if ($Occurrences -ne 1) {
        throw "Expected exactly one Windows RDRAM release block in $RuntimeRecompCpp, found $Occurrences."
    }

    $RuntimeRecompText = $RuntimeRecompText.Replace(
        $OriginalWindowsFreeBlock,
        $PatchedWindowsFreeBlock
    )
    Set-Content -LiteralPath $RuntimeRecompCpp -Value $RuntimeRecompText -Encoding UTF8
    Write-Host "Applied Windows shutdown RDRAM lifetime patch: librecomp"
}
else {
    throw "Could not find the expected N64ModernRuntime Windows RDRAM release block. Refusing to patch an unexpected source revision."
}

# Diagnose external OSMesgQueue delivery failures without changing runtime
# behavior. Stadium 2 can softlock if an external completion message reaches a
# temporarily full guest queue. Keep the existing requeue/drop policy intact,
# but preserve the event source and log failed non-blocking deliveries.
$MesgQueueCpp = Join-Path $SourceDir "ultramodern\src\mesgqueue.cpp"
if (-not (Test-Path -LiteralPath $MesgQueueCpp -PathType Leaf)) {
    throw "Runtime message queue source file not found: $MesgQueueCpp"
}

$MesgQueueText = Get-Content -LiteralPath $MesgQueueCpp -Raw
$MesgQueueDiagMarker = "// Aero-Stadium-2-FR external message queue diagnostics 2026-09-27.1"

$OriginalMesgQueueIncludes = @"
#include <bitset>
#include <thread>
"@
$PatchedMesgQueueIncludes = @"
#include <bitset>
#include <thread>
#include <cstdio>
"@

$OriginalQueuedMessage = @"
struct QueuedMessage {
    PTR(OSMesgQueue) mq;
    OSMesg mesg;
    bool jam;
    bool requeue_if_blocked;
};
"@
$PatchedQueuedMessage = @"
struct QueuedMessage {
    PTR(OSMesgQueue) mq;
    OSMesg mesg;
    bool jam;
    bool requeue_if_blocked;
    int source;
};
"@

$OriginalEnqueueSource = @"
void ultramodern::enqueue_external_message_src(PTR(OSMesgQueue) mq, OSMesg msg, bool jam, EventMessageSource src) {
    external_messages.enqueue({mq, msg, jam, requeue_enabled[static_cast<int>(src)]});
}

void ultramodern::enqueue_external_message(PTR(OSMesgQueue) mq, OSMesg msg, bool jam, bool requeue_if_blocked) {
    external_messages.enqueue({mq, msg, jam, requeue_if_blocked});
}
"@
$PatchedEnqueueSource = @"
void ultramodern::enqueue_external_message_src(PTR(OSMesgQueue) mq, OSMesg msg, bool jam, EventMessageSource src) {
    external_messages.enqueue({mq, msg, jam, requeue_enabled[static_cast<int>(src)], static_cast<int>(src)});
}

void ultramodern::enqueue_external_message(PTR(OSMesgQueue) mq, OSMesg msg, bool jam, bool requeue_if_blocked) {
    external_messages.enqueue({mq, msg, jam, requeue_if_blocked, -1});
}
"@

$OriginalExternalDelivery = @"
void dequeue_external_messages(RDRAM_ARG1) {
    QueuedMessage to_send;
    std::vector<QueuedMessage> requeued_messages{};
    while (external_messages.try_dequeue(to_send)) {
        if (!do_send(PASS_RDRAM to_send.mq, to_send.mesg, to_send.jam, false) && to_send.requeue_if_blocked) {
            requeued_messages.push_back(to_send);
        }
    }
    for (QueuedMessage& cur_mesg : requeued_messages) {
        external_messages.enqueue(cur_mesg);
    }
}

void ultramodern::wait_for_external_message(RDRAM_ARG1) {
    QueuedMessage to_send;
    external_messages.wait_dequeue(to_send);
    if (!do_send(PASS_RDRAM to_send.mq, to_send.mesg, to_send.jam, false) && to_send.requeue_if_blocked) {
        external_messages.enqueue(to_send);
    }
}

void ultramodern::wait_for_external_message_timed(RDRAM_ARG u32 millis) {
    QueuedMessage to_send;
    if (external_messages.wait_dequeue_timed(to_send, std::chrono::milliseconds{millis})) {
        if (!do_send(PASS_RDRAM to_send.mq, to_send.mesg, to_send.jam, false) && to_send.requeue_if_blocked) {
            external_messages.enqueue(to_send);
        }
    }
}
"@

$PatchedExternalDelivery = @"
$MesgQueueDiagMarker
const char* aerostadium2_event_source_name(int source) {
    switch (source) {
        case static_cast<int>(ultramodern::EventMessageSource::Timer): return "Timer";
        case static_cast<int>(ultramodern::EventMessageSource::Sp): return "SP";
        case static_cast<int>(ultramodern::EventMessageSource::Si): return "SI";
        case static_cast<int>(ultramodern::EventMessageSource::Ai): return "AI";
        case static_cast<int>(ultramodern::EventMessageSource::Vi): return "VI";
        case static_cast<int>(ultramodern::EventMessageSource::Pi): return "PI";
        case static_cast<int>(ultramodern::EventMessageSource::Dp): return "DP";
        default: return "generic";
    }
}

void aerostadium2_log_external_send_failure(RDRAM_ARG const QueuedMessage& message) {
    static uint32_t logged_failures = 0;
    if (logged_failures >= 256) {
        return;
    }

    OSMesgQueue* mq = TO_PTR(OSMesgQueue, message.mq);
    std::fprintf(
        stderr,
        "[mq-ext-fail] source=%s mq=0x%08X msg=0x%08X jam=%d requeue=%d valid=%d count=%d\n",
        aerostadium2_event_source_name(message.source),
        static_cast<uint32_t>(message.mq),
        static_cast<uint32_t>(message.mesg),
        message.jam ? 1 : 0,
        message.requeue_if_blocked ? 1 : 0,
        mq->validCount,
        mq->msgCount
    );
    std::fflush(stderr);
    ++logged_failures;
}

void dequeue_external_messages(RDRAM_ARG1) {
    QueuedMessage to_send;
    std::vector<QueuedMessage> requeued_messages{};
    while (external_messages.try_dequeue(to_send)) {
        const bool sent = do_send(PASS_RDRAM to_send.mq, to_send.mesg, to_send.jam, false);
        if (!sent) {
            aerostadium2_log_external_send_failure(PASS_RDRAM to_send);
            if (to_send.requeue_if_blocked) {
                requeued_messages.push_back(to_send);
            }
        }
    }
    for (QueuedMessage& cur_mesg : requeued_messages) {
        external_messages.enqueue(cur_mesg);
    }
}

void ultramodern::wait_for_external_message(RDRAM_ARG1) {
    QueuedMessage to_send;
    external_messages.wait_dequeue(to_send);
    const bool sent = do_send(PASS_RDRAM to_send.mq, to_send.mesg, to_send.jam, false);
    if (!sent) {
        aerostadium2_log_external_send_failure(PASS_RDRAM to_send);
        if (to_send.requeue_if_blocked) {
            external_messages.enqueue(to_send);
        }
    }
}

void ultramodern::wait_for_external_message_timed(RDRAM_ARG u32 millis) {
    QueuedMessage to_send;
    if (external_messages.wait_dequeue_timed(to_send, std::chrono::milliseconds{millis})) {
        const bool sent = do_send(PASS_RDRAM to_send.mq, to_send.mesg, to_send.jam, false);
        if (!sent) {
            aerostadium2_log_external_send_failure(PASS_RDRAM to_send);
            if (to_send.requeue_if_blocked) {
                external_messages.enqueue(to_send);
            }
        }
    }
}
"@

if ($MesgQueueText.Contains($MesgQueueDiagMarker)) {
    foreach ($ExpectedBlock in @(
        $PatchedMesgQueueIncludes,
        $PatchedQueuedMessage,
        $PatchedEnqueueSource,
        $PatchedExternalDelivery
    )) {
        if (-not $MesgQueueText.Contains($ExpectedBlock)) {
            throw "N64ModernRuntime message queue diagnostic marker exists, but a patched block does not match the expected content."
        }
    }
    Write-Host "External message queue diagnostics already applied."
}
else {
    foreach ($RequiredBlock in @(
        $OriginalMesgQueueIncludes,
        $OriginalQueuedMessage,
        $OriginalEnqueueSource,
        $OriginalExternalDelivery
    )) {
        if (-not $MesgQueueText.Contains($RequiredBlock)) {
            throw "Could not find an expected N64ModernRuntime message queue block. Refusing to patch an unexpected source revision."
        }
    }

    $MesgQueueText = $MesgQueueText.Replace($OriginalMesgQueueIncludes, $PatchedMesgQueueIncludes)
    $MesgQueueText = $MesgQueueText.Replace($OriginalQueuedMessage, $PatchedQueuedMessage)
    $MesgQueueText = $MesgQueueText.Replace($OriginalEnqueueSource, $PatchedEnqueueSource)
    $MesgQueueText = $MesgQueueText.Replace($OriginalExternalDelivery, $PatchedExternalDelivery)
    Set-Content -LiteralPath $MesgQueueCpp -Value $MesgQueueText -Encoding UTF8
    Write-Host "Applied external OSMesgQueue delivery diagnostics: ultramodern"
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

$ConfigureExit = Invoke-LoggedProcess `
    -FilePath $CMakeExe `
    -ArgumentList $ConfigureArgumentLine `
    -WorkingDirectory $RepoRoot `
    -StdoutLog $ConfigureStdoutLog `
    -StderrLog $ConfigureStderrLog `
    -Activity "CMake configure"

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

$BuildExit = Invoke-LoggedProcess `
    -FilePath $CMakeExe `
    -ArgumentList $BuildArgumentLine `
    -WorkingDirectory $RepoRoot `
    -StdoutLog $BuildStdoutLog `
    -StderrLog $BuildStderrLog `
    -Activity "MSBuild ultramodern+librecomp"

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
    aero_windows_shutdown_rdram_patch = "2026-09-27.1"
    aero_message_queue_diagnostics = "2026-09-27.1"
}

$Versions | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $LocalRoot "versions.json") -Encoding UTF8

Write-Host ""
Write-Host "N64ModernRuntime build completed successfully."
Write-Host "ultramodern : $($UltraLib.FullName)"
Write-Host "librecomp   : $($LibrecompLib.FullName)"
exit 0
