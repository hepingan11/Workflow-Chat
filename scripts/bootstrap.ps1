$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:WORKFLOW_CHAT_REPO_URL) { $env:WORKFLOW_CHAT_REPO_URL } else { "https://github.com/hepingan11/Workflow-Chat.git" }
$Branch = if ($env:WORKFLOW_CHAT_BRANCH) { $env:WORKFLOW_CHAT_BRANCH } else { "main" }
$InstallDir = if ($env:WORKFLOW_CHAT_INSTALL_DIR) { $env:WORKFLOW_CHAT_INSTALL_DIR } else { Join-Path (Get-Location) "Workflow-Chat" }

function Require-Command($Name, $InstallHint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Error "Missing command: $Name. $InstallHint"
  }
}

function Ask-Yes($Prompt, $Default) {
  if ($env:WORKFLOW_CHAT_YES -eq "1" -or $env:WORKFLOW_CHAT_YES -eq "true") {
    return $true
  }

  $suffix = if ($Default) { "Y/n" } else { "y/N" }
  $answer = Read-Host "$Prompt ($suffix)"
  if ([string]::IsNullOrWhiteSpace($answer)) {
    return $Default
  }

  return @("y", "yes", "1", "true") -contains $answer.Trim().ToLowerInvariant()
}

function Get-GitOutput {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Arguments
  )
  $output = & git @Arguments 2>$null
  if ($LASTEXITCODE -ne 0) {
    return ""
  }
  return ($output | Out-String).Trim()
}

function Update-ExistingRepository {
  Write-Host "Existing repository found. Checking latest version..." -ForegroundColor Yellow

  $originUrl = Get-GitOutput @("-C", $InstallDir, "remote", "get-url", "origin")
  if ($originUrl -and $originUrl -ne $RepoUrl) {
    Write-Warning "Repository origin is different from bootstrap repo."
    Write-Host "Current origin: $originUrl"
    Write-Host "Bootstrap repo: $RepoUrl"
    if (-not (Ask-Yes "Continue with the current repository origin" $true)) {
      Write-Host "Stopped before setup."
      exit 0
    }
  }

  git -C $InstallDir fetch origin $Branch

  $currentBranch = Get-GitOutput @("-C", $InstallDir, "rev-parse", "--abbrev-ref", "HEAD")
  if ($currentBranch -ne $Branch) {
    Write-Warning "Current branch is '$currentBranch', target branch is '$Branch'."
    if (Ask-Yes "Checkout target branch '$Branch'" $true) {
      git -C $InstallDir checkout $Branch
    } else {
      Write-Host "Keeping current branch. Version check will continue on current HEAD."
    }
  }

  $localHead = Get-GitOutput @("-C", $InstallDir, "rev-parse", "HEAD")
  $remoteHead = Get-GitOutput @("-C", $InstallDir, "rev-parse", "origin/$Branch")
  $mergeBase = Get-GitOutput @("-C", $InstallDir, "merge-base", "HEAD", "origin/$Branch")
  $dirty = Get-GitOutput @("-C", $InstallDir, "status", "--porcelain")

  if (-not $localHead -or -not $remoteHead -or -not $mergeBase) {
    Write-Warning "Could not compare local and remote versions. Setup will continue without updating."
    return
  }

  if ($localHead -eq $remoteHead) {
    Write-Host "Current version is already up to date." -ForegroundColor Green
    return
  }

  if ($localHead -eq $mergeBase) {
    Write-Host "A newer version is available on origin/$Branch." -ForegroundColor Yellow
    Write-Host "Local:  $localHead"
    Write-Host "Remote: $remoteHead"

    if ($dirty) {
      Write-Warning "Local uncommitted changes were detected. The update uses git pull --ff-only and will not reset files."
      Write-Host $dirty
      if (-not (Ask-Yes "Try updating anyway" $false)) {
        Write-Host "Skipped update. Setup will continue with the current version."
        return
      }
    } elseif (-not (Ask-Yes "Update to the latest version before setup" $true)) {
      Write-Host "Skipped update. Setup will continue with the current version."
      return
    }

    git -C $InstallDir pull --ff-only origin $Branch
    return
  }

  if ($remoteHead -eq $mergeBase) {
    Write-Warning "Local repository is ahead of origin/$Branch. No update is needed."
    return
  }

  Write-Warning "Local and remote branches have diverged. Auto update was skipped to avoid overwriting your work."
  Write-Host "Please resolve with Git manually, then run bootstrap again."
}

Write-Host ""
Write-Host "Guiwuli Digital Employee bootstrap" -ForegroundColor Cyan
Write-Host "Repo:    $RepoUrl"
Write-Host "Branch:  $Branch"
Write-Host "Install: $InstallDir"
Write-Host ""

Require-Command "git" "Install Git first: https://git-scm.com/downloads"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
  $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $pythonCmd) {
  Write-Error "Missing Python. Install Python 3.11+ first: https://www.python.org/downloads/"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue) -and -not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
  Write-Warning "npm was not found. Web dependency installation will fail until Node.js is installed: https://nodejs.org/"
}

if (Test-Path $InstallDir) {
  if (Test-Path (Join-Path $InstallDir ".git")) {
    Update-ExistingRepository
  } else {
    Write-Error "Install directory exists but is not a Git repository: $InstallDir. Choose another directory or remove it and retry."
  }
} else {
  Write-Host "Cloning repository..." -ForegroundColor Yellow
  git clone --branch $Branch $RepoUrl $InstallDir
}

Set-Location $InstallDir

if (Test-Path ".\setup.ps1") {
  powershell -ExecutionPolicy Bypass -File ".\setup.ps1"
} else {
  Write-Error "setup.ps1 was not found in the repository."
}
