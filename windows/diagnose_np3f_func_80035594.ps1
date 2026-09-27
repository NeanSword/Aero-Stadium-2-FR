param()

$ErrorActionPreference = "Stop"
$RunnerVersion = "2026-09-27.3"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$Output = Join-Path $LogDir "NP3F_FUNC_80035594_SOURCE.txt"

Write-Host "=== Aero-Stadium-2-FR / diagnose func_80035594 ==="
Write-Host "Runner version: $RunnerVersion"

if (-not (Test-Path -LiteralPath $GeneratedDir -PathType Container)) {
    throw "Generated NP3F directory not found: $GeneratedDir"
}

$Matches = @(
    Get-ChildItem -LiteralPath $GeneratedDir -Filter "funcs_*.c" -File |
        Select-String -Pattern "\bfunc_80035594\s*\("
)

$ClassifiedMatches = New-Object System.Collections.Generic.List[object]
foreach ($Match in $Matches) {
    $CandidateLines = @(Get-Content -LiteralPath $Match.Path)
    $CandidateStart = $Match.LineNumber - 1
    $CandidateEnd = [Math]::Min($CandidateLines.Count - 1, $CandidateStart + 8)
    $SignatureText = ($CandidateLines[$CandidateStart..$CandidateEnd] -join " ")

    $OpenBraceIndex = $SignatureText.IndexOf("{")
    $SemicolonIndex = $SignatureText.IndexOf(";")
    $IsDefinition = $OpenBraceIndex -ge 0 -and ($SemicolonIndex -lt 0 -or $OpenBraceIndex -lt $SemicolonIndex)

    $ClassifiedMatches.Add([pscustomobject]@{
        Path = $Match.Path
        LineNumber = $Match.LineNumber
        Line = $Match.Line.Trim()
        IsDefinition = $IsDefinition
    })
}

$DefinitionMatches = @($ClassifiedMatches | Where-Object { $_.IsDefinition })
if ($DefinitionMatches.Count -ne 1) {
    $Summary = $ClassifiedMatches | ForEach-Object {
        "{0}:{1}: definition={2} :: {3}" -f $_.Path, $_.LineNumber, $_.IsDefinition, $_.Line
    }
    $SummaryText = $Summary -join [Environment]::NewLine
    $Message = "Expected exactly one generated definition for func_80035594, found $($DefinitionMatches.Count). Occurrences:" + [Environment]::NewLine + $SummaryText
    throw $Message
}

$SourcePath = $DefinitionMatches[0].Path
$Lines = @(Get-Content -LiteralPath $SourcePath)
$Start = $DefinitionMatches[0].LineNumber - 1

$BraceDepth = 0
$SeenOpeningBrace = $false
$End = $null
for ($i = $Start; $i -lt $Lines.Count; $i++) {
    $Line = $Lines[$i]
    $OpenCount = ([regex]::Matches($Line, "\{")).Count
    $CloseCount = ([regex]::Matches($Line, "\}")).Count
    if ($OpenCount -gt 0) { $SeenOpeningBrace = $true }
    $BraceDepth += $OpenCount
    $BraceDepth -= $CloseCount
    if ($SeenOpeningBrace -and $BraceDepth -eq 0) {
        $End = $i
        break
    }
}

if ($null -eq $End) {
    throw "Could not determine the end of func_80035594 in $SourcePath"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Report = New-Object System.Collections.Generic.List[string]
$Report.Add("=== NP3F func_80035594 generated-source diagnostic ===")
$Report.Add("Runner version: $RunnerVersion")
$Report.Add("Source: $SourcePath")
$Report.Add("Function lines: $($Start + 1)-$($End + 1)")
$Report.Add("")
$Report.Add("=== All func_80035594 occurrences ===")
foreach ($Occurrence in $ClassifiedMatches) {
    $Report.Add(("{0}:{1}: definition={2} :: {3}" -f $Occurrence.Path, $Occurrence.LineNumber, $Occurrence.IsDefinition, $Occurrence.Line))
}
$Report.Add("")
$Report.Add("=== Function source ===")
for ($i = $Start; $i -le $End; $i++) {
    $Report.Add(("{0,6}: {1}" -f ($i + 1), $Lines[$i]))
}

$Report.Add("")
$Report.Add("=== References to 0x8008498C / 8008498C in generated output ===")
$AddressHits = @(Get-ChildItem -LiteralPath $GeneratedDir -Recurse -File | Select-String -Pattern "8008498C" -SimpleMatch)
if ($AddressHits.Count -eq 0) {
    $Report.Add("(none)")
} else {
    foreach ($Hit in $AddressHits) {
        $Report.Add(("{0}:{1}: {2}" -f $Hit.Path, $Hit.LineNumber, $Hit.Line.Trim()))
    }
}

$Report.Add("")
$Report.Add("=== Obsolete Aero hook references in generated output ===")
foreach ($Hook in @("aero_poll_events", "aero_cartridge_read_u32", "aero_lookup_asset")) {
    $HookHits = @(Get-ChildItem -LiteralPath $GeneratedDir -Recurse -File | Select-String -Pattern $Hook -SimpleMatch)
    if ($HookHits.Count -eq 0) {
        $Report.Add("${Hook}: none")
    } else {
        foreach ($Hit in $HookHits) {
            $Report.Add(("{0}: {1}:{2}: {3}" -f $Hook, $Hit.Path, $Hit.LineNumber, $Hit.Line.Trim()))
        }
    }
}

$Report | Set-Content -LiteralPath $Output -Encoding UTF8
Write-Host "Source: $SourcePath"
Write-Host "Function lines: $($Start + 1)-$($End + 1)"
Write-Host "Diagnostic: $Output"
Write-Host "Done."
