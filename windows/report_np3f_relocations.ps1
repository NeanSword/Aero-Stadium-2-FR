param(
    [Parameter(Mandatory=$true)]
    [string]$UsRom,

    [string]$FrRom = "",

    [string]$Yaml = "",

    [string]$Window = "0x4000"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$FrPath = if ([string]::IsNullOrWhiteSpace($FrRom)) {
    Join-Path $RepoRoot "baseroms\fr\baserom.z64"
} else {
    (Resolve-Path -LiteralPath $FrRom).Path
}
$UsPath = (Resolve-Path -LiteralPath $UsRom).Path
$YamlPath = if ([string]::IsNullOrWhiteSpace($Yaml)) {
    Join-Path $RepoRoot "yamls\fr\splat.yaml"
} else {
    (Resolve-Path -LiteralPath $Yaml).Path
}

if (-not (Test-Path -LiteralPath $FrPath -PathType Leaf)) {
    throw "French ROM not found: $FrPath"
}
if (-not (Test-Path -LiteralPath $UsPath -PathType Leaf)) {
    throw "US ROM not found: $UsPath"
}
if (-not (Test-Path -LiteralPath $YamlPath -PathType Leaf)) {
    throw "Splat YAML not found: $YamlPath"
}

Push-Location $RepoRoot
try {
    python .\tools\np3f\map_subsegment_relocations.py --fr $FrPath --us $UsPath --yaml $YamlPath --window $Window
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "NP3F/NP3E relocation report completed."
Write-Host "JSON: build\np3f\analysis\subsegment_relocations.json"
Write-Host "CSV : build\np3f\analysis\subsegment_relocations.csv"
