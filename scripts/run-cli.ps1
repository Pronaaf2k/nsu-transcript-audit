Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'import-root-env.ps1')
[void](Import-RootEnv -RootPath $root)

$apiDir = Join-Path $root 'packages/api'
$venvPython = Join-Path $root 'packages/cli/.venv/Scripts/python.exe'
$apiPython = Join-Path $apiDir '.venv/Scripts/python.exe'
$apiUrl = 'http://127.0.0.1:8000/health'

function Test-ApiUp {
  try {
    $null = Invoke-WebRequest -Uri $apiUrl -UseBasicParsing -TimeoutSec 2
    return $true
  }
  catch {
    return $false
  }
}

if (-not (Test-Path $venvPython)) {
  Write-Host "Missing packages/cli/.venv. Run 'pnpm setup:local' first." -ForegroundColor Red
  exit 1
}

$mutexName = 'Global\nsu-transcript-audit-api-startup'
$mutexCreated = $false
$startupMutex = [System.Threading.Mutex]::new($false, $mutexName, [ref]$mutexCreated)
$hasMutex = $false

try {
  try {
    $hasMutex = $startupMutex.WaitOne(30000)
  }
  catch [System.Threading.AbandonedMutexException] {
    $hasMutex = $true
  }

  if (-not $hasMutex) {
    Write-Host "Timed out waiting for API startup lock." -ForegroundColor Red
    exit 1
  }

  if (-not (Test-ApiUp)) {
    if (-not (Test-Path $apiPython)) {
      Write-Host "Missing packages/api/.venv. Run 'pnpm setup:local' first." -ForegroundColor Red
      exit 1
    }

    Write-Host "API not running. Starting local backend on http://localhost:8000 ..." -ForegroundColor Yellow
    $apiCommand = "Set-Location '$apiDir'; & '$apiPython' -m uvicorn main:app --reload --port 8000"
    Start-Process powershell -ArgumentList '-NoExit', '-Command', $apiCommand | Out-Null

    $maxAttempts = 60
    for ($i = 0; $i -lt $maxAttempts; $i++) {
      Start-Sleep -Milliseconds 500
      if (Test-ApiUp) {
        Write-Host "API is ready." -ForegroundColor Green
        break
      }
    }

    if (-not (Test-ApiUp)) {
      Write-Host "API failed to start in time. Check the spawned API window for errors." -ForegroundColor Red
      exit 1
    }
  }
}
finally {
  if ($hasMutex) {
    $startupMutex.ReleaseMutex() | Out-Null
  }
  $startupMutex.Dispose()
}

Push-Location (Join-Path $root 'packages/cli')
try {
  & "$venvPython" main.py @args
}
finally {
  Pop-Location
}
