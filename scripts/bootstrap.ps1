$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:WORKFLOW_CHAT_REPO_URL) { $env:WORKFLOW_CHAT_REPO_URL } else { "https://github.com/hepingan11/Workflow-Chat.git" }
$Branch = if ($env:WORKFLOW_CHAT_BRANCH) { $env:WORKFLOW_CHAT_BRANCH } else { "main" }
$InstallDir = if ($env:WORKFLOW_CHAT_INSTALL_DIR) { $env:WORKFLOW_CHAT_INSTALL_DIR } else { Join-Path (Get-Location) "Workflow-Chat" }

function Require-Command($Name, $InstallHint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Error "Missing command: $Name. $InstallHint"
  }
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

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Warning "npm was not found. Web dependency installation will fail until Node.js is installed: https://nodejs.org/"
}

if (Test-Path $InstallDir) {
  if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "Existing repository found, updating..." -ForegroundColor Yellow
    git -C $InstallDir fetch origin $Branch
    git -C $InstallDir checkout $Branch
    git -C $InstallDir pull --ff-only origin $Branch
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
