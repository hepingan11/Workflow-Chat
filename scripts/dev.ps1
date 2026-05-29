$ErrorActionPreference = "Stop"

Write-Host "Workflow Chat scaffold"
Write-Host "API:    cd apps/api; pip install -e .; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Write-Host "Worker: cd apps/worker; pip install -e .; python -m worker.main"
Write-Host "Web:    cd apps/web; npm install; cmd /c npm run dev"
