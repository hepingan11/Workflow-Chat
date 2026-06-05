$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
$usePyLauncher = $false

if (-not $pythonCmd) {
  $pythonCmd = Get-Command py -ErrorAction SilentlyContinue
  $usePyLauncher = $true
}

if (-not $pythonCmd) {
  Write-Error "Python was not found. Please install Python 3.11+ first."
}

if ($usePyLauncher) {
  py -3 scripts/setup.py
} else {
  python scripts/setup.py
}
