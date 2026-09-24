param(
    [Parameter(Mandatory=$true)]
    [string]$UsRom,

    [string]$FrRom = "",

    [string]$Yaml = ""
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
    python .\tools\np3f\compare_subsegments.py --fr $FrPath --us $UsPath --yaml $YamlPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "NP3F/NP3E subsegment report completed."
Write-Host "JSON: build\np3f\analysis\subsegment_diff.json"
Write-Host "CSV : build\np3f\analysis\subsegment_diff.csv"
