#requires -Version 7
<#
.SYNOPSIS
  Fast-forward the stable branch to upstream, then merge it into the dev branch.

.DESCRIPTION
  - master tracks the official repository and only ever fast-forwards.
  - dev carries your fork's changes; each run merges master into it.
  Both branches are pushed to origin. Run from anywhere; the script locates
  the repository root from its own path.
#>
[CmdletBinding()]
param(
  [string]$UpstreamUrl = 'https://github.com/deepseek-ai/deepseek-harness.git',
  [string]$DevBranch = 'dev',
  [string]$StableBranch = 'master'
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

function Invoke-Git {
  param([Parameter(ValueFromRemainingArguments)][string[]]$Args)
  & git @Args
  if ($LASTEXITCODE -ne 0) { throw "git $($Args -join ' ') failed (exit $LASTEXITCODE)" }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  throw 'git not found on PATH.'
}

# Refuse to run with uncommitted changes: merging over a dirty tree can
# destroy local work.
if (git status --porcelain) {
  throw 'working tree has uncommitted changes. Commit or stash them first.'
}

# Ensure the upstream remote exists and points at the official repo.
$existing = git remote get-url upstream 2>$null
if (-not $existing) {
  Write-Host "[sync] adding upstream remote: $UpstreamUrl"
  Invoke-Git remote add upstream $UpstreamUrl
}

Write-Host '[sync] fetching upstream...'
Invoke-Git fetch upstream
Invoke-Git fetch origin

# --- stable branch: fast-forward only, never carries local commits ---
Write-Host "[sync] updating $StableBranch to upstream/$StableBranch (fast-forward only)..."
Invoke-Git checkout $StableBranch
try {
  Invoke-Git merge --ff-only "upstream/$StableBranch"
} catch {
  throw "$StableBranch has diverged from upstream. Inspect with: git log --oneline $StableBranch...upstream/$StableBranch"
}

Write-Host "[sync] pushing $StableBranch to origin..."
Invoke-Git push origin $StableBranch

# --- dev branch: create on first run, then absorb the stable branch ---
git show-ref --verify --quiet "refs/heads/$DevBranch"
if ($LASTEXITCODE -ne 0) {
  Write-Host "[sync] creating $DevBranch from $StableBranch..."
  Invoke-Git checkout -b $DevBranch
} else {
  Invoke-Git checkout $DevBranch
}

Write-Host "[sync] merging $StableBranch into $DevBranch..."
try {
  Invoke-Git merge $StableBranch --no-edit
} catch {
  throw "merge conflict. Resolve it, then: git add . ; git merge --continue ; git push origin $DevBranch"
}

Write-Host "[sync] pushing $DevBranch to origin..."
Invoke-Git push -u origin $DevBranch

Write-Host "[sync] done: $StableBranch tracks upstream, $DevBranch carries your changes on top."