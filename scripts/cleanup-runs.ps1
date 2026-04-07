param(
    [string]$RunsDir = "runs",
    [bool]$PruneBakCsv = $true,
    [bool]$PruneLocalSummary = $true,
    [bool]$PruneIndexDirs = $false,
    [bool]$PruneRunDirs = $false,
    [string[]]$RunDirsToPrune = @(
        "phase2-weekly-local",
        "phase3-wiki-check",
        "phase3-wiki-pr",
        "quality-manual-20260404",
        "real-llm-check"
    ),
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-PathSizeBytes {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return [int64]0
    }

    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        return [int64](Get-Item -LiteralPath $Path).Length
    }

    $measure = Get-ChildItem -LiteralPath $Path -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum

    if ($null -eq $measure.Sum) {
        return [int64]0
    }

    return [int64]$measure.Sum
}

function Is-ChildPath {
    param(
        [string]$Path,
        [string]$PotentialParent
    )

    if ($Path.Length -le $PotentialParent.Length) {
        return $false
    }

    $prefix = $PotentialParent.TrimEnd([char[]]@('\', '/')) + [System.IO.Path]::DirectorySeparatorChar
    return $Path.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)
}

$runsRoot = Resolve-Path -LiteralPath $RunsDir -ErrorAction Stop
$runsRootPath = $runsRoot.Path

$seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
$rawCandidates = New-Object System.Collections.Generic.List[object]

function Add-Candidate {
    param(
        [string]$Type,
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $item = Get-Item -LiteralPath $Path
    $fullPath = $item.FullName

    if (-not $seen.Add($fullPath)) {
        return
    }

    $rawCandidates.Add(
        [pscustomobject]@{
            Type = $Type
            Path = $fullPath
            SizeBytes = Get-PathSizeBytes -Path $fullPath
        }
    ) | Out-Null
}

if ($PruneBakCsv) {
    Get-ChildItem -LiteralPath $runsRootPath -Recurse -File -Filter "*.bak.csv" |
        ForEach-Object {
            Add-Candidate -Type "bak-csv" -Path $_.FullName
        }
}

if ($PruneLocalSummary) {
    Get-ChildItem -LiteralPath $runsRootPath -Recurse -File -Filter "local-summary.json" |
        ForEach-Object {
            Add-Candidate -Type "local-summary" -Path $_.FullName
        }
}

if ($PruneIndexDirs) {
    Get-ChildItem -LiteralPath $runsRootPath -Recurse -Directory |
        Where-Object { $_.Name -eq "index" } |
        ForEach-Object {
            Add-Candidate -Type "index-dir" -Path $_.FullName
        }
}

if ($PruneRunDirs) {
    foreach ($dirName in $RunDirsToPrune) {
        $path = Join-Path $runsRootPath $dirName
        Add-Candidate -Type "run-dir" -Path $path
    }
}

# Remove nested children when parent is also selected.
$ordered = $rawCandidates | Sort-Object { $_.Path.Length }
$finalCandidates = New-Object System.Collections.Generic.List[object]
foreach ($candidate in $ordered) {
    $isChild = $false
    foreach ($kept in $finalCandidates) {
        if (Is-ChildPath -Path $candidate.Path -PotentialParent $kept.Path) {
            $isChild = $true
            break
        }
    }

    if (-not $isChild) {
        $finalCandidates.Add($candidate) | Out-Null
    }
}

if ($finalCandidates.Count -eq 0) {
    Write-Host "No cleanup candidates found under $runsRootPath"
    exit 0
}

$totalBytes = ($finalCandidates | Measure-Object -Property SizeBytes -Sum).Sum
if ($null -eq $totalBytes) {
    $totalBytes = 0
}

Write-Host "Cleanup candidates under $runsRootPath"
($finalCandidates |
    Sort-Object Type, Path |
    Select-Object Type, @{Name = "SizeKB"; Expression = { [math]::Round($_.SizeBytes / 1KB, 2) } }, Path |
    Format-Table -AutoSize | Out-String).TrimEnd() | Write-Host
Write-Host ("Total candidate size: {0} KB" -f [math]::Round(($totalBytes / 1KB), 2))

if (-not $Apply) {
    Write-Host "Dry run only. Re-run with -Apply to delete candidates."
    exit 0
}

foreach ($entry in ($finalCandidates | Sort-Object { $_.Path.Length } -Descending)) {
    if (-not (Test-Path -LiteralPath $entry.Path)) {
        continue
    }

    Remove-Item -LiteralPath $entry.Path -Recurse -Force
    Write-Host "Deleted [$($entry.Type)] $($entry.Path)"
}

Write-Host "Cleanup completed."