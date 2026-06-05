$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  $python = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $python) {
  Write-Error "未找到 Python。请先安装 Python 3.11+。"
}

if ($python.Source -like "*\py.exe") {
  py -3 scripts/setup.py
} else {
  python scripts/setup.py
}
