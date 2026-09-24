param(
    [Parameter(Mandatory=$true)]
    [string]$UsRom,

    [Parameter(Mandatory=$true)]
    [string]$FrRom,

    [int]$MinRun = 4096
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Tool = Join-Path $RepoRoot "tools\np3f\compare_roms.py"

python $Tool $UsRom $FrRom --min-run $MinRun
if ($LASTEXITCODE -ne 0) {
    throw "ROM comparison failed."
}
