param(
    [Parameter(Mandatory = $false)]
    [string]$Rva = "0x47BE09"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$MapFile = Join-Path $RepoRoot "build\np3f\link-smoke-prebuilt-vs2022-x64\bin\AeroStadium2.map"
$Resolver = Join-Path $RepoRoot "tools\recomp\resolve_msvc_map.py"

if (-not (Test-Path -LiteralPath $MapFile)) {
    throw "Map file not found: $MapFile"
}

Push-Location $RepoRoot
try {
    python $Resolver $MapFile $Rva --context 6
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
