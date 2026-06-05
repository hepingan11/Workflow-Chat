$ErrorActionPreference = "Stop"

$RepoUrl = if ($env:WORKFLOW_CHAT_REPO_URL) { $env:WORKFLOW_CHAT_REPO_URL } else { "https://github.com/hepingan11/Guiwuli-Digital-Employee.git" }
$Branch = if ($env:WORKFLOW_CHAT_BRANCH) { $env:WORKFLOW_CHAT_BRANCH } else { "main" }
$InstallDir = if ($env:WORKFLOW_CHAT_INSTALL_DIR) { $env:WORKFLOW_CHAT_INSTALL_DIR } else { Join-Path (Get-Location) "Guiwuli-Digital-Employee" }

function Require-Command($Name, $InstallHint) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Write-Error "缺少命令：$Name。$InstallHint"
  }
}

Write-Host ""
Write-Host "Guiwuli Digital Employee bootstrap" -ForegroundColor Cyan
Write-Host "Repo:    $RepoUrl"
Write-Host "Branch:  $Branch"
Write-Host "Install: $InstallDir"
Write-Host ""

Require-Command "git" "请先安装 Git：https://git-scm.com/downloads"

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  $python = Get-Command py -ErrorAction SilentlyContinue
}
if (-not $python) {
  Write-Error "缺少 Python。请先安装 Python 3.11+：https://www.python.org/downloads/"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Warning "未检测到 npm。Web 依赖安装会失败，请先安装 Node.js：https://nodejs.org/"
}

if (Test-Path $InstallDir) {
  if (Test-Path (Join-Path $InstallDir ".git")) {
    Write-Host "检测到已有仓库，正在更新..." -ForegroundColor Yellow
    git -C $InstallDir fetch origin $Branch
    git -C $InstallDir checkout $Branch
    git -C $InstallDir pull --ff-only origin $Branch
  } else {
    Write-Error "安装目录已存在但不是 Git 仓库：$InstallDir。请换一个目录或删除后重试。"
  }
} else {
  Write-Host "正在拉取仓库..." -ForegroundColor Yellow
  git clone --branch $Branch $RepoUrl $InstallDir
}

Set-Location $InstallDir

if (Test-Path ".\setup.ps1") {
  powershell -ExecutionPolicy Bypass -File ".\setup.ps1"
} else {
  Write-Error "仓库中未找到 setup.ps1，无法继续初始化。"
}
