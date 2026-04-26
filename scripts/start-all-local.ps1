Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'import-root-env.ps1')
[void](Import-RootEnv -RootPath $root)

$apiPython = Join-Path $root 'packages/api/.venv/Scripts/python.exe'

if (-not (Test-Path $apiPython)) {
  Write-Host "Missing packages/api/.venv. Run 'pnpm setup:local' first." -ForegroundColor Red
  exit 1
}

$webCommand = "`$env:Path += ';C:\Program Files\nodejs;C:\Users\$env:USERNAME\AppData\Roaming\npm'; Set-Location '$root'; powershell -ExecutionPolicy Bypass -File '$root\scripts\run-web.ps1'"
$apiCommand = "Set-Location '$root\packages\api'; & '$apiPython' -m uvicorn main:app --reload --port 8000"
$mcpCommand = "Set-Location '$root'; & '$apiPython' '$root\packages\api\mcp_server.py'"

Write-Host "Starting services in separate PowerShell windows..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList '-NoExit', '-Command', $apiCommand | Out-Null
Start-Process powershell -ArgumentList '-NoExit', '-Command', $webCommand | Out-Null
Start-Process powershell -ArgumentList '-NoExit', '-Command', $mcpCommand | Out-Null

Write-Host "Started:" -ForegroundColor Green
Write-Host "  API:          http://localhost:8000/docs" -ForegroundColor Green
Write-Host "  Web:          http://localhost:3000" -ForegroundColor Green
Write-Host "  MCP:          packages/api/mcp_server.py" -ForegroundColor Green
Write-Host "Close each spawned window to stop its service." -ForegroundColor Yellow
