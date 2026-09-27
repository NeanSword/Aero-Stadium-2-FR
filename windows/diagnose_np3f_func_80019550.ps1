param()

$ErrorActionPreference = "Stop"
$RunnerVersion = "2026-09-27.1"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$GeneratedDir = Join-Path $RepoRoot "generated\recomp\np3f"
$LogDir = Join-Path $RepoRoot "build\np3f\logs"
$ReportPath = Join-Path $LogDir "NP3F_FUNC_80019550_SOURCE.txt"
$Target = "func_80019550"

Write-Host "=== Aero-Stadium-2-FR / diagnose func_80019550 ==="
Write-Host "Runner version: $RunnerVersion"

if (-not (Test-Path -LiteralPath $GeneratedDir -PathType Container)) {
    throw "Generated NP3F directory not found: $GeneratedDir"
}
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Occurrences = @(
    Get-ChildItem -LiteralPath $GeneratedDir -Filter "funcs_*.c" -File |
        Select-String -Pattern "\bfunc_80019550\s*\("
)

if ($Occurrences.Count -eq 0) {
    throw "No generated occurrence of func_80019550 was found."
}

$Classified = New-Object System.Collections.Generic.List[object]
foreach ($Occurrence in $Occurrences) {
    $CandidateLines = @(Get-Content -LiteralPath $Occurrence.Path)
    $Start = $Occurrence.LineNumber - 1
    $End = [Math]::Min($CandidateLines.Count - 1, $Start + 8)
    $Text = ($CandidateLines[$Start..$End] -join " ")
    $Brace = $Text.IndexOf("{")
    $Semi = $Text.IndexOf(";")
    $IsDefinition = $Brace -ge 0 -and ($Semi -lt 0 -or $Brace -lt $Semi)
    $Classified.Add([pscustomobject]@{
        Path = $Occurrence.Path
        LineNumber = $Occurrence.LineNumber
        Line = $Occurrence.Line.Trim()
        IsDefinition = $IsDefinition
    })
}

$Definitions = @($Classified | Where-Object { $_.IsDefinition })
if ($Definitions.Count -ne 1) {
    $Summary = $Classified | ForEach-Object {
        "{0}:{1}: definition={2} :: {3}" -f $_.Path, $_.LineNumber, $_.IsDefinition, $_.Line
    }
    throw ("Expected exactly one definition of func_80019550, found {0}.`n{1}" -f $Definitions.Count, ($Summary -join [Environment]::NewLine))
}

$SourcePath = $Definitions[0].Path
$Lines = @(Get-Content -LiteralPath $SourcePath)
$Start = $Definitions[0].LineNumber - 1
$Depth = 0
$Started = $false
$End = $Start
for ($Index = $Start; $Index -lt $Lines.Count; $Index++) {
    $Line = $Lines[$Index]
    $OpenCount = ([regex]::Matches($Line, "\{")).Count
    $CloseCount = ([regex]::Matches($Line, "\}")).Count
    if ($OpenCount -gt 0) { $Started = $true }
    if ($Started) {
        $Depth += $OpenCount
        $Depth -= $CloseCount
        $End = $Index
        if ($Depth -eq 0) { break }
    }
}
if (-not $Started -or $Depth -ne 0) {
    throw "Could not determine complete function body for func_80019550."
}

$FunctionLines = @($Lines[$Start..$End])
$AiHits = @()
for ($Index = 0; $Index -lt $FunctionLines.Count; $Index++) {
    if ($FunctionLines[$Index] -match "A450|MEM_W|MEM_H|MEM_B") {
        $AiHits += [pscustomobject]@{
            AbsoluteLine = $Start + $Index + 1
            Text = $FunctionLines[$Index].Trim()
        }
    }
}

$GlobalAiHits = @(
    Get-ChildItem -LiteralPath $GeneratedDir -Filter "funcs_*.c" -File |
        Select-String -Pattern "A4500000|A4500004|A450000C"
)

$Report = New-Object System.Collections.Generic.List[string]
$Report.Add("=== Aero-Stadium-2-FR / func_80019550 diagnostic ===")
$Report.Add("Runner version: $RunnerVersion")
$Report.Add("Source: $SourcePath")
$Report.Add("Function lines: $($Start + 1)-$($End + 1)")
$Report.Add("")
$Report.Add("=== All func_80019550 occurrences ===")
foreach ($Occurrence in $Classified) {
    $Report.Add(("{0}:{1}: definition={2} :: {3}" -f $Occurrence.Path, $Occurrence.LineNumber, $Occurrence.IsDefinition, $Occurrence.Line))
}
$Report.Add("")
$Report.Add("=== Function source ===")
for ($Index = $Start; $Index -le $End; $Index++) {
    $Report.Add(("{0,6}: {1}" -f ($Index + 1), $Lines[$Index]))
}
$Report.Add("")
$Report.Add("=== Memory accesses inside func_80019550 ===")
if ($AiHits.Count -eq 0) {
    $Report.Add("none")
}
else {
    foreach ($Hit in $AiHits) {
        $Report.Add(("{0,6}: {1}" -f $Hit.AbsoluteLine, $Hit.Text))
    }
}
$Report.Add("")
$Report.Add("=== Generated references to AI registers ===")
if ($GlobalAiHits.Count -eq 0) {
    $Report.Add("none")
}
else {
    foreach ($Hit in $GlobalAiHits) {
        $Report.Add(("{0}:{1}: {2}" -f $Hit.Path, $Hit.LineNumber, $Hit.Line.Trim()))
    }
}

$Report | Set-Content -LiteralPath $ReportPath -Encoding UTF8
Write-Host "Diagnostic written: $ReportPath"
Write-Host "Function source: $SourcePath"
Write-Host "AI-related lines in function: $($AiHits.Count)"
Write-Host "Global AI register references: $($GlobalAiHits.Count)"
exit 0
