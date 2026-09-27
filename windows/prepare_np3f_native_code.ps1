# Run after Splat extraction and bootstrap_n64recomp.ps1.
param()
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RepoRoot '.venv/Scripts/python.exe'
$Source = Join-Path $RepoRoot '.local/n64recomp/src'
$Build = Join-Path $RepoRoot '.local/n64recomp/build-vs2022-x64'
$CMake = (Get-Command cmake -ErrorAction Stop).Source
$LogDir = Join-Path $RepoRoot 'build/np3f/logs'
New-Item -ItemType Directory -Force $LogDir | Out-Null
function Invoke-Step([string]$Name, [string]$Program, [string[]]$Arguments) {
    $Log = Join-Path $LogDir ($Name + '.log')
    $StdoutLog = Join-Path $LogDir ($Name + '.stdout.log')
    $StderrLog = Join-Path $LogDir ($Name + '.stderr.log')

    Remove-Item -LiteralPath $Log,$StdoutLog,$StderrLog -Force -ErrorAction SilentlyContinue

    # Windows PowerShell 5.1 converts native stderr into ErrorRecord objects.
    # unittest writes its normal progress dots to stderr, so with the script's
    # global ErrorActionPreference=Stop the old "*>" redirection aborted a
    # successful Python test run as NativeCommandError. Keep stdout/stderr
    # separate while the native process runs and trust its real exit code.
    $PreviousErrorActionPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        & $Program @Arguments 1> $StdoutLog 2> $StderrLog
        $ExitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $PreviousErrorActionPreference
    }

    @(
        "=== stdout ==="
        if (Test-Path -LiteralPath $StdoutLog) { Get-Content -LiteralPath $StdoutLog }
        ""
        "=== stderr ==="
        if (Test-Path -LiteralPath $StderrLog) { Get-Content -LiteralPath $StderrLog }
        ""
        "=== exit code: $ExitCode ==="
    ) | Set-Content -LiteralPath $Log -Encoding UTF8

    if ($ExitCode -ne 0) {
        Get-Content -LiteralPath $Log -Tail 50
        throw "Failed: $Name ($ExitCode)"
    }

    Write-Host "$Name : OK"
}
Push-Location $RepoRoot
try {
    Invoke-Step 'native_adapter_tests' $Python @('tools/recomp/test_native_adapters.py')
    Invoke-Step 'native_compiler_patch' $Python @('tools/recomp/patch_n64recomp_symbols.py', '--source', $Source)
    Invoke-Step 'native_compiler_configure' $CMake @('-S', $Source, '-B', $Build, '-G', 'Visual Studio 17 2022', '-A', 'x64')
    Invoke-Step 'native_compiler_build' $CMake @('--build', $Build, '--config', 'Release', '--target', 'N64RecompCLI', 'RSPRecomp', '--parallel', '2')
    $Compiler = Join-Path $RepoRoot '.local/bin/N64Recomp-native.exe'
    Copy-Item -LiteralPath (Join-Path $Build 'Release/N64Recomp.exe') -Destination $Compiler
    Invoke-Step 'native_symbols' $Python @('tools/recomp/generate_np3f_symbols.py')
    Invoke-Step 'native_relocations' $Python @('tools/recomp/add_np3f_relocations.py')
    Invoke-Step 'native_recompile' $Compiler @('recomp/np3f.toml')
    Invoke-Step 'native_audio_config' $Python @('tools/recomp/generate_np3f_rsp_audio.py',
        '--rom', 'baseroms/fr/baserom.z64', '--output-config', 'build/np3f/recomp/aspMain_np3f.toml',
        '--output-cpp', 'generated/rsp/np3f/aspMain_np3f.cpp',
        '--output-report', 'build/np3f/analysis/aspMain_np3f.json')
    Invoke-Step 'native_audio_recompile' (Join-Path $Build 'Release/RSPRecomp.exe') @('build/np3f/recomp/aspMain_np3f.toml')
    Invoke-Step 'native_task4_config' $Python @('tools/recomp/generate_np3f_rsp_task4.py',
        '--rom', 'baseroms/fr/baserom.z64', '--output-config', 'build/np3f/recomp/task4_np3f.toml',
        '--output-cpp', 'generated/rsp/np3f/task4_np3f.cpp',
        '--output-report', 'build/np3f/analysis/task4_np3f.json')
    Invoke-Step 'native_task4_recompile' (Join-Path $Build 'Release/RSPRecomp.exe') @('build/np3f/recomp/task4_np3f.toml')
}
finally { Pop-Location }
