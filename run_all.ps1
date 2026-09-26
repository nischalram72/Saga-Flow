Write-Host "Starting Sagaflow Services..."

$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Definition

$job1 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\order-service'; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8001" -PassThru
$job2 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\inventory-service'; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8002" -PassThru
$job3 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\payment-service'; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8003" -PassThru
$job4 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\orchestrator-service'; .\venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8004" -PassThru

$job5 = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$scriptPath\frontend'; npm run dev" -PassThru

Write-Host "All services started in new windows!"
