param([switch]$Force)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Rt64Owner = "rt64"
$Rt64Repo = "rt64"
$Rt64Commit = "23cab603c4f9f4a8b369b38e036f1aa484603878"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$LocalRoot = Join-Path $RepoRoot ".local\rt64"
$SourceDir = Join-Path $LocalRoot "src"
$PinFile = Join-Path $LocalRoot "PINNED_COMMIT.txt"
$TempRoot = Join-Path $LocalRoot ".download"

$Headers = @{
    "User-Agent" = "AeroStadium2-RT64-Setup"
    "Accept" = "application/vnd.github+json"
}
if ($env:GITHUB_TOKEN) {
    $Headers["Authorization"] = "Bearer $($env:GITHUB_TOKEN)"
}

function Get-GitHubRepoFromUrl {
    param([string]$Url, [string]$ParentOwner, [string]$ParentRepo)

    $Resolved = $Url.Trim()
    if ($Resolved -match "^git@github\.com:([^/]+)/(.+)$") {
        return [pscustomobject]@{ Owner = $Matches[1]; Repo = ($Matches[2] -replace "\.git$", "") }
    }

    if ($Resolved.StartsWith("../") -or $Resolved.StartsWith("./")) {
        $Base = [Uri]("https://github.com/{0}/{1}/" -f $ParentOwner, $ParentRepo)
        $Resolved = ([Uri]::new($Base, $Resolved)).AbsoluteUri
    }

    $Uri = [Uri]$Resolved
    if ($Uri.Host -ne "github.com") {
        throw "Unsupported submodule URL: $Url"
    }

    $Parts = $Uri.AbsolutePath.Trim("/").Split("/")
    if ($Parts.Count -lt 2) {
        throw "Could not parse submodule URL: $Url"
    }

    return [pscustomobject]@{
        Owner = $Parts[0]
        Repo = ($Parts[1] -replace "\.git$", "")
    }
}

function Read-Gitmodules {
    param([string]$Path)

    $Result = @{}
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $Result
    }

    $CurrentPath = $null
    $CurrentUrl = $null

    foreach ($Line in Get-Content -LiteralPath $Path) {
        $Trimmed = $Line.Trim()

        if ($Trimmed -match "^\[submodule\s+") {
            if ($CurrentPath -and $CurrentUrl) {
                $Result[$CurrentPath] = $CurrentUrl
            }
            $CurrentPath = $null
            $CurrentUrl = $null
            continue
        }

        if ($Trimmed -match "^path\s*=\s*(.+)$") {
            $CurrentPath = $Matches[1].Trim()
            continue
        }

        if ($Trimmed -match "^url\s*=\s*(.+)$") {
            $CurrentUrl = $Matches[1].Trim()
            continue
        }
    }

    if ($CurrentPath -and $CurrentUrl) {
        $Result[$CurrentPath] = $CurrentUrl
    }

    return $Result
}

function Download-GitHubArchive {
    param([string]$Owner, [string]$Repo, [string]$Commit, [string]$Destination)

    $SafeName = ("{0}_{1}_{2}" -f $Owner, $Repo, $Commit) -replace "[^A-Za-z0-9_.-]", "_"
    $ZipPath = Join-Path $TempRoot "$SafeName.zip"
    $ExpandDir = Join-Path $TempRoot "$SafeName-expanded"

    Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ExpandDir -Recurse -Force -ErrorAction SilentlyContinue

    $ArchiveUrl = "https://codeload.github.com/$Owner/$Repo/zip/$Commit"
    Write-Host "  Download $Owner/$Repo @ $Commit"
    Invoke-WebRequest -Uri $ArchiveUrl -OutFile $ZipPath -Headers $Headers

    New-Item -ItemType Directory -Force -Path $ExpandDir | Out-Null
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExpandDir -Force

    $ArchiveRoot = Get-ChildItem -LiteralPath $ExpandDir -Directory | Select-Object -First 1
    if ($null -eq $ArchiveRoot) {
        throw "Archive $Owner/$Repo @ $Commit did not contain a root directory."
    }

    Remove-Item -LiteralPath $Destination -Recurse -Force -ErrorAction SilentlyContinue
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Destination) | Out-Null
    Move-Item -LiteralPath $ArchiveRoot.FullName -Destination $Destination

    Remove-Item -LiteralPath $ZipPath -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $ExpandDir -Recurse -Force -ErrorAction SilentlyContinue
}

function Install-GitHubTree {
    param([string]$Owner, [string]$Repo, [string]$Commit, [string]$Destination, [int]$Depth = 0)

    if ($Depth -gt 8) {
        throw "Submodule recursion is unexpectedly deep at $Owner/$Repo."
    }

    Download-GitHubArchive -Owner $Owner -Repo $Repo -Commit $Commit -Destination $Destination

    $GitmodulesPath = Join-Path $Destination ".gitmodules"
    if (-not (Test-Path -LiteralPath $GitmodulesPath -PathType Leaf)) {
        return
    }

    $Modules = Read-Gitmodules -Path $GitmodulesPath
    if ($Modules.Count -eq 0) {
        return
    }

    $TreeUrl = "https://api.github.com/repos/$Owner/$Repo/git/trees/$($Commit)?recursive=1"
    $TreeResponse = Invoke-RestMethod -Uri $TreeUrl -Headers $Headers
    if ($TreeResponse.truncated) {
        throw "GitHub returned a truncated tree for $Owner/$Repo @ $Commit."
    }

    $Gitlinks = @{}
    foreach ($Entry in $TreeResponse.tree) {
        if ($Entry.mode -eq "160000" -and $Entry.type -eq "commit") {
            $Gitlinks[$Entry.path] = $Entry.sha
        }
    }

    foreach ($ModulePath in ($Modules.Keys | Sort-Object)) {
        if (-not $Gitlinks.ContainsKey($ModulePath)) {
            Write-Warning "No gitlink found for $Owner/$Repo submodule $ModulePath; skipping."
            continue
        }

        $SubRepo = Get-GitHubRepoFromUrl -Url $Modules[$ModulePath] -ParentOwner $Owner -ParentRepo $Repo
        $SubCommit = [string]$Gitlinks[$ModulePath]
        $SubDestination = Join-Path $Destination ($ModulePath -replace "/", "\")
        $Indent = "  " * ($Depth + 1)
        Write-Host ("{0}Submodule {1} -> {2}/{3} @ {4}" -f $Indent, $ModulePath, $SubRepo.Owner, $SubRepo.Repo, $SubCommit)
        Install-GitHubTree -Owner $SubRepo.Owner -Repo $SubRepo.Repo -Commit $SubCommit -Destination $SubDestination -Depth ($Depth + 1)
    }
}

Write-Host "=== Aero-Stadium-2-FR / RT64 Windows source bootstrap ==="
Write-Host "RT64 pin : $Rt64Commit"
Write-Host "Target   : $SourceDir"
Write-Host ""

if ((Test-Path -LiteralPath $PinFile -PathType Leaf) -and (Test-Path -LiteralPath (Join-Path $SourceDir "CMakeLists.txt") -PathType Leaf) -and -not $Force) {
    $ExistingPin = (Get-Content -LiteralPath $PinFile -Raw).Trim()
    if ($ExistingPin -eq $Rt64Commit) {
        Write-Host "RT64 already matches the pinned commit. Use -Force to redownload."
        exit 0
    }
}

New-Item -ItemType Directory -Force -Path $LocalRoot | Out-Null
Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $TempRoot | Out-Null

try {
    if ($Force) {
        Remove-Item -LiteralPath $SourceDir -Recurse -Force -ErrorAction SilentlyContinue
    }

    Install-GitHubTree -Owner $Rt64Owner -Repo $Rt64Repo -Commit $Rt64Commit -Destination $SourceDir

    $RequiredFiles = @(
        "CMakeLists.txt",
        "src\hle\rt64_application.h",
        "src\contrib\dxc\bin\x64\dxc.exe",
        "src\contrib\dxc\bin\x64\dxcompiler.dll",
        "src\contrib\dxc\bin\x64\dxil.dll",
        "src\contrib\mupen64plus-win32-deps\SDL2-2.26.3\include\SDL.h",
        "src\contrib\mupen64plus-win32-deps\SDL2-2.26.3\lib\x64\SDL2.dll",
        "src\contrib\Vulkan-Headers\include\vulkan\vulkan.h",
        "src\contrib\zstd\build\cmake\CMakeLists.txt",
        "src\contrib\re-spirv\CMakeLists.txt",
        "src\contrib\nativefiledialog-extended\CMakeLists.txt"
    )

    $Missing = @()
    foreach ($RelativePath in $RequiredFiles) {
        $FullPath = Join-Path $SourceDir $RelativePath
        if (-not (Test-Path -LiteralPath $FullPath -PathType Leaf)) {
            $Missing += $RelativePath
        }
    }

    if ($Missing.Count -ne 0) {
        throw "RT64 bootstrap is incomplete. Missing: $($Missing -join ', ')"
    }

    Set-Content -LiteralPath $PinFile -Value $Rt64Commit -Encoding ASCII

    Write-Host ""
    Write-Host "RT64 source bootstrap: OK"
    Write-Host "Pinned commit: $Rt64Commit"
    Write-Host "Source       : $SourceDir"
    Write-Host ""
    Write-Host "Next:"
    Write-Host "  powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\windows\build_np3f_link_smoke.ps1 -Clean"
}
finally {
    Remove-Item -LiteralPath $TempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
