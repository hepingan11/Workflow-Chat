$ErrorActionPreference = "Stop"

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Set-Location -Path $PSScriptRoot

$apiDir = Join-Path $PSScriptRoot "apps\api"
$webDir = Join-Path $PSScriptRoot "apps\web"
$logDir = Join-Path $PSScriptRoot ".workflow-chat\logs"
$webLog = Join-Path $logDir "web-dev.log"
$venvPython = Join-Path $apiDir ".venv\Scripts\python.exe"

New-Item -ItemType Directory -Path $logDir -Force | Out-Null

function Get-PythonCommand {
  if (Test-Path $venvPython) {
    return $venvPython
  }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) {
    return $python.Source
  }

  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    return $py.Source
  }

  throw "Python was not found. Please install Python 3.11+ first."
}

function Ensure-ApiEnv {
  $python = Get-PythonCommand

  if (-not (Test-Path $venvPython)) {
    Write-Host "Creating API virtual environment..."
    if ((Split-Path -Leaf $python) -ieq "py.exe") {
      & $python -3 -m venv (Join-Path $apiDir ".venv")
    } else {
      & $python -m venv (Join-Path $apiDir ".venv")
    }
  }

  Write-Host "Installing API dependencies..."
  & $venvPython -m pip install -e $apiDir
}

function Ensure-WebEnv {
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm was not found. Please install Node.js first."
  }

  if (-not (Test-Path (Join-Path $webDir "node_modules"))) {
    Write-Host "Installing Web dependencies..."
    Push-Location $webDir
    try {
      npm install
    } finally {
      Pop-Location
    }
  }
}

function Stop-ProcessTree {
  param([int]$ProcessId)

  Get-CimInstance Win32_Process -Filter "ParentProcessId = $ProcessId" |
    ForEach-Object { Stop-ProcessTree -ProcessId $_.ProcessId }

  Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

Ensure-ApiEnv
Ensure-WebEnv

if (Test-Path $webLog) {
  Clear-Content -Path $webLog
}

Write-Host "Starting Web dev server in background..."
$webProcess = Start-Process `
  -FilePath "cmd.exe" `
  -ArgumentList @("/d", "/c", "npm run dev > `"$webLog`" 2>&1") `
  -WorkingDirectory $webDir `
  -PassThru `
  -WindowStyle Hidden

Write-Host "Web: http://127.0.0.1:3000"
Write-Host "Web log: $webLog"
Write-Host "API: http://127.0.0.1:8000"
Write-Host "Backend logs are shown below. Press Ctrl+C to stop both servers."
Write-Host ""

try {
  Push-Location $apiDir
  & $venvPython -m uvicorn app.main:app --host 127.0.0.1 --port 8000
} finally {
  Pop-Location
  if ($webProcess -and -not $webProcess.HasExited) {
    Write-Host ""
    Write-Host "Stopping Web dev server..."
    Stop-ProcessTree -ProcessId $webProcess.Id
  }
}
