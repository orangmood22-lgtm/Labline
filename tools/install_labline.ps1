#Requires -Version 5.1
<#
.SYNOPSIS
    Project-local Labline skill installation via junction (Windows symlink equivalent).

.DESCRIPTION
    [DEPRECATED behavior — see warning below]
    Recommended over global install for projects that mix Labline with other skill packs.
    Creates a junction in <project>/.claude/skills/labline (or .agents/skills/labline) pointing
    to the cloned Labline repository's skills directory.

.NOTES
    ⚠️  KNOWN BUG: this script creates a NESTED junction at .claude/skills/labline/, which
    Claude Code's slash-command discovery does NOT find (CC only scans one directory level).
    The Bash version (install_labline.sh) was rewritten in v0.4.4 to use flat per-skill
    symlinks + a manifest-tracked re-runnable installer. PowerShell parity is pending.

    Recommended for Windows users:
      Option A (best):    Use WSL2 with the Bash installer:
                            wsl bash ~/labline_repo/tools/install_labline.sh
      Option B (manual):  Create flat junctions yourself, one per skill:
                            $repo = "C:\path\to\labline_repo"
                            $proj = "C:\path\to\your-project"
                            New-Item -ItemType Directory -Force "$proj\.claude\skills" | Out-Null
                            Get-ChildItem "$repo\skills" -Directory |
                              Where-Object { $_.Name -ne 'skills-codex' -and (Test-Path "$($_.FullName)\SKILL.md") } |
                              ForEach-Object {
                                $link = "$proj\.claude\skills\$($_.Name)"
                                if (-not (Test-Path $link)) {
                                  New-Item -ItemType Junction -Path $link -Target $_.FullName | Out-Null
                                }
                              }
      Option C (legacy):  Continue with this script — but Claude Code's slash-command
                          autocomplete will NOT see your skills (you'd have to invoke
                          them via /skills <name> or copy them out manually).

.PARAMETER ProjectPath
    Path to the project root. Defaults to current directory.

.PARAMETER Platform
    auto (default), claude, or codex. Auto-detects from project markers.

.PARAMETER LablineRepo
    Override path to Labline repo. Defaults to auto-detect.

.PARAMETER Force
    Replace existing target. Existing target is backed up to labline.backup.<timestamp>.

.PARAMETER NoDoc
    Skip updating CLAUDE.md / AGENTS.md.

.PARAMETER DryRun
    Print plan without making changes.

.EXAMPLE
    .\tools\install_labline.ps1
    .\tools\install_labline.ps1 C:\projects\my-paper -Platform codex
    .\tools\install_labline.ps1 -LablineRepo C:\Users\PC\.codex\Auto-research-in-sleep -Force
#>

[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$ProjectPath = (Get-Location).Path,

    [ValidateSet('auto', 'claude', 'codex')]
    [string]$Platform = 'auto',

    [string]$LablineRepo = '',

    [switch]$Force,
    [switch]$NoDoc,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

# ─── Resolve project path ─────────────────────────────────────────────────────
if (-not (Test-Path $ProjectPath -PathType Container)) {
    Write-Host "Error: project path does not exist: $ProjectPath" -ForegroundColor Red; exit 1
}
$ProjectPath = (Resolve-Path $ProjectPath).Path

# ─── Resolve Labline repo location ───────────────────────────────────────────────
function Resolve-LablineRepo {
    if ($LablineRepo) {
        if (Test-Path (Join-Path $LablineRepo 'skills')) { return (Resolve-Path $LablineRepo).Path }
        Write-Host "Error: -LablineRepo path has no skills/ subdir: $LablineRepo" -ForegroundColor Red; throw
    }
    $parent = Split-Path $PSScriptRoot -Parent
    if (Test-Path (Join-Path $parent 'skills')) { return $parent }
    if ($env:LABLINE_REPO -and (Test-Path (Join-Path $env:LABLINE_REPO 'skills'))) {
        return (Resolve-Path $env:LABLINE_REPO).Path
    }
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'labline_repo'),
        (Join-Path $env:USERPROFILE 'Desktop\labline_repo'),
        (Join-Path $env:USERPROFILE '.labline'),
        (Join-Path $env:USERPROFILE 'Desktop\Auto-research-in-sleep'),
        (Join-Path $env:USERPROFILE '.codex\Auto-research-in-sleep'),
        (Join-Path $env:USERPROFILE '.claude\Auto-research-in-sleep')
    )) {
        if (Test-Path (Join-Path $p 'skills')) { return $p }
    }
    Write-Host "Error: cannot find Labline repo. Use -LablineRepo PATH or set `$env:LABLINE_REPO." -ForegroundColor Red
    throw
}

$LablineRepoResolved = Resolve-LablineRepo

# ─── Resolve platform ─────────────────────────────────────────────────────────
function Detect-Platform {
    $hasClaude = (Test-Path (Join-Path $ProjectPath 'CLAUDE.md')) -or `
                 (Test-Path (Join-Path $ProjectPath '.claude\skills')) -or `
                 (Test-Path (Join-Path $ProjectPath '.claude\settings.json'))
    $hasCodex  = (Test-Path (Join-Path $ProjectPath 'AGENTS.md')) -or `
                 (Test-Path (Join-Path $ProjectPath '.agents\skills')) -or `
                 (Test-Path (Join-Path $ProjectPath '.codex\config.toml'))
    $hasCursor = (Test-Path (Join-Path $ProjectPath '.cursor')) -or `
                 (Test-Path (Join-Path $ProjectPath '.cursor\rules')) -or `
                 (Test-Path (Join-Path $ProjectPath '.cursor\mcp.json'))

    if ($hasCursor -and (-not $hasClaude) -and (-not $hasCodex)) { return 'cursor' }
    if ($hasClaude -and $hasCodex) { return 'ambiguous' }
    if ($hasClaude) { return 'claude' }
    if ($hasCodex)  { return 'codex' }
    return 'unknown'
}

if ($Platform -eq 'auto') {
    $detected = Detect-Platform
    switch ($detected) {
        'claude' { $Platform = 'claude' }
        'codex'  { $Platform = 'codex' }
        'cursor' {
            Write-Host "Error: Cursor does not use a project skills directory; see docs\CURSOR_ADAPTATION.md" -ForegroundColor Red; exit 1
        }
        'ambiguous' {
            Write-Host "Error: project has both Claude and Codex markers; pass -Platform claude or -Platform codex" -ForegroundColor Red; exit 1
        }
        'unknown' {
            Write-Host "Error: cannot auto-detect platform (no CLAUDE.md/AGENTS.md/.claude/.agents found)" -ForegroundColor Red
            Write-Host "       Pass -Platform claude or -Platform codex" -ForegroundColor Yellow
            exit 1
        }
    }
}

# ─── Compute paths ────────────────────────────────────────────────────────────
switch ($Platform) {
    'claude' {
        $SourceDir = Join-Path $LablineRepoResolved 'skills'
        $TargetRelative = '.claude\skills\labline'
        $DocFile = Join-Path $ProjectPath 'CLAUDE.md'
        $TargetRelDisplay = '.claude/skills/labline'
    }
    'codex' {
        $SourceDir = Join-Path $LablineRepoResolved 'skills\skills-codex'
        $TargetRelative = '.agents\skills\labline'
        $DocFile = Join-Path $ProjectPath 'AGENTS.md'
        $TargetRelDisplay = '.agents/skills/labline'
    }
}
$TargetDir = Join-Path $ProjectPath $TargetRelative
$TargetParent = Split-Path $TargetDir -Parent

if (-not (Test-Path $SourceDir -PathType Container)) {
    Write-Host "Error: source skill directory does not exist: $SourceDir" -ForegroundColor Red; exit 1
}

# ─── Print plan ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Labline Project Install Plan"
Write-Host "  Project:        $ProjectPath"
Write-Host "  Platform:       $Platform"
Write-Host "  Labline repo:      $LablineRepoResolved"
Write-Host "  Source:         $SourceDir"
Write-Host "  Target:         $TargetDir  (relative: $TargetRelDisplay)"
Write-Host "  Doc file:       $DocFile"
if ($DryRun) { Write-Host "  Mode:           DRY-RUN (no changes)" -ForegroundColor Yellow }
else         { Write-Host "  Mode:           APPLY" -ForegroundColor Green }
Write-Host ""

# ─── Idempotency check ────────────────────────────────────────────────────────
if (Test-Path $TargetDir) {
    $item = Get-Item $TargetDir -Force
    if ($item.LinkType -in @('Junction', 'SymbolicLink')) {
        $existingTarget = $item.Target | Select-Object -First 1
        if ($existingTarget -eq $SourceDir) {
            Write-Host "✓ Already installed (junction points to $SourceDir)" -ForegroundColor Green
            exit 0
        }
        if (-not $Force) {
            Write-Host "Error: target exists and points elsewhere:" -ForegroundColor Red
            Write-Host "  Target:    $TargetDir"
            Write-Host "  Currently: $existingTarget"
            Write-Host "  Expected:  $SourceDir"
            Write-Host "  Use -Force to backup and replace." -ForegroundColor Yellow
            exit 1
        }
    } elseif (-not $Force) {
        Write-Host "Error: target exists and is not a junction: $TargetDir" -ForegroundColor Red
        Write-Host "  Use -Force to backup (as labline.backup.<timestamp>) and replace." -ForegroundColor Yellow
        exit 1
    }
}

# ─── Apply ────────────────────────────────────────────────────────────────────
if ($DryRun) {
    Write-Host "(dry-run) would create junction: $TargetDir -> $SourceDir"
    if (-not $NoDoc) { Write-Host "(dry-run) would update doc:  $DocFile" }
    Write-Host "(dry-run) would record metadata: $ProjectPath\.labline\skill-source.txt"
    exit 0
}

# Backup if force-replacing
if ((Test-Path $TargetDir) -and $Force) {
    $backup = "${TargetDir}.backup.$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    Move-Item $TargetDir $backup
    Write-Host "Backed up existing target to: $backup" -ForegroundColor Yellow
}

# Create parent dir + junction
New-Item -ItemType Directory -Force -Path $TargetParent | Out-Null
New-Item -ItemType Junction -Path $TargetDir -Target $SourceDir | Out-Null
Write-Host "✓ Created junction: $TargetDir -> $SourceDir" -ForegroundColor Green

# Record metadata
$lablineDir = Join-Path $ProjectPath '.labline'
New-Item -ItemType Directory -Force -Path $lablineDir | Out-Null
$lablineCommit = try { (git -C $LablineRepoResolved rev-parse HEAD 2>$null).Trim() } catch { 'unknown' }
if (-not $lablineCommit) { $lablineCommit = 'unknown' }
$installedAt = (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ')
$metaContent = @"
platform=$Platform
link_mode=junction
project_path=$ProjectPath
link_path=$TargetDir
labline_repo=$LablineRepoResolved
skill_source=$SourceDir
labline_commit=$lablineCommit
installed_at=$installedAt
"@
Set-Content -Path (Join-Path $lablineDir 'skill-source.txt') -Value $metaContent -NoNewline
Write-Host "✓ Recorded metadata: $lablineDir\skill-source.txt" -ForegroundColor Green

# Update managed block in CLAUDE.md / AGENTS.md
if (-not $NoDoc) {
    $blockBegin = '<!-- Labline:BEGIN -->'
    $blockEnd   = '<!-- Labline:END -->'
    $blockBody = @"
$blockBegin
## Labline Skill Scope
For Labline workflows in this project, use only the project-local Labline skills under ``$TargetRelDisplay``.
Do not use global skills or non-Labline project skills unless the user explicitly asks to mix them.
$blockEnd
"@

    if ((Test-Path $DocFile) -and ((Get-Content $DocFile -Raw) -match [regex]::Escape($blockBegin))) {
        $text = Get-Content $DocFile -Raw
        $pattern = [regex]::Escape($blockBegin) + '.*?' + [regex]::Escape($blockEnd)
        $new = [regex]::Replace($text, $pattern, $blockBody, [System.Text.RegularExpressions.RegexOptions]::Singleline)
        Set-Content -Path $DocFile -Value $new -NoNewline
        Write-Host "✓ Updated managed Labline block in: $DocFile" -ForegroundColor Green
    } else {
        if ((Test-Path $DocFile) -and ((Get-Item $DocFile).Length -gt 0)) {
            Add-Content -Path $DocFile -Value ""
        }
        Add-Content -Path $DocFile -Value $blockBody
        Write-Host "✓ Appended managed Labline block to: $DocFile" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "Install complete. Update with: cd $LablineRepoResolved; git pull" -ForegroundColor Cyan
