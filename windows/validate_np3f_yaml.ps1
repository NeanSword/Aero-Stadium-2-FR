param(
    [Parameter(Mandatory=$true)]
    [string]$CandidateYaml
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Tool = Join-Path $RepoRoot "tools\np3f\validate_candidate_yaml.py"

python $Tool $CandidateYaml
if ($LASTEXITCODE -ne 0) {
    throw "NP3F candidate YAML validation failed."
}

Write-Host "NP3F candidate YAML validation passed."
