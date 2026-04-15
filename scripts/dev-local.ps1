Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$apiDir = Join-Path $root 'packages/api'
$venvPython = Join-Path $apiDir '.venv/Scripts/python.exe'

if (-not (Test-Path $venvPython)) {
  Write-Host "Missing packages/api/.venv. Run 'pnpm setup:local' first." -ForegroundColor Red
  exit 1
}

$webCommand = "Set-Location '$root'; pnpm --filter web dev"
$apiCommand = "Set-Location '$apiDir'; & '$venvPython' -m uvicorn main:app --reload --port 8000"

Write-Host "Starting web app and API in separate PowerShell windows..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit', '-Command', $webCommand | Out-Null
Start-Process powershell -ArgumentList '-NoExit', '-Command', $apiCommand | Out-Null

Write-Host "Web: http://localhost:3000" -ForegroundColor Green
Write-Host "API: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "Use Ctrl+C in each spawned window to stop services." -ForegroundColor Yellow
