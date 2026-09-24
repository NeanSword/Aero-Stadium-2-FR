param(
    [Parameter(Mandatory=$true)]
    [string]$SourceRom,

    [string]$Destination = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($Destination)) {
    $Destination = Join-Path $RepoRoot "baseroms\fr\baserom.z64"
}

$Tool = Join-Path $RepoRoot "tools\np3f\convert_to_z64.py"

python $Tool $SourceRom $Destination
if ($LASTEXITCODE -ne 0) {
    throw "ROM conversion failed."
}

Write-Host ""
Write-Host "Z64 conversion completed."
Write-Host "Run .\windows\verify_np3f.ps1 to verify the resulting dump."
